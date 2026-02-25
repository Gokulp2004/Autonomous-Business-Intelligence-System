"""
insight_generator.py - Optimized Gemini-Powered Insight Generation

Optimizations applied:
  1. Response caching — same data = same insight, no repeat API calls
  2. Token-compressed prompts — only send essential stats (~60% fewer tokens)
  3. Rate limiting with exponential backoff + jitter
  4. Local fallback — generates basic insights without API when quota is exhausted
"""

import os
import json
import asyncio
import hashlib
import random
import traceback
from typing import Optional

from google import genai
from google.genai import types as genai_types

from ..config import settings

MAX_RETRIES = 2          # reduced from 3 to fail faster
RETRY_DELAYS = [5, 15]   # shorter delays

# ── In-memory cache ──────────────────────────────────────────
_insight_cache: dict[str, dict] = {}

# ── Quota cooldown ───────────────────────────────────────────
import time
_api_cooldown_until: float = 0
_API_COOLDOWN_SECS = 300  # 5 minutes


def _is_api_available() -> bool:
    return time.time() > _api_cooldown_until


def _set_api_cooldown():
    global _api_cooldown_until
    _api_cooldown_until = time.time() + _API_COOLDOWN_SECS
    print(f"[InsightGen] API cooldown set for {_API_COOLDOWN_SECS}s.")


def _cache_key(analysis: dict, anomalies: dict, forecasts: list) -> str:
    """Generate a hash key from analysis inputs so identical data reuses cached insights."""
    summary = analysis.get("summary", {})
    sig = json.dumps({
        "rows": summary.get("total_rows"),
        "cols": summary.get("total_columns"),
        "corr_count": len(analysis.get("strong_correlations", [])),
        "anomaly_count": (anomalies or {}).get("summary", {}).get("total_anomalous_values", 0),
        "forecast_count": len(forecasts) if isinstance(forecasts, list) else 0,
    }, sort_keys=True)
    return hashlib.md5(sig.encode()).hexdigest()


# ── Token-Compressed Prompt ──────────────────────────────────

INSIGHT_PROMPT = """You are a BI Analyst. Analyze this data and produce a Markdown insight report.

## Dataset
{overview}

## Key Statistics (top columns)
{descriptive_stats}

## Strong Correlations
{correlations}

## Distributions
{distributions}

## Trends
{trends}

## Anomalies
{anomalies}

## Forecasts
{forecasts}

---

Generate a concise insight report with these sections:

## Executive Summary
2-3 sentences on the most critical findings.

## Key Findings
Top 3-5 discoveries with supporting data points.

## Trends & Patterns
Significant trends with direction and magnitude.

## Anomalies & Concerns
Unusual values or data quality issues.

## Actionable Recommendations
3-5 specific, ranked recommendations.

Use bullet points, bold for emphasis, and include specific numbers. Be concise.
"""


def _format_dict_compact(d: dict, max_chars: int = 2000) -> str:
    """Format dict compactly — much smaller than the old 5000-char limit."""
    if not d:
        return "None."
    try:
        return json.dumps(d, indent=1, default=str)[:max_chars]
    except Exception:
        return str(d)[:max_chars]


def _format_stats_compact(stats: dict) -> str:
    """Only send mean/min/max per column — NOT the full 11-metric table."""
    if not stats:
        return "None."
    lines = []
    for col, metrics in list(stats.items())[:8]:  # max 8 columns
        mean = metrics.get("mean", "?")
        mn = metrics.get("min", "?")
        mx = metrics.get("max", "?")
        lines.append(f"{col}: mean={mean}, min={mn}, max={mx}")
    return "\n".join(lines) if lines else "None."


def _format_correlations_compact(corrs: list) -> str:
    """Only top 5 correlations, one line each."""
    if not corrs:
        return "None."
    lines = []
    for c in corrs[:5]:
        lines.append(f"{c.get('col_a')} <-> {c.get('col_b')}: r={c.get('correlation', '?')}")
    return "\n".join(lines)


def _format_anomalies_compact(anomaly_results: dict) -> str:
    """Minimal anomaly summary."""
    if not anomaly_results:
        return "None."
    summary = anomaly_results.get("summary", {})
    per_col = anomaly_results.get("per_column", {})
    lines = [f"Total anomalies: {summary.get('total_anomalous_values', 0)}"]
    for col, data in list(per_col.items())[:6]:
        z = data.get("z_score", {}).get("count", 0)
        iqr = data.get("iqr", {}).get("count", 0)
        lines.append(f"  {col}: z={z}, iqr={iqr}")
    return "\n".join(lines)


def _format_forecasts_compact(forecast_results: list) -> str:
    """One line per forecast column."""
    if not forecast_results:
        return "None."
    lines = []
    for fc in forecast_results[:6]:
        col = fc.get("column", "?")
        method = fc.get("method", "?")
        preds = fc.get("forecast", [])
        last_val = preds[-1].get("predicted", "?") if preds else "?"
        lines.append(f"{col} ({method}): last_predicted={last_val}")
    return "\n".join(lines) if lines else "None."


async def generate_insights(
    analysis_results: dict,
    anomaly_results: Optional[dict] = None,
    forecast_results: Optional[list] = None,
) -> dict:
    """
    Generate AI-powered insights. Optimized flow:
      1. Check cache → return if hit
      2. Try Gemini API with compressed prompt
      3. On quota error → generate local fallback insights (no API needed)
    """
    # ── 1. Cache check ───────────────────────────────────────
    key = _cache_key(analysis_results, anomaly_results or {}, forecast_results or [])
    if key in _insight_cache:
        return _insight_cache[key]

    # ── 2. Cooldown check — skip API if recently rate-limited ─
    if not _is_api_available():
        result = _generate_local_insights(analysis_results, anomaly_results, forecast_results)
        _insight_cache[key] = result
        return result

    # ── 3. Ensure API key ────────────────────────────────────
    api_key = settings.GOOGLE_API_KEY
    if not api_key or api_key == "your_google_api_key_here":
        api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv()
            api_key = os.environ.get("GOOGLE_API_KEY", "")
        except Exception:
            pass
    if not api_key or api_key == "your_google_api_key_here":
        result = _generate_local_insights(analysis_results, anomaly_results, forecast_results)
        _insight_cache[key] = result
        return result

    print(f"[InsightGen] Using API key: {api_key[:10]}... model: {settings.GEMINI_MODEL}")

    try:
        # Build compact prompt
        summary = analysis_results.get("summary", {})
        overview = (
            f"Rows: {summary.get('total_rows', '?')}, "
            f"Columns: {summary.get('total_columns', '?')} "
            f"({summary.get('numeric_columns', 0)} numeric, "
            f"{summary.get('categorical_columns', 0)} categorical)"
        )

        prompt = INSIGHT_PROMPT.format(
            overview=overview,
            descriptive_stats=_format_stats_compact(analysis_results.get("descriptive_stats", {})),
            correlations=_format_correlations_compact(analysis_results.get("strong_correlations", [])),
            distributions=_format_dict_compact(analysis_results.get("distributions", {}), 1500),
            trends=_format_dict_compact(analysis_results.get("trends", {}), 1500),
            anomalies=_format_anomalies_compact(anomaly_results or {}),
            forecasts=_format_forecasts_compact(forecast_results or []),
        )

        # Call Gemini with retry + jitter
        client = genai.Client(api_key=api_key)
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await client.aio.models.generate_content(
                    model=settings.GEMINI_MODEL,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.2,
                        max_output_tokens=2048,  # reduced from 4096
                    ),
                )
                break
            except Exception as retry_err:
                last_error = retry_err
                err_str = str(retry_err)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    if attempt < MAX_RETRIES - 1:
                        delay = RETRY_DELAYS[attempt] + random.uniform(0, 3)
                        print(f"[InsightGen] Rate limited, retrying in {delay:.1f}s (attempt {attempt+1})")
                        await asyncio.sleep(delay)
                        continue
                    # All retries exhausted → set cooldown + fall back to local
                    _set_api_cooldown()
                    print("[InsightGen] Quota exhausted, using local fallback.")
                    result = _generate_local_insights(analysis_results, anomaly_results, forecast_results)
                    _insight_cache[key] = result
                    return result
                raise

        insight_text = response.text if response.text else "No insights generated."
        sections = _parse_sections(insight_text)

        result = {"insights": insight_text, "sections": sections, "error": None}
        _insight_cache[key] = result
        return result

    except Exception as e:
        traceback.print_exc()
        # On any failure, try local fallback
        print(f"[InsightGen] API failed: {e}. Using local fallback.")
        result = _generate_local_insights(analysis_results, anomaly_results, forecast_results)
        _insight_cache[key] = result
        return result


def _parse_sections(markdown: str) -> dict:
    """Parse a markdown insight report into individual sections."""
    sections = {}
    current_section = None
    current_lines = []
    
    for line in markdown.split("\n"):
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = line[3:].strip().lower().replace(" ", "_").replace("&", "and")
            current_lines = []
        elif current_section:
            current_lines.append(line)
    
    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()
    
    return sections


# ══════════════════════════════════════════════════════════════
#  LOCAL FALLBACK — generates insights from data alone (no API)
# ══════════════════════════════════════════════════════════════

def _generate_local_insights(
    analysis_results: dict,
    anomaly_results: Optional[dict] = None,
    forecast_results: Optional[list] = None,
) -> dict:
    """Generate basic insights using statistical data directly — zero API calls."""
    summary = analysis_results.get("summary", {})
    stats = analysis_results.get("descriptive_stats", {})
    corrs = analysis_results.get("strong_correlations", [])
    distributions = analysis_results.get("distributions", {})
    trends = analysis_results.get("trends", {})
    feature_imp = analysis_results.get("feature_importance", [])
    anomalies = anomaly_results or {}

    lines = []

    # ── Executive Summary ────────────────────────────────────
    lines.append("## Executive Summary")
    lines.append(
        f"This dataset contains **{summary.get('total_rows', '?')} rows** and "
        f"**{summary.get('total_columns', '?')} columns** "
        f"({summary.get('numeric_columns', 0)} numeric, "
        f"{summary.get('categorical_columns', 0)} categorical). "
    )
    anomaly_total = anomalies.get("summary", {}).get("total_anomalous_values", 0)
    if anomaly_total > 0:
        lines.append(f"**{anomaly_total} anomalous values** were detected across the dataset. ")
    if corrs:
        lines.append(f"**{len(corrs)} strong correlations** were found between variables.")
    lines.append("")

    # ── Key Findings ─────────────────────────────────────────
    lines.append("## Key Findings")
    finding_num = 1
    for col, m in list(stats.items())[:5]:
        mean = m.get("mean")
        std = m.get("std")
        if mean is not None and std is not None:
            cv = abs(std / mean * 100) if mean != 0 else 0
            volatility = "high" if cv > 50 else "moderate" if cv > 20 else "low"
            lines.append(
                f"{finding_num}. **{col}** has a mean of **{_num(mean)}** "
                f"(std: {_num(std)}, CV: {cv:.1f}% — {volatility} variability)"
            )
            finding_num += 1
    if corrs:
        top = corrs[0]
        lines.append(
            f"{finding_num}. Strongest correlation: **{top.get('col_a')}** and "
            f"**{top.get('col_b')}** (r = {_num(top.get('correlation', 0))})"
        )
    lines.append("")

    # ── Trends & Patterns ────────────────────────────────────
    lines.append("## Trends & Patterns")
    if trends:
        for col_name, trend_data in list(trends.items())[:6]:
            if isinstance(trend_data, dict):
                direction = trend_data.get("direction", "unknown")
                strength = trend_data.get("strength", "")
                lines.append(f"- **{col_name}**: {direction} trend ({strength})")
            else:
                lines.append(f"- **{col_name}**: {trend_data}")
    else:
        lines.append("- No significant time-based trends detected.")
    lines.append("")

    # ── Anomalies & Concerns ─────────────────────────────────
    lines.append("## Anomalies & Concerns")
    if anomaly_total > 0:
        per_col = anomalies.get("per_column", {})
        for col, data in list(per_col.items())[:6]:
            z = data.get("z_score", {}).get("count", 0)
            iqr = data.get("iqr", {}).get("count", 0)
            if z + iqr > 0:
                lines.append(f"- **{col}**: {z} Z-score outliers, {iqr} IQR outliers")
    else:
        lines.append("- No significant anomalies detected.")
    lines.append("")

    # ── Correlations ─────────────────────────────────────────
    if corrs:
        lines.append("## Correlations & Relationships")
        for c in corrs[:5]:
            direction = c.get("direction", "positive")
            strength = c.get("strength", "strong")
            lines.append(
                f"- **{c.get('col_a')}** and **{c.get('col_b')}**: "
                f"r = {_num(c.get('correlation', 0))} ({strength}, {direction})"
            )
        lines.append("")

    # ── Recommendations ──────────────────────────────────────
    lines.append("## Actionable Recommendations")
    rec_num = 1
    if anomaly_total > 0:
        lines.append(f"{rec_num}. Investigate the {anomaly_total} detected anomalies for data quality or business events.")
        rec_num += 1
    if corrs:
        top = corrs[0]
        lines.append(f"{rec_num}. Leverage the strong relationship between {top.get('col_a')} and {top.get('col_b')} for predictive modeling.")
        rec_num += 1
    # High-variability columns
    for col, m in list(stats.items())[:3]:
        mean = m.get("mean", 0)
        std = m.get("std", 0)
        if mean and abs(std / mean * 100) > 40:
            lines.append(f"{rec_num}. Analyze what drives the high variability in **{col}** (CV > 40%).")
            rec_num += 1
            break
    if rec_num <= 3:
        lines.append(f"{rec_num}. Collect more data over time to strengthen trend analysis.")
    lines.append("")

    markdown = "\n".join(lines)
    sections = _parse_sections(markdown)

    return {
        "insights": markdown,
        "sections": sections,
        "error": None,
        "source": "local_fallback",
    }


def _num(v) -> str:
    """Format a number for display."""
    if v is None:
        return "N/A"
    if isinstance(v, float):
        if abs(v) >= 1000:
            return f"{v:,.0f}"
        return f"{v:.4f}"
    return str(v)

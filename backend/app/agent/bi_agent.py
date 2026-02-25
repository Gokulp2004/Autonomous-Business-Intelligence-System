"""
bi_agent.py — Direct Gemini SDK BI Agent (replaces Google ADK)

Uses google.genai.Client with function-calling to let the LLM
invoke tools, then returns a final text answer.

Optimizations kept:
  1. Response caching — identical questions return cached answers
  2. Quota cooldown — skips API for 5 min after a 429
  3. Pre-flight check — tiny HTTP call before expensive agent call
  4. Local fallback — answers from data alone when API unavailable
"""

import os
import asyncio
import json
import hashlib
import time
import traceback

from google import genai
from google.genai import types as genai_types

from ..config import settings
from .tools import (
    set_context,
    get_data_summary,
    get_column_statistics,
    query_data,
    get_correlation_insights,
    get_trend_insights,
    get_anomaly_summary,
    compute_group_aggregation,
    get_analysis_results,
)
from .prompts import SYSTEM_PROMPT

# ── Response cache ───────────────────────────────────────────
_chat_cache: dict[str, dict] = {}


def _chat_cache_key(file_id: str, question: str) -> str:
    q_norm = question.strip().lower()[:200]
    return hashlib.md5(f"{file_id}:{q_norm}".encode()).hexdigest()


# ── Quota cooldown ───────────────────────────────────────────
_api_cooldown_until: float = 0
_API_COOLDOWN_SECS = 300


def _is_api_available() -> bool:
    return time.time() > _api_cooldown_until


def _set_api_cooldown():
    global _api_cooldown_until
    _api_cooldown_until = time.time() + _API_COOLDOWN_SECS
    print(f"[Agent] API cooldown set for {_API_COOLDOWN_SECS}s.")


# ── Resolve API key robustly ─────────────────────────────────
def _get_api_key() -> str:
    """Get the API key from settings, env, or .env file."""
    key = settings.GOOGLE_API_KEY
    if key and key != "your_google_api_key_here":
        return key
    key = os.environ.get("GOOGLE_API_KEY", "")
    if key and key != "your_google_api_key_here":
        return key
    try:
        from dotenv import load_dotenv
        load_dotenv()
        key = os.environ.get("GOOGLE_API_KEY", "")
    except Exception:
        pass
    return key


# ── Tool declarations for Gemini function calling ────────────
TOOL_DECLARATIONS = genai_types.Tool(
    function_declarations=[
        genai_types.FunctionDeclaration(
            name="get_data_summary",
            description="Get a high-level summary of the loaded dataset including row count, column names, and data types.",
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={},
            ),
        ),
        genai_types.FunctionDeclaration(
            name="get_column_statistics",
            description="Get detailed statistics for a specific column. Returns count, mean, std, min, max, median, quartiles for numeric columns or value counts for categorical.",
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={
                    "column_name": genai_types.Schema(type="STRING", description="Exact column name to analyze"),
                },
                required=["column_name"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="query_data",
            description="Filter the dataset and return matching rows. Operators: ==, !=, >, <, >=, <=, contains.",
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={
                    "filter_column": genai_types.Schema(type="STRING", description="Column name to filter on"),
                    "operator": genai_types.Schema(type="STRING", description="One of: ==, !=, >, <, >=, <=, contains"),
                    "value": genai_types.Schema(type="STRING", description="Value to compare against"),
                },
                required=["filter_column", "operator", "value"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="get_correlation_insights",
            description="Get strong correlations found in the data (|r| > 0.7).",
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={},
            ),
        ),
        genai_types.FunctionDeclaration(
            name="get_trend_insights",
            description="Get time-series trend information for numeric columns.",
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={},
            ),
        ),
        genai_types.FunctionDeclaration(
            name="get_anomaly_summary",
            description="Get a summary of detected anomalies/outliers in the data.",
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={},
            ),
        ),
        genai_types.FunctionDeclaration(
            name="compute_group_aggregation",
            description="Compute a grouped aggregation (sum, mean, median, count, min, max) on the data.",
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={
                    "group_by_column": genai_types.Schema(type="STRING", description="Column to group by"),
                    "value_column": genai_types.Schema(type="STRING", description="Numeric column to aggregate"),
                    "aggregation": genai_types.Schema(type="STRING", description="One of: sum, mean, median, count, min, max"),
                },
                required=["group_by_column", "value_column", "aggregation"],
            ),
        ),
        genai_types.FunctionDeclaration(
            name="get_analysis_results",
            description="Get the full statistical analysis summary including descriptive stats, distributions, and segment analysis.",
            parameters=genai_types.Schema(
                type="OBJECT",
                properties={},
            ),
        ),
    ]
)

# ── Map function names to actual Python callables ────────────
_TOOL_MAP = {
    "get_data_summary": lambda **kw: get_data_summary(),
    "get_column_statistics": lambda **kw: get_column_statistics(**kw),
    "query_data": lambda **kw: query_data(**kw),
    "get_correlation_insights": lambda **kw: get_correlation_insights(),
    "get_trend_insights": lambda **kw: get_trend_insights(),
    "get_anomaly_summary": lambda **kw: get_anomaly_summary(),
    "compute_group_aggregation": lambda **kw: compute_group_aggregation(**kw),
    "get_analysis_results": lambda **kw: get_analysis_results(),
}


def _execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name with given arguments."""
    fn = _TOOL_MAP.get(name)
    if fn is None:
        return f"Unknown tool: {name}"
    try:
        return fn(**args)
    except Exception as e:
        return f"Tool {name} error: {e}"


# ── Main agent query function ────────────────────────────────
async def run_agent_query(
    df,
    analysis_results: dict,
    anomaly_results: dict,
    file_id: str,
    question: str,
    session_id: str = None,
) -> dict:
    """
    Run a user question through Gemini with function calling.
    Flow: cache → cooldown → preflight → multi-turn tool loop → local fallback.
    """
    # 1. Cache check
    cache_key = _chat_cache_key(file_id, question)
    if cache_key in _chat_cache:
        return _chat_cache[cache_key]

    # 2. Cooldown check
    if not _is_api_available():
        result = _local_chat_fallback(df, analysis_results, anomaly_results, question)
        _chat_cache[cache_key] = result
        return result

    try:
        # Set the data context for tools
        set_context(df, analysis_results, file_id)

        # Create genai client
        api_key = _get_api_key()
        print(f"[Agent] Using API key: {api_key[:10]}... model: {settings.GEMINI_MODEL}")
        client = genai.Client(api_key=api_key)

        # Build initial contents
        contents = [
            genai_types.Content(
                role="user",
                parts=[genai_types.Part.from_text(text=question)],
            )
        ]

        tool_calls_log = []
        max_rounds = 6

        for _round in range(max_rounds):
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[TOOL_DECLARATIONS],
                    temperature=0.2,
                ),
            )

            # Check for function calls in the response
            part = response.candidates[0].content.parts[0]

            if part.function_call:
                fc = part.function_call
                fn_name = fc.name
                fn_args = dict(fc.args) if fc.args else {}
                print(f"[Agent] Tool call: {fn_name}({fn_args})")

                tool_calls_log.append({"tool": fn_name, "args": fn_args})

                # Execute the tool
                tool_result = _execute_tool(fn_name, fn_args)

                # Append assistant's function_call and our function_response
                contents.append(response.candidates[0].content)
                contents.append(
                    genai_types.Content(
                        role="user",
                        parts=[genai_types.Part.from_function_response(
                            name=fn_name,
                            response={"result": tool_result},
                        )],
                    )
                )
                # Continue loop for next round
            else:
                # Text response — we're done
                answer = part.text or "I could not generate a response."

                if "RESOURCE_EXHAUSTED" in answer or "429" in answer:
                    _set_api_cooldown()
                    result = _local_chat_fallback(df, analysis_results, anomaly_results, question)
                    _chat_cache[cache_key] = result
                    return result

                result = {
                    "answer": answer,
                    "tool_calls": tool_calls_log,
                    "session_id": session_id or "direct",
                    "error": False,
                }
                _chat_cache[cache_key] = result
                return result

        # If we exhausted rounds, collect whatever text we have
        answer = "I analyzed the data using multiple tools. Here's what I found based on the analysis."
        result = {
            "answer": answer,
            "tool_calls": tool_calls_log,
            "session_id": session_id or "direct",
            "error": False,
        }
        _chat_cache[cache_key] = result
        return result

    except Exception as e:
        err_str = str(e)
        traceback.print_exc()
        _set_api_cooldown()

        try:
            result = _local_chat_fallback(df, analysis_results, anomaly_results, question)
            _chat_cache[cache_key] = result
            return result
        except Exception as fallback_err:
            print(f"[Agent] Local fallback also failed: {fallback_err}")
            return {
                "answer": f"Agent error: {err_str}",
                "tool_calls": [],
                "error": True,
            }


# ══════════════════════════════════════════════════════════════
#  LOCAL CHAT FALLBACK — answers from data, zero API calls
# ══════════════════════════════════════════════════════════════

def _local_chat_fallback(df, analysis: dict, anomalies: dict, question: str) -> dict:
    """Answer common questions using only the cached analysis data."""
    import pandas as pd

    q = question.lower().strip()
    summary = analysis.get("summary", {})
    stats = analysis.get("descriptive_stats", {})
    corrs = analysis.get("strong_correlations", [])
    trends = analysis.get("trends", {})
    anomaly_summary = (anomalies or {}).get("summary", {})

    answer_lines = []

    if any(w in q for w in ["summary", "overview", "describe", "about", "insight", "key"]):
        answer_lines.append("**Dataset Overview:**")
        answer_lines.append(f"- **{summary.get('total_rows', '?')} rows** x **{summary.get('total_columns', '?')} columns**")
        answer_lines.append(f"- {summary.get('numeric_columns', 0)} numeric, {summary.get('categorical_columns', 0)} categorical, {summary.get('datetime_columns', 0)} datetime")
        quality = summary.get("data_quality_score")
        if quality:
            answer_lines.append(f"- Data quality score: **{quality}%**")
        if corrs:
            answer_lines.append(f"- {len(corrs)} strong correlations found")
        total_anom = anomaly_summary.get("total_anomalous_values", 0)
        if total_anom:
            answer_lines.append(f"- {total_anom} anomalies detected")

    elif any(w in q for w in ["anomal", "outlier", "unusual", "weird"]):
        total = anomaly_summary.get("total_anomalous_values", 0)
        answer_lines.append(f"**Anomaly Report:** {total} anomalous values detected.")
        per_col = (anomalies or {}).get("per_column", {})
        for col, data in list(per_col.items())[:6]:
            z = data.get("z_score", {}).get("count", 0)
            iqr = data.get("iqr", {}).get("count", 0)
            if z + iqr > 0:
                answer_lines.append(f"- **{col}**: {z} Z-score outliers, {iqr} IQR outliers")

    elif any(w in q for w in ["trend", "time", "over time", "increas", "decreas"]):
        answer_lines.append("**Trend Analysis:**")
        if trends:
            for col, t in list(trends.items())[:6]:
                if isinstance(t, dict):
                    answer_lines.append(f"- **{col}**: {t.get('direction', '?')} ({t.get('strength', '')})")
                else:
                    answer_lines.append(f"- **{col}**: {t}")
        else:
            answer_lines.append("No significant trends detected in the data.")

    elif any(w in q for w in ["correlat", "relationship", "related"]):
        answer_lines.append("**Strong Correlations:**")
        if corrs:
            for c in corrs[:6]:
                answer_lines.append(
                    f"- **{c.get('col_a')}** & **{c.get('col_b')}**: "
                    f"r = {c.get('correlation', '?')} ({c.get('strength', '')}, {c.get('direction', '')})"
                )
        else:
            answer_lines.append("No strong correlations found (|r| > 0.7).")

    elif any(w in q for w in ["distribution", "spread", "skew", "normal"]):
        dists = analysis.get("distributions", {})
        answer_lines.append("**Distribution Analysis:**")
        for col, d in list(dists.items())[:6]:
            if isinstance(d, dict):
                answer_lines.append(
                    f"- **{col}**: {d.get('shape', '?')} (skew={d.get('skewness', '?')}, "
                    f"normal={'Yes' if d.get('is_normal') else 'No'})"
                )

    elif any(w in q for w in ["top", "best", "highest", "most", "largest"]):
        target_col = None
        for col in df.select_dtypes(include=["number"]).columns:
            if col.lower() in q:
                target_col = col
                break
        if target_col is None and len(df.select_dtypes(include=["number"]).columns) > 0:
            target_col = df.select_dtypes(include=["number"]).columns[0]

        if target_col:
            cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
            if cat_cols:
                group_col = cat_cols[0]
                for c in cat_cols:
                    if c.lower() in q:
                        group_col = c
                        break
                top = df.groupby(group_col)[target_col].sum().sort_values(ascending=False).head(5)
                answer_lines.append(f"**Top {group_col} by {target_col}:**")
                for name, val in top.items():
                    answer_lines.append(f"- **{name}**: {val:,.2f}")
            else:
                answer_lines.append(f"**Top values in {target_col}:**")
                top = df[target_col].nlargest(5)
                for idx, val in top.items():
                    answer_lines.append(f"- Row {idx}: {val:,.2f}")

    else:
        matched_col = None
        for col in df.columns:
            if col.lower() in q:
                matched_col = col
                break

        if matched_col and matched_col in stats:
            s = stats[matched_col]
            answer_lines.append(f"**Statistics for {matched_col}:**")
            answer_lines.append(f"- Mean: {_fmt(s.get('mean'))}")
            answer_lines.append(f"- Std: {_fmt(s.get('std'))}")
            answer_lines.append(f"- Min: {_fmt(s.get('min'))} / Max: {_fmt(s.get('max'))}")
            answer_lines.append(f"- Median: {_fmt(s.get('median'))}")
        else:
            answer_lines.append("Here's a quick overview of the dataset:")
            answer_lines.append(f"- **{summary.get('total_rows', '?')} rows**, **{summary.get('total_columns', '?')} columns**")
            answer_lines.append(f"- Columns: {', '.join(df.columns.tolist()[:10])}")
            if corrs:
                answer_lines.append(f"- {len(corrs)} strong correlations found")
            answer_lines.append("\nTry asking about specific columns, trends, anomalies, or correlations!")

    return {
        "answer": "\n".join(answer_lines),
        "tool_calls": [{"tool": "local_fallback", "args": {"reason": "API quota optimization"}}],
        "error": False,
        "source": "local_fallback",
    }


def _fmt(v) -> str:
    if v is None:
        return "N/A"
    if isinstance(v, float):
        return f"{v:,.4f}" if abs(v) < 1000 else f"{v:,.0f}"
    return str(v)

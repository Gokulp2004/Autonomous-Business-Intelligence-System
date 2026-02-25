"""
chart_generator.py - Automated Chart Generation Engine

Programmatically generates Plotly chart configurations from analysis results.
The frontend renders these using react-plotly.js.

Chart types produced:
  - Distribution histograms (numeric columns)
  - Box plots (numeric columns)
  - Correlation heatmap
  - Scatter matrix for top correlated pairs
  - Trend line charts (if time-series)
  - Categorical bar charts
  - Feature importance horizontal bar
  - Anomaly scatter overlay
  - Pie chart for top categorical column

Each function returns a Plotly JSON dict: { data: [...], layout: {...} }
"""

import math
import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────

_PALETTE = [
    "#6366f1", "#8b5cf6", "#06b6d4", "#10b981", "#f59e0b",
    "#ef4444", "#ec4899", "#14b8a6", "#f97316", "#3b82f6",
]


def _safe(v):
    """Convert numpy/pandas types to plain Python for JSON serialization."""
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else round(f, 6)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, (np.ndarray,)):
        return [_safe(x) for x in v.tolist()]
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else round(v, 6)
    return v


def _safe_list(series):
    """Convert a pandas Series to a JSON-safe list."""
    return [_safe(x) for x in series.tolist()]


# ──────────────────────────────────────────────────────────────────
# Individual Chart Builders
# ──────────────────────────────────────────────────────────────────

def build_histogram(df: pd.DataFrame, col: str, color: str = "#6366f1") -> dict:
    """Histogram for a single numeric column."""
    vals = df[col].dropna()
    return {
        "id": f"hist_{col}",
        "type": "histogram",
        "title": f"Distribution of {col}",
        "data": [
            {
                "type": "histogram",
                "x": _safe_list(vals),
                "marker": {"color": color, "opacity": 0.75},
                "nbinsx": min(30, max(10, len(vals) // 5)),
                "name": col,
            }
        ],
        "layout": {
            "title": {"text": f"Distribution of {col}", "font": {"size": 14}},
            "xaxis": {"title": col},
            "yaxis": {"title": "Count"},
            "bargap": 0.05,
            "margin": {"t": 40, "b": 40, "l": 50, "r": 20},
            "height": 340,
        },
    }


def build_box_plots(df: pd.DataFrame, numeric_cols: list) -> dict:
    """Combined box plot for all numeric columns."""
    traces = []
    for i, col in enumerate(numeric_cols[:8]):
        vals = df[col].dropna()
        traces.append({
            "type": "box",
            "y": _safe_list(vals),
            "name": col,
            "marker": {"color": _PALETTE[i % len(_PALETTE)]},
            "boxmean": True,
        })
    return {
        "id": "box_all",
        "type": "box",
        "title": "Box Plots — Numeric Columns",
        "data": traces,
        "layout": {
            "title": {"text": "Box Plots — Numeric Columns", "font": {"size": 14}},
            "yaxis": {"title": "Value"},
            "margin": {"t": 40, "b": 60, "l": 50, "r": 20},
            "height": 380,
            "showlegend": True,
        },
    }


def build_correlation_heatmap(analysis: dict) -> dict | None:
    """Heatmap from the correlation matrix in analysis results."""
    corr = analysis.get("correlation_matrix")
    if not corr:
        return None
    cols = list(corr.keys())
    z = []
    for r in cols:
        row = []
        for c in cols:
            val = corr.get(r, {}).get(c, 0)
            row.append(_safe(val))
        z.append(row)

    return {
        "id": "corr_heatmap",
        "type": "heatmap",
        "title": "Correlation Matrix",
        "data": [
            {
                "type": "heatmap",
                "z": z,
                "x": cols,
                "y": cols,
                "colorscale": "RdBu",
                "zmin": -1,
                "zmax": 1,
                "reversescale": True,
                "text": [[f"{v:.2f}" if v is not None else "" for v in row] for row in z],
                "texttemplate": "%{text}",
                "hovertemplate": "%{y} vs %{x}: %{z:.3f}<extra></extra>",
            }
        ],
        "layout": {
            "title": {"text": "Correlation Matrix", "font": {"size": 14}},
            "margin": {"t": 40, "b": 80, "l": 80, "r": 20},
            "height": 420,
            "xaxis": {"tickangle": -45},
        },
    }


def build_scatter_pairs(df: pd.DataFrame, analysis: dict) -> list:
    """Scatter plots for the top correlated column pairs."""
    pairs = analysis.get("strong_correlations", [])
    charts = []
    for i, pair in enumerate(pairs[:4]):
        a, b = pair["col_a"], pair["col_b"]
        if a not in df.columns or b not in df.columns:
            continue
        sub = df[[a, b]].dropna()
        charts.append({
            "id": f"scatter_{a}_{b}",
            "type": "scatter",
            "title": f"{a} vs {b} (r={pair['correlation']})",
            "data": [
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": _safe_list(sub[a]),
                    "y": _safe_list(sub[b]),
                    "marker": {
                        "color": _PALETTE[i % len(_PALETTE)],
                        "size": 6,
                        "opacity": 0.6,
                    },
                    "name": f"{a} vs {b}",
                }
            ],
            "layout": {
                "title": {"text": f"{a} vs {b} (r={pair['correlation']})", "font": {"size": 14}},
                "xaxis": {"title": a},
                "yaxis": {"title": b},
                "margin": {"t": 40, "b": 40, "l": 50, "r": 20},
                "height": 340,
            },
        })
    return charts


def build_trend_chart(df: pd.DataFrame, datetime_col: str, numeric_cols: list) -> dict | None:
    """Line chart showing trends over time."""
    if datetime_col not in df.columns:
        return None
    sorted_df = df.sort_values(datetime_col)
    x_vals = _safe_list(sorted_df[datetime_col])

    traces = []
    for i, col in enumerate(numeric_cols[:6]):
        if col not in sorted_df.columns:
            continue
        traces.append({
            "type": "scatter",
            "mode": "lines+markers",
            "x": x_vals,
            "y": _safe_list(sorted_df[col]),
            "name": col,
            "marker": {"size": 4},
            "line": {"color": _PALETTE[i % len(_PALETTE)], "width": 2},
        })

    if not traces:
        return None

    return {
        "id": "trend_lines",
        "type": "line",
        "title": "Trends Over Time",
        "data": traces,
        "layout": {
            "title": {"text": "Trends Over Time", "font": {"size": 14}},
            "xaxis": {"title": datetime_col},
            "yaxis": {"title": "Value"},
            "margin": {"t": 40, "b": 50, "l": 50, "r": 20},
            "height": 380,
            "hovermode": "x unified",
            "showlegend": True,
        },
    }


def build_categorical_bars(df: pd.DataFrame, cat_cols: list) -> list:
    """Bar charts for top values in categorical columns."""
    charts = []
    for i, col in enumerate(cat_cols[:4]):
        vc = df[col].value_counts().head(10)
        charts.append({
            "id": f"cat_bar_{col}",
            "type": "bar",
            "title": f"Top Values — {col}",
            "data": [
                {
                    "type": "bar",
                    "x": [str(x) for x in vc.index.tolist()],
                    "y": [int(v) for v in vc.values.tolist()],
                    "marker": {"color": _PALETTE[i % len(_PALETTE)], "opacity": 0.85},
                    "name": col,
                }
            ],
            "layout": {
                "title": {"text": f"Top Values — {col}", "font": {"size": 14}},
                "xaxis": {"title": col, "tickangle": -30},
                "yaxis": {"title": "Count"},
                "margin": {"t": 40, "b": 60, "l": 50, "r": 20},
                "height": 340,
            },
        })
    return charts


def build_pie_chart(df: pd.DataFrame, col: str) -> dict:
    """Pie chart for a categorical column."""
    vc = df[col].value_counts().head(8)
    return {
        "id": f"pie_{col}",
        "type": "pie",
        "title": f"Composition — {col}",
        "data": [
            {
                "type": "pie",
                "labels": [str(x) for x in vc.index.tolist()],
                "values": [int(v) for v in vc.values.tolist()],
                "hole": 0.4,
                "marker": {"colors": _PALETTE[: len(vc)]},
                "textinfo": "percent+label",
            }
        ],
        "layout": {
            "title": {"text": f"Composition — {col}", "font": {"size": 14}},
            "margin": {"t": 40, "b": 20, "l": 20, "r": 20},
            "height": 360,
            "showlegend": True,
        },
    }


def build_feature_importance_bar(analysis: dict) -> dict | None:
    """Horizontal bar for feature importance scores."""
    fi = analysis.get("feature_importance", [])
    if not fi:
        return None
    features = [f["feature"] for f in fi]
    scores = [_safe(f["importance"]) for f in fi]
    return {
        "id": "feature_importance",
        "type": "bar",
        "title": "Feature Importance",
        "data": [
            {
                "type": "bar",
                "y": features,
                "x": scores,
                "orientation": "h",
                "marker": {
                    "color": _PALETTE[:len(features)],
                    "opacity": 0.85,
                },
            }
        ],
        "layout": {
            "title": {"text": "Feature Importance (Mutual Information)", "font": {"size": 14}},
            "xaxis": {"title": "Importance Score"},
            "margin": {"t": 40, "b": 40, "l": 120, "r": 20},
            "height": max(200, len(features) * 40 + 80),
        },
    }


def build_anomaly_overlay(df: pd.DataFrame, anomalies: dict) -> list:
    """Scatter charts with anomaly points highlighted."""
    per_col = anomalies.get("per_column", {})
    charts = []
    for i, (col, info) in enumerate(list(per_col.items())[:4]):
        if col not in df.columns:
            continue
        vals = df[col].dropna()
        x_all = list(range(len(vals)))
        y_all = _safe_list(vals)

        # Collect anomaly indices
        anom_indices = set()
        for method in ["zscore", "iqr"]:
            method_data = info.get(method, {})
            # method_data can be a dict with an 'anomalies' list, or a list directly
            if isinstance(method_data, dict):
                anomaly_list = method_data.get("anomalies", [])
            elif isinstance(method_data, list):
                anomaly_list = method_data
            else:
                anomaly_list = []
            for a in anomaly_list:
                idx = a.get("index") if isinstance(a, dict) else None
                if idx is not None:
                    anom_indices.add(idx)

        x_normal = [x for x in x_all if x not in anom_indices]
        y_normal = [y_all[x] for x in x_normal]
        x_anom = [x for x in x_all if x in anom_indices]
        y_anom = [y_all[x] for x in x_anom]

        charts.append({
            "id": f"anomaly_{col}",
            "type": "scatter",
            "title": f"Anomalies — {col}",
            "data": [
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": x_normal,
                    "y": y_normal,
                    "marker": {"color": _PALETTE[i % len(_PALETTE)], "size": 5, "opacity": 0.5},
                    "name": "Normal",
                },
                {
                    "type": "scatter",
                    "mode": "markers",
                    "x": x_anom,
                    "y": y_anom,
                    "marker": {"color": "#ef4444", "size": 9, "symbol": "x", "opacity": 0.9},
                    "name": "Anomaly",
                },
            ],
            "layout": {
                "title": {"text": f"Anomalies — {col}", "font": {"size": 14}},
                "xaxis": {"title": "Row Index"},
                "yaxis": {"title": col},
                "margin": {"t": 40, "b": 40, "l": 50, "r": 20},
                "height": 340,
                "showlegend": True,
            },
        })
    return charts


# ──────────────────────────────────────────────────────────────────
# Master Orchestrator
# ──────────────────────────────────────────────────────────────────

def generate_all_charts(
    df: pd.DataFrame,
    analysis: dict,
    anomalies: dict | None = None,
) -> list[dict]:
    """
    Generate a comprehensive set of charts from the analysis results.

    Returns a list of Plotly chart configs, each with:
      id, type, title, data, layout
    """
    charts = []
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    # 1. Histograms for numeric columns (max 6)
    for i, col in enumerate(numeric_cols[:6]):
        charts.append(build_histogram(df, col, _PALETTE[i % len(_PALETTE)]))

    # 2. Box plots
    if numeric_cols:
        charts.append(build_box_plots(df, numeric_cols))

    # 3. Correlation heatmap
    heatmap = build_correlation_heatmap(analysis)
    if heatmap:
        charts.append(heatmap)

    # 4. Scatter plots for correlated pairs
    charts.extend(build_scatter_pairs(df, analysis))

    # 5. Trend line chart
    if datetime_cols:
        trend = build_trend_chart(df, datetime_cols[0], numeric_cols)
        if trend:
            charts.append(trend)

    # 6. Categorical bar charts
    charts.extend(build_categorical_bars(df, cat_cols))

    # 7. Pie chart for first categorical column
    if cat_cols:
        charts.append(build_pie_chart(df, cat_cols[0]))

    # 8. Feature importance
    fi = build_feature_importance_bar(analysis)
    if fi:
        charts.append(fi)

    # 9. Anomaly overlays
    if anomalies:
        charts.extend(build_anomaly_overlay(df, anomalies))

    return charts


def generate_dashboard_summary(
    df: pd.DataFrame,
    analysis: dict,
    anomalies: dict | None = None,
    forecasts: list | None = None,
) -> dict:
    """
    Generate KPI summary cards for the dashboard header.

    Returns dict with:
      - total_rows, total_columns, numeric_columns, categorical_columns
      - data_quality_score
      - anomaly_count
      - correlation_count
      - trend_direction (overall)
      - top_insight
    """
    summary = analysis.get("summary", {})
    total_rows = summary.get("total_rows", len(df))
    total_cols = summary.get("total_columns", len(df.columns))

    # Data quality = % non-missing cells
    total_cells = total_rows * total_cols
    missing_cells = int(df.isnull().sum().sum()) if total_cells > 0 else 0
    quality = round((1 - missing_cells / total_cells) * 100, 1) if total_cells > 0 else 100.0

    # Anomaly count
    anom_count = 0
    if anomalies:
        anom_summary = anomalies.get("summary", {})
        anom_count = anom_summary.get("total_anomalies", 0)

    # Correlations
    strong = analysis.get("strong_correlations", [])

    # Trends
    trends = analysis.get("trends", {})
    increasing = sum(1 for t in trends.values() if t.get("direction") == "increasing")
    decreasing = sum(1 for t in trends.values() if t.get("direction") == "decreasing")

    return {
        "total_rows": total_rows,
        "total_columns": total_cols,
        "numeric_columns": summary.get("numeric_columns", 0),
        "categorical_columns": summary.get("categorical_columns", 0),
        "datetime_columns": summary.get("datetime_columns", 0),
        "data_quality_score": quality,
        "missing_cells": missing_cells,
        "anomaly_count": anom_count,
        "correlation_count": len(strong),
        "trends_increasing": increasing,
        "trends_decreasing": decreasing,
        "has_forecasts": bool(forecasts),
        "forecast_count": len(forecasts) if forecasts else 0,
    }

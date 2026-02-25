"""
tools.py - Agent Tools (Functions the AI Agent Can Call)

In Google ADK, "tools" are Python functions that the agent can invoke.
The agent reads the function name, docstring, and parameter types to
understand what each tool does, then decides which one to call.

These tools give the agent access to the data without exposing raw DataFrames.
"""

import pandas as pd
import numpy as np
import os
import json


# Module-level data store (set by the agent before a session)
_current_df: pd.DataFrame | None = None
_current_analysis: dict | None = None
_current_file_id: str | None = None


def set_context(df: pd.DataFrame, analysis: dict, file_id: str):
    """Set the data context for tools to use during a session."""
    global _current_df, _current_analysis, _current_file_id
    _current_df = df
    _current_analysis = analysis
    _current_file_id = file_id


def get_data_summary() -> str:
    """Get a high-level summary of the loaded dataset including row count, column names, and data types.
    Use this first to understand what data is available."""
    if _current_df is None:
        return "No data loaded."

    df = _current_df
    info_lines = [
        f"Dataset: {_current_file_id}",
        f"Rows: {len(df):,}",
        f"Columns: {len(df.columns)}",
        "",
        "Column details:",
    ]
    for col in df.columns:
        dtype = str(df[col].dtype)
        missing = int(df[col].isnull().sum())
        unique = int(df[col].nunique())
        info_lines.append(f"  - {col} ({dtype}): {unique} unique, {missing} missing")

    return "\n".join(info_lines)


def get_column_statistics(column_name: str) -> str:
    """Get detailed statistics for a specific numeric column.
    Returns count, mean, std, min, max, median, quartiles.
    Args:
        column_name: The exact name of the column to analyze.
    """
    if _current_df is None:
        return "No data loaded."

    if column_name not in _current_df.columns:
        return f"Column \'{column_name}\' not found. Available: {list(_current_df.columns)}"

    s = _current_df[column_name]

    if pd.api.types.is_numeric_dtype(s):
        stats = s.describe()
        return (
            f"Statistics for \'{column_name}\':\n"
            f"  Count: {int(stats['count']):,}\n"
            f"  Mean: {stats['mean']:.4f}\n"
            f"  Std: {stats['std']:.4f}\n"
            f"  Min: {stats['min']:.4f}\n"
            f"  25%: {stats['25%']:.4f}\n"
            f"  Median: {stats['50%']:.4f}\n"
            f"  75%: {stats['75%']:.4f}\n"
            f"  Max: {stats['max']:.4f}"
        )
    else:
        vc = s.value_counts().head(10)
        lines = [f"Value counts for \'{column_name}\' (top 10):"]
        for val, cnt in vc.items():
            lines.append(f"  {val}: {cnt} ({cnt/len(s)*100:.1f}%)")
        return "\n".join(lines)


def query_data(filter_column: str, operator: str, value: str) -> str:
    """Filter the dataset and return matching rows count and sample.
    Args:
        filter_column: Column name to filter on.
        operator: One of: ==, !=, >, <, >=, <=, contains
        value: The value to compare against.
    Returns:
        A summary of matching rows.
    """
    if _current_df is None:
        return "No data loaded."

    df = _current_df
    if filter_column not in df.columns:
        return f"Column \'{filter_column}\' not found. Available: {list(df.columns)}"

    col = df[filter_column]
    try:
        if operator == "contains":
            mask = col.astype(str).str.contains(str(value), case=False, na=False)
        elif operator == "==":
            if pd.api.types.is_numeric_dtype(col):
                mask = col == float(value)
            else:
                mask = col.astype(str) == str(value)
        elif operator == "!=":
            if pd.api.types.is_numeric_dtype(col):
                mask = col != float(value)
            else:
                mask = col.astype(str) != str(value)
        elif operator == ">":
            mask = col > float(value)
        elif operator == "<":
            mask = col < float(value)
        elif operator == ">=":
            mask = col >= float(value)
        elif operator == "<=":
            mask = col <= float(value)
        else:
            return f"Unknown operator: {operator}. Use one of: ==, !=, >, <, >=, <=, contains"

        filtered = df[mask]
        result_lines = [
            f"Filter: {filter_column} {operator} {value}",
            f"Matching rows: {len(filtered):,} out of {len(df):,} ({len(filtered)/len(df)*100:.1f}%)",
        ]

        if len(filtered) > 0:
            result_lines.append("\nSample (first 5 rows):")
            sample = filtered.head(5)
            for _, row in sample.iterrows():
                row_str = ", ".join(f"{c}={row[c]}" for c in df.columns[:6])
                result_lines.append(f"  {row_str}")

        return "\n".join(result_lines)

    except Exception as e:
        return f"Filter failed: {str(e)}"


def get_correlation_insights() -> str:
    """Get strong correlations found in the data.
    Returns pairs of columns with correlation > 0.7."""
    if _current_analysis is None:
        return "No analysis available."

    corrs = _current_analysis.get("strong_correlations", [])
    if not corrs:
        return "No strong correlations (|r| > 0.7) found in this dataset."

    lines = ["Strong Correlations Found:"]
    for c in corrs:
        lines.append(
            f"  - {c['col_a']} & {c['col_b']}: r={c['correlation']} "
            f"({c['direction']}, {c['strength']})"
        )
    return "\n".join(lines)


def get_trend_insights() -> str:
    """Get time-series trend information for numeric columns.
    Shows direction, statistical significance, and percentage change."""
    if _current_analysis is None:
        return "No analysis available."

    trends = _current_analysis.get("trends", {})
    if not trends:
        return "No trends detected. This may mean the data has no datetime column."

    lines = ["Trend Analysis:"]
    for col, t in trends.items():
        sig = "statistically significant" if t.get("significant") else "not significant"
        pct = f", {t['pct_change']}% change" if t.get('pct_change') is not None else ""
        lines.append(
            f"  - {col}: {t['direction']} (R\u00b2={t['r_squared']}, {sig}{pct})"
        )
    return "\n".join(lines)


def get_anomaly_summary() -> str:
    """Get a summary of detected anomalies in the data.
    Returns count of anomalies per column and overall statistics."""
    if _current_analysis is None:
        return "No analysis available."

    # Anomalies are stored separately but we access via analysis context
    return "Anomaly data is available in the analysis results. Ask me about specific columns."


def compute_group_aggregation(group_by_column: str, value_column: str, aggregation: str) -> str:
    """Compute a grouped aggregation on the data.
    Args:
        group_by_column: Column to group by.
        value_column: Numeric column to aggregate.
        aggregation: One of: sum, mean, median, count, min, max
    Returns:
        Aggregated results per group.
    """
    if _current_df is None:
        return "No data loaded."

    df = _current_df
    for c in [group_by_column, value_column]:
        if c not in df.columns:
            return f"Column \'{c}\' not found. Available: {list(df.columns)}"

    agg_funcs = {"sum": "sum", "mean": "mean", "median": "median", "count": "count", "min": "min", "max": "max"}
    if aggregation not in agg_funcs:
        return f"Unknown aggregation: {aggregation}. Use: {list(agg_funcs.keys())}"

    try:
        grouped = df.groupby(group_by_column)[value_column].agg(agg_funcs[aggregation])
        grouped = grouped.sort_values(ascending=False)

        lines = [f"{aggregation.upper()} of {value_column} by {group_by_column}:"]
        for idx, val in grouped.head(15).items():
            lines.append(f"  {idx}: {val:,.4f}" if isinstance(val, float) else f"  {idx}: {val:,}")
        return "\n".join(lines)

    except Exception as e:
        return f"Aggregation failed: {str(e)}"


def get_analysis_results() -> str:
    """Get the full statistical analysis summary including descriptive stats,
    distributions, categorical summaries, and segment analysis."""
    if _current_analysis is None:
        return "No analysis available."

    summary = _current_analysis.get("summary", {})
    lines = [
        "Analysis Summary:",
        f"  Rows: {summary.get('total_rows', 0):,}",
        f"  Columns: {summary.get('total_columns', 0)}",
        f"  Numeric: {summary.get('numeric_columns', 0)}",
        f"  Categorical: {summary.get('categorical_columns', 0)}",
        f"  Datetime: {summary.get('datetime_columns', 0)}",
        f"  Normal distributions: {summary.get('normal_distributions', 0)}",
        f"  Has strong correlations: {summary.get('has_strong_correlations', False)}",
        f"  Has trends: {summary.get('has_trends', False)}",
    ]

    # Add descriptive stats summary
    desc = _current_analysis.get("descriptive_stats", {})
    if desc:
        lines.append("\nDescriptive Stats (mean values):")
        for col, stats in desc.items():
            lines.append(f"  {col}: mean={stats.get('mean', 'N/A')}, median={stats.get('median', 'N/A')}")

    return "\n".join(lines)


# Export list of all tools for the agent
ALL_TOOLS = [
    get_data_summary,
    get_column_statistics,
    query_data,
    get_correlation_insights,
    get_trend_insights,
    get_anomaly_summary,
    compute_group_aggregation,
    get_analysis_results,
]

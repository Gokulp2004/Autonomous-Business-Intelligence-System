"""
data_cleaner.py — Automated Data Cleaning Pipeline

Real-world data is messy. This module automatically fixes common problems:
  - Empty rows/columns
  - Duplicate records
  - Inconsistent column names
  - Wrong data types (numbers/dates stored as text)
  - Missing values (NaN)
  - Whitespace issues
  - Outlier detection (for awareness — not removed)

The pipeline returns BOTH the cleaned DataFrame AND a detailed report
explaining every change, so the user knows exactly what happened to their data.

Key principle: Be transparent. Never silently modify data without telling the user.
"""

import pandas as pd
import numpy as np
from typing import Any


# ── Step Functions ───────────────────────────────────────────────
# Each step is a separate function for clarity and testability.
# They all follow the pattern: take a df + report list, return the modified df.


def _step_remove_empty(df: pd.DataFrame, actions: list) -> pd.DataFrame:
    """Step 1: Remove completely empty rows and columns."""
    orig_rows, orig_cols = df.shape

    empty_rows = df.isnull().all(axis=1).sum()
    if empty_rows > 0:
        df = df.dropna(how="all")
        actions.append({
            "step": "Remove empty rows",
            "severity": "info",
            "detail": f"Removed {empty_rows} completely empty row(s).",
            "affected": int(empty_rows),
        })

    empty_cols = [c for c in df.columns if df[c].isnull().all()]
    if empty_cols:
        df = df.drop(columns=empty_cols)
        actions.append({
            "step": "Remove empty columns",
            "severity": "info",
            "detail": f"Removed {len(empty_cols)} empty column(s): {', '.join(empty_cols)}",
            "affected": len(empty_cols),
        })

    return df


def _step_remove_duplicates(df: pd.DataFrame, actions: list) -> pd.DataFrame:
    """Step 2: Remove duplicate rows."""
    dup_count = int(df.duplicated().sum())
    if dup_count > 0:
        df = df.drop_duplicates().reset_index(drop=True)
        actions.append({
            "step": "Remove duplicates",
            "severity": "warning" if dup_count > len(df) * 0.05 else "info",
            "detail": f"Removed {dup_count} duplicate row(s) ({dup_count / (len(df) + dup_count) * 100:.1f}% of data).",
            "affected": dup_count,
        })
    else:
        actions.append({
            "step": "Remove duplicates",
            "severity": "success",
            "detail": "No duplicate rows found.",
            "affected": 0,
        })
    return df


def _step_standardize_columns(df: pd.DataFrame, actions: list) -> pd.DataFrame:
    """Step 3: Standardize column names to snake_case."""
    original_names = df.columns.tolist()
    new_names = []
    renamed = []

    for col in df.columns:
        clean = (
            col.strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace(".", "_")
            .replace("(", "")
            .replace(")", "")
            .replace("/", "_")
        )
        # Remove consecutive underscores
        while "__" in clean:
            clean = clean.replace("__", "_")
        clean = clean.strip("_")
        new_names.append(clean)

    df.columns = new_names

    changed = [(o, n) for o, n in zip(original_names, new_names) if o != n]
    if changed:
        examples = [f"'{o}' → '{n}'" for o, n in changed[:5]]
        actions.append({
            "step": "Standardize column names",
            "severity": "info",
            "detail": f"Renamed {len(changed)} column(s): {'; '.join(examples)}" +
                      (f" (and {len(changed) - 5} more)" if len(changed) > 5 else ""),
            "affected": len(changed),
        })
    else:
        actions.append({
            "step": "Standardize column names",
            "severity": "success",
            "detail": "Column names already clean.",
            "affected": 0,
        })

    # Handle duplicated column names after standardizing
    if df.columns.duplicated().any():
        cols = pd.Series(df.columns)
        for dup in cols[cols.duplicated()].unique():
            idxs = cols[cols == dup].index.tolist()
            for i, idx in enumerate(idxs[1:], start=2):
                cols.iloc[idx] = f"{dup}_{i}"
        df.columns = cols
        actions.append({
            "step": "Fix duplicate column names",
            "severity": "warning",
            "detail": "Some columns had the same name after standardizing. Added suffixes to disambiguate.",
            "affected": int(df.columns.duplicated().sum()),
        })

    return df


def _step_convert_types(df: pd.DataFrame, actions: list) -> pd.DataFrame:
    """Step 4: Auto-detect and convert data types."""
    conversions = []

    for col in df.columns:
        original_dtype = str(df[col].dtype)

        # Skip already-typed columns
        if df[col].dtype != "object":
            continue

        # Try numeric first
        numeric_converted = pd.to_numeric(df[col], errors="coerce")
        non_null_original = df[col].dropna().shape[0]
        non_null_numeric = numeric_converted.dropna().shape[0]

        # If >80% of non-null values convert to numbers, treat as numeric
        if non_null_original > 0 and non_null_numeric / non_null_original > 0.8:
            df[col] = numeric_converted
            conversions.append(f"'{col}': text → numeric")
            continue

        # Try datetime
        try:
            datetime_converted = pd.to_datetime(df[col], format="mixed", errors="coerce", dayfirst=False)
            non_null_datetime = datetime_converted.dropna().shape[0]
            if non_null_original > 0 and non_null_datetime / non_null_original > 0.8:
                df[col] = datetime_converted
                conversions.append(f"'{col}': text → datetime")
                continue
        except Exception:
            pass

    if conversions:
        actions.append({
            "step": "Auto-detect data types",
            "severity": "info",
            "detail": f"Converted {len(conversions)} column(s): {'; '.join(conversions[:5])}" +
                      (f" (and {len(conversions) - 5} more)" if len(conversions) > 5 else ""),
            "affected": len(conversions),
        })
    else:
        actions.append({
            "step": "Auto-detect data types",
            "severity": "success",
            "detail": "All column types look correct.",
            "affected": 0,
        })

    return df


def _step_handle_missing(df: pd.DataFrame, actions: list) -> pd.DataFrame:
    """
    Step 5: Handle missing values.

    Strategy:
      - Columns with >60% missing → drop (unreliable)
      - Numeric columns → fill with median (robust to outliers)
      - Categorical columns → fill with mode (most frequent value)
      - Datetime columns → leave as-is (interpolation is context-dependent)
    """
    missing_cols = []
    dropped_cols = []
    filled_cols = []

    for col in df.columns:
        missing = int(df[col].isnull().sum())
        if missing == 0:
            continue

        total = len(df)
        pct = missing / total * 100

        if pct > 60:
            # Too unreliable — drop it
            df = df.drop(columns=[col])
            dropped_cols.append(f"'{col}' ({pct:.0f}% missing)")
        elif pd.api.types.is_numeric_dtype(df[col]):
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)
            filled_cols.append({
                "column": col,
                "missing": missing,
                "pct": round(pct, 1),
                "strategy": "median",
                "fill_value": _safe_val(median_val),
            })
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            # Don't fill datetimes — just report
            missing_cols.append({
                "column": col,
                "missing": missing,
                "pct": round(pct, 1),
                "strategy": "kept_as_is",
                "fill_value": None,
            })
        else:
            mode_series = df[col].mode()
            mode_val = mode_series.iloc[0] if len(mode_series) > 0 else "Unknown"
            df[col] = df[col].fillna(mode_val)
            filled_cols.append({
                "column": col,
                "missing": missing,
                "pct": round(pct, 1),
                "strategy": "mode",
                "fill_value": str(mode_val),
            })

    if dropped_cols:
        actions.append({
            "step": "Drop high-missing columns",
            "severity": "warning",
            "detail": f"Dropped {len(dropped_cols)} column(s) with >60% missing: {'; '.join(dropped_cols)}",
            "affected": len(dropped_cols),
        })

    if filled_cols:
        examples = [f"'{f['column']}' ({f['missing']} nulls → {f['strategy']}={f['fill_value']})" for f in filled_cols[:5]]
        actions.append({
            "step": "Fill missing values",
            "severity": "info",
            "detail": f"Filled missing values in {len(filled_cols)} column(s): {'; '.join(examples)}" +
                      (f" (and {len(filled_cols) - 5} more)" if len(filled_cols) > 5 else ""),
            "affected": len(filled_cols),
            "details": filled_cols,
        })

    if missing_cols:
        names = [m["column"] for m in missing_cols]
        actions.append({
            "step": "Datetime missing values",
            "severity": "info",
            "detail": f"Left {len(missing_cols)} datetime column(s) with missing values unchanged: {', '.join(names)}",
            "affected": len(missing_cols),
        })

    if not dropped_cols and not filled_cols and not missing_cols:
        actions.append({
            "step": "Handle missing values",
            "severity": "success",
            "detail": "No missing values found — data is complete!",
            "affected": 0,
        })

    return df


def _step_strip_whitespace(df: pd.DataFrame, actions: list) -> pd.DataFrame:
    """Step 6: Strip whitespace and normalize string columns."""
    str_cols = df.select_dtypes(include=["object"]).columns.tolist()
    if str_cols:
        for col in str_cols:
            df[col] = df[col].astype(str).str.strip()
            # Replace 'nan' strings (from astype) back to NaN
            df[col] = df[col].replace("nan", np.nan).replace("None", np.nan)
        actions.append({
            "step": "Clean text values",
            "severity": "info",
            "detail": f"Stripped whitespace from {len(str_cols)} text column(s).",
            "affected": len(str_cols),
        })
    return df


def _step_detect_outliers(df: pd.DataFrame, actions: list) -> pd.DataFrame:
    """
    Step 7: Detect outliers using IQR method.
    We only FLAG them (don't remove), so the user is aware.

    IQR method:
      - Q1 = 25th percentile, Q3 = 75th percentile
      - IQR = Q3 - Q1
      - Outlier = value < Q1 - 1.5*IQR or value > Q3 + 1.5*IQR
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    outlier_summary = []

    for col in numeric_cols:
        series = df[col].dropna()
        if len(series) < 10:
            continue

        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1

        if iqr == 0:
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outliers = ((series < lower) | (series > upper)).sum()

        if outliers > 0:
            outlier_summary.append({
                "column": col,
                "outlier_count": int(outliers),
                "pct": round(outliers / len(series) * 100, 1),
                "lower_bound": round(float(lower), 2),
                "upper_bound": round(float(upper), 2),
            })

    if outlier_summary:
        examples = [f"'{o['column']}' ({o['outlier_count']} outliers, {o['pct']}%)" for o in outlier_summary[:5]]
        actions.append({
            "step": "Detect outliers",
            "severity": "warning",
            "detail": f"Found outliers in {len(outlier_summary)} column(s): {'; '.join(examples)}. "
                      "Outliers are flagged but NOT removed — review them in your analysis.",
            "affected": sum(o["outlier_count"] for o in outlier_summary),
            "details": outlier_summary,
        })
    else:
        actions.append({
            "step": "Detect outliers",
            "severity": "success",
            "detail": "No significant outliers detected.",
            "affected": 0,
        })

    return df


# ── Main Pipeline ────────────────────────────────────────────────


def clean_data(df: pd.DataFrame) -> dict:
    """
    Run the full automated cleaning pipeline.

    Pipeline steps (in order):
      1. Remove empty rows/columns
      2. Remove duplicate rows
      3. Standardize column names
      4. Auto-detect and convert data types
      5. Handle missing values
      6. Strip whitespace from text
      7. Detect outliers

    Args:
        df: Raw DataFrame from file parser.

    Returns:
        dict with:
          - cleaned_df: the cleaned DataFrame
          - actions: list of step-by-step cleaning actions with severity
          - summary: before/after comparison
    """
    actions = []
    before_shape = df.shape
    before_missing = int(df.isnull().sum().sum())
    before_dtypes = df.dtypes.astype(str).to_dict()

    # Run each step in order
    df = _step_remove_empty(df, actions)
    df = _step_remove_duplicates(df, actions)
    df = _step_standardize_columns(df, actions)
    df = _step_convert_types(df, actions)
    df = _step_handle_missing(df, actions)
    df = _step_strip_whitespace(df, actions)
    df = _step_detect_outliers(df, actions)

    after_shape = df.shape
    after_missing = int(df.isnull().sum().sum())
    after_dtypes = df.dtypes.astype(str).to_dict()

    summary = {
        "before": {
            "rows": before_shape[0],
            "columns": before_shape[1],
            "missing_values": before_missing,
            "dtypes": before_dtypes,
        },
        "after": {
            "rows": after_shape[0],
            "columns": after_shape[1],
            "missing_values": after_missing,
            "dtypes": after_dtypes,
        },
        "rows_removed": before_shape[0] - after_shape[0],
        "columns_removed": before_shape[1] - after_shape[1],
        "missing_fixed": before_missing - after_missing,
        "total_actions": len([a for a in actions if a["affected"] > 0]),
    }

    return {
        "cleaned_df": df,
        "actions": actions,
        "summary": summary,
    }


def _safe_val(val) -> Any:
    """Convert numpy values to JSON-safe Python types."""
    if val is None:
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return round(float(val), 4) if not np.isnan(val) else None
    return val

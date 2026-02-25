"""
file_parser.py — Excel/CSV File Parser & Data Profiler

Reads uploaded files into Pandas DataFrames and generates rich metadata
about each column (types, missing values, unique counts, sample values).

Why a separate module?
  - Single Responsibility: one module does one thing well
  - Easy to extend: add support for JSON, Parquet, etc. later
  - Reusable: any part of the app can call parse_file()
"""

import pandas as pd
import numpy as np
import os


def parse_file(file_path: str, sheet_name: int | str = 0) -> pd.DataFrame:
    """
    Parse a CSV or Excel file into a Pandas DataFrame.

    Args:
        file_path: Path to the uploaded file.
        sheet_name: For Excel files, which sheet to read (default: first sheet).

    Returns:
        A Pandas DataFrame with the file's data.

    Raises:
        ValueError: If the file format is not supported.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".csv":
        # Try common CSV encodings and delimiters
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            for sep in [",", ";", "\t", "|"]:
                try:
                    df = pd.read_csv(
                        file_path,
                        encoding=encoding,
                        sep=sep,
                        on_bad_lines="skip",  # skip malformed rows
                    )
                    # If only 1 column was detected, the separator was probably wrong
                    if len(df.columns) > 1 or sep == "|":
                        return df
                except UnicodeDecodeError:
                    continue
                except Exception:
                    continue
        # Fallback: read with default settings
        return pd.read_csv(file_path, on_bad_lines="skip")

    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
        return df

    else:
        raise ValueError(f"Unsupported file format: {ext}")


def get_sheet_names(file_path: str) -> list[str]:
    """
    Get sheet names from an Excel file.
    Returns empty list for CSV files.
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".xlsx", ".xls"):
        xl = pd.ExcelFile(file_path, engine="openpyxl")
        return xl.sheet_names
    return []


def profile_dataframe(df: pd.DataFrame) -> dict:
    """
    Generate a rich profile/summary of a DataFrame.

    This gives the user a quick understanding of their data BEFORE
    running any analysis. Think of it as a "first look" report.

    Returns:
        dict with:
          - row_count: total rows
          - column_count: total columns
          - columns: list of column profiles (one per column)
          - memory_usage_mb: approximate memory footprint
          - duplicate_rows: number of duplicate rows
    """
    profiles = []

    for col in df.columns:
        series = df[col]
        missing = int(series.isnull().sum())
        total = len(series)

        profile = {
            "name": col,
            "dtype": str(series.dtype),
            "missing_count": missing,
            "missing_pct": round(missing / total * 100, 1) if total > 0 else 0,
            "unique_count": int(series.nunique()),
            "sample_values": _get_sample_values(series),
        }

        # Add type-specific stats
        if pd.api.types.is_numeric_dtype(series):
            profile["category"] = "numeric"
            clean = series.dropna()
            if len(clean) > 0:
                profile["min"] = _safe_number(clean.min())
                profile["max"] = _safe_number(clean.max())
                profile["mean"] = _safe_number(clean.mean())
                profile["median"] = _safe_number(clean.median())
                profile["std"] = _safe_number(clean.std())
        elif pd.api.types.is_datetime64_any_dtype(series):
            profile["category"] = "datetime"
            clean = series.dropna()
            if len(clean) > 0:
                profile["min"] = str(clean.min())
                profile["max"] = str(clean.max())
        else:
            profile["category"] = "text"
            clean = series.dropna()
            if len(clean) > 0:
                top = clean.value_counts().head(3)
                profile["top_values"] = {str(k): int(v) for k, v in top.items()}

        profiles.append(profile)

    return {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": profiles,
        "memory_usage_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
        "duplicate_rows": int(df.duplicated().sum()),
    }


def _safe_number(val) -> float | int | None:
    """Convert numpy numbers to Python-native numbers for JSON serialization."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return round(float(val), 4)
    if isinstance(val, (int, float)):
        return round(val, 4) if isinstance(val, float) else val
    return str(val)


def _get_sample_values(series: pd.Series, n: int = 3) -> list:
    """Get n non-null sample values from a series."""
    clean = series.dropna().unique()
    samples = clean[:n].tolist()
    # Convert numpy types to Python-native for JSON
    result = []
    for s in samples:
        if isinstance(s, (np.integer,)):
            result.append(int(s))
        elif isinstance(s, (np.floating,)):
            result.append(round(float(s), 4))
        elif isinstance(s, (np.datetime64, pd.Timestamp)):
            result.append(str(s))
        else:
            result.append(str(s))
    return result


def get_file_path(file_id: str, upload_dir: str = "uploads") -> str:
    """
    Find the file path for a given file_id in the uploads directory.

    We store files as {file_id}.csv or {file_id}.xlsx, so we search
    for any file starting with the file_id.
    """
    for fname in os.listdir(upload_dir):
        if fname.startswith(file_id):
            return os.path.join(upload_dir, fname)
    raise FileNotFoundError(f"No uploaded file found for file_id: {file_id}")

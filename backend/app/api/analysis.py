"""
analysis.py - Analysis Endpoints

Triggers data cleaning, statistical analysis, anomaly detection,
forecasting, and AI insight generation on an uploaded dataset.
"""

import json
import math
import os
import traceback

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException

from ..config import settings
from ..core.file_parser import parse_file, get_file_path
from ..core.data_cleaner import clean_data
from ..core.analyzer import run_analysis as analyze_data
from ..core.forecaster import generate_all_forecasts
from ..core.anomaly import detect_anomalies
from ..agent.insight_generator import generate_insights

router = APIRouter()

# In-memory cache of results keyed by file_id
_results_cache: dict = {}
# Separate cache for cleaned DataFrames (needed by chat agent)
_df_cache: dict = {}


def get_cached_data(file_id: str):
    """Return (cleaned_df, results_dict) from cache, or (None, None)."""
    return _df_cache.get(file_id), _results_cache.get(file_id)


def _make_json_safe(obj):
    """Recursively convert numpy/pandas types to JSON-safe Python types."""
    if obj is None:
        return None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        v = float(obj)
        if math.isnan(v) or math.isinf(v):
            return None
        return round(v, 6)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [_make_json_safe(x) for x in obj.tolist()]
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {str(k): _make_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_make_json_safe(x) for x in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return round(obj, 6)
    return obj


@router.post("/run/{file_id}")
async def run_analysis(file_id: str):
    """
    Run the full analysis pipeline on a previously uploaded file.

    Pipeline: parse -> clean -> analyze -> anomalies -> forecasts -> cache.
    """
    try:
        # 1. Locate and parse the file
        file_path = get_file_path(file_id)
        if not file_path:
            raise HTTPException(status_code=404, detail=f"File '{file_id}' not found.")

        raw_df = parse_file(file_path)

        # 2. Clean the data
        cleaning_result = clean_data(raw_df)
        cleaned_df = cleaning_result["cleaned_df"]
        cleaning_actions = cleaning_result["actions"]
        cleaning_summary = cleaning_result["summary"]

        # 3. Run statistical analysis on cleaned data
        analysis_result = analyze_data(cleaned_df)

        # 4. Run anomaly detection
        anomaly_result = detect_anomalies(cleaned_df)

        # 5. Run forecasting (if time-series data detected)
        forecast_result = None
        datetime_cols = analysis_result.get("datetime_columns", [])
        numeric_cols = cleaned_df.select_dtypes(include=[np.number]).columns.tolist()
        if datetime_cols and numeric_cols:
            forecast_result = generate_all_forecasts(
                cleaned_df, datetime_cols[0], numeric_cols, periods=30
            )

        # 6. Save cleaned data to outputs
        output_dir = settings.OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)
        cleaned_path = os.path.join(output_dir, f"{file_id}_cleaned.csv")
        cleaned_df.to_csv(cleaned_path, index=False)

        # 7. Build preview of cleaned data (first 15 rows)
        preview_records = cleaned_df.head(15).to_dict(orient="records")

        result = {
            "file_id": file_id,
            "status": "completed",
            "cleaning": {
                "actions": cleaning_actions,
                "summary": cleaning_summary,
            },
            "analysis": analysis_result,
            "anomalies": anomaly_result,
            "forecasts": forecast_result,
            "preview": preview_records,
            "cleaned_file": f"{file_id}_cleaned.csv",
        }

        # Make everything JSON-safe
        result = _make_json_safe(result)

        # Cache results AND the cleaned DataFrame for chat/insights
        _results_cache[file_id] = result
        _df_cache[file_id] = cleaned_df

        return result

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/results/{file_id}")
async def get_results(file_id: str):
    """Retrieve cached analysis results for a file."""
    if file_id not in _results_cache:
        raise HTTPException(status_code=404, detail="No results found. Run analysis first.")
    return _results_cache[file_id]


@router.post("/insights/{file_id}")
async def get_insights(file_id: str):
    """
    Generate AI-powered insights for a previously analyzed file.

    Calls Gemini to produce a structured markdown report with:
      - Executive Summary
      - Key Findings
      - Trends & Patterns
      - Anomalies & Concerns
      - Recommendations
    """
    if file_id not in _results_cache:
        raise HTTPException(
            status_code=404,
            detail="No analysis results found. Run /run/{file_id} first.",
        )

    cached = _results_cache[file_id]
    analysis = cached.get("analysis", {})
    anomalies = cached.get("anomalies", {})
    forecasts = cached.get("forecasts", [])

    try:
        result = await generate_insights(
            analysis_results=analysis,
            anomaly_results=anomalies,
            forecast_results=forecasts if isinstance(forecasts, list) else [],
        )
        return _make_json_safe(result)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Insight generation failed: {str(e)}")

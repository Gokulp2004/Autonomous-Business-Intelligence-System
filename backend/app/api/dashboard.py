"""
dashboard.py - Dashboard Data Endpoints

Serves chart configurations and KPI summaries for the frontend dashboard.
Charts are Plotly JSON objects that the frontend renders with react-plotly.js.
"""

import traceback
from fastapi import APIRouter, HTTPException

from .analysis import get_cached_data, _make_json_safe
from ..core.chart_generator import generate_all_charts, generate_dashboard_summary

router = APIRouter()


@router.get("/summary/{file_id}")
async def get_dashboard_summary(file_id: str):
    """
    Get KPI summary cards for the dashboard header.

    Returns: total_rows, total_columns, data_quality_score,
             anomaly_count, correlation_count, trend info.
    """
    df, results = get_cached_data(file_id)
    if df is None or results is None:
        raise HTTPException(
            status_code=404,
            detail="No analysis results found. Run analysis first.",
        )

    try:
        analysis = results.get("analysis", {})
        anomalies = results.get("anomalies", {})
        forecasts = results.get("forecasts")

        summary = generate_dashboard_summary(
            df=df,
            analysis=analysis,
            anomalies=anomalies,
            forecasts=forecasts if isinstance(forecasts, list) else None,
        )
        return _make_json_safe(summary)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Dashboard summary failed: {str(e)}")


@router.get("/charts/{file_id}")
async def get_charts(file_id: str):
    """
    Get all Plotly chart configurations for the frontend to render.

    Each chart has: id, type, title, data (Plotly traces), layout (Plotly layout).
    """
    df, results = get_cached_data(file_id)
    if df is None or results is None:
        raise HTTPException(
            status_code=404,
            detail="No analysis results found. Run analysis first.",
        )

    try:
        analysis = results.get("analysis", {})
        anomalies = results.get("anomalies", {})

        charts = generate_all_charts(
            df=df,
            analysis=analysis,
            anomalies=anomalies,
        )
        return _make_json_safe({"charts": charts, "count": len(charts)})

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chart generation failed: {str(e)}")

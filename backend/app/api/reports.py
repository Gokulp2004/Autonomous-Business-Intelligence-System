"""
reports.py - Report Generation & Download Endpoints

Generates PDF and PowerPoint reports from analysis results.
Uses fpdf2 for PDF and python-pptx for PowerPoint.
"""

import os
import traceback
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..config import settings
from .analysis import get_cached_data
from ..core.report_generator import generate_pdf_report, generate_ppt_report

router = APIRouter()


@router.post("/generate/{file_id}")
async def generate_report(file_id: str, format: str = "pdf"):
    """
    Generate a downloadable report from analysis results.

    Query params:
        - format: "pdf" or "pptx"

    Returns:
        - filename, download_url, format, file_id
    """
    df, results = get_cached_data(file_id)
    if df is None or results is None:
        raise HTTPException(
            status_code=404,
            detail="No analysis results found. Run analysis first.",
        )

    fmt = format.lower().strip()
    if fmt not in ("pdf", "pptx", "ppt"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{format}'. Use 'pdf' or 'pptx'.",
        )

    try:
        if fmt == "pdf":
            filename = generate_pdf_report(file_id, results, df)
        else:
            filename = generate_ppt_report(file_id, results, df)

        return {
            "status": "success",
            "file_id": file_id,
            "format": fmt if fmt != "ppt" else "pptx",
            "filename": filename,
            "download_url": f"/api/reports/download/{filename}",
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@router.get("/download/{filename}")
async def download_report(filename: str):
    """Download a previously generated report file."""
    filepath = os.path.join(settings.OUTPUT_DIR, filename)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"Report file '{filename}' not found.")

    # Determine content type
    if filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".pptx"):
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type,
    )

"""
schemas.py — Pydantic Data Models (Schemas)

Pydantic models define the SHAPE of data flowing through our API.
They validate incoming requests and document outgoing responses.

Think of them as contracts: "this endpoint expects data that looks like THIS,
and will return data that looks like THAT."
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional


# ── Request Models ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""
    file_id: str
    question: str


class ReportRequest(BaseModel):
    """Request body for report generation."""
    file_id: str
    format: str = "pdf"  # "pdf" or "ppt"
    include_charts: bool = True
    include_insights: bool = True


# ── Response Models ─────────────────────────────────────────────

class UploadResponse(BaseModel):
    """Response after a successful file upload."""
    file_id: str
    filename: str
    columns: List[str]
    row_count: int
    dtypes: Dict[str, str]
    preview: List[Dict[str, Any]]


class AnalysisResponse(BaseModel):
    """Response with analysis results."""
    file_id: str
    status: str
    cleaning_report: List[str]
    statistics: Dict[str, Any]
    correlations: Optional[Dict[str, Any]] = None
    trends: Optional[Dict[str, Any]] = None
    anomalies: Optional[Dict[str, Any]] = None
    insights: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    answer: str
    charts: Optional[List[Dict[str, Any]]] = None
    suggested_questions: Optional[List[str]] = None


class DashboardResponse(BaseModel):
    """Response with dashboard data."""
    file_id: str
    kpis: List[Dict[str, Any]]
    charts: List[Dict[str, Any]]
    insights: List[str]

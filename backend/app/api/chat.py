"""
chat.py - Natural Language Chat Endpoints

Allows users to ask questions about their data in plain English.
The Google ADK agent interprets the question and returns answers.
Supports multi-turn conversations with history context.
"""

import traceback
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from ..agent.bi_agent import run_agent_query
from .analysis import get_cached_data

router = APIRouter()


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    file_id: str
    question: str
    session_id: Optional[str] = None
    history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    answer: str
    tool_calls: list = []
    session_id: Optional[str] = None
    error: bool = False
    suggestions: list = []


def _build_suggestions(df, analysis: dict) -> list:
    """Generate contextual question suggestions based on the data."""
    suggestions = [
        "What are the key insights from this dataset?",
        "Are there any anomalies or outliers?",
        "Summarize the main trends.",
    ]

    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if numeric_cols:
        suggestions.append(f"What is the distribution of {numeric_cols[0]}?")
    if len(numeric_cols) >= 2:
        suggestions.append(f"How are {numeric_cols[0]} and {numeric_cols[1]} correlated?")
    if cat_cols and numeric_cols:
        suggestions.append(f"Break down {numeric_cols[0]} by {cat_cols[0]}.")

    return suggestions[:6]


@router.post("/ask", response_model=ChatResponse)
async def ask_question(request: ChatRequest):
    """
    Ask a natural-language question about the uploaded data.

    The ADK agent will:
      1. Understand the question
      2. Decide which tools to call
      3. Synthesize the tool results into a human-readable answer

    Request body:
        - file_id: which dataset to query
        - question: the user's question in plain English
        - session_id: optional, for multi-turn conversation continuity
        - history: optional, previous messages for context
    """
    df, results = get_cached_data(request.file_id)

    if df is None or results is None:
        raise HTTPException(
            status_code=404,
            detail="No analysis results found. Please run analysis first.",
        )

    try:
        analysis = results.get("analysis", {})
        anomalies = results.get("anomalies", {})

        # Build context from conversation history
        history_context = ""
        if request.history and len(request.history) > 0:
            recent = request.history[-6:]  # last 3 exchanges
            history_context = "\n\nConversation context:\n"
            for msg in recent:
                prefix = "User" if msg.role == "user" else "Assistant"
                history_context += f"{prefix}: {msg.content[:300]}\n"

        question = request.question
        if history_context:
            question = f"{question}\n{history_context}"

        result = await run_agent_query(
            df=df,
            analysis_results=analysis,
            anomaly_results=anomalies,
            file_id=request.file_id,
            question=question,
            session_id=request.session_id,
        )

        suggestions = _build_suggestions(df, analysis) if not result.get("error") else []

        return ChatResponse(
            answer=result["answer"],
            tool_calls=result.get("tool_calls", []),
            session_id=result.get("session_id"),
            error=result.get("error", False),
            suggestions=suggestions,
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/suggestions/{file_id}")
async def get_suggestions(file_id: str):
    """Get contextual question suggestions for a dataset."""
    df, results = get_cached_data(file_id)
    if df is None or results is None:
        return {"suggestions": [
            "What are the key insights from this dataset?",
            "Are there any anomalies?",
            "Summarize the main trends.",
        ]}

    analysis = results.get("analysis", {})
    return {"suggestions": _build_suggestions(df, analysis)}

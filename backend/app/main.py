"""
main.py — FastAPI Application Entry Point

This is the "front door" of our backend. When someone sends a request
to our server, FastAPI routes it to the correct handler function.

Think of it like a receptionist who directs visitors to the right department.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api import upload, analysis, chat, reports, dashboard
from app.config import settings

# Create the FastAPI app instance
app = FastAPI(
    title="Autonomous BI System",
    description="AI-powered business intelligence with automatic analysis, insights, and reporting.",
    version="1.0.0",
)

# ── CORS Middleware ──────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Our React frontend (localhost:3000) needs to talk to our backend (localhost:8000)
# Browsers block this by default for security. CORS middleware allows it.
# Merge default + extra CORS origins (from EXTRA_CORS_ORIGINS env var)
_cors_origins = list(settings.CORS_ORIGINS)
if settings.EXTRA_CORS_ORIGINS:
    _cors_origins += [o.strip() for o in settings.EXTRA_CORS_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static File Serving ─────────────────────────────────────────
# Serve generated reports and charts as downloadable files
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

# ── Register API Routers ────────────────────────────────────────
# Each router handles a group of related endpoints
# prefix = the URL path prefix for that group
# tags = grouping in the auto-generated API docs (Swagger UI)
app.include_router(upload.router,    prefix="/api/upload",    tags=["Upload"])
app.include_router(analysis.router,  prefix="/api/analysis",  tags=["Analysis"])
app.include_router(chat.router,      prefix="/api/chat",      tags=["Chat"])
app.include_router(reports.router,   prefix="/api/reports",   tags=["Reports"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint — confirms the server is running."""
    return {
        "status": "running",
        "service": "Autonomous BI System",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy"}

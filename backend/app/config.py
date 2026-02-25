"""
config.py — Application Configuration

This file loads settings from environment variables (like API keys)
so we never hard-code secrets into our source code.

Uses Pydantic's BaseSettings which automatically reads from .env files.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """
    All configuration for the app lives here.
    Values come from environment variables or the .env file.
    """

    # ── App Settings ─────────────────────────────────────────
    APP_NAME: str = "Autonomous BI System"
    DEBUG: bool = True

    # ── Google ADK / Gemini ──────────────────────────────────
    GOOGLE_API_KEY: str = ""          # Your Gemini API key
    GEMINI_MODEL: str = "gemini-2.5-flash"  # 2.5-flash has better free-tier quota

    # ── CORS (frontend URLs allowed to call this backend) ────
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    # Extra origins from env (comma-separated), e.g. Render frontend URL
    EXTRA_CORS_ORIGINS: str = ""

    # ── File Storage ─────────────────────────────────────────
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"
    MAX_FILE_SIZE_MB: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Single instance used throughout the app
settings = Settings()

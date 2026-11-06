"""Application configuration settings."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jobs.db")

# Follow-up reminder threshold (days)
FOLLOW_UP_DAYS = 7

# CORS origins allowed
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
if "your-client-id" in GOOGLE_CLIENT_ID.lower():
    GOOGLE_CLIENT_ID = ""

"""Application configuration settings."""
import os

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jobs.db")

# Follow-up reminder threshold (days)
FOLLOW_UP_DAYS = 7

# CORS origins allowed
CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

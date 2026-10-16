"""
Configuration module for the MarkItDown FastAPI backend service.
Provides environment-based configuration for database, security, JWT, OpenAI, and conversion rules.
"""

import os
from pathlib import Path
from typing import List, Set

# Base directory of the backend module
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings:
    # Project Info
    PROJECT_NAME: str = "MarkItDown API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # Database Configuration (SQLite)
    DATABASE_PATH: Path = BACKEND_DIR / "markitdown.db"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DATABASE_PATH.as_posix()}")

    # Security & JWT Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "markitdown-super-secret-key-change-in-prod-2026")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

    # External LLM / OpenAI API Configuration (for markitdown-ocr & vision)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Document & Conversion Red Line Constraints (Section 3 of agent.md)
    # File upload size limit (Default: 50MB)
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(50 * 1024 * 1024)))

    # Allowed extensions whitelist per agent.md Section 3.2
    ALLOWED_EXTENSIONS: Set[str] = {
        ".pdf",
        ".docx",
        ".pptx",
        ".xlsx",
        ".xls",
        ".jpg",
        ".jpeg",
        ".png",
        ".mp3",
        ".wav",
        ".html",
        ".csv",
        ".json",
        ".xml",
        ".zip",
        ".epub",
    }

    # Classifier Configuration (Section 5.1)
    CLASSIFIER_WEIGHTS_PATH: Path = BACKEND_DIR / "classifier" / "weights" / "best_model.pth"
    CLASSIFIER_MODEL_TYPE: str = os.getenv("CLASSIFIER_MODEL_TYPE", "cnn")

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "*",
    ]


settings = Settings()

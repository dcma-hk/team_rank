"""Configuration settings for the Team Stack Ranking Manager."""

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Application settings."""
    
    EXCEL_PATH: str = os.getenv("EXCEL_PATH", "rank.xlsx")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    
    # Data validation settings
    MAX_MEMBERS: int = 500
    MAX_METRICS: int = 100
    MAX_ROLES: int = 20
    
    # Algorithm settings
    DEFAULT_TARGET_PERCENT: float = 0.05  # 5%
    MAX_ADJUSTMENT_ITERATIONS: int = 3
    TARGET_ACHIEVEMENT_TOLERANCE: float = 0.005  # 0.5%

settings = Settings()

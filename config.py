"""Application configuration and settings."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings from environment variables"""
    
    # Database
    PG_HOST: str = os.getenv("PG_HOST", "postgres_ig")
    PG_PORT: int = int(os.getenv("PG_PORT", "5432"))
    PG_DB: str = os.getenv("PG_DB", "semantic_search")
    PG_USER: str = os.getenv("PG_USER", "semantic_user")
    PG_PASS: str = os.getenv("PG_PASS", "semantic_pass")
  
    # API
    API_HOST: str = os.getenv("API_HOST")
    API_PORT: int = int(os.getenv("API_PORT"))
    
    # Ingestion
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE"))
    MAX_CONCURRENT_INGESTIONS: int = int(os.getenv("MAX_CONCURRENT_INGESTIONS"))

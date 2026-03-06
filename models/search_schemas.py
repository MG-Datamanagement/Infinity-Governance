"""Search and statistics related schemas."""

from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field
from .enums import SourceType


class SearchRequest(BaseModel):
    """Payload for full-text catalogue search."""
    query: str
    source_type: Optional[SourceType] = None
    limit: int = 50


class StatisticsResponse(BaseModel):
    """Response containing catalog statistics."""
    total_sources: int
    active_sources: int
    total_datasets: int
    total_columns: int
    successful_jobs: int
    failed_jobs: int
    source_types_count: int
    sources_by_type: Dict[str, int]
    last_ingestion: Optional[datetime]

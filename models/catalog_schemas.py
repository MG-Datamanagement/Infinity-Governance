"""Catalog and column related schemas."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ColumnInfo(BaseModel):
    """Metadata for a single column."""
    name: str
    data_type: str
    ordinal_position: Optional[int]
    is_nullable: bool = True
    is_primary_key: bool = False
    is_foreign_key: bool = False
    description: Optional[str] = None


class CatalogInfo(BaseModel):
    """Catalog information with details."""
    id: str
    database_name: Optional[str]
    schema_name: Optional[str]
    table_name: str
    full_name: Optional[str]
    description: Optional[str]
    source_name: Optional[str]
    source_type: Optional[str]
    columns: List[ColumnInfo] = []
    properties: Dict[str, Any] = Field(default_factory=dict)
    column_count: Optional[int] = None
    row_count: Optional[int] = None
    owner_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CatalogDataCardResponse(BaseModel):
    """Data card response for a catalog."""
    catalog_id: str
    table_name: str
    full_name: Optional[str]
    data_card: str
    generated_at: datetime
    status: str  # "generated" | "cached"

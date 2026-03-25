"""Domain related schemas."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class DomainCreate(BaseModel):
    """Request to create a new domain."""
    name: str = Field(..., min_length=1, max_length=255, description="Domain name e.g. 'Finance'")
    description: Optional[str] = Field(None, description="What this domain covers")
    color: Optional[str] = Field(None, description="UI color hex e.g. '#3B82F6'")
    parent_domain_id: Optional[str] = Field(None, description="Parent domain UUID for nesting")
    owner_id: str = Field(..., description="Owner UUID responsible for this domain")


class DomainUpdate(BaseModel):
    """Request to update an existing domain."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = None
    parent_domain_id: Optional[str] = None
    owner_id: Optional[str] = None


class DomainResponse(BaseModel):
    """Domain information returned by the API."""
    id: str
    name: str
    description: Optional[str]
    color: Optional[str]
    parent_domain_id: Optional[str]
    parent_domain_name: Optional[str]   # resolved from join
    dataset_count: int = 0
    owner_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DomainAssignRequest(BaseModel):
    """Request to assign catalogs to a domain."""
    catalog_ids: List[str] = Field(..., description="List of catalog UUIDs to assign to this domain")
    assigned_by: Optional[str] = Field("system", description="Who is making this assignment")


class DomainCatalogResponse(BaseModel):
    """Catalog info when listed under a domain."""
    catalog_id: str
    full_name: Optional[str]
    table_name: str
    database_name: Optional[str]
    schema_name: Optional[str]
    source_name: Optional[str]
    source_type: Optional[str]
    assigned_at: datetime
    assigned_by: Optional[str]

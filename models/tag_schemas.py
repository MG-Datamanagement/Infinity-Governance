"""Tag related schemas."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    """Request to create a new tag."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, description="UI color hex e.g. '#10B981'")
    owner_id: str = Field(..., description="Owner UUID")


class TagUpdate(BaseModel):
    """Request to update an existing tag."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = None
    owner_id: Optional[str] = None


class TagResponse(BaseModel):
    """Tag information returned by the API."""
    id: str
    name: str
    description: Optional[str]
    color: Optional[str]
    owner_id: Optional[str]
    created_at: datetime
    updated_at: datetime


class TagAssignRequest(BaseModel):
    """Request to assign tags to catalogs."""
    catalog_ids: List[str] = Field(..., description="List of catalog UUIDs to tag")
    assigned_by: Optional[str] = "system"

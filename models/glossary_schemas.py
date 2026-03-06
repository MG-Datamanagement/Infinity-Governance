"""Glossary group and term related schemas."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class GlossaryGroupCreate(BaseModel):
    """Request to create a new glossary group."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    owner_id: Optional[str] = None
    parent_group_id: Optional[str] = None


class GlossaryGroupUpdate(BaseModel):
    """Request to update an existing glossary group."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    owner_id: Optional[str] = None
    parent_group_id: Optional[str] = None


class GlossaryGroupResponse(BaseModel):
    """Glossary group information returned by the API."""
    id: str
    name: str
    description: Optional[str]
    owner_id: Optional[str]
    owner_name: Optional[str]
    parent_group_id: Optional[str]
    parent_group_name: Optional[str]
    child_group_count: int = 0
    child_term_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class GlossaryTermCreate(BaseModel):
    """Request to create a new glossary term."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    owner_id: Optional[str] = None
    parent_group_id: Optional[str] = None


class GlossaryTermUpdate(BaseModel):
    """Request to update an existing glossary term."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    owner_id: Optional[str] = None
    parent_group_id: Optional[str] = None


class GlossaryTermResponse(BaseModel):
    """Glossary term information returned by the API."""
    id: str
    name: str
    description: Optional[str]
    owner_id: Optional[str]
    owner_name: Optional[str]
    parent_group_id: Optional[str]
    parent_group_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class GlossaryGroupNode(BaseModel):
    """Nested glossary group node for hierarchical responses."""
    id: str
    name: str
    description: Optional[str]
    owner_id: Optional[str]
    owner_name: Optional[str]
    child_groups: List["GlossaryGroupNode"] = []
    terms: List[GlossaryTermResponse] = []


GlossaryGroupNode.update_forward_refs()


class GlossaryTermAssignRequest(BaseModel):
    """Request to assign glossary terms to catalogs/columns."""
    catalog_ids: List[str] = Field(default_factory=list)
    column_ids: List[str] = Field(default_factory=list)
    assigned_by: Optional[str] = None

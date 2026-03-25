"""Lineage related schemas."""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ColumnMappingIn(BaseModel):
    """One column-to-column pair supplied by the user."""
    upstream_column_id: str = Field(..., description="Column ID in the upstream (source) table")
    downstream_column_id: str = Field(..., description="Column ID in the downstream (target) table")


class ColumnMappingOut(BaseModel):
    """Resolved column-mapping record returned in lineage responses."""
    id: str
    lineage_id: str
    upstream_column_id: str
    upstream_column_name: Optional[str]
    downstream_column_id: str
    downstream_column_name: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


class LineageCreate(BaseModel):
    """
    POST /lineage
    User defines: which two tables are connected, how columns map,
    the SQL/logic that transforms data, and optionally an owner.
    """
    upstream_catalog_id: str = Field(..., description="Catalog ID of the producing/source table")
    downstream_catalog_id: str = Field(..., description="Catalog ID of the consuming/target table")
    transformation_query: Optional[str] = Field(None, description="SQL or description of the join/transform logic")
    column_mappings: List[ColumnMappingIn] = Field(default_factory=list)
    owner_id: Optional[str] = Field(None, description="Owner (user or team) who defined this lineage")


class LineageUpdate(BaseModel):
    """
    PATCH /lineage/{lineage_id}
    All fields optional. column_mappings replaces ALL existing mappings when provided.
    """
    transformation_query: Optional[str] = None
    column_mappings: Optional[List[ColumnMappingIn]] = None
    owner_id: Optional[str] = None
    is_active: Optional[bool] = None


class TableRef(BaseModel):
    """Reference to a table/catalog."""
    id: str
    table_name: str
    full_name: Optional[str]
    schema_name: Optional[str]
    database_name: Optional[str]

    class Config:
        orm_mode = True


class LineageEdgeOut(BaseModel):
    """A single directed lineage edge with its column mappings."""
    id: str
    upstream: TableRef
    downstream: TableRef
    transformation_query: Optional[str]
    column_mappings: List[ColumnMappingOut] = []
    owner_id: Optional[str]
    owner_name: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class LineageEdge(BaseModel):
    """One hop in the recursive graph."""
    lineage_id: str
    transformation_query: Optional[str]
    column_mappings: List[ColumnMappingOut] = []
    connected_node: "LineageNode"

    class Config:
        orm_mode = True


class LineageNode(BaseModel):
    """A table node inside the lineage graph with its outgoing edges."""
    depth: int
    table: TableRef
    edges: List[LineageEdge] = []

    class Config:
        orm_mode = True


LineageNode.update_forward_refs()
LineageEdge.update_forward_refs()


class LineageGraphResponse(BaseModel):
    """Full lineage graph returned by GET /lineage/{catalog_id}."""
    root_table: TableRef
    direction: str           # "upstream" | "downstream" | "both"
    max_depth: int
    owner_id: Optional[str]
    owner_name: Optional[str]
    nodes: List[LineageNode]

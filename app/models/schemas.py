"""
Pydantic models and data schemas for Infinity Governance API
"""
from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


# Enums
class OwnerEntityType(str, Enum):
    """Types of owner entities"""
    CORP_USER = "CORP_USER"
    CORP_GROUP = "CORP_GROUP"


class DomainState(str, Enum):
    """States for domains"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


# Domain Models
class OwnerInput(BaseModel):
    """Owner input model"""
    ownerUrn: str
    ownerEntityType: OwnerEntityType
    ownershipTypeUrn: str


class CreateDomainInput(BaseModel):
    """Input model for creating a domain"""
    id: str
    name: str
    description: str
    owners: List[OwnerInput]


class DomainResponse(BaseModel):
    """Response model for domain operations"""
    urn: str
    id: str
    name: str
    description: str
    ownerUrn: str
    ownerEntityType: str
    ownershipTypeUrn: str
    state: str = DomainState.ACTIVE


class UpdateDomainInput(BaseModel):
    """Input model for updating a domain"""
    urn: str  # Required - identifies which domain to update
    
    # Optional fields - only updated if provided
    name: Optional[str] = None
    description: Optional[str] = None
    ownerUrn: Optional[str] = None
    ownershipTypeUrn: Optional[str] = None
    ownerEntityType: Optional[OwnerEntityType] = None
    state: Optional[DomainState] = None


# Tag Models
class CreateTagInput(BaseModel):
    """Input model for creating a tag"""
    id: str
    name: str
    description: str
    owners: List[OwnerInput]


class TagResponse(BaseModel):
    """Response model for tag operations"""
    urn: str
    id: str
    name: str
    description: str
    ownerUrn: str
    ownerEntityType: str
    ownershipTypeUrn: str


class UpdateTagInput(BaseModel):
    """Input model for updating a tag"""
    urn: str  # Required - identifies which tag to update
    
    # Required for GraphQL
    name: Optional[str] = None
    description: Optional[str] = None
    
    # Optional for PostgreSQL only
    ownerUrn: Optional[str] = None
    ownershipTypeUrn: Optional[str] = None
    ownerEntityType: Optional[OwnerEntityType] = None

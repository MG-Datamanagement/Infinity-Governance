"""Owner/User schemas for data asset ownership."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator
from .enums import OwnerRole


class OwnerCreate(BaseModel):
    """Payload for registering a new owner (person or team)."""
    name: str = Field(..., min_length=1, max_length=255, description="Display name of the owner")
    role: OwnerRole = Field(..., description="Accountability role assigned to this owner")
    email: Optional[str] = Field(None, max_length=255, description="Contact email (optional)")

    @validator("email")
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and "@" not in v:
            raise ValueError("email must be a valid email address")
        return v


class OwnerUpdate(BaseModel):
    """
    Partial update for an existing owner — all fields are optional.
    Only the fields that are provided will be updated in the database.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[OwnerRole] = None
    email: Optional[str] = Field(None, max_length=255)

    @validator("email")
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v and "@" not in v:
            raise ValueError("email must be a valid email address")
        return v


class OwnerResponse(BaseModel):
    """Serialised owner record returned by the API."""
    id: str
    name: str
    role: str
    email: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

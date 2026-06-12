from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime
import re


class TagCreate(BaseModel):

    name: str
    tag_type: str
    description: Optional[str] = None
    security_policy: Optional[str] = None
    color: Optional[str] = None
    status: Optional[str] = "active"
    owner_id: Optional[str] = None

    # @validator("tag_type")
    # def validate_tag_type(cls, v):

    #     allowed = ["privacy", "classification", "retention", "general"]

    #     v = v.lower()

    #     if v not in allowed:
    #         raise ValueError("Invalid tag_type")

    #     return v

    # @validator("color")
    # def validate_color(cls, v):
    #     if v is None:
    #         return v

    #     hex_pattern = r"^#([A-Fa-f0-9]{6})$"

    #     if not re.match(hex_pattern, v):
    #         raise ValueError("Color must be a valid hex code like '#10B981'")

    #     return v
    

    # @validator("security_policy")
    # def validate_policy(cls, v, values):

    #     tag_type = values.get("tag_type")

    #     privacy_classification = ["low", "medium", "high", "critical"]

    #     retention = [
    #         "30_days",
    #         "90_days",
    #         "1_year",
    #         "3_years",
    #         "7_years",
    #         "indefinite"
    #     ]

    #     if tag_type in ["privacy", "classification"]:

    #         if v not in privacy_classification:
    #             raise ValueError(
    #                 "Invalid security policy for privacy/classification"
    #             )

    #     elif tag_type == "retention":

    #         if v not in retention:
    #             raise ValueError("Invalid retention policy")

    #     elif tag_type == "general":

    #         if v is not None:
    #             raise ValueError(
    #                 "General tags cannot have security_policy"
    #             )

    #     return v

class TagResponse(BaseModel):
    id: str
    name: str
    tag_type: str
    description: Optional[str]
    security_policy: Optional[str]
    color: Optional[str]
    status: Optional[str]
    owner_id: Optional[str]
    created_at: datetime
    updated_at: datetime
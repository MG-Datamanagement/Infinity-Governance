from pydantic import BaseModel, root_validator
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from typing import Optional

class DomainUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class DomainCreateRequest(BaseModel):
    name: str
    description: str
    owner: str
    color: str

    custom_domain_name: Optional[str] = None   # ✅ changed
    catalog_id: Optional[UUID] = None

    @root_validator
    def validate_input(cls, values):
        name = values.get("name")
        custom_domain_name = values.get("custom_domain_name")

        if not custom_domain_name and not name:
            raise ValueError("Either 'custom_domain_name' or 'name' must be provided")

        return values
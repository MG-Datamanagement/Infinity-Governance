from pydantic import BaseModel, root_validator
from typing import Optional
from uuid import UUID

class DomainCreateRequest(BaseModel):
    name: str
    description: str
    owner: str
    color: str

    custom_domain_name: Optional[str] = None  
    catalog_id: Optional[UUID] = None

    @root_validator
    def validate_input(cls, values):
        name = values.get("name")
        custom_domain_name = values.get("custom_domain_name")

        if not custom_domain_name and not name:
            raise ValueError("Either 'custom_domain_name' or 'name' must be provided")

        return values
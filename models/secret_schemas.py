from pydantic import BaseModel, Field
from typing import Optional, Literal

class SecretCreateRequest(BaseModel):
    name: str = Field(..., example="POSTGRES_PASSWORD")
    type: Literal["password", "api_key", "connection_string"] = Field(
        ..., example="password"
    )
    value: str = Field(..., example="mypassword123")
    description: Optional[str] = Field(None, example="Postgres DB password")



class SecretUpdateRequest(BaseModel):
    value: str = Field(..., example="new_password_123")
    description: Optional[str] = Field(None, example="Updated secret")
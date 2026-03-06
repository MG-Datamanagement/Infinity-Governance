"""Ingestion job related schemas."""

from typing import Optional
from pydantic import BaseModel, Field, root_validator


class IngestionRequest(BaseModel):
    """Payload for triggering a metadata ingestion run against an existing source."""
    source_id: str
    include_profiling: bool = False
    include_lineage: bool = True
    incremental: bool = False
    owner_id: Optional[str] = None

    require_auto_pii_detection: bool = Field(
        default=False,
        description=(
            "When True, automatically classify all ingested tables and columns "
            "with AI-suggested tags immediately after ingestion completes."
        ),
    )

    required_human_approval: bool = Field(
        default=False,
        description=(
            "Only valid when require_auto_pii_detection=True. "
            "If True, AI suggestions are stored as PENDING and must be approved "
            "by a human before they are applied. "
            "If False, suggestions are written directly to the assignment tables."
        ),
    )

    pii_min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum confidence score (0.0-1.0) for a suggested tag to be "
            "saved or queued for approval. Results below this threshold are "
            "discarded silently."
        ),
    )

    @root_validator
    def check_approval_requires_pii_detection(cls, values):
        required_human_approval = values.get("required_human_approval")
        require_auto_pii_detection = values.get("require_auto_pii_detection")

        if required_human_approval and not require_auto_pii_detection:
            raise ValueError(
                "required_human_approval can only be True when "
                "require_auto_pii_detection is also True."
            )
        return values


    # @model_validator(mode="after")
    # def check_approval_requires_pii_detection(self) -> "IngestionRequest":
    #     if self.required_human_approval and not self.require_auto_pii_detection:
    #         raise ValueError(
    #             "required_human_approval can only be True when "
    #             "require_auto_pii_detection is also True."
    #         )
    #     return self


class IngestionResponse(BaseModel):
    """Response from ingestion trigger request."""
    job_id: str
    source_id: str
    source_name: str
    status: str
    message: str

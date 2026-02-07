# backend/dtos/strategy/userdto.py
"""
UserDTO DTO - Data transfer object for UserDTO.

Immutable Pydantic model representing UserDTO data.

@layer: DTOs (Strategy)
@dependencies: [pydantic]
"""
# Standard library
from datetime import UTC, datetime

# Third-party
from pydantic import BaseModel, Field, field_validator

# Project modules


class UserDTO(BaseModel):
    """UserDTO data transfer object."""

    # Primary identifier
    userdto_id: str = Field(
        default_factory=lambda: "USE_" + datetime.now(UTC).strftime("%Y%m%d_%H%M%S"),
        description="UserDTO unique identifier (USE_YYYYMMDD_HHMMSS_hash format)"
    )

    # Core data fields
    id: str

    # Pydantic configuration
    model_config = {
        "frozen": True,
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Standard UserDTO creation",
                    "userdto_id": "USE_20250101_120000_abc123",
                    # TODO: Add realistic example field values
                },
            ]
        }
    }

    # Validators
    @field_validator("userdto_id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Validate userdto_id follows military datetime format."""
        import re
        pattern = r"^USE_\d{8}_\d{6}_[a-f0-9]+$"
        if not re.match(pattern, v):
            raise ValueError(
                f"userdto_id must match USE_YYYYMMDD_HHMMSS_hash format, got: {v}"
            )
        return v


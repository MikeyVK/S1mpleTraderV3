# backend\dtos\DemoDTO.py
# template=dto version=0d83ee77 created=2026-02-21T16:26Z updated=
"""DemoDTO DTO module.

Data Transfer Object for DemoDTO.

@layer: DTOs
@dependencies: pydantic.BaseModel
@responsibilities: Data validation, type safety
"""

# Third-party
from pydantic import BaseModel, Field

# Project modules

class DemoDTO(BaseModel):
    """DemoDTO DTO.

    Data Transfer Object for DemoDTO.

    Fields:
        name: str
        value: int
    """
    name: str = Field(
        description="name field",
    )
    value: int = Field(
        description="value field",
    )

    model_config = {
        "frozen": False,
        "extra": "forbid",
    }

# D:\dev\SimpleTraderV3-parallel\.st3\ExampleV2DTO.py
# template=dto version=0d83ee77 created=2026-02-18T21:57Z updated=
"""ExampleV2DTO DTO module.

Data Transfer Object for ExampleV2DTO.

@layer: DTOs
@dependencies: pydantic.BaseModel
@responsibilities: Data validation, type safety
"""

# Third-party
from pydantic import BaseModel, Field

# Project modules

class ExampleV2DTO(BaseModel):
    """ExampleV2DTO DTO.

    Data Transfer Object for ExampleV2DTO.

    Fields:
        id: int
        name: str
        email: str
        created_at: datetime
    """
    id: int = Field(
        description="id field",
    )
    name: str = Field(
        description="name field",
    )
    email: str = Field(
        description="email field",
    )
    created_at: datetime = Field(
        description="created_at field",
    )

    model_config = {
        "frozen": False,
        "extra": "forbid",
    }

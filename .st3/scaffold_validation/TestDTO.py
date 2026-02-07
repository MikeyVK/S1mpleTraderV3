# d:\dev\SimpleTraderV3\.st3\scaffold_validation\TestDTO.py
# template=dto version=0d83ee77 created=2026-02-05T19:30Z updated=
"""TestDTO DTO module.

Data Transfer Object for testdto.

@layer: Domain
@dependencies: pydantic.BaseModel
@responsibilities: Data validation, type safety, immutability
"""

# Third-party
from pydantic import BaseModel, Field

# Project modules


class TestDTO(BaseModel):
    """TestDTO DTO.

    Data Transfer Object for testdto.

    Fields:
        id: Field description
        value: Field description
    """
    id: int = Field(
        default=...,
        description="Field description",
    )
    value: str = Field(
        default=...,
        description="Field description",
    )

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                "TestDTO(id=1, value=\u0027test\u0027)"
            ]
        }
    }

# tests/baselines/baseline_dto.py
# template=dto version=baseline_v1 created=2026-02-13T14:30:00Z updated=


"""BaselineTestDTO DTO module.

Data Transfer Object for baselinetestdto.

@layer: dtos
@dependencies: []
@responsibilities: Data validation, type safety, immutability
"""



# Third-party
from pydantic import BaseModel, Field

# Project modules












class BaselineTestDTO(BaseModel):

    """Test DTO for baseline capture

    Data Transfer Object for baselinetestdto.
    

    Fields:

        id: Identifier

        value: Test value

    """


    id: str = Field(

        default=...,

        description="Identifier",
    )

    value: int = Field(

        default=...,

        description="Test value",
    )


    model_config = {
        "frozen": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                "BaselineTestDTO(id=\u0027test\u0027, value=42)"
            ]
        }
    }

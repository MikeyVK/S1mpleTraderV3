# .st3/scaffold_review/ReviewSignalDTO.py
# template=dto version=0d83ee77 created=2026-02-02T08:39Z updated=
"""ReviewSignalDTO DTO module.

Data Transfer Object for reviewsignaldto.

@layer: DTOs (Review)
@dependencies: pydantic.BaseModel
@responsibilities: Data validation, type safety, immutability
"""

# Third-party
from pydantic import BaseModel, Field

# Project modules


class ReviewSignalDTO(BaseModel):
    """Signal DTO for scaffolding review.

    Data Transfer Object for reviewsignaldto.

    Fields:
        signal_id: Unique signal identifier.
        symbol: Instrument symbol.
        confidence: Confidence score between 0 and 1.
        source: Signal source system.
    """
    signal_id: str = Field(
        default=...,
        description="Unique signal identifier.",
    )
    symbol: str = Field(
        default="EURUSD",
        description="Instrument symbol.",
    )
    confidence: float = Field(
        default=0.5,
        description="Confidence score between 0 and 1.",
    )
    source: str = Field(
        default="unknown",
        description="Signal source system.",
    )

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "confidence": 0.7,
                    "signal_id": "sig_001",
                    "source": "unit-test",
                    "symbol": "EURUSD"
                }
            ]
        }
    }

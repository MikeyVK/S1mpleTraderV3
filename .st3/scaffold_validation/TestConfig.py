# d:\dev\SimpleTraderV3\.st3\scaffold_validation\TestConfig.py
# template=schema version=74378193 created=2026-02-05T19:30Z updated=
"""TestConfig schema.

Pydantic schema for configuration/validation.

@layer: Backend (Config Schemas)
"""

# Third-party
from pydantic import BaseModel, Field

# Project modules


class TestConfig(BaseModel):
    """TestConfig schema."""

    model_config = {
        "frozen": False,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": ["TestConfig(setting='value')"]
        },
    }

    setting: str = Field(
        description="Field description",
    )

# .st3/scaffold_review/ReviewWorkflowConfig.py
# template=schema version=74378193 created=2026-02-02T08:39Z updated=
"""ReviewWorkflowConfig schema.

Workflow configuration schema for review.

@layer: Backend (Config Schemas)
"""

# Third-party
from pydantic import BaseModel, Field

# Project modules


class ReviewWorkflowConfig(BaseModel):
    """Workflow configuration schema for review."""

    model_config = {
        "frozen": False,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [{'enabled': True, 'max_orders': 5, 'mode': 'paper'}]
        },
    }

    enabled: bool = Field(
        default=True,
        description="Whether the workflow is enabled.",
    )
    max_orders: int = Field(
        default=5,
        description="Maximum number of orders to place.",
    )
    mode: str = Field(
        default="paper",
        description="Execution mode (paper|live).",
    )

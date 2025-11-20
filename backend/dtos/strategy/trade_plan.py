"""
TradePlan DTO.

Acts as the Execution Anchor for a strategy's lifecycle, linking
strategic intent (Journal) with market reality (Ledger).

@layer: Strategy
@dependencies: [backend.core.enums, backend.utils.id_generators]
"""

import re
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from backend.core.enums import TradeStatus
from backend.utils.id_generators import generate_trade_plan_id

class TradePlan(BaseModel):
    """
    Root container for a strategy's lifecycle.

    Serves as the stable identity (Anchor) for cross-referencing
    Ledger reality with Journal causality.
    """

    plan_id: str = Field(
        default_factory=generate_trade_plan_id,
        description="Unique identifier. The anchor for cross-referencing."
    )
    strategy_instance_id: str = Field(..., description="ID of the owning strategy instance.")
    status: TradeStatus = Field(..., description="Current lifecycle state.")
    created_at: datetime = Field(..., description="Creation timestamp (UTC).")

    model_config = {
        "frozen": False,
        "str_strip_whitespace": True,
        "validate_assignment": True
    }

    @field_validator("plan_id")
    @classmethod
    def validate_plan_id_format(cls, v: str) -> str:
        """
        Ensures plan_id follows the standard format: TPL_{YYYYMMDD}_{HHMMSS}_{hash}
        Example: TPL_20251030_120000_abc12
        """
        pattern = r"^TPL_\d{8}_\d{6}_[0-9a-z]{5,8}$"
        if not re.match(pattern, v):
            raise ValueError(f"plan_id must match format '{pattern}', got '{v}'")
        return v

# backend/dtos/strategy/entry_plan.py
"""
EntryPlan DTO - WHAT/WHERE to enter (lean version).

Specifies WHAT order to place and WHERE (price levels) for entry.
Pure execution parameters without timing/routing/metadata.

**Refactored to Lean Spec (2025-10-27):**
- Removed: created_at, planner_id (moved to worker context)
- Removed: timing (moved to ExecutionPlan - execution tactics)
- Removed: reference_price, max_slippage_pct (moved to ExecutionPlan)
- Removed: valid_until, planner_metadata, rationale (unnecessary)
- Removed: causality (sub-planners don't track causality)

**What Remains:** Pure entry specification (WHAT/WHERE)
- Symbol, direction, order type
- Price levels (limit_price, stop_price) for order execution

**Causality Propagation:**
Sub-planners receive StrategyDirective as input (has causality).
PlanningAggregator extracts causality from StrategyDirective and
adds plan IDs to create ExecutionDirective with complete chain.

@layer: DTOs (Strategy Planning Output)
@dependencies: [pydantic, backend.utils.id_generators]
"""

# Standard Library Imports
import re
from decimal import Decimal
from typing import Literal

# Third-Party Imports
from pydantic import BaseModel, Field, field_validator

# Our Application Imports
from backend.utils.id_generators import generate_entry_plan_id


class EntryPlan(BaseModel):
    """
    Entry plan - WHAT/WHERE to enter (lean spec).

    Pure entry execution parameters created by Entry Planning workers.
    Defines WHAT order (type, symbol, direction) and WHERE (price levels).

    **Key Responsibilities:**
    - Order type selection (MARKET, LIMIT, STOP_LIMIT)
    - Price levels (limit_price, stop_price)

    **NOT Responsible For:**
    - Timing/urgency (→ ExecutionPlan)
    - Slippage tolerance (→ ExecutionPlan)
    - Position sizing (→ SizePlan)
    - Exit strategy (→ ExitPlan)
    - Metadata/rationale (worker context only)

    **Usage Example:**
    ```python
    # Limit order entry at specific price
    plan = EntryPlan(
        symbol="BTC_USDT",
        direction="BUY",
        order_type="LIMIT",
        limit_price=Decimal("95500.00")
    )
    ```

    **Attributes:**
        plan_id: Auto-generated unique identifier (ENT_YYYYMMDD_HHMMSS_hash)
        symbol: Trading pair (e.g., 'BTC_USDT')
        direction: Trade direction (BUY or SELL)
        order_type: Order execution type (MARKET, LIMIT, STOP_LIMIT)
        limit_price: Limit price for LIMIT orders (optional)
        stop_price: Stop trigger price for STOP_LIMIT orders (optional)
    """

    # Identiteit
    plan_id: str = Field(
        default_factory=generate_entry_plan_id,
        description="Unique identifier for this entry plan"
    )

    # Trade basics
    symbol: str = Field(
        description="Trading pair symbol (e.g., 'BTC_USDT')"
    )
    direction: Literal["BUY", "SELL"] = Field(
        description="Trade direction"
    )

    # Entry execution strategy
    order_type: Literal["MARKET", "LIMIT", "STOP_LIMIT"] = Field(
        description="Order type for entry execution"
    )

    # Price levels
    limit_price: Decimal | None = Field(
        None,
        description="Limit price for LIMIT orders"
    )
    stop_price: Decimal | None = Field(
        None,
        description="Stop price for STOP_LIMIT orders"
    )

    model_config = {
        "frozen": False,  # Mutable for updates
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Market entry (WHAT/WHERE only)",
                    "plan_id": "ENT_20251027_143052_a1b2c3d4",
                    "symbol": "BTC_USDT",
                    "direction": "BUY",
                    "order_type": "MARKET"
                },
                {
                    "description": "Limit entry at specific price",
                    "plan_id": "ENT_20251027_143053_e5f6g7h8",
                    "symbol": "ETH_USDT",
                    "direction": "SELL",
                    "order_type": "LIMIT",
                    "limit_price": "3510.00"
                },
                {
                    "description": "Stop-limit for breakout",
                    "plan_id": "ENT_20251027_143054_i9j0k1l2",
                    "symbol": "SOL_USDT",
                    "direction": "BUY",
                    "order_type": "STOP_LIMIT",
                    "stop_price": "125.00",
                    "limit_price": "125.50"
                }
            ]
        }
    }

    @field_validator("plan_id")
    @classmethod
    def validate_plan_id_format(cls, v: str) -> str:
        """Validate plan_id follows military datetime format: ENT_YYYYMMDD_HHMMSS_hash"""
        pattern = r'^ENT_\d{8}_\d{6}_[0-9a-f]{8}$'
        if not re.match(pattern, v):
            raise ValueError(
                f"plan_id must match format ENT_YYYYMMDD_HHMMSS_hash, got: {v}"
            )
        return v

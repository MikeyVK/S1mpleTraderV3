# backend/dtos/strategy/exit_plan.py
"""
ExitPlan DTO - WHERE OUT specification (lean version).

Specifies WHERE to exit a position through price levels.
Pure exit execution parameters without dynamic behavior logic.

**Lean Spec Philosophy:**
- WHERE OUT: stop_loss_price, take_profit_price
- NO trailing stops, breakeven adjustments (PositionMonitor handles)
- NO metadata, timestamps, causality (sub-planners don't track)

**What This IS:**
- Static exit price targets for order placement
- Simple risk/reward level specification

**What This Is NOT:**
- Dynamic exit logic (trailing, breakeven) → PositionMonitor
- Execution timing/routing → RoutingPlan
- Metadata/causality tracking → StrategyDirective has causality

**Causality Propagation:**
Sub-planners receive StrategyDirective as input (has causality).
PlanningAggregator extracts causality from StrategyDirective and
adds plan IDs to create ExecutionDirective with complete chain.

@layer: DTOs (Strategy Planning Output)
@dependencies: [pydantic, decimal, backend.utils.id_generators]
"""

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from backend.utils.id_generators import generate_exit_plan_id


class ExitPlan(BaseModel):
    """
    Exit plan - WHERE OUT specification (lean spec).

    Pure exit price levels created by Exit Planning workers.
    Defines WHERE to exit via stop loss and take profit targets.

    **Key Responsibilities:**
    - Stop loss price (required - risk protection)
    - Take profit price (optional - profit target)

    **NOT Responsible For:**
    - Trailing stops, breakeven logic (PositionMonitor handles)
    - Execution timing (RoutingPlan handles)
    - Causality tracking (parent StrategyDirective has it)

    Fields:
        plan_id: Unique exit plan ID (EXT_YYYYMMDD_HHMMSS_hash)
        stop_loss_price: Stop loss price level (required, > 0)
        take_profit_price: Take profit price level (optional, > 0)

    Examples:
        >>> # SL and TP
        >>> plan = ExitPlan(
        ...     stop_loss_price=Decimal("95000.00"),
        ...     take_profit_price=Decimal("105000.00")
        ... )

        >>> # SL only (let winners run)
        >>> plan = ExitPlan(
        ...     stop_loss_price=Decimal("95000.00")
        ... )
    """

    plan_id: str = Field(
        default_factory=generate_exit_plan_id,
        pattern=r'^EXT_\d{8}_\d{6}_[0-9a-f]{8}$',
        description="Unique exit plan ID (military datetime format)"
    )

    stop_loss_price: Decimal = Field(
        description="Stop loss price level (required for risk protection)",
        gt=0,
        decimal_places=8,
        max_digits=20
    )

    take_profit_price: Optional[Decimal] = Field(
        None,
        description="Take profit price level (optional profit target)",
        gt=0,
        decimal_places=8,
        max_digits=20
    )

    @field_validator("stop_loss_price", "take_profit_price")
    @classmethod
    def validate_positive_prices(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure price levels are positive when provided."""
        if v is not None and v <= 0:
            raise ValueError("Price must be greater than 0")
        return v

    model_config = {
        "frozen": True,
        "extra": "forbid"
    }

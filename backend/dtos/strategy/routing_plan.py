# backend/dtos/strategy/routing_plan.py
"""
RoutingPlan DTO - HOW/WHEN execution specification (lean version).

Specifies HOW and WHEN to execute orders through timing strategy,
urgency levels, and slippage tolerance.

**Lean Spec Philosophy:**
- HOW/WHEN: timing, time_in_force, slippage, urgency, iceberg
- NO TWAP params (duration, intervals) - platform config handles
- NO metadata, timestamps, causality (sub-planners don't track)

**What This IS:**
- Execution timing strategy selection (IMMEDIATE, TWAP, PATIENT)
- Order behavior params (TIF, slippage tolerance, urgency)
- Routing hints (iceberg preference)

**What This Is NOT:**
- TWAP implementation params → Platform/exchange config
- Dynamic routing logic → ExecutionHandler decides
- Metadata/causality tracking → StrategyDirective has causality

**Causality Propagation:**
Sub-planners receive StrategyDirective as input (has causality).
PlanningAggregator extracts causality from StrategyDirective and
adds plan IDs to create ExecutionDirective with complete chain.

@layer: DTOs (Strategy Planning Output)
@dependencies: [pydantic, decimal, typing, backend.utils.id_generators]
"""

# Standard Library Imports
from decimal import Decimal
from typing import Literal

# Third-Party Imports
from pydantic import BaseModel, Field, field_validator

# Our Application Imports
from backend.utils.id_generators import generate_routing_plan_id


class RoutingPlan(BaseModel):
    """
    Routing plan - HOW/WHEN execution specification (lean spec).

    Pure execution timing/routing parameters created by Routing workers.
    Defines HOW (slippage, urgency) and WHEN (timing strategy, TIF).

    **Key Responsibilities:**
    - Timing strategy (IMMEDIATE, TWAP, LAYERED, PATIENT)
    - Time in force (GTC, IOC, FOK)
    - Slippage tolerance (max acceptable %)
    - Execution urgency (0=patient, 1=urgent)
    - Iceberg preference (visibility control)

    **NOT Responsible For:**
    - TWAP implementation (duration, intervals) → Platform config
    - Dynamic routing decisions → ExecutionHandler
    - Causality tracking → Parent StrategyDirective has it

    Fields:
        plan_id: Unique routing plan ID (ROU_YYYYMMDD_HHMMSS_hash)
        timing: Execution timing strategy
        time_in_force: Order validity duration
        max_slippage_pct: Max acceptable slippage (0-100%)
        execution_urgency: Priority score (0.0=patient, 1.0=urgent)
        iceberg_preference: Hide order size (default False)

    Examples:
        >>> # Urgent market entry
        >>> plan = RoutingPlan(
        ...     timing="IMMEDIATE",
        ...     time_in_force="IOC",
        ...     max_slippage_pct=Decimal("1.0"),
        ...     execution_urgency=Decimal("0.9")
        ... )

        >>> # Patient accumulation via TWAP
        >>> plan = RoutingPlan(
        ...     timing="TWAP",
        ...     time_in_force="GTC",
        ...     max_slippage_pct=Decimal("0.2"),
        ...     execution_urgency=Decimal("0.2"),
        ...     iceberg_preference=True
        ... )
    """

    plan_id: str = Field(
        default_factory=generate_routing_plan_id,
        pattern=r'^ROU_\d{8}_\d{6}_[0-9a-f]{8}$',
        description="Unique routing plan ID (military datetime format)"
    )

    timing: Literal["IMMEDIATE", "TWAP", "LAYERED", "PATIENT"] = Field(
        description="Execution timing strategy"
    )

    time_in_force: Literal["GTC", "IOC", "FOK"] = Field(
        description="Order validity duration"
    )

    max_slippage_pct: Decimal = Field(
        description="Max acceptable slippage percentage (0-100%)",
        ge=0,
        le=100,
        decimal_places=8,
        max_digits=20
    )

    execution_urgency: Decimal = Field(
        description="Execution priority score (0.0=patient, 1.0=urgent)",
        ge=0,
        le=1,
        decimal_places=8,
        max_digits=20
    )

    iceberg_preference: bool = Field(
        False,
        description="Hide order size for large orders (default False)"
    )

    @field_validator("max_slippage_pct", "execution_urgency")
    @classmethod
    def validate_bounded_decimals(cls, v: Decimal, info) -> Decimal:
        """Ensure bounded Decimal fields are within range."""
        field_name = info.field_name

        if field_name == "max_slippage_pct":
            if v < 0 or v > 100:
                raise ValueError(
                    "max_slippage_pct must be between 0 and 100"
                )
        elif field_name == "execution_urgency":
            if v < 0 or v > 1:
                raise ValueError(
                    "execution_urgency must be between 0.0 and 1.0"
                )

        return v

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "description": (
                        "Urgent market entry (high urgency, IOC)"
                    ),
                    "plan_id": "ROU_20251027_100530_a1b2c3d4",
                    "timing": "IMMEDIATE",
                    "time_in_force": "IOC",
                    "max_slippage_pct": "1.0",
                    "execution_urgency": "0.9",
                    "iceberg_preference": False
                },
                {
                    "description": (
                        "Patient TWAP accumulation (low urgency, iceberg)"
                    ),
                    "plan_id": "ROU_20251027_143000_e5f6g7h8",
                    "timing": "TWAP",
                    "time_in_force": "GTC",
                    "max_slippage_pct": "0.2",
                    "execution_urgency": "0.2",
                    "iceberg_preference": True
                },
                {
                    "description": (
                        "Layered limit orders (medium urgency, tight slippage)"
                    ),
                    "plan_id": "ROU_20251027_150500_i9j0k1l2",
                    "timing": "LAYERED",
                    "time_in_force": "GTC",
                    "max_slippage_pct": "0.1",
                    "execution_urgency": "0.5",
                    "iceberg_preference": False
                }
            ]
        }
    }

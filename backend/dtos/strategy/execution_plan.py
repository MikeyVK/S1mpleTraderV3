# backend/dtos/strategy/execution_plan.py
"""
ExecutionPlan DTO - Universal execution trade-offs.

Replaces RoutingPlan with connector-agnostic execution plan that expresses
WHAT the strategy wants (trade-offs) rather than HOW to execute (connector-specific).

**Architectural Contract (EXECUTION_PLAN_DESIGN.md):**
- Universal trade-offs: urgency, visibility, slippage (all Decimal 0.0-1.0)
- Constraints vs Hints: MUST respect (max_slippage) vs MAY interpret (preferred_style)
- Action types: EXECUTE_TRADE, CANCEL_ORDER, MODIFY_ORDER, CANCEL_GROUP
- Immutability: frozen=True for audit trail integrity
- Type safety: Decimal (not float) for precision requirements

**Breaking Changes from RoutingPlan:**
- REMOVED: time_in_force, iceberg_preference, timing (connector-specific)
- ADDED: execution_urgency (0.0-1.0), visibility_preference (0.0-1.0)
- ADDED: action field for non-trade operations (cancel, modify)
- ADDED: hints (preferred_execution_style, chunk_count_hint, chunk_distribution)

**Translation Pattern:**
ExecutionPlan (universal) → ExecutionTranslator → ConnectorExecutionSpec (CEX/DEX/Backtest)
Strategy layer connector-agnostic, platform layer handles specifics.

@layer: DTOs (Strategy Planning Output)
@dependencies: [pydantic, decimal, backend.core.enums, backend.utils.id_generators]
"""

# Standard Library Imports
from decimal import Decimal

# Third-Party Imports
from pydantic import BaseModel, Field, field_validator

# Our Application Imports
from backend.core.enums import ExecutionAction
from backend.utils.id_generators import generate_execution_plan_id


class ExecutionPlan(BaseModel):
    """
    Execution plan - Universal trade-offs for connector-agnostic execution.

    Expresses WHAT the strategy wants (trade-offs) not HOW to execute it.
    Translator layer converts universal plan → connector-specific execution spec.

    **Key Responsibilities:**
    - Universal trade-offs: urgency, visibility, slippage (0.0-1.0 range)
    - Hard constraints: max_slippage_pct (MUST respect)
    - Optional hints: preferred_execution_style, chunk_count (MAY interpret)
    - Action type: EXECUTE_TRADE, CANCEL_ORDER, MODIFY_ORDER, CANCEL_GROUP

    **NOT Responsible For:**
    - Connector-specific params (time_in_force, iceberg) → Translator decides
    - TWAP implementation (duration, intervals) → Platform/translator config
    - Routing decisions → ExecutionTranslator handles

    **Universal Trade-Offs:**
    - execution_urgency: 0.0 (patient) → 1.0 (urgent/immediate)
    - visibility_preference: 0.0 (stealth) → 1.0 (transparent/visible)
    - max_slippage_pct: 0.0 (tight) → 1.0 (100% slippage, emergency only)

    **Constraints vs Hints:**
    - Constraints (MUST): max_slippage_pct, must_complete_immediately
    - Hints (MAY): preferred_execution_style, chunk_count_hint, chunk_distribution

    Fields:
        plan_id: Unique execution plan ID (EXP_YYYYMMDD_HHMMSS_xxxxx)
        action: Action type (EXECUTE_TRADE, CANCEL_ORDER, etc)
        execution_urgency: Patience vs speed (0.0=patient, 1.0=urgent)
        visibility_preference: Stealth vs transparency (0.0=stealth, 1.0=visible)
        max_slippage_pct: Hard price limit (0.0-1.0, 4 decimal places)
        must_complete_immediately: Force immediate execution (default False)
        max_execution_window_minutes: Time window for completion (optional)
        preferred_execution_style: Hint for execution style (e.g., "TWAP", "VWAP")
        chunk_count_hint: Hint for number of chunks (optional)
        chunk_distribution: Hint for chunk distribution (e.g., "UNIFORM", "WEIGHTED")
        min_fill_ratio: Minimum fill ratio to accept (optional)

    Examples:
        >>> # High urgency market order
        >>> plan = ExecutionPlan(
        ...     action=ExecutionAction.EXECUTE_TRADE,
        ...     execution_urgency=Decimal("0.90"),
        ...     visibility_preference=Decimal("0.70"),
        ...     max_slippage_pct=Decimal("0.0100"),
        ...     must_complete_immediately=True
        ... )

        >>> # Patient TWAP accumulation
        >>> plan = ExecutionPlan(
        ...     action=ExecutionAction.EXECUTE_TRADE,
        ...     execution_urgency=Decimal("0.20"),
        ...     visibility_preference=Decimal("0.10"),
        ...     max_slippage_pct=Decimal("0.0050"),
        ...     max_execution_window_minutes=30,
        ...     preferred_execution_style="TWAP",
        ...     chunk_count_hint=5
        ... )

        >>> # Emergency cancel group
        >>> plan = ExecutionPlan(
        ...     action=ExecutionAction.CANCEL_GROUP,
        ...     execution_urgency=Decimal("1.0"),
        ...     visibility_preference=Decimal("0.5"),
        ...     max_slippage_pct=Decimal("0.0"),
        ...     must_complete_immediately=True
        ... )
    """

    plan_id: str = Field(
        default_factory=generate_execution_plan_id,
        pattern=r'^EXP_\d{8}_\d{6}_[0-9a-z]{5}$',
        description="Unique execution plan ID (military datetime format)"
    )

    action: ExecutionAction = Field(
        default=ExecutionAction.EXECUTE_TRADE,
        description=(
            "Action type (EXECUTE_TRADE, CANCEL_ORDER, "
            "MODIFY_ORDER, CANCEL_GROUP)"
        )
    )

    execution_urgency: Decimal = Field(
        description="Patience vs speed trade-off (0.0=patient, 1.0=urgent)",
        ge=0,
        le=1,
        decimal_places=2,
        max_digits=3
    )

    visibility_preference: Decimal = Field(
        description=(
            "Stealth vs transparency trade-off "
            "(0.0=stealth, 1.0=visible)"
        ),
        ge=0,
        le=1,
        decimal_places=2,
        max_digits=3
    )

    max_slippage_pct: Decimal = Field(
        description=(
            "Hard price limit - max acceptable slippage (0.0-1.0 = 0-100%)"
        ),
        ge=0,
        le=1,
        decimal_places=4,
        max_digits=5
    )

    must_complete_immediately: bool = Field(
        default=False,
        description="Force immediate execution (constraint, not hint)"
    )

    max_execution_window_minutes: int | None = Field(
        default=None,
        description="Maximum time window for completion (minutes)",
        ge=1
    )

    preferred_execution_style: str | None = Field(
        default=None,
        description=(
            "Hint for execution style (e.g., 'TWAP', 'VWAP', 'ICEBERG') - "
            "MAY be interpreted"
        )
    )

    chunk_count_hint: int | None = Field(
        default=None,
        description="Hint for number of execution chunks - MAY be interpreted",
        ge=1
    )

    chunk_distribution: str | None = Field(
        default=None,
        description=(
            "Hint for chunk distribution (e.g., 'UNIFORM', 'WEIGHTED') - "
            "MAY be interpreted"
        )
    )

    min_fill_ratio: Decimal | None = Field(
        default=None,
        description="Minimum fill ratio to accept (0.0-1.0)",
        ge=0,
        le=1,
        decimal_places=2,
        max_digits=3
    )

    @field_validator("execution_urgency", "visibility_preference")
    @classmethod
    def validate_trade_off_range(cls, v: Decimal, info) -> Decimal:
        """Ensure trade-off fields are within 0.0-1.0 range."""
        field_name = info.field_name

        if v < 0 or v > 1:
            raise ValueError(
                f"{field_name} must be between 0.0 and 1.0 "
                f"(got {v})"
            )

        return v

    @field_validator("max_slippage_pct")
    @classmethod
    def validate_slippage_range(cls, v: Decimal) -> Decimal:
        """Ensure slippage is within 0.0-1.0 range (0-100%)."""
        if v < 0 or v > 1:
            raise ValueError(
                f"max_slippage_pct must be between 0.0 and 1.0 "
                f"(0-100% slippage, got {v})"
            )

        return v

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "description": "High urgency market order - immediate execution",
                    "plan_id": "EXP_20251028_100530_a8f3c",
                    "action": "EXECUTE_TRADE",
                    "execution_urgency": "0.90",
                    "visibility_preference": "0.70",
                    "max_slippage_pct": "0.0100",
                    "must_complete_immediately": True
                },
                {
                    "description": "Patient TWAP accumulation - stealth, low urgency",
                    "plan_id": "EXP_20251028_143000_b7c4d",
                    "action": "EXECUTE_TRADE",
                    "execution_urgency": "0.20",
                    "visibility_preference": "0.10",
                    "max_slippage_pct": "0.0050",
                    "must_complete_immediately": False,
                    "max_execution_window_minutes": 30,
                    "preferred_execution_style": "TWAP",
                    "chunk_count_hint": 5,
                    "chunk_distribution": "UNIFORM",
                    "min_fill_ratio": "0.80"
                },
                {
                    "description": "Emergency cancel group - max urgency, immediate",
                    "plan_id": "EXP_20251028_150500_c8e6f",
                    "action": "CANCEL_GROUP",
                    "execution_urgency": "1.0",
                    "visibility_preference": "0.5",
                    "max_slippage_pct": "0.0",
                    "must_complete_immediately": True
                },
                {
                    "description": "DEX swap - stealth mode, private mempool hint",
                    "plan_id": "EXP_20251028_153000_d9a7f",
                    "action": "EXECUTE_TRADE",
                    "execution_urgency": "0.60",
                    "visibility_preference": "0.05",
                    "max_slippage_pct": "0.0200",
                    "preferred_execution_style": "PRIVATE_MEMPOOL"
                },
                {
                    "description": "Backtest simulation - medium urgency, no hints",
                    "plan_id": "EXP_20251028_160000_e1b8g",
                    "action": "EXECUTE_TRADE",
                    "execution_urgency": "0.50",
                    "visibility_preference": "0.50",
                    "max_slippage_pct": "0.0"
                }
            ]
        }
    }

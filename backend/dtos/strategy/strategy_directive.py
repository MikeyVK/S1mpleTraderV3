# backend/dtos/strategy/strategy_directive.py
"""
StrategyDirective and sub-directive DTOs for quant-driven trade planning.

@layer: Strategy
@dependencies: backend.utils.id_generators, backend.core.enums
@responsibilities:
    - Bridge detection framework (Signal, Risk)
      and Planning Layer (EntryPlan, SizePlan, ExitPlan, ExecutionPlan)
    - Contain 4 sub-directives (Entry, Size, Exit, Routing) with constraints/hints
    - Enable signal-driven position management (NEW_TRADE, MODIFY_EXISTING, CLOSE_EXISTING)
    - Provide causality tracking from analysis to execution planning
"""

# Standard library imports
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

# Third-party imports
from pydantic import BaseModel, Field, ValidationInfo, field_validator

# Application imports
from backend.core.enums import BatchExecutionMode, DirectiveScope
from backend.dtos.causality import CausalityChain
from backend.utils.id_generators import generate_strategy_directive_id


class EntryDirective(BaseModel):
    """
    Entry constraints and hints for EntryPlanner.

    Attributes:
        symbol: Trading symbol (e.g., "BTC_USDT")
        direction: Trade direction (BUY or SELL)
        timing_preference: Urgency [0.0-1.0], 1.0 = immediate, 0.0 = patient
        preferred_price_zone: Optional preferred price zone (min, max)
        max_acceptable_slippage: Maximum acceptable slippage as decimal (e.g., 0.001 = 0.1%)
    """

    symbol: str = Field(
        ...,
        description="Trading symbol (e.g., 'BTC_USDT')"
    )
    direction: str = Field(
        ...,
        description="Trade direction: BUY or SELL"
    )
    timing_preference: Annotated[
        Decimal, Field(ge=Decimal("0.0"), le=Decimal("1.0"))
    ] = Field(
        default=Decimal("0.5"),
        description=(
            "Entry timing urgency [0.0-1.0]: "
            "1.0 = immediate, 0.0 = patient waiting for ideal price"
        )
    )
    preferred_price_zone: tuple[Decimal, Decimal] | None = Field(
        default=None,
        description="Optional preferred entry price zone (min, max)"
    )
    max_acceptable_slippage: Annotated[
        Decimal, Field(ge=Decimal("0.0"))
    ] = Field(
        default=Decimal("0.005"),
        description=(
            "Maximum acceptable slippage as decimal (e.g., 0.001 = 0.1%)"
        )
    )


class SizeDirective(BaseModel):
    """
    Sizing constraints and hints for SizePlanner.

    Attributes:
        aggressiveness: Position size aggressiveness [0.0-1.0], 1.0 = max size, 0.0 = minimal
        max_risk_amount: Maximum risk amount in quote currency
        account_risk_pct: Maximum account risk as decimal (e.g., 0.02 = 2%)
    """

    aggressiveness: Annotated[
        Decimal, Field(ge=Decimal("0.0"), le=Decimal("1.0"))
    ] = Field(
        default=Decimal("0.5"),
        description=(
            "Position size aggressiveness [0.0-1.0]: "
            "1.0 = maximum size, 0.0 = minimal size"
        )
    )
    max_risk_amount: Annotated[
        Decimal, Field(gt=Decimal("0.0"))
    ] = Field(
        ...,
        description=(
            "Maximum risk amount in quote currency (e.g., 100.00 USDT)"
        )
    )
    account_risk_pct: Annotated[
        Decimal, Field(ge=Decimal("0.0"), le=Decimal("1.0"))
    ] = Field(
        default=Decimal("0.02"),
        description=(
            "Maximum account risk as decimal (e.g., 0.02 = 2% of account)"
        )
    )


class ExitDirective(BaseModel):
    """
    Exit constraints and hints for ExitPlanner.

    Attributes:
        profit_taking_preference: Profit-taking aggressiveness [0.0-1.0],
            1.0 = tight targets, 0.0 = let profits run
        risk_reward_ratio: Minimum risk-reward ratio (e.g., 2.5 = 2.5:1)
        stop_loss_tolerance: Stop loss distance as decimal
            (e.g., 0.015 = 1.5% from entry)
    """

    profit_taking_preference: Annotated[
        Decimal, Field(ge=Decimal("0.0"), le=Decimal("1.0"))
    ] = Field(
        default=Decimal("0.5"),
        description=(
            "Profit-taking aggressiveness [0.0-1.0]: "
            "1.0 = tight targets (quick profits), 0.0 = let profits run"
        )
    )
    risk_reward_ratio: Annotated[
        Decimal, Field(gt=Decimal("0.0"))
    ] = Field(
        default=Decimal("2.0"),
        description=(
            "Minimum risk-reward ratio (e.g., 2.5 = 2.5:1 reward to risk)"
        )
    )
    stop_loss_tolerance: Annotated[
        Decimal, Field(ge=Decimal("0.0"))
    ] = Field(
        default=Decimal("0.02"),
        description=(
            "Stop loss distance as decimal (e.g., 0.015 = 1.5% from entry)"
        )
    )


class ExecutionDirective(BaseModel):
    """
    Routing/execution constraints and hints for ExecutionPlanner.

    NOTE: Visibility preferences (iceberg orders, stealth execution) are handled
    at ExecutionPlan level via visibility_preference field, not here.
    ExecutionDirective provides strategic hints; ExecutionPlan provides concrete
    execution specifications.

    Attributes:
        execution_urgency: Execution urgency [0.0-1.0],
            1.0 = market orders, 0.0 = patient limit orders
        max_total_slippage_pct: Maximum total slippage across all executions
            as decimal
    """

    execution_urgency: Annotated[
        Decimal, Field(ge=Decimal("0.0"), le=Decimal("1.0"))
    ] = Field(
        default=Decimal("0.5"),
        description=(
            "Execution urgency [0.0-1.0]: "
            "1.0 = immediate market orders, 0.0 = patient limit orders"
        )
    )
    max_total_slippage_pct: Annotated[
        Decimal, Field(ge=Decimal("0.0"))
    ] = Field(
        default=Decimal("0.01"),
        description=(
            "Maximum total slippage across all executions as decimal "
            "(e.g., 0.01 = 1%)"
        )
    )


class ExecutionPolicy(BaseModel):
    """
    Strategic execution coordination policy for command batches.

    Defines how multiple ExecutionCommands from a single StrategyDirective
    should be coordinated during execution. This is the STRATEGIC intent
    (what should happen) - not the technical execution mechanism.

    ARCHITECTURAL POSITION:
    - Lives in StrategyDirective as optional field
    - Flows unchanged ("dumb pipe") to ExecutionCommandBatch.mode
    - No transformation logic - pure 1:1 mapping

    USE CASES:
    - INDEPENDENT: Flash crash exit - close all positions regardless of individual failures
    - COORDINATED: Pair trade - both legs must succeed or cancel both
    - SEQUENTIAL: DCA with dependencies - execute in order, stop on failure

    Attributes:
        mode: Coordination mode (INDEPENDENT, COORDINATED, SEQUENTIAL)
        timeout_seconds: Optional coordination timeout in seconds

    See Also:
        - docs/development/backend/dtos/EXECUTION_COMMAND_BATCH_DESIGN.md
        - BatchExecutionMode enum in backend.core.enums
    """

    mode: BatchExecutionMode = Field(
        default=BatchExecutionMode.INDEPENDENT,
        description=(
            "Coordination mode: INDEPENDENT (fire all, ignore failures), "
            "COORDINATED (cancel pending on failure), "
            "SEQUENTIAL (execute in order, stop on failure)"
        )
    )
    timeout_seconds: Annotated[int, Field(gt=0)] | None = Field(
        default=None,
        description=(
            "Optional coordination timeout in seconds. "
            "For COORDINATED mode, defines how long to wait for all legs."
        )
    )

    model_config = {
        "frozen": True,  # Immutable after creation
        "str_strip_whitespace": True,
    }


class StrategyDirective(BaseModel):
    """
    Universal strategy directive from ANY StrategyPlanner to role-based planners.

    ARCHITECTURAL POSITION:
    StrategyDirective is the critical bridge between ANY StrategyPlanner type and the Planning
    Layer (EntryPlan, SizePlan, ExitPlan, ExecutionPlan). It translates strategic analysis into
    tactical constraints/hints that guide role-based planners.

    STRATEGYPLANNER TYPES:
    - **Entry Strategy**: Signal + Context → NEW_TRADE
    - **Position Management**: Position monitoring + tick → MODIFY_EXISTING
    - **Risk Control**: Risk events → CLOSE_EXISTING
    - **Scheduled Operations**: Time trigger → NEW_TRADE

    DIRECTIVE FLOW:
    1. StrategyPlanner receives trigger (signals, tick, risk, schedule)
    2. StrategyPlanner produces StrategyDirective with:
       - Scope: NEW_TRADE, MODIFY_EXISTING, or CLOSE_EXISTING
       - TriggerContext: Causality tracking (what caused this directive)
       - Sub-directives: EntryDirective, SizeDirective, ExitDirective, ExecutionDirective
    3. Role-based planners (EntryPlanner, SizePlanner, etc.) receive StrategyDirective
    4. Each planner reads its corresponding sub-directive and produces Planning DTO
    5. DirectiveAssembler combines all Planning DTOs into ExecutionDirective

    DIRECTIVE SCOPES:
    - **NEW_TRADE**: Open new position
      - Required fields: scope=NEW_TRADE, target_plan_ids=[]
      - Typical sub-directives: EntryDirective, SizeDirective, ExitDirective, ExecutionDirective
      - All sub-directives are OPTIONAL - planners use defaults if missing

    - **MODIFY_EXISTING**: Adjust existing position or open order
      - Required fields: scope=MODIFY_EXISTING, target_plan_ids=[...] (not empty)
      - Typical sub-directives:
        - EntryDirective: Modify open limit order (price, timing)
        - SizeDirective: Increase/decrease position size
        - ExitDirective: Adjust stops/targets
        - ExecutionDirective: Change routing strategy
      - All sub-directives are OPTIONAL - only provided sub-directives trigger changes

    - **CLOSE_EXISTING**: Close existing position(s)
      - Required fields: scope=CLOSE_EXISTING, target_plan_ids=[...] (not empty)
      - Typical sub-directives:
        - ExecutionDirective: Execution urgency for emergency exits
        - ExitDirective: Partial close targets
      - All sub-directives are OPTIONAL

    SUB-DIRECTIVES AS CONSTRAINTS:
    Each sub-directive provides constraints/hints to its corresponding planner.
    If a sub-directive is MISSING, the planner behavior depends on the strategy mode:
    - **Beginner mode**: Single planner per phase uses its default/conservative logic
    - **Advanced mode**: Multiple planners may be active, coordinator decides which to invoke

    Planner mapping:
    - **EntryDirective** → EntryPlanner: "Use this symbol, direction, timing preference"
    - **SizeDirective** → SizePlanner: "Use this aggressiveness, max risk"
    - **ExitDirective** → ExitPlanner: "Use this risk-reward ratio, stop tolerance"
    - **ExecutionDirective** → ExecutionPlanner: "Use this execution urgency, slippage limits"

    NOT RESPONSIBLE FOR:
    - Calculating exact entry prices (EntryPlanner's job)
    - Determining exact position sizes (SizePlanner's job)
    - Computing stop/target prices (ExitPlanner's job)
    - Choosing specific order types/routes (ExecutionPlanner's job)

    USAGE EXAMPLE 1 - NEW TRADE FROM SIGNAL:
    ```python
    # MomentumPlanner analyzes Signal
    directive = StrategyDirective(
        strategy_planner_id="momentum_planner",
        trigger_context=TriggerContext(
            signal_ids=["SIG_20251027_100001_a1b2c3d4"]
        ),
        scope=DirectiveScope.NEW_TRADE,
        confidence=Decimal("0.85"),
        # Sub-directives provide constraints to planners
        entry_directive=EntryDirective(
            symbol="BTC_USDT",
            direction="BUY",
            timing_preference=Decimal("0.9"),
            max_acceptable_slippage=Decimal("0.001")
        ),
        size_directive=SizeDirective(
            aggressiveness=Decimal("0.7"),
            max_risk_amount=Decimal("200.00"),
            account_risk_pct=Decimal("0.02")
        ),
        exit_directive=ExitDirective(
            profit_taking_preference=Decimal("0.3"),
            risk_reward_ratio=Decimal("3.0"),
            stop_loss_tolerance=Decimal("0.015")
        ),
        routing_directive=ExecutionDirective(
            execution_urgency=Decimal("0.8"),
            max_total_slippage_pct=Decimal("0.002")
        )
    )
    ```

    USAGE EXAMPLE 2 - MODIFY EXISTING FROM TICK (POSITION MANAGEMENT):
    ```python
    # TrailingStopPlanner monitors position via tick
    directive = StrategyDirective(
        strategy_planner_id="trailing_stop_planner",
        trigger_context=TriggerContext(
            monitored_position_ids=["POS_12345678-1234-1234-1234-123456789012"],
            trigger_tick={"symbol": "BTC_USDT", "price": Decimal("45000"), "timestamp": "..."}
        ),
        scope=DirectiveScope.MODIFY_EXISTING,
        target_plan_ids=["TPL_12345678-1234-1234-1234-123456789012"],
        confidence=Decimal("0.95"),
        # Only exit adjustment needed
        exit_directive=ExitDirective(
            profit_taking_preference=Decimal("0.8"),
            risk_reward_ratio=Decimal("2.0"),
            stop_loss_tolerance=Decimal("0.005")  # Tighter trailing stop
        )
    )
    ```

    USAGE EXAMPLE 3 - CLOSE EXISTING FROM RISK (RISK CONTROL):
    ```python
    # EmergencyExitPlanner responds to critical risk
    directive = StrategyDirective(
        strategy_planner_id="emergency_exit_planner",
        trigger_context=TriggerContext(
            risk_ids=["RSK_20251027_143001_v5w6x7y8"],
            trigger_event={"type": "FLASH_CRASH", "severity": "CRITICAL"}
        ),
        scope=DirectiveScope.CLOSE_EXISTING,
        target_plan_ids=["TPL_12345678-1234-1234-1234-123456789012"],
        confidence=Decimal("0.99"),
        # Only routing urgency needed for emergency exit
        routing_directive=ExecutionDirective(
            execution_urgency=Decimal("1.0"),  # Immediate market order
            max_total_slippage_pct=Decimal("0.05")  # Accept high slippage
        )
    )
    ```

    USAGE EXAMPLE 4 - NEW TRADE FROM SCHEDULE (SCHEDULED OPERATIONS):
    ```python
    # DCAPlanner executes on schedule
    directive = StrategyDirective(
        strategy_planner_id="dca_planner",
        trigger_context=TriggerContext(
            schedule_trigger={"frequency": "WEEKLY", "day": "MONDAY", "time": "10:00"}
        ),
        scope=DirectiveScope.NEW_TRADE,
        confidence=Decimal("0.80"),
        # DCA-specific constraints
        entry_directive=EntryDirective(
            symbol="BTC_USDT",
            direction="BUY",
            timing_preference=Decimal("0.3")  # Patient entry
        ),
        size_directive=SizeDirective(
            aggressiveness=Decimal("0.5"),
            max_risk_amount=Decimal("100.00")  # Fixed amount per DCA
        ),
        routing_directive=ExecutionDirective(
            execution_urgency=Decimal("0.2")  # Use limit orders
        )
    )
    ```

    CAUSALITY TRACKING VIA JOURNAL:
    ```python
    # Query Journal using trigger_context IDs
    journal_entries = StrategyJournal.query(
        signal_ids=directive.trigger_context.signal_ids,
        directive_id=directive.directive_id
    )
    # Reconstruct decision chain:
    # Signal → StrategyDirective → EntryPlan → ExecutionDirective
    ```

    Attributes:
        directive_id: Auto-generated unique directive ID (STR_ prefix)
        strategy_planner_id: ID of StrategyPlanner that produced this directive
        decision_timestamp: Auto-set UTC timestamp of directive creation
        trigger_context: Context of what triggered this directive (causality tracking)
        scope: Directive scope (NEW_TRADE, MODIFY_EXISTING, CLOSE_EXISTING)
        confidence: Confidence score [0.0-1.0] in this directive
        target_plan_ids: List of existing plan IDs (for MODIFY_EXISTING/CLOSE_EXISTING)
        entry_directive: Optional entry constraints for EntryPlanner
        size_directive: Optional sizing constraints for SizePlanner
        exit_directive: Optional exit constraints for ExitPlanner
        routing_directive: Optional routing constraints for ExecutionPlanner
    """

    directive_id: str = Field(
        default_factory=generate_strategy_directive_id,
        description="Auto-generated unique directive ID with STR_ prefix"
    )
    strategy_planner_id: str = Field(
        ...,
        description="ID of StrategyPlanner that produced this directive"
    )
    decision_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Auto-set UTC timestamp of directive creation"
    )
    causality: CausalityChain = Field(
        ...,
        description=(
            "Causality tracking - IDs from birth (tick/news/schedule) through "
            "worker outputs (signals, assessments) to this directive"
        )
    )
    scope: DirectiveScope = Field(
        ...,
        description="Directive scope: NEW_TRADE, MODIFY_EXISTING, or CLOSE_EXISTING"
    )
    confidence: Annotated[
        Decimal, Field(ge=Decimal("0.0"), le=Decimal("1.0"))
    ] = Field(
        ...,
        description=(
            "Confidence score [0.0-1.0] in this directive "
            "based on planner's analysis strength"
        )
    )
    target_plan_ids: list[str] = Field(
        default_factory=list,
        description=(
            "List of existing plan IDs to modify/close "
            "(for MODIFY_EXISTING/CLOSE_EXISTING scopes)"
        )
    )
    entry_directive: EntryDirective | None = Field(
        default=None,
        description=(
            "Optional entry constraints for EntryPlanner (used for NEW_TRADE)"
        )
    )
    size_directive: SizeDirective | None = Field(
        default=None,
        description=(
            "Optional sizing constraints for SizePlanner "
            "(used for NEW_TRADE/MODIFY_EXISTING)"
        )
    )
    exit_directive: ExitDirective | None = Field(
        default=None,
        description=(
            "Optional exit constraints for ExitPlanner "
            "(used for NEW_TRADE/MODIFY_EXISTING)"
        )
    )
    routing_directive: ExecutionDirective | None = Field(
        default=None,
        description=(
            "Optional routing constraints for ExecutionPlanner "
            "(used for all scopes)"
        )
    )
    execution_policy: ExecutionPolicy | None = Field(
        default=None,
        description=(
            "Optional execution coordination policy. "
            "Defines how multiple commands from this directive should be coordinated. "
            "Flows unchanged to ExecutionCommandBatch.mode. "
            "If None, defaults to INDEPENDENT (fire all, ignore failures)."
        )
    )

    @field_validator("target_plan_ids")
    @classmethod
    def validate_target_plan_ids_for_scope(cls, v: list[str], info: ValidationInfo) -> list[str]:
        """
        Validate target_plan_ids consistency with scope.

        For MODIFY_EXISTING and CLOSE_EXISTING, target_plan_ids must not be empty.
        For NEW_TRADE, target_plan_ids should be empty.
        """
        scope: DirectiveScope | None = info.data.get("scope")
        if scope in (DirectiveScope.MODIFY_EXISTING, DirectiveScope.CLOSE_EXISTING):
            if not v:
                # Type narrowing: scope is DirectiveScope here
                assert scope is not None
                raise ValueError(
                    f"target_plan_ids must not be empty for scope {scope.value}"
                )
        elif scope == DirectiveScope.NEW_TRADE:
            if v:
                raise ValueError(
                    "target_plan_ids must be empty for NEW_TRADE scope"
                )
        return v

    model_config = {
        "frozen": True,  # Immutable after creation - strategic decisions don't change
        "str_strip_whitespace": True,
        "json_schema_extra": {
            "examples": [
                {
                    "description": "New trade directive (full planning pipeline)",
                    "directive_id": "STR_20251027_100002_a1b2c3d4",
                    "decision_timestamp": "2025-10-27T10:00:02Z",
                    "strategy_planner_id": "signal_based_planner",
                    "scope": "NEW_TRADE",
                    "confidence": 0.85,
                    "causality": {
                        "origin": {"id": "TCK_20251027_100000_x1y2z3a4", "type": "TICK"},
                        "signal_ids": ["SIG_20251027_100001_b5c6d7e8"],
                        "strategy_directive_id": "STR_20251027_100002_a1b2c3d4"
                    },
                    "entry_directive": {
                        "symbol": "BTC_USDT",
                        "direction": "BUY",
                        "order_preference": "LIMIT"
                    },
                    "size_directive": {
                        "account_risk_pct": 0.01
                    },
                    "exit_directive": {
                        "risk_reward_ratio": 2.0
                    },
                    "routing_directive": {
                        "execution_urgency": 0.75,
                        "max_slippage_pct": 0.002
                    }
                },
                {
                    "description": "Modify existing trade directive (risk response)",
                    "directive_id": "STR_20251027_143002_j3k4l5m6",
                    "decision_timestamp": "2025-10-27T14:30:02Z",
                    "strategy_planner_id": "risk_response_planner",
                    "scope": "MODIFY_EXISTING",
                    "confidence": 0.92,
                    "target_plan_ids": ["TPL_20251027_100010_n7o8p9q0"],
                    "causality": {
                        "origin": {"id": "NWS_20251027_143000_r1s2t3u4", "type": "NEWS"},
                        "risk_ids": ["RSK_20251027_143001_v5w6x7y8"],
                        "strategy_directive_id": "STR_20251027_143002_j3k4l5m6"
                    },
                    "exit_directive": {
                        "stop_loss_price": "95000.00"
                    }
                },
                {
                    "description": "Close existing trade directive (exit signal)",
                    "directive_id": "STR_20251027_150003_d3e4f5g6",
                    "decision_timestamp": "2025-10-27T15:00:03Z",
                    "strategy_planner_id": "exit_signal_planner",
                    "scope": "CLOSE_EXISTING",
                    "confidence": 0.78,
                    "target_plan_ids": ["TPL_20251027_100010_h7i8j9k0"],
                    "causality": {
                        "origin": {"id": "TCK_20251027_150000_l1m2n3o4", "type": "TICK"},
                        "strategy_directive_id": "STR_20251027_150003_d3e4f5g6"
                    }
                }
            ]
        }
    }

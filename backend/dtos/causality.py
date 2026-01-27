# backend/dtos/causality.py
"""
CausalityChain - ID-only causality tracking DTO.

Verzamelt ALLEEN IDs voor Journal causality reconstruction in FlowTerminator.
Flows through entire pipeline, workers extend via model_copy(update={...}).

Design: Single Responsibility - NO business data, NO timestamps, ONLY IDs.

@layer: DTO (Domain Transfer Objects)
@dependencies: [pydantic]
"""

# Third-Party Imports
from pydantic import BaseModel, Field

# Our Application Imports
from backend.dtos.shared import Origin


class CausalityChain(BaseModel):
    """
    ID-only causality tracking container.

    Tracks the complete decision chain from birth (tick/news/schedule event)
    through all worker outputs (signals, assessments, directives, plans) for
    Journal reconstruction and audit trail.

    **Single Responsibility:** Collect ONLY IDs for causality reconstruction.

    **NOT responsible for:**
    - Business data (symbol, price, direction - those live in DTOs)
    - Timestamps (each DTO has own timestamp)
    - Confidence scores (Signal/StrategyDirective have that)
    - Event metadata (Risk/CriticalEvent have that)

    **Design Pattern:**
    Workers use model_copy(update={...}) to extend chain:
    ```python
    from backend.dtos.shared import Origin, OriginType

    # Origin copied from PlatformDataDTO
    extended = input_dto.causality.model_copy(update={
        "strategy_directive_id": "STR_20251026_100002_abc1d2e3"
    })
    output_dto.causality = extended
    ```

    **Origin Concept:**
    Every strategy run originates from platform data (copied from PlatformDataDTO):
    - TICK: Market tick data
    - NEWS: News event data
    - SCHEDULE: Scheduled event data

    Origin field is required and immutable (frozen).

    Attributes:
        origin: Origin reference copied from PlatformDataDTO (required, frozen)

        Worker Output IDs (added during pipeline flow):
            signal_ids: Signal IDs (list - multiple signals possible)
            risk_ids: Risk IDs (list - includes critical risk events)
            strategy_directive_id: StrategyDirective ID (planning bridge)
            entry_plan_id: EntryPlan ID
            size_plan_id: SizePlan ID
            exit_plan_id: ExitPlan ID
            execution_plan_id: ExecutionPlan ID (execution trade-offs)
            execution_directive_id: ExecutionDirective ID (final stage)
            order_ids: Order IDs (list - execution intent added by ExecutionHandler)
            fill_ids: Fill IDs (list - execution reality added by ExchangeConnector)
    """

    # === Origin (Platform Data Birth) ===
    origin: Origin = Field(
        description="Origin reference copied from PlatformDataDTO (TICK/NEWS/SCHEDULE)"
    )

    # === Worker Output IDs (Toegevoegd tijdens pipeline flow) ===
    signal_ids: list[str] = Field(
        default_factory=list,
        description="Signal IDs - multiple signals mogelijk (confluence)"
    )
    risk_ids: list[str] = Field(
        default_factory=list,
        description="Risk IDs (critical risk events)"
    )
    strategy_directive_id: str | None = Field(
        default=None,
        description="StrategyDirective ID - planning bridge"
    )
    entry_plan_id: str | None = Field(
        default=None,
        description="EntryPlan ID - entry execution plan"
    )
    size_plan_id: str | None = Field(
        default=None,
        description="SizePlan ID - position sizing plan"
    )
    exit_plan_id: str | None = Field(
        default=None,
        description="ExitPlan ID - exit/stop management plan"
    )
    execution_plan_id: str | None = Field(
        default=None,
        description="ExecutionPlan ID - execution trade-offs (HOW/WHEN)"
    )
    execution_command_id: str | None = Field(
        default=None,
        description="ExecutionCommand ID - final aggregated execution instruction"
    )
    order_ids: list[str] = Field(
        default_factory=list,
        description="Order IDs - execution intent (toegevoegd door ExecutionHandler)"
    )
    fill_ids: list[str] = Field(
        default_factory=list,
        description=(
            "Fill IDs - execution reality (toegevoegd door ExchangeConnector, "
            "kan verschillen van orders bij partial fills)"
        )
    )

    model_config = {
        "frozen": True,  # Immutable - origin field cannot be changed after creation
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Tick-based flow (origin TICK → signal → strategy)",
                    "origin": {"id": "TCK_20251109_100000_a1b2c3d4", "type": "TICK"},
                    "signal_ids": ["SIG_20251109_100001_e5f6g7h8"],
                    "strategy_directive_id": "STR_20251109_100002_m3n4o5p6"
                },
                {
                    "description": (
                        "Scheduled DCA flow (origin SCHEDULE → entry → size → execution)"
                    ),
                    "origin": {"id": "SCH_20251109_120000_q7r8s9t0", "type": "SCHEDULE"},
                    "strategy_directive_id": "STR_20251109_120001_u1v2w3x4",
                    "entry_plan_id": "ENT_20251109_120002_y5z6a7b8",
                    "size_plan_id": "SIZ_20251109_120003_c9d0e1f2",
                    "execution_command_id": "EXC_20251109_120010_g3h4i5j6"
                },
                {
                    "description": "Risk-based exit (origin NEWS → risk → modify directive)",
                    "origin": {"id": "NWS_20251109_143000_k7l8m9n0", "type": "NEWS"},
                    "risk_ids": ["RSK_20251109_143001_o1p2q3r4"],
                    "strategy_directive_id": "STR_20251109_143002_w9x0y1z2",
                    "exit_plan_id": "EXT_20251109_143003_a3b4c5d6"
                }
            ]
        }
    }

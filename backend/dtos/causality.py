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
from pydantic import BaseModel, Field, model_validator


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
    extended = input_dto.causality.model_copy(update={
        "strategy_directive_id": "STR_20251026_100002_abc1d2e3"
    })
    output_dto.causality = extended
    ```

    **Birth Concept:**
    Every strategy run "is born" at one of three events:
    - Market tick (tick_id)
    - News event (news_id)
    - Schedule event (schedule_id)

    At least one birth ID is required (enforced by validator).

    Attributes:
        Birth IDs (at least 1 required):
            tick_id: Market tick ID - strategy run born from market data
            news_id: News event ID - strategy run born from news
            schedule_id: Schedule event ID - strategy run born from DCA/rebalancing

        Worker Output IDs (added during pipeline flow):
            signal_ids: Signal IDs (list - multiple signals possible)
            risk_ids: Risk IDs (list - includes critical risk events)
            strategy_directive_id: StrategyDirective ID (planning bridge)
            entry_plan_id: EntryPlan ID
            size_plan_id: SizePlan ID
            exit_plan_id: ExitPlan ID
            execution_plan_id: ExecutionPlan ID (execution trade-offs)
            execution_directive_id: ExecutionDirective ID (final stage)
    """

    # === Birth IDs (Strategy Run Initiators) ===
    tick_id: str | None = Field(
        default=None,
        description="Market tick ID - strategy run geboren bij market data event"
    )
    news_id: str | None = Field(
        default=None,
        description="News event ID - strategy run geboren bij news event"
    )
    schedule_id: str | None = Field(
        default=None,
        description="Schedule event ID - strategy run geboren bij DCA/rebalancing schedule"
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
    execution_directive_id: str | None = Field(
        default=None,
        description="ExecutionDirective ID - final execution command"
    )

    @model_validator(mode='after')
    def validate_birth_id(self) -> 'CausalityChain':
        """
        Validate that at least one birth ID is present.

        Every strategy run must "be born" at tick/news/schedule event.

        Raises:
            ValueError: If all birth IDs are None
        """
        if not any([self.tick_id, self.news_id, self.schedule_id]):
            raise ValueError(
                "CausalityChain requires at least one birth ID "
                "(tick_id, news_id, or schedule_id)"
            )
        return self

    model_config = {
        "frozen": False,  # Mutable - workers extend via model_copy(update={...})
        "str_strip_whitespace": True,
        "validate_assignment": True,
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Tick-based flow (birth → signal → strategy)",
                    "tick_id": "TCK_20251027_100000_a1b2c3d4",
                    "signal_ids": ["SIG_20251027_100001_e5f6g7h8"],
                    "strategy_directive_id": "STR_20251027_100002_m3n4o5p6"
                },
                {
                    "description": "Scheduled DCA flow (schedule → entry → size → execution)",
                    "schedule_id": "SCH_20251027_120000_q7r8s9t0",
                    "strategy_directive_id": "STR_20251027_120001_u1v2w3x4",
                    "entry_plan_id": "ENT_20251027_120002_y5z6a7b8",
                    "size_plan_id": "SIZ_20251027_120003_c9d0e1f2",
                    "execution_directive_id": "EXE_20251027_120010_g3h4i5j6"
                },
                {
                    "description": "Risk-based exit (news → risk → modify directive)",
                    "news_id": "NWS_20251027_143000_k7l8m9n0",
                    "risk_ids": ["RSK_20251027_143001_o1p2q3r4"],
                    "strategy_directive_id": "STR_20251027_143002_w9x0y1z2",
                    "exit_plan_id": "EXT_20251027_143003_a3b4c5d6"
                },
                {
                    "description": "Multiple signals confluence (confluence → planning)",
                    "tick_id": "TCK_20251027_150000_e7f8g9h0",
                    "signal_ids": [
                        "SIG_20251027_150001_i1j2k3l4",
                        "SIG_20251027_150001_m5n6o7p8",
                        "SIG_20251027_150002_q9r0s1t2"
                    ],
                    "strategy_directive_id": "STR_20251027_150003_y7z8a9b0",
                    "entry_plan_id": "ENT_20251027_150004_c1d2e3f4",
                    "size_plan_id": "SIZ_20251027_150004_g5h6i7j8",
                    "exit_plan_id": "EXT_20251027_150005_k9l0m1n2",
                    "execution_plan_id": "EXP_20251027_150005_o3p4q5r6",
                    "execution_directive_id": "EXE_20251027_150010_s7t8u9v0"
                }
            ]
        }
    }

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
    - Confidence scores (OpportunitySignal/StrategyDirective have that)
    - Event metadata (ThreatSignal/CriticalEvent have that)

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
            opportunity_signal_ids: OpportunitySignal IDs (list - multiple signals possible)
            threat_ids: ThreatSignal IDs (list - includes CriticalEvent)
            context_assessment_id: AggregatedContextAssessment ID (SWOT context)
            strategy_directive_id: StrategyDirective ID (SWOT planning bridge)
            entry_plan_id: EntryPlan ID
            size_plan_id: SizePlan ID
            exit_plan_id: ExitPlan ID
            routing_plan_id: RoutingPlan ID
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
    opportunity_signal_ids: list[str] = Field(
        default_factory=list,
        description="OpportunitySignal IDs - multiple signals mogelijk (confluence)"
    )
    threat_ids: list[str] = Field(
        default_factory=list,
        description="ThreatSignal IDs (CriticalEvent = ThreatSignal in causality)"
    )
    context_assessment_id: str | None = Field(
        default=None,
        description="AggregatedContextAssessment ID (SWOT context)"
    )
    strategy_directive_id: str | None = Field(
        default=None,
        description="StrategyDirective ID - SWOT planning bridge"
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
    routing_plan_id: str | None = Field(
        default=None,
        description="RoutingPlan ID - broker routing plan"
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

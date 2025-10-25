# backend/dtos/strategy/opportunity_signal.py
"""
OpportunitySignal DTO: OpportunityWorker output contract.

Represents a detected trading opportunity in the SWOT analysis framework.
OpportunityWorkers emit OpportunitySignals to signal potential long/short
entries based on technical analysis patterns.

Part of SWOT framework:
- ContextWorkers → BaseContext (Strengths & Weaknesses)
- OpportunityWorkers → OpportunitySignal (Opportunities)
- ThreatWorkers → CriticalEvent (Threats)
- PlanningWorker → Confrontation Matrix (combines quadrants)

@layer: DTO (Strategy)
@dependencies: [pydantic, datetime, backend.utils.id_generators]
@responsibilities: [opportunity detection contract, causal tracking, SWOT confidence]
"""
import re

from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

from backend.utils.id_generators import generate_opportunity_id


class OpportunitySignal(BaseModel):
    """
    OpportunityWorker output DTO representing a detected trading opportunity.

    Fields:
        initiator_id: Flow initiator ID (TCK_/SCH_/NWS_/MAN_)
        opportunity_id: Unique opportunity ID (OPP_ prefix, auto-generated)
        timestamp: When the opportunity was detected (UTC)
        asset: Trading pair (BASE/QUOTE format)
        direction: Trading direction (long/short)
        signal_type: Type of signal (UPPER_SNAKE_CASE, 3-25 chars)
        confidence: Optional confidence [0.0, 1.0] for SWOT confrontation

    SWOT Framework:
        confidence (0.0-1.0) mirrors CriticalEvent.severity for mathematical
        confrontation in PlanningWorker's matrix analysis. This represents
        how confident the OpportunityWorker is about this opportunity.

        High confidence (e.g., 0.9) = strong technical setup
        Low confidence (e.g., 0.3) = weak or uncertain pattern

    Causal Chain:
        initiator_id → opportunity_id → (PlanningWorker decision)

    Pure Signal:
        This is a pattern detection event at a specific time/price.
        Entry planning (price, stops, sizing) happens in later stages.
        No trade_id yet - that's created by PlanningWorker if approved.

    Examples:
        >>> from backend.utils.id_generators import generate_tick_id
        >>> signal = OpportunitySignal(
        ...     initiator_id=generate_tick_id(),
        ...     timestamp=datetime.now(timezone.utc),
        ...     asset="BTC/EUR",
        ...     direction="long",
        ...     signal_type="FVG_ENTRY",
        ...     confidence=0.85
        ... )
    """

    initiator_id: str = Field(
        pattern=(
            r'^(TCK|SCH|NWS|MAN)_[0-9a-f]{8}-[0-9a-f]{4}-'
            r'[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        ),
        description="Typed ID of flow initiator"
    )

    opportunity_id: str = Field(
        default_factory=generate_opportunity_id,
        pattern=(
            r'^OPP_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-'
            r'[0-9a-f]{4}-[0-9a-f]{12}$'
        ),
        description="Typed opportunity ID"
    )

    timestamp: datetime = Field(
        description="When the opportunity was detected (UTC)"
    )

    asset: str = Field(
        min_length=5,
        max_length=20,
        pattern=r'^[A-Z0-9_]+/[A-Z0-9_]+$',
        description="Trading pair (BASE/QUOTE format)"
    )

    direction: Literal["long", "short"] = Field(
        description="Trading direction"
    )

    signal_type: str = Field(
        min_length=3,
        max_length=25,
        description="Type of signal (UPPER_SNAKE_CASE)"
    )

    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Opportunity confidence [0.0, 1.0] for SWOT confrontation",
    )

    @field_validator('signal_type')
    @classmethod
    def validate_signal_type_format(cls, v: str) -> str:
        """Validate UPPER_SNAKE_CASE format and reserved prefixes."""

        # Check reserved prefixes first
        reserved_prefixes = ['SYSTEM_', 'INTERNAL_', '_']
        if any(v.startswith(prefix) for prefix in reserved_prefixes):
            raise ValueError(
                f"signal_type cannot start with reserved prefix: {v}"
            )

        # Check UPPER_SNAKE_CASE pattern
        pattern = r'^[A-Z][A-Z0-9_]*$'
        if not re.match(pattern, v):
            raise ValueError(
                f"signal_type must follow UPPER_SNAKE_CASE: {v}"
            )

        return v

    @field_validator('timestamp')
    @classmethod
    def ensure_utc_timezone(cls, v: datetime) -> datetime:
        """Ensure timestamp is timezone-aware and in UTC."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    model_config = {
        "frozen": True,
        "extra": "forbid"
    }

# backend/dtos/strategy/signal.py
"""
Signal DTO: SignalDetector output contract.

Represents a detected trading signal based on technical analysis patterns.
SignalDetectors emit Signals to indicate potential long/short entry opportunities.

Signal Framework:
- ContextWorkers → Objective market context (indicators, regime, volatility)
- SignalDetectors → Signal (Entry/exit patterns)
- RiskMonitors → Risk (Portfolio/position risks)
- StrategyPlanners → Decision making (combines signals, risk, context)

@layer: DTO (Strategy)
@dependencies: [pydantic, datetime, backend.utils.id_generators, backend.dtos.causality]
@responsibilities: [signal detection contract, causal tracking, confidence scoring]
"""
import re

from datetime import datetime, timezone
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

from backend.utils.id_generators import generate_signal_id
from backend.dtos.causality import CausalityChain


class OpportunitySignal(BaseModel):
    """
    OpportunityWorker output DTO representing a detected trading opportunity.

    Fields:
        causality: CausalityChain - IDs from birth (tick/news/schedule)
        opportunity_id: Unique opportunity ID (OPP_ prefix, auto-generated)
        timestamp: When the opportunity was detected (UTC)
        asset: Trading pair (BASE/QUOTE format)
        direction: Trading direction (long/short)
        signal_type: Type of signal (UPPER_SNAKE_CASE, 3-25 chars)
        confidence: Optional confidence [0.0, 1.0] for SWOT confrontation

    SWOT Framework:
        confidence (0.0-1.0) mirrors ThreatSignal.severity for mathematical
        confrontation in PlanningWorker's matrix analysis. This represents
        how confident the OpportunityWorker is about this opportunity.

        High confidence (e.g., 0.9) = strong technical setup
        Low confidence (e.g., 0.3) = weak or uncertain pattern

    Causal Chain:
        CausalityChain birth ID → opportunity_id → (StrategyPlanner decision)

    Pure Signal:
        This is a pattern detection event at a specific time/price.
        Entry planning (price, stops, sizing) happens in later stages.
        No trade_id yet - that's created by PlanningWorker if approved.

    Examples:
        >>> signal = OpportunitySignal(
        ...     causality=CausalityChain(tick_id="TCK_20251026_100000_a1b2c3d4"),
        ...     timestamp=datetime.now(timezone.utc),
        ...     asset="BTC/EUR",
        ...     direction="long",
        ...     signal_type="FVG_ENTRY",
        ...     confidence=0.85
        ... )
    """

    causality: CausalityChain = Field(
        description="Causality tracking - IDs from birth (tick/news/schedule)"
    )

    signal_id: str = Field(
        default_factory=generate_signal_id,
        pattern=r'^SIG_\d{8}_\d{6}_[0-9a-f]{8}$',
        description="Typed signal ID (military datetime format)"
    )

    timestamp: datetime = Field(
        description="When the signal was detected (UTC)"
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
        description="Signal confidence [0.0, 1.0] for decision making",
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
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "description": "FVG breakout signal (LONG)",
                    "signal_id": "SIG_20251027_100001_a1b2c3d4",
                    "timestamp": "2025-10-27T10:00:01Z",
                    "asset": "BTCUSDT",
                    "direction": "LONG",
                    "signal_type": "FVG_BREAKOUT",
                    "confidence": 0.85
                },
                {
                    "description": "MSS reversal signal (SHORT)",
                    "signal_id": "SIG_20251027_143000_e5f6g7h8",
                    "timestamp": "2025-10-27T14:30:00Z",
                    "asset": "ETHUSDT",
                    "direction": "SHORT",
                    "signal_type": "MSS_REVERSAL",
                    "confidence": 0.72
                },
                {
                    "description": "High confidence breakout (no confidence defaults to None)",
                    "signal_id": "SIG_20251027_150500_i9j0k1l2",
                    "timestamp": "2025-10-27T15:05:00Z",
                    "asset": "SOLUSDT",
                    "direction": "LONG",
                    "signal_type": "TREND_CONTINUATION"
                }
            ]
        }
    }

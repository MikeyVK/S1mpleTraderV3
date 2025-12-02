# backend/dtos/strategy/signal.py
"""
Signal DTO: SignalDetector output contract.

Represents a detected trading signal based on technical analysis patterns.
SignalDetectors emit Signals to indicate potential long/short entry opportunities.

IMPORTANT: Signal is a PRE-CAUSALITY DTO.
- Signal represents a detection FACT at a specific point in time
- CausalityChain is created by StrategyPlanner (first post-causality component)
- Signal does NOT have a causality field

Signal Framework:
- ContextWorkers -> Objective market context (indicators, regime, volatility)
- SignalDetectors -> Signal (Entry/exit patterns) [THIS DTO]
- RiskMonitors -> Risk (Portfolio/position risks)
- StrategyPlanners -> Decision making (combines signals, risk, context)

@layer: DTO (Strategy)
@dependencies: [pydantic, datetime, decimal, backend.utils.id_generators]
@responsibilities: [signal detection contract, confidence scoring]
"""
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.utils.id_generators import generate_signal_id


class Signal(BaseModel):
    """
    SignalDetector output DTO representing a detected trading signal.

    This is a PRE-CAUSALITY DTO - it does NOT contain a causality field.
    CausalityChain is created by StrategyPlanner when it makes a decision.

    Fields:
        signal_id: Unique signal ID (SIG_ prefix, auto-generated)
        timestamp: When the signal was detected (UTC)
        symbol: Trading pair (UPPER_CASE with underscore, e.g., BTC_USDT)
        direction: Trading direction (long/short)
        signal_type: Type of signal (UPPER_SNAKE_CASE, 3-25 chars)
        confidence: Optional confidence [0.0, 1.0] for decision making (Decimal)

    Signal Framework:
        confidence (0.0-1.0) mirrors Risk.severity for balanced decision
        making in StrategyPlanner analysis. This represents how confident
        the SignalDetector is about this signal.

        High confidence (e.g., 0.9) = strong technical setup
        Low confidence (e.g., 0.3) = weak or uncertain pattern

    Pure Signal:
        This is a pattern detection event at a specific time/price.
        Entry planning (price, stops, sizing) happens in later stages.
        No trade_id yet - that's created by StrategyPlanner if approved.

    Examples:
        >>> from decimal import Decimal
        >>> signal = Signal(
        ...     timestamp=datetime.now(timezone.utc),
        ...     symbol="BTC_USDT",
        ...     direction="long",
        ...     signal_type="FVG_ENTRY",
        ...     confidence=Decimal("0.85")
        ... )
    """

    signal_id: str = Field(
        default_factory=generate_signal_id,
        pattern=r'^SIG_\d{8}_\d{6}_[0-9a-f]{8}$',
        description="Typed signal ID (military datetime format)"
    )

    timestamp: datetime = Field(
        description="When the signal was detected (UTC)"
    )

    symbol: str = Field(
        min_length=3,
        max_length=20,
        pattern=r'^[A-Z][A-Z0-9_]*$',
        description="Trading pair (UPPER_CASE format, e.g., BTC_USDT)"
    )

    direction: Literal["long", "short"] = Field(
        description="Trading direction"
    )

    signal_type: str = Field(
        min_length=3,
        max_length=25,
        description="Type of signal (UPPER_SNAKE_CASE)"
    )

    confidence: Decimal | None = Field(
        default=None,
        ge=Decimal("0.0"),
        le=Decimal("1.0"),
        description="Signal confidence [0.0, 1.0] for decision making (Decimal)",
    )

    @field_validator('confidence', mode='before')
    @classmethod
    def convert_to_decimal(cls, v: float | Decimal | str | None) -> Decimal | None:
        """Convert float/str input to Decimal for financial precision."""
        if v is None:
            return None
        if isinstance(v, Decimal):
            return v
        return Decimal(str(v))

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
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "description": "FVG breakout signal (LONG)",
                    "signal_id": "SIG_20251027_100001_a1b2c3d4",
                    "timestamp": "2025-10-27T10:00:01Z",
                    "symbol": "BTC_USDT",
                    "direction": "long",
                    "signal_type": "FVG_BREAKOUT",
                    "confidence": "0.85"
                },
                {
                    "description": "MSS reversal signal (SHORT)",
                    "signal_id": "SIG_20251027_143000_e5f6g7h8",
                    "timestamp": "2025-10-27T14:30:00Z",
                    "symbol": "ETH_USDT",
                    "direction": "short",
                    "signal_type": "MSS_REVERSAL",
                    "confidence": "0.72"
                },
                {
                    "description": "High confidence breakout (no confidence defaults to None)",
                    "signal_id": "SIG_20251027_150500_i9j0k1l2",
                    "timestamp": "2025-10-27T15:05:00Z",
                    "symbol": "SOL_USDC",
                    "direction": "long",
                    "signal_type": "TREND_CONTINUATION"
                }
            ]
        }
    }

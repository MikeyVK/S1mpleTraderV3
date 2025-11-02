# backend/dtos/strategy/risk.py
"""
Risk DTO: RiskMonitor output contract.

Represents a detected risk event requiring defensive action or awareness.
RiskMonitors emit Risk signals to indicate conditions that may threaten
portfolio health, position safety, or system stability.

Risk Framework:
- ContextWorkers → Objective market context (indicators, regime, volatility)
- SignalDetectors → Signal (Entry/exit patterns)
- RiskMonitors → Risk (Portfolio/position risks)
- StrategyPlanners → Decision making (combines signals, risk, context)

@layer: DTO (Strategy)
@dependencies: [pydantic, datetime, re, backend.utils.id_generators, backend.dtos.causality]
@responsibilities: [risk detection contract, causal tracking, severity scoring]
"""

from datetime import datetime, timezone
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from backend.utils.id_generators import generate_risk_id
from backend.dtos.causality import CausalityChain


class Risk(BaseModel):
    """
    RiskMonitor output DTO representing a detected risk.

    Fields:
        causality: CausalityChain - IDs from birth (tick/news/schedule)
        risk_id: Unique risk ID (RSK_ prefix, auto-generated)
        timestamp: When the risk was detected (UTC)
        risk_type: Type of risk (UPPER_SNAKE_CASE, 3-25 chars)
        severity: Risk severity [0.0, 1.0] for decision making
        affected_asset: Optional asset identifier (None = system-wide)

    Risk Framework:
        severity (0.0-1.0) mirrors Signal.confidence for balanced decision making
        in StrategyPlanner analysis. This represents how severe the risk is.

        High severity (e.g., 0.9) = critical risk requiring immediate action
        Low severity (e.g., 0.3) = minor concern or warning signal

    Causal Chain:
        CausalityChain birth ID → risk_id → (StrategyPlanner decision)

    System-Wide Scope:
        No trade_id reference - risks are system-level events.
        affected_asset=None signals system-wide impact (e.g., exchange down).

    Examples:
        >>> risk = Risk(
        ...     causality=CausalityChain(tick_id="TCK_20251026_100000_a1b2c3d4"),
        ...     timestamp=datetime.now(timezone.utc),
        ...     risk_type="STOP_LOSS_HIT",
        ...     severity=0.9,
        ...     affected_asset="BTC/EUR"
        ... )
    """

    causality: CausalityChain = Field(
        description="Causality tracking - IDs from birth (tick/news/schedule)"
    )

    risk_id: str = Field(
        default_factory=generate_risk_id,
        pattern=r'^RSK_\d{8}_\d{6}_[0-9a-f]{8}$',
        description="Unique risk ID (military datetime format)",
    )

    timestamp: datetime = Field(
        description="Risk detection time (UTC)",
    )

    risk_type: str = Field(
        description="Risk type identifier (UPPER_SNAKE_CASE, 3-25 chars)",
        min_length=3,
        max_length=25,
    )

    severity: float = Field(
        description="Risk severity [0.0, 1.0] for decision making",
        ge=0.0,
        le=1.0,
    )

    # Optional field - None indicates system-wide risk (not asset-specific)
    affected_asset: Optional[str] = Field(
        None,
        description="Affected asset (None = system-wide risk)",
        min_length=5,
        max_length=20,
        pattern=r'^[A-Z0-9_]+/[A-Z0-9_]+$',
    )

    model_config = {
        "frozen": True,
        "extra": "forbid",
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Market-wide risk (no specific asset)",
                    "risk_id": "RSK_20251027_100001_a1b2c3d4",
                    "timestamp": "2025-10-27T10:00:01Z",
                    "risk_type": "FLASH_CRASH",
                    "severity": 0.95
                },
                {
                    "description": "Asset-specific liquidity crisis",
                    "risk_id": "RSK_20251027_143000_e5f6g7h8",
                    "timestamp": "2025-10-27T14:30:00Z",
                    "risk_type": "LIQUIDITY_CRISIS",
                    "severity": 0.82,
                    "affected_asset": "BTCUSDT"
                },
                {
                    "description": "Regulatory news event (medium severity)",
                    "risk_id": "RSK_20251027_150500_i9j0k1l2",
                    "timestamp": "2025-10-27T15:05:00Z",
                    "risk_type": "REGULATORY_NEWS",
                    "severity": 0.65,
                    "affected_asset": "ETHUSDT"
                }
            ]
        }
    }

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc_timezone(cls, value: datetime) -> datetime:
        """Convert naive datetime to UTC-aware datetime."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @field_validator("risk_type")
    @classmethod
    def validate_risk_type_format(cls, v: str) -> str:
        """Validate UPPER_SNAKE_CASE format and reserved prefixes."""

        # Check reserved prefixes first
        reserved_prefixes = ['SYSTEM_', 'INTERNAL_', '_']
        if any(v.startswith(prefix) for prefix in reserved_prefixes):
            raise ValueError(
                f"risk_type cannot start with reserved prefix: {v}"
            )

        # Check UPPER_SNAKE_CASE pattern
        pattern = r'^[A-Z][A-Z0-9_]*$'
        if not re.match(pattern, v):
            raise ValueError(
                f"risk_type must follow UPPER_SNAKE_CASE: {v}"
            )

        return v

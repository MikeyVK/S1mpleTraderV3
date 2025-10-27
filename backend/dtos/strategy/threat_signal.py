# backend/dtos/strategy/threat_signal.py
"""
ThreatSignal DTO: ThreatWorker output contract.

Represents a detected threat/risk event in the SWOT analysis framework.
ThreatWorkers emit ThreatSignals to signal conditions requiring defensive
action or system-wide awareness.

Part of SWOT framework:
- ContextWorkers → BaseContext (Strengths & Weaknesses)
- OpportunityWorkers → OpportunitySignal (Opportunities)
- ThreatWorkers → ThreatSignal (Threats)
- PlanningWorker → Confrontation Matrix (combines quadrants)

@layer: DTO (Strategy)
@dependencies: [pydantic, datetime, re, backend.utils.id_generators, backend.dtos.causality]
@responsibilities: [threat detection contract, causal tracking, SWOT severity]
"""

from datetime import datetime, timezone
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from backend.utils.id_generators import generate_threat_id
from backend.dtos.causality import CausalityChain


class ThreatSignal(BaseModel):
    """
    ThreatWorker output DTO representing a detected threat.

    Fields:
        causality: CausalityChain - IDs from birth (tick/news/schedule)
        threat_id: Unique threat ID (THR_ prefix, auto-generated)
        timestamp: When the threat was detected (UTC)
        threat_type: Type of threat (UPPER_SNAKE_CASE, 3-25 chars)
        severity: Threat severity [0.0, 1.0] for SWOT confrontation
        affected_asset: Optional asset identifier (None = system-wide)

    SWOT Framework:
        severity (0.0-1.0) mirrors OpportunitySignal.confidence for
        mathematical confrontation in PlanningWorker's matrix analysis.
        This represents how severe the threat is.

        High severity (e.g., 0.9) = critical threat requiring immediate action
        Low severity (e.g., 0.3) = minor concern or warning signal

    Causal Chain:
        CausalityChain birth ID → threat_id → (StrategyPlanner decision)

    System-Wide Scope:
        No trade_id reference - threats are system-level events.
        affected_asset=None signals system-wide impact (e.g., exchange down).

    Examples:
        >>> signal = ThreatSignal(
        ...     causality=CausalityChain(tick_id="TCK_20251026_100000_a1b2c3d4"),
        ...     timestamp=datetime.now(timezone.utc),
        ...     threat_type="STOP_LOSS_HIT",
        ...     severity=0.9,
        ...     affected_asset="BTC/EUR"
        ... )
    """

    causality: CausalityChain = Field(
        description="Causality tracking - IDs from birth (tick/news/schedule)"
    )

    threat_id: str = Field(
        default_factory=generate_threat_id,
        pattern=r'^THR_\d{8}_\d{6}_[0-9a-f]{8}$',
        description="Unique threat ID (military datetime format)",
    )

    timestamp: datetime = Field(
        description="Threat detection time (UTC)",
    )

    threat_type: str = Field(
        description="Threat type identifier (UPPER_SNAKE_CASE, 3-25 chars)",
        min_length=3,
        max_length=25,
    )

    severity: float = Field(
        description="Threat severity [0.0, 1.0] for SWOT confrontation",
        ge=0.0,
        le=1.0,
    )

    # Optional field - None indicates system-wide threat (not asset-specific)
    affected_asset: Optional[str] = Field(
        None,
        description="Affected asset (None = system-wide threat)",
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
                    "description": "Market-wide threat (no specific asset)",
                    "threat_id": "THR_20251027_100001_a1b2c3d4",
                    "timestamp": "2025-10-27T10:00:01Z",
                    "threat_type": "FLASH_CRASH",
                    "severity": 0.95
                },
                {
                    "description": "Asset-specific liquidity crisis",
                    "threat_id": "THR_20251027_143000_e5f6g7h8",
                    "timestamp": "2025-10-27T14:30:00Z",
                    "threat_type": "LIQUIDITY_CRISIS",
                    "severity": 0.82,
                    "affected_asset": "BTCUSDT"
                },
                {
                    "description": "Regulatory news event (medium severity)",
                    "threat_id": "THR_20251027_150500_i9j0k1l2",
                    "timestamp": "2025-10-27T15:05:00Z",
                    "threat_type": "REGULATORY_NEWS",
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

    @field_validator("threat_type")
    @classmethod
    def validate_threat_type_format(cls, v: str) -> str:
        """Validate UPPER_SNAKE_CASE format and reserved prefixes."""

        # Check reserved prefixes first
        reserved_prefixes = ['SYSTEM_', 'INTERNAL_', '_']
        if any(v.startswith(prefix) for prefix in reserved_prefixes):
            raise ValueError(
                f"threat_type cannot start with reserved prefix: {v}"
            )

        # Check UPPER_SNAKE_CASE pattern
        pattern = r'^[A-Z][A-Z0-9_]*$'
        if not re.match(pattern, v):
            raise ValueError(
                f"threat_type must follow UPPER_SNAKE_CASE: {v}"
            )

        return v

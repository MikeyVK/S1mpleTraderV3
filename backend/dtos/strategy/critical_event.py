# backend/dtos/execution/critical_event.py
"""
CriticalEvent DTO: ThreatWorker output contract.

Represents a detected threat/risk event in the SWOT analysis framework.
ThreatWorkers emit CriticalEvents to signal conditions requiring defensive
action or system-wide awareness.

Part of SWOT framework:
- ContextWorkers → BaseContext (Strengths & Weaknesses)
- OpportunityWorkers → OpportunitySignal (Opportunities)
- ThreatWorkers → CriticalEvent (Threats)
- PlanningWorker → Confrontation Matrix (combines quadrants)

@layer: DTO (Execution)
@dependencies: [pydantic, datetime, re, backend.utils.id_generators]
@responsibilities: [threat detection contract, causal tracking, SWOT severity]
"""

from datetime import datetime, timezone
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from backend.utils.id_generators import generate_threat_id


class CriticalEvent(BaseModel):
    """
    ThreatWorker output DTO representing a detected threat.

    Fields:
        initiator_id: Flow initiator ID (TCK_/SCH_/NWS_/MAN_)
        threat_id: Unique threat ID (THR_ prefix, auto-generated)
        timestamp: When the threat was detected (UTC)
        threat_type: Type of threat (UPPER_SNAKE_CASE, 3-25 chars)
        severity: Threat severity [0.0, 1.0] for SWOT confrontation
        affected_asset: Optional asset identifier (None = system-wide)

    SWOT Framework:
        severity (0.0-1.0) mirrors OpportunitySignal.confidence for
        mathematical confrontation in PlanningWorker's matrix analysis.

    Causal Chain:
        initiator_id → threat_id → (PlanningWorker decision)

    System-Wide Scope:
        No trade_id reference - threats are system-level events.
        affected_asset=None signals system-wide impact (e.g., exchange down).
    """

    initiator_id: str = Field(
        ...,
        description="Flow initiator ID (TCK_/SCH_/NWS_/MAN_)",
    )

    threat_id: str = Field(
        default_factory=generate_threat_id,
        description="Unique threat ID (THR_ prefix)",
    )

    timestamp: datetime = Field(
        ...,
        description="Threat detection time (UTC)",
    )

    threat_type: str = Field(
        ...,
        description="Threat type identifier (UPPER_SNAKE_CASE, 3-25 chars)",
        min_length=3,
        max_length=25,
    )

    severity: float = Field(
        ...,
        description="Threat severity [0.0, 1.0] for SWOT confrontation",
        ge=0.0,
        le=1.0,
    )

    # Optional field - None indicates system-wide threat (not asset-specific)
    affected_asset: Optional[str] = Field(
        None,
        description="Affected asset (None = system-wide threat)",
        min_length=5,
    )

    model_config = {
        "frozen": True,
        "extra": "forbid",
    }

    @field_validator("timestamp", mode="before")
    @classmethod
    def ensure_utc_timezone(cls, value: datetime) -> datetime:
        """Convert naive datetime to UTC-aware datetime."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @field_validator("initiator_id")
    @classmethod
    def validate_initiator_id(cls, value: str) -> str:
        """Validate initiator_id has valid flow initiator prefix."""
        valid_prefixes = ("TCK_", "SCH_", "NWS_", "MAN_")
        if not any(value.startswith(prefix) for prefix in valid_prefixes):
            raise ValueError(
                f"initiator_id must start with {valid_prefixes}"
            )

        # Validate UUID format after prefix
        prefix_len = 4  # All prefixes are 4 chars
        uuid_part = value[prefix_len:]
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
            r"[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        if not uuid_pattern.match(uuid_part):
            raise ValueError(
                "initiator_id must be PREFIX_UUID format"
            )

        return value

    @field_validator("threat_id")
    @classmethod
    def validate_threat_id(cls, value: str) -> str:
        """Validate threat_id has THR_ prefix and UUID format."""
        if not value.startswith("THR_"):
            raise ValueError("threat_id must start with THR_")

        # Validate UUID format
        uuid_part = value[4:]  # Skip "THR_"
        uuid_pattern = re.compile(
            r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
            r"[0-9a-f]{4}-[0-9a-f]{12}$"
        )
        if not uuid_pattern.match(uuid_part):
            raise ValueError(
                "threat_id must be THR_UUID format"
            )

        return value

    @field_validator("threat_type")
    @classmethod
    def validate_threat_type(cls, value: str) -> str:
        """
        Validate threat_type format.

        Rules:
        - UPPER_SNAKE_CASE only
        - 3-25 characters (enforced by Field)
        - No reserved prefixes (SYSTEM_, INTERNAL_, _)
        """
        # Check reserved prefixes FIRST
        reserved_prefixes = ("SYSTEM_", "INTERNAL_", "_")
        if any(value.startswith(prefix) for prefix in reserved_prefixes):
            raise ValueError(
                f"threat_type cannot start with reserved prefix "
                f"{reserved_prefixes}"
            )

        # Then check pattern
        pattern = re.compile(r"^[A-Z][A-Z0-9_]*$")
        if not pattern.match(value):
            raise ValueError(
                "threat_type must be UPPER_SNAKE_CASE format"
            )

        return value

    @field_validator("affected_asset")
    @classmethod
    def validate_affected_asset(cls, value: Optional[str]) -> Optional[str]:
        """
        Validate affected_asset format if provided.

        Format: BASE/QUOTE or BASE_VARIANT/QUOTE
        Examples: BTC/EUR, ETH/USDT, BTC_PERP/USDT
        """
        if value is None:
            return None

        # Pattern: BASE/QUOTE with optional underscores in BASE
        pattern = re.compile(r"^[A-Z][A-Z0-9_]*/[A-Z][A-Z0-9]*$")
        if not pattern.match(value):
            raise ValueError(
                "affected_asset must be BASE/QUOTE format "
                "(e.g., BTC/EUR, BTC_PERP/USDT)"
            )

        return value

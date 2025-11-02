# backend/dtos/shared/disposition_envelope.py
"""
DispositionEnvelope DTO: Worker output flow control contract.

Standardized return type for all workers to communicate execution outcome
and next-step intentions to the EventAdapter. Enables event-driven flow
control without coupling workers to the EventBus.

Part of Platgeslagen Orkestratie architecture:
- Workers return DispositionEnvelope (CONTINUE/PUBLISH/STOP)
- EventAdapter interprets disposition and routes accordingly
- No direct worker-to-worker coupling or Operator layer needed

@layer: DTO (Shared)
@dependencies: [pydantic, typing, re]
@responsibilities: [flow control contract, event validation, TickCache routing]
"""

import re
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class DispositionEnvelope(BaseModel):
    """
    Worker output envelope for flow control and event routing.

    Fields:
        disposition: Flow control instruction (CONTINUE/PUBLISH/STOP)
        event_name: Event name for PUBLISH (UPPER_SNAKE_CASE, 3-100 chars)
        event_payload: Optional System DTO as event payload

    Dispositions:
        - CONTINUE: Continue flow, data placed in TickCache
        - PUBLISH: Publish event on EventBus with optional payload
        - STOP: Terminate this flow branch

    Architecture (Point-in-Time Data Model):
        - Flow data → TickCache (sync, plugin-specific DTOs)
        - Signals/alerts → EventBus (async, System DTOs)
        - DispositionEnvelope bridges worker logic and adapter routing

    Event Name Convention:
        - UPPER_SNAKE_CASE pattern required
        - Reserved prefixes blocked: SYSTEM_, INTERNAL_, _
        - Length: 3-100 characters

    Examples:
        >>> # Context worker continues flow
        >>> DispositionEnvelope(disposition="CONTINUE")

        >>> # Signal detector publishes signal with payload
        >>> from backend.dtos.strategy.signal import Signal
        >>> signal = Signal(...)
        >>> DispositionEnvelope(
        ...     disposition="PUBLISH",
        ...     event_name="SIGNAL_GENERATED",
        ...     event_payload=signal
        ... )

        >>> # Pure signal event (no payload needed)
        >>> DispositionEnvelope(
        ...     disposition="PUBLISH",
        ...     event_name="EMERGENCY_HALT"
        ... )

        >>> # Stop flow
        >>> DispositionEnvelope(disposition="STOP")
    """

    disposition: Literal["CONTINUE", "PUBLISH", "STOP"] = Field(
        default="CONTINUE",
        description="Flow control instruction for EventAdapter"
    )

    event_name: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=100,
        description="Event name for publication (required when disposition=PUBLISH)"
    )

    event_payload: Optional[BaseModel] = Field(
        default=None,
        description="Optional System DTO as event payload"
    )

    @field_validator("event_name")
    @classmethod
    def validate_event_name_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate event name follows UPPER_SNAKE_CASE convention.
        
        Event names must:
        - Use UPPER_SNAKE_CASE format (uppercase letters, digits, underscores)
        - Not use reserved prefixes: SYSTEM_, INTERNAL_, _
        - Be between 3 and 100 characters
        
        Args:
            v: Event name to validate
        
        Returns:
            Validated event name
        
        Raises:
            ValueError: If event name doesn't follow UPPER_SNAKE_CASE or uses reserved prefix
        """
        if v is None:
            return v

        # Check reserved prefixes first (before pattern check)
        reserved_prefixes = ("SYSTEM_", "INTERNAL_", "_")
        if any(v.startswith(prefix) for prefix in reserved_prefixes):
            raise ValueError(
                f"Event name cannot use reserved prefix (SYSTEM_, INTERNAL_, _): '{v}'"
            )

        # Check UPPER_SNAKE_CASE pattern
        pattern = r"^[A-Z][A-Z0-9_]*[A-Z0-9]$"
        if not re.match(pattern, v):
            raise ValueError(
                f"Event name must follow UPPER_SNAKE_CASE convention: '{v}'"
            )

        return v

    @model_validator(mode='after')
    def validate_publish_requirements(self) -> 'DispositionEnvelope':
        """Ensure PUBLISH disposition has event_name (payload is optional)."""
        if self.disposition == 'PUBLISH':
            if not self.event_name:
                raise ValueError(
                    "event_name is required when disposition='PUBLISH'"
                )
        return self

    model_config = {
        "frozen": True,  # Immutable after creation
        "extra": "forbid",  # No additional fields allowed
        "json_schema_extra": {
            "examples": [
                {
                    "description": "Context worker continues flow (data to TickCache)",
                    "disposition": "CONTINUE"
                },
                {
                    "description": (
                        "Signal detector publishes signal with DTO payload"
                    ),
                    "disposition": "PUBLISH",
                    "event_name": "SIGNAL_DETECTED",
                    "event_payload": (
                        "Signal(signal_id='SIG_...')"
                    )
                },
                {
                    "description": "Emergency halt (pure signal event, no payload)",
                    "disposition": "PUBLISH",
                    "event_name": "EMERGENCY_HALT"
                },
                {
                    "description": "Regime filter stops flow (conditions not met)",
                    "disposition": "STOP"
                }
            ]
        }
    }

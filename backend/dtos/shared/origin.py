# backend/dtos/shared/origin.py
"""
Origin DTO: Platform data origin tracking.

Type-safe reference for platform data sources (TICK/NEWS/SCHEDULE).
Used in PlatformDataDTO and CausalityChain for origin tracking.

@layer: DTO (Shared)
@dependencies: [pydantic, enum]
@responsibilities: [origin identity, type-safe reference, ID validation]
"""

from enum import Enum
from pydantic import BaseModel, model_validator


class OriginType(str, Enum):
    """Platform data origin types."""
    TICK = "TICK"
    NEWS = "NEWS"
    SCHEDULE = "SCHEDULE"


class Origin(BaseModel):
    """
    Platform data origin - type-safe reference.
    
    Attributes:
        id: Origin ID with type prefix (TCK_/NWS_/SCH_...)
        type: Origin type enum (TICK/NEWS/SCHEDULE)
        
    Examples:
        >>> # Tick data origin
        >>> origin = Origin(
        ...     id="TCK_20251109_143022_abc123",
        ...     type=OriginType.TICK
        ... )
        
        >>> # News data origin
        >>> origin = Origin(
        ...     id="NWS_20251109_143022_def456",
        ...     type=OriginType.NEWS
        ... )
    """
    
    id: str
    type: OriginType
    
    model_config = {"frozen": True}
    
    @model_validator(mode='after')
    def validate_id_prefix(self) -> 'Origin':
        """Validate ID prefix matches type."""
        prefix = self.id.split('_')[0]
        expected = {
            OriginType.TICK: "TCK",
            OriginType.NEWS: "NWS",
            OriginType.SCHEDULE: "SCH"
        }
        if prefix != expected[self.type]:
            raise ValueError(
                f"ID prefix '{prefix}' doesn't match type '{self.type.value}'"
            )
        return self

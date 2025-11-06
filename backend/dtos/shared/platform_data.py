# backend/dtos/shared/platform_data.py
"""
PlatformDataDTO - Data envelope for provider-to-strategy communication.

This DTO wraps platform data (candles, orderbook, news, etc.) from DataProviders
before delivery to FlowInitiator. It provides a consistent envelope structure
regardless of payload type.

@layer: DTOs (Shared)
@dependencies: [pydantic, datetime]
"""

# Standard Library Imports
from datetime import datetime

# Third-Party Imports
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlatformDataDTO(BaseModel):
    """
    Minimal data envelope for DataProvider → FlowInitiator communication.

    Wraps provider DTOs (CandleWindow, OrderBookSnapshot, etc.) with minimal
    metadata needed for cache initialization and type routing.

    Attributes:
        source_type: Provider type identifier for DTO type lookup (e.g., "candle_stream")
        timestamp: Point-in-time timestamp for RunAnchor initialization
        payload: Actual provider DTO (immutable BaseModel subtype)

    Example:
        >>> from datetime import datetime, timezone
        >>> candle_window = CandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        >>> platform_dto = PlatformDataDTO(
        ...     source_type="candle_stream",
        ...     timestamp=datetime.now(timezone.utc),
        ...     payload=candle_window
        ... )
    """

    source_type: str = Field(
        ...,
        description="Provider type identifier for DTO type lookup in ConfigTranslator",
        min_length=1
    )

    timestamp: datetime = Field(
        ...,
        description="Point-in-time timestamp used for cache.start_new_run(timestamp)"
    )

    payload: BaseModel = Field(
        ...,
        description="Provider DTO instance (CandleWindow, OrderBookSnapshot, etc.)"
    )

    @field_validator("source_type")
    @classmethod
    def validate_source_type_not_empty(cls, value: str) -> str:
        """Validate that source_type is not empty string."""
        if not value or not value.strip():
            raise ValueError("source_type cannot be empty")
        return value

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "examples": [
                {
                    "source_type": "candle_stream",
                    "timestamp": "2025-11-06T14:00:00Z",
                    "payload": {
                        "symbol": "BTC",
                        "timeframe": "1h",
                        "close": 50000.0
                    }
                }
            ]
        }
    )

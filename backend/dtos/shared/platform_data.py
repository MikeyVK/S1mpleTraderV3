# backend/dtos/shared/platform_data.py
"""
PlatformDataDTO - Data envelope for provider-to-strategy communication.

This DTO wraps platform data (candles, orderbook, news, etc.) from DataProviders
before delivery to FlowInitiator. It provides a consistent envelope structure
regardless of payload type.

@layer: DTOs (Shared)
@dependencies: [pydantic, datetime, backend.dtos.shared.origin]
"""

# Standard Library Imports
from datetime import datetime

# Third-Party Imports
from pydantic import BaseModel, ConfigDict, Field

# Our Application Imports
from backend.dtos.shared.origin import Origin, OriginType


class PlatformDataDTO(BaseModel):
    """
    Minimal data envelope for DataProvider → FlowInitiator communication.

    Wraps provider DTOs (CandleWindow, OrderBookSnapshot, etc.) with minimal
    metadata needed for cache initialization and type routing.

    Attributes:
        origin: Type-safe platform data origin (TICK/NEWS/SCHEDULE)
        timestamp: Point-in-time timestamp for RunAnchor initialization
        payload: Actual provider DTO (immutable BaseModel subtype)

    Example:
        >>> from datetime import datetime, timezone
        >>> from backend.dtos.shared.origin import Origin, OriginType
        >>> candle_window = CandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        >>> origin = Origin(id="TCK_20251109_143000_abc123", type=OriginType.TICK)
        >>> platform_dto = PlatformDataDTO(
        ...     origin=origin,
        ...     timestamp=datetime.now(timezone.utc),
        ...     payload=candle_window
        ... )
    """

    origin: Origin = Field(
        ...,
        description="Type-safe platform data origin (TICK/NEWS/SCHEDULE)"
    )

    timestamp: datetime = Field(
        ...,
        description="Point-in-time timestamp used for cache.start_new_run(timestamp)"
    )

    payload: BaseModel = Field(
        ...,
        description="Provider DTO instance (CandleWindow, OrderBookSnapshot, etc.)"
    )

    model_config = ConfigDict(
        frozen=True,
        json_schema_extra={
            "examples": [
                {
                    "origin": {
                        "id": "TCK_20251109_143000_abc123",
                        "type": "TICK"
                    },
                    "timestamp": "2025-11-09T14:30:00Z",
                    "payload": {
                        "symbol": "BTC",
                        "timeframe": "1h",
                        "close": 50000.0
                    }
                },
                {
                    "origin": {
                        "id": "NWS_20251109_150000_def456",
                        "type": "NEWS"
                    },
                    "timestamp": "2025-11-09T15:00:00Z",
                    "payload": {
                        "headline": "Fed announces rate decision",
                        "sentiment": "neutral"
                    }
                }
            ]
        }
    )

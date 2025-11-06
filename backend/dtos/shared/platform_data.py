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
from typing import Any, Dict, Optional

# Third-Party Imports
from pydantic import BaseModel, Field, field_validator


class PlatformDataDTO(BaseModel):
    """
    Data envelope for platform-to-strategy communication.
    
    DataProviders wrap their output in this envelope before publishing
    to FlowInitiator. The envelope provides consistent metadata while
    allowing flexible payload types.
    
    Attributes:
        source_type: Provider type identifier (e.g., "candle_stream", "orderbook_snapshot")
        timestamp: Point-in-time timestamp for this data (used as RunAnchor)
        payload: Actual data object (any BaseModel subtype)
        symbol: Optional symbol identifier (e.g., "BTC", "ETH")
        timeframe: Optional timeframe identifier (e.g., "1h", "4h")
        metadata: Optional additional context (latency, exchange, etc.)
    
    Example:
        >>> from datetime import datetime, timezone
        >>> candle_window = CandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        >>> platform_dto = PlatformDataDTO(
        ...     source_type="candle_stream",
        ...     timestamp=datetime.now(timezone.utc),
        ...     payload=candle_window,
        ...     symbol="BTC",
        ...     timeframe="1h"
        ... )
    """
    
    source_type: str = Field(
        ...,
        description="Provider type identifier (e.g., 'candle_stream', 'orderbook_snapshot')",
        min_length=1
    )
    
    timestamp: datetime = Field(
        ...,
        description="Point-in-time timestamp for this data (becomes RunAnchor)"
    )
    
    payload: BaseModel = Field(
        ...,
        description="Actual data object (must be BaseModel subtype)"
    )
    
    symbol: Optional[str] = Field(
        default=None,
        description="Optional symbol identifier (e.g., 'BTC', 'ETH')"
    )
    
    timeframe: Optional[str] = Field(
        default=None,
        description="Optional timeframe identifier (e.g., '1h', '4h')"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional additional context (latency, exchange, etc.)"
    )
    
    @field_validator("source_type")
    @classmethod
    def validate_source_type_not_empty(cls, value: str) -> str:
        """Validate that source_type is not empty string."""
        if not value or not value.strip():
            raise ValueError("source_type cannot be empty")
        return value
    
    class Config:
        """Pydantic configuration."""
        
        frozen = True  # Immutable after creation
        
        json_schema_extra = {
            "examples": [
                {
                    "source_type": "candle_stream",
                    "timestamp": "2025-11-06T14:00:00Z",
                    "payload": {
                        "symbol": "BTC",
                        "timeframe": "1h",
                        "close": 50000.0
                    },
                    "symbol": "BTC",
                    "timeframe": "1h"
                },
                {
                    "source_type": "orderbook_snapshot",
                    "timestamp": "2025-11-06T14:00:00Z",
                    "payload": {
                        "symbol": "ETH",
                        "bid_price": 3000.0,
                        "ask_price": 3001.0
                    },
                    "symbol": "ETH",
                    "metadata": {
                        "exchange": "binance",
                        "latency_ms": 12
                    }
                }
            ]
        }

# tests/unit/dtos/shared/test_platform_data.py
"""
Unit tests for PlatformDataDTO.

Tests the platform data envelope contract used by DataProviders to deliver
data to FlowInitiator according to TDD principles:
- Structure: source_type, timestamp, payload (required)
- Optional fields: symbol, timeframe, metadata
- Immutability: frozen=True enforced
- Nested payload: Any BaseModel subclass

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, backend.dtos.shared.platform_data]
"""

# Standard Library Imports
from datetime import datetime, timezone

# Third-Party Imports
import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

# Our Application Imports
from backend.dtos.shared.platform_data import PlatformDataDTO


class MockCandleWindow(BaseModel):
    """Mock CandleWindow DTO for testing payloads."""
    
    model_config = ConfigDict(frozen=True)
    
    symbol: str
    timeframe: str
    close: float


class MockOrderBookSnapshot(BaseModel):
    """Mock OrderBook DTO for testing payloads."""
    
    model_config = ConfigDict(frozen=True)
    
    symbol: str
    bid_price: float
    ask_price: float


class TestPlatformDataDTOCreation:
    """Test suite for PlatformDataDTO creation with valid data."""
    
    def test_create_with_required_fields_only(self):
        """Test creation with only required fields."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            payload=payload
        )
        
        assert dto.source_type == "candle_stream"
        assert dto.timestamp == timestamp
        assert dto.payload == payload
        assert dto.symbol is None
        assert dto.timeframe is None
        assert dto.metadata is None
    
    def test_create_with_all_fields(self):
        """Test creation with all optional fields populated."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        metadata = {"exchange": "binance", "latency_ms": 12}
        
        dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            symbol="BTC",
            timeframe="1h",
            payload=payload,
            metadata=metadata
        )
        
        assert dto.source_type == "candle_stream"
        assert dto.timestamp == timestamp
        assert dto.symbol == "BTC"
        assert dto.timeframe == "1h"
        assert dto.payload == payload
        assert dto.metadata == metadata
        assert dto.metadata is not None  # Type narrowing for Pylance
        assert dto.metadata["exchange"] == "binance"
    
    def test_create_with_different_payload_types(self):
        """Test that payload accepts different BaseModel types."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        
        # Test with CandleWindow payload
        candle_payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        candle_dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            payload=candle_payload
        )
        assert isinstance(candle_dto.payload, MockCandleWindow)
        
        # Test with OrderBook payload
        orderbook_payload = MockOrderBookSnapshot(
            symbol="ETH",
            bid_price=3000.0,
            ask_price=3001.0
        )
        orderbook_dto = PlatformDataDTO(
            source_type="orderbook_snapshot",
            timestamp=timestamp,
            payload=orderbook_payload
        )
        assert isinstance(orderbook_dto.payload, MockOrderBookSnapshot)


class TestPlatformDataDTOValidation:
    """Test suite for PlatformDataDTO field validation."""
    
    def test_missing_required_field_source_type(self):
        """Test that missing source_type raises ValidationError."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        with pytest.raises(ValidationError) as exc_info:
            PlatformDataDTO(
                # source_type missing!
                timestamp=timestamp,
                payload=payload
            )
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("source_type",) for error in errors)
    
    def test_missing_required_field_timestamp(self):
        """Test that missing timestamp raises ValidationError."""
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        with pytest.raises(ValidationError) as exc_info:
            PlatformDataDTO(
                source_type="candle_stream",
                # timestamp missing!
                payload=payload
            )
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("timestamp",) for error in errors)
    
    def test_missing_required_field_payload(self):
        """Test that missing payload raises ValidationError."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        
        with pytest.raises(ValidationError) as exc_info:
            PlatformDataDTO(
                source_type="candle_stream",
                timestamp=timestamp
                # payload missing!
            )
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("payload",) for error in errors)
    
    def test_invalid_timestamp_type(self):
        """Test that completely invalid timestamp type raises ValidationError."""
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        with pytest.raises(ValidationError) as exc_info:
            PlatformDataDTO(
                source_type="candle_stream",
                timestamp=[1, 2, 3],  # List instead of datetime!
                payload=payload
            )
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("timestamp",) for error in errors)
    
    def test_invalid_payload_type(self):
        """Test that non-BaseModel payload raises ValidationError."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        
        with pytest.raises(ValidationError) as exc_info:
            PlatformDataDTO(
                source_type="candle_stream",
                timestamp=timestamp,
                payload="not a basemodel"  # String instead of BaseModel!
            )
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("payload",) for error in errors)
    
    def test_empty_source_type(self):
        """Test that empty source_type raises ValidationError."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        with pytest.raises(ValidationError) as exc_info:
            PlatformDataDTO(
                source_type="",  # Empty string!
                timestamp=timestamp,
                payload=payload
            )
        
        errors = exc_info.value.errors()
        assert any(error["loc"] == ("source_type",) for error in errors)


class TestPlatformDataDTOImmutability:
    """Test suite for PlatformDataDTO immutability (frozen=True)."""
    
    def test_cannot_modify_source_type(self):
        """Test that source_type cannot be modified after creation."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            payload=payload
        )
        
        with pytest.raises(ValidationError):
            dto.source_type = "modified"
    
    def test_cannot_modify_timestamp(self):
        """Test that timestamp cannot be modified after creation."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            payload=payload
        )
        
        new_timestamp = datetime(2025, 11, 6, 15, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValidationError):
            dto.timestamp = new_timestamp
    
    def test_cannot_modify_payload(self):
        """Test that payload cannot be modified after creation."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            payload=payload
        )
        
        new_payload = MockCandleWindow(symbol="ETH", timeframe="4h", close=3000.0)
        with pytest.raises(ValidationError):
            dto.payload = new_payload
    
    def test_cannot_modify_optional_fields(self):
        """Test that optional fields cannot be modified after creation."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            symbol="BTC",
            timeframe="1h",
            payload=payload
        )
        
        with pytest.raises(ValidationError):
            dto.symbol = "ETH"
        
        with pytest.raises(ValidationError):
            dto.timeframe = "4h"


class TestPlatformDataDTOMetadata:
    """Test suite for PlatformDataDTO metadata field."""
    
    def test_metadata_none_by_default(self):
        """Test that metadata defaults to None."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            payload=payload
        )
        
        assert dto.metadata is None
    
    def test_metadata_accepts_dict(self):
        """Test that metadata accepts dict values."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        metadata = {
            "exchange": "binance",
            "latency_ms": 12,
            "data_source": "websocket"
        }
        
        dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            payload=payload,
            metadata=metadata
        )
        
        assert dto.metadata is not None
        assert dto.metadata["exchange"] == "binance"
        assert dto.metadata["latency_ms"] == 12
    
    def test_metadata_empty_dict(self):
        """Test that metadata accepts empty dict."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            payload=payload,
            metadata={}
        )
        
        assert dto.metadata == {}


class TestPlatformDataDTOEdgeCases:
    """Test suite for PlatformDataDTO edge cases and boundaries."""
    
    def test_source_type_with_special_characters(self):
        """Test source_type with underscores and numbers."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        dto = PlatformDataDTO(
            source_type="candle_stream_v2_btc_eth",
            timestamp=timestamp,
            payload=payload
        )
        
        assert dto.source_type == "candle_stream_v2_btc_eth"
    
    def test_timestamp_with_microseconds(self):
        """Test timestamp with microsecond precision."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, 123456, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            payload=payload
        )
        
        assert dto.timestamp.microsecond == 123456
    
    def test_symbol_none_explicitly_set(self):
        """Test that symbol can be explicitly set to None."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        
        dto = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp,
            payload=payload,
            symbol=None
        )
        
        assert dto.symbol is None
    
    def test_multiple_instances_independent(self):
        """Test that multiple PlatformDataDTO instances are independent."""
        timestamp1 = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        timestamp2 = datetime(2025, 11, 6, 15, 0, 0, tzinfo=timezone.utc)
        
        payload1 = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        payload2 = MockCandleWindow(symbol="ETH", timeframe="4h", close=3000.0)
        
        dto1 = PlatformDataDTO(
            source_type="candle_stream",
            timestamp=timestamp1,
            payload=payload1,
            symbol="BTC"
        )
        
        dto2 = PlatformDataDTO(
            source_type="orderbook_snapshot",
            timestamp=timestamp2,
            payload=payload2,
            symbol="ETH"
        )
        
        assert dto1.source_type != dto2.source_type
        assert dto1.timestamp != dto2.timestamp
        assert dto1.payload != dto2.payload
        assert dto1.symbol != dto2.symbol

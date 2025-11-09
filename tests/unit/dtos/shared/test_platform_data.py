# tests/unit/dtos/shared/test_platform_data.py
"""
Unit tests for PlatformDataDTO.

Tests the minimal data envelope contract between DataProviders and FlowInitiator.
Focus on essential behavior: structure, immutability, validation.

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
from backend.dtos.shared.origin import Origin, OriginType


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


def create_test_origin(origin_type: OriginType = OriginType.TICK) -> Origin:
    """Helper to create test Origin instances."""
    type_map = {
        OriginType.TICK: "TCK_20251109_143000_abc123",
        OriginType.NEWS: "NWS_20251109_143000_def456",
        OriginType.SCHEDULE: "SCH_20251109_143000_ghi789"
    }
    return Origin(id=type_map[origin_type], type=origin_type)


class TestPlatformDataDTOStructure:
    """Test DTO structure with required fields only."""

    def test_create_with_all_required_fields(self):
        """Test successful creation with origin, timestamp, payload."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        origin = create_test_origin(OriginType.TICK)

        dto = PlatformDataDTO(
            origin=origin,
            timestamp=timestamp,
            payload=payload
        )

        assert dto.origin == origin
        assert dto.timestamp == timestamp
        assert dto.payload == payload

    def test_different_payload_types(self):
        """Test payload accepts any BaseModel subtype."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        origin = create_test_origin(OriginType.TICK)

        # CandleWindow payload
        candle_dto = PlatformDataDTO(
            origin=origin,
            timestamp=timestamp,
            payload=MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        )
        assert isinstance(candle_dto.payload, MockCandleWindow)

        # OrderBook payload
        orderbook_dto = PlatformDataDTO(
            origin=create_test_origin(OriginType.NEWS),
            timestamp=timestamp,
            payload=MockOrderBookSnapshot(symbol="ETH", bid_price=3000.0, ask_price=3001.0)
        )
        assert isinstance(orderbook_dto.payload, MockOrderBookSnapshot)


class TestPlatformDataDTOValidation:
    """Test field validation for required fields."""

    def test_missing_origin(self):
        """Test that missing origin raises ValidationError."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)

        with pytest.raises(ValidationError) as exc_info:
            PlatformDataDTO(timestamp=timestamp, payload=payload)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("origin",) for error in errors)

    def test_missing_timestamp(self):
        """Test that missing timestamp raises ValidationError."""
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        origin = create_test_origin()

        with pytest.raises(ValidationError) as exc_info:
            PlatformDataDTO(origin=origin, payload=payload)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("timestamp",) for error in errors)

    def test_missing_payload(self):
        """Test that missing payload raises ValidationError."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        origin = create_test_origin()

        with pytest.raises(ValidationError) as exc_info:
            PlatformDataDTO(origin=origin, timestamp=timestamp)

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("payload",) for error in errors)

    def test_invalid_timestamp_type(self):
        """Test that invalid timestamp type raises ValidationError."""
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        origin = create_test_origin()

        with pytest.raises(ValidationError) as exc_info:
            PlatformDataDTO(
                origin=origin,
                timestamp=[1, 2, 3],  # type: ignore
                payload=payload
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("timestamp",) for error in errors)

    def test_invalid_payload_type(self):
        """Test that non-BaseModel payload raises ValidationError."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        origin = create_test_origin()

        with pytest.raises(ValidationError) as exc_info:
            PlatformDataDTO(
                origin=origin,
                timestamp=timestamp,
                payload="not_a_basemodel"  # type: ignore
            )

        errors = exc_info.value.errors()
        assert any(error["loc"] == ("payload",) for error in errors)


class TestPlatformDataDTOImmutability:
    """Test frozen=True enforcement."""

    def test_cannot_modify_origin(self):
        """Test that origin cannot be modified after creation."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        origin = create_test_origin(OriginType.TICK)
        dto = PlatformDataDTO(
            origin=origin,
            timestamp=timestamp,
            payload=payload
        )

        new_origin = create_test_origin(OriginType.NEWS)
        with pytest.raises(ValidationError, match="frozen"):
            dto.origin = new_origin  # type: ignore

    def test_cannot_modify_timestamp(self):
        """Test that timestamp cannot be modified after creation."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        origin = create_test_origin()
        dto = PlatformDataDTO(
            origin=origin,
            timestamp=timestamp,
            payload=payload
        )

        new_timestamp = datetime(2025, 11, 6, 15, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValidationError, match="frozen"):
            dto.timestamp = new_timestamp  # type: ignore

    def test_cannot_modify_payload(self):
        """Test that payload cannot be modified after creation."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        origin = create_test_origin()
        dto = PlatformDataDTO(
            origin=origin,
            timestamp=timestamp,
            payload=payload
        )

        new_payload = MockCandleWindow(symbol="ETH", timeframe="4h", close=3000.0)
        with pytest.raises(ValidationError, match="frozen"):
            dto.payload = new_payload  # type: ignore


class TestPlatformDataDTOEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_different_origin_types(self):
        """Test that all origin types work correctly."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)

        for origin_type in [OriginType.TICK, OriginType.NEWS, OriginType.SCHEDULE]:
            origin = create_test_origin(origin_type)
            dto = PlatformDataDTO(
                origin=origin,
                timestamp=timestamp,
                payload=payload
            )
            assert dto.origin.type == origin_type

    def test_timestamp_with_microseconds(self):
        """Test timestamp preserves microsecond precision."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, 123456, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        origin = create_test_origin()

        dto = PlatformDataDTO(
            origin=origin,
            timestamp=timestamp,
            payload=payload
        )

        assert dto.timestamp.microsecond == 123456

    def test_multiple_instances_independent(self):
        """Test multiple DTO instances are independent (frozen enforcement)."""
        timestamp = datetime(2025, 11, 6, 14, 0, 0, tzinfo=timezone.utc)
        payload1 = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        payload2 = MockCandleWindow(symbol="ETH", timeframe="4h", close=3000.0)

        dto1 = PlatformDataDTO(
            origin=create_test_origin(OriginType.TICK),
            timestamp=timestamp,
            payload=payload1
        )
        dto2 = PlatformDataDTO(
            origin=create_test_origin(OriginType.NEWS),
            timestamp=timestamp,
            payload=payload2
        )

        assert dto1.origin.type != dto2.origin.type
        assert dto1.payload != dto2.payload


class TestPlatformDataDTOOriginIntegration:
    """Test Origin DTO integration for type-safe origin tracking."""

    def test_create_with_tick_origin(self):
        """Test PlatformDataDTO with TICK origin."""
        timestamp = datetime(2025, 11, 9, 14, 30, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        origin = Origin(id="TCK_20251109_143000_abc123", type=OriginType.TICK)

        dto = PlatformDataDTO(
            origin=origin,
            timestamp=timestamp,
            payload=payload
        )

        assert dto.origin == origin
        assert dto.origin.type == OriginType.TICK
        assert dto.origin.id == "TCK_20251109_143000_abc123"

    def test_create_with_news_origin(self):
        """Test PlatformDataDTO with NEWS origin."""
        timestamp = datetime(2025, 11, 9, 14, 30, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        origin = Origin(id="NWS_20251109_143000_def456", type=OriginType.NEWS)

        dto = PlatformDataDTO(
            origin=origin,
            timestamp=timestamp,
            payload=payload
        )

        assert dto.origin == origin
        assert dto.origin.type == OriginType.NEWS

    def test_create_with_schedule_origin(self):
        """Test PlatformDataDTO with SCHEDULE origin."""
        timestamp = datetime(2025, 11, 9, 14, 30, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        origin = Origin(id="SCH_20251109_143000_ghi789", type=OriginType.SCHEDULE)

        dto = PlatformDataDTO(
            origin=origin,
            timestamp=timestamp,
            payload=payload
        )

        assert dto.origin == origin
        assert dto.origin.type == OriginType.SCHEDULE

    def test_origin_is_required(self):
        """Test that origin field is required (cannot be None)."""
        timestamp = datetime(2025, 11, 9, 14, 30, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)

        with pytest.raises(ValidationError, match="origin"):
            PlatformDataDTO(
                timestamp=timestamp,
                payload=payload
            )

    def test_origin_immutability(self):
        """Test that origin cannot be modified after creation."""
        timestamp = datetime(2025, 11, 9, 14, 30, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)
        origin = Origin(id="TCK_20251109_143000_abc123", type=OriginType.TICK)

        dto = PlatformDataDTO(
            origin=origin,
            timestamp=timestamp,
            payload=payload
        )

        new_origin = Origin(id="NWS_20251109_143000_def456", type=OriginType.NEWS)
        with pytest.raises((ValidationError, AttributeError)):
            dto.origin = new_origin  # type: ignore

    def test_origin_validation_enforced(self):
        """Test that Origin validation rules are enforced."""
        timestamp = datetime(2025, 11, 9, 14, 30, 0, tzinfo=timezone.utc)
        payload = MockCandleWindow(symbol="BTC", timeframe="1h", close=50000.0)

        # Invalid: wrong prefix for type
        with pytest.raises(ValidationError):
            origin = Origin(id="NWS_20251109_143000_abc123", type=OriginType.TICK)
            PlatformDataDTO(
                origin=origin,
                timestamp=timestamp,
                payload=payload
            )


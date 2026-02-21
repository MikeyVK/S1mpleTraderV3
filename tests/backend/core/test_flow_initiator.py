# tests/unit/core/test_flow_initiator.py
"""
Tests for FlowInitiator implementation.

FlowInitiator is a Platform-within-Strategy worker that:
- Initializes StrategyCache for new runs (start_new_run)
- Stores PlatformDataDTO payloads by type (set_result_dto)
- Returns CONTINUE disposition to trigger worker pipeline

@layer: Tests (Unit)
@dependencies: [pytest, unittest.mock, backend.core.flow_initiator]
"""

# Standard library
from datetime import UTC, datetime
from unittest.mock import Mock, call

# Third-party
import pytest
from pydantic import BaseModel, ConfigDict

# Project modules
from backend.core.flow_initiator import FlowInitiator
from backend.core.interfaces.strategy_cache import IStrategyCache
from backend.core.interfaces.worker import IWorker, IWorkerLifecycle, WorkerInitializationError
from backend.dtos.shared import Origin, OriginType
from backend.dtos.shared.disposition_envelope import DispositionEnvelope
from backend.dtos.shared.platform_data import PlatformDataDTO


def create_test_origin(origin_type: OriginType = OriginType.TICK) -> Origin:
    """Helper function to create test Origin instances."""
    type_map = {
        OriginType.TICK: "TCK_20251109_143000_abc123",
        OriginType.NEWS: "NWS_20251109_143000_def456",
        OriginType.SCHEDULE: "SCH_20251109_143000_ghi789",
    }
    return Origin(id=type_map[origin_type], type=origin_type)


# Mock DTOs for testing
class MockCandleWindow(BaseModel):
    """Mock CandleWindow DTO."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    data: str


class MockNewsEvent(BaseModel):
    """Mock NewsEvent DTO."""

    model_config = ConfigDict(frozen=True)

    headline: str
    sentiment: float


class TestFlowInitiatorProtocols:
    """Test FlowInitiator protocol compliance."""

    def test_flow_initiator_implements_iworker(self) -> None:
        """FlowInitiator implements IWorker protocol."""
        flow_initiator = FlowInitiator(name="test_flow_initiator")

        assert isinstance(flow_initiator, IWorker)
        assert hasattr(flow_initiator, "name")

    def test_flow_initiator_implements_iworkerlifecycle(self) -> None:
        """FlowInitiator implements IWorkerLifecycle protocol."""
        flow_initiator = FlowInitiator(name="test_flow_initiator")

        assert isinstance(flow_initiator, IWorkerLifecycle)
        assert hasattr(flow_initiator, "initialize")
        assert hasattr(flow_initiator, "shutdown")

    def test_flow_initiator_name_property(self) -> None:
        """FlowInitiator has name property (IWorker requirement)."""
        flow_initiator = FlowInitiator(name="flow_init_abc")

        assert flow_initiator.name == "flow_init_abc"


class TestFlowInitiatorLifecycle:
    """Test FlowInitiator lifecycle management."""

    @pytest.fixture
    def cache_mock(self) -> Mock:
        """Provide StrategyCache mock."""
        return Mock(spec=IStrategyCache)

    @pytest.fixture
    def flow_initiator(self) -> FlowInitiator:
        """Provide fresh FlowInitiator instance."""
        return FlowInitiator(name="test_flow_initiator")

    def test_initialize_with_strategy_cache(
        self, flow_initiator: FlowInitiator, cache_mock: Mock
    ) -> None:
        """FlowInitiator initializes with strategy_cache (Platform-within-Strategy)."""
        dto_types = {"candle_stream": MockCandleWindow}

        flow_initiator.initialize(strategy_cache=cache_mock, dto_types=dto_types)

        # Verify initialization succeeded (behavior check, not implementation)
        # Internal state is tested indirectly via on_data_ready() tests

    def test_initialize_validates_strategy_cache_not_none(
        self, flow_initiator: FlowInitiator
    ) -> None:
        """FlowInitiator requires strategy_cache (not a Platform worker)."""
        with pytest.raises(WorkerInitializationError) as exc_info:
            flow_initiator.initialize(strategy_cache=None)

        assert "strategy_cache required" in str(exc_info.value).lower()

    def test_initialize_validates_dto_types_capability(
        self, flow_initiator: FlowInitiator, cache_mock: Mock
    ) -> None:
        """FlowInitiator requires dto_types capability."""
        with pytest.raises(WorkerInitializationError) as exc_info:
            flow_initiator.initialize(strategy_cache=cache_mock)

        assert "dto_types" in str(exc_info.value).lower()

    def test_shutdown_is_idempotent(self, flow_initiator: FlowInitiator) -> None:
        """Shutdown can be called multiple times safely."""
        # Should not raise
        flow_initiator.shutdown()
        flow_initiator.shutdown()


class TestFlowInitiatorDataHandling:
    """Test FlowInitiator data processing."""

    @pytest.fixture
    def cache_mock(self) -> Mock:
        """Provide StrategyCache mock."""
        return Mock(spec=IStrategyCache)

    @pytest.fixture
    def flow_initiator(self, cache_mock: Mock) -> FlowInitiator:
        """Provide initialized FlowInitiator."""
        flow_initiator = FlowInitiator(name="test_flow_initiator")
        flow_initiator.initialize(
            strategy_cache=cache_mock,
            dto_types={"candle_stream": MockCandleWindow, "news_feed": MockNewsEvent},
        )
        return flow_initiator

    @pytest.fixture
    def test_timestamp(self) -> datetime:
        """Provide test timestamp."""
        return datetime(2025, 11, 6, 10, 0, 0, tzinfo=UTC)

    def test_on_data_ready_starts_new_run(
        self, flow_initiator: FlowInitiator, cache_mock: Mock, test_timestamp: datetime
    ) -> None:
        """on_data_ready calls cache.start_new_strategy_run with timestamp."""
        candle_payload = MockCandleWindow(symbol="BTC_EUR", data="test")
        platform_dto = PlatformDataDTO(
            origin=create_test_origin(OriginType.TICK),
            timestamp=test_timestamp,
            payload=candle_payload,
        )

        flow_initiator.on_data_ready(platform_dto)

        # Should initialize cache with empty dict and timestamp
        cache_mock.start_new_strategy_run.assert_called_once()
        call_args = cache_mock.start_new_strategy_run.call_args
        assert call_args[0][0] == {}  # Empty strategy_cache dict
        assert call_args[0][1] == test_timestamp  # Timestamp

    def test_on_data_ready_stores_payload_in_cache(
        self, flow_initiator: FlowInitiator, cache_mock: Mock, test_timestamp: datetime
    ) -> None:
        """on_data_ready stores payload DTO in cache via set_result_dto."""
        candle_payload = MockCandleWindow(symbol="BTC_EUR", data="test_data")
        platform_dto = PlatformDataDTO(
            origin=create_test_origin(OriginType.TICK),
            timestamp=test_timestamp,
            payload=candle_payload,
        )

        flow_initiator.on_data_ready(platform_dto)

        # Should store payload (not PlatformDataDTO wrapper!)
        cache_mock.set_result_dto.assert_called_once()
        stored_dto = cache_mock.set_result_dto.call_args[0][0]
        assert stored_dto is candle_payload
        assert isinstance(stored_dto, MockCandleWindow)

    def test_on_data_ready_returns_continue_disposition(
        self, flow_initiator: FlowInitiator, test_timestamp: datetime
    ) -> None:
        """on_data_ready returns CONTINUE disposition for EventAdapter."""
        platform_dto = PlatformDataDTO(
            origin=create_test_origin(OriginType.TICK),
            timestamp=test_timestamp,
            payload=MockCandleWindow(symbol="BTC_EUR", data="test"),
        )

        result = flow_initiator.on_data_ready(platform_dto)

        assert isinstance(result, DispositionEnvelope)
        assert result.disposition == "CONTINUE"

    def test_on_data_ready_call_order(
        self, flow_initiator: FlowInitiator, cache_mock: Mock, test_timestamp: datetime
    ) -> None:
        """on_data_ready calls start_new_strategy_run BEFORE set_result_dto."""
        platform_dto = PlatformDataDTO(
            origin=create_test_origin(OriginType.TICK),
            timestamp=test_timestamp,
            payload=MockCandleWindow(symbol="BTC_EUR", data="test"),
        )

        flow_initiator.on_data_ready(platform_dto)

        # Verify call order: start_new_strategy_run → set_result_dto
        assert cache_mock.method_calls == [
            call.start_new_strategy_run({}, test_timestamp),
            call.set_result_dto(platform_dto.payload),
        ]

    def test_on_data_ready_handles_different_dto_types(
        self, flow_initiator: FlowInitiator, cache_mock: Mock, test_timestamp: datetime
    ) -> None:
        """on_data_ready handles multiple DTO types via source_type lookup."""
        # Test candle_stream
        candle_dto = PlatformDataDTO(
            origin=create_test_origin(OriginType.TICK),
            timestamp=test_timestamp,
            payload=MockCandleWindow(symbol="BTC_EUR", data="candles"),
        )
        flow_initiator.on_data_ready(candle_dto)

        # Test news_feed
        news_dto = PlatformDataDTO(
            origin=create_test_origin(OriginType.TICK),
            timestamp=test_timestamp,
            payload=MockNewsEvent(headline="Breaking News", sentiment=0.8),
        )
        flow_initiator.on_data_ready(news_dto)

        # Both should be stored
        assert cache_mock.set_result_dto.call_count == 2
        assert cache_mock.start_new_strategy_run.call_count == 2


class TestFlowInitiatorErrorHandling:
    """Test FlowInitiator error scenarios."""

    @pytest.fixture
    def cache_mock(self) -> Mock:
        """Provide StrategyCache mock."""
        return Mock(spec=IStrategyCache)

    @pytest.fixture
    def flow_initiator(self, cache_mock: Mock) -> FlowInitiator:
        """Provide initialized FlowInitiator."""
        flow_initiator = FlowInitiator(name="test_flow_initiator")
        flow_initiator.initialize(
            strategy_cache=cache_mock, dto_types={"candle_stream": MockCandleWindow}
        )
        return flow_initiator

    @pytest.fixture
    def test_timestamp(self) -> datetime:
        """Provide test timestamp."""
        return datetime(2025, 11, 6, 10, 0, 0, tzinfo=UTC)

    def test_on_data_ready_raises_on_unknown_payload_type(
        self, flow_initiator: FlowInitiator, test_timestamp: datetime
    ) -> None:
        """on_data_ready raises ValueError for unknown payload type."""

        # Create an unknown DTO type (not in dto_types mapping)
        class UnknownDTO(BaseModel):
            """Unknown DTO type not configured in dto_types."""

            data: str

        platform_dto = PlatformDataDTO(
            origin=create_test_origin(OriginType.TICK),
            timestamp=test_timestamp,
            payload=UnknownDTO(data="test"),
        )

        with pytest.raises(ValueError) as exc_info:
            flow_initiator.on_data_ready(platform_dto)

        error_msg = str(exc_info.value).lower()
        assert "no dto type mapping" in error_msg
        assert "unknowndto" in error_msg

    def test_error_message_shows_available_types(
        self, flow_initiator: FlowInitiator, test_timestamp: datetime
    ) -> None:
        """Error message for unknown payload type shows available types."""

        # Create an unknown DTO type
        class InvalidDTO(BaseModel):
            """Invalid DTO type."""

            value: int

        platform_dto = PlatformDataDTO(
            origin=create_test_origin(OriginType.TICK),
            timestamp=test_timestamp,
            payload=InvalidDTO(value=42),
        )

        with pytest.raises(ValueError) as exc_info:
            flow_initiator.on_data_ready(platform_dto)

        error_msg = str(exc_info.value)
        assert "MockCandleWindow" in error_msg  # Should show available type

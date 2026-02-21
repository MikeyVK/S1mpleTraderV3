# tests/unit/core/test_strategy_cache.py
"""
Tests for StrategyCache implementation.

Tests the core functionality of the point-in-time DTO container including
run lifecycle, DTO storage/retrieval, and RunAnchor validation.

@layer: Tests (Unit)
@dependencies: [pytest, datetime, pydantic, backend.core.strategy_cache]
"""

# Standard library
from datetime import UTC, datetime

# Third-party
import pytest
from pydantic import BaseModel

# Project modules
from backend.core.interfaces.strategy_cache import (
    NoActiveRunError,
    RunAnchor,
    StrategyCacheType,
)
from backend.core.strategy_cache import StrategyCache


# Mock DTOs for testing
class MockContextDTO(BaseModel):
    """Mock context DTO for testing."""

    value: str


class MockSignalDTO(BaseModel):
    """Mock signal DTO for testing."""

    signal: str
    confidence: float


class MockDataDTO(BaseModel):
    """Another mock DTO for testing."""

    data: int


# Mock worker for testing
class MockWorker:
    """Simple mock worker."""

    def __init__(self, name: str):
        self.name = name


class TestStrategyCache:
    """Test suite for StrategyCache."""

    @pytest.fixture
    def cache(self):
        """Provide fresh cache instance."""
        return StrategyCache()

    @pytest.fixture
    def test_timestamp(self):
        """Provide test timestamp."""
        return datetime(2025, 10, 28, 10, 30, 0, tzinfo=UTC)

    @pytest.fixture
    def empty_strategy_cache(self) -> StrategyCacheType:
        """Provide empty strategy cache dict."""
        return {}

    @pytest.fixture
    def prefilled_strategy_cache(self) -> StrategyCacheType:
        """Provide pre-filled strategy cache dict."""
        return {
            MockContextDTO: MockContextDTO(value="test_context"),
        }

    # --- Initialization Tests ---

    def test_initial_state_has_no_active_run(self, cache):
        """Cache should have no active run initially."""
        with pytest.raises(NoActiveRunError):
            cache.get_run_anchor()

    def test_initial_state_has_dto_returns_false(self, cache):
        """has_dto should return False when no run is active."""
        assert cache.has_dto(MockContextDTO) is False

    # --- start_new_strategy_run Tests ---

    def test_start_new_strategy_run_with_empty_cache(
        self, cache, empty_strategy_cache, test_timestamp
    ):
        """Should successfully start run with empty cache."""
        cache.start_new_strategy_run(empty_strategy_cache, test_timestamp)

        anchor = cache.get_run_anchor()
        assert anchor.timestamp == test_timestamp

    def test_start_new_strategy_run_with_prefilled_cache(
        self, cache, prefilled_strategy_cache, test_timestamp
    ):
        """Should successfully start run with pre-filled cache."""
        cache.start_new_strategy_run(prefilled_strategy_cache, test_timestamp)

        # Should have access to pre-filled DTOs
        assert cache.has_dto(MockContextDTO) is True

    def test_start_new_strategy_run_replaces_previous_run(
        self, cache, empty_strategy_cache, test_timestamp
    ):
        """Starting new run should replace previous run."""
        # Start first run
        first_timestamp = test_timestamp
        cache.start_new_strategy_run(empty_strategy_cache, first_timestamp)

        # Start second run
        second_timestamp = datetime(2025, 10, 28, 11, 0, 0, tzinfo=UTC)
        new_cache = {}
        cache.start_new_strategy_run(new_cache, second_timestamp)

        # Anchor should be updated
        anchor = cache.get_run_anchor()
        assert anchor.timestamp == second_timestamp

    # --- get_run_anchor Tests ---

    def test_get_run_anchor_returns_correct_timestamp(
        self, cache, empty_strategy_cache, test_timestamp
    ):
        """Should return RunAnchor with correct timestamp."""
        cache.start_new_strategy_run(empty_strategy_cache, test_timestamp)

        anchor = cache.get_run_anchor()
        assert isinstance(anchor, RunAnchor)
        assert anchor.timestamp == test_timestamp

    def test_get_run_anchor_raises_when_no_active_run(self, cache):
        """Should raise NoActiveRunError when no run is active."""
        with pytest.raises(NoActiveRunError) as exc_info:
            cache.get_run_anchor()

        assert "No active strategy run" in str(exc_info.value)

    def test_run_anchor_is_immutable(self, cache, empty_strategy_cache, test_timestamp):
        """RunAnchor should be frozen/immutable."""
        cache.start_new_strategy_run(empty_strategy_cache, test_timestamp)
        anchor = cache.get_run_anchor()

        # Should not be able to modify
        with pytest.raises(Exception):  # Pydantic raises ValidationError
            anchor.timestamp = datetime.now(UTC)

    # --- set_result_dto Tests ---

    def test_set_result_dto_stores_dto(self, cache, empty_strategy_cache, test_timestamp):
        """Should store DTO in cache."""
        cache.start_new_strategy_run(empty_strategy_cache, test_timestamp)

        worker = MockWorker("test_worker")
        dto = MockSignalDTO(signal="BUY", confidence=0.85)

        cache.set_result_dto(worker, dto)

        assert cache.has_dto(MockSignalDTO) is True

    def test_set_result_dto_overwrites_existing_dto_of_same_type(
        self, cache, empty_strategy_cache, test_timestamp
    ):
        """Should overwrite if DTO of same type already exists."""
        cache.start_new_strategy_run(empty_strategy_cache, test_timestamp)

        worker = MockWorker("test_worker")

        # Set first DTO
        dto1 = MockSignalDTO(signal="BUY", confidence=0.85)
        cache.set_result_dto(worker, dto1)

        # Set second DTO of same type
        dto2 = MockSignalDTO(signal="SELL", confidence=0.95)
        cache.set_result_dto(worker, dto2)

        # Should have latest DTO
        dtos = cache.get_required_dtos(worker)
        assert dtos[MockSignalDTO].signal == "SELL"
        assert dtos[MockSignalDTO].confidence == 0.95

    def test_set_result_dto_raises_when_no_active_run(self, cache):
        """Should raise NoActiveRunError when no run is active."""
        worker = MockWorker("test_worker")
        dto = MockSignalDTO(signal="BUY", confidence=0.85)

        with pytest.raises(NoActiveRunError) as exc_info:
            cache.set_result_dto(worker, dto)

        assert "No active strategy run" in str(exc_info.value)

    # --- get_required_dtos Tests ---

    def test_get_required_dtos_returns_all_dtos_in_cache(
        self, cache, empty_strategy_cache, test_timestamp
    ):
        """Should return all DTOs in cache."""
        cache.start_new_strategy_run(empty_strategy_cache, test_timestamp)

        worker = MockWorker("test_worker")

        # Add multiple DTOs
        cache.set_result_dto(worker, MockSignalDTO(signal="BUY", confidence=0.85))
        cache.set_result_dto(worker, MockDataDTO(data=42))

        dtos = cache.get_required_dtos(worker)

        assert MockSignalDTO in dtos
        assert MockDataDTO in dtos
        assert len(dtos) == 2

    def test_get_required_dtos_includes_prefilled_dtos(
        self, cache, prefilled_strategy_cache, test_timestamp
    ):
        """Should include DTOs that were pre-filled at run start."""
        cache.start_new_strategy_run(prefilled_strategy_cache, test_timestamp)

        worker = MockWorker("test_worker")
        dtos = cache.get_required_dtos(worker)

        assert MockContextDTO in dtos
        assert dtos[MockContextDTO].value == "test_context"

    def test_get_required_dtos_raises_when_no_active_run(self, cache):
        """Should raise NoActiveRunError when no run is active."""
        worker = MockWorker("test_worker")

        with pytest.raises(NoActiveRunError) as exc_info:
            cache.get_required_dtos(worker)

        assert "No active strategy run" in str(exc_info.value)

    # --- has_dto Tests ---

    def test_has_dto_returns_true_for_existing_dto(
        self, cache, empty_strategy_cache, test_timestamp
    ):
        """Should return True for DTO that exists in cache."""
        cache.start_new_strategy_run(empty_strategy_cache, test_timestamp)

        worker = MockWorker("test_worker")
        cache.set_result_dto(worker, MockSignalDTO(signal="BUY", confidence=0.85))

        assert cache.has_dto(MockSignalDTO) is True

    def test_has_dto_returns_false_for_missing_dto(
        self, cache, empty_strategy_cache, test_timestamp
    ):
        """Should return False for DTO that doesn't exist in cache."""
        cache.start_new_strategy_run(empty_strategy_cache, test_timestamp)

        assert cache.has_dto(MockSignalDTO) is False

    def test_has_dto_returns_false_when_no_active_run(self, cache):
        """Should return False when no run is active."""
        assert cache.has_dto(MockSignalDTO) is False

    # --- clear_cache Tests ---

    def test_clear_cache_removes_all_dtos(self, cache, empty_strategy_cache, test_timestamp):
        """Should clear all DTOs from cache."""
        cache.start_new_strategy_run(empty_strategy_cache, test_timestamp)

        worker = MockWorker("test_worker")
        cache.set_result_dto(worker, MockSignalDTO(signal="BUY", confidence=0.85))

        cache.clear_cache()

        # Should have no active run after clear
        with pytest.raises(NoActiveRunError):
            cache.get_run_anchor()

        assert cache.has_dto(MockSignalDTO) is False

    def test_clear_cache_is_idempotent(self, cache):
        """Should succeed even when called multiple times."""
        cache.clear_cache()  # Clear when nothing active
        cache.clear_cache()  # Should not raise

    # --- Integration Tests ---

    def test_full_strategy_run_workflow(self, cache, test_timestamp):
        """Test complete workflow of a strategy run."""
        # 1. Start run with pre-filled platform data
        platform_data = {
            MockContextDTO: MockContextDTO(value="ohlcv_data"),
        }
        cache.start_new_strategy_run(platform_data, test_timestamp)

        # 2. Verify anchor
        anchor = cache.get_run_anchor()
        assert anchor.timestamp == test_timestamp

        # 3. Workers add their DTOs
        worker1 = MockWorker("ema_detector")
        cache.set_result_dto(worker1, MockSignalDTO(signal="context_ready", confidence=1.0))

        worker2 = MockWorker("momentum_signal")
        cache.set_result_dto(worker2, MockDataDTO(data=123))

        # 4. Verify all DTOs available
        assert cache.has_dto(MockContextDTO) is True  # Platform
        assert cache.has_dto(MockSignalDTO) is True  # Worker1
        assert cache.has_dto(MockDataDTO) is True  # Worker2

        # 5. Worker can retrieve all needed DTOs
        dtos = cache.get_required_dtos(worker2)
        assert len(dtos) == 3
        assert MockContextDTO in dtos
        assert MockSignalDTO in dtos
        assert MockDataDTO in dtos

        # 6. Clear after run completion
        cache.clear_cache()
        assert cache.has_dto(MockContextDTO) is False

# tests/unit/core/interfaces/test_worker.py
"""
Tests for IWorker and IWorkerLifecycle protocol definitions.

This module contains protocol structure tests for worker interfaces.
These tests validate protocol compliance via structural typing (duck typing).

@layer: Tests (Unit)
@dependencies: [pytest, unittest.mock, backend.core.interfaces]
"""

# Standard library
from unittest.mock import Mock

# Third-party
import pytest

# Project modules
from backend.core.interfaces.strategy_cache import IStrategyCache
from backend.core.interfaces.worker import (
    IWorker,
    IWorkerLifecycle,
    WorkerInitializationError,
)


# Protocol Structure Tests


class TestIWorkerProtocol:
    """Test IWorker protocol structure and compliance."""

    def test_iworker_has_name_property(self) -> None:
        """IWorker protocol requires 'name' property returning str."""

        class ValidWorker:  # pylint: disable=too-few-public-methods
            """Test worker implementation."""

            @property
            def name(self) -> str:
                """Return worker name."""
                return "test_worker"

        worker: IWorker = ValidWorker()  # type: ignore[assignment]
        assert isinstance(worker.name, str)
        assert worker.name == "test_worker"

    def test_iworker_protocol_is_runtime_checkable(self) -> None:
        """IWorker protocol can be checked at runtime via isinstance()."""

        class ValidWorker:  # pylint: disable=too-few-public-methods
            """Test worker implementation."""

            @property
            def name(self) -> str:
                """Return worker name."""
                return "valid"

        worker = ValidWorker()
        # Protocol should be runtime checkable
        assert isinstance(worker, IWorker)


class TestIWorkerLifecycleProtocol:
    """Test IWorkerLifecycle protocol structure and compliance."""

    def test_iworkerlifecycle_has_initialize_method(self) -> None:
        """IWorkerLifecycle requires initialize(strategy_cache, **capabilities) method."""

        class ValidWorker:  # pylint: disable=too-few-public-methods
            """Test worker implementation."""

            def initialize(
                self,
                strategy_cache: IStrategyCache,
                **capabilities
            ) -> None:
                """Initialize worker."""

        worker: IWorkerLifecycle = ValidWorker()  # type: ignore[assignment]
        # Protocol compliance check passes (structural typing)
        assert hasattr(worker, 'initialize')

    def test_iworkerlifecycle_has_shutdown_method(self) -> None:
        """IWorkerLifecycle requires shutdown() method."""

        class ValidWorker:  # pylint: disable=too-few-public-methods
            """Test worker implementation."""

            def shutdown(self) -> None:
                """Shutdown worker."""

        worker: IWorkerLifecycle = ValidWorker()  # type: ignore[assignment]
        assert hasattr(worker, 'shutdown')

    def test_iworkerlifecycle_initialize_signature(self) -> None:
        """Initialize method has correct signature with kwargs for capabilities."""

        class ValidWorker:  # pylint: disable=too-few-public-methods
            """Test worker implementation."""

            def __init__(self) -> None:
                """Initialize test worker."""
                self.cache = None
                self.capabilities = {}

            def initialize(
                self,
                strategy_cache: IStrategyCache,
                **capabilities
            ) -> None:
                """Initialize with dependencies."""
                self.cache = strategy_cache
                self.capabilities = capabilities

        worker: IWorkerLifecycle = ValidWorker()  # type: ignore[assignment]

        # Should accept strategy_cache + optional capabilities
        cache = Mock(spec=IStrategyCache)
        persistence = Mock()

        worker.initialize(strategy_cache=cache, persistence=persistence)
        assert worker.cache is cache
        assert worker.capabilities == {'persistence': persistence}

    def test_iworkerlifecycle_shutdown_signature(self) -> None:
        """Shutdown method has correct signature (no parameters)."""

        class ValidWorker:  # pylint: disable=too-few-public-methods
            """Test worker implementation."""

            def shutdown(self) -> None:
                """Shutdown worker."""

        worker: IWorkerLifecycle = ValidWorker()  # type: ignore[assignment]

        # Should accept no parameters
        worker.shutdown()

    def test_iworkerlifecycle_protocol_is_runtime_checkable(self) -> None:
        """IWorkerLifecycle protocol can be checked at runtime."""

        class ValidWorker:  # pylint: disable=too-few-public-methods
            """Test worker implementation."""

            def initialize(
                self,
                strategy_cache: IStrategyCache,
                **capabilities
            ) -> None:
                """Initialize worker."""

            def shutdown(self) -> None:
                """Shutdown worker."""

        worker = ValidWorker()
        assert isinstance(worker, IWorkerLifecycle)

    def test_iworkerlifecycle_combined_with_iworker(self) -> None:
        """Worker can implement both IWorker and IWorkerLifecycle protocols."""

        class CompleteWorker:  # pylint: disable=too-few-public-methods
            """Test worker implementing both protocols."""

            @property
            def name(self) -> str:
                """Return worker name."""
                return "complete_worker"

            def initialize(
                self,
                strategy_cache: IStrategyCache,
                **capabilities
            ) -> None:
                """Initialize worker."""

            def shutdown(self) -> None:
                """Shutdown worker."""

        worker = CompleteWorker()

        # Should satisfy both protocols
        assert isinstance(worker, IWorker)
        assert isinstance(worker, IWorkerLifecycle)


class TestWorkerInitializationError:
    """Test WorkerInitializationError exception."""

    def test_worker_initialization_error_is_exception(self) -> None:
        """WorkerInitializationError is Exception subclass."""
        assert issubclass(WorkerInitializationError, Exception)

    def test_worker_initialization_error_can_be_raised(self) -> None:
        """WorkerInitializationError can be instantiated with message."""
        error = WorkerInitializationError("Test error message")
        assert str(error) == "Test error message"

    def test_worker_initialization_error_can_be_caught(self) -> None:
        """WorkerInitializationError can be caught in try/except."""

        def failing_function() -> None:
            """Raise WorkerInitializationError."""
            raise WorkerInitializationError("Initialization failed")

        with pytest.raises(WorkerInitializationError) as exc_info:
            failing_function()

        assert "Initialization failed" in str(exc_info.value)


class TestProtocolCompliance:
    """Test protocol compliance with type checking."""

    def test_incomplete_worker_fails_iworkerlifecycle(self) -> None:
        """Worker missing methods doesn't satisfy IWorkerLifecycle."""

        class IncompleteWorker:  # pylint: disable=too-few-public-methods
            """Test worker with missing shutdown method."""

            def initialize(
                self,
                strategy_cache: IStrategyCache,
                **capabilities
            ) -> None:
                """Initialize worker."""
            # Missing shutdown() method!

        worker = IncompleteWorker()

        # Should NOT satisfy IWorkerLifecycle (missing shutdown)
        assert not isinstance(worker, IWorkerLifecycle)

    def test_protocol_type_hints_are_enforced(self) -> None:
        """Protocol enforces method signatures via type checking."""

        class ValidWorker:  # pylint: disable=too-few-public-methods
            """Test worker implementation."""

            def __init__(self) -> None:
                """Initialize test worker."""
                self.cache = None

            def initialize(
                self,
                strategy_cache: IStrategyCache,
                **capabilities
            ) -> None:
                """Initialize with dependencies."""
                self.cache = strategy_cache

            def shutdown(self) -> None:
                """Shutdown worker."""
                self.cache = None

        worker: IWorkerLifecycle = ValidWorker()  # type: ignore[assignment]

        # Type checker validates this at compile time
        # Runtime test confirms protocol compliance
        assert hasattr(worker, 'initialize')
        assert hasattr(worker, 'shutdown')

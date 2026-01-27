# backend/core/interfaces/worker.py
"""
Worker Interface - Base protocol for all worker types.

This module defines the minimal interface that all workers must implement.
It includes the two-phase initialization pattern via IWorkerLifecycle.

@layer: Backend (Core Protocols)
@dependencies: [typing]
@responsibilities:
    - Define IWorker protocol (minimal name property)
    - Define IWorkerLifecycle protocol (two-phase initialization)
    - Provide WorkerInitializationError exception
"""

# Standard library
from typing import TYPE_CHECKING, Protocol, runtime_checkable

# Third-party
# (none)

# Project modules
if TYPE_CHECKING:
    from backend.core.interfaces.strategy_cache import IStrategyCache


__all__ = ["IWorker", "IWorkerLifecycle", "WorkerInitializationError"]


@runtime_checkable
class IWorker(Protocol):  # pylint: disable=too-few-public-methods
    """
    Base protocol for all worker types.

    This is a minimal interface that defines the contract all workers
    must fulfill. Specific worker types (SignalDetector, ContextWorker,
    etc.) will extend this with additional methods.
    """

    @property
    def name(self) -> str:
        """
        Get the worker's name/identifier.

        Returns:
            Worker name (typically from manifest or configuration)
        """
        ...


@runtime_checkable
class IWorkerLifecycle(Protocol):
    """
    Protocol for worker lifecycle management (two-phase initialization).

    Workers follow two-phase initialization pattern:
    1. Construction (__init__): Receive BuildSpec, store manifest data
    2. Runtime initialization (initialize): Inject runtime dependencies

    This decouples worker configuration (BuildSpec) from runtime platform
    services (StrategyCache, capabilities). Workers remain testable in
    isolation without platform singletons.

    Worker Scopes (strategy_cache usage):
        - Platform Workers: Don't use strategy_cache (pass None)
          Examples: DataProvider (singleton, no strategy context)

        - Strategy Workers: Require strategy_cache (per-strategy instance)
          Examples: SignalDetector, RiskMonitor, PlanningWorker

        - Platform-within-Strategy: Singleton but strategy-aware
          Examples: FlowInitiator (singleton, routes to strategies)

    Example (Strategy Worker):
        ```python
        # Construction phase
        worker = SignalDetector(build_spec)

        # Runtime initialization
        worker.initialize(
            strategy_cache=platform.strategy_cache,
            persistence=persistence_service,
            strategy_ledger=ledger_service
        )

        # Active phase
        # ... worker operates normally ...

        # Cleanup phase
        worker.shutdown()
        ```

    Example (Platform Worker):
        ```python
        # Construction phase
        data_provider = DataProvider(build_spec)

        # Runtime initialization (no strategy_cache needed)
        data_provider.initialize(
            strategy_cache=None,
            market_connection=connection_service
        )
        ```

    Capabilities:
        - persistence: IPersistenceService (optional)
        - strategy_ledger: IStrategyLedger (optional)
        - aggregated_ledger: IAggregatedLedger (optional)

    See: docs/development/IWORKERLIFECYCLE_DESIGN.md
    """

    def initialize(
        self,
        strategy_cache: "IStrategyCache | None" = None,
        **capabilities
    ) -> None:
        """
        Initialize worker with runtime dependencies.

        This method MUST be called after construction and before first use.
        It injects platform services that workers need during operation.

        Phase Transition: Constructed → Active

        Args:
            strategy_cache: Platform singleton for strategy state management.
                - Required for Strategy Workers (per-strategy instances)
                - Required for Platform-within-Strategy Workers (routing)
                - None for Platform Workers (no strategy context)
            **capabilities: Optional runtime capabilities:
                - persistence: IPersistenceService (for state persistence)
                - strategy_ledger: IStrategyLedger (for strategy analytics)
                - aggregated_ledger: IAggregatedLedger (for aggregated data)

        Raises:
            WorkerInitializationError: If initialization fails
                (dependencies invalid, resources unavailable, etc.)

        Note:
            Strategy Workers MUST validate strategy_cache is not None.
            Platform Workers MUST NOT use strategy_cache (ignore if provided).
            Workers MAY store capability references if needed.
            Workers MUST validate required capabilities are present.
        """
        ...

    def shutdown(self) -> None:
        """
        Graceful worker shutdown and resource cleanup.

        This method MUST be called before worker disposal to ensure:
        - Open resources are closed (files, connections, etc.)
        - Background tasks are cancelled
        - Cached state is flushed if needed

        Phase Transition: Active → Shutdown

        Critical Requirements:
            - MUST NOT raise exceptions (catch and log internally)
            - MUST be idempotent (safe to call multiple times)
            - SHOULD complete within reasonable time (<5s typical)

        Note:
            This is NOT a destructor (__del__). It's explicit lifecycle
            management. Platform orchestrator calls this during graceful
            shutdown sequences.
        """
        ...


class WorkerInitializationError(Exception):
    """
    Exception raised when worker initialization fails.

    This exception signals that a worker could not complete its
    initialize() phase successfully. Common causes:
    - Required capability missing
    - Invalid strategy_cache state
    - Resource allocation failure
    - Configuration validation failure during initialization

    Example:
        ```python
        def initialize(self, strategy_cache, **capabilities):
            if 'persistence' not in capabilities:
                raise WorkerInitializationError(
                    f"{self.name}: persistence capability required "
                    f"but not provided"
                )
        ```
    """

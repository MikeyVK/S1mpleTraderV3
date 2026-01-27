# backend/core/flow_initiator.py
"""
FlowInitiator - Per-strategy data ingestion and cache initialization.

FlowInitiator is a Platform-within-Strategy worker that:
1. Initializes StrategyCache for new runs (start_new_run)
2. Stores PlatformDataDTO payloads by type (set_result_dto)
3. Returns CONTINUE disposition to trigger worker pipeline

@layer: Backend (Core)
@dependencies: [backend.core.interfaces, backend.dtos.shared]
@responsibilities:
    - Initialize StrategyCache with RunAnchor
    - Store provider DTOs in cache by TYPE
    - Return CONTINUE disposition for EventAdapter routing
"""

# Standard library
from __future__ import annotations

from typing import TYPE_CHECKING, Any

# Third-party
from pydantic import BaseModel

# Project modules
from backend.core.interfaces.worker import IWorker, IWorkerLifecycle, WorkerInitializationError
from backend.dtos.shared.disposition_envelope import DispositionEnvelope

if TYPE_CHECKING:
    from backend.core.interfaces.strategy_cache import IStrategyCache
    from backend.dtos.shared.platform_data import PlatformDataDTO


__all__ = ["FlowInitiator"]


class FlowInitiator(IWorker, IWorkerLifecycle):
    """
    Per-strategy data ingestion and cache initialization component.

    Architecture:
    - EventAdapter-compliant: Standard IWorker + IWorkerLifecycle pattern
    - Platform-within-Strategy: Singleton but requires strategy_cache
    - Type-safe: DTO types injected via ConfigTranslator
    - Generic: Single handler for all data types

    Flow:
    1. DataProvider publishes PlatformDataDTO
    2. EventAdapter calls on_data_ready()
    3. FlowInitiator: start_new_run() + set_result_dto()
    4. Return CONTINUE disposition
    5. EventAdapter publishes continuation event
    6. Workers retrieve data from StrategyCache
    """

    def __init__(self, name: str) -> None:
        """
        Construct FlowInitiator with name.

        Args:
            name: Worker name (typically "flow_initiator_{strategy_id}")
        """
        self._name = name
        self._cache: IStrategyCache | None = None
        self._dto_types: dict[str, type[BaseModel]] = {}

    @property
    def name(self) -> str:
        """Get worker name (IWorker requirement)."""
        return self._name

    def initialize(
        self,
        strategy_cache: IStrategyCache | None = None,
        **capabilities: Any
    ) -> None:
        """
        Initialize with runtime dependencies.

        Args:
            strategy_cache: StrategyCache instance (REQUIRED - Platform-within-Strategy)
            **capabilities: Required capabilities:
                - dto_types: Dict[str, Type[BaseModel]] - DTO type mappings

        Raises:
            WorkerInitializationError: If strategy_cache is None or dto_types missing
        """
        # Validate strategy_cache (Platform-within-Strategy requirement)
        if strategy_cache is None:
            raise WorkerInitializationError(
                f"{self._name}: strategy_cache required for FlowInitiator "
                f"(Platform-within-Strategy worker)"
            )

        # Validate dto_types capability
        if "dto_types" not in capabilities:
            raise WorkerInitializationError(
                f"{self._name}: 'dto_types' capability required for DTO type resolution"
            )

        self._cache = strategy_cache
        self._dto_types = capabilities["dto_types"]

    def on_data_ready(self, data: PlatformDataDTO) -> DispositionEnvelope:
        """
        Handle data ready event from DataProvider.

        Flow:
        1. Initialize StrategyCache with RunAnchor (start_new_strategy_run)
        2. Validate payload type has DTO type mapping
        3. Store payload in cache by TYPE (set_result_dto)
        4. Return CONTINUE disposition for EventAdapter

        Args:
            data: PlatformDataDTO from DataProvider

        Returns:
            DispositionEnvelope with CONTINUE disposition

        Raises:
            ValueError: If payload type has no DTO type mapping
        """
        # Type narrowing: cache is guaranteed non-None after initialize()
        assert self._cache is not None, "FlowInitiator not initialized (call initialize() first)"

        # 1. Initialize StrategyCache with timestamp
        self._cache.start_new_strategy_run({}, data.timestamp)

        # 2. Validate DTO type mapping exists
        payload_type = type(data.payload)
        if payload_type not in self._dto_types.values():
            available_types = list(self._dto_types.values())
            raise ValueError(
                f"No DTO type mapping for payload type: {payload_type.__name__}. "
                f"Available types: {[t.__name__ for t in available_types]}. "
                f"Check ExecutionEnvironment provider configuration."
            )

        # 3. Store payload in StrategyCache (by TYPE)
        self._cache.set_result_dto(data.payload)

        # 4. Return CONTINUE disposition
        return DispositionEnvelope(disposition="CONTINUE")

    def shutdown(self) -> None:
        """
        Graceful shutdown (no resources to cleanup).

        FlowInitiator has no persistent resources to release.
        Implements IWorkerLifecycle requirement.
        """
        # No cleanup needed - idempotent
        ...

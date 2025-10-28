"""
Strategy Cache Interface - Point-in-Time DTO Container for Strategy Runs.

This module defines the IStrategyCache protocol, which serves as a simple,
SRP-focused container for DTOs during a single strategy run.
"""

from typing import Protocol, Dict, Type
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from backend.core.interfaces.worker import IWorker


# Type alias for the cache container
StrategyCacheType = Dict[Type[BaseModel], BaseModel]


class RunAnchor(BaseModel):
    """
    Point-in-time validation anchor for a strategy run.

    All data within this run (DTOs in cache, platform provider responses)
    MUST be consistent with this timestamp.

    Attributes:
        timestamp: The point-in-time moment for this run
    """
    model_config = ConfigDict(frozen=True)

    timestamp: datetime


class IStrategyCache(Protocol):
    """
    Point-in-time DTO container for one strategy run.

    Responsibilities:
    - Store DTOs (from any source: workers, platform, etc.)
    - Retrieve DTOs for workers
    - Provide timestamp anchor for point-in-time validation

    NOT responsible for:
    - How DTOs get into cache (that's orchestration)
    - Dependency validation (that's bootstrap)
    - Persistence (that's IStateProvider, IJournalWriter)

    This is a "dumb container" - it doesn't know or care where DTOs
    come from. It simply stores and retrieves them based on type.
    """

    def start_new_strategy_run(
        self,
        strategy_cache: StrategyCacheType,
        timestamp: datetime
    ) -> None:
        """
        Configure cache for new strategy run.

        Args:
            strategy_cache: DTO container for this run (may be pre-filled)
            timestamp: Point-in-time anchor for this run

        Note:
            The cache may already contain DTOs provided by platform
            capability providers. Workers will add their own DTOs during
            the run via set_result_dto().
        """
        ...

    def get_run_anchor(self) -> RunAnchor:
        """
        Get the point-in-time validation anchor for this run.

        Workers use this timestamp to validate that platform providers
        deliver data consistent with this moment.

        Returns:
            RunAnchor containing the timestamp for this run

        Raises:
            NoActiveRunError: If no strategy run is active

        Example:
            >>> anchor = self.strategy_cache.get_run_anchor()
            >>> ohlcv = self.ohlcv_provider.get_window(
            ...     end_time=anchor.timestamp,
            ...     lookback=100
            ... )
        """
        ...

    def get_required_dtos(
        self,
        requesting_worker: IWorker
    ) -> Dict[Type[BaseModel], BaseModel]:
        """
        Retrieve DTOs required by worker from cache.

        Args:
            requesting_worker: Worker requesting DTOs

        Returns:
            Dictionary mapping DTO types to instances from cache

        Raises:
            MissingContextDataError: If required DTO not in cache

        Note:
            The worker's manifest (requires_system_resources.context_dtos.critical)
            determines which DTOs are required. Bootstrap validation ensures
            all critical DTOs have producers.
        """
        ...

    def set_result_dto(
        self,
        producing_worker: IWorker,
        result_dto: BaseModel
    ) -> None:
        """
        Add worker-produced DTO to cache.

        Args:
            producing_worker: Worker producing the DTO
            result_dto: DTO instance to store

        Raises:
            UnexpectedDTOTypeError: If DTO type not in manifest.produces_dtos
            NoActiveRunError: If no strategy run is active

        Note:
            The DTO type is used as the cache key. Only one instance per
            type can exist in the cache (last write wins).
        """
        ...

    def has_dto(self, dto_type: Type[BaseModel]) -> bool:
        """
        Check if DTO type is present in cache.

        Args:
            dto_type: Type of DTO to check

        Returns:
            True if DTO in cache, False otherwise

        Note:
            Workers should primarily use this for OPTIONAL dependencies.
            Critical dependencies are guaranteed by bootstrap validation.
        """
        ...

    def clear_cache(self) -> None:
        """
        Clear the cache after run completion.

        This is called by the orchestration layer (TickCacheManager or
        equivalent) after the strategy run completes or fails.

        Always succeeds (even if cache is already empty).
        """
        ...


class NoActiveRunError(Exception):
    """Raised when cache operation attempted without active run."""


class MissingContextDataError(Exception):
    """Raised when required DTO not found in cache."""

    def __init__(self, worker_name: str, missing_dtos: list[str]):
        self.worker_name = worker_name
        self.missing_dtos = missing_dtos
        super().__init__(
            f"Worker '{worker_name}' requires DTOs {missing_dtos} "
            f"which are not in cache. This indicates a bootstrap validation "
            f"bug or wiring configuration error."
        )


class UnexpectedDTOTypeError(Exception):
    """Raised when worker produces DTO not declared in manifest."""

    def __init__(self, worker_name: str, dto_type: str, declared_dtos: list[str]):
        self.worker_name = worker_name
        self.dto_type = dto_type
        self.declared_dtos = declared_dtos
        super().__init__(
            f"Worker '{worker_name}' produced DTO '{dto_type}' "
            f"which is not declared in manifest.produces_dtos: {declared_dtos}. "
            f"Update manifest or fix worker implementation."
        )

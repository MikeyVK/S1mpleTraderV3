# backend/core/strategy_cache.py
"""
Strategy Cache Implementation - Concrete point-in-time DTO container.

This module provides the concrete implementation of IStrategyCache for managing
strategy run state and DTO caching with RunAnchor validation.

@layer: Backend (Core Services)
@dependencies: [typing, datetime, pydantic, backend.core.interfaces.strategy_cache]
@responsibilities:
    - Implement IStrategyCache protocol
    - Manage strategy run lifecycle (start/clear)
    - Store and retrieve DTOs with type safety
    - Validate RunAnchor consistency
"""

# Standard library
from datetime import datetime
from typing import Dict, Type

# Third-party
from pydantic import BaseModel

# Project modules
from backend.core.interfaces.strategy_cache import (
    NoActiveRunError,
    RunAnchor,
    StrategyCacheType,
)


class StrategyCache:
    """
    Concrete implementation of IStrategyCache.

    This is a simple, stateful container that holds DTOs for the
    currently active strategy run. It's designed to be a singleton
    service that gets reconfigured for each new run.
    """

    def __init__(self):
        """Initialize with no active run."""
        self._current_cache: StrategyCacheType | None = None
        self._current_anchor: RunAnchor | None = None

    def start_new_strategy_run(
        self,
        strategy_cache: StrategyCacheType,
        timestamp: datetime
    ) -> None:
        """Configure cache for new strategy run."""
        self._current_cache = strategy_cache
        self._current_anchor = RunAnchor(timestamp=timestamp)

    def get_run_anchor(self) -> RunAnchor:
        """Get the point-in-time validation anchor."""
        if self._current_anchor is None:
            raise NoActiveRunError(
                "No active strategy run. Call start_new_strategy_run() first."
            )
        return self._current_anchor

    def get_required_dtos(
        self,
        requesting_worker
    ) -> Dict[Type[BaseModel], BaseModel]:
        """
        Retrieve DTOs required by worker from cache.

        Returns all DTOs currently in cache. The worker is responsible
        for extracting the specific DTOs it needs based on its manifest.
        """
        if self._current_cache is None:
            raise NoActiveRunError(
                "No active strategy run. Call start_new_strategy_run() first."
            )

        return dict(self._current_cache)

    def set_result_dto(
        self,
        producing_worker,
        result_dto: BaseModel
    ) -> None:
        """
        Add worker-produced DTO to cache.

        The DTO type is used as the cache key. Only one instance per
        type can exist (last write wins).
        """
        if self._current_cache is None:
            raise NoActiveRunError(
                "No active strategy run. Call start_new_strategy_run() first."
            )

        # Store DTO using its type as key
        dto_type = type(result_dto)
        self._current_cache[dto_type] = result_dto

    def has_dto(self, dto_type: Type[BaseModel]) -> bool:
        """Check if DTO type is present in cache."""
        if self._current_cache is None:
            return False
        return dto_type in self._current_cache

    def clear_cache(self) -> None:
        """Clear the cache after run completion."""
        self._current_cache = None
        self._current_anchor = None

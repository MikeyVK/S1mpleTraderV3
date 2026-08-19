# mcp_server/state/response_cache.py
"""In-memory cache for storing StructuredTool outputs.

@layer: Backend (State)
@dependencies: [mcp_server.core.interfaces, collections, pydantic]
@responsibilities:
    - Cache StructuredTool output DTO instances in memory
    - Enforce a FIFO/LRU eviction policy using OrderedDict to prevent memory leaks
"""

from __future__ import annotations

import re
import uuid
from collections import OrderedDict
from typing import TYPE_CHECKING, TypeVar, cast

from mcp_server.core.interfaces import IToolResponsePublisher, IToolResponseReader
from mcp_server.schemas.cache_publication import CachePublication

if TYPE_CHECKING:
    from pydantic import BaseModel

T = TypeVar("T", bound="BaseModel")


class ResponseCacheManager(IToolResponsePublisher, IToolResponseReader):
    """In-memory session cache manager for tool responses.

    Uses OrderedDict to implement a simple bounded FIFO cache eviction.
    """

    def __init__(self, max_size: int = 50) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, BaseModel] = OrderedDict()

    def put(self, tool_name: str, output: BaseModel) -> CachePublication:
        """Publish the output DTO to the cache and return a CachePublication."""
        try:
            # Generate a new unique run_id
            run_id = uuid.uuid4().hex

            if run_id in self._cache:
                self._cache.move_to_end(run_id)
            self._cache[run_id] = output

            # Enforce FIFO eviction
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)
            return CachePublication(run_id=run_id, success=True)
        except Exception:
            return CachePublication(run_id=None, success=False, error_code="write_failed")

    def get(self, run_id: str, response_model: type[T] | None = None) -> T | None:
        """Retrieve and deserialize a cached DTO using the expected type-safe model."""
        if not re.match(r"^[a-f0-9]{32}$", run_id):
            return None

        if run_id not in self._cache:
            return None

        self._cache.move_to_end(run_id)
        dto = self._cache[run_id]

        # If response_model is provided, check or cast
        if response_model is not None:
            if isinstance(dto, response_model):
                return dto
            return None

        return cast(T, dto)

    def exists(self, run_id: str) -> bool:
        """Check if a cached result exists for the run_id."""
        if not re.match(r"^[a-f0-9]{32}$", run_id):
            return False
        return run_id in self._cache

# mcp_server/resources/cache.py
"""Resource for reading cached tool outputs.

@layer: MCP (Resources)
@dependencies: [mcp_server.resources.base, mcp_server.core.interfaces, re]
@responsibilities:
    - Match URIs for cached tool outputs (pgmcp://cache/runs/{run_id})
    - Read the cached output from the cache manager and return compact JSON
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from pydantic import BaseModel

from mcp_server.resources.base import BaseResource

if TYPE_CHECKING:
    from mcp_server.core.interfaces import IToolResponseReader


class CachedResponseResource(BaseResource):
    """Resource provider for cached tool responses."""

    uri_pattern = "pgmcp://cache/runs/.*"
    description = "Cached tool execution results"
    mime_type = "application/json"

    def __init__(self, cache: IToolResponseReader) -> None:
        self._cache = cache

    def matches(self, uri: str) -> bool:
        """Check if the URI matches the cached runs pattern with a valid hex UUID."""
        if not uri.startswith("pgmcp://cache/runs/"):
            return False
        run_id = uri.rsplit("/", maxsplit=1)[-1]
        return bool(re.match(r"^[a-f0-9]{32}$", run_id))

    async def read(self, uri: str) -> str:
        """Read the resource content from the cache and return compact JSON."""
        if not uri.startswith("pgmcp://cache/runs/"):
            raise ValueError(f"Invalid resource URI: {uri}")

        run_id = uri.rsplit("/", maxsplit=1)[-1]
        if not re.match(r"^[a-f0-9]{32}$", run_id):
            raise ValueError(f"Invalid run_id format: {run_id}")

        dto = self._cache.get(run_id, BaseModel)
        if not dto:
            raise ValueError("No cached data found")

        # Returns whitespace-stripped compact JSON with None values excluded
        try:
            return dto.model_dump_json(exclude_none=True)
        except Exception as e:
            fallback = {
                "success": False,
                "error_type": "SerializationError",
                "message": f"Unable to serialize DTO: {e}",
                "dto_type": type(dto).__name__,
            }
            if hasattr(dto, "error_message") and dto.error_message:
                fallback["error_message"] = str(dto.error_message)
            if hasattr(dto, "traceback") and dto.traceback:
                fallback["traceback"] = str(dto.traceback)
            return json.dumps(fallback)

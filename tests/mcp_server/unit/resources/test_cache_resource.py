# c:\temp\pgmcp\tests\mcp_server\unit\resources\test_cache_resource.py
# template=unit_test version=3d15d309 created=2026-06-25T19:43Z updated=
"""
Unit tests for mcp_server.resources.cache.

Tests for CachedResponseResource validation and reading.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.resources.cache, unittest.mock]
"""

# Third-party
from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

# Project modules
from mcp_server.resources.cache import CachedResponseResource


class DummyModel(BaseModel):
    value: str


@pytest.mark.anyio
class TestCachedResponseResource:
    """Test suite for cache resource."""

    def test_matches_valid_hex_uuid(self) -> None:
        """Verify matches() only returns True for valid 32-character hex UUID URIs."""
        mock_cache = MagicMock()
        resource = CachedResponseResource(mock_cache)

        # Valid hex UUID URI should match
        valid_id = "a" * 32
        assert resource.matches(f"pgmcp://cache/runs/{valid_id}")

        # Invalid formats or non-matching paths should not match
        assert not resource.matches("pgmcp://cache/runs/invalid-uuid")
        assert not resource.matches(f"pgmcp://cache/runs/{valid_id}-extra")
        assert not resource.matches("pgmcp://other/path")

    async def test_read_valid_hex_uuid(self) -> None:
        """Verify read() retrieves valid hex UUID keys and rejects invalid formats."""
        mock_cache = MagicMock()
        resource = CachedResponseResource(mock_cache)

        valid_id = "a" * 32
        model = DummyModel(value="cached-value")
        mock_cache.get.return_value = model

        # Valid URI should succeed and return compact json
        result = await resource.read(f"pgmcp://cache/runs/{valid_id}")
        assert "cached-value" in result
        mock_cache.get.assert_called_once_with(valid_id, BaseModel)

        # Invalid URI format should raise ValueError
        with pytest.raises(ValueError):
            await resource.read("pgmcp://cache/runs/invalid-uuid")

        with pytest.raises(ValueError):
            await resource.read("pgmcp://other/path")

# c:\temp\pgmcp\tests\mcp_server\unit\state\test_response_cache.py
# template=unit_test version=3d15d309 created=2026-06-25T19:42Z updated=
"""
Unit tests for mcp_server.state.response_cache.

Tests for ResponseCacheManager key validation and normalization.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.state.response_cache, unittest.mock]
"""

# Third-party
import pytest
from pydantic import BaseModel, ValidationError

# Project modules
from mcp_server.schemas.cache_publication import CachePublication
from mcp_server.state.response_cache import ResponseCacheManager


class TestResponseCache:
    """Test suite for response_cache."""

    def test_cache_publication_validation(self) -> None:
        """Verify that CachePublication run_id enforces 32-character hex UUID format."""
        # Valid hex UUID should pass
        pub = CachePublication(run_id="a" * 32)
        assert pub.run_id == "a" * 32

        # Invalid strings should raise ValidationError
        with pytest.raises(ValidationError):
            CachePublication(run_id="invalid-uuid")

        with pytest.raises(ValidationError):
            CachePublication(run_id="g" * 32)  # Non-hex characters

    def test_response_cache_manager_put_get_exists(self) -> None:
        """Verify ResponseCacheManager put, get, and exists behavior with hex UUIDs."""
        cache = ResponseCacheManager()

        class DummyModel(BaseModel):
            value: str

        model = DummyModel(value="test")
        pub = cache.put("test_tool", model)

        assert pub.success
        assert pub.run_id is not None
        assert len(pub.run_id) == 32

        # exists and get should work with the raw run_id
        assert cache.exists(pub.run_id)
        assert cache.get(pub.run_id, DummyModel) == model

        # exists and get should reject invalid formats or URIs
        assert not cache.exists("invalid-uuid")
        assert cache.get("invalid-uuid") is None
        assert not cache.exists(f"pgmcp://cache/runs/{pub.run_id}")
        assert cache.get(f"pgmcp://cache/runs/{pub.run_id}") is None

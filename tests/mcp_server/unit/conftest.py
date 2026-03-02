"""Test fixtures for MCP server unit tests."""

import pytest


@pytest.fixture
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Fixture that sets mock environment variables for testing."""
    monkeypatch.setenv("MCP_SERVER_NAME", "test-server")
    monkeypatch.setenv("MCP_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    return monkeypatch

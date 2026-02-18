"""Unit tests for ScopeConfig singleton (Issue #149, Cycle 1).

@layer: tests
@dependencies: mcp_server.config.scope_config
@responsibilities: Verify ScopeConfig loads scopes.yaml (flat list), has_scope(),
                   singleton behaviour, case-sensitivity.
"""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml

from mcp_server.config.scope_config import ScopeConfig

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_MINIMAL_SCOPES_YAML = {
    "version": "1.0",
    "scopes": ["architecture", "mcp-server", "platform", "tooling", "workflow", "documentation"],
}


@pytest.fixture(name="scopes_yaml_path")
def _scopes_yaml_path() -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fh:
        yaml.dump(_MINIMAL_SCOPES_YAML, fh, allow_unicode=True)
        return Path(fh.name)


@pytest.fixture(name="scope_config")
def _scope_config(scopes_yaml_path: Path) -> Generator[ScopeConfig, None, None]:
    ScopeConfig.reset_instance()
    cfg = ScopeConfig.from_file(str(scopes_yaml_path))
    yield cfg
    ScopeConfig.reset_instance()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestScopeConfigFromFile:
    """Loading and singleton behaviour."""

    def test_from_file_loads_scopes(self, scope_config: ScopeConfig) -> None:
        assert "tooling" in scope_config.scopes
        assert "architecture" in scope_config.scopes
        assert "documentation" in scope_config.scopes

    def test_from_file_raises_on_missing_file(self) -> None:
        ScopeConfig.reset_instance()
        with pytest.raises(FileNotFoundError, match="Scope config not found"):
            ScopeConfig.from_file(".st3/nonexistent_scopes.yaml")

    def test_singleton_returns_same_instance(self, scopes_yaml_path: Path) -> None:
        ScopeConfig.reset_instance()
        cfg1 = ScopeConfig.from_file(str(scopes_yaml_path))
        cfg2 = ScopeConfig.from_file(str(scopes_yaml_path))
        assert cfg1 is cfg2


class TestScopeConfigHasScope:
    """has_scope() correctness and edge cases."""

    def test_has_scope_returns_true_for_known_scope(self, scope_config: ScopeConfig) -> None:
        assert scope_config.has_scope("tooling") is True

    def test_has_scope_returns_true_for_hyphenated_scope(self, scope_config: ScopeConfig) -> None:
        assert scope_config.has_scope("mcp-server") is True

    def test_has_scope_returns_false_for_unknown_scope(self, scope_config: ScopeConfig) -> None:
        assert scope_config.has_scope("unknown-scope") is False

    def test_has_scope_is_case_sensitive(self, scope_config: ScopeConfig) -> None:
        assert scope_config.has_scope("Tooling") is False
        assert scope_config.has_scope("ARCHITECTURE") is False

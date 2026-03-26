"""Unit tests for ScopeConfig loader-based access (Issue #149, Cycle 1).

@layer: Tests (Unit)
@dependencies: pytest, yaml, mcp_server.config.schemas
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import ScopeConfig
from mcp_server.core.exceptions import ConfigError

_MINIMAL_SCOPES_YAML = {
    "version": "1.0",
    "scopes": ["architecture", "mcp-server", "platform", "tooling", "workflow", "documentation"],
}


def _load_scope_config(config_path: Path) -> ScopeConfig:
    return ConfigLoader(config_path.parent).load_scope_config(config_path=config_path)


@pytest.fixture(name="scopes_yaml_path")
def _scopes_yaml_path() -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    ) as fh:
        yaml.dump(_MINIMAL_SCOPES_YAML, fh, allow_unicode=True)
        return Path(fh.name)


@pytest.fixture(name="scope_config")
def _scope_config(scopes_yaml_path: Path) -> ScopeConfig:
    return _load_scope_config(scopes_yaml_path)


class TestScopeConfigFromFile:
    """Loading behaviour through ConfigLoader."""

    def test_from_file_loads_scopes(self, scope_config: ScopeConfig) -> None:
        assert "tooling" in scope_config.scopes
        assert "architecture" in scope_config.scopes
        assert "documentation" in scope_config.scopes

    def test_from_file_raises_on_missing_file(self) -> None:
        with pytest.raises(ConfigError, match="Config file not found"):
            _load_scope_config(Path(".st3/nonexistent_scopes.yaml"))

    def test_repeated_loads_are_equivalent(self, scopes_yaml_path: Path) -> None:
        cfg1 = _load_scope_config(scopes_yaml_path)
        cfg2 = _load_scope_config(scopes_yaml_path)
        assert cfg1 == cfg2


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

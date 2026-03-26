# tests/unit/config/test_c_settings_structural.py
"""
Structural tests for C_SETTINGS singleton and wrapper removal.

Zone 1: class introspection and source inspection; no YAML, no filesystem.
These tests must all be GREEN after the settings and loader flag-day work.

@layer: Tests (Unit)
@dependencies: [importlib.util, inspect, mcp_server.config.settings]
"""

import importlib.util
import inspect

import mcp_server.config.settings as _settings_module
from mcp_server.config.settings import Settings


def test_settings_module_does_not_export_singleton() -> None:
    """Module-level 'settings' must not exist — singleton deleted.

    Ref: c_settings_1.singleton_deleted.
    """
    assert not hasattr(_settings_module, "settings"), (
        "mcp_server.config.settings must not export a module-level 'settings' singleton. "
        "Use Settings.from_env() at the composition root (server.py)."
    )


def test_settings_exposes_from_env_not_load() -> None:
    """Settings must expose from_env(); load() must be deleted (c_settings_1.from_env)."""
    assert hasattr(Settings, "from_env"), "Settings.from_env() must exist."
    assert not hasattr(Settings, "load"), (
        "Settings.load() must be deleted — use Settings.from_env() instead."
    )


def test_legacy_workflows_wrapper_module_deleted() -> None:
    """The legacy workflows wrapper must be removed after the loader flag-day."""
    assert importlib.util.find_spec("mcp_server.config.workflows") is None


def test_log_level_env_var_renamed() -> None:
    """'MCP_LOG_LEVEL' must not appear in settings source (c_settings_1.log_level_rename)."""
    source = inspect.getsource(_settings_module)
    assert "MCP_LOG_LEVEL" not in source, (
        "settings.py still references 'MCP_LOG_LEVEL'. Rename to 'LOG_LEVEL'."
    )

"""
@module: tests.unit.test_pytest_config
@layer: Test Infrastructure
@responsibilities:
  - Verify that pytest addopts excludes integration tests from the default run
  - Prevents regression where integration-marked tests run against live GitHub API
"""

from __future__ import annotations

import tomllib
from pathlib import Path


def _load_addopts() -> list[str]:
    return _load_pytest_config()["addopts"]


def _load_pytest_config() -> dict:
    pyproject = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data["tool"]["pytest"]["ini_options"]


def test_testpaths_set_to_mcp_server() -> None:
    """Default pytest run must only collect tests/mcp_server/.

    Backend tests are run explicitly via pytest tests/backend/ and should
    NOT be included in the default discovery. testpaths in pyproject.toml
    enforces this separation.
    """
    config = _load_pytest_config()
    assert "testpaths" in config, (
        "testpaths must be set in [tool.pytest.ini_options] to restrict "
        "default discovery to tests/mcp_server/"
    )
    assert config["testpaths"] == ["tests/mcp_server"], (
        f"testpaths must be ['tests/mcp_server']; got {config['testpaths']}"
    )


def test_addopts_excludes_integration_marker() -> None:
    """Default pytest run must never execute integration-marked tests.

    Integration tests call the live GitHub API and create real issues.
    Exclusion via -m 'not integration' in addopts is the fix for #237.
    """
    addopts = _load_addopts()
    addopts_str = " ".join(addopts)
    assert "not integration" in addopts_str, (
        "addopts must contain '-m not integration' to prevent integration tests "
        "from running in the default suite. "
        f"Current addopts: {addopts}"
    )

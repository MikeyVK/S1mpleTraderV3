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
    pyproject = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    return data["tool"]["pytest"]["ini_options"]["addopts"]


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

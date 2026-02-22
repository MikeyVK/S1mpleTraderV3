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


# ---------------------------------------------------------------------------
# C3 RED: integration marker saneren
# ---------------------------------------------------------------------------


def _load_markers() -> list[str]:
    return _load_pytest_config()["markers"]


def test_integration_marker_has_formal_definition() -> None:
    """integration marker must have formal definition containing 'end-to-end'.

    Formal definition per planning.md: tests that validate end-to-end
    behaviour across the full scope using real subprocesses, external
    services or the full MCP system.
    """
    markers = _load_markers()
    integration_desc = next((m for m in markers if m.startswith("integration:")), None)
    assert integration_desc is not None, "integration marker must be defined in pyproject.toml"
    assert "end-to-end" in integration_desc, (
        f"integration marker description must contain 'end-to-end'; got: {integration_desc}"
    )


def test_slow_marker_has_formal_definition() -> None:
    """slow marker must have formal definition describing subprocess-spawning tests.

    Formal definition per planning.md: fully hermetic but spawns real
    subprocesses or git operations on tmp_path. Enabled by default.
    """
    markers = _load_markers()
    slow_desc = next((m for m in markers if m.startswith("slow:")), None)
    assert slow_desc is not None, "slow marker must be defined in pyproject.toml"
    assert "subprocess" in slow_desc or "spawns" in slow_desc, (
        f"slow marker description must mention subprocess-spawning behaviour; got: {slow_desc}"
    )


def test_qa_tests_relocated_to_integration_directory() -> None:
    """test_qa.py must live in tests/mcp_server/integration/ (not in unit/ subtree).

    The QA tests (ruff/mypy on real workspace files) are integration tests
    because they operate on the real filesystem, not on isolated tmp_path.
    """
    repo_root = Path(__file__).parent.parent.parent.parent
    target_path = repo_root / "tests" / "mcp_server" / "integration" / "test_qa.py"
    wrong_path = repo_root / "tests" / "mcp_server" / "unit" / "mcp_server" / "integration" / "test_qa.py"
    assert target_path.exists(), (
        f"test_qa.py must be at {target_path.relative_to(repo_root)}; "
        f"currently found at wrong location: {wrong_path.relative_to(repo_root)}"
    )


def test_asyncio_mode_is_strict() -> None:
    """asyncio_mode must be 'strict' to avoid event-loop overhead on sync tests.

    'auto' makes all 1812 tests pay event-loop setup cost; 1456 are sync and
    don't need it. 'strict' is also a required prerequisite for pytest-xdist (C4).
    """
    config = _load_pytest_config()
    asyncio_mode = config.get("asyncio_mode")
    assert asyncio_mode == "strict", (
        f"asyncio_mode must be 'strict'; got '{asyncio_mode}'. "
        "Change asyncio_mode in [tool.pytest.ini_options] and add "
        "pytestmark = pytest.mark.asyncio to each async test module."
    )


# ---------------------------------------------------------------------------
# C4 RED: pytest-xdist parallel execution
# ---------------------------------------------------------------------------


def test_xdist_in_requirements_dev() -> None:
    """pytest-xdist must be listed in requirements-dev.txt.

    Parallel test execution with `-n auto` requires pytest-xdist.
    """
    req_dev = Path(__file__).parent.parent.parent.parent / "requirements-dev.txt"
    content = req_dev.read_text(encoding="utf-8")
    assert "pytest-xdist" in content, (
        "pytest-xdist must be added to requirements-dev.txt for parallel execution support"
    )


def test_addopts_has_n_auto() -> None:
    """addopts must contain '-n auto' to enable parallel test execution.

    Running 1800+ tests sequentially takes ~66s; xdist typically halves that.
    """
    addopts = _load_addopts()
    addopts_str = " ".join(addopts)
    assert "-n auto" in addopts_str, (
        f"addopts must contain '-n auto' for parallel execution; current: {addopts}"
    )


def test_qa_tests_have_xdist_group_marker() -> None:
    """Filesystem-touching integration tests must carry @pytest.mark.xdist_group.

    Without xdist_group, parallel workers may collide on the same tmp_path
    or workspace files, causing flaky failures.
    """
    repo_root = Path(__file__).parent.parent.parent.parent
    qa_path = repo_root / "tests" / "mcp_server" / "integration" / "test_qa.py"
    content = qa_path.read_text(encoding="utf-8")
    assert "xdist_group" in content, (
        "tests/mcp_server/integration/test_qa.py must use "
        "pytest.mark.xdist_group to prevent worker collisions under -n auto"
    )

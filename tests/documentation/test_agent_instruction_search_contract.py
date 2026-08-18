"""Contract tests for active agent instructions and tracked consumers.

These tests keep host-specific authoritative sources aligned with their workspace
consumers while preventing removed MCP tools from returning to active contracts.
"""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parents[2]
REMOVED_TOOL = "search_documentation"

ACTIVE_AGENT_PATHS = (
    Path("AGENTS.md"),
    Path(".agents/AGENTS.md"),
    Path("docs/agents/codex/AGENTS.md"),
    Path("docs/agents/vscode/copilot/AGENTS.md"),
    Path("docs/agents/antigravity/AGENTS.md"),
    Path("docs/agents/codex/rules/research.agent.md"),
    Path(".agents/rules/research.agent.md"),
    Path("docs/agents/vscode/copilot/.github/agents/co.agent.md"),
    Path("docs/agents/vscode/copilot/.github/agents/qa.agent.md"),
    Path(".github/agents/co.agent.md"),
    Path(".github/agents/qa.agent.md"),
)

HOST_NATIVE_SEARCH_PATHS = ACTIVE_AGENT_PATHS[:7]

SOURCE_CONSUMER_PAIRS = (
    (Path("docs/agents/vscode/copilot/AGENTS.md"), Path("AGENTS.md")),
    (Path("docs/agents/codex/AGENTS.md"), Path(".agents/AGENTS.md")),
    (
        Path("docs/agents/codex/rules/research.agent.md"),
        Path(".agents/rules/research.agent.md"),
    ),
    (
        Path("docs/agents/vscode/copilot/.github/agents/co.agent.md"),
        Path(".github/agents/co.agent.md"),
    ),
    (
        Path("docs/agents/vscode/copilot/.github/agents/qa.agent.md"),
        Path(".github/agents/qa.agent.md"),
    ),
)


def _read(relative_path: Path) -> str:
    """Read one repository-relative agent asset."""

    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


@pytest.mark.parametrize("relative_path", ACTIVE_AGENT_PATHS)
def test_active_agent_contracts_do_not_reference_removed_tool(
    relative_path: Path,
) -> None:
    """Active instructions and restricted allowlists omit the removed tool."""

    assert REMOVED_TOOL not in _read(relative_path), str(relative_path)


@pytest.mark.parametrize("relative_path", HOST_NATIVE_SEARCH_PATHS)
def test_active_search_guidance_uses_host_native_repository_search(
    relative_path: Path,
) -> None:
    """Instruction surfaces explicitly direct agents to host-native search."""

    content = _read(relative_path).lower()
    assert "host-native repository search" in content, str(relative_path)


@pytest.mark.parametrize(("source_path", "consumer_path"), SOURCE_CONSUMER_PAIRS)
def test_authoritative_agent_sources_match_tracked_consumers(
    source_path: Path,
    consumer_path: Path,
) -> None:
    """Each tracked workspace consumer exactly matches its source asset."""

    assert _read(consumer_path) == _read(source_path), (
        f"{consumer_path} has drifted from {source_path}"
    )

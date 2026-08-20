"""Contract tests for active agent instructions and tracked consumers.

These tests keep host-specific authoritative sources aligned with every tracked
workspace consumer while protecting durable search and QA authority boundaries.
"""

from collections.abc import Iterator
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

QA_ENTRYPOINT_PATHS = (
    Path("docs/agents/codex/rules/qa.agent.md"),
    Path(".agents/rules/qa.agent.md"),
    Path("docs/agents/codex/skills/pgmcp-qa/SKILL.md"),
    Path(".agents/skills/pgmcp-qa/SKILL.md"),
    Path("docs/agents/antigravity/rules/qa.agent.md"),
    Path("docs/agents/vscode/copilot/.github/agents/qa.agent.md"),
    Path(".github/agents/qa.agent.md"),
)

QA_BOOTSTRAP_MARKERS = (
    "unverified context",
    "not binding",
    "direct evidence",
    "findings-only",
    "independent qa",
    "go/nogo",
)


def _read(relative_path: Path) -> str:
    """Read one repository-relative agent asset."""

    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def _files_below(relative_root: Path) -> Iterator[Path]:
    """Yield repository-relative files below an authoritative source root."""

    absolute_root = REPO_ROOT / relative_root
    for source_path in sorted(path for path in absolute_root.rglob("*") if path.is_file()):
        yield source_path.relative_to(REPO_ROOT)


def _source_consumer_pairs() -> tuple[tuple[Path, Path], ...]:
    """Build the complete tracked source-consumer topology."""

    codex_root = Path("docs/agents/codex")
    pairs = [
        (source_path, Path(".agents") / source_path.relative_to(codex_root))
        for source_path in _files_below(codex_root)
    ]

    vscode_root = Path("docs/agents/vscode/copilot")
    pairs.append((vscode_root / "AGENTS.md", Path("AGENTS.md")))
    for source_root in (
        vscode_root / ".github/agents",
        vscode_root / ".github/prompts",
    ):
        pairs.extend(
            (source_path, source_path.relative_to(vscode_root))
            for source_path in _files_below(source_root)
        )

    return tuple(pairs)


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


@pytest.mark.parametrize(("source_path", "consumer_path"), _source_consumer_pairs())
def test_authoritative_agent_sources_match_tracked_consumers(
    source_path: Path,
    consumer_path: Path,
) -> None:
    """Every tracked workspace consumer exactly matches its source asset."""

    assert (REPO_ROOT / consumer_path).is_file(), (
        f"{consumer_path} is missing for authoritative source {source_path}"
    )
    assert _read(consumer_path) == _read(source_path), (
        f"{consumer_path} has drifted from {source_path}"
    )


@pytest.mark.parametrize("relative_path", QA_ENTRYPOINT_PATHS)
def test_qa_entrypoints_bootstrap_evidence_and_invocation_authority(
    relative_path: Path,
) -> None:
    """QA entrypoints reject anchoring before declaring their mission or startup."""

    content = _read(relative_path).lower()
    bootstrap_position = content.find("## evidence precedence")
    later_section_positions = tuple(
        position
        for heading in ("## mission", "## start the session")
        if (position := content.find(heading)) >= 0
    )

    assert bootstrap_position >= 0, str(relative_path)
    assert later_section_positions, str(relative_path)
    assert bootstrap_position < min(later_section_positions), str(relative_path)
    for marker in QA_BOOTSTRAP_MARKERS:
        assert marker in content[: min(later_section_positions)], (
            f"{relative_path} is missing early QA marker: {marker}"
        )

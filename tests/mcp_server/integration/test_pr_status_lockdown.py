# tests/mcp_server/integration/test_pr_status_lockdown.py
# template=unit_test version=cycle6-red created=2026-04-23T00:00Z updated=
"""
Integration tests for PR-status lockdown via dynamic category enforcement (issue #283 C6).

Verifies that:
  1. Every branch-mutating tool is configured under categories.branch_mutating in enforcement.yaml.
  3. EnforcementRunner blocks all 17 tools when PRStatus.OPEN.
  4. EnforcementRunner allows all 17 tools when PRStatus.ABSENT.
  5. MergePRTool is explicitly NOT configured under branch_mutating (escape hatch).

@layer: Tests (Integration)
@dependencies: [pytest, unittest.mock,
    mcp_server.tools.git_tools,
    mcp_server.tools.git_pull_tool,
    mcp_server.tools.safe_edit_tool,
    mcp_server.tools.code_tools,
    mcp_server.tools.scaffold_artifact,
    mcp_server.tools.project_tools,
    mcp_server.tools.phase_tools,
    mcp_server.tools.cycle_tools,
    mcp_server.tools.pr_tools,
    mcp_server.managers.enforcement_runner,
    mcp_server.core.interfaces]
@responsibilities:
    - Verify config category mapping for all 17 branch-mutating tools
    - Verify EnforcementRunner dispatches check_pr_status for all 17 via dynamic category
    - Verify MergePRTool escape hatch is preserved
"""

from __future__ import annotations

# Standard library
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

# Third-party
import pytest

# Project modules
from mcp_server.config.loader import ConfigLoader
from mcp_server.core.exceptions import ValidationError
from mcp_server.core.interfaces import ICoreTool, IPRStatusReader, PRStatus
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.enforcement_runner import EnforcementContext, EnforcementRunner
from mcp_server.managers.state_repository import FileStateRepository
from mcp_server.tools.cycle_tools import ForceCycleTransitionTool, TransitionCycleTool
from mcp_server.tools.git_pull_tool import GitPullTool
from mcp_server.tools.git_tools import (
    CreateBranchTool,
    GitCommitTool,
    GitDeleteBranchTool,
    GitMergeTool,
    GitPushTool,
    GitRestoreTool,
)
from mcp_server.tools.phase_tools import ForcePhaseTransitionTool, TransitionPhaseTool
from mcp_server.tools.pr_tools import MergePRTool, SubmitPRTool
from mcp_server.tools.project_tools import (
    InitializeProjectTool,
    SavePlanningDeliverablesTool,
    UpdatePlanningDeliverablesTool,
)
from mcp_server.tools.safe_edit_tool import SafeEditTool
from mcp_server.tools.scaffold_artifact import ScaffoldArtifactTool
from tests.mcp_server.test_support import get_default_server_root

if TYPE_CHECKING:
    pass

_REPO_ROOT = Path(__file__).parent.parent.parent.parent

# ---------------------------------------------------------------------------
# Parametrize: the complete list of 17 branch-mutating tools
# ---------------------------------------------------------------------------
BRANCH_MUTATING_TOOLS: list[type[Any]] = [
    # git_tools
    CreateBranchTool,
    GitCommitTool,
    GitRestoreTool,
    GitPushTool,
    GitMergeTool,
    GitDeleteBranchTool,
    # git_pull_tool
    GitPullTool,
    # safe_edit_tool
    SafeEditTool,
    # scaffold_artifact
    ScaffoldArtifactTool,
    # project_tools
    InitializeProjectTool,
    SavePlanningDeliverablesTool,
    UpdatePlanningDeliverablesTool,
    # phase_tools
    TransitionPhaseTool,
    ForcePhaseTransitionTool,
    # cycle_tools
    TransitionCycleTool,
    ForceCycleTransitionTool,
    # pr_tools
    SubmitPRTool,
]

_TOOL_IDS = [t.__name__ for t in BRANCH_MUTATING_TOOLS]

assert len(BRANCH_MUTATING_TOOLS) == 17, (
    f"Expected 17 branch-mutating tools, got {len(BRANCH_MUTATING_TOOLS)}"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pr_reader(status: PRStatus) -> IPRStatusReader:
    reader = MagicMock(spec=IPRStatusReader)
    reader.get_pr_status.return_value = status
    return reader


def _make_runner(pr_status: PRStatus, tmp_path: Path) -> EnforcementRunner:
    """Build an EnforcementRunner with the live enforcement.yaml and a mocked PR reader."""
    enforcement_yaml = _REPO_ROOT / get_default_server_root() / "config" / "enforcement.yaml"
    loader = ConfigLoader(config_root=_REPO_ROOT / get_default_server_root() / "config")
    config = loader.load_enforcement_config(config_path=enforcement_yaml)
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=config,
        git_config=loader.load_git_config(),
        pr_status_reader=_make_pr_reader(pr_status),
        server_root=tmp_path,
        state_reader=FileStateRepository(state_file=tmp_path / "state.json"),
    )


# ---------------------------------------------------------------------------
# 1. Inheritance — must FAIL in RED for 17/17 tools
# ---------------------------------------------------------------------------


class TestBranchMutatingToolRegistration:
    """Each branch-mutating tool must be configured in enforcement.yaml categories."""

    @pytest.mark.parametrize("tool_cls", BRANCH_MUTATING_TOOLS, ids=_TOOL_IDS)
    def test_is_registered_in_categories(self, tool_cls: type[ICoreTool[Any, Any]]) -> None:
        assert tool_cls.name.fget is not None
        tool_name = tool_cls.name.fget(None)
        loader = ConfigLoader(config_root=_REPO_ROOT / get_default_server_root() / "config")
        enforcement_yaml = _REPO_ROOT / get_default_server_root() / "config" / "enforcement.yaml"
        config = loader.load_enforcement_config(config_path=enforcement_yaml)
        assert tool_name in config.categories.get("branch_mutating", []), (
            f"Tool '{tool_name}' ({tool_cls.__name__}) must be configured under "
            f"categories.branch_mutating in enforcement.yaml"
        )


# ---------------------------------------------------------------------------
# 2. Escape hatch — MergePRTool must NOT be a BranchMutatingTool
# ---------------------------------------------------------------------------


class TestMergePREscapeHatch:
    """MergePRTool is the escape hatch — it must NOT be a branch-mutating tool."""

    def test_merge_pr_tool_is_not_branch_mutating(self) -> None:
        loader = ConfigLoader(config_root=_REPO_ROOT / get_default_server_root() / "config")
        config = loader.load_enforcement_config()
        assert MergePRTool.name.fget is not None
        tool_name = MergePRTool.name.fget(None)
        assert tool_name not in config.categories.get("branch_mutating", []), (
            f"MergePRTool ({tool_name}) must NOT be configured under branch_mutating; "
            "it is the escape hatch that clears PRStatus.OPEN"
        )


# ---------------------------------------------------------------------------
# 3. Enforcement: blocked when PRStatus.OPEN
# ---------------------------------------------------------------------------


class TestBranchMutatingToolBlockedWhenPROpen:
    """EnforcementRunner must block every branch-mutating tool when PRStatus.OPEN."""

    @pytest.mark.parametrize("tool_cls", BRANCH_MUTATING_TOOLS, ids=_TOOL_IDS)
    def test_blocked_when_pr_open(
        self, tool_cls: type[ICoreTool[Any, Any]], tmp_path: Path
    ) -> None:
        runner = _make_runner(PRStatus.OPEN, tmp_path)
        assert tool_cls.name.fget is not None
        tool_name = tool_cls.name.fget(None)
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=tool_name,
            params=SimpleNamespace(),
        )
        note_context = NoteContext()

        with pytest.raises(ValidationError, match="open PR"):
            runner.run(
                event=tool_name,
                timing="pre",
                enforcement_ctx=ctx,
                note_context=note_context,
            )


# ---------------------------------------------------------------------------
# 4. Enforcement: allowed when PRStatus.ABSENT
# ---------------------------------------------------------------------------


class TestBranchMutatingToolAllowedWhenPRAbsent:
    """EnforcementRunner must NOT block branch-mutating tools when PRStatus.ABSENT."""

    @pytest.mark.parametrize("tool_cls", BRANCH_MUTATING_TOOLS, ids=_TOOL_IDS)
    def test_allowed_when_pr_absent(
        self, tool_cls: type[ICoreTool[Any, Any]], tmp_path: Path
    ) -> None:
        runner = _make_runner(PRStatus.ABSENT, tmp_path)
        assert tool_cls.name.fget is not None
        tool_name = tool_cls.name.fget(None)
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=tool_name,
            params=SimpleNamespace(),
        )
        note_context = NoteContext()

        # Must not raise ValidationError from check_pr_status (other rules may still fire)
        try:
            runner.run(
                event=tool_name,
                timing="pre",
                enforcement_ctx=ctx,
                note_context=note_context,
            )
        except ValidationError as exc:
            assert "open PR" not in str(exc), (
                f"{tool_cls.__name__} must not be blocked by check_pr_status when "
                f"PRStatus.ABSENT, but got: {exc}"
            )

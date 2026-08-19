from tests.mcp_server.test_support import get_default_server_root

# tests/mcp_server/integration/test_ready_phase_enforcement.py
# template=unit_test version= created=2026-04-09T00:00Z updated=
"""
Integration tests for ready-phase enforcement (issue #283).

Verifies the full enforcement dispatch path:
  EnforcementRunner.run(event=tool.enforcement_event, ...) produces
  the expected outcome for submit_pr events.

C6 update: removed legacy git_add_or_commit + ExclusionNote tests
(exclude_branch_local_artifacts pattern deleted in C6 GREEN).
Removed MergeReadinessContext param from _make_runner since
check_phase_readiness reads state.json directly.

@layer: Tests (Integration)
@dependencies: [json, pathlib, pytest,
    mcp_server.tools.git_tools, mcp_server.tools.pr_tools,
    mcp_server.managers.enforcement_runner,
    mcp_server.config.loader]
@responsibilities:
    - Test enforcement_event class variable on GitCommitTool and SubmitPRTool
    - Test submit_pr pre-enforcement blocks PR outside pr_allowed_phase
    - Test submit_pr pre-enforcement allows PR in pr_allowed_phase
"""

# Standard library
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

# Third-party
import pytest

# Project modules
from mcp_server.config.loader import ConfigLoader
from mcp_server.core.exceptions import ValidationError
from mcp_server.core.interfaces import IContextLoadedReader, IPRStatusReader, PRStatus
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.enforcement_runner import (
    EnforcementContext,
    EnforcementRunner,
)
from mcp_server.managers.state_repository import FileStateRepository
from mcp_server.tools.git_tools import GitCommitTool
from mcp_server.tools.pr_tools import SubmitPRTool

_REPO_ROOT = Path(__file__).parent.parent.parent.parent

_STATE_JSON = f"{get_default_server_root()}/state.json"


def _write_state(tmp_path: Path, current_phase: str) -> None:
    state_dir = tmp_path / get_default_server_root()
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "state.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "branch": "refactor/283-test",
                "workflow_name": "refactor",
                "current_phase": current_phase,
            }
        ),
        encoding="utf-8",
    )


def _make_runner(tmp_path: Path) -> EnforcementRunner:
    """Build EnforcementRunner backed by the live enforcement.yaml."""
    enforcement_yaml = _REPO_ROOT / get_default_server_root() / "config" / "enforcement.yaml"
    loader = ConfigLoader(config_root=_REPO_ROOT / get_default_server_root() / "config")
    config = loader.load_enforcement_config(config_path=enforcement_yaml)

    pr_reader = MagicMock(spec=IPRStatusReader)
    pr_reader.get_pr_status.return_value = PRStatus.ABSENT

    context_reader = MagicMock(spec=IContextLoadedReader)
    context_reader.is_context_loaded.return_value = True

    return EnforcementRunner(
        workspace_root=tmp_path,
        config=config,
        git_config=loader.load_git_config(),
        pr_status_reader=pr_reader,
        context_loaded_reader=context_reader,
        server_root=tmp_path / get_default_server_root(),
        state_reader=FileStateRepository(
            state_file=tmp_path / get_default_server_root() / "state.json"
        ),
    )


class TestReadyPhaseEnforcement:
    """Integration tests for the ready-phase enforcement path (issue #283)."""

    def test_git_commit_tool_enforcement_event(self) -> None:
        """GitCommitTool.enforcement_event matches the tool name in enforcement.yaml."""
        assert GitCommitTool.enforcement_event == "git_add_or_commit"

    def test_submit_pr_tool_enforcement_event(self) -> None:
        """SubmitPRTool.enforcement_event matches the tool name in enforcement.yaml."""
        assert SubmitPRTool.enforcement_event == "submit_pr"

    def test_submit_pr_blocked_outside_pr_allowed_phase(self, tmp_path: Path) -> None:
        """submit_pr pre-enforcement raises ValidationError when phase != pr_allowed_phase."""
        _write_state(tmp_path, "implementation")
        runner = _make_runner(tmp_path)
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=SubmitPRTool.name,
            params=SimpleNamespace(),
        )
        note_context = NoteContext()
        with pytest.raises(ValidationError, match="ready"):
            runner.run(
                event=SubmitPRTool.enforcement_event,  # type: ignore[arg-type]
                timing="pre",
                enforcement_ctx=ctx,
                note_context=note_context,
            )

    def test_submit_pr_allowed_in_pr_allowed_phase(self, tmp_path: Path) -> None:
        """submit_pr pre-enforcement returns no notes in ready phase."""
        _write_state(tmp_path, "ready")
        runner = _make_runner(tmp_path)
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name=SubmitPRTool.name,
            params=SimpleNamespace(),
        )
        note_context = NoteContext()
        runner.run(
            event=SubmitPRTool.enforcement_event,  # type: ignore[arg-type]
            timing="pre",
            enforcement_ctx=ctx,
            note_context=note_context,
        )

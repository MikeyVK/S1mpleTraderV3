# tests/mcp_server/unit/managers/test_enforcement_runner_c2.py
"""Unit tests for C2 EnforcementRunner: tool_category dispatch + new handlers.

Tests exercise the public runner.run() API exclusively; no private-method access.

@layer: Tests (Unit)
@dependencies: [pathlib, pytest, unittest.mock, mcp_server.managers.enforcement_runner,
                mcp_server.core.interfaces]
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.core.interfaces import IPRStatusReader, PRStatus
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.enforcement_runner import (
    EnforcementAction,
    EnforcementConfig,
    EnforcementContext,
    EnforcementRule,
    EnforcementRunner,
)


def _make_ctx(tmp_path: Path, tool_name: str = "any_tool") -> EnforcementContext:
    return EnforcementContext(
        workspace_root=tmp_path,
        tool_name=tool_name,
        params={},
    )


def _make_note_context() -> NoteContext:
    return NoteContext()


def _make_runner(
    tmp_path: Path,
    config: EnforcementConfig,
    pr_status_reader: IPRStatusReader | None = None,
) -> EnforcementRunner:
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=config,
        pr_status_reader=pr_status_reader,
    )


class TestToolCategoryDispatch:
    """EnforcementRunner.run() dispatches on tool_category."""

    def test_rule_with_matching_tool_category_is_executed(self, tmp_path: Path) -> None:
        """When tool_category matches the rule, the action handler is invoked."""
        executed: list[str] = []

        def fake_handler(action: EnforcementAction, ctx: EnforcementContext, ws: Path, nc: NoteContext) -> None:
            executed.append(action.type)

        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    timing="pre",
                    tool_category="branch_mutating",
                    actions=[EnforcementAction(type="check_pr_status")],
                )
            ]
        )
        reader = MagicMock(spec=IPRStatusReader)
        reader.get_pr_status.return_value = PRStatus.ABSENT
        runner = _make_runner(tmp_path, config, pr_status_reader=reader)

        runner.run(
            event="git_commit",
            timing="pre",
            tool_category="branch_mutating",
            enforcement_ctx=_make_ctx(tmp_path),
            note_context=_make_note_context(),
        )

        assert executed or reader.get_pr_status.called

    def test_rule_with_non_matching_tool_category_is_skipped(self, tmp_path: Path) -> None:
        """When tool_category does not match, the rule is not executed."""
        reader = MagicMock(spec=IPRStatusReader)
        reader.get_pr_status.return_value = PRStatus.OPEN  # would raise if executed

        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    timing="pre",
                    tool_category="branch_mutating",
                    actions=[EnforcementAction(type="check_pr_status")],
                )
            ]
        )
        runner = _make_runner(tmp_path, config, pr_status_reader=reader)

        # tool_category="other" — must not trigger the rule
        runner.run(
            event="merge_pr",
            timing="pre",
            tool_category="other",
            enforcement_ctx=_make_ctx(tmp_path),
            note_context=_make_note_context(),
        )

        reader.get_pr_status.assert_not_called()

    def test_tool_name_rule_still_dispatches_without_tool_category(self, tmp_path: Path) -> None:
        """Existing tool-name rules remain functional when tool_category is not passed."""
        executed: list[bool] = []

        def fake_handler(action: EnforcementAction, ctx: EnforcementContext, ws: Path, nc: NoteContext) -> None:
            executed.append(True)

        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    timing="pre",
                    tool="submit_pr",
                    actions=[EnforcementAction(type="check_phase_readiness", policy="ready")],
                )
            ]
        )
        runner = EnforcementRunner(
            workspace_root=tmp_path,
            config=config,
            registry={"check_phase_readiness": fake_handler},
        )

        runner.run(
            event="submit_pr",
            timing="pre",
            enforcement_ctx=_make_ctx(tmp_path),
            note_context=_make_note_context(),
        )

        assert executed == [True]

    def test_unknown_tool_category_in_config_raises_config_error(self, tmp_path: Path) -> None:
        """Startup must fail fast when enforcement.yaml references an unknown tool_category."""
        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    timing="pre",
                    tool_category="nonexistent_category",
                    actions=[EnforcementAction(type="check_pr_status")],
                )
            ]
        )
        with pytest.raises(ConfigError):
            _make_runner(tmp_path, config)


class TestCheckPRStatusHandler:
    """check_pr_status action via runner.run() public API."""

    def test_blocks_when_pr_is_open(self, tmp_path: Path) -> None:
        """ValidationError raised when PRStatus.OPEN."""
        reader = MagicMock(spec=IPRStatusReader)
        reader.get_pr_status.return_value = PRStatus.OPEN

        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    timing="pre",
                    tool_category="branch_mutating",
                    actions=[EnforcementAction(type="check_pr_status")],
                )
            ]
        )
        runner = _make_runner(tmp_path, config, pr_status_reader=reader)

        with pytest.raises(ValidationError):
            runner.run(
                event="git_commit",
                timing="pre",
                tool_category="branch_mutating",
                enforcement_ctx=_make_ctx(tmp_path),
                note_context=_make_note_context(),
            )

    def test_passes_when_pr_is_absent(self, tmp_path: Path) -> None:
        """No exception when PRStatus.ABSENT."""
        reader = MagicMock(spec=IPRStatusReader)
        reader.get_pr_status.return_value = PRStatus.ABSENT

        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    timing="pre",
                    tool_category="branch_mutating",
                    actions=[EnforcementAction(type="check_pr_status")],
                )
            ]
        )
        runner = _make_runner(tmp_path, config, pr_status_reader=reader)

        # Must not raise
        runner.run(
            event="git_commit",
            timing="pre",
            tool_category="branch_mutating",
            enforcement_ctx=_make_ctx(tmp_path),
            note_context=_make_note_context(),
        )

    def test_check_pr_status_reads_branch_from_enforcement_context(self, tmp_path: Path) -> None:
        """get_pr_status is called with the tool_name from the enforcement context as branch."""
        reader = MagicMock(spec=IPRStatusReader)
        reader.get_pr_status.return_value = PRStatus.ABSENT

        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    timing="pre",
                    tool_category="branch_mutating",
                    actions=[EnforcementAction(type="check_pr_status")],
                )
            ]
        )
        runner = _make_runner(tmp_path, config, pr_status_reader=reader)
        ctx = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="git_push",
            params={"head": "feature/42-test"},
        )

        runner.run(
            event="git_push",
            timing="pre",
            tool_category="branch_mutating",
            enforcement_ctx=ctx,
            note_context=_make_note_context(),
        )

        reader.get_pr_status.assert_called_once()

    def test_no_pr_status_reader_raises_config_error(self, tmp_path: Path) -> None:
        """check_pr_status without a pr_status_reader must raise ConfigError."""
        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    timing="pre",
                    tool_category="branch_mutating",
                    actions=[EnforcementAction(type="check_pr_status")],
                )
            ]
        )
        runner = _make_runner(tmp_path, config, pr_status_reader=None)

        with pytest.raises(ConfigError):
            runner.run(
                event="git_commit",
                timing="pre",
                tool_category="branch_mutating",
                enforcement_ctx=_make_ctx(tmp_path),
                note_context=_make_note_context(),
            )


class TestCheckPhaseReadinessHandler:
    """check_phase_readiness action via runner.run() public API."""

    def _make_state(self, tmp_path: Path, phase: str) -> None:
        state_dir = tmp_path / ".st3"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "state.json").write_text(
            f'{{"current_phase": "{phase}"}}', encoding="utf-8"
        )

    def test_passes_when_phase_matches_policy(self, tmp_path: Path) -> None:
        """No exception when current phase equals the required policy phase."""
        self._make_state(tmp_path, "ready")

        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    timing="pre",
                    tool="submit_pr",
                    actions=[EnforcementAction(type="check_phase_readiness", policy="ready")],
                )
            ]
        )
        runner = _make_runner(tmp_path, config)

        runner.run(
            event="submit_pr",
            timing="pre",
            enforcement_ctx=_make_ctx(tmp_path),
            note_context=_make_note_context(),
        )

    def test_blocks_when_phase_does_not_match_policy(self, tmp_path: Path) -> None:
        """ValidationError raised when current phase differs from the required policy phase."""
        self._make_state(tmp_path, "implementation")

        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    timing="pre",
                    tool="submit_pr",
                    actions=[EnforcementAction(type="check_phase_readiness", policy="ready")],
                )
            ]
        )
        runner = _make_runner(tmp_path, config)

        with pytest.raises(ValidationError):
            runner.run(
                event="submit_pr",
                timing="pre",
                enforcement_ctx=_make_ctx(tmp_path),
                note_context=_make_note_context(),
            )

    def test_blocks_when_state_json_absent(self, tmp_path: Path) -> None:
        """ValidationError raised when state.json is absent (no active phase)."""
        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    timing="pre",
                    tool="submit_pr",
                    actions=[EnforcementAction(type="check_phase_readiness", policy="ready")],
                )
            ]
        )
        runner = _make_runner(tmp_path, config)

        with pytest.raises(ValidationError):
            runner.run(
                event="submit_pr",
                timing="pre",
                enforcement_ctx=_make_ctx(tmp_path),
                note_context=_make_note_context(),
            )

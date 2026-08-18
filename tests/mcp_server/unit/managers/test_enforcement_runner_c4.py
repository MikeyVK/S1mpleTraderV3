# tests/mcp_server/unit/managers/test_enforcement_runner_c4.py
"""Unit tests for C4 EnforcementRunner: check_context_loaded handler.

Tests exercise the public runner.run() API exclusively; no private-method access.

@layer: Tests (Unit)
@dependencies: [pathlib, pytest, unittest.mock, mcp_server.managers.enforcement_runner,
                mcp_server.core.interfaces]
"""

from __future__ import annotations
from tests.mcp_server.test_support import get_default_server_root


from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.core.interfaces import IContextLoadedReader
from mcp_server.core.operation_notes import Note, NoteContext
from mcp_server.managers.enforcement_runner import (
    EnforcementAction,
    EnforcementConfig,
    EnforcementContext,
    EnforcementRule,
    EnforcementRunner,
)
from mcp_server.managers.state_repository import FileStateRepository
from mcp_server.schemas import GitConfig

# Real GitConfig so extract_issue_number("feature/42-test") returns 42,
# matching the issue_number written by _write_state_json.
_GIT_CONFIG = GitConfig(
    branch_types=["feature", "bug", "refactor", "docs", "hotfix", "epic"],
    protected_branches=["main"],
    branch_name_pattern=r"^[a-z0-9-]+$",
    commit_types=["feat", "fix", "docs", "chore"],
    default_base_branch="main",
    issue_title_max_length=72,
)


def _make_runner_c4(
    tmp_path: Path,
    config: EnforcementConfig,
    context_loaded_reader: IContextLoadedReader | None = None,
) -> EnforcementRunner:
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=config,
        git_config=_GIT_CONFIG,
        server_root=tmp_path / get_default_server_root(),
        context_loaded_reader=context_loaded_reader,
        state_reader=FileStateRepository(
            state_file=tmp_path / get_default_server_root() / "state.json"
        ),
    )


def _make_ctx(
    tmp_path: Path,
    tool_name: str = "some_tool",
    current_branch: str = "feature/42-test",
) -> EnforcementContext:
    return EnforcementContext(
        workspace_root=tmp_path,
        tool_name=tool_name,
        params={"current_branch": current_branch},
    )


def _make_note_context() -> NoteContext:
    return NoteContext()


def _write_state_json(tmp_path: Path) -> None:
    """Create a minimal state.json so the bootstrap predicate does not trigger."""
    server_root = tmp_path / get_default_server_root()
    server_root.mkdir(parents=True, exist_ok=True)
    (server_root / "state.json").write_text(
        '{"schema_version": "1.0.0", "branch": "feature/42-test", '
        '"current_phase": "implementation", "issue_number": 42, '
        '"workflow_name": "feature"}',
        encoding="utf-8",
    )


def _make_check_context_loaded_config(
    tool: str = "some_tool",
    exempt_tools: list[str] | None = None,
    enabled: bool = True,
) -> EnforcementConfig:
    return EnforcementConfig(
        enforcement=[
            EnforcementRule(
                event_source="tool",
                tool=tool,
                timing="pre",
                actions=[
                    EnforcementAction(
                        type="check_context_loaded",
                        exempt_tools=exempt_tools or [],
                        enabled=enabled,
                    )
                ],
            )
        ]
    )


class TestCheckContextLoadedHandler:
    """check_context_loaded action via runner.run() public API."""

    def test_raises_config_error_when_reader_not_configured(self, tmp_path: Path) -> None:
        """Missing context_loaded_reader must raise ConfigError at execution time."""
        _write_state_json(tmp_path)
        config = _make_check_context_loaded_config()
        runner = _make_runner_c4(tmp_path, config, context_loaded_reader=None)

        with pytest.raises(ConfigError):
            runner.run(
                event="some_tool",
                timing="pre",
                enforcement_ctx=_make_ctx(tmp_path),
                note_context=_make_note_context(),
            )

    def test_passes_when_context_is_loaded(self, tmp_path: Path) -> None:
        """No exception when reader reports context already loaded for branch."""
        _write_state_json(tmp_path)
        reader = MagicMock(spec=IContextLoadedReader)
        reader.is_context_loaded.return_value = True
        config = _make_check_context_loaded_config()
        runner = _make_runner_c4(tmp_path, config, context_loaded_reader=reader)

        runner.run(
            event="some_tool",
            timing="pre",
            enforcement_ctx=_make_ctx(tmp_path),
            note_context=_make_note_context(),
        )

        reader.is_context_loaded.assert_called_once_with("feature/42-test")

    def test_raises_validation_error_when_context_not_loaded(self, tmp_path: Path) -> None:
        """ValidationError raised when reader reports context not yet loaded."""
        _write_state_json(tmp_path)
        reader = MagicMock(spec=IContextLoadedReader)
        reader.is_context_loaded.return_value = False
        config = _make_check_context_loaded_config()
        runner = _make_runner_c4(tmp_path, config, context_loaded_reader=reader)

        with pytest.raises(ValidationError):
            runner.run(
                event="some_tool",
                timing="pre",
                enforcement_ctx=_make_ctx(tmp_path),
                note_context=_make_note_context(),
            )

    def test_produces_suggestion_note_on_block(self, tmp_path: Path) -> None:
        """SuggestionNote present in note_context when ValidationError is raised."""
        _write_state_json(tmp_path)
        reader = MagicMock(spec=IContextLoadedReader)
        reader.is_context_loaded.return_value = False
        config = _make_check_context_loaded_config()
        runner = _make_runner_c4(tmp_path, config, context_loaded_reader=reader)
        note_context = _make_note_context()

        with pytest.raises(ValidationError):
            runner.run(
                event="some_tool",
                timing="pre",
                enforcement_ctx=_make_ctx(tmp_path),
                note_context=note_context,
            )

        notes = [n for n in note_context.of_type(Note) if n.key == "load_context_suggestion"]
        assert len(notes) >= 1

    def test_exempt_tool_bypasses_when_not_loaded(self, tmp_path: Path) -> None:
        """Tool listed in exempt_tools passes even when context is not loaded.

        exempt_tools is checked before the bootstrap predicate, so no state.json needed.
        """
        reader = MagicMock(spec=IContextLoadedReader)
        reader.is_context_loaded.return_value = False
        config = _make_check_context_loaded_config(tool="some_tool", exempt_tools=["some_tool"])
        runner = _make_runner_c4(tmp_path, config, context_loaded_reader=reader)

        # Must not raise
        runner.run(
            event="some_tool",
            timing="pre",
            enforcement_ctx=_make_ctx(tmp_path, tool_name="some_tool"),
            note_context=_make_note_context(),
        )

    def test_exempt_tool_bypasses_when_reader_none(self, tmp_path: Path) -> None:
        """Tool in exempt_tools bypasses even when no reader is configured.

        exempt_tools is checked before the bootstrap predicate, so no state.json needed.
        """
        config = _make_check_context_loaded_config(tool="some_tool", exempt_tools=["some_tool"])
        runner = _make_runner_c4(tmp_path, config, context_loaded_reader=None)

        # Must not raise ConfigError — exempt_tools checked before reader access
        runner.run(
            event="some_tool",
            timing="pre",
            enforcement_ctx=_make_ctx(tmp_path, tool_name="some_tool"),
            note_context=_make_note_context(),
        )

    def test_gate_disabled_when_enabled_false(self, tmp_path: Path) -> None:
        """No error raised when action.enabled=False, regardless of reader or context state.

        Disabling a gate requires an explicit YAML decision (explicit over implicit).
        """
        _write_state_json(tmp_path)
        # No reader injected — would raise ConfigError if enabled=True
        config = _make_check_context_loaded_config(enabled=False)
        runner = _make_runner_c4(tmp_path, config, context_loaded_reader=None)

        # Must not raise — gate is explicitly disabled
        runner.run(
            event="some_tool",
            timing="pre",
            enforcement_ctx=_make_ctx(tmp_path),
            note_context=_make_note_context(),
        )

    def test_bootstrap_passes_when_no_state_json(self, tmp_path: Path) -> None:
        """Gate is inactive when state.json does not exist (bootstrap mode).

        No state.json means no active phase has been initialised.
        The gate must return silently rather than raise, even when context
        is not loaded, so that initialize_project is never blocked.
        """
        reader = MagicMock(spec=IContextLoadedReader)
        reader.is_context_loaded.return_value = False
        config = _make_check_context_loaded_config()
        # server_root = tmp_path / get_default_server_root() per _make_runner_c4
        # — no state.json there
        runner = _make_runner_c4(tmp_path, config, context_loaded_reader=reader)

        # Must not raise — bootstrap path returns silently
        runner.run(
            event="some_tool",
            timing="pre",
            enforcement_ctx=_make_ctx(tmp_path),
            note_context=_make_note_context(),
        )

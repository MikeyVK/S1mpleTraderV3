# tests/mcp_server/unit/managers/test_enforcement_runner.py
# template=unit_test version=3d15d309 created=2026-03-13T10:02Z updated=
"""Unit tests for enforcement runner configuration and dispatch.

@layer: Tests (Unit)
@dependencies: [pathlib, pytest, unittest.mock, mcp_server.managers.enforcement_runner]
"""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from mcp_server.core.exceptions import ConfigError, ValidationError
from mcp_server.managers.enforcement_runner import (
    EnforcementAction,
    EnforcementConfig,
    EnforcementContext,
    EnforcementRule,
    EnforcementRunner,
)


def _write_enforcement_file(tmp_path: Path, content: str) -> None:
    config_dir = tmp_path / ".st3" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "enforcement.yaml").write_text(content, encoding="utf-8")


def _make_runner(
    tmp_path: Path,
    config: EnforcementConfig,
    registry: dict[str, object] | None = None,
) -> EnforcementRunner:
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=config,
        git_manager=MagicMock(),
        project_manager=MagicMock(),
        state_engine=MagicMock(),
        registry=registry,
    )


class TestEnforcementRunner:
    """Test suite for Cycle 5 enforcement loading and dispatch."""

    def test_constructor_raises_config_error_for_unknown_action_type(self, tmp_path: Path) -> None:
        """Unknown action types must fail fast at startup."""
        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    tool="create_branch",
                    timing="pre",
                    actions=[EnforcementAction(type="unknown_action")],
                )
            ]
        )

        with pytest.raises(ConfigError, match="unknown_action"):
            _make_runner(tmp_path, config)

    def test_run_dispatches_registered_handler_for_matching_tool_event(
        self, tmp_path: Path
    ) -> None:
        """Matching tool rules must dispatch their registered handlers."""
        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    tool="transition_phase",
                    timing="post",
                    actions=[
                        EnforcementAction(type="commit_state_files", paths=[".st3/state.json"])
                    ],
                )
            ]
        )
        calls: list[tuple[str, str]] = []

        def fake_handler(
            action: EnforcementAction,
            context: EnforcementContext,
            workspace_root: Path,
        ) -> str:
            calls.append((action.type, context.tool_name))
            assert workspace_root == tmp_path
            return "handled"

        runner = _make_runner(
            tmp_path,
            config,
            registry={"commit_state_files": fake_handler},
        )

        notes = runner.run(
            event="transition_phase",
            timing="post",
            context=EnforcementContext(
                workspace_root=tmp_path,
                tool_name="transition_phase",
                params=SimpleNamespace(branch="feature/257-reorder-workflow-phases"),
            ),
        )

        assert notes == ["handled"]
        assert calls == [("commit_state_files", "transition_phase")]

    def test_check_branch_policy_rejects_invalid_base_branch(self, tmp_path: Path) -> None:
        """Branch policy must block disallowed base branches."""
        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    tool="create_branch",
                    timing="pre",
                    actions=[
                        EnforcementAction(
                            type="check_branch_policy",
                            rules={"feature": ["main", "epic/*"]},
                        )
                    ],
                )
            ]
        )
        runner = _make_runner(tmp_path, config)

        with pytest.raises(ValidationError, match="cannot be created from base"):
            runner.run(
                event="create_branch",
                timing="pre",
                context=EnforcementContext(
                    workspace_root=tmp_path,
                    tool_name="create_branch",
                    params=SimpleNamespace(
                        branch_type="feature",
                        base_branch="release/1.0",
                    ),
                ),
            )


class TestEnforcementSchemaValidation:
    """Direct schema validation coverage for enforcement config models."""

    def test_branch_policy_action_requires_rules(self) -> None:
        """check_branch_policy actions must declare at least one rule."""
        with pytest.raises(ValueError, match="requires non-empty rules"):
            EnforcementAction(type="check_branch_policy")

    def test_commit_state_files_action_requires_paths(self) -> None:
        """commit_state_files actions must declare tracked paths."""
        with pytest.raises(ValueError, match="requires non-empty paths"):
            EnforcementAction(type="commit_state_files")

    def test_delete_file_action_requires_path(self) -> None:
        """delete_file actions must declare a single target path."""
        with pytest.raises(ValueError, match="requires path"):
            EnforcementAction(type="delete_file")

    def test_tool_event_source_requires_tool_name(self) -> None:
        """Tool-triggered rules must include the tool name."""
        with pytest.raises(ValueError, match="requires tool"):
            EnforcementRule(event_source="tool", timing="pre")

    def test_phase_event_source_requires_phase_name(self) -> None:
        """Phase-triggered rules must include the phase name."""
        with pytest.raises(ValueError, match="requires phase"):
            EnforcementRule(event_source="phase", timing="post")

# tests\mcp_server\unit\managers\test_enforcement_runner.py
# template=unit_test version=3d15d309 created=2026-03-13T10:02Z updated=
"""Unit tests for enforcement runner configuration and dispatch."""

from pathlib import Path
from types import SimpleNamespace

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


class TestEnforcementRunner:
    """Test suite for Cycle 5 enforcement loading and dispatch."""

    def test_from_workspace_raises_config_error_for_unknown_action_type(self, tmp_path: Path) -> None:
        """Unknown action types must fail fast at startup."""
        _write_enforcement_file(
            tmp_path,
            """
            enforcement:
              - event_source: tool
                tool: create_branch
                timing: pre
                actions:
                  - type: unknown_action
            """,
        )

        with pytest.raises(ConfigError, match="unknown_action"):
            EnforcementRunner.from_workspace(tmp_path)

    def test_run_dispatches_registered_handler_for_matching_tool_event(self, tmp_path: Path) -> None:
        """Matching tool rules must dispatch their registered handlers."""
        config = EnforcementConfig(
            enforcement=[
                EnforcementRule(
                    event_source="tool",
                    tool="transition_phase",
                    timing="post",
                    actions=[EnforcementAction(type="commit_state_files", paths=[".st3/state.json"])],
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

        runner = EnforcementRunner(
            workspace_root=tmp_path,
            config=config,
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
        runner = EnforcementRunner(workspace_root=tmp_path, config=config)

        with pytest.raises(ValidationError, match="cannot be created from base"):
            runner.run(
                event="create_branch",
                timing="pre",
                context=EnforcementContext(
                    workspace_root=tmp_path,
                    tool_name="create_branch",
                    params=SimpleNamespace(branch_type="feature", base_branch="release/1.0"),
                ),
            )

# tests/mcp_server/integration/test_c5_cleanup_and_prstatus.py
"""C5 contract tests: CreatePRTool removal, enforcement.yaml cleanup,
GitHubManager.get_pr_status() real implementation, MergePRTool pr_status_writer.

@layer: Tests (Integration)
@responsibilities:
    - CreatePRTool and CreatePRInput are removed from pr_tools (D2 revised)
    - Dead create_pr enforcement rule removed from enforcement.yaml
    - GitHubManager.get_pr_status() queries GitHub API via adapter.list_prs()
    - MergePRTool sets PRStatus.ABSENT after successful merge
"""

from __future__ import annotations

import inspect
from pathlib import Path
from unittest.mock import MagicMock

import yaml

import mcp_server.tools.pr_tools as pr_tools_module
from mcp_server.core.interfaces import IPRStatusWriter, PRStatus
from mcp_server.managers.github_manager import GitHubManager
from mcp_server.schemas import GitConfig
from mcp_server.tools.pr_tools import MergePRInput, MergePRTool

_ENFORCEMENT_YAML = Path(__file__).parents[3] / ".st3" / "config" / "enforcement.yaml"


class TestCreatePRToolRemoval:
    """D2 (revised): CreatePRTool and CreatePRInput must be gone from pr_tools."""

    def test_create_pr_tool_class_removed(self) -> None:
        """CreatePRTool must no longer exist in pr_tools module (D2 revised)."""
        assert not hasattr(pr_tools_module, "CreatePRTool"), (
            "CreatePRTool is dead code after C5 — must be removed from pr_tools.py"
        )

    def test_create_pr_input_class_removed(self) -> None:
        """CreatePRInput must no longer exist in pr_tools module (D2 revised)."""
        assert not hasattr(pr_tools_module, "CreatePRInput"), (
            "CreatePRInput is dead code after C5 — must be removed from pr_tools.py"
        )

    def test_enforcement_yaml_has_no_create_pr_rule(self) -> None:
        """The create_pr enforcement rule must be removed (dead config for removed tool)."""
        config = yaml.safe_load(_ENFORCEMENT_YAML.read_text(encoding="utf-8"))
        create_pr_rules = [
            rule for rule in config["enforcement"] if rule.get("tool") == "create_pr"
        ]
        assert create_pr_rules == [], (
            "enforcement.yaml must not contain a rule for create_pr — tool is removed"
        )


class TestGitHubManagerGetPRStatus:
    """GitHubManager.get_pr_status() must query the GitHub API via adapter.list_prs()."""

    def test_get_pr_status_returns_open_when_open_pr_exists(self) -> None:
        """Returns PRStatus.OPEN when adapter.list_prs() returns a non-empty list."""
        adapter = MagicMock()
        mock_pr = MagicMock()
        mock_pr.head.ref = "feature/42-test"
        adapter.list_prs.return_value = [mock_pr]

        manager = GitHubManager(adapter=adapter)
        status = manager.get_pr_status("feature/42-test")

        assert status == PRStatus.OPEN
        adapter.list_prs.assert_called_once_with(state="open", head="feature/42-test")

    def test_get_pr_status_returns_absent_when_no_open_pr(self) -> None:
        """Returns PRStatus.ABSENT when adapter.list_prs() returns empty list."""
        adapter = MagicMock()
        adapter.list_prs.return_value = []

        manager = GitHubManager(adapter=adapter)
        status = manager.get_pr_status("feature/99-no-pr")

        assert status == PRStatus.ABSENT

    def test_get_pr_status_is_not_a_stub(self) -> None:
        """get_pr_status must not contain 'stub' in its source (C1 stub removed)."""
        source = inspect.getsource(GitHubManager.get_pr_status)
        assert "stub" not in source.lower(), (
            "GitHubManager.get_pr_status() must be the real implementation, not the C1 stub"
        )


class TestMergePRToolPRStatusWriter:
    """MergePRTool must write PRStatus.ABSENT after a successful merge."""

    def _make_merge_tool(
        self,
        manager: GitHubManager,
        pr_status_writer: IPRStatusWriter,
    ) -> MergePRTool:
        git_config = MagicMock(spec=GitConfig)
        git_config.default_base_branch = "main"
        return MergePRTool(
            manager=manager,
            git_config=git_config,
            pr_status_writer=pr_status_writer,
        )

    def test_merge_pr_tool_constructor_accepts_pr_status_writer(self) -> None:
        """MergePRTool.__init__ must accept pr_status_writer parameter."""
        sig = inspect.signature(MergePRTool.__init__)
        assert "pr_status_writer" in sig.parameters, (
            "MergePRTool.__init__ must accept pr_status_writer: IPRStatusWriter"
        )

    def test_merge_pr_sets_pr_status_absent_on_success(self) -> None:
        """PRStatus.ABSENT must be written after a successful merge."""
        import asyncio

        from mcp_server.core.operation_notes import NoteContext

        manager = MagicMock(spec=GitHubManager)
        manager.merge_pr.return_value = {
            "merged": True,
            "sha": "abc1234",
            "message": "Pull Request successfully merged",
        }
        pr_status_writer = MagicMock(spec=IPRStatusWriter)

        tool = self._make_merge_tool(manager, pr_status_writer)
        params = MergePRInput(pr_number=42)

        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(params, NoteContext())
        )

        assert not result.is_error
        pr_status_writer.set_pr_status.assert_called_once()
        _branch, status = pr_status_writer.set_pr_status.call_args[0]
        assert status == PRStatus.ABSENT

    def test_merge_pr_does_not_set_pr_status_on_failure(self) -> None:
        """PRStatus must NOT be written when merge fails."""
        import asyncio

        from mcp_server.core.exceptions import ExecutionError
        from mcp_server.core.operation_notes import NoteContext

        manager = MagicMock(spec=GitHubManager)
        manager.merge_pr.side_effect = ExecutionError("Merge conflict")

        pr_status_writer = MagicMock(spec=IPRStatusWriter)
        tool = self._make_merge_tool(manager, pr_status_writer)
        params = MergePRInput(pr_number=42)

        result = asyncio.get_event_loop().run_until_complete(
            tool.execute(params, NoteContext())
        )

        assert result.is_error
        pr_status_writer.set_pr_status.assert_not_called()

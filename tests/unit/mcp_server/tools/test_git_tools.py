"""Tests for Git Tools - commit, push, merge, checkout, delete."""
import pytest
from unittest.mock import MagicMock
from mcp_server.tools.git_tools import (
    GitCommitTool,
    GitPushTool,
    GitMergeTool,
    GitCheckoutTool,
    GitDeleteBranchTool,
    GitStashTool,
)


class TestGitCommitTool:
    """Tests for GitCommitTool."""

    @pytest.mark.asyncio
    async def test_commit_red_phase(self) -> None:
        """Test commit in RED phase."""
        mock_manager = MagicMock()
        mock_manager.commit_tdd_phase.return_value = "abc123"

        tool = GitCommitTool(manager=mock_manager)
        result = await tool.execute(
            phase="red",
            message="add failing tests for Feature"
        )

        mock_manager.commit_tdd_phase.assert_called_once_with(
            "red", "add failing tests for Feature"
        )
        assert "abc123" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_commit_green_phase(self) -> None:
        """Test commit in GREEN phase."""
        mock_manager = MagicMock()
        mock_manager.commit_tdd_phase.return_value = "def456"

        tool = GitCommitTool(manager=mock_manager)
        result = await tool.execute(phase="green", message="implement Feature")

        mock_manager.commit_tdd_phase.assert_called_once_with(
            "green", "implement Feature"
        )
        assert "def456" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_commit_refactor_phase(self) -> None:
        """Test commit in REFACTOR phase."""
        mock_manager = MagicMock()
        mock_manager.commit_tdd_phase.return_value = "ghi789"

        tool = GitCommitTool(manager=mock_manager)
        result = await tool.execute(phase="refactor", message="improve quality")

        mock_manager.commit_tdd_phase.assert_called_once_with(
            "refactor", "improve quality"
        )
        assert "ghi789" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_commit_docs_phase(self) -> None:
        """Test commit with docs phase."""
        mock_manager = MagicMock()
        mock_manager.commit_docs.return_value = "jkl012"

        tool = GitCommitTool(manager=mock_manager)
        result = await tool.execute(phase="docs", message="update README")

        mock_manager.commit_docs.assert_called_once_with("update README")
        assert "jkl012" in result.content[0]["text"]

    def test_commit_tool_schema(self) -> None:
        """Test commit tool has correct schema."""
        tool = GitCommitTool(manager=MagicMock())
        schema = tool.input_schema

        assert "phase" in schema["properties"]
        assert "message" in schema["properties"]
        assert "phase" in schema["required"]
        assert "message" in schema["required"]
        assert "enum" in schema["properties"]["phase"]


class TestGitPushTool:
    """Tests for GitPushTool."""

    @pytest.mark.asyncio
    async def test_push_default(self) -> None:
        """Test push without upstream flag."""
        mock_manager = MagicMock()
        mock_manager.get_status.return_value = {"branch": "feature/test"}

        tool = GitPushTool(manager=mock_manager)
        result = await tool.execute()

        mock_manager.push.assert_called_once_with(set_upstream=False)
        assert "feature/test" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_push_with_upstream(self) -> None:
        """Test push with --set-upstream flag."""
        mock_manager = MagicMock()
        mock_manager.get_status.return_value = {"branch": "feature/new"}

        tool = GitPushTool(manager=mock_manager)
        result = await tool.execute(set_upstream=True)

        mock_manager.push.assert_called_once_with(set_upstream=True)

    def test_push_tool_schema(self) -> None:
        """Test push tool has correct schema."""
        tool = GitPushTool(manager=MagicMock())
        schema = tool.input_schema

        assert "set_upstream" in schema["properties"]
        assert schema["properties"]["set_upstream"]["type"] == "boolean"


class TestGitMergeTool:
    """Tests for GitMergeTool."""

    @pytest.mark.asyncio
    async def test_merge_branch(self) -> None:
        """Test merge a feature branch."""
        mock_manager = MagicMock()
        mock_manager.get_status.return_value = {"branch": "main"}

        tool = GitMergeTool(manager=mock_manager)
        result = await tool.execute(branch="feature/test")

        mock_manager.merge.assert_called_once_with("feature/test")
        assert "feature/test" in result.content[0]["text"]

    def test_merge_tool_schema(self) -> None:
        """Test merge tool has correct schema."""
        tool = GitMergeTool(manager=MagicMock())
        schema = tool.input_schema

        assert "branch" in schema["properties"]
        assert "branch" in schema["required"]


class TestGitCheckoutTool:
    """Tests for GitCheckoutTool."""

    @pytest.mark.asyncio
    async def test_checkout_branch(self) -> None:
        """Test checkout to a branch."""
        mock_manager = MagicMock()

        tool = GitCheckoutTool(manager=mock_manager)
        result = await tool.execute(branch="feature/test")

        mock_manager.checkout.assert_called_once_with("feature/test")
        assert "feature/test" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_checkout_main(self) -> None:
        """Test checkout to main branch."""
        mock_manager = MagicMock()

        tool = GitCheckoutTool(manager=mock_manager)
        result = await tool.execute(branch="main")

        mock_manager.checkout.assert_called_once_with("main")
        assert "main" in result.content[0]["text"]

    def test_checkout_tool_schema(self) -> None:
        """Test checkout tool has correct schema."""
        tool = GitCheckoutTool(manager=MagicMock())
        schema = tool.input_schema

        assert "branch" in schema["properties"]
        assert "branch" in schema["required"]


class TestGitDeleteBranchTool:
    """Tests for GitDeleteBranchTool."""

    @pytest.mark.asyncio
    async def test_delete_branch(self) -> None:
        """Test delete a branch."""
        mock_manager = MagicMock()

        tool = GitDeleteBranchTool(manager=mock_manager)
        result = await tool.execute(branch="feature/test")

        mock_manager.delete_branch.assert_called_once_with("feature/test", force=False)
        assert "feature/test" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_delete_branch_force(self) -> None:
        """Test force delete a branch."""
        mock_manager = MagicMock()

        tool = GitDeleteBranchTool(manager=mock_manager)
        result = await tool.execute(branch="feature/test", force=True)

        mock_manager.delete_branch.assert_called_once_with("feature/test", force=True)

    def test_delete_branch_tool_schema(self) -> None:
        """Test delete branch tool has correct schema."""
        tool = GitDeleteBranchTool(manager=MagicMock())
        schema = tool.input_schema

        assert "branch" in schema["properties"]
        assert "force" in schema["properties"]
        assert "branch" in schema["required"]
        assert schema["properties"]["force"]["type"] == "boolean"


class TestGitStashTool:
    """Tests for GitStashTool."""

    @pytest.mark.asyncio
    async def test_stash_push(self) -> None:
        """Test stash push action."""
        mock_manager = MagicMock()

        tool = GitStashTool(manager=mock_manager)
        result = await tool.execute(action="push")

        mock_manager.stash.assert_called_once_with(message=None)
        assert "Stashed" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_stash_push_with_message(self) -> None:
        """Test stash push with custom message."""
        mock_manager = MagicMock()

        tool = GitStashTool(manager=mock_manager)
        result = await tool.execute(action="push", message="WIP: feature work")

        mock_manager.stash.assert_called_once_with(message="WIP: feature work")
        assert "WIP: feature work" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_stash_pop(self) -> None:
        """Test stash pop action."""
        mock_manager = MagicMock()

        tool = GitStashTool(manager=mock_manager)
        result = await tool.execute(action="pop")

        mock_manager.stash_pop.assert_called_once()
        assert "Applied" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_stash_list(self) -> None:
        """Test stash list action."""
        mock_manager = MagicMock()
        mock_manager.stash_list.return_value = [
            "stash@{0}: WIP on main: abc1234",
            "stash@{1}: On feature: def5678"
        ]

        tool = GitStashTool(manager=mock_manager)
        result = await tool.execute(action="list")

        mock_manager.stash_list.assert_called_once()
        assert "stash@{0}" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_stash_list_empty(self) -> None:
        """Test stash list when no stashes exist."""
        mock_manager = MagicMock()
        mock_manager.stash_list.return_value = []

        tool = GitStashTool(manager=mock_manager)
        result = await tool.execute(action="list")

        assert "No stashes" in result.content[0]["text"]

    def test_stash_tool_schema(self) -> None:
        """Test stash tool has correct schema."""
        tool = GitStashTool(manager=MagicMock())
        schema = tool.input_schema

        assert "action" in schema["properties"]
        assert "message" in schema["properties"]
        assert "action" in schema["required"]
        assert "enum" in schema["properties"]["action"]
        assert set(schema["properties"]["action"]["enum"]) == {"push", "pop", "list"}

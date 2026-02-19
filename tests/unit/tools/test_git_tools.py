"""Unit tests for git_tools.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mcp_server.managers.git_manager import GitManager
from mcp_server.tools.git_tools import (
    CreateBranchInput,
    CreateBranchTool,
    GetParentBranchInput,
    GetParentBranchTool,
    GitCheckoutInput,
    GitCheckoutTool,
    GitCommitInput,
    GitCommitTool,
    GitDeleteBranchInput,
    GitDeleteBranchTool,
    GitMergeInput,
    GitMergeTool,
    GitPushInput,
    GitPushTool,
    GitRestoreInput,
    GitRestoreTool,
    GitStashInput,
    GitStashTool,
    GitStatusInput,
    GitStatusTool,
)
from mcp_server.tools.tool_result import ToolResult


@pytest.fixture
def mock_git_manager():
    """Fixture for mocked GitManager."""
    return MagicMock()


@pytest.mark.asyncio
async def test_create_branch_tool_requires_base_branch(mock_git_manager):
    """Test that base_branch parameter is required."""
    with pytest.raises(Exception):  # Pydantic validation error
        CreateBranchInput(name="test-branch", branch_type="feature")


@pytest.mark.asyncio
async def test_create_branch_tool_calls_manager_with_explicit_base(mock_git_manager):
    """Test that tool passes all parameters including base_branch to manager."""
    tool = CreateBranchTool(manager=mock_git_manager)
    mock_git_manager.create_branch.return_value = "feature/test-branch"

    params = CreateBranchInput(name="test-branch", branch_type="feature", base_branch="HEAD")
    result = await tool.execute(params)

    mock_git_manager.create_branch.assert_called_once_with("test-branch", "feature", "HEAD")
    assert isinstance(result, ToolResult)
    assert "Created and switched to branch: feature/test-branch" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_create_branch_tool_with_branch_name_as_base(mock_git_manager):
    """Test creating branch from another branch name."""
    tool = CreateBranchTool(manager=mock_git_manager)
    mock_git_manager.create_branch.return_value = "fix/new-fix"

    params = CreateBranchInput(
        name="new-fix", branch_type="fix", base_branch="refactor/51-labels-yaml"
    )
    result = await tool.execute(params)

    mock_git_manager.create_branch.assert_called_once_with(
        "new-fix", "fix", "refactor/51-labels-yaml"
    )
    assert "fix/new-fix" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_create_branch_tool_name_changed(mock_git_manager):
    """Test that tool name is 'create_branch' (not 'create_feature_branch')."""
    tool = CreateBranchTool(manager=mock_git_manager)
    assert tool.name == "create_branch", "Tool should be renamed to create_branch"


@pytest.mark.asyncio
async def test_git_status_tool(mock_git_manager):
    """Test git status tool."""
    tool = GitStatusTool(manager=mock_git_manager)
    mock_git_manager.get_status.return_value = {
        "branch": "main",
        "is_clean": False,
        "untracked_files": ["foo.py"],
        "modified_files": ["bar.py"],
    }

    result = await tool.execute(GitStatusInput())

    assert isinstance(result, ToolResult)
    assert "Branch: main" in result.content[0]["text"]
    assert "Untracked: foo.py" in result.content[0]["text"]
    assert "Modified: bar.py" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_tool_tdd(mock_git_manager):
    """Test git commit tool with TDD phase (legacy path, with cycle_number)."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "abc1234"

    # Legacy phase="red" must include cycle_number (Issue #146 Cycle 7)
    params = GitCommitInput(phase="red", message="failing test", cycle_number=1)
    result = await tool.execute(params)

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="tdd",
        message="failing test",
        sub_phase="red",
        cycle_number=1,
        commit_type=None,
        files=None,
    )
    assert "Committed: abc1234" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_legacy_phase_tdd_requires_cycle_number(mock_git_manager):
    """Legacy phase='red' maps to TDD and must enforce cycle_number.

    Issue #146 Cycle 7: Bypass via legacy path must be closed.
    git_tools.py:251-256 only checks workflow_phase but legacy path maps
    phase='red' -> tdd AFTER the check, allowing None cycle_number to slip through.
    """
    tool = GitCommitTool(manager=mock_git_manager)

    result = await tool.execute(GitCommitInput(phase="red", message="failing test"))

    assert result.is_error, "Expected error when phase='red' used without cycle_number"
    assert "cycle_number is required" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_legacy_phase_green_requires_cycle_number(mock_git_manager):
    """Legacy phase='green' maps to TDD and must enforce cycle_number.

    Issue #146 Cycle 7: All non-docs legacy phases map to TDD scope.
    """
    tool = GitCommitTool(manager=mock_git_manager)

    result = await tool.execute(GitCommitInput(phase="green", message="implement feature"))

    assert result.is_error, "Expected error when phase='green' used without cycle_number"
    assert "cycle_number is required" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_legacy_phase_docs_does_not_require_cycle_number(mock_git_manager):
    """Legacy phase='docs' maps to documentation (not TDD), so no cycle_number needed.

    Issue #146 Cycle 7: Only TDD-mapped phases require cycle_number.
    phase='docs' -> documentation phase -> no enforcement.
    """
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "doc5678"

    result = await tool.execute(GitCommitInput(phase="docs", message="update readme"))

    assert "Committed: doc5678" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_tool_docs(mock_git_manager):
    """Test git commit tool with docs phase."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "doc1234"

    params = GitCommitInput(phase="docs", message="update readme")
    result = await tool.execute(params)

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="documentation",
        message="update readme",
        sub_phase=None,
        cycle_number=None,
        commit_type=None,
        files=None,
    )
    assert "Committed: doc1234" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_tool_with_workflow_phase(mock_git_manager):
    """Test git commit tool with workflow_phase parameter (NEW)."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "wf1234"

    params = GitCommitInput(
        message="complete research",
        workflow_phase="research",
    )
    result = await tool.execute(params)

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="research",
        message="complete research",
        sub_phase=None,
        cycle_number=None,
        commit_type=None,
        files=None,
    )
    assert "Committed: wf1234" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_tool_with_workflow_phase_and_subphase(mock_git_manager):
    """Test git commit tool with workflow_phase and sub_phase."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "wf5678"

    params = GitCommitInput(
        message="add failing test",
        workflow_phase="tdd",
        sub_phase="red",
        cycle_number=1,
    )
    result = await tool.execute(params)

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="tdd",
        message="add failing test",
        sub_phase="red",
        cycle_number=1,
        commit_type=None,
        files=None,
    )
    assert "Committed: wf5678" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_tool_with_cycle_number(mock_git_manager):
    """Test git commit tool with cycle_number."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "wf9012"

    params = GitCommitInput(
        message="implement feature",
        workflow_phase="tdd",
        sub_phase="green",
        cycle_number=1,
    )
    result = await tool.execute(params)

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="tdd",
        message="implement feature",
        sub_phase="green",
        cycle_number=1,
        commit_type=None,
        files=None,
    )
    assert "Committed: wf9012" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_tool_with_workflow_phase_and_files(mock_git_manager):
    """Test git commit tool with workflow_phase and files."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "wf3456"

    params = GitCommitInput(
        message="refactor code",
        workflow_phase="tdd",
        sub_phase="refactor",
        cycle_number=1,
        files=["src/app.py", "tests/test_app.py"],
    )
    result = await tool.execute(params)

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="tdd",
        message="refactor code",
        sub_phase="refactor",
        cycle_number=1,
        commit_type=None,
        files=["src/app.py", "tests/test_app.py"],
    )
    assert "Committed: wf3456" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_tool_backward_compat_with_old_phase(mock_git_manager):
    """Test backward compatibility: old 'phase' parameter still works with cycle_number."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "old1234"

    # Legacy phase="red" requires cycle_number (Issue #146 Cycle 7)
    params = GitCommitInput(phase="red", message="old style commit", cycle_number=2)
    result = await tool.execute(params)

    # Should map legacy phase to workflow scope path
    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="tdd",
        message="old style commit",
        sub_phase="red",
        cycle_number=2,
        commit_type=None,
        files=None,
    )
    assert "Committed: old1234" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_tool_with_commit_type_override(mock_git_manager):
    """Test commit_type override parameter."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "override123"

    params = GitCommitInput(
        workflow_phase="tdd",
        sub_phase="red",
        commit_type="fix",  # Override default 'test'
        message="fix failing test",
        cycle_number=1,
    )
    result = await tool.execute(params)

    # Should pass commit_type to commit_with_scope
    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="tdd",
        message="fix failing test",
        sub_phase="red",
        cycle_number=1,
        commit_type="fix",
        files=None,
    )
    assert "Committed: override123" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_tool_with_invalid_commit_type():
    """Test that invalid commit_type raises ValueError."""
    with pytest.raises(ValueError, match="Invalid commit_type 'invalid_type'"):
        GitCommitInput(
            workflow_phase="tdd",
            sub_phase="red",
            commit_type="invalid_type",  # Invalid type
            message="test commit",
        )


@pytest.mark.asyncio
async def test_git_commit_tool_commit_type_case_insensitive(mock_git_manager):
    """Test that commit_type is normalized to lowercase."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "case123"

    params = GitCommitInput(
        workflow_phase="tdd",
        sub_phase="red",
        commit_type="FEAT",  # Uppercase should be normalized
        message="add feature",
        cycle_number=1,
    )

    # Should be normalized to lowercase by validator
    assert params.commit_type == "feat"

    result = await tool.execute(params)

    # Should pass normalized commit_type
    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="tdd",
        message="add feature",
        sub_phase="red",
        cycle_number=1,
        commit_type="feat",  # Normalized to lowercase
        files=None,
    )
    assert "Committed: case123" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_commit_integration_workflow_phases():
    """Integration test: Full commit workflow with real workphases.yaml."""
    # Create a real GitManager with mocked adapter but real workphases.yaml
    mock_adapter = MagicMock()
    mock_adapter.commit.return_value = "integration123"

    # Use the real .st3/workphases.yaml
    workphases_path = Path(".st3/workphases.yaml")
    if not workphases_path.exists():
        pytest.skip("workphases.yaml not found - skipping integration test")

    manager = GitManager(adapter=mock_adapter, workphases_path=workphases_path)
    tool = GitCommitTool(manager=manager)

    # Test 1: Research phase (no subphase)
    params1 = GitCommitInput(message="investigate alternatives", workflow_phase="research")
    result1 = await tool.execute(params1)

    assert "Committed: integration123" in result1.content[0]["text"]
    mock_adapter.commit.assert_called_with("docs(P_RESEARCH): investigate alternatives", files=None)

    # Test 2: TDD with subphase
    params2 = GitCommitInput(
        message="add failing test",
        workflow_phase="tdd",
        sub_phase="red",
        cycle_number=1,
    )
    result2 = await tool.execute(params2)

    assert "Committed: integration123" in result2.content[0]["text"]
    mock_adapter.commit.assert_called_with("test(P_TDD_SP_C1_RED): add failing test", files=None)

    # Test 3: Coordination phase (NEW)
    params3 = GitCommitInput(
        message="delegate to child issues",
        workflow_phase="coordination",
        sub_phase="delegation",
    )
    result3 = await tool.execute(params3)

    assert "Committed: integration123" in result3.content[0]["text"]
    mock_adapter.commit.assert_called_with(
        "chore(P_COORDINATION_SP_DELEGATION): delegate to child issues", files=None
    )


@pytest.mark.asyncio
async def test_git_checkout_tool(mock_git_manager):
    """Test git checkout tool with PhaseStateEngine state sync."""
    tool = GitCheckoutTool(manager=mock_git_manager)

    # Mock PhaseStateEngine to return state with phase info
    mock_engine = MagicMock()
    mock_engine.get_state.return_value = {"current_phase": "tdd", "branch": "main"}

    params = GitCheckoutInput(branch="main")

    with (
        patch("mcp_server.managers.phase_state_engine.PhaseStateEngine", return_value=mock_engine),
        patch("mcp_server.managers.project_manager.ProjectManager"),
        patch("pathlib.Path.cwd", return_value=MagicMock()),
    ):
        result = await tool.execute(params)

        mock_git_manager.checkout.assert_called_once_with("main")
        mock_engine.get_state.assert_called_once_with("main")
        assert "Switched to branch: main" in result.content[0]["text"]
        assert "tdd" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_checkout_tool_displays_parent_branch(mock_git_manager):
    """Test git checkout displays parent_branch when present.

    Issue #79: Show parent_branch in checkout output for context.
    """
    tool = GitCheckoutTool(manager=mock_git_manager)

    # Mock PhaseStateEngine to return state with parent_branch
    mock_engine = MagicMock()
    mock_engine.get_state.return_value = {
        "current_phase": "design",
        "branch": "feature/79-test",
        "parent_branch": "epic/76-quality-gates",
    }

    params = GitCheckoutInput(branch="feature/79-test")

    with (
        patch("mcp_server.managers.phase_state_engine.PhaseStateEngine", return_value=mock_engine),
        patch("mcp_server.managers.project_manager.ProjectManager"),
        patch("pathlib.Path.cwd", return_value=MagicMock()),
    ):
        result = await tool.execute(params)

        mock_git_manager.checkout.assert_called_once_with("feature/79-test")
        assert "Switched to branch: feature/79-test" in result.content[0]["text"]
        assert "Current phase: design" in result.content[0]["text"]
        assert "Parent branch: epic/76-quality-gates" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_checkout_tool_no_parent_branch(mock_git_manager):
    """Test git checkout without parent_branch doesn't show it.

    Issue #79: Backward compatibility - don't show parent if None.
    """
    tool = GitCheckoutTool(manager=mock_git_manager)

    # Mock PhaseStateEngine to return state WITHOUT parent_branch
    mock_engine = MagicMock()
    mock_engine.get_state.return_value = {
        "current_phase": "tdd",
        "branch": "main",
        "parent_branch": None,
    }

    params = GitCheckoutInput(branch="main")

    with (
        patch("mcp_server.managers.phase_state_engine.PhaseStateEngine", return_value=mock_engine),
        patch("mcp_server.managers.project_manager.ProjectManager"),
        patch("pathlib.Path.cwd", return_value=MagicMock()),
    ):
        result = await tool.execute(params)

        mock_git_manager.checkout.assert_called_once_with("main")
        output = result.content[0]["text"]
        assert "Switched to branch: main" in output
        assert "Current phase: tdd" in output
        assert "Parent branch:" not in output  # Should NOT appear


@pytest.mark.asyncio
async def test_git_push_tool(mock_git_manager):
    """Test git push tool."""
    tool = GitPushTool(manager=mock_git_manager)
    mock_git_manager.get_status.return_value = {"branch": "feature/foo"}

    params = GitPushInput(set_upstream=True)
    result = await tool.execute(params)

    mock_git_manager.push.assert_called_once_with(set_upstream=True)
    assert "Pushed branch: feature/foo" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_merge_tool(mock_git_manager):
    """Test git merge tool."""
    tool = GitMergeTool(manager=mock_git_manager)
    mock_git_manager.get_status.return_value = {"branch": "main"}

    params = GitMergeInput(branch="feature/foo")
    result = await tool.execute(params)

    mock_git_manager.merge.assert_called_once_with("feature/foo")
    assert "Merged feature/foo into main" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_delete_branch_tool(mock_git_manager):
    """Test git delete branch tool."""
    tool = GitDeleteBranchTool(manager=mock_git_manager)

    params = GitDeleteBranchInput(branch="feature/old", force=True)
    result = await tool.execute(params)

    mock_git_manager.delete_branch.assert_called_once_with("feature/old", force=True)
    assert "Deleted branch: feature/old" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_stash_tool(mock_git_manager):
    """Test git stash tool with different actions."""
    tool = GitStashTool(manager=mock_git_manager)

    # Push
    result = await tool.execute(GitStashInput(action="push", message="wip"))
    mock_git_manager.stash.assert_called_with(message="wip", include_untracked=False)
    assert "Stashed changes: wip" in result.content[0]["text"]

    # Pop
    result = await tool.execute(GitStashInput(action="pop"))
    mock_git_manager.stash_pop.assert_called_once()
    assert "Applied and removed latest stash" in result.content[0]["text"]

    # List
    mock_git_manager.stash_list.return_value = ["stash@{0}: wip"]
    result = await tool.execute(GitStashInput(action="list"))
    assert "stash@{0}: wip" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_git_restore_tool(mock_git_manager):
    """Test git restore tool."""
    tool = GitRestoreTool(manager=mock_git_manager)

    params = GitRestoreInput(files=["foo.py", "bar.py"], source="HEAD")
    result = await tool.execute(params)

    mock_git_manager.restore.assert_called_once_with(files=["foo.py", "bar.py"], source="HEAD")
    assert "Restored 2 file(s)" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_get_parent_branch_current_branch():
    """Test get parent branch for current branch.

    Issue #79: Query parent_branch from PhaseStateEngine state.
    """
    tool = GetParentBranchTool()

    # Mock PhaseStateEngine to return state with parent_branch
    mock_engine = MagicMock()
    mock_engine.get_state.return_value = {
        "current_phase": "tdd",
        "branch": "feature/79-parent-branch-tracking",
        "parent_branch": "epic/76-quality-gates",
    }

    params = GetParentBranchInput()  # No branch specified = current branch

    with (
        patch("mcp_server.managers.phase_state_engine.PhaseStateEngine", return_value=mock_engine),
        patch("mcp_server.managers.project_manager.ProjectManager"),
        patch("pathlib.Path.cwd", return_value=MagicMock()),
        patch("mcp_server.tools.git_tools.GitManager") as mock_git,
    ):
        mock_git.return_value.get_current_branch.return_value = "feature/79-parent-branch-tracking"

        result = await tool.execute(params)

        mock_engine.get_state.assert_called_once_with("feature/79-parent-branch-tracking")
        assert "Parent branch: epic/76-quality-gates" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_get_parent_branch_specified_branch():
    """Test get parent branch for specified branch.

    Issue #79: Query parent_branch for any branch, not just current.
    """
    tool = GetParentBranchTool()

    # Mock PhaseStateEngine to return state with parent_branch
    mock_engine = MagicMock()
    mock_engine.get_state.return_value = {
        "current_phase": "design",
        "branch": "feature/77-error-handling",
        "parent_branch": "epic/76-quality-gates",
    }

    params = GetParentBranchInput(branch="feature/77-error-handling")

    with (
        patch("mcp_server.managers.phase_state_engine.PhaseStateEngine", return_value=mock_engine),
        patch("mcp_server.managers.project_manager.ProjectManager"),
        patch("pathlib.Path.cwd", return_value=MagicMock()),
    ):
        result = await tool.execute(params)

        mock_engine.get_state.assert_called_once_with("feature/77-error-handling")
        assert "Parent branch: epic/76-quality-gates" in result.content[0]["text"]
        assert "feature/77-error-handling" in result.content[0]["text"]


@pytest.mark.asyncio
async def test_get_parent_branch_not_set():
    """Test get parent branch when not set.

    Issue #79: Graceful handling when parent_branch is None.
    """
    tool = GetParentBranchTool()

    # Mock PhaseStateEngine to return state WITHOUT parent_branch
    mock_engine = MagicMock()
    mock_engine.get_state.return_value = {
        "current_phase": "tdd",
        "branch": "main",
        "parent_branch": None,
    }

    params = GetParentBranchInput(branch="main")

    with (
        patch("mcp_server.managers.phase_state_engine.PhaseStateEngine", return_value=mock_engine),
        patch("mcp_server.managers.project_manager.ProjectManager"),
        patch("pathlib.Path.cwd", return_value=MagicMock()),
    ):
        result = await tool.execute(params)

        mock_engine.get_state.assert_called_once_with("main")
        output = result.content[0]["text"]
        assert "Parent branch: (not set)" in output
        assert "main" in output


# ===== Cycle Number Enforcement Tests (Issue #146 Cycle 5) =====


@pytest.mark.asyncio
async def test_git_commit_tdd_requires_cycle_number(mock_git_manager):
    """Test that TDD phase commits REQUIRE cycle_number (Issue #146)."""
    tool = GitCommitTool(manager=mock_git_manager)

    # Attempt to commit in TDD phase without cycle_number
    params = GitCommitInput(
        message="update documentation",
        workflow_phase="tdd",
        # cycle_number is MISSING - should return error result
    )

    result = await tool.execute(params)

    assert result.is_error, "Expected error when cycle_number missing for TDD"
    error_text = result.content[0]["text"]
    assert "cycle_number" in error_text
    assert "TDD" in error_text or "tdd" in error_text.lower()


@pytest.mark.asyncio
async def test_git_commit_tdd_subphase_requires_cycle_number(mock_git_manager):
    """Test that TDD sub-phase commits REQUIRE cycle_number (Issue #146)."""
    tool = GitCommitTool(manager=mock_git_manager)

    # Attempt to commit in TDD sub-phase without cycle_number
    params = GitCommitInput(
        message="implement feature",
        workflow_phase="tdd",
        sub_phase="green",
        # cycle_number is MISSING - should return error result
    )

    result = await tool.execute(params)

    assert result.is_error, "Expected error when cycle_number missing for TDD sub-phase"
    error_text = result.content[0]["text"]
    assert "cycle_number" in error_text


@pytest.mark.asyncio
async def test_git_commit_non_tdd_allows_no_cycle_number(mock_git_manager):
    """Test that non-TDD phases do NOT require cycle_number (Issue #146)."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "abc1234"

    # Commit in research phase without cycle_number - should succeed
    params = GitCommitInput(
        message="research alternatives",
        workflow_phase="research",
        # cycle_number is OMITTED - should be allowed
    )

    result = await tool.execute(params)

    # Should succeed
    assert "Committed: abc1234" in result.content[0]["text"]
    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="research",
        message="research alternatives",
        sub_phase=None,
        cycle_number=None,
        commit_type=None,
        files=None,
    )


@pytest.mark.asyncio
async def test_git_commit_tdd_with_cycle_number_succeeds(mock_git_manager):
    """Test that TDD commits WITH cycle_number succeed (Issue #146)."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "def5678"

    # Commit in TDD phase WITH cycle_number - should succeed
    params = GitCommitInput(
        message="add schema validation",
        workflow_phase="tdd",
        sub_phase="green",
        cycle_number=3,
    )

    result = await tool.execute(params)

    # Should succeed
    assert "Committed: def5678" in result.content[0]["text"]
    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="tdd",
        message="add schema validation",
        sub_phase="green",
        cycle_number=3,
        commit_type=None,
        files=None,
    )


# --- C2 re-run: commit phase mismatch guard (GAP-07) ---


@pytest.mark.asyncio
async def test_git_add_or_commit_raises_on_phase_mismatch(mock_git_manager):
    """CommitPhaseMismatchError when workflow_phase doesn't match state.json (GAP-07)."""
    from mcp_server.tools.git_tools import CommitPhaseMismatchError

    def phase_guard(branch: str, workflow_phase: str, cycle_number: int | None) -> None:
        raise CommitPhaseMismatchError(
            f"phase_mismatch: commit says '{workflow_phase}' but state.json says 'design'"
        )

    tool = GitCommitTool(manager=mock_git_manager, phase_guard=phase_guard)
    mock_git_manager.adapter.get_current_branch.return_value = "feature/229-phase-deliverables-enforcement"

    params = GitCommitInput(workflow_phase="tdd", cycle_number=2, message="add red test")
    with pytest.raises(CommitPhaseMismatchError, match="phase_mismatch"):
        await tool.execute(params)


@pytest.mark.asyncio
async def test_git_add_or_commit_raises_on_cycle_mismatch(mock_git_manager):
    """CommitPhaseMismatchError when cycle_number doesn't match state.json current_tdd_cycle (GAP-07)."""
    from mcp_server.tools.git_tools import CommitPhaseMismatchError

    def phase_guard(branch: str, workflow_phase: str, cycle_number: int | None) -> None:
        raise CommitPhaseMismatchError(
            f"phase_mismatch: commit says cycle {cycle_number} but state.json says cycle 3"
        )

    tool = GitCommitTool(manager=mock_git_manager, phase_guard=phase_guard)
    mock_git_manager.adapter.get_current_branch.return_value = "feature/229-phase-deliverables-enforcement"

    params = GitCommitInput(workflow_phase="tdd", cycle_number=2, message="add green impl")
    with pytest.raises(CommitPhaseMismatchError, match="phase_mismatch"):
        await tool.execute(params)


@pytest.mark.asyncio
async def test_git_add_or_commit_passes_when_phase_and_cycle_match(mock_git_manager):
    """No error when workflow_phase and cycle_number match state.json (GAP-07)."""
    from mcp_server.tools.git_tools import CommitPhaseMismatchError  # noqa: F401

    def phase_guard(branch: str, workflow_phase: str, cycle_number: int | None) -> None:
        pass  # phase=tdd, cycle=2 matches state.json

    tool = GitCommitTool(manager=mock_git_manager, phase_guard=phase_guard)
    mock_git_manager.adapter.get_current_branch.return_value = "feature/229-phase-deliverables-enforcement"
    mock_git_manager.commit_with_scope.return_value = "abc1234"

    params = GitCommitInput(workflow_phase="tdd", cycle_number=2, message="implement guard")
    result = await tool.execute(params)

    assert "Committed: abc1234" in result.content[0]["text"]

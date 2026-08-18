"""Unit tests for git_tools.py.

@layer: Tests (Unit)
@dependencies: [pytest, pathlib, mcp_server.tools.git_tools]
"""

from tests.mcp_server.test_support import get_default_server_root
from pathlib import Path
from unittest.mock import ANY, MagicMock

import pytest
from pydantic import ValidationError

from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.config.loader import ConfigLoader
from mcp_server.core.exceptions import ExecutionError
from mcp_server.core.interfaces import IContextLoadedWriter
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.git_manager import BranchDeleteResult, GitManager
from mcp_server.managers.state_repository import StateBranchMismatchError
from mcp_server.schemas.tool_outputs import (
    CheckMergeOutput,
    CreateBranchOutput,
    GetParentBranchOutput,
    GitCheckoutOutput,
    GitCommitOutput,
    GitDeleteBranchOutput,
    GitMergeOutput,
    GitPushOutput,
    GitRestoreOutput,
    GitStashOutput,
    GitStatusOutput,
)
from mcp_server.tools.git_tools import (
    CheckMergeInput,
    CheckMergeTool,
    CommitPhaseMismatchError,
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


@pytest.fixture
def mock_git_manager() -> MagicMock:
    """Fixture for mocked GitManager."""
    manager = MagicMock()
    git_config = MagicMock()
    git_config.branch_types = ["feature", "bug", "docs", "refactor", "hotfix", "epic"]
    git_config.commit_types = ["feat", "fix", "docs", "chore", "test", "refactor"]
    git_config.has_branch_type.side_effect = lambda value: value in git_config.branch_types
    git_config.has_commit_type.side_effect = lambda value: value.lower() in git_config.commit_types
    git_config.extract_issue_number.side_effect = lambda branch: 79 if "79" in branch else 999
    manager.git_config = git_config
    manager.adapter.get_current_branch.return_value = "feature/257-reorder-workflow-phases"
    manager.get_current_branch.return_value = "feature/257-reorder-workflow-phases"
    return manager


@pytest.mark.asyncio
async def test_create_branch_tool_requires_base_branch() -> None:
    """Test that base_branch parameter is required."""
    with pytest.raises(Exception):  # noqa: B017 — Pydantic validation error; exact type varies by version
        CreateBranchInput(name="test-branch", branch_type="feature")


@pytest.mark.asyncio
async def test_create_branch_tool_calls_manager_with_explicit_base(
    mock_git_manager: MagicMock,
) -> None:
    """Test that tool passes all parameters including base_branch to manager."""
    tool = CreateBranchTool(manager=mock_git_manager)
    mock_git_manager.create_branch.return_value = "feature/test-branch"

    params = CreateBranchInput(name="test-branch", branch_type="feature", base_branch="HEAD")
    result = await tool.execute(params, NoteContext())

    mock_git_manager.create_branch.assert_called_once_with("test-branch", "feature", "HEAD", ANY)

    assert isinstance(result, CreateBranchOutput)
    assert result.success is True
    assert result.branch_name == "feature/test-branch"
    assert result.branch_type == "feature"
    assert result.base_branch == "HEAD"


@pytest.mark.asyncio
async def test_create_branch_tool_with_branch_name_as_base(mock_git_manager: MagicMock) -> None:
    """Test creating branch from another branch name."""
    tool = CreateBranchTool(manager=mock_git_manager)
    mock_git_manager.create_branch.return_value = "bug/new-fix"

    params = CreateBranchInput(
        name="new-fix", branch_type="bug", base_branch="refactor/51-labels-yaml"
    )
    result = await tool.execute(params, NoteContext())

    mock_git_manager.create_branch.assert_called_once_with(
        "new-fix", "bug", "refactor/51-labels-yaml", ANY
    )

    assert isinstance(result, CreateBranchOutput)
    assert result.success is True
    assert result.branch_name == "bug/new-fix"
    assert result.branch_type == "bug"
    assert result.base_branch == "refactor/51-labels-yaml"


@pytest.mark.asyncio
async def test_create_branch_tool_name_changed(mock_git_manager: MagicMock) -> None:
    """Test that tool name is 'create_branch' (not 'create_feature_branch')."""
    tool = CreateBranchTool(manager=mock_git_manager)
    assert tool.name == "create_branch", "Tool should be renamed to create_branch"


@pytest.mark.asyncio
async def test_git_status_tool(mock_git_manager: MagicMock) -> None:
    """Test git status tool."""

    tool = GitStatusTool(manager=mock_git_manager)
    mock_git_manager.get_status.return_value = {
        "branch": "main",
        "is_clean": False,
        "untracked_files": ["foo.py"],
        "modified_files": ["bar.py"],
    }

    result = await tool.execute(GitStatusInput(), NoteContext())

    assert isinstance(result, GitStatusOutput)
    assert result.success
    assert result.branch == "main"
    assert result.is_clean is False
    assert result.untracked_files == ["foo.py"]
    assert result.modified_files == ["bar.py"]
    assert result.untracked_count == 1
    assert result.modified_count == 1


@pytest.mark.asyncio
async def test_git_commit_tool_rejects_legacy_phase_kwarg() -> None:
    """Legacy phase= must be removed from GitCommitInput in cycle 4."""
    with pytest.raises(ValidationError):
        GitCommitInput(phase="red", message="failing test", cycle_number=1)


@pytest.mark.asyncio
async def test_git_commit_tool_docs(mock_git_manager: MagicMock) -> None:
    """Test git commit tool with documentation workflow_phase."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "doc1234"

    params = GitCommitInput(workflow_phase="documentation", message="update readme")
    result = await tool.execute(params, NoteContext())

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="documentation",
        message="update readme",
        note_context=ANY,
        sub_phase=None,
        cycle_number=None,
        commit_type=None,
        files=None,
        skip_paths=frozenset(),
        issue_number=999,
    )
    from mcp_server.schemas.tool_outputs import GitCommitOutput  # noqa: PLC0415

    assert isinstance(result, GitCommitOutput)
    assert result.success is True
    assert result.commit_hash == "doc1234"


@pytest.mark.asyncio
async def test_git_commit_tool_resolves_commit_type_from_phase_contracts(
    mock_git_manager: MagicMock,
) -> None:
    """Implementation commits should pass a resolved commit_type into GitManager."""
    resolver = MagicMock(return_value="refactor")
    tool = GitCommitTool(manager=mock_git_manager, commit_type_resolver=resolver)
    mock_git_manager.commit_with_scope.return_value = "abc1234"
    mock_git_manager.adapter.get_current_branch.return_value = "feature/257-reorder-workflow-phases"

    params = GitCommitInput(
        message="refactor code",
        workflow_phase="implementation",
        sub_phase="refactor",
        cycle_number=4,
    )
    result = await tool.execute(params, NoteContext())

    resolver.assert_called_once_with(
        "feature/257-reorder-workflow-phases",
        "implementation",
        "refactor",
    )
    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="implementation",
        message="refactor code",
        note_context=ANY,
        sub_phase="refactor",
        cycle_number=4,
        commit_type="refactor",
        files=None,
        skip_paths=frozenset(),
        issue_number=999,
    )
    from mcp_server.schemas.tool_outputs import GitCommitOutput  # noqa: PLC0415

    assert isinstance(result, GitCommitOutput)
    assert result.success is True
    assert result.commit_hash == "abc1234"
    assert result.commit_type == "refactor"


@pytest.mark.asyncio
async def test_git_commit_tool_with_workflow_phase(mock_git_manager: MagicMock) -> None:
    """Test git commit tool with workflow_phase parameter (NEW)."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "wf1234"

    params = GitCommitInput(
        message="complete research",
        workflow_phase="research",
    )
    result = await tool.execute(params, NoteContext())

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="research",
        message="complete research",
        note_context=ANY,
        sub_phase=None,
        cycle_number=None,
        commit_type=None,
        files=None,
        skip_paths=frozenset(),
        issue_number=999,
    )
    from mcp_server.schemas.tool_outputs import GitCommitOutput  # noqa: PLC0415

    assert isinstance(result, GitCommitOutput)
    assert result.success is True
    assert result.commit_hash == "wf1234"


@pytest.mark.asyncio
async def test_git_commit_tool_with_workflow_phase_and_subphase(
    mock_git_manager: MagicMock,
) -> None:
    """Test git commit tool with workflow_phase and sub_phase."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "wf5678"

    params = GitCommitInput(
        message="add failing test",
        workflow_phase="implementation",
        sub_phase="red",
        cycle_number=1,
    )
    result = await tool.execute(params, NoteContext())

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="implementation",
        message="add failing test",
        note_context=ANY,
        sub_phase="red",
        cycle_number=1,
        commit_type=None,
        files=None,
        skip_paths=frozenset(),
        issue_number=999,
    )
    from mcp_server.schemas.tool_outputs import GitCommitOutput  # noqa: PLC0415

    assert isinstance(result, GitCommitOutput)
    assert result.success is True
    assert result.commit_hash == "wf5678"


@pytest.mark.asyncio
async def test_git_commit_tool_with_cycle_number(mock_git_manager: MagicMock) -> None:
    """Test git commit tool with cycle_number."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "wf9012"

    params = GitCommitInput(
        message="implement feature",
        workflow_phase="implementation",
        sub_phase="green",
        cycle_number=1,
    )
    result = await tool.execute(params, NoteContext())

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="implementation",
        message="implement feature",
        note_context=ANY,
        sub_phase="green",
        cycle_number=1,
        commit_type=None,
        files=None,
        skip_paths=frozenset(),
        issue_number=999,
    )
    from mcp_server.schemas.tool_outputs import GitCommitOutput  # noqa: PLC0415

    assert isinstance(result, GitCommitOutput)
    assert result.success is True
    assert result.commit_hash == "wf9012"


@pytest.mark.asyncio
async def test_git_commit_tool_with_workflow_phase_and_files(mock_git_manager: MagicMock) -> None:
    """Test git commit tool with workflow_phase and files."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "wf3456"

    params = GitCommitInput(
        message="refactor code",
        workflow_phase="implementation",
        sub_phase="refactor",
        cycle_number=1,
        files=["src/app.py", "tests/test_app.py"],
    )
    result = await tool.execute(params, NoteContext())

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="implementation",
        message="refactor code",
        note_context=ANY,
        sub_phase="refactor",
        cycle_number=1,
        commit_type=None,
        files=["src/app.py", "tests/test_app.py"],
        skip_paths=frozenset(),
        issue_number=999,
    )
    from mcp_server.schemas.tool_outputs import GitCommitOutput  # noqa: PLC0415

    assert isinstance(result, GitCommitOutput)
    assert result.success is True
    assert result.commit_hash == "wf3456"


@pytest.mark.asyncio
async def test_git_commit_tool_backward_compat_with_old_phase(mock_git_manager: MagicMock) -> None:
    """Legacy phase input is rejected instead of being mapped implicitly."""
    del mock_git_manager
    with pytest.raises(ValidationError):
        GitCommitInput(phase="red", message="old style commit", cycle_number=2)


@pytest.mark.asyncio
async def test_git_commit_tool_with_commit_type_override(mock_git_manager: MagicMock) -> None:
    """Test commit_type override parameter."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "override123"

    params = GitCommitInput(
        workflow_phase="implementation",
        sub_phase="red",
        commit_type="fix",  # Override default 'test'
        message="fix failing test",
        cycle_number=1,
    )
    result = await tool.execute(params, NoteContext())

    # Should pass commit_type to commit_with_scope
    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="implementation",
        message="fix failing test",
        note_context=ANY,
        sub_phase="red",
        cycle_number=1,
        commit_type="fix",
        files=None,
        skip_paths=frozenset(),
        issue_number=999,
    )
    from mcp_server.schemas.tool_outputs import GitCommitOutput  # noqa: PLC0415

    assert isinstance(result, GitCommitOutput)
    assert result.success is True
    assert result.commit_hash == "override123"


@pytest.mark.asyncio
async def test_git_commit_tool_schema_excludes_invalid_commit_type(
    mock_git_manager: MagicMock,
) -> None:
    """A4 schema: commit_type.enum from git_config does not include unknown types."""
    tool = GitCommitTool(manager=mock_git_manager)
    schema = tool.input_schema
    enum_values = schema["properties"]["commit_type"]["enum"]
    assert "invalid_type" not in enum_values
    assert "feat" in enum_values  # from mock_git_manager fixture


@pytest.mark.asyncio
async def test_git_commit_tool_execute_with_valid_commit_type(mock_git_manager: MagicMock) -> None:
    """Tool executes correctly when commit_type is a valid enum value."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "case123"

    params = GitCommitInput(
        workflow_phase="implementation",
        sub_phase="red",
        commit_type="feat",
        message="add feature",
        cycle_number=1,
    )

    result = await tool.execute(params, NoteContext())

    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="implementation",
        message="add feature",
        note_context=ANY,
        sub_phase="red",
        cycle_number=1,
        commit_type="feat",
        files=None,
        skip_paths=frozenset(),
        issue_number=999,
    )
    from mcp_server.schemas.tool_outputs import GitCommitOutput  # noqa: PLC0415

    assert isinstance(result, GitCommitOutput)
    assert result.success is True
    assert result.commit_hash == "case123"


def test_git_commit_input_allows_implementation_without_cycle_number() -> None:
    """C5: @model_validator removed; GitCommitInput allows implementation phase
    without cycle_number.


    The enforcement moved to execute(). Model construction must not raise.
    """
    params = GitCommitInput(workflow_phase="implementation", message="test commit")
    assert params.workflow_phase == "implementation"
    assert params.cycle_number is None


@pytest.mark.asyncio
async def test_git_commit_cycle_number_required_auto_detect_path(
    mock_git_manager: MagicMock,
) -> None:
    """C5 regression: auto-detect path resolves cycle-based phase → error when cycle_number omitted.

    workflow_phase is not passed by the caller; execute() loads state.json and resolves
    current_phase='implementation'. Because the phase is cycle-based, the runtime guard must
    return ToolResult.error before attempting the commit.
    """
    mock_state = MagicMock()
    mock_state.current_phase = "implementation"
    mock_state.workflow_name = "feature"
    mock_state.issue_number = 42

    mock_state_engine = MagicMock()
    mock_state_engine.get_state.return_value = mock_state

    mock_resolver = MagicMock()
    mock_resolver.is_cycle_based_phase.return_value = True

    tool = GitCommitTool(
        manager=mock_git_manager,
        state_engine=mock_state_engine,
        phase_contract_resolver=mock_resolver,
    )

    params = GitCommitInput(message="commit without cycle")
    result = await tool.execute(params, NoteContext())

    assert isinstance(result, GitCommitOutput)
    assert result.success is False
    assert result.error_message is not None
    assert "cycle_number" in result.error_message.lower()
    mock_git_manager.commit_with_scope.assert_not_called()


@pytest.mark.asyncio
async def test_git_commit_cycle_number_required_explicit_path(
    mock_git_manager: MagicMock,
) -> None:
    """C5 regression: explicit cycle-based phase with no cycle_number → execute-level error.

    The caller passes workflow_phase='implementation' explicitly, but omits cycle_number.
    The runtime guard in execute() must return ToolResult.error regardless of the path.
    """
    mock_state = MagicMock()
    mock_state.workflow_name = "feature"
    mock_state.issue_number = 99

    mock_state_engine = MagicMock()
    mock_state_engine.get_state.return_value = mock_state

    mock_resolver = MagicMock()
    mock_resolver.is_cycle_based_phase.return_value = True

    tool = GitCommitTool(
        manager=mock_git_manager,
        state_engine=mock_state_engine,
        phase_contract_resolver=mock_resolver,
    )

    params = GitCommitInput(workflow_phase="implementation", message="explicit no cycle")
    result = await tool.execute(params, NoteContext())

    assert isinstance(result, GitCommitOutput)
    assert result.success is False
    assert result.error_message is not None
    assert "cycle_number" in result.error_message.lower()
    mock_git_manager.commit_with_scope.assert_not_called()


@pytest.mark.asyncio
async def test_git_commit_integration_workflow_phases() -> None:
    """Integration test: Full commit workflow with real workphases.yaml."""
    # Create a real GitManager with mocked adapter but real workphases config
    mock_adapter = MagicMock()
    mock_adapter.commit.return_value = "integration123"

    loader = ConfigLoader(config_root=Path(f"{get_default_server_root()}/config"))
    git_config = loader.load_git_config()
    workphases_config = loader.load_workphases_config()
    manager = GitManager(
        git_config=git_config,
        adapter=mock_adapter,
        workphases_config=workphases_config,
    )
    resolver = MagicMock(
        side_effect=lambda _branch, workflow_phase, sub_phase: {
            ("implementation", "red"): "test",
            ("implementation", "green"): "feat",
            ("implementation", "refactor"): "refactor",
        }.get((workflow_phase, sub_phase))
    )
    tool = GitCommitTool(manager=manager, commit_type_resolver=resolver)
    manager.adapter.get_current_branch.return_value = "feature/999-e2e-test"

    # Test 1: Research phase (no subphase)
    params1 = GitCommitInput(message="investigate alternatives", workflow_phase="research")
    result1 = await tool.execute(params1, NoteContext())

    from mcp_server.schemas.tool_outputs import GitCommitOutput  # noqa: PLC0415

    assert isinstance(result1, GitCommitOutput)
    assert result1.success is True
    assert result1.commit_hash == "integration123"
    mock_adapter.commit.assert_called_with(
        "docs(P_RESEARCH): investigate alternatives (#999)", files=None, skip_paths=frozenset()
    )

    # Test 2: TDD with subphase
    params2 = GitCommitInput(
        message="add failing test",
        workflow_phase="implementation",
        sub_phase="red",
        cycle_number=1,
    )
    result2 = await tool.execute(params2, NoteContext())

    assert isinstance(result2, GitCommitOutput)
    assert result2.success is True
    assert result2.commit_hash == "integration123"
    mock_adapter.commit.assert_called_with(
        "test(P_IMPLEMENTATION_SP_C1_RED): add failing test (#999)",
        files=None,
        skip_paths=frozenset(),
    )

    # Test 3: Coordination phase (NEW)
    params3 = GitCommitInput(
        message="delegate to child issues",
        workflow_phase="coordination",
        sub_phase="delegation",
    )
    result3 = await tool.execute(params3, NoteContext())

    assert isinstance(result3, GitCommitOutput)
    assert result3.success is True
    assert result3.commit_hash == "integration123"
    mock_adapter.commit.assert_called_with(
        "chore(P_COORDINATION_SP_DELEGATION): delegate to child issues (#999)",
        files=None,
        skip_paths=frozenset(),
    )


@pytest.mark.asyncio
async def test_git_checkout_tool(mock_git_manager: MagicMock) -> None:
    """Test git checkout tool with PhaseStateEngine state sync."""
    # Mock PhaseStateEngine to return state with phase info
    mock_engine = MagicMock()
    mock_state = MagicMock()
    mock_state.current_phase = "implementation"
    mock_state.parent_branch = None
    mock_engine.get_state.return_value = mock_state

    tool = GitCheckoutTool(manager=mock_git_manager, state_engine=mock_engine)
    params = GitCheckoutInput(branch="main")
    result = await tool.execute(params, NoteContext())

    mock_git_manager.checkout.assert_called_once_with("main")
    mock_engine.get_state.assert_called_once_with("main")
    from mcp_server.schemas.tool_outputs import GitCheckoutOutput  # noqa: PLC0415

    assert isinstance(result, GitCheckoutOutput)
    assert result.success is True
    assert result.branch == "main"
    assert result.current_phase == "implementation"


@pytest.mark.asyncio
async def test_git_checkout_tool_displays_parent_branch(mock_git_manager: MagicMock) -> None:
    """Test git checkout displays parent_branch when present.

    Issue #79: Show parent_branch in checkout output for context.
    """
    tool = GitCheckoutTool(manager=mock_git_manager)

    # Mock PhaseStateEngine to return state with parent_branch
    mock_engine = MagicMock()
    mock_state = MagicMock()
    mock_state.current_phase = "design"
    mock_state.parent_branch = "epic/76-quality-gates"
    mock_engine.get_state.return_value = mock_state

    tool = GitCheckoutTool(manager=mock_git_manager, state_engine=mock_engine)
    params = GitCheckoutInput(branch="feature/79-test")
    result = await tool.execute(params, NoteContext())

    mock_git_manager.checkout.assert_called_once_with("feature/79-test")
    from mcp_server.schemas.tool_outputs import GitCheckoutOutput  # noqa: PLC0415

    assert isinstance(result, GitCheckoutOutput)
    assert result.success is True
    assert result.branch == "feature/79-test"
    assert result.current_phase == "design"
    assert result.parent_branch == "epic/76-quality-gates"


@pytest.mark.asyncio
async def test_git_checkout_tool_no_parent_branch(mock_git_manager: MagicMock) -> None:
    """Test git checkout without parent_branch doesn't show it.

    Issue #79: Backward compatibility - don't show parent if None.
    """
    tool = GitCheckoutTool(manager=mock_git_manager)

    # Mock PhaseStateEngine to return state WITHOUT parent_branch
    mock_engine = MagicMock()
    mock_state = MagicMock()
    mock_state.current_phase = "implementation"
    mock_state.parent_branch = None
    mock_engine.get_state.return_value = mock_state

    tool = GitCheckoutTool(manager=mock_git_manager, state_engine=mock_engine)
    params = GitCheckoutInput(branch="main")
    result = await tool.execute(params, NoteContext())

    mock_git_manager.checkout.assert_called_once_with("main")
    from mcp_server.schemas.tool_outputs import GitCheckoutOutput  # noqa: PLC0415

    assert isinstance(result, GitCheckoutOutput)
    assert result.success is True
    assert result.branch == "main"
    assert result.current_phase == "implementation"
    assert result.parent_branch is None


@pytest.mark.asyncio
async def test_git_push_tool(mock_git_manager: MagicMock) -> None:
    """Test git push tool."""
    tool = GitPushTool(manager=mock_git_manager)
    mock_git_manager.get_status.return_value = {"branch": "feature/foo"}

    params = GitPushInput(set_upstream=True)
    result = await tool.execute(params, NoteContext())

    mock_git_manager.push.assert_called_once_with(set_upstream=True)

    assert isinstance(result, GitPushOutput)
    assert result.success is True
    assert result.branch == "feature/foo"
    assert result.set_upstream is True


@pytest.mark.asyncio
async def test_git_merge_tool(mock_git_manager: MagicMock) -> None:
    """Test git merge tool."""
    tool = GitMergeTool(manager=mock_git_manager)
    mock_git_manager.get_status.return_value = {"branch": "main"}

    params = GitMergeInput(branch="feature/foo")
    result = await tool.execute(params, NoteContext())

    mock_git_manager.merge.assert_called_once_with("feature/foo", ANY)

    assert isinstance(result, GitMergeOutput)
    assert result.success is True
    assert result.source_branch == "feature/foo"
    assert result.target_branch == "main"


@pytest.mark.asyncio
async def test_git_delete_branch_tool(mock_git_manager: MagicMock) -> None:
    """Test git delete branch tool."""
    tool = GitDeleteBranchTool(manager=mock_git_manager)
    mock_git_manager.delete_branch.return_value = BranchDeleteResult(
        local_status="deleted", remote_status="deleted"
    )

    params = GitDeleteBranchInput(branch="feature/old", force=True)
    result = await tool.execute(params, NoteContext())
    mock_git_manager.delete_branch.assert_called_once_with(
        "feature/old", ANY, force=True, mode="both"
    )

    assert isinstance(result, GitDeleteBranchOutput)
    assert result.success is True
    assert result.branch == "feature/old"
    assert result.local_status == "deleted"
    assert result.remote_status == "deleted"


@pytest.mark.asyncio
async def test_git_delete_branch_mode_local(mock_git_manager: MagicMock) -> None:
    """Test delete branch tool passes mode=local to manager."""
    tool = GitDeleteBranchTool(manager=mock_git_manager)
    mock_git_manager.delete_branch.return_value = BranchDeleteResult(
        local_status="deleted", remote_status="skipped"
    )

    params = GitDeleteBranchInput(branch="feature/old", mode="local")
    result = await tool.execute(params, NoteContext())

    mock_git_manager.delete_branch.assert_called_once_with(
        "feature/old", ANY, force=False, mode="local"
    )

    assert isinstance(result, GitDeleteBranchOutput)
    assert result.success is True
    assert result.branch == "feature/old"
    assert result.local_status == "deleted"
    assert result.remote_status == "skipped"


@pytest.mark.asyncio
async def test_git_delete_branch_mode_remote(mock_git_manager: MagicMock) -> None:
    """Test delete branch tool passes mode=remote to manager."""
    tool = GitDeleteBranchTool(manager=mock_git_manager)
    mock_git_manager.delete_branch.return_value = BranchDeleteResult(
        local_status="skipped", remote_status="deleted"
    )

    params = GitDeleteBranchInput(branch="feature/old", mode="remote")
    result = await tool.execute(params, NoteContext())

    mock_git_manager.delete_branch.assert_called_once_with(
        "feature/old", ANY, force=False, mode="remote"
    )

    assert isinstance(result, GitDeleteBranchOutput)
    assert result.success is True
    assert result.branch == "feature/old"
    assert result.local_status == "skipped"
    assert result.remote_status == "deleted"


@pytest.mark.asyncio
async def test_git_stash_tool(mock_git_manager: MagicMock) -> None:
    """Test git stash tool with different actions."""
    tool = GitStashTool(manager=mock_git_manager)

    # Push

    # Push
    result = await tool.execute(GitStashInput(action="push", message="wip"), NoteContext())
    mock_git_manager.stash.assert_called_with(message="wip", include_untracked=False)
    assert isinstance(result, GitStashOutput)
    assert result.success is True
    assert result.action == "push"
    assert result.message == "wip"

    # Pop
    result = await tool.execute(GitStashInput(action="pop"), NoteContext())
    mock_git_manager.stash_pop.assert_called_once()
    assert isinstance(result, GitStashOutput)
    assert result.success is True
    assert result.action == "pop"

    # List
    mock_git_manager.stash_list.return_value = ["stash@{0}: wip"]
    result = await tool.execute(GitStashInput(action="list"), NoteContext())
    assert isinstance(result, GitStashOutput)
    assert result.success is True
    assert result.action == "list"
    assert result.stashes == ["stash@{0}: wip"]


@pytest.mark.asyncio
async def test_git_restore_tool(mock_git_manager: MagicMock) -> None:
    """Test git restore tool."""
    tool = GitRestoreTool(manager=mock_git_manager)

    params = GitRestoreInput(files=["foo.py", "bar.py"], source="HEAD")
    result = await tool.execute(params, NoteContext())

    mock_git_manager.restore.assert_called_once_with(
        files=["foo.py", "bar.py"], note_context=ANY, source="HEAD"
    )

    assert isinstance(result, GitRestoreOutput)
    assert result.success is True
    assert result.files == ["foo.py", "bar.py"]
    assert result.source == "HEAD"
    assert result.files_count == 2


@pytest.mark.asyncio
async def test_get_parent_branch_current_branch() -> None:
    """Test get parent branch for current branch.

    Issue #79: Query parent_branch from PhaseStateEngine state.
    """

    mock_git_manager = MagicMock()
    mock_git_manager.get_current_branch.return_value = "feature/79-parent-branch-tracking"

    mock_engine = MagicMock()
    mock_state = MagicMock()
    mock_state.current_phase = "implementation"
    mock_state.parent_branch = "epic/76-quality-gates"
    mock_engine.get_state.return_value = mock_state

    tool = GetParentBranchTool(manager=mock_git_manager, state_engine=mock_engine)
    params = GetParentBranchInput()
    result = await tool.execute(params, NoteContext())

    mock_engine.get_state.assert_called_once_with("feature/79-parent-branch-tracking")
    assert isinstance(result, GetParentBranchOutput)
    assert result.success
    assert result.branch == "feature/79-parent-branch-tracking"
    assert result.parent_branch == "epic/76-quality-gates"


@pytest.mark.asyncio
async def test_get_parent_branch_specified_branch() -> None:
    """Test get parent branch for specified branch.

    Issue #79: Query parent_branch for any branch, not just current.
    """

    mock_engine = MagicMock()
    mock_state = MagicMock()
    mock_state.current_phase = "design"
    mock_state.parent_branch = "epic/76-quality-gates"
    mock_engine.get_state.return_value = mock_state

    tool = GetParentBranchTool(manager=MagicMock(), state_engine=mock_engine)
    params = GetParentBranchInput(branch="feature/77-error-handling")
    result = await tool.execute(params, NoteContext())

    mock_engine.get_state.assert_called_once_with("feature/77-error-handling")
    assert isinstance(result, GetParentBranchOutput)
    assert result.success
    assert result.branch == "feature/77-error-handling"
    assert result.parent_branch == "epic/76-quality-gates"


@pytest.mark.asyncio
async def test_get_parent_branch_not_set() -> None:
    """Test get parent branch when not set.

    Issue #79: Graceful handling when parent_branch is None.
    """

    mock_engine = MagicMock()
    mock_state = MagicMock()
    mock_state.current_phase = "implementation"
    mock_state.parent_branch = None
    mock_engine.get_state.return_value = mock_state

    tool = GetParentBranchTool(manager=MagicMock(), state_engine=mock_engine)
    params = GetParentBranchInput(branch="main")
    result = await tool.execute(params, NoteContext())

    mock_engine.get_state.assert_called_once_with("main")
    assert isinstance(result, GetParentBranchOutput)
    assert result.success
    assert result.branch == "main"
    assert result.parent_branch is None


# ===== Cycle Number Enforcement Tests (Issue #146 Cycle 5) =====


def test_git_commit_implementation_phase_requires_cycle_number() -> None:
    """C5: model_validator removed; construction with implementation phase succeeds.

    Enforcement moved back to execute() (runtime guard via PhaseContractResolver).
    """
    params = GitCommitInput(
        message="update documentation",
        workflow_phase="implementation",
        # cycle_number is MISSING - must not raise at model level after C5
    )
    assert params.cycle_number is None


def test_git_commit_implementation_subphase_requires_cycle_number() -> None:
    """C5: model_validator removed; construction with implementation sub-phase succeeds.

    Enforcement moved back to execute() (runtime guard via PhaseContractResolver).
    """
    params = GitCommitInput(
        message="implement feature",
        workflow_phase="implementation",
        sub_phase="green",
        # cycle_number is MISSING - must not raise at model level after C5
    )
    assert params.cycle_number is None


@pytest.mark.asyncio
async def test_git_commit_non_tdd_allows_no_cycle_number(mock_git_manager: MagicMock) -> None:
    """Test that non-implementation phases do NOT require cycle_number (Issue #146)."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "abc1234"

    # Commit in research phase without cycle_number - should succeed
    params = GitCommitInput(
        message="research alternatives",
        workflow_phase="research",
        # cycle_number is OMITTED - should be allowed
    )

    result = await tool.execute(params, NoteContext())

    # Should succeed
    assert isinstance(result, GitCommitOutput)
    assert result.success is True
    assert result.commit_hash == "abc1234"
    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="research",
        message="research alternatives",
        note_context=ANY,
        sub_phase=None,
        cycle_number=None,
        commit_type=None,
        files=None,
        skip_paths=frozenset(),
        issue_number=999,
    )


@pytest.mark.asyncio
async def test_git_commit_implementation_with_cycle_number_succeeds(
    mock_git_manager: MagicMock,
) -> None:
    """Test that implementation-phase commits WITH cycle_number succeed (Issue #146)."""
    tool = GitCommitTool(manager=mock_git_manager)
    mock_git_manager.commit_with_scope.return_value = "def5678"

    # Commit in implementation phase WITH cycle_number - should succeed
    params = GitCommitInput(
        message="add schema validation",
        workflow_phase="implementation",
        sub_phase="green",
        cycle_number=3,
    )

    result = await tool.execute(params, NoteContext())

    # Should succeed
    assert isinstance(result, GitCommitOutput)
    assert result.success is True
    assert result.commit_hash == "def5678"
    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="implementation",
        message="add schema validation",
        note_context=ANY,
        sub_phase="green",
        cycle_number=3,
        commit_type=None,
        files=None,
        skip_paths=frozenset(),
        issue_number=999,
    )


# --- C2 re-run: commit phase mismatch guard (GAP-07) ---


@pytest.mark.asyncio
async def test_git_add_or_commit_raises_on_phase_mismatch(mock_git_manager: MagicMock) -> None:
    """CommitPhaseMismatchError when workflow_phase doesn't match state.json (GAP-07)."""

    def phase_guard(_branch: str, workflow_phase: str, _cycle_number: int | None) -> None:
        raise CommitPhaseMismatchError(
            f"phase_mismatch: commit says '{workflow_phase}' but state.json says 'design'"
        )

    tool = GitCommitTool(manager=mock_git_manager, phase_guard=phase_guard)
    mock_git_manager.adapter.get_current_branch.return_value = (
        "feature/229-phase-deliverables-enforcement"
    )

    params = GitCommitInput(
        workflow_phase="implementation",
        cycle_number=2,
        message="add red test",
    )
    result = await tool.execute(params, NoteContext())

    assert isinstance(result, GitCommitOutput)
    assert result.success is False
    assert result.error_message is not None
    assert "phase_mismatch" in result.error_message


@pytest.mark.asyncio
async def test_git_add_or_commit_raises_on_cycle_mismatch(mock_git_manager: MagicMock) -> None:
    """CommitPhaseMismatchError when cycle_number mismatches state.json (GAP-07)."""

    def phase_guard(_branch: str, _workflow_phase: str, cycle_number: int | None) -> None:
        raise CommitPhaseMismatchError(
            f"phase_mismatch: commit says cycle {cycle_number} but state.json says cycle 3"
        )

    tool = GitCommitTool(manager=mock_git_manager, phase_guard=phase_guard)
    mock_git_manager.adapter.get_current_branch.return_value = (
        "feature/229-phase-deliverables-enforcement"
    )

    params = GitCommitInput(
        workflow_phase="implementation",
        cycle_number=2,
        message="add green impl",
    )
    result = await tool.execute(params, NoteContext())

    assert isinstance(result, GitCommitOutput)
    assert result.success is False
    assert result.error_message is not None
    assert "phase_mismatch" in result.error_message


@pytest.mark.asyncio
async def test_git_add_or_commit_passes_when_phase_and_cycle_match(
    mock_git_manager: MagicMock,
) -> None:
    """No error when workflow_phase and cycle_number match state.json (GAP-07)."""

    def phase_guard(_branch: str, _workflow_phase: str, _cycle_number: int | None) -> None:
        pass  # phase=implementation, cycle=2 matches state.json

    tool = GitCommitTool(manager=mock_git_manager, phase_guard=phase_guard)
    mock_git_manager.adapter.get_current_branch.return_value = (
        "feature/229-phase-deliverables-enforcement"
    )
    mock_git_manager.commit_with_scope.return_value = "abc1234"

    params = GitCommitInput(
        workflow_phase="implementation",
        cycle_number=2,
        message="implement guard",
    )
    result = await tool.execute(params, NoteContext())

    assert isinstance(result, GitCommitOutput)
    assert result.success is True
    assert result.commit_hash == "abc1234"


@pytest.mark.asyncio
async def test_git_commit_no_state_json_returns_error(mock_git_manager: MagicMock) -> None:
    """GitCommitTool returns ToolResult.error when state.json is missing (e.g. main)."""
    mock_state_engine = MagicMock()
    mock_state_engine.get_state.side_effect = FileNotFoundError("Branch state for 'main' not found")
    mock_git_manager.adapter.get_current_branch.return_value = "main"

    tool = GitCommitTool(manager=mock_git_manager, state_engine=mock_state_engine)

    # No workflow_phase — triggers auto-detect from state.json
    params = GitCommitInput(message="chore: cleanup")

    result = await tool.execute(params, NoteContext())

    assert isinstance(result, GitCommitOutput)
    assert result.success is False
    error_text = result.error_message
    assert error_text is not None
    assert "workflow_phase" in error_text
    assert "main" in error_text


class TestGitCommitBranchMismatch:
    """C_ENGINE_BREAK: GitCommitTool handles StateBranchMismatchError (issue #231, cycle 2)."""

    @pytest.mark.asyncio
    async def test_commit_auto_detect_handles_branch_mismatch(
        self, mock_git_manager: MagicMock
    ) -> None:
        """Auto-detect path must catch StateBranchMismatchError and return ToolResult.error."""
        mock_state_engine = MagicMock()
        mock_state_engine.get_state.side_effect = StateBranchMismatchError(
            "Loaded state branch 'main' does not match requested branch 'feature/231-test'"
        )
        mock_git_manager.adapter.get_current_branch.return_value = "feature/231-test"

        tool = GitCommitTool(manager=mock_git_manager, state_engine=mock_state_engine)
        params = GitCommitInput(message="chore: cleanup")

        result = await tool.execute(params, NoteContext())

        assert isinstance(result, GitCommitOutput)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_commit_type_resolver_returns_none_on_branch_mismatch(
        self, mock_git_manager: MagicMock
    ) -> None:
        """build_commit_type_resolver returns None (no type) on StateBranchMismatchError."""
        mock_state_engine = MagicMock()
        mock_state_engine.get_state.side_effect = StateBranchMismatchError(
            "Loaded state branch 'main' does not match requested branch 'feature/231-test'"
        )
        mock_git_manager.adapter.get_current_branch.return_value = "feature/231-test"
        mock_git_manager.commit_with_scope.return_value = "abc1234"

        resolver_fn = MagicMock(return_value=None)
        tool = GitCommitTool(manager=mock_git_manager, commit_type_resolver=resolver_fn)
        params = GitCommitInput(
            message="refactor cleanup",
            workflow_phase="implementation",
            sub_phase="refactor",
            cycle_number=2,
        )

        result = await tool.execute(params, NoteContext())

        assert isinstance(result, GitCommitOutput)
        assert result.success is True
        assert result.commit_hash == "abc1234"

    @pytest.mark.asyncio
    async def test_get_parent_branch_handles_branch_mismatch(
        self, mock_git_manager: MagicMock
    ) -> None:
        """GetParentBranchTool.execute() returns error on StateBranchMismatchError."""

        mock_state_engine = MagicMock()
        mock_state_engine.get_state.side_effect = StateBranchMismatchError(
            "Loaded state branch 'main' does not match requested branch 'feature/231-test'"
        )
        mock_git_manager.get_current_branch.return_value = "feature/231-test"

        tool = GetParentBranchTool(manager=mock_git_manager, state_engine=mock_state_engine)
        params = GetParentBranchInput()

        result = await tool.execute(params, NoteContext())

        assert isinstance(result, GetParentBranchOutput)
        assert not result.success
        assert result.error_message is not None
        assert "does not match requested branch" in result.error_message


# ---------------------------------------------------------------------------
# C5 RED — GitCommitTool triggers record_sub_phase (issue #298)
# ---------------------------------------------------------------------------


class TestGitCommitToolRecordSubPhase:
    """C5 (issue #298): GitCommitTool.execute() calls record_sub_phase after every commit."""

    @pytest.mark.asyncio
    async def test_git_commit_tool_calls_record_sub_phase_with_sub_phase(
        self, mock_git_manager: MagicMock
    ) -> None:
        """After a successful commit with sub_phase='red', record_sub_phase is called with 'red'."""
        mock_state_engine = MagicMock()
        mock_git_manager.commit_with_scope.return_value = "aabbccdd"
        mock_git_manager.adapter.get_current_branch.return_value = "feature/298-test"

        tool = GitCommitTool(manager=mock_git_manager, state_engine=mock_state_engine)
        params = GitCommitInput(
            workflow_phase="implementation",
            cycle_number=1,
            sub_phase="red",
            message="add failing test",
        )
        result = await tool.execute(params, NoteContext())

        assert isinstance(result, GitCommitOutput)
        assert result.success is True
        mock_state_engine.record_sub_phase.assert_called_once_with("feature/298-test", "red")

    @pytest.mark.asyncio
    async def test_git_commit_tool_calls_record_sub_phase_with_none(
        self, mock_git_manager: MagicMock
    ) -> None:
        """After a successful commit with sub_phase=None, record_sub_phase is called with None."""
        mock_state_engine = MagicMock()
        mock_git_manager.commit_with_scope.return_value = "11223344"
        mock_git_manager.adapter.get_current_branch.return_value = "feature/298-test"

        tool = GitCommitTool(manager=mock_git_manager, state_engine=mock_state_engine)
        params = GitCommitInput(
            workflow_phase="research",
            message="initial research notes",
        )
        result = await tool.execute(params, NoteContext())

        assert isinstance(result, GitCommitOutput)
        assert result.success is True
        mock_state_engine.record_sub_phase.assert_called_once_with("feature/298-test", None)

    @pytest.mark.asyncio
    async def test_git_commit_tool_does_not_call_record_sub_phase_when_engine_none(
        self, mock_git_manager: MagicMock
    ) -> None:
        """When state_engine is None, record_sub_phase must NOT be called (no AttributeError)."""
        mock_git_manager.commit_with_scope.return_value = "deadbeef"
        mock_git_manager.adapter.get_current_branch.return_value = "feature/298-test"

        tool = GitCommitTool(manager=mock_git_manager)  # no state_engine
        params = GitCommitInput(
            workflow_phase="documentation",
            message="update readme",
        )
        result = await tool.execute(params, NoteContext())

        assert isinstance(result, GitCommitOutput)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_git_commit_tool_calls_record_sub_phase_before_commit(
        self, mock_git_manager: MagicMock
    ) -> None:
        """GitCommitTool must record the sub_phase before creating the commit."""
        mock_state_engine = MagicMock()
        mock_git_manager.commit_with_scope.return_value = "aabbccdd"
        mock_git_manager.adapter.get_current_branch.return_value = "feature/298-test"

        # Track call sequence using a parent mock manager
        parent = MagicMock()
        parent.attach_mock(mock_state_engine.record_sub_phase, "record_sub_phase")
        parent.attach_mock(mock_git_manager.commit_with_scope, "commit_with_scope")

        tool = GitCommitTool(manager=mock_git_manager, state_engine=mock_state_engine)
        params = GitCommitInput(
            workflow_phase="implementation",
            cycle_number=1,
            sub_phase="red",
            message="add failing test",
        )
        result = await tool.execute(params, NoteContext())

        assert isinstance(result, GitCommitOutput)
        assert result.success is True

        # Verify record_sub_phase was called before commit_with_scope
        calls = [c[0] for c in parent.mock_calls]
        assert "record_sub_phase" in calls
        assert "commit_with_scope" in calls
        assert calls.index("record_sub_phase") < calls.index("commit_with_scope")

    @pytest.mark.asyncio
    async def test_git_commit_tool_rolls_back_sub_phase_on_commit_failure(
        self, mock_git_manager: MagicMock
    ) -> None:
        """If the commit fails, GitCommitTool must roll back the sub_phase to its original value."""
        mock_state_engine = MagicMock()
        mock_state_engine.get_state.return_value.current_sub_phase = "green"
        mock_git_manager.commit_with_scope.side_effect = Exception("Commit failed!")
        mock_git_manager.adapter.get_current_branch.return_value = "feature/298-test"

        tool = GitCommitTool(manager=mock_git_manager, state_engine=mock_state_engine)
        params = GitCommitInput(
            workflow_phase="implementation",
            cycle_number=1,
            sub_phase="refactor",
            message="clean up code",
        )
        result = await tool.execute(params, NoteContext())

        assert isinstance(result, GitCommitOutput)
        assert result.success is False
        assert result.error_message is not None and "Commit failed!" in result.error_message

        # Assert sequence:
        # 1. get_state called to retrieve original subphase ("green")
        # 2. record_sub_phase called with "refactor"
        # 3. record_sub_phase called with "green" (rollback) after exception
        mock_state_engine.get_state.assert_called_once_with("feature/298-test")

        # Verify both calls in order
        calls = mock_state_engine.record_sub_phase.mock_calls
        assert len(calls) == 2
        assert calls[0][1] == ("feature/298-test", "refactor")
        assert calls[1][1] == ("feature/298-test", "green")

    @pytest.mark.asyncio
    async def test_git_commit_tool_appends_state_json_to_files_list(
        self, mock_git_manager: MagicMock
    ) -> None:
        """GitCommitTool must dynamically resolve state.json's path and append it to files."""
        mock_state_engine = MagicMock()
        repo_path = "C:/temp/pgmcp"
        state_path = "C:/temp/pgmcp/.pgmcp/state.json"

        mock_state_engine.state_path = state_path
        mock_git_manager.adapter.repo_path = repo_path
        mock_git_manager.commit_with_scope.return_value = "aabbccdd"
        mock_git_manager.adapter.get_current_branch.return_value = "feature/298-test"

        tool = GitCommitTool(manager=mock_git_manager, state_engine=mock_state_engine)
        params = GitCommitInput(
            workflow_phase="implementation",
            cycle_number=1,
            sub_phase="red",
            message="add failing test",
            files=["src/foo.py"],
        )
        result = await tool.execute(params, NoteContext())

        assert isinstance(result, GitCommitOutput)
        assert result.success is True

        mock_git_manager.commit_with_scope.assert_called_once()
        called_kwargs = mock_git_manager.commit_with_scope.call_args[1]
        assert called_kwargs["files"] == ["src/foo.py", ".pgmcp/state.json"]


# C_228.2 RED — issue_number wiring in GitCommitTool (issue #228)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_commit_tool_auto_detect_includes_suffix(mock_git_manager: MagicMock) -> None:
    """Auto-detect path: get_state() returns issue_number=42.

    commit_with_scope must be called with issue_number=42.
    """
    mock_state_engine = MagicMock()
    branch_state_stub = MagicMock()
    branch_state_stub.current_phase = "research"
    branch_state_stub.issue_number = 42
    mock_state_engine.get_state.return_value = branch_state_stub

    mock_git_manager.adapter.get_current_branch.return_value = "feature/42-my-feature"
    mock_git_manager.commit_with_scope.return_value = "abc1234"

    tool = GitCommitTool(manager=mock_git_manager, state_engine=mock_state_engine)
    params = GitCommitInput(message="implement suffix")
    # workflow_phase is None → triggers auto-detect

    result = await tool.execute(params, NoteContext())

    mock_state_engine.get_state.assert_called_once_with("feature/42-my-feature")
    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="research",
        message="implement suffix",
        note_context=ANY,
        sub_phase=None,
        cycle_number=None,
        commit_type=ANY,
        files=None,
        skip_paths=frozenset(),
        issue_number=42,
    )
    assert isinstance(result, GitCommitOutput)
    assert result.success is True


@pytest.mark.asyncio
async def test_commit_tool_explicit_phase_uses_git_config(mock_git_manager: MagicMock) -> None:
    """Explicit workflow_phase: git_config.extract_issue_number called; no get_state call."""
    mock_git_manager.adapter.get_current_branch.return_value = "feature/42-my-feature"
    mock_git_manager.git_config.extract_issue_number.side_effect = None
    mock_git_manager.git_config.extract_issue_number.return_value = 42
    mock_git_manager.commit_with_scope.return_value = "abc1234"

    tool = GitCommitTool(manager=mock_git_manager)
    params = GitCommitInput(
        message="complete research",
        workflow_phase="research",
    )

    result = await tool.execute(params, NoteContext())

    mock_git_manager.git_config.extract_issue_number.assert_called_once_with(
        "feature/42-my-feature"
    )
    mock_git_manager.commit_with_scope.assert_called_once_with(
        workflow_phase="research",
        message="complete research",
        note_context=ANY,
        sub_phase=None,
        cycle_number=None,
        commit_type=ANY,
        files=None,
        skip_paths=frozenset(),
        issue_number=42,
    )
    assert isinstance(result, GitCommitOutput)
    assert result.success is True


@pytest.mark.asyncio
async def test_commit_tool_auto_detect_mismatch_returns_error(mock_git_manager: MagicMock) -> None:
    """StateBranchMismatchError on auto-detect path returns ToolResult.error.

    Must not silently degrade to issue_number=None.
    """
    mock_state_engine = MagicMock()
    mock_state_engine.get_state.side_effect = StateBranchMismatchError(
        "Loaded state branch 'main' does not match requested branch 'feature/42-test'"
    )
    mock_git_manager.adapter.get_current_branch.return_value = "feature/42-test"

    tool = GitCommitTool(manager=mock_git_manager, state_engine=mock_state_engine)
    params = GitCommitInput(message="chore: cleanup")

    result = await tool.execute(params, NoteContext())

    assert isinstance(result, GitCommitOutput)
    assert result.success is False
    mock_git_manager.commit_with_scope.assert_not_called()


@pytest.mark.asyncio
async def test_git_checkout_resets_context_loaded_on_success(
    mock_git_manager: MagicMock,
) -> None:
    """writer.set_context_loaded(branch, False) called on successful checkout."""
    writer = MagicMock(spec=IContextLoadedWriter)
    tool = GitCheckoutTool(manager=mock_git_manager, context_loaded_writer=writer)

    params = GitCheckoutInput(branch="feature/268-test")
    result = await tool.execute(params, NoteContext())

    assert isinstance(result, GitCheckoutOutput)
    assert result.success is True
    writer.set_context_loaded.assert_called_once_with("feature/268-test", value=False)


@pytest.mark.asyncio
async def test_git_checkout_no_reset_when_writer_none(
    mock_git_manager: MagicMock,
) -> None:
    """No error when context_loaded_writer=None and checkout succeeds."""
    tool = GitCheckoutTool(manager=mock_git_manager, context_loaded_writer=None)

    params = GitCheckoutInput(branch="feature/268-test")
    result = await tool.execute(params, NoteContext())

    assert isinstance(result, GitCheckoutOutput)
    assert result.success is True


# ---------------------------------------------------------------------------
# CheckMergeTool tests (C6 RED)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_merge_sha_is_ancestor(mock_git_manager: MagicMock) -> None:
    """SHA is an ancestor of HEAD -> CheckMergeOutput returned."""

    mock_git_manager.is_ancestor.return_value = True
    tool = CheckMergeTool(manager=mock_git_manager)

    params = CheckMergeInput(merge_sha="abc1234")
    result = await tool.execute(params, NoteContext())

    assert isinstance(result, CheckMergeOutput)
    assert result.success
    assert result.is_ancestor is True
    mock_git_manager.is_ancestor.assert_called_once_with("abc1234")


@pytest.mark.asyncio
async def test_check_merge_sha_not_ancestor(mock_git_manager: MagicMock) -> None:
    """SHA is not an ancestor -> CheckMergeOutput with success=False returned."""

    mock_git_manager.is_ancestor.return_value = False
    tool = CheckMergeTool(manager=mock_git_manager)

    params = CheckMergeInput(merge_sha="abc1234")
    result = await tool.execute(params, NoteContext())

    assert isinstance(result, CheckMergeOutput)
    assert not result.success
    assert result.is_ancestor is False
    mock_git_manager.is_ancestor.assert_called_once_with("abc1234")


@pytest.mark.asyncio
async def test_check_merge_git_error_raises(mock_git_manager: MagicMock) -> None:
    """Git command fails -> execute returns CheckMergeOutput with success=False."""

    mock_git_manager.is_ancestor.side_effect = ExecutionError("git error status 2")
    tool = CheckMergeTool(manager=mock_git_manager)

    params = CheckMergeInput(merge_sha="abc1234")
    result = await tool.execute(params, NoteContext())

    assert isinstance(result, CheckMergeOutput)
    assert not result.success
    assert result.error_message is not None
    assert "git error status 2" in result.error_message


@pytest.mark.asyncio
async def test_check_merge_manager_delegates_to_adapter() -> None:
    """GitManager.is_ancestor delegates to GitAdapter.is_ancestor and propagates value."""
    mock_adapter = MagicMock(spec=GitAdapter)
    mock_adapter.is_ancestor.return_value = True
    mock_adapter.get_current_branch.return_value = "bug/357-fix-agent-lifecycle"

    mock_git_config = MagicMock()
    mock_git_config.default_base_branch = "main"

    real_manager = GitManager(git_config=mock_git_config, adapter=mock_adapter)
    result = real_manager.is_ancestor("abc1234")

    assert result is True
    mock_adapter.is_ancestor.assert_called_once_with("abc1234")


# ---------------------------------------------------------------------------
# GitListBranchesTool and GitDiffTool tests (Cycle 4 RED)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_git_list_branches_tool(mock_git_manager: MagicMock) -> None:
    """Test GitListBranchesTool returns GitListBranchesOutput DTO."""
    from mcp_server.schemas.tool_outputs import GitListBranchesOutput  # noqa: PLC0415
    from mcp_server.tools.git_analysis_tools import (  # noqa: PLC0415
        GitListBranchesInput,
        GitListBranchesTool,
    )

    tool = GitListBranchesTool(manager=mock_git_manager)
    mock_git_manager.get_current_branch.return_value = "feature/402"
    mock_git_manager.list_branches.return_value = [
        "  main",
        "* feature/402",
        "  remotes/origin/main",
    ]

    result = await tool.execute(GitListBranchesInput(), NoteContext())

    assert isinstance(result, GitListBranchesOutput)
    assert result.success
    assert result.current_branch == "feature/402"
    assert result.branches_count == 3
    assert len(result.branches) == 3
    assert result.branches[0].name == "main"
    assert result.branches[0].is_current is False
    assert result.branches[1].name == "feature/402"
    assert result.branches[1].is_current is True


@pytest.mark.asyncio
async def test_git_diff_tool(mock_git_manager: MagicMock) -> None:
    """Test GitDiffTool returns GitDiffOutput DTO."""
    from mcp_server.schemas.tool_outputs import GitDiffOutput  # noqa: PLC0415
    from mcp_server.tools.git_analysis_tools import GitDiffInput, GitDiffTool  # noqa: PLC0415

    tool = GitDiffTool(manager=mock_git_manager)
    mock_git_manager.compare_branches.return_value = (
        " 3 files changed, 45 insertions(+), 12 deletions(-)\n"
    )

    params = GitDiffInput(source_branch="main", target_branch="feature/402")
    result = await tool.execute(params, NoteContext())

    assert isinstance(result, GitDiffOutput)
    assert result.success
    assert result.source_branch == "main"
    assert result.target_branch == "feature/402"
    assert result.files_changed == 3
    assert result.insertions == 45
    assert result.deletions == 12

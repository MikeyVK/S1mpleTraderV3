"""Unit tests for GitManager."""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
from pathlib import Path
from unittest.mock import MagicMock

# Third-party
import pytest

from mcp_server.core.exceptions import PreflightError, ValidationError

# Module under test
from mcp_server.managers.git_manager import GitManager


class TestGitManagerValidation:
    """Test suite for GitManager validation and branching logic."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        """Fixture for mocked GitAdapter."""
        adapter = MagicMock()
        adapter.is_clean.return_value = True
        return adapter

    @pytest.fixture
    def manager(self, mock_adapter: MagicMock) -> GitManager:
        """Fixture for GitManager with mocked adapter."""
        return GitManager(adapter=mock_adapter)

    def test_init_default(self) -> None:
        """Test initialization with default adapter."""
        mgr = GitManager()
        assert mgr.adapter is not None

    def test_get_status(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test get_status delegation."""
        mock_adapter.get_status.return_value = {"branch": "main"}
        status = manager.get_status()
        assert status == {"branch": "main"}
        mock_adapter.get_status.assert_called_once()

    def test_create_branch_valid(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test creating a branch with explicit base."""
        name = manager.create_branch("my-feature", "feature", "HEAD")

        assert name == "feature/my-feature"
        mock_adapter.create_branch.assert_called_once_with("feature/my-feature", base="HEAD")
        mock_adapter.is_clean.assert_called_once()

    def test_create_branch_epic_valid(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test creating an epic branch with explicit base."""
        name = manager.create_branch("91-test-suite-cleanup", "epic", "HEAD")

        assert name == "epic/91-test-suite-cleanup"
        mock_adapter.create_branch.assert_called_once_with(
            "epic/91-test-suite-cleanup", base="HEAD"
        )
        mock_adapter.is_clean.assert_called_once()

    def test_create_branch_invalid_type(self, manager: GitManager) -> None:
        """Test validation of branch type."""
        with pytest.raises(ValidationError, match="Invalid branch type"):
            manager.create_branch("valid-name", "invalid-type", "HEAD")

    def test_create_branch_invalid_name(self, manager: GitManager) -> None:
        """Test validation of branch name (regex)."""
        with pytest.raises(ValidationError, match="Invalid branch name"):
            manager.create_branch("Bad Name!", "feature", "HEAD")

    def test_create_branch_dirty(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test pre-flight check failure for dirty working directory."""
        mock_adapter.is_clean.return_value = False

        with pytest.raises(PreflightError, match="Working directory is not clean"):
            manager.create_branch("valid-name", "feature", "HEAD")


    def test_delete_branch_protected(self, manager: GitManager) -> None:
        """Test deletion of protected branch is prevented."""
        with pytest.raises(ValidationError, match="Cannot delete protected branch"):
            manager.delete_branch("main")


class TestGitManagerOperations:
    """Test suite for GitManager operations (commit, merge, stash)."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        """Fixture for mocked GitAdapter."""
        adapter = MagicMock()
        adapter.is_clean.return_value = True
        return adapter

    @pytest.fixture
    def manager(self, mock_adapter: MagicMock) -> GitManager:
        """Fixture for GitManager with mocked adapter."""
        return GitManager(adapter=mock_adapter)

    def test_restore_success(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test restore operation."""
        manager.restore(files=["a.py", "b.py"], source="HEAD")

        mock_adapter.restore.assert_called_once_with(files=["a.py", "b.py"], source="HEAD")

    def test_restore_requires_files(self, manager: GitManager) -> None:
        """Test restore operation requires files."""
        with pytest.raises(ValidationError):
            manager.restore(files=[])

    def test_checkout(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test checkout delegation."""
        manager.checkout("main")
        mock_adapter.checkout.assert_called_once_with("main")

    def test_push(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test push delegation."""
        manager.push(set_upstream=True)
        mock_adapter.push.assert_called_once_with(set_upstream=True)

    def test_merge_clean(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test merge with clean state."""
        manager.merge("feature-branch")
        mock_adapter.merge.assert_called_once_with("feature-branch")

    def test_merge_dirty(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test merge fails with dirty state."""
        mock_adapter.is_clean.return_value = False
        with pytest.raises(PreflightError, match="Working directory is not clean"):
            manager.merge("feature-branch")

    def test_delete_branch_valid(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test deleting a valid branch."""
        manager.delete_branch("feature/old")
        mock_adapter.delete_branch.assert_called_once_with("feature/old", force=False)

    def test_stash_operations(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test stash delegations."""
        manager.stash("saving work")
        mock_adapter.stash.assert_called_with(message="saving work", include_untracked=False)

        manager.stash("saving work", include_untracked=True)
        mock_adapter.stash.assert_called_with(message="saving work", include_untracked=True)

        manager.stash_pop()
        mock_adapter.stash_pop.assert_called_once()

        mock_adapter.stash_list.return_value = ["stash@{0}"]
        assert manager.stash_list() == ["stash@{0}"]

    def test_get_current_branch(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test getting current branch."""
        mock_adapter.get_current_branch.return_value = "main"
        assert manager.get_current_branch() == "main"

    def test_list_branches(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test listing branches."""
        mock_adapter.list_branches.return_value = ["main", "dev"]
        assert manager.list_branches(verbose=True) == ["main", "dev"]
        mock_adapter.list_branches.assert_called_with(verbose=True, remote=False)

    def test_compare_branches(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test diff stat delegation."""
        mock_adapter.get_diff_stat.return_value = "diff"
        assert manager.compare_branches("main", "feat") == "diff"
        mock_adapter.get_diff_stat.assert_called_with("main", "feat")

    def test_get_recent_commits(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test retrieving recent commits."""
        mock_adapter.get_recent_commits.return_value = ["msg1"]
        assert manager.get_recent_commits(1) == ["msg1"]


class TestGitManagerCreateBranch:
    """Tests for NEW create_branch method with explicit base_branch (Issue #64)."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        """Fixture for mocked GitAdapter."""
        adapter = MagicMock()
        adapter.is_clean.return_value = True
        adapter.get_current_branch.return_value = "refactor/51-mcp"
        return adapter

    @pytest.fixture
    def manager(self, mock_adapter: MagicMock) -> GitManager:
        """Fixture for GitManager with mocked adapter."""
        return GitManager(adapter=mock_adapter)

    def test_create_branch_requires_base_branch_parameter(self, manager: GitManager) -> None:
        """RED: create_branch should require base_branch parameter (no default)."""
        with pytest.raises(TypeError):
            manager.create_branch("test", "feature")  # type: ignore[call-arg]

    def test_create_branch_passes_base_to_adapter(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """RED: Should pass base_branch to adapter.create_branch as base."""
        manager.create_branch("test", "feature", "main")

        mock_adapter.create_branch.assert_called_once_with("feature/test", base="main")


class TestGitManagerCommitWithScope:
    """Tests for commit_with_scope method with workflow phase scopes."""

    @pytest.fixture
    def mock_adapter(self) -> MagicMock:
        """Fixture for mocked GitAdapter."""
        return MagicMock()

    @pytest.fixture
    def manager(self, mock_adapter: MagicMock, tmp_path: Path) -> GitManager:
        """Fixture for GitManager with mocked adapter and test workphases."""
        # Create test workphases.yaml
        workphases_path = tmp_path / "workphases.yaml"
        workphases_path.write_text("""
phases:
  research:
    display_name: "Research"
    commit_type_hint: "docs"
    subphases: []
  tdd:
    display_name: "TDD"
    commit_type_hint: null
    subphases: ["red", "green", "refactor"]
  coordination:
    display_name: "Coordination"
    commit_type_hint: "chore"
    subphases: ["delegation", "sync", "review"]
version: "1.0"
""")
        mgr = GitManager(adapter=mock_adapter)
        mgr._workphases_path = workphases_path
        return mgr

    def test_commit_with_scope_phase_only(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with phase-only scope (no subphase)."""
        mock_adapter.commit.return_value = "abc123"

        result = manager.commit_with_scope(
            workflow_phase="research",
            message="investigate alternatives",
        )

        assert result == "abc123"
        mock_adapter.commit.assert_called_once_with(
            "docs(P_RESEARCH): investigate alternatives", files=None
        )

    def test_commit_with_scope_phase_and_subphase(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with phase and subphase."""
        mock_adapter.commit.return_value = "def456"

        result = manager.commit_with_scope(
            workflow_phase="tdd",
            sub_phase="red",
            message="add failing test",
        )

        assert result == "def456"
        mock_adapter.commit.assert_called_once_with(
            "test(P_TDD_SP_RED): add failing test", files=None
        )

    def test_commit_with_scope_with_cycle_number(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with cycle number in TDD format."""
        mock_adapter.commit.return_value = "ghi789"

        result = manager.commit_with_scope(
            workflow_phase="tdd",
            sub_phase="green",
            cycle_number=1,
            message="implement feature",
        )

        assert result == "ghi789"
        mock_adapter.commit.assert_called_once_with(
            "feat(P_TDD_SP_C1_GREEN): implement feature", files=None
        )

    def test_commit_with_scope_coordination_phase(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with coordination phase (new phase type)."""
        mock_adapter.commit.return_value = "jkl012"

        result = manager.commit_with_scope(
            workflow_phase="coordination",
            sub_phase="delegation",
            message="delegate to child issues",
        )

        assert result == "jkl012"
        mock_adapter.commit.assert_called_once_with(
            "chore(P_COORDINATION_SP_DELEGATION): delegate to child issues", files=None
        )

    def test_commit_with_scope_with_files(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with specific files."""
        mock_adapter.commit.return_value = "mno345"

        result = manager.commit_with_scope(
            workflow_phase="tdd",
            sub_phase="refactor",
            message="clean up code",
            files=["src/app.py", "tests/test_app.py"],
        )

        assert result == "mno345"
        mock_adapter.commit.assert_called_once_with(
            "refactor(P_TDD_SP_REFACTOR): clean up code",
            files=["src/app.py", "tests/test_app.py"],
        )

    def test_commit_with_scope_with_commit_type_override(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test commit with explicit commit_type override."""
        mock_adapter.commit.return_value = "pqr678"

        result = manager.commit_with_scope(
            workflow_phase="tdd",
            sub_phase="red",
            message="fix failing test",
            commit_type="fix",  # Override default 'test'
        )

        assert result == "pqr678"
        mock_adapter.commit.assert_called_once_with(
            "fix(P_TDD_SP_RED): fix failing test",
            files=None,
        )

    def test_commit_with_scope_invalid_phase_raises_error(self, manager: GitManager) -> None:
        """Test that invalid phase raises ValueError with actionable message."""
        with pytest.raises(ValueError, match="Unknown workflow phase"):
            manager.commit_with_scope(
                workflow_phase="invalid_phase",
                message="test",
            )

    def test_commit_with_scope_invalid_subphase_raises_error(self, manager: GitManager) -> None:
        """Test that invalid subphase raises ValueError with actionable message."""
        with pytest.raises(ValueError, match="Invalid sub_phase"):
            manager.commit_with_scope(
                workflow_phase="tdd",
                sub_phase="invalid_subphase",
                message="test",
            )

    def test_commit_with_scope_empty_files_raises_error(self, manager: GitManager) -> None:
        """Test that empty files list raises ValidationError."""
        with pytest.raises(ValidationError, match="Files list cannot be empty"):
            manager.commit_with_scope(
                workflow_phase="research",
                message="test",
                files=[],
            )

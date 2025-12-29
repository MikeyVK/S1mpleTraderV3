"""Unit tests for GitManager."""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
from unittest.mock import MagicMock

# Third-party
import pytest

# Module under test
from mcp_server.managers.git_manager import GitManager
from mcp_server.core.exceptions import ValidationError, PreflightError


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

    def test_create_feature_branch_valid(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test creating a valid feature branch."""
        name = manager.create_feature_branch("my-feature", "feature")

        assert name == "feature/my-feature"
        mock_adapter.create_branch.assert_called_once_with("feature/my-feature")
        mock_adapter.is_clean.assert_called_once()

    def test_create_feature_branch_invalid_type(self, manager: GitManager) -> None:
        """Test validation of branch type."""
        with pytest.raises(ValidationError, match="Invalid branch type"):
            manager.create_feature_branch("valid-name", "invalid-type")

    def test_create_feature_branch_invalid_name(self, manager: GitManager) -> None:
        """Test validation of branch name (regex)."""
        with pytest.raises(ValidationError, match="Invalid branch name"):
            manager.create_feature_branch("Bad Name!", "feature")

    def test_create_feature_branch_dirty(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test pre-flight check failure for dirty working directory."""
        mock_adapter.is_clean.return_value = False

        with pytest.raises(PreflightError, match="Working directory is not clean"):
            manager.create_feature_branch("valid-name", "feature")

    def test_commit_tdd_phase_invalid(self, manager: GitManager) -> None:
        """Test validation of TDD phase."""
        with pytest.raises(ValidationError, match="Invalid TDD phase"):
            manager.commit_tdd_phase("blue", "message")

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

    def test_commit_tdd_phase_valid(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test valid TDD commit."""
        mock_adapter.commit.return_value = "hash123"

        result = manager.commit_tdd_phase("red", "failing test")

        assert result == "hash123"
        mock_adapter.commit.assert_called_once_with("test: failing test", files=None)

    def test_commit_tdd_phase_with_files_passes_through(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test valid TDD commit with files."""
        mock_adapter.commit.return_value = "hash123"

        result = manager.commit_tdd_phase("green", "scoped", files=["a.py"])

        assert result == "hash123"
        mock_adapter.commit.assert_called_once_with("feat: scoped", files=["a.py"])

    def test_commit_docs(self, manager: GitManager, mock_adapter: MagicMock) -> None:
        """Test documentation commit helpers."""
        manager.commit_docs("update readme")
        mock_adapter.commit.assert_called_once_with("docs: update readme", files=None)

    def test_commit_docs_with_files_passes_through(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """Test documentation commit helpers with files."""
        manager.commit_docs("update docs", files=["README.md"])

        mock_adapter.commit.assert_called_once_with("docs: update docs", files=["README.md"])

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
        mock_adapter.get_recent_commits.assert_called_with(limit=1)


class TestGitManagerCreateBranch:
    """Tests for create_branch with explicit base_branch parameter (Issue #64)."""

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

    def test_create_feature_branch_requires_base_branch(self, manager: GitManager) -> None:
        """RED: create_feature_branch should require base_branch parameter."""
        with pytest.raises(TypeError, match="base_branch"):
            manager.create_feature_branch("test-feature", "feature")  # Missing base_branch

    def test_create_feature_branch_passes_base_to_adapter(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """RED: Should pass base_branch to adapter.create_branch."""
        manager.create_feature_branch("test-feature", "feature", base_branch="main")

        mock_adapter.create_branch.assert_called_once_with(
            "feature/test-feature", base="main"
        )

    def test_create_feature_branch_with_head(
        self, manager: GitManager, mock_adapter: MagicMock
    ) -> None:
        """RED: Should support HEAD as base_branch."""
        manager.create_feature_branch("test-feature", "feature", base_branch="HEAD")

        mock_adapter.create_branch.assert_called_once_with(
            "feature/test-feature", base="HEAD"
        )

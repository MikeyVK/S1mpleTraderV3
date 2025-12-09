"""Tests for GitAdapter - extended git operations."""
import pytest
from unittest.mock import MagicMock, patch
from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.core.exceptions import ExecutionError


class TestGitAdapterCheckout:
    """Tests for checkout functionality."""

    def test_checkout_existing_branch(self) -> None:
        """Test checkout to existing branch."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_branch = MagicMock()
            mock_branch.name = "feature/test"
            mock_repo.heads.__iter__ = lambda self: iter([mock_branch])
            mock_repo.heads.__contains__ = lambda self, x: x == "feature/test"
            mock_repo.heads.__getitem__ = lambda self, x: mock_branch
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.checkout("feature/test")

            mock_branch.checkout.assert_called_once()

    def test_checkout_nonexistent_branch_raises_error(self) -> None:
        """Test checkout to non-existent branch raises ExecutionError."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.heads.__contains__ = lambda self, x: False
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            with pytest.raises(ExecutionError, match="does not exist"):
                adapter.checkout("nonexistent")


class TestGitAdapterPush:
    """Tests for push functionality."""

    def test_push_to_origin(self) -> None:
        """Test push to origin remote."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_origin = MagicMock()
            mock_repo.remotes.__iter__ = lambda self: iter([mock_origin])
            mock_repo.remotes.__contains__ = lambda self, x: x == "origin"
            mock_repo.remote.return_value = mock_origin
            mock_repo.active_branch.name = "feature/test"
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.push()

            mock_origin.push.assert_called_once()

    def test_push_with_set_upstream(self) -> None:
        """Test push with --set-upstream flag."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_origin = MagicMock()
            mock_repo.remotes.__contains__ = lambda self, x: x == "origin"
            mock_repo.remote.return_value = mock_origin
            mock_repo.active_branch.name = "feature/new"
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.push(set_upstream=True)

            mock_origin.push.assert_called_once()

    def test_push_no_remote_raises_error(self) -> None:
        """Test push without origin remote raises ExecutionError."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.remotes.__iter__ = lambda self: iter([])
            mock_repo.remote.side_effect = ValueError("Remote origin not found")
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            with pytest.raises(ExecutionError, match="origin"):
                adapter.push()


class TestGitAdapterMerge:
    """Tests for merge functionality."""

    def test_merge_branch(self) -> None:
        """Test merge branch into current."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.heads.__contains__ = lambda self, x: x == "feature/test"
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.merge("feature/test")

            mock_repo.git.merge.assert_called_once_with("feature/test")

    def test_merge_nonexistent_branch_raises_error(self) -> None:
        """Test merge non-existent branch raises ExecutionError."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.heads.__contains__ = lambda self, x: False
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            with pytest.raises(ExecutionError, match="does not exist"):
                adapter.merge("nonexistent")


class TestGitAdapterDeleteBranch:
    """Tests for branch deletion."""

    def test_delete_branch(self) -> None:
        """Test delete a branch."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.heads.__contains__ = lambda self, x: x == "feature/test"
            mock_repo.active_branch.name = "main"
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.delete_branch("feature/test")

            mock_repo.delete_head.assert_called_once_with("feature/test", force=False)

    def test_delete_current_branch_raises_error(self) -> None:
        """Test cannot delete current branch."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.active_branch.name = "feature/test"
            mock_repo.heads.__contains__ = lambda self, x: x == "feature/test"
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            with pytest.raises(ExecutionError, match="current branch"):
                adapter.delete_branch("feature/test")

    def test_delete_nonexistent_branch_raises_error(self) -> None:
        """Test delete non-existent branch raises ExecutionError."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.heads.__contains__ = lambda self, x: False
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            with pytest.raises(ExecutionError, match="does not exist"):
                adapter.delete_branch("nonexistent")

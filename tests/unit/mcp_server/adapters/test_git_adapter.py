"""Tests for GitAdapter - extended git operations."""

from unittest.mock import MagicMock, patch

import pytest

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
            mock_repo.heads.__iter__ = lambda _self: iter([mock_branch])
            mock_repo.heads.__contains__ = lambda _self, x: x == "feature/test"
            mock_repo.heads.__getitem__ = lambda _self, _x: mock_branch
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.checkout("feature/test")

            mock_branch.checkout.assert_called_once()

    def test_checkout_nonexistent_branch_raises_error(self) -> None:
        """Test checkout to non-existent branch raises ExecutionError."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.heads.__contains__ = lambda _self, _x: False
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            with pytest.raises(ExecutionError, match="does not exist"):
                adapter.checkout("nonexistent")

    def test_checkout_remote_only_branch(self) -> None:
        """Test checkout creates local tracking branch from remote-only ref.

        Scenario S2: Remote-tracking ref exists, no local branch.
        Expected: Create local tracking branch and checkout.

        TDD Cycle 1 - RED: This test WILL FAIL until remote fallback implemented.
        """
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()

            # Setup: No local branch exists
            mock_repo.heads.__contains__ = lambda _self, _x: False

            # Setup: Origin remote with remote-tracking ref
            mock_origin = MagicMock()
            mock_remote_ref = MagicMock()
            mock_remote_ref.name = "origin/feature/test"
            mock_origin.refs = [mock_remote_ref]
            mock_repo.remote.return_value = mock_origin

            # Setup: create_head returns mock branch with tracking methods
            mock_local_branch = MagicMock()
            mock_repo.create_head.return_value = mock_local_branch

            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            # WHEN: Checkout remote-only branch
            adapter.checkout("feature/test")

            # THEN: Local tracking branch created from remote ref
            mock_repo.create_head.assert_called_once_with("feature/test", mock_remote_ref)
            mock_local_branch.set_tracking_branch.assert_called_once_with(mock_remote_ref)
            mock_local_branch.checkout.assert_called_once()

    def test_checkout_strips_origin_prefix(self) -> None:
        """Test checkout normalizes origin/ prefix in input.

        Scenario S5: User provides 'origin/feature/test' as input.
        Expected: Prefix stripped, local branch created as 'feature/test'.

        TDD Cycle 2 - RED: This test WILL FAIL until prefix normalization added.
        """
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()

            # Setup: No local branch exists
            mock_repo.heads.__contains__ = lambda _self, _x: False

            # Setup: Origin remote with remote-tracking ref
            mock_origin = MagicMock()
            mock_remote_ref = MagicMock()
            mock_remote_ref.name = "origin/feature/test"
            mock_origin.refs = [mock_remote_ref]
            mock_repo.remote.return_value = mock_origin

            # Setup: create_head returns mock branch
            mock_local_branch = MagicMock()
            mock_repo.create_head.return_value = mock_local_branch

            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            # WHEN: Checkout WITH origin/ prefix
            adapter.checkout("origin/feature/test")

            # THEN: Prefix stripped, local branch "feature/test" created
            # NOT: create_head("origin/feature/test", ...)
            mock_repo.create_head.assert_called_once_with("feature/test", mock_remote_ref)
            mock_local_branch.set_tracking_branch.assert_called_once_with(mock_remote_ref)
            mock_local_branch.checkout.assert_called_once()


class TestGitAdapterPush:
    """Tests for push functionality."""

    def test_push_to_origin(self) -> None:
        """Test push to origin remote."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_origin = MagicMock()
            mock_repo.remotes.__iter__ = lambda _self: iter([mock_origin])
            mock_repo.remotes.__contains__ = lambda _self, _x: _x == "origin"
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
            mock_repo.remotes.__contains__ = lambda _self, _x: _x == "origin"
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
            mock_repo.remotes.__iter__ = lambda _self: iter([])
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
            mock_repo.heads.__contains__ = lambda _self, _x: _x == "feature/test"
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.merge("feature/test")

            mock_repo.git.merge.assert_called_once_with("feature/test")

    def test_merge_nonexistent_branch_raises_error(self) -> None:
        """Test merge non-existent branch raises ExecutionError."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.heads.__contains__ = lambda _self, _x: False
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
            mock_repo.heads.__contains__ = lambda _self, _x: _x == "feature/test"
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
            mock_repo.heads.__contains__ = lambda _self, _x: _x == "feature/test"
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            with pytest.raises(ExecutionError, match="current branch"):
                adapter.delete_branch("feature/test")

    def test_delete_nonexistent_branch_raises_error(self) -> None:
        """Test delete non-existent branch raises ExecutionError."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.heads.__contains__ = lambda _self, _x: False
            mock_repo_class.return_value = mock_repo


class TestGitAdapterStash:
    """Tests for git stash functionality."""

    def test_stash_changes(self) -> None:
        """Test stash current changes."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.stash()

            mock_repo.git.stash.assert_called_once_with("push")

    def test_stash_changes_include_untracked(self) -> None:
        """Test stash current changes including untracked files (-u)."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.stash(include_untracked=True)

            mock_repo.git.stash.assert_called_once_with("push", "-u")

    def test_stash_with_message(self) -> None:
        """Test stash with custom message."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.stash(message="WIP: feature work")

            mock_repo.git.stash.assert_called_once_with("push", "-m", "WIP: feature work")

    def test_stash_with_message_include_untracked(self) -> None:
        """Test stash with message including untracked files (-u)."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.stash(message="WIP: feature work", include_untracked=True)

            mock_repo.git.stash.assert_called_once_with("push", "-u", "-m", "WIP: feature work")

    def test_stash_pop(self) -> None:
        """Test pop the latest stash."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.stash_pop()

            mock_repo.git.stash.assert_called_once_with("pop")

    def test_stash_list(self) -> None:
        """Test list all stashes."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.git.stash.return_value = (
                "stash@{0}: WIP on main: abc1234 commit msg\n"
                "stash@{1}: On feature: def5678 another msg"
            )
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            result = adapter.stash_list()

            mock_repo.git.stash.assert_called_once_with("list")
            assert len(result) == 2
            assert "stash@{0}" in result[0]

    def test_stash_list_empty(self) -> None:
        """Test list stashes when none exist."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.git.stash.return_value = ""
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            result = adapter.stash_list()

            assert result == []

    def test_stash_error_handling(self) -> None:
        """Test stash error is wrapped in ExecutionError."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.git.stash.side_effect = Exception("Git error")
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            with pytest.raises(ExecutionError, match="stash"):
                adapter.stash()

            adapter = GitAdapter("/fake/path")

            with pytest.raises(ExecutionError, match="does not exist"):
                adapter.delete_branch("nonexistent")


class TestGitAdapterCommit:
    """Tests for git commit functionality."""

    def test_commit_stages_all_when_files_none(self) -> None:
        """Test commit stages all changes when files is omitted."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_commit = MagicMock()
            mock_commit.hexsha = "abc1234"
            mock_repo.index.commit.return_value = mock_commit
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            result = adapter.commit("msg")

            assert result == "abc1234"
            mock_repo.git.add.assert_called_once_with(".")
            mock_repo.index.commit.assert_called_once_with("msg")

    def test_commit_stages_only_given_files(self) -> None:
        """Test commit stages only provided files."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_commit = MagicMock()
            mock_commit.hexsha = "abc1234"
            mock_repo.index.commit.return_value = mock_commit
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            result = adapter.commit("msg", files=["a.py", "docs/readme.md"])

            assert result == "abc1234"
            mock_repo.git.add.assert_called_once_with("a.py", "docs/readme.md")
            mock_repo.index.commit.assert_called_once_with("msg")


class TestGitAdapterRestore:
    """Tests for git restore functionality."""

    def test_restore_calls_git_restore_for_files(self) -> None:
        """Test restore delegates to `git restore` with correct args."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.restore(files=["a.py", "b.py"], source="HEAD")

            mock_repo.git.restore.assert_called_once_with(
                "--source=HEAD",
                "--staged",
                "--worktree",
                "--",
                "a.py",
                "b.py",
            )

    def test_restore_wraps_errors_in_execution_error(self) -> None:
        """Test restore errors are wrapped in ExecutionError."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.git.restore.side_effect = Exception("Git error")
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            with pytest.raises(ExecutionError, match="restore"):
                adapter.restore(files=["a.py"], source="HEAD")


class TestGitAdapterCreateBranch:
    """Tests for create_branch functionality (Issue #64 - TDD RED phase)."""

    def test_create_branch_requires_explicit_base(self) -> None:
        """RED: Should fail when base parameter missing (no default allowed)."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            # Should require base parameter (no default)
            with pytest.raises(TypeError, match="base"):
                adapter.create_branch("test-branch")  # Missing base parameter

    def test_create_branch_with_head(self) -> None:
        """RED: Should create from current HEAD when base='HEAD'."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_head = MagicMock()
            mock_commit = MagicMock()
            mock_commit.hexsha = "abc123f"
            mock_head.commit = mock_commit
            mock_repo.head = mock_head
            mock_repo.heads = []
            mock_new_branch = MagicMock()
            mock_repo.create_head.return_value = mock_new_branch
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.create_branch("test-branch", base="HEAD")

            # Should resolve HEAD to commit and create from it
            mock_repo.create_head.assert_called_once_with("test-branch", mock_commit)
            mock_new_branch.checkout.assert_called_once()

    def test_create_branch_with_branch_name(self) -> None:
        """RED: Should create from specified branch name."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.heads = []
            mock_new_branch = MagicMock()
            mock_repo.create_head.return_value = mock_new_branch
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.create_branch("test-branch", base="main")

            # Should pass branch name directly to create_head
            mock_repo.create_head.assert_called_once_with("test-branch", "main")
            mock_new_branch.checkout.assert_called_once()

    def test_create_branch_with_commit_hash(self) -> None:
        """RED: Should create from specific commit hash."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo.heads = []
            mock_new_branch = MagicMock()
            mock_repo.create_head.return_value = mock_new_branch
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")
            adapter.create_branch("test-branch", base="abc123f")

            # Should pass commit hash directly
            mock_repo.create_head.assert_called_once_with("test-branch", "abc123f")
            mock_new_branch.checkout.assert_called_once()

    def test_create_branch_already_exists_raises_error(self) -> None:
        """RED: Should fail when branch already exists."""
        with patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class:
            mock_repo = MagicMock()
            mock_branch = MagicMock()
            mock_branch.name = "existing-branch"
            # Use MagicMock list-like behavior instead of setting __contains__
            mock_repo.heads = MagicMock()
            mock_repo.heads.__iter__ = lambda _self: iter([mock_branch])
            mock_repo.heads.__contains__ = lambda _self, _x: _x == "existing-branch"
            mock_repo_class.return_value = mock_repo

            adapter = GitAdapter("/fake/path")

            with pytest.raises(ExecutionError, match="already exists"):
                adapter.create_branch("existing-branch", base="main")

    def test_create_branch_logs_operation(self) -> None:
        """GREEN: Should log branch creation with all relevant details."""
        with (
            patch("mcp_server.adapters.git_adapter.Repo") as mock_repo_class,
            patch("mcp_server.core.logging.get_logger") as mock_logger,
        ):
            mock_repo = MagicMock()
            mock_repo.heads = []
            mock_new_branch = MagicMock()
            mock_repo.create_head.return_value = mock_new_branch
            mock_repo_class.return_value = mock_repo

            mock_log = MagicMock()
            mock_logger.return_value = mock_log

            adapter = GitAdapter("/fake/path")
            adapter.create_branch("test-branch", base="main")

            # Should log the operation
            assert mock_log.debug.called or mock_log.info.called

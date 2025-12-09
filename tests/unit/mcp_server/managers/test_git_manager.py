"""Tests for GitManager - extended git operations."""
import pytest
from unittest.mock import MagicMock
from mcp_server.managers.git_manager import GitManager
from mcp_server.core.exceptions import ValidationError, PreflightError


class TestGitManagerCommitTddPhase:
    """Tests for TDD phase commit functionality."""

    def test_commit_tdd_red_phase(self) -> None:
        """Test commit with TDD red phase prefix."""
        mock_adapter = MagicMock()
        mock_adapter.commit.return_value = "abc123"

        manager = GitManager(adapter=mock_adapter)
        result = manager.commit_tdd_phase("red", "add failing tests for Feature")

        mock_adapter.commit.assert_called_once_with(
            "test: add failing tests for Feature"
        )
        assert result == "abc123"

    def test_commit_tdd_green_phase(self) -> None:
        """Test commit with TDD green phase prefix."""
        mock_adapter = MagicMock()
        mock_adapter.commit.return_value = "def456"

        manager = GitManager(adapter=mock_adapter)
        result = manager.commit_tdd_phase("green", "implement Feature")

        mock_adapter.commit.assert_called_once_with("feat: implement Feature")
        assert result == "def456"

    def test_commit_tdd_refactor_phase(self) -> None:
        """Test commit with TDD refactor phase prefix."""
        mock_adapter = MagicMock()
        mock_adapter.commit.return_value = "ghi789"

        manager = GitManager(adapter=mock_adapter)
        result = manager.commit_tdd_phase("refactor", "improve code quality")

        mock_adapter.commit.assert_called_once_with("refactor: improve code quality")
        assert result == "ghi789"

    def test_commit_invalid_phase_raises_error(self) -> None:
        """Test commit with invalid phase raises ValidationError."""
        manager = GitManager(adapter=MagicMock())

        with pytest.raises(ValidationError, match="Invalid TDD phase"):
            manager.commit_tdd_phase("invalid", "some message")


class TestGitManagerCommitDocs:
    """Tests for docs commit functionality."""

    def test_commit_docs(self) -> None:
        """Test commit with docs phase prefix."""
        mock_adapter = MagicMock()
        mock_adapter.commit.return_value = "jkl012"

        manager = GitManager(adapter=mock_adapter)
        result = manager.commit_docs("update README")

        mock_adapter.commit.assert_called_once_with("docs: update README")
        assert result == "jkl012"


class TestGitManagerCheckout:
    """Tests for checkout functionality."""

    def test_checkout_branch(self) -> None:
        """Test checkout to existing branch."""
        mock_adapter = MagicMock()

        manager = GitManager(adapter=mock_adapter)
        manager.checkout("feature/test")

        mock_adapter.checkout.assert_called_once_with("feature/test")

    def test_checkout_to_main(self) -> None:
        """Test checkout to main branch."""
        mock_adapter = MagicMock()

        manager = GitManager(adapter=mock_adapter)
        manager.checkout("main")

        mock_adapter.checkout.assert_called_once_with("main")


class TestGitManagerPush:
    """Tests for push functionality."""

    def test_push_current_branch(self) -> None:
        """Test push current branch to origin."""
        mock_adapter = MagicMock()
        mock_adapter.get_current_branch.return_value = "feature/test"

        manager = GitManager(adapter=mock_adapter)
        manager.push()

        mock_adapter.push.assert_called_once_with(set_upstream=False)

    def test_push_with_upstream(self) -> None:
        """Test push with --set-upstream flag."""
        mock_adapter = MagicMock()

        manager = GitManager(adapter=mock_adapter)
        manager.push(set_upstream=True)

        mock_adapter.push.assert_called_once_with(set_upstream=True)


class TestGitManagerMerge:
    """Tests for merge functionality."""

    def test_merge_feature_to_main(self) -> None:
        """Test merge feature branch to main."""
        mock_adapter = MagicMock()
        mock_adapter.is_clean.return_value = True
        mock_adapter.get_current_branch.return_value = "main"

        manager = GitManager(adapter=mock_adapter)
        manager.merge("feature/test")

        mock_adapter.merge.assert_called_once_with("feature/test")

    def test_merge_requires_clean_workdir(self) -> None:
        """Test merge requires clean working directory."""
        mock_adapter = MagicMock()
        mock_adapter.is_clean.return_value = False

        manager = GitManager(adapter=mock_adapter)

        with pytest.raises(PreflightError, match="not clean"):
            manager.merge("feature/test")


class TestGitManagerDeleteBranch:
    """Tests for branch deletion."""

    def test_delete_merged_branch(self) -> None:
        """Test delete a merged branch."""
        mock_adapter = MagicMock()

        manager = GitManager(adapter=mock_adapter)
        manager.delete_branch("feature/test")

        mock_adapter.delete_branch.assert_called_once_with("feature/test", force=False)

    def test_delete_branch_force(self) -> None:
        """Test force delete a branch."""
        mock_adapter = MagicMock()

        manager = GitManager(adapter=mock_adapter)
        manager.delete_branch("feature/test", force=True)

        mock_adapter.delete_branch.assert_called_once_with("feature/test", force=True)

    def test_cannot_delete_main_branch(self) -> None:
        """Test cannot delete main branch."""
        manager = GitManager(adapter=MagicMock())

        with pytest.raises(ValidationError, match="Cannot delete.*main"):
            manager.delete_branch("main")

    def test_cannot_delete_protected_branches(self) -> None:
        """Test cannot delete protected branches."""
        manager = GitManager(adapter=MagicMock())

        for branch in ["main", "master", "develop"]:
            with pytest.raises(ValidationError, match="Cannot delete"):
                manager.delete_branch(branch)

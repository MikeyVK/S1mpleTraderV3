"""Tests for GitManager (Issue #55 integration)."""
from unittest.mock import MagicMock

import pytest

from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.config.git_config import GitConfig
from mcp_server.core.exceptions import ValidationError
from mcp_server.managers.git_manager import GitManager


class TestGitManagerConfigIntegration:
    """Test GitManager uses GitConfig instead of hardcoded values."""

    def setup_method(self):
        """Setup test fixtures."""
        GitConfig.reset_instance()
        self.mock_adapter = MagicMock(spec=GitAdapter)
        self.mock_adapter.is_clean.return_value = True
        self.mock_adapter.get_current_branch.return_value = "main"
        self.manager = GitManager(adapter=self.mock_adapter)

    def teardown_method(self):
        """Cleanup after tests."""
        GitConfig.reset_instance()

    # Cycle 2: Convention #1 - Branch type validation
    def test_create_branch_uses_git_config_branch_types(self):
        """Test create_branch() validates branch_type via GitConfig."""
        # Valid type from git.yaml
        self.manager.create_branch("123-test", "feature", "main")
        self.mock_adapter.create_branch.assert_called_once_with("feature/123-test", base="main")

        # Invalid type not in git.yaml
        with pytest.raises(ValidationError, match="Invalid branch type: hotfix"):
            self.manager.create_branch("123-test", "hotfix", "main")

    # Cycle 3: Convention #5 - Branch name pattern
    def test_create_branch_uses_git_config_name_pattern(self):
        """Test create_branch() validates name via GitConfig pattern."""
        # Valid kebab-case
        self.manager.create_branch("valid-name-123", "feature", "main")

        # Invalid: uppercase
        with pytest.raises(ValidationError, match="Invalid branch name: Invalid-Name"):
            self.manager.create_branch("Invalid-Name", "feature", "main")

        # Invalid: underscore
        with pytest.raises(ValidationError, match="Invalid branch name: invalid_name"):
            self.manager.create_branch("invalid_name", "feature", "main")

    # Cycle 4/5: Workflow commit mapping + validation
    def test_commit_with_scope_uses_workflow_and_subphase_validation(self):
        """Test commit_with_scope validates workflow/subphase and maps types."""
        self.mock_adapter.commit.return_value = "abc123"

        self.manager.commit_with_scope("tdd", "failing test", sub_phase="red")
        self.mock_adapter.commit.assert_called_with(
            "test(P_TDD_SP_RED): failing test", files=None
        )

        self.manager.commit_with_scope("tdd", "make it pass", sub_phase="green")
        self.mock_adapter.commit.assert_called_with(
            "feat(P_TDD_SP_GREEN): make it pass", files=None
        )

        self.manager.commit_with_scope("documentation", "update README")
        self.mock_adapter.commit.assert_called_with(
            "docs(P_DOCUMENTATION): update README", files=None
        )

        with pytest.raises(ValueError):
            self.manager.commit_with_scope("invalid", "message")

    # Cycle 6: Convention #4 - Protected branches
    def test_delete_branch_uses_git_config_protected(self):
        """Test delete_branch() checks GitConfig protected branches."""
        # Protected branches from git.yaml
        with pytest.raises(ValidationError, match="Cannot delete protected branch: main"):
            self.manager.delete_branch("main")

        with pytest.raises(ValidationError, match="Cannot delete protected branch: master"):
            self.manager.delete_branch("master")

        with pytest.raises(ValidationError, match="Cannot delete protected branch: develop"):
            self.manager.delete_branch("develop")

        # Unprotected branch should work
        self.manager.delete_branch("feature/123-test")
        self.mock_adapter.delete_branch.assert_called_once_with("feature/123-test", force=False)

"""Tests for GitManager (Issue #55 integration).

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.adapters.git_adapter, mcp_server.managers.git_manager
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.adapters.git_adapter import GitAdapter
from mcp_server.config.loader import ConfigLoader
from mcp_server.core.exceptions import ValidationError
from mcp_server.core.operation_notes import NoteContext
from mcp_server.managers.git_manager import GitManager


class TestGitManagerConfigIntegration:
    """Test GitManager uses GitConfig instead of hardcoded values."""

    def setup_method(self) -> None:
        """Setup test fixtures."""
        self.mock_adapter = MagicMock(spec=GitAdapter)
        self.mock_adapter.is_clean.return_value = True
        self.mock_adapter.get_current_branch.return_value = "main"
        self.git_config = ConfigLoader(Path(".st3/config")).load_git_config()
        workphases_config = ConfigLoader(Path(".st3/config")).load_workphases_config()
        self.manager = GitManager(git_config=self.git_config, adapter=self.mock_adapter, workphases_config=workphases_config)

    def test_create_branch_uses_git_config_branch_types(self) -> None:
        """Test create_branch() validates branch_type via GitConfig."""
        ctx = NoteContext()
        self.manager.create_branch("123-test", "feature", "main", ctx)
        self.mock_adapter.create_branch.assert_called_once_with("feature/123-test", base="main")

        with pytest.raises(ValidationError, match="Invalid branch type: invalid-type"):
            self.manager.create_branch("123-test", "invalid-type", "main", NoteContext())

    def test_create_branch_uses_git_config_name_pattern(self) -> None:
        """Test create_branch() validates name via GitConfig pattern."""
        self.manager.create_branch("valid-name-123", "feature", "main", NoteContext())

        with pytest.raises(ValidationError, match="Invalid branch name: Invalid-Name"):
            self.manager.create_branch("Invalid-Name", "feature", "main", NoteContext())

        with pytest.raises(ValidationError, match="Invalid branch name: invalid_name"):
            self.manager.create_branch("invalid_name", "feature", "main", NoteContext())

    def test_commit_with_scope_uses_workflow_and_subphase_validation(self) -> None:
        """Test commit_with_scope validates workflow/subphase and uses explicit types."""
        self.mock_adapter.commit.return_value = "abc123"
        ctx = NoteContext()

        self.manager.commit_with_scope(
            "implementation",
            "failing test",
            note_context=ctx,
            sub_phase="red",
            commit_type="test",
        )
        call_args = self.mock_adapter.commit.call_args
        assert call_args[0][0] == "test(P_IMPLEMENTATION_SP_RED): failing test"
        assert call_args[1]["files"] is None

        self.manager.commit_with_scope(
            "implementation",
            "make it pass",
            note_context=NoteContext(),
            sub_phase="green",
            commit_type="feat",
        )
        call_args = self.mock_adapter.commit.call_args
        assert call_args[0][0] == "feat(P_IMPLEMENTATION_SP_GREEN): make it pass"
        assert call_args[1]["files"] is None

        self.manager.commit_with_scope("documentation", "update README", note_context=NoteContext())
        call_args = self.mock_adapter.commit.call_args
        assert call_args[0][0] == "docs(P_DOCUMENTATION): update README"
        assert call_args[1]["files"] is None

        with pytest.raises(ValueError):
            self.manager.commit_with_scope("invalid", "message", note_context=NoteContext())

    def test_delete_branch_uses_git_config_protected(self) -> None:
        """Test delete_branch() checks GitConfig protected branches."""
        with pytest.raises(ValidationError, match="Cannot delete protected branch: main"):
            self.manager.delete_branch("main", NoteContext())

        with pytest.raises(ValidationError, match="Cannot delete protected branch: master"):
            self.manager.delete_branch("master", NoteContext())

        with pytest.raises(ValidationError, match="Cannot delete protected branch: develop"):
            self.manager.delete_branch("develop", NoteContext())

        self.manager.delete_branch("feature/123-test", NoteContext())
        self.mock_adapter.delete_branch.assert_called_once_with("feature/123-test", force=False)

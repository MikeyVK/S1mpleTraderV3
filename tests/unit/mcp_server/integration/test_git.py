"""Tests for Git integration."""
from unittest.mock import Mock

import pytest

from mcp_server.core.exceptions import PreflightError, ValidationError
from mcp_server.managers.git_manager import GitManager


@pytest.fixture(name="mock_git_adapter")
def _mock_git_adapter_fixture() -> Mock:
    """Create a mock GitAdapter for testing."""
    return Mock()

def test_git_manager_create_branch_valid(mock_git_adapter: Mock) -> None:
    """Test creating a branch with explicit base on clean working directory."""
    mock_git_adapter.is_clean.return_value = True
    manager = GitManager(adapter=mock_git_adapter)

    branch = manager.create_branch("my-feature", "feature", "HEAD")

    assert branch == "feature/my-feature"
    mock_git_adapter.create_branch.assert_called_with("feature/my-feature", base="HEAD")

def test_git_manager_create_branch_dirty(mock_git_adapter: Mock) -> None:
    """Test that creating branch fails on dirty working directory."""
    mock_git_adapter.is_clean.return_value = False
    manager = GitManager(adapter=mock_git_adapter)

    with pytest.raises(PreflightError):
        manager.create_branch("my-feature", "feature", "HEAD")

def test_git_manager_invalid_name(mock_git_adapter: Mock) -> None:
    """Test that invalid branch names are rejected."""
    manager = GitManager(adapter=mock_git_adapter)
    with pytest.raises(ValidationError):
        manager.create_branch("Invalid Name", "feature", "HEAD")

def test_git_manager_commit_tdd(mock_git_adapter: Mock) -> None:
    """Test TDD commit prefixes message correctly with 'test:' prefix."""
    manager = GitManager(adapter=mock_git_adapter)
    manager.commit_tdd_phase("red", "Added test")

    mock_git_adapter.commit.assert_called_with("test: Added test", files=None)

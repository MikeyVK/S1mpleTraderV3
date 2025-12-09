"""Tests for Git integration."""
from unittest.mock import Mock

import pytest

from mcp_server.core.exceptions import PreflightError, ValidationError
from mcp_server.managers.git_manager import GitManager


@pytest.fixture
def mock_git_adapter():
    return Mock()

def test_git_manager_create_branch_valid(mock_git_adapter):
    mock_git_adapter.is_clean.return_value = True
    manager = GitManager(adapter=mock_git_adapter)

    branch = manager.create_feature_branch("my-feature", "feature")

    assert branch == "feature/my-feature"
    mock_git_adapter.create_branch.assert_called_with("feature/my-feature")

def test_git_manager_create_branch_dirty(mock_git_adapter):
    mock_git_adapter.is_clean.return_value = False
    manager = GitManager(adapter=mock_git_adapter)

    with pytest.raises(PreflightError):
        manager.create_feature_branch("my-feature")

def test_git_manager_invalid_name(mock_git_adapter):
    manager = GitManager(adapter=mock_git_adapter)
    with pytest.raises(ValidationError):
        manager.create_feature_branch("Invalid Name")

def test_git_manager_commit_tdd(mock_git_adapter):
    manager = GitManager(adapter=mock_git_adapter)
    manager.commit_tdd_phase("red", "Added test")

    mock_git_adapter.commit.assert_called_with("test: Added test")

"""Tests for Git integration.

@layer: Tests (Integration)
@dependencies: pytest, pathlib, unittest.mock, mcp_server.config.loader, mcp_server.config.schemas, mcp_server.managers.git_manager
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import GitConfig
from mcp_server.core.exceptions import PreflightError, ValidationError
from mcp_server.managers.git_manager import GitManager


@pytest.fixture(name="mock_git_adapter")
def _mock_git_adapter_fixture() -> Mock:
    """Create a mock GitAdapter for testing."""
    return Mock()


@pytest.fixture(name="git_config")
def _git_config_fixture() -> GitConfig:
    return ConfigLoader(Path(".st3/config")).load_git_config()


def test_git_manager_create_branch_valid(mock_git_adapter: Mock, git_config: GitConfig) -> None:
    """Test creating a branch with explicit base on clean working directory."""
    mock_git_adapter.is_clean.return_value = True
    manager = GitManager(git_config=git_config, adapter=mock_git_adapter)

    branch = manager.create_branch("my-feature", "feature", "HEAD")

    assert branch == "feature/my-feature"
    mock_git_adapter.create_branch.assert_called_with("feature/my-feature", base="HEAD")


def test_git_manager_create_branch_epic_valid(
    mock_git_adapter: Mock, git_config: GitConfig
) -> None:
    """Test creating an epic branch with explicit base on clean working directory."""
    mock_git_adapter.is_clean.return_value = True
    manager = GitManager(git_config=git_config, adapter=mock_git_adapter)

    branch = manager.create_branch("91-test-suite-cleanup", "epic", "HEAD")

    assert branch == "epic/91-test-suite-cleanup"
    mock_git_adapter.create_branch.assert_called_with("epic/91-test-suite-cleanup", base="HEAD")


def test_git_manager_create_branch_dirty(mock_git_adapter: Mock, git_config: GitConfig) -> None:
    """Test that creating branch fails on dirty working directory."""
    mock_git_adapter.is_clean.return_value = False
    manager = GitManager(git_config=git_config, adapter=mock_git_adapter)

    with pytest.raises(PreflightError):
        manager.create_branch("my-feature", "feature", "HEAD")


def test_git_manager_invalid_name(mock_git_adapter: Mock, git_config: GitConfig) -> None:
    """Test that invalid branch names are rejected."""
    manager = GitManager(git_config=git_config, adapter=mock_git_adapter)
    with pytest.raises(ValidationError):
        manager.create_branch("Invalid Name", "feature", "HEAD")


def test_git_manager_commit_tdd(mock_git_adapter: Mock, git_config: GitConfig) -> None:
    """Test implementation-phase commit through workflow scope."""
    manager = GitManager(git_config=git_config, adapter=mock_git_adapter)
    manager.commit_with_scope(
        "implementation",
        "Added test",
        sub_phase="red",
        cycle_number=1,
        commit_type="test",
    )

    mock_git_adapter.commit.assert_called_with(
        "test(P_IMPLEMENTATION_SP_C1_RED): Added test",
        files=None,
    )

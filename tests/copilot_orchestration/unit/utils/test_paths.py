# tests\copilot_orchestration\unit\utils\test_paths.py
# template=unit_test version=3d15d309 created=2026-03-21T12:02Z updated=
"""
Unit tests for copilot_orchestration.utils._paths.

Tests find_workspace_root sentinel-based upward traversal and STATE_RELPATH constant value.

@layer: Tests (Unit)
@dependencies: [pytest, copilot_orchestration.utils._paths]
@responsibilities:
    - Test TestFindWorkspaceRoot functionality
    - Verify upward directory traversal and sentinel detection
    - Verify no magic depth limit exists
"""

# Standard library
from typing import Any

# Third-party
import pytest
from pathlib import Path

# Project modules
from copilot_orchestration.utils._paths import find_workspace_root, STATE_RELPATH


class TestStateRelpath:
    """Test suite for the STATE_RELPATH constant."""

    def test_state_relpath_value(self) -> None:
        """STATE_RELPATH equals Path('.copilot/session-sub-role.json')."""
        # Arrange - expected value from design §9.8
        expected = Path(".copilot/session-sub-role.json")

        # Act - constant is module-level; no call needed

        # Assert - verify exact value matches design contract
        assert STATE_RELPATH == expected

    def test_state_relpath_is_path(self) -> None:
        """STATE_RELPATH is a pathlib.Path instance, not a plain string."""
        # Arrange / Act - no setup needed

        # Assert
        assert isinstance(STATE_RELPATH, Path)


class TestFindWorkspaceRoot:
    """Test suite for _paths."""

    def test_resolves_from_workspace_root_itself(
        self,
        tmp_path: Path    ):
        """Resolves when anchor is the workspace root (contains pyproject.toml)."""
        # Arrange - Setup test data and preconditions
        (tmp_path / "pyproject.toml").touch()

        # Act - Execute the functionality being tested
        result = find_workspace_root(tmp_path)

        # Assert - Verify the expected outcome
        assert result == tmp_path
    def test_resolves_from_nested_file(
        self,
        tmp_path: Path    ):
        """Resolves correctly when anchor is a file several levels below root."""
        # Arrange - Setup test data and preconditions
        (tmp_path / "pyproject.toml").touch()
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        anchor = nested / "file.py"
        anchor.touch()

        # Act - Execute the functionality being tested
        result = find_workspace_root(anchor)

        # Assert - Verify the expected outcome
        assert result == tmp_path
    def test_resolves_via_git_sentinel(
        self,
        tmp_path: Path    ):
        """Resolves root when only .git is present (no pyproject.toml)."""
        # Arrange - Setup test data and preconditions
        (tmp_path / ".git").mkdir()
        src = tmp_path / "src"
        src.mkdir()
        anchor = src / "module.py"
        anchor.touch()

        # Act - Execute the functionality being tested
        result = find_workspace_root(anchor)

        # Assert - Verify the expected outcome
        assert result == tmp_path
    def test_raises_when_no_sentinel_found(
        self,
        tmp_path: Path    ):
        """Raises RuntimeError with 'workspace root' in message when no sentinel exists."""
        # Arrange - Setup test data and preconditions
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        anchor = nested / "file.py"
        anchor.touch()

        # Act - Execute the functionality being tested
        # pytest.raises handles both Act and Assert here

        # Assert - Verify the expected outcome
        with pytest.raises(RuntimeError, match="workspace root"):
            find_workspace_root(anchor)
    def test_prefers_pyproject_toml_over_git(
        self,
        tmp_path: Path    ):
        """Stops at inner pyproject.toml before reaching the outer .git sentinel."""
        # Arrange - Setup test data and preconditions
        (tmp_path / ".git").mkdir()
        middle = tmp_path / "sub"
        middle.mkdir()
        (middle / "pyproject.toml").touch()
        deep = middle / "deep"
        deep.mkdir()
        anchor = deep / "file.py"
        anchor.touch()

        # Act - Execute the functionality being tested
        result = find_workspace_root(anchor)

        # Assert - Verify the expected outcome
        assert result == middle
    def test_anchor_is_directory(
        self,
        tmp_path: Path    ):
        """Handles a directory anchor (not a file path) correctly."""
        # Arrange - Setup test data and preconditions
        (tmp_path / "pyproject.toml").touch()
        subdir = tmp_path / "mydir"
        subdir.mkdir()

        # Act - Execute the functionality being tested
        result = find_workspace_root(subdir)

        # Assert - Verify the expected outcome
        assert result == tmp_path
    def test_does_not_use_magic_depth(
        self,
        tmp_path: Path    ):
        """Resolves correctly from more than 5 levels deep (no depth cap)."""
        # Arrange - Setup test data and preconditions
        (tmp_path / "pyproject.toml").touch()
        deep = tmp_path / "a" / "b" / "c" / "d" / "e" / "f"
        deep.mkdir(parents=True)
        anchor = deep / "file.py"
        anchor.touch()

        # Act - Execute the functionality being tested
        result = find_workspace_root(anchor)

        # Assert - Verify the expected outcome
        assert result == tmp_path

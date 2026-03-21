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
from pathlib import Path

# Third-party
import pytest

# Project modules
from copilot_orchestration.utils._paths import find_workspace_root, state_path_for_role


class TestStatePathForRole:
    """Test suite for the state_path_for_role function."""

    def test_imp_role_returns_imp_scoped_path(self) -> None:
        """state_path_for_role('imp') returns '.copilot/session-sub-role-imp.json'."""
        assert state_path_for_role("imp") == Path(".copilot/session-sub-role-imp.json")

    def test_qa_role_returns_qa_scoped_path(self) -> None:
        """state_path_for_role('qa') returns '.copilot/session-sub-role-qa.json'."""
        assert state_path_for_role("qa") == Path(".copilot/session-sub-role-qa.json")

    def test_returns_path_instance(self) -> None:
        """Return type is pathlib.Path, not plain string."""
        assert isinstance(state_path_for_role("imp"), Path)

    def test_roles_produce_distinct_paths(self) -> None:
        """Different roles produce different file paths (no shared file)."""
        assert state_path_for_role("imp") != state_path_for_role("qa")


class TestFindWorkspaceRoot:
    """Test suite for find_workspace_root."""

    def test_resolves_from_workspace_root_itself(
        self,
        tmp_path: Path,
    ) -> None:
        """Resolves when anchor is the workspace root (contains pyproject.toml)."""
        # Arrange - Setup test data and preconditions
        (tmp_path / "pyproject.toml").touch()

        # Act - Execute the functionality being tested
        result = find_workspace_root(tmp_path)

        # Assert - Verify the expected outcome
        assert result == tmp_path

    def test_resolves_from_nested_file(
        self,
        tmp_path: Path,
    ) -> None:
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
        tmp_path: Path,
    ) -> None:
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
        tmp_path: Path,
    ) -> None:
        """Raises RuntimeError with 'workspace root' in message when no sentinel exists."""
        # Arrange - Setup test data and preconditions
        nested = tmp_path / "a" / "b"
        nested.mkdir(parents=True)
        anchor = nested / "file.py"
        anchor.touch()

        # Act + Assert - pytest.raises covers both here
        with pytest.raises(RuntimeError, match="workspace root"):
            find_workspace_root(anchor)

    def test_prefers_pyproject_toml_over_git(
        self,
        tmp_path: Path,
    ) -> None:
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
        tmp_path: Path,
    ) -> None:
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
        tmp_path: Path,
    ) -> None:
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

"""Integration tests for git_tools Pydantic validators using GitConfig.

TDD Cycles 8-9: Verify Field pattern validators derive from GitConfig.

Conventions tested:
- #7: Branch type validation pattern
- #8: TDD phase validation pattern
"""
import tempfile
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from mcp_server.tools.git_tools import CreateBranchInput, GitCommitInput
from mcp_server.config.git_config import GitConfig


class TestGitToolsConfigIntegration:
    """Test git_tools Field validators use GitConfig (Conventions #7-8)."""

    def setup_method(self) -> None:
        """Reset GitConfig singleton before each test."""
        GitConfig.reset_instance()

    def teardown_method(self) -> None:
        """Reset GitConfig singleton after each test."""
        GitConfig.reset_instance()

    def test_create_branch_respects_custom_branch_types(self) -> None:
        """Convention #7: CreateBranchInput.branch_type adapts to git.yaml.

        Verifies DRY fix: When git.yaml defines custom branch types,
        the Field pattern validator should accept them (not hardcoded).
        """
        # Create custom git.yaml with "epic" and "hotfix" (no "feature")
        custom_config = {
            "branch_types": ["epic", "hotfix"],
            "tdd_phases": ["red", "green", "refactor", "docs"],
            "commit_prefix_map": {
                "red": "test",
                "green": "feat",
                "refactor": "refactor",
                "docs": "docs",
            },
            "protected_branches": ["main"],
            "branch_name_pattern": "^[a-z0-9-]+$",
            "default_base_branch": "main"
        }

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        ) as temp_file:
            yaml.dump(custom_config, temp_file)
            temp_path = temp_file.name

        try:
            # Load custom config (needed to populate singleton)
            _ = GitConfig.from_file(temp_path)

            # "hotfix" should pass (in custom config)
            input_hotfix = CreateBranchInput(
                name="test-branch",
                branch_type="hotfix",
                base_branch="main"
            )
            assert input_hotfix.branch_type == "hotfix"

            # "feature" should FAIL (NOT in custom config)
            with pytest.raises(ValidationError) as exc_info:
                CreateBranchInput(
                    name="test-branch",
                    branch_type="feature",  # Not in custom config
                    base_branch="main"
                )
            # Validator uses GitConfig, rejects "feature"
            error_str = str(exc_info.value)
            assert "Invalid branch_type 'feature'" in error_str
            assert "Valid types from git.yaml: epic, hotfix" in error_str

        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_git_commit_respects_custom_phases(self) -> None:
        """Convention #8: GitCommitInput.phase adapts to git.yaml.

        Verifies DRY fix: When git.yaml defines custom TDD phases,
        the Field pattern validator should accept them (not hardcoded).
        """
        # Create custom git.yaml with "test" and "impl" phases
        custom_config = {
            "branch_types": ["feature", "fix"],
            "tdd_phases": ["test", "impl"],
            "commit_prefix_map": {"test": "test", "impl": "feat"},
            "protected_branches": ["main"],
            "branch_name_pattern": "^[a-z0-9-]+$",
            "default_base_branch": "main"
        }

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.yaml',
            delete=False
        ) as temp_file:
            yaml.dump(custom_config, temp_file)
            temp_path = temp_file.name

        try:
            # Load custom config (needed to populate singleton)
            _ = GitConfig.from_file(temp_path)

            # "impl" should pass (in custom config)
            input_impl = GitCommitInput(
                phase="impl",
                message="test message"
            )
            assert input_impl.phase == "impl"

            # "red" should FAIL (NOT in custom config)
            with pytest.raises(ValidationError) as exc_info:
                GitCommitInput(
                    phase="red",  # Not in custom config
                    message="test message"
                )
            # Validator uses GitConfig, rejects "red"
            error_str = str(exc_info.value)
            assert "Invalid phase 'red'" in error_str
            assert "Valid phases from git.yaml: test, impl" in error_str

        finally:
            Path(temp_path).unlink(missing_ok=True)

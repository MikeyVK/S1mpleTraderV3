"""Integration tests for git_tools Pydantic validators using GitConfig.

Cycle 8-9 follow-up: Verify field validators derive from GitConfig.

Conventions tested:
- #7: Branch type validation pattern
"""

import tempfile
from pathlib import Path

import pytest
import yaml  # type: ignore[import-untyped]
from pydantic import ValidationError

from mcp_server.config.loader import ConfigLoader
from mcp_server.tools.git_tools import CreateBranchInput


class TestGitToolsConfigIntegration:
    """Test git_tools Field validators use GitConfig (Conventions #7-8)."""

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
            "default_base_branch": "main",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
            yaml.dump(custom_config, temp_file)
            temp_path = temp_file.name

        try:
            # Load custom config and inject it into the input validator
            git_config = ConfigLoader(Path(temp_path).parent).load_git_config(
                config_path=Path(temp_path)
            )
            CreateBranchInput.configure(git_config)

            # "hotfix" should pass (in custom config)
            input_hotfix = CreateBranchInput(
                name="test-branch", branch_type="hotfix", base_branch="main"
            )
            assert input_hotfix.branch_type == "hotfix"

            # "feature" should FAIL (NOT in custom config)
            with pytest.raises(ValidationError) as exc_info:
                CreateBranchInput(
                    name="test-branch",
                    branch_type="feature",  # Not in custom config
                    base_branch="main",
                )
            # Validator uses GitConfig, rejects "feature"
            error_str = str(exc_info.value)
            assert "Invalid branch_type 'feature'" in error_str
            assert "Valid types from git.yaml: epic, hotfix" in error_str

        finally:
            Path(temp_path).unlink(missing_ok=True)

"""Integration tests for pr_tools using GitConfig.

TDD Cycle 10: Verify PR tools use GitConfig for default base branch.

Convention tested:
- #9-11: Default base branch for PR creation
"""

import tempfile
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from mcp_server.config.loader import ConfigLoader
from mcp_server.tools.pr_tools import CreatePRInput


class TestPRToolsConfigIntegration:
    """Test pr_tools use GitConfig (Conventions #9-11)."""

    def test_create_pr_uses_git_config_default_base(self) -> None:
        """Convention #9-11: CreatePRInput.base default from GitConfig.

        Verifies DRY fix: When git.yaml defines custom default_base_branch,
        CreatePRInput should use it (not hardcoded "main").
        """
        # Create custom git.yaml with "develop" as default base
        custom_config = {
            "branch_types": ["feature", "fix"],
            "tdd_phases": ["red", "green"],
            "commit_prefix_map": {"red": "test", "green": "feat"},
            "protected_branches": ["main", "develop"],
            "branch_name_pattern": "^[a-z0-9-]+$",
            "default_base_branch": "develop",  # Custom default
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as temp_file:
            yaml.dump(custom_config, temp_file)
            temp_path = temp_file.name

        try:
            git_config = ConfigLoader(Path(temp_path).parent).load_git_config(
                config_path=Path(temp_path)
            )
            CreatePRInput.configure(git_config)

            # Create PR input without explicit base
            pr_input = CreatePRInput(
                title="Test PR",
                body="Test body",
                head="feature/123-test",
                # base omitted - should use default_base_branch from git.yaml
            )

            # After fix: should use "develop" from git.yaml
            assert pr_input.base == "develop", (
                f"Expected base='develop' from git.yaml, got "
                f"'{pr_input.base}'. If this fails, the Field default is "
                "still hardcoded."
            )

        finally:
            Path(temp_path).unlink(missing_ok=True)

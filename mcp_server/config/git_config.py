"""Git configuration model (Issue #55).

Purpose: Centralized git conventions configuration
Source: .st3/git.yaml
Pattern: Singleton with ClassVar (prevents Pydantic v2 ModelPrivateAttr bug)
"""
import re
from pathlib import Path
from typing import ClassVar, Optional

import yaml  # type: ignore
from pydantic import BaseModel, Field, model_validator


class GitConfig(BaseModel):
    """Git conventions configuration.

    All git-related validations and defaults centralized here.
    Replaces 11 hardcoded conventions across 5 files.
    """

    # Singleton instance (ClassVar prevents Pydantic field conversion)
    singleton_instance: ClassVar[Optional["GitConfig"]] = None

    # Convention #1: Branch types
    branch_types: list[str] = Field(
        default=["feature", "fix", "refactor", "docs", "epic"],
        description="Allowed branch types for create_branch()",
        min_length=1
    )

    # Convention #2: TDD phases
    tdd_phases: list[str] = Field(
        default=["red", "green", "refactor", "docs"],
        description="TDD phases for commit_tdd_phase()",
        min_length=1
    )

    # Convention #3: Commit prefix mapping
    commit_prefix_map: dict[str, str] = Field(
        default={"red": "test", "green": "feat", "refactor": "refactor", "docs": "docs"},
        description="TDD phase → Conventional Commit prefix mapping",
        min_length=1
    )

    # Convention #4: Protected branches
    protected_branches: list[str] = Field(
        default=["main", "master", "develop"],
        description="Branches that cannot be deleted",
        min_length=1
    )

    # Convention #5: Branch name pattern
    branch_name_pattern: str = Field(
        default=r"^[a-z0-9-]+$",
        description="Regex pattern for branch name validation (kebab-case default)"
    )

    # Conventions #9-11: Default base branch
    default_base_branch: str = Field(
        default="main",
        description="Default base branch for PR creation"
    )

    # Compiled regex (cached after validation)
    _compiled_pattern: ClassVar[Optional[re.Pattern[str]]] = None

    @model_validator(mode="after")
    def validate_cross_references(self) -> "GitConfig":
        """Cross-validation: commit_prefix_map keys must be subset of tdd_phases.

        Ensures referential integrity between TDD phases and commit prefixes.
        """
        # Check commit_prefix_map keys
        prefix_keys = set(self.commit_prefix_map)
        phase_set = set(self.tdd_phases)
        invalid_phases = prefix_keys - phase_set
        if invalid_phases:
            raise ValueError(
                f"commit_prefix_map contains invalid phases: {invalid_phases}. "
                f"Must be subset of tdd_phases: {self.tdd_phases}"
            )

        # Validate branch_name_pattern not empty/whitespace
        pattern = str(self.branch_name_pattern)
        if not pattern or pattern.isspace():
            raise ValueError(
                "branch_name_pattern cannot be empty. "
                "Provide a valid regex pattern (e.g., '^[a-z0-9-]+$' for kebab-case)"
            )

        # Compile and cache regex pattern (fail-fast)
        try:
            GitConfig._compiled_pattern = re.compile(pattern)
        except re.error as e:
            raise ValueError(
                f"Invalid branch_name_pattern regex: {pattern}. "
                f"Error: {e}"
            ) from e

        return self

    @classmethod
    def from_file(cls, path: str = ".st3/git.yaml") -> "GitConfig":
        """Load config from YAML file (singleton pattern).

        Args:
            path: Path to git.yaml file

        Returns:
            GitConfig singleton instance

        Raises:
            FileNotFoundError: If git.yaml doesn't exist
            ValueError: If YAML invalid or validation fails
        """
        # Return cached instance if exists
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        # Load YAML
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Git config not found: {path}. "
                f"Create .st3/git.yaml with git conventions."
            )

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Create and cache instance
        cls.singleton_instance = cls(**data)
        return cls.singleton_instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing only)."""
        cls.singleton_instance = None
        cls._compiled_pattern = None

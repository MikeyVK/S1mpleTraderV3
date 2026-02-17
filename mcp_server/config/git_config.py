"""Git configuration model (Issue #55).

Purpose: Centralized git conventions configuration
Source: .st3/git.yaml
Pattern: Singleton with ClassVar (prevents Pydantic v2 ModelPrivateAttr bug)
"""

# pyright: reportAttributeAccessIssue=false
import re
from pathlib import Path
from typing import ClassVar, Optional

import yaml
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
        min_length=1,
    )

    # Convention #2: TDD phases (DEPRECATED - use workflow phases)
    tdd_phases: list[str] = Field(
        default=["red", "green", "refactor", "docs"],
        description=(
            "DEPRECATED: Use workflow phases from workphases.yaml instead. "
            "Legacy TDD phase aliases for backward compatibility"
        ),
        min_length=1,
    )

    # Convention #3: Commit prefix mapping (DEPRECATED - use commit_type in workflow commits)
    commit_prefix_map: dict[str, str] = Field(
        default={"red": "test", "green": "feat", "refactor": "refactor", "docs": "docs"},
        description=(
            "DEPRECATED: Use commit_type parameter in workflow-based commits. "
            "TDD phase → Conventional Commit prefix mapping"
        ),
        min_length=1,
    )

    # Convention #4: Protected branches
    protected_branches: list[str] = Field(
        default=["main", "master", "develop"],
        description="Branches that cannot be deleted",
        min_length=1,
    )

    # Convention #5: Branch name pattern
    branch_name_pattern: str = Field(
        default=r"^[a-z0-9-]+$",
        description="Regex pattern for branch name validation (kebab-case default)",
    )

    # Convention #6: Conventional Commit types (Issue #138)
    commit_types: list[str] = Field(
        default=[
            "feat",
            "fix",
            "docs",
            "style",
            "refactor",
            "test",
            "chore",
            "perf",
            "ci",
            "build",
            "revert",
        ],
        description="Allowed Conventional Commit types (https://www.conventionalcommits.org/)",
        min_length=1,
    )

    # Conventions #9-11: Default base branch
    default_base_branch: str = Field(
        default="main", description="Default base branch for PR creation"
    )

    # Compiled regex (cached after validation)
    _compiled_pattern: ClassVar[re.Pattern[str] | None] = None

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
            raise ValueError(f"Invalid branch_name_pattern regex: {pattern}. Error: {e}") from e

        return self

    # REFACTOR: Helper methods for GitManager integration
    def has_branch_type(self, branch_type: str) -> bool:
        """Check if branch_type is valid (Convention #1).

        Args:
            branch_type: Branch type to check (e.g., "feature", "fix")

        Returns:
            True if branch_type in allowed types
        """
        return branch_type in self.branch_types

    def validate_branch_name(self, name: str) -> bool:
        """Validate branch name against pattern (Convention #5).

        Args:
            name: Branch name to validate

        Returns:
            True if name matches pattern (uses cached compiled regex)
        """
        if GitConfig._compiled_pattern is None:
            # Fallback: compile if not cached (shouldn't happen after validation)
            GitConfig._compiled_pattern = re.compile(self.branch_name_pattern)
        return GitConfig._compiled_pattern.match(name) is not None

    def has_phase(self, phase: str) -> bool:
        """Check if phase is valid TDD phase (Convention #2).

        DEPRECATED: Use workflow phases from workphases.yaml instead.
        This method supports legacy TDD-only workflow.

        Args:
            phase: TDD phase to check (e.g., "red", "green")

        Returns:
            True if phase in allowed phases
        """
        return phase in self.tdd_phases

    def has_commit_type(self, commit_type: str) -> bool:
        """Check if commit_type is valid Conventional Commit type (Convention #6).

        Args:
            commit_type: Commit type to check (e.g., "feat", "fix")

        Returns:
            True if commit_type in allowed types
        """
        return commit_type.lower() in self.commit_types

    def get_prefix(self, phase: str) -> str:
        """Get commit prefix for TDD phase (Convention #3).

        DEPRECATED: Use commit_type parameter in workflow-based commits.
        This method supports legacy TDD-only workflow.

        Args:
            phase: TDD phase (e.g., "red", "green")

        Returns:
            Conventional Commit prefix (e.g., "test", "feat")

        Raises:
            KeyError: If phase not in commit_prefix_map
        """
        return self.commit_prefix_map[phase]

    def is_protected(self, branch_name: str) -> bool:
        """Check if branch is protected (Convention #4).

        Args:
            branch_name: Branch name to check

        Returns:
            True if branch is protected (cannot be deleted)
        """
        return branch_name in self.protected_branches

    def get_all_prefixes(self) -> list[str]:
        """Get all commit prefixes with colons (Convention #6).

        Returns:
            List of prefixes with colons (e.g., ["test:", "feat:", "refactor:", "docs:"])

        Purpose: For PolicyEngine commit message validation.
        Replaces hardcoded prefix list in policies.yaml.
        """
        # Direct comprehension avoids FieldInfo iteration issues
        # Cast to dict for explicit type - pylint understands concrete dict
        prefix_dict: dict[str, str] = dict(self.commit_prefix_map)
        return [f"{prefix}:" for prefix in prefix_dict.values()]

    def build_branch_type_regex(self) -> str:
        """Build regex pattern for branch type matching (Convention #7).

        Returns:
            Regex pattern like "(?:feature|fix|refactor|docs|epic)"

        Purpose: For git_tools to extract issue numbers from branch names.
        Eliminates DRY violation by deriving from branch_types.
        """
        return f"(?:{'|'.join(self.branch_types)})"

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
                f"Git config not found: {path}. Create .st3/git.yaml with git conventions."
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

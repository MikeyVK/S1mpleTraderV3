"""Pure GitConfig schema for ConfigLoader-managed YAML loading."""

from __future__ import annotations

import re
from typing import ClassVar

from pydantic import BaseModel, Field, model_validator


class GitConfig(BaseModel):
    """Git conventions configuration value object."""

    branch_types: list[str] = Field(
        default=["feature", "bug", "fix", "refactor", "docs", "hotfix", "epic"],
        description="Allowed branch types for create_branch()",
        min_length=1,
    )
    tdd_phases: list[str] = Field(
        default=["red", "green", "refactor", "docs"],
        description=(
            "DEPRECATED: Use workflow phases from workphases.yaml instead. "
            "Legacy TDD phase aliases for backward compatibility"
        ),
        min_length=1,
    )
    commit_prefix_map: dict[str, str] = Field(
        default={
            "red": "test",
            "green": "feat",
            "refactor": "refactor",
            "docs": "docs",
        },
        description=(
            "DEPRECATED: Use commit_type parameter in workflow-based commits. "
            "TDD phase to Conventional Commit prefix mapping"
        ),
        min_length=1,
    )
    protected_branches: list[str] = Field(
        default=["main", "master", "develop"],
        description="Branches that cannot be deleted",
        min_length=1,
    )
    branch_name_pattern: str = Field(
        default=r"^[a-z0-9-]+$",
        description="Regex pattern for branch name validation (kebab-case default)",
    )
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
        description="Allowed Conventional Commit types",
        min_length=1,
    )
    default_base_branch: str = Field(
        default="main",
        description="Default base branch for PR creation",
    )
    issue_title_max_length: int = Field(
        default=72,
        description="Maximum allowed length for issue titles",
        ge=1,
    )

    _compiled_pattern: ClassVar[re.Pattern[str] | None] = None

    @model_validator(mode="after")
    def validate_cross_references(self) -> GitConfig:
        prefix_keys = set(self.commit_prefix_map)
        phase_set = set(self.tdd_phases)
        invalid_phases = prefix_keys - phase_set
        if invalid_phases:
            raise ValueError(
                f"commit_prefix_map contains invalid phases: {invalid_phases}. "
                f"Must be subset of tdd_phases: {self.tdd_phases}"
            )

        pattern = str(self.branch_name_pattern)
        if not pattern or pattern.isspace():
            raise ValueError(
                "branch_name_pattern cannot be empty. "
                "Provide a valid regex pattern (e.g. '^[a-z0-9-]+$' for kebab-case)"
            )

        try:
            GitConfig._compiled_pattern = re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Invalid branch_name_pattern regex: {pattern}. Error: {exc}") from exc

        return self

    def has_branch_type(self, branch_type: str) -> bool:
        return branch_type in self.branch_types

    def validate_branch_name(self, name: str) -> bool:
        if GitConfig._compiled_pattern is None:
            GitConfig._compiled_pattern = re.compile(self.branch_name_pattern)
        return GitConfig._compiled_pattern.match(name) is not None

    def has_phase(self, phase: str) -> bool:
        return phase in self.tdd_phases

    def has_commit_type(self, commit_type: str) -> bool:
        return commit_type.lower() in self.commit_types

    def get_prefix(self, phase: str) -> str:
        return self.commit_prefix_map[phase]

    def is_protected(self, branch_name: str) -> bool:
        return branch_name in self.protected_branches

    def get_all_prefixes(self) -> list[str]:
        prefix_dict: dict[str, str] = dict(self.commit_prefix_map)
        return [f"{prefix}:" for prefix in prefix_dict.values()]

    def build_branch_type_regex(self) -> str:
        return f"(?:{'|'.join(self.branch_types)})"

    def extract_issue_number(self, branch: str) -> int | None:
        pattern = rf"^(?:{self.build_branch_type_regex()[3:-1]})/(\d+)-"
        match = re.match(pattern, branch)
        if match is None:
            return None
        return int(match.group(1))

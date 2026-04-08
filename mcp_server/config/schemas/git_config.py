# mcp_server/config/schemas/git_config.py
"""
Git configuration schema value object.

Defines the typed contract for git conventions loaded from YAML by the
configuration layer.

@layer: Backend (Config)
@dependencies: [pydantic, re, typing]
@responsibilities:
    - Define the typed GitConfig schema contract
    - Validate cross-field git configuration consistency
    - Expose helper methods for branch and commit convention checks
"""

from __future__ import annotations

import re
from typing import ClassVar

from pydantic import BaseModel, Field, model_validator


class GitConfig(BaseModel):
    """Git conventions configuration value object."""

    branch_types: list[str] = Field(
        ...,
        description="Allowed branch types for create_branch()",
        min_length=1,
    )
    protected_branches: list[str] = Field(
        ...,
        description="Branches that cannot be deleted",
        min_length=1,
    )
    branch_name_pattern: str = Field(
        ...,
        description="Regex pattern for branch name validation (kebab-case default)",
    )
    commit_types: list[str] = Field(
        ...,
        description="Allowed Conventional Commit types",
        min_length=1,
    )
    default_base_branch: str = Field(
        ...,
        description="Default base branch for PR creation",
    )
    issue_title_max_length: int = Field(
        ...,
        description="Maximum allowed length for issue titles",
        ge=1,
    )

    _compiled_pattern: ClassVar[re.Pattern[str] | None] = None

    @model_validator(mode="after")
    def validate_branch_name_pattern(self) -> GitConfig:
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

    def has_commit_type(self, commit_type: str) -> bool:
        return commit_type.lower() in self.commit_types

    def is_protected(self, branch_name: str) -> bool:
        return branch_name in self.protected_branches

    def get_all_prefixes(self) -> list[str]:
        return [f"{t}:" for t in self.commit_types]

    def build_branch_type_regex(self) -> str:
        return f"(?:{'|'.join(self.branch_types)})"

    def extract_issue_number(self, branch: str) -> int | None:
        pattern = rf"^(?:{self.build_branch_type_regex()[3:-1]})/(\d+)-"
        match = re.match(pattern, branch)
        if match is None:
            return None
        return int(match.group(1))

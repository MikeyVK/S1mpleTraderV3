# mcp_server/config/schemas/issue_config.py
"""
Issue configuration schema definitions.

Defines typed value objects for issue types, workflow mapping, and label
requirements loaded by the config layer.

@layer: Backend (Config)
@dependencies: [pydantic]
@responsibilities:
    - Define issue type and root issue config schema contracts
    - Validate issue workflow and label requirement metadata
    - Provide issue-type lookup helpers for workflow consumers
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, PrivateAttr


class IssueTypeEntry(BaseModel):
    """Single issue type entry from issues.yaml."""

    name: str
    workflow: str
    label: str


class IssueConfig(BaseModel):
    """Issue conventions configuration value object."""

    version: str
    issue_types: list[IssueTypeEntry]
    required_label_categories: list[str] = Field(default_factory=list)
    optional_label_inputs: dict[str, Any] = Field(default_factory=dict)
    _index: dict[str, IssueTypeEntry] = PrivateAttr(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:  # noqa: ANN401
        self._index = {entry.name: entry for entry in self.issue_types}

    def get_workflow(self, issue_type: str) -> str:
        entry = self._index.get(issue_type)
        if entry is None:
            valid = sorted(self._index)
            raise ValueError(f"Unknown issue type: '{issue_type}'. Valid types: {valid}")
        return entry.workflow

    def get_label(self, issue_type: str) -> str:
        entry = self._index.get(issue_type)
        if entry is None:
            valid = sorted(self._index)
            raise ValueError(f"Unknown issue type: '{issue_type}'. Valid types: {valid}")
        return entry.label

    def has_issue_type(self, issue_type: str) -> bool:
        return issue_type in self._index

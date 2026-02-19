"""Issue configuration model (Issue #149).

Purpose: Config-driven issue type conventions — maps issue_type to workflow and type:* label.
Source: .st3/issues.yaml
Pattern: Singleton with ClassVar (matches GitConfig pattern)
"""

from pathlib import Path
from typing import Any, ClassVar, Optional

import yaml
from pydantic import BaseModel


class IssueTypeEntry(BaseModel):
    """Single issue type entry from issues.yaml."""

    name: str
    workflow: str
    label: str  # e.g. "type:bug" — hotfix maps to "type:bug", not "type:hotfix"


class IssueConfig(BaseModel):
    """Issue conventions configuration.

    Maps issue types to workflows and type:* labels.
    Loaded from .st3/issues.yaml. Singleton per process.
    """

    singleton_instance: ClassVar[Optional["IssueConfig"]] = None

    version: str
    issue_types: list[IssueTypeEntry]
    required_label_categories: list[str] = []
    optional_label_inputs: dict[str, Any] = {}

    # Internal lookup built after validation
    _index: ClassVar[dict[str, IssueTypeEntry]] = {}

    def model_post_init(self, __context: Any) -> None:  # noqa: ANN401
        """Build name → entry lookup index."""
        IssueConfig._index = {entry.name: entry for entry in self.issue_types}

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_workflow(self, issue_type: str) -> str:
        """Return workflow name for the given issue type.

        Args:
            issue_type: Issue type name (e.g. "feature", "hotfix").

        Returns:
            Workflow name (e.g. "feature", "hotfix").

        Raises:
            ValueError: If issue_type is not in issues.yaml.
        """
        entry = IssueConfig._index.get(issue_type)
        if entry is None:
            valid = sorted(IssueConfig._index)
            raise ValueError(f"Unknown issue type: '{issue_type}'. Valid types: {valid}")
        return entry.workflow

    def get_label(self, issue_type: str) -> str:
        """Return the type:* label for the given issue type.

        Note: 'hotfix' returns 'type:bug' (not 'type:hotfix').

        Args:
            issue_type: Issue type name.

        Returns:
            Label string (e.g. "type:bug", "type:feature").

        Raises:
            ValueError: If issue_type is not in issues.yaml.
        """
        entry = IssueConfig._index.get(issue_type)
        if entry is None:
            valid = sorted(IssueConfig._index)
            raise ValueError(f"Unknown issue type: '{issue_type}'. Valid types: {valid}")
        return entry.label

    def has_issue_type(self, issue_type: str) -> bool:
        """Return True if the issue type is defined in issues.yaml."""
        return issue_type in IssueConfig._index

    # ------------------------------------------------------------------
    # Singleton factory
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str = ".st3/issues.yaml") -> "IssueConfig":
        """Load config from YAML file (singleton pattern).

        Args:
            path: Path to issues.yaml file.

        Returns:
            IssueConfig singleton instance.

        Raises:
            FileNotFoundError: If issues.yaml doesn't exist.
            ValueError: If YAML is invalid or validation fails.
        """
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Issue config not found: {path}. "
                f"Create .st3/issues.yaml with issue type conventions."
            )

        with open(config_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        cls.singleton_instance = cls(**data)
        return cls.singleton_instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing only)."""
        cls.singleton_instance = None
        cls._index = {}

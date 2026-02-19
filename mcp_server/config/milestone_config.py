"""Milestone configuration model (Issue #149).

Purpose: Config-driven milestone validation — permissive when list empty.
Source: .st3/milestones.yaml
Pattern: Singleton with ClassVar (matches GitConfig pattern)
"""

from pathlib import Path
from typing import ClassVar, Optional

import yaml
from pydantic import BaseModel


class MilestoneEntry(BaseModel):
    """Single milestone entry from milestones.yaml."""

    number: int
    title: str
    state: str = "open"


class MilestoneConfig(BaseModel):
    """Milestone validation configuration.

    Validates milestone titles against known milestones.
    Permissive (always passes) when milestones list is empty — this is
    intentional: the file starts empty and is populated manually.
    Loaded from .st3/milestones.yaml. Singleton per process.
    """

    singleton_instance: ClassVar[Optional["MilestoneConfig"]] = None

    version: str
    milestones: list[MilestoneEntry] = []

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def validate_milestone(self, title: str) -> bool:
        """Return True if title is a known milestone, or if list is empty (permissive).

        Args:
            title: Milestone title to check.

        Returns:
            True when list is empty (permissive) or title matches a known milestone.
        """
        if not self.milestones:
            return True
        return any(m.title == title for m in self.milestones)

    # ------------------------------------------------------------------
    # Singleton factory
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str = ".st3/milestones.yaml") -> "MilestoneConfig":
        """Load config from YAML file (singleton pattern).

        Args:
            path: Path to milestones.yaml file.

        Returns:
            MilestoneConfig singleton instance.

        Raises:
            FileNotFoundError: If milestones.yaml doesn't exist.
        """
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Milestone config not found: {path}. "
                f"Create .st3/milestones.yaml (empty list is valid)."
            )

        with open(config_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        cls.singleton_instance = cls(**data)
        return cls.singleton_instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing only)."""
        cls.singleton_instance = None

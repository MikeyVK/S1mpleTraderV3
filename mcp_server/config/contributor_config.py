"""Contributor configuration model (Issue #149).

Purpose: Config-driven assignee validation — permissive when list empty.
Source: .st3/contributors.yaml
Pattern: Singleton with ClassVar (matches GitConfig pattern)
"""

from pathlib import Path
from typing import ClassVar, Optional

import yaml
from pydantic import BaseModel


class ContributorEntry(BaseModel):
    """Single contributor entry from contributors.yaml."""

    login: str
    name: str | None = None


class ContributorConfig(BaseModel):
    """Contributor validation configuration.

    Validates assignee logins against known contributors.
    Permissive (always passes) when contributors list is empty — this is
    intentional: the file starts empty and is populated manually.
    Loaded from .st3/contributors.yaml. Singleton per process.
    """

    singleton_instance: ClassVar[Optional["ContributorConfig"]] = None

    version: str
    contributors: list[ContributorEntry] = []

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def validate_assignee(self, login: str) -> bool:
        """Return True if login is a known contributor, or if list is empty (permissive).

        Args:
            login: GitHub login to check (case-sensitive).

        Returns:
            True when list is empty (permissive) or login matches a known contributor.
        """
        if not self.contributors:
            return True
        return any(c.login == login for c in self.contributors)

    # ------------------------------------------------------------------
    # Singleton factory
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str = ".st3/contributors.yaml") -> "ContributorConfig":
        """Load config from YAML file (singleton pattern).

        Args:
            path: Path to contributors.yaml file.

        Returns:
            ContributorConfig singleton instance.

        Raises:
            FileNotFoundError: If contributors.yaml doesn't exist.
        """
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Contributor config not found: {path}. "
                f"Create .st3/contributors.yaml (empty list is valid)."
            )

        with open(config_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        cls.singleton_instance = cls(**data)
        return cls.singleton_instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing only)."""
        cls.singleton_instance = None

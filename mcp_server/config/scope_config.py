"""Scope configuration model (Issue #149).

Purpose: Config-driven scope validation — flat list of valid scope names.
Source: .st3/scopes.yaml
Pattern: Singleton with ClassVar (matches GitConfig pattern)
"""

from pathlib import Path
from typing import ClassVar, Optional

import yaml
from pydantic import BaseModel


class ScopeConfig(BaseModel):
    """Scope conventions configuration.

    Holds the list of valid scope names. Labels are derived by convention
    as 'scope:{name}' — no explicit label field is needed here.
    Loaded from .st3/scopes.yaml. Singleton per process.
    """

    singleton_instance: ClassVar[Optional["ScopeConfig"]] = None

    version: str
    scopes: list[str]

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def has_scope(self, name: str) -> bool:
        """Return True if name is a valid scope (case-sensitive).

        Args:
            name: Scope name to validate.

        Returns:
            True if name is in the scopes list.
        """
        return name in self.scopes

    # ------------------------------------------------------------------
    # Singleton factory
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str = ".st3/scopes.yaml") -> "ScopeConfig":
        """Load config from YAML file (singleton pattern).

        Args:
            path: Path to scopes.yaml file.

        Returns:
            ScopeConfig singleton instance.

        Raises:
            FileNotFoundError: If scopes.yaml doesn't exist.
            ValueError: If YAML is invalid or validation fails.
        """
        if cls.singleton_instance is not None:
            return cls.singleton_instance

        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Scope config not found: {path}. Create .st3/scopes.yaml with valid scope names."
            )

        with open(config_path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        cls.singleton_instance = cls(**data)
        return cls.singleton_instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing only)."""
        cls.singleton_instance = None

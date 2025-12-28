"""
Label configuration management.

Loads and validates label definitions from labels.yaml.

@layer: Backend (Config)
@dependencies: [dataclasses, re, pathlib, yaml, pydantic]
@responsibilities:
    - Load labels from YAML
    - Validate label format (name, color)
    - Provide label lookup by name/category
    - Sync labels to GitHub
"""

# Standard library
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Label:
    """Immutable label definition from labels.yaml."""

    name: str
    color: str  # 6-char hex WITHOUT # prefix
    description: str = ""

    def __post_init__(self) -> None:
        """Validate color format on construction."""
        if not self._is_valid_color(self.color):
            raise ValueError(
                f"Invalid color format '{self.color}'. "
                f"Expected 6-character hex WITHOUT # prefix (e.g., 'ff0000')"
            )

    @staticmethod
    def _is_valid_color(color: str) -> bool:
        """Check if color is valid 6-char hex."""
        return bool(re.match(r'^[0-9a-fA-F]{6}$', color))

    def to_github_dict(self) -> dict[str, str]:
        """Convert to GitHub API format."""
        return {
            "name": self.name,
            "color": self.color,
            "description": self.description
        }

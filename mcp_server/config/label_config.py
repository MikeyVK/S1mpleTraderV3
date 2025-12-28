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
from pathlib import Path
from typing import Optional

# Third-party
from pydantic import BaseModel, Field, field_validator, ConfigDict
import yaml  # type: ignore[import-untyped]


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


class LabelConfig(BaseModel):
    """Label configuration loaded from labels.yaml."""

    version: str = Field(..., description="Schema version")
    labels: list[Label] = Field(..., description="Label definitions")
    freeform_exceptions: list[str] = Field(
        default_factory=list,
        description="Non-pattern labels"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True  # Allow Label dataclass
    )

    _instance: Optional["LabelConfig"] = None
    _labels_by_name: dict[str, Label] = {}

    @classmethod
    def load(cls, config_path: Path | None = None) -> "LabelConfig":
        """Load label configuration from YAML file."""
        if cls._instance is not None:
            return cls._instance

        if config_path is None:
            config_path = Path(".st3/labels.yaml")

        if not config_path.exists():
            raise FileNotFoundError(
                f"Label configuration not found: {config_path}"
            )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in {config_path}: {e}") from e

        # Parse labels (ensure labels field exists)
        if "labels" not in data:
            raise ValueError("Missing required field: labels")
        label_dicts = data["labels"]
        labels = [Label(**ld) for ld in label_dicts]

        # Create instance
        instance = cls(
            version=data.get("version"),
            labels=labels,
            freeform_exceptions=data.get("freeform_exceptions", [])
        )

        instance._build_caches()
        cls._instance = instance
        return instance

    def _build_caches(self) -> None:
        """Build internal lookup caches."""
        self._labels_by_name = {label.name: label for label in self.labels}

    @field_validator("labels")
    @classmethod
    def validate_no_duplicates(cls, labels: list[Label]) -> list[Label]:
        """Ensure no duplicate label names."""
        names = [label.name for label in labels]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            raise ValueError(f"Duplicate label names: {set(duplicates)}")
        return labels

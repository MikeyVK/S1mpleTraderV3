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
    - Support dynamic label patterns
"""

# Standard library
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any

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


@dataclass(frozen=True)
class LabelPattern:
    """Dynamic label pattern definition.
    
    Patterns allow validation of labels that follow a template
    (e.g., parent:issue-18, parent:issue-42) without pre-creating them.
    """

    pattern: str  # Regex pattern
    description: str
    color: str  # Default color for pattern-matched labels
    example: str = ""

    def matches(self, label_name: str) -> bool:
        """Check if label name matches this pattern."""
        return bool(re.match(self.pattern, label_name))


class LabelConfig(BaseModel):
    """Label configuration loaded from labels.yaml.
    
    Example:
        >>> config = LabelConfig(
        ...     version="1.0",
        ...     labels=[
        ...         Label(name="type:feature", color="1D76DB", description="New feature")
        ...     ],
        ...     freeform_exceptions=["good first issue"],
        ...     label_patterns=[
        ...         LabelPattern(pattern="^parent:issue-\\d+$", description="Parent issue",
        ...                      color="EDEDED", example="parent:issue-18")
        ...     ]
        ... )
    """

    version: str = Field(..., description="Schema version")
    labels: list[Label] = Field(..., description="Label definitions")
    freeform_exceptions: list[str] = Field(
        default_factory=list,
        description="Non-pattern labels"
    )
    label_patterns: list[LabelPattern] = Field(
        default_factory=list,
        description="Dynamic label patterns (validated but not pre-created)"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True  # Allow Label/LabelPattern dataclasses
    )

    _instance: Optional["LabelConfig"] = None
    _labels_by_name: dict[str, Label] = {}
    _labels_by_category: dict[str, list[Label]] = {}

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

        # Parse label patterns (optional)
        pattern_dicts = data.get("label_patterns", [])
        patterns = [LabelPattern(**pd) for pd in pattern_dicts]

        # Create instance
        instance = cls(
            version=data.get("version"),
            labels=labels,
            freeform_exceptions=data.get("freeform_exceptions", []),
            label_patterns=patterns
        )

        instance._build_caches()
        cls._instance = instance
        return instance

    def _build_caches(self) -> None:
        """Build internal lookup caches."""
        self._labels_by_name = {label.name: label for label in self.labels}

        # Group by category
        self._labels_by_category = {}
        for label in self.labels:
            if ":" in label.name:
                cat = label.name.split(":", 1)[0]
                if cat not in self._labels_by_category:
                    self._labels_by_category[cat] = []
                self._labels_by_category[cat].append(label)

    def validate_label_name(self, name: str) -> tuple[bool, str]:
        """Validate label name against pattern rules.
        
        Checks in order:
        1. Freeform exceptions (always valid)
        2. Defined labels (exact match)
        3. Dynamic patterns (regex match)
        4. Standard category:value pattern
        """
        # Check freeform exceptions
        if name in self.freeform_exceptions:
            return (True, "")

        # Check if it's a defined label (exact match)
        if name in self._labels_by_name:
            return (True, "")

        # Check dynamic patterns
        for pattern in self.label_patterns:
            if pattern.matches(name):
                return (True, "")

        # Check standard category:value pattern
        pattern_str = r'^(type|priority|status|phase|scope|component|effort|parent):[a-z0-9-]+$'
        if not re.match(pattern_str, name):
            # Build helpful error with pattern examples
            pattern_examples = [p.example for p in self.label_patterns if p.example]
            examples_str = f" Dynamic patterns: {', '.join(pattern_examples)}." if pattern_examples else ""
            
            return (
                False,
                f"Label '{name}' does not match required pattern. "
                f"Expected format: 'category:value' where category is one of "
                f"[type, priority, status, phase, scope, component, effort, parent] "
                f"and value is lowercase alphanumeric with hyphens.{examples_str} "
                f"Freeform labels must be in freeform_exceptions list."
            )

        return (True, "")

    def label_exists(self, name: str) -> bool:
        """Check if label is defined in labels.yaml (exact match only)."""
        return name in self._labels_by_name

    def get_label(self, name: str) -> Label | None:
        """Get label by exact name match."""
        return self._labels_by_name.get(name)

    def get_labels_by_category(self, category: str) -> list[Label]:
        """Get all labels in a category."""
        return self._labels_by_category.get(category, [])

    def sync_to_github(
        self,
        github_adapter: Any,
        dry_run: bool = False
    ) -> dict[str, list[str]]:
        """Sync labels to GitHub repository."""
        result: dict[str, list[str]] = {
            "created": [],
            "updated": [],
            "skipped": [],
            "errors": []
        }

        try:
            existing = github_adapter.list_labels()
            existing_by_name = {label["name"]: label for label in existing}
        except Exception as e:  # pylint: disable=broad-exception-caught
            result["errors"].append(f"Failed to fetch labels: {e}")
            return result

        for label in self.labels:
            try:
                if label.name not in existing_by_name:
                    if not dry_run:
                        github_adapter.create_label(
                            name=label.name,
                            color=label.color,
                            description=label.description
                        )
                    result["created"].append(label.name)
                else:
                    existing_label = existing_by_name[label.name]
                    if self._needs_update(label, existing_label):
                        if not dry_run:
                            github_adapter.update_label(
                                name=label.name,
                                color=label.color,
                                description=label.description
                            )
                        result["updated"].append(label.name)
                    else:
                        result["skipped"].append(label.name)

            except Exception as e:  # pylint: disable=broad-exception-caught
                result["errors"].append(f"{label.name}: {e}")

        return result

    def _needs_update(self, yaml_label: Label, github_label: dict[str, Any]) -> bool:
        """Check if GitHub label needs update."""
        return bool(
            yaml_label.color != github_label["color"] or
            yaml_label.description != github_label.get("description", "")
        )

    @field_validator("labels")
    @classmethod
    def validate_no_duplicates(cls, labels: list[Label]) -> list[Label]:
        """Ensure no duplicate label names."""
        names = [label.name for label in labels]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            raise ValueError(f"Duplicate label names: {set(duplicates)}")
        return labels

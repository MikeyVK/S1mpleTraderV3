"""Legacy compatibility wrapper for LabelConfig during C_LOADER migration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, PrivateAttr, field_validator

from mcp_server.config.loader import ConfigLoader
from mcp_server.core.exceptions import ConfigError


@dataclass(frozen=True)
class Label:
    """Immutable label definition from labels.yaml."""

    name: str
    color: str
    description: str = ""

    def __post_init__(self) -> None:
        if not re.match(r"^[0-9a-fA-F]{6}$", self.color):
            raise ValueError(
                f"Invalid color format '{self.color}'. "
                f"Expected 6-character hex WITHOUT # prefix (e.g., 'ff0000')"
            )

    def to_github_dict(self) -> dict[str, str]:
        return {"name": self.name, "color": self.color, "description": self.description}


@dataclass(frozen=True)
class LabelPattern:
    """Dynamic label pattern definition."""

    pattern: str
    description: str
    color: str
    example: str = ""

    def matches(self, label_name: str) -> bool:
        return bool(re.match(self.pattern, label_name))


class LabelConfig(BaseModel):
    """Compatibility surface for pre-C_LOADER consumers."""

    version: str
    labels: list[Label]
    freeform_exceptions: list[str] = []
    label_patterns: list[LabelPattern] = []

    model_config = ConfigDict(arbitrary_types_allowed=True)

    _instance: ClassVar[LabelConfig | None] = None
    _loaded_path: ClassVar[Path | None] = None
    _loaded_mtime: ClassVar[float | None] = None

    _labels_by_name: dict[str, Label] = PrivateAttr(default_factory=dict)
    _labels_by_category: dict[str, list[Label]] = PrivateAttr(default_factory=dict)

    @field_validator("labels")
    @classmethod
    def validate_no_duplicates(cls, labels: list[Label]) -> list[Label]:
        names = [label.name for label in labels]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            raise ValueError(f"Duplicate label names: {set(duplicates)}")
        return labels

    @classmethod
    def load(cls, config_path: Path | None = None) -> LabelConfig:
        if config_path is None:
            if cls._instance is not None:
                return cls._instance
            config_path = Path(".st3/config/labels.yaml")

        if not config_path.exists():
            raise FileNotFoundError(f"Label configuration not found: {config_path}")

        current_mtime = config_path.stat().st_mtime
        if (
            cls._instance is not None
            and cls._loaded_path == config_path
            and cls._loaded_mtime == current_mtime
        ):
            return cls._instance

        loader = ConfigLoader(config_root=config_path.parent)
        try:
            data, _ = loader._load_yaml("labels.yaml", config_path=config_path)
        except ConfigError as exc:
            if "Invalid YAML in" in str(exc):
                raise ValueError(f"Invalid YAML syntax in {config_path}: {exc}") from exc
            raise

        if "labels" not in data:
            raise ValueError("Missing required field: labels")

        labels = [Label(**label_dict) for label_dict in data["labels"]]
        patterns = [LabelPattern(**pattern_dict) for pattern_dict in data.get("label_patterns", [])]
        instance = cls.model_validate(
            {
                "version": data.get("version"),
                "labels": labels,
                "freeform_exceptions": data.get("freeform_exceptions", []),
                "label_patterns": patterns,
            }
        )
        instance._build_caches()

        cls._instance = instance
        cls._loaded_path = config_path
        cls._loaded_mtime = current_mtime
        return instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
        cls._loaded_path = None
        cls._loaded_mtime = None

    def _build_caches(self) -> None:
        self._labels_by_name = {label.name: label for label in self.labels}
        self._labels_by_category = {}
        for label in self.labels:
            if ":" in label.name:
                category = label.name.split(":", 1)[0]
                self._labels_by_category.setdefault(category, []).append(label)

    def validate_label_name(self, name: str) -> tuple[bool, str]:
        if name in self.freeform_exceptions:
            return (True, "")
        if name in self._labels_by_name:
            return (True, "")
        for pattern in self.label_patterns:
            if pattern.matches(name):
                return (True, "")

        pattern_examples = [pattern.example for pattern in self.label_patterns if pattern.example]
        examples_str = (
            f" Dynamic patterns: {', '.join(pattern_examples)}." if pattern_examples else ""
        )
        pattern_str = r"^(type|priority|status|phase|scope|component|effort|parent):[a-z0-9-]+$"
        if not re.match(pattern_str, name):
            return (
                False,
                f"Label '{name}' does not match required pattern. "
                f"Expected format: 'category:value' where category is one of "
                f"[type, priority, status, phase, scope, component, effort, parent] "
                f"and value is lowercase alphanumeric with hyphens.{examples_str} "
                f"Freeform labels must be in freeform_exceptions list.",
            )

        return (True, "")

    def label_exists(self, name: str) -> bool:
        return name in self._labels_by_name

    def get_label(self, name: str) -> Label | None:
        return self._labels_by_name.get(name)

    def get_labels_by_category(self, category: str) -> list[Label]:
        return self._labels_by_category.get(category, [])

    def sync_to_github(self, github_adapter: Any, dry_run: bool = False) -> dict[str, list[str]]:  # noqa: ANN401
        result: dict[str, list[str]] = {"created": [], "updated": [], "skipped": [], "errors": []}

        try:
            existing = github_adapter.list_labels()
            existing_by_name = {label["name"]: label for label in existing}
        except Exception as exc:  # noqa: BLE001
            result["errors"].append(f"Failed to fetch labels: {exc}")
            return result

        for label in self.labels:
            try:
                if label.name not in existing_by_name:
                    if not dry_run:
                        github_adapter.create_label(
                            name=label.name,
                            color=label.color,
                            description=label.description,
                        )
                    result["created"].append(label.name)
                else:
                    existing_label = existing_by_name[label.name]
                    if self._needs_update(label, existing_label):
                        if not dry_run:
                            github_adapter.update_label(
                                name=label.name,
                                color=label.color,
                                description=label.description,
                            )
                        result["updated"].append(label.name)
                    else:
                        result["skipped"].append(label.name)
            except Exception as exc:  # noqa: BLE001
                result["errors"].append(f"{label.name}: {exc}")

        return result

    def _needs_update(self, yaml_label: Label, github_label: dict[str, Any]) -> bool:
        return bool(
            yaml_label.color != github_label["color"]
            or yaml_label.description != github_label.get("description", "")
        )

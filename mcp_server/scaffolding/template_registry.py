"""mcp_server.scaffolding.template_registry

Template Registry for multi-tier template version management (Issue #72 Task 1.1).

Task 3.8: Registry storage format migrated from YAML to JSON.

Responsibilities:
- Load/save `.st3/template_registry.json`
- Track version hashes → tier chains
- Detect hash collisions
- Manage current versions per artifact type
- One-time migration: if legacy `.st3/template_registry.yaml` exists and JSON is missing,
  convert YAML→JSON and delete the YAML file.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import json

import yaml


class TemplateRegistry:
    """Read/write operations for `.st3/template_registry.json`.

    Notes:
    - Internal representation matches persisted schema keys exactly.
    - Migration: if initialized with a `.json` path that does not exist and a sibling
      `template_registry.yaml` exists, it will be converted to JSON and removed.
    """

    def __init__(self, registry_path: Path = Path(".st3/template_registry.json")) -> None:
        self.registry_path = registry_path
        self._data: dict[str, Any] = self._load()

    def _legacy_yaml_path(self) -> Path:
        return self.registry_path.with_name("template_registry.yaml")

    def _load(self) -> dict[str, Any]:
        """Load registry JSON or initialize if missing.

        Migration behavior (Task 3.8):
        - If JSON path exists: load JSON.
        - Else if legacy YAML exists: load YAML, persist JSON, delete YAML.
        - Else: return empty registry.
        """
        if self.registry_path.exists():
            return self._load_json_file(self.registry_path)

        legacy_yaml = self._legacy_yaml_path()
        if legacy_yaml.exists() and self.registry_path.suffix.lower() == ".json":
            data = self._load_yaml_file(legacy_yaml)
            self._data = data
            self._persist()
            legacy_yaml.unlink(missing_ok=True)
            return data

        return self._empty_registry()

    def _load_json_file(self, path: Path) -> dict[str, Any]:
        try:
            text = path.read_text(encoding="utf-8")
            if not text.strip():
                return self._empty_registry()
            data = json.loads(text)
            if not isinstance(data, dict):
                return self._empty_registry()
            return cast(dict[str, Any], data)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return self._empty_registry()

    def _load_yaml_file(self, path: Path) -> dict[str, Any]:
        try:
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if data is None or not isinstance(data, dict):
                return self._empty_registry()
            return cast(dict[str, Any], data)
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            return self._empty_registry()

    def _empty_registry(self) -> dict[str, Any]:
        """Return empty registry structure."""
        return {
            "version": "1.0",
            "version_hashes": {},
            "current_versions": {},
            "templates": {},
        }

    def save_version(
        self,
        artifact_type: str,
        version_hash: str,
        tier_versions: dict[str, tuple[str, str]],  # {tier_name: (template_id, version)}
    ) -> None:
        """Save new version entry to registry.

        Args:
            artifact_type: "worker", "research", etc.
            version_hash: 8-char hex hash
            tier_versions: Tier chain with versions

        Raises:
            ValueError: If hash collision detected (different tier chain for same hash)
        """
        if version_hash in self._data["version_hashes"]:
            existing = self._data["version_hashes"][version_hash]
            if existing["artifact_type"] != artifact_type:
                raise ValueError(
                    f"Hash collision: {version_hash} used by "
                    f"{existing['artifact_type']} and {artifact_type}"
                )

            existing_tiers = {
                tier: (existing[tier]["template_id"], existing[tier]["version"])
                for tier in ["concrete", "tier0", "tier1", "tier2", "tier3"]
                if tier in existing
            }
            if existing_tiers == tier_versions:
                return

            raise ValueError(
                f"Hash collision: {version_hash} for {artifact_type} "
                f"maps to different tier versions"
            )

        entry: dict[str, Any] = {
            "artifact_type": artifact_type,
            "created": datetime.now(UTC).isoformat(),
            "hash_algorithm": "SHA256",
        }

        for tier_name, (template_id, version) in tier_versions.items():
            entry[tier_name] = {"template_id": template_id, "version": version}

        self._data["version_hashes"][version_hash] = entry
        self._data["current_versions"][artifact_type] = version_hash
        self._persist()

    def lookup_hash(self, version_hash: str) -> dict[str, Any] | None:
        result = self._data["version_hashes"].get(version_hash)
        return cast(dict[str, Any] | None, result)

    def get_current_version(self, artifact_type: str) -> str | None:
        result = self._data["current_versions"].get(artifact_type)
        return cast(str | None, result)

    def get_all_hashes(self) -> list[str]:
        return list(self._data["version_hashes"].keys())

    def get_all_artifact_types(self) -> list[str]:
        return list(self._data["current_versions"].keys())

    def _persist(self) -> None:
        """Write registry to disk (JSON)."""
        self._data["last_updated"] = datetime.now(UTC).isoformat()

        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.registry_path.write_text(
            json.dumps(self._data, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )

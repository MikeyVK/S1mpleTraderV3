"""
Template Registry for multi-tier template version management (Issue #72 Task 1.1).

Responsibilities:
- Load/save .st3/template_registry.yaml
- Track version hashes → tier chains
- Detect hash collisions
- Manage current versions per artifact type
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import yaml


class TemplateRegistry:
    """
    Read/write operations for .st3/template_registry.yaml.

    Responsibilities:
    - Load registry from disk (YAML parsing)
    - Lookup hash → tier chain mapping
    - Save new version entry (after scaffolding)
    - Detect hash collisions (within artifact_type namespace)

    Note:
        Internal representation matches YAML schema exactly (no transformation).
        Uses version_hashes: top-level key with concrete/tier0/tier1/tier2/tier3 structure.
    """

    def __init__(self, registry_path: Path = Path(".st3/template_registry.yaml")) -> None:
        self.registry_path = registry_path
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        """Load registry YAML or initialize if missing."""
        if not self.registry_path.exists():
            return self._empty_registry()

        with self.registry_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
            # Guard against empty/invalid YAML files
            if data is None or not isinstance(data, dict):
                return self._empty_registry()
            return cast(dict[str, Any], data)

    def _empty_registry(self) -> dict[str, Any]:
        """Return empty registry structure."""
        return {
            "version": "1.0",
            "version_hashes": {},  # Matches YAML schema (not "hashes")
            "current_versions": {},
            "templates": {}
        }

    def save_version(
        self,
        artifact_type: str,
        version_hash: str,
        tier_versions: dict[str, tuple[str, str]],  # {tier_name: (template_id, version)}
    ) -> None:
        """
        Save new version entry to registry.

        Args:
            artifact_type: "worker", "research", etc.
            version_hash: 8-char hex hash
            tier_versions: Tier chain with versions
                Example: {
                    "concrete": ("worker.py", "3.1.0"),
                    "tier0": ("tier0_base_artifact", "1.0.0"),
                    "tier1": ("tier1_base_code", "1.1.0"),
                    "tier2": ("tier2_base_python", "2.0.0"),
                    "tier3": ("tier3_base_python_component", "1.2.0"),
                }

        Raises:
            ValueError: If hash collision detected (different tier chain for same hash)
        """
        # Check collision
        if version_hash in self._data["version_hashes"]:
            existing = self._data["version_hashes"][version_hash]
            if existing["artifact_type"] != artifact_type:
                # Collision across artifact types (CRITICAL ERROR)
                raise ValueError(
                    f"Hash collision: {version_hash} used by "
                    f"{existing['artifact_type']} and {artifact_type}"
                )
            # Same artifact type, check if tier chain matches
            existing_tiers = {
                tier: (existing[tier]["template_id"], existing[tier]["version"])
                for tier in ["concrete", "tier0", "tier1", "tier2", "tier3"]
                if tier in existing
            }
            if existing_tiers == tier_versions:
                # Exact match, no-op
                return

            # Collision within artifact type (version changed)
            raise ValueError(
                f"Hash collision: {version_hash} for {artifact_type} "
                f"maps to different tier versions"
            )

        # Save entry (matches YAML schema structure exactly)
        entry: dict[str, Any] = {
            "artifact_type": artifact_type,
            "created": datetime.now(UTC).isoformat(),
            "hash_algorithm": "SHA256",
        }

        # Add tier version entries (concrete, tier0, tier1, tier2, tier3)
        for tier_name, (template_id, version) in tier_versions.items():
            entry[tier_name] = {"template_id": template_id, "version": version}

        self._data["version_hashes"][version_hash] = entry
        self._data["current_versions"][artifact_type] = version_hash
        self._persist()

    def lookup_hash(self, version_hash: str) -> dict[str, Any] | None:
        """
        Lookup tier chain by hash.

        Returns:
            Dict with artifact_type, concrete, tier0-3 entries, created timestamp
            or None if hash not found
        """
        result = self._data["version_hashes"].get(version_hash)
        return cast(dict[str, Any] | None, result)

    def get_current_version(self, artifact_type: str) -> str | None:
        """Get current hash for artifact type."""
        result = self._data["current_versions"].get(artifact_type)
        return cast(str | None, result)

    def get_all_hashes(self) -> list[str]:
        """Get all registered version hashes."""
        return list(self._data["version_hashes"].keys())

    def get_all_artifact_types(self) -> list[str]:
        """Get all artifact types with current versions."""
        return list(self._data["current_versions"].keys())

    def _persist(self) -> None:
        """Write registry to disk."""
        self._data["last_updated"] = datetime.now(UTC).isoformat()

        # Ensure parent directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        with self.registry_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(self._data, f, sort_keys=False)

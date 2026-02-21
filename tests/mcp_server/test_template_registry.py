"""
Tests for Template Registry (Issue #72 Task 3.8).

Covers TemplateRegistry CRUD operations, hash collision detection,
current version tracking, JSON persistence, and YAML→JSON migration.
"""

from __future__ import annotations

from datetime import UTC, datetime

import json

import pytest
import yaml

from mcp_server.scaffolding.template_registry import TemplateRegistry


class TestTemplateRegistryInitialization:
    """Test registry initialization and loading."""

    def test_initialize_new_registry(self, tmp_path):
        """Should create empty registry with correct schema when file doesn't exist."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        assert not registry.get_all_hashes()
        assert not registry.get_all_artifact_types()

    def test_load_existing_registry_json(self, tmp_path):
        """Should load existing registry from disk (JSON)."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        existing_data = {
            "version": "1.0",
            "version_hashes": {
                "abc12345": {
                    "artifact_type": "worker",
                    "created": "2026-01-23T10:00:00",
                    "hash_algorithm": "SHA256",
                    "concrete": {"template_id": "worker.py", "version": "3.1.0"},
                    "tier0": {"template_id": "tier0_base_artifact", "version": "1.0.0"},
                }
            },
            "current_versions": {"worker": "abc12345"},
            "templates": {},
        }

        registry_path.write_text(json.dumps(existing_data, indent=2), encoding="utf-8")

        registry = TemplateRegistry(registry_path)
        entry = registry.lookup_hash("abc12345")
        assert entry is not None
        assert entry["artifact_type"] == "worker"
        assert registry.get_current_version("worker") == "abc12345"

    def test_load_empty_json_file(self, tmp_path):
        """Should handle empty JSON file gracefully."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        registry_path.touch()

        registry = TemplateRegistry(registry_path)
        assert not registry.get_all_hashes()
        assert not registry.get_all_artifact_types()

    def test_load_invalid_json_file(self, tmp_path):
        """Should handle invalid JSON content gracefully."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)

        registry_path.write_text("just a string", encoding="utf-8")

        registry = TemplateRegistry(registry_path)
        assert not registry.get_all_hashes()
        assert not registry.get_all_artifact_types()

    def test_migrate_yaml_to_json_and_delete_yaml(self, tmp_path):
        """Should migrate legacy YAML to JSON on first run and delete YAML."""
        st3_dir = tmp_path / ".st3"
        st3_dir.mkdir(parents=True, exist_ok=True)

        legacy_yaml = st3_dir / "template_registry.yaml"
        target_json = st3_dir / "template_registry.json"

        legacy_data = {
            "version": "1.0",
            "version_hashes": {
                "abc12345": {
                    "artifact_type": "worker",
                    "created": "2026-01-23T10:00:00",
                    "hash_algorithm": "SHA256",
                    "concrete": {"template_id": "worker.py", "version": "3.1.0"},
                }
            },
            "current_versions": {"worker": "abc12345"},
            "templates": {},
        }
        legacy_yaml.write_text(yaml.safe_dump(legacy_data, sort_keys=False), encoding="utf-8")

        registry = TemplateRegistry(target_json)

        entry = registry.lookup_hash("abc12345")
        assert entry is not None
        assert entry["artifact_type"] == "worker"

        assert target_json.exists()
        assert not legacy_yaml.exists()


class TestTemplateRegistrySaveVersion:
    """Test saving version entries to registry."""

    def test_save_new_version(self, tmp_path):
        """Should save new version entry with all tier information."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        tier_versions = {
            "concrete": ("worker.py", "3.1.0"),
            "tier0": ("tier0_base_artifact", "1.0.0"),
            "tier1": ("tier1_base_code", "1.1.0"),
            "tier2": ("tier2_base_python", "2.0.0"),
            "tier3": ("tier3_base_python_component", "1.2.0"),
        }

        registry.save_version("worker", "abc12345", tier_versions)

        assert "abc12345" in registry.get_all_hashes()
        entry = registry.lookup_hash("abc12345")
        assert entry is not None
        assert entry["artifact_type"] == "worker"
        assert entry["hash_algorithm"] == "SHA256"
        assert entry["concrete"]["template_id"] == "worker.py"
        assert entry["concrete"]["version"] == "3.1.0"
        assert entry["tier0"]["template_id"] == "tier0_base_artifact"
        assert entry["tier0"]["version"] == "1.0.0"

        assert registry.get_current_version("worker") == "abc12345"
        assert "worker" in registry.get_all_artifact_types()

        assert registry_path.exists()
        persisted = json.loads(registry_path.read_text(encoding="utf-8"))
        assert persisted["version_hashes"]["abc12345"]["artifact_type"] == "worker"

    def test_save_version_idempotent(self, tmp_path):
        """Should be idempotent when saving identical version."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        tier_versions = {
            "concrete": ("worker.py", "3.1.0"),
            "tier0": ("tier0_base_artifact", "1.0.0"),
        }

        registry.save_version("worker", "abc12345", tier_versions)
        registry.save_version("worker", "abc12345", tier_versions)

        assert registry.get_current_version("worker") == "abc12345"

    def test_save_version_collision_different_artifact_type(self, tmp_path):
        """Should raise ValueError when hash collision across artifact types."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        registry.save_version(
            "worker",
            "abc12345",
            {
                "concrete": ("worker.py", "3.1.0"),
                "tier0": ("tier0_base_artifact", "1.0.0"),
            },
        )

        with pytest.raises(ValueError, match="Hash collision.*used by worker and research"):
            registry.save_version(
                "research",
                "abc12345",
                {
                    "concrete": ("research.py", "2.0.0"),
                    "tier0": ("tier0_base_artifact", "1.0.0"),
                },
            )

    def test_save_version_collision_same_artifact_type_different_tiers(self, tmp_path):
        """Should raise ValueError when hash collision within artifact type."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        registry.save_version(
            "worker",
            "abc12345",
            {
                "concrete": ("worker.py", "3.1.0"),
                "tier0": ("tier0_base_artifact", "1.0.0"),
            },
        )

        with pytest.raises(ValueError, match="Hash collision.*maps to different tier versions"):
            registry.save_version(
                "worker",
                "abc12345",
                {
                    "concrete": ("worker.py", "3.2.0"),
                    "tier0": ("tier0_base_artifact", "1.0.0"),
                },
            )


class TestTemplateRegistryLookup:
    """Test hash lookup operations."""

    def test_lookup_existing_hash(self, tmp_path):
        """Should return tier chain for existing hash."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        tier_versions = {
            "concrete": ("worker.py", "3.1.0"),
            "tier0": ("tier0_base_artifact", "1.0.0"),
            "tier1": ("tier1_base_code", "1.1.0"),
        }

        registry.save_version("worker", "abc12345", tier_versions)

        result = registry.lookup_hash("abc12345")
        assert result is not None
        assert result["artifact_type"] == "worker"
        assert result["concrete"]["template_id"] == "worker.py"
        assert result["tier0"]["template_id"] == "tier0_base_artifact"
        assert result["tier1"]["template_id"] == "tier1_base_code"

    def test_lookup_nonexistent_hash(self, tmp_path):
        """Should return None for non-existent hash."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        result = registry.lookup_hash("nonexistent")
        assert result is None


class TestTemplateRegistryCurrentVersions:
    """Test current version tracking."""

    def test_get_current_version(self, tmp_path):
        """Should return current hash for artifact type."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        registry.save_version(
            "worker",
            "abc12345",
            {
                "concrete": ("worker.py", "3.1.0"),
                "tier0": ("tier0_base_artifact", "1.0.0"),
            },
        )

        assert registry.get_current_version("worker") == "abc12345"

    def test_get_current_version_nonexistent(self, tmp_path):
        """Should return None for non-existent artifact type."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        assert registry.get_current_version("nonexistent") is None

    def test_update_current_version(self, tmp_path):
        """Should update current version when saving new version for same artifact type."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        registry.save_version(
            "worker",
            "abc12345",
            {
                "concrete": ("worker.py", "3.1.0"),
                "tier0": ("tier0_base_artifact", "1.0.0"),
            },
        )

        registry.save_version(
            "worker",
            "def67890",
            {
                "concrete": ("worker.py", "3.2.0"),
                "tier0": ("tier0_base_artifact", "1.0.0"),
            },
        )

        assert registry.get_current_version("worker") == "def67890"

        all_hashes = registry.get_all_hashes()
        assert "abc12345" in all_hashes
        assert "def67890" in all_hashes


class TestTemplateRegistryPersistence:
    """Test registry persistence to disk."""

    def test_persist_creates_parent_directory(self, tmp_path):
        """Should create parent directory if it doesn't exist."""
        registry_path = tmp_path / ".st3" / "nested" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        registry.save_version("worker", "abc12345", {"concrete": ("worker.py", "3.1.0")})

        assert registry_path.exists()
        assert registry_path.parent.exists()

    def test_persist_updates_last_updated(self, tmp_path):
        """Should set last_updated timestamp on persist."""
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry = TemplateRegistry(registry_path)

        before = datetime.now(UTC)
        registry.save_version("worker", "abc12345", {"concrete": ("worker.py", "3.1.0")})
        after = datetime.now(UTC)

        persisted = json.loads(registry_path.read_text(encoding="utf-8"))

        assert "last_updated" in persisted
        last_updated = datetime.fromisoformat(persisted["last_updated"])
        assert before <= last_updated <= after

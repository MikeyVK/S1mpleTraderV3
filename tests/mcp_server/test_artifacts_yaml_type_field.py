# SCAFFOLD: template=generic version=6f1837e9 created=2026-01-26T21:14:02Z
"""
Tests for artifacts.yaml type field (TDD Cycle 1).

RED phase: Validate that all artifacts have type field set to code|doc|config|tracking
per tdd-planning.md Cycle 1 and tracking-type-architecture.md.

@layer: Tests (Unit)
@dependencies: pytest, yaml, mcp_server configuration artifacts
"""

from pathlib import Path
from typing import TypedDict, cast

import pytest
import yaml


class ArtifactTypeEntry(TypedDict, total=False):
    """One artifact entry from artifacts.yaml."""

    type_id: str
    type: str


class ArtifactsYamlData(TypedDict):
    """Subset of artifacts.yaml used by these tests."""

    artifact_types: list[ArtifactTypeEntry]


class TestArtifactsYamlTypeField:
    """Test artifacts.yaml has type field for all artifact_types."""

    @pytest.fixture
    def artifacts_yaml_path(self) -> Path:
        """Path to artifacts.yaml."""
        return Path(__file__).parent.parent.parent / ".st3" / "config" / "artifacts.yaml"

    @pytest.fixture
    def artifacts_data(self, artifacts_yaml_path: Path) -> ArtifactsYamlData:
        """Load artifacts.yaml data."""
        with open(artifacts_yaml_path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f)

        assert isinstance(loaded, dict)
        artifact_types = loaded.get("artifact_types")
        assert isinstance(artifact_types, list)
        assert all(isinstance(item, dict) for item in artifact_types)

        return {"artifact_types": cast(list[ArtifactTypeEntry], artifact_types)}

    def test_all_artifacts_have_type_field(self, artifacts_data: ArtifactsYamlData) -> None:
        """All artifacts must have type field set to code|doc|config|tracking."""
        artifact_types = artifacts_data.get("artifact_types", [])
        assert len(artifact_types) > 0, "artifacts.yaml must have artifact_types"

        valid_types = ["code", "doc", "config", "tracking"]

        for artifact in artifact_types:
            type_id = artifact.get("type_id", "unknown")
            assert "type" in artifact, f"Artifact {type_id} missing 'type' field"
            assert artifact["type"] in valid_types, (
                f"Artifact {type_id} has invalid type: {artifact['type']} (expected: {valid_types})"
            )

    def test_design_artifact_has_doc_type(self, artifacts_data: ArtifactsYamlData) -> None:
        """Design artifact must have type: doc."""
        artifact_types = artifacts_data.get("artifact_types", [])
        design = next((a for a in artifact_types if a.get("type_id") == "design"), None)
        assert design is not None, "Design artifact not found in artifacts.yaml"
        assert design.get("type") == "doc", f"Design artifact has wrong type: {design.get('type')}"

    def test_code_artifacts_have_code_type(self, artifacts_data: ArtifactsYamlData) -> None:
        """DTO, worker, adapter, tool, resource must have type: code."""
        artifact_types = artifacts_data.get("artifact_types", [])
        code_type_ids = ["dto", "worker", "adapter", "tool", "resource"]

        for type_id in code_type_ids:
            artifact = next((a for a in artifact_types if a.get("type_id") == type_id), None)
            if artifact:  # Only check if exists
                assert artifact.get("type") == "code", (
                    f"Artifact {type_id} has wrong type: {artifact.get('type')}"
                )

    def test_document_artifacts_have_doc_type(self, artifacts_data: ArtifactsYamlData) -> None:
        """Research, planning, design, architecture, tracking, reference must have type: doc."""
        artifact_types = artifacts_data.get("artifact_types", [])
        doc_type_ids = ["research", "planning", "design", "architecture", "tracking", "reference"]

        for type_id in doc_type_ids:
            artifact = next((a for a in artifact_types if a.get("type_id") == type_id), None)
            if artifact:  # Only check if exists
                assert artifact.get("type") == "doc", (
                    f"Artifact {type_id} has wrong type: {artifact.get('type')}"
                )

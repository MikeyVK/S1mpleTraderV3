# SCAFFOLD: template=generic version=6f1837e9 created=2026-01-26T21:14:02Z
"""
Tests for artifacts.yaml type field (TDD Cycle 1).

RED phase: Validate that all artifacts have type field set to code|doc|config|tracking
per tdd-planning.md Cycle 1 and tracking-type-architecture.md.
"""

from pathlib import Path

import pytest
import yaml


class TestArtifactsYamlTypeField:
    """Test artifacts.yaml has type field for all artifact_types."""

    @pytest.fixture
    def artifacts_yaml_path(self):
        """Path to artifacts.yaml."""
        return Path(__file__).parent.parent / ".st3" / "artifacts.yaml"

    @pytest.fixture
    def artifacts_data(self, artifacts_yaml_path):
        """Load artifacts.yaml data."""
        with open(artifacts_yaml_path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    def test_all_artifacts_have_type_field(self, artifacts_data):
        """All artifacts must have type field set to code|doc|config|tracking."""
        artifact_types = artifacts_data.get("artifact_types", [])
        assert len(artifact_types) > 0, "artifacts.yaml must have artifact_types"

        valid_types = ["code", "doc", "config", "tracking"]

        for artifact in artifact_types:
            type_id = artifact.get("type_id", "unknown")
            assert "type" in artifact, f"Artifact {type_id} missing 'type' field"
            assert artifact["type"] in valid_types, \
                f"Artifact {type_id} has invalid type: {artifact['type']} (expected: {valid_types})"

    def test_design_artifact_has_doc_type(self, artifacts_data):
        """Design artifact must have type: doc."""
        artifact_types = artifacts_data.get("artifact_types", [])
        design = next((a for a in artifact_types if a.get("type_id") == "design"), None)
        assert design is not None, "Design artifact not found in artifacts.yaml"
        assert design["type"] == "doc", f"Design artifact has wrong type: {design.get('type')}"

    def test_code_artifacts_have_code_type(self, artifacts_data):
        """DTO, worker, adapter, tool, resource must have type: code."""
        artifact_types = artifacts_data.get("artifact_types", [])
        code_type_ids = ["dto", "worker", "adapter", "tool", "resource"]

        for type_id in code_type_ids:
            artifact = next((a for a in artifact_types if a.get("type_id") == type_id), None)
            if artifact:  # Only check if exists
                assert artifact.get("type") == "code", \
                    f"Artifact {type_id} has wrong type: {artifact.get('type')}"

    def test_document_artifacts_have_doc_type(self, artifacts_data):
        """Research, planning, design, architecture, tracking, reference must have type: doc."""
        artifact_types = artifacts_data.get("artifact_types", [])
        doc_type_ids = ["research", "planning", "design", "architecture", "tracking", "reference"]

        for type_id in doc_type_ids:
            artifact = next((a for a in artifact_types if a.get("type_id") == type_id), None)
            if artifact:  # Only check if exists
                assert artifact.get("type") == "doc", \
                    f"Artifact {type_id} has wrong type: {artifact.get('type')}"

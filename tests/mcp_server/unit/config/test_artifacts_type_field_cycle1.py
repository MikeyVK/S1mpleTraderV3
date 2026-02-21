"""Unit tests for artifacts.yaml type field (Issue #72, TDD Cycle 1).

RED Phase Test:
- Validates ALL artifacts in .st3/artifacts.yaml have type field (code|doc|config)
- Validates code artifacts (dto, worker, adapter, tool, resource, etc.) have type: code
- Validates document artifacts (research, planning, design, etc.) have type: doc

Author: AI Agent
Created: 2026-01-26
Issue: #72 (Template Library Management)
TDD Cycle: 1
"""

from pathlib import Path

import pytest

from mcp_server.config.artifact_registry_config import (
    ArtifactRegistryConfig,
    ArtifactType,
)


@pytest.fixture
def artifacts_config() -> ArtifactRegistryConfig:
    """Load config from actual .st3/artifacts.yaml."""
    # Find project root (.st3 directory exists there)
    current_dir = Path(__file__).resolve()
    project_root = current_dir
    while not (project_root / ".st3").exists():
        project_root = project_root.parent
        if project_root == project_root.parent:
            raise FileNotFoundError("Could not find .st3 directory")

    artifacts_yaml = project_root / ".st3" / "artifacts.yaml"
    return ArtifactRegistryConfig.from_file(artifacts_yaml)


class TestArtifactsTypeField:
    """Test type field validation for all artifacts (Issue #72, Cycle 1)."""

    def test_all_artifacts_have_type_field(self, artifacts_config: ArtifactRegistryConfig) -> None:
        """All artifacts must have type field (code|doc|config)."""
        # RED: Every artifact must have a type field
        for artifact in artifacts_config.artifact_types:
            assert hasattr(artifact, "type"), f"Artifact {artifact.type_id} missing 'type' field"
            assert artifact.type in [
                ArtifactType.CODE,
                ArtifactType.DOC,
                ArtifactType.TRACKING,
            ], (
                f"Artifact {artifact.type_id} has invalid type: "
                f"{artifact.type} (expected CODE|DOC|TRACKING)"
            )

    def test_code_artifacts_have_correct_type(
        self, artifacts_config: ArtifactRegistryConfig
    ) -> None:
        """Code artifacts must have type: code."""
        # RED: Assert all known code artifacts have type=CODE
        code_type_ids = [
            "dto",
            "worker",
            "adapter",
            "tool",
            "resource",
            "interface",
            "schema",
            "service",
        ]
        for type_id in code_type_ids:
            artifact = artifacts_config.get_artifact(type_id)
            if artifact:  # Skip if artifact doesn't exist yet
                assert artifact.type == ArtifactType.CODE, (
                    f"Code artifact '{type_id}' MUST have type=CODE, got {artifact.type}"
                )

    def test_document_artifacts_have_correct_type(
        self, artifacts_config: ArtifactRegistryConfig
    ) -> None:
        """Document artifacts must have type: doc."""
        # RED: Assert all known document artifacts have type=DOC
        doc_type_ids = [
            "research",
            "planning",
            "design",
            "architecture",
            "tracking",
            "reference",
        ]
        for type_id in doc_type_ids:
            artifact = artifacts_config.get_artifact(type_id)
            if artifact:  # Skip if artifact doesn't exist yet
                assert artifact.type == ArtifactType.DOC, (
                    f"Document artifact '{type_id}' MUST have type=DOC, got {artifact.type}"
                )

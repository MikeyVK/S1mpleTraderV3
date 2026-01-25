"""
Unit tests for ArtifactDefinition - version field removal (Task 1.5b).

RED phase: Documents that version field should NOT exist in ArtifactDefinition.
Rationale: artifacts.yaml = selection config (variants), registry = provenance (versions).
Having ArtifactDefinition.version conflicts with "templates+registry=SSOT" principle.
"""

import pytest
from pydantic import ValidationError

from mcp_server.config.artifact_registry_config import ArtifactDefinition


class TestArtifactDefinitionNoVersion:
    """Test that version field is removed from ArtifactDefinition (Task 1.5b)."""

    def test_artifact_definition_has_no_version_field(self):
        """ArtifactDefinition should NOT have version field.
        
        REQUIREMENT (Task 1.5b): artifacts.yaml is selection config (which template),
        NOT version source (that's registry.yaml). Version field creates conceptual conflict.
        """
        # Create minimal valid artifact definition
        artifact_data = {
            "type": "code",
            "type_id": "dto",
            "name": "Data Transfer Object",
            "description": "Pydantic DTO",
            "file_extension": ".py",
            "state_machine": {
                "initial_state": "draft",
                "states": ["draft", "final"],
                "valid_transitions": []
            }
        }
        
        # After Task 1.5b, this should work without version
        artifact = ArtifactDefinition(**artifact_data)
        
        # REQUIREMENT: version should NOT be a field
        # Currently FAILS because version exists with default "1.0"
        # After Task 1.5b fix:
        assert not hasattr(artifact, 'version')
        
    def test_artifact_yaml_without_version_is_valid(self):
        """artifacts.yaml entries should NOT require version field.
        
        REQUIREMENT: Version comes from template registry, not artifacts.yaml.
        """
        # Simulate parsing artifacts.yaml entry without version
        yaml_entry = {
            "type": "code",
            "type_id": "worker",
            "name": "Worker",
            "description": "Async worker",
            "file_extension": ".py",
            "state_machine": {
                "initial_state": "draft",
                "states": ["draft", "final"],
                "valid_transitions": []
            }
        }
        
        # Should parse without version field
        artifact = ArtifactDefinition(**yaml_entry)
        
        # REQUIREMENT: No version attribute
        # Currently FAILS - gets default "1.0"
        # After Task 1.5b fix:
        assert not hasattr(artifact, 'version')


class TestArtifactManagerNoVersionContext:
    """Test that template_version is NOT injected into context (Task 1.5b)."""
    
    def test_scaffold_context_has_no_template_version(self):
        """scaffold_artifact() should NOT inject template_version into context.
        
        REQUIREMENT (Task 1.5b): Version comes from registry hash lookup, not artifact config.
        Context should have artifact_type, version_hash, timestamp (from Task 1.1c),
        but NOT template_version.
        """
        # This test documents current wrong behavior
        # After Task 1.5b: Remove template_version context injection from artifact_manager.py
        
        # Currently CANNOT test without full integration
        # After Task 1.5b fix, add integration test checking scaffolder.scaffold() context
        pass

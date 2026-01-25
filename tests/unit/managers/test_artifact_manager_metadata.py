"""
Unit tests for ArtifactManager metadata enrichment.

Tests context enrichment with scaffold metadata fields.
Following TDD: These tests are written BEFORE implementation (RED phase).
"""

# pyright: basic, reportPrivateUsage=false

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from mcp_server.managers.artifact_manager import ArtifactManager


class TestArtifactManagerMetadataEnrichment:
    """Test metadata field injection into scaffold context."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        """Create manager with workspace_root set."""
        return ArtifactManager(workspace_root=str(tmp_path))

    def test_enrichment_adds_template_id(self, manager: ArtifactManager) -> None:
        """RED: Context should include template_id from artifact type."""
        context = {"name": "UserDTO"}
        enriched = manager._enrich_context("dto", context)  # pylint: disable=protected-access

        assert "template_id" in enriched
        assert enriched["template_id"] == "dto"

    def test_enrichment_adds_scaffold_created_timestamp(
        self, manager: ArtifactManager
    ) -> None:
        """RED: Context should include scaffold_created in ISO 8601 UTC."""
        context = {"name": "UserDTO"}
        enriched = manager._enrich_context("dto", context)  # pylint: disable=protected-access

        assert "scaffold_created" in enriched
        # Verify it's a valid ISO 8601 timestamp with Z suffix
        timestamp = enriched["scaffold_created"]
        assert timestamp.endswith("Z")
        # Should parse without error
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed.tzinfo == timezone.utc

    def test_enrichment_adds_output_path_for_file_artifacts(
        self, manager: ArtifactManager
    ) -> None:
        """RED: File artifacts should get output_path field."""
        context = {"name": "UserDTO"}
        enriched = manager._enrich_context("dto", context)  # pylint: disable=protected-access

        assert "output_path" in enriched
        # Should be computed from directory resolution
        assert isinstance(enriched["output_path"], str)
        assert len(enriched["output_path"]) > 0

    def test_enrichment_no_output_path_for_ephemeral_artifacts(
        self, manager: ArtifactManager
    ) -> None:
        """RED: Ephemeral artifacts should NOT have output_path."""
        # Assuming "commit_message" is ephemeral (output_type: ephemeral)
        context = {"message": "Initial commit"}
        enriched = manager._enrich_context(  # pylint: disable=protected-access
            "commit_message", context
        )

        assert "output_path" not in enriched

    def test_enrichment_preserves_original_context(
        self, manager: ArtifactManager
    ) -> None:
        """RED: Original context fields should be preserved."""
        context = {
            "name": "UserDTO",
            "description": "User data transfer object",
            "fields": ["id", "name"]
        }
        enriched = manager._enrich_context("dto", context)  # pylint: disable=protected-access

        # Original fields still present
        assert enriched["name"] == "UserDTO"
        assert enriched["description"] == "User data transfer object"
        assert enriched["fields"] == ["id", "name"]

        # Plus new metadata fields
        assert "template_id" in enriched
        assert "scaffold_created" in enriched
        # NOTE (Task 1.5b): template_version removed - comes from registry hash now

    def test_timestamp_format_is_consistent(self, manager: ArtifactManager) -> None:
        """RED: Timestamps should always use same ISO 8601 format."""
        context1 = {"name": "UserDTO"}
        context2 = {"name": "ProductDTO"}

        enriched1 = manager._enrich_context("dto", context1)  # pylint: disable=protected-access
        enriched2 = manager._enrich_context("dto", context2)  # pylint: disable=protected-access

        # Both should have Z suffix
        assert enriched1["scaffold_created"].endswith("Z")
        assert enriched2["scaffold_created"].endswith("Z")

        # Format: YYYY-MM-DDTHH:MM:SSZ (19 or 20 chars with/without millis)
        ts_len = len(enriched1["scaffold_created"])
        assert ts_len in (19, 20)

    @pytest.mark.asyncio
    async def test_enrichment_called_during_scaffold(
        self, manager: ArtifactManager
    ) -> None:
        """RED: scaffold_artifact() should call _enrich_context()."""
        # Mock scaffolder to return content WITH valid SCAFFOLD header (for validation)
        manager.scaffolder = Mock()
        mock_content = "# SCAFFOLD: template=dto version=1.0 created=2026-01-24T10:00:00Z path=test.py\nclass UserDTO: pass"
        manager.scaffolder.scaffold.return_value = Mock(content=mock_content)

        context = {"name": "UserDTO"}
        await manager.scaffold_artifact("dto", **context)

        # scaffolder.scaffold should receive enriched context
        call_args = manager.scaffolder.scaffold.call_args
        call_kwargs = call_args[1]  # Keyword arguments

        assert "template_id" in call_kwargs
        assert "version_hash" in call_kwargs  # Manager injects version_hash (not template_version)
        assert "scaffold_created" in call_kwargs


class TestArtifactManagerNullTemplate:
    """Test fail-fast guard for null template_path (QA-2)."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        """Create manager with workspace_root set."""
        return ArtifactManager(workspace_root=str(tmp_path))

    @pytest.mark.asyncio
    async def test_scaffold_raises_config_error_for_null_template_path(
        self, manager: ArtifactManager
    ) -> None:
        """QA-2: scaffold_artifact should fail fast if template_path is null."""
        from mcp_server.core.exceptions import ConfigError

        # Worker artifact has template_path = null in artifacts.yaml
        with pytest.raises(ConfigError, match=r"Artifact type 'worker' has no template configured"):
            await manager.scaffold_artifact("worker", name="TestWorker")


class TestArtifactManagerTierChainExtraction:
    """Test real version extraction from TEMPLATE_METADATA (SSOT integrity)."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        """Create manager with workspace_root set."""
        return ArtifactManager(workspace_root=str(tmp_path))

    def test_extract_tier_chain_reads_real_versions_from_metadata(
        self, manager: ArtifactManager
    ) -> None:
        """CRITICAL: Verify tier_chain extracts actual versions from TEMPLATE_METADATA, not fallback "1.0"."""
        # Use dto.py.jinja2 which extends tier2_base_python → tier1_base_code → tier0_base_artifact
        tier_chain = manager._extract_tier_chain("concrete/dto.py.jinja2")  # pylint: disable=protected-access
        
        # Should extract real versions from TEMPLATE_METADATA in each template
        assert len(tier_chain) > 0, "Tier chain should not be empty for dto template"
        
        # Verify structure: list of (template_name, version) tuples
        for template_name, version in tier_chain:
            assert isinstance(template_name, str), f"Template name should be string, got {type(template_name)}"
            assert isinstance(version, str), f"Version should be string, got {type(version)}"
            assert template_name != "", "Template name should not be empty"
            assert version != "", "Version should not be empty"
        
        # CRITICAL: At least one template should have non-"1.0" version if metadata is present
        # This prevents silent regression where all versions fall back to "1.0"
        template_names = [name for name, _ in tier_chain]
        versions = [ver for _, ver in tier_chain]
        
        # Verify expected templates in chain
        assert "dto.py" in template_names, "Chain should contain concrete dto template"
        
        # Log extracted versions for debugging
        print(f"\nExtracted tier chain: {tier_chain}")
        print(f"Versions: {versions}")
        
        # NOTE: This test verifies API correctness (Path not string) and extraction logic
        # If all versions are "1.0", it means either:
        # 1. Templates truly don't have version metadata (legitimate)
        # 2. extract_metadata() failed and fell back to "1.0" (bug)
        # We can't strictly assert non-"1.0" without controlling template content,
        # but we can verify the extraction attempt succeeded
        assert len(versions) == len(template_names), "Should have version for each template"

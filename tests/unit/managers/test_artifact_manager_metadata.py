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

    def test_enrichment_adds_template_version(self, manager: ArtifactManager) -> None:
        """RED: Context should include template_version from artifacts.yaml."""
        context = {"name": "UserDTO"}
        enriched = manager._enrich_context("dto", context)  # pylint: disable=protected-access

        assert "template_version" in enriched
        assert enriched["template_version"] == "1.0"

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
        assert "template_version" in enriched
        assert "scaffold_created" in enriched

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
        # Mock scaffolder to avoid template rendering
        manager.scaffolder = Mock()
        manager.scaffolder.scaffold.return_value = Mock(content="# Generated content")

        context = {"name": "UserDTO"}
        await manager.scaffold_artifact("dto", **context)

        # scaffolder.scaffold should receive enriched context
        call_args = manager.scaffolder.scaffold.call_args
        call_kwargs = call_args[1]  # Keyword arguments

        assert "template_id" in call_kwargs
        assert "template_version" in call_kwargs
        assert "scaffold_created" in call_kwargs

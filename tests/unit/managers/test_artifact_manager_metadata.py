"""Unit tests for ArtifactManager metadata enrichment via public API."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from mcp_server.core.exceptions import ConfigError
from mcp_server.managers.artifact_manager import ArtifactManager


class TestArtifactManagerMetadataEnrichment:
    """Test metadata field injection via public API."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        """Create manager with mocked collaborators."""
        manager = ArtifactManager(workspace_root=str(tmp_path))
        # Mock scaffolder to capture enriched context
        manager.scaffolder = Mock()
        header = "# SCAFFOLD: dto:abc123 | 2026-01-24T10:00:00Z | test.py"
        manager.scaffolder.scaffold.return_value = Mock(
            content=f"{header}\nclass Test: pass",
            file_name="test.py"
        )
        # Mock validation to avoid file I/O
        manager.validation_service = Mock()
        manager.validation_service.validate = AsyncMock(return_value=(True, []))
        return manager

    @pytest.mark.asyncio
    async def test_enrichment_adds_template_id(self, manager: ArtifactManager) -> None:
        """Context should include template_id from artifact type."""
        await manager.scaffold_artifact("dto", name="UserDTO")

        call_kwargs = manager.scaffolder.scaffold.call_args[1]
        assert "template_id" in call_kwargs
        assert call_kwargs["template_id"] == "dto"

    @pytest.mark.asyncio
    async def test_enrichment_adds_scaffold_created_timestamp(
        self, manager: ArtifactManager
    ) -> None:
        """Context should include scaffold_created in ISO 8601 UTC."""
        await manager.scaffold_artifact("dto", name="UserDTO")

        call_kwargs = manager.scaffolder.scaffold.call_args[1]
        assert "scaffold_created" in call_kwargs
        timestamp = call_kwargs["scaffold_created"]
        assert timestamp.endswith("Z")
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert parsed.tzinfo == timezone.utc

    @pytest.mark.asyncio
    async def test_enrichment_adds_output_path_for_file_artifacts(
        self, manager: ArtifactManager
    ) -> None:
        """File artifacts should get output_path field."""
        await manager.scaffold_artifact("dto", name="UserDTO")

        call_kwargs = manager.scaffolder.scaffold.call_args[1]
        assert "output_path" in call_kwargs
        assert isinstance(call_kwargs["output_path"], str)
        assert len(call_kwargs["output_path"]) > 0

    @pytest.mark.asyncio
    async def test_enrichment_preserves_original_context(
        self, manager: ArtifactManager
    ) -> None:
        """Original context fields should be preserved."""
        await manager.scaffold_artifact(
            "dto",
            name="UserDTO",
            description="User data transfer object",
            fields=["id", "name"]
        )

        call_kwargs = manager.scaffolder.scaffold.call_args[1]
        assert call_kwargs["name"] == "UserDTO"
        assert call_kwargs["description"] == "User data transfer object"
        assert call_kwargs["fields"] == ["id", "name"]
        assert "template_id" in call_kwargs
        assert "scaffold_created" in call_kwargs

    @pytest.mark.asyncio
    async def test_timestamp_format_is_consistent(
        self, manager: ArtifactManager
    ) -> None:
        """Timestamps should always use same ISO 8601 format."""
        await manager.scaffold_artifact("dto", name="UserDTO")
        enriched1 = manager.scaffolder.scaffold.call_args[1]

        await manager.scaffold_artifact("dto", name="ProductDTO")
        enriched2 = manager.scaffolder.scaffold.call_args[1]

        assert enriched1["scaffold_created"].endswith("Z")
        assert enriched2["scaffold_created"].endswith("Z")
        ts_len = len(enriched1["scaffold_created"])
        assert ts_len in (19, 20)

    @pytest.mark.asyncio
    async def test_enrichment_includes_version_hash(
        self, manager: ArtifactManager
    ) -> None:
        """scaffold_artifact() should inject version_hash into context."""
        await manager.scaffold_artifact("dto", name="UserDTO")

        call_kwargs = manager.scaffolder.scaffold.call_args[1]
        assert "template_id" in call_kwargs
        assert "version_hash" in call_kwargs
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
        # Worker artifact has template_path = null in artifacts.yaml
        expected_msg = r"Artifact type 'worker' has no template configured"
        with pytest.raises(ConfigError, match=expected_msg):
            await manager.scaffold_artifact("worker", name="TestWorker")


class TestArtifactManagerTierChainExtraction:
    """Test version extraction from TEMPLATE_METADATA via scaffold behavior."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        """Create manager with mocked collaborators."""
        manager = ArtifactManager(workspace_root=str(tmp_path))
        # Mock scaffolder to capture version_hash computation
        manager.scaffolder = Mock()
        header = "# SCAFFOLD: dto:abc123 | 2026-01-24T10:00:00Z | test.py"
        manager.scaffolder.scaffold.return_value = Mock(
            content=f"{header}\nclass Test: pass",
            file_name="test.py"
        )
        # Mock validation to avoid file I/O
        manager.validation_service = Mock()
        manager.validation_service.validate = AsyncMock(return_value=(True, []))
        return manager

    @pytest.mark.asyncio
    async def test_scaffold_computes_version_hash_from_tier_chain(
        self, manager: ArtifactManager
    ) -> None:
        """Scaffold should compute version_hash from template tier chain."""
        await manager.scaffold_artifact("dto", name="UserDTO")

        call_kwargs = manager.scaffolder.scaffold.call_args[1]
        # version_hash should be present (computed from tier chain)
        assert "version_hash" in call_kwargs
        assert isinstance(call_kwargs["version_hash"], str)
        assert len(call_kwargs["version_hash"]) > 0

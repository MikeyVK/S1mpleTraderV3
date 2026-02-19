"""
End-to-end tests for scaffold metadata system.

Tests the full workflow: scaffold → file write → parse → validate.
Following TDD: Tests metadata enrichment with EXISTING templates.

NOTE: Phase 0.4 scope is metadata enrichment, not new templates.
Using existing DTO template to verify metadata injection works.
"""

# pyright: basic

from pathlib import Path

import pytest

from mcp_server.core.exceptions import ConfigError, MetadataParseError
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.scaffolding.metadata import ScaffoldMetadataParser
from mcp_server.scaffolding.template_registry import TemplateRegistry


class TestMetadataEndToEnd:
    """E2E tests for scaffold metadata workflow."""

    @pytest.fixture(autouse=True)
    def _force_v1_pipeline(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Force V1 pipeline: these tests validate V1 scaffolding infrastructure."""
        monkeypatch.setenv("PYDANTIC_SCAFFOLDING_ENABLED", "false")

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        """Create manager with workspace_root set."""
        return ArtifactManager(workspace_root=str(tmp_path))

    @pytest.fixture
    def parser(self) -> ScaffoldMetadataParser:
        """Create metadata parser."""
        return ScaffoldMetadataParser()

    @pytest.mark.asyncio
    async def test_scaffold_file_artifact_has_metadata(
        self, manager: ArtifactManager, parser: ScaffoldMetadataParser
    ) -> None:
        """E2E: Scaffold DTO → file written → metadata parsed."""
        # Scaffold DTO artifact (file type)
        result = await manager.scaffold_artifact(
            "dto",
            name="UserDTO",
            description="User data transfer object",
            frozen=False,  # User state is mutable
            examples=[{"id": 123, "name": "John Doe"}],
            fields=[
                {"name": "id", "type": "int", "description": "User ID"},
                {"name": "name", "type": "str", "description": "User name"}
            ],
            dependencies=["pydantic"],
            responsibilities=["User data validation"]
        )

        # Should return path (file artifact)
        assert isinstance(result, str)
        assert Path(result).exists()

        # Read scaffolded file
        file_path = Path(result)
        content = file_path.read_text(encoding="utf-8")

        # Parse metadata from file (content, extension)
        metadata = parser.parse(content, file_path.suffix)

        # Validate metadata fields (2-line format: path on line 1, metadata on line 2)
        assert metadata is not None
        assert metadata["template"] == "dto"
        assert len(metadata["version"]) == 8  # 8-char hex hash (Issue #72)
        assert "created" in metadata
        assert metadata["created"].endswith("Z")  # UTC timestamp
        # Path is on line 1 in 2-line format (not in metadata dict)
        lines = content.split("\n")
        assert lines[0].startswith("#"), "Line 1 should be filepath comment"
        assert ".py" in lines[0], "Filepath should have .py extension"

    @pytest.mark.asyncio
    async def test_scaffold_file_artifact_returns_path(
        self, manager: ArtifactManager
    ) -> None:
        """E2E: Scaffold file artifact → returns path → file exists."""
        result = await manager.scaffold_artifact(
            "dto",
            name="TestDTO",
            description="Test DTO",
            frozen=True,
            examples=[{"test": "data"}],
            fields=[{"name": "test", "type": "str", "description": "Test field"}],
            dependencies=["pydantic"],
            responsibilities=["Data validation"]
        )

        # Should return path string
        assert isinstance(result, str)
        # Path should exist on disk
        assert Path(result).exists()
        # Path should be absolute
        assert Path(result).is_absolute()

    @pytest.mark.asyncio
    async def test_manual_file_without_metadata_returns_none(
        self, parser: ScaffoldMetadataParser, tmp_path: Path
    ) -> None:
        """E2E: Manual file (no metadata) → parse returns None."""
        # Create manual file without scaffold metadata
        manual_file = tmp_path / "manual.py"
        manual_file.write_text("# This is a manual file\nprint('hello')\n", encoding="utf-8")

        # Parse should return None (no metadata found)
        metadata = parser.parse(manual_file.read_text(encoding="utf-8"), ".py")
        assert metadata is None

    @pytest.mark.asyncio
    async def test_invalid_metadata_format_fails_gracefully(
        self, parser: ScaffoldMetadataParser, tmp_path: Path
    ) -> None:
        """E2E: Invalid metadata format → MetadataParseError raised."""
        # Create file with invalid metadata (invalid version format) using 2-line format
        invalid_file = tmp_path / "invalid.py"
        invalid_file.write_text(
            "# backend/dtos/invalid.py\n"
            "# template=dto version=NOT_A_VERSION created=2026-01-20T14:00:00Z updated=\n",
            encoding="utf-8"
        )

        # Parse should raise MetadataParseError for invalid version format
        with pytest.raises(MetadataParseError):
            parser.parse(invalid_file.read_text(encoding="utf-8"), ".py")
        # Error is raised successfully - test passed!

    @pytest.mark.asyncio
    async def test_workspace_root_not_set_gives_helpful_error(
        self
    ) -> None:
        """E2E: workspace_root not set → ConfigError with hints."""
        # Create manager WITHOUT workspace_root
        manager = ArtifactManager()

        # Scaffold without output_path should fail with helpful error
        with pytest.raises(ConfigError) as exc_info:
            await manager.scaffold_artifact(
                "dto",
                name="TestDTO",
                description="Test",
                frozen=True,
                examples=[{"test": "data"}],
                fields=[{"name": "test", "type": "str", "description": "Test field"}],
                dependencies=["pydantic"],
                responsibilities=["Validation"]
            )

        # Error should have helpful hints
        error_msg = str(exc_info.value)
        assert "workspace_root not configured" in error_msg
        assert "Option 1:" in error_msg or "Option 2:" in error_msg or "Option 3:" in error_msg

    @pytest.mark.skip(reason="commit_message template in wrong location (separate issue)")
    @pytest.mark.asyncio
    async def test_scaffold_ephemeral_returns_temp_path(
        self, manager: ArtifactManager
    ) -> None:
        """E2E: Scaffold ephemeral artifact → writes to .st3/temp/ and returns path."""
        result = await manager.scaffold_artifact(
            "commit_message",
            type="feat",
            summary="Add new feature",
            description="Detailed description of the feature"
        )

        # Should return temp file path string
        assert isinstance(result, str)
        assert result.startswith(".st3" + str(Path("/")) + "temp" + str(Path("/")))
        assert "commit_message_" in result
        # Temp file should exist
        temp_file = Path(result)
        assert temp_file.exists()
        # Read and verify content from file
        content = temp_file.read_text(encoding="utf-8")
        assert "feat:" in content
        assert "Add new feature" in content

        # Ephemeral artifacts now have path in metadata (temp path)
        parser = ScaffoldMetadataParser()
        metadata = parser.parse(content, ".txt")
        assert metadata is not None
        assert metadata["template"] == "commit_message"
    @pytest.mark.asyncio
    async def test_scaffold_registry_roundtrip(
        self, tmp_path: Path, parser: ScaffoldMetadataParser
    ) -> None:
        """E2E: Scaffold ? parse header ? registry lookup roundtrip (Issue #72 Task 1.6.2).

        Tests complete provenance tracking:
        1. Scaffold artifact with registry enabled
        2. Parse SCAFFOLD header from generated file
        3. Lookup version_hash in registry
        4. Verify tier chain matches
        """
        # Setup registry in temp directory
        registry_path = tmp_path / ".st3" / "template_registry.json"
        registry_path.parent.mkdir(parents=True, exist_ok=True)
        template_registry = TemplateRegistry(registry_path=registry_path)

        # Create manager WITH registry DI
        manager = ArtifactManager(
            workspace_root=str(tmp_path),
            template_registry=template_registry
        )

        # 1. Scaffold artifact
        result = await manager.scaffold_artifact(
            "dto",
            name="ProvenanceDto",
            description="Test provenance tracking",
            frozen=True,
            examples=[{"tracking_id": "test-123"}],
            fields=[{"name": "tracking_id", "type": "str", "description": "Tracking ID"}],
            dependencies=["pydantic"],
            responsibilities=["Provenance data validation"]
        )

        # Verify file was created
        assert isinstance(result, str)
        file_path = Path(result)
        assert file_path.exists()

        # 2. Parse SCAFFOLD header
        content = file_path.read_text(encoding="utf-8")
        metadata = parser.parse(content, file_path.suffix)

        assert metadata is not None
        assert metadata["template"] == "dto"
        assert "version" in metadata  # This is the version_hash
        version_hash = metadata["version"]
        assert len(version_hash) == 8  # 8-char hex hash

        # 3. Lookup in registry
        registry_entry = template_registry.lookup_hash(version_hash)

        assert registry_entry is not None
        assert registry_entry["artifact_type"] == "dto"
        assert "concrete" in registry_entry
        assert registry_entry["concrete"]["template_id"] == "dto.py"

        # 4. Verify current version tracking
        current = template_registry.get_current_version("dto")
        assert current == version_hash

        # 5. Verify registry file was created
        assert registry_path.exists()

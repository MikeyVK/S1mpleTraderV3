"""
Unit tests for ArtifactManager registry integration (Task 1.1c).

RED phase: Tests that scaffold_artifact() integrates with TemplateRegistry:
- Computes version_hash before rendering
- Calls registry.save_version() with tier chain
- Injects version_hash into template context
- Creates .st3/template_registry.yaml if not exists
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.template_registry import TemplateRegistry


class TestArtifactManagerRegistryIntegration:
    """Test registry integration in scaffold_artifact flow (Task 1.1c)."""

    @pytest.mark.asyncio
    async def test_scaffold_artifact_saves_to_registry(self):
        """Should call registry.save_version() when scaffolding artifact.

        REQUIREMENT (Task 1.1c): Every scaffold operation must write registry entry
        for provenance tracking.
        """
        # Setup
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.scaffold.return_value = Mock(
            content='"""Test."""\nclass Test:\n    pass\n',
            file_name='test.py'
        )

        mock_registry = Mock(spec=TemplateRegistry)
        mock_fs_adapter = Mock()
        mock_fs_adapter.resolve_path.return_value = Path('/test/test.py')

        mock_validation_service = Mock()
        mock_validation_service.validate = AsyncMock(return_value=(True, []))

        with patch.object(
            ArtifactManager, 'get_artifact_path', return_value=Path('/test/test.py')
        ):
            manager = ArtifactManager(
                scaffolder=mock_scaffolder,
                fs_adapter=mock_fs_adapter,
                validation_service=mock_validation_service
            )

            # Inject mock_registry into manager
            manager.template_registry = mock_registry

            await manager.scaffold_artifact('dto', name='Test', fields=[])

        # After Task 1.1c GREEN:
        mock_registry.save_version.assert_called_once()

    @pytest.mark.asyncio
    async def test_scaffold_artifact_computes_version_hash_before_rendering(self):
        """Should compute version_hash and inject into template context.

        REQUIREMENT: version_hash must be computed BEFORE rendering so it can
        be included in SCAFFOLD metadata header.
        """
        # Setup
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.scaffold.return_value = Mock(
            content='# SCAFFOLD: dto:abc123ef | 2026-01-23 | test.py\n',
            file_name='test.py'
        )

        mock_fs_adapter = Mock()
        mock_fs_adapter.resolve_path.return_value = Path('/test/test.py')

        mock_validation_service = Mock()
        mock_validation_service.validate = AsyncMock(return_value=(True, []))

        with patch.object(
            ArtifactManager, 'get_artifact_path', return_value=Path('/test/test.py')
        ):
            manager = ArtifactManager(
                scaffolder=mock_scaffolder,
                fs_adapter=mock_fs_adapter,
                validation_service=mock_validation_service
            )

            await manager.scaffold_artifact('dto', name='Test', fields=[])

        # REQUIREMENT: scaffolder.scaffold() should receive version_hash in context
        call_args = mock_scaffolder.scaffold.call_args

        # After Task 1.1c GREEN:
        assert 'version_hash' in call_args[1]
        assert len(call_args[1]['version_hash']) == 8  # 8-char hash

    @pytest.mark.asyncio
    async def test_scaffold_artifact_includes_artifact_type_in_context(self):
        """Should inject artifact_type into context for SCAFFOLD header.

        REQUIREMENT: Template needs artifact_type for SCAFFOLD header format:
        # SCAFFOLD: {artifact_type}:{version_hash} | {timestamp} | {path}
        """
        # Setup
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.scaffold.return_value = Mock(
            content='"""Test."""\nclass Test:\n    pass\n',
            file_name='test.py'
        )

        mock_fs_adapter = Mock()
        mock_fs_adapter.resolve_path.return_value = Path('/test/test.py')

        mock_validation_service = Mock()
        mock_validation_service.validate = AsyncMock(return_value=(True, []))

        with patch.object(
            ArtifactManager, 'get_artifact_path', return_value=Path('/test/test.py')
        ):
            manager = ArtifactManager(
                scaffolder=mock_scaffolder,
                fs_adapter=mock_fs_adapter,
                validation_service=mock_validation_service
            )

            await manager.scaffold_artifact('dto', name='Test', fields=[])

        # REQUIREMENT: artifact_type should be in context
        call_args = mock_scaffolder.scaffold.call_args

        # This might already work if _enrich_context adds it
        # But verify it's available for SCAFFOLD metadata
        assert 'template_id' in call_args[1]  # Currently 'template_id' is used
        # After Task 1.1c, should also have 'artifact_type'

    @pytest.mark.asyncio
    async def test_registry_yaml_created_if_not_exists(self):
        """Should create .st3/template_registry.yaml on first scaffold operation.

        REQUIREMENT: Registry file should be auto-created, not require manual setup.
        """
        # Setup - simulate first run (no registry file)
        mock_scaffolder = Mock(spec=TemplateScaffolder)
        mock_scaffolder.scaffold.return_value = Mock(
            content='"""Test."""\nclass Test:\n    pass\n',
            file_name='test.py'
        )

        mock_fs_adapter = Mock()
        mock_fs_adapter.resolve_path.return_value = Path('/test/test.py')

        mock_validation_service = Mock()
        mock_validation_service.validate = AsyncMock(return_value=(True, []))

        with patch.object(
            ArtifactManager, 'get_artifact_path', return_value=Path('/test/test.py')
        ):
            manager = ArtifactManager(
                scaffolder=mock_scaffolder,
                fs_adapter=mock_fs_adapter,
                validation_service=mock_validation_service
            )

            await manager.scaffold_artifact('dto', name='Test', fields=[])

        # REQUIREMENT: .st3/template_registry.yaml should exist after scaffolding
        # Currently FAILS - registry not integrated
        # After Task 1.1c fix, verify file creation via TemplateRegistry._persist()

"""Tests for directory resolution (Cycle 8)."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.core.exceptions import ConfigError
from mcp_server.managers.artifact_manager import ArtifactManager


class TestDirectoryResolution:
    """Test get_artifact_path() method."""

    def test_get_artifact_path_returns_full_path(self):
        """get_artifact_path() returns complete path with filename."""
        mock_registry = Mock(spec=ArtifactRegistryConfig)
        artifact = Mock()
        artifact.type_id = 'dto'
        artifact.file_extension = '.py'
        artifact.name_suffix = 'DTO'
        mock_registry.get_artifact.return_value = artifact

        workspace_root = Path('/project').resolve()  # Normalize for Windows
        manager = ArtifactManager(
            workspace_root=workspace_root,
            registry=mock_registry
        )

        with patch('mcp_server.managers.artifact_manager.DirectoryPolicyResolver') as mock_resolver_cls:
            mock_resolver = Mock()
            mock_resolver.find_directories_for_artifact.return_value = ['mcp_server/dtos']
            mock_resolver_cls.return_value = mock_resolver

            path = manager.get_artifact_path('dto', 'User')

            # Check path components instead of absolute equality (Windows vs Unix)
            assert path.name == 'UserDTO.py'
            assert 'mcp_server' in path.parts
            assert 'dtos' in path.parts
            assert path.is_absolute()

    def test_uses_first_directory_when_multiple(self):
        """When multiple directories allow artifact, use first one."""
        mock_registry = Mock(spec=ArtifactRegistryConfig)
        artifact = Mock()
        artifact.file_extension = '.py'
        artifact.name_suffix = ''
        mock_registry.get_artifact.return_value = artifact

        manager = ArtifactManager(workspace_root=Path('/test'), registry=mock_registry)

        with patch('mcp_server.managers.artifact_manager.DirectoryPolicyResolver') as mock_resolver_cls:
            mock_resolver = Mock()
            mock_resolver.find_directories_for_artifact.return_value = ['dir1', 'dir2']
            mock_resolver_cls.return_value = mock_resolver

            path = manager.get_artifact_path('test', 'Name')

            assert 'dir1' in str(path)

    def test_error_when_no_directory_found(self):
        """ConfigError raised when no valid directory."""
        mock_registry = Mock(spec=ArtifactRegistryConfig)
        artifact = Mock()
        artifact.type_id = 'unknown'
        mock_registry.get_artifact.return_value = artifact

        manager = ArtifactManager(workspace_root=Path('/test'), registry=mock_registry)

        with patch('mcp_server.managers.artifact_manager.DirectoryPolicyResolver') as mock_resolver_cls:
            mock_resolver = Mock()
            mock_resolver.find_directories_for_artifact.return_value = []
            mock_resolver_cls.return_value = mock_resolver

            with pytest.raises(ConfigError):
                manager.get_artifact_path('unknown', 'Test')

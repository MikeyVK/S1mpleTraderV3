"""
Unit tests for label tool validation integration.

Tests integration of LabelConfig validation into label tools.

@layer: Tests (Unit)
@dependencies: [pytest, unittest.mock, mcp_server.tools.label_tools]
"""
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

import pytest

from mcp_server.tools.label_tools import (
    CreateLabelTool,
    CreateLabelInput,
    AddLabelsTool,
    AddLabelsInput,
)


class TestCreateLabelValidation:
    """Test CreateLabelTool validation integration."""

    @pytest.mark.asyncio
    async def test_create_label_valid_pattern(self, tmp_path):
        """Test creating label with valid pattern name."""
        # Create labels.yaml
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            # Mock manager
            mock_manager = Mock()
            mock_manager.create_label = AsyncMock(return_value=Mock(name="type:bug", color="FF0000"))
            
            tool = CreateLabelTool(manager=mock_manager)
            params = CreateLabelInput(name="type:bug", color="FF0000", description="Bug report")
            
            result = await tool.execute(params)
            
            assert mock_manager.create_label.called
            assert "type:bug" in result.text

    @pytest.mark.asyncio
    async def test_create_label_invalid_pattern(self, tmp_path):
        """Test creating label with invalid pattern name."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
freeform_exceptions: []
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            mock_manager.create_label = AsyncMock()
            
            tool = CreateLabelTool(manager=mock_manager)
            params = CreateLabelInput(name="invalid-label", color="FF0000")
            
            result = await tool.execute(params)
            
            assert not mock_manager.create_label.called
            assert "does not match required pattern" in result.text

    @pytest.mark.asyncio
    async def test_create_label_freeform_exception(self, tmp_path):
        """Test creating freeform exception label."""
        yaml_content = """version: "1.0"
labels:
  - name: "good first issue"
    color: "7057FF"
freeform_exceptions:
  - "good first issue"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            mock_manager.create_label = AsyncMock(return_value=Mock(name="good first issue", color="7057FF"))
            
            tool = CreateLabelTool(manager=mock_manager)
            params = CreateLabelInput(name="good first issue", color="7057FF")
            
            result = await tool.execute(params)
            
            assert mock_manager.create_label.called

    @pytest.mark.asyncio
    async def test_create_label_with_hash_prefix(self, tmp_path):
        """Test creating label with # prefix in color."""
        yaml_content = """version: "1.0"
labels: []
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            mock_manager.create_label = AsyncMock()
            
            tool = CreateLabelTool(manager=mock_manager)
            params = CreateLabelInput(name="type:feature", color="#FF0000")
            
            result = await tool.execute(params)
            
            assert not mock_manager.create_label.called
            assert "must not include # prefix" in result.text
            assert "FF0000" in result.text

    @pytest.mark.asyncio
    async def test_create_label_invalid_color_format(self, tmp_path):
        """Test creating label with invalid color format."""
        yaml_content = """version: "1.0"
labels: []
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            mock_manager.create_label = AsyncMock()
            
            tool = CreateLabelTool(manager=mock_manager)
            params = CreateLabelInput(name="type:feature", color="GGGGGG")
            
            result = await tool.execute(params)
            
            assert not mock_manager.create_label.called
            assert "Invalid color" in result.text


class TestAddLabelsValidation:
    """Test AddLabelsTool validation integration."""

    @pytest.mark.asyncio
    async def test_add_labels_all_exist(self, tmp_path):
        """Test adding labels that all exist in config."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "priority:high"
    color: "FF0000"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            mock_manager.add_labels = AsyncMock()
            
            tool = AddLabelsTool(manager=mock_manager)
            params = AddLabelsInput(issue_number=123, labels=["type:feature", "priority:high"])
            
            result = await tool.execute(params)
            
            assert mock_manager.add_labels.called
            assert "123" in result.text

    @pytest.mark.asyncio
    async def test_add_labels_some_undefined(self, tmp_path):
        """Test adding labels where some don't exist."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            mock_manager.add_labels = AsyncMock()
            
            tool = AddLabelsTool(manager=mock_manager)
            params = AddLabelsInput(issue_number=123, labels=["type:feature", "undefined:label"])
            
            result = await tool.execute(params)
            
            assert not mock_manager.add_labels.called
            assert "not defined in labels.yaml" in result.text
            assert "undefined:label" in result.text

    @pytest.mark.asyncio
    async def test_add_labels_all_undefined(self, tmp_path):
        """Test adding labels where all don't exist."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            mock_manager.add_labels = AsyncMock()
            
            tool = AddLabelsTool(manager=mock_manager)
            params = AddLabelsInput(issue_number=123, labels=["foo:bar", "baz:qux"])
            
            result = await tool.execute(params)
            
            assert not mock_manager.add_labels.called
            assert "not defined in labels.yaml" in result.text

    @pytest.mark.asyncio
    async def test_add_labels_empty_list(self, tmp_path):
        """Test adding empty label list."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            mock_manager.add_labels = AsyncMock()
            
            tool = AddLabelsTool(manager=mock_manager)
            params = AddLabelsInput(issue_number=123, labels=[])
            
            result = await tool.execute(params)
            
            assert mock_manager.add_labels.called


class TestSyncLabelsToGitHubTool:
    """Test SyncLabelsToGitHubTool integration."""

    @pytest.mark.asyncio
    async def test_sync_dry_run_default(self, tmp_path):
        """Test sync with default dry_run=True."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            from mcp_server.tools.label_tools import SyncLabelsToGitHubTool, SyncLabelsInput
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            mock_manager.list_labels = Mock(return_value=[])
            mock_manager.create_label = AsyncMock()
            
            tool = SyncLabelsToGitHubTool(manager=mock_manager)
            params = SyncLabelsInput()  # Default dry_run=True
            
            result = await tool.execute(params)
            
            assert "dry_run: True" in result.text.lower() or "preview" in result.text.lower()
            assert not mock_manager.create_label.called

    @pytest.mark.asyncio
    async def test_sync_creates_new_labels(self, tmp_path):
        """Test sync creates new labels."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            from mcp_server.tools.label_tools import SyncLabelsToGitHubTool, SyncLabelsInput
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            mock_manager.list_labels = Mock(return_value=[])
            mock_manager.create_label = AsyncMock()
            mock_manager.update_label = AsyncMock()
            
            tool = SyncLabelsToGitHubTool(manager=mock_manager)
            params = SyncLabelsInput(dry_run=False)
            
            result = await tool.execute(params)
            
            assert "Created 1" in result.text or "created: 1" in result.text.lower()

    @pytest.mark.asyncio
    async def test_sync_updates_changed_labels(self, tmp_path):
        """Test sync updates labels with changed color."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            from mcp_server.tools.label_tools import SyncLabelsToGitHubTool, SyncLabelsInput
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            # Existing label with different color
            mock_manager.list_labels = Mock(return_value=[{
                "name": "type:feature",
                "color": "FF0000",  # Different color
                "description": "New feature"
            }])
            mock_manager.update_label = AsyncMock()
            
            tool = SyncLabelsToGitHubTool(manager=mock_manager)
            params = SyncLabelsInput(dry_run=False)
            
            result = await tool.execute(params)
            
            assert "Updated 1" in result.text or "updated: 1" in result.text.lower()

    @pytest.mark.asyncio
    async def test_sync_skips_unchanged_labels(self, tmp_path):
        """Test sync skips labels with no changes."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            from mcp_server.tools.label_tools import SyncLabelsToGitHubTool, SyncLabelsInput
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            # Existing label identical to YAML
            mock_manager.list_labels = Mock(return_value=[{
                "name": "type:feature",
                "color": "1D76DB",
                "description": "New feature"
            }])
            mock_manager.update_label = AsyncMock()
            
            tool = SyncLabelsToGitHubTool(manager=mock_manager)
            params = SyncLabelsInput(dry_run=False)
            
            result = await tool.execute(params)
            
            assert "Skipped 1" in result.text or "skipped: 1" in result.text.lower()
            assert not mock_manager.update_label.called

    @pytest.mark.asyncio
    async def test_sync_reports_errors(self, tmp_path):
        """Test sync reports errors in result."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with patch("mcp_server.config.label_config.LabelConfig.load") as mock_load:
            from mcp_server.config.label_config import LabelConfig
            from mcp_server.tools.label_tools import SyncLabelsToGitHubTool, SyncLabelsInput
            
            config = LabelConfig.load(yaml_file)
            mock_load.return_value = config
            
            mock_manager = Mock()
            mock_manager.list_labels = Mock(side_effect=Exception("API Error"))
            
            tool = SyncLabelsToGitHubTool(manager=mock_manager)
            params = SyncLabelsInput(dry_run=False)
            
            result = await tool.execute(params)
            
            assert "error" in result.text.lower() or "fail" in result.text.lower()

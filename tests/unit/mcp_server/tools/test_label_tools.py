"""
Unit tests for label tool validation integration.

Tests integration of LabelConfig validation into label tools.

@layer: Tests (Unit)
@dependencies: [pytest, unittest.mock, mcp_server.tools.label_tools]
"""
from unittest.mock import Mock

import pytest

from mcp_server.config.label_config import LabelConfig
from mcp_server.tools.label_tools import (
    CreateLabelTool,
    CreateLabelInput,
    AddLabelsTool,
    AddLabelsInput,
    SyncLabelsToGitHubTool,
    SyncLabelsInput,
)


class TestCreateLabelValidation:
    """Test CreateLabelTool validation integration."""

    @pytest.mark.asyncio
    async def test_create_label_valid_pattern(self, tmp_path):
        """Test creating label with valid pattern name."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig._instance = None  # pylint: disable=protected-access
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.create_label = Mock(
            return_value=Mock(name="type:bug", color="FF0000")
        )

        tool = CreateLabelTool(manager=mock_manager)
        params = CreateLabelInput(
            name="type:bug", color="FF0000", description="Bug report"
        )

        result = await tool.execute(params)

        assert mock_manager.create_label.called
        assert "type:bug" in result.content[0]["text"]

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

        LabelConfig._instance = None  # pylint: disable=protected-access
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.create_label = Mock()

        tool = CreateLabelTool(manager=mock_manager)
        params = CreateLabelInput(name="invalid-label", color="FF0000")

        result = await tool.execute(params)

        assert not mock_manager.create_label.called
        assert "does not match required pattern" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_create_label_with_hash_prefix(self, tmp_path):
        """Test creating label with # prefix in color."""
        yaml_content = """version: "1.0"
labels: []
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig._instance = None  # pylint: disable=protected-access
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.create_label = Mock()

        tool = CreateLabelTool(manager=mock_manager)
        params = CreateLabelInput(name="type:feature", color="#FF0000")

        result = await tool.execute(params)

        assert not mock_manager.create_label.called
        assert "must not include # prefix" in result.content[0]["text"]
        assert "FF0000" in result.content[0]["text"]


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

        LabelConfig._instance = None  # pylint: disable=protected-access
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.add_labels = Mock()

        tool = AddLabelsTool(manager=mock_manager)
        params = AddLabelsInput(
            issue_number=123, labels=["type:feature", "priority:high"]
        )

        result = await tool.execute(params)

        assert mock_manager.add_labels.called
        assert "123" in result.content[0]["text"]

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

        LabelConfig._instance = None  # pylint: disable=protected-access
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.add_labels = Mock()

        tool = AddLabelsTool(manager=mock_manager)
        params = AddLabelsInput(
            issue_number=123, labels=["type:feature", "undefined:label"]
        )

        result = await tool.execute(params)

        assert not mock_manager.add_labels.called
        assert "not defined in labels.yaml" in result.content[0]["text"]
        assert "undefined:label" in result.content[0]["text"]


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

        LabelConfig._instance = None  # pylint: disable=protected-access
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.list_labels = Mock(return_value=[])
        mock_manager.create_label = Mock()

        tool = SyncLabelsToGitHubTool(manager=mock_manager)
        params = SyncLabelsInput()  # Default dry_run=True

        result = await tool.execute(params)

        assert (
            "dry_run: True" in result.content[0]["text"]
            or "preview" in result.content[0]["text"].lower()
        )
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

        LabelConfig._instance = None  # pylint: disable=protected-access
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.list_labels = Mock(return_value=[])
        mock_manager.create_label = Mock()
        mock_manager.update_label = Mock()

        tool = SyncLabelsToGitHubTool(manager=mock_manager)
        params = SyncLabelsInput(dry_run=False)

        result = await tool.execute(params)

        assert "Created 1" in result.content[0]["text"] or "created: 1" in result.content[
            0
        ]["text"].lower()

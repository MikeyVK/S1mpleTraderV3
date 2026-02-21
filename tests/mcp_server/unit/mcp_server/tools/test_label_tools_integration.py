"""
Unit tests for label tool integration with LabelConfig.

Tests validation hooks in CreateLabelTool, AddLabelsTool, and DetectLabelDriftTool.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.tools.label_tools, mcp_server.config.label_config]
"""

# Standard library
from unittest.mock import Mock

# Third-party
import pytest

# Local
from mcp_server.config.label_config import LabelConfig
from mcp_server.tools.label_tools import (
    AddLabelsInput,
    AddLabelsTool,
    CreateLabelInput,
    CreateLabelTool,
    DetectLabelDriftInput,
    DetectLabelDriftTool,
)


# Test Helper
class _MockLabel:  # pylint: disable=too-few-public-methods
    """Mock label object for testing (avoids Mock.name conflict)."""

    def __init__(self, name: str, color: str, description: str = "") -> None:
        self.name = name
        self.color = color
        self.description = description


class TestCreateLabelToolValidation:
    """Tests for CreateLabelTool validation hooks."""

    @pytest.mark.asyncio
    async def test_create_label_validates_name_pattern(self, tmp_path):
        """CreateLabelTool rejects invalid label name pattern."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        tool = CreateLabelTool(manager=Mock())
        params = CreateLabelInput(name="invalid-name", color="FF0000")

        result = await tool.execute(params)
        assert "does not match required pattern" in result.content[0]["text"]

    @pytest.mark.asyncio
    async def test_create_label_rejects_hash_prefix(self, tmp_path):
        """CreateLabelTool rejects color with # prefix."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        tool = CreateLabelTool(manager=Mock())
        params = CreateLabelInput(name="type:bug", color="#FF0000")

        result = await tool.execute(params)
        result_text = result.content[0]["text"]
        assert "must not include # prefix" in result_text.lower()
        assert "FF0000" in result_text

    @pytest.mark.asyncio
    async def test_create_label_valid_succeeds(self, tmp_path):
        """CreateLabelTool creates label with valid name and color."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.create_label = Mock(return_value=_MockLabel(name="type:bug", color="FF0000"))

        tool = CreateLabelTool(manager=mock_manager)
        params = CreateLabelInput(name="type:bug", color="FF0000")

        result = await tool.execute(params)
        assert "Created label" in result.content[0]["text"]
        mock_manager.create_label.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_label_freeform_exception_allowed(self, tmp_path):
        """CreateLabelTool allows freeform exceptions like 'good first issue'."""
        yaml_content = """version: "1.0"
freeform_exceptions:
  - "good first issue"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.create_label = Mock(
            return_value=_MockLabel(name="good first issue", color="7057FF")
        )

        tool = CreateLabelTool(manager=mock_manager)
        params = CreateLabelInput(name="good first issue", color="7057FF")

        result = await tool.execute(params)
        assert "Created label" in result.content[0]["text"]


class TestAddLabelsToolValidation:
    """Tests for AddLabelsTool validation hooks."""

    @pytest.mark.asyncio
    async def test_add_labels_validates_existence(self, tmp_path):
        """AddLabelsTool rejects undefined labels (strict enforcement)."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        tool = AddLabelsTool(manager=Mock())
        params = AddLabelsInput(issue_number=1, labels=["undefined-label"])

        result = await tool.execute(params)
        result_text = result.content[0]["text"]
        assert "not defined in labels.yaml" in result_text
        assert "undefined-label" in result_text

    @pytest.mark.asyncio
    async def test_add_labels_all_valid_succeeds(self, tmp_path):
        """AddLabelsTool adds all labels when all are valid."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "priority:high"
    color: "D93F0B"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        tool = AddLabelsTool(manager=mock_manager)
        params = AddLabelsInput(issue_number=1, labels=["type:feature", "priority:high"])

        result = await tool.execute(params)
        assert "Added labels" in result.content[0]["text"]
        mock_manager.add_labels.assert_called_once_with(1, ["type:feature", "priority:high"])

    @pytest.mark.asyncio
    async def test_add_labels_partial_invalid_rejects_all(self, tmp_path):
        """AddLabelsTool rejects entire operation if ANY label is undefined."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        tool = AddLabelsTool(manager=mock_manager)
        params = AddLabelsInput(issue_number=1, labels=["type:feature", "undefined"])

        result = await tool.execute(params)
        assert "not defined in labels.yaml" in result.content[0]["text"]
        mock_manager.add_labels.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_labels_freeform_allowed(self, tmp_path):
        """AddLabelsTool accepts freeform exceptions."""
        yaml_content = """version: "1.0"
freeform_exceptions:
  - "good first issue"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "good first issue"
    color: "7057FF"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        tool = AddLabelsTool(manager=mock_manager)
        params = AddLabelsInput(issue_number=1, labels=["good first issue"])

        result = await tool.execute(params)
        assert "Added labels" in result.content[0]["text"]


class TestDetectLabelDriftTool:
    """Tests for DetectLabelDriftTool (read-only drift detection)."""

    @pytest.mark.asyncio
    async def test_drift_detection_github_has_extra_labels(self, tmp_path):
        """DetectLabelDriftTool detects labels in GitHub not in YAML."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.list_labels = Mock(
            return_value=[
                _MockLabel(name="type:feature", color="1D76DB", description=""),
                _MockLabel(name="custom-label", color="FF0000", description=""),
            ]
        )

        tool = DetectLabelDriftTool(manager=mock_manager)
        params = DetectLabelDriftInput()

        result = await tool.execute(params)
        result_text = result.content[0]["text"]
        assert "drift detected" in result_text.lower()
        assert "GitHub-only labels" in result_text
        assert "custom-label" in result_text

    @pytest.mark.asyncio
    async def test_drift_detection_yaml_has_extra_labels(self, tmp_path):
        """DetectLabelDriftTool detects labels in YAML not in GitHub."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "type:new"
    color: "FF0000"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.list_labels = Mock(
            return_value=[_MockLabel(name="type:feature", color="1D76DB", description="")]
        )

        tool = DetectLabelDriftTool(manager=mock_manager)
        params = DetectLabelDriftInput()

        result = await tool.execute(params)
        result_text = result.content[0]["text"]
        assert "drift detected" in result_text.lower()
        assert "YAML-only labels" in result_text
        assert "type:new" in result_text

    @pytest.mark.asyncio
    async def test_drift_detection_color_mismatch(self, tmp_path):
        """DetectLabelDriftTool detects color differences."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        # Create mock label with attributes (not Mock object)
        class MockLabel:
            def __init__(self, name, color, description):
                self.name = name
                self.color = color
                self.description = description

        mock_manager = Mock()
        mock_manager.list_labels = Mock(
            return_value=[MockLabel(name="type:feature", color="FF0000", description="")]
        )

        tool = DetectLabelDriftTool(manager=mock_manager)
        params = DetectLabelDriftInput()

        result = await tool.execute(params)
        result_text = result.content[0]["text"]
        assert "drift detected" in result_text.lower()
        assert "Color mismatches" in result_text
        assert "1D76DB" in result_text
        assert "FF0000" in result_text

    @pytest.mark.asyncio
    async def test_drift_detection_description_mismatch(self, tmp_path):
        """DetectLabelDriftTool detects description differences."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "YAML description"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.list_labels = Mock(
            return_value=[
                _MockLabel(
                    name="type:feature",
                    color="1D76DB",
                    description="GitHub description",
                )
            ]
        )

        tool = DetectLabelDriftTool(manager=mock_manager)
        params = DetectLabelDriftInput()

        result = await tool.execute(params)
        result_text = result.content[0]["text"]
        assert "drift detected" in result_text.lower()
        assert "Description mismatches" in result_text

    @pytest.mark.asyncio
    async def test_drift_detection_no_drift(self, tmp_path):
        """DetectLabelDriftTool reports no drift when aligned."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "Test"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.list_labels = Mock(
            return_value=[_MockLabel(name="type:feature", color="1D76DB", description="Test")]
        )

        tool = DetectLabelDriftTool(manager=mock_manager)
        params = DetectLabelDriftInput()

        result = await tool.execute(params)
        result_text = result.content[0]["text"]
        assert "no drift detected" in result_text.lower()
        assert "aligned" in result_text.lower()

    @pytest.mark.asyncio
    async def test_drift_detection_returns_structured_report(self, tmp_path):
        """DetectLabelDriftTool returns structured drift report."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.list_labels = Mock(
            return_value=[
                _MockLabel(name="type:feature", color="FF0000", description=""),  # Color mismatch
                _MockLabel(name="github-only", color="000000", description=""),  # GitHub only
            ]
        )

        tool = DetectLabelDriftTool(manager=mock_manager)
        params = DetectLabelDriftInput()

        result = await tool.execute(params)
        result_text = result.content[0]["text"]
        # Should contain multiple drift types
        assert "GitHub-only labels" in result_text
        assert "Color mismatches" in result_text
        assert "github-only" in result_text

    @pytest.mark.asyncio
    async def test_drift_detection_handles_github_api_error(self, tmp_path):
        """DetectLabelDriftTool handles GitHub API errors gracefully."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig.reset()
        LabelConfig.load(yaml_file)

        mock_manager = Mock()
        mock_manager.list_labels = Mock(side_effect=Exception("API Error"))

        tool = DetectLabelDriftTool(manager=mock_manager)
        params = DetectLabelDriftInput()

        result = await tool.execute(params)
        assert "Error loading labels" in result.content[0]["text"]

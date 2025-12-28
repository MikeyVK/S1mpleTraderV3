"""
Unit tests for Label dataclass and LabelConfig.

Tests immutable label definition with color validation and YAML loading.

@layer: Tests (Unit)
@dependencies: [pytest, dataclasses, mcp_server.config.label_config]
"""

# Standard library
from dataclasses import FrozenInstanceError

# Third-party
import pytest
from pydantic import ValidationError

# Project modules
from mcp_server.config.label_config import Label, LabelConfig


class TestLabelCreation:
    """Test Label dataclass creation with various inputs."""

    def test_label_creation_valid(self):
        """Create label with valid color."""
        label = Label(name="type:feature", color="1D76DB")
        assert label.name == "type:feature"
        assert label.color == "1D76DB"
        assert not label.description

    def test_label_creation_with_description(self):
        """Create label with optional description."""
        label = Label(
            name="type:bug",
            color="D73A4A",
            description="Something isn't working"
        )
        assert label.name == "type:bug"
        assert label.color == "D73A4A"
        assert label.description == "Something isn't working"

    def test_label_creation_lowercase_color(self):
        """Accept lowercase hex color."""
        label = Label(name="priority:high", color="ff0000")
        assert label.color == "ff0000"

    def test_label_creation_uppercase_color(self):
        """Accept uppercase hex color."""
        label = Label(name="priority:low", color="FF0000")
        assert label.color == "FF0000"

    def test_label_creation_mixed_color(self):
        """Accept mixed case hex color."""
        label = Label(name="phase:design", color="AbC123")
        assert label.color == "AbC123"


class TestLabelColorValidation:
    """Test Label color format validation."""

    def test_label_invalid_color_hash_prefix(self):
        """Reject color with # prefix."""
        with pytest.raises(ValueError, match="Invalid color format"):
            Label(name="type:test", color="#ff0000")

    def test_label_invalid_color_too_short(self):
        """Reject color that is too short."""
        with pytest.raises(ValueError, match="Invalid color format"):
            Label(name="type:test", color="ff00")

    def test_label_invalid_color_non_hex(self):
        """Reject color with non-hex characters."""
        with pytest.raises(ValueError, match="Invalid color format"):
            Label(name="type:test", color="gggggg")


class TestLabelImmutability:
    """Test Label immutability (frozen=True)."""

    def test_label_immutable(self):
        """Verify frozen=True prevents modification."""
        label = Label(name="type:feature", color="1D76DB")
        with pytest.raises(FrozenInstanceError):
            label.name = "type:bug"  # type: ignore[misc]

    def test_label_color_immutable(self):
        """Verify color field is also immutable."""
        label = Label(name="type:feature", color="1D76DB")
        with pytest.raises(FrozenInstanceError):
            label.color = "FF0000"  # type: ignore[misc]


class TestLabelConversion:
    """Test Label conversion methods."""

    def test_label_to_github_dict(self):
        """Convert Label to GitHub API format."""
        label = Label(
            name="type:feature",
            color="1D76DB",
            description="New feature"
        )
        result = label.to_github_dict()

        assert result == {
            "name": "type:feature",
            "color": "1D76DB",
            "description": "New feature"
        }

    def test_label_to_github_dict_no_description(self):
        """Convert Label without description to GitHub format."""
        label = Label(name="priority:high", color="D93F0B")
        result = label.to_github_dict()

        assert result == {
            "name": "priority:high",
            "color": "D93F0B",
            "description": ""
        }


class TestLabelConfigLoading:
    """Test LabelConfig loading from YAML files."""

    def test_load_valid_yaml(self, tmp_path):
        """Load simple valid YAML configuration."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:test"
    color: "ff0000"
    description: "Test label"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        # Clear singleton before test
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        assert config.version == "1.0"
        assert len(config.labels) == 1
        assert config.labels[0].name == "type:test"
        assert config.labels[0].color == "ff0000"

    def test_load_multiple_labels(self, tmp_path):
        """Load YAML with multiple labels."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "type:bug"
    color: "D73A4A"
  - name: "priority:high"
    color: "D93F0B"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        assert len(config.labels) == 3

    def test_load_with_freeform_exceptions(self, tmp_path):
        """Load YAML with freeform_exceptions list."""
        yaml_content = """version: "1.0"
freeform_exceptions:
  - "good first issue"
  - "help wanted"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        assert len(config.freeform_exceptions) == 2
        assert "good first issue" in config.freeform_exceptions

    def test_load_file_not_found(self, tmp_path):
        """Raise FileNotFoundError for missing file."""
        yaml_file = tmp_path / "nonexistent.yaml"
        LabelConfig._instance = None  # pylint: disable=protected-access

        with pytest.raises(FileNotFoundError, match="Label configuration not found"):
            LabelConfig.load(yaml_file)

    def test_load_invalid_yaml_syntax(self, tmp_path):
        """Raise ValueError for invalid YAML syntax."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:test
    invalid yaml [[[
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        with pytest.raises(ValueError, match="Invalid YAML syntax"):
            LabelConfig.load(yaml_file)

    def test_load_missing_version_field(self, tmp_path):
        """Raise ValidationError for missing version."""
        yaml_content = """labels:
  - name: "type:test"
    color: "ff0000"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        with pytest.raises(ValidationError):
            LabelConfig.load(yaml_file)

    def test_load_missing_labels_field(self, tmp_path):
        """Raise ValueError for missing labels field."""
        yaml_content = """version: "1.0"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        with pytest.raises(ValueError, match="Missing required field"):
            LabelConfig.load(yaml_file)

    def test_load_invalid_color_in_yaml(self, tmp_path):
        """Raise ValueError for invalid color in YAML."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:test"
    color: "#ff0000"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        with pytest.raises(ValueError, match="Invalid color format"):
            LabelConfig.load(yaml_file)

    def test_load_duplicate_label_names(self, tmp_path):
        """Raise ValidationError for duplicate label names."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:test"
    color: "ff0000"
  - name: "type:test"
    color: "00ff00"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        with pytest.raises(ValidationError, match="Duplicate label names"):
            LabelConfig.load(yaml_file)

    def test_load_singleton_pattern(self, tmp_path):
        """Verify singleton pattern returns same instance."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:test"
    color: "ff0000"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config1 = LabelConfig.load(yaml_file)
        config2 = LabelConfig.load(yaml_file)
        assert config1 is config2

    def test_load_empty_labels_list(self, tmp_path):
        """Load YAML with empty labels list."""
        yaml_content = """version: "1.0"
labels: []
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        assert not config.labels

    def test_load_builds_caches(self, tmp_path):
        """Verify _labels_by_name cache is populated."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "priority:high"
    color: "D93F0B"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        # pylint: disable=protected-access
        assert "type:feature" in config._labels_by_name
        assert "priority:high" in config._labels_by_name


class TestLabelValidation:
    """Test label name validation methods."""

    def test_validate_label_name_type_valid(self, tmp_path):
        """Accept valid type: label."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        valid, error = config.validate_label_name("type:feature")
        assert valid
        assert error == ""

    def test_validate_label_name_priority_valid(self, tmp_path):
        """Accept valid priority: label."""
        yaml_content = """version: "1.0"
labels:
  - name: "priority:high"
    color: "D93F0B"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        valid, error = config.validate_label_name("priority:high")
        assert valid
        assert error == ""

    def test_validate_label_name_status_valid(self, tmp_path):
        """Accept valid status: label."""
        yaml_content = """version: "1.0"
labels:
  - name: "status:in-progress"
    color: "FFA500"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        valid, error = config.validate_label_name("status:in-progress")
        assert valid
        assert error == ""

    def test_validate_label_name_phase_valid(self, tmp_path):
        """Accept valid phase: label."""
        yaml_content = """version: "1.0"
labels:
  - name: "phase:design"
    color: "0E8A16"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        valid, error = config.validate_label_name("phase:design")
        assert valid
        assert error == ""

    def test_validate_label_name_scope_valid(self, tmp_path):
        """Accept valid scope: label."""
        yaml_content = """version: "1.0"
labels:
  - name: "scope:backend"
    color: "5319E7"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        valid, error = config.validate_label_name("scope:backend")
        assert valid
        assert error == ""

    def test_validate_label_name_component_valid(self, tmp_path):
        """Accept valid component: label."""
        yaml_content = """version: "1.0"
labels:
  - name: "component:api"
    color: "D4C5F9"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        valid, error = config.validate_label_name("component:api")
        assert valid
        assert error == ""

    def test_validate_label_name_effort_valid(self, tmp_path):
        """Accept valid effort: label."""
        yaml_content = """version: "1.0"
labels:
  - name: "effort:small"
    color: "C2E0C6"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        valid, error = config.validate_label_name("effort:small")
        assert valid
        assert error == ""

    def test_validate_label_name_parent_valid(self, tmp_path):
        """Accept valid parent: label."""
        yaml_content = """version: "1.0"
labels:
  - name: "parent:epic-42"
    color: "B60205"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        valid, error = config.validate_label_name("parent:epic-42")
        assert valid
        assert error == ""

    def test_validate_label_name_invalid_pattern(self, tmp_path):
        """Reject label that doesn't match pattern."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        valid, error = config.validate_label_name("InvalidLabel")
        assert not valid
        assert "does not match required pattern" in error

    def test_validate_label_name_freeform_exception(self, tmp_path):
        """Accept freeform label in exceptions list."""
        yaml_content = """version: "1.0"
freeform_exceptions:
  - "good first issue"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        valid, error = config.validate_label_name("good first issue")
        assert valid
        assert error == ""

    def test_label_exists_true(self, tmp_path):
        """Return True for defined label."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        assert config.label_exists("type:feature")

    def test_label_exists_false(self, tmp_path):
        """Return False for undefined label."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        assert not config.label_exists("type:bug")

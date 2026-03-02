"""
Unit tests for Label dataclass and LabelConfig.

Tests immutable label definition with color validation and YAML loading.

@layer: Tests (Unit)
@dependencies: [pytest, dataclasses, mcp_server.config.label_config]
"""

# Standard library
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock

# Third-party
import pytest
from pydantic import ValidationError

# Project modules
from mcp_server.config.label_config import Label, LabelConfig


class TestLabelCreation:
    """Test Label dataclass creation with various inputs."""

    def test_label_creation_valid(self) -> None:
        """Create label with valid color."""
        label = Label(name="type:feature", color="1D76DB")
        assert label.name == "type:feature"
        assert label.color == "1D76DB"
        assert not label.description

    def test_label_creation_with_description(self) -> None:
        """Create label with optional description."""
        label = Label(name="type:bug", color="D73A4A", description="Something isn't working")
        assert label.name == "type:bug"
        assert label.color == "D73A4A"
        assert label.description == "Something isn't working"

    def test_label_creation_lowercase_color(self) -> None:
        """Accept lowercase hex color."""
        label = Label(name="priority:high", color="ff0000")
        assert label.color == "ff0000"

    def test_label_creation_uppercase_color(self) -> None:
        """Accept uppercase hex color."""
        label = Label(name="priority:low", color="FF0000")
        assert label.color == "FF0000"

    def test_label_creation_mixed_color(self) -> None:
        """Accept mixed case hex color."""
        label = Label(name="phase:design", color="AbC123")
        assert label.color == "AbC123"


class TestLabelColorValidation:
    """Test Label color format validation."""

    def test_label_invalid_color_hash_prefix(self) -> None:
        """Reject color with # prefix."""
        with pytest.raises(ValueError, match="Invalid color format"):
            Label(name="type:test", color="#ff0000")

    def test_label_invalid_color_too_short(self) -> None:
        """Reject color that is too short."""
        with pytest.raises(ValueError, match="Invalid color format"):
            Label(name="type:test", color="ff00")

    def test_label_invalid_color_non_hex(self) -> None:
        """Reject color with non-hex characters."""
        with pytest.raises(ValueError, match="Invalid color format"):
            Label(name="type:test", color="gggggg")


class TestLabelImmutability:
    """Test Label immutability (frozen=True)."""

    def test_label_immutable(self) -> None:
        """Verify frozen=True prevents modification."""
        label = Label(name="type:feature", color="1D76DB")
        with pytest.raises(FrozenInstanceError):
            label.name = "type:bug"  # type: ignore[misc]

    def test_label_color_immutable(self) -> None:
        """Verify color field is also immutable."""
        label = Label(name="type:feature", color="1D76DB")
        with pytest.raises(FrozenInstanceError):
            label.color = "FF0000"  # type: ignore[misc]


class TestLabelConversion:
    """Test Label conversion methods."""

    def test_label_to_github_dict(self) -> None:
        """Convert Label to GitHub API format."""
        label = Label(name="type:feature", color="1D76DB", description="New feature")
        result = label.to_github_dict()

        assert result == {"name": "type:feature", "color": "1D76DB", "description": "New feature"}

    def test_label_to_github_dict_no_description(self) -> None:
        """Convert Label without description to GitHub format."""
        label = Label(name="priority:high", color="D93F0B")
        result = label.to_github_dict()

        assert result == {"name": "priority:high", "color": "D93F0B", "description": ""}


class TestLabelConfigLoading:
    """Test LabelConfig loading from YAML files."""

    def test_load_valid_yaml(self, tmp_path: Path) -> None:
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

    def test_load_multiple_labels(self, tmp_path: Path) -> None:
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

    def test_load_with_freeform_exceptions(self, tmp_path: Path) -> None:
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

    def test_load_file_not_found(self, tmp_path: Path) -> None:
        """Raise FileNotFoundError for missing file."""
        yaml_file = tmp_path / "nonexistent.yaml"
        LabelConfig._instance = None  # pylint: disable=protected-access

        with pytest.raises(FileNotFoundError, match="Label configuration not found"):
            LabelConfig.load(yaml_file)

    def test_load_invalid_yaml_syntax(self, tmp_path: Path) -> None:
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

    def test_load_missing_version_field(self, tmp_path: Path) -> None:
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

    def test_load_missing_labels_field(self, tmp_path: Path) -> None:
        """Raise ValueError for missing labels field."""
        yaml_content = """version: "1.0"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        with pytest.raises(ValueError, match="Missing required field"):
            LabelConfig.load(yaml_file)

    def test_load_invalid_color_in_yaml(self, tmp_path: Path) -> None:
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

    def test_load_duplicate_label_names(self, tmp_path: Path) -> None:
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

    def test_load_singleton_pattern(self, tmp_path: Path) -> None:
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

    def test_load_empty_labels_list(self, tmp_path: Path) -> None:
        """Load YAML with empty labels list."""
        yaml_content = """version: "1.0"
labels: []
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        assert not config.labels

    def test_load_builds_caches(self, tmp_path: Path) -> None:
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

    def test_validate_label_name_type_valid(self, tmp_path: Path) -> None:
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
        assert not error

    def test_validate_label_name_priority_valid(self, tmp_path: Path) -> None:
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
        assert not error

    def test_validate_label_name_status_valid(self, tmp_path: Path) -> None:
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
        assert not error

    def test_validate_label_name_phase_valid(self, tmp_path: Path) -> None:
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
        assert not error

    def test_validate_label_name_scope_valid(self, tmp_path: Path) -> None:
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
        assert not error

    def test_validate_label_name_component_valid(self, tmp_path: Path) -> None:
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
        assert not error

    def test_validate_label_name_effort_valid(self, tmp_path: Path) -> None:
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
        assert not error

    def test_validate_label_name_parent_valid(self, tmp_path: Path) -> None:
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
        assert not error

    def test_validate_label_name_invalid_pattern(self, tmp_path: Path) -> None:
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

    def test_validate_label_name_freeform_exception(self, tmp_path: Path) -> None:
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
        assert not error

    def test_label_exists_true(self, tmp_path: Path) -> None:
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

    def test_label_exists_false(self, tmp_path: Path) -> None:
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


class TestLabelQueries:
    """Test label query methods."""

    def test_get_label_found(self, tmp_path: Path) -> None:
        """Return label when found by name."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        label = config.get_label("type:feature")
        assert label is not None
        assert label.name == "type:feature"
        assert label.color == "1D76DB"

    def test_get_label_not_found(self, tmp_path: Path) -> None:
        """Return None when label not found."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        label = config.get_label("type:bug")
        assert label is None

    def test_get_label_case_sensitive(self, tmp_path: Path) -> None:
        """Label lookup is case-sensitive."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        label = config.get_label("Type:feature")
        assert label is None

    def test_get_labels_by_category_type(self, tmp_path: Path) -> None:
        """Return all type: labels."""
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
        labels = config.get_labels_by_category("type")
        assert len(labels) == 2
        assert labels[0].name == "type:feature"
        assert labels[1].name == "type:bug"

    def test_get_labels_by_category_priority(self, tmp_path: Path) -> None:
        """Return all priority: labels."""
        yaml_content = """version: "1.0"
labels:
  - name: "priority:high"
    color: "D93F0B"
  - name: "priority:low"
    color: "0E8A16"
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        labels = config.get_labels_by_category("priority")
        assert len(labels) == 2
        assert labels[0].name == "priority:high"
        assert labels[1].name == "priority:low"

    def test_get_labels_by_category_empty(self, tmp_path: Path) -> None:
        """Return empty list for unknown category."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        labels = config.get_labels_by_category("nonexistent")
        assert labels == []

    def test_get_labels_by_category_cache_correct(self, tmp_path: Path) -> None:
        """Verify category grouping is correct."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "priority:high"
    color: "D93F0B"
  - name: "type:bug"
    color: "D73A4A"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        type_labels = config.get_labels_by_category("type")
        priority_labels = config.get_labels_by_category("priority")
        assert len(type_labels) == 2
        assert len(priority_labels) == 1
        assert all(label.name.startswith("type:") for label in type_labels)
        assert priority_labels[0].name == "priority:high"

    def test_cache_build_on_load(self, tmp_path: Path) -> None:
        """Caches are populated at load time."""
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
        assert len(config._labels_by_name) == 2
        assert "type:feature" in config._labels_by_name
        assert "priority:high" in config._labels_by_name


class TestGitHubSync:
    """Test GitHub label synchronization."""

    def test_sync_create_new_labels(self, tmp_path: Path) -> None:
        """Create labels that don't exist in GitHub."""

        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature"
  - name: "type:bug"
    color: "D73A4A"
    description: "Bug fix"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)

        # Mock GitHub adapter
        github_mock = Mock()
        github_mock.list_labels.return_value = []

        result = config.sync_to_github(github_mock, dry_run=False)

        assert len(result["created"]) == 2
        assert "type:feature" in result["created"]
        assert "type:bug" in result["created"]
        assert github_mock.create_label.call_count == 2

    def test_sync_update_changed_color(self, tmp_path: Path) -> None:
        """Update label when color differs."""

        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "FF0000"
    description: "New feature"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)

        github_mock = Mock()
        github_mock.list_labels.return_value = [
            {"name": "type:feature", "color": "1D76DB", "description": "New feature"}
        ]

        result = config.sync_to_github(github_mock, dry_run=False)

        assert len(result["updated"]) == 1
        assert "type:feature" in result["updated"]
        assert github_mock.update_label.call_count == 1

    def test_sync_update_changed_description(self, tmp_path: Path) -> None:
        """Update label when description differs."""

        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "Updated description"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)

        github_mock = Mock()
        github_mock.list_labels.return_value = [
            {"name": "type:feature", "color": "1D76DB", "description": "Old description"}
        ]

        result = config.sync_to_github(github_mock, dry_run=False)

        assert len(result["updated"]) == 1
        assert "type:feature" in result["updated"]

    def test_sync_skip_unchanged(self, tmp_path: Path) -> None:
        """Skip label when no changes needed."""

        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)

        github_mock = Mock()
        github_mock.list_labels.return_value = [
            {"name": "type:feature", "color": "1D76DB", "description": "New feature"}
        ]

        result = config.sync_to_github(github_mock, dry_run=False)

        assert len(result["skipped"]) == 1
        assert "type:feature" in result["skipped"]
        assert github_mock.update_label.call_count == 0

    def test_sync_dry_run_no_changes(self, tmp_path: Path) -> None:
        """Dry run mode doesn't call GitHub API."""

        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)

        github_mock = Mock()
        github_mock.list_labels.return_value = []

        result = config.sync_to_github(github_mock, dry_run=True)

        assert len(result["created"]) == 1
        assert github_mock.create_label.call_count == 0

    def test_sync_dry_run_reports_changes(self, tmp_path: Path) -> None:
        """Dry run shows what would change."""

        yaml_content = """version: "1.0"
labels:
  - name: "type:new"
    color: "FF0000"
  - name: "type:existing"
    color: "00FF00"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)

        github_mock = Mock()
        github_mock.list_labels.return_value = [
            {"name": "type:existing", "color": "0000FF", "description": ""}
        ]

        result = config.sync_to_github(github_mock, dry_run=True)

        assert len(result["created"]) == 1
        assert len(result["updated"]) == 1
        assert github_mock.create_label.call_count == 0
        assert github_mock.update_label.call_count == 0

    def test_sync_github_api_error(self, tmp_path: Path) -> None:
        """Handle GitHub API errors gracefully."""

        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)

        github_mock = Mock()
        github_mock.list_labels.side_effect = Exception("API error")

        result = config.sync_to_github(github_mock)

        assert len(result["errors"]) == 1
        assert "Failed to fetch labels" in result["errors"][0]

    def test_sync_partial_success(self, tmp_path: Path) -> None:
        """Some labels succeed, some fail."""

        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "type:bug"
    color: "D73A4A"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)

        github_mock = Mock()
        github_mock.list_labels.return_value = []
        github_mock.create_label.side_effect = [None, Exception("Failed")]

        result = config.sync_to_github(github_mock, dry_run=False)

        assert len(result["created"]) == 1
        assert len(result["errors"]) == 1
        assert "type:bug" in result["errors"][0]

    def test_sync_empty_labels_list(self, tmp_path: Path) -> None:
        """Handle empty labels.yaml gracefully."""

        yaml_content = """version: "1.0"
labels: []
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)

        github_mock = Mock()
        github_mock.list_labels.return_value = []

        result = config.sync_to_github(github_mock)

        assert result["created"] == []
        assert result["updated"] == []
        assert result["skipped"] == []
        assert result["errors"] == []

    def test_sync_result_format(self, tmp_path: Path) -> None:
        """Result has correct dict structure."""

        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)

        github_mock = Mock()
        github_mock.list_labels.return_value = []

        result = config.sync_to_github(github_mock)

        assert "created" in result
        assert "updated" in result
        assert "skipped" in result
        assert "errors" in result
        assert isinstance(result["created"], list)

    def test_needs_update_color_differs(self, tmp_path: Path) -> None:
        """Helper detects color change."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "FF0000"
    description: "Test"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        label = config.labels[0]

        github_label = {"color": "1D76DB", "description": "Test"}
        assert config._needs_update(label, github_label)  # pylint: disable=protected-access

    def test_needs_update_description_differs(self, tmp_path: Path) -> None:
        """Helper detects description change."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)
        LabelConfig._instance = None  # pylint: disable=protected-access

        config = LabelConfig.load(yaml_file)
        label = config.labels[0]

        github_label = {"color": "1D76DB", "description": "Old"}
        assert config._needs_update(label, github_label)  # pylint: disable=protected-access

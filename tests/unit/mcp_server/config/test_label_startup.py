# tests/unit/mcp_server/config/test_label_startup.py
"""
Unit tests for label configuration startup validation.

Tests non-blocking validation during server initialization according to TDD principles.

@layer: Tests (Unit)
@dependencies: [pytest, logging, pathlib, mcp_server.config.label_startup]
"""

# Standard library
import logging

# Project modules
from mcp_server.config.label_startup import validate_label_config_on_startup


class TestStartupValidationSuccess:
    """Test successful validation with valid labels.yaml"""

    def test_startup_validation_success(self, tmp_path, caplog):
        """Test that valid config logs info message"""
        # Arrange
        yaml_content = """version: "1.0"
freeform_exceptions:
  - "good first issue"
labels:
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        caplog.set_level(logging.INFO)

        # Act
        validate_label_config_on_startup(yaml_file)

        # Assert
        assert "Successfully loaded label configuration from" in caplog.text
        assert "1 labels defined" in caplog.text


class TestStartupValidationFileNotFound:
    """Test handling of missing labels.yaml"""

    def test_startup_validation_file_not_found(self, tmp_path, caplog):
        """Test that missing file logs warning"""
        # Arrange
        yaml_file = tmp_path / "nonexistent.yaml"
        caplog.set_level(logging.WARNING)

        # Act
        validate_label_config_on_startup(yaml_file)

        # Assert
        assert "Label configuration file not found" in caplog.text
        assert str(yaml_file) in caplog.text


class TestStartupValidationInvalidYaml:
    """Test handling of syntax errors in YAML"""

    def test_startup_validation_invalid_yaml(self, tmp_path, caplog):
        """Test that YAML syntax error logs error"""
        # Arrange
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: [invalid yaml structure
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        caplog.set_level(logging.ERROR)

        # Act
        validate_label_config_on_startup(yaml_file)

        # Assert
        assert "Failed to load label configuration" in caplog.text


class TestStartupValidationDuplicateLabels:
    """Test handling of Pydantic validation errors"""

    def test_startup_validation_duplicate_labels(self, tmp_path, caplog):
        """Test that duplicate labels log error"""
        # Arrange
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "type:feature"
    color: "FF0000"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        caplog.set_level(logging.ERROR)

        # Act
        validate_label_config_on_startup(yaml_file)

        # Assert
        assert "Failed to load label configuration" in caplog.text
        assert "Duplicate label names" in caplog.text


class TestStartupValidationNonBlocking:
    """Test that validation is non-blocking"""

    def test_startup_validation_non_blocking(self, tmp_path, caplog):
        """Test that function returns even on error"""
        # Arrange
        yaml_file = tmp_path / "nonexistent.yaml"
        caplog.set_level(logging.WARNING)

        # Act - Should NOT raise exception
        validate_label_config_on_startup(yaml_file)

        # Assert
        # Function completes without raising


class TestStartupValidationLogMessages:
    """Test exact log message content"""

    def test_startup_validation_log_messages(self, tmp_path, caplog):
        """Test that log messages contain expected details"""
        # Arrange
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
  - name: "priority:high"
    color: "D93F0B"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        caplog.set_level(logging.INFO)

        # Act
        validate_label_config_on_startup(yaml_file)

        # Assert
        assert "Successfully loaded label configuration" in caplog.text
        assert "2 labels defined" in caplog.text
        assert str(yaml_file) in caplog.text

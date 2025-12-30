"""
Unit tests for label configuration startup validation.

Tests early detection of configuration issues at server startup.

@layer: Tests (Unit)
@dependencies: [pytest, logging, mcp_server.config.label_config]
"""

# Standard library
import logging

# Third-party

# Local
from mcp_server.config.label_config import LabelConfig
from mcp_server.config.label_startup import validate_label_config_on_startup


class TestStartupValidation:
    """Tests for validate_label_config_on_startup."""

    def test_startup_validation_success(self, tmp_path, caplog):
        """Valid config logs info message."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        LabelConfig._instance = None  # pylint: disable=protected-access
        LabelConfig.load(yaml_file)

        with caplog.at_level(logging.INFO):
            validate_label_config_on_startup()

        assert "Loaded labels.yaml: 1 labels" in caplog.text

    def test_startup_validation_file_not_found(self, tmp_path, caplog):
        """Missing file logs warning."""
        LabelConfig._instance = None  # pylint: disable=protected-access
        nonexistent = str(tmp_path / "nonexistent.yaml")

        with caplog.at_level(logging.WARNING):
            validate_label_config_on_startup(nonexistent)

        assert "not found" in caplog.text
        assert "WARNING" in caplog.text

    def test_startup_validation_invalid_yaml(self, tmp_path, caplog):
        """Syntax error logs error."""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text("invalid: yaml: syntax:")

        LabelConfig._instance = None  # pylint: disable=protected-access

        with caplog.at_level(logging.ERROR):
            validate_label_config_on_startup(str(yaml_file))

        assert "ERROR" in caplog.text

    def test_startup_validation_non_blocking(self):
        """Function returns even on error (non-blocking)."""
        LabelConfig._instance = None  # pylint: disable=protected-access

        # Should not raise, just log
        validate_label_config_on_startup()
        assert True  # Got here without exception

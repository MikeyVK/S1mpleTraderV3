"""
Unit tests for label configuration startup validation.

Tests early detection of configuration issues at server startup.

@layer: Tests (Unit)
@dependencies: [pytest, logging, mcp_server.config.label_config]
"""

# Standard library
import logging
from collections.abc import Iterator
from pathlib import Path

# Third-party
import pytest

# Local
from mcp_server.config.label_config import LabelConfig
from mcp_server.config.label_startup import validate_label_config_on_startup


@pytest.fixture(autouse=True)
def reset_labelconfig_singleton() -> Iterator[None]:
    """Reset LabelConfig singleton before each test for isolation."""
    LabelConfig.reset()
    yield
    LabelConfig.reset()


class TestStartupValidation:
    """Tests for validate_label_config_on_startup."""

    def test_startup_validation_success(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Valid config logs info message."""
        yaml_content = """version: "1.0"
labels:
  - name: "type:feature"
    color: "1D76DB"
"""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text(yaml_content)

        with caplog.at_level(logging.INFO):
            validate_label_config_on_startup(str(yaml_file))

        assert "Loaded labels.yaml: 1 labels" in caplog.text

    def test_startup_validation_file_not_found(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Missing file logs warning."""
        nonexistent = str(tmp_path / "nonexistent.yaml")

        with caplog.at_level(logging.WARNING):
            validate_label_config_on_startup(nonexistent)

        assert "not found" in caplog.text
        assert "WARNING" in caplog.text

    def test_startup_validation_invalid_yaml(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Syntax error logs error."""
        yaml_file = tmp_path / "labels.yaml"
        yaml_file.write_text("invalid: yaml: syntax:")

        with caplog.at_level(logging.ERROR):
            validate_label_config_on_startup(str(yaml_file))

        assert "ERROR" in caplog.text

    def test_startup_validation_non_blocking(self) -> None:
        """Function returns even on error (non-blocking)."""
        # Should not raise, just log
        validate_label_config_on_startup()
        assert True  # Got here without exception

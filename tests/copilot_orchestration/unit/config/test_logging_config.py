# tests\copilot_orchestration\unit\config\test_logging_config.py
# template=unit_test version=3d15d309 created=2026-03-22T20:38Z updated=
"""
Unit tests for copilot_orchestration.config.logging_config.

Unit tests for LoggingConfig: factory fallback chain, apply() dir creation,
Protocol compliance, Fail-Fast errors.

@layer: Tests (Unit)
@dependencies: [pytest, copilot_orchestration.config.logging_config]
@responsibilities:
    - Test TestLoggingConfig functionality
    - Verify Factory, apply(), Protocol compliance, error propagation
"""

# Standard library
import logging
from collections.abc import Generator
from pathlib import Path

# Third-party
import pytest
import yaml

# Project modules
from copilot_orchestration.config.logging_config import LoggingConfig
from copilot_orchestration.contracts.interfaces import ILoggingConfig

_OVERRIDE_YAML = """\
level: DEBUG
format: "%(levelname)s %(message)s"
handlers:
  stderr: {}
  file:
    path: .copilot/logs/orchestration.log
"""


class TestLoggingConfig:
    """Test suite for logging_config."""

    @pytest.fixture()
    def _reset_root_logger(self) -> Generator[None, None, None]:
        """Reset root logger before test; restore and close test-added handlers after.

        Required because logging.basicConfig is idempotent: if any handler is already
        attached to the root logger, subsequent basicConfig calls are no-ops. Without
        this fixture, test ordering would make handler-verification assertions unreliable.
        Also closes FileHandlers before tmp_path teardown (prevents PermissionError on Windows).
        """
        saved_handlers = logging.root.handlers[:]
        saved_level = logging.root.level
        for h in logging.root.handlers[:]:
            logging.root.removeHandler(h)
        logging.root.setLevel(logging.WARNING)
        yield
        for h in logging.root.handlers[:]:
            h.close()
            logging.root.removeHandler(h)
        for h in saved_handlers:
            logging.root.addHandler(h)
        logging.root.setLevel(saved_level)

    def test_loads_package_default_when_no_project_yaml(self, tmp_path: Path) -> None:
        """Falls back to package _default_logging.yaml when .copilot/logging.yaml absent."""
        cfg = LoggingConfig.from_copilot_dir(tmp_path)
        assert isinstance(cfg, LoggingConfig)

    def test_loads_project_yaml_when_present(self, tmp_path: Path) -> None:
        """Uses .copilot/logging.yaml (DEBUG level) when present.

        Package default (WARNING) is bypassed.
        """
        copilot_dir = tmp_path / ".copilot"
        copilot_dir.mkdir()
        (copilot_dir / "logging.yaml").write_text(_OVERRIDE_YAML, encoding="utf-8")

        cfg = LoggingConfig.from_copilot_dir(tmp_path)

        assert cfg.level == "DEBUG"

    def test_corrupt_yaml_raises(self, tmp_path: Path) -> None:
        """Corrupt YAML in project override propagates yaml.YAMLError at construction."""
        copilot_dir = tmp_path / ".copilot"
        copilot_dir.mkdir()
        (copilot_dir / "logging.yaml").write_text("level: [unclosed", encoding="utf-8")

        with pytest.raises(yaml.YAMLError):
            LoggingConfig.from_copilot_dir(tmp_path)

    def test_missing_explicit_path_raises_file_not_found(self, tmp_path: Path) -> None:
        """Passing a non-existent path directly to __init__ raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            LoggingConfig(tmp_path / "nonexistent.yaml", tmp_path)

    def test_apply_creates_log_directory(self, tmp_path: Path, _reset_root_logger: None) -> None:
        """apply() creates the .copilot/logs/ directory and attaches a FileHandler."""
        cfg = LoggingConfig.from_copilot_dir(tmp_path)
        log_dir = tmp_path / ".copilot" / "logs"
        assert not log_dir.exists()

        cfg.apply()

        assert log_dir.exists()
        assert any(isinstance(h, logging.FileHandler) for h in logging.root.handlers)

    def test_apply_idempotent_when_dir_exists(
        self, tmp_path: Path, _reset_root_logger: None
    ) -> None:
        """apply() does not raise when the log directory already exists."""
        log_dir = tmp_path / ".copilot" / "logs"
        log_dir.mkdir(parents=True)

        cfg = LoggingConfig.from_copilot_dir(tmp_path)
        cfg.apply()  # must not raise

        assert any(isinstance(h, logging.FileHandler) for h in logging.root.handlers)

    def test_satisfies_ilogging_config_protocol(self, tmp_path: Path) -> None:
        """LoggingConfig instance satisfies the ILoggingConfig Protocol (isinstance check)."""
        cfg = LoggingConfig.from_copilot_dir(tmp_path)
        assert isinstance(cfg, ILoggingConfig)

    def test_stub_satisfies_protocol(self) -> None:
        """A minimal stub with apply() satisfies ILoggingConfig for DI in tests."""

        class StubConfig:
            def apply(self) -> None:
                pass

        assert isinstance(StubConfig(), ILoggingConfig)

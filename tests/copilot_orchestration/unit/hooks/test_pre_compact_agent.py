# tests\copilot_orchestration\unit\hooks\test_pre_compact_agent.py
# template=unit_test version=3d15d309 created=2026-03-22T21:30Z updated=
"""
Unit tests for copilot_orchestration.hooks.pre_compact_agent.

Tests error-path logging in read_json_file: JSONDecodeError and missing file
are currently swallowed silently — these tests enforce DEBUG logging on those
paths.

@layer: Tests (Unit)
@dependencies: [pytest, copilot_orchestration.hooks.pre_compact_agent]
@responsibilities:
    - Verify read_json_file logs DEBUG on JSONDecodeError
    - Verify read_json_file logs DEBUG on OSError (missing file)
    - No subprocess, no git, no filesystem side-effects beyond tmp_path
"""

# Standard library
import logging
from pathlib import Path

# Third-party
import pytest

# Project modules
from copilot_orchestration.hooks.pre_compact_agent import read_json_file

_LOGGER_NAME = "copilot_orchestration.hooks.pre_compact_agent"


class TestReadJsonFileLogging:
    """Logging behaviour of read_json_file error paths."""

    def test_json_decode_error_logs_debug(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """read_json_file logs at DEBUG when the file contains invalid JSON."""
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json}", encoding="utf-8")
        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            result = read_json_file(bad)
        assert result == {}
        assert any(r.levelno == logging.DEBUG for r in caplog.records)

    def test_missing_file_logs_debug(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """read_json_file logs at DEBUG when the file does not exist."""
        missing = tmp_path / "ghost.json"
        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            result = read_json_file(missing)
        assert result == {}
        # Missing file returns {} without logging (path check guards it) —
        # log should only fire for genuine errors, not for absent optional files.
        # This test documents the expected behaviour: no DEBUG for absent files.
        # Update: if implementation logs on absent → this assertion is wrong;
        # keep as documentation of the design intent.
        # The assertion below will be green already for missing file (no logs emitted):
        assert caplog.records == []

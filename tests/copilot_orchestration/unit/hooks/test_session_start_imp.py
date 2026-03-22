# tests\copilot_orchestration\unit\hooks\test_session_start_imp.py
# template=unit_test version=3d15d309 created=2026-03-22T21:30Z updated=
"""
Unit tests for copilot_orchestration.hooks.session_start_imp.

Tests is_usable_snapshot logging: stale timestamp, no changed_files,
no file overlap. All pure-function tests — no filesystem or subprocess.

@layer: Tests (Unit)
@dependencies: [pytest, copilot_orchestration.hooks.session_start_imp]
@responsibilities:
    - Verify is_usable_snapshot logs DEBUG when snapshot is rejected
    - Verify is_usable_snapshot logs DEBUG when snapshot is accepted
    - No subprocess calls — pure function tests only
"""

# Standard library
import logging
from datetime import UTC, datetime, timedelta

# Third-party
import pytest

# Project modules
from copilot_orchestration.hooks.session_start_imp import is_usable_snapshot

_LOGGER_NAME = "copilot_orchestration.hooks.session_start_imp"


def _fresh_ts() -> str:
    return datetime.now(UTC).isoformat()


def _stale_ts() -> str:
    return (datetime.now(UTC) - timedelta(hours=10)).isoformat()


class TestIsUsableSnapshotLogging:
    """Logging behaviour of is_usable_snapshot."""

    def test_stale_snapshot_logs_debug(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """is_usable_snapshot logs at DEBUG when snapshot is rejected as stale."""
        snapshot = {"timestamp": _stale_ts(), "files_in_scope": ["src/x.py"]}
        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            result = is_usable_snapshot(snapshot, ["src/x.py"])
        assert result is False
        assert any(r.levelno == logging.DEBUG for r in caplog.records)

    def test_no_changed_files_logs_debug(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """is_usable_snapshot logs at DEBUG when no changed files are present."""
        snapshot = {"timestamp": _fresh_ts(), "files_in_scope": ["src/x.py"]}
        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            result = is_usable_snapshot(snapshot, [])
        assert result is False
        assert any(r.levelno == logging.DEBUG for r in caplog.records)

    def test_no_file_overlap_logs_debug(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """is_usable_snapshot logs at DEBUG when snapshot files and changed files do not overlap."""
        snapshot = {"timestamp": _fresh_ts(), "files_in_scope": ["src/a.py"]}
        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            result = is_usable_snapshot(snapshot, ["src/b.py"])
        assert result is False
        assert any(r.levelno == logging.DEBUG for r in caplog.records)

    def test_usable_snapshot_logs_debug(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """is_usable_snapshot logs at DEBUG when snapshot is accepted."""
        snapshot = {"timestamp": _fresh_ts(), "files_in_scope": ["src/x.py"]}
        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            result = is_usable_snapshot(snapshot, ["src/x.py"])
        assert result is True
        assert any(r.levelno == logging.DEBUG for r in caplog.records)

# c:\temp\pgmcp\tests\mcp_server\unit\managers\test_state_version_validator.py
# template=unit_test version=8825c0bb created=2026-07-20T21:18Z updated=2026-07-20T23:20Z
"""
Unit tests for mcp_server.managers.state_version_validator.

Unit tests for StateVersionValidator covering CQS validation and backup.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.managers.state_version_validator]
@responsibilities:
    - Test StateVersionValidator validate_file (Query)
    - Test StateVersionValidator backup_file (Command)
"""

import json
from pathlib import Path

import pytest

from mcp_server.core.exceptions import (
    PlanningVersionMismatchError,
    StateCorruptedError,
    StateNotFoundError,
    StateVersionMismatchError,
)
from mcp_server.managers.state_version_validator import StateVersionValidator


class TestStateVersionValidator:
    """Test suite for state_version_validator."""

    @pytest.fixture
    def validator(self) -> StateVersionValidator:
        """Fixture providing validator instance."""
        return StateVersionValidator()

    def test_state_version_validator_missing_raises_state_not_found(
        self, validator: StateVersionValidator, tmp_path: Path
    ) -> None:
        """Verify that validating a missing file raises StateNotFoundError."""
        missing_file = tmp_path / "non_existent.json"

        with pytest.raises(StateNotFoundError) as exc_info:
            validator.validate_file(missing_file, expected_version="1.0.0")

        assert exc_info.value.file_path == str(missing_file)
        assert "State file does not exist" in str(exc_info.value)

    def test_state_version_validator_corrupt_raises_state_corrupted_error(
        self, validator: StateVersionValidator, tmp_path: Path
    ) -> None:
        """Verify that validating a malformed JSON file raises StateCorruptedError."""
        corrupt_file = tmp_path / "corrupt.json"
        corrupt_file.write_text("{invalid json", encoding="utf-8")

        with pytest.raises(StateCorruptedError) as exc_info:
            validator.validate_file(corrupt_file, expected_version="1.0.0")

        assert exc_info.value.file_path == str(corrupt_file)
        assert "Corrupted or malformed JSON" in str(exc_info.value)

    def test_state_version_validator_not_dict_raises_state_corrupted_error(
        self, validator: StateVersionValidator, tmp_path: Path
    ) -> None:
        """Verify that a state file containing a JSON list instead
        of a dict raises StateCorruptedError.
        """
        list_file = tmp_path / "list.json"
        list_file.write_text("[1, 2, 3]", encoding="utf-8")

        with pytest.raises(StateCorruptedError) as exc_info:
            validator.validate_file(list_file, expected_version="1.0.0")

        assert exc_info.value.file_path == str(list_file)
        assert "must be a JSON object" in str(exc_info.value)

    def test_state_version_validator_mismatch_raises_state_version_mismatch_error(
        self, validator: StateVersionValidator, tmp_path: Path
    ) -> None:
        """Verify that validating state.json with a mismatched version
        raises StateVersionMismatchError.
        """
        mismatch_file = tmp_path / "state.json"
        mismatch_file.write_text(json.dumps({"schema_version": "0.9.0"}), encoding="utf-8")

        with pytest.raises(StateVersionMismatchError) as exc_info:
            validator.validate_file(mismatch_file, expected_version="1.0.0", is_planning=False)

        assert exc_info.value.file_path == str(mismatch_file)
        assert exc_info.value.actual_version == "0.9.0"
        assert exc_info.value.expected_version == "1.0.0"

    def test_state_version_validator_planning_mismatch_raises_planning_version_mismatch_error(
        self, validator: StateVersionValidator, tmp_path: Path
    ) -> None:
        """Verify that validating deliverables.json with a mismatched
        version raises PlanningVersionMismatchError.
        """
        mismatch_file = tmp_path / "deliverables.json"
        mismatch_file.write_text(json.dumps({"schema_version": "0.9.0"}), encoding="utf-8")

        with pytest.raises(PlanningVersionMismatchError) as exc_info:
            validator.validate_file(mismatch_file, expected_version="1.0.0", is_planning=True)

        assert exc_info.value.file_path == str(mismatch_file)
        assert exc_info.value.actual_version == "0.9.0"
        assert exc_info.value.expected_version == "1.0.0"

    def test_state_version_validator_valid_file_passes(
        self, validator: StateVersionValidator, tmp_path: Path
    ) -> None:
        """Verify that a valid file with matching version does not raise any error."""
        valid_file = tmp_path / "valid.json"
        valid_file.write_text(json.dumps({"schema_version": "1.0.0"}), encoding="utf-8")

        # Should not raise any exception
        validator.validate_file(valid_file, expected_version="1.0.0")

    def test_state_version_validator_backup_file_renames_to_bak(
        self, validator: StateVersionValidator, tmp_path: Path
    ) -> None:
        """Verify that backup_file renames the file to .bak and overwrites existing backups."""
        test_file = tmp_path / "state.json"
        test_file.write_text("original content", encoding="utf-8")

        # Test basic rename
        validator.backup_file(test_file)

        backup_file = tmp_path / "state.json.bak"
        assert not test_file.exists()
        assert backup_file.exists()
        assert backup_file.read_text(encoding="utf-8") == "original content"

        # Test overwrite of existing backup
        test_file2 = tmp_path / "state.json"
        test_file2.write_text("new content", encoding="utf-8")

        validator.backup_file(test_file2)
        assert not test_file2.exists()
        assert backup_file.exists()
        assert backup_file.read_text(encoding="utf-8") == "new content"

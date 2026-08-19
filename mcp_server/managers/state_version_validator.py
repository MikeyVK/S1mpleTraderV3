# c:\temp\pgmcp\mcp_server\managers\state_version_validator.py
# template=service version=5d5b489a created=2026-07-20T21:19Z updated=2026-07-20T23:25Z
"""StateVersionValidator service module.

Validator service for dynamic state files schema versions and corruptions.

@layer: Managers
@dependencies: [Path, json, typing]
@responsibilities:
    - Validate dynamic state file schema versions
    - Detect malformed JSON and raise corrupted errors
    - Command file backup to a .bak suffix on error
"""

import json
import logging
from pathlib import Path

from mcp_server.core.exceptions import (
    PlanningVersionMismatchError,
    StateCorruptedError,
    StateNotFoundError,
    StateVersionMismatchError,
)

logger = logging.getLogger(__name__)


class StateVersionValidator:
    """Validator service for dynamic state files schema versions and corruptions."""

    def validate_file(
        self,
        file_path: Path,
        expected_version: str,
        is_planning: bool = False,
    ) -> None:
        """Read and validate the version and syntax of a state file (Query).

        Does not mutate the filesystem.

        Raises:
            StateNotFoundError: If the file does not exist.
            StateCorruptedError: If JSON decoding or base schema validation fails.
            StateVersionMismatchError: If the version field does not match expected_version.
            PlanningVersionMismatchError: If deliverables.json version does
                not match expected_version.
        """
        if not file_path.exists():
            raise StateNotFoundError(f"State file does not exist: {file_path.name}", str(file_path))

        try:
            content = file_path.read_text(encoding="utf-8")
            data = json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            raise StateCorruptedError(
                f"Corrupted or malformed JSON in state file: {e}", str(file_path)
            ) from e

        if not isinstance(data, dict):
            raise StateCorruptedError("State file content must be a JSON object", str(file_path))

        actual_version = data.get("schema_version")
        if actual_version != expected_version:
            msg = f"Schema version mismatch. Expected: {expected_version}, Actual: {actual_version}"
            if is_planning:
                raise PlanningVersionMismatchError(
                    message=msg,
                    file_path=str(file_path),
                    actual_version=str(actual_version),
                    expected_version=expected_version,
                )
            raise StateVersionMismatchError(
                message=msg,
                file_path=str(file_path),
                actual_version=str(actual_version),
                expected_version=expected_version,
            )

    def backup_file(self, file_path: Path) -> None:
        """Rename the invalid file at file_path to file_path.bak (Command).

        If a backup file already exists, it is overwritten.
        """
        if file_path.exists():
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            if backup_path.exists():
                try:
                    backup_path.unlink()
                except OSError as e:
                    logger.warning(f"Failed to delete existing backup file: {e}")
            try:
                file_path.rename(backup_path)
            except OSError as e:
                logger.error(f"Failed to rename file {file_path} to {backup_path}: {e}")
                raise

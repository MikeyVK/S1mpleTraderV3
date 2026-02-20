"""DeliverableChecker — structural validation of issue deliverables (Issue #229).

Validates deliverable specs declared in projects.json ``validates`` entries.
Supported check types:

    file_exists     File must be present at relative *file* path.
    contains_text   File must contain *text* substring.
    absent_text     File must NOT contain *text* substring.
    key_path        JSON/YAML file must contain dot-notation *path*.

All ``file`` paths are resolved relative to *workspace_root*.

Quality Requirements:
- Pyright: strict mode passing
- Ruff: all configured rules passing
- Coverage: 100% for this module
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


class DeliverableCheckError(ValueError):
    """Raised when a deliverable validation check fails.

    The error message always contains the deliverable ID for tracing.
    """


class DeliverableChecker:
    """Runs structural checks on deliverable specs from projects.json.

    Attributes:
        _workspace_root: Absolute root path; all file paths resolved from here.
    """

    def __init__(self, workspace_root: Path) -> None:
        """Initialise with *workspace_root* as the file resolution base.

        Args:
            workspace_root: Absolute directory used to resolve relative paths
                in deliverable specs.
        """
        self._workspace_root = workspace_root

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self, deliverable_id: str, validates: dict) -> None:
        """Validate one deliverable spec.

        Args:
            deliverable_id: Human-readable ID for error messages (e.g. "D1.1").
            validates: Spec dict with at minimum a ``type`` key.

        Raises:
            DeliverableCheckError: When the check fails.
            ValueError: When ``type`` is unknown or required keys are missing.
        """
        check_type: str = validates.get("type", "")
        dispatch = {
            "file_exists": self._check_file_exists,
            "file_glob": self._check_file_glob,
            "contains_text": self._check_contains_text,
            "absent_text": self._check_absent_text,
            "key_path": self._check_key_path,
        }
        handler = dispatch.get(check_type)
        if handler is None:
            raise ValueError(
                f"[{deliverable_id}] Unknown check type: '{check_type}'. "
                f"Valid types: {list(dispatch)}"
            )
        handler(deliverable_id, validates)

    # ------------------------------------------------------------------
    # Private check handlers
    # ------------------------------------------------------------------

    def _resolve(self, relative_file: str) -> Path:
        """Resolve *relative_file* against workspace root.

        Args:
            relative_file: Slash-separated path relative to workspace root.

        Returns:
            Absolute Path.
        """
        return self._workspace_root / Path(relative_file)

    def _check_file_exists(self, deliverable_id: str, spec: dict) -> None:
        """Raise if file at spec['file'] does not exist.

        Args:
            deliverable_id: ID for error message.
            spec: Must contain ``file`` key.

        Raises:
            DeliverableCheckError: File not found.
        """
        path = self._resolve(spec["file"])
        if not path.exists():
            raise DeliverableCheckError(
                f"[{deliverable_id}] file_exists FAILED: '{spec['file']}' not found "
                f"(resolved: {path})"
            )

    def _check_file_glob(self, deliverable_id: str, spec: dict) -> None:
        """Raise if no files match spec['pattern'] inside spec['dir'].

        Args:
            deliverable_id: ID for error message.
            spec: Must contain ``dir`` and ``pattern`` keys.
                  ``dir`` is relative to workspace root; ``pattern`` is a glob expression.

        Raises:
            DeliverableCheckError: No matching files found.
        """
        base = self._workspace_root / Path(spec["dir"])
        pattern: str = spec["pattern"]
        matches = list(base.glob(pattern))
        if not matches:
            raise DeliverableCheckError(
                f"[{deliverable_id}] file_glob FAILED: no files matching '{pattern}' "
                f"in '{spec['dir']}' (resolved: {base})"
            )

    def _check_contains_text(self, deliverable_id: str, spec: dict) -> None:
        """Raise if file at spec['file'] does not contain spec['text'].

        Args:
            deliverable_id: ID for error message.
            spec: Must contain ``file`` and ``text`` keys.

        Raises:
            DeliverableCheckError: File missing or text not found.
        """
        path = self._resolve(spec["file"])
        if not path.exists():
            raise DeliverableCheckError(
                f"[{deliverable_id}] contains_text FAILED: '{spec['file']}' not found"
            )
        content = path.read_text(encoding="utf-8")
        expected: str = spec["text"]
        if expected not in content:
            raise DeliverableCheckError(
                f"[{deliverable_id}] contains_text FAILED: "
                f"'{expected}' not found in '{spec['file']}'"
            )

    def _check_absent_text(self, deliverable_id: str, spec: dict) -> None:
        """Raise if file at spec['file'] CONTAINS spec['text'].

        Args:
            deliverable_id: ID for error message.
            spec: Must contain ``file`` and ``text`` keys.

        Raises:
            DeliverableCheckError: File missing or forbidden text present.
        """
        path = self._resolve(spec["file"])
        if not path.exists():
            raise DeliverableCheckError(
                f"[{deliverable_id}] absent_text FAILED: '{spec['file']}' not found"
            )
        content = path.read_text(encoding="utf-8")
        forbidden: str = spec["text"]
        if forbidden in content:
            raise DeliverableCheckError(
                f"[{deliverable_id}] absent_text FAILED: "
                f"'{forbidden}' found in '{spec['file']}' (must be absent)"
            )

    def _check_key_path(self, deliverable_id: str, spec: dict) -> None:
        """Raise if dot-notation path spec['path'] is missing from JSON/YAML.

        Args:
            deliverable_id: ID for error message.
            spec: Must contain ``file`` and ``path`` keys.
                  ``path`` is dot-separated (e.g. "229.planning_deliverables").

        Raises:
            DeliverableCheckError: File missing or key path absent.
        """
        path = self._resolve(spec["file"])
        if not path.exists():
            raise DeliverableCheckError(
                f"[{deliverable_id}] key_path FAILED: '{spec['file']}' not found"
            )
        content = path.read_text(encoding="utf-8")
        suffix = path.suffix.lower()
        data: Any = json.loads(content) if suffix == ".json" else yaml.safe_load(content)

        key_path: str = spec["path"]
        current: Any = data
        for segment in key_path.split("."):
            if not isinstance(current, dict) or segment not in current:
                raise DeliverableCheckError(
                    f"[{deliverable_id}] key_path FAILED: "
                    f"'{key_path}' not found in '{spec['file']}' "
                    f"(missing at segment '{segment}')"
                )
            current = current[segment]

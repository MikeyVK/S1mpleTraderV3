"""WorkphasesConfig — reader for workphases.yaml exit_requires/entry_expects.

Provides structured access to per-phase deliverable gate declarations
defined in .st3/workphases.yaml (Issue #229).

Schema extension (optional fields per phase):
    exit_requires:
      - key: "planning_deliverables"
        description: "TDD cycle breakdown"
    entry_expects:
      - key: "planning_deliverables"
        description: "Expected from planning phase"

Quality Requirements:
- Pyright: strict mode passing
- Ruff: all configured rules passing
- Coverage: 100% for this module
"""

from __future__ import annotations

from pathlib import Path

import yaml


class WorkphasesConfig:
    """Read-only accessor for workphases.yaml deliverable gate fields.

    Attributes:
        _data: Parsed YAML content as a dict.
    """

    def __init__(self, path: Path) -> None:
        """Load workphases.yaml from *path*.

        Args:
            path: Absolute or relative path to the workphases.yaml file.

        Raises:
            FileNotFoundError: If *path* does not exist.
            yaml.YAMLError: If the file is not valid YAML.
        """
        with path.open(encoding="utf-8") as fh:
            self._data: dict = yaml.safe_load(fh) or {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_exit_requires(self, phase: str) -> list[dict]:
        """Return the exit_requires list for *phase*, or [] if absent.

        Args:
            phase: Phase name (e.g. "planning", "design").

        Returns:
            List of deliverable gate dicts, empty list when field absent.
        """
        return self._get_phase_field(phase, "exit_requires")

    def get_entry_expects(self, phase: str) -> list[dict]:
        """Return the entry_expects list for *phase*, or [] if absent.

        Args:
            phase: Phase name (e.g. "tdd", "integration").

        Returns:
            List of deliverable gate dicts, empty list when field absent.
        """
        return self._get_phase_field(phase, "entry_expects")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_phase_field(self, phase: str, field: str) -> list[dict]:
        """Return *field* from the *phase* block, or [] when absent.

        Args:
            phase: Phase name key in ``phases`` mapping.
            field: YAML field name ("exit_requires" or "entry_expects").

        Returns:
            Parsed list of dicts; empty list for absent/null values.
        """
        phases: dict = self._data.get("phases", {})
        phase_block: dict = phases.get(phase, {})
        result = phase_block.get(field, [])
        return result if isinstance(result, list) else []

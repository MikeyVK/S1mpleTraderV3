# mcp_server/core/scope_encoder.py
# template=generic version=f35abd82 created=2026-02-15T06:38Z updated=2026-02-21T00:00Z
"""Scope Encoder - Generate commit scopes with strict validation.

Generates git commit scopes in format:
- Phase only: P_RESEARCH
- Phase + subphase: P_TDD_SP_RED
- Phase + cycle + subphase: P_TDD_SP_C1_RED

Validation:
- Phase must exist in workphases.yaml
- sub_phase must be in workphases.yaml[phase].subphases (STRICT)
- Empty subphases list = no subphases allowed
- Actionable error messages (what failed, valid values, example, recovery)
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ScopeEncoder:
    """Encode commit scopes with strict phase and subphase validation."""

    def __init__(self, workphases_path: Path) -> None:
        """Initialize encoder with workphases.yaml path.

        Args:
            workphases_path: Path to workphases.yaml configuration
        """
        self.workphases_path = workphases_path
        self._config: dict[str, Any] | None = None  # Lazy load

    def _load_config(self) -> dict[str, Any]:
        """Load and cache workphases.yaml.

        Returns:
            Parsed config dict with phases structure

        Raises:
            FileNotFoundError: workphases.yaml not found
        """
        if self._config is None:
            with open(self.workphases_path) as f:
                loaded = yaml.safe_load(f)
                self._config = loaded if loaded is not None else {}

        assert self._config is not None  # Type narrowing for Pyright
        return self._config

    def generate_scope(
        self,
        phase: str,
        sub_phase: str | None = None,
        cycle_number: int | None = None,
    ) -> str:
        """Generate commit scope with strict validation.

        Args:
            phase: Workflow phase (research, planning, design, tdd, ...)
            sub_phase: Optional subphase (red, green, refactor, c1, ...)
            cycle_number: Optional cycle number (1, 2, 3, ...)

        Returns:
            Formatted scope string (e.g., "P_TDD_SP_C1_RED")

        Raises:
            ValueError: Invalid phase or sub_phase with actionable message
            FileNotFoundError: workphases.yaml not found

        Examples:
            >>> encoder.generate_scope("research")
            "P_RESEARCH"

            >>> encoder.generate_scope("tdd", "red")
            "P_TDD_SP_RED"

            >>> encoder.generate_scope("tdd", "red", cycle_number=1)
            "P_TDD_SP_C1_RED"
        """
        # 1. Load config
        config = self._load_config()
        phases = config.get("phases", {})

        # 2. Normalize phase (case-insensitive)
        phase_lower = phase.lower()

        # 3. Validate phase exists
        if phase_lower not in phases:
            valid_phases = list(phases.keys())
            raise ValueError(
                f"Unknown workflow phase: '{phase}'\n\n"
                f"Valid phases: {', '.join(valid_phases)}\n\n"
                f"Example:\n"
                f"  git_add_or_commit(\n"
                f'      message="complete research",\n'
                f'      workflow_phase="research"\n'
                f"  )\n\n"
                f"Recovery: Use one of the valid workflow phases listed above."
            )

        phase_config = phases[phase_lower]
        configured_subphases = phase_config.get("subphases", [])

        # 4. Validate sub_phase if provided
        if sub_phase is not None:
            if not configured_subphases:
                raise ValueError(
                    f"Invalid sub_phase '{sub_phase}' for workflow phase '{phase}'\n\n"
                    f"{phase} does not support subphases.\n\n"
                    f"Valid subphases for {phase}: []\n\n"
                    f"Example:\n"
                    f"  git_add_or_commit(\n"
                    f'      message="complete {phase}",\n'
                    f'      workflow_phase="{phase}"\n'
                    f"  )\n\n"
                    f"Recovery: Remove sub_phase parameter."
                )

            if sub_phase not in configured_subphases:
                raise ValueError(
                    f"Invalid sub_phase '{sub_phase}' for workflow phase '{phase}'\n\n"
                    f"Valid subphases for {phase}: {', '.join(configured_subphases)}\n\n"
                    f"Example:\n"
                    f"  git_add_or_commit(\n"
                    f"      message='add user tests',\n"
                    f"      workflow_phase='{phase}',\n"
                    f"      sub_phase='{configured_subphases[0]}'\n"
                    f"  )\n\n"
                    f"Recovery: Use one of the valid subphases listed above."
                )

        # 5. Generate scope string
        phase_upper = phase_lower.upper()

        if sub_phase is None:
            return f"P_{phase_upper}"

        sub_phase_upper = sub_phase.upper()

        if cycle_number is not None:
            return f"P_{phase_upper}_SP_C{cycle_number}_{sub_phase_upper}"

        return f"P_{phase_upper}_SP_{sub_phase_upper}"

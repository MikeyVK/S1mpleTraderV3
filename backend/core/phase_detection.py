# backend/core/phase_detection.py
# template=generic version=f35abd82 created=2026-02-15T06:38Z updated=
"""Phase Detection Utilities.

Provides deterministic workflow phase detection from commit-scope and state.json.
NO type-heuristic guessing - unknown is acceptable outcome.

@layer: Core
@dependencies: [typing, pathlib, json, re, yaml]
@responsibilities:
    - Define PhaseDetectionResult TypedDict schema
    - Parse commit-scope (P_PHASE_SP_SUBPHASE format)
    - Fallback to state.json when commit-scope missing
    - Validate phases against workphases.yaml
    - Return unknown with actionable error when both fail
"""

# Standard library
import json
import logging
import re
from pathlib import Path
from typing import Literal, TypedDict

# Third-party
import yaml

# Project modules


logger = logging.getLogger(__name__)


class PhaseDetectionResult(TypedDict):
    """
    Result of phase detection with source tracking.

    Fields:
        workflow_phase: Phase name (e.g., "tdd", "research", "unknown")
        sub_phase: Optional subphase identifier (e.g., "red", "c1", None)
        source: Where the phase was detected from
        confidence: Confidence level of detection
        raw_scope: Original scope string from commit (if applicable)
        error_message: Actionable recovery instructions when detection fails
    """

    workflow_phase: str
    sub_phase: str | None
    source: Literal["commit-scope", "state.json", "unknown"]
    confidence: Literal["high", "medium", "unknown"]
    raw_scope: str | None
    error_message: str | None


class ScopeDecoder:
    """
    Decoder for workflow phase from commit-scope with deterministic precedence.

    Precedence: commit-scope > state.json > unknown (NO type-heuristic guessing)

    Scope Format:
        - P_PHASE: e.g., P_RESEARCH, P_TDD
        - P_PHASE_SP_SUBPHASE: e.g., P_TDD_SP_RED, P_PLANNING_SP_C1
    """

    # Regex patterns for scope parsing
    SCOPE_PATTERN_WITH_SUBPHASE = re.compile(r"^P_([A-Z]+)_SP_([A-Z0-9_]+)$", re.IGNORECASE)
    SCOPE_PATTERN_PHASE_ONLY = re.compile(r"^P_([A-Z]+)$", re.IGNORECASE)
    # Conventional Commits scope extraction
    COMMIT_SCOPE_PATTERN = re.compile(r"^[a-z]+\(([^)]+)\):", re.IGNORECASE)

    def __init__(
        self,
        state_path: Path | None = None,
        workphases_path: Path | None = None,
    ) -> None:
        """
        Initialize ScopeDecoder with optional state.json and workphases.yaml paths.

        Args:
            state_path: Path to state.json file (defaults to .st3/state.json)
            workphases_path: Path to workphases.yaml file (defaults to .st3/workphases.yaml)
        """
        self.state_path = state_path or Path(".st3/state.json")
        self.workphases_path = workphases_path or Path(".st3/workphases.yaml")
        self._valid_phases: set[str] | None = None

    def detect_phase(
        self,
        commit_message: str | None,
        fallback_to_state: bool = True,
    ) -> PhaseDetectionResult:
        """
        Detect workflow phase with deterministic precedence.

        Precedence chain: commit-scope > state.json > unknown

        Args:
            commit_message: Commit message to parse (Conventional Commits format)
            fallback_to_state: Whether to fallback to state.json if scope missing

        Returns:
            PhaseDetectionResult with detected phase or unknown

        Notes:
            - Never raises exceptions (graceful degradation)
            - Returns unknown with actionable error_message when all sources fail
            - NO type-heuristic guessing from commit type
            - Validates phase names against workphases.yaml
        """
        # Try commit-scope first (PRIMARY for context tools)
        if commit_message:
            scope_result = self._parse_commit_scope(commit_message)
            if scope_result:
                return scope_result

        # Fallback to state.json (SECONDARY)
        if fallback_to_state:
            state_result = self._read_state_json()
            if state_result:
                return state_result

        # Unknown fallback (TERTIARY)
        return self._unknown_fallback()

    def _parse_commit_scope(self, commit_message: str) -> PhaseDetectionResult | None:
        """
        Parse workflow phase from commit scope (Conventional Commits).

        Format: type(P_PHASE_SP_SUBPHASE): message

        Returns:
            PhaseDetectionResult if scope matches pattern AND phase is valid, None otherwise

        Notes:
            - Validates phase against workphases.yaml
            - Invalid phases are rejected (returns None for fallback)
        """
        # Extract scope from commit message
        scope_match = self.COMMIT_SCOPE_PATTERN.match(commit_message)
        if not scope_match:
            return None

        scope = scope_match.group(1)

        # Try P_PHASE_SP_SUBPHASE format first
        match_with_subphase = self.SCOPE_PATTERN_WITH_SUBPHASE.match(scope)
        if match_with_subphase:
            phase = match_with_subphase.group(1).lower()
            subphase = match_with_subphase.group(2).lower()

            # Validate phase against workphases.yaml
            valid_phases = self._load_valid_phases()
            if valid_phases and phase not in valid_phases:
                logger.debug(
                    f"Invalid phase '{phase}' in commit-scope '{scope}'. "
                    f"Valid phases: {sorted(valid_phases)}"
                )
                return None

            return {
                "workflow_phase": phase,
                "sub_phase": subphase,
                "source": "commit-scope",
                "confidence": "high",
                "raw_scope": scope,
                "error_message": None,
            }

        # Try P_PHASE format (no subphase)
        match_phase_only = self.SCOPE_PATTERN_PHASE_ONLY.match(scope)
        if match_phase_only:
            phase = match_phase_only.group(1).lower()

            # Validate phase against workphases.yaml
            valid_phases = self._load_valid_phases()
            if valid_phases and phase not in valid_phases:
                logger.debug(
                    f"Invalid phase '{phase}' in commit-scope '{scope}'. "
                    f"Valid phases: {sorted(valid_phases)}"
                )
                return None

            return {
                "workflow_phase": phase,
                "sub_phase": None,
                "source": "commit-scope",
                "confidence": "high",
                "raw_scope": scope,
                "error_message": None,
            }

        # Scope exists but doesn't match expected format
        return None

    def _load_valid_phases(self) -> set[str]:
        """
        Load valid phase names from workphases.yaml.

        Returns:
            Set of valid phase names (lowercase)

        Notes:
            - Cached after first load
            - Graceful degradation on missing file
        """
        if self._valid_phases is not None:
            return self._valid_phases

        try:
            if not self.workphases_path.exists():
                logger.warning(f"workphases.yaml not found at {self.workphases_path}")
                self._valid_phases = set()
                return self._valid_phases

            with self.workphases_path.open("r", encoding="utf-8") as f:
                workphases_data = yaml.safe_load(f)

            phases = workphases_data.get("phases", {})
            self._valid_phases = {phase_name.lower() for phase_name in phases}

            logger.debug(f"Loaded {len(self._valid_phases)} valid phases from workphases.yaml")
            return self._valid_phases

        except (OSError, yaml.YAMLError) as e:
            logger.warning(f"Failed to load workphases.yaml: {e}")
            self._valid_phases = set()
            return self._valid_phases

    def _read_state_json(self) -> PhaseDetectionResult | None:
        """
        Read workflow phase from state.json.

        Returns:
            PhaseDetectionResult with medium confidence if state.json exists and has valid phase,
            None otherwise (graceful degradation on missing file, malformed JSON, or invalid phase)

        Notes:
            - Validates phase against workphases.yaml
            - Invalid phases are rejected (returns None for unknown fallback)
        """
        try:
            if not self.state_path.exists():
                return None

            with self.state_path.open("r", encoding="utf-8") as f:
                state_data = json.load(f)

            current_phase = state_data.get("current_phase")
            if not current_phase:
                return None

            # Validate phase against workphases.yaml
            valid_phases = self._load_valid_phases()
            if valid_phases and current_phase.lower() not in valid_phases:
                logger.warning(
                    f"Invalid phase '{current_phase}' in state.json. "
                    f"Valid phases: {sorted(valid_phases)}"
                )
                return None

            return {
                "workflow_phase": current_phase,
                "sub_phase": None,
                "source": "state.json",
                "confidence": "medium",
                "raw_scope": None,
                "error_message": None,
            }
        except (OSError, json.JSONDecodeError) as e:
            # Graceful degradation - log but don't raise
            logger.debug(f"Failed to read state.json: {e}")
            return None

    def _unknown_fallback(self) -> PhaseDetectionResult:
        """
        Return unknown phase with actionable error message.

        Returns:
            PhaseDetectionResult with workflow_phase="unknown"
        """
        return {
            "workflow_phase": "unknown",
            "sub_phase": None,
            "source": "unknown",
            "confidence": "unknown",
            "raw_scope": None,
            "error_message": (
                "Phase detection failed. "
                "Recovery: Run transition_phase(to_phase='<phase>') "
                "or commit with scope 'type(P_PHASE): message'. "
                "Valid phases: research, planning, design, tdd, integration, "
                "documentation, coordination"
            ),
        }

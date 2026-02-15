# backend/core/phase_detection.py
# template=generic version=f35abd82 created=2026-02-15T06:38Z updated=
"""Phase Detection Utilities.

Provides deterministic workflow phase detection from commit-scope and state.json.
NO type-heuristic guessing - unknown is acceptable outcome.

@layer: Core
@dependencies: [typing, pathlib, json, re]
@responsibilities:
    - Define PhaseDetectionResult TypedDict schema
    - Parse commit-scope (P_PHASE_SP_SUBPHASE format)
    - Fallback to state.json when commit-scope missing
    - Return unknown with actionable error when both fail
"""

# Standard library
import logging
from typing import Literal, Optional, TypedDict

# Third-party

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
    sub_phase: Optional[str]
    source: Literal["commit-scope", "state.json", "unknown"]
    confidence: Literal["high", "medium", "unknown"]
    raw_scope: Optional[str]
    error_message: Optional[str]

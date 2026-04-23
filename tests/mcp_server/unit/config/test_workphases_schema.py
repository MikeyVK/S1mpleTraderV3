# tests\mcp_server\unit\config\test_workphases_schema.py
# template=unit_test version=3d15d309 created=2026-04-09T17:44Z updated=
"""
Unit tests for mcp_server.config.schemas.workphases.

Unit tests for workphases schema extensions (issue #283 C1)

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.config.schemas.workphases]
@responsibilities:
    - Test TestWorkphasesSchema functionality
    - Verify PhaseDefinition.terminal field, WorkphasesConfig validator, get_terminal_phase()
    - None
"""

# Standard library

# Third-party
import pytest
from pydantic import ValidationError

# Project modules
from mcp_server.config.schemas.workphases import PhaseDefinition, WorkphasesConfig


def _minimal_workphases(**extra: PhaseDefinition) -> WorkphasesConfig:
    """Minimal valid WorkphasesConfig with exactly one terminal phase."""
    phases: dict[str, PhaseDefinition] = {
        "planning": PhaseDefinition(display_name="Planning"),
        "ready": PhaseDefinition(display_name="Ready", terminal=True),
    }
    phases.update(extra)
    return WorkphasesConfig(phases=phases)


class TestPhaseDefinitionTerminalField:
    """PhaseDefinition.terminal: bool = False field (C1 deliverable)."""

    def test_terminal_defaults_to_false(self) -> None:
        phase = PhaseDefinition(display_name="Planning")
        assert phase.terminal is False

    def test_terminal_can_be_set_true(self) -> None:
        phase = PhaseDefinition(display_name="Ready", terminal=True)
        assert phase.terminal is True

    def test_terminal_field_is_bool(self) -> None:
        phase = PhaseDefinition(display_name="Ready", terminal=True)
        assert isinstance(phase.terminal, bool)


class TestWorkphasesConfigValidator:
    """WorkphasesConfig.validate_single_terminal_phase model_validator (C1 deliverable)."""

    def test_valid_single_terminal_phase_passes(self) -> None:
        config = _minimal_workphases()
        assert config is not None

    def test_no_terminal_phase_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            WorkphasesConfig(
                phases={
                    "planning": PhaseDefinition(display_name="Planning"),
                    "research": PhaseDefinition(display_name="Research"),
                }
            )
        assert "terminal" in str(exc_info.value).lower()

    def test_two_terminal_phases_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            WorkphasesConfig(
                phases={
                    "ready": PhaseDefinition(display_name="Ready", terminal=True),
                    "done": PhaseDefinition(display_name="Done", terminal=True),
                }
            )
        assert "terminal" in str(exc_info.value).lower()

    def test_empty_phases_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            WorkphasesConfig(phases={})
        assert "terminal" in str(exc_info.value).lower()


class TestWorkphasesConfigGetTerminalPhase:
    """WorkphasesConfig.get_terminal_phase() query method (C1 deliverable)."""

    def test_returns_terminal_phase_name(self) -> None:
        config = _minimal_workphases()
        assert config.get_terminal_phase() == "ready"

    def test_returns_correct_name_when_phase_is_first(self) -> None:
        config = WorkphasesConfig(
            phases={
                "ready": PhaseDefinition(display_name="Ready", terminal=True),
                "planning": PhaseDefinition(display_name="Planning"),
            }
        )
        assert config.get_terminal_phase() == "ready"

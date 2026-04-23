# tests/mcp_server/unit/config/test_validator_c3.py
# template=unit_test version=3d15d309 created=2026-04-09T19:17Z updated=
"""
Unit tests for mcp_server.config.validator.

Tests for ConfigValidator._validate_merge_policy_phase cross-validation (C3 issue #283)

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.config.validator, mcp_server.schemas]
@responsibilities:
    - Test TestConfigValidatorC3 functionality
    - Verify merge policy phase validation
    - Verify merge policy cross-validation raises ConfigError for unknown phases
"""

# Standard library
from typing import Any

# Third-party
import pytest

from mcp_server.config.schemas.phase_contracts_config import MergePolicy
from mcp_server.config.schemas.workphases import PhaseDefinition

# Project modules
from mcp_server.config.validator import ConfigValidator
from mcp_server.core.exceptions import ConfigError
from mcp_server.schemas import (
    ArtifactRegistryConfig,
    OperationPoliciesConfig,
    PhaseContractsConfig,
    ProjectStructureConfig,
    WorkflowConfig,
    WorkphasesConfig,
)


def _workphases(phases: list[str] = None, terminal: str = "ready") -> WorkphasesConfig:  # type: ignore[assignment]
    phase_dict: dict[str, PhaseDefinition] = {}
    for p in phases or ["planning", "implementation"]:
        phase_dict[p] = PhaseDefinition(display_name=p.capitalize())
    phase_dict[terminal] = PhaseDefinition(display_name=terminal.capitalize(), terminal=True)
    return WorkphasesConfig(version="1.0", phases=phase_dict)


def _phase_contracts(pr_allowed_phase: str = "ready") -> PhaseContractsConfig:
    return PhaseContractsConfig(
        merge_policy=MergePolicy(pr_allowed_phase=pr_allowed_phase),
        workflows={},
    )


def _stub_validate_startup_args(
    pr_allowed_phase: str = "ready",
    workphases: WorkphasesConfig | None = None,
) -> dict[str, Any]:
    return {
        "policies": OperationPoliciesConfig(version="1.0", operations={}),  # type: ignore[call-arg]
        "workflow": WorkflowConfig(version="1.0", workflows={}),
        "structure": ProjectStructureConfig(version="1.0", directories={}),  # type: ignore[call-arg]
        "artifact": ArtifactRegistryConfig(version="1.0", artifact_types=[]),
        "phase_contracts": _phase_contracts(pr_allowed_phase),
        "workphases": workphases or _workphases(),
    }


class TestConfigValidatorC3:
    """Test suite for ConfigValidator._validate_merge_policy_phase (C3 issue #283)."""

    def test_validate_merge_policy_phase_raises_for_unknown_phase(
        self,
    ) -> None:
        """_validate_merge_policy_phase raises ConfigError for unknown pr_allowed_phase."""
        # Arrange
        phase_contracts = _phase_contracts(pr_allowed_phase="nonexistent_phase")
        workphases = _workphases()

        # Act / Assert
        with pytest.raises(ConfigError, match="nonexistent_phase"):
            ConfigValidator()._validate_merge_policy_phase(  # pyright: ignore[reportPrivateUsage]
                phase_contracts=phase_contracts,
                known_phases=set(workphases.phases),
            )

    def test_validate_merge_policy_phase_ok_for_known_phase(
        self,
    ) -> None:
        """_validate_merge_policy_phase does not raise for a known workphase."""
        # Arrange
        phase_contracts = _phase_contracts(pr_allowed_phase="ready")
        workphases = _workphases()

        # Act (no exception expected)
        ConfigValidator()._validate_merge_policy_phase(  # pyright: ignore[reportPrivateUsage]
            phase_contracts=phase_contracts,
            known_phases=set(workphases.phases),
        )

    def test_validate_startup_raises_for_invalid_merge_policy_phase(
        self,
    ) -> None:
        """validate_startup raises ConfigError for invalid pr_allowed_phase."""
        # Arrange
        kwargs = _stub_validate_startup_args(pr_allowed_phase="unknown_phase")

        # Act / Assert
        with pytest.raises(ConfigError, match="unknown_phase"):
            ConfigValidator().validate_startup(**kwargs)

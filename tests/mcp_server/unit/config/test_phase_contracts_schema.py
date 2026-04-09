# tests\mcp_server\unit\config\test_phase_contracts_schema.py
# template=unit_test version=3d15d309 created=2026-04-09T17:44Z updated=
"""
Unit tests for mcp_server.config.schemas.phase_contracts_config.

Unit tests for phase_contracts schema extensions (issue #283 C1)

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.config.schemas.phase_contracts_config]
@responsibilities:
    - Test TestPhaseContractsSchema functionality
    - Verify BranchLocalArtifact, MergePolicy models, PhaseContractsConfig.merge_policy
      required field, get_pr_allowed_phase()
    - None
"""

# Standard library

# Third-party
import pytest
from pydantic import ValidationError

# Project modules
from mcp_server.config.schemas.phase_contracts_config import (
    BranchLocalArtifact,
    MergePolicy,
    PhaseContractsConfig,
)


def _minimal_policy(pr_allowed_phase: str = "ready") -> MergePolicy:
    return MergePolicy(pr_allowed_phase=pr_allowed_phase, branch_local_artifacts=[])


def _minimal_contracts(pr_allowed_phase: str = "ready") -> PhaseContractsConfig:
    return PhaseContractsConfig(
        merge_policy=_minimal_policy(pr_allowed_phase),
        workflows={},
    )


class TestBranchLocalArtifact:
    """BranchLocalArtifact Pydantic model (C1 deliverable)."""

    def test_requires_path(self) -> None:
        with pytest.raises(ValidationError):
            BranchLocalArtifact(reason="no path")  # type: ignore[call-arg]

    def test_requires_reason(self) -> None:
        with pytest.raises(ValidationError):
            BranchLocalArtifact(path=".st3/state.json")  # type: ignore[call-arg]

    def test_valid_construction(self) -> None:
        artifact = BranchLocalArtifact(path=".st3/state.json", reason="branch-local MCP state")
        assert artifact.path == ".st3/state.json"
        assert artifact.reason == "branch-local MCP state"


class TestMergePolicy:
    """MergePolicy Pydantic model (C1 deliverable)."""

    def test_requires_pr_allowed_phase(self) -> None:
        with pytest.raises(ValidationError):
            MergePolicy()  # type: ignore[call-arg]

    def test_branch_local_artifacts_defaults_empty(self) -> None:
        policy = MergePolicy(pr_allowed_phase="ready")
        assert policy.branch_local_artifacts == []

    def test_branch_local_artifacts_accepts_list(self) -> None:
        policy = MergePolicy(
            pr_allowed_phase="ready",
            branch_local_artifacts=[
                BranchLocalArtifact(path=".st3/state.json", reason="state"),
            ],
        )
        assert len(policy.branch_local_artifacts) == 1


class TestPhaseContractsConfigMergePolicy:
    """PhaseContractsConfig.merge_policy required + get_pr_allowed_phase() (C1 deliverable)."""

    def test_merge_policy_required(self) -> None:
        """PhaseContractsConfig without merge_policy must raise ValidationError."""
        with pytest.raises(ValidationError):
            PhaseContractsConfig(workflows={})  # type: ignore[call-arg]

    def test_merge_policy_accepted_on_construction(self) -> None:
        config = _minimal_contracts()
        assert config.merge_policy.pr_allowed_phase == "ready"

    def test_extra_fields_still_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            PhaseContractsConfig(
                merge_policy=_minimal_policy(),
                workflows={},
                unknown_field="x",
            )

    def test_get_pr_allowed_phase_returns_configured_value(self) -> None:
        config = _minimal_contracts(pr_allowed_phase="ready")
        assert config.get_pr_allowed_phase() == "ready"

    def test_get_pr_allowed_phase_reflects_policy(self) -> None:
        config = _minimal_contracts(pr_allowed_phase="validation")
        assert config.get_pr_allowed_phase() == "validation"

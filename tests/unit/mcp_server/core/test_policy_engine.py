"""Tests for PolicyEngine - Phase A.1 (RED phase)."""
import pytest
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp_server.core.policy_engine import (
    PolicyEngine,
    DecisionContext,
    PolicyDecision,
)


@dataclass
class MockProjectPlan:
    """Mock project plan for testing."""
    issue_number: int
    required_phases: list[str]
    current_phase: str


class TestPolicyEngineDecide:
    """Test PolicyEngine.decide() core validation."""

    def test_decide_with_valid_project_plan(self):
        """Should allow operation when project plan exists and phase matches."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="commit",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(
                issue_number=30,
                required_phases=["discovery", "planning", "tdd"],
                current_phase="tdd"
            ),
            phase="tdd",
            metadata={"message": "green: Implement PolicyEngine"}
        )
        
        decision = engine.decide(ctx)
        
        assert decision.allowed is True
        assert decision.requires_human_approval is False
        assert "Valid commit" in decision.reason or "TDD phase prefix" in decision.reason

    def test_decide_without_project_plan_requires_approval(self):
        """Should require human approval when no project plan exists."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="commit",
            branch="feature/unknown-branch",
            project_plan=None,
            phase="tdd",
            metadata={"message": "Some commit"}
        )
        
        decision = engine.decide(ctx)
        
        assert decision.allowed is False
        assert decision.requires_human_approval is True
        assert "No project plan" in decision.reason

    def test_decide_with_phase_mismatch_requires_approval(self):
        """Should require approval when phase doesn't match project plan."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="commit",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(
                issue_number=30,
                required_phases=["discovery", "planning", "tdd"],
                current_phase="planning"
            ),
            phase="tdd",
            metadata={"message": "green: Premature implementation"}
        )
        
        decision = engine.decide(ctx)
        
        assert decision.allowed is False
        assert decision.requires_human_approval is True
        assert "Phase mismatch" in decision.reason

    def test_decide_with_phase_not_in_plan_requires_approval(self):
        """Should require approval when phase not in required_phases."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="commit",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(
                issue_number=30,
                required_phases=["discovery", "planning", "tdd"],
                current_phase="integration"
            ),
            phase="integration",
            metadata={"message": "Skip to integration"}
        )
        
        decision = engine.decide(ctx)
        
        assert decision.allowed is False
        assert decision.requires_human_approval is True
        assert "not in required phases" in decision.reason


class TestPolicyEngineDecideCommit:
    """Test PolicyEngine._decide_commit() for git commits."""

    def test_decide_commit_with_tdd_phase_prefix(self):
        """Should allow commits with TDD phase prefixes (red/green/refactor/docs)."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="commit",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(
                issue_number=30,
                required_phases=["tdd"],
                current_phase="tdd"
            ),
            phase="tdd",
            metadata={"message": "green: Implement PolicyEngine"}
        )
        
        decision = engine._decide_commit(ctx)
        
        assert decision.allowed is True
        assert "TDD phase prefix" in decision.reason

    def test_decide_commit_without_phase_prefix_requires_approval(self):
        """Should require approval for commits without phase prefix."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="commit",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(
                issue_number=30,
                required_phases=["tdd"],
                current_phase="tdd"
            ),
            phase="tdd",
            metadata={"message": "Implement PolicyEngine"}  # No prefix!
        )
        
        decision = engine._decide_commit(ctx)
        
        assert decision.allowed is False
        assert decision.requires_human_approval is True
        assert "Missing TDD phase prefix" in decision.reason


class TestPolicyEngineDecideScaffold:
    """Test PolicyEngine._decide_scaffold() for scaffolding operations."""

    def test_decide_scaffold_in_component_phase(self):
        """Should allow scaffolding during component phase."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="scaffold",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(
                issue_number=30,
                required_phases=["component", "tdd"],
                current_phase="component"
            ),
            phase="component",
            metadata={"component_type": "dto", "name": "PolicyDecision"}
        )
        
        decision = engine._decide_scaffold(ctx)
        
        assert decision.allowed is True

    def test_decide_scaffold_in_tdd_phase(self):
        """Should allow scaffolding during TDD phase (tests)."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="scaffold",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(
                issue_number=30,
                required_phases=["tdd"],
                current_phase="tdd"
            ),
            phase="tdd",
            metadata={"component_type": "test", "name": "test_policy_engine"}
        )
        
        decision = engine._decide_scaffold(ctx)
        
        assert decision.allowed is True

    def test_decide_scaffold_in_discovery_phase_requires_approval(self):
        """Should require approval for scaffolding in discovery phase."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="scaffold",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(
                issue_number=30,
                required_phases=["discovery", "planning"],
                current_phase="discovery"
            ),
            phase="discovery",
            metadata={"component_type": "dto"}
        )
        
        decision = engine._decide_scaffold(ctx)
        
        assert decision.allowed is False
        assert decision.requires_human_approval is True


class TestPolicyEngineDecideCreateFile:
    """Test PolicyEngine._decide_create_file() for file creation."""

    def test_decide_create_file_config_allowed(self):
        """Should allow creating config files (YAML, JSON, TOML)."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="create_file",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(issue_number=30, required_phases=["tdd"], current_phase="tdd"),
            phase="tdd",
            metadata={"path": "config/settings.yaml"}
        )
        
        decision = engine._decide_create_file(ctx)
        
        assert decision.allowed is True
        assert "Config file" in decision.reason

    def test_decide_create_file_backend_python_blocked(self):
        """Should block creating Python files in backend/ (must use scaffold)."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="create_file",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(issue_number=30, required_phases=["tdd"], current_phase="tdd"),
            phase="tdd",
            metadata={"path": "backend/core/policy_engine.py"}
        )
        
        decision = engine._decide_create_file(ctx)
        
        assert decision.allowed is False
        assert decision.requires_human_approval is True
        assert "must use scaffold" in decision.reason.lower()

    def test_decide_create_file_test_python_blocked(self):
        """Should block creating test files in tests/ (must use scaffold)."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="create_file",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(issue_number=30, required_phases=["tdd"], current_phase="tdd"),
            phase="tdd",
            metadata={"path": "tests/unit/test_something.py"}
        )
        
        decision = engine._decide_create_file(ctx)
        
        assert decision.allowed is False
        assert decision.requires_human_approval is True

    def test_decide_create_file_script_allowed(self):
        """Should allow creating scripts in scripts/ directory."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="create_file",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(issue_number=30, required_phases=["tdd"], current_phase="tdd"),
            phase="tdd",
            metadata={"path": "scripts/analyze_coverage.py"}
        )
        
        decision = engine._decide_create_file(ctx)
        
        assert decision.allowed is True


class TestPolicyEngineAuditTrail:
    """Test PolicyEngine audit logging."""

    def test_decide_logs_audit_trail(self):
        """Should log all decisions to audit trail."""
        engine = PolicyEngine()
        ctx = DecisionContext(
            operation="commit",
            branch="feature/30-policy-engine-core",
            project_plan=MockProjectPlan(issue_number=30, required_phases=["tdd"], current_phase="tdd"),
            phase="tdd",
            metadata={"message": "green: Test commit"}
        )
        
        decision = engine.decide(ctx)
        
        # Check that audit trail contains this decision
        assert len(engine.audit_trail) > 0
        last_entry = engine.audit_trail[-1]
        assert last_entry["operation"] == "commit"
        assert last_entry["branch"] == "feature/30-policy-engine-core"
        assert last_entry["decision"]["allowed"] == decision.allowed

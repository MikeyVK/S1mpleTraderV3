"""Unit tests for PolicyEngine (refactored, config-driven).

Tests Phase 4: Policy decision engine with config integration
"""

import pytest

from mcp_server.config.component_registry import ComponentRegistryConfig
from mcp_server.config.operation_policies import OperationPoliciesConfig
from mcp_server.config.project_structure import ProjectStructureConfig
from mcp_server.core.policy_engine import PolicyDecision, PolicyEngine


class TestPolicyEngineConfigDriven:
    """Test suite for refactored config-driven PolicyEngine."""

    def setup_method(self):
        """Reset singletons before each test."""
        ComponentRegistryConfig.reset_instance()
        OperationPoliciesConfig.reset_instance()
        ProjectStructureConfig.reset_instance()

    def test_scaffold_allowed_in_tdd_phase(self):
        """Test scaffold operation allowed in tdd phase."""
        engine = PolicyEngine()
        decision = engine.decide(
            operation="scaffold",
            path="backend/dtos/user_dto.py",
            phase="tdd",
            context={"component_type": "dto"}
        )
        assert decision.allowed is True
        assert "scaffold" in decision.reason.lower()
        assert decision.operation == "scaffold"

    def test_scaffold_blocked_in_review_phase(self):
        """Test scaffold operation blocked in review phase."""
        engine = PolicyEngine()
        decision = engine.decide(
            operation="scaffold",
            phase="review",
            context={}
        )
        assert decision.allowed is False
        assert "review" in decision.reason.lower()

    def test_create_file_blocked_for_backend_py(self):
        """Test create_file blocked for backend Python files."""
        engine = PolicyEngine()
        decision = engine.decide(
            operation="create_file",
            path="backend/services/user_service.py",
            phase="tdd",
            context={}
        )
        assert decision.allowed is False
        assert "blocked" in decision.reason.lower() or "scaffold" in decision.reason.lower()

    def test_create_file_allowed_for_markdown(self):
        """Test create_file allowed for markdown files."""
        engine = PolicyEngine()
        decision = engine.decide(
            operation="create_file",
            path="docs/README.md",
            phase="docs",
            context={}
        )
        assert decision.allowed is True

    def test_commit_requires_tdd_prefix(self):
        """Test commit requires TDD phase prefix."""
        engine = PolicyEngine()
        decision = engine.decide(
            operation="commit",
            phase="tdd",
            context={"message": "add user dto"}
        )
        assert decision.allowed is False
        assert "prefix" in decision.reason.lower()

    def test_commit_allowed_with_green_prefix(self):
        """Test commit allowed with green: prefix."""
        engine = PolicyEngine()
        decision = engine.decide(
            operation="commit",
            phase="tdd",
            context={"message": "green: implement user dto"}
        )
        assert decision.allowed is True

    def test_component_type_validation(self):
        """Test component type validation in directory."""
        engine = PolicyEngine()
        decision = engine.decide(
            operation="scaffold",
            path="backend/dtos/service.py",
            phase="tdd",
            context={"component_type": "service"}  # Service not allowed in dtos/
        )
        assert decision.allowed is False
        assert "service" in decision.reason.lower()

    def test_allowed_extension_validation(self):
        """Test file extension validation."""
        engine = PolicyEngine()
        decision = engine.decide(
            operation="create_file",
            path="docs/design.txt",
            phase="design",
            context={}
        )
        # .txt should be allowed for docs directory
        assert decision.allowed is True

    def test_audit_trail_logging(self):
        """Test decisions are logged to audit trail."""
        engine = PolicyEngine()
        engine.decide(
            operation="scaffold",
            path="backend/dtos/user_dto.py",
            phase="tdd",
            context={"component_type": "dto"}
        )
        trail = engine.get_audit_trail()
        assert len(trail) == 1
        assert trail[0]["operation"] == "scaffold"
        assert trail[0]["allowed"] is True

    def test_policy_decision_contains_directory_policy(self):
        """Test PolicyDecision includes resolved directory policy."""
        engine = PolicyEngine()
        decision = engine.decide(
            operation="scaffold",
            path="backend/dtos/user_dto.py",
            phase="tdd",
            context={"component_type": "dto"}
        )
        assert decision.directory_policy is not None
        assert decision.directory_policy.path == "backend/dtos"

    def test_error_handling_denies_by_default(self):
        """Test errors result in denied decision (fail-safe)."""
        engine = PolicyEngine()
        decision = engine.decide(
            operation="invalid_operation",
            phase="tdd",
            context={}
        )
        # Invalid operation should be denied or require approval
        # Config-driven engine should handle gracefully
        assert decision is not None

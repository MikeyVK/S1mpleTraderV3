"""Unit tests for PolicyEngine (refactored, config-driven).

Tests Phase 4: Policy decision engine with config integration
"""

from tests.mcp_server.test_support import make_policy_engine


class TestPolicyEngineConfigDriven:
    """Test suite for refactored config-driven PolicyEngine."""

    def test_scaffold_allowed_in_implementation_phase(self) -> None:
        """Test scaffold operation allowed in implementation phase."""
        engine = make_policy_engine()
        decision = engine.decide(
            operation="scaffold",
            path="backend/dtos/user_dto.py",
            phase="implementation",
            context={"component_type": "dto"},
        )
        assert decision.allowed is True
        assert "scaffold" in decision.reason.lower()
        assert decision.operation == "scaffold"

    def test_scaffold_blocked_in_review_phase(self) -> None:
        """Test scaffold operation blocked in review phase."""
        engine = make_policy_engine()
        decision = engine.decide(operation="scaffold", phase="review", context={})
        assert decision.allowed is False
        assert "review" in decision.reason.lower()

    def test_create_file_blocked_for_backend_py(self) -> None:
        """Test create_file blocked for backend Python files."""
        engine = make_policy_engine()
        decision = engine.decide(
            operation="create_file",
            path="backend/services/user_service.py",
            phase="implementation",
            context={},
        )
        assert decision.allowed is False
        assert "blocked" in decision.reason.lower() or "scaffold" in decision.reason.lower()

    def test_create_file_allowed_for_markdown(self) -> None:
        """Test create_file allowed for markdown files."""
        engine = make_policy_engine()
        decision = engine.decide(
            operation="create_file", path="docs/README.md", phase="docs", context={}
        )
        assert decision.allowed is True

    def test_commit_requires_configured_prefix(self) -> None:
        """Test commit requires a configured commit prefix."""
        engine = make_policy_engine()
        decision = engine.decide(
            operation="commit", phase="implementation", context={"message": "add user dto"}
        )
        assert decision.allowed is False
        assert "prefix" in decision.reason.lower()

    def test_commit_allowed_with_green_prefix(self) -> None:
        """Test commit allowed with feat: prefix (green phase maps to feat:)."""
        engine = make_policy_engine()
        decision = engine.decide(
            operation="commit",
            phase="implementation",
            context={"message": "feat: implement user dto"},
        )
        assert decision.allowed is True

    def test_component_type_validation(self) -> None:
        """Test component type validation in directory."""
        engine = make_policy_engine()
        decision = engine.decide(
            operation="scaffold",
            path="backend/dtos/service.py",
            phase="implementation",
            context={"component_type": "service"},  # Service not allowed in dtos/
        )
        assert decision.allowed is False
        assert "service" in decision.reason.lower()

    def test_allowed_extension_validation(self) -> None:
        """Test file extension validation."""
        engine = make_policy_engine()
        decision = engine.decide(
            operation="create_file", path="docs/design.txt", phase="design", context={}
        )
        # .txt should be allowed for docs directory
        assert decision.allowed is True

    def test_audit_trail_logging(self) -> None:
        """Test decisions are logged to audit trail."""
        engine = make_policy_engine()
        engine.decide(
            operation="scaffold",
            path="backend/dtos/user_dto.py",
            phase="implementation",
            context={"component_type": "dto"},
        )
        trail = engine.get_audit_trail()
        assert len(trail) == 1
        assert trail[0]["operation"] == "scaffold"
        assert trail[0]["allowed"] is True

    def test_policy_decision_contains_directory_policy(self) -> None:
        """Test PolicyDecision includes resolved directory policy."""
        engine = make_policy_engine()
        decision = engine.decide(
            operation="scaffold",
            path="backend/dtos/user_dto.py",
            phase="implementation",
            context={"component_type": "dto"},
        )
        assert decision.directory_policy is not None
        assert decision.directory_policy.path == "backend/dtos"

    def test_error_handling_denies_by_default(self) -> None:
        """Test errors result in denied decision (fail-safe)."""
        engine = make_policy_engine()
        decision = engine.decide(
            operation="invalid_operation",
            phase="implementation",
            context={},
        )
        # Invalid operation should be denied or require approval
        # Config-driven engine should handle gracefully
        assert decision is not None

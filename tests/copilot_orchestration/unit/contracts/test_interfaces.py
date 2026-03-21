# tests\copilot_orchestration\unit\contracts\test_interfaces.py
# template=unit_test version=3d15d309 created=2026-03-21T12:20Z updated=
"""
Unit tests for copilot_orchestration.contracts.interfaces.

Structural tests: Protocol compliance and TypedDict shape verification. No logic lives in the contracts layer.

@layer: Tests (Unit)
@dependencies: [pytest, copilot_orchestration.contracts.interfaces]
@responsibilities:
    - Test TestISubRoleRequirementsLoaderProtocol functionality
    - Verify Protocol compliance and TypedDict shape correctness
    - Verify TypedDict shapes have correct key types
"""

# Project modules
from copilot_orchestration.contracts.interfaces import (
    ISubRoleRequirementsLoader,
    SessionSubRoleState,
    SubRoleSpec,
)


class TestISubRoleRequirementsLoaderProtocol:
    """Test suite for ISubRoleRequirementsLoader Protocol and related TypedDicts."""

    def test_concrete_class_satisfies_protocol(self) -> None:
        """A concrete class implementing all four methods satisfies ISubRoleRequirementsLoader at runtime."""
        # Arrange - define minimal concrete class that covers all protocol methods
        class StubLoader:
            def valid_sub_roles(self, role: str) -> frozenset[str]:
                return frozenset()

            def default_sub_role(self, role: str) -> str:
                return ""

            def requires_crosschat_block(self, role: str, sub_role: str) -> bool:
                return False

            def get_requirement(self, role: str, sub_role: str) -> SubRoleSpec:
                return SubRoleSpec(
                    requires_crosschat_block=False,
                    heading="",
                    block_prefix="",
                    guide_line="",
                    markers=[],
                )

        # Act
        result = isinstance(StubLoader(), ISubRoleRequirementsLoader)

        # Assert
        assert result is True

    def test_sub_role_spec_keys(self) -> None:
        """SubRoleSpec TypedDict accepts all required keys and preserves their values."""
        # Arrange / Act - construct with all required keys
        spec: SubRoleSpec = SubRoleSpec(
            requires_crosschat_block=True,
            heading="heading",
            block_prefix="prefix",
            guide_line="guide",
            markers=["M1"],
        )

        # Assert - verify exact values
        assert spec["requires_crosschat_block"] is True
        assert spec["heading"] == "heading"
        assert spec["block_prefix"] == "prefix"
        assert spec["guide_line"] == "guide"
        assert spec["markers"] == ["M1"]

    def test_session_sub_role_state_keys(self) -> None:
        """SessionSubRoleState TypedDict accepts all required keys and preserves their values."""
        # Arrange / Act - construct with all required keys
        state: SessionSubRoleState = SessionSubRoleState(
            session_id="sid-1",
            role="imp",
            sub_role="implementer",
            detected_at="2026-03-21T00:00:00Z",
        )

        # Assert - verify exact values
        assert state["session_id"] == "sid-1"
        assert state["role"] == "imp"
        assert state["sub_role"] == "implementer"
        assert state["detected_at"] == "2026-03-21T00:00:00Z"

    def test_protocol_has_all_four_methods(self) -> None:
        """ISubRoleRequirementsLoader Protocol exposes all four required method names."""
        # Arrange - retrieve publicly visible names from the Protocol
        public_names = {name for name in dir(ISubRoleRequirementsLoader) if not name.startswith("_")}

        # Assert - all four contract methods are present
        assert "valid_sub_roles" in public_names
        assert "default_sub_role" in public_names
        assert "requires_crosschat_block" in public_names
        assert "get_requirement" in public_names

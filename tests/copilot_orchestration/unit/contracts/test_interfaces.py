# tests\copilot_orchestration\unit\contracts\test_interfaces.py
# template=unit_test version=3d15d309 created=2026-03-21T12:20Z updated=
"""
Unit tests for copilot_orchestration.contracts.interfaces.

Structural tests: Protocol compliance and TypedDict shape verification.
No logic lives in the contracts layer.

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
        """A concrete class implementing all four methods satisfies the Protocol."""

        # Arrange - define minimal concrete class that covers all protocol methods
        class StubLoader:
            def valid_sub_roles(self, _role: str) -> frozenset[str]:
                return frozenset()

            def default_sub_role(self, _role: str) -> str:
                return ""

            def requires_crosschat_block(self, _role: str, _sub_role: str) -> bool:
                return False

            def get_requirement(self, _role: str, _sub_role: str) -> SubRoleSpec:
                return SubRoleSpec(
                    requires_crosschat_block=False,
                    heading="",
                    block_template="",
                    markers=[],
                )

            def max_sub_role_name_len(self) -> int:
                return 40

        # Act
        result = isinstance(StubLoader(), ISubRoleRequirementsLoader)  # pyright: ignore[reportGeneralTypeIssues]

        # Assert
        assert result is True

    def test_sub_role_spec_keys(self) -> None:
        """SubRoleSpec TypedDict accepts all required keys and preserves their values."""
        # Arrange / Act - construct with all required keys
        template = "[{sub_role}] End your response with this block:\n\n```text\n{markers_list}\n```"
        spec: SubRoleSpec = SubRoleSpec(
            requires_crosschat_block=True,
            heading="heading",
            block_template=template,
            markers=["M1"],
        )

        # Assert - verify exact values
        assert spec["requires_crosschat_block"] is True
        assert spec["heading"] == "heading"
        assert spec["block_template"] == template
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

    def test_sub_role_spec_has_block_template(self) -> None:
        """block_template is a required field in SubRoleSpec (C_CROSSCHAT.1)."""
        assert "block_template" in SubRoleSpec.__required_keys__

    def test_sub_role_spec_requires_description_field(self) -> None:
        """description is a required field in SubRoleSpec (C_DESC.1)."""
        assert "description" in SubRoleSpec.__required_keys__

    def test_sub_role_spec_no_legacy_fields(self) -> None:
        """block_prefix, guide_line, block_prefix_hint, marker_verb absent (C_CROSSCHAT.1)."""
        all_keys = SubRoleSpec.__required_keys__ | SubRoleSpec.__optional_keys__
        assert "block_prefix" not in all_keys
        assert "guide_line" not in all_keys
        assert "block_prefix_hint" not in all_keys
        assert "marker_verb" not in all_keys

    def test_protocol_has_all_four_methods(self) -> None:
        """ISubRoleRequirementsLoader Protocol exposes all four required method names."""
        # Arrange - retrieve publicly visible names from the Protocol
        public_names = {
            name for name in dir(ISubRoleRequirementsLoader) if not name.startswith("_")
        }

        # Assert - all four contract methods are present
        assert "valid_sub_roles" in public_names
        assert "default_sub_role" in public_names
        assert "requires_crosschat_block" in public_names
        assert "get_requirement" in public_names

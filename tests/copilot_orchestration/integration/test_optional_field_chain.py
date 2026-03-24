# tests\copilot_orchestration\integration\test_optional_field_chain.py
# template=integration_test version=85ea75d4 created=2026-03-23T20:08Z updated=
"""
Integration tests for optional_field_chain.

Full chain: YAML on disk → SubRoleRequirementsLoader → get_requirement()
→ build_stop_reason(). Verifies block_prefix and markers flow
through all three layers into the canonical crosschat block instruction.

@layer: Tests (Integration)
@dependencies: [pytest, pytest-asyncio, tempfile]
@responsibilities:
    - Test end-to-end optional_field_chain
    - Verify full-stack integration
    - Validate file system interactions
"""

# Standard library
from pathlib import Path

# Project modules
from copilot_orchestration.config.requirements_loader import SubRoleRequirementsLoader
from copilot_orchestration.hooks.stop_handover_guard import build_stop_reason

_YAML_WITH_OPTIONAL_FIELDS = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      implementer:
        requires_crosschat_block: true
        heading: "Impl Hand-Over"
        block_prefix: "verifier "
        guide_line: "Review the implementation."
        block_prefix_hint: "Paste into @qa verifier chat."
        marker_verb: "add a section called"
        markers:
          - "Scope"
          - "Files Changed"
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: true
        heading: "V"
        block_prefix: "B"
        guide_line: "G"
        markers: []
"""

_YAML_WITHOUT_OPTIONAL_FIELDS = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      implementer:
        requires_crosschat_block: true
        heading: "Impl Hand-Over"
        block_prefix: "verifier "
        guide_line: "Review it."
        markers:
          - "Scope"
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: true
        heading: "V"
        block_prefix: "B"
        guide_line: "G"
        markers: []
"""


class TestOptionalFieldChain:
    """Integration test suite for optional_field_chain."""

    def test_block_prefix_hint_appears_in_stop_reason(self, tmp_path: Path) -> None:
        """block_prefix from YAML flows through get_requirement() into build_stop_reason() canonical output."""
        yaml_path = tmp_path / "r.yaml"
        yaml_path.write_text(_YAML_WITH_OPTIONAL_FIELDS)
        spec = SubRoleRequirementsLoader(yaml_path).get_requirement("imp", "implementer")
        result = build_stop_reason(spec, "implementer")
        assert "verifier" in result

    def test_marker_verb_from_yaml_used_in_stop_reason(self, tmp_path: Path) -> None:
        """Markers from YAML flow through get_requirement() into build_stop_reason() output."""
        yaml_path = tmp_path / "r.yaml"
        yaml_path.write_text(_YAML_WITH_OPTIONAL_FIELDS)
        spec = SubRoleRequirementsLoader(yaml_path).get_requirement("imp", "implementer")
        result = build_stop_reason(spec, "implementer")
        assert "Scope" in result and "Files Changed" in result

    def test_chain_works_without_optional_fields(self, tmp_path: Path) -> None:
        """build_stop_reason() does not crash when optional fields are absent from YAML."""
        yaml_path = tmp_path / "r.yaml"
        yaml_path.write_text(_YAML_WITHOUT_OPTIONAL_FIELDS)
        spec = SubRoleRequirementsLoader(yaml_path).get_requirement("imp", "implementer")
        result = build_stop_reason(spec, "implementer")
        assert "Scope" in result
        assert result

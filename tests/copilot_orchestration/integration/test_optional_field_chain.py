# tests\copilot_orchestration\integration\test_optional_field_chain.py
# template=integration_test version=85ea75d4 created=2026-03-23T20:08Z updated=
"""
Integration tests for optional_field_chain.

Full chain: YAML on disk → SubRoleRequirementsLoader → get_requirement()
→ build_stop_reason(). Verifies block_template and markers flow
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

# Third-party
import pytest

# Project modules
from copilot_orchestration.config.requirements_loader import SubRoleRequirementsLoader
from copilot_orchestration.hooks.detect_sub_role import (
    build_crosschat_block_instruction,
    build_ups_output,
)
from copilot_orchestration.hooks.notify_compaction import build_compaction_output
from copilot_orchestration.hooks.stop_handover_guard import build_stop_reason
from copilot_orchestration.utils._paths import find_workspace_root

_YAML_WITH_BLOCK_TEMPLATE = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      implementer:
        requires_crosschat_block: true
        heading: "Impl Hand-Over"
        block_template: |-
          [{sub_role}] End your response with this block:

          ```text
          verifier
          Review the implementation.
          ```

          Required sections:
          {markers_list}
        markers:
          - "Scope"
          - "Files Changed"
        description: "Implement the current cycle."
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: true
        heading: "V"
        block_template: |-
          [{sub_role}] End your response with this block:

          ```text
          implementer
          QA done.
          ```

          Required sections:
          {markers_list}
        markers: []
        description: "Review the implementation handover."
"""

_YAML_MINIMAL_WITH_BLOCK_TEMPLATE = """\
roles:
  imp:
    default_sub_role: implementer
    sub_roles:
      implementer:
        requires_crosschat_block: true
        heading: "Impl Hand-Over"
        block_template: |-
          [{sub_role}] End:

          ```text
          verifier
          Review it.
          ```

          Required sections:
          {markers_list}
        markers:
          - "Scope"
        description: "Implement the current cycle."
  qa:
    default_sub_role: verifier
    sub_roles:
      verifier:
        requires_crosschat_block: true
        heading: "V"
        block_template: |-
          [{sub_role}] End:

          ```text
          implementer
          QA done.
          ```

          Required sections:
          {markers_list}
        markers: []
        description: "Review the implementation handover."
"""


def _project_loader() -> SubRoleRequirementsLoader:
    """Load the workspace .copilot/sub-role-requirements.yaml for integration coverage."""
    return SubRoleRequirementsLoader.from_copilot_dir(find_workspace_root(Path(__file__)))


_PROJECT_SUB_ROLES = [
    (role, sub_role)
    for role in ("imp", "qa")
    for sub_role in sorted(_project_loader().valid_sub_roles(role))
]


class TestOptionalFieldChain:
    """Integration test suite for optional_field_chain."""

    @pytest.mark.parametrize(("role", "sub_role"), _PROJECT_SUB_ROLES)
    def test_real_yaml_build_ups_output_injects_description_for_all_sub_roles(
        self,
        role: str,
        sub_role: str,
    ) -> None:
        """C_DESC.4: UPS output includes the configured description for all 11 sub-roles."""
        loader = _project_loader()
        spec = loader.get_requirement(role, sub_role)
        result = build_ups_output(sub_role, loader, role)

        hook = result.get("hookSpecificOutput")
        assert isinstance(hook, dict)
        message = hook.get("systemMessage")
        assert isinstance(message, str)
        assert spec["description"].strip() in message
        if spec["requires_crosschat_block"]:
            assert message.endswith(build_crosschat_block_instruction(sub_role, spec))
        else:
            assert "```text" not in message
            assert message == spec["description"].strip()

    @pytest.mark.parametrize(("role", "sub_role"), _PROJECT_SUB_ROLES)
    def test_real_yaml_build_compaction_output_injects_description_for_all_sub_roles(
        self,
        role: str,
        sub_role: str,
    ) -> None:
        """C_DESC.4: compaction output includes the configured description for all 11 sub-roles."""
        loader = _project_loader()
        spec = loader.get_requirement(role, sub_role)
        result = build_compaction_output({"sub_role": sub_role}, loader, role)

        message = result.get("systemMessage")
        assert isinstance(message, str)
        assert spec["description"].strip() in message
        if spec["requires_crosschat_block"]:
            assert message.endswith(build_crosschat_block_instruction(sub_role, spec))
        else:
            assert "```text" not in message

    def test_prepare_qa_brief_prompt_no_longer_mentions_guide_line(self) -> None:
        """C_DESC.4: prepare-qa-brief prompt no longer references removed guide_line config."""
        workspace_root = find_workspace_root(Path(__file__))
        prompt_path = workspace_root / ".github" / "prompts" / "prepare-qa-brief.prompt.md"
        assert "guide_line" not in prompt_path.read_text()

    def test_block_template_content_appears_in_stop_reason(self, tmp_path: Path) -> None:
        """block_template from YAML flows through get_requirement() into build_stop_reason()."""
        yaml_path = tmp_path / "r.yaml"
        yaml_path.write_text(_YAML_WITH_BLOCK_TEMPLATE)
        spec = SubRoleRequirementsLoader(yaml_path).get_requirement("imp", "implementer")
        result = build_stop_reason(spec, "implementer")
        assert "verifier" in result

    def test_markers_from_yaml_appear_in_stop_reason(self, tmp_path: Path) -> None:
        """Markers from YAML flow through get_requirement() into build_stop_reason() output."""
        yaml_path = tmp_path / "r.yaml"
        yaml_path.write_text(_YAML_WITH_BLOCK_TEMPLATE)
        spec = SubRoleRequirementsLoader(yaml_path).get_requirement("imp", "implementer")
        result = build_stop_reason(spec, "implementer")
        assert "Scope" in result and "Files Changed" in result

    def test_chain_works_with_minimal_block_template(self, tmp_path: Path) -> None:
        """build_stop_reason() works correctly with a minimal block_template."""
        yaml_path = tmp_path / "r.yaml"
        yaml_path.write_text(_YAML_MINIMAL_WITH_BLOCK_TEMPLATE)
        spec = SubRoleRequirementsLoader(yaml_path).get_requirement("imp", "implementer")
        result = build_stop_reason(spec, "implementer")
        assert "Scope" in result

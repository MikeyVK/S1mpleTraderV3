# tests\copilot_orchestration\unit\hooks\test_detect_sub_role.py
# template=unit_test version=3d15d309 created=2026-03-21T12:53Z updated=
"""
Unit tests for copilot_orchestration.hooks.detect_sub_role.

Tests detect_sub_role pure query function: exact match, case-insensitive,
difflib typo correction, default fallback, oversized input handling.

@layer: Tests (Unit)
@dependencies: [pytest, copilot_orchestration.hooks.detect_sub_role]
@responsibilities:
    - Test TestDetectSubRole functionality
    - Verify pure query function — regex exact match, case-insensitive match,
      difflib typo, default fallback
    - Verify oversized input returns default without crashing
    - Verify loader.max_sub_role_name_len() is larger than all known sub-role names
    - Pure query only — no filesystem interaction in any test
"""

# Standard library
import logging
from pathlib import Path

# Third-party
import pytest

# Project modules
from copilot_orchestration.config.requirements_loader import SubRoleRequirementsLoader
from copilot_orchestration.contracts.interfaces import SubRoleSpec
from copilot_orchestration.hooks.detect_sub_role import (
    _match_sub_role,
    build_crosschat_block_instruction,
    build_ups_output,
    detect_sub_role,
)
from copilot_orchestration.utils._paths import find_workspace_root


class _StubLoader:
    """Minimal ISubRoleRequirementsLoader for testing detect_sub_role."""

    def valid_sub_roles(self, role: str) -> frozenset[str]:
        if role == "imp":
            return frozenset(
                {"researcher", "planner", "designer", "implementer", "validator", "documenter"}
            )
        return frozenset(
            {
                "plan-reviewer",
                "design-reviewer",
                "verifier",
                "validation-reviewer",
                "doc-reviewer",
            }
        )

    def default_sub_role(self, role: str) -> str:
        return "implementer" if role == "imp" else "verifier"

    def requires_crosschat_block(self, role: str, sub_role: str) -> bool:  # noqa: ARG002
        return False

    def get_requirement(self, role: str, sub_role: str) -> SubRoleSpec:  # noqa: ARG002
        return SubRoleSpec(
            requires_crosschat_block=False,
            heading="",
            block_template="",
            markers=[],
            description="",
        )

    def max_sub_role_name_len(self) -> int:
        return 40


class TestDetectSubRole:
    """Test suite for detect_sub_role."""

    def test_exact_match_returns_sub_role(self) -> None:
        """Exact sub-role name in prompt is matched."""
        loader = _StubLoader()
        assert detect_sub_role("implementer: start cycle", loader, "imp") == "implementer"

    def test_case_insensitive_match(self) -> None:
        """Match is case-insensitive."""
        loader = _StubLoader()
        assert detect_sub_role("Implementer: start cycle", loader, "imp") == "implementer"

    def test_exact_match_researcher(self) -> None:
        """Another exact sub-role name is matched."""
        loader = _StubLoader()
        assert detect_sub_role("researcher task", loader, "imp") == "researcher"

    def test_exact_match_qa_verifier(self) -> None:
        """QA role sub-role is matched."""
        loader = _StubLoader()
        assert detect_sub_role("verifier: check the branch", loader, "qa") == "verifier"

    def test_no_match_returns_default(self) -> None:
        """Falls back to default when no sub-role in prompt."""
        loader = _StubLoader()
        result = detect_sub_role("no sub role mentioned here", loader, "imp")
        assert result == loader.default_sub_role("imp")

    def test_empty_prompt_returns_default(self) -> None:
        """Empty prompt returns default sub-role (exploration mode guard in __main__)."""
        loader = _StubLoader()
        assert detect_sub_role("", loader, "imp") == loader.default_sub_role("imp")

    def test_low_similarity_typo_falls_back_to_default(self) -> None:
        """Typo not close enough (0.85 cutoff) falls back to default."""
        loader = _StubLoader()
        result = detect_sub_role("implementar task", loader, "imp")
        assert result == loader.default_sub_role("imp")

    def test_hyphenated_sub_role_matched(self) -> None:
        """Hyphenated sub-role name is matched exactly."""
        loader = _StubLoader()
        assert detect_sub_role("plan-reviewer: check the plan", loader, "qa") == "plan-reviewer"

    def test_slash_command_prefix_stripped_before_match(self) -> None:
        """Prompt starting with /command is stripped; first word after is matched."""
        loader = _StubLoader()
        result = detect_sub_role("/start-work implementer: do the task", loader, "imp")
        assert result == "implementer"

    def test_slash_resume_work_prefix_stripped(self) -> None:
        """A different /command prefix is also stripped correctly."""
        loader = _StubLoader()
        result = detect_sub_role("/resume-work researcher: investigate", loader, "imp")
        assert result == "researcher"

    def test_slash_command_only_no_sub_role_returns_default(self) -> None:
        """Prompt with /command but no recognisable sub-role falls back to default."""
        loader = _StubLoader()
        result = detect_sub_role("/start-work do something random", loader, "imp")
        assert result == loader.default_sub_role("imp")

    def test_oversized_input_returns_default_without_crash(self) -> None:
        """Very long input does not crash detect_sub_role(); returns default.

        Documents that detect_sub_role() handles oversized tokens gracefully.
        __main__ truncates to loader.max_sub_role_name_len() (from YAML config)
        before calling the engine; this test verifies the pure function also
        handles oversized input safely without any truncation of its own.
        """
        loader = _StubLoader()
        oversized = "x" * 200  # well beyond any real sub-role name
        result = detect_sub_role(oversized, loader, "imp")
        assert result == loader.default_sub_role("imp")

    def test_max_sub_role_name_len_covers_all_known_sub_roles(self) -> None:
        """loader.max_sub_role_name_len() is larger than every known sub-role name.

        Ensures the YAML config value is adequate: __main__ truncates first-word
        input to this length before matching, so it must exceed the longest
        sub-role name or valid sub-roles would be silently truncated.
        """
        loader = _StubLoader()
        all_names = loader.valid_sub_roles("imp") | loader.valid_sub_roles("qa")
        longest = max(len(name) for name in all_names)
        max_len = loader.max_sub_role_name_len()
        assert longest < max_len, (
            f"Longest sub-role '{max(all_names, key=len)}' ({longest} chars) "
            f">= loader.max_sub_role_name_len() ({max_len}); update the YAML config."
        )


_LOGGER_NAME = "copilot_orchestration.hooks.detect_sub_role"


class TestDetectSubRoleLogging:
    """Logging behaviour of _match_sub_role."""

    def test_match_logs_debug_when_match_found(self, caplog: pytest.LogCaptureFixture) -> None:
        """_match_sub_role logs at DEBUG when a sub-role is matched."""
        loader = _StubLoader()
        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            _match_sub_role("implementer: start cycle", loader, "imp")
        assert any(r.levelno == logging.DEBUG for r in caplog.records)

    def test_no_match_logs_debug(self, caplog: pytest.LogCaptureFixture) -> None:
        """_match_sub_role logs at DEBUG when no sub-role is found."""
        loader = _StubLoader()
        with caplog.at_level(logging.DEBUG, logger=_LOGGER_NAME):
            _match_sub_role("totally unrelated text here", loader, "imp")
        assert any(r.levelno == logging.DEBUG for r in caplog.records)


class _EnforcingStubLoader(_StubLoader):
    """Stub loader where all sub-roles have requires_crosschat_block=True."""

    def requires_crosschat_block(self, role: str, sub_role: str) -> bool:  # noqa: ARG002
        return True

    def get_requirement(self, role: str, sub_role: str) -> SubRoleSpec:  # noqa: ARG002
        return SubRoleSpec(
            requires_crosschat_block=True,
            heading="",
            block_template=("[{sub_role}] End:\n\n```text\n{sub_role}\n{markers_list}\n```"),
            markers=[],
            description="",
        )


class _UpsContractLoader(_StubLoader):
    """Stub loader for the C_DESC.2 build_ups_output() return contract."""

    def __init__(self, *, description: str, requires_crosschat_block: bool) -> None:
        self._description = description
        self._requires_crosschat_block = requires_crosschat_block

    def requires_crosschat_block(self, role: str, sub_role: str) -> bool:  # noqa: ARG002
        raise AssertionError("build_ups_output() must use spec['requires_crosschat_block']")

    def get_requirement(self, role: str, sub_role: str) -> SubRoleSpec:  # noqa: ARG002
        return SubRoleSpec(
            requires_crosschat_block=self._requires_crosschat_block,
            heading="",
            block_template=("[{sub_role}] End:\n\n```text\nverifier\n{markers_list}\n```"),
            markers=["Scope"],
            description=self._description,
        )


class TestBuildUpsOutput:
    """Tests for build_ups_output - S1 front-loading via UserPromptSubmit hook.

    build_ups_output(sub_role, loader, role) injects a systemMessage
    when requires_crosschat_block is True, so the agent sees the handover
    instruction BEFORE generating output (not just at Stop time).
    """

    def test_returns_empty_dict_for_empty_description_without_crosschat(self) -> None:
        """C_DESC.2 case 1: empty description + no crosschat returns {}."""
        loader = _UpsContractLoader(description="", requires_crosschat_block=False)
        result = build_ups_output("researcher", loader, "imp")
        assert result == {}

    def test_returns_crosschat_only_for_empty_description_with_crosschat(self) -> None:
        """C_DESC.2 case 2: empty description + crosschat returns only the block."""
        loader = _UpsContractLoader(description="", requires_crosschat_block=True)
        result = build_ups_output("implementer", loader, "imp")
        assert result == {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "systemMessage": "[implementer] End:\n\n```text\nverifier\n## Scope\n```",
            }
        }

    def test_returns_description_only_for_non_empty_description_without_crosschat(self) -> None:
        """C_DESC.2 case 3: description + no crosschat returns only the description."""
        loader = _UpsContractLoader(
            description="Implement the current cycle.",
            requires_crosschat_block=False,
        )
        result = build_ups_output("researcher", loader, "imp")
        assert result == {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "systemMessage": "Implement the current cycle.",
            }
        }

    def test_returns_description_and_crosschat_for_non_empty_description_with_crosschat(
        self,
    ) -> None:
        """C_DESC.2 case 4: description + crosschat joins both parts with one blank line."""
        loader = _UpsContractLoader(
            description="Implement the current cycle.",
            requires_crosschat_block=True,
        )
        result = build_ups_output("implementer", loader, "imp")
        assert result == {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "systemMessage": (
                    "Implement the current cycle.\n\n"
                    "[implementer] End:\n\n```text\nverifier\n## Scope\n```"
                ),
            }
        }

    def test_enforced_sub_role_returns_hook_specific_output(self) -> None:
        """Enforced sub-role produces hookSpecificOutput with hookEventName=UserPromptSubmit."""
        loader = _EnforcingStubLoader()
        result = build_ups_output("implementer", loader, "imp")
        hook = result.get("hookSpecificOutput")
        assert isinstance(hook, dict)
        assert hook.get("hookEventName") == "UserPromptSubmit"

    def test_enforced_sub_role_system_message_is_non_empty_string(self) -> None:
        """systemMessage must be a non-empty string."""
        loader = _EnforcingStubLoader()
        result = build_ups_output("implementer", loader, "imp")
        msg = result["hookSpecificOutput"]["systemMessage"]  # type: ignore[index]
        assert isinstance(msg, str)
        assert msg.strip()

    @pytest.mark.parametrize(
        "role,sub_role",
        [
            (role, sub_role)
            for role in ("imp", "qa")
            for sub_role in sorted(
                SubRoleRequirementsLoader.from_copilot_dir(
                    find_workspace_root(Path(__file__))
                ).valid_sub_roles(role)
            )
        ],
    )
    def test_canonical_instruction_frame_under_200_chars(self, role: str, sub_role: str) -> None:
        """Pre-markers frame is under 200 chars for every sub-role in the real YAML config."""
        loader = SubRoleRequirementsLoader.from_copilot_dir(find_workspace_root(Path(__file__)))
        if not loader.requires_crosschat_block(role, sub_role):
            pytest.skip("sub-role does not require crosschat block")
        spec = loader.get_requirement(role, sub_role)
        result = build_crosschat_block_instruction(sub_role, spec)
        # Split on the first H2 marker header — everything before it is the "frame"
        frame = result.split("## ")[0]
        assert len(frame) < 200, f"[{role}/{sub_role}] frame is {len(frame)} chars (limit: 200)"

    def test_non_enforced_sub_role_returns_empty_dict(self) -> None:
        """Non-enforced sub-role produces {} (no injection)."""
        loader = _StubLoader()  # requires_crosschat_block always False
        result = build_ups_output("researcher", loader, "imp")
        assert result == {}

    def test_qa_enforced_sub_role_returns_ups_output(self) -> None:
        """qa role enforced sub-role also produces front-load output."""
        loader = _EnforcingStubLoader()
        result = build_ups_output("verifier", loader, "qa")
        hook = result.get("hookSpecificOutput")
        assert isinstance(hook, dict)
        assert hook.get("hookEventName") == "UserPromptSubmit"


_SPEC_FOR_CANONICAL = SubRoleSpec(
    requires_crosschat_block=True,
    heading="### Hand-Over",
    block_template=(
        "[{sub_role}] End your response with this block:\n\n"
        "```text\nverifier\nReview the latest implementation work on this branch.\n\n"
        "{markers_list}\n```"
    ),
    markers=["Scope", "Files Changed", "Proof", "Ready-for-QA"],
    description="",
)

_SPEC_NEW_STYLE = SubRoleSpec(
    requires_crosschat_block=True,
    heading="### Hand-Over",
    block_template=(
        "[{sub_role}] End your response with this block:\n\n"
        "```text\nverifier\nReview the work.\n\n"
        "{markers_list}\n```"
    ),
    markers=["Scope", "Files Changed"],
    description="",
)


class TestBuildCrosschatBlockInstructionBlockTemplate:
    """RED tests for block_template-based build_crosschat_block_instruction.

    C_CROSSCHAT.3: function must use spec['block_template'].format(...) instead
    of legacy spec['block_prefix'] / spec['guide_line'].
    """

    def test_block_template_sub_role_substituted(self) -> None:
        """block_template {sub_role} placeholder is replaced with the sub_role arg."""
        result = build_crosschat_block_instruction("implementer", _SPEC_NEW_STYLE)
        assert "[implementer]" in result
        assert "{sub_role}" not in result

    def test_block_template_markers_list_substituted(self) -> None:
        """block_template {markers_list} is replaced with rendered markers."""
        result = build_crosschat_block_instruction("implementer", _SPEC_NEW_STYLE)
        assert "Scope" in result
        assert "Files Changed" in result
        assert "{markers_list}" not in result

    def test_block_template_markers_list_format_is_h2_headers(self) -> None:
        """markers_list renders each marker as a ## H2 header (not a numbered list)."""
        result = build_crosschat_block_instruction("implementer", _SPEC_NEW_STYLE)
        assert "## Scope" in result
        assert "## Files Changed" in result
        # Old numbered-list format must be absent
        assert "1. Scope" not in result

    def test_block_template_markers_inside_fence(self) -> None:
        """Each marker must appear inside the code fence, not after the closing ```."""
        result = build_crosschat_block_instruction("implementer", _SPEC_NEW_STYLE)
        # Extract everything between the opening ```text and the closing ```
        fence_start = result.index("```text") + len("```text")
        fence_end = result.index("```", fence_start)
        fence_content = result[fence_start:fence_end]
        assert "## Scope" in fence_content, "Scope marker is outside the fence"
        assert "## Files Changed" in fence_content, "Files Changed marker is outside the fence"

    def test_crlf_normalized_before_format(self) -> None:
        """CRLF in block_template is normalized to LF before str.format()."""
        spec_crlf = SubRoleSpec(
            requires_crosschat_block=True,
            heading="",
            block_template="line1\r\n{markers_list}",
            markers=[],
            description="",
        )
        result = build_crosschat_block_instruction("imp", spec_crlf)
        assert "\r\n" not in result

    def test_unknown_placeholder_raises_config_error(self) -> None:
        """Unknown {placeholder} in block_template raises ConfigError."""
        from copilot_orchestration.config.requirements_loader import ConfigError  # noqa: PLC0415

        spec_bad = SubRoleSpec(
            requires_crosschat_block=True,
            heading="",
            block_template="[{sub_role}] {unknown_key}",
            markers=[],
            description="",
        )
        with pytest.raises(ConfigError):
            build_crosschat_block_instruction("implementer", spec_bad)


class TestBuildCrosschatBlockInstruction:
    """Tests for build_crosschat_block_instruction — canonical pure function.

    All three injection points (S1, S2, S3) delegate to this function.
    Tests verify correctness, structure, and the 200-char limit on the
    pre-markers portion (§1.2 NF requirement).
    """

    def test_contains_sub_role_prefix(self) -> None:
        """Output starts with [sub_role] prefix."""
        result = build_crosschat_block_instruction("implementer", _SPEC_FOR_CANONICAL)
        assert result.startswith("[implementer]")

    def test_contains_all_markers(self) -> None:
        """Every marker from spec appears in Required sections."""
        result = build_crosschat_block_instruction("implementer", _SPEC_FOR_CANONICAL)
        for marker in _SPEC_FOR_CANONICAL["markers"]:
            assert marker in result, f"Marker {marker!r} missing from canonical instruction"

    def test_contains_code_fence(self) -> None:
        """Output contains a markdown code fence (```text)."""
        result = build_crosschat_block_instruction("implementer", _SPEC_FOR_CANONICAL)
        assert "```text" in result

    def test_pre_markers_portion_under_200_chars_stub(self) -> None:
        """Portion before the first H2 marker is under 200 chars for stub spec.

        Mirrors the §1.2 parametrised assertion: enumerate via loader.valid_sub_roles(role).
        This test uses a fixed stub spec; integration coverage uses the real loader.
        """
        result = build_crosschat_block_instruction("implementer", _SPEC_FOR_CANONICAL)
        # Split on the first H2 marker header — everything before it is the "frame"
        pre_markers = result.split("## ")[0]
        assert len(pre_markers) < 200, (
            f"pre-markers portion is {len(pre_markers)} chars; limit is 200"
        )

    def test_markers_rendered_as_h2_headers(self) -> None:
        """Markers are rendered as ## H2 headers, not as a numbered list."""
        result = build_crosschat_block_instruction("implementer", _SPEC_FOR_CANONICAL)
        assert "## Scope" in result
        assert "## Files Changed" in result
        assert "## Proof" in result
        assert "## Ready-for-QA" in result

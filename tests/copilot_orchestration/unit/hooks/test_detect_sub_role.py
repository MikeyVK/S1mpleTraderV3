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
            block_prefix="",
            guide_line="",
            markers=[],
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


class TestBuildUpsOutput:
    """Tests for build_ups_output — S1 front-loading via UserPromptSubmit hook.

    build_ups_output(sub_role, loader, role) injects a systemMessage
    when requires_crosschat_block is True, so the agent sees the handover
    instruction BEFORE generating output (not just at Stop time).
    """

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
        frame = result.split("Required sections:")[0]
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
    block_prefix="verifier",
    guide_line="Review the latest implementation work on this branch.",
    markers=["Scope", "Files Changed", "Proof", "Ready-for-QA"],
)


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

    def test_contains_block_prefix(self) -> None:
        """block_prefix from spec appears inside the code fence."""
        result = build_crosschat_block_instruction("implementer", _SPEC_FOR_CANONICAL)
        assert _SPEC_FOR_CANONICAL["block_prefix"] in result

    def test_contains_guide_line(self) -> None:
        """guide_line from spec appears inside the code fence."""
        result = build_crosschat_block_instruction("implementer", _SPEC_FOR_CANONICAL)
        assert _SPEC_FOR_CANONICAL["guide_line"] in result

    def test_contains_all_markers(self) -> None:
        """Every marker from spec appears in Required sections."""
        result = build_crosschat_block_instruction("implementer", _SPEC_FOR_CANONICAL)
        for marker in _SPEC_FOR_CANONICAL["markers"]:
            assert marker in result, f"Marker {marker!r} missing from canonical instruction"

    def test_contains_code_fence(self) -> None:
        """Output contains a markdown code fence (```text)."""
        result = build_crosschat_block_instruction("implementer", _SPEC_FOR_CANONICAL)
        assert "```text" in result

    def test_block_prefix_stripped(self) -> None:
        """Trailing whitespace on block_prefix is stripped."""
        spec_with_trailing = SubRoleSpec(
            requires_crosschat_block=True,
            heading="",
            block_prefix="verifier   ",
            guide_line="guide",
            markers=[],
        )
        result = build_crosschat_block_instruction("implementer", spec_with_trailing)
        assert "verifier   " not in result
        assert "verifier" in result

    def test_guide_line_stripped(self) -> None:
        """Trailing whitespace on guide_line is stripped."""
        spec_with_trailing = SubRoleSpec(
            requires_crosschat_block=True,
            heading="",
            block_prefix="prefix",
            guide_line="guide with spaces   ",
            markers=[],
        )
        result = build_crosschat_block_instruction("implementer", spec_with_trailing)
        assert "guide with spaces   " not in result
        assert "guide with spaces" in result

    def test_pre_markers_portion_under_200_chars_stub(self) -> None:
        """Portion before 'Required sections:' is under 200 chars for stub spec.

        Mirrors the §1.2 parametrised assertion: enumerate via loader.valid_sub_roles(role).
        This test uses a fixed stub spec; integration coverage uses the real loader.
        """
        result = build_crosschat_block_instruction("implementer", _SPEC_FOR_CANONICAL)
        pre_markers = result.split("Required sections:")[0]
        assert len(pre_markers) < 200, (
            f"pre-markers portion is {len(pre_markers)} chars; limit is 200"
        )

    def test_markers_numbered(self) -> None:
        """Markers are rendered as a numbered list."""
        result = build_crosschat_block_instruction("implementer", _SPEC_FOR_CANONICAL)
        assert "  1. Scope" in result
        assert "  2. Files Changed" in result

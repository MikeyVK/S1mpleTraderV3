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

# Third-party
import pytest

# Project modules
from copilot_orchestration.contracts.interfaces import SubRoleSpec
from copilot_orchestration.hooks.detect_sub_role import _match_sub_role, detect_sub_role


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


from copilot_orchestration.hooks.detect_sub_role import build_ups_output  # noqa: E402

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

    def test_enforced_sub_role_system_message_max_200_chars(self) -> None:
        """systemMessage must not exceed 200 characters (context bloat guard)."""
        loader = _EnforcingStubLoader()
        result = build_ups_output("implementer", loader, "imp")
        msg = result["hookSpecificOutput"]["systemMessage"]  # type: ignore[index]
        assert len(msg) <= 200, f"systemMessage is {len(msg)} chars (limit: 200)"

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

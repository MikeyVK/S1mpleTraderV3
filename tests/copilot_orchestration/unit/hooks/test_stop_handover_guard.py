# tests\copilot_orchestration\unit\hooks\test_stop_handover_guard.py
# template=unit_test version=3d15d309 created=2026-03-21T13:08Z updated=
"""
Unit tests for copilot_orchestration.hooks.stop_handover_guard.

Tests for stop_handover_guard evaluate_stop_hook: pass-through for non-enforced
sub-roles, block enforcement for cross-chat sub-roles, exploration mode (no file)
results in pass-through, ConfigError is caught and treated as pass-through.

@layer: Tests (Unit)
@dependencies: [pytest, copilot_orchestration.hooks.stop_handover_guard]
@responsibilities:
    - Test TestStopHandoverGuard functionality
    - Verify evaluate_stop_hook DI interface: loader fixture, state file, exploration mode
    - No sub-role name literals in test code â€” all names derived from loader fixture
"""

# Standard library
import json
import logging
from pathlib import Path

# Third-party
import pytest

# Project modules
from copilot_orchestration.config.requirements_loader import ConfigError
from copilot_orchestration.contracts.interfaces import SubRoleSpec
from copilot_orchestration.hooks.stop_handover_guard import build_stop_reason, evaluate_stop_hook

_SESSION_ID = "test-session-abc"

_SPEC_STUB = SubRoleSpec(
    requires_crosschat_block=True,
    heading="### Hand-Over",
    block_prefix="@next: take over.",
    guide_line="Use the guide.",
    markers=["Task:", "Files:"],
)


class _StubLoader:
    """Minimal ISubRoleRequirementsLoader for testing stop_handover_guard."""

    _VALID: dict[str, frozenset[str]] = {
        "imp": frozenset(
            {
                "researcher",
                "planner",
                "designer",
                "implementer",
                "validator",
                "documenter",
            }
        ),
        "qa": frozenset(
            {
                "plan-reviewer",
                "design-reviewer",
                "verifier",
                "validation-reviewer",
                "doc-reviewer",
            }
        ),
    }
    _ENFORCE: dict[str, frozenset[str]] = {
        "imp": frozenset({"implementer", "validator"}),
        "qa": frozenset({"verifier"}),
    }
    _DEFAULT: dict[str, str] = {"imp": "implementer", "qa": "verifier"}

    def valid_sub_roles(self, role: str) -> frozenset[str]:
        return self._VALID[role]

    def default_sub_role(self, role: str) -> str:
        return self._DEFAULT[role]

    def requires_crosschat_block(self, role: str, sub_role: str) -> bool:
        return sub_role in self._ENFORCE[role]

    def get_requirement(self, role: str, sub_role: str) -> SubRoleSpec:  # noqa: ARG002
        return _SPEC_STUB


class _ConfigErrorLoader(_StubLoader):
    """Loader that raises ConfigError from requires_crosschat_block (unknown sub-role)."""

    def requires_crosschat_block(self, role: str, sub_role: str) -> bool:  # noqa: ARG002
        raise ConfigError(f"Unknown (role, sub_role): ({role!r}, {sub_role!r})")


def _make_state(role: str, sub_role: str, session_id: str = _SESSION_ID) -> str:
    return json.dumps(
        {
            "session_id": session_id,
            "role": role,
            "sub_role": sub_role,
            "detected_at": "2026-01-01T00:00:00Z",
        }
    )


class TestStopHandoverGuard:
    """Test suite for stop_handover_guard."""

    def test_pass_through_for_all_non_enforced_imp_sub_roles(self, tmp_path: Path) -> None:
        """All non-enforced imp sub-roles return {} (no block)."""
        loader = _StubLoader()
        role = "imp"
        non_enforced = [
            s for s in loader.valid_sub_roles(role) if not loader.requires_crosschat_block(role, s)
        ]
        assert non_enforced, "fixture must have at least one non-enforced imp sub-role"
        state_path = tmp_path / "state.json"
        for sub_role in non_enforced:
            state_path.write_text(_make_state(role, sub_role))
            result = evaluate_stop_hook({"sessionId": _SESSION_ID}, role, loader, state_path)
            assert result == {}, f"expected pass-through for {sub_role!r}"

    def test_pass_through_for_all_non_enforced_qa_sub_roles(self, tmp_path: Path) -> None:
        """All non-enforced qa sub-roles return {} (no block)."""
        loader = _StubLoader()
        role = "qa"
        non_enforced = [
            s for s in loader.valid_sub_roles(role) if not loader.requires_crosschat_block(role, s)
        ]
        assert non_enforced, "fixture must have at least one non-enforced qa sub-role"
        state_path = tmp_path / "state.json"
        for sub_role in non_enforced:
            state_path.write_text(_make_state(role, sub_role))
            result = evaluate_stop_hook({"sessionId": _SESSION_ID}, role, loader, state_path)
            assert result == {}, f"expected pass-through for {sub_role!r}"

    def test_exploration_mode_missing_file_imp_returns_pass_through(self, tmp_path: Path) -> None:
        """Missing state file â†’ exploration mode â†’ {} (no block)."""
        loader = _StubLoader()
        state_path = tmp_path / "missing.json"  # does not exist
        result = evaluate_stop_hook({"sessionId": _SESSION_ID}, "imp", loader, state_path)
        assert result == {}

    def test_exploration_mode_missing_file_qa_returns_pass_through(self, tmp_path: Path) -> None:
        """Missing state file for qa â†’ exploration mode â†’ {} (no block)."""
        loader = _StubLoader()
        state_path = tmp_path / "missing.json"  # does not exist
        result = evaluate_stop_hook({"sessionId": _SESSION_ID}, "qa", loader, state_path)
        assert result == {}

    def test_file_with_non_enforced_sub_role_passes_through_regardless_of_session_id(
        self, tmp_path: Path
    ) -> None:
        """State file with any session_id is read; non-enforced sub-role â†’ pass-through."""
        loader = _StubLoader()
        role = "imp"
        non_enforced = next(
            s for s in loader.valid_sub_roles(role) if not loader.requires_crosschat_block(role, s)
        )
        state_path = tmp_path / "state.json"
        # Session ID in file differs from event â€” still honoured (no session_id comparison)
        state_path.write_text(_make_state(role, non_enforced, session_id="OLD-SESSION"))
        result = evaluate_stop_hook({"sessionId": _SESSION_ID}, role, loader, state_path)
        assert result == {}

    def test_exploration_mode_malformed_state_file_returns_pass_through(
        self, tmp_path: Path
    ) -> None:
        """Malformed JSON in state file â†’ exploration mode â†’ {} (no block)."""
        loader = _StubLoader()
        role = "imp"
        state_path = tmp_path / "state.json"
        state_path.write_text("{not valid json}")
        result = evaluate_stop_hook({"sessionId": _SESSION_ID}, role, loader, state_path)
        assert result == {}

    def test_config_error_in_requires_crosschat_block_causes_pass_through(
        self, tmp_path: Path
    ) -> None:
        """ConfigError from loader.requires_crosschat_block â†’ caught â†’ pass-through {}."""
        loader = _ConfigErrorLoader()
        role = "imp"
        # Write a valid state file with a normally-enforced sub-role
        state_path = tmp_path / "state.json"
        state_path.write_text(_make_state(role, "implementer"))
        result = evaluate_stop_hook({"sessionId": _SESSION_ID}, role, loader, state_path)
        assert result == {}

    def test_imp_default_sub_role_produces_block(self, tmp_path: Path) -> None:
        """Valid state with imp default sub-role (enforced) triggers block."""
        loader = _StubLoader()
        role = "imp"
        sub_role = loader.default_sub_role(role)
        state_path = tmp_path / "state.json"
        state_path.write_text(_make_state(role, sub_role))
        result = evaluate_stop_hook({"sessionId": _SESSION_ID}, role, loader, state_path)
        assert result.get("hookSpecificOutput", {}).get("decision") == "block"

    def test_imp_non_default_enforced_sub_role_produces_block(self, tmp_path: Path) -> None:
        """Valid state with a non-default but enforced imp sub-role also triggers block."""
        loader = _StubLoader()
        role = "imp"
        default_sub = loader.default_sub_role(role)
        other_enforced = next(
            s
            for s in sorted(loader.valid_sub_roles(role))
            if loader.requires_crosschat_block(role, s) and s != default_sub
        )
        state_path = tmp_path / "state.json"
        state_path.write_text(_make_state(role, other_enforced))
        result = evaluate_stop_hook({"sessionId": _SESSION_ID}, role, loader, state_path)
        assert result.get("hookSpecificOutput", {}).get("decision") == "block"

    def test_qa_default_sub_role_produces_block(self, tmp_path: Path) -> None:
        """Valid state with qa default sub-role (enforced) triggers block."""
        loader = _StubLoader()
        role = "qa"
        sub_role = loader.default_sub_role(role)
        state_path = tmp_path / "state.json"
        state_path.write_text(_make_state(role, sub_role))
        result = evaluate_stop_hook({"sessionId": _SESSION_ID}, role, loader, state_path)
        assert result.get("hookSpecificOutput", {}).get("decision") == "block"

    def test_retry_bypasses_enforcement_for_enforced_sub_role(self, tmp_path: Path) -> None:
        """stop_hook_active=True bypasses enforcement even for enforced sub-role."""
        loader = _StubLoader()
        role = "imp"
        sub_role = loader.default_sub_role(role)  # enforced
        state_path = tmp_path / "state.json"
        state_path.write_text(_make_state(role, sub_role))
        result = evaluate_stop_hook(
            {"sessionId": _SESSION_ID, "stop_hook_active": True},
            role,
            loader,
            state_path,
        )
        assert result == {}

    def test_retry_bypasses_enforcement_even_without_state_file(self, tmp_path: Path) -> None:
        """stop_hook_active=True returns {} even when no state file exists."""
        loader = _StubLoader()
        role = "imp"
        state_path = tmp_path / "missing.json"  # does not exist
        result = evaluate_stop_hook(
            {"sessionId": _SESSION_ID, "stop_hook_active": True},
            role,
            loader,
            state_path,
        )
        assert result == {}

    def test_block_response_has_required_structure(self, tmp_path: Path) -> None:
        """Block response contains hookSpecificOutput with hookEventName and reason."""
        loader = _StubLoader()
        role = "imp"
        sub_role = loader.default_sub_role(role)  # enforced
        state_path = tmp_path / "state.json"
        state_path.write_text(_make_state(role, sub_role))
        result = evaluate_stop_hook({"sessionId": _SESSION_ID}, role, loader, state_path)
        hook_output = result.get("hookSpecificOutput")
        assert isinstance(hook_output, dict)
        assert hook_output.get("hookEventName") == "Stop"
        assert hook_output.get("decision") == "block"
        assert isinstance(hook_output.get("reason"), str)
        assert hook_output["reason"]  # non-empty


_STOP_LOGGER_NAME = "copilot_orchestration.hooks.stop_handover_guard"


class TestStopHandoverGuardLogging:
    """Logging behaviour of evaluate_stop_hook."""

    def test_block_decision_logged_at_info(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """evaluate_stop_hook logs at INFO when a BLOCK decision is made."""
        loader = _StubLoader()
        role = "imp"
        sub_role = loader.default_sub_role(role)  # enforced → produces block
        state_path = tmp_path / "state.json"
        state_path.write_text(_make_state(role, sub_role))
        with caplog.at_level(logging.INFO, logger=_STOP_LOGGER_NAME):
            evaluate_stop_hook({"sessionId": _SESSION_ID}, role, loader, state_path)
        assert any(
            "block" in r.message.lower() and r.levelno == logging.INFO for r in caplog.records
        )

    def test_allow_decision_logged_at_debug(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """evaluate_stop_hook logs at DEBUG when an ALLOW (pass-through) decision is made."""
        loader = _StubLoader()
        role = "imp"
        non_enforced = next(
            s
            for s in sorted(loader.valid_sub_roles(role))
            if not loader.requires_crosschat_block(role, s)
        )
        state_path = tmp_path / "state.json"
        state_path.write_text(_make_state(role, non_enforced))
        with caplog.at_level(logging.DEBUG, logger=_STOP_LOGGER_NAME):
            evaluate_stop_hook({"sessionId": _SESSION_ID}, role, loader, state_path)
        assert any(r.levelno == logging.DEBUG for r in caplog.records)


class TestBuildStopReason:
    """Tests for build_stop_reason assertiveness — S2.

    The stop reason must be short, directive, and action-focused.
    Meta-text that wastes tokens without improving compliance is forbidden.
    """

    def test_contains_immediate_write_directive(self) -> None:
        """Reason must instruct the model to write the block immediately."""
        result = build_stop_reason(_SPEC_STUB)
        lower = result.lower()
        # Must contain an action directive ("write", "now", or both in proximity)
        assert "write" in lower or "now" in lower, (
            "build_stop_reason must contain an immediate write directive"
        )

    def test_contains_heading_from_spec(self) -> None:
        """Heading from spec must appear in the reason text."""
        result = build_stop_reason(_SPEC_STUB)
        assert _SPEC_STUB["heading"] in result

    def test_contains_each_marker(self) -> None:
        """Every required marker section must be mentioned."""
        result = build_stop_reason(_SPEC_STUB)
        for marker in _SPEC_STUB["markers"]:
            assert marker in result, f"Marker {marker!r} missing from stop reason"

    def test_block_prefix_in_reason(self) -> None:
        """The block_prefix must appear so model knows the exact opening line."""
        result = build_stop_reason(_SPEC_STUB)
        assert _SPEC_STUB["block_prefix"] in result

    def test_no_meta_apology_instructions(self) -> None:
        """Waste-token meta-instructions must be absent."""
        result = build_stop_reason(_SPEC_STUB)
        forbidden = ["no prose", "no explanation", "no apology"]
        for phrase in forbidden:
            assert phrase.lower() not in result.lower(), (
                f"Forbidden meta-instruction {phrase!r} found in stop reason"
            )

    def test_reason_under_600_chars(self) -> None:
        """Stop reason must be concise — under 600 characters."""
        result = build_stop_reason(_SPEC_STUB)
        assert len(result) < 600, (
            f"build_stop_reason is {len(result)} chars; must be < 600 for assertiveness"
        )

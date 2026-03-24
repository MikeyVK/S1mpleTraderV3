# src\copilot_orchestration\hooks\detect_sub_role.py
# template=generic version=f35abd82 created=2026-03-21T12:54Z updated=
"""detect_sub_role module.

Pure query functions that detect sub-role from user prompt text.

__main__ block owns all I/O (reads stdin JSON,
writes SessionSubRoleState to role-scoped state file).

@layer: copilot_orchestration (Hooks)
@dependencies: [None]
@responsibilities:
    - _match_sub_role(prompt, loader, role) -> str | None: core matching engine,
      returns matched sub-role or None when nothing found (no fallback applied)
    - detect_sub_role(prompt, loader, role) -> str: public API, wraps _match_sub_role
      and falls back to loader.default_sub_role(role) when None is returned
    - Step 0: strip /command prefix if present
    - Step 1: regex match against loader.valid_sub_roles(role) candidates (case-insensitive)
    - Step 2: difflib.get_close_matches on words >= 7 chars, cutoff 0.85
    - __main__ block: reads sys.argv[1] (role), stdin JSON;
      first-word extraction capped at loader.max_sub_role_name_len() (from YAML config);
      calls _match_sub_role for the matching decision (single algorithm);
      writes SessionSubRoleState to role-scoped file on match;
      exploration mode (no match) -> does nothing
"""

# Standard library
import difflib
import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

# Project modules
from copilot_orchestration.config.logging_config import LoggingConfig
from copilot_orchestration.config.requirements_loader import SubRoleRequirementsLoader
from copilot_orchestration.contracts.interfaces import (
    ISubRoleRequirementsLoader,
    SessionSubRoleState,
    SubRoleSpec,
)
from copilot_orchestration.utils._paths import find_workspace_root, state_path_for_role

logger = logging.getLogger(__name__)

JsonObject = dict[str, object]

_SLASH_CMD_RE = re.compile(r"^/\S+\s*")


def _match_sub_role(
    prompt: str,
    loader: ISubRoleRequirementsLoader,
    role: str,
) -> str | None:
    """Core matching engine — returns matched sub-role or None (no fallback applied).

    Pure query — no I/O, no side effects.
    Returns None when neither regex nor difflib finds a candidate.
    """
    # Step 0: strip /command prefix (e.g. /start-work, /resume-work)
    cleaned = _SLASH_CMD_RE.sub("", prompt.strip())

    candidates = loader.valid_sub_roles(role)

    # Step 1: exact / normalised match
    match = re.search(
        r"\b(" + "|".join(re.escape(s) for s in candidates) + r")\b",
        cleaned,
        re.IGNORECASE,
    )
    if match:
        result = match.group(1).lower().replace(" ", "-")
        logger.debug("_match_sub_role: matched %r for role %r", result, role)
        return result

    # Step 2: typo correction via difflib (words >= 7 chars only)
    words = [w for w in re.split(r"\W+", cleaned) if len(w) >= 7]
    close = difflib.get_close_matches(" ".join(words), list(candidates), n=1, cutoff=0.85)
    result = close[0] if close else None
    logger.debug("_match_sub_role: result=%r for role %r", result, role)
    return result


def detect_sub_role(
    prompt: str,
    loader: ISubRoleRequirementsLoader,
    role: str,
) -> str:
    """Detect sub-role from prompt text.

    Public API — always returns a member of loader.valid_sub_roles(role).
    Falls back to loader.default_sub_role(role) when no match found.
    Pure query — no I/O, no side effects.
    """
    return _match_sub_role(prompt, loader, role) or loader.default_sub_role(role)


def build_crosschat_block_instruction(sub_role: str, spec: SubRoleSpec) -> str:
    """Canonical cross-chat block instruction injected at all three hook points.

    Compact, complete, and identical at S1/S2/S3 to create reinforcement.
    Pure function — no I/O, no side effects.
    """
    markers = "\n".join(f"  {i + 1}. {m}" for i, m in enumerate(spec["markers"]))
    return (
        f"[{sub_role}] End your response with this block:\n\n"
        "> **✂ cross-chat block**\n>\n"
        f"> {spec['block_prefix'].strip()}\n"
        f"> {spec['guide_line'].strip()}\n\n"
        f"Required sections:\n{markers}"
    )


def build_ups_output(
    sub_role: str,
    loader: ISubRoleRequirementsLoader,
    role: str,
) -> JsonObject:
    """Build UserPromptSubmit hookSpecificOutput for front-loading handover instruction.

    Returns a hookSpecificOutput dict with a systemMessage when the sub-role
    requires a crosschat block, so the agent sees the instruction before
    generating output — not just at Stop time.

    Returns {} when requires_crosschat_block is False (no injection needed).
    Pure query — no I/O, no side effects.
    """
    if not loader.requires_crosschat_block(role, sub_role):
        return {}
    spec = loader.get_requirement(role, sub_role)
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "systemMessage": build_crosschat_block_instruction(sub_role, spec),
        }
    }


def main() -> None:  # pragma: no cover
    role = sys.argv[1]
    payload = json.loads(sys.stdin.read())
    prompt_text: str = payload.get("prompt", "")
    session_id: str = payload.get("sessionId", "")

    workspace_root = find_workspace_root(Path(__file__))
    LoggingConfig.from_copilot_dir(workspace_root).apply()
    state_path = workspace_root / state_path_for_role(role)
    _loader = SubRoleRequirementsLoader.from_copilot_dir(workspace_root)

    # Input preparation: strip /command prefix, extract and sanitise first word.
    # Cap length at loader.max_sub_role_name_len() (from YAML config) before
    # passing to the matching engine (_match_sub_role) — no matching logic here.
    _max_len = _loader.max_sub_role_name_len()
    _stripped = _SLASH_CMD_RE.sub("", prompt_text.strip())
    _words = _stripped.split()
    _first_word = re.sub(r"[^\w-]", "", _words[0]).lower()[:_max_len] if _words else ""

    _detected = _match_sub_role(_first_word, _loader, role)
    if _detected:
        # Match found: always write role-scoped file (allows mid-session sub-role change)
        _state: SessionSubRoleState = {
            "session_id": session_id,  # stored for audit only, not used for decisions
            "role": role,
            "sub_role": _detected,
            "detected_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        state_path.write_text(json.dumps(_state))
        # S1: front-load handover instruction via UserPromptSubmit systemMessage
        _ups = build_ups_output(_detected, _loader, role)
        if _ups:
            json.dump(_ups, sys.stdout, ensure_ascii=True)
    # No match: exploration mode — preserve existing file or do nothing


if __name__ == "__main__":  # pragma: no cover
    main()

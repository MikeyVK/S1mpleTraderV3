# src\copilot_orchestration\hooks\detect_sub_role.py
# template=generic version=f35abd82 created=2026-03-21T12:54Z updated=
"""detect_sub_role module.

Pure query function that detects sub-role from user prompt text.

__main__ block owns all I/O (reads stdin JSON,
writes SessionSubRoleState to role-scoped state file).

@layer: copilot_orchestration (Hooks)
@dependencies: [None]
@responsibilities:
    - detect_sub_role(prompt, loader, role) -> str: pure query, no I/O, no side effects
    - Step 0: strip /command prefix if present
    - Step 1: regex match against loader.valid_sub_roles(role) candidates (case-insensitive)
    - Step 2: difflib.get_close_matches on words >= 7 chars, cutoff 0.85
    - Fallback: loader.default_sub_role(role)
    - __main__ block: reads sys.argv[1] (role), stdin JSON;
      first-word detection; writes SessionSubRoleState to role-scoped file;
      exploration mode (no file + no match) -> does nothing
"""

# Standard library
import difflib
import logging
import re

# Project modules
from copilot_orchestration.contracts.interfaces import ISubRoleRequirementsLoader

logger = logging.getLogger(__name__)

_SLASH_CMD_RE = re.compile(r"^/\S+\s*")


def detect_sub_role(
    prompt: str,
    loader: ISubRoleRequirementsLoader,
    role: str,
) -> str:
    """Detect sub-role from prompt text.

    Pure query — no I/O, no side effects.
    Returns a member of loader.valid_sub_roles(role).
    Falls back to loader.default_sub_role(role) when no match found.
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
        return match.group(1).lower().replace(" ", "-")

    # Step 2: typo correction via difflib (words >= 7 chars only)
    words = [w for w in re.split(r"\W+", cleaned) if len(w) >= 7]
    close = difflib.get_close_matches(" ".join(words), list(candidates), n=1, cutoff=0.85)
    return close[0] if close else loader.default_sub_role(role)


if __name__ == "__main__":  # pragma: no cover
    import json
    import sys
    from datetime import UTC, datetime
    from pathlib import Path

    from copilot_orchestration.config.requirements_loader import SubRoleRequirementsLoader
    from copilot_orchestration.contracts.interfaces import SessionSubRoleState
    from copilot_orchestration.utils._paths import find_workspace_root, state_path_for_role

    role = sys.argv[1]
    payload = json.loads(sys.stdin.read())
    prompt_text: str = payload.get("prompt", "")
    session_id: str = payload.get("sessionId", "")

    workspace_root = find_workspace_root(Path(__file__))
    state_path = workspace_root / state_path_for_role(role)
    _loader = SubRoleRequirementsLoader.from_copilot_dir(workspace_root)

    # Strip /command prefix then extract first word for role detection
    _cleaned = _SLASH_CMD_RE.sub("", prompt_text.strip())
    _first_token = _cleaned.split()[0] if _cleaned.split() else ""
    _first_word = re.sub(r"[^\w-]", "", _first_token).lower()

    _valid = _loader.valid_sub_roles(role)
    _match = next((s for s in _valid if s.lower() == _first_word), None)

    if _match:
        # Match found: always write role-scoped file (allows mid-session sub-role change)
        _state: SessionSubRoleState = {
            "session_id": session_id,  # stored for audit only, not used for decisions
            "role": role,
            "sub_role": _match,
            "detected_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
        state_path.write_text(json.dumps(_state))
    # No match: if file exists, preserve it; if no file, stay silent (exploration mode)

# src\copilot_orchestration\hooks\detect_sub_role.py
# template=generic version=f35abd82 created=2026-03-21T12:54Z updated=
"""detect_sub_role module.

Pure query function that detects sub-role from user prompt text. __main__ block owns all I/O (reads stdin JSON, writes SessionSubRoleState to state file).

@layer: copilot_orchestration (Hooks)
@dependencies: [None]
@responsibilities:
    - detect_sub_role(prompt, loader, role) -> str: pure query, no I/O, no side effects
    - Step 1: regex match against loader.valid_sub_roles(role) candidates (case-insensitive)
    - Step 2: difflib.get_close_matches on words >= 7 chars, cutoff 0.85
    - Fallback: loader.default_sub_role(role)
    - __main__ block: reads sys.argv[1] (role), stdin JSON; idempotency check; writes SessionSubRoleState
"""

# Standard library
import difflib
import logging
import re

# Third-party

# Project modules
from copilot_orchestration.contracts.interfaces import ISubRoleRequirementsLoader

logger = logging.getLogger(__name__)


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
    candidates = loader.valid_sub_roles(role)

    # Step 1: exact / normalised match
    match = re.search(
        r"\b(" + "|".join(re.escape(s) for s in candidates) + r")\b",
        prompt,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).lower().replace(" ", "-")

    # Step 2: typo correction via difflib (words >= 7 chars only)
    words = [w for w in re.split(r"\W+", prompt) if len(w) >= 7]
    close = difflib.get_close_matches(" ".join(words), list(candidates), n=1, cutoff=0.85)
    return close[0] if close else loader.default_sub_role(role)


if __name__ == "__main__":  # pragma: no cover
    import json
    import sys
    from datetime import datetime
    from pathlib import Path

    from copilot_orchestration.config.requirements_loader import SubRoleRequirementsLoader
    from copilot_orchestration.contracts.interfaces import SessionSubRoleState
    from copilot_orchestration.utils._paths import STATE_RELPATH, find_workspace_root

    role = sys.argv[1]
    payload = json.loads(sys.stdin.read())
    prompt_text: str = payload.get("prompt", "")
    session_id: str = payload.get("sessionId", "")

    workspace_root = find_workspace_root(Path(__file__))
    state_path = workspace_root / STATE_RELPATH
    _loader = SubRoleRequirementsLoader.from_copilot_dir(workspace_root)

    try:
        existing = json.loads(state_path.read_text())
        if existing.get("session_id") == session_id:
            sys.exit(0)
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    _sub_role = detect_sub_role(prompt_text, _loader, role)
    _state: SessionSubRoleState = {
        "session_id": session_id,
        "role": role,
        "sub_role": _sub_role,
        "detected_at": datetime.utcnow().isoformat() + "Z",
    }
    state_path.write_text(json.dumps(_state))

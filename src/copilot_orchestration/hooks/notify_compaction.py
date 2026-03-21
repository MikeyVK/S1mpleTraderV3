# src\copilot_orchestration\hooks\notify_compaction.py
# template=generic version=f35abd82 created=2026-03-21T13:42Z updated=
"""NotifyCompaction module.

PreCompact hook — thin __main__-only adapter.

Reads state file for current sub_role, writes a systemMessage so the agent
remembers its active sub-role after context compaction.
Exit 0 always (soft failure — hook errors must not break agent session).

@layer: copilot_orchestration (Hooks)
@dependencies: [None]
@responsibilities:
    - Read sessionId from stdin JSON payload
    - Resolve state path via find_workspace_root + STATE_RELPATH
    - If state file exists and session_id matches: output systemMessage with active sub-role
    - If session_id mismatch or file absent: output {}
    - Always exit 0 (soft failure — hook errors must not break agent session)
"""

# Standard library
import json
import sys
from pathlib import Path

# Project modules
from copilot_orchestration.utils._paths import STATE_RELPATH, find_workspace_root

if __name__ == "__main__":  # pragma: no cover
    workspace_root = find_workspace_root(Path(__file__))
    state_path = workspace_root / STATE_RELPATH

    payload = json.loads(sys.stdin.read())
    session_id: str = payload.get("sessionId", "")

    output: dict[str, object] = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except json.JSONDecodeError:
            state = {}

        if state.get("session_id") == session_id:
            sub_role = str(state.get("sub_role", "unknown"))
            output = {
                "systemMessage": (
                    f"Context was compacted. Your active sub-role is **{sub_role}**. "
                    "Use /resume-work to restore full behavioral context before continuing."
                )
            }

    print(json.dumps(output))

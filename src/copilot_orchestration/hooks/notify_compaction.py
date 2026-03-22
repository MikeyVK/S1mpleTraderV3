# src\copilot_orchestration\hooks\notify_compaction.py
# template=generic version=f35abd82 created=2026-03-21T13:42Z updated=
"""NotifyCompaction module.

PreCompact hook — thin __main__-only adapter.

Reads role-scoped state file for current sub_role, writes a systemMessage so the
agent remembers its active sub-role after context compaction.
Exit 0 always (soft failure — hook errors must not break agent session).

@layer: copilot_orchestration (Hooks)
@dependencies: [None]
@responsibilities:
    - Read role from sys.argv[1]
    - Resolve state path via find_workspace_root + state_path_for_role(role)
    - If state file exists and contains a sub_role: output systemMessage
    - If file absent or unreadable: output {}
    - Always exit 0 (soft failure — hook errors must not break agent session)
"""

# Standard library
import json
import logging
import sys
from pathlib import Path

# Project modules
from copilot_orchestration.utils._paths import find_workspace_root, state_path_for_role

logger = logging.getLogger(__name__)


def build_compaction_output(state: dict[str, object]) -> dict[str, object]:
    """Return systemMessage dict when state contains a sub_role, else empty dict."""
    sub_role = state.get("sub_role")
    if sub_role:
        logger.info("compaction output: sub_role=%s", sub_role)
        return {
            "systemMessage": (
                f"Context was compacted. Your active sub-role is **{sub_role}**. "
                "Use /resume-work to restore full behavioral context before continuing."
            )
        }
    logger.debug("no sub_role in state — empty compaction output")
    return {}


if __name__ == "__main__":  # pragma: no cover
    role = sys.argv[1] if len(sys.argv) > 1 else "imp"
    workspace_root = find_workspace_root(Path(__file__))
    state_path = workspace_root / state_path_for_role(role)

    # Consume stdin (required by hook protocol, sessionId not used for decisions)
    json.loads(sys.stdin.read())

    state: dict[str, object] = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except json.JSONDecodeError:
            state = {}

    print(json.dumps(build_compaction_output(state)))

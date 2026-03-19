from __future__ import annotations

import json
import sys


# Workspace-level PreCompact hook — fires for all sessions.
#
# Standard chats rely on VS Code's built-in conversation compaction summary.
# Snapshot persistence is reserved for agent-specific hooks so generic sessions
# do not create .copilot/sessions/*.json noise.
def main() -> None:
    json.dump({}, sys.stdout, ensure_ascii=True)


if __name__ == "__main__":
    main()

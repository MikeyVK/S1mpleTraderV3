from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

MAX_CHANGED_FILES = 8


def main() -> None:
    workspace_root = Path(__file__).resolve().parents[2]
    branch_name = run_git_command(
        workspace_root,
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
    )
    changed_files = get_changed_files(workspace_root)

    context_lines: list[str] = ["Workspace context:"]

    if branch_name:
        context_lines.append(f"- Branch: {branch_name}")

    if changed_files:
        displayed = ", ".join(changed_files[:MAX_CHANGED_FILES])
        if len(changed_files) > MAX_CHANGED_FILES:
            displayed += ", ..."
        context_lines.append(f"- Changed files: {displayed}")
    else:
        context_lines.append("- Changed files: none")

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(context_lines),
        }
    }
    json.dump(output, sys.stdout, ensure_ascii=True)


def get_changed_files(workspace_root: Path) -> list[str]:
    status_output = run_git_command(
        workspace_root,
        ["git", "status", "--porcelain=v1", "--untracked-files=normal"],
    )
    if not status_output:
        return []

    changed_files: list[str] = []
    for line in status_output.splitlines():
        if len(line) < 4:
            continue
        path_part = line[3:].strip()
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1].strip()
        if path_part:
            changed_files.append(path_part.replace("\\", "/"))
    return changed_files


def run_git_command(workspace_root: Path, command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=workspace_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ""

    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


if __name__ == "__main__":
    main()

from __future__ import annotations

# Agent-specific SessionStart hook for @imp.
# The workspace-level session_start.py already injects branch and changed files.
# This script adds implementation-specific context: snapshot recovery, pending
# handover, and role recommendations.  It is invoked via hooks: in imp.agent.md.
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

SNAPSHOT_RELATIVE_PATH = Path(".copilot") / "session-state.json"
JsonObject = dict[str, object]
MAX_CHANGED_FILES = 8
MAX_SCOPE_FILES = 8
MAX_GOAL_LENGTH = 280
MAX_HANDOVER_LENGTH = 200
MAX_PROMPT_BLOCK_LENGTH = 500
SNAPSHOT_MAX_AGE_HOURS = 6


def main() -> None:
    workspace_root = Path(__file__).resolve().parents[3]
    snapshot = read_json_file(workspace_root / SNAPSHOT_RELATIVE_PATH)
    changed_files = get_changed_files(workspace_root)
    snapshot_is_fresh = is_usable_snapshot(snapshot, changed_files)

    context_lines: list[str] = ["Implementation context:"]

    if snapshot_is_fresh:
        active_role = as_clean_text(snapshot.get("active_role"))
        if active_role:
            context_lines.append(f"- Last active role: @{active_role}")

        last_user_goal = as_clean_text(snapshot.get("last_user_goal"))
        if last_user_goal:
            context_lines.append(f"- Last user goal: {truncate(last_user_goal, MAX_GOAL_LENGTH)}")

        files_in_scope = as_string_list(snapshot.get("files_in_scope"))
        if files_in_scope:
            displayed_scope = ", ".join(files_in_scope[:MAX_SCOPE_FILES])
            if len(files_in_scope) > MAX_SCOPE_FILES:
                displayed_scope = f"{displayed_scope}, ..."
            context_lines.append(f"- Files in scope: {displayed_scope}")

        pending_handover_summary = as_clean_text(snapshot.get("pending_handover_summary"))
        if pending_handover_summary:
            context_lines.append(
                f"- Pending handover: {truncate(pending_handover_summary, MAX_HANDOVER_LENGTH)}"
            )

        handover_prompt_block = as_clean_text(snapshot.get("handover_prompt_block"))
        if handover_prompt_block:
            context_lines.append(
                "- Stored handoff prompt block: "
                f"{truncate(handover_prompt_block, MAX_PROMPT_BLOCK_LENGTH)}"
            )

        if pending_handover_summary or handover_prompt_block:
            context_lines.append(
                "- Recommended next step: continue implementation or use "
                "/prepare-handover before switching to @qa."
            )
        else:
            context_lines.append(
                "- Recommended next step: use /start-implementation "
                "to establish scope before coding."
            )
    elif snapshot:
        context_lines.append("- Snapshot ignored: stale or not relevant to current changed files.")
        context_lines.append(
            "- Recommended next step: use /start-implementation "
            "and restate the active goal explicitly."
        )
    else:
        context_lines.append(
            "- No snapshot found. Recommended next step: use "
            "/start-implementation to establish scope."
        )

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


def read_json_file(path: Path) -> JsonObject:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def is_usable_snapshot(snapshot: JsonObject, changed_files: list[str]) -> bool:
    timestamp = snapshot.get("timestamp")
    if not isinstance(timestamp, str) or not timestamp.strip():
        return False
    try:
        snapshot_time = datetime.fromisoformat(timestamp)
    except ValueError:
        return False
    if snapshot_time.tzinfo is None:
        snapshot_time = snapshot_time.replace(tzinfo=UTC)
    age = datetime.now(UTC) - snapshot_time.astimezone(UTC)
    if age.total_seconds() > SNAPSHOT_MAX_AGE_HOURS * 3600:
        return False

    snapshot_files = as_string_list(snapshot.get("files_in_scope"))
    if not changed_files:
        return False
    if snapshot_files:
        changed_set = set(changed_files)
        snapshot_set = set(snapshot_files)
        if changed_set.isdisjoint(snapshot_set):
            return False

    return True


def as_clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.split())
    return normalized.strip()


def as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        if isinstance(item, str):
            normalized = item.strip()
            if normalized:
                items.append(normalized.replace("\\", "/"))
    return items


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


if __name__ == "__main__":
    main()

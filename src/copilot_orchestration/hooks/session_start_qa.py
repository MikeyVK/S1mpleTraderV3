from __future__ import annotations

# Agent-specific SessionStart hook for @qa.
# The workspace-level session_start.py already injects branch and changed files.
# This script adds QA-specific context: pending handover from snapshot, implementation
# scope, and review recommendations.  It is invoked via hooks: in qa.agent.md.
import json
import logging
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from copilot_orchestration.config.logging_config import LoggingConfig

SNAPSHOT_RELATIVE_PATH = Path(".copilot") / "session-state.json"
JsonObject = dict[str, object]
MAX_FILES_IN_SCOPE = 8
MAX_GOAL_LENGTH = 280
MAX_HANDOVER_LENGTH = 400
MAX_PROMPT_BLOCK_LENGTH = 800
SNAPSHOT_MAX_AGE_HOURS = 6

logger = logging.getLogger(__name__)


def main() -> None:
    workspace_root = Path(__file__).resolve().parents[3]
    LoggingConfig.from_copilot_dir(workspace_root).apply()
    logger.info("session_start_qa: starting for workspace=%s", workspace_root)
    snapshot = read_json_file(workspace_root / SNAPSHOT_RELATIVE_PATH)
    changed_files = get_changed_files(workspace_root)
    snapshot_is_fresh = is_usable_snapshot(snapshot, changed_files)
    if snapshot_is_fresh:
        logger.debug("session_start_qa: snapshot fresh")
    elif snapshot:
        logger.debug("session_start_qa: snapshot stale or irrelevant")
    else:
        logger.debug("session_start_qa: no snapshot found")

    context_lines: list[str] = ["QA context:"]

    if snapshot_is_fresh:
        active_role = as_clean_text(snapshot.get("active_role"))
        if active_role:
            context_lines.append(f"- Last active role: @{active_role}")

        last_user_goal = as_clean_text(snapshot.get("last_user_goal"))
        if last_user_goal:
            context_lines.append(
                f"- Implementation goal: {truncate(last_user_goal, MAX_GOAL_LENGTH)}"
            )

        files_in_scope = as_string_list(snapshot.get("files_in_scope"))
        if files_in_scope:
            displayed = ", ".join(files_in_scope[:MAX_FILES_IN_SCOPE])
            if len(files_in_scope) > MAX_FILES_IN_SCOPE:
                displayed += ", ..."
            context_lines.append(f"- Implementation scope: {displayed}")

        pending_handover_summary = as_clean_text(snapshot.get("pending_handover_summary"))
        if pending_handover_summary:
            context_lines.append(
                f"- Pending handover: {truncate(pending_handover_summary, MAX_HANDOVER_LENGTH)}"
            )

        handover_prompt_block = as_clean_text(snapshot.get("handover_prompt_block"))
        if handover_prompt_block:
            context_lines.append(
                "- Stored handoff prompt: "
                f"{truncate(handover_prompt_block, MAX_PROMPT_BLOCK_LENGTH)}"
            )

        if pending_handover_summary or handover_prompt_block:
            context_lines.append(
                "- Recommended next step: use /request-qa-review to start "
                "a structured review of the implementation hand-over."
            )
        else:
            context_lines.append(
                "- No hand-over found in snapshot. Ask @imp to "
                "/prepare-handover before starting review."
            )
    elif snapshot:
        context_lines.append("- Snapshot ignored: stale or not relevant to current changed files.")
        context_lines.append(
            "- Recommended next step: ask @imp for a structured hand-over before starting review."
        )
    else:
        context_lines.append("- No implementation snapshot found.")
        context_lines.append(
            "- Recommended next step: ask @imp to complete implementation "
            "and /prepare-handover first."
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
        logger.debug("snapshot rejected: stale (age %.0fs)", age.total_seconds())
        return False

    snapshot_files = as_string_list(snapshot.get("files_in_scope"))
    if not changed_files:
        logger.debug("snapshot rejected: no changed files")
        return False
    if snapshot_files:
        changed_set = set(changed_files)
        snapshot_set = set(snapshot_files)
        if changed_set.isdisjoint(snapshot_set):
            logger.debug("snapshot rejected: no file overlap")
            return False

    logger.debug("snapshot accepted")
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

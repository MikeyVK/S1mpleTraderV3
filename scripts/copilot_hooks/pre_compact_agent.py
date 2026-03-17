from __future__ import annotations

# Agent-specific PreCompact hook — fires for @imp and @qa sessions in addition
# to the workspace-level pre_compact.py.
#
# Writes a rich snapshot to TWO locations:
#   1. .copilot/sessions/{chat_id}.json  — per-chat (same as workspace hook,
#      overwritten here with richer content: handover, prompt block, role)
#   2. .copilot/session-state.json       — shared cross-session handover state
#      that @imp and @qa SessionStart hooks read to recover context
#
# The workspace-level hook writes only to location 1 (per-chat, lightweight).
# This script additionally writes to location 2, which is the path that
# session_start_imp.py and session_start_qa.py read for cross-chat recovery.

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SHARED_SNAPSHOT_PATH = Path(".copilot") / "session-state.json"
SESSIONS_DIR = Path(".copilot") / "sessions"
MAX_FILES_IN_SCOPE = 12
MAX_GOAL_LENGTH = 400
MAX_HANDOVER_LENGTH = 300
MAX_PROMPT_BLOCK_LENGTH = 1200
FILE_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+"
    r"\.(?:py|md|json|yaml|yml|toml|ini|txt|ps1|sh|ts|tsx|js|jsx)"
)


def main() -> None:
    workspace_root = Path(__file__).resolve().parents[2]
    event = read_stdin_json()

    chat_id = derive_chat_id(event)
    transcript_payload = read_transcript(event, workspace_root)
    message_records = collect_message_records(transcript_payload)
    text_fragments = collect_text_fragments(transcript_payload)
    if not text_fragments:
        text_fragments = collect_text_fragments(event)

    previous_snapshot = read_json_file(workspace_root / SHARED_SNAPSHOT_PATH)

    last_user_goal = (
        extract_last_user_goal(message_records)
        or extract_goal_from_text_fragments(text_fragments)
        or as_clean_text(previous_snapshot.get("last_user_goal"))
    )
    active_role = (
        infer_active_role(message_records)
        or infer_role_from_text_fragments(text_fragments)
        or as_clean_text(previous_snapshot.get("active_role"))
    )
    files_in_scope = (
        extract_files_in_scope(message_records)
        or extract_files_from_text_fragments(text_fragments)
        or as_string_list(previous_snapshot.get("files_in_scope"))
    )
    pending_handover_summary = (
        extract_pending_handover_summary(message_records)
        or extract_handover_from_text_fragments(text_fragments)
    )
    handover_prompt_block = extract_handover_prompt_block(message_records)

    now = datetime.now(timezone.utc).isoformat()

    per_chat_snapshot = {
        "timestamp": now,
        "chat_id": chat_id,
        "active_role": active_role or "imp",
        "last_user_goal": truncate(last_user_goal, MAX_GOAL_LENGTH),
        "files_in_scope": files_in_scope[:MAX_FILES_IN_SCOPE],
        "pending_handover_summary": truncate(pending_handover_summary, MAX_HANDOVER_LENGTH),
        "handover_prompt_block": truncate(handover_prompt_block, MAX_PROMPT_BLOCK_LENGTH),
        "snapshot_source": "pre_compact_agent",
    }

    # 1. Write per-chat snapshot (overrides the lightweight workspace version)
    sessions_dir = workspace_root / SESSIONS_DIR
    sessions_dir.mkdir(parents=True, exist_ok=True)
    per_chat_path = sessions_dir / f"{chat_id}.json"
    per_chat_path.write_text(
        json.dumps(per_chat_snapshot, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    # 2. Write shared cross-session snapshot for SessionStart recovery
    shared_snapshot = {k: v for k, v in per_chat_snapshot.items() if k != "chat_id"}
    shared_path = workspace_root / SHARED_SNAPSHOT_PATH
    shared_path.parent.mkdir(parents=True, exist_ok=True)
    shared_path.write_text(
        json.dumps(shared_snapshot, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    json.dump(
        {"systemMessage": (
            f"Saved agent snapshot to {per_chat_path.relative_to(workspace_root).as_posix()}"
            f" and {SHARED_SNAPSHOT_PATH.as_posix()}."
        )},
        sys.stdout,
        ensure_ascii=True,
    )


def derive_chat_id(event: dict[str, Any]) -> str:
    raw_path = event.get("transcript_path")
    if isinstance(raw_path, str) and raw_path.strip():
        return Path(raw_path).stem or "default"
    return "default"


def read_transcript(event: dict[str, Any], workspace_root: Path) -> dict[str, Any]:
    raw_path = event.get("transcript_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return {}
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    return read_json_file(candidate)


def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_stdin_json() -> dict[str, Any]:
    try:
        raw_input = sys.stdin.read()
    except OSError:
        return {}
    if not raw_input.strip():
        return {}
    try:
        return json.loads(raw_input)
    except json.JSONDecodeError:
        return {}


def collect_message_records(payload: Any) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    _visit_message_nodes(payload, records)
    return _deduplicate_records(records)


def collect_text_fragments(payload: Any) -> list[str]:
    fragments: list[str] = []
    _visit_text_nodes(payload, fragments)
    return _deduplicate_fragments(fragments)


def _visit_message_nodes(node: Any, records: list[dict[str, str]]) -> None:
    if isinstance(node, dict):
        role = as_clean_text(node.get("role"))
        text = _extract_text(node.get("content")) or _extract_text(node.get("text"))
        if role and text:
            records.append({"role": role.lower(), "text": text})
        for value in node.values():
            _visit_message_nodes(value, records)
    elif isinstance(node, list):
        for item in node:
            _visit_message_nodes(item, records)


def _visit_text_nodes(node: Any, fragments: list[str]) -> None:
    if isinstance(node, str):
        text = as_clean_text(node)
        if text:
            fragments.append(text)
    elif isinstance(node, dict):
        for value in node.values():
            _visit_text_nodes(value, fragments)
    elif isinstance(node, list):
        for item in node:
            _visit_text_nodes(item, fragments)


def _extract_text(node: Any) -> str:
    if isinstance(node, str):
        return as_clean_text(node)
    if isinstance(node, dict):
        for key in ("text", "value", "content"):
            extracted = _extract_text(node.get(key))
            if extracted:
                return extracted
        return as_clean_text(" ".join(v for v in (_extract_text(v) for v in node.values()) if v))
    if isinstance(node, list):
        return as_clean_text(" ".join(v for v in (_extract_text(i) for i in node) if v))
    return ""


def _deduplicate_records(records: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for r in records:
        key = (r["role"], r["text"])
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result


def _deduplicate_fragments(fragments: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for f in fragments:
        if f not in seen:
            seen.add(f)
            result.append(f)
    return result


def extract_last_user_goal(records: list[dict[str, str]]) -> str:
    for record in reversed(records):
        if record["role"] == "user" and record["text"]:
            return record["text"]
    return ""


def extract_goal_from_text_fragments(fragments: list[str]) -> str:
    for fragment in fragments:
        lowered = fragment.lower()
        if "scope" in lowered and "proof" in lowered and "ready-for-qa" in lowered:
            continue
        if lowered.endswith((".json", ".md")) or ":/" in lowered or ":\\" in lowered:
            continue
        if len(fragment) >= 20:
            return fragment
    return ""


def infer_active_role(records: list[dict[str, str]]) -> str:
    for record in reversed(records):
        text = record["text"].lower()
        if "@qa" in text or ".github/agents/qa.agent.md" in text:
            return "qa"
        if "@imp" in text or ".github/agents/imp.agent.md" in text:
            return "imp"
    return ""


def infer_role_from_text_fragments(fragments: list[str]) -> str:
    for fragment in reversed(fragments):
        lowered = fragment.lower()
        if "@qa" in lowered or ".github/agents/qa.agent.md" in lowered:
            return "qa"
        if "@imp" in lowered or ".github/agents/imp.agent.md" in lowered:
            return "imp"
    return ""


def extract_files_in_scope(records: list[dict[str, str]]) -> list[str]:
    discovered: list[str] = []
    seen: set[str] = set()
    for record in records:
        for match in FILE_PATH_PATTERN.findall(record["text"]):
            normalized = match.strip().replace("\\", "/")
            if normalized and normalized not in seen:
                seen.add(normalized)
                discovered.append(normalized)
    return discovered


def extract_files_from_text_fragments(fragments: list[str]) -> list[str]:
    discovered: list[str] = []
    seen: set[str] = set()
    for fragment in fragments:
        for match in FILE_PATH_PATTERN.findall(fragment):
            normalized = match.strip().replace("\\", "/")
            if normalized and normalized not in seen:
                seen.add(normalized)
                discovered.append(normalized)
    return discovered


def extract_pending_handover_summary(records: list[dict[str, str]]) -> str:
    for record in reversed(records):
        if record["role"] != "assistant":
            continue
        text = record["text"]
        lowered = text.lower()
        if "ready-for-qa" in lowered or "ready for qa" in lowered:
            return text
        if _has_handover_shape(lowered):
            return text
    return ""


def extract_handover_from_text_fragments(fragments: list[str]) -> str:
    for fragment in reversed(fragments):
        lowered = fragment.lower()
        if "ready-for-qa" in lowered or "ready for qa" in lowered:
            return fragment
        if _has_handover_shape(lowered):
            return fragment
    return ""


def extract_handover_prompt_block(records: list[dict[str, str]]) -> str:
    for record in reversed(records):
        if record["role"] != "assistant":
            continue
        block = _extract_fenced_text_block(record["text"])
        if block:
            return block
    return ""


def _extract_fenced_text_block(text: str) -> str:
    match = re.search(r"```text\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return as_clean_text(match.group(1))


def _has_handover_shape(text: str) -> bool:
    return all(m in text for m in ["scope", "files", "proof", "out-of-scope", "open blockers"])


def as_clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip()


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip().replace("\\", "/") for item in value if isinstance(item, str) and item.strip()]


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


if __name__ == "__main__":
    main()

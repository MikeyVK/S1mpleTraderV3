from __future__ import annotations

import json
import re
import sys
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SNAPSHOT_RELATIVE_PATH = Path(".copilot") / "session-state.json"
MAX_FILES_IN_SCOPE = 12
MAX_GOAL_LENGTH = 400
MAX_HANDOVER_LENGTH = 300
MAX_PROMPT_BLOCK_LENGTH = 1200
FILE_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.-])(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]+\.(?:py|md|json|yaml|yml|toml|ini|txt|ps1|sh|ts|tsx|js|jsx)"
)


def main() -> None:
    workspace_root = Path(__file__).resolve().parents[2]
    event = read_stdin_json()
    transcript_path = get_transcript_path(event, workspace_root)
    transcript_payload = read_json_file(transcript_path) if transcript_path else {}
    message_records = collect_message_records(transcript_payload)
    text_fragments = collect_text_fragments(transcript_payload)
    if not text_fragments:
        text_fragments = collect_text_fragments(event)

    previous_snapshot = read_json_file(workspace_root / SNAPSHOT_RELATIVE_PATH)

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

    snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "active_role": active_role or "imp",
        "last_user_goal": truncate(last_user_goal, MAX_GOAL_LENGTH),
        "files_in_scope": files_in_scope[:MAX_FILES_IN_SCOPE],
        "pending_handover_summary": truncate(
            pending_handover_summary,
            MAX_HANDOVER_LENGTH,
        ),
        "handover_prompt_block": truncate(
            handover_prompt_block,
            MAX_PROMPT_BLOCK_LENGTH,
        ),
        "snapshot_source": "pre_compact",
    }

    snapshot_path = workspace_root / SNAPSHOT_RELATIVE_PATH
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )

    json.dump(
        {
            "systemMessage": (
                f"Saved implementation snapshot to {SNAPSHOT_RELATIVE_PATH.as_posix()}."
            )
        },
        sys.stdout,
        ensure_ascii=True,
    )


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


def get_transcript_path(event: dict[str, Any], workspace_root: Path) -> Path | None:
    raw_path = event.get("transcript_path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    return candidate


def read_json_file(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def collect_message_records(payload: Any) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    visit_message_nodes(payload, records)
    return deduplicate_records(records)


def collect_text_fragments(payload: Any) -> list[str]:
    fragments: list[str] = []
    visit_text_nodes(payload, fragments)
    return deduplicate_text_fragments(fragments)


def visit_message_nodes(node: Any, records: list[dict[str, str]]) -> None:
    if isinstance(node, dict):
        role = as_clean_text(node.get("role"))
        text = extract_text(node.get("content")) or extract_text(node.get("text"))
        if role and text:
            records.append({"role": role.lower(), "text": text})
        for value in node.values():
            visit_message_nodes(value, records)
        return

    if isinstance(node, list):
        for item in node:
            visit_message_nodes(item, records)


def visit_text_nodes(node: Any, fragments: list[str]) -> None:
    if isinstance(node, str):
        text = as_clean_text(node)
        if text:
            fragments.append(text)
        return

    if isinstance(node, dict):
        for value in node.values():
            visit_text_nodes(value, fragments)
        return

    if isinstance(node, list):
        for item in node:
            visit_text_nodes(item, fragments)


def extract_text(node: Any) -> str:
    if isinstance(node, str):
        return as_clean_text(node)

    if isinstance(node, dict):
        for key in ("text", "value", "content"):
            extracted = extract_text(node.get(key))
            if extracted:
                return extracted
        values = [extract_text(value) for value in node.values()]
        return as_clean_text(" ".join(value for value in values if value))

    if isinstance(node, list):
        values = [extract_text(item) for item in node]
        return as_clean_text(" ".join(value for value in values if value))

    return ""


def deduplicate_records(records: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    unique_records: list[dict[str, str]] = []
    for record in records:
        key = (record["role"], record["text"])
        if key in seen:
            continue
        seen.add(key)
        unique_records.append(record)
    return unique_records


def deduplicate_text_fragments(fragments: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_fragments: list[str] = []
    for fragment in fragments:
        if fragment in seen:
            continue
        seen.add(fragment)
        unique_fragments.append(fragment)
    return unique_fragments


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
        if lowered.endswith(".json") or lowered.endswith(".md"):
            continue
        if ":/" in lowered or ":\\" in lowered:
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
    discovered_paths: list[str] = []
    seen: set[str] = set()

    for record in records:
        for match in FILE_PATH_PATTERN.findall(record["text"]):
            normalized = normalize_path(match)
            if normalized and normalized not in seen:
                seen.add(normalized)
                discovered_paths.append(normalized)

    return discovered_paths


def extract_files_from_text_fragments(fragments: list[str]) -> list[str]:
    discovered_paths: list[str] = []
    seen: set[str] = set()
    for fragment in fragments:
        for match in FILE_PATH_PATTERN.findall(fragment):
            normalized = normalize_path(match)
            if normalized and normalized not in seen:
                seen.add(normalized)
                discovered_paths.append(normalized)
    return discovered_paths


def extract_pending_handover_summary(records: list[dict[str, str]]) -> str:
    for record in reversed(records):
        if record["role"] != "assistant":
            continue
        text = record["text"]
        lowered = text.lower()
        if "ready-for-qa" in lowered or "ready for qa" in lowered:
            return text
        if has_handover_shape(lowered):
            return text
    return ""


def extract_handover_from_text_fragments(fragments: list[str]) -> str:
    for fragment in reversed(fragments):
        lowered = fragment.lower()
        if "ready-for-qa" in lowered or "ready for qa" in lowered:
            return fragment
        if has_handover_shape(lowered):
            return fragment
    return ""


def extract_handover_prompt_block(records: list[dict[str, str]]) -> str:
    for record in reversed(records):
        if record["role"] != "assistant":
            continue
        block = extract_first_fenced_text_block(record["text"])
        if block:
            return block
    return ""


def extract_first_fenced_text_block(text: str) -> str:
    match = re.search(r"```text\s*(.*?)```", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return as_clean_text(match.group(1))


def has_handover_shape(text: str) -> bool:
    required_markers = [
        "scope",
        "files",
        "proof",
        "out-of-scope",
        "open blockers",
    ]
    return all(marker in text for marker in required_markers)


def as_clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    normalized = " ".join(value.split())
    return normalized.strip()


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
        return []
    normalized_items: list[str] = []
    for item in value:
        if isinstance(item, str):
            normalized = normalize_path(item)
            if normalized:
                normalized_items.append(normalized)
    return normalized_items


def normalize_path(value: str) -> str:
    return value.strip().strip('"\'').replace("\\", "/")


def truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


if __name__ == "__main__":
    main()

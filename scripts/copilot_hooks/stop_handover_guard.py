from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import TypedDict

JsonObject = dict[str, object]


class RoleRequirement(TypedDict):
    heading: str
    block_prefix: str
    guide_line: str
    markers: list[str]


FENCED_TEXT_BLOCK_PATTERN = re.compile(r"```text\s*(.*?)```", re.IGNORECASE | re.DOTALL)
ROLE_REQUIREMENTS: dict[str, RoleRequirement] = {
    "imp": {
        "heading": "### Copy-Paste Prompt For QA Chat",
        "block_prefix": "@qa Review the latest implementation work on this branch.",
        "guide_line": "Use qa_agent.md as the project-specific QA guide.",
        "markers": [
            "Review target:",
            "Implementation claim under review:",
            "Proof provided by implementation:",
            "QA focus:",
        ],
    },
    "qa": {
        "heading": "### Copy-Paste Prompt For Implementation Chat",
        "block_prefix": "@imp Address the latest QA findings on this branch.",
        "guide_line": "Use imp_agent.md as the project-specific implementation guide.",
        "markers": [
            "Task:",
            "Files likely in scope:",
            "Required fixes:",
            "Out of scope:",
            "Required proof on return:",
            "Return requirement:",
        ],
    },
}


def main() -> None:
    role = normalize_role(sys.argv[1] if len(sys.argv) > 1 else "")
    event = read_stdin_json()
    json.dump(evaluate_stop_hook(event, role), sys.stdout, ensure_ascii=True)


def evaluate_stop_hook(event: JsonObject, role: str) -> JsonObject:
    if role not in ROLE_REQUIREMENTS:
        return {}
    if is_stop_retry_active(event):
        return {}

    transcript_payload = read_transcript(event)
    message_records = collect_message_records(transcript_payload)
    last_assistant_text = extract_last_assistant_text(message_records)
    if has_valid_handover(last_assistant_text, role):
        return {}

    return {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "decision": "block",
            "reason": build_stop_reason(role),
        }
    }


def normalize_role(value: str) -> str:
    return value.strip().lower()


def is_stop_retry_active(event: JsonObject) -> bool:
    value = event.get("stop_hook_active")
    if isinstance(value, bool):
        return value
    return False


def read_transcript(event: JsonObject) -> object:
    raw_path = event.get("transcript_path") or event.get("transcriptPath")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return {}

    candidate = Path(raw_path)
    if not candidate.is_absolute():
        cwd = event.get("cwd")
        if isinstance(cwd, str) and cwd.strip():
            candidate = Path(cwd) / candidate
    try:
        return parse_transcript_content(candidate.read_text(encoding="utf-8-sig"))
    except OSError:
        return {}


def parse_transcript_content(raw_text: str) -> object:
    stripped = raw_text.lstrip("\ufeff").strip()
    if not stripped:
        return {}
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        records: list[object] = []
        for line in stripped.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                return {}
        if not records:
            return {}
        if len(records) == 1:
            return records[0]
        return records


def read_stdin_json() -> JsonObject:
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


def collect_message_records(payload: object) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    _visit_message_nodes(payload, records)
    return deduplicate_records(records)


def _visit_message_nodes(node: object, records: list[dict[str, str]]) -> None:
    if isinstance(node, dict):
        role = clean_text(node.get("role"))
        text = extract_text(node.get("content")) or extract_text(node.get("text"))
        if role and text:
            records.append({"role": role.lower(), "text": text})
        for value in node.values():
            _visit_message_nodes(value, records)
    elif isinstance(node, list):
        for item in node:
            _visit_message_nodes(item, records)


def extract_text(node: object) -> str:
    if isinstance(node, str):
        return clean_text(node)
    if isinstance(node, dict):
        for key in ("text", "value", "content"):
            extracted = extract_text(node.get(key))
            if extracted:
                return extracted
        combined = " ".join(part for part in (extract_text(v) for v in node.values()) if part)
        return clean_text(combined)
    if isinstance(node, list):
        combined = " ".join(part for part in (extract_text(i) for i in node) if part)
        return clean_text(combined)
    return ""


def deduplicate_records(records: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for record in records:
        key = (record["role"], record["text"])
        if key not in seen:
            seen.add(key)
            result.append(record)
    return result


def clean_text(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).strip()


def extract_last_assistant_text(records: list[dict[str, str]]) -> str:
    for record in reversed(records):
        if record["role"] == "assistant":
            return record["text"]
    return ""


def has_valid_handover(text: str, role: str) -> bool:
    if not text:
        return False

    requirements = ROLE_REQUIREMENTS[role]
    if requirements["heading"] not in text:
        return False

    blocks = FENCED_TEXT_BLOCK_PATTERN.findall(text)
    if len(blocks) != 1:
        return False

    block = clean_text(blocks[0])
    if not block.startswith(requirements["block_prefix"]):
        return False
    if requirements["guide_line"] not in block:
        return False
    return all(marker in block for marker in requirements["markers"])


def build_stop_reason(role: str) -> str:
    requirements = ROLE_REQUIREMENTS[role]
    marker_lines = "\n".join(f"- {marker}" for marker in requirements["markers"])
    return (
        "Do not stop yet.\n\n"
        "The final response is missing the required copy-paste handover block.\n\n"
        "Continue with exactly one final assistant message that contains:\n"
        f"- the heading `{requirements['heading']}`\n"
        "- exactly one fenced `text` block\n"
        "- no prose before or after that heading and fenced block\n\n"
        "Inside the fenced `text` block:\n"
        f"- start with `{requirements['block_prefix']}`\n"
        f"- include `{requirements['guide_line']}`\n"
        f"{marker_lines}\n\n"
        "Make the block directly copy-pasteable and end after it."
    )


if __name__ == "__main__":
    main()

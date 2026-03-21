from __future__ import annotations

import json
import sys
from pathlib import Path

# Project modules
from copilot_orchestration.config.requirements_loader import ConfigError, SubRoleRequirementsLoader
from copilot_orchestration.contracts.interfaces import (
    ISubRoleRequirementsLoader,
    SubRoleSpec,
)
from copilot_orchestration.utils._paths import find_workspace_root, state_path_for_role

JsonObject = dict[str, object]


def main() -> None:
    role = normalize_role(sys.argv[1] if len(sys.argv) > 1 else "")
    event = read_stdin_json()
    workspace_root = find_workspace_root(Path(__file__))
    state_path = workspace_root / state_path_for_role(role)
    loader = SubRoleRequirementsLoader.from_copilot_dir(workspace_root)
    json.dump(
        evaluate_stop_hook(event, role, loader, state_path),
        sys.stdout,
        ensure_ascii=True,
    )


def evaluate_stop_hook(
    event: JsonObject,
    role: str,
    loader: ISubRoleRequirementsLoader,
    state_path: Path,
) -> JsonObject:
    if is_stop_retry_active(event):
        return {}

    sub_role = read_sub_role(state_path)
    if sub_role is None:
        # Exploration mode: no state file (or unreadable) — no enforcement
        return {}

    try:
        if not loader.requires_crosschat_block(role, sub_role):
            return {}
        spec = loader.get_requirement(role, sub_role)
    except ConfigError:
        # Unknown (role, sub_role) combination — treat as pass-through
        return {}

    return {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "decision": "block",
            "reason": build_stop_reason(spec),
        }
    }


def read_sub_role(state_path: Path) -> str | None:
    """Read sub_role from state file; return None if file is absent or unreadable."""
    try:
        state = json.loads(state_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    value = state.get("sub_role")
    return str(value) if value else None


def normalize_role(value: str) -> str:
    return value.strip().lower()


def is_stop_retry_active(event: JsonObject) -> bool:
    value = event.get("stop_hook_active")
    if isinstance(value, bool):
        return value
    return False


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


def build_stop_reason(spec: SubRoleSpec) -> str:
    marker_lines = "\n".join(f"- {marker}" for marker in spec["markers"])
    return (
        "Do not stop yet.\n\n"
        "The final response is missing the required copy-paste handover block.\n\n"
        "Continue with exactly one final assistant message that contains:\n"
        f"- the heading `{spec['heading']}`\n"
        "- exactly one fenced `text` block\n"
        "- no prose before or after that heading and fenced block\n\n"
        "Inside the fenced `text` block:\n"
        f"- start with `{spec['block_prefix']}`\n"
        f"- include `{spec['guide_line']}`\n"
        f"{marker_lines}\n\n"
        "Make the block directly copy-pasteable and end after it."
    )


if __name__ == "__main__":
    main()

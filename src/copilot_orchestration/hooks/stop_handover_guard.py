from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# Project modules
from copilot_orchestration.config.logging_config import LoggingConfig
from copilot_orchestration.config.requirements_loader import ConfigError, SubRoleRequirementsLoader
from copilot_orchestration.contracts.interfaces import (
    ISubRoleRequirementsLoader,
    SubRoleSpec,
)
from copilot_orchestration.hooks.detect_sub_role import build_crosschat_block_instruction
from copilot_orchestration.utils._paths import find_workspace_root, state_path_for_role

JsonObject = dict[str, object]

logger = logging.getLogger(__name__)


def main() -> None:  # pragma: no cover
    role = normalize_role(sys.argv[1] if len(sys.argv) > 1 else "")
    event = read_stdin_json()
    workspace_root = find_workspace_root(Path(__file__))
    LoggingConfig.from_copilot_dir(workspace_root).apply()
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
    logger.debug(
        "stop hook: event keys=%s raw=%s",
        list(event.keys()),
        json.dumps(event, ensure_ascii=True)[:500],
    )
    logger.debug("stop hook: stop_hook_active=%r", is_stop_retry_active(event))
    if is_stop_retry_active(event):
        return {}

    logger.debug("stop hook: state_path=%s exists=%s", state_path, state_path.exists())
    sub_role = read_sub_role(state_path)
    logger.debug("stop hook: sub_role=%r", sub_role)
    if sub_role is None:
        # Exploration mode: no state file (or unreadable) — no enforcement
        return {}

    try:
        if not loader.requires_crosschat_block(role, sub_role):
            logger.debug("ALLOW stop: role=%r sub_role=%r (no enforcement)", role, sub_role)
            return {}
        spec = loader.get_requirement(role, sub_role)
    except ConfigError:
        # Unknown (role, sub_role) combination — treat as pass-through
        return {}

    logger.info("BLOCK stop: role=%r sub_role=%r", role, sub_role)
    return {
        "hookSpecificOutput": {
            "hookEventName": "Stop",
            "decision": "block",
            "reason": build_stop_reason(spec, sub_role),
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
    # VS Code sends stopHookActive (camelCase) — confirmed by VS Code source docs.
    # Clean-break decision: read camelCase only (see design §3.5).
    value = event.get("stopHookActive")  # ← was: "stop_hook_active"
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
        result = json.loads(raw_input)
        if not isinstance(result, dict):
            return {}
        return result  # type: ignore[return-value]  # json boundary: dict confirmed above
    except json.JSONDecodeError:
        return {}


def build_stop_reason(spec: SubRoleSpec, sub_role: str) -> str:
    return "Write NOW.\n\n" + build_crosschat_block_instruction(sub_role, spec)


if __name__ == "__main__":  # pragma: no cover
    main()

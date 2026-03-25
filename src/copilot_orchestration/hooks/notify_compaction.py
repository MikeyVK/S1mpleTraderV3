# src\copilot_orchestration\hooks\notify_compaction.py
# template=generic version=f35abd82 created=2026-03-21T13:42Z updated=
"""NotifyCompaction module.

PreCompact hook — thin __main__-only adapter.

Reads role-scoped state file for current sub_role, writes a systemMessage so the
agent remembers its active sub-role and handover block requirement after context compaction.
Exit 0 always (soft failure — hook errors must not break agent session).

@layer: copilot_orchestration (Hooks)
@dependencies: [copilot_orchestration.hooks.detect_sub_role]
@responsibilities:
    - Read role from sys.argv[1]
    - Resolve state path via find_workspace_root + state_path_for_role(role)
    - If state file exists and contains a sub_role: output systemMessage (base + optional block)
    - If file absent or unreadable: output {}
    - Always exit 0 (soft failure — hook errors must not break agent session)
"""

# Standard library
import json
import logging
import sys
from pathlib import Path

# Project modules
from copilot_orchestration.config.logging_config import LoggingConfig
from copilot_orchestration.config.requirements_loader import SubRoleRequirementsLoader
from copilot_orchestration.contracts.interfaces import ISubRoleRequirementsLoader
from copilot_orchestration.hooks.detect_sub_role import build_crosschat_block_instruction
from copilot_orchestration.utils._paths import find_workspace_root, state_path_for_role

logger = logging.getLogger(__name__)


def build_compaction_output(
    state: dict[str, object],
    loader: ISubRoleRequirementsLoader,
    role: str,
) -> dict[str, object]:
    """Return systemMessage dict when state contains a sub_role, else empty dict.

    Injects the sub-role description and canonical crosschat block instruction when
    configured, so the agent receives the same guidance after compaction as at
    UserPromptSubmit. ConfigError from the loader propagates - caller handles it.
    """
    sub_role = state.get("sub_role")
    if not sub_role:
        logger.debug("no sub_role in state - empty compaction output")
        return {}

    sub_role_str = str(sub_role)
    base = (
        f"Context was compacted. Active sub-role: **{sub_role_str}**. "
        "Use /resume-work to restore full context."
    )
    logger.info("compaction output: sub_role=%s", sub_role_str)

    spec = loader.get_requirement(role, sub_role_str)
    description = spec["description"].strip()
    if description:
        base += "\n\n" + description
    if spec["requires_crosschat_block"]:
        base += "\n\n" + build_crosschat_block_instruction(sub_role_str, spec)
    return {"systemMessage": base}


def main() -> None:  # pragma: no cover
    role = sys.argv[1] if len(sys.argv) > 1 else "imp"
    workspace_root = find_workspace_root(Path(__file__))
    LoggingConfig.from_copilot_dir(workspace_root).apply()
    state_path = workspace_root / state_path_for_role(role)

    # Consume stdin (required by hook protocol, sessionId not used for decisions)
    json.loads(sys.stdin.read())

    state: dict[str, object] = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except json.JSONDecodeError:
            state = {}

    _loader = SubRoleRequirementsLoader.from_copilot_dir(workspace_root)
    print(json.dumps(build_compaction_output(state, _loader, role)))


if __name__ == "__main__":  # pragma: no cover
    main()

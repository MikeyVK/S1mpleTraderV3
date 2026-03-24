"""Acceptance checks for C_V2.7 configuration deliverables (issue #263).

Formal verification that the VS Code orchestration configuration is correct:
  - Prompt set: exactly 6 files present, 3 removed files absent
  - .vscode/settings.json: chat.useCustomAgentHooks enabled
  - .gitignore: STATE_RELPATH entry present
  - imp/qa .agent.md: UserPromptSubmit hook wired; notify_compaction.py
    is second in PreCompact (after pre_compact_agent.py)
  - sub-role-requirements.yaml: all imp and qa sub-roles defined

Reference: planning.md §C_V2.7 success criteria, design §9.6/9.7.
"""

import json
import re
from pathlib import Path

import yaml

_WORKSPACE_ROOT = Path(__file__).parents[3]
_PROMPTS_DIR = _WORKSPACE_ROOT / ".github" / "prompts"
_IMP_AGENT_MD = _WORKSPACE_ROOT / ".github" / "agents" / "imp.agent.md"
_QA_AGENT_MD = _WORKSPACE_ROOT / ".github" / "agents" / "qa.agent.md"
_SUB_ROLE_REQUIREMENTS = _WORKSPACE_ROOT / ".copilot" / "sub-role-requirements.yaml"
_VSCODE_SETTINGS = _WORKSPACE_ROOT / ".vscode" / "settings.json"
_GITIGNORE = _WORKSPACE_ROOT / ".gitignore"

# STATE_RELPATH was removed in C_V2.8 (superseded by state_path_for_role(role)).
# .gitignore now uses the glob pattern to cover all role-scoped state files.
_STATE_GITIGNORE_PATTERN = ".copilot/session-sub-role-*.json"

_EXPECTED_PROMPTS = frozenset(
    {
        "start-work.prompt.md",
        "resume-work.prompt.md",
        "prepare-handover.prompt.md",
        "request-review.prompt.md",
        "prepare-implementation-brief.prompt.md",
        "prepare-qa-brief.prompt.md",
    }
)
_REMOVED_PROMPTS = frozenset(
    {
        "start-implementation.prompt.md",
        "resume-implementation.prompt.md",
        "plan-executionDirectiveBatchCoordination.prompt.md",
    }
)

_IMP_SUB_ROLES = frozenset(
    {"researcher", "planner", "designer", "implementer", "validator", "documenter"}
)
_QA_SUB_ROLES = frozenset(
    {"plan-verifier", "design-reviewer", "verifier", "validation-reviewer", "doc-reviewer"}
)


def _parse_agent_frontmatter(path: Path) -> dict:  # type: ignore[type-arg]
    """Extract and parse YAML frontmatter from a .agent.md file."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^---\n(.*?)^---\n", text, re.MULTILINE | re.DOTALL)
    if match is None:
        return {}
    return yaml.safe_load(match.group(1)) or {}  # type: ignore[return-value]


class TestCV27Acceptance:
    def test_prompt_directory_contains_exactly_six_files(self) -> None:
        """Prompts directory contains exactly the 6 expected prompt files (no more, no less)."""
        actual = frozenset(f.name for f in _PROMPTS_DIR.iterdir() if f.is_file())
        assert actual == _EXPECTED_PROMPTS, (
            f"Expected prompt files: {sorted(_EXPECTED_PROMPTS)}\n"
            f"Actual:                {sorted(actual)}\n"
            f"Extra:  {sorted(actual - _EXPECTED_PROMPTS)}\n"
            f"Missing: {sorted(_EXPECTED_PROMPTS - actual)}"
        )

    def test_removed_prompts_are_absent(self) -> None:
        """start-implementation, resume-implementation, and plan-execution prompts are absent."""
        for name in sorted(_REMOVED_PROMPTS):
            assert not (_PROMPTS_DIR / name).exists(), f"Removed prompt still present: {name}"

    def test_vscode_settings_contains_agent_hooks_enabled(self) -> None:
        """.vscode/settings.json has chat.useCustomAgentHooks set to true."""
        settings = json.loads(_VSCODE_SETTINGS.read_text(encoding="utf-8"))
        assert settings.get("chat.useCustomAgentHooks") is True, (
            "Expected 'chat.useCustomAgentHooks': true in .vscode/settings.json"
        )

    def test_gitignore_contains_role_scoped_state_pattern(self) -> None:
        """.gitignore contains the glob pattern for role-scoped state files (C_V2.8+)."""
        content = _GITIGNORE.read_text(encoding="utf-8")
        assert _STATE_GITIGNORE_PATTERN in content, (
            f"Expected '{_STATE_GITIGNORE_PATTERN}' in .gitignore"
        )

    def test_imp_agent_has_userpromptsubmit_hook(self) -> None:
        """imp.agent.md declares at least one UserPromptSubmit hook entry."""
        frontmatter = _parse_agent_frontmatter(_IMP_AGENT_MD)
        hooks = frontmatter.get("hooks", {})
        user_prompt_submit = hooks.get("UserPromptSubmit", [])
        assert len(user_prompt_submit) > 0, (
            "imp.agent.md: UserPromptSubmit hook is missing from frontmatter"
        )

    def test_notify_compaction_is_second_in_imp_precompact(self) -> None:
        """PreCompact[0]=copilot-pre-compact-agent, [1]=copilot-notify-compaction (imp)."""
        frontmatter = _parse_agent_frontmatter(_IMP_AGENT_MD)
        pre_compact = frontmatter.get("hooks", {}).get("PreCompact", [])
        assert len(pre_compact) >= 2, "imp.agent.md: PreCompact must have at least 2 entries"
        first_cmd = pre_compact[0].get("command", "")
        second_cmd = pre_compact[1].get("command", "")
        assert "copilot-pre-compact-agent" in first_cmd, (
            f"imp.agent.md: PreCompact[0] must be copilot-pre-compact-agent, got: {first_cmd!r}"
        )
        assert "copilot-notify-compaction" in second_cmd, (
            f"imp.agent.md: PreCompact[1] must be copilot-notify-compaction, got: {second_cmd!r}"
        )

    def test_notify_compaction_is_second_in_qa_precompact(self) -> None:
        """PreCompact[0]=copilot-pre-compact-agent, [1]=copilot-notify-compaction (qa)."""
        frontmatter = _parse_agent_frontmatter(_QA_AGENT_MD)
        pre_compact = frontmatter.get("hooks", {}).get("PreCompact", [])
        assert len(pre_compact) >= 2, "qa.agent.md: PreCompact must have at least 2 entries"
        first_cmd = pre_compact[0].get("command", "")
        second_cmd = pre_compact[1].get("command", "")
        assert "copilot-pre-compact-agent" in first_cmd, (
            f"qa.agent.md: PreCompact[0] must be copilot-pre-compact-agent, got: {first_cmd!r}"
        )
        assert "copilot-notify-compaction" in second_cmd, (
            f"qa.agent.md: PreCompact[1] must be copilot-notify-compaction, got: {second_cmd!r}"
        )

    def test_imp_sub_roles_are_defined_in_yaml(self) -> None:
        """sub-role-requirements.yaml defines exactly the expected imp sub-roles."""
        requirements = yaml.safe_load(_SUB_ROLE_REQUIREMENTS.read_text(encoding="utf-8"))
        actual = frozenset(requirements["roles"]["imp"]["sub_roles"].keys())
        assert actual == _IMP_SUB_ROLES, (
            f"sub-role-requirements.yaml imp sub-roles mismatch.\n"
            f"Expected: {sorted(_IMP_SUB_ROLES)}\n"
            f"Actual:   {sorted(actual)}"
        )

    def test_qa_sub_roles_are_defined_in_yaml(self) -> None:
        """sub-role-requirements.yaml defines exactly the expected qa sub-roles."""
        requirements = yaml.safe_load(_SUB_ROLE_REQUIREMENTS.read_text(encoding="utf-8"))
        actual = frozenset(requirements["roles"]["qa"]["sub_roles"].keys())
        assert actual == _QA_SUB_ROLES, (
            f"sub-role-requirements.yaml qa sub-roles mismatch.\n"
            f"Expected: {sorted(_QA_SUB_ROLES)}\n"
            f"Actual:   {sorted(actual)}"
        )

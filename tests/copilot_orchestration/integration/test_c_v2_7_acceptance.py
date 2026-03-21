"""Acceptance checks for C_V2.7 configuration deliverables (issue #263).

Formal verification that the VS Code orchestration configuration is correct:
  - Prompt set: exactly 6 files present, 3 removed files absent
  - .vscode/settings.json: chat.useCustomAgentHooks enabled
  - .gitignore: STATE_RELPATH entry present
  - imp/qa .agent.md: UserPromptSubmit hook wired; notify_compaction.py
    is second in PreCompact (after pre_compact_agent.py)
  - imp_agent.md: sub-role table contains all 6 imp sub-roles
  - qa_agent.md: sub-role table contains all 5 qa sub-roles

Reference: planning.md §C_V2.7 success criteria, design §9.6/9.7.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

_WORKSPACE_ROOT = Path(__file__).parents[3]
_PROMPTS_DIR = _WORKSPACE_ROOT / ".github" / "prompts"
_IMP_AGENT_MD = _WORKSPACE_ROOT / ".github" / "agents" / "imp.agent.md"
_QA_AGENT_MD = _WORKSPACE_ROOT / ".github" / "agents" / "qa.agent.md"
_IMP_ROLE_GUIDE = _WORKSPACE_ROOT / "imp_agent.md"
_QA_ROLE_GUIDE = _WORKSPACE_ROOT / "qa_agent.md"
_VSCODE_SETTINGS = _WORKSPACE_ROOT / ".vscode" / "settings.json"
_GITIGNORE = _WORKSPACE_ROOT / ".gitignore"

# STATE_RELPATH must match utils/_paths.py: Path(".copilot/session-sub-role.json")
_STATE_RELPATH_STR = ".copilot/session-sub-role.json"

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
    {"plan-reviewer", "design-reviewer", "verifier", "validation-reviewer", "doc-reviewer"}
)


def _parse_agent_frontmatter(path: Path) -> dict:  # type: ignore[type-arg]
    """Extract and parse YAML frontmatter from a .agent.md file."""
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^---\n(.*?)^---\n", text, re.MULTILINE | re.DOTALL)
    if match is None:
        return {}
    return yaml.safe_load(match.group(1)) or {}  # type: ignore[return-value]


class TestC_V27Acceptance:
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

    def test_gitignore_contains_state_relpath(self) -> None:
        """.gitignore contains the exact STATE_RELPATH (.copilot/session-sub-role.json)."""
        content = _GITIGNORE.read_text(encoding="utf-8")
        assert _STATE_RELPATH_STR in content, (
            f"Expected '{_STATE_RELPATH_STR}' in .gitignore"
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
        """imp.agent.md: pre_compact_agent.py is first and notify_compaction.py is second in PreCompact."""
        frontmatter = _parse_agent_frontmatter(_IMP_AGENT_MD)
        pre_compact = frontmatter.get("hooks", {}).get("PreCompact", [])
        assert len(pre_compact) >= 2, (
            "imp.agent.md: PreCompact must have at least 2 entries"
        )
        first_cmd = pre_compact[0].get("command", "")
        second_cmd = pre_compact[1].get("command", "")
        assert "pre_compact_agent.py" in first_cmd, (
            f"imp.agent.md: PreCompact[0] must be pre_compact_agent.py, got: {first_cmd!r}"
        )
        assert "notify_compaction.py" in second_cmd, (
            f"imp.agent.md: PreCompact[1] must be notify_compaction.py, got: {second_cmd!r}"
        )

    def test_notify_compaction_is_second_in_qa_precompact(self) -> None:
        """qa.agent.md: pre_compact_agent.py is first and notify_compaction.py is second in PreCompact."""
        frontmatter = _parse_agent_frontmatter(_QA_AGENT_MD)
        pre_compact = frontmatter.get("hooks", {}).get("PreCompact", [])
        assert len(pre_compact) >= 2, (
            "qa.agent.md: PreCompact must have at least 2 entries"
        )
        first_cmd = pre_compact[0].get("command", "")
        second_cmd = pre_compact[1].get("command", "")
        assert "pre_compact_agent.py" in first_cmd, (
            f"qa.agent.md: PreCompact[0] must be pre_compact_agent.py, got: {first_cmd!r}"
        )
        assert "notify_compaction.py" in second_cmd, (
            f"qa.agent.md: PreCompact[1] must be notify_compaction.py, got: {second_cmd!r}"
        )

    def test_imp_agent_md_has_all_six_imp_sub_roles(self) -> None:
        """imp_agent.md sub-role table contains all 6 imp sub-roles."""
        content = _IMP_ROLE_GUIDE.read_text(encoding="utf-8")
        for sub_role in sorted(_IMP_SUB_ROLES):
            assert sub_role in content, (
                f"imp_agent.md: sub-role '{sub_role}' not found in sub-role table"
            )

    def test_qa_agent_md_has_all_five_qa_sub_roles(self) -> None:
        """qa_agent.md sub-role table contains all 5 qa sub-roles."""
        content = _QA_ROLE_GUIDE.read_text(encoding="utf-8")
        for sub_role in sorted(_QA_SUB_ROLES):
            assert sub_role in content, (
                f"qa_agent.md: sub-role '{sub_role}' not found in sub-role table"
            )

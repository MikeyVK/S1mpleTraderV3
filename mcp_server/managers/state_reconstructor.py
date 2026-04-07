# mcp_server/managers/state_reconstructor.py
"""Branch state reconstruction from git metadata and project context.

@layer: Platform
@dependencies: [ScopeDecoder, ProjectManager, BranchState]
@responsibilities:
    - Reconstruct missing branch state from project metadata
    - Infer the active workflow phase from git commit scopes
    - Fall back safely when no valid phase can be detected
    - Produce reconstructed BranchState payloads for transition flows
"""

from __future__ import annotations

# Standard library
import logging
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

# Project modules
from mcp_server.core.phase_detection import ScopeDecoder
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.managers.state_repository import BranchState
from mcp_server.schemas import GitConfig

logger = logging.getLogger(__name__)


class StateReconstructor:
    """Reconstruct missing or invalid branch state from git and project metadata."""

    def __init__(
        self,
        workspace_root: Path | str,
        git_config: GitConfig,
        project_manager: ProjectManager,
        scope_decoder: ScopeDecoder,
    ) -> None:
        self._workspace_root = Path(workspace_root)
        self._git_config = git_config
        self._project_manager = project_manager
        self._scope_decoder = scope_decoder

    def reconstruct(self, branch: str) -> BranchState:
        """Reconstruct branch state from deliverables.json plus git commit scopes."""
        logger.info("Reconstructing state for branch '%s'...", branch)

        issue_number = self._git_config.extract_issue_number(branch)
        if issue_number is None:
            msg = (
                f"Cannot extract issue number from branch '{branch}'. "
                "Expected format: <type>/<number>-<title>"
            )
            raise ValueError(msg)

        project = self._project_manager.get_project_plan(issue_number)
        if not project:
            msg = f"Project plan not found for issue {issue_number}"
            raise ValueError(msg)

        workflow_phases = project["required_phases"]
        current_phase = self._infer_phase_from_git(branch, workflow_phases)
        parent_branch = project.get("parent_branch")

        state = BranchState(
            branch=branch,
            issue_number=issue_number,
            workflow_name=project["workflow_name"],
            current_phase=current_phase,
            current_cycle=None,
            last_cycle=None,
            cycle_history=[],
            required_phases=project.get("required_phases", workflow_phases),
            execution_mode=project.get("execution_mode", "normal"),
            issue_title=project.get("issue_title"),
            parent_branch=parent_branch,
            created_at=datetime.now(UTC).isoformat(),
            transitions=[],
            reconstructed=True,
        )

        logger.info(
            "Reconstructed state: issue=%s, phase=%s, workflow=%s, parent=%s",
            issue_number,
            current_phase,
            project["workflow_name"],
            parent_branch,
        )
        return state

    def _infer_phase_from_git(self, branch: str, workflow_phases: list[str]) -> str:
        """Infer current phase from commit scopes, with workflow-first fallback."""
        try:
            commits = self._get_git_commits(branch)
            for commit in commits:
                result = self._scope_decoder.detect_phase(commit, fallback_to_state=False)
                phase = result["workflow_phase"]
                if phase != "unknown" and phase in workflow_phases:
                    logger.info("Detected phase '%s' from git commits", phase)
                    return phase
        except RuntimeError as exc:
            logger.warning("Git command failed during phase detection: %s", exc)

        fallback_phase = workflow_phases[0]
        logger.info("No valid phase detected, using fallback: %s", fallback_phase)
        return fallback_phase

    def _get_git_commits(self, branch: str, limit: int = 50) -> list[str]:
        """Return recent commit subjects for one branch."""
        try:
            env = os.environ.copy()
            env.setdefault("GIT_TERMINAL_PROMPT", "0")
            env.setdefault("GIT_PAGER", "cat")
            env.setdefault("PAGER", "cat")

            result = subprocess.run(
                ["git", "log", f"--max-count={limit}", "--pretty=%s", branch],
                cwd=self._workspace_root,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=True,
                timeout=2,
                env=env,
            )
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
        except subprocess.CalledProcessError as exc:
            msg = f"Git log failed: {exc.stderr}"
            raise RuntimeError(msg) from exc
        except subprocess.TimeoutExpired as exc:
            msg = "Git log command timed out"
            raise RuntimeError(msg) from exc

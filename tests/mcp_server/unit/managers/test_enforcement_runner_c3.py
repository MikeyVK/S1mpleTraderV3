# tests/mcp_server/unit/managers/test_enforcement_runner_c3.py
# template=unit_test version=3d15d309 created=2026-04-09T19:17Z updated=
"""
Unit tests for mcp_server.managers.enforcement_runner.

Tests for C3 action handlers: exclude_branch_local_artifacts and check_merge_readiness

@layer: Tests (Unit)
@dependencies: [pathlib, pytest, mcp_server.managers.enforcement_runner, mcp_server.managers.phase_contract_resolver]
@responsibilities:
    - Test TestEnforcementRunnerC3 functionality
    - Verify new C3 enforcement handlers
    - Verify enforcement rules block invalid commits and PRs
"""

# Standard library
from pathlib import Path
from types import SimpleNamespace

# Third-party
import pytest

# Project modules
from mcp_server.core.exceptions import ValidationError
from mcp_server.managers.enforcement_runner import (
    EnforcementAction,
    EnforcementConfig,
    EnforcementContext,
    EnforcementRule,
    EnforcementRunner,
)
from mcp_server.managers.phase_contract_resolver import MergeReadinessContext


def _make_runner_with_merge_ctx(
    tmp_path: Path,
    merge_readiness_ctx: MergeReadinessContext,
) -> EnforcementRunner:
    return EnforcementRunner(
        workspace_root=tmp_path,
        config=EnforcementConfig(enforcement=[]),
        merge_readiness_ctx=merge_readiness_ctx,
    )


def _merge_ctx(current: str = "implementation", allowed: str = "ready") -> MergeReadinessContext:
    return MergeReadinessContext(current_phase=current, pr_allowed_phase=allowed)


class TestEnforcementRunnerC3:
    """Test suite for C3 enforcement handlers in EnforcementRunner."""

    def test_exclude_branch_local_artifacts_blocks_st3_path(
        self,
        tmp_path: Path,
    ) -> None:
        """exclude_branch_local_artifacts raises ValidationError when staged files include .st3/ paths."""
        # Arrange
        runner = _make_runner_with_merge_ctx(tmp_path, _merge_ctx())
        action = EnforcementAction(type="exclude_branch_local_artifacts")
        context = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="git_add_or_commit",
            params=SimpleNamespace(files=[".st3/state.json", "mcp_server/foo.py"]),
        )

        # Act / Assert
        with pytest.raises(ValidationError):
            runner._handle_exclude_branch_local_artifacts(  # pyright: ignore[reportPrivateUsage]
                action, context, tmp_path
            )

    def test_exclude_branch_local_artifacts_allows_non_st3_paths(
        self,
        tmp_path: Path,
    ) -> None:
        """exclude_branch_local_artifacts returns None for normal source files."""
        # Arrange
        runner = _make_runner_with_merge_ctx(tmp_path, _merge_ctx())
        action = EnforcementAction(type="exclude_branch_local_artifacts")
        context = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="git_add_or_commit",
            params=SimpleNamespace(files=["mcp_server/config/loader.py", "tests/conftest.py"]),
        )

        # Act
        result = runner._handle_exclude_branch_local_artifacts(  # pyright: ignore[reportPrivateUsage]
            action, context, tmp_path
        )

        # Assert
        assert result is None

    def test_check_merge_readiness_raises_when_wrong_phase(
        self,
        tmp_path: Path,
    ) -> None:
        """check_merge_readiness raises ValidationError when current_phase != pr_allowed_phase."""
        # Arrange
        runner = _make_runner_with_merge_ctx(
            tmp_path, _merge_ctx(current="implementation", allowed="ready")
        )
        action = EnforcementAction(type="check_merge_readiness")
        context = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="create_pr",
            params=SimpleNamespace(),
        )

        # Act / Assert
        with pytest.raises(ValidationError):
            runner._handle_check_merge_readiness(  # pyright: ignore[reportPrivateUsage]
                action, context, tmp_path
            )

    def test_check_merge_readiness_ok_when_correct_phase(
        self,
        tmp_path: Path,
    ) -> None:
        """check_merge_readiness returns None when current_phase == pr_allowed_phase."""
        # Arrange
        runner = _make_runner_with_merge_ctx(
            tmp_path, _merge_ctx(current="ready", allowed="ready")
        )
        action = EnforcementAction(type="check_merge_readiness")
        context = EnforcementContext(
            workspace_root=tmp_path,
            tool_name="create_pr",
            params=SimpleNamespace(),
        )

        # Act
        result = runner._handle_check_merge_readiness(  # pyright: ignore[reportPrivateUsage]
            action, context, tmp_path
        )

        # Assert
        assert result is None

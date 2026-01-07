"""Tests for InitializeProjectTool with parent_branch tracking.

Issue #79: Tests for parent_branch in InitializeProjectTool.
- Accepts explicit parent_branch parameter
- Auto-detects parent_branch from git reflog (best effort)
- Handles auto-detection failure gracefully
"""
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.tools.project_tools import InitializeProjectInput, InitializeProjectTool


class TestInitializeProjectToolParentBranch:
    """Test parent_branch functionality in InitializeProjectTool."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace.

        Args:
            tmp_path: Pytest tmp_path fixture

        Returns:
            Path to temporary workspace root
        """
        return tmp_path

    @pytest.fixture
    def tool(self, workspace_root: Path) -> InitializeProjectTool:
        """Create InitializeProjectTool instance.

        Args:
            workspace_root: Path to workspace root

        Returns:
            InitializeProjectTool instance
        """
        return InitializeProjectTool(workspace_root=workspace_root)

    @pytest.mark.asyncio
    async def test_initialize_with_explicit_parent_branch(
        self, tool: InitializeProjectTool
    ) -> None:
        """Test initializing project with explicit parent_branch.

        Issue #79: User can provide parent_branch explicitly.
        """
        # Mock git to return current branch
        with patch.object(tool.git_manager, "get_current_branch") as mock_branch:
            mock_branch.return_value = "feature/79-test"

            # Execute
            result = await tool.execute(
                InitializeProjectInput(
                    issue_number=79,
                    issue_title="Test",
                    workflow_name="feature",
                    parent_branch="epic/76-quality-gates"
                )
            )

        # Verify
        assert result.is_error is False
        content_text = result.content[0]["text"]
        assert "epic/76-quality-gates" in content_text
        assert '"parent_branch": "epic/76-quality-gates"' in content_text

    @pytest.mark.asyncio
    async def test_initialize_auto_detects_parent_branch(
        self, tool: InitializeProjectTool
    ) -> None:
        """Test auto-detection of parent_branch via git reflog.

        Issue #79: If parent_branch not provided, auto-detect from git reflog.
        """
        # Mock git operations
        with patch.object(tool.git_manager, "get_current_branch") as mock_branch, \
             patch.object(tool, "_detect_parent_branch_from_reflog") as mock_detect:
            mock_branch.return_value = "feature/80-test"
            mock_detect.return_value = "main"  # Auto-detected

            # Execute - no parent_branch parameter
            result = await tool.execute(
                InitializeProjectInput(
                    issue_number=80,
                    issue_title="Test Auto-detect",
                    workflow_name="bug"
                )
            )

        # Verify
        assert result.is_error is False
        content_text = result.content[0]["text"]
        assert '"parent_branch": "main"' in content_text
        mock_detect.assert_called_once_with("feature/80-test")

    @pytest.mark.asyncio
    async def test_initialize_auto_detect_fails_gracefully(
        self, tool: InitializeProjectTool
    ) -> None:
        """Test auto-detection failure results in None.

        Issue #79: If git reflog fails, parent_branch should be None.
        """
        # Mock git operations
        with patch.object(tool.git_manager, "get_current_branch") as mock_branch, \
             patch.object(tool, "_detect_parent_branch_from_reflog") as mock_detect:
            mock_branch.return_value = "feature/81-test"
            mock_detect.return_value = None  # Detection failed

            # Execute
            result = await tool.execute(
                InitializeProjectInput(
                    issue_number=81,
                    issue_title="Test Failed Detect",
                    workflow_name="docs"
                )
            )

        # Verify - no error, parent_branch is null
        assert result.is_error is False
        content_text = result.content[0]["text"]
        assert '"parent_branch": null' in content_text
        mock_detect.assert_called_once_with("feature/81-test")

    @pytest.mark.asyncio
    async def test_explicit_parent_branch_overrides_auto_detect(
        self, tool: InitializeProjectTool
    ) -> None:
        """Test explicit parent_branch skips auto-detection.

        Issue #79: If parent_branch provided, don't call git reflog.
        """
        # Mock git operations
        with patch.object(tool.git_manager, "get_current_branch") as mock_branch, \
             patch.object(tool, "_detect_parent_branch_from_reflog") as mock_detect:
            mock_branch.return_value = "feature/82-test"

            # Execute with explicit parent_branch
            result = await tool.execute(
                InitializeProjectInput(
                    issue_number=82,
                    issue_title="Test Override",
                    workflow_name="feature",
                    parent_branch="epic/special"
                )
            )

        # Verify - auto-detect NOT called
        assert result.is_error is False
        content_text = result.content[0]["text"]
        assert '"parent_branch": "epic/special"' in content_text
        mock_detect.assert_not_called()

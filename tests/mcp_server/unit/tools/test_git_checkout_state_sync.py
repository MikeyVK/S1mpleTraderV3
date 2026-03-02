"""Tests for GitCheckoutTool state synchronization with PhaseStateEngine."""

from unittest.mock import Mock, patch

import pytest

from mcp_server.tools.git_tools import GitCheckoutTool
from mcp_server.tools.tool_result import ToolResult


class TestGitCheckoutStateSync:
    """Test suite for git_checkout tool PhaseStateEngine state synchronization."""

    @pytest.mark.asyncio
    async def test_checkout_syncs_state_and_returns_phase(self) -> None:
        """Test that git_checkout syncs state and returns current phase info."""
        # Setup
        mock_manager = Mock()
        tool = GitCheckoutTool(manager=mock_manager)

        params = Mock()
        params.branch = "feature/123-test"

        mock_engine = Mock()
        mock_engine.get_state.return_value = {
            "current_phase": "tdd",
            "phase_history": ["research", "planning", "design", "tdd"],
        }

        # Patch imports that happen inside execute()
        with (
            patch(
                "mcp_server.tools.git_tools.phase_state_engine.PhaseStateEngine",
                return_value=mock_engine,
            ),
            patch("mcp_server.tools.git_tools.project_manager.ProjectManager"),
            patch("pathlib.Path.cwd", return_value=Mock()),
        ):
            # Execute
            result = await tool.execute(params)

            # Verify
            mock_manager.checkout.assert_called_once_with("feature/123-test")
            mock_engine.get_state.assert_called_once_with("feature/123-test")

            assert isinstance(result, ToolResult)
            assert result.is_error is False
            assert "feature/123-test" in str(result)
            assert "tdd" in str(result)

    @pytest.mark.asyncio
    async def test_checkout_handles_state_sync_failure_gracefully(self) -> None:
        """Test that git_checkout handles state sync failures gracefully."""
        # Setup
        mock_manager = Mock()
        tool = GitCheckoutTool(manager=mock_manager)

        params = Mock()
        params.branch = "feature/456-test"

        mock_engine = Mock()
        mock_engine.get_state.side_effect = ValueError("State sync failed")

        # Patch imports
        with (
            patch(
                "mcp_server.tools.git_tools.phase_state_engine.PhaseStateEngine",
                return_value=mock_engine,
            ),
            patch("mcp_server.tools.git_tools.project_manager.ProjectManager"),
            patch("pathlib.Path.cwd", return_value=Mock()),
        ):
            # Execute
            result = await tool.execute(params)

            # Verify - should still succeed even if state sync fails
            mock_manager.checkout.assert_called_once_with("feature/456-test")
            assert isinstance(result, ToolResult)
            assert result.is_error is False
            assert "feature/456-test" in str(result)

    @pytest.mark.asyncio
    async def test_checkout_handles_unknown_phase(self) -> None:
        """Test that git_checkout handles unknown/missing phase gracefully."""
        # Setup
        mock_manager = Mock()
        tool = GitCheckoutTool(manager=mock_manager)

        params = Mock()
        params.branch = "main"

        mock_engine = Mock()
        mock_engine.get_state.return_value = {}  # No current_phase key

        # Patch imports
        with (
            patch(
                "mcp_server.tools.git_tools.phase_state_engine.PhaseStateEngine",
                return_value=mock_engine,
            ),
            patch("mcp_server.tools.git_tools.project_manager.ProjectManager"),
            patch("pathlib.Path.cwd", return_value=Mock()),
        ):
            # Execute
            result = await tool.execute(params)

            # Verify
            mock_manager.checkout.assert_called_once_with("main")
            mock_engine.get_state.assert_called_once_with("main")

            assert isinstance(result, ToolResult)
            assert result.is_error is False
            assert "main" in str(result)
            assert "unknown" in str(result)

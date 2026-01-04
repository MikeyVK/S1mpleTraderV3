"""Tests for GitCheckoutTool async execution."""
import asyncio
from unittest.mock import Mock, patch, MagicMock

import pytest

from mcp_server.tools.git_tools import GitCheckoutTool
from mcp_server.tools.base import ToolResult


class TestGitCheckoutAsync:
    """Test suite for git_checkout tool async execution."""

    @pytest.mark.asyncio
    async def test_checkout_uses_asyncio_to_thread(self):
        """Test that git_checkout uses asyncio.to_thread for blocking operations."""
        # Setup
        mock_manager = Mock()
        tool = GitCheckoutTool(manager=mock_manager)

        params = Mock()
        params.branch = "feature/123-test"

        mock_engine = Mock()
        mock_engine.get_state.return_value = {
            'current_phase': 'tdd',
            'phase_history': ['research', 'planning', 'design', 'tdd']
        }

        # Patch asyncio.to_thread to verify it's called
        with patch('asyncio.to_thread', side_effect=asyncio.to_thread) as mock_to_thread, \
             patch('mcp_server.managers.phase_state_engine.PhaseStateEngine', return_value=mock_engine), \
             patch('mcp_server.managers.project_manager.ProjectManager'), \
             patch('pathlib.Path.cwd', return_value=Mock()):

            # Execute
            result = await tool.execute(params)

            # Verify
            # We expect at least 2 calls to to_thread:
            # 1. manager.checkout
            # 2. sync_state (the inner function)
            assert mock_to_thread.call_count >= 2
            
            # Verify checkout was called
            mock_manager.checkout.assert_called_once_with("feature/123-test")
            
            # Verify result
            assert isinstance(result, ToolResult)
            assert result.is_error is False
            assert "feature/123-test" in str(result)
            assert "tdd" in str(result)

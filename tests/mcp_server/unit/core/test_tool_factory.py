# tests/mcp_server/unit/core/test_tool_factory.py
# template=unit_test version=3d15d309 created=2026-06-19T22:38Z updated=
"""Unit tests for mcp_server.core.tool_factory.

Unit tests for ToolFactory composition root.

@layer: Tests (Unit)
@dependencies: [mcp_server.core.tool_factory, unittest.mock]
@responsibilities:
    - Test TestToolFactory functionality
"""

# Standard library
from pathlib import Path
from unittest.mock import MagicMock

# Third-party
# Project modules
from mcp_server.core.decorators.enforcement_decorator import EnforcementDecorator
from mcp_server.core.decorators.input_validation_decorator import InputValidationDecorator
from mcp_server.core.decorators.tool_error_handler_decorator import ToolErrorHandlerDecorator
from mcp_server.core.interfaces.icore_tool import ICoreTool
from mcp_server.core.tool_factory import ToolFactory
from mcp_server.managers.enforcement_runner import EnforcementRunner


class TestToolFactory:
    """Test suite for tool_factory."""

    def test_create_tool_decorates_correctly(self) -> None:
        """Verify that create_tool wraps core tool in correct decorator stack."""
        mock_runner = MagicMock(spec=EnforcementRunner)
        mock_root = Path("mock/workspace/root")
        factory = ToolFactory(enforcement_runner=mock_runner, workspace_root=mock_root)

        mock_core_tool = MagicMock(spec=ICoreTool)
        mock_core_tool.name = "mock_tool"
        mock_core_tool.description = "mock description"
        mock_core_tool.args_model = None

        decorated = factory.create_tool(mock_core_tool)

        # 1. Outer decorator: ToolErrorHandlerDecorator
        assert isinstance(decorated, ToolErrorHandlerDecorator)

        # Private attribute access (_inner_tool, _enforcement_runner, _workspace_root) is
        # required in this unit test to verify the structural ordering and configuration
        # of the nested decorator pipeline stack.

        # 2. Middle decorator: InputValidationDecorator
        middle = decorated._inner_tool  # pyright: ignore[reportPrivateUsage]
        assert isinstance(middle, InputValidationDecorator)

        # 3. Inner decorator: EnforcementDecorator
        inner = middle._inner_tool  # pyright: ignore[reportPrivateUsage]
        assert isinstance(inner, EnforcementDecorator)
        assert inner._enforcement_runner == mock_runner  # pyright: ignore[reportPrivateUsage]
        assert inner._workspace_root == mock_root  # pyright: ignore[reportPrivateUsage]

        # 4. Target tool
        assert inner._inner_tool == mock_core_tool  # pyright: ignore[reportPrivateUsage]

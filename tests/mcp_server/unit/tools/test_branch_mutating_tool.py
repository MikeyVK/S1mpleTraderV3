# tests/mcp_server/unit/tools/test_branch_mutating_tool.py
"""Unit tests for BranchMutatingTool ABC.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.tools.base]
"""

from __future__ import annotations

import inspect
from abc import ABC

from mcp_server.tools.base import BaseTool, BranchMutatingTool


class TestBranchMutatingTool:
    """BranchMutatingTool is a zero-method ABC that lives in base.py."""

    def test_class_exists_in_base(self) -> None:
        assert BranchMutatingTool is not None

    def test_inherits_from_base_tool(self) -> None:
        assert issubclass(BranchMutatingTool, BaseTool)

    def test_is_abstract(self) -> None:
        assert issubclass(BranchMutatingTool, ABC)

    def test_tool_category_is_branch_mutating(self) -> None:
        assert BranchMutatingTool.tool_category == "branch_mutating"

    def test_no_new_abstract_methods_beyond_base(self) -> None:
        """BranchMutatingTool must not add new abstract methods — only BaseTool.execute."""
        base_abstracts = {
            name
            for name, _ in inspect.getmembers(BaseTool)
            if getattr(getattr(BaseTool, name, None), "__isabstractmethod__", False)
        }
        branch_abstracts = {
            name
            for name, _ in inspect.getmembers(BranchMutatingTool)
            if getattr(getattr(BranchMutatingTool, name, None), "__isabstractmethod__", False)
        }
        assert branch_abstracts == base_abstracts

    def test_base_tool_tool_category_defaults_to_none(self) -> None:
        """BaseTool.tool_category is None by default; BranchMutatingTool overrides it."""
        assert BaseTool.tool_category is None

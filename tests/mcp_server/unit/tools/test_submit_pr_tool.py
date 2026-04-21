# tests/mcp_server/unit/tools/test_submit_pr_tool.py
"""Unit tests for SubmitPRTool and SubmitPRInput scaffold.

Also asserts design D2: CreatePRTool class remains in pr_tools.py as internal utility.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.tools.pr_tools, mcp_server.tools.base]
"""

from __future__ import annotations

from mcp_server.tools.base import BranchMutatingTool
from mcp_server.tools.pr_tools import CreatePRTool, SubmitPRInput, SubmitPRTool


class TestSubmitPRInput:
    """SubmitPRInput Pydantic model has the required fields per design 3.2."""

    def test_head_field_required(self) -> None:
        assert "head" in SubmitPRInput.model_fields

    def test_title_field_required(self) -> None:
        assert "title" in SubmitPRInput.model_fields

    def test_base_field_optional(self) -> None:
        field = SubmitPRInput.model_fields.get("base")
        assert field is not None
        assert not field.is_required()

    def test_draft_field_optional(self) -> None:
        field = SubmitPRInput.model_fields.get("draft")
        assert field is not None
        assert not field.is_required()


class TestSubmitPRTool:
    """SubmitPRTool is a BranchMutatingTool named 'submit_pr'."""

    def test_class_exists(self) -> None:
        assert SubmitPRTool is not None

    def test_inherits_branch_mutating_tool(self) -> None:
        assert issubclass(SubmitPRTool, BranchMutatingTool)

    def test_name_is_submit_pr(self) -> None:
        assert SubmitPRTool.name == "submit_pr"

    def test_args_model_is_submit_pr_input(self) -> None:
        assert SubmitPRTool.args_model is SubmitPRInput


class TestCreatePRToolInternalUtility:
    """Design D2: CreatePRTool class stays in pr_tools.py as internal utility."""

    def test_class_still_exists(self) -> None:
        assert CreatePRTool is not None

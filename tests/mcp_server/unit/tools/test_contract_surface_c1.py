"""C1 RED — Contract Surface.

Tests for C1 deliverables:
  C1.1  BranchMutatingTool ABC in mcp_server/tools/base.py
  C1.2  EnforcementRule.tool_category in enforcement_config.py
  C1.3  IPRStatusReader / IPRStatusWriter / PRStatus in core/interfaces/__init__.py
  C1.4  SubmitPRTool scaffold in mcp_server/tools/pr_tools.py
  C1.5  PRStatusCache in mcp_server/state/pr_status_cache.py

All tests in this file must FAIL before the production code is written (RED).

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, mcp_server.tools.base, mcp_server.config.schemas.enforcement_config,
               mcp_server.core.interfaces, mcp_server.tools.pr_tools, mcp_server.state.pr_status_cache]
"""

from __future__ import annotations

import inspect
from abc import ABC

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# C1.1  BranchMutatingTool ABC
# ---------------------------------------------------------------------------


class TestBranchMutatingTool:
    """C1.1 — BranchMutatingTool is a zero-method ABC in base.py."""

    def test_class_exists_in_base(self) -> None:
        from mcp_server.tools.base import BranchMutatingTool  # noqa: PLC0415

        assert BranchMutatingTool is not None

    def test_inherits_from_base_tool(self) -> None:
        from mcp_server.tools.base import BaseTool, BranchMutatingTool  # noqa: PLC0415

        assert issubclass(BranchMutatingTool, BaseTool)

    def test_is_abstract(self) -> None:
        from mcp_server.tools.base import BranchMutatingTool  # noqa: PLC0415

        assert issubclass(BranchMutatingTool, ABC)

    def test_tool_category_is_branch_mutating(self) -> None:
        from mcp_server.tools.base import BranchMutatingTool  # noqa: PLC0415

        assert BranchMutatingTool.tool_category == "branch_mutating"

    def test_zero_abstract_methods_beyond_base(self) -> None:
        """BranchMutatingTool must not add new abstract methods (only BaseTool.execute)."""
        from mcp_server.tools.base import BaseTool, BranchMutatingTool  # noqa: PLC0415

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
        # BranchMutatingTool should not add any new abstract methods
        assert branch_abstracts == base_abstracts

    def test_base_tool_still_has_no_tool_category(self) -> None:
        """BaseTool must not have tool_category set (it's BranchMutatingTool's concern)."""
        from mcp_server.tools.base import BaseTool  # noqa: PLC0415

        # tool_category should not be present on BaseTool itself
        assert not hasattr(BaseTool, "tool_category") or BaseTool.tool_category is None  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# C1.2  EnforcementRule accepts tool_category
# ---------------------------------------------------------------------------


class TestEnforcementRuleToolCategory:
    """C1.2 — EnforcementRule.tool_category field and updated validator."""

    def test_rule_accepts_tool_category_field(self) -> None:
        from mcp_server.config.schemas.enforcement_config import EnforcementRule  # noqa: PLC0415

        rule = EnforcementRule(
            event_source="tool",
            timing="pre",
            tool_category="branch_mutating",
            actions=[],
        )
        assert rule.tool_category == "branch_mutating"

    def test_rule_with_tool_name_still_works(self) -> None:
        from mcp_server.config.schemas.enforcement_config import EnforcementRule  # noqa: PLC0415

        rule = EnforcementRule(
            event_source="tool",
            timing="pre",
            tool="submit_pr",
            actions=[],
        )
        assert rule.tool == "submit_pr"

    def test_rule_rejects_neither_tool_nor_tool_category(self) -> None:
        """event_source=tool requires tool OR tool_category."""
        from mcp_server.config.schemas.enforcement_config import EnforcementRule  # noqa: PLC0415

        with pytest.raises(ValidationError):
            EnforcementRule(event_source="tool", timing="pre", actions=[])

    def test_rule_tool_and_tool_category_are_mutually_exclusive(self) -> None:
        """Providing both tool and tool_category must be rejected."""
        from mcp_server.config.schemas.enforcement_config import EnforcementRule  # noqa: PLC0415

        with pytest.raises(ValidationError):
            EnforcementRule(
                event_source="tool",
                timing="pre",
                tool="submit_pr",
                tool_category="branch_mutating",
                actions=[],
            )

    def test_extra_fields_still_forbidden(self) -> None:
        from mcp_server.config.schemas.enforcement_config import EnforcementRule  # noqa: PLC0415

        with pytest.raises(ValidationError):
            EnforcementRule(
                event_source="tool",
                timing="pre",
                tool="submit_pr",
                unknown_field="x",
                actions=[],
            )


# ---------------------------------------------------------------------------
# C1.3  PRStatus / IPRStatusReader / IPRStatusWriter
# ---------------------------------------------------------------------------


class TestPRStatusInterfaces:
    """C1.3 — PRStatus enum and reader/writer interfaces in core/interfaces/__init__.py."""

    def test_pr_status_enum_exists(self) -> None:
        from mcp_server.core.interfaces import PRStatus  # noqa: PLC0415

        assert PRStatus is not None

    def test_pr_status_has_open_and_absent(self) -> None:
        from mcp_server.core.interfaces import PRStatus  # noqa: PLC0415

        assert PRStatus.OPEN is not None
        assert PRStatus.ABSENT is not None

    def test_ipr_status_reader_exists(self) -> None:
        from mcp_server.core.interfaces import IPRStatusReader  # noqa: PLC0415

        assert IPRStatusReader is not None

    def test_ipr_status_reader_has_get_pr_status(self) -> None:
        from mcp_server.core.interfaces import IPRStatusReader  # noqa: PLC0415

        assert hasattr(IPRStatusReader, "get_pr_status")

    def test_ipr_status_writer_exists(self) -> None:
        from mcp_server.core.interfaces import IPRStatusWriter  # noqa: PLC0415

        assert IPRStatusWriter is not None

    def test_ipr_status_writer_has_set_pr_status(self) -> None:
        from mcp_server.core.interfaces import IPRStatusWriter  # noqa: PLC0415

        assert hasattr(IPRStatusWriter, "set_pr_status")


# ---------------------------------------------------------------------------
# C1.4  SubmitPRTool scaffold
# ---------------------------------------------------------------------------


class TestSubmitPRToolScaffold:
    """C1.4 — SubmitPRInput and SubmitPRTool class skeleton in pr_tools.py."""

    def test_submit_pr_input_exists(self) -> None:
        from mcp_server.tools.pr_tools import SubmitPRInput  # noqa: PLC0415

        assert SubmitPRInput is not None

    def test_submit_pr_input_required_fields(self) -> None:
        from mcp_server.tools.pr_tools import SubmitPRInput  # noqa: PLC0415

        fields = SubmitPRInput.model_fields
        assert "head" in fields
        assert "title" in fields

    def test_submit_pr_tool_class_exists(self) -> None:
        from mcp_server.tools.pr_tools import SubmitPRTool  # noqa: PLC0415

        assert SubmitPRTool is not None

    def test_submit_pr_tool_inherits_branch_mutating_tool(self) -> None:
        from mcp_server.tools.base import BranchMutatingTool  # noqa: PLC0415
        from mcp_server.tools.pr_tools import SubmitPRTool  # noqa: PLC0415

        assert issubclass(SubmitPRTool, BranchMutatingTool)

    def test_submit_pr_tool_name_is_submit_pr(self) -> None:
        from mcp_server.tools.pr_tools import SubmitPRTool  # noqa: PLC0415

        assert SubmitPRTool.name == "submit_pr"

    def test_create_pr_tool_still_exists_as_internal_utility(self) -> None:
        """Design D2: CreatePRTool class remains in pr_tools.py as internal utility."""
        from mcp_server.tools.pr_tools import CreatePRTool  # noqa: PLC0415

        assert CreatePRTool is not None


# ---------------------------------------------------------------------------
# C1.5  PRStatusCache implementation
# ---------------------------------------------------------------------------


class TestPRStatusCache:
    """C1.5 — PRStatusCache in mcp_server/state/pr_status_cache.py."""

    def test_pr_status_cache_class_exists(self) -> None:
        from mcp_server.state.pr_status_cache import PRStatusCache  # noqa: PLC0415

        assert PRStatusCache is not None

    def test_pr_status_cache_implements_reader(self) -> None:
        from mcp_server.core.interfaces import IPRStatusReader  # noqa: PLC0415
        from mcp_server.state.pr_status_cache import PRStatusCache  # noqa: PLC0415

        assert issubclass(PRStatusCache, IPRStatusReader)

    def test_pr_status_cache_implements_writer(self) -> None:
        from mcp_server.core.interfaces import IPRStatusWriter  # noqa: PLC0415
        from mcp_server.state.pr_status_cache import PRStatusCache  # noqa: PLC0415

        assert issubclass(PRStatusCache, IPRStatusWriter)

    def test_pr_status_cache_has_get_pr_status(self) -> None:
        from mcp_server.state.pr_status_cache import PRStatusCache  # noqa: PLC0415

        assert hasattr(PRStatusCache, "get_pr_status")

    def test_pr_status_cache_has_set_pr_status(self) -> None:
        from mcp_server.state.pr_status_cache import PRStatusCache  # noqa: PLC0415

        assert hasattr(PRStatusCache, "set_pr_status")

    def test_pr_status_cache_cold_start_returns_absent(self) -> None:
        """Cold start (empty cache, no GitHub API mock): unknown branch → ABSENT."""
        from unittest.mock import MagicMock  # noqa: PLC0415

        from mcp_server.core.interfaces import PRStatus  # noqa: PLC0415
        from mcp_server.state.pr_status_cache import PRStatusCache  # noqa: PLC0415

        mock_github = MagicMock()
        mock_github.get_pr_status.return_value = PRStatus.ABSENT
        cache = PRStatusCache(github_manager=mock_github)

        result = cache.get_pr_status("feature/unknown-branch")
        assert result == PRStatus.ABSENT

    def test_set_then_get_returns_set_value(self) -> None:
        """Cache is session-leading: set → get returns same value without API call."""
        from unittest.mock import MagicMock  # noqa: PLC0415

        from mcp_server.core.interfaces import PRStatus  # noqa: PLC0415
        from mcp_server.state.pr_status_cache import PRStatusCache  # noqa: PLC0415

        mock_github = MagicMock()
        cache = PRStatusCache(github_manager=mock_github)

        cache.set_pr_status("feature/my-branch", PRStatus.OPEN)
        result = cache.get_pr_status("feature/my-branch")

        assert result == PRStatus.OPEN
        # API should NOT be called when cache hit exists
        mock_github.get_pr_status.assert_not_called()

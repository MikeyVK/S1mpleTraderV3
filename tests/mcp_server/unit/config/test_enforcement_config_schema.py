# tests/mcp_server/unit/config/test_enforcement_config_schema.py
"""Unit tests for EnforcementRule schema — tool_category field and validator.

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, mcp_server.config.schemas.enforcement_config]
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mcp_server.config.schemas.enforcement_config import EnforcementRule


class TestEnforcementRuleToolCategory:
    """EnforcementRule.tool_category field and updated validate_target validator."""

    def test_rule_accepts_tool_category(self) -> None:
        rule = EnforcementRule(
            event_source="tool",
            timing="pre",
            tool_category="branch_mutating",
            actions=[],
        )
        assert rule.tool_category == "branch_mutating"

    def test_rule_with_tool_name_still_works(self) -> None:
        rule = EnforcementRule(
            event_source="tool",
            timing="pre",
            tool="submit_pr",
            actions=[],
        )
        assert rule.tool == "submit_pr"

    def test_neither_tool_nor_tool_category_raises(self) -> None:
        """event_source=tool requires tool OR tool_category."""
        with pytest.raises(ValidationError):
            EnforcementRule(event_source="tool", timing="pre", actions=[])

    def test_both_tool_and_tool_category_raises(self) -> None:
        """tool and tool_category are mutually exclusive."""
        with pytest.raises(ValidationError):
            EnforcementRule(
                event_source="tool",
                timing="pre",
                tool="submit_pr",
                tool_category="branch_mutating",
                actions=[],
            )

    def test_extra_fields_still_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            EnforcementRule(
                event_source="tool",
                timing="pre",
                tool="submit_pr",
                unknown_field="x",
                actions=[],
            )

"""
tests/unit/tools/test_create_issue_label_assembly.py
======================================================
Cycle 5 — Label assembly in CreateIssueTool.

Tests for the private `_assemble_labels()` method and for `execute()` forwarding
the assembled label list to GitHubManager (no free-form labels, no `labels=None`).

Assembly rules (in order):
  type_label     = "type:epic"                   if is_epic
                 = IssueConfig.get_label(issue_type)   otherwise
  scope_label    = "scope:{scope}"
  priority_label = "priority:{priority}"
  phase_label    = "phase:{first_phase}"          from workflows.yaml via issue_type → workflow
  parent_label   = "parent:{n}"                  if parent_issue is not None
"""

from unittest.mock import MagicMock

import pytest

from mcp_server.tools.issue_tools import CreateIssueInput, CreateIssueTool, IssueBody

# ---------------------------------------------------------------------------
# Shared minimal input factory
# ---------------------------------------------------------------------------

BODY = IssueBody(problem="Test problem")


def make_params(**overrides) -> CreateIssueInput:  # type: ignore[no-untyped-def]
    """Return a minimal valid CreateIssueInput with optional overrides."""
    base = {
        "issue_type": "feature",
        "title": "Test issue",
        "priority": "medium",
        "scope": "mcp-server",
        "body": BODY,
    }
    base.update(overrides)
    return CreateIssueInput(**base)


# ---------------------------------------------------------------------------
# TestTypeLabelAssembly
# ---------------------------------------------------------------------------


class TestTypeLabelAssembly:
    def test_feature_produces_type_feature(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(issue_type="feature"))
        assert "type:feature" in labels

    def test_bug_produces_type_bug(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(issue_type="bug"))
        assert "type:bug" in labels

    def test_hotfix_produces_type_bug_not_type_hotfix(self) -> None:
        """hotfix maps to type:bug via IssueConfig.get_label(), not type:hotfix."""
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(issue_type="hotfix"))
        assert "type:bug" in labels
        assert "type:hotfix" not in labels

    def test_is_epic_overrides_type_to_type_epic(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(issue_type="feature", is_epic=True))
        assert "type:epic" in labels
        assert "type:feature" not in labels

    def test_is_epic_overrides_any_issue_type(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(issue_type="bug", is_epic=True))
        assert "type:epic" in labels
        assert "type:bug" not in labels

    def test_no_duplicate_type_labels(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(issue_type="feature"))
        type_labels = [l for l in labels if l.startswith("type:")]
        assert len(type_labels) == 1


# ---------------------------------------------------------------------------
# TestScopeLabelAssembly
# ---------------------------------------------------------------------------


class TestScopeLabelAssembly:
    def test_scope_mcp_server_produces_scope_mcp_server(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(scope="mcp-server"))
        assert "scope:mcp-server" in labels

    def test_scope_tooling_produces_scope_tooling(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(scope="tooling"))
        assert "scope:tooling" in labels

    def test_scope_platform_produces_scope_platform(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(scope="platform"))
        assert "scope:platform" in labels


# ---------------------------------------------------------------------------
# TestPriorityLabelAssembly
# ---------------------------------------------------------------------------


class TestPriorityLabelAssembly:
    def test_priority_medium_produces_priority_medium(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(priority="medium"))
        assert "priority:medium" in labels

    def test_priority_high_produces_priority_high(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(priority="high"))
        assert "priority:high" in labels

    def test_priority_critical_produces_priority_critical(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(priority="critical"))
        assert "priority:critical" in labels


# ---------------------------------------------------------------------------
# TestPhaseLabelAssembly
# ---------------------------------------------------------------------------


class TestPhaseLabelAssembly:
    def test_feature_workflow_first_phase_is_research(self) -> None:
        """feature → workflow:feature → first phase = research."""
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(issue_type="feature"))
        assert "phase:research" in labels

    def test_hotfix_workflow_first_phase_is_tdd(self) -> None:
        """hotfix → workflow:hotfix → first phase = tdd."""
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(issue_type="hotfix"))
        assert "phase:tdd" in labels

    def test_docs_workflow_first_phase_is_planning(self) -> None:
        """docs → workflow:docs → first phase = planning."""
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(issue_type="docs"))
        assert "phase:planning" in labels

    def test_bug_workflow_first_phase_is_research(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(issue_type="bug"))
        assert "phase:research" in labels

    def test_no_duplicate_phase_labels(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(issue_type="feature"))
        phase_labels = [l for l in labels if l.startswith("phase:")]
        assert len(phase_labels) == 1


# ---------------------------------------------------------------------------
# TestParentLabelAssembly
# ---------------------------------------------------------------------------


class TestParentLabelAssembly:
    def test_parent_issue_produces_parent_n_label(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(parent_issue=91))
        assert "parent:91" in labels

    def test_parent_issue_none_produces_no_parent_label(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(parent_issue=None))
        assert not any(l.startswith("parent:") for l in labels)

    def test_parent_issue_different_value(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(parent_issue=149))
        assert "parent:149" in labels


# ---------------------------------------------------------------------------
# TestFullLabelSet
# ---------------------------------------------------------------------------


class TestFullLabelSet:
    def test_minimal_input_produces_four_labels(self) -> None:
        """Minimal input → type + scope + priority + phase (no parent)."""
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params())
        assert len(labels) == 4

    def test_with_parent_issue_produces_five_labels(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(make_params(parent_issue=10))
        assert len(labels) == 5

    def test_full_label_set_no_duplicates(self) -> None:
        tool = CreateIssueTool(manager=MagicMock())
        labels = tool._assemble_labels(
            make_params(issue_type="bug", priority="high", scope="platform", parent_issue=55)
        )
        assert len(labels) == len(set(labels))


# ---------------------------------------------------------------------------
# TestExecuteForwardsAssembledLabels
# ---------------------------------------------------------------------------


class TestExecuteForwardsAssembledLabels:
    @pytest.mark.asyncio
    async def test_execute_passes_assembled_labels_to_manager(self) -> None:
        """execute() must pass the assembled label list — not None — to create_issue."""
        mock_manager = MagicMock()
        mock_manager.create_issue.return_value = {
            "number": 1,
            "title": "Test",
            "url": "http://x",
        }
        tool = CreateIssueTool(manager=mock_manager)

        params = make_params(issue_type="feature", scope="mcp-server", priority="medium")
        await tool.execute(params)

        call_kwargs = mock_manager.create_issue.call_args.kwargs
        labels = call_kwargs["labels"]
        assert labels is not None
        assert isinstance(labels, list)
        assert len(labels) > 0

    @pytest.mark.asyncio
    async def test_execute_labels_include_type_scope_priority_phase(self) -> None:
        mock_manager = MagicMock()
        mock_manager.create_issue.return_value = {"number": 2, "title": "T", "url": ""}
        tool = CreateIssueTool(manager=mock_manager)

        params = make_params(issue_type="feature", scope="tooling", priority="high")
        await tool.execute(params)

        labels = mock_manager.create_issue.call_args.kwargs["labels"]
        assert "type:feature" in labels
        assert "scope:tooling" in labels
        assert "priority:high" in labels
        assert "phase:research" in labels

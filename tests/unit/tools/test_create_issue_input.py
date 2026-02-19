"""
tests/unit/tools/test_create_issue_input.py
============================================
Cycle 4 — CreateIssueInput schema refactor.

Tests:
- All required fields (issue_type, title, priority, scope, body)
- Validators: issue_type against IssueConfig, title max length, priority, scope
- Optional fields: is_epic, parent_issue, milestone, assignees
- Breaking change: body must be IssueBody, not str
"""

import json

import pytest
from pydantic import ValidationError

from mcp_server.tools.issue_tools import CreateIssueInput, IssueBody

# ---------------------------------------------------------------------------
# Helper: minimal valid input
# ---------------------------------------------------------------------------

VALID_BODY = IssueBody(problem="The tool crashes on startup.")

VALID_MINIMAL: dict = {
    "issue_type": "feature",
    "title": "Add structured issue creation",
    "priority": "medium",
    "scope": "mcp-server",
    "body": VALID_BODY,
}


# ---------------------------------------------------------------------------
# TestCreateIssueInputRequired
# ---------------------------------------------------------------------------


class TestCreateIssueInputRequired:
    def test_all_required_fields_accepted(self) -> None:
        inp = CreateIssueInput(**VALID_MINIMAL)
        assert inp.issue_type == "feature"
        assert inp.title == "Add structured issue creation"
        assert inp.priority == "medium"
        assert inp.scope == "mcp-server"
        assert inp.body == VALID_BODY

    def test_missing_issue_type_raises(self) -> None:
        data = {k: v for k, v in VALID_MINIMAL.items() if k != "issue_type"}
        with pytest.raises(ValidationError):
            CreateIssueInput(**data)

    def test_missing_title_raises(self) -> None:
        data = {k: v for k, v in VALID_MINIMAL.items() if k != "title"}
        with pytest.raises(ValidationError):
            CreateIssueInput(**data)

    def test_missing_priority_raises(self) -> None:
        data = {k: v for k, v in VALID_MINIMAL.items() if k != "priority"}
        with pytest.raises(ValidationError):
            CreateIssueInput(**data)

    def test_missing_scope_raises(self) -> None:
        data = {k: v for k, v in VALID_MINIMAL.items() if k != "scope"}
        with pytest.raises(ValidationError):
            CreateIssueInput(**data)

    def test_missing_body_raises(self) -> None:
        data = {k: v for k, v in VALID_MINIMAL.items() if k != "body"}
        with pytest.raises(ValidationError):
            CreateIssueInput(**data)


# ---------------------------------------------------------------------------
# TestIssueTypeValidation
# ---------------------------------------------------------------------------


class TestIssueTypeValidation:
    def test_valid_issue_type_feature(self) -> None:
        inp = CreateIssueInput(**{**VALID_MINIMAL, "issue_type": "feature"})
        assert inp.issue_type == "feature"

    def test_valid_issue_type_bug(self) -> None:
        inp = CreateIssueInput(**{**VALID_MINIMAL, "issue_type": "bug"})
        assert inp.issue_type == "bug"

    def test_valid_issue_type_hotfix(self) -> None:
        inp = CreateIssueInput(**{**VALID_MINIMAL, "issue_type": "hotfix"})
        assert inp.issue_type == "hotfix"

    def test_valid_issue_type_chore(self) -> None:
        inp = CreateIssueInput(**{**VALID_MINIMAL, "issue_type": "chore"})
        assert inp.issue_type == "chore"

    def test_unknown_issue_type_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            CreateIssueInput(**{**VALID_MINIMAL, "issue_type": "nonsense"})
        assert "nonsense" in str(exc_info.value)

    def test_unknown_issue_type_error_hints_valid_values(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            CreateIssueInput(**{**VALID_MINIMAL, "issue_type": "invalid_type"})
        error_str = str(exc_info.value)
        # Error message should reference at least one valid type
        assert "feature" in error_str or "Valid" in error_str or "valid" in error_str


# ---------------------------------------------------------------------------
# TestTitleValidation
# ---------------------------------------------------------------------------


class TestTitleValidation:
    def test_title_within_72_chars_accepted(self) -> None:
        title = "A" * 72
        inp = CreateIssueInput(**{**VALID_MINIMAL, "title": title})
        assert len(inp.title) == 72

    def test_title_exceeding_72_chars_raises(self) -> None:
        title = "A" * 73
        with pytest.raises(ValidationError):
            CreateIssueInput(**{**VALID_MINIMAL, "title": title})

    def test_short_title_accepted(self) -> None:
        inp = CreateIssueInput(**{**VALID_MINIMAL, "title": "Fix bug"})
        assert inp.title == "Fix bug"


# ---------------------------------------------------------------------------
# TestPriorityValidation
# ---------------------------------------------------------------------------


class TestPriorityValidation:
    @pytest.mark.parametrize("priority", ["critical", "high", "medium", "low", "triage"])
    def test_valid_priority_accepted(self, priority: str) -> None:
        inp = CreateIssueInput(**{**VALID_MINIMAL, "priority": priority})
        assert inp.priority == priority

    def test_unknown_priority_raises(self) -> None:
        with pytest.raises(ValidationError):
            CreateIssueInput(**{**VALID_MINIMAL, "priority": "urgent"})

    def test_unknown_priority_error_references_valid_values(self) -> None:
        """Validator must report config-sourced values, not a hardcoded constant."""
        with pytest.raises(ValidationError) as exc_info:
            CreateIssueInput(**{**VALID_MINIMAL, "priority": "urgent"})
        error_str = str(exc_info.value)
        # At least one of the config-driven priorities must appear in the error
        assert any(p in error_str for p in ["critical", "high", "medium", "low", "triage"])


# ---------------------------------------------------------------------------
# TestScopeValidation
# ---------------------------------------------------------------------------


class TestScopeValidation:
    @pytest.mark.parametrize(
        "scope",
        ["architecture", "mcp-server", "platform", "tooling", "workflow", "documentation"],
    )
    def test_valid_scope_accepted(self, scope: str) -> None:
        inp = CreateIssueInput(**{**VALID_MINIMAL, "scope": scope})
        assert inp.scope == scope

    def test_unknown_scope_raises(self) -> None:
        with pytest.raises(ValidationError):
            CreateIssueInput(**{**VALID_MINIMAL, "scope": "backend"})


# ---------------------------------------------------------------------------
# TestBodyTypeValidation
# ---------------------------------------------------------------------------


class TestBodyTypeValidation:
    def test_body_must_be_issue_body_instance(self) -> None:
        with pytest.raises(ValidationError):
            CreateIssueInput(**{**VALID_MINIMAL, "body": "plain string body"})  # type: ignore[arg-type]

    def test_body_as_issue_body_accepted(self) -> None:
        body = IssueBody(problem="Correct type")
        inp = CreateIssueInput(**{**VALID_MINIMAL, "body": body})
        assert inp.body.problem == "Correct type"


# ---------------------------------------------------------------------------
# TestOptionalFields
# ---------------------------------------------------------------------------


class TestOptionalFields:
    def test_is_epic_defaults_to_false(self) -> None:
        inp = CreateIssueInput(**VALID_MINIMAL)
        assert inp.is_epic is False

    def test_is_epic_true_accepted(self) -> None:
        inp = CreateIssueInput(**{**VALID_MINIMAL, "is_epic": True})
        assert inp.is_epic is True

    def test_parent_issue_defaults_to_none(self) -> None:
        inp = CreateIssueInput(**VALID_MINIMAL)
        assert inp.parent_issue is None

    def test_parent_issue_positive_int_accepted(self) -> None:
        inp = CreateIssueInput(**{**VALID_MINIMAL, "parent_issue": 91})
        assert inp.parent_issue == 91

    def test_parent_issue_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            CreateIssueInput(**{**VALID_MINIMAL, "parent_issue": 0})

    def test_parent_issue_negative_raises(self) -> None:
        with pytest.raises(ValidationError):
            CreateIssueInput(**{**VALID_MINIMAL, "parent_issue": -1})

    def test_milestone_defaults_to_none(self) -> None:
        inp = CreateIssueInput(**VALID_MINIMAL)
        assert inp.milestone is None

    def test_milestone_string_title_accepted(self) -> None:
        inp = CreateIssueInput(**{**VALID_MINIMAL, "milestone": "v2.0"})
        assert inp.milestone == "v2.0"

    def test_assignees_defaults_to_none(self) -> None:
        inp = CreateIssueInput(**VALID_MINIMAL)
        assert inp.assignees is None

    def test_assignees_list_accepted(self) -> None:
        inp = CreateIssueInput(**{**VALID_MINIMAL, "assignees": ["alice", "bob"]})
        assert inp.assignees == ["alice", "bob"]


# ---------------------------------------------------------------------------
# TestBodyJsonStringCoercion  (Cycle 8 RED — MCP chat interface compat)
# ---------------------------------------------------------------------------


class TestBodyJsonStringCoercion:
    """body field must accept a JSON string and coerce it to IssueBody.

    The MCP chat interface (Copilot Chat) serializes nested objects as JSON
    strings before passing them to the tool. Without coercion, every chat
    invocation fails with 'is not of type object'.
    """

    def test_body_json_string_minimal_is_coerced(self) -> None:
        """A JSON string with only `problem` is parsed into IssueBody."""
        body_str = json.dumps({"problem": "Widget crashes on startup."})
        inp = CreateIssueInput(**{**VALID_MINIMAL, "body": body_str})
        assert isinstance(inp.body, IssueBody)
        assert inp.body.problem == "Widget crashes on startup."

    def test_body_json_string_full_is_coerced(self) -> None:
        """A JSON string with all optional fields is fully parsed."""
        body_str = json.dumps({
            "problem": "Login fails.",
            "expected": "Redirect to dashboard.",
            "actual": "500 error.",
            "context": "Windows 11.",
            "steps_to_reproduce": "1. Open\n2. Click",
            "related_docs": ["docs/planning.md"],
        })
        inp = CreateIssueInput(**{**VALID_MINIMAL, "body": body_str})
        assert inp.body.expected == "Redirect to dashboard."
        assert inp.body.related_docs == ["docs/planning.md"]
        assert inp.body.steps_to_reproduce == "1. Open\n2. Click"

    def test_body_json_string_missing_problem_raises(self) -> None:
        """A JSON string without `problem` raises ValidationError."""
        body_str = json.dumps({"expected": "Something"})
        with pytest.raises(ValidationError):
            CreateIssueInput(**{**VALID_MINIMAL, "body": body_str})

    def test_body_invalid_json_string_raises(self) -> None:
        """A non-JSON string raises ValidationError with clear message."""
        with pytest.raises(ValidationError):
            CreateIssueInput(**{**VALID_MINIMAL, "body": "not valid json"})

    def test_body_dict_still_accepted(self) -> None:
        """Plain dict input still works (existing behavior must not break)."""
        inp = CreateIssueInput(**{**VALID_MINIMAL, "body": {"problem": "Dict input still works."}})
        assert isinstance(inp.body, IssueBody)
        assert inp.body.problem == "Dict input still works."

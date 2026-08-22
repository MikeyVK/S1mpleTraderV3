# tests/mcp_server/unit/config/test_tool_presentation_rollout.py
# template=unit_test version=8825c0bb created=2026-08-21T22:59Z updated=2026-08-22
"""Approved tool-presentation rollout contract tests.

@layer: Tests (Unit)
@dependencies: [pyyaml, presentation_config, text_presenter, tool_outputs]
@responsibilities:
    - Verify the approved 29-tool declarative mechanics matrix
    - Verify representative nested, inline, bounded, and outcome-neutral output
    - Avoid duplicating the runtime-derived supported tool catalog
"""

from __future__ import annotations

import string
from pathlib import Path
from typing import TypeAlias

import yaml

from mcp_server.bootstrap import SupportedToolContract
from mcp_server.config.schemas.presentation_config import (
    CollectionPresentationConfig,
    PresentationConfig,
)
from mcp_server.presenters.text_presenter import (
    TextPresenter,
    validate_presentation_alignment,
)
from mcp_server.schemas.tool_outputs import (
    GateFindingDTO,
    GateResultDTO,
    HealthCheckOutput,
    HealthStatus,
    IssueOutput,
    IssueSummaryDTO,
    ListIssuesOutput,
    PhaseDTO,
    PhaseTaskDTO,
    ProjectPlanOutput,
    PROutput,
    RunQualityGatesOutput,
    RunTestsOutput,
    TestFailureDTO,
)

_REPO_ROOT = Path(__file__).parents[4]
_PRESENTATION_PATH = _REPO_ROOT / ".pgmcp" / "config" / "presentation.yaml"

PlaceholderSet: TypeAlias = frozenset[str]
CollectionExpectation: TypeAlias = tuple[str, PlaceholderSet, tuple[str, PlaceholderSet] | None]


def _placeholders(template: str) -> PlaceholderSet:
    return frozenset(
        field_name.split(".")[0].split("[")[0]
        for _, field_name, _, _ in string.Formatter().parse(template)
        if field_name is not None
    )


def _load_config() -> PresentationConfig:
    raw = yaml.safe_load(_PRESENTATION_PATH.read_text(encoding="utf-8"))
    return PresentationConfig.model_validate(raw)


def _collection_shape(
    declaration: CollectionPresentationConfig,
) -> CollectionExpectation:
    child = None
    if declaration.children:
        nested = declaration.children[0]
        child = (nested.field, _placeholders(nested.item_template))
    return declaration.field, _placeholders(declaration.item_template), child


_MECHANICS: dict[str, tuple[int, tuple[CollectionExpectation, ...]]] = {
    "transition_cycle": (20, (("skipped_gates", frozenset({"item"}), None),)),
    "force_cycle_transition": (20, (("skipped_gates", frozenset({"item"}), None),)),
    "get_work_context": (20, ()),
    "initialize_project": (
        20,
        (
            ("required_phases", frozenset({"item"}), None),
            ("files_created", frozenset({"item"}), None),
        ),
    ),
    "get_project_plan": (
        10,
        (
            (
                "phases",
                frozenset({"name", "status"}),
                ("tasks", frozenset({"id", "title", "status"})),
            ),
        ),
    ),
    "save_planning_deliverables": (
        10,
        (("cycles", frozenset({"cycle_number", "deliverables_count"}), None),),
    ),
    "update_planning_deliverables": (
        10,
        (("cycles", frozenset({"cycle_number", "deliverables_count"}), None),),
    ),
    "transition_phase": (20, (("skipped_gates", frozenset({"item"}), None),)),
    "force_phase_transition": (20, (("skipped_gates", frozenset({"item"}), None),)),
    "git_list_branches": (
        20,
        (("branches", frozenset({"name", "is_current", "upstream"}), None),),
    ),
    "git_status": (
        20,
        (
            ("modified_files", frozenset({"item"}), None),
            ("untracked_files", frozenset({"item"}), None),
        ),
    ),
    "git_add_or_commit": (20, (("files", frozenset({"item"}), None),)),
    "git_restore": (20, (("files", frozenset({"item"}), None),)),
    "git_stash": (10, (("stashes", frozenset({"item"}), None),)),
    "create_issue": (10, ()),
    "update_issue": (10, ()),
    "get_issue": (10, ()),
    "list_issues": (
        10,
        (
            (
                "issues",
                frozenset(
                    {
                        "number",
                        "title",
                        "state",
                        "html_url",
                        "labels",
                        "assignees_summary",
                        "created_at",
                    }
                ),
                None,
            ),
        ),
    ),
    "list_prs": (
        10,
        (
            (
                "pull_requests",
                frozenset({"number", "title", "state", "html_url", "base_ref", "head_ref"}),
                None,
            ),
        ),
    ),
    "list_labels": (
        10,
        (("labels", frozenset({"name", "color", "description"}), None),),
    ),
    "add_labels": (10, ()),
    "remove_labels": (10, ()),
    "list_milestones": (
        10,
        (("milestones", frozenset({"number", "title", "state"}), None),),
    ),
    "scaffold_artifact": (
        20,
        (
            ("files_created", frozenset({"item"}), None),
            ("missing_fields", frozenset({"item"}), None),
            ("provided_fields", frozenset({"item"}), None),
        ),
    ),
    "auto_fix": (
        20,
        (
            ("gates_executed", frozenset({"item"}), None),
            ("modified_files", frozenset({"item"}), None),
        ),
    ),
    "run_quality_gates": (
        10,
        (
            (
                "gates",
                frozenset({"name", "passed", "status", "score"}),
                (
                    "findings",
                    frozenset(
                        {
                            "file",
                            "line",
                            "column",
                            "code",
                            "message",
                            "severity",
                            "fixable",
                        }
                    ),
                ),
            ),
        ),
    ),
    "run_tests": (
        5,
        (
            (
                "failures",
                frozenset({"test_id", "location", "short_reason", "is_collection_error"}),
                None,
            ),
        ),
    ),
    "safe_edit_file": (
        10,
        (
            (
                "issues",
                frozenset({"severity", "message", "line", "column", "code"}),
                None,
            ),
        ),
    ),
    "validate_template": (
        10,
        (("errors", frozenset({"severity", "message"}), None),),
    ),
}

_INLINE_SEQUENCE_FIELDS = {
    "get_work_context": "valid_phases",
    "create_issue": "labels",
    "update_issue": "labels",
    "get_issue": "labels",
    "add_labels": "labels",
    "remove_labels": "labels",
}


class TestToolPresentationRollout:
    """Verify approved presentation mechanics without wording snapshots."""

    def test_matches_approved_mechanics_matrix(self) -> None:
        config = _load_config()

        assert len(_MECHANICS) == 29
        for tool_name, (max_items, collections) in _MECHANICS.items():
            tool = config.tools[tool_name]
            assert tool.max_items == max_items, tool_name
            assert tuple(_collection_shape(item) for item in tool.collections) == collections, (
                tool_name
            )

        for tool_name, field in _INLINE_SEQUENCE_FIELDS.items():
            tool = config.tools[tool_name]
            templates = [tool.template_success or ""]
            templates.extend(
                case_template
                for enum_case in tool.enum_cases
                for case_template in enum_case.cases.values()
            )
            assert any(field in _placeholders(template) for template in templates), tool_name

    def test_renders_nested_project_plan_in_source_order(self) -> None:
        presenter = TextPresenter(config=_load_config())
        output = ProjectPlanOutput(
            issue_number=456,
            workflow_name="feature",
            phases=[
                PhaseDTO(
                    name="research",
                    status="complete",
                    tasks=[
                        PhaseTaskDTO(id="R1", title="Map boundaries", status="complete"),
                        PhaseTaskDTO(id="R2", title="Approve strategy", status="complete"),
                    ],
                ),
                PhaseDTO(
                    name="design",
                    status="active",
                    tasks=[PhaseTaskDTO(id="D1", title="Define model", status="active")],
                ),
            ],
        )

        text = presenter.present_text("get_project_plan", output)

        markers = ["research", "R1", "R2", "design", "D1"]
        positions = [text.index(marker) for marker in markers]
        assert positions == sorted(positions)

    def test_renders_nested_issue_labels_without_python_repr(self) -> None:
        presenter = TextPresenter(config=_load_config())
        output = ListIssuesOutput(
            issues_count=1,
            issues=[
                IssueSummaryDTO(
                    number=456,
                    title="Compact output",
                    state="open",
                    html_url="https://example.invalid/issues/456",
                    labels=["feature", "priority:high", "presentation"],
                    assignees_summary="agent",
                    created_at="2026-08-22",
                )
            ],
        )

        text = presenter.present_text("list_issues", output)

        assert "feature, priority:high, presentation" in text
        assert "['feature'" not in text

    def test_renders_bounded_failures_without_verbose_payloads(self) -> None:
        presenter = TextPresenter(config=_load_config())
        failures = [
            TestFailureDTO(
                test_id=f"test_{index}",
                location=f"tests/test_{index}.py:1",
                short_reason=f"reason-{index}",
                traceback=f"private-trace-{index}",
            )
            for index in range(7)
        ]
        output = RunTestsOutput(
            success=False,
            error_message="tests failed",
            exit_code=1,
            passed_count=3,
            failed_count=7,
            skipped_count=0,
            errors_count=0,
            duration_seconds=1.25,
            failures=failures,
            stderr="private-stderr",
        )

        text = presenter.present_text("run_tests", output, success=False)

        assert "reason-0" in text
        assert "reason-4" in text
        assert "reason-5" not in text
        assert "… 2 more failures" in text
        assert "private-trace" not in text
        assert "private-stderr" not in text

    def test_reports_quality_outcome_as_data_not_claim(self) -> None:
        presenter = TextPresenter(config=_load_config())
        output = RunQualityGatesOutput(
            success=False,
            error_message="gate failed",
            overall_pass=False,
            scope="files",
            file_count=1,
            gates=[
                GateResultDTO(
                    name="ruff",
                    passed=False,
                    status="failed",
                    score=None,
                    details="verbose details stay cached",
                )
            ],
        )

        text = presenter.present_text("run_quality_gates", output, success=False)

        assert "overall pass: false" in text.lower()
        assert "ruff" in text
        assert "verbose details stay cached" not in text
        assert "passed successfully" not in text
        assert "Quality gates failed" not in text

    def test_renders_bounded_quality_findings_without_cached_details(self) -> None:
        """Inline findings are bounded while the structured DTO remains complete."""
        presenter = TextPresenter(config=_load_config())
        findings = [
            GateFindingDTO(
                gate="ruff",
                message=("ruff executable unavailable" if index == 1 else f"issue-{index}"),
                file=None if index == 1 else f"src/file_{index}.py",
                line=None if index == 1 else index + 1,
                column=None if index == 1 else 3,
                code=None if index == 1 else f"E{index:03}",
                severity=None if index == 1 else "error",
                fixable=index % 2 == 0,
                details=f"private-detail-{index}",
            )
            for index in range(12)
        ]
        output = RunQualityGatesOutput(
            overall_pass=False,
            scope="files",
            file_count=12,
            gates=[
                GateResultDTO(
                    name="ruff",
                    passed=False,
                    status="failed",
                    score="Fail",
                    details="private gate details",
                    findings=findings,
                )
            ],
        )

        text = presenter.present_text("run_quality_gates", output)
        cached_payload = output.model_dump(mode="json")

        assert "issue-0" in text
        assert "issue-9" in text
        assert "issue-10" not in text
        assert "… 2 more findings" in text
        assert "-:-:- [-] ruff executable unavailable" in text
        assert "private-detail" not in text
        assert "private gate details" not in text
        assert len(cached_payload["gates"][0]["findings"]) == 12
        assert cached_payload["gates"][0]["findings"][11]["details"] == "private-detail-11"

    def test_real_quality_gate_config_aligns_with_nested_output_contract(self) -> None:
        """The deployed YAML section must resolve every nested DTO placeholder."""
        config = _load_config()
        focused_config = PresentationConfig.model_validate(
            {
                "global": config.global_settings.model_dump(mode="python"),
                "tools": {
                    "run_quality_gates": config.tools["run_quality_gates"].model_dump(mode="python")
                },
            }
        )
        presenter = TextPresenter(config=focused_config)

        validate_presentation_alignment(
            presenter,
            (
                SupportedToolContract(
                    name="run_quality_gates",
                    output_model=RunQualityGatesOutput,
                ),
            ),
        )

    def test_expands_issue_and_pr_details(self) -> None:
        presenter = TextPresenter(config=_load_config())
        issue = IssueOutput(
            number=456,
            title="Compact output",
            state="open",
            milestone_title="M1",
            assignees_summary="agent",
            html_url="https://example.invalid/issues/456",
            body="Issue body",
            labels=["feature"],
            created_at="2026-08-22",
            updated_at="2026-08-22",
            author="owner",
        )
        pull_request = PROutput(
            number=99,
            title="Compact output",
            html_url="https://example.invalid/pull/99",
            state="open",
            base_ref="main",
            head_ref="feature/456",
            body="PR body",
        )

        issue_text = presenter.present_text("get_issue", issue)
        pr_text = presenter.present_text("get_pr", pull_request)

        for value in ("Issue body", "feature", issue.html_url, issue.created_at):
            assert value in issue_text
        for value in ("PR body", "open", pull_request.html_url):
            assert value in pr_text

    def test_retains_health_check_identity_below_budget(self) -> None:
        presenter = TextPresenter(config=_load_config())
        output = HealthCheckOutput(
            status=HealthStatus.HEALTHY,
            version="1.2.3",
            pid=42,
            platform="test",
            uptime_seconds=3.5,
        )

        text = presenter.present_text("health_check", output)

        assert text == (
            "📋 **Server Health Status**\n"
            "- Status: healthy\n"
            "- Version: 1.2.3\n"
            "- Process ID: 42\n"
            "- Platform: test\n"
            "- Uptime: 3.5 seconds\n"
        )

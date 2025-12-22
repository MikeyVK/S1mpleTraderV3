"""
Dogfooding test: Initialize project for issue #18 with actual phase structure.

This test validates that initialize_project() can handle the real-world complexity
of issue #18's 7-phase implementation plan (Phases A-G).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.managers.dependency_graph_validator import (
    DependencyGraphValidator,
)
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.state.project import PhaseSpec, ProjectSpec


@pytest.fixture
def issue_18_project_spec() -> ProjectSpec:
    """
    Project spec for issue #18: Tooling-Enforced Lifecycle Workflow.

    From docs/development/mcp_server/ISSUE_18_IMPLEMENTATION_PLAN.md:
    - Phase A: Foundation (PhaseStateEngine + PolicyEngine)
    - Phase B: Phase Transition Tool (TransitionPhaseTool)
    - Phase C: Commit Choke Point (TDD sub-phase enforcement)
    - Phase D: File Creation Enforcement (scaffold tools mandatory)
    - Phase E: PR + Close Choke Points (artifact enforcement)
    - Phase F: SafeEdit Fast-Only (remove subprocess QA)
    - Phase G: Code Quality Gates (coverage + complexity metrics)

    Dependencies:
    - Phase A is foundation (no dependencies)
    - Phases B, C, D depend on A (need state engine + policy)
    - Phase E depends on B, C, D (needs all workflow tools)
    - Phase F depends on A (only needs policy engine)
    - Phase G depends on A, C (needs state + commit enforcement)
    """
    return ProjectSpec(
        project_title="Issue #18: Tooling-Enforced Lifecycle Workflow",
        phases=[
            PhaseSpec(
                phase_id="phase-a",
                title="Foundation: PhaseStateEngine + PolicyEngine",
                depends_on=[],
                blocks=[],
                labels=["phase:red", "priority:critical", "type:infrastructure"],
            ),
            PhaseSpec(
                phase_id="phase-b",
                title="Phase Transition Tool",
                depends_on=["phase-a"],
                blocks=[],
                labels=["phase:red", "priority:high", "type:feature"],
            ),
            PhaseSpec(
                phase_id="phase-c",
                title="Commit Choke Point (TDD Sub-Phases)",
                depends_on=["phase-a"],
                blocks=[],
                labels=["phase:red", "priority:critical", "type:enforcement"],
            ),
            PhaseSpec(
                phase_id="phase-d",
                title="File Creation Enforcement (Scaffold Tools)",
                depends_on=["phase-a"],
                blocks=[],
                labels=["phase:red", "priority:high", "type:enforcement"],
            ),
            PhaseSpec(
                phase_id="phase-e",
                title="PR + Close Choke Points",
                depends_on=["phase-b", "phase-c", "phase-d"],
                blocks=[],
                labels=["phase:red", "priority:high", "type:enforcement"],
            ),
            PhaseSpec(
                phase_id="phase-f",
                title="SafeEdit Fast-Only Alignment",
                depends_on=["phase-a"],
                blocks=[],
                labels=["phase:red", "priority:medium", "type:optimization"],
            ),
            PhaseSpec(
                phase_id="phase-g",
                title="Code Quality & Coverage Gates",
                depends_on=["phase-a", "phase-c"],
                blocks=[],
                labels=["phase:red", "priority:high", "type:quality"],
            ),
        ],
        parent_issue_number=None,  # Create new parent issue
        auto_create_branches=False,
        enforce_dependencies=True,
    )


@pytest.fixture
def mock_github_adapter() -> MagicMock:
    """Mock GitHub adapter with expected API responses for issue #18."""
    adapter = MagicMock()

    # Mock milestone creation
    adapter.create_milestone.return_value = {
        "number": 5,
        "title": "Issue #18: Tooling-Enforced Lifecycle Workflow"
    }

    # Mock parent issue + sub-issue creation (8 total: 1 parent + 7 phases)
    sub_issue_responses = [
        {
            "number": 18,
            "html_url": "https://github.com/user/repo/issues/18",
            "title": "Issue #18: Tooling-Enforced Lifecycle Workflow",
        },
        {
            "number": 19,
            "html_url": "https://github.com/user/repo/issues/19",
            "title": "Phase A: Foundation: PhaseStateEngine + PolicyEngine",
        },
        {
            "number": 20,
            "html_url": "https://github.com/user/repo/issues/20",
            "title": "Phase B: Phase Transition Tool",
        },
        {
            "number": 21,
            "html_url": "https://github.com/user/repo/issues/21",
            "title": "Phase C: Commit Choke Point (TDD Sub-Phases)",
        },
        {
            "number": 22,
            "html_url": "https://github.com/user/repo/issues/22",
            "title": "Phase D: File Creation Enforcement (Scaffold Tools)",
        },
        {
            "number": 23,
            "html_url": "https://github.com/user/repo/issues/23",
            "title": "Phase E: PR + Close Choke Points",
        },
        {
            "number": 24,
            "html_url": "https://github.com/user/repo/issues/24",
            "title": "Phase F: SafeEdit Fast-Only Alignment",
        },
        {
            "number": 25,
            "html_url": "https://github.com/user/repo/issues/25",
            "title": "Phase G: Code Quality & Coverage Gates",
        },
    ]
    adapter.create_issue.side_effect = sub_issue_responses

    # Mock update_issue for parent body update
    adapter.update_issue.return_value = None

    return adapter


# pylint: disable=too-many-locals
# Justification: Complex integration test requires validation of multiple fields
# pylint: disable=redefined-outer-name
# Justification: Pytest fixtures intentionally redefine fixture names
def test_initialize_issue_18_project(
    issue_18_project_spec: ProjectSpec,
    mock_github_adapter: MagicMock,
    tmp_path: Path,
) -> None:
    """
    Test: Initialize project for issue #18 with 7 phases (A-G).

    Validates:
    - All 7 phases created as sub-issues
    - Dependencies correctly mapped (Phase E depends on B, C, D)
    - Milestone created
    - Parent issue created with links to all sub-issues
    - .st3/projects.json persisted with correct structure
    - ProjectSummary contains all phases with dependency graph
    """
    # Arrange
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    manager = ProjectManager(
        github_adapter=mock_github_adapter,
        workspace_root=workspace_root,
    )

    # Act
    summary = manager.initialize_project(issue_18_project_spec)

    # Assert: Milestone created
    assert summary.milestone_id == 5

    # Assert: Parent issue created
    assert summary.parent_issue["number"] == 18
    assert summary.parent_issue["url"] == "https://github.com/user/repo/issues/18"

    # Assert: All 7 sub-issues created
    assert len(summary.sub_issues) == 7

    # Assert: Phase A (no dependencies)
    phase_a = summary.sub_issues["phase-a"]
    assert phase_a.issue_number == 19
    assert phase_a.depends_on == []
    assert phase_a.blocks == []

    # Assert: Phase B (depends on A)
    phase_b = summary.sub_issues["phase-b"]
    assert phase_b.issue_number == 20
    assert phase_b.depends_on == ["phase-a"]

    # Assert: Phase C (depends on A)
    phase_c = summary.sub_issues["phase-c"]
    assert phase_c.issue_number == 21
    assert phase_c.depends_on == ["phase-a"]

    # Assert: Phase D (depends on A)
    phase_d = summary.sub_issues["phase-d"]
    assert phase_d.issue_number == 22
    assert phase_d.depends_on == ["phase-a"]

    # Assert: Phase E (depends on B, C, D) - most complex dependency
    phase_e = summary.sub_issues["phase-e"]
    assert phase_e.issue_number == 23
    assert sorted(phase_e.depends_on) == ["phase-b", "phase-c", "phase-d"]

    # Assert: Phase F (depends on A)
    phase_f = summary.sub_issues["phase-f"]
    assert phase_f.issue_number == 24
    assert phase_f.depends_on == ["phase-a"]

    # Assert: Phase G (depends on A, C)
    phase_g = summary.sub_issues["phase-g"]
    assert phase_g.issue_number == 25
    assert sorted(phase_g.depends_on) == ["phase-a", "phase-c"]

    # Assert: Dependency graph correct
    # Dependency graph maps phase_id → list of phases it BLOCKS (not depends_on)
    # Since we didn't specify blocks explicitly, graph should be empty lists
    expected_graph: dict[str, list[str]] = {
        "phase-a": [],
        "phase-b": [],
        "phase-c": [],
        "phase-d": [],
        "phase-e": [],
        "phase-f": [],
        "phase-g": [],
    }
    assert summary.dependency_graph == expected_graph

    # Assert: Persistence
    projects_file = workspace_root / ".st3" / "projects.json"
    assert projects_file.exists()

    with projects_file.open(encoding="utf-8") as f:
        projects_data = json.load(f)

    assert "projects" in projects_data
    assert summary.project_id in projects_data["projects"]
    project_metadata = projects_data["projects"][summary.project_id]
    assert project_metadata["parent_issue"]["number"] == 18
    assert project_metadata["milestone_id"] == 5
    assert len(project_metadata["phases"]) == 7

    # Assert: GitHub API calls
    # 1 milestone + 1 parent issue + 7 sub-issues + 1 parent update = 10 calls
    assert mock_github_adapter.create_milestone.call_count == 1
    assert mock_github_adapter.create_issue.call_count == 8  # parent + 7 sub-issues
    assert mock_github_adapter.update_issue.call_count == 1


# pylint: disable=redefined-outer-name
# Justification: Pytest fixtures intentionally redefine fixture names
def test_issue_18_topological_order(
    issue_18_project_spec: ProjectSpec,
    mock_github_adapter: MagicMock,
    tmp_path: Path,
) -> None:
    """
    Test: Topological sort produces valid execution order for issue #18 phases.

    Expected order:
    1. phase-a (no dependencies)
    2. phase-b, phase-c, phase-d, phase-f (all depend on A)
    3. phase-g (depends on A, C - must come after C)
    4. phase-e (depends on B, C, D - must come after all three)
    """
    # Arrange
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    manager = ProjectManager(
        github_adapter=mock_github_adapter,
        workspace_root=workspace_root,
    )

    # Act
    _summary = manager.initialize_project(issue_18_project_spec)

    # Assert: Topological order validation
    validator = DependencyGraphValidator()
    topo_order = validator.topological_sort(issue_18_project_spec.phases)

    # Phase A must be first
    assert topo_order[0] == "phase-a"

    # Phase E must come after B, C, D
    phase_e_index = topo_order.index("phase-e")
    assert topo_order.index("phase-b") < phase_e_index
    assert topo_order.index("phase-c") < phase_e_index
    assert topo_order.index("phase-d") < phase_e_index

    # Phase G must come after A and C
    phase_g_index = topo_order.index("phase-g")
    assert topo_order.index("phase-a") < phase_g_index
    assert topo_order.index("phase-c") < phase_g_index


# pylint: disable=redefined-outer-name
# Justification: Pytest fixtures intentionally redefine fixture names
def test_issue_18_concurrent_phases_identification(
    issue_18_project_spec: ProjectSpec,
    mock_github_adapter: MagicMock,
    tmp_path: Path,
) -> None:
    """
    Test: Identify phases that can run concurrently for issue #18.

    Concurrent groups:
    - Group 1: phase-a (start)
    - Group 2: phase-b, phase-c, phase-d, phase-f (all depend only on A)
    - Group 3: phase-g (depends on A + C)
    - Group 4: phase-e (depends on B + C + D, must wait for group 2)

    This validates that the project structure supports parallel development.
    """
    # Arrange
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    manager = ProjectManager(
        github_adapter=mock_github_adapter,
        workspace_root=workspace_root,
    )

    # Act
    summary = manager.initialize_project(issue_18_project_spec)

    # Assert: Phases B, C, D, F can run concurrently (all depend only on A)
    phase_b = summary.sub_issues["phase-b"]
    phase_c = summary.sub_issues["phase-c"]
    phase_d = summary.sub_issues["phase-d"]
    phase_f = summary.sub_issues["phase-f"]

    assert phase_b.depends_on == ["phase-a"]
    assert phase_c.depends_on == ["phase-a"]
    assert phase_d.depends_on == ["phase-a"]
    assert phase_f.depends_on == ["phase-a"]

    # These 4 phases have no dependencies on each other
    concurrent_phase_ids = ["phase-b", "phase-c", "phase-d", "phase-f"]
    for phase_id in concurrent_phase_ids:
        phase = summary.sub_issues[phase_id]
        # None of the other concurrent phases should be in depends_on
        for other_phase_id in concurrent_phase_ids:
            if other_phase_id != phase_id:
                assert other_phase_id not in phase.depends_on


# pylint: disable=redefined-outer-name
# Justification: Pytest fixtures intentionally redefine fixture names
def test_issue_18_with_existing_parent_issue(
    issue_18_project_spec: ProjectSpec,
    mock_github_adapter: MagicMock,
    tmp_path: Path,
) -> None:
    """
    Test: Use existing issue #18 as parent instead of creating new one.

    Validates that parent_issue_number parameter works correctly.
    """
    # Arrange
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    # Modify spec to use existing issue
    spec_with_parent = ProjectSpec(
        project_title=issue_18_project_spec.project_title,
        phases=issue_18_project_spec.phases,
        parent_issue_number=18,  # Use existing issue
        auto_create_branches=False,
        enforce_dependencies=True,
    )

    # Mock get_issue for existing parent (not used - parent_issue_number
    # logic doesn't call get_issue)
    # Reset create_issue mock to only handle sub-issues (7 calls)
    sub_issue_responses = [
        {"number": 19, "html_url": "https://github.com/user/repo/issues/19"},
        {"number": 20, "html_url": "https://github.com/user/repo/issues/20"},
        {"number": 21, "html_url": "https://github.com/user/repo/issues/21"},
        {"number": 22, "html_url": "https://github.com/user/repo/issues/22"},
        {"number": 23, "html_url": "https://github.com/user/repo/issues/23"},
        {"number": 24, "html_url": "https://github.com/user/repo/issues/24"},
        {"number": 25, "html_url": "https://github.com/user/repo/issues/25"},
    ]
    mock_github_adapter.create_issue.side_effect = sub_issue_responses

    manager = ProjectManager(
        github_adapter=mock_github_adapter,
        workspace_root=workspace_root,
    )

    # Act
    summary = manager.initialize_project(spec_with_parent)

    # Assert: Parent issue is existing issue #18
    assert summary.parent_issue["number"] == 18

    # Assert: Only 7 sub-issues created (not 8 with parent)
    assert mock_github_adapter.create_issue.call_count == 7  # Only sub-issues

    # Assert: All 7 phases present
    assert len(summary.sub_issues) == 7

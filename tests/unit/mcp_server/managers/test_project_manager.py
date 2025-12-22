"""RED tests for ProjectManager.initialize_project() orchestration.

Tests the full workflow:
1. Validate dependency graph (reject cycles)
2. Create GitHub milestone
3. Create parent issue (if parent_issue_number not provided)
4. Create sub-issues for each phase
5. Update parent issue with sub-issue links
6. Persist ProjectMetadata to .st3/projects.json
7. Return ProjectSummary

All tests use mocked GitHubAdapter - no real API calls.
"""

import json
from pathlib import Path
from unittest.mock import Mock
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.state.project import PhaseSpec, ProjectSpec, ProjectSummary


class TestProjectManagerInitializeProject:
    """Test ProjectManager.initialize_project() full workflow."""

    def test_initialize_project_linear_dependencies(self, tmp_path: Path) -> None:
        """Test project initialization with linear dependencies A→B→C."""
        # Setup
        mock_adapter = Mock()
        mock_adapter.create_milestone.return_value = {"number": 10, "title": "Test Milestone"}
        mock_adapter.create_issue.side_effect = [
            {"number": 101, "html_url": "https://github.com/org/repo/issues/101"},  # parent
            {"number": 102, "html_url": "https://github.com/org/repo/issues/102"},  # phase A
            {"number": 103, "html_url": "https://github.com/org/repo/issues/103"},  # phase B
            {"number": 104, "html_url": "https://github.com/org/repo/issues/104"},  # phase C
        ]
        mock_adapter.update_issue.return_value = None

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Test Linear",
            phases=[
                PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=["B"]),
                PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"], blocks=["C"]),
                PhaseSpec(phase_id="C", title="Phase C", depends_on=["B"], blocks=[]),
            ],
            parent_issue_number=None,
        )

        # Execute
        result: ProjectSummary = manager.initialize_project(spec)

        # Verify
        # pylint: disable=no-member
        # Justification: False positive - result.project_id is a valid string field
        assert result.project_id.startswith("test-linear-")
        assert result.milestone_id == 10
        expected_parent = {
            "number": 101, "url": "https://github.com/org/repo/issues/101"
        }
        assert result.parent_issue == expected_parent
        assert len(result.sub_issues) == 3
        assert result.sub_issues["A"].issue_number == 102
        assert result.sub_issues["B"].issue_number == 103
        assert result.sub_issues["C"].issue_number == 104
        assert result.dependency_graph == {"A": ["B"], "B": ["C"], "C": []}

        # Verify milestone created
        mock_adapter.create_milestone.assert_called_once()

        # Verify 4 issues created (1 parent + 3 phases)
        assert mock_adapter.create_issue.call_count == 4

        # Verify parent issue updated with sub-issue links
        mock_adapter.update_issue.assert_called_once()

    def test_initialize_project_parallel_dependencies(self, tmp_path: Path) -> None:
        """Test project initialization with parallel dependencies A→B+C."""
        mock_adapter = Mock()
        mock_adapter.create_milestone.return_value = {"number": 11, "title": "Parallel Test"}
        mock_adapter.create_issue.side_effect = [
            {"number": 201, "html_url": "https://github.com/org/repo/issues/201"},  # parent
            {"number": 202, "html_url": "https://github.com/org/repo/issues/202"},  # phase A
            {"number": 203, "html_url": "https://github.com/org/repo/issues/203"},  # phase B
            {"number": 204, "html_url": "https://github.com/org/repo/issues/204"},  # phase C
        ]
        mock_adapter.update_issue.return_value = None

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Test Parallel",
            phases=[
                PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=["B", "C"]),
                PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"], blocks=[]),
                PhaseSpec(phase_id="C", title="Phase C", depends_on=["A"], blocks=[]),
            ],
            parent_issue_number=None,
        )

        result: ProjectSummary = manager.initialize_project(spec)

        # pylint: disable=no-member
        # Justification: False positive - result.project_id is a valid string field
        assert result.project_id.startswith("test-parallel-")
        assert len(result.sub_issues) == 3
        assert result.dependency_graph == {"A": ["B", "C"], "B": [], "C": []}

    def test_initialize_project_detects_cycle(self, tmp_path: Path) -> None:
        """Test project initialization rejects circular dependencies A↔B."""
        mock_adapter = Mock()
        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Test Cycle",
            phases=[
                PhaseSpec(phase_id="A", title="Phase A", depends_on=["B"], blocks=[]),
                PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"], blocks=[]),
            ],
            parent_issue_number=None,
        )

        # Execute and verify
        try:
            manager.initialize_project(spec)
            assert False, "Expected ValueError for circular dependency"
        except ValueError as e:
            assert "circular dependency" in str(e).lower()

        # Verify no GitHub calls made (validation happens first)
        mock_adapter.create_milestone.assert_not_called()
        mock_adapter.create_issue.assert_not_called()

    def test_persist_project_metadata_to_json(self, tmp_path: Path) -> None:
        """Test that ProjectMetadata is persisted to .st3/projects.json."""
        mock_adapter = Mock()
        mock_adapter.create_milestone.return_value = {"number": 12, "title": "Persist Test"}
        mock_adapter.create_issue.side_effect = [
            {"number": 301, "html_url": "https://github.com/org/repo/issues/301"},  # parent
            {"number": 302, "html_url": "https://github.com/org/repo/issues/302"},  # phase A
        ]
        mock_adapter.update_issue.return_value = None

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Test Persist",
            phases=[PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=[])],
            parent_issue_number=None,
        )

        result = manager.initialize_project(spec)

        # Verify file exists
        projects_file = tmp_path / ".st3" / "projects.json"
        assert projects_file.exists()

        # Verify content
        with open(projects_file, encoding="utf-8") as f:
            data = json.load(f)

        assert "projects" in data
        assert result.project_id in data["projects"]
        project_data = data["projects"][result.project_id]
        assert project_data["parent_issue"]["number"] == 301
        assert project_data["milestone_id"] == 12
        assert "A" in project_data["phases"]

    def test_load_existing_projects_from_json(self, tmp_path: Path) -> None:
        """Test loading existing projects and adding new project preserves both."""
        # Pre-create existing project
        st3_dir = tmp_path / ".st3"
        st3_dir.mkdir(exist_ok=True)
        projects_file = st3_dir / "projects.json"

        existing_data = {
            "projects": {
                "existing-project-1": {
                    "project_id": "existing-project-1",
                    "parent_issue": {
                        "number": 100,
                        "url": "https://github.com/org/repo/issues/100",
                    },
                    "milestone_id": 5,
                    "phases": {
                        "X": {
                            "issue_number": 101,
                            "url": "https://github.com/org/repo/issues/101",
                            "depends_on": [],
                            "blocks": [],
                            "status": "open",
                        }
                    },
                }
            }
        }
        with open(projects_file, "w", encoding="utf-8") as f:
            json.dump(existing_data, f)

        # Create new project
        mock_adapter = Mock()
        mock_adapter.create_milestone.return_value = {"number": 13, "title": "New Project"}
        mock_adapter.create_issue.side_effect = [
            {"number": 401, "html_url": "https://github.com/org/repo/issues/401"},  # parent
            {"number": 402, "html_url": "https://github.com/org/repo/issues/402"},  # phase Y
        ]
        mock_adapter.update_issue.return_value = None

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="New Project",
            phases=[PhaseSpec(phase_id="Y", title="Phase Y", depends_on=[], blocks=[])],
            parent_issue_number=None,
        )

        result = manager.initialize_project(spec)

        # Verify both projects exist
        with open(projects_file, encoding="utf-8") as f:
            data = json.load(f)

        assert len(data["projects"]) == 2
        assert "existing-project-1" in data["projects"]
        assert result.project_id in data["projects"]

    def test_atomic_write_on_github_failure(self, tmp_path: Path) -> None:
        """Test atomic write: rollback if GitHub API fails mid-operation."""
        mock_adapter = Mock()
        mock_adapter.create_milestone.return_value = {"number": 14, "title": "Failure Test"}
        mock_adapter.create_issue.side_effect = [
            {"number": 501, "html_url": "https://github.com/org/repo/issues/501"},  # parent
            Exception("GitHub API Error"),  # phase creation fails
        ]

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Test Failure",
            phases=[PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=[])],
            parent_issue_number=None,
        )

        # Execute and verify exception propagates
        try:
            manager.initialize_project(spec)
            assert False, "Expected exception from GitHub API failure"
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Testing generic exception propagation from mocked API
            assert "GitHub API Error" in str(e)

        # Verify no .st3/projects.json created (rollback)
        projects_file = tmp_path / ".st3" / "projects.json"
        assert not projects_file.exists()

    def test_create_milestone_via_adapter(self, tmp_path: Path) -> None:
        """Test that milestone is created via GitHubAdapter.create_milestone()."""
        mock_adapter = Mock()
        mock_adapter.create_milestone.return_value = {"number": 15, "title": "Milestone Test"}
        mock_adapter.create_issue.side_effect = [
            {"number": 601, "html_url": "https://github.com/org/repo/issues/601"},  # parent
            {"number": 602, "html_url": "https://github.com/org/repo/issues/602"},  # phase A
        ]
        mock_adapter.update_issue.return_value = None

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Milestone Test",
            phases=[PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=[])],
            parent_issue_number=None,
        )

        result = manager.initialize_project(spec)

        # Verify milestone created with correct title
        mock_adapter.create_milestone.assert_called_once()
        call_args = mock_adapter.create_milestone.call_args
        assert "Milestone Test" in str(call_args)

        assert result.milestone_id == 15

    def test_create_sub_issues_via_adapter(self, tmp_path: Path) -> None:
        """Test that sub-issues are created via GitHubAdapter.create_issue() for each phase."""
        mock_adapter = Mock()
        mock_adapter.create_milestone.return_value = {"number": 16, "title": "Sub-issue Test"}
        mock_adapter.create_issue.side_effect = [
            {"number": 701, "html_url": "https://github.com/org/repo/issues/701"},  # parent
            {"number": 702, "html_url": "https://github.com/org/repo/issues/702"},  # phase A
            {"number": 703, "html_url": "https://github.com/org/repo/issues/703"},  # phase B
        ]
        mock_adapter.update_issue.return_value = None

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Sub-issue Test",
            phases=[
                PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=["B"]),
                PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"], blocks=[]),
            ],
            parent_issue_number=None,
        )

        result = manager.initialize_project(spec)

        # Verify 3 issues created: 1 parent + 2 phases
        assert mock_adapter.create_issue.call_count == 3

        # Verify phase titles in issue creation calls
        calls = [str(call) for call in mock_adapter.create_issue.call_args_list]
        assert any("Phase A" in call for call in calls)
        assert any("Phase B" in call for call in calls)

        assert len(result.sub_issues) == 2

    def test_update_parent_issue_with_links(self, tmp_path: Path) -> None:
        """Test that parent issue body is updated with sub-issue links."""
        mock_adapter = Mock()
        mock_adapter.create_milestone.return_value = {"number": 17, "title": "Update Test"}
        mock_adapter.create_issue.side_effect = [
            {"number": 801, "html_url": "https://github.com/org/repo/issues/801"},  # parent
            {"number": 802, "html_url": "https://github.com/org/repo/issues/802"},  # phase A
            {"number": 803, "html_url": "https://github.com/org/repo/issues/803"},  # phase B
        ]
        mock_adapter.update_issue.return_value = None

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Update Test",
            phases=[
                PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=["B"]),
                PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"], blocks=[]),
            ],
            parent_issue_number=None,
        )

        manager.initialize_project(spec)

        # Verify parent issue updated
        mock_adapter.update_issue.assert_called_once()
        call_args = mock_adapter.update_issue.call_args

        # Verify update includes sub-issue numbers
        assert "802" in str(call_args) or "803" in str(call_args)

    def test_return_project_summary(self, tmp_path: Path) -> None:
        """Test that initialize_project returns ProjectSummary with all fields."""
        mock_adapter = Mock()
        mock_adapter.create_milestone.return_value = {"number": 18, "title": "Summary Test"}
        mock_adapter.create_issue.side_effect = [
            {"number": 901, "html_url": "https://github.com/org/repo/issues/901"},  # parent
            {"number": 902, "html_url": "https://github.com/org/repo/issues/902"},  # phase A
        ]
        mock_adapter.update_issue.return_value = None

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Summary Test",
            phases=[PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=[])],
            parent_issue_number=None,
        )

        result: ProjectSummary = manager.initialize_project(spec)

        # Verify ProjectSummary fields
        assert isinstance(result, ProjectSummary)
        # pylint: disable=no-member
        # Justification: False positive - result.project_id is a valid string field
        assert result.project_id.startswith("summary-test-")
        assert result.milestone_id == 18
        assert result.parent_issue["number"] == 901
        assert result.parent_issue["url"] == "https://github.com/org/repo/issues/901"
        assert "A" in result.sub_issues
        assert result.sub_issues["A"].issue_number == 902
        assert result.sub_issues["A"].url == "https://github.com/org/repo/issues/902"
        assert result.dependency_graph == {"A": []}

    def test_validate_graph_before_github_calls(self, tmp_path: Path) -> None:
        """Test that dependency graph validation happens before any GitHub API calls."""
        mock_adapter = Mock()
        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Validation Order Test",
            phases=[
                PhaseSpec(phase_id="A", title="Phase A", depends_on=["B"], blocks=[]),
                PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"], blocks=[]),
            ],
            parent_issue_number=None,
        )

        try:
            manager.initialize_project(spec)
            assert False, "Expected ValueError"
        except ValueError:
            pass

        # Verify NO GitHub calls made (validation happened first)
        mock_adapter.create_milestone.assert_not_called()
        mock_adapter.create_issue.assert_not_called()
        mock_adapter.update_issue.assert_not_called()

    def test_handle_github_api_error_gracefully(self, tmp_path: Path) -> None:
        """Test that GitHub API errors are handled gracefully with clear error messages."""
        mock_adapter = Mock()
        mock_adapter.create_milestone.side_effect = Exception("Rate limit exceeded")

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Error Handling Test",
            phases=[PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=[])],
            parent_issue_number=None,
        )

        try:
            manager.initialize_project(spec)
            assert False, "Expected exception"
        except Exception as e:  # pylint: disable=broad-exception-caught
            # Justification: Testing generic exception propagation from mocked API
            assert "Rate limit exceeded" in str(e)

        # Verify no persistence happened (error before persistence)
        projects_file = tmp_path / ".st3" / "projects.json"
        assert not projects_file.exists()

    def test_validate_existing_parent_issue(self, tmp_path: Path) -> None:
        """Test that providing parent_issue_number validates the issue exists."""
        mock_adapter = Mock()

        # Mock successful milestone creation
        mock_adapter.create_milestone.return_value = {"number": 10}

        # Mock get_issue to raise error (parent doesn't exist)
        mock_adapter.get_issue.side_effect = Exception("Issue not found")

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Test with Non-Existent Parent",
            phases=[PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=[])],
            parent_issue_number=999,  # Non-existent issue
        )

        try:
            manager.initialize_project(spec)
            assert False, "Expected ValueError for non-existent parent"
        except ValueError as e:
            assert "Parent issue #999 not found" in str(e)

        # Verify get_issue was called with correct number
        mock_adapter.get_issue.assert_called_once_with(999)

        # Verify no sub-issues created (validation failed early)
        assert not mock_adapter.create_issue.call_count

    def test_use_existing_parent_issue_url(self, tmp_path: Path) -> None:
        """Test that existing parent issue's real URL is used."""
        mock_adapter = Mock()

        # Mock milestone creation
        mock_adapter.create_milestone.return_value = {"number": 10}

        # Mock existing parent issue
        mock_parent = Mock()
        mock_parent.html_url = "https://github.com/owner/repo/issues/18"
        mock_adapter.get_issue.return_value = mock_parent

        # Mock sub-issue creation
        mock_adapter.create_issue.return_value = {
            "number": 20,
            "html_url": "https://github.com/owner/repo/issues/20"
        }

        # Mock update_issue
        mock_adapter.update_issue.return_value = None

        manager = ProjectManager(github_adapter=mock_adapter, workspace_root=tmp_path)

        spec = ProjectSpec(
            project_title="Test with Existing Parent",
            phases=[PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=[])],
            parent_issue_number=18,
        )

        result = manager.initialize_project(spec)

        # Verify real URL used from API
        assert result.parent_issue["number"] == 18
        assert result.parent_issue["url"] == "https://github.com/owner/repo/issues/18"

        # Verify get_issue was called
        mock_adapter.get_issue.assert_called_once_with(18)

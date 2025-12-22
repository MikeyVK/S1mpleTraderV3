"""Tests for project initialization DTOs."""
# Standard library
from typing import Literal

import pytest

# Project modules
from mcp_server.state.project import (
    PhaseSpec,
    ProjectSpec,
    SubIssueMetadata,
    ProjectMetadata,
    ProjectSummary,
    ValidationError,
    ValidationResult,
)


class TestPhaseSpec:
    """Tests for PhaseSpec DTO."""

    def test_valid_phase_spec(self) -> None:
        """Test creating a valid PhaseSpec."""
        phase = PhaseSpec(
            phase_id="A",
            title="Foundation: PhaseStateEngine + PolicyEngine",
            depends_on=[],
            blocks=["B", "C"],
            labels=["phase:red", "enhancement"]
        )
        assert phase.phase_id == "A"
        assert phase.title == "Foundation: PhaseStateEngine + PolicyEngine"
        assert phase.depends_on == []
        assert phase.blocks == ["B", "C"]
        assert phase.labels == ["phase:red", "enhancement"]

    def test_phase_spec_default_labels(self) -> None:
        """Test PhaseSpec with default labels."""
        phase = PhaseSpec(phase_id="B", title="Test Phase")
        assert phase.labels == ["phase:red"]

    def test_phase_spec_empty_dependencies(self) -> None:
        """Test PhaseSpec with no dependencies or blocks."""
        phase = PhaseSpec(phase_id="C", title="Independent Phase")
        assert phase.depends_on == []
        assert phase.blocks == []

    def test_phase_spec_self_dependency_rejected(self) -> None:
        """Test that phase cannot depend on itself."""
        with pytest.raises(ValueError, match="cannot depend on itself"):
            PhaseSpec(phase_id="A", title="Invalid Phase", depends_on=["A"])

    def test_phase_spec_self_block_rejected(self) -> None:
        """Test that phase cannot block itself."""
        with pytest.raises(ValueError, match="cannot block itself"):
            PhaseSpec(phase_id="A", title="Invalid Phase", blocks=["A"])

    def test_phase_spec_empty_phase_id_rejected(self) -> None:
        """Test that empty phase_id is rejected."""
        with pytest.raises(ValueError):
            PhaseSpec(phase_id="", title="Test Phase")

    def test_phase_spec_empty_title_rejected(self) -> None:
        """Test that empty title is rejected."""
        with pytest.raises(ValueError):
            PhaseSpec(phase_id="A", title="")


class TestProjectSpec:
    """Tests for ProjectSpec DTO."""

    def test_valid_project_spec(self) -> None:
        """Test creating a valid ProjectSpec."""
        phases = [
            PhaseSpec(phase_id="A", title="Phase A", depends_on=[], blocks=["B"]),
            PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"], blocks=[])
        ]
        spec = ProjectSpec(
            project_title="Issue #18: Choke Point Enforcement",
            phases=phases,
            parent_issue_number=18,
            auto_create_branches=True,
            enforce_dependencies=True
        )
        assert spec.project_title == "Issue #18: Choke Point Enforcement"
        assert len(spec.phases) == 2
        assert spec.parent_issue_number == 18
        assert spec.auto_create_branches is True
        assert spec.enforce_dependencies is True

    def test_project_spec_default_flags(self) -> None:
        """Test ProjectSpec with default boolean flags."""
        phases = [PhaseSpec(phase_id="A", title="Phase A")]
        spec = ProjectSpec(
            project_title="Test Project",
            phases=phases,
            parent_issue_number=1
        )
        assert spec.auto_create_branches is False
        assert spec.enforce_dependencies is True

    def test_project_spec_duplicate_phase_ids_rejected(self) -> None:
        """Test that duplicate phase IDs are rejected."""
        phases = [
            PhaseSpec(phase_id="A", title="Phase A"),
            PhaseSpec(phase_id="A", title="Duplicate Phase A")
        ]
        with pytest.raises(ValueError, match="Duplicate phase IDs"):
            ProjectSpec(
                project_title="Invalid Project",
                phases=phases,
                parent_issue_number=1
            )

    def test_project_spec_nonexistent_dependency_rejected(self) -> None:
        """Test that dependencies must reference existing phases."""
        phases = [PhaseSpec(phase_id="A", title="Phase A", depends_on=["B"])]
        with pytest.raises(ValueError, match="depends on non-existent phase"):
            ProjectSpec(
                project_title="Invalid Project",
                phases=phases,
                parent_issue_number=1
            )

    def test_project_spec_nonexistent_block_rejected(self) -> None:
        """Test that blocks must reference existing phases."""
        phases = [PhaseSpec(phase_id="A", title="Phase A", blocks=["B"])]
        with pytest.raises(ValueError, match="blocks non-existent phase"):
            ProjectSpec(
                project_title="Invalid Project",
                phases=phases,
                parent_issue_number=1
            )

    def test_project_spec_zero_parent_issue_rejected(self) -> None:
        """Test that parent_issue_number must be positive."""
        phases = [PhaseSpec(phase_id="A", title="Phase A")]
        with pytest.raises(ValueError):
            ProjectSpec(
                project_title="Invalid Project",
                phases=phases,
                parent_issue_number=0
            )

    def test_project_spec_negative_parent_issue_rejected(self) -> None:
        """Test that parent_issue_number cannot be negative."""
        phases = [PhaseSpec(phase_id="A", title="Phase A")]
        with pytest.raises(ValueError):
            ProjectSpec(
                project_title="Invalid Project",
                phases=phases,
                parent_issue_number=-1
            )


class TestSubIssueMetadata:
    """Tests for SubIssueMetadata DTO."""

    def test_valid_sub_issue_metadata(self) -> None:
        """Test creating valid SubIssueMetadata."""
        metadata = SubIssueMetadata(
            issue_number=29,
            url="https://github.com/owner/repo/issues/29",
            depends_on=[],
            blocks=["B", "C"],
            status="open"
        )
        assert metadata.issue_number == 29
        assert metadata.url == "https://github.com/owner/repo/issues/29"
        assert metadata.depends_on == []
        assert metadata.blocks == ["B", "C"]
        assert metadata.status == "open"

    def test_sub_issue_metadata_default_status(self) -> None:
        """Test SubIssueMetadata with default status."""
        metadata = SubIssueMetadata(
            issue_number=30,
            url="https://github.com/owner/repo/issues/30"
        )
        assert metadata.status == "open"

    def test_sub_issue_metadata_all_statuses(self) -> None:
        """Test all valid status values."""
        valid_statuses: list[Literal["open", "in-progress", "closed"]] = [
            "open", "in-progress", "closed"
        ]
        for status in valid_statuses:
            metadata = SubIssueMetadata(
                issue_number=31,
                url="https://github.com/owner/repo/issues/31",
                status=status
            )
            assert metadata.status == status

    def test_sub_issue_metadata_zero_issue_number_rejected(self) -> None:
        """Test that issue_number must be positive."""
        with pytest.raises(ValueError):
            SubIssueMetadata(issue_number=0, url="https://github.com/owner/repo/issues/0")


class TestProjectMetadata:
    """Tests for ProjectMetadata DTO."""

    def test_valid_project_metadata(self) -> None:
        """Test creating valid ProjectMetadata."""
        phases = {
            "A": SubIssueMetadata(
                issue_number=29,
                url="https://github.com/owner/repo/issues/29"
            ),
            "B": SubIssueMetadata(
                issue_number=30,
                url="https://github.com/owner/repo/issues/30"
            )
        }
        metadata = ProjectMetadata(
            project_id="project-18",
            parent_issue={"number": 18, "url": "https://github.com/owner/repo/issues/18"},
            milestone_id=1,
            phases=phases
        )
        assert metadata.project_id == "project-18"
        assert metadata.parent_issue["number"] == 18
        assert metadata.parent_issue["url"] == "https://github.com/owner/repo/issues/18"
        assert metadata.milestone_id == 1
        assert len(metadata.phases) == 2
        assert "A" in metadata.phases
        assert "B" in metadata.phases

    def test_project_metadata_empty_phases(self) -> None:
        """Test ProjectMetadata with empty phases dict."""
        metadata = ProjectMetadata(
            project_id="project-empty",
            parent_issue={"number": 1, "url": "https://github.com/owner/repo/issues/1"},
            milestone_id=1,
            phases={}
        )
        assert not metadata.phases


class TestProjectSummary:
    """Tests for ProjectSummary DTO."""

    def test_valid_project_summary(self) -> None:
        """Test creating valid ProjectSummary."""
        sub_issues = {
            "A": SubIssueMetadata(
                issue_number=29,
                url="https://github.com/owner/repo/issues/29",
                depends_on=[],
                blocks=["B"]
            )
        }
        dependency_graph = {
            "A": ["B"],
            "B": []
        }
        summary = ProjectSummary(
            project_id="project-18",
            milestone_id=1,
            parent_issue={"number": 18, "url": "https://github.com/owner/repo/issues/18"},
            sub_issues=sub_issues,
            dependency_graph=dependency_graph
        )
        assert summary.project_id == "project-18"
        assert summary.milestone_id == 1
        assert summary.parent_issue["number"] == 18
        assert summary.parent_issue["url"] == "https://github.com/owner/repo/issues/18"
        assert len(summary.sub_issues) == 1
        assert len(summary.dependency_graph) == 2

    def test_project_summary_empty_graph(self) -> None:
        """Test ProjectSummary with empty graph."""
        summary = ProjectSummary(
            project_id="project-empty",
            milestone_id=1,
            parent_issue={"number": 1, "url": "https://github.com/owner/repo/issues/1"},
            sub_issues={},
            dependency_graph={}
        )
        assert not summary.sub_issues
        assert not summary.dependency_graph


class TestValidationError:
    """Tests for ValidationError DTO."""

    def test_valid_validation_error(self) -> None:
        """Test creating valid ValidationError."""
        error = ValidationError(
            type="missing_issue",
            message="Phase B issue not found in GitHub",
            phase_id="B",
            issue_number=30,
            details={"expected": "30", "found": "missing"}
        )
        assert error.type == "missing_issue"
        assert error.message == "Phase B issue not found in GitHub"
        assert error.phase_id == "B"
        assert error.issue_number == 30
        assert error.details is not None

    def test_validation_error_minimal(self) -> None:
        """Test ValidationError with only required fields."""
        error = ValidationError(
            type="circular_dependency",
            message="Circular dependency detected"
        )
        assert error.type == "circular_dependency"
        assert error.message == "Circular dependency detected"
        assert error.phase_id is None
        assert error.issue_number is None
        assert error.details is None

    def test_validation_error_with_details_list(self) -> None:
        """Test ValidationError with list details."""
        error = ValidationError(
            type="circular_dependency",
            message="Cycle detected",
            details={"cycle": ["A", "B", "C", "A"]}
        )
        assert error.details is not None
        assert "cycle" in error.details


class TestValidationResult:
    """Tests for ValidationResult DTO."""

    def test_valid_validation_result(self) -> None:
        """Test creating valid ValidationResult."""
        errors = [
            ValidationError(type="missing_issue", message="Issue not found")
        ]
        warnings = [
            ValidationError(type="label_mismatch", message="Labels differ")
        ]
        result = ValidationResult(valid=False, errors=errors, warnings=warnings)
        assert result.valid is False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1

    def test_validation_result_success(self) -> None:
        """Test ValidationResult for successful validation."""
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert not result.errors
        assert not result.warnings

    def test_validation_result_errors_only(self) -> None:
        """Test ValidationResult with errors but no warnings."""
        errors = [ValidationError(type="missing_issue", message="Issue not found")]
        result = ValidationResult(valid=False, errors=errors)
        assert not result.valid
        assert len(result.errors) == 1
        assert not result.warnings

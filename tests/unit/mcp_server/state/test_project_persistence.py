"""Tests for project metadata persistence."""
# Standard library
import json
from pathlib import Path

# Project modules
from mcp_server.state.project import ProjectMetadata, SubIssueMetadata


class TestProjectPersistence:
    """Tests for .st3/projects.json persistence."""

    def test_write_and_read_project_metadata(self, tmp_path: Path) -> None:
        """Test writing and reading project metadata to JSON."""
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True, exist_ok=True)

        metadata = ProjectMetadata(
            project_id="project-18",
            parent_issue={"number": 18, "url": "https://github.com/owner/repo/issues/18"},
            milestone_id=1,
            phases={
                "A": SubIssueMetadata(
                    issue_number=29,
                    url="https://github.com/owner/repo/issues/29",
                    depends_on=[],
                    blocks=["B"],
                    status="open"
                )
            }
        )

        # Write
        data = {"projects": {metadata.project_id: metadata.model_dump()}}
        projects_file.write_text(json.dumps(data, indent=2))

        # Read
        loaded_data = json.loads(projects_file.read_text())
        loaded_metadata = ProjectMetadata(**loaded_data["projects"]["project-18"])

        assert loaded_metadata.project_id == metadata.project_id
        assert loaded_metadata.parent_issue == metadata.parent_issue
        assert loaded_metadata.milestone_id == metadata.milestone_id
        assert len(loaded_metadata.phases) == 1

    def test_multiple_projects_in_file(self, tmp_path: Path) -> None:
        """Test storing multiple projects in same file."""
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True, exist_ok=True)

        project1 = ProjectMetadata(
            project_id="project-18",
            parent_issue={"number": 18, "url": "https://github.com/owner/repo/issues/18"},
            milestone_id=1,
            phases={}
        )
        project2 = ProjectMetadata(
            project_id="project-22",
            parent_issue={"number": 22, "url": "https://github.com/owner/repo/issues/22"},
            milestone_id=2,
            phases={}
        )

        data = {
            "projects": {
                project1.project_id: project1.model_dump(),
                project2.project_id: project2.model_dump()
            }
        }
        projects_file.write_text(json.dumps(data, indent=2))

        loaded_data = json.loads(projects_file.read_text())
        assert len(loaded_data["projects"]) == 2
        assert "project-18" in loaded_data["projects"]
        assert "project-22" in loaded_data["projects"]

    def test_file_not_exists_returns_empty(self, tmp_path: Path) -> None:
        """Test reading non-existent file returns empty structure."""
        projects_file = tmp_path / ".st3" / "projects.json"

        # File doesn't exist - should handle gracefully
        if projects_file.exists():
            loaded_data = json.loads(projects_file.read_text())
        else:
            loaded_data = {"projects": {}}

        assert loaded_data == {"projects": {}}

    def test_atomic_write_via_temp_file(self, tmp_path: Path) -> None:
        """Test atomic write using temporary file."""
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True, exist_ok=True)

        metadata = ProjectMetadata(
            project_id="project-18",
            parent_issue={"number": 18, "url": "https://github.com/owner/repo/issues/18"},
            milestone_id=1,
            phases={}
        )

        # Write atomically via temp file
        temp_file = projects_file.with_suffix(".tmp")
        data = {"projects": {metadata.project_id: metadata.model_dump()}}
        temp_file.write_text(json.dumps(data, indent=2))
        temp_file.replace(projects_file)

        # Verify
        assert projects_file.exists()
        assert not temp_file.exists()
        loaded_data = json.loads(projects_file.read_text())
        assert "project-18" in loaded_data["projects"]

    def test_preserve_existing_projects_on_update(self, tmp_path: Path) -> None:
        """Test updating file preserves existing projects."""
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True, exist_ok=True)

        # Write initial project
        project1 = ProjectMetadata(
            project_id="project-18",
            parent_issue={"number": 18, "url": "https://github.com/owner/repo/issues/18"},
            milestone_id=1,
            phases={}
        )
        data = {"projects": {project1.project_id: project1.model_dump()}}
        projects_file.write_text(json.dumps(data, indent=2))

        # Add second project
        loaded_data = json.loads(projects_file.read_text())
        project2 = ProjectMetadata(
            project_id="project-22",
            parent_issue={"number": 22, "url": "https://github.com/owner/repo/issues/22"},
            milestone_id=2,
            phases={}
        )
        loaded_data["projects"][project2.project_id] = project2.model_dump()
        projects_file.write_text(json.dumps(loaded_data, indent=2))

        # Verify both exist
        final_data = json.loads(projects_file.read_text())
        assert len(final_data["projects"]) == 2
        assert "project-18" in final_data["projects"]
        assert "project-22" in final_data["projects"]

    def test_json_serialization_roundtrip(self, tmp_path: Path) -> None:
        """Test full JSON serialization roundtrip with all fields."""
        projects_file = tmp_path / ".st3" / "projects.json"
        projects_file.parent.mkdir(parents=True, exist_ok=True)

        metadata = ProjectMetadata(
            project_id="project-18",
            parent_issue={"number": 18, "url": "https://github.com/owner/repo/issues/18"},
            milestone_id=1,
            phases={
                "A": SubIssueMetadata(
                    issue_number=29,
                    url="https://github.com/owner/repo/issues/29",
                    depends_on=[],
                    blocks=["B", "C"],
                    status="open"
                ),
                "B": SubIssueMetadata(
                    issue_number=30,
                    url="https://github.com/owner/repo/issues/30",
                    depends_on=["A"],
                    blocks=["D"],
                    status="in-progress"
                )
            }
        )

        # Serialize
        json_str = metadata.model_dump_json(indent=2)
        data = {"projects": {metadata.project_id: json.loads(json_str)}}
        projects_file.write_text(json.dumps(data, indent=2))

        # Deserialize
        loaded_data = json.loads(projects_file.read_text())
        loaded_metadata = ProjectMetadata(**loaded_data["projects"]["project-18"])

        # Verify all fields
        assert loaded_metadata.project_id == "project-18"
        expected_parent = {
            "number": 18, "url": "https://github.com/owner/repo/issues/18"
        }
        assert loaded_metadata.parent_issue == expected_parent
        assert loaded_metadata.milestone_id == 1
        assert len(loaded_metadata.phases) == 2
        assert loaded_metadata.phases["A"].issue_number == 29
        assert loaded_metadata.phases["A"].status == "open"
        assert loaded_metadata.phases["B"].status == "in-progress"
        assert loaded_metadata.phases["A"].blocks == ["B", "C"]
        assert loaded_metadata.phases["B"].depends_on == ["A"]

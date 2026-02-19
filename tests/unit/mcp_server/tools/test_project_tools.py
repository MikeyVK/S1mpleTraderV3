"""Tests for InitializeProjectTool with parent_branch tracking.

Issue #79: Tests for parent_branch in InitializeProjectTool.
- Accepts explicit parent_branch parameter
- Auto-detects parent_branch from git reflog (best effort)
- Handles auto-detection failure gracefully

Issue #229 Cycle 4: SavePlanningDeliverablesTool (D4.1/D4.2/D4.3/GAP-04/GAP-06).
Issue #229 Cycle 5: UpdatePlanningDeliverablesTool (D5.1/D5.2/D5.3/GAP-09).
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.managers.project_manager import ProjectManager
from mcp_server.tools.project_tools import (
    InitializeProjectInput,
    InitializeProjectTool,
    SavePlanningDeliverablesInput,
    SavePlanningDeliverablesTool,
    UpdatePlanningDeliverablesInput,
    UpdatePlanningDeliverablesTool,
)


class TestInitializeProjectToolParentBranch:
    """Test parent_branch functionality in InitializeProjectTool."""

    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace.

        Args:
            tmp_path: Pytest tmp_path fixture

        Returns:
            Path to temporary workspace root
        """
        return tmp_path

    @pytest.fixture
    def tool(self, workspace_root: Path) -> InitializeProjectTool:
        """Create InitializeProjectTool instance.

        Args:
            workspace_root: Path to workspace root

        Returns:
            InitializeProjectTool instance
        """
        return InitializeProjectTool(workspace_root=workspace_root)

    @pytest.mark.asyncio
    async def test_initialize_with_explicit_parent_branch(
        self, tool: InitializeProjectTool
    ) -> None:
        """Test initializing project with explicit parent_branch.

        Issue #79: User can provide parent_branch explicitly.
        """
        # Mock git to return current branch
        with patch.object(tool.git_manager, "get_current_branch") as mock_branch:
            mock_branch.return_value = "feature/79-test"

            # Execute
            result = await tool.execute(
                InitializeProjectInput(
                    issue_number=79,
                    issue_title="Test",
                    workflow_name="feature",
                    parent_branch="epic/76-quality-gates",
                )
            )

        # Verify
        assert result.is_error is False
        content_text = result.content[0]["text"]
        assert "epic/76-quality-gates" in content_text
        assert '"parent_branch": "epic/76-quality-gates"' in content_text

    @pytest.mark.asyncio
    async def test_initialize_auto_detects_parent_branch(self, tool: InitializeProjectTool) -> None:
        """Test auto-detection of parent_branch via git reflog.

        Issue #79: If parent_branch not provided, auto-detect from git reflog.
        """
        # Mock git operations
        with (
            patch.object(tool.git_manager, "get_current_branch") as mock_branch,
            patch.object(tool, "_detect_parent_branch_from_reflog") as mock_detect,
        ):
            mock_branch.return_value = "feature/80-test"
            mock_detect.return_value = "main"  # Auto-detected

            # Execute - no parent_branch parameter
            result = await tool.execute(
                InitializeProjectInput(
                    issue_number=80, issue_title="Test Auto-detect", workflow_name="bug"
                )
            )

        # Verify
        assert result.is_error is False
        content_text = result.content[0]["text"]
        assert '"parent_branch": "main"' in content_text
        mock_detect.assert_called_once_with("feature/80-test")

    @pytest.mark.asyncio
    async def test_initialize_auto_detect_fails_gracefully(
        self, tool: InitializeProjectTool
    ) -> None:
        """Test auto-detection failure results in None.

        Issue #79: If git reflog fails, parent_branch should be None.
        """
        # Mock git operations
        with (
            patch.object(tool.git_manager, "get_current_branch") as mock_branch,
            patch.object(tool, "_detect_parent_branch_from_reflog") as mock_detect,
        ):
            mock_branch.return_value = "feature/81-test"
            mock_detect.return_value = None  # Detection failed

            # Execute
            result = await tool.execute(
                InitializeProjectInput(
                    issue_number=81, issue_title="Test Failed Detect", workflow_name="docs"
                )
            )

        # Verify - no error, parent_branch is null
        assert result.is_error is False
        content_text = result.content[0]["text"]
        assert '"parent_branch": null' in content_text
        mock_detect.assert_called_once_with("feature/81-test")

    @pytest.mark.asyncio
    async def test_explicit_parent_branch_overrides_auto_detect(
        self, tool: InitializeProjectTool
    ) -> None:
        """Test explicit parent_branch skips auto-detection.

        Issue #79: If parent_branch provided, don't call git reflog.
        """
        # Mock git operations
        with (
            patch.object(tool.git_manager, "get_current_branch") as mock_branch,
            patch.object(tool, "_detect_parent_branch_from_reflog") as mock_detect,
        ):
            mock_branch.return_value = "feature/82-test"

            # Execute with explicit parent_branch
            result = await tool.execute(
                InitializeProjectInput(
                    issue_number=82,
                    issue_title="Test Override",
                    workflow_name="feature",
                    parent_branch="epic/special",
                )
            )

        # Verify - auto-detect NOT called
        assert result.is_error is False
        content_text = result.content[0]["text"]
        assert '"parent_branch": "epic/special"' in content_text
        mock_detect.assert_not_called()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_deliverables(validates: dict | None = None) -> dict:
    """Return a minimal valid planning_deliverables dict with one cycle.

    If *validates* is given it is attached to the single deliverable entry,
    allowing L2 validation to be exercised.
    """
    deliverable: dict = {"id": "D1.1", "description": "placeholder"}
    if validates is not None:
        deliverable["validates"] = validates
    return {
        "tdd_cycles": {
            "total": 1,
            "cycles": [
                {
                    "cycle_number": 1,
                    "deliverables": [deliverable],
                    "exit_criteria": "Tests pass",
                }
            ],
        }
    }


class TestSavePlanningDeliverablesTool:
    """Tests for SavePlanningDeliverablesTool.

    Issue #229 Cycle 4 (GAP-04 + GAP-06):
    - D4.1: tool defined in project_tools.py
    - D4.2: tool registered in server.py (integration test, see test_server_tool_registration.py)
    - D4.3: Layer 2 validates-entry schema validation before persisting
    """

    @pytest.fixture()
    def tool(self, tmp_path: Path) -> SavePlanningDeliverablesTool:
        return SavePlanningDeliverablesTool(workspace_root=tmp_path)

    @pytest.fixture()
    def initialized(self, tmp_path: Path) -> tuple[Path, int]:
        """Initialize a project so save_planning_deliverables can run."""
        pm = ProjectManager(workspace_root=tmp_path)
        pm.initialize_project(
            issue_number=229,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        return tmp_path, 229

    # ------------------------------------------------------------------
    # D4.1: basic persistence
    # ------------------------------------------------------------------

    @pytest.mark.asyncio()
    async def test_save_planning_deliverables_tool_persists_to_projects_json(
        self, initialized: tuple[Path, int]
    ) -> None:
        """Happy path: valid payload is written to projects.json. (D4.1)"""
        workspace_root, issue_number = initialized
        tool_with_root = SavePlanningDeliverablesTool(workspace_root=workspace_root)

        result = await tool_with_root.execute(
            SavePlanningDeliverablesInput(
                issue_number=issue_number,
                planning_deliverables=_minimal_deliverables(),
            )
        )

        assert not result.is_error, f"Expected success, got: {result.content}"
        pm = ProjectManager(workspace_root=workspace_root)
        plan = pm.get_project_plan(issue_number)
        assert plan is not None
        assert "planning_deliverables" in plan

    @pytest.mark.asyncio()
    async def test_save_planning_deliverables_tool_rejects_duplicate(
        self, initialized: tuple[Path, int]
    ) -> None:
        """Duplicate call is rejected with clear error."""
        workspace_root, issue_number = initialized
        tool = SavePlanningDeliverablesTool(workspace_root=workspace_root)
        params = SavePlanningDeliverablesInput(
            issue_number=issue_number,
            planning_deliverables=_minimal_deliverables(),
        )
        await tool.execute(params)  # First call succeeds
        result = await tool.execute(params)  # Second call must fail

        assert result.is_error
        assert "already exist" in result.content[0]["text"].lower()

    @pytest.mark.asyncio()
    async def test_save_planning_deliverables_tool_rejects_missing_tdd_cycles(
        self, initialized: tuple[Path, int]
    ) -> None:
        """Payload without tdd_cycles key is rejected."""
        workspace_root, issue_number = initialized
        tool = SavePlanningDeliverablesTool(workspace_root=workspace_root)

        result = await tool.execute(
            SavePlanningDeliverablesInput(
                issue_number=issue_number,
                planning_deliverables={"notes": "forgot the tdd_cycles key"},
            )
        )

        assert result.is_error
        assert "tdd_cycles" in result.content[0]["text"]

    # ------------------------------------------------------------------
    # D4.3: Layer 2 validates-entry schema validation
    # ------------------------------------------------------------------

    @pytest.mark.asyncio()
    async def test_save_planning_deliverables_tool_rejects_unknown_validates_type(
        self, initialized: tuple[Path, int]
    ) -> None:
        """validates entry with unknown type is rejected before persisting. (D4.3)"""
        workspace_root, issue_number = initialized
        tool = SavePlanningDeliverablesTool(workspace_root=workspace_root)

        result = await tool.execute(
            SavePlanningDeliverablesInput(
                issue_number=issue_number,
                planning_deliverables=_minimal_deliverables(
                    validates={"type": "does_not_exist", "file": "x.py"}
                ),
            )
        )

        assert result.is_error
        text = result.content[0]["text"]
        assert "does_not_exist" in text
        assert "D1.1" in text  # deliverable ID surfaced in error

    @pytest.mark.asyncio()
    async def test_save_planning_deliverables_tool_rejects_validates_missing_required_field(
        self, initialized: tuple[Path, int]
    ) -> None:
        """validates entry missing required field (text for contains_text) is rejected. (D4.3)"""
        workspace_root, issue_number = initialized
        tool = SavePlanningDeliverablesTool(workspace_root=workspace_root)

        result = await tool.execute(
            SavePlanningDeliverablesInput(
                issue_number=issue_number,
                planning_deliverables=_minimal_deliverables(
                    validates={"type": "contains_text", "file": "x.py"}  # missing 'text'
                ),
            )
        )

        assert result.is_error
        text = result.content[0]["text"]
        assert "text" in text  # missing field name surfaced

    @pytest.mark.asyncio()
    async def test_save_planning_deliverables_tool_error_lists_available_types_and_fields(
        self, initialized: tuple[Path, int]
    ) -> None:
        """Error on unknown type lists all valid types and their required fields. (D4.3)"""
        workspace_root, issue_number = initialized
        tool = SavePlanningDeliverablesTool(workspace_root=workspace_root)

        result = await tool.execute(
            SavePlanningDeliverablesInput(
                issue_number=issue_number,
                planning_deliverables=_minimal_deliverables(validates={"type": "wrong_type"}),
            )
        )

        assert result.is_error
        text = result.content[0]["text"]
        # Must list all valid types
        for valid_type in ("file_exists", "file_glob", "contains_text", "absent_text", "key_path"):
            assert valid_type in text, f"Expected '{valid_type}' listed in error, got: {text}"


class TestUpdatePlanningDeliverablesTool:
    """Tests for UpdatePlanningDeliverablesTool.

    Issue #229 Cycle 5 (GAP-09):
    - D5.1: tool defined in project_tools.py
    - D5.2: update_planning_deliverables in project_manager.py
    - D5.3: tool registered in server.py
    """

    @pytest.fixture()
    def initialized(self, tmp_path: Path) -> tuple[Path, int]:
        """Create workspace with initial planning deliverables already saved."""
        issue_number = 229
        manager = ProjectManager(workspace_root=tmp_path)
        manager.initialize_project(
            issue_number=issue_number,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        manager.save_planning_deliverables(
            issue_number=issue_number,
            planning_deliverables=_minimal_deliverables(),
        )
        return tmp_path, issue_number

    @pytest.mark.asyncio()
    async def test_update_planning_deliverables_tool_appends_new_cycle(
        self, initialized: tuple[Path, int]
    ) -> None:
        """Sending a new cycle_number appends it to tdd_cycles.cycles. (D5.1)"""
        workspace_root, issue_number = initialized
        tool = UpdatePlanningDeliverablesTool(workspace_root=workspace_root)

        result = await tool.execute(
            UpdatePlanningDeliverablesInput(
                issue_number=issue_number,
                planning_deliverables={
                    "tdd_cycles": {
                        "total": 2,
                        "cycles": [
                            {
                                "cycle_number": 2,
                                "deliverables": [{"id": "D2.1", "description": "new cycle"}],
                                "exit_criteria": "Tests pass",
                            }
                        ],
                    }
                },
            )
        )

        assert not result.is_error
        manager = ProjectManager(workspace_root=workspace_root)
        data = json.loads(manager.projects_file.read_text())[str(issue_number)]
        cycles = data["planning_deliverables"]["tdd_cycles"]["cycles"]
        assert len(cycles) == 2  # original C1 + new C2
        assert cycles[1]["cycle_number"] == 2

    @pytest.mark.asyncio()
    async def test_update_planning_deliverables_tool_merges_deliverable_by_id(
        self, initialized: tuple[Path, int]
    ) -> None:
        """New deliverable id in existing cycle is appended. (D5.1)"""
        workspace_root, issue_number = initialized
        tool = UpdatePlanningDeliverablesTool(workspace_root=workspace_root)

        result = await tool.execute(
            UpdatePlanningDeliverablesInput(
                issue_number=issue_number,
                planning_deliverables={
                    "tdd_cycles": {
                        "total": 1,
                        "cycles": [
                            {
                                "cycle_number": 1,
                                "deliverables": [
                                    {"id": "D1.2", "description": "second deliverable"}
                                ],
                                "exit_criteria": "Tests pass",
                            }
                        ],
                    }
                },
            )
        )

        assert not result.is_error
        manager = ProjectManager(workspace_root=workspace_root)
        data = json.loads(manager.projects_file.read_text())[str(issue_number)]
        cycle1 = data["planning_deliverables"]["tdd_cycles"]["cycles"][0]
        ids = [d["id"] for d in cycle1["deliverables"]]
        assert "D1.1" in ids  # original preserved
        assert "D1.2" in ids  # new one appended

    @pytest.mark.asyncio()
    async def test_update_planning_deliverables_tool_updates_existing_deliverable_by_id(
        self, initialized: tuple[Path, int]
    ) -> None:
        """Existing deliverable id in existing cycle is overwritten. (D5.1)"""
        workspace_root, issue_number = initialized
        tool = UpdatePlanningDeliverablesTool(workspace_root=workspace_root)

        result = await tool.execute(
            UpdatePlanningDeliverablesInput(
                issue_number=issue_number,
                planning_deliverables={
                    "tdd_cycles": {
                        "total": 1,
                        "cycles": [
                            {
                                "cycle_number": 1,
                                "deliverables": [
                                    {"id": "D1.1", "description": "updated description"}
                                ],
                                "exit_criteria": "Tests pass",
                            }
                        ],
                    }
                },
            )
        )

        assert not result.is_error
        manager = ProjectManager(workspace_root=workspace_root)
        data = json.loads(manager.projects_file.read_text())[str(issue_number)]
        cycle1 = data["planning_deliverables"]["tdd_cycles"]["cycles"][0]
        d1_1 = next(d for d in cycle1["deliverables"] if d["id"] == "D1.1")
        assert d1_1["description"] == "updated description"

    @pytest.mark.asyncio()
    async def test_update_planning_deliverables_tool_rejects_before_initial_save(
        self, tmp_path: Path
    ) -> None:
        """Returns error when called before save_planning_deliverables. (D5.1)"""
        issue_number = 229
        manager = ProjectManager(workspace_root=tmp_path)
        manager.initialize_project(
            issue_number=issue_number,
            issue_title="Phase deliverables enforcement",
            workflow_name="feature",
        )
        tool = UpdatePlanningDeliverablesTool(workspace_root=tmp_path)

        result = await tool.execute(
            UpdatePlanningDeliverablesInput(
                issue_number=issue_number,
                planning_deliverables=_minimal_deliverables(),
            )
        )

        assert result.is_error
        assert "save_planning_deliverables" in result.content[0]["text"]

    @pytest.mark.asyncio()
    async def test_update_planning_deliverables_tool_validates_validates_entry_schema(
        self, initialized: tuple[Path, int]
    ) -> None:
        """Invalid validates entry is rejected before persisting. (D5.1)"""
        workspace_root, issue_number = initialized
        tool = UpdatePlanningDeliverablesTool(workspace_root=workspace_root)

        result = await tool.execute(
            UpdatePlanningDeliverablesInput(
                issue_number=issue_number,
                planning_deliverables=_minimal_deliverables(validates={"type": "unknown_type"}),
            )
        )

        assert result.is_error
        text = result.content[0]["text"]
        for valid_type in ("file_exists", "file_glob", "contains_text", "absent_text", "key_path"):
            assert valid_type in text, f"Expected '{valid_type}' listed in error, got: {text}"

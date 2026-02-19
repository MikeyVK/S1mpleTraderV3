"""Tests for DeliverableChecker and WorkphasesConfig schema extension.

Issue #229 Cycle 1: workphases.yaml exit_requires/entry_expects schema +
structural deliverable checker (file_exists, contains_text, absent_text, key_path).
"""

import json
from pathlib import Path

import pytest
import yaml

from mcp_server.config.workphases_config import WorkphasesConfig
from mcp_server.managers.deliverable_checker import DeliverableCheckError, DeliverableChecker


# ---------------------------------------------------------------------------
# WorkphasesConfig schema tests
# ---------------------------------------------------------------------------


class TestWorkphasesConfigSchema:
    """Verify exit_requires / entry_expects fields parse correctly."""

    def test_workphases_schema_exit_requires_field_is_parsed(self, tmp_path: Path) -> None:
        """Phase with exit_requires list is parsed into WorkphasesConfig.

        Issue #229 C1: exit_requires must be readable per phase.
        """
        workphases_path = tmp_path / "workphases.yaml"
        workphases_path.write_text(
            """
phases:
  planning:
    display_name: "Planning"
    exit_requires:
      - key: "planning_deliverables"
        description: "TDD cycle breakdown"
"""
        )

        config = WorkphasesConfig(workphases_path)
        exit_requires = config.get_exit_requires("planning")

        assert len(exit_requires) == 1
        assert exit_requires[0]["key"] == "planning_deliverables"

    def test_workphases_schema_entry_expects_field_is_parsed(self, tmp_path: Path) -> None:
        """Phase with entry_expects list is parsed into WorkphasesConfig.

        Issue #229 C1: entry_expects must be readable per phase.
        """
        workphases_path = tmp_path / "workphases.yaml"
        workphases_path.write_text(
            """
phases:
  tdd:
    display_name: "TDD"
    entry_expects:
      - key: "planning_deliverables"
        description: "Expected from planning phase"
"""
        )

        config = WorkphasesConfig(workphases_path)
        entry_expects = config.get_entry_expects("tdd")

        assert len(entry_expects) == 1
        assert entry_expects[0]["key"] == "planning_deliverables"

    def test_workphases_schema_backward_compat_phases_without_field(
        self, tmp_path: Path
    ) -> None:
        """Phases without exit_requires/entry_expects return empty list.

        Issue #229 C1: existing phases must not break when fields are absent.
        """
        workphases_path = tmp_path / "workphases.yaml"
        workphases_path.write_text(
            """
phases:
  research:
    display_name: "Research"
    subphases: []
  planning:
    display_name: "Planning"
    exit_requires:
      - key: "planning_deliverables"
        description: "TDD cycle breakdown"
"""
        )

        config = WorkphasesConfig(workphases_path)

        # research has no exit_requires or entry_expects — must return []
        assert config.get_exit_requires("research") == []
        assert config.get_entry_expects("research") == []

        # planning has exit_requires but no entry_expects
        assert config.get_entry_expects("planning") == []


# ---------------------------------------------------------------------------
# DeliverableChecker tests
# ---------------------------------------------------------------------------


class TestDeliverableChecker:
    """Verify DeliverableChecker validates deliverable specs correctly."""

    @pytest.fixture
    def checker(self, tmp_path: Path) -> DeliverableChecker:
        return DeliverableChecker(workspace_root=tmp_path)

    # --- file_exists ---

    def test_deliverable_checker_file_not_found_raises(
        self, checker: DeliverableChecker
    ) -> None:
        """file_exists check raises DeliverableCheckError when file absent.

        Issue #229 C1.
        """
        with pytest.raises(DeliverableCheckError, match="D1.1"):
            checker.check(
                "D1.1",
                {"type": "file_exists", "file": "mcp_server/managers/deliverable_checker.py"},
            )

    # --- contains_text (SCAFFOLD-header) ---

    def test_deliverable_checker_md_missing_scaffold_header_raises(
        self, checker: DeliverableChecker, tmp_path: Path
    ) -> None:
        """contains_text raises when SCAFFOLD header absent from .md file.

        Issue #229 C1: SCAFFOLD-header = contains_text with text='<!-- template='.
        """
        md_file = tmp_path / "docs" / "planning.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("# Planning\n\nNo header here.\n")

        with pytest.raises(DeliverableCheckError, match="D1.2"):
            checker.check(
                "D1.2",
                {
                    "type": "contains_text",
                    "file": "docs/planning.md",
                    "text": "<!-- template=",
                },
            )

    def test_deliverable_checker_md_valid_scaffold_header_passes(
        self, checker: DeliverableChecker, tmp_path: Path
    ) -> None:
        """contains_text passes silently when SCAFFOLD header present.

        Issue #229 C1.
        """
        md_file = tmp_path / "docs" / "planning.md"
        md_file.parent.mkdir(parents=True)
        md_file.write_text("<!-- template=planning version=abc created=2026-02-19 -->\n# Planning\n")

        # Must not raise
        checker.check(
            "D1.2",
            {
                "type": "contains_text",
                "file": "docs/planning.md",
                "text": "<!-- template=",
            },
        )

    # --- key_path (JSON) ---

    def test_deliverable_checker_json_key_path_present_passes(
        self, checker: DeliverableChecker, tmp_path: Path
    ) -> None:
        """key_path passes silently when dot-notation path resolves in JSON.

        Issue #229 C1.
        """
        json_file = tmp_path / ".st3" / "projects.json"
        json_file.parent.mkdir(parents=True)
        json_file.write_text(
            json.dumps({"229": {"planning_deliverables": {"tdd_cycles": {"total": 2}}}})
        )

        # Must not raise
        checker.check(
            "D1.3",
            {
                "type": "key_path",
                "file": ".st3/projects.json",
                "path": "229.planning_deliverables",
            },
        )

    def test_deliverable_checker_json_key_path_missing_raises(
        self, checker: DeliverableChecker, tmp_path: Path
    ) -> None:
        """key_path raises DeliverableCheckError when path absent in JSON.

        Issue #229 C1.
        """
        json_file = tmp_path / ".st3" / "projects.json"
        json_file.parent.mkdir(parents=True)
        json_file.write_text(json.dumps({"229": {}}))

        with pytest.raises(DeliverableCheckError, match="D1.4"):
            checker.check(
                "D1.4",
                {
                    "type": "key_path",
                    "file": ".st3/projects.json",
                    "path": "229.planning_deliverables",
                },
            )

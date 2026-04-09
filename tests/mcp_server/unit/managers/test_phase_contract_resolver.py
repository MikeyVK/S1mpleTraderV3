# tests\mcp_server\unit\managers\test_phase_contract_resolver.py
# template=unit_test version=3d15d309 created=2026-03-12T21:27Z updated=
"""Unit tests for phase contract config loading and resolution.

@layer: Tests (Unit)
@dependencies: pytest, tests.mcp_server.test_support, mcp_server.managers.phase_contract_resolver
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mcp_server.core.exceptions import ConfigError
from mcp_server.managers.phase_contract_resolver import (
    CheckSpec,
    PhaseContractResolver,
)
from tests.mcp_server.test_support import make_phase_config_context


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Create a minimal workspace with workphases, phase contracts, and deliverables."""
    st3_dir = tmp_path / ".st3"
    config_dir = st3_dir / "config"
    config_dir.mkdir(parents=True)

    (config_dir / "workphases.yaml").write_text(
        """
phases:
  planning:
    display_name: "Planning"
  implementation:
    display_name: "Implementation"
  documentation:
    display_name: "Documentation"
  ready:
    display_name: "Ready"
    terminal: true
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (config_dir / "phase_contracts.yaml").write_text(
        """
merge_policy:
  pr_allowed_phase: ready
  branch_local_artifacts: []
workflows:
  feature:
    planning:
      exit_requires:
        - id: planning-doc
          type: heading_present
          required: true
          file: docs/development/issue257/planning.md
          heading: "## Goal"
    implementation:
      cycle_based: true
      subphases: [red, green, refactor]
      commit_type_map:
        red: test
        green: feat
        refactor: refactor
      exit_requires:
        - id: required-design-doc
          type: file_exists
          required: true
          file: docs/development/issue257/design.md
        - id: design-doc
          type: file_exists
          required: false
          file: docs/development/issue257/design-original.md
      cycle_exit_requires:
        "1":
          - id: c1-red-test
            type: file_glob
            required: true
            dir: tests/mcp_server/unit/managers
            pattern: test_phase_contract_resolver.py
  docs:
    documentation:
      exit_requires:
        - id: docs-readme
          type: file_exists
          required: true
          file: docs/mcp_server/README.md
""".strip()
        + "\n",
        encoding="utf-8",
    )

    deliverables = {
        "257": {
            "planning_deliverables": {
                "tdd_cycles": {
                    "total": 1,
                    "cycles": [
                        {
                            "cycle_number": 1,
                            "deliverables": [
                                {
                                    "id": "design-doc",
                                    "description": "Override recommended config gate",
                                    "validates": {
                                        "type": "file_exists",
                                        "file": "docs/development/issue257/design-override.md",
                                    },
                                },
                                {
                                    "id": "required-design-doc",
                                    "description": "Attempt to override required config gate",
                                    "validates": {
                                        "type": "file_exists",
                                        "file": "docs/development/issue257/should-not-win.md",
                                    },
                                },
                                {
                                    "id": "issue-extra",
                                    "description": "Add new issue-specific recommended gate",
                                    "validates": {
                                        "type": "contains_text",
                                        "file": "docs/development/issue257/design.md",
                                        "text": "PhaseContractResolver",
                                    },
                                },
                            ],
                            "exit_criteria": "Cycle 1 contract checks are valid",
                        }
                    ],
                }
            }
        }
    }
    (st3_dir / "deliverables.json").write_text(json.dumps(deliverables, indent=2), encoding="utf-8")

    return tmp_path


class TestPhaseConfigContext:
    """Tests for config loading and fail-fast validation."""

    def test_invalid_cycle_based_phase_raises_config_error(self, tmp_path: Path) -> None:
        """cycle_based phases must declare a non-empty commit_type_map."""
        st3_dir = tmp_path / ".st3"
        config_dir = st3_dir / "config"
        config_dir.mkdir(parents=True)

        (config_dir / "workphases.yaml").write_text(
            "phases:\n"
            "  implementation:\n"
            "    display_name: Implementation\n"
            "  ready:\n"
            "    display_name: Ready\n"
            "    terminal: true\n",
            encoding="utf-8",
        )
        (config_dir / "phase_contracts.yaml").write_text(
            """
merge_policy:
  pr_allowed_phase: ready
  branch_local_artifacts: []
workflows:
  feature:
    implementation:
      cycle_based: true
""".strip()
            + "\n",
            encoding="utf-8",
        )

        with pytest.raises(ConfigError, match="commit_type_map") as exc_info:
            make_phase_config_context(tmp_path)

        assert exc_info.value.file_path is not None
        assert exc_info.value.file_path.replace("\\", "/").endswith(
            "/.st3/config/phase_contracts.yaml"
        )

    def test_loader_applies_defaults_for_optional_phase_fields(self, tmp_path: Path) -> None:
        """Missing optional fields should resolve to empty collections and false."""
        st3_dir = tmp_path / ".st3"
        config_dir = st3_dir / "config"
        config_dir.mkdir(parents=True)

        (config_dir / "workphases.yaml").write_text(
            "phases:\n"
            "  planning:\n"
            "    display_name: Planning\n"
            "  ready:\n"
            "    display_name: Ready\n"
            "    terminal: true\n",
            encoding="utf-8",
        )
        (config_dir / "phase_contracts.yaml").write_text(
            """
merge_policy:
  pr_allowed_phase: ready
  branch_local_artifacts: []
workflows:
  feature:
    planning: {}
""".strip()
            + "\n",
            encoding="utf-8",
        )

        context = make_phase_config_context(tmp_path)
        planning_phase = context.phase_contracts.workflows["feature"]["planning"]

        assert planning_phase.subphases == []
        assert planning_phase.commit_type_map == {}
        assert planning_phase.cycle_based is False
        assert planning_phase.exit_requires == []
        assert planning_phase.cycle_exit_requires == {}

    def test_context_loads_workphases_phase_contracts_and_issue_deliverables(
        self, workspace_root: Path
    ) -> None:
        """Facade should expose both config sources and optional issue deliverables."""
        context = make_phase_config_context(workspace_root, issue_number=257)

        assert context.workphases.get_entry_expects("implementation") == []
        assert "feature" in context.phase_contracts.workflows
        assert "implementation" in context.phase_contracts.workflows["feature"]
        assert context.planning_deliverables is not None

    def test_context_uses_refactor_commit_mapping_in_fixture(self, workspace_root: Path) -> None:
        """Implementation refactor subphase should keep the existing refactor commit type."""
        context = make_phase_config_context(workspace_root)

        assert (
            context.phase_contracts.workflows["feature"]["implementation"].commit_type_map[
                "refactor"
            ]
            == "refactor"
        )


class TestPhaseContractResolver:
    """Tests for config-backed phase resolution."""

    def test_resolve_merges_issue_specific_checks_without_overriding_required_gates(
        self, workspace_root: Path
    ) -> None:
        """Required config gates stay immutable while recommended gates can be overridden."""
        resolver = PhaseContractResolver(
            make_phase_config_context(workspace_root, issue_number=257)
        )

        checks = resolver.resolve("feature", "implementation", cycle_number=1)

        assert [check.id for check in checks] == [
            "required-design-doc",
            "c1-red-test",
            "design-doc",
            "issue-extra",
        ]
        assert all(isinstance(check, CheckSpec) for check in checks)
        check_by_id = {check.id: check for check in checks}
        assert check_by_id["required-design-doc"].file == "docs/development/issue257/design.md"
        assert check_by_id["required-design-doc"].required is True
        assert check_by_id["design-doc"].file == "docs/development/issue257/design-override.md"
        assert check_by_id["design-doc"].required is False
        assert check_by_id["issue-extra"].type == "contains_text"
        assert check_by_id["issue-extra"].required is False

    def test_resolve_returns_empty_list_for_non_applicable_docs_implementation(
        self, workspace_root: Path
    ) -> None:
        """Docs workflow has no implementation contract and should resolve cleanly to []."""
        resolver = PhaseContractResolver(make_phase_config_context(workspace_root))

        assert resolver.resolve("docs", "implementation", None) == []

    def test_resolve_returns_empty_list_for_unknown_workflow_and_phase(
        self, workspace_root: Path
    ) -> None:
        """Unknown workflow/phase combinations should not raise and should return []."""
        resolver = PhaseContractResolver(make_phase_config_context(workspace_root))

        assert resolver.resolve("unknown-workflow", "implementation", None) == []
        assert resolver.resolve("feature", "unknown-phase", None) == []

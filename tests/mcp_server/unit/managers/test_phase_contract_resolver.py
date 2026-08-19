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
    PhaseContractResolver,
)
from tests.mcp_server.test_support import get_default_server_root, make_phase_config_context


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Create a minimal workspace with workphases, phase contracts, and deliverables."""
    phase_gate_dir = tmp_path / get_default_server_root()
    config_dir = phase_gate_dir / "config"
    config_dir.mkdir(parents=True)

    (config_dir / "workphases.yaml").write_text(
        """
version: "1.0.0"
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

    (config_dir / "contracts.yaml").write_text(
        """
version: "1.0.0"
merge_policy:
  pr_allowed_phase: ready
  branch_local_artifacts: []
workflows:
  feature:
    phases:
      - name: planning
        exit_requires:
          - id: planning-doc
            type: heading_present
            required: true
            file: docs/development/issue257/planning.md
            heading: "## Goal"
        instructions:
          sub_role: test-role
          phase_instructions: Test instructions.
          handover_template: Test handover.
      - name: implementation
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
          1:
            - id: c1-red-test
              type: file_glob
              required: true
              dir: tests/mcp_server/unit/managers
              pattern: test_phase_contract_resolver.py
        instructions:
          sub_role: test-role
          phase_instructions: Test instructions.
          handover_template: Test handover.
      - name: ready
        instructions:
          sub_role: test-role
          phase_instructions: Test instructions.
          handover_template: Test handover.
  docs:
    phases:
      - name: documentation
        exit_requires:
          - id: docs-readme
            type: file_exists
            required: true
            file: docs/mcp_server/README.md
        instructions:
          sub_role: test-role
          phase_instructions: Test instructions.
          handover_template: Test handover.
      - name: ready
        instructions:
          sub_role: test-role
          phase_instructions: Test instructions.
          handover_template: Test handover.
""".strip()
        + "\n",
        encoding="utf-8",
    )

    deliverables = {
        "257": {
            "planning_deliverables": {
                "cycles": {
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
    (phase_gate_dir / "deliverables.json").write_text(
        json.dumps(deliverables, indent=2), encoding="utf-8"
    )

    return tmp_path


class TestPhaseConfigContext:
    """Tests for config loading and fail-fast validation."""

    def test_invalid_cycle_based_phase_raises_config_error(self, tmp_path: Path) -> None:
        """cycle_based phases must declare a non-empty commit_type_map."""
        phase_gate_dir = tmp_path / get_default_server_root()
        config_dir = phase_gate_dir / "config"
        config_dir.mkdir(parents=True)

        (config_dir / "workphases.yaml").write_text(
            'version: "1.0.0"\n'
            "phases:\n"
            "  implementation:\n"
            "    display_name: Implementation\n"
            "  ready:\n"
            "    display_name: Ready\n"
            "    terminal: true\n",
            encoding="utf-8",
        )
        (config_dir / "contracts.yaml").write_text(
            'version: "1.0.0"\n'
            "merge_policy:\n"
            "  pr_allowed_phase: ready\n"
            "  branch_local_artifacts: []\n"
            "workflows:\n"
            "  feature:\n"
            "    phases:\n"
            "      - name: implementation\n"
            "        cycle_based: true\n"
            "        instructions:\n"
            "          sub_role: test-role\n"
            "          phase_instructions: Test instructions.\n"
            "          handover_template: Test handover.\n"
            "      - name: ready\n"
            "        instructions:\n"
            "          sub_role: test-role\n"
            "          phase_instructions: Test instructions.\n"
            "          handover_template: Test handover.\n",
            encoding="utf-8",
        )

        with pytest.raises(ConfigError, match="commit_type_map") as exc_info:
            make_phase_config_context(tmp_path)

        assert exc_info.value.file_path is not None
        assert exc_info.value.file_path.replace("\\", "/").endswith(
            f"/{get_default_server_root()}/config/contracts.yaml"
        )

    def test_loader_applies_defaults_for_optional_phase_fields(self, tmp_path: Path) -> None:
        """Missing optional fields should resolve to empty collections and false."""
        phase_gate_dir = tmp_path / get_default_server_root()
        config_dir = phase_gate_dir / "config"
        config_dir.mkdir(parents=True)

        (config_dir / "workphases.yaml").write_text(
            'version: "1.0.0"\n'
            "phases:\n"
            "  planning:\n"
            "    display_name: Planning\n"
            "  ready:\n"
            "    display_name: Ready\n"
            "    terminal: true\n",
            encoding="utf-8",
        )
        (config_dir / "contracts.yaml").write_text(
            'version: "1.0.0"\n'
            "merge_policy:\n"
            "  pr_allowed_phase: ready\n"
            "  branch_local_artifacts: []\n"
            "workflows:\n"
            "  feature:\n"
            "    phases:\n"
            "      - name: planning\n"
            "        instructions:\n"
            "          sub_role: test-role\n"
            "          phase_instructions: Test instructions.\n"
            "          handover_template: Test handover.\n"
            "      - name: ready\n"
            "        instructions:\n"
            "          sub_role: test-role\n"
            "          phase_instructions: Test instructions.\n"
            "          handover_template: Test handover.\n",
            encoding="utf-8",
        )

        context = make_phase_config_context(tmp_path)
        planning_phase = context.contracts.workflows["feature"].get_phase("planning")

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
        assert "feature" in context.contracts.workflows
        assert "implementation" in context.contracts.workflows["feature"].get_phase_names()
        assert context.planning_deliverables is not None

    def test_context_uses_refactor_commit_mapping_in_fixture(self, workspace_root: Path) -> None:
        """Implementation refactor subphase should keep the existing refactor commit type."""
        context = make_phase_config_context(workspace_root)

        assert (
            context.contracts.workflows["feature"]
            .get_phase("implementation")
            .commit_type_map["refactor"]
            == "refactor"
        )


class TestPhaseContractResolver:
    """Tests for config-backed phase resolution."""

    def test_resolve_returns_empty_list_for_non_applicable_docs_implementation(
        self, workspace_root: Path
    ) -> None:
        """Docs workflow has no implementation contract and should resolve cleanly to []."""
        resolver = PhaseContractResolver(make_phase_config_context(workspace_root))

        assert resolver.resolve_phase_exit("docs", "implementation", None) == []

    def test_resolve_returns_empty_list_for_unknown_workflow_and_phase(
        self, workspace_root: Path
    ) -> None:
        """Unknown workflow/phase combinations should not raise and should return []."""
        resolver = PhaseContractResolver(make_phase_config_context(workspace_root))

        assert resolver.resolve_phase_exit("unknown-workflow", "implementation", None) == []
        assert resolver.resolve_phase_exit("feature", "unknown-phase", None) == []

    def test_resolve_phase_exit_returns_exit_requires_plus_cycle_gates_when_cycle_number_present(
        self, workspace_root: Path
    ) -> None:
        """resolve_phase_exit with cycle_number returns exit_requires + cycle_exit_requires."""
        resolver = PhaseContractResolver(
            make_phase_config_context(workspace_root, issue_number=257)
        )

        checks = resolver.resolve_phase_exit("feature", "implementation", cycle_number=1)

        assert [check.id for check in checks] == [
            "required-design-doc",
            "c1-red-test",
            "design-doc",
            "issue-extra",
        ]

    def test_resolve_phase_exit_returns_only_exit_requires_when_no_cycle_number(
        self, workspace_root: Path
    ) -> None:
        """resolve_phase_exit without cycle_number returns only exit_requires, no cycle gates."""
        resolver = PhaseContractResolver(make_phase_config_context(workspace_root))

        checks = resolver.resolve_phase_exit("feature", "implementation")

        ids = [check.id for check in checks]
        assert "required-design-doc" in ids
        assert "design-doc" in ids
        assert "c1-red-test" not in ids

    def test_resolve_cycle_exit_returns_only_cycle_exit_requires(
        self, workspace_root: Path
    ) -> None:
        """resolve_cycle_exit returns only cycle_exit_requires, not exit_requires."""
        resolver = PhaseContractResolver(make_phase_config_context(workspace_root))

        checks = resolver.resolve_cycle_exit("feature", "implementation", cycle_number=1)

        assert [check.id for check in checks] == ["c1-red-test"]

    def test_resolve_cycle_exit_excludes_phase_level_exit_requires(
        self, workspace_root: Path
    ) -> None:
        """Regression: cycle exit must not include phase-level exit_requires gates.

        The defect: resolve(cycle_number=N) merged both exit_requires and cycle_exit_requires,
        causing transition_cycle() to enforce phase-level gates that belong only to phase
        transitions.
        """
        resolver = PhaseContractResolver(
            make_phase_config_context(workspace_root, issue_number=257)
        )

        checks = resolver.resolve_cycle_exit("feature", "implementation", cycle_number=1)

        required_ids = {check.id for check in checks if check.required}
        assert "required-design-doc" not in required_ids
        assert "c1-red-test" in required_ids

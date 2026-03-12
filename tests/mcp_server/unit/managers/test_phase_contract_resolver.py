# tests\mcp_server\unit\managers\test_phase_contract_resolver.py
# template=unit_test version=3d15d309 created=2026-03-12T21:27Z updated=
"""Unit tests for phase contract config loading and resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.core.exceptions import ConfigError
from mcp_server.managers.phase_contract_resolver import (
    CheckSpec,
    PhaseConfigContext,
    PhaseContractResolver,
)


@pytest.fixture
def workspace_root(tmp_path: Path) -> Path:
    """Create a minimal workspace with workphases and phase contract config."""
    st3_dir = tmp_path / ".st3"
    config_dir = st3_dir / "config"
    config_dir.mkdir(parents=True)

    (st3_dir / "workphases.yaml").write_text(
        """
phases:
  planning:
    display_name: "Planning"
  implementation:
    display_name: "Implementation"
  documentation:
    display_name: "Documentation"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    (config_dir / "phase_contracts.yaml").write_text(
        """
workflows:
  feature:
    planning:
      checks:
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
        refactor: chore
      checks:
        - id: design-doc
          type: file_exists
          required: false
          file: docs/development/issue257/design.md
      cycle_checks:
        "1":
          - id: c1-red-test
            type: file_glob
            required: true
            file: tests/mcp_server/unit/managers/test_phase_contract_resolver.py
  docs:
    documentation:
      checks:
        - id: docs-readme
          type: file_exists
          required: true
          file: docs/mcp_server/README.md
""".strip()
        + "\n",
        encoding="utf-8",
    )

    return tmp_path


class TestPhaseConfigContext:
    """Tests for config loading and fail-fast validation."""

    def test_invalid_cycle_based_phase_raises_config_error(self, tmp_path: Path) -> None:
        """cycle_based phases must declare a non-empty commit_type_map."""
        st3_dir = tmp_path / ".st3"
        config_dir = st3_dir / "config"
        config_dir.mkdir(parents=True)

        (st3_dir / "workphases.yaml").write_text(
            "phases:\n  implementation:\n    display_name: Implementation\n",
            encoding="utf-8",
        )
        (config_dir / "phase_contracts.yaml").write_text(
            """
workflows:
  feature:
    implementation:
      cycle_based: true
""".strip()
            + "\n",
            encoding="utf-8",
        )

        with pytest.raises(ConfigError, match="commit_type_map") as exc_info:
            PhaseConfigContext.from_workspace(tmp_path)

        assert exc_info.value.file_path == ".st3/config/phase_contracts.yaml"

    def test_loader_applies_defaults_for_optional_phase_fields(self, tmp_path: Path) -> None:
        """Missing optional fields should resolve to empty collections and false."""
        st3_dir = tmp_path / ".st3"
        config_dir = st3_dir / "config"
        config_dir.mkdir(parents=True)

        (st3_dir / "workphases.yaml").write_text(
            "phases:\n  planning:\n    display_name: Planning\n",
            encoding="utf-8",
        )
        (config_dir / "phase_contracts.yaml").write_text(
            """
workflows:
  feature:
    planning: {}
""".strip()
            + "\n",
            encoding="utf-8",
        )

        context = PhaseConfigContext.from_workspace(tmp_path)
        planning_phase = context.phase_contracts.workflows["feature"]["planning"]

        assert planning_phase.subphases == []
        assert planning_phase.commit_type_map == {}
        assert planning_phase.cycle_based is False
        assert planning_phase.checks == []
        assert planning_phase.cycle_checks == {}

    def test_context_loads_workphases_and_phase_contracts(self, workspace_root: Path) -> None:
        """Facade should expose both config sources through one injectable object."""
        context = PhaseConfigContext.from_workspace(workspace_root)

        assert context.workphases.get_entry_expects("implementation") == []
        assert "feature" in context.phase_contracts.workflows
        assert "implementation" in context.phase_contracts.workflows["feature"]


class TestPhaseContractResolver:
    """Tests for config-backed phase resolution."""

    def test_resolve_returns_check_specs_for_known_cycle(self, workspace_root: Path) -> None:
        """Resolver should combine phase checks with cycle-specific checks."""
        resolver = PhaseContractResolver(PhaseConfigContext.from_workspace(workspace_root))

        checks = resolver.resolve("feature", "implementation", cycle_number=1)

        assert [check.id for check in checks] == ["design-doc", "c1-red-test"]
        assert all(isinstance(check, CheckSpec) for check in checks)
        assert checks[0].required is False
        assert checks[1].required is True

    def test_resolve_returns_empty_list_for_unknown_phase(self, workspace_root: Path) -> None:
        """Unknown phases should be treated as not applicable, not exceptional."""
        resolver = PhaseContractResolver(PhaseConfigContext.from_workspace(workspace_root))

        assert resolver.resolve("feature", "unknown-phase", cycle_number=None) == []

    def test_resolve_returns_empty_list_for_non_applicable_workflow_phase(
        self, workspace_root: Path
    ) -> None:
        """Workflows without a given phase should resolve to an empty list."""
        resolver = PhaseContractResolver(PhaseConfigContext.from_workspace(workspace_root))

        assert resolver.resolve("docs", "implementation", cycle_number=None) == []

# tests/mcp_server/unit/config/test_loader.py
# template=unit_test version= created=2026-04-09T00:00Z updated=
"""
Unit tests for ConfigLoader._inject_terminal_phase (issue #283 C2).

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.config.loader, mcp_server.config.schemas]
"""

# Standard library
from pathlib import Path

# Third-party
# (geen)
# Project modules
from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.workflows import WorkflowConfig
from mcp_server.config.schemas.workphases import PhaseDefinition, WorkphasesConfig


def _workflow_config(phases: list[str]) -> WorkflowConfig:
    return WorkflowConfig(
        version="1.0",
        workflows={
            "feature": {  # type: ignore[dict-item]
                "name": "feature",
                "phases": phases,
                "default_execution_mode": "interactive",
                "description": "Feature workflow",
            }
        },
    )


def _workphases_config(terminal_name: str = "ready") -> WorkphasesConfig:
    return WorkphasesConfig(
        version="1.0",
        phases={
            "planning": PhaseDefinition(display_name="Planning"),
            "implementation": PhaseDefinition(display_name="Implementation"),
            terminal_name: PhaseDefinition(display_name="Ready", terminal=True),
        },
    )


class TestInjectTerminalPhase:
    """Tests for ConfigLoader._inject_terminal_phase static method (C2 issue #283)."""

    def test_inject_terminal_phase_appends_to_all_workflows(self) -> None:
        """_inject_terminal_phase appends terminal phase name to every workflow."""
        workflow_config = _workflow_config(["planning", "implementation"])
        workphases = _workphases_config("ready")

        result = ConfigLoader._inject_terminal_phase(  # pyright: ignore[reportPrivateUsage]
            workflow_config, workphases
        )

        assert "ready" in result.workflows["feature"].phases

    def test_inject_terminal_phase_does_not_duplicate(self) -> None:
        """Workflows already containing the terminal phase are not modified."""
        workflow_config = _workflow_config(["planning", "implementation", "ready"])
        workphases = _workphases_config("ready")

        result = ConfigLoader._inject_terminal_phase(  # pyright: ignore[reportPrivateUsage]
            workflow_config, workphases
        )

        assert result.workflows["feature"].phases.count("ready") == 1

    def test_inject_terminal_phase_returns_new_object(self) -> None:
        """Input WorkflowConfig must not be mutated (CQS / D6)."""
        workflow_config = _workflow_config(["planning", "implementation"])
        workphases = _workphases_config("ready")
        original_phases = list(workflow_config.workflows["feature"].phases)

        result = ConfigLoader._inject_terminal_phase(  # pyright: ignore[reportPrivateUsage]
            workflow_config, workphases
        )

        assert result is not workflow_config
        assert workflow_config.workflows["feature"].phases == original_phases

    def test_inject_terminal_phase_no_file_io(self) -> None:
        """Calling _inject_terminal_phase without a real filesystem does not raise."""
        workflow_config = _workflow_config(["planning"])
        workphases = _workphases_config("ready")

        result = ConfigLoader._inject_terminal_phase(  # pyright: ignore[reportPrivateUsage]
            workflow_config, workphases
        )

        assert result is not None

    def test_load_workflow_config_does_not_inject(self, tmp_path: Path) -> None:
        """load_workflow_config() result must NOT contain terminal phase injection."""
        config_dir = tmp_path / ".st3" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "workflows.yaml").write_text(
            "version: '1.0'\n"
            "workflows:\n"
            "  feature:\n"
            "    name: feature\n"
            "    phases: [planning, implementation]\n"
            "    default_execution_mode: interactive\n"
            "    description: Feature workflow\n",
            encoding="utf-8",
        )
        loader = ConfigLoader(config_root=tmp_path)

        result = loader.load_workflow_config()

        assert "ready" not in result.workflows["feature"].phases

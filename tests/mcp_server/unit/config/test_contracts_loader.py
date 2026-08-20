# tests\mcp_server\unit\config\test_contracts_loader.py
# template=unit_test version=3d15d309 created=2026-05-02T18:00Z updated=
"""
Unit tests for mcp_server.config.loader.

Unit tests for load_contracts_config (issue #271 C2)

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.config.loader, mcp_server.config.schemas.contracts_config]
@responsibilities:
    - Test load_contracts_config happy path, error paths, removed methods, 6-workflow roundtrip
    - Verify ContractsConfig roundtrip equality for all 6 production workflows
    - Verify _inject_terminal_phase and load_phase_contracts_config are removed
"""

# Standard library
import re
from pathlib import Path

# Third-party
import pytest
import yaml

# Project modules
from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas.contracts_config import (
    BranchLocalArtifact,
    ContractsConfig,
    MergePolicy,
    PhaseInstructionsSpec,
    WorkflowEntry,
    WorkflowPhaseEntry,
)
from mcp_server.core.exceptions import ConfigError
from tests.mcp_server.test_support import get_default_server_root

_STUB_INSTR_DICT: dict[str, str] = {
    "sub_role": "test-role",
    "phase_instructions": "Test instructions.",
    "handover_template": "Test handover.",
}
_STUB_INSTRUCTIONS = PhaseInstructionsSpec(
    sub_role="test-role",
    phase_instructions="Test instructions.",
    handover_template="Test handover.",
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def config_dir(tmp_path: Path) -> Path:
    """Return a tmp .pgmcp/config directory."""
    d = tmp_path / get_default_server_root() / "config"
    d.mkdir(parents=True)
    return d


def _write_contracts(config_dir: Path, content: str) -> None:
    (config_dir / "contracts.yaml").write_text(content, encoding="utf-8")


_MINIMAL_YAML = """\
version: "1.0.0"
merge_policy:
  pr_allowed_phase: ready
  branch_local_artifacts: []
workflows:
  feature:
    phases:
      - name: research
        instructions:
          sub_role: test-role
          phase_instructions: Test instructions.
          handover_template: Test handover.
      - name: ready
        instructions:
          sub_role: test-role
          phase_instructions: Test instructions.
          handover_template: Test handover.
"""


def _make_loader_with_workflows(config_dir: Path, workflows: dict[str, object]) -> ConfigLoader:
    # Inject stub instructions into every phase that lacks them (field is required).
    enriched: dict[str, object] = {}
    for wf_name, wf_data in workflows.items():
        if isinstance(wf_data, dict) and "phases" in wf_data:
            phases = [
                {**p, "instructions": _STUB_INSTR_DICT}
                if isinstance(p, dict) and "instructions" not in p
                else p
                for p in wf_data["phases"]
            ]
            wf_data = {**wf_data, "phases": phases}
        enriched[wf_name] = wf_data
    content = yaml.dump(
        {
            "version": "1.0.0",
            "merge_policy": {
                "pr_allowed_phase": "ready",
                "branch_local_artifacts": [
                    {"path": f"{get_default_server_root()}/state.json", "reason": "branch-local"},
                ],
            },
            "workflows": enriched,
        },
        default_flow_style=False,
        allow_unicode=True,
    )
    _write_contracts(config_dir, content)
    return ConfigLoader(config_dir)


def _policy() -> MergePolicy:
    return MergePolicy(
        pr_allowed_phase="ready",
        branch_local_artifacts=[
            BranchLocalArtifact(
                path=f"{get_default_server_root()}/state.json", reason="branch-local"
            )
        ],
    )


def _wpe(name: str, **kwargs: object) -> WorkflowPhaseEntry:
    if "instructions" not in kwargs:
        kwargs["instructions"] = _STUB_INSTRUCTIONS
    return WorkflowPhaseEntry(name=name, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# load_contracts_config — happy path
# ---------------------------------------------------------------------------


class TestLoadContractsConfig:
    """Test load_contracts_config returns ContractsConfig on valid input."""

    def test_returns_contracts_config_instance(self, config_dir: Path) -> None:
        """load_contracts_config must return a ContractsConfig instance."""
        _write_contracts(config_dir, _MINIMAL_YAML)
        loader = ConfigLoader(config_dir)
        result = loader.load_contracts_config()
        assert isinstance(result, ContractsConfig)

    def test_feature_workflow_research_first_ready_last(self) -> None:
        """Real contracts.yaml: feature workflow has research first and ready last."""
        real = Path(__file__).parents[4] / get_default_server_root() / "config" / "contracts.yaml"
        if not real.exists():
            pytest.skip("contracts.yaml not yet created — passes after C2 GREEN")
        result = ConfigLoader(real.parent).load_contracts_config()
        phases = result.get_phases("feature")
        assert phases[0] == "research"
        assert phases[-1] == "ready"

    def test_real_chore_workflow_is_lightweight_and_non_cycle_based(self) -> None:
        """Real contracts.yaml exposes the approved five-phase chore contract."""
        real = Path(__file__).parents[4] / get_default_server_root() / "config" / "contracts.yaml"
        result = ConfigLoader(real.parent).load_contracts_config()

        assert result.get_phases("chore") == [
            "research",
            "implementation",
            "validation",
            "documentation",
            "ready",
        ]

        chore = result.workflows["chore"]
        research = chore.get_phase("research")
        implementation = chore.get_phase("implementation")

        assert research.exit_requires == []
        assert implementation.cycle_based is False
        assert implementation.subphases == []
        assert implementation.commit_type_map == {}
        assert "approved Research artifact" in implementation.instructions.phase_instructions
        assert "direct Chore / Research hand-over" in implementation.instructions.phase_instructions
        assert "when neither input exists" in implementation.instructions.phase_instructions

    def test_all_ready_contracts_are_exactly_equal(self) -> None:
        """Every workflow exposes one identical Ready instruction and hand-over."""

        real = Path(__file__).parents[4] / get_default_server_root() / "config" / "contracts.yaml"
        result = ConfigLoader(real.parent).load_contracts_config()
        ready_specs = [
            workflow.get_phase("ready").instructions for workflow in result.workflows.values()
        ]

        first = ready_specs[0]
        assert all(spec.phase_instructions == first.phase_instructions for spec in ready_specs)
        assert all(spec.handover_template == first.handover_template for spec in ready_specs)

    def test_ready_contract_retains_terminal_invariants(self) -> None:
        """The common Ready contract owns final evidence, transfer, and PR submission."""

        real = Path(__file__).parents[4] / get_default_server_root() / "config" / "contracts.yaml"
        result = ConfigLoader(real.parent).load_contracts_config()
        ready = result.workflows["feature"].get_phase("ready").instructions
        instructions = ready.phase_instructions
        handover = ready.handover_template or ""

        for marker in (
            "evidence",
            "deferred",
            "git_status",
            "git_diff_stat",
            "scaffold_artifact",
            "git_add_or_commit",
            "submit_pr",
        ):
            assert marker in instructions

        headings = (
            "#### Scope",
            "#### Deliverables",
            "#### Evidence",
            "#### Open Work",
            "#### Review Request",
        )
        positions = tuple(handover.index(heading) for heading in headings)
        assert positions == tuple(sorted(positions))
        assert "Review requested" in handover
        assert "human approval" not in instructions.lower()
        assert "merge_pr" not in instructions
        assert "selected workflow" in instructions
        assert "Validation evidence" not in instructions
        assert "Validation evidence" not in handover

    def test_real_contracts_preserve_global_instruction_invariants(self) -> None:
        """All effective contracts keep the approved structural instruction contract."""

        real = Path(__file__).parents[4] / get_default_server_root() / "config" / "contracts.yaml"
        result = ConfigLoader(real.parent).load_contracts_config()
        phases = [
            (workflow_name, phase)
            for workflow_name, workflow in result.workflows.items()
            for phase in workflow.phases
        ]

        assert len(phases) == 39

        headings = ("Scope", "Deliverables", "Evidence", "Open Work", "Review Request")
        prohibited = (
            "explore_subagent",
            "internal qa",
            "invoke the qa agent",
            "qa sub-agent",
            "return pass",
        )
        model_version = re.compile(r"\b(?:gpt|gemini|claude)[ -]?\d", re.IGNORECASE)

        for workflow_name, phase in phases:
            instructions = phase.instructions.phase_instructions
            handover = phase.instructions.handover_template or ""
            contract = f"{workflow_name}/{phase.name}"

            assert instructions.strip(), contract
            assert "get_work_context" not in instructions, contract
            assert handover.strip(), contract

            title = (
                "### Ready Hand-over"
                if phase.name == "ready"
                else f"### {workflow_name.title()} / {phase.name.title()} Hand-over"
            )
            assert handover.startswith(f"{title}\n"), contract

            canonical_headings = tuple(f"#### {heading}" for heading in headings)
            positions = tuple(handover.index(heading) for heading in canonical_headings)
            assert positions == tuple(sorted(positions)), contract
            assert "Review requested" in handover, contract

            effective_contract = f"{instructions}\n{handover}"
            lower_contract = effective_contract.lower()
            assert not any(marker in lower_contract for marker in prohibited), contract
            assert model_version.search(effective_contract) is None, contract

    def test_preimplementation_handovers_link_primary_review_inputs(self) -> None:
        """Research, Planning, and Design transfers expose clickable review inputs."""

        real = Path(__file__).parents[4] / get_default_server_root() / "config" / "contracts.yaml"
        result = ConfigLoader(real.parent).load_contracts_config()
        markdown_link = re.compile(r"\[[^\]\n]+\]\([^)\n]+\)")

        for workflow_name, workflow in result.workflows.items():
            for phase in workflow.phases:
                if phase.name not in {"research", "planning", "design"}:
                    continue

                handover = phase.instructions.handover_template or ""
                contract = f"{workflow_name}/{phase.name}"
                assert markdown_link.search(handover), contract
                assert not re.search(r"\([A-Za-z]:[\\/]", handover), contract

    def test_real_implementation_cycle_semantics_are_preserved(self) -> None:
        """Cycle-based workflows retain TDD metadata; Chore remains non-cycle-based."""

        real = Path(__file__).parents[4] / get_default_server_root() / "config" / "contracts.yaml"
        result = ConfigLoader(real.parent).load_contracts_config()

        for workflow_name in ("feature", "bug", "hotfix", "refactor"):
            implementation = result.workflows[workflow_name].get_phase("implementation")
            assert implementation.cycle_based is True
            assert implementation.subphases == ["red", "green", "refactor"]
            assert set(implementation.commit_type_map) == {"red", "green", "refactor"}

        chore = result.workflows["chore"].get_phase("implementation")
        assert chore.cycle_based is False
        assert chore.subphases == []
        assert chore.commit_type_map == {}

    def test_required_phase_artifacts_retain_scaffold_and_persistence(self) -> None:
        """Required Research, Planning, and Design artifacts remain executable."""

        real = Path(__file__).parents[4] / get_default_server_root() / "config" / "contracts.yaml"
        result = ConfigLoader(real.parent).load_contracts_config()
        artifact_ids = {"research-doc", "planning-doc", "design-doc"}
        schema_discovery_contracts = {
            ("docs", "planning"),
            ("epic", "research"),
            ("epic", "planning"),
            ("epic", "design"),
        }

        for workflow_name, workflow in result.workflows.items():
            for phase in workflow.phases:
                required_ids = {check.id for check in phase.exit_requires} & artifact_ids
                if not required_ids:
                    continue

                instructions = phase.instructions.phase_instructions
                contract = f"{workflow_name}/{phase.name}"
                assert "scaffold_artifact" in instructions, contract
                assert "context=" in instructions, contract
                assert "git_add_or_commit" in instructions, contract
                if (workflow_name, phase.name) in schema_discovery_contracts:
                    assert "scaffold_schema" in instructions, contract

    def test_loaded_object_passes_model_validator(self, config_dir: Path) -> None:
        """Loaded object must satisfy the model_validator (last phase == pr_allowed_phase)."""
        _write_contracts(config_dir, _MINIMAL_YAML)
        result = ConfigLoader(config_dir).load_contracts_config()
        assert result.merge_policy.pr_allowed_phase == "ready"
        assert result.get_phases("feature")[-1] == "ready"


# ---------------------------------------------------------------------------
# load_contracts_config — error paths
# ---------------------------------------------------------------------------


class TestLoadContractsConfigErrors:
    def test_missing_file_raises_config_error(self, config_dir: Path) -> None:
        """ConfigError (not FileNotFoundError) must be raised when contracts.yaml absent."""
        with pytest.raises(ConfigError):
            ConfigLoader(config_dir).load_contracts_config()

    def test_yaml_parse_error_raises_config_error(self, config_dir: Path) -> None:
        """ConfigError must be raised on YAML parse error."""
        _write_contracts(config_dir, "merge_policy: [\ninvalid yaml")
        with pytest.raises(ConfigError):
            ConfigLoader(config_dir).load_contracts_config()


# ---------------------------------------------------------------------------
# Removed methods
# ---------------------------------------------------------------------------


class TestRemovedLoaderMethods:
    def test_inject_terminal_phase_does_not_exist(self) -> None:
        """_inject_terminal_phase must be removed from ConfigLoader."""
        assert not hasattr(ConfigLoader, "_inject_terminal_phase")

    def test_load_phase_contracts_config_does_not_exist(self) -> None:
        """load_phase_contracts_config must be removed from ConfigLoader."""
        assert not hasattr(ConfigLoader, "load_phase_contracts_config")


# ---------------------------------------------------------------------------
# Roundtrip tests — all 7 workflows
# ---------------------------------------------------------------------------


class TestContractsConfigRoundtrip:
    """YAML → ContractsConfig → hand-crafted object equality for all 6 workflows."""

    def test_feature_workflow_roundtrip(self, config_dir: Path) -> None:
        impl = {
            "name": "implementation",
            "cycle_based": True,
            "subphases": ["red", "green", "refactor"],
            "commit_type_map": {"red": "test", "green": "feat", "refactor": "refactor"},
        }
        loader = _make_loader_with_workflows(
            config_dir,
            {
                "feature": {
                    "phases": [
                        {"name": "research"},
                        {"name": "planning"},
                        {"name": "design"},
                        impl,
                        {"name": "validation"},
                        {"name": "documentation"},
                        {"name": "ready"},
                    ]
                }
            },
        )
        expected = ContractsConfig(
            merge_policy=_policy(),
            workflows={
                "feature": WorkflowEntry(
                    phases=[
                        _wpe("research"),
                        _wpe("planning"),
                        _wpe("design"),
                        _wpe(
                            "implementation",
                            cycle_based=True,
                            subphases=["red", "green", "refactor"],
                            commit_type_map={
                                "red": "test",
                                "green": "feat",
                                "refactor": "refactor",
                            },
                        ),
                        _wpe("validation"),
                        _wpe("documentation"),
                        _wpe("ready"),
                    ]
                )
            },
        )
        assert loader.load_contracts_config() == expected

    def test_bug_workflow_roundtrip(self, config_dir: Path) -> None:
        impl = {
            "name": "implementation",
            "cycle_based": True,
            "subphases": ["red", "green", "refactor"],
            "commit_type_map": {"red": "test", "green": "feat", "refactor": "refactor"},
        }
        loader = _make_loader_with_workflows(
            config_dir,
            {
                "bug": {
                    "phases": [
                        {"name": "research"},
                        {"name": "planning"},
                        {"name": "design"},
                        impl,
                        {"name": "validation"},
                        {"name": "documentation"},
                        {"name": "ready"},
                    ]
                }
            },
        )
        expected = ContractsConfig(
            merge_policy=_policy(),
            workflows={
                "bug": WorkflowEntry(
                    phases=[
                        _wpe("research"),
                        _wpe("planning"),
                        _wpe("design"),
                        _wpe(
                            "implementation",
                            cycle_based=True,
                            subphases=["red", "green", "refactor"],
                            commit_type_map={
                                "red": "test",
                                "green": "feat",
                                "refactor": "refactor",
                            },
                        ),
                        _wpe("validation"),
                        _wpe("documentation"),
                        _wpe("ready"),
                    ]
                )
            },
        )
        assert loader.load_contracts_config() == expected

    def test_hotfix_workflow_roundtrip(self, config_dir: Path) -> None:
        impl = {
            "name": "implementation",
            "cycle_based": True,
            "subphases": ["red", "green", "refactor"],
            "commit_type_map": {"red": "test", "green": "feat", "refactor": "refactor"},
        }
        loader = _make_loader_with_workflows(
            config_dir,
            {
                "hotfix": {
                    "phases": [
                        impl,
                        {"name": "validation"},
                        {"name": "documentation"},
                        {"name": "ready"},
                    ]
                }
            },
        )
        expected = ContractsConfig(
            merge_policy=_policy(),
            workflows={
                "hotfix": WorkflowEntry(
                    phases=[
                        _wpe(
                            "implementation",
                            cycle_based=True,
                            subphases=["red", "green", "refactor"],
                            commit_type_map={
                                "red": "test",
                                "green": "feat",
                                "refactor": "refactor",
                            },
                        ),
                        _wpe("validation"),
                        _wpe("documentation"),
                        _wpe("ready"),
                    ]
                )
            },
        )
        assert loader.load_contracts_config() == expected

    def test_refactor_workflow_roundtrip(self, config_dir: Path) -> None:
        impl = {
            "name": "implementation",
            "cycle_based": True,
            "subphases": ["red", "green", "refactor"],
            "commit_type_map": {"red": "test", "green": "feat", "refactor": "refactor"},
        }
        loader = _make_loader_with_workflows(
            config_dir,
            {
                "refactor": {
                    "phases": [
                        {"name": "research"},
                        {"name": "planning"},
                        impl,
                        {"name": "validation"},
                        {"name": "documentation"},
                        {"name": "ready"},
                    ]
                }
            },
        )
        expected = ContractsConfig(
            merge_policy=_policy(),
            workflows={
                "refactor": WorkflowEntry(
                    phases=[
                        _wpe("research"),
                        _wpe("planning"),
                        _wpe(
                            "implementation",
                            cycle_based=True,
                            subphases=["red", "green", "refactor"],
                            commit_type_map={
                                "red": "test",
                                "green": "feat",
                                "refactor": "refactor",
                            },
                        ),
                        _wpe("validation"),
                        _wpe("documentation"),
                        _wpe("ready"),
                    ]
                )
            },
        )
        assert loader.load_contracts_config() == expected

    def test_docs_workflow_roundtrip(self, config_dir: Path) -> None:
        loader = _make_loader_with_workflows(
            config_dir,
            {
                "docs": {
                    "phases": [
                        {"name": "planning"},
                        {"name": "documentation"},
                        {"name": "ready"},
                    ]
                }
            },
        )
        expected = ContractsConfig(
            merge_policy=_policy(),
            workflows={
                "docs": WorkflowEntry(
                    phases=[
                        _wpe("planning"),
                        _wpe("documentation"),
                        _wpe("ready"),
                    ]
                )
            },
        )
        assert loader.load_contracts_config() == expected

    def test_epic_workflow_roundtrip(self, config_dir: Path) -> None:
        loader = _make_loader_with_workflows(
            config_dir,
            {
                "epic": {
                    "phases": [
                        {"name": "research"},
                        {"name": "planning"},
                        {"name": "design"},
                        {"name": "coordination"},
                        {"name": "documentation"},
                        {"name": "ready"},
                    ]
                }
            },
        )
        expected = ContractsConfig(
            merge_policy=_policy(),
            workflows={
                "epic": WorkflowEntry(
                    phases=[
                        _wpe("research"),
                        _wpe("planning"),
                        _wpe("design"),
                        _wpe("coordination"),
                        _wpe("documentation"),
                        _wpe("ready"),
                    ]
                )
            },
        )
        assert loader.load_contracts_config() == expected

    def test_real_epic_workflow_uses_coordination_scoped_sub_roles(self) -> None:
        """Real contracts.yaml: epic workflow uses @co-scoped sub-role names."""
        real = Path(__file__).parents[4] / get_default_server_root() / "config" / "contracts.yaml"
        if not real.exists():
            pytest.skip("contracts.yaml not yet created — passes after C2 GREEN")

        result = ConfigLoader(real.parent).load_contracts_config()
        epic = result.workflows["epic"]

        assert [phase.instructions.sub_role for phase in epic.phases] == [
            "epic-researcher",
            "epic-planner",
            "epic-designer",
            "epic-coordinator",
            "epic-documenter",
            "epic-releaser",
        ]

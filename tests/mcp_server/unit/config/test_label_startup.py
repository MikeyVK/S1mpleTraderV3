# tests/mcp_server/unit/config/test_label_startup.py
"""
Unit tests for ConfigValidator and label_startup removal.

Tests fail-fast cross-config validation paths for startup configuration and
verifies that the legacy label_startup module remains removed.

@layer: Tests (Unit)
@dependencies: [pytest, importlib.util, mcp_server.config.validator]
"""

from __future__ import annotations

import importlib.util

import pytest

from mcp_server.config.validator import ConfigValidator
from mcp_server.core.exceptions import ConfigError
from mcp_server.schemas import (
    ArtifactRegistryConfig,
    OperationPoliciesConfig,
    PhaseContractsConfig,
    ProjectStructureConfig,
    WorkflowConfig,
    WorkphasesConfig,
)


class TestConfigValidator:
    @pytest.fixture
    def validator(self) -> ConfigValidator:
        return ConfigValidator()

    @pytest.fixture
    def operation_policies(self) -> OperationPoliciesConfig:
        return OperationPoliciesConfig(
            operations={
                "create_file": {
                    "operation_id": "create_file",
                    "description": "Create file",
                    "allowed_phases": ["planning"],
                    "blocked_patterns": [],
                    "allowed_extensions": [".py"],
                    "require_tdd_prefix": False,
                    "allowed_prefixes": [],
                }
            }
        )

    @pytest.fixture
    def workflow_config(self) -> WorkflowConfig:
        return WorkflowConfig(
            version="1.0",
            workflows={
                "feature": {
                    "name": "feature",
                    "phases": ["research", "planning", "implementation"],
                    "default_execution_mode": "interactive",
                    "description": "Feature workflow",
                }
            },
        )

    @pytest.fixture
    def project_structure(self) -> ProjectStructureConfig:
        return ProjectStructureConfig(
            directories={
                "src": {
                    "path": "src",
                    "parent": None,
                    "description": "Source",
                    "allowed_artifact_types": ["dto"],
                    "allowed_extensions": [".py"],
                    "require_scaffold_for": [],
                }
            }
        )

    @pytest.fixture
    def artifact_registry(self) -> ArtifactRegistryConfig:
        return ArtifactRegistryConfig(
            version="1.0",
            artifact_types=[
                {
                    "type": "code",
                    "type_id": "dto",
                    "name": "DTO",
                    "description": "Data transfer object",
                    "file_extension": ".py",
                    "required_fields": ["name"],
                    "optional_fields": [],
                    "state_machine": {
                        "states": ["CREATED"],
                        "initial_state": "CREATED",
                        "valid_transitions": [],
                    },
                }
            ],
        )

    @pytest.fixture
    def workphases_config(self) -> WorkphasesConfig:
        return WorkphasesConfig(
            version="1.0",
            phases={
                "research": {"display_name": "Research"},
                "planning": {"display_name": "Planning"},
                "implementation": {"display_name": "Implementation"},
                "ready": {"display_name": "Ready", "terminal": True},
            },
        )

    @pytest.fixture
    def phase_contracts(self) -> PhaseContractsConfig:
        return PhaseContractsConfig(
            merge_policy={"pr_allowed_phase": "ready", "branch_local_artifacts": []},
            workflows={
                "feature": {
                    "implementation": {
                        "subphases": ["red", "green"],
                        "commit_type_map": {"red": "test", "green": "feat"},
                        "cycle_based": True,
                        "exit_requires": [],
                        "cycle_exit_requires": {},
                    }
                }
            }
        )

    def test_label_startup_deleted(self) -> None:
        assert importlib.util.find_spec("mcp_server.config.label_startup") is None

    def test_config_validator_exists(self) -> None:
        assert callable(getattr(ConfigValidator, "validate_startup", None))

    def test_validate_startup_accepts_valid_config(
        self,
        validator: ConfigValidator,
        operation_policies: OperationPoliciesConfig,
        workflow_config: WorkflowConfig,
        project_structure: ProjectStructureConfig,
        artifact_registry: ArtifactRegistryConfig,
        phase_contracts: PhaseContractsConfig,
        workphases_config: WorkphasesConfig,
    ) -> None:
        validator.validate_startup(
            policies=operation_policies,
            workflow=workflow_config,
            structure=project_structure,
            artifact=artifact_registry,
            phase_contracts=phase_contracts,
            workphases=workphases_config,
        )

    def test_validate_startup_raises_on_unknown_workflow_phase(
        self,
        validator: ConfigValidator,
        operation_policies: OperationPoliciesConfig,
        project_structure: ProjectStructureConfig,
        artifact_registry: ArtifactRegistryConfig,
        workphases_config: WorkphasesConfig,
    ) -> None:
        workflow_config = WorkflowConfig(
            version="1.0",
            workflows={
                "feature": {
                    "name": "feature",
                    "phases": ["research", "validation"],
                    "default_execution_mode": "interactive",
                    "description": "Feature workflow",
                }
            },
        )
        phase_contracts = PhaseContractsConfig(
            merge_policy={"pr_allowed_phase": "ready", "branch_local_artifacts": []},
            workflows={},
        )

        with pytest.raises(ConfigError, match="Workflow 'feature' references unknown phases"):
            validator.validate_startup(
                policies=operation_policies,
                workflow=workflow_config,
                structure=project_structure,
                artifact=artifact_registry,
                phase_contracts=phase_contracts,
                workphases=workphases_config,
            )

    def test_validate_startup_raises_on_unknown_phase_contract_workflow(
        self,
        validator: ConfigValidator,
        operation_policies: OperationPoliciesConfig,
        workflow_config: WorkflowConfig,
        project_structure: ProjectStructureConfig,
        artifact_registry: ArtifactRegistryConfig,
        workphases_config: WorkphasesConfig,
    ) -> None:
        phase_contracts = PhaseContractsConfig(
            merge_policy={"pr_allowed_phase": "ready", "branch_local_artifacts": []},
            workflows={
                "bug": {
                    "implementation": {
                        "subphases": ["red"],
                        "commit_type_map": {"red": "test"},
                        "cycle_based": True,
                        "exit_requires": [],
                        "cycle_exit_requires": {},
                    }
                }
            }
        )

        with pytest.raises(ConfigError, match="unknown workflow"):
            validator.validate_startup(
                policies=operation_policies,
                workflow=workflow_config,
                structure=project_structure,
                artifact=artifact_registry,
                phase_contracts=phase_contracts,
                workphases=workphases_config,
            )

    def test_validate_startup_raises_on_unknown_phase_contract_phase(
        self,
        validator: ConfigValidator,
        operation_policies: OperationPoliciesConfig,
        workflow_config: WorkflowConfig,
        project_structure: ProjectStructureConfig,
        artifact_registry: ArtifactRegistryConfig,
        workphases_config: WorkphasesConfig,
    ) -> None:
        phase_contracts = PhaseContractsConfig(
            merge_policy={"pr_allowed_phase": "ready", "branch_local_artifacts": []},
            workflows={
                "feature": {
                    "validation": {
                        "subphases": ["red"],
                        "commit_type_map": {"red": "test"},
                        "cycle_based": True,
                        "exit_requires": [],
                        "cycle_exit_requires": {},
                    }
                }
            }
        )

        with pytest.raises(ConfigError, match="unknown phases"):
            validator.validate_startup(
                policies=operation_policies,
                workflow=workflow_config,
                structure=project_structure,
                artifact=artifact_registry,
                phase_contracts=phase_contracts,
                workphases=workphases_config,
            )

    def test_validate_startup_raises_when_phase_missing_from_workphases(
        self,
        validator: ConfigValidator,
        operation_policies: OperationPoliciesConfig,
        project_structure: ProjectStructureConfig,
        artifact_registry: ArtifactRegistryConfig,
    ) -> None:
        workflow_config = WorkflowConfig(
            version="1.0",
            workflows={
                "feature": {
                    "name": "feature",
                    "phases": ["research", "validation"],
                    "default_execution_mode": "interactive",
                    "description": "Feature workflow",
                }
            },
        )
        phase_contracts = PhaseContractsConfig(
            merge_policy={"pr_allowed_phase": "ready", "branch_local_artifacts": []},
            workflows={
                "feature": {
                    "validation": {
                        "subphases": ["red"],
                        "commit_type_map": {"red": "test"},
                        "cycle_based": True,
                        "exit_requires": [],
                        "cycle_exit_requires": {},
                    }
                }
            }
        )
        workphases_config = WorkphasesConfig(
            version="1.0",
            phases={
                "research": {"display_name": "Research"},
                "ready": {"display_name": "Ready", "terminal": True},
            },
        )

        with pytest.raises(ConfigError, match="missing from workphases"):
            validator.validate_startup(
                policies=operation_policies,
                workflow=workflow_config,
                structure=project_structure,
                artifact=artifact_registry,
                phase_contracts=phase_contracts,
                workphases=workphases_config,
            )

    def test_validate_startup_raises_on_unknown_policy_phase(
        self,
        validator: ConfigValidator,
        workflow_config: WorkflowConfig,
        project_structure: ProjectStructureConfig,
        artifact_registry: ArtifactRegistryConfig,
        phase_contracts: PhaseContractsConfig,
        workphases_config: WorkphasesConfig,
    ) -> None:
        operation_policies = OperationPoliciesConfig(
            operations={
                "create_file": {
                    "operation_id": "create_file",
                    "description": "Create file",
                    "allowed_phases": ["validation"],
                    "blocked_patterns": [],
                    "allowed_extensions": [".py"],
                    "require_tdd_prefix": False,
                    "allowed_prefixes": [],
                }
            }
        )

        with pytest.raises(ConfigError, match="Operation 'create_file' references unknown phases"):
            validator.validate_startup(
                policies=operation_policies,
                workflow=workflow_config,
                structure=project_structure,
                artifact=artifact_registry,
                phase_contracts=phase_contracts,
                workphases=workphases_config,
            )

    def test_validate_startup_raises_on_unknown_project_structure_artifact(
        self,
        validator: ConfigValidator,
        operation_policies: OperationPoliciesConfig,
        workflow_config: WorkflowConfig,
        artifact_registry: ArtifactRegistryConfig,
        phase_contracts: PhaseContractsConfig,
        workphases_config: WorkphasesConfig,
    ) -> None:
        project_structure = ProjectStructureConfig(
            directories={
                "src": {
                    "path": "src",
                    "parent": None,
                    "description": "Source",
                    "allowed_artifact_types": ["worker"],
                    "allowed_extensions": [".py"],
                    "require_scaffold_for": [],
                }
            }
        )

        with pytest.raises(ConfigError, match="unknown artifact types"):
            validator.validate_startup(
                policies=operation_policies,
                workflow=workflow_config,
                structure=project_structure,
                artifact=artifact_registry,
                phase_contracts=phase_contracts,
                workphases=workphases_config,
            )

    def test_validate_startup_raises_on_unknown_project_structure_parent(
        self,
        validator: ConfigValidator,
        operation_policies: OperationPoliciesConfig,
        workflow_config: WorkflowConfig,
        project_structure: ProjectStructureConfig,
        artifact_registry: ArtifactRegistryConfig,
        phase_contracts: PhaseContractsConfig,
        workphases_config: WorkphasesConfig,
    ) -> None:
        project_structure.directories["tests"] = project_structure.directories["src"].model_copy(
            update={"path": "tests", "parent": "missing"}
        )

        with pytest.raises(ConfigError, match="unknown parent"):
            validator.validate_startup(
                policies=operation_policies,
                workflow=workflow_config,
                structure=project_structure,
                artifact=artifact_registry,
                phase_contracts=phase_contracts,
                workphases=workphases_config,
            )

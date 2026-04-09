# mcp_server/config/validator.py
"""
Startup cross-config validation for MCP server composition root.

Validates relationships between already loaded configuration value objects
before the MCP server starts accepting requests.

@layer: Backend (Config)
@dependencies: [mcp_server.core.exceptions, mcp_server.schemas]
@responsibilities:
    - Validate workflow phases against workphases metadata
    - Validate phase contracts against workflow and workphase definitions
    - Validate policy and project-structure references across config objects
"""

from __future__ import annotations

from mcp_server.core.exceptions import ConfigError
from mcp_server.schemas import (
    ArtifactRegistryConfig,
    OperationPoliciesConfig,
    PhaseContractsConfig,
    ProjectStructureConfig,
    WorkflowConfig,
    WorkphasesConfig,
)


class ConfigValidator:
    """Validate cross-config relationships after ConfigLoader has loaded schemas."""

    def validate_startup(
        self,
        policies: OperationPoliciesConfig,
        workflow: WorkflowConfig,
        structure: ProjectStructureConfig,
        artifact: ArtifactRegistryConfig,
        phase_contracts: PhaseContractsConfig,
        workphases: WorkphasesConfig,
    ) -> None:
        """Validate startup relationships across already loaded config objects."""
        known_workflows = set(workflow.workflows)
        known_phases = set(workphases.phases)
        known_artifact_types = set(artifact.list_type_ids())

        self._validate_phase_contracts(
            workflow=workflow,
            phase_contracts=phase_contracts,
            known_workflows=known_workflows,
            known_phases=known_phases,
        )
        self._validate_workflow_phases(workflow=workflow, known_phases=known_phases)
        self._validate_operation_policies(policies=policies, known_phases=known_phases)
        self._validate_project_structure(
            structure=structure,
            known_artifact_types=known_artifact_types,
        )
        self._validate_merge_policy_phase(
            phase_contracts=phase_contracts,
            known_phases=known_phases,
        )

    def _validate_workflow_phases(
        self,
        workflow: WorkflowConfig,
        known_phases: set[str],
    ) -> None:
        for workflow_name, workflow_template in workflow.workflows.items():
            unknown_workflow_phases = set(workflow_template.phases) - known_phases
            if unknown_workflow_phases:
                raise ConfigError(
                    f"Workflow '{workflow_name}' references unknown phases: "
                    f"{sorted(unknown_workflow_phases)}"
                )

    def _validate_phase_contracts(
        self,
        workflow: WorkflowConfig,
        phase_contracts: PhaseContractsConfig,
        known_workflows: set[str],
        known_phases: set[str],
    ) -> None:
        for workflow_name, phase_map in phase_contracts.workflows.items():
            if workflow_name not in known_workflows:
                raise ConfigError(f"phase_contracts references unknown workflow: '{workflow_name}'")

            workflow_phases = set(workflow.get_workflow(workflow_name).phases)
            unknown_contract_phases = set(phase_map) - workflow_phases
            if unknown_contract_phases:
                raise ConfigError(
                    "phase_contracts for workflow "
                    f"'{workflow_name}' reference unknown phases: "
                    f"{sorted(unknown_contract_phases)}"
                )

            for phase_name in phase_map:
                if phase_name not in known_phases:
                    raise ConfigError(
                        "phase_contracts reference phase "
                        f"'{phase_name}' that is missing from workphases.yaml"
                    )

    def _validate_operation_policies(
        self,
        policies: OperationPoliciesConfig,
        known_phases: set[str],
    ) -> None:
        for operation_id, policy in policies.operations.items():
            unknown_policy_phases = set(policy.allowed_phases) - known_phases
            if unknown_policy_phases:
                raise ConfigError(
                    f"Operation '{operation_id}' references unknown phases: "
                    f"{sorted(unknown_policy_phases)}"
                )

    def _validate_project_structure(
        self,
        structure: ProjectStructureConfig,
        known_artifact_types: set[str],
    ) -> None:
        known_directories = set(structure.directories)

        for directory_path, policy in structure.directories.items():
            unknown_artifact_types = set(policy.allowed_artifact_types) - known_artifact_types
            if unknown_artifact_types:
                raise ConfigError(
                    f"Directory '{directory_path}' references unknown artifact types: "
                    f"{sorted(unknown_artifact_types)}"
                )

            if policy.parent is not None and policy.parent not in known_directories:
                raise ConfigError(
                    f"Directory '{directory_path}' references unknown parent: '{policy.parent}'"
                )

    def _validate_merge_policy_phase(
        self,
        phase_contracts: PhaseContractsConfig,
        known_phases: set[str],
    ) -> None:
        pr_phase = phase_contracts.merge_policy.pr_allowed_phase
        if pr_phase not in known_phases:
            raise ConfigError(
                f"merge_policy.pr_allowed_phase '{pr_phase}' is not a known workphase. "
                f"Known phases: {sorted(known_phases)}"
            )

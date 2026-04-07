"""Pure config schema package for C_LOADER migration."""

from mcp_server.config.schemas.artifact_registry_config import (
    ArtifactDefinition,
    ArtifactRegistryConfig,
    ArtifactType,
    StateMachine,
    StateMachineTransition,
)
from mcp_server.config.schemas.contributor_config import ContributorConfig, ContributorEntry
from mcp_server.config.schemas.enforcement_config import (
    EnforcementAction,
    EnforcementConfig,
    EnforcementRule,
)
from mcp_server.config.schemas.git_config import GitConfig
from mcp_server.config.schemas.issue_config import IssueConfig, IssueTypeEntry
from mcp_server.config.schemas.label_config import Label, LabelConfig, LabelPattern
from mcp_server.config.schemas.milestone_config import MilestoneConfig, MilestoneEntry
from mcp_server.config.schemas.operation_policies_config import (
    OperationPoliciesConfig,
    OperationPolicy,
)
from mcp_server.config.schemas.phase_contracts_config import (
    CheckSpec,
    PhaseContractPhase,
    PhaseContractsConfig,
)
from mcp_server.config.schemas.project_structure_config import (
    DirectoryPolicy,
    ProjectStructureConfig,
)
from mcp_server.config.schemas.quality_config import (
    ArtifactLoggingConfig,
    CapabilitiesMetadata,
    ExecutionConfig,
    GateScope,
    JsonViolationsParsing,
    QualityConfig,
    QualityGate,
    SuccessCriteria,
    TextViolationsParsing,
    ViolationDTO,
)
from mcp_server.config.schemas.scaffold_metadata_config import (
    CommentPattern,
    MetadataField,
    ScaffoldMetadataConfig,
)
from mcp_server.config.schemas.scope_config import ScopeConfig
from mcp_server.config.schemas.workflows import WorkflowConfig, WorkflowTemplate
from mcp_server.config.schemas.workphases import PhaseDefinition, WorkphasesConfig

__all__ = [
    "ArtifactDefinition",
    "ArtifactLoggingConfig",
    "ArtifactRegistryConfig",
    "ArtifactType",
    "CapabilitiesMetadata",
    "CheckSpec",
    "CommentPattern",
    "ContributorConfig",
    "ContributorEntry",
    "DirectoryPolicy",
    "EnforcementAction",
    "EnforcementConfig",
    "EnforcementRule",
    "ExecutionConfig",
    "GateScope",
    "GitConfig",
    "IssueConfig",
    "IssueTypeEntry",
    "JsonViolationsParsing",
    "Label",
    "LabelConfig",
    "LabelPattern",
    "MetadataField",
    "MilestoneConfig",
    "MilestoneEntry",
    "OperationPoliciesConfig",
    "OperationPolicy",
    "PhaseContractPhase",
    "PhaseContractsConfig",
    "PhaseDefinition",
    "ProjectStructureConfig",
    "QualityConfig",
    "QualityGate",
    "ScaffoldMetadataConfig",
    "ScopeConfig",
    "StateMachine",
    "StateMachineTransition",
    "SuccessCriteria",
    "TextViolationsParsing",
    "ViolationDTO",
    "WorkflowConfig",
    "WorkflowTemplate",
    "WorkphasesConfig",
]

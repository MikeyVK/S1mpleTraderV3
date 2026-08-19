# mcp_server/schemas/__init__.py
"""MCP Server validation schemas for artifact scaffolding.

Two-Schema Pattern:
- Context: User-facing schemas (no lifecycle fields)
- RenderContext: System-enriched schemas (Context + LifecycleMixin)

Infrastructure:
- LifecycleMixin: System-managed fields (output_path, scaffold_created, template_id, version_hash)
- BaseContext: Abstract base for all Context schemas
- BaseRenderContext: Abstract base for all RenderContext schemas
"""

from mcp_server.config.schemas.artifact_registry_config import (
    ArtifactDefinition,
    ArtifactRegistryConfig,
    SchemaFieldDef,
)
from mcp_server.config.schemas.contracts_config import (
    BranchLocalArtifact,
    CheckSpec,
    ContractsConfig,
    MergePolicy,
    WorkflowEntry,
    WorkflowPhaseEntry,
)
from mcp_server.config.schemas.contributor_config import ContributorConfig, ContributorEntry
from mcp_server.config.schemas.enforcement_config import (
    EnforcementAction,
    EnforcementConfig,
    EnforcementRule,
)
from mcp_server.config.schemas.git_config import GitConfig
from mcp_server.config.schemas.issue_config import IssueConfig
from mcp_server.config.schemas.label_config import LabelConfig
from mcp_server.config.schemas.milestone_config import MilestoneConfig
from mcp_server.config.schemas.operation_policies_config import OperationPoliciesConfig
from mcp_server.config.schemas.project_structure_config import ProjectStructureConfig
from mcp_server.config.schemas.quality_config import (
    JsonViolationsParsing,
    QualityConfig,
    QualityGate,
    TextViolationsParsing,
    ViolationDTO,
)
from mcp_server.config.schemas.scaffold_metadata_config import (
    CommentPattern,
    MetadataField,
    ScaffoldMetadataConfig,
)
from mcp_server.config.schemas.scope_config import ScopeConfig
from mcp_server.config.schemas.workflows import WorkflowConfig
from mcp_server.config.schemas.workphases import WorkphasesConfig
from mcp_server.schemas.base import BaseContext, BaseRenderContext
from mcp_server.schemas.error_outputs import (
    CacheErrorOutput,
    EnforcementErrorOutput,
    ExecutionErrorOutput,
    ToolErrorOutput,
    ValidationErrorOutput,
)
from mcp_server.schemas.mixins.lifecycle import LifecycleMixin
from mcp_server.schemas.tool_outputs import BaseToolOutput

__all__ = [
    # Infrastructure
    "LifecycleMixin",
    "BaseContext",
    "BaseRenderContext",
    "BaseToolOutput",
    "ToolErrorOutput",
    "ValidationErrorOutput",
    "ExecutionErrorOutput",
    "CacheErrorOutput",
    "EnforcementErrorOutput",
    # Config schemas and value objects
    "ArtifactRegistryConfig",
    "ArtifactDefinition",
    "SchemaFieldDef",
    "BranchLocalArtifact",
    "CheckSpec",
    "CommentPattern",
    "ContractsConfig",
    "ContributorConfig",
    "ContributorEntry",
    "EnforcementAction",
    "EnforcementConfig",
    "EnforcementRule",
    "GitConfig",
    "IssueConfig",
    "JsonViolationsParsing",
    "LabelConfig",
    "MergePolicy",
    "MetadataField",
    "MilestoneConfig",
    "OperationPoliciesConfig",
    "ProjectStructureConfig",
    "QualityConfig",
    "QualityGate",
    "ScaffoldMetadataConfig",
    "ScopeConfig",
    "TextViolationsParsing",
    "ViolationDTO",
    "WorkflowConfig",
    "WorkflowEntry",
    "WorkflowPhaseEntry",
    "WorkphasesConfig",
]

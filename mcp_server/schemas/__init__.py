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

from mcp_server.config.schemas.artifact_registry_config import ArtifactRegistryConfig
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
from mcp_server.config.schemas.scope_config import ScopeConfig
from mcp_server.config.schemas.phase_contracts_config import CheckSpec, PhaseContractsConfig
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
from mcp_server.config.schemas.workflows import WorkflowConfig
from mcp_server.config.schemas.workphases import WorkphasesConfig
from mcp_server.schemas.base import BaseContext, BaseRenderContext
from mcp_server.schemas.contexts.architecture import ArchitectureContext
from mcp_server.schemas.contexts.commit import CommitContext
from mcp_server.schemas.contexts.design import DesignContext
from mcp_server.schemas.contexts.doc_base import DocArtifactContext
from mcp_server.schemas.contexts.dto import DTOContext
from mcp_server.schemas.contexts.generic import GenericContext
from mcp_server.schemas.contexts.integration_test import IntegrationTestContext
from mcp_server.schemas.contexts.issue import IssueContext
from mcp_server.schemas.contexts.planning import PlanningContext
from mcp_server.schemas.contexts.pr import PRContext
from mcp_server.schemas.contexts.reference import ReferenceContext
from mcp_server.schemas.contexts.research import ResearchContext
from mcp_server.schemas.contexts.schema import SchemaContext
from mcp_server.schemas.contexts.service import ServiceContext
from mcp_server.schemas.contexts.titled_base import TitledArtifactContext
from mcp_server.schemas.contexts.tool import ToolContext
from mcp_server.schemas.contexts.unit_test import UnitTestContext
from mcp_server.schemas.contexts.worker import WorkerContext
from mcp_server.schemas.mixins.lifecycle import LifecycleMixin
from mcp_server.schemas.render_contexts.architecture import ArchitectureRenderContext
from mcp_server.schemas.render_contexts.commit import CommitRenderContext
from mcp_server.schemas.render_contexts.design import DesignRenderContext
from mcp_server.schemas.render_contexts.dto import DTORenderContext
from mcp_server.schemas.render_contexts.generic import GenericRenderContext
from mcp_server.schemas.render_contexts.integration_test import IntegrationTestRenderContext
from mcp_server.schemas.render_contexts.issue import IssueRenderContext
from mcp_server.schemas.render_contexts.planning import PlanningRenderContext
from mcp_server.schemas.render_contexts.pr import PRRenderContext
from mcp_server.schemas.render_contexts.reference import ReferenceRenderContext
from mcp_server.schemas.render_contexts.research import ResearchRenderContext
from mcp_server.schemas.render_contexts.schema import SchemaRenderContext
from mcp_server.schemas.render_contexts.service import ServiceRenderContext
from mcp_server.schemas.render_contexts.tool import ToolRenderContext
from mcp_server.schemas.render_contexts.unit_test import UnitTestRenderContext
from mcp_server.schemas.render_contexts.worker import WorkerRenderContext

__all__ = [
    # Infrastructure
    "LifecycleMixin",
    "BaseContext",
    "BaseRenderContext",
    # Context schemas (user-facing)
    "ArchitectureContext",
    "CommitContext",
    "DesignContext",
    "DocArtifactContext",
    "DTOContext",
    "GenericContext",
    "IntegrationTestContext",
    "IssueContext",
    "PlanningContext",
    "PRContext",
    "ReferenceContext",
    "ResearchContext",
    "SchemaContext",
    "ServiceContext",
    "TitledArtifactContext",
    "ToolContext",
    "UnitTestContext",
    "WorkerContext",
    # RenderContext schemas (system-enriched)
    "ArchitectureRenderContext",
    "CommitRenderContext",
    "DesignRenderContext",
    "DTORenderContext",
    "GenericRenderContext",
    "IntegrationTestRenderContext",
    "IssueRenderContext",
    "PlanningRenderContext",
    "PRRenderContext",
    "ReferenceRenderContext",
    "ResearchRenderContext",
    "SchemaRenderContext",
    "ServiceRenderContext",
    "ToolRenderContext",
    "UnitTestRenderContext",
    "WorkerRenderContext",
    # Config schemas and value objects
    "ArtifactRegistryConfig",
    "CheckSpec",
    "CommentPattern",
    "ContributorConfig",
    "ContributorEntry",
    "EnforcementAction",
    "EnforcementConfig",
    "EnforcementRule",
    "GitConfig",
    "IssueConfig",
    "JsonViolationsParsing",
    "LabelConfig",
    "MetadataField",
    "MilestoneConfig",
    "OperationPoliciesConfig",
    "PhaseContractsConfig",
    "ProjectStructureConfig",
    "QualityConfig",
    "QualityGate",
    "ScaffoldMetadataConfig",
    "ScopeConfig",
    "TextViolationsParsing",
    "ViolationDTO",
    "WorkflowConfig",
    "WorkphasesConfig",
]

# mcp_server/schemas/contexts/__init__.py
"""Context schemas for MCP artifact scaffolding (user-facing)."""

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

__all__ = [
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
]

# mcp_server/schemas/render_contexts/__init__.py
"""RenderContext schemas for MCP artifact templates (system-enriched)."""

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
]

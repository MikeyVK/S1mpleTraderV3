# mcp_server/schemas/contexts/doc_base.py
# template=schema version=74378193 created=2026-02-18T00:00Z updated=
"""DocArtifactContext base schema for document artifact types.

Common base for all document artifact context schemas: research, planning,
design, architecture, reference. Inherits title field + validator from
TitledArtifactContext, eliminating duplication.

@layer: MCP Server (Schema Infrastructure)
"""

# Third-party
from pydantic import ConfigDict

# Project modules
from mcp_server.schemas.contexts.titled_base import TitledArtifactContext


class DocArtifactContext(TitledArtifactContext):
    """Base context class for all document artifact types.

    Inherits `title` field and `validate_title_not_empty` from
    TitledArtifactContext. Document subclasses (research, planning, design,
    architecture, reference) extend this class.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

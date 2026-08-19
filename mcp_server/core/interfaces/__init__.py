# mcp_server\core\interfaces\__init__.py
# template=generic version=f35abd82 created=2026-03-12T15:02Z updated=
"""Protocol interfaces for workflow state, gate orchestration, PR status, and test execution."""

from __future__ import annotations

from mcp_server.core.interfaces.icore_tool import ICoreTool as ICoreTool
from mcp_server.core.interfaces.itool import ITool as ITool
from mcp_server.core.interfaces.ipresenter import (
    IPresenter as IPresenter,
    IResourcePresenter as IResourcePresenter,
    ITextPresenter as ITextPresenter,
)
from mcp_server.core.interfaces.itool_response_cache import (
    IToolResponsePublisher as IToolResponsePublisher,
    IToolResponseReader as IToolResponseReader,
)
from mcp_server.core.interfaces.gate import (
    GateReport as GateReport,
    GateViolation as GateViolation,
    IWorkflowGateRunner as IWorkflowGateRunner,
)
from mcp_server.core.interfaces.state import (
    IStateReader as IStateReader,
    IStateRepository as IStateRepository,
)
from mcp_server.core.interfaces.ipr_status import (
    PRStatus as PRStatus,
    IPRStatusReader as IPRStatusReader,
    IPRStatusWriter as IPRStatusWriter,
)
from mcp_server.core.interfaces.ipytest_runner import (
    IPytestRunner as IPytestRunner,
)
from mcp_server.core.interfaces.git import (
    IGitContextReader as IGitContextReader,
    IBranchParentReader as IBranchParentReader,
)
from mcp_server.core.interfaces.quality import (
    IQualityStateRepository as IQualityStateRepository,
)
from mcp_server.core.interfaces.workflow import (
    IWorkflowStateMutator as IWorkflowStateMutator,
)
from mcp_server.core.interfaces.context import (
    IContextLoadedReader as IContextLoadedReader,
    IContextLoadedWriter as IContextLoadedWriter,
)
from mcp_server.core.interfaces.file_writer import (
    IAtomicFileWriter as IAtomicFileWriter,
)

# c:\temp\pgmcp\tests\mcp_server\unit\core\interfaces\test_interface_imports.py
# template=unit_test version=3d15d309 created=2026-06-20T18:24Z updated=
"""
Unit tests for mcp_server.core.interfaces.gate.

None

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.core.interfaces.gate, unittest.mock]
@responsibilities:
    - Test TestInterfaceImports functionality
    - Verify None
    - None
"""

# No external mocks/dependencies needed for import verification
# Project modules
from mcp_server.core.interfaces.context import IContextLoadedReader, IContextLoadedWriter
from mcp_server.core.interfaces.gate import GateReport, GateViolation, IWorkflowGateRunner
from mcp_server.core.interfaces.git import IBranchParentReader, IGitContextReader
from mcp_server.core.interfaces.ipr_status import IPRStatusReader, IPRStatusWriter, PRStatus
from mcp_server.core.interfaces.ipytest_runner import IPytestRunner
from mcp_server.core.interfaces.quality import IQualityStateRepository
from mcp_server.core.interfaces.state import IStateReader, IStateRepository
from mcp_server.core.interfaces.workflow import IWorkflowStateMutator


class TestInterfaceImports:
    """Test suite for gate."""

    def test_imports(self):
        """Verify that all interfaces and types can be imported from their sub-modules."""
        assert GateReport is not None
        assert GateViolation is not None
        assert IWorkflowGateRunner is not None
        assert IStateReader is not None
        assert IStateRepository is not None
        assert PRStatus is not None
        assert IPRStatusReader is not None
        assert IPRStatusWriter is not None
        assert IPytestRunner is not None
        assert IGitContextReader is not None
        assert IBranchParentReader is not None
        assert IQualityStateRepository is not None
        assert IWorkflowStateMutator is not None
        assert IContextLoadedReader is not None
        assert IContextLoadedWriter is not None

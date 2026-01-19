"""Integration tests for MCP server tool registration.

Tests verify that the correct tools are registered in the server
and that legacy tools have been properly removed.
"""

from mcp_server.server import MCPServer


def test_scaffold_artifact_tool_registered():
    """Verify ScaffoldArtifactTool is registered in server tools list."""
    server = MCPServer()
    tool_names = [type(t).__name__ for t in server.tools]
    assert 'ScaffoldArtifactTool' in tool_names, \
        f"ScaffoldArtifactTool not found in {tool_names}"


def test_legacy_scaffold_tools_not_registered():
    """Verify legacy scaffold tools are NOT registered."""
    server = MCPServer()
    tool_names = [type(t).__name__ for t in server.tools]
    assert 'ScaffoldComponentTool' not in tool_names, \
        "Legacy ScaffoldComponentTool should not be registered"
    assert 'ScaffoldDesignDocTool' not in tool_names, \
        "Legacy ScaffoldDesignDocTool should not be registered"


def test_scaffold_artifact_tool_has_correct_name():
    """Verify tool name matches expected MCP tool name."""
    server = MCPServer()
    scaffold_tools = [t for t in server.tools if type(t).__name__ == 'ScaffoldArtifactTool']
    assert len(scaffold_tools) == 1, "Expected exactly one ScaffoldArtifactTool"
    tool = scaffold_tools[0]
    assert tool.name == 'scaffold_artifact', \
        f"Expected name 'scaffold_artifact', got '{tool.name}'"

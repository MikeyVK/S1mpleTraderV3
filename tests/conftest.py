"""
@module: tests.conftest
@layer: Test Infrastructure
@dependencies: pytest
@responsibilities:
  - Register root-level pytest plugins for the full test tree
  - Host only top-level cross-suite pytest configuration
"""

pytest_plugins = [
    "tests.mcp_server.fixtures.artifact_test_harness",
    "tests.mcp_server.fixtures.workflow_fixtures",
]

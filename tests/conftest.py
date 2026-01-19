"""
@module: tests.conftest
@layer: Test Infrastructure
@dependencies: pytest
@responsibilities:
  - Import shared fixtures for pytest discovery
"""

# Import fixtures from fixture modules
pytest_plugins = [
    "tests.fixtures.artifact_test_harness",
    "tests.fixtures.workflow_fixtures",
]

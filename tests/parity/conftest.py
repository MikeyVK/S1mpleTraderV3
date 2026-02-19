# tests/parity/conftest.py
# template=generic version=f35abd82 created=2026-02-17T08:22Z updated=
"""ParityTestFixtures module.

Pytest fixtures for parity testing

@layer: Test Infrastructure
@dependencies: [None]
@responsibilities:
    - Provide sample Python output from v1 templates
    - Provide sample Markdown output from v1 templates
    - Standardize test data across parity test suite
"""

# Third-party
import pytest

# Project modules


@pytest.fixture
def sample_python_output() -> str:
    """V1 template output sample for Python file.

    Returns:
        Expected Python file output from v1 dto.py template
    """
    return '''
# backend/dtos/example.py
# template=dto version=abc123 created=2026-01-15T10:30:00Z updated=
"""ExampleDTO module.

Data transfer object for example

@layer: DTOs
@dependencies: [pydantic]
@responsibilities:
    - Define example data structure
    - Validate example inputs
"""

# Standard library
import logging

# Third-party
from pydantic import BaseModel, Field

# Project modules


logger = logging.getLogger(__name__)

class ExampleDTO(BaseModel):
    """Data transfer object for example."""

    id: int = Field(..., description="Example ID")
    name: str = Field(..., description="Example name")
'''.strip()


@pytest.fixture
def sample_markdown_output() -> str:
    """V1 template output sample for Markdown file.

    Returns:
        Expected Markdown output from v1 research.md template
    """
    return """
# Research: Example Topic

**Last Updated:** 2026-01-15T10:30:00Z
**Status:** DRAFT
**Related Issues:** #42

## Purpose

Investigate example topic for implementation.

## Background

Context and motivation for research.

## Research Questions

1. Question 1
2. Question 2

## Findings

### Finding 1

Detailed analysis.

## Recommendations

- Recommendation 1
- Recommendation 2
""".strip()

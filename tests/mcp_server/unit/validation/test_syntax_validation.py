# tests/unit/validation/test_validation_service.py
"""
Unit tests for ValidationService validation policy.

Tests verify:
- Code artifacts: Syntax validation (BLOCK on errors)
- Doc artifacts: H1 title validation (WARN policy)

@layer: Tests (Unit)
@test_type: Unit
"""

from mcp_server.validation.base import ValidationIssue
from mcp_server.validation.validation_service import ValidationService


def test_validate_syntax_python_valid() -> None:
    """GIVEN: Valid Python code, WHEN: validate_syntax(.py), THEN: passed=True."""
    service = ValidationService()

    valid_python = """
from pydantic import BaseModel

class TestDTO(BaseModel):
    name: str
"""
    passed, issues = service.validate_syntax("test.py", valid_python)

    assert passed is True
    assert issues == ()


def test_validate_syntax_python_invalid() -> None:
    """GIVEN: Invalid Python syntax, WHEN: validate_syntax(.py), THEN: passed=False."""
    service = ValidationService()

    invalid_python = """
class TestDTO:
    def __init__(self
        # Missing closing parenthesis
"""
    passed, issues = service.validate_syntax("test.py", invalid_python)

    assert passed is False
    assert issues == (
        ValidationIssue(
            message="Python syntax error: '(' was never closed",
            line=3,
            column=17,
            code="python_syntax_error",
        ),
    )


def test_validate_syntax_markdown_valid() -> None:
    """GIVEN: Markdown with H1, WHEN: validate_syntax(.md), THEN: passed=True."""
    service = ValidationService()

    valid_md = """# My Document

Some content here.
"""
    passed, issues = service.validate_syntax("test.md", valid_md)

    assert passed is True
    assert not issues


def test_validate_syntax_markdown_missing_h1() -> None:
    """GIVEN: Markdown without H1, WHEN: validate_syntax(.md), THEN: passed=False."""
    service = ValidationService()

    invalid_md = """## Subtitle Only

No H1 title!
"""
    passed, issues = service.validate_syntax("test.md", invalid_md)

    assert passed is False
    assert issues == (
        ValidationIssue(
            message="Markdown is missing an H1 title",
            code="markdown_missing_h1",
        ),
    )


def test_validate_syntax_unknown_filetype_passes() -> None:
    """GIVEN: Unknown filetype, WHEN: validate_syntax(), THEN: passed=True (no validation)."""
    service = ValidationService()

    content = "any content"
    passed, issues = service.validate_syntax("test.txt", content)

    assert passed is True
    assert not issues


def test_validate_content_returns_canonical_syntax_issue() -> None:
    """Code-artifact syntax failures remain structured at the service boundary."""
    service = ValidationService()

    passed, issues = service.validate_content("def broken(", "service")

    assert passed is False
    assert issues == (
        ValidationIssue(
            message="Python syntax error: '(' was never closed",
            line=1,
            column=11,
            code="python_syntax_error",
        ),
    )


def test_validate_content_non_code_passes_without_issues() -> None:
    """Non-code artifacts preserve the existing no-op validation policy."""
    service = ValidationService()

    passed, issues = service.validate_content("plain text", "reference")

    assert passed is True
    assert issues == ()

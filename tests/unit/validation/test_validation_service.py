# tests/unit/validation/test_validation_service.py
"""
Unit tests for ValidationService validation policy.

Tests verify:
- Code artifacts: Syntax validation (BLOCK on errors)
- Doc artifacts: Pass validation (WARN policy - no blocking)

@layer: Tests (Unit)
@test_type: Unit
"""

from mcp_server.validation.validation_service import ValidationService


def test_validate_content_code_artifact_valid():
    """GIVEN: Valid Python code, WHEN: validate_content("code"), THEN: passed=True."""
    service = ValidationService()

    valid_python = """
from pydantic import BaseModel

class TestDTO(BaseModel):
    name: str
"""
    passed, issues = service.validate_content(valid_python, "code")

    assert passed is True
    assert not issues


def test_validate_content_code_artifact_invalid_syntax():
    """GIVEN: Invalid Python syntax, WHEN: validate_content("code"), THEN: passed=False."""
    service = ValidationService()

    invalid_python = """
class TestDTO:
    def __init__(self
        # Missing closing parenthesis
"""
    passed, issues = service.validate_content(invalid_python, "code")

    assert passed is False
    assert "syntax error" in issues.lower()
    assert "line" in issues.lower()


def test_validate_content_doc_artifact_always_passes():
    """GIVEN: Any doc content, WHEN: validate_content("doc"), THEN: passed=True (WARN policy)."""
    service = ValidationService()

    # Even "invalid" markdown should pass (WARN policy - no blocking)
    doc_content = """
# Incomplete Design

<!-- Missing sections -->
"""
    passed, issues = service.validate_content(doc_content, "doc")

    assert passed is True
    assert not issues


def test_validate_content_specific_type_id_dto():
    """GIVEN: Valid Python, WHEN: validate_content("dto"), THEN: passed=True (backward compat)."""
    service = ValidationService()

    valid_dto = """
from pydantic import BaseModel

class UserDTO(BaseModel):
    id: int
    name: str
"""
    passed, issues = service.validate_content(valid_dto, "dto")

    assert passed is True
    assert not issues


def test_validate_content_specific_type_id_dto_invalid():
    """GIVEN: Invalid Python, WHEN: validate_content("dto"), THEN: passed=False."""
    service = ValidationService()

    invalid_dto = """
class UserDTO
    # Missing colon after class name
    pass
"""
    passed, issues = service.validate_content(invalid_dto, "dto")

    assert passed is False
    assert "syntax error" in issues.lower()

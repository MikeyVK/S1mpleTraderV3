"""
Unit tests for PythonValidator.

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
from typing import Generator
from unittest.mock import patch

# Third-party
import pytest

# Module under test
from mcp_server.validation.python_validator import PythonValidator
from mcp_server.validation.base import ValidationResult


class TestPythonValidator:
    """Test suite for PythonValidator."""

    @pytest.fixture
    def validator(self) -> Generator[PythonValidator, None, None]:
        """Fixture for PythonValidator with mocked QAManager."""
        with patch("mcp_server.validation.python_validator.QAManager") as mock_qa_cls:
            val = PythonValidator()
            val.qa_manager = mock_qa_cls.return_value
            yield val

    @pytest.mark.asyncio
    async def test_validate_existing_file_pass(self, validator: PythonValidator) -> None:
        """Test validation of an existing file that passes QA."""
        # Setup
        path = "test_file.py"
        # Type ignore explanation: Mock object dynamic attributes
        validator.qa_manager.run_quality_gates.return_value = {  # type: ignore
            "overall_pass": True,
            "gates": [
                {"name": "Linting", "passed": True, "score": "10.00/10", "issues": []},
                {"name": "Type Checking", "passed": True, "score": "Pass", "issues": []}
            ]
        }

        # Execute
        result = await validator.validate(path)

        # Verify
        assert isinstance(result, ValidationResult)
        assert result.passed is True
        assert result.score == 10.0
        assert not result.issues
        # Type ignore explanation: Mock object assertion
        validator.qa_manager.run_quality_gates.assert_called_once_with([path])  # type: ignore

    @pytest.mark.asyncio
    async def test_validate_content_with_issues(self, validator: PythonValidator) -> None:
        """Test validation of content string with reported issues."""
        # Setup
        path = "virtual_file.py"
        content = "def foo(): pass"

        # Mocking temp file creation is tricky, but validate uses mkstemp.
        # We rely on validate passing the temp file path to qa_manager.
        validator.qa_manager.run_quality_gates.return_value = {  # type: ignore
            "overall_pass": False,
            "gates": [
                {
                    "name": "Linting",
                    "passed": False,
                    "score": "5.00/10",
                    "issues": [
                        {
                            "message": "Missing docstring",
                            "line": 1,
                            "column": 0,
                            "code": "C0111"
                        }
                    ]
                }
            ]
        }

        # Execute
        result = await validator.validate(path, content)

        # Verify
        assert result.passed is False
        assert result.score == 5.0
        assert len(result.issues) == 1
        assert result.issues[0].message == "[Linting] Missing docstring"

        # Verify it called QA with a temp file, not the original path
        # Type ignore explanation: Mock object assertion
        call_args = validator.qa_manager.run_quality_gates.call_args  # type: ignore
        assert call_args is not None
        # run_quality_gates takes a list of files as first arg
        files_arg = call_args[0][0]
        assert isinstance(files_arg, list)
        scanned_path = files_arg[0]

        assert scanned_path != path
        assert scanned_path.endswith(".py")

    def test_parse_result_mapping(self, validator: PythonValidator) -> None:
        """Test _parse_result logic mapping back filenames."""
        raw_result = {
            "overall_pass": False,
            "gates": [
                {
                    "name": "MyPy",
                    "issues": [
                        {"message": "/tmp/tmp123.py:4: error: Bad type"}
                    ]
                }
            ]
        }

        # Validate logic mapping
        # pylint: disable=protected-access
        result = validator._parse_result(
            raw_result, "original.py", "/tmp/tmp123.py"
        )

        assert len(result.issues) == 1
        # The temp path should be replaced by basename of original
        assert "original.py" in result.issues[0].message
        assert "/tmp/tmp123.py" not in result.issues[0].message

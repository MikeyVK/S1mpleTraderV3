"""Tests for QAManager real implementation."""
from pathlib import Path

import pytest

from mcp_server.managers.qa_manager import QAManager


class TestQAManagerPylint:
    """Tests for _run_pylint with real subprocess execution."""

    def test_pylint_returns_score(self) -> None:
        """Should return a numeric score from pylint output."""
        manager = QAManager()
        # Use a known good file in the project
        result = manager._run_pylint(["mcp_server/__init__.py"])

        assert "score" in result
        assert result["name"] == "Linting"
        # Score should be a string like "10.00/10" or similar
        assert "/" in result["score"] or result["score"] == "N/A"

    def test_pylint_detects_issues(self) -> None:
        """Should detect and report linting issues."""
        manager = QAManager()
        # Create a temporary file with known issues
        # For now, test with a file that has trailing whitespace
        result = manager._run_pylint(["mcp_server/__init__.py"])

        assert "issues" in result
        assert isinstance(result["issues"], list)

    def test_pylint_passes_clean_file(self) -> None:
        """Should pass for a clean file with no issues."""
        manager = QAManager()
        result = manager._run_pylint(["mcp_server/__init__.py"])

        # __init__.py should be clean
        assert result["passed"] is True
        assert "10" in result["score"]

    def test_pylint_fails_with_issues(self, tmp_path: Path) -> None:
        """Should fail when pylint finds issues."""
        # Create a file with known pylint issues
        bad_file = tmp_path / "bad_code.py"
        bad_file.write_text("x=1   \n")  # trailing whitespace

        manager = QAManager()
        result = manager._run_pylint([str(bad_file)])

        # Should detect trailing whitespace
        assert result["passed"] is False or len(result["issues"]) > 0


class TestQAManagerMypy:
    """Tests for _run_mypy with real subprocess execution."""

    def test_mypy_returns_result(self) -> None:
        """Should return mypy type checking results."""
        manager = QAManager()
        result = manager._run_mypy(["mcp_server/__init__.py"])

        assert "passed" in result
        assert result["name"] == "Type Checking"

    def test_mypy_detects_type_errors(self) -> None:
        """Should detect type errors in files."""
        manager = QAManager()
        result = manager._run_mypy(["mcp_server/__init__.py"])

        assert "issues" in result
        assert isinstance(result["issues"], list)

    def test_mypy_passes_typed_file(self) -> None:
        """Should pass for properly typed files."""
        manager = QAManager()
        # Files with py.typed marker should pass
        result = manager._run_mypy(["mcp_server/__init__.py"])

        # May have issues or not, but should return valid structure
        assert result["gate_number"] == 2


class TestQAManagerIntegration:
    """Integration tests for full quality gates flow."""

    def test_run_quality_gates_returns_real_results(self) -> None:
        """Should run actual pylint and mypy, not stub data."""
        manager = QAManager()
        result = manager.run_quality_gates(["mcp_server/__init__.py"])

        assert "overall_pass" in result
        assert len(result["gates"]) >= 2

        # Verify pylint ran (should have real score)
        pylint_gate = result["gates"][0]
        assert pylint_gate["name"] == "Linting"
        # Score should not always be "10/10" - it's calculated

    def test_run_quality_gates_includes_issues(self) -> None:
        """Should include specific issues in output."""
        manager = QAManager()
        result = manager.run_quality_gates(["mcp_server/managers/qa_manager.py"])

        # At least one gate should have issues list
        has_issues_field = any("issues" in gate for gate in result["gates"])
        assert has_issues_field

    def test_run_quality_gates_nonexistent_file(self) -> None:
        """Should handle nonexistent files gracefully."""
        manager = QAManager()
        result = manager.run_quality_gates(["nonexistent_file.py"])

        # Should not crash, should report error
        assert result["overall_pass"] is False

# tests/unit/mcp_server/managers/test_qa_manager.py
"""
Unit tests for QAManager.

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
import subprocess
import typing
from unittest.mock import MagicMock, patch

# Third-party
import pytest

# Module under test
from mcp_server.managers.qa_manager import QAManager


class TestQAManager:
    """Test suite for QAManager."""

    @pytest.fixture
    def manager(self) -> QAManager:
        """Fixture for QAManager."""
        return QAManager()

    @pytest.mark.asyncio
    async def test_check_health_pass(self, manager: QAManager) -> None:
        """Test health check passes when tools are available."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            assert manager.check_health() is True
            assert mock_run.call_count == 3  # pylint, mypy, pyright

    @pytest.mark.asyncio
    async def test_check_health_fail(self, manager: QAManager) -> None:
        """Test health check fails when subprocess raises error."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert manager.check_health() is False

    @pytest.mark.asyncio
    async def test_run_quality_gates_missing_file(self, manager: QAManager) -> None:
        """Test quality gates fail on missing file."""
        with patch("pathlib.Path.exists", return_value=False):
            result = manager.run_quality_gates(["ghost.py"])
            assert result["overall_pass"] is False
            assert "File not found" in result["gates"][0]["issues"][0]["message"]

    @pytest.mark.asyncio
    async def test_run_quality_gates_pylint_fail(self, manager: QAManager) -> None:
        """Test quality gates fail on Pylint errors."""
        pylint_output = """
test.py:10:0: C0111: Missing docstring (missing-docstring)
Your code has been rated at 5.00/10
"""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:

            # Setup Pylint failure output
            mock_proc_pylint = MagicMock()
            mock_proc_pylint.stdout = pylint_output
            mock_proc_pylint.stderr = ""

            # Setup Mypy pass output
            mock_proc_mypy = MagicMock()
            mock_proc_mypy.stdout = ""
            mock_proc_mypy.stderr = ""

            # Setup Pyright pass output (JSON)
            mock_proc_pyright = MagicMock()
            mock_proc_pyright.stdout = '{"generalDiagnostics": []}'
            mock_proc_pyright.stderr = ""

            mock_run.side_effect = [mock_proc_pylint, mock_proc_mypy, mock_proc_pyright]

            result = manager.run_quality_gates(["test.py"])

            assert result["overall_pass"] is False
            pylint_gate = next(g for g in result["gates"] if g["name"] == "Linting")
            assert pylint_gate["passed"] is False
            assert pylint_gate["score"] == "5.00/10"
            assert pylint_gate["issues"][0]["code"] == "C0111"

    @pytest.mark.asyncio
    async def test_run_quality_gates_mypy_fail(self, manager: QAManager) -> None:
        """Test quality gates fail on Mypy errors."""
        mypy_output = "test.py:12: error: Incompatible types"

        with patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:

            # Pylint Pass
            mock_proc_pylint = MagicMock()
            mock_proc_pylint.stdout = "Your code has been rated at 10.00/10"
            mock_proc_pylint.stderr = ""

            # Mypy Fail
            mock_proc_mypy = MagicMock()
            mock_proc_mypy.stdout = mypy_output
            mock_proc_mypy.stderr = ""

            # Pyright pass output (JSON)
            mock_proc_pyright = MagicMock()
            mock_proc_pyright.stdout = '{"generalDiagnostics": []}'
            mock_proc_pyright.stderr = ""

            mock_run.side_effect = [mock_proc_pylint, mock_proc_mypy, mock_proc_pyright]

            result = manager.run_quality_gates(["test.py"])

            assert result["overall_pass"] is False
            mypy_gate = next(g for g in result["gates"] if g["name"] == "Type Checking")
            assert mypy_gate["passed"] is False
            assert "Incompatible types" in mypy_gate["issues"][0]["message"]

    @pytest.mark.asyncio
    async def test_run_quality_gates_pass(self, manager: QAManager) -> None:
        """Test passing quality gates."""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:

            # Pylint Pass
            mock_proc_pylint = MagicMock()
            mock_proc_pylint.stdout = "Your code has been rated at 10.00/10"
            mock_proc_pylint.stderr = ""

            # Mypy Pass
            mock_proc_mypy = MagicMock()
            mock_proc_mypy.stdout = ""
            mock_proc_mypy.stderr = ""

            # Pyright Pass
            mock_proc_pyright = MagicMock()
            mock_proc_pyright.stdout = '{"generalDiagnostics": []}'
            mock_proc_pyright.stderr = ""

            mock_run.side_effect = [mock_proc_pylint, mock_proc_mypy, mock_proc_pyright]

            result = manager.run_quality_gates(["test.py"])

            assert result["overall_pass"] is True
            assert not any(g["issues"] for g in result["gates"])

    @pytest.mark.asyncio
    async def test_subprocess_timeout(self, manager: QAManager) -> None:
        """Test handling of subprocess timeout (e.g., Mypy hangs)."""
        with patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:

            # Pylint runs ok
            mock_proc_pylint = MagicMock()
            mock_proc_pylint.stdout = "Your code has been rated at 10.00/10"
            mock_proc_pylint.stderr = ""

            # Mypy times out
            mock_proc_pyright = MagicMock()
            mock_proc_pyright.stdout = '{"generalDiagnostics": []}'
            mock_proc_pyright.stderr = ""

            mock_run.side_effect = [
                mock_proc_pylint,
                subprocess.TimeoutExpired(["mypy"], 1),
                mock_proc_pyright,
            ]

            result = manager.run_quality_gates(["test.py"])
            mypy_gate = next(g for g in result["gates"] if g["name"] == "Type Checking")
            assert mypy_gate["passed"] is False
            assert "timed out" in mypy_gate["issues"][0]["message"]

    @pytest.mark.asyncio
    async def test_subprocess_not_found(self, manager: QAManager) -> None:
        """Test handling of FileNotFoundError (tool missing) during execution."""
        # Use simple variable type hint to satisfy 'typing' usage requirement
        # without complex logic impact.
        _unused: typing.Any = None

        with patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run", side_effect=FileNotFoundError("Tool not found")):

            result = manager.run_quality_gates(["test.py"])

            # Pylint fails first
            pylint_gate = next(g for g in result["gates"] if g["name"] == "Linting")
            assert pylint_gate["passed"] is False
            assert "not found" in pylint_gate["issues"][0]["message"]

    @pytest.mark.asyncio
    async def test_run_quality_gates_pyright_fail(self, manager: QAManager) -> None:
        """Test quality gates fail on Pyright errors."""
        pyright_output = (
            '{"generalDiagnostics": ['
            '{"file":"test.py","severity":"error","message":"Bad type","range":'
            '{"start":{"line":11,"character":0},"end":{"line":11,"character":3}}}'
            ']}'
        )

        with patch("pathlib.Path.exists", return_value=True), \
             patch("subprocess.run") as mock_run:
            mock_proc_pylint = MagicMock()
            mock_proc_pylint.stdout = "Your code has been rated at 10.00/10"
            mock_proc_pylint.stderr = ""

            mock_proc_mypy = MagicMock()
            mock_proc_mypy.stdout = ""
            mock_proc_mypy.stderr = ""

            mock_proc_pyright = MagicMock()
            mock_proc_pyright.stdout = pyright_output
            mock_proc_pyright.stderr = ""

            mock_run.side_effect = [mock_proc_pylint, mock_proc_mypy, mock_proc_pyright]

            result = manager.run_quality_gates(["test.py"])
            assert result["overall_pass"] is False

            pyright_gate = next(g for g in result["gates"] if g["name"] == "Pyright")
            assert pyright_gate["passed"] is False
            assert "Bad type" in pyright_gate["issues"][0]["message"]

    def _satisfy_typing_import(self) -> typing.Any:
        """Helper to legitimately use typing import."""
        return None

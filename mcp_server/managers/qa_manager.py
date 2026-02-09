"""QA Manager for quality gates."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp_server.config.quality_config import QualityConfig, QualityGate


def _venv_script_path(script_name: str) -> str:
    """Return a best-effort path to a venv script.

    On Windows virtualenvs, console scripts are typically in the same folder
    as sys.executable.
    """
    exe_dir = str(Path(sys.executable).resolve().parent)
    return str(Path(exe_dir) / script_name)


def _pyright_script_name() -> str:
    """Return the appropriate pyright script name for the current OS."""
    return "pyright.exe" if os.name == "nt" else "pyright"


class QAManager:
    """Manager for quality assurance and gates."""

    def _filter_files(
        self, files: list[str]
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Filter Python files and generate pre-gate issues for non-Python files.

        Returns:
            (python_files, pre_gate_issues)
        """
        python_files = [f for f in files if str(f).endswith(".py")]
        non_python_files = [f for f in files if f not in python_files]

        issues: list[dict[str, Any]] = []
        if not python_files:
            issues.append({
                "message": "No Python (.py) files provided; quality gates support .py only"
            })

        for f in non_python_files:
            issues.append({
                "file": f,
                "message": "Skipped non-Python file (quality gates support .py only)"
            })

        return python_files, issues

    def run_quality_gates(self, files: list[str]) -> dict[str, Any]:
        """Run quality gates on specified files.
        
        Uses active_gates list from quality.yaml for config-driven execution.
        """
        results: dict[str, Any] = {
            "overall_pass": True,
            "gates": [],
        }

        # Verify files exist
        missing_files = [f for f in files if not Path(f).exists()]
        if missing_files:
            results["overall_pass"] = False
            results["gates"].append({
                "gate_number": 0,
                "name": "File Validation",
                "passed": False,
                "score": "N/A",
                "issues": [{"message": f"File not found: {f}"} for f in missing_files]
            })
            return results

        python_files, pre_gate_issues = self._filter_files(files)

        if pre_gate_issues or not python_files:
            results["gates"].append({
                "gate_number": 0,
                "name": "File Filtering",
                "passed": bool(python_files),
                "score": "N/A",
                "issues": pre_gate_issues,
            })
            if not python_files:
                results["overall_pass"] = False

        if not python_files:
            return results

        quality_config = QualityConfig.load()

        # Config-driven gate execution using active_gates list
        if not quality_config.active_gates:
            # No active gates configured - return empty results
            results["gates"].append({
                "gate_number": 0,
                "name": "Configuration",
                "passed": False,
                "score": "N/A",
                "issues": [{"message": "No active_gates configured in quality.yaml"}]
            })
            results["overall_pass"] = False
            return results

        # Execute gates dynamically based on active_gates configuration
        for gate_number, gate_id in enumerate(quality_config.active_gates, start=1):
            gate = quality_config.gates.get(gate_id)
            if gate is None:
                results["gates"].append({
                    "gate_number": gate_number,
                    "name": f"Unknown Gate: {gate_id}",
                    "passed": False,
                    "score": "N/A",
                    "issues": [{"message": f"Gate '{gate_id}' not found in quality.yaml"}]
                })
                results["overall_pass"] = False
                continue

            # Apply scope filtering if gate defines scope
            gate_files = python_files
            if gate.scope:
                gate_files = gate.scope.filter_files(python_files)

            if not gate_files:
                # No files in scope - skip gate with pass
                results["gates"].append({
                    "gate_number": gate_number,
                    "name": gate.name,
                    "passed": True,
                    "score": "Skipped (no matching files)",
                    "issues": []
                })
                continue

            # Execute gate using generic executor
            gate_result = self._execute_gate(gate, gate_files, gate_number=gate_number)
            results["gates"].append(gate_result)
            if not gate_result["passed"]:
                results["overall_pass"] = False

        return results


    def check_health(self) -> bool:
        """Check if QA tools are available."""
        try:
            # Check if pylint and mypy are installed
            for tool in ["pylint", "mypy"]:
                subprocess.run(
                    [sys.executable, "-m", tool, "--version"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

            # Check if pyright is available (console script)
            subprocess.run(
                [_venv_script_path(_pyright_script_name()), "--version"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _require_gate(self, quality_config: QualityConfig, gate_id: str) -> QualityGate:
        gate = quality_config.gates.get(gate_id)
        if gate is None:
            raise KeyError(f"Missing required quality gate in .st3/quality.yaml: {gate_id}")
        return gate

    def _resolve_command(self, base_command: list[str], files: list[str]) -> list[str]:
        cmd = list(base_command)

        if cmd and cmd[0] == "python":
            cmd[0] = sys.executable

        if cmd and cmd[0] in {"pyright", "pyright.exe"}:
            cmd[0] = _venv_script_path(_pyright_script_name())

        return [*cmd, *files]

    def _execute_gate(
        self, gate: QualityGate, files: list[str], gate_number: int
    ) -> dict[str, Any]:
        """Execute a quality gate with generic command execution.
        
        Generic executor that replaces tool-specific methods (_run_pylint, _run_mypy, _run_pyright).
        Eliminates code duplication by handling subprocess execution, timeout, and error handling uniformly.
        
        Args:
            gate: Gate configuration from quality.yaml
            files: List of files to check
            gate_number: Gate number for result reporting
            
        Returns:
            Result dict with gate_number, name, passed, score, issues
        """
        result: dict[str, Any] = {
            "gate_number": gate_number,
            "name": gate.name,
            "passed": True,
            "score": "Pass",
            "issues": []
        }

        try:
            cmd = self._resolve_command(gate.execution.command, files)

            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=gate.execution.timeout_seconds,
                check=False
            )

            # Combine stdout + stderr for parsing
            combined_output = proc.stdout + proc.stderr

            # Use parsing strategy from quality.yaml config (WP2)
            strategy = gate.parsing.strategy

            # Strategy-based parsing:
            issues: list[dict[str, Any]] = []
            score = "Pass"

            if strategy == "exit_code":
                # Exit code strategy: check returncode against success.exit_codes_ok
                if proc.returncode in gate.success.exit_codes_ok:
                    # Success - tool returned acceptable exit code
                    result["passed"] = True
                    result["issues"] = []
                    result["score"] = "Pass"
                else:
                    # Failure - tool returned non-acceptable exit code
                    result["passed"] = False
                    result["score"] = f"Fail (exit code {proc.returncode})"
                    result["issues"] = [{
                        "message": f"Tool exited with code {proc.returncode}",
                        "output": combined_output[:500]  # Truncate for readability
                    }]

            elif strategy == "text_regex":
                # Text regex strategy: not yet fully implemented (future WP)
                # Requires pattern matching configuration from quality.yaml
                result["passed"] = False
                result["score"] = "Not Implemented"
                result["issues"] = [{
                    "message": "text_regex parsing strategy not yet implemented",
                    "details": "Use exit_code strategy for current gates"
                }]

            elif strategy == "json_field":
                # JSON field strategy: not yet fully implemented (future WP)
                # Requires field extraction configuration from quality.yaml
                result["passed"] = False
                result["score"] = "Not Implemented"
                result["issues"] = [{
                    "message": "json_field parsing strategy not yet implemented",
                    "details": "Use exit_code strategy for current gates"
                }]

            else:
                # Unknown strategy - default to exit_code behavior
                if proc.returncode != 0:
                    result["passed"] = False
                    result["score"] = f"Fail (exit code {proc.returncode})"
                    result["issues"] = [{
                        "message": f"Tool exited with code {proc.returncode}",
                        "output": combined_output[:500]
                    }]

        except subprocess.TimeoutExpired:
            result["passed"] = False
            result["score"] = "Timeout"
            result["issues"] = [{"message": f"{gate.name} timed out"}]
        except FileNotFoundError:
            result["passed"] = False
            result["score"] = "Not Found"
            result["issues"] = [{"message": f"{gate.name} not found"}]

        return result










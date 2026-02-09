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
            # Fallback to legacy hardcoded gates if active_gates not configured
            return self._run_legacy_gates(quality_config, python_files, results)

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

    def _run_legacy_gates(self, quality_config: QualityConfig, python_files: list[str], results: dict[str, Any]) -> dict[str, Any]:
        """Legacy hardcoded gate execution (deprecated - kept for backward compatibility)."""
        pylint_gate = self._require_gate(quality_config, "pylint")
        mypy_gate = self._require_gate(quality_config, "mypy")
        pyright_gate = self._require_gate(quality_config, "pyright")

        # Gate 1: Pylint (no scope filtering - strict on all files)
        pylint_result = self._run_pylint(pylint_gate, python_files)
        results["gates"].append(pylint_result)
        if not pylint_result["passed"]:
            results["overall_pass"] = False

        # Gate 2: Mypy (apply scope filtering per config)
        mypy_files = python_files
        if mypy_gate.scope:
            mypy_files = mypy_gate.scope.filter_files(python_files)

        if not mypy_files:
            # No files in scope - skip gate with pass
            results["gates"].append({
                "gate_number": 2,
                "name": mypy_gate.name,
                "passed": True,
                "score": "Skipped (no matching files)",
                "issues": []
            })
        else:
            mypy_result = self._run_mypy(mypy_gate, mypy_files)
            results["gates"].append(mypy_result)
            if not mypy_result["passed"]:
                results["overall_pass"] = False

        # Gate 3: Pyright (no scope filtering for now)
        pyright_result = self._run_pyright(pyright_gate, python_files)
        results["gates"].append(pyright_result)
        if not pyright_result["passed"]:
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
                # Text regex strategy: use patterns from quality.yaml (future WP)
                # For now fall back to tool-specific parsing for backward compatibility
                tool_type = self._detect_tool_type(gate.name.lower())
                if tool_type == "pylint":
                    issues = self._parse_pylint_output(combined_output)
                    score = self._extract_pylint_score(combined_output)
                    result["score"] = score
                    result["issues"] = issues
                    result["passed"] = not issues and "10" in score
                elif tool_type == "mypy":
                    issues = self._parse_mypy_output(combined_output)
                    result["issues"] = issues
                    result["passed"] = not issues
                    result["score"] = "Pass" if result["passed"] else f"Fail ({len(issues)} errors)"
                elif tool_type == "pyright":
                    # Pyright fails hard on non-zero exit code
                    if proc.returncode != 0:
                        result["passed"] = False
                        issues = self._parse_pyright_output(combined_output)
                        if not issues:
                            # No diagnostics parsed - add generic failure
                            preview = "\n".join(combined_output.split("\n")[:20])
                            issues = [{
                                "message": f"Pyright failed (exit code {proc.returncode})",
                                "details": preview if preview else "No output captured"
                            }]
                        result["issues"] = issues
                        result["score"] = f"Fail ({len(issues)} errors)"
                    else:
                        # Exit code 0 - parse diagnostics normally
                        issues = self._parse_pyright_output(combined_output)
                        result["issues"] = issues
                        result["passed"] = not issues
                        result["score"] = "Pass" if result["passed"] else f"Fail ({len(issues)} errors)"
                else:
                    # Fallback: treat as exit_code strategy
                    if proc.returncode != 0:
                        result["passed"] = False
                        result["score"] = f"Fail (exit code {proc.returncode})"
                        result["issues"] = [{
                            "message": f"Tool exited with code {proc.returncode}",
                            "output": combined_output[:500]
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

    def _detect_tool_type(self, gate_name: str) -> str:
        """Detect tool type from gate name for backward compatibility.
        
        Args:
            gate_name: Gate name from quality.yaml (lowercase)
            
        Returns:
            Tool type: 'pylint', 'mypy', 'pyright', or 'unknown'
        """
        if "pylint" in gate_name or "linting" in gate_name:
            return "pylint"
        elif "mypy" in gate_name or "type checking" in gate_name:
            return "mypy"
        elif "pyright" in gate_name:
            return "pyright"
        else:
            return "unknown"

    def _run_pylint(self, gate: QualityGate, files: list[str]) -> dict[str, Any]:
        """Run pylint checks on files."""
        result: dict[str, Any] = {
            "gate_number": 1,
            "name": gate.name,
            "passed": True,
            "score": "10/10",
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

            # Parse pylint output
            output = proc.stdout + proc.stderr
            issues = self._parse_pylint_output(output)
            score = self._extract_pylint_score(output)

            result["issues"] = issues
            result["score"] = score
            result["passed"] = not issues and "10" in score

        except subprocess.TimeoutExpired:
            result["passed"] = False
            result["score"] = "N/A"
            result["issues"] = [{"message": "Pylint timed out"}]
        except FileNotFoundError:
            result["passed"] = False
            result["score"] = "N/A"
            result["issues"] = [{"message": "Pylint not found"}]

        return result

    def _parse_pylint_output(self, output: str) -> list[dict[str, Any]]:
        """Parse pylint output into structured issues."""
        issues: list[dict[str, Any]] = []

        # Pattern: filepath:line:col: code: message
        pattern = r"^(.+?):(\d+):(\d+): ([A-Z]\d+): (.+)$"

        for line in output.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                issues.append({
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "column": int(match.group(3)),
                    "code": match.group(4),
                    "message": match.group(5)
                })

        return issues

    def _extract_pylint_score(self, output: str) -> str:
        """Extract score from pylint output."""
        # Pattern: "Your code has been rated at X.XX/10"
        pattern = r"Your code has been rated at ([\d.]+)/10"
        match = re.search(pattern, output)
        if match:
            return f"{match.group(1)}/10"
        return "10/10"  # Default if no issues found

    def _run_mypy(self, gate: QualityGate, files: list[str]) -> dict[str, Any]:
        """Run mypy type checking on files."""
        result: dict[str, Any] = {
            "gate_number": 2,
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

            # Parse mypy output from both stdout and stderr
            combined_output = proc.stdout + proc.stderr
            issues = self._parse_mypy_output(combined_output)
            result["issues"] = issues
            result["passed"] = not issues
            result["score"] = "Pass" if result["passed"] else f"Fail ({len(issues)} errors)"

        except subprocess.TimeoutExpired:
            result["passed"] = False
            result["score"] = "Timeout"
            result["issues"] = [{"message": "Mypy timed out"}]
        except FileNotFoundError:
            result["passed"] = False
            result["score"] = "Not Found"
            result["issues"] = [{"message": "Mypy not found"}]

        return result

    def _parse_mypy_output(self, output: str) -> list[dict[str, Any]]:
        """Parse mypy output into structured issues."""
        issues: list[dict[str, Any]] = []

        # Pattern: filepath:line: error: message
        pattern = r"^(.+?):(\d+): (error|warning): (.+)$"

        for line in output.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                issues.append({
                    "file": match.group(1),
                    "line": int(match.group(2)),
                    "severity": match.group(3),
                    "message": match.group(4)
                })

        return issues

    def _run_pyright(self, gate: QualityGate, files: list[str]) -> dict[str, Any]:
        """Run pyright type checking on files.

        Note: pyright is a separate CLI (not `python -m pyright`).
        """
        result: dict[str, Any] = {
            "gate_number": 3,
            "name": gate.name,
            "passed": True,
            "score": "Pass",
            "issues": [],
        }

        try:
            cmd = self._resolve_command(gate.execution.command, files)

            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=gate.execution.timeout_seconds,
                check=False,
            )

            # Combine stdout + stderr for robust parsing
            combined_output = (proc.stdout or "") + (proc.stderr or "")

            # Fail hard on non-zero exit code
            if proc.returncode:
                result["passed"] = False
                # Parse output for specific errors, but always mark as failed
                issues = self._parse_pyright_output(combined_output)
                if not issues:
                    # No diagnostics parsed - add generic failure message with context
                    preview = "\n".join(combined_output.split("\n")[:20])
                    issues = [{
                        "message": f"Pyright failed (exit code {proc.returncode})",
                        "details": preview if preview else "No output captured"
                    }]
                result["issues"] = issues
                result["score"] = f"Fail ({len(issues)} errors)"
            else:
                # Exit code 0 - parse diagnostics normally
                issues = self._parse_pyright_output(combined_output)
                result["issues"] = issues
                result["passed"] = not issues
                result["score"] = "Pass" if result["passed"] else f"Fail ({len(issues)} errors)"

        except subprocess.TimeoutExpired:
            result["passed"] = False
            result["score"] = "Timeout"
            result["issues"] = [{"message": "Pyright timed out"}]
        except FileNotFoundError:
            result["passed"] = False
            result["score"] = "Not Found"
            result["issues"] = [{"message": "Pyright not found"}]

        return result

    def _pyright_issue_from_diag(self, diag: dict[str, Any]) -> dict[str, Any]:
        """Convert a single pyright diagnostic to the common issue format."""
        issue: dict[str, Any] = {
            "message": str(diag.get("message", "Unknown issue")),
        }

        file_path = diag.get("file")
        if isinstance(file_path, str):
            issue["file"] = file_path

        start = ((diag.get("range") or {}).get("start") or {})
        line = start.get("line")
        char = start.get("character")
        if isinstance(line, int):
            issue["line"] = line + 1  # pyright is 0-based
        if isinstance(char, int):
            issue["column"] = char + 1

        rule = diag.get("rule")
        if rule is not None:
            issue["code"] = str(rule)

        sev = diag.get("severity")
        if sev is not None:
            issue["severity"] = str(sev)

        return issue

    def _parse_pyright_output(self, output: str) -> list[dict[str, Any]]:
        """Parse pyright --outputjson output into structured issues."""
        issues: list[dict[str, Any]] = []

        # When `--outputjson` is used, output is JSON. Keep parsing defensive.
        try:
            data = json.loads(output)
            diagnostics = data.get("generalDiagnostics", [])
            if isinstance(diagnostics, list):
                for diag in diagnostics:
                    if isinstance(diag, dict):
                        issues.append(self._pyright_issue_from_diag(diag))

        except (json.JSONDecodeError, TypeError, ValueError):
            # Fall back to plain-text parsing if JSON isn't available/valid.
            for line in output.split("\n"):
                text = line.strip()
                if text:
                    issues.append({"message": text})

        return issues

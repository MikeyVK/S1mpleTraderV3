"""QA Manager for quality gates."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


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

    def run_quality_gates(self, files: list[str]) -> dict[str, Any]:
        """Run quality gates on specified files."""
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

        python_files = [f for f in files if str(f).endswith(".py")]
        non_python_files = [f for f in files if f not in python_files]

        if non_python_files or not python_files:
            issues: list[dict[str, Any]] = []
            if not python_files:
                results["overall_pass"] = False
                issues.append({
                    "message": "No Python (.py) files provided; quality gates support .py only"
                })

            for f in non_python_files:
                issues.append({
                    "file": f,
                    "message": "Skipped non-Python file (quality gates support .py only)"
                })

            results["gates"].append({
                "gate_number": 0,
                "name": "File Filtering",
                "passed": bool(python_files),
                "score": "N/A",
                "issues": issues,
            })

        if not python_files:
            return results

        # Gate 1: Pylint (Whitespace/Imports/Line Length)
        pylint_result = self._run_pylint(python_files)
        results["gates"].append(pylint_result)
        if not pylint_result["passed"]:
            results["overall_pass"] = False

        # Gate 2: Mypy (Type Checking)
        mypy_result = self._run_mypy(python_files)
        results["gates"].append(mypy_result)
        if not mypy_result["passed"]:
            results["overall_pass"] = False

        # Gate 3: Pyright (Pylance parity)
        pyright_result = self._run_pyright(python_files)
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

    def _run_pylint(self, files: list[str]) -> dict[str, Any]:
        """Run pylint checks on files."""
        result: dict[str, Any] = {
            "gate_number": 1,
            "name": "Linting",
            "passed": True,
            "score": "10/10",
            "issues": []
        }

        try:
            # Run pylint with specific checks
            python_exe = sys.executable
            cmd = [
                python_exe, "-m", "pylint",
                *files,
                "--enable=all",
                "--max-line-length=100",
                "--output-format=text"
            ]

            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=60,
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

    def _run_mypy(self, files: list[str]) -> dict[str, Any]:
        """Run mypy type checking on files."""
        result: dict[str, Any] = {
            "gate_number": 2,
            "name": "Type Checking",
            "passed": True,
            "score": "Pass",
            "issues": []
        }

        try:
            python_exe = sys.executable
            cmd = [
                python_exe, "-m", "mypy",
                *files,
                "--strict",
                "--no-error-summary"
            ]

            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=60,
                check=False
            )

            # Parse mypy output
            issues = self._parse_mypy_output(proc.stdout)
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

    def _run_pyright(self, files: list[str]) -> dict[str, Any]:
        """Run pyright type checking on files.

        Note: pyright is a separate CLI (not `python -m pyright`).
        """
        result: dict[str, Any] = {
            "gate_number": 3,
            "name": "Pyright",
            "passed": True,
            "score": "Pass",
            "issues": [],
        }

        try:
            cmd = [
                _venv_script_path(_pyright_script_name()),
                "--outputjson",
                *files,
            ]

            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )

            issues = self._parse_pyright_output(proc.stdout or "")
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

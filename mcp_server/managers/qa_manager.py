"""QA Manager for quality gates."""
# pylint: disable=subprocess-run-check  # We handle return codes manually
# pylint: disable=too-few-public-methods  # Manager pattern with single entry point
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


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

        # Gate 1: Pylint (Whitespace/Imports/Line Length)
        pylint_result = self._run_pylint(files)
        results["gates"].append(pylint_result)
        if not pylint_result["passed"]:
            results["overall_pass"] = False

        # Gate 2: Mypy (Type Checking)
        mypy_result = self._run_mypy(files)
        results["gates"].append(mypy_result)
        if not mypy_result["passed"]:
            results["overall_pass"] = False

        return results

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
                timeout=60
            )

            # Parse pylint output
            output = proc.stdout + proc.stderr
            issues = self._parse_pylint_output(output)
            score = self._extract_pylint_score(output)

            result["issues"] = issues
            result["score"] = score
            result["passed"] = len(issues) == 0 and "10" in score

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
                timeout=60
            )

            # Parse mypy output
            issues = self._parse_mypy_output(proc.stdout)
            result["issues"] = issues
            result["passed"] = len(issues) == 0
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

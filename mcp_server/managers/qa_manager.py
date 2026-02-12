"""QA Manager for quality gates."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

from mcp_server.config.quality_config import QualityConfig, QualityGate

MAX_OUTPUT_LINES = 50
MAX_OUTPUT_BYTES = 5120


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

    def _filter_files(self, files: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
        """Filter Python files and generate pre-gate issues for non-Python files.

        Returns:
            (python_files, pre_gate_issues)
        """

        python_files = [f for f in files if str(f).endswith(".py")]
        non_python_files = [f for f in files if f not in python_files]

        issues: list[dict[str, Any]] = []
        if not python_files:
            issues.append(
                {
                    "message": "No Python (.py) files provided; quality gates support .py only",
                }
            )

        for file_path in non_python_files:
            issues.append(
                {
                    "file": file_path,
                    "message": "Skipped non-Python file (quality gates support .py only)",
                }
            )

        return python_files, issues

    def run_quality_gates(self, files: list[str]) -> dict[str, Any]:
        """Run configured quality gates on specified files.

        Returns v2.0 JSON schema with version, mode, summary, and gates.

        Notes:
            - Gate catalog and active gates are defined in `.st3/quality.yaml`.
            - Only `.py` files are eligible for file-scoped gates.
            - Some gates (e.g., pytest) are repo-scoped and ignore file lists.
        """
        # Determine execution mode
        is_file_specific_mode = bool(files)
        mode = "file-specific" if is_file_specific_mode else "project-level"

        # Initialize v2.0 response schema
        results: dict[str, Any] = {
            "version": "2.0",
            "mode": mode,
            "files": files,
            "summary": {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
            },
            "gates": [],
            "overall_pass": True,  # Backward compatibility
        }

        # Determine execution mode:
        # files=[] (empty) → project-level test validation (pytest gates only: Gate 5-6)
        # files=[...] (populated) → file-specific validation
        #                            (static gates only: Gates 0-4, skip pytest)
        is_file_specific_mode = bool(files)

        if is_file_specific_mode:
            # File-specific mode: validate file existence
            missing_files = [f for f in files if not Path(f).exists()]
            if missing_files:
                self._update_summary_and_append_gate(
                    results,
                    {
                        "gate_number": 0,
                        "name": "File Validation",
                        "passed": False,
                        "score": "N/A",
                        "issues": [{"message": f"File not found: {f}"} for f in missing_files],
                    },
                )
                return results

            python_files, pre_gate_issues = self._filter_files(files)

            if pre_gate_issues or not python_files:
                self._update_summary_and_append_gate(
                    results,
                    {
                        "gate_number": 0,
                        "name": "File Filtering",
                        "passed": bool(python_files),
                        "score": "N/A",
                        "issues": pre_gate_issues,
                    },
                )

            if not python_files:
                return results
        else:
            # Project-level test validation mode:
            # - python_files stays empty (no file discovery)
            # - File-based static gates (Gates 0-4) will skip: "Skipped (no matching files)"
            # - Pytest gates (Gate 5-6) proceed with their configured targets (e.g., tests/)
            python_files = []
        # In file-specific mode, early return if no valid files
        if is_file_specific_mode and not python_files:
            return results

        quality_config = QualityConfig.load()

        if not quality_config.active_gates:
            self._update_summary_and_append_gate(
                results,
                {
                    "gate_number": 0,
                    "name": "Configuration",
                    "passed": False,
                    "score": "N/A",
                    "issues": [
                        {
                            "message": "No active_gates configured in .st3/quality.yaml",
                        }
                    ],
                },
            )
            return results

        gate_catalog = cast(dict[str, QualityGate], quality_config.gates)

        for idx, gate_id in enumerate(quality_config.active_gates, start=1):
            gate = gate_catalog.get(gate_id)
            if gate is None:
                self._update_summary_and_append_gate(
                    results,
                    {
                        "gate_number": idx,
                        "name": gate_id,
                        "passed": False,
                        "score": "N/A",
                        "issues": [
                            {
                                "message": f"Active gate not found in catalog: {gate_id}",
                            }
                        ],
                    },
                )
                continue

            gate_files = self._files_for_gate(gate, python_files)

            # Skip pytest gates (project-level tests) when in file-specific validation mode
            if is_file_specific_mode and self._is_pytest_gate(gate):
                self._update_summary_and_append_gate(
                    results,
                    {
                        "gate_number": idx,
                        "name": gate.name,
                        "passed": True,
                        "score": "Skipped (file-specific mode)",
                        "issues": [],
                    },
                )
                continue
            # Skip gates with no files after scope filtering
            # Exception: in project-level test validation mode, allow pytest gates to run
            is_repo_scoped_pytest_gate = not is_file_specific_mode and self._is_pytest_gate(gate)
            if not gate_files and not is_repo_scoped_pytest_gate:
                self._update_summary_and_append_gate(
                    results,
                    {
                        "gate_number": idx,
                        "name": gate.name,
                        "passed": True,
                        "score": "Skipped (no matching files)",
                        "issues": [],
                    },
                )
                continue
            gate_result = self._execute_gate(gate, gate_files, gate_number=idx, gate_id=gate_id)
            self._update_summary_and_append_gate(results, gate_result)

        return results

    def _update_summary_and_append_gate(
        self, results: dict[str, Any], gate_result: dict[str, Any]
    ) -> None:
        """Add gate result and update summary counts."""
        results["gates"].append(gate_result)

        # Determine gate status for summary
        if gate_result.get("passed"):
            score = gate_result.get("score", "")
            if isinstance(score, str) and "Skipped" in score:
                results["summary"]["skipped"] += 1
            else:
                results["summary"]["passed"] += 1
        else:
            results["summary"]["failed"] += 1
            results["overall_pass"] = False

    def check_health(self) -> bool:
        """Check if QA tools are available."""

        try:
            for tool in ["ruff", "mypy"]:
                subprocess.run(
                    [sys.executable, "-m", tool, "--version"],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            subprocess.run(
                [_venv_script_path(_pyright_script_name()), "--version"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                [sys.executable, "-m", "pytest", "--version"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def _resolve_command(self, base_command: list[str], files: list[str]) -> list[str]:
        cmd = list(base_command)
        if cmd and cmd[0] == "python":
            # Prefer venv Python if available
            venv_python = Path(__file__).parents[2] / ".venv" / "Scripts" / "python.exe"
            if venv_python.exists():
                cmd[0] = str(venv_python)
            else:
                cmd[0] = sys.executable

        if cmd and cmd[0] in {"pyright", "pyright.exe"}:
            cmd[0] = _venv_script_path(_pyright_script_name())

        return [*cmd, *files]

    def _files_for_gate(self, gate: QualityGate, python_files: list[str]) -> list[str]:
        """Determine which files should be passed to a gate.

        Some gates are repo-scoped (e.g., pytest) and do not accept/need file args.
        """

        # Repo-scoped gate: pytest. Gate config already contains target paths.
        if self._is_pytest_gate(gate):
            return []

        eligible = [
            f
            for f in python_files
            if any(str(f).endswith(ext) for ext in gate.capabilities.file_types)
        ]

        if gate.scope is not None:
            eligible = gate.scope.filter_files(eligible)

        return eligible

    def _is_pytest_gate(self, gate: QualityGate) -> bool:
        cmd = gate.execution.command
        if not cmd:
            return False

        if cmd[0] == "pytest":
            return True
        if len(cmd) >= 3 and cmd[0] == "python" and cmd[1] == "-m" and cmd[2] == "pytest":
            return True
        return len(cmd) >= 3 and cmd[0] == sys.executable and cmd[1] == "-m" and cmd[2] == "pytest"

    def _command_for_hints(self, gate: QualityGate, files: list[str]) -> str:
        parts = [*gate.execution.command, *files]
        return " ".join(str(p) for p in parts)

    def _gate_hints(self, gate_id: str, gate: QualityGate, files: list[str]) -> list[str]:
        cmd = self._command_for_hints(gate, files)
        hints: list[str] = [f"Re-run: {cmd}"]

        if gate_id == "gate0_ruff_format":
            hints.append(
                "To apply formatting: run the same command without "
                "`--check`/`--diff` (e.g. `python -m ruff format <files>`)."
            )

        elif gate_id == "gate1_formatting":
            hints.append(
                "This gate is stricter than the VS Code/IDE baseline "
                "(it does not inherit pyproject ignores)."
            )
            hints.append(
                "Line length (E501) and import placement (PLC0415) are enforced in Gate 2/3."
            )

        elif gate_id == "gate2_imports":
            hints.append(
                "Move imports to module top-level (PLC0415). Never import inside functions/methods."
            )

        elif gate_id == "gate3_line_length":
            hints.append(
                "Split long lines to <= 100 chars (E501). "
                "Prefer intermediate variables and broken method chains."
            )

        elif gate_id == "gate4_types":
            hints.append(
                "Run type fixes in order: add annotations -> narrow Optionals "
                "(assert/isinstance) -> refactor types (TypedDict/Protocol) -> "
                "targeted ignore as last resort."
            )
            hints.append(
                "This gate is scoped (DTOs only). If you hit false positives, "
                "prefer narrowing or tiny, code-specific ignores."
            )

        elif gate_id == "gate5_tests":
            hints.append(
                "Re-run pytest and fix the first failing test; reduce scope by "
                "running the failing test file only."
            )

        return hints

    def _truncate_output_text(self, text: str) -> tuple[str, bool]:
        """Truncate output text by line and byte limits."""
        if not text:
            return "", False

        truncated = False
        lines = text.splitlines()

        if len(lines) > MAX_OUTPUT_LINES:
            lines = lines[:MAX_OUTPUT_LINES]
            truncated = True

        trimmed = "\n".join(lines).strip()
        encoded = trimmed.encode("utf-8")
        if len(encoded) > MAX_OUTPUT_BYTES:
            trimmed = encoded[:MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore").rstrip()
            truncated = True

        return trimmed, truncated

    def _build_output_capture(self, stdout: str, stderr: str) -> dict[str, Any]:
        """Build structured output capture with truncation metadata."""
        stdout_text, stdout_truncated = self._truncate_output_text(stdout)
        stderr_text, stderr_truncated = self._truncate_output_text(stderr)

        is_truncated = stdout_truncated or stderr_truncated
        details_parts: list[str] = []
        if stdout_text:
            details_parts.append(f"stdout:\n{stdout_text}")
        if stderr_text:
            details_parts.append(f"stderr:\n{stderr_text}")

        details = "\n\n".join(details_parts) if details_parts else "No output captured"
        if is_truncated:
            details = (
                f"{details}\n\n[truncated to {MAX_OUTPUT_LINES} lines / "
                f"{MAX_OUTPUT_BYTES} bytes per stream]"
            )

        return {
            "stdout": stdout_text,
            "stderr": stderr_text,
            "truncated": is_truncated,
            "details": details,
        }

    def _execute_gate(
        self, gate: QualityGate, files: list[str], gate_number: int, gate_id: str | None = None
    ) -> dict[str, Any]:
        """Execute a single gate using its configured parsing strategy."""

        result: dict[str, Any] = {
            "gate_number": gate_number,
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
                cwd=gate.execution.working_dir,
            )

            combined_output = (proc.stdout or "") + (proc.stderr or "")

            if gate.parsing.strategy == "exit_code":
                ok_codes = set(gate.success.exit_codes_ok)

                # Try JSON parsing if gate produces JSON (Ruff gates with --output-format=json)
                if gate.capabilities.produces_json:
                    # Parse Ruff JSON violations
                    parser_input = proc.stdout if (proc.stdout or "").strip() else combined_output
                    parsed_issues = self._parse_ruff_json(parser_input)
                    if parsed_issues:
                        # Violations found - gate fails
                        result["passed"] = False
                        fixable_count = sum(1 for issue in parsed_issues if issue.get("fixable"))
                        result["score"] = (
                            f"{len(parsed_issues)} violations, {fixable_count} auto-fixable"
                        )
                        result["issues"] = parsed_issues
                        result["output"] = self._build_output_capture(
                            proc.stdout or "", proc.stderr or ""
                        )
                    elif proc.returncode in ok_codes:
                        # No violations, exit code OK - gate passes
                        result["score"] = "Pass"
                        result["passed"] = True
                        result["issues"] = []
                    else:
                        # JSON parsing failed but exit code indicates error
                        result["passed"] = False
                        result["score"] = f"Fail (exit={proc.returncode})"
                        output_capture = self._build_output_capture(
                            proc.stdout or "", proc.stderr or ""
                        )
                        result["output"] = {
                            "stdout": output_capture["stdout"],
                            "stderr": output_capture["stderr"],
                            "truncated": output_capture["truncated"],
                        }
                        result["issues"] = [
                            {
                                "message": f"Gate failed with exit code {proc.returncode}",
                                "details": output_capture["details"],
                            }
                        ]
                else:
                    # Traditional exit code-only parsing
                    if proc.returncode in ok_codes:
                        result["passed"] = True
                        result["score"] = "Pass"
                        result["issues"] = []
                    else:
                        result["passed"] = False
                        result["score"] = f"Fail (exit={proc.returncode})"
                        output_capture = self._build_output_capture(
                            proc.stdout or "", proc.stderr or ""
                        )
                        result["output"] = {
                            "stdout": output_capture["stdout"],
                            "stderr": output_capture["stderr"],
                            "truncated": output_capture["truncated"],
                        }
                        result["issues"] = [
                            {
                                "message": f"Gate failed with exit code {proc.returncode}",
                                "details": output_capture["details"],
                            }
                        ]

            elif gate.parsing.strategy == "json_field":
                issues = self._parse_json_field_issues(combined_output)
                result["issues"] = issues
                # If parsing is JSON-field based, treat any issue list as failure.
                result["passed"] = not issues
                result["score"] = "Pass" if result["passed"] else f"Fail ({len(issues)} errors)"

            elif gate.parsing.strategy == "text_regex":
                # Minimal v1: consider non-zero exit code as failure; surface output.
                # Detailed regex extraction is intentionally deferred.
                if proc.returncode in set(gate.success.exit_codes_ok):
                    result["passed"] = True
                    result["issues"] = []
                    result["score"] = "Pass"
                else:
                    result["passed"] = False
                    output_capture = self._build_output_capture(
                        proc.stdout or "", proc.stderr or ""
                    )
                    result["output"] = {
                        "stdout": output_capture["stdout"],
                        "stderr": output_capture["stderr"],
                        "truncated": output_capture["truncated"],
                    }
                    result["issues"] = [
                        {
                            "message": f"Gate failed with exit code {proc.returncode}",
                            "details": output_capture["details"],
                        }
                    ]
                    result["score"] = f"Fail (exit={proc.returncode})"

            else:
                result["passed"] = False
                result["score"] = "N/A"
                result["issues"] = [
                    {"message": f"Unsupported parsing strategy: {gate.parsing.strategy}"}
                ]

        except subprocess.TimeoutExpired:
            result["passed"] = False
            result["score"] = "Timeout"
            result["issues"] = [{"message": f"{gate.name} timed out"}]
        except FileNotFoundError as e:
            result["passed"] = False
            result["score"] = "Not Found"
            result["issues"] = [{"message": f"Tool not found: {e}"}]

        if gate_id and not result["passed"]:
            result["hints"] = self._gate_hints(gate_id, gate, files)

        return result

    def _parse_json_field_issues(self, output: str) -> list[dict[str, Any]]:
        """Best-effort JSON diagnostic parsing.

        This is primarily intended for pyright-like tools that emit JSON diagnostics.
        """

        try:
            data = json.loads(output)
        except (json.JSONDecodeError, TypeError, ValueError):
            # If output isn't JSON, surface as plain issue.
            text = output.strip()
            return [{"message": text}] if text else []

        diagnostics = data.get("generalDiagnostics")
        if not isinstance(diagnostics, list):
            return []

        issues: list[dict[str, Any]] = []
        for diag in diagnostics:
            if not isinstance(diag, dict):
                continue

            issue: dict[str, Any] = {
                "message": str(diag.get("message", "Unknown issue")),
            }

            file_path = diag.get("file")
            if isinstance(file_path, str):
                issue["file"] = file_path

            rng = diag.get("range") or {}
            start = (rng.get("start") or {}) if isinstance(rng, dict) else {}

            line = start.get("line")
            char = start.get("character")
            if isinstance(line, int):
                issue["line"] = line + 1
            if isinstance(char, int):
                issue["column"] = char + 1

            rule = diag.get("rule")
            if rule is not None:
                issue["code"] = str(rule)

            sev = diag.get("severity")
            if sev is not None:
                issue["severity"] = str(sev)

            issues.append(issue)

        return issues

    def _parse_ruff_json(self, output: str) -> list[dict[str, Any]]:
        """Parse Ruff JSON output into structured violation issues.

        Ruff's --output-format=json produces an array of violation objects.
        Each violation has:
        - code: Rule code (e.g., "E501", "F401")
        - message: Description of the violation
        - location: {row: int, column: int}
        - filename: Path to the file
        - fix: Optional fix object with {applicability: "safe" | "unsafe" | "display"}

        Args:
            output: JSON string from Ruff command stdout

        Returns:
            List of structured issue dicts with fields: file, line, column, code, message, fixable
        """
        try:
            violations = json.loads(output)
        except (json.JSONDecodeError, TypeError, ValueError):
            # Not valid JSON, return empty (caller handles exit code as failure)
            return []

        if not isinstance(violations, list):
            return []

        issues: list[dict[str, Any]] = []
        for violation in violations:
            if not isinstance(violation, dict):
                continue

            issue: dict[str, Any] = {
                "code": violation.get("code", "UNKNOWN"),
                "message": violation.get("message", "No message"),
            }

            # Extract location
            location = violation.get("location", {})
            if isinstance(location, dict):
                issue["line"] = location.get("row")
                issue["column"] = location.get("column")

            # Extract filename
            filename = violation.get("filename")
            if filename:
                issue["file"] = str(filename)

            # Determine fixability
            fix = violation.get("fix")
            if fix is not None and isinstance(fix, dict):
                applicability = fix.get("applicability")
                issue["fixable"] = applicability == "safe"
            else:
                issue["fixable"] = False

            issues.append(issue)

        return issues

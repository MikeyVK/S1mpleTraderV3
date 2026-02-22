"""QA Manager for quality gates."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from mcp_server.config.quality_config import (
    JsonViolationsParsing,
    QualityConfig,
    QualityGate,
    ViolationDTO,
)

DEFAULT_ARTIFACT_LOG_MAX_FILES = 200
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

    # Default configuration (UPPERCASE constants for test mocking compatibility)
    QA_LOG_DIR = Path("temp/qa_logs")
    QA_LOG_ENABLED = True
    QA_LOG_MAX_FILES = DEFAULT_ARTIFACT_LOG_MAX_FILES

    def __init__(self) -> None:
        """Initialize QA Manager with default runtime configuration."""
        # Runtime configuration (lowercase for instance mutability)
        self.qa_log_dir = self.QA_LOG_DIR
        self.qa_log_enabled = self.QA_LOG_ENABLED
        self.qa_log_max_files = self.QA_LOG_MAX_FILES

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
                "total_violations": 0,
                "auto_fixable": 0,
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
        # Apply artifact logging config (config-first with safe defaults)
        self.qa_log_enabled = quality_config.artifact_logging.enabled
        self.qa_log_dir = Path(quality_config.artifact_logging.output_dir)
        self.qa_log_max_files = quality_config.artifact_logging.max_files

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
            skip_reason = self._get_skip_reason(gate, gate_files, is_file_specific_mode)
            if skip_reason is not None:
                self._update_summary_and_append_gate(
                    results,
                    {
                        "gate_number": idx,
                        "id": idx,
                        "name": gate.name,
                        "passed": True,
                        "status": "skipped",
                        "skip_reason": skip_reason,
                        "score": skip_reason,
                        "issues": [],
                    },
                )
                continue
            gate_result = self._execute_gate(gate, gate_files, gate_number=idx, gate_id=gate_id)
            self._update_summary_and_append_gate(results, gate_result)

        # Build top-level timing breakdown (Improvement E)
        timings: dict[str, int] = {}
        for gate_result in results["gates"]:
            gate_id_key = str(gate_result.get("gate_number", gate_result.get("id", "?")))
            timings[gate_id_key] = gate_result.get("duration_ms", 0)
        timings["total"] = sum(timings.values())
        results["timings"] = timings

        return results

    def _update_summary_and_append_gate(
        self, results: dict[str, Any], gate_result: dict[str, Any]
    ) -> None:
        """Add gate result and update summary counts + violation totals."""
        results["gates"].append(gate_result)

        # Use status field if present, else infer from passed/score (backward compat)
        status = gate_result.get("status")
        if status is None:
            if gate_result.get("passed"):
                score = gate_result.get("score", "")
                status = "skipped" if isinstance(score, str) and "Skipped" in score else "passed"
            else:
                status = "failed"

        if status == "skipped":
            results["summary"]["skipped"] += 1
        elif status == "passed":
            results["summary"]["passed"] += 1
        else:
            results["summary"]["failed"] += 1
            results["overall_pass"] = False

        # Accumulate violation totals (skip for skipped gates)
        if status != "skipped":
            issues = gate_result.get("issues", [])
            results["summary"]["total_violations"] += len(issues)
            results["summary"]["auto_fixable"] += sum(1 for issue in issues if issue.get("fixable"))

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

    def _supports_pytest_json_report(self) -> bool:
        """Detect whether pytest-json-report plugin is installed."""
        return importlib.util.find_spec("pytest_jsonreport") is not None

    def _maybe_enable_pytest_json_report(self, gate: QualityGate, command: list[str]) -> list[str]:
        """Add pytest JSON report flags when plugin support is available."""
        if not self._is_pytest_gate(gate):
            return command

        if not self._supports_pytest_json_report():
            return command

        if "--json-report" in command:
            return command

        return [*command, "--json-report"]

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

    def _get_skip_reason(
        self, gate: QualityGate, gate_files: list[str], is_file_specific_mode: bool
    ) -> str | None:
        """Return standardized, mode-aware skip reason for a gate, if any.

        Skip reasons are explicit about WHY the gate was skipped to avoid
        confusion between intentional mode-based skips and actual errors.
        """
        if is_file_specific_mode and self._is_pytest_gate(gate):
            return "Skipped (file-specific mode - tests run project-wide)"

        is_repo_scoped_pytest_gate = not is_file_specific_mode and self._is_pytest_gate(gate)
        if not gate_files and not is_repo_scoped_pytest_gate:
            if not is_file_specific_mode:
                return "Skipped (project-level mode - static analysis unavailable)"
            return "Skipped (no matching files)"

        return None

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

    def _collect_environment_metadata(self, cmd: list[str]) -> dict[str, str]:
        """Collect environment metadata for command reproducibility.

        Returns a dict with python_version, tool_path, platform, and
        optionally tool_version (best-effort via ``--version``).

        When the command follows the ``python -m <tool>`` pattern the version
        probe targets the *tool* (``python -m <tool> --version``) rather than
        the Python interpreter, so ``tool_version`` reflects the actual tool.
        """
        executable = cmd[0] if cmd else ""

        # Detect ``python -m <tool>`` pattern
        is_python_m = (
            len(cmd) >= 3 and "python" in os.path.basename(executable).lower() and cmd[1] == "-m"
        )
        tool_name = cmd[2] if is_python_m else executable

        # Resolve the tool on PATH (the actual binary, not python)
        tool_path = (
            (shutil.which(tool_name) or "") if is_python_m else (shutil.which(executable) or "")
        )

        env: dict[str, str] = {
            "python_version": platform.python_version(),
            "tool_path": tool_path,
            "platform": platform.platform(),
        }

        # Best-effort tool version probe
        version_cmd: list[str] = (
            [executable, "-m", tool_name, "--version"] if is_python_m else [executable, "--version"]
        )
        try:
            ver_proc = subprocess.run(
                version_cmd,
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            version_line = (ver_proc.stdout or ver_proc.stderr or "").strip().splitlines()
            if version_line:
                env["tool_version"] = version_line[0]
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass

        return env

    def _cleanup_artifact_logs(self) -> None:
        """Keep only the newest artifact logs to avoid unbounded growth."""
        if not self.qa_log_dir.exists():
            return

        artifacts = sorted(
            self.qa_log_dir.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

        for stale_file in artifacts[self.qa_log_max_files :]:
            stale_file.unlink(missing_ok=True)

    def _write_artifact_log(
        self,
        gate_number: int,
        gate_name: str,
        command: list[str],
        files: list[str],
        result: dict[str, Any],
    ) -> str | None:
        """Write failed gate diagnostics to configured JSON artifact directory."""
        if not self.qa_log_enabled:
            return None

        try:
            self.qa_log_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            safe_gate_name = gate_name.lower().replace(" ", "_").replace(":", "")
            artifact_path = self.qa_log_dir / f"{timestamp}_gate{gate_number}_{safe_gate_name}.json"
            payload = {
                "timestamp": timestamp,
                "gate_number": gate_number,
                "gate_name": gate_name,
                "command": command,
                "files": files,
                "passed": result.get("passed", False),
                "score": result.get("score", "N/A"),
                "issues": result.get("issues", []),
                "output": result.get("output", {}),
            }

            artifact_body = json.dumps(payload, ensure_ascii=False, indent=2)
            artifact_path.write_text(artifact_body, encoding="utf-8")
            self._cleanup_artifact_logs()
            return artifact_path.as_posix()
        except OSError:
            return None

    def _execute_gate(
        self, gate: QualityGate, files: list[str], gate_number: int, gate_id: str | None = None
    ) -> dict[str, Any]:
        """Execute a single gate using its configured parsing strategy."""

        result: dict[str, Any] = {
            "gate_number": gate_number,
            "id": gate_number,
            "name": gate.name,
            "passed": True,
            "status": "passed",
            "skip_reason": None,
            "score": "Pass",
            "issues": [],
        }

        cmd: list[str] = []
        try:
            cmd = self._resolve_command(gate.execution.command, files)
            cmd = self._maybe_enable_pytest_json_report(gate, cmd)

            start_time = time.monotonic()
            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=gate.execution.timeout_seconds,
                check=False,
                cwd=gate.execution.working_dir,
            )
            duration_ms = round((time.monotonic() - start_time) * 1000)

            result["duration_ms"] = duration_ms
            result["command"] = {
                "executable": cmd[0] if cmd else "",
                "args": cmd[1:] if len(cmd) > 1 else [],
                "cwd": gate.execution.working_dir,
                "exit_code": proc.returncode,
                "environment": self._collect_environment_metadata(cmd),
            }

            combined_output = (proc.stdout or "") + (proc.stderr or "")

            if gate.parsing.strategy == "exit_code":
                ok_codes = set(gate.success.exit_codes_ok)

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
                    result["output"] = output_capture
                    result["issues"] = [
                        {
                            "message": f"Gate failed with exit code {proc.returncode}",
                            "details": output_capture["details"],
                        }
                    ]

            elif gate.parsing.strategy == "json_field":
                # Prefer stdout for JSON parsing (more reliable than combined)
                parser_input = proc.stdout if (proc.stdout or "").strip() else combined_output
                diagnostics_path = getattr(gate.parsing, "diagnostics_path", None)
                issues = self._parse_json_field_issues(parser_input, diagnostics_path)

                # Extract additional fields from JSON via configured pointers
                fields_data = self._extract_json_fields(parser_input, gate)

                # Apply success criteria (max_errors / require_no_issues)
                issue_count = len(issues)
                if gate.success.max_errors is not None:
                    result["passed"] = issue_count <= gate.success.max_errors
                elif gate.success.require_no_issues:
                    result["passed"] = issue_count == 0
                else:
                    result["passed"] = True

                result["issues"] = issues
                result["score"] = "Pass" if result["passed"] else f"Fail ({issue_count} errors)"
                if fields_data:
                    result["fields"] = fields_data

            elif gate.parsing.strategy == "text_regex":
                if proc.returncode in set(gate.success.exit_codes_ok):
                    result["passed"] = True
                    result["issues"] = []
                    result["score"] = "Pass"
                else:
                    result["passed"] = False
                    output_capture = self._build_output_capture(
                        proc.stdout or "", proc.stderr or ""
                    )
                    result["output"] = output_capture
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

        if not result["passed"]:
            result["status"] = "failed"
            artifact_path = self._write_artifact_log(gate_number, gate.name, cmd, files, result)
            if artifact_path is not None:
                result["artifact_path"] = artifact_path
                # Provide escape hatch to full logs when output was truncated
                output_dict = result.get("output")
                if isinstance(output_dict, dict) and output_dict.get("truncated"):
                    output_dict["full_log_path"] = artifact_path

        if gate_id and not result["passed"]:
            result["hints"] = self._gate_hints(gate_id, gate, files)

        return result

    def _resolve_json_pointer(self, data: dict[str, object], pointer: str) -> object:
        """Resolve a JSON Pointer (RFC 6901) against parsed JSON data.

        Args:
            data: Parsed JSON data structure.
            pointer: JSON Pointer string (e.g., '/generalDiagnostics').

        Returns:
            The value at the pointer path, or None if not found.
        """
        if pointer == "/":
            return data

        segments = pointer.lstrip("/").split("/")
        current: object = data
        for segment in segments:
            if isinstance(current, dict):
                current = current.get(segment)
            elif isinstance(current, list):
                try:
                    current = current[int(segment)]
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current

    def _extract_violations_array(
        self,
        payload: list[dict[str, Any]] | dict[str, Any],
        parsing: JsonViolationsParsing,
    ) -> list[dict[str, Any]]:
        """Extract the violations array from *payload* using ``parsing.violations_path``.

        When ``violations_path`` is ``None`` the payload itself must be a list
        and is returned as-is.  When the path is given it is treated as a
        dot-separated key sequence that is used to descend into the dict.
        Returns an empty list when any step in the path is missing or the
        resolved value is not a list.

        Args:
            payload: Root JSON value – either a list (root-array tools) or a
                dict (tools that wrap diagnostics under a key).
            parsing: Provides ``violations_path``.

        Returns:
            The extracted list of violation dicts, or ``[]`` on any miss.
        """
        if parsing.violations_path is None:
            return payload if isinstance(payload, list) else []

        current: Any = payload
        for segment in parsing.violations_path.split("."):
            if not isinstance(current, dict):
                return []
            current = current.get(segment)
            if current is None:
                return []

        return current if isinstance(current, list) else []

    @staticmethod
    def _resolve_field_path(item: dict[str, Any], path: str) -> Any:  # noqa: ANN401
        """Resolve a field value from *item* using a flat or nested *path*.

        A path without ``/`` is a flat key lookup: ``item.get(path)``.
        A path with ``/`` is a nested lookup: each segment descends one level
        into the dict.  Returns ``None`` if any intermediate key is absent or
        the value is not a dict.

        Args:
            item: The JSON object to extract from.
            path: Dot-free path where ``/`` separates nesting levels.

        Returns:
            The resolved value, or ``None`` if the path cannot be traversed.
        """
        if "/" not in path:
            return item.get(path)
        current: Any = item
        for segment in path.split("/"):
            if not isinstance(current, dict):
                return None
            current = current.get(segment)
        return current

    def _parse_json_violations(
        self,
        payload: list[dict[str, Any]],
        parsing: JsonViolationsParsing,
    ) -> list[ViolationDTO]:
        """Map a root-array JSON payload to a list of ViolationDTOs.

        Each item in *payload* is a flat dict or nested object.
        The ``parsing.field_map`` maps ViolationDTO field names to the
        corresponding key path in the item.  A path containing ``/`` is
        resolved as a nested lookup; plain keys use flat ``dict.get`` access.
        Missing keys result in ``None`` for optional fields.
        The ``fixable`` field is determined by truthiness of the mapped value.

        Args:
            payload: List of parsed JSON objects (root-array format).
            parsing: Describes how to extract fields from each item.

        Returns:
            List of ViolationDTO instances.
        """
        result: list[ViolationDTO] = []
        resolve = self._resolve_field_path
        for item in payload:
            fmap = parsing.field_map
            fixable_key = fmap.get("fixable")
            fixable_val = resolve(item, fixable_key) if fixable_key else None
            result.append(
                ViolationDTO(
                    file=resolve(item, fmap["file"]) if "file" in fmap else None,
                    message=resolve(item, fmap["message"]) if "message" in fmap else None,
                    line=resolve(item, fmap["line"]) if "line" in fmap else None,
                    col=resolve(item, fmap["col"]) if "col" in fmap else None,
                    rule=resolve(item, fmap["rule"]) if "rule" in fmap else None,
                    fixable=bool(fixable_val),
                    severity=None,
                )
            )
        return result

    def _parse_json_field_issues(
        self, output: str, diagnostics_path: str | None = None
    ) -> list[dict[str, Any]]:
        """Best-effort JSON diagnostic parsing.

        This is primarily intended for pyright-like tools that emit JSON diagnostics.

        Args:
            output: Raw JSON string from tool stdout/stderr.
            diagnostics_path: Optional JSON Pointer (RFC 6901) to diagnostics array.
                Falls back to 'generalDiagnostics' when not provided.
        """

        try:
            data = json.loads(output)
        except (json.JSONDecodeError, TypeError, ValueError):
            # If output isn't JSON, surface as plain issue.
            text = output.strip()
            return [{"message": text}] if text else []

        if diagnostics_path:
            diagnostics = self._resolve_json_pointer(data, diagnostics_path)
        else:
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

    def _extract_json_fields(self, output: str, gate: QualityGate) -> dict[str, object]:
        """Extract named fields from JSON output using configured pointers.

        Uses the ``fields`` mapping from ``JsonFieldParsing`` config to resolve
        each named field via its JSON Pointer path.

        Args:
            output: Raw JSON string from tool output.
            gate: Gate config; only ``json_field`` parsing has ``fields``.

        Returns:
            Dict of field_name → resolved_value. Empty if parsing fails or
            no ``fields`` configured.
        """
        fields_config: dict[str, str] = getattr(gate.parsing, "fields", {})
        if not fields_config:
            return {}

        try:
            data = json.loads(output)
        except (json.JSONDecodeError, TypeError, ValueError):
            return {}

        extracted: dict[str, object] = {}
        for field_name, pointer in fields_config.items():
            value = self._resolve_json_pointer(data, pointer)
            if value is not None:
                extracted[field_name] = value
        return extracted

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

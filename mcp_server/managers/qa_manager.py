"""QA Manager for quality gates."""

from __future__ import annotations

import json
import os
import platform
import re
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
    TextViolationsParsing,
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

    def __init__(self, workspace_root: Path | None = None) -> None:
        """Initialize QA Manager with default runtime configuration."""
        # Runtime configuration (lowercase for instance mutability)
        self.qa_log_dir = self.QA_LOG_DIR
        self.qa_log_enabled = self.QA_LOG_ENABLED
        self.qa_log_max_files = self.QA_LOG_MAX_FILES
        # Optional workspace root: used for baseline state persistence in .st3/state.json
        self.workspace_root = workspace_root

    def run_quality_gates(self, files: list[str]) -> dict[str, Any]:
        """Run configured quality gates on specified files.

        Returns v2.0 JSON schema with version, mode, summary, and gates.

        Notes:
            - Gate catalog and active gates are defined in `.st3/quality.yaml`.
            - Each gate filters files by its configured `capabilities.file_types`.
            - Some gates (e.g., pytest) are repo-scoped and ignore file lists.
        """
        mode = "file-specific" if files else "project-level"

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

        # Validate file existence
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

        python_files = list(files)

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
            skip_reason = self._get_skip_reason(gate_files)
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

        # Persist baseline state: advance SHA on all-pass, accumulate failed_files on failure.
        if results["overall_pass"]:
            self._advance_baseline_on_all_pass()
        else:
            self._accumulate_failed_files_on_failure(files)

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

    # ------------------------------------------------------------------
    # Baseline state management
    # ------------------------------------------------------------------

    def _advance_baseline_on_all_pass(self) -> None:
        """Persist current HEAD as baseline_sha and reset failed_files on all-pass run.

        Only executed when workspace_root is set. Reads/writes .st3/state.json in-place,
        touching only the quality_gates sub-key to avoid overwriting workflow phase data.
        """
        if self.workspace_root is None:
            return

        head_sha = self._get_head_sha()
        if head_sha is None:
            return

        state_path = self.workspace_root / ".st3" / "state.json"
        state_data = self._load_state_json(state_path)
        state_data["quality_gates"] = {
            "baseline_sha": head_sha,
            "failed_files": [],
        }
        self._save_state_json(state_path, state_data)

    def _accumulate_failed_files_on_failure(self, newly_failed: list[str]) -> None:
        """Union newly-failed files with persisted failed_files; leave baseline_sha unchanged.

        Only executed when workspace_root is set and at least one gate failed.
        Ensures deterministic sort and no duplicates in the persisted list.
        """
        if self.workspace_root is None:
            return

        state_path = self.workspace_root / ".st3" / "state.json"
        state_data = self._load_state_json(state_path)

        quality_gates: dict[str, Any] = state_data.get("quality_gates", {})
        existing = set(quality_gates.get("failed_files", []))
        merged = sorted(existing | set(newly_failed))

        quality_gates["failed_files"] = merged
        state_data["quality_gates"] = quality_gates
        self._save_state_json(state_path, state_data)

    def _get_head_sha(self) -> str | None:
        """Return the current git HEAD commit SHA, or None on error."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except OSError:
            pass
        return None

    @staticmethod
    def _load_state_json(state_path: Path) -> dict[str, Any]:
        """Read state.json from disk, returning empty dict when absent or malformed."""
        if not state_path.exists():
            return {}
        try:
            return dict(json.loads(state_path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return {}

    @staticmethod
    def _save_state_json(state_path: Path, data: dict[str, Any]) -> None:
        """Atomically write data to state.json (creates parent dirs if needed)."""
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Scope resolution
    # ------------------------------------------------------------------

    def _resolve_scope(self, scope: str) -> list[str]:
        """Resolve scope keyword to a sorted, deduplicated list of relative file paths.

        Args:
            scope: One of ``"project"``, ``"branch"``, or ``"auto"``.

        Returns:
            Sorted list of relative paths (POSIX separators) for the given scope.
            Returns ``[]`` gracefully when workspace_root is absent or config is missing.
        """
        if scope == "project":
            return self._resolve_project_scope()
        if scope == "branch":
            return self._resolve_branch_scope()
        if scope == "auto":
            return self._resolve_auto_scope()
        return []

    def _git_diff_py_files(self, base_ref: str) -> list[str]:
        """Run ``git diff --name-only <base_ref>..HEAD`` and return ``.py`` files.

        Args:
            base_ref: The git ref to diff against (e.g. a branch name or commit SHA).

        Returns:
            Sorted list of ``.py`` paths from the diff output. Empty on error or
            when the diff contains no Python files.
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", f"{base_ref}..HEAD"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return []
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return sorted(line for line in lines if line.endswith(".py"))
        except OSError:
            return []

    def _resolve_branch_scope(self) -> list[str]:
        """Return Python files changed since the parent branch via git diff.

        The parent branch is read from ``workflow.parent_branch`` in
        ``.st3/state.json``.  Falls back to ``"main"`` when the key is absent
        or the state file cannot be loaded.

        Returns:
            Sorted list of ``.py`` file paths (relative POSIX). Empty list on error
            or when the diff is empty.
        """
        parent = "main"
        if self.workspace_root is not None:
            state = self._load_state_json(self.workspace_root / ".st3" / "state.json")
            parent = state.get("workflow", {}).get("parent_branch") or "main"
        return self._git_diff_py_files(parent)

    def _resolve_auto_scope(self) -> list[str]:
        """Return union of git diff (``baseline_sha..HEAD``) and persisted ``failed_files``.

        Reads ``quality_gates.baseline_sha`` and ``quality_gates.failed_files``
        from ``.st3/state.json``.

        Returns:
            Sorted, deduplicated list of ``.py`` paths. Returns ``[]`` when
            workspace_root is absent or no ``baseline_sha`` is recorded (C24
            handles the no-baseline fallback).
        """
        if self.workspace_root is None:
            return []

        state = self._load_state_json(self.workspace_root / ".st3" / "state.json")
        quality_gates: dict[str, Any] = state.get("quality_gates", {})
        baseline_sha: str | None = quality_gates.get("baseline_sha") or None
        if not baseline_sha:
            return self._resolve_project_scope()

        diff_files = set(self._git_diff_py_files(baseline_sha))
        failed_files = set(quality_gates.get("failed_files", []))
        union = diff_files | failed_files
        return sorted(union)

    def _resolve_project_scope(self) -> list[str]:
        """Expand project_scope.include_globs against workspace_root.

        Returns:
            Sorted list of unique relative POSIX paths. Empty list when
            workspace_root is None, include_globs is empty, or nothing matches.
        """
        if self.workspace_root is None:
            return []

        quality_config = QualityConfig.load()
        project_scope = quality_config.project_scope
        if project_scope is None or not project_scope.include_globs:
            return []

        matched: set[str] = set()
        for glob_pattern in project_scope.include_globs:
            for abs_path in self.workspace_root.glob(glob_pattern):
                if abs_path.is_file():
                    rel = abs_path.relative_to(self.workspace_root)
                    matched.add(rel.as_posix())

        return sorted(matched)

    # ------------------------------------------------------------------
    # Output formatting
    # ------------------------------------------------------------------

    @staticmethod
    def _format_summary_line(results: dict[str, Any]) -> str:
        """Return a concise one-line status string for the given gate results.

        Format (design.md §4.8):
        - Pass:      ``"✅ Quality gates: N/N passed (0 violations)"``
        - Fail:      ``"❌ Quality gates: N/M passed — V violations in gate_id[, ...]"``
        - Skip+pass: ``"⚠️ Quality gates: N/N active (S skipped)"``

        Args:
            results: The dict returned by ``run_quality_gates``.

        Returns:
            A single-line string suitable for ``content[0].text`` in a ToolResult.
        """
        summary = results["summary"]
        passed: int = summary["passed"]
        failed: int = summary["failed"]
        skipped: int = summary["skipped"]
        total_violations: int = summary["total_violations"]
        total_active = passed + failed

        if failed > 0:
            failed_names = [
                g["name"] for g in results.get("gates", []) if g.get("status") == "failed"
            ]
            gate_list = ", ".join(failed_names)
            return (
                f"❌ Quality gates: {passed}/{total_active} passed"
                f" — {total_violations} violations in {gate_list}"
            )

        if skipped > 0:
            return f"⚠️ Quality gates: {passed}/{total_active} active ({skipped} skipped)"

        return f"✅ Quality gates: {passed}/{total_active} passed ({total_violations} violations)"

    @staticmethod
    def _build_compact_result(results: dict[str, Any]) -> dict[str, Any]:
        """Return a compact gate payload with violations only — no debug fields.

        Design contract (design.md §4.9):
        ``{"gates": [{"id": str, "passed": bool, "skipped": bool, "violations": list}]}``

        Args:
            results: The dict returned by ``run_quality_gates``.

        Returns:
            Compact payload suitable for ``content[1].json`` in a ToolResult.
        """
        compact_gates = []
        for gate in results.get("gates", []):
            compact_gates.append(
                {
                    "id": str(gate.get("name", gate.get("id", ""))),
                    "passed": bool(gate.get("passed", False)),
                    "skipped": gate.get("status") == "skipped",
                    "violations": gate.get("issues", []),
                }
            )
        return {"gates": compact_gates}

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
        """Determine which files should be passed to a gate based on file_types capability."""
        eligible = [
            f
            for f in python_files
            if any(str(f).endswith(ext) for ext in gate.capabilities.file_types)
        ]

        if gate.scope is not None:
            eligible = gate.scope.filter_files(eligible)

        return eligible

    def _get_skip_reason(self, gate_files: list[str]) -> str | None:
        """Return skip reason for a gate, or None if it should run.

        A gate is skipped when no files match its configured file_types.
        """
        if not gate_files:
            return "Skipped (no matching files)"
        return None

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

            if gate.capabilities.parsing_strategy == "json_violations":
                raw: list[dict[str, Any]] | dict[str, Any] = json.loads(proc.stdout or "[]")
                violations = self._parse_json_violations(
                    self._extract_violations_array(raw, gate.capabilities.json_violations),
                    gate.capabilities.json_violations,
                )
                result["issues"] = [
                    {
                        "message": v.message,
                        "file": v.file,
                        "line": v.line,
                        "col": v.col,
                        "rule": v.rule,
                        "severity": v.severity,
                        "fixable": v.fixable,
                    }
                    for v in violations
                ]
                result["passed"] = len(violations) == 0
                result["score"] = (
                    "Pass" if result["passed"] else f"Fail ({len(violations)} violations)"
                )

            elif gate.capabilities.parsing_strategy == "text_violations":
                text_violations = self._parse_text_violations(
                    proc.stdout or "", gate.capabilities.text_violations
                )
                result["issues"] = [
                    {
                        "message": v.message,
                        "file": v.file,
                        "line": v.line,
                        "col": v.col,
                        "rule": v.rule,
                        "severity": v.severity,
                        "fixable": v.fixable,
                    }
                    for v in text_violations
                ]
                result["passed"] = len(text_violations) == 0
                result["score"] = (
                    "Pass" if result["passed"] else f"Fail ({len(text_violations)} violations)"
                )

            elif gate.parsing.strategy == "exit_code":
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

    def _parse_text_violations(
        self,
        output: str,
        parsing: TextViolationsParsing,
    ) -> list[ViolationDTO]:
        """Parse line-based tool output into ViolationDTOs using a named-group regex.

        Each line of *output* is matched against ``parsing.pattern``.  Lines
        that do not match are silently skipped.  Named groups in the pattern
        map directly to ViolationDTO fields:
        ``file``, ``line``, ``col``, ``rule``, ``message``, ``severity``.

        ``line`` and ``col`` groups are converted to ``int`` when present.
        The ``severity`` group falls back to ``parsing.severity_default`` when
        absent from the pattern or not captured on a given line.

        When a group is absent or None, ``parsing.defaults`` is consulted.
        Default values may contain ``{placeholder}`` references to other
        captured group names; those are resolved via ``str.format_map``.

        Args:
            output: Raw stdout/stderr from a quality gate tool.
            parsing: Pattern and defaults for text-based parsing.

        Returns:
            List of ViolationDTO instances, one per matching line.
        """
        pattern = re.compile(parsing.pattern)
        result: list[ViolationDTO] = []
        for raw_line in output.splitlines():
            m = pattern.search(raw_line)
            if m is None:
                continue
            groups = m.groupdict()
            # Safe mapping for interpolation: replace None with "" so format_map works
            safe_groups = {k: (v or "") for k, v in groups.items()}

            raw_line_num = self._resolve_text_field("line", groups, safe_groups, parsing.defaults)
            raw_col_num = self._resolve_text_field("col", groups, safe_groups, parsing.defaults)
            result.append(
                ViolationDTO(
                    file=self._resolve_text_field("file", groups, safe_groups, parsing.defaults),
                    message=self._resolve_text_field(
                        "message", groups, safe_groups, parsing.defaults
                    ),
                    line=int(raw_line_num) if raw_line_num is not None else None,
                    col=int(raw_col_num) if raw_col_num is not None else None,
                    rule=self._resolve_text_field("rule", groups, safe_groups, parsing.defaults),
                    fixable=False,
                    severity=self._resolve_text_field(
                        "severity", groups, safe_groups, parsing.defaults
                    )
                    or parsing.severity_default,
                )
            )
        return result

    @staticmethod
    def _resolve_text_field(
        field: str,
        groups: dict[str, str | None],
        safe_groups: dict[str, str],
        defaults: dict[str, str],
    ) -> str | None:
        """Return captured group value or an interpolated default for *field*.

        Priority: captured group value (non-None) → defaults[field] with
        {placeholder} interpolation via safe_groups → None.
        """
        val = groups.get(field)
        if val is not None:
            return val
        template = defaults.get(field)
        if template is None:
            return None
        try:
            return template.format_map(safe_groups) or None
        except KeyError:
            return None

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

        ``parsing.line_offset`` is added to the extracted line number (useful
        for tools that report 0-based lines).

        ``parsing.fixable_when`` overrides ``field_map["fixable"]``: when set,
        the named source key is used for the truthy fixable check.

        Args:
            payload: List of parsed JSON objects (root-array format).
            parsing: Describes how to extract fields from each item.

        Returns:
            List of ViolationDTO instances.
        """
        result: list[ViolationDTO] = []
        resolve = self._resolve_field_path
        fixable_key = parsing.fixable_when or parsing.field_map.get("fixable")
        for item in payload:
            fmap = parsing.field_map
            raw_line = resolve(item, fmap["line"]) if "line" in fmap else None
            line = (raw_line + parsing.line_offset) if isinstance(raw_line, int) else raw_line
            fixable_val = resolve(item, fixable_key) if fixable_key else None
            result.append(
                ViolationDTO(
                    file=resolve(item, fmap["file"]) if "file" in fmap else None,
                    message=resolve(item, fmap["message"]) if "message" in fmap else None,
                    line=line,
                    col=resolve(item, fmap["col"]) if "col" in fmap else None,
                    rule=resolve(item, fmap["rule"]) if "rule" in fmap else None,
                    fixable=bool(fixable_val),
                    severity=None,
                )
            )
        return result

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

"""QA Manager for quality gates."""

from __future__ import annotations

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server.core.interfaces import IGitContextReader, IQualityStateRepository, IStateReader
    from mcp_server.schemas.tool_outputs import AutoFixOutput
from mcp_server.managers.state_repository import StateBranchMismatchError
from mcp_server.schemas import (
    QualityConfig,
    QualityGate,
)
from mcp_server.utils.path_resolver import resolve_input_paths
from mcp_server.utils.violation_parser import ViolationParser

logger = logging.getLogger(__name__)

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

    _quality_config: QualityConfig | None

    @property
    def quality_config(self) -> QualityConfig | None:
        """Return the injected quality configuration."""
        return self._quality_config

    # Default configuration (UPPERCASE constants for test mocking compatibility)
    QA_LOG_DIR = Path("temp/qa_logs")
    QA_LOG_ENABLED = True

    def _require_quality_config(self) -> QualityConfig:
        """Return the injected quality configuration."""
        quality_config = self._quality_config
        if quality_config is None:
            raise ValueError("QualityConfig must be injected for quality-gate execution")
        return quality_config

    QA_LOG_MAX_FILES = DEFAULT_ARTIFACT_LOG_MAX_FILES

    def __init__(
        self,
        workspace_root: Path | None = None,
        quality_config: QualityConfig | None = None,
        logs_dir: Path | None = None,
        *,
        quality_state_repository: IQualityStateRepository,
        git_context_reader: IGitContextReader,
        state_reader: IStateReader,
    ) -> None:
        """Initialize QA Manager with injected quality configuration."""
        # Runtime configuration (lowercase for instance mutability)
        self.qa_log_dir = (logs_dir / "qa_logs") if logs_dir is not None else self.QA_LOG_DIR
        self.qa_log_enabled = self.QA_LOG_ENABLED
        self.qa_log_max_files = self.QA_LOG_MAX_FILES
        # Optional workspace root: used for baseline state persistence
        self.workspace_root = workspace_root
        self._quality_config = quality_config
        self._quality_state_repository = quality_state_repository
        self._git_context_reader = git_context_reader
        self._state_reader = state_reader

    def run_quality_gates(
        self,
        files: list[str],
        effective_scope: str = "auto",
        verbose: bool = False,
    ) -> dict[str, Any]:
        """Run configured quality gates on specified files.

        Returns v2.0 JSON schema with version, mode, summary, and gates.

        Notes:
            - Gate catalog and active gates are defined in `config/quality.yaml`.
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

        # Validate file existence. Mixed explicit file lists can legitimately contain
        # deleted branch-diff paths; keep validating the remaining existing files.
        existing_files = [f for f in files if Path(f).exists()]
        missing_files = [f for f in files if not Path(f).exists()]
        if missing_files and not existing_files:
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

        python_files = list(existing_files)
        quality_config = self._require_quality_config()
        # Apply artifact logging config (config-first with safe defaults)
        self.qa_log_enabled = quality_config.artifact_logging.enabled
        if quality_config.artifact_logging.output_dir is not None:
            self.qa_log_dir = Path(quality_config.artifact_logging.output_dir)
        # else: keep injected logs_dir / "qa_logs" set in __init__
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
                            "message": "No active_gates configured in config/quality.yaml",
                        }
                    ],
                },
            )
            return results

        gate_catalog = quality_config.gates

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

            gate_files = self.files_for_gate(gate, python_files)
            skip_reason = "Skipped (no matching files)" if not gate_files else None
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
            if verbose:
                gate_result = self.execute_gate(
                    gate, gate_files, gate_number=idx, gate_id=gate_id, verbose=True
                )
            else:
                gate_result = self.execute_gate(gate, gate_files, gate_number=idx, gate_id=gate_id)
            self._update_summary_and_append_gate(results, gate_result)

        # Build top-level timing breakdown (Improvement E)
        timings: dict[str, int] = {}
        for gate_result in results["gates"]:
            gate_id_key = str(gate_result.get("gate_number", gate_result.get("id", "?")))
            timings[gate_id_key] = gate_result.get("duration_ms", 0)
        timings["total"] = sum(timings.values())
        results["timings"] = timings

        # Persist baseline state only for auto-scope lifecycle runs.
        if self._is_auto_lifecycle_scope(effective_scope):
            if results["overall_pass"]:
                self._advance_baseline_on_all_pass()
            else:
                failed_subset = self._collect_failed_files_from_results(results, files)
                self._accumulate_failed_files_on_failure(failed_subset)

        return results

    def _update_summary_and_append_gate(
        self, results: dict[str, Any], gate_result: dict[str, Any]
    ) -> None:
        """Add gate result and update summary counts + violation totals."""
        results["gates"].append(gate_result)

        # Use status field if present, else infer from passed/score (backward compat)
        status = self._resolve_gate_status(gate_result)
        gate_result["status"] = status

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

    @staticmethod
    def _resolve_gate_status(gate_result: dict[str, Any]) -> str:
        """Resolve canonical gate status (passed/failed/skipped) from gate payload."""
        status = gate_result.get("status")
        if isinstance(status, str):
            return status

        if gate_result.get("passed"):
            score = gate_result.get("score", "")
            if isinstance(score, str) and "Skipped" in score:
                return "skipped"
            return "passed"
        return "failed"

    @staticmethod
    def _is_auto_lifecycle_scope(scope: str) -> bool:
        """Return True when baseline lifecycle mutation is allowed for this scope."""
        return scope.strip().lower() == "auto"

    @staticmethod
    def _collect_failed_files_from_results(
        results: dict[str, Any], evaluated_files: list[str]
    ) -> list[str]:
        """Extract failing-file subset from gate results; fallback to evaluated set.

        Prefers explicit issue-level ``file`` references from failed gates.
        If no file-level references are present, conservatively falls back to
        the evaluated set to avoid dropping failure signal.
        """
        evaluated_set = set(evaluated_files)
        failed_files: set[str] = set()

        for gate in results.get("gates", []):
            status = QAManager._resolve_gate_status(gate)
            if status != "failed":
                continue

            for issue in gate.get("issues", []):
                file_path = issue.get("file")
                if isinstance(file_path, str) and file_path in evaluated_set:
                    failed_files.add(file_path)

        if failed_files:
            return sorted(failed_files)
        return sorted(evaluated_set)

    # ------------------------------------------------------------------
    # Baseline state management
    # ------------------------------------------------------------------

    def _advance_baseline_on_all_pass(self) -> None:
        """Persist current HEAD as baseline_sha and reset failed_files on all-pass run."""
        head_sha = self._get_head_sha()
        if head_sha is None:
            return
        from mcp_server.state.quality_state import QualityState  # noqa: PLC0415

        self._quality_state_repository.apply(
            lambda _s: QualityState(baseline_sha=head_sha, failed_files=[])
        )

    def _accumulate_failed_files_on_failure(self, newly_failed: list[str]) -> None:
        """Union newly-failed files with persisted failed_files; leave baseline_sha unchanged."""
        from mcp_server.state.quality_state import QualityState  # noqa: PLC0415

        def _union(s: QualityState) -> QualityState:
            merged = sorted(set(s.failed_files) | set(newly_failed))
            return QualityState(baseline_sha=s.baseline_sha, failed_files=merged)

        self._quality_state_repository.apply(_union)

    def _get_head_sha(self) -> str | None:
        """Return the current git HEAD commit SHA, or None on error."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except OSError:
            pass
        return None

    # ------------------------------------------------------------------
    # Scope resolution
    # ------------------------------------------------------------------

    def resolve_scope(self, scope: str, files: list[str] | None = None) -> list[str]:
        """Resolve scope keyword to a sorted, deduplicated list of relative file paths.

        Args:
            scope: One of ``"project"``, ``"branch"``, ``"auto"``, or ``"files"``.
            files: Required when ``scope="files"``; the caller-supplied explicit
                file or directory list. Directories are expanded to ``.py`` files;
                missing paths surface a warning and are excluded.

        Returns:
            Sorted list of relative paths (POSIX separators) for the given scope.
            Returns ``[]`` gracefully when workspace_root is absent or config is missing.
        """
        if scope == "files":
            if not files:
                return []
            if self.workspace_root is None:
                return sorted(set(files))
            resolved, warnings = resolve_input_paths(files, self.workspace_root)
            for w in warnings:
                logger.warning(w)
            return resolved
        if scope == "project":
            return self._resolve_project_scope()
        if scope == "branch":
            return self._resolve_branch_scope()
        if scope == "auto":
            return self._resolve_auto_scope()
        return []

    def _resolve_branch_scope(self) -> list[str]:
        """Return Python files changed on this branch since merge-base with parent.

        The parent branch is read from ``parent_branch`` in the persisted
        ``BranchState`` loaded via ``IStateReader``. Falls back to ``"main"``
        when state is absent or the field is unset.

        Uses merge-base semantics (``parent...HEAD``) to isolate branch-introduced
        changes and avoid noise from parent tip drift.

        Returns:
            Sorted list of ``.py`` file paths (relative POSIX). Empty list on error
            or when the diff is empty.
        """
        branch = self._git_context_reader.get_current_branch()
        parent = "main"
        try:
            state = self._state_reader.load(branch)
            parent = state.parent_branch or "main"
        except (KeyError, FileNotFoundError, StateBranchMismatchError, OSError):
            pass
        return self._git_diff_py_files(parent, use_merge_base=True)

    def _resolve_auto_scope(self) -> list[str]:
        """Return union of git diff (``baseline_sha..HEAD``) and persisted ``failed_files``.

        Returns:
            Sorted, deduplicated list of ``.py`` paths. Returns project scope when
            no ``baseline_sha`` is recorded (C24 handles the no-baseline fallback).
        """
        state = self._quality_state_repository.load()
        baseline_sha = state.baseline_sha
        if not baseline_sha:
            return self._resolve_project_scope()
        diff_files = set(self._git_diff_py_files(baseline_sha))
        failed_files = set(state.failed_files)
        return sorted(diff_files | failed_files)

    def _git_diff_py_files(self, base_ref: str, *, use_merge_base: bool = False) -> list[str]:
        """Run git diff and return changed ``.py`` files.

        Args:
            base_ref: The git ref to diff against (branch name or commit SHA).
            use_merge_base: When True, use ``base_ref...HEAD`` (merge-base semantics).
                When False, use ``base_ref..HEAD`` (tip-to-tip semantics).

        Returns:
            Sorted list of ``.py`` paths from diff output. Empty on error or
            when the diff contains no Python files.
        """
        diff_ref = f"{base_ref}...HEAD" if use_merge_base else f"{base_ref}..HEAD"
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=d", diff_ref],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                return []
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            return sorted(line for line in lines if line.endswith(".py"))
        except FileNotFoundError:
            return []

    def _resolve_project_scope(self) -> list[str]:
        """Expand project_scope.include_globs against workspace_root.

        Returns:
            Sorted list of unique relative POSIX paths. Empty list when
            workspace_root is None, include_globs is empty, or nothing matches.
        """
        if self.workspace_root is None:
            return []

        quality_config = self._require_quality_config()
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

    # TODO: [Phase 2] Summary formatting logic will be refactored to align with text presenter
    @staticmethod
    def format_summary_line(
        results: dict[str, Any],
        scope: str | None = None,
        file_count: int | None = None,
    ) -> str:
        """Return a concise one-line status string for the given gate results.

        Format (design.md §4.8, C39 additions):
        - All-skipped:  ``"✅ Nothing to check (no changed files)[scope_part] — Nms"``
        - Pass:         ``"✅ Quality gates: N/N passed (V violations)[scope_part] — Nms"``
        - Fail:         ``"❌ Quality gates: N/M passed — V violations in
          gate_id[scope_part] — Nms"``
        - Skip+pass:    ``"⚠️ Quality gates: N/N active (S skipped)[scope_part] — Nms"``

        C39 additions (F-1, F-19, duration_ms):
        - F-1: all gates skipped → ✅ "Nothing to check" instead of ⚠️.
        - F-19: optional ``scope`` and ``file_count`` appended as ``[scope · N files]``.
        - duration_ms appended as `` — Nms`` suffix (taken from ``results["timings"]["total"]``).

        Args:
            results: The dict returned by ``run_quality_gates``.
            scope: Optional scope keyword (``"auto"``, ``"branch"``, ``"project"``, ``"files"``).
            file_count: Number of files resolved for this scope run.

        Returns:
            A single-line string suitable for ``content[0].text`` in a ToolResult.
        """
        summary = results["summary"]
        passed: int = summary["passed"]
        failed: int = summary["failed"]
        skipped: int = summary["skipped"]
        total_violations: int = summary["total_violations"]
        total_active = passed + failed

        duration_ms: int = int(results.get("timings", {}).get("total", 0))
        duration_part = f" — {duration_ms}ms"

        scope_part = ""
        if scope is not None:
            if file_count is not None:
                scope_part = f" [{scope} · {file_count} files]"
            else:
                scope_part = f" [{scope}]"

        # F-1: all gates skipped = clean empty-diff state — no attention needed
        if passed == 0 and failed == 0 and skipped > 0:
            return f"✅ Nothing to check (no changed files){scope_part}{duration_part}"

        if failed > 0:
            failed_names = [
                g["name"] for g in results.get("gates", []) if g.get("status") == "failed"
            ]
            gate_list = ", ".join(failed_names)
            return (
                f"❌ Quality gates: {passed}/{total_active} passed"
                f" — {total_violations} violations in {gate_list}{scope_part}{duration_part}"
            )

        if skipped > 0:
            return (
                f"⚠️ Quality gates: {passed}/{total_active} active"
                f" ({skipped} skipped){scope_part}{duration_part}"
            )

        return (
            f"✅ Quality gates: {passed}/{total_active} passed"
            f" ({total_violations} violations){scope_part}{duration_part}"
        )

    def normalize_file_path(self, path: str | None) -> str | None:
        """Normalize a violation file path to workspace-relative POSIX form (C36 / F-15).

        Rules:
        - ``None`` → ``None``
        - Absolute path with ``workspace_root`` set → relative POSIX via
          :meth:`pathlib.PurePath.relative_to`; falls back to POSIX absolute
          when the path escapes the workspace root.
        - Absolute path without ``workspace_root`` → POSIX absolute (forward slashes).
        - Relative path (any OS separators) → forward-slash form only.

        Args:
            path: Raw file path string from a gate violation.

        Returns:
            Canonical workspace-relative POSIX string, or ``None`` when input is ``None``.
        """
        if path is None:
            return None
        p = Path(path)
        if p.is_absolute():
            if self.workspace_root is not None:
                try:
                    return p.relative_to(self.workspace_root).as_posix()
                except ValueError:
                    return p.as_posix()
            return p.as_posix()
        # Relative path: just normalize OS separators to POSIX forward slashes.
        return str(path).replace("\\", "/")

    def build_compact_result(self, results: dict[str, Any]) -> dict[str, Any]:
        """Return a compact gate payload with violations only — no debug fields.

        Design contract (design.md §4.9 / C26 + C35 + C39):
        ``{
            "overall_pass": bool,
            "gates": [{"id": str, "passed": bool, "skipped": bool,
                        "status": str, "violations": list}]
        }``

        C35 additions (F-2, F-3):
        - ``overall_pass`` added at root level.
        - Per-gate ``status`` enum (``"passed"|"failed"|"skipped"``) added.

        C36 addition (F-15):
        - Each violation ``file`` field is normalized via
          :meth:`_normalize_file_path` to workspace-relative POSIX form.

        C39 change (duration_ms contract):
        - ``duration_ms`` removed from compact JSON root; it is now included
          in the summary line text via :meth:`_format_summary_line`.

        Args:
            results: The dict returned by ``run_quality_gates``.

        Returns:
            Compact payload suitable for ``content[1].json`` in a ToolResult.
        """
        compact_gates = []
        for gate in results.get("gates", []):
            gate_status: str = gate.get("status") or ("passed" if gate.get("passed") else "failed")
            raw_violations: list[dict[str, Any]] = gate.get("issues", [])
            normalized_violations = [
                {**v, "file": self.normalize_file_path(v.get("file"))} if "file" in v else v
                for v in raw_violations
            ]
            compact_gates.append(
                {
                    "id": str(gate.get("name", gate.get("id", ""))),
                    "passed": bool(gate.get("passed", False)),
                    "skipped": gate_status == "skipped",
                    "status": gate_status,
                    "violations": normalized_violations,
                }
            )
        return {
            "overall_pass": bool(results.get("overall_pass", True)),
            "gates": compact_gates,
        }

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

        # Convert file paths to workspace-relative POSIX format so that glob matching
        # (like ruff's --per-file-ignores) works correctly on all platforms (including Windows).
        rel_files = []
        for f in files:
            p = Path(f)
            if self.workspace_root is not None and p.is_absolute():
                try:
                    rel_files.append(p.relative_to(self.workspace_root).as_posix())
                except ValueError:
                    rel_files.append(p.as_posix())
            elif p.is_absolute():
                rel_files.append(p.as_posix())
            else:
                rel_files.append(str(f).replace("\\", "/"))

        return [*cmd, *rel_files]

    def files_for_gate(self, gate: QualityGate, python_files: list[str]) -> list[str]:
        """Determine which files should be passed to a gate based on file_types capability."""
        eligible = [
            f
            for f in python_files
            if any(str(f).endswith(ext) for ext in gate.capabilities.file_types)
        ]

        if gate.scope is not None:
            eligible = gate.scope.filter_files(eligible)

        return eligible

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

    def collect_environment_metadata(self, cmd: list[str]) -> dict[str, str]:
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

    def execute_gate(
        self,
        gate: QualityGate,
        files: list[str],
        gate_number: int,
        gate_id: str | None = None,
        verbose: bool = False,
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
            if verbose:
                details_parts = [f"Exit code: {proc.returncode}"]
                if proc.stdout:
                    details_parts.append(f"STDOUT:\n{proc.stdout}")
                if proc.stderr:
                    details_parts.append(f"STDERR:\n{proc.stderr}")
                result["details"] = "\n\n".join(details_parts)
            else:
                result["details"] = ""
            result["command"] = {
                "executable": cmd[0] if cmd else "",
                "args": cmd[1:] if len(cmd) > 1 else [],
                "cwd": gate.execution.working_dir,
                "exit_code": proc.returncode,
                "environment": self.collect_environment_metadata(cmd),
            }

            if gate.capabilities.parsing_strategy == "json_violations":
                assert gate.capabilities.json_violations is not None, (
                    "json_violations capabilities required when parsing_strategy='json_violations'"
                )
                exit_code_ok = proc.returncode in gate.success.exit_codes_ok
                raw: list[dict[str, Any]] | dict[str, Any] = json.loads(proc.stdout or "[]")
                violations = ViolationParser.parse_json_violations(
                    ViolationParser.extract_violations_array(
                        raw, gate.capabilities.json_violations
                    ),
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
                result["passed"] = exit_code_ok and len(violations) == 0
                if not exit_code_ok and not result["issues"]:
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
                result["score"] = (
                    "Pass"
                    if result["passed"]
                    else (
                        f"Fail (exit={proc.returncode})"
                        if not exit_code_ok
                        else f"Fail ({len(violations)} violations)"
                    )
                )

            elif gate.capabilities.parsing_strategy == "text_violations":
                assert gate.capabilities.text_violations is not None, (
                    "text_violations capabilities required when parsing_strategy='text_violations'"
                )
                exit_code_ok = proc.returncode in gate.success.exit_codes_ok
                text_violations = ViolationParser.parse_text_violations(
                    proc.stdout or "",
                    gate.capabilities.text_violations,
                    gate.capabilities.supports_autofix,
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
                result["passed"] = exit_code_ok and len(text_violations) == 0
                if not exit_code_ok and not result["issues"]:
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
                result["score"] = (
                    "Pass"
                    if result["passed"]
                    else (
                        f"Fail (exit={proc.returncode})"
                        if not exit_code_ok
                        else f"Fail ({len(text_violations)} violations)"
                    )
                )

            else:  # no parsing_strategy → pass/fail on exit code
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
        except subprocess.TimeoutExpired:
            result["passed"] = False
            result["score"] = "Timeout"
            result["issues"] = [{"message": f"{gate.name} timed out"}]
            result["details"] = (
                f"Timeout (after {gate.execution.timeout_seconds}s)" if verbose else ""
            )
        except FileNotFoundError as e:
            result["passed"] = False
            result["score"] = "Not Found"
            result["issues"] = [{"message": f"Tool not found: {e}"}]
            result["details"] = f"Tool not found: {e}" if verbose else ""

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

    # Parsing methods extracted to ViolationParser
    def run_auto_fix(
        self,
        scope: str = "auto",
        files: list[str] | None = None,
    ) -> AutoFixOutput:
        """Run all autofix-capable quality gates on files resolved for scope.

        Returns an AutoFixOutput DTO.
        """
        from mcp_server.schemas.tool_outputs import AutoFixOutput  # noqa: PLC0415

        # 1. Retrieve quality config and gates
        quality_config = self._require_quality_config()

        # 2. Filter gates where supports_autofix is True
        autofix_gates = {
            gate_id: gate
            for gate_id, gate in quality_config.gates.items()
            if gate.capabilities.supports_autofix
        }

        # 3. Resolve target files using _resolve_scope
        resolved_files = self.resolve_scope(scope, files)

        # 4. Track executed gates and before/after git status
        gates_executed: list[str] = []

        status_before = self._git_context_reader.get_status()
        before_dirty = set(status_before.get("modified_files", [])) | set(
            status_before.get("untracked_files", [])
        )
        # 5. Run fixers
        success = True
        error_message: str | None = None

        for gate in autofix_gates.values():
            # Filter files for the gate
            gate_files = self.files_for_gate(gate, resolved_files)
            if not gate_files:
                continue

            gates_executed.append(gate.name)

            # Resolve command and execute
            cmd = self._resolve_command(gate.execution.fix_command or [], gate_files)
            try:
                proc = subprocess.run(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=gate.execution.timeout_seconds,
                    check=False,
                    cwd=gate.execution.working_dir,
                )
                if proc.returncode not in gate.success.exit_codes_ok:
                    success = False
                    if not error_message:
                        error_message = (
                            f"Gate '{gate.name}' failed with exit code {proc.returncode}"
                        )
            except subprocess.TimeoutExpired:
                success = False
                if not error_message:
                    error_message = f"Gate '{gate.name}' timed out"
            except Exception as e:
                success = False
                if not error_message:
                    error_message = f"Gate '{gate.name}' failed: {e}"

        # 6. Detect modified/dirty files
        status_after = self._git_context_reader.get_status()
        after_dirty = set(status_after.get("modified_files", [])) | set(
            status_after.get("untracked_files", [])
        )

        # Include any file that became dirty, and any file that was dirty and target of resolving
        modified_files = sorted((after_dirty - before_dirty) | (after_dirty & set(resolved_files)))

        return AutoFixOutput(
            success=success,
            error_message=error_message,
            modified_files=modified_files,
            modified_files_count=len(modified_files),
            gates_executed=gates_executed,
            gates_executed_count=len(gates_executed),
        )

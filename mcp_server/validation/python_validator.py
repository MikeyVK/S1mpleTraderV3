"""Python validator implementation."""
import ast
import contextlib
import os
import tempfile
from typing import Any

from mcp_server.managers.qa_manager import QAManager

from .base import BaseValidator, ValidationIssue, ValidationResult


class PythonValidator(BaseValidator):
    """Validator for Python files using QAManager (Pylint/MyPy)."""

    def __init__(self, syntax_only: bool = False) -> None:
        """
        Initialize Python validator.

        Args:
            syntax_only: If True, only check syntax (for pre-write validation).
                        If False, run full QA gates (for post-write validation).
        """
        self.syntax_only = syntax_only
        if not syntax_only:
            self.qa_manager = QAManager()

    def __repr__(self) -> str:
        """Return string representation."""
        mode = "syntax_only" if self.syntax_only else "full_qa"
        return f"PythonValidator(mode={mode})"

    async def validate(self, path: str, content: str | None = None) -> ValidationResult:
        """
        Validate Python content.

        If content is provided, validates a temporary file to check before saving.
        If content is None:
          - In syntax_only mode: Cannot validate without content
          - In full QA mode: Runs quality gates on existing file at path
        """
        # Full QA mode with existing file (content=None, syntax_only=False)
        if content is None and not self.syntax_only:
            # Run quality gates directly on existing file
            result = self.qa_manager.run_quality_gates([path])
            return self._parse_result(result, original_path=path, scanned_path=path)

        # Read content if not provided (syntax_only mode requires content)
        if content is None:
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
            except OSError as e:
                return ValidationResult(
                    passed=False,
                    score=0.0,
                    issues=[ValidationIssue(f"Failed to read file: {e}")]
                )

        # Syntax-only mode for pre-write validation (fast, no config needed)
        if self.syntax_only:
            return self._validate_syntax(path, content)

        # Full QA mode for post-write validation (requires quality.yaml)
        return await self._validate_full_qa(path, content)

    def _validate_syntax(self, path: str, content: str) -> ValidationResult:
        """Fast syntax-only validation using ast.parse."""
        try:
            ast.parse(content, filename=path)
            return ValidationResult(passed=True, score=10.0, issues=[])
        except SyntaxError as e:
            issue = ValidationIssue(
                message=f"Python syntax error: {e.msg}",
                line=e.lineno,
                column=e.offset,
                severity="error"
            )
            return ValidationResult(passed=False, score=0.0, issues=[issue])

    async def _validate_full_qa(self, path: str, content: str) -> ValidationResult:
        """Full QA validation using quality gates (requires quality.yaml)."""
        scan_path = path
        temp_file = None

        try:
            # Write to temp file for QA gates
            dir_name = os.path.dirname(path) or "."
            os.makedirs(dir_name, exist_ok=True)

            fd, temp_file_path = tempfile.mkstemp(suffix=".py", dir=dir_name, text=True)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            scan_path = temp_file_path
            temp_file = temp_file_path

            # Run QA Manager
            result = self.qa_manager.run_quality_gates([scan_path])

            return self._parse_result(result, original_path=path, scanned_path=scan_path)

        finally:
            # Cleanup temp file
            if temp_file and os.path.exists(temp_file):
                with contextlib.suppress(OSError):
                    os.unlink(temp_file)

    def _parse_result(
        self, raw_result: dict[str, Any], original_path: str, scanned_path: str
    ) -> ValidationResult:
        """Convert QAManager dict to ValidationResult."""
        passed = raw_result.get("overall_pass", False)

        # Calculate score (average of gates or use linting score)
        # QAManager returns 'score' string like "10.00/10" for Linting
        score = 0.0
        lint_gate = next(
            (g for g in raw_result.get("gates", []) if g["name"] == "Linting"), None
        )
        if lint_gate and "score" in lint_gate:
            try:
                score_str = lint_gate["score"].split("/")[0]
                score = float(score_str)
            except (ValueError, IndexError):
                pass

        issues = []
        for gate in raw_result.get("gates", []):
            for issue in gate.get("issues", []):
                # Map scanned path back to original path in messages
                msg = issue.get("message", "")
                if scanned_path in msg:
                    msg = msg.replace(scanned_path, os.path.basename(original_path))

                issues.append(ValidationIssue(
                    message=f"[{gate['name']}] {msg}",
                    line=issue.get("line"),
                    column=issue.get("column"),
                    code=issue.get("code"),
                    severity="error"  # Everything failure in QA gate is an error for now
                ))

        return ValidationResult(
            passed=passed,
            score=score,
            issues=issues
        )


class PythonSyntaxValidator(PythonValidator):  # pylint: disable=too-few-public-methods
    """Python validator in syntax-only mode (for pre-write validation)."""

    def __init__(self) -> None:
        """Initialize with syntax_only=True."""
        super().__init__(syntax_only=True)

"""Python validator implementation."""
import os
import tempfile
from typing import Any

from mcp_server.managers.qa_manager import QAManager
from .base import BaseValidator, ValidationResult, ValidationIssue


class PythonValidator(BaseValidator):
    """Validator for Python files using QAManager (Pylint/MyPy)."""
    # pylint: disable=too-few-public-methods

    def __init__(self) -> None:
        """Initialize Python validator."""
        self.qa_manager = QAManager()

    async def validate(self, path: str, content: str | None = None) -> ValidationResult:
        """
        Validate Python content.
        
        If content is provided, validates a temporary file to check before saving.
        """
        scan_path = path
        temp_file = None

        try:
            # If content provided, write to temp file
            if content is not None:
                # Create temp file in same directory to preserve import context if possible,
                # or just use system temp if that's risky.
                # For import checking, being in the valid package structure matters.
                # Let's try to verify in-place if possible
                # (SafeEdit might imply we want to check *before* overwriting).
                # But creating a temp file in the same dir is best for pylint context.
                dir_name = os.path.dirname(path)
                # Create temp file with .py extension
                fd, temp_file_path = tempfile.mkstemp(suffix=".py", dir=dir_name, text=True)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                scan_path = temp_file_path
                temp_file = temp_file_path

            # Run QA Manager
            # Note: run_quality_gates is synchronous (subprocess calls)
            result = self.qa_manager.run_quality_gates([scan_path])

            return self._parse_result(result, original_path=path, scanned_path=scan_path)

        finally:
            # Cleanup temp file
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except OSError:
                    pass

    def _parse_result(self, raw_result: dict[str, Any], original_path: str, scanned_path: str) -> ValidationResult:
        """Convert QAManager dict to ValidationResult."""
        passed = raw_result.get("overall_pass", False)
        
        # Calculate score (average of gates or use linting score)
        # QAManager returns 'score' string like "10.00/10" for Linting
        score = 0.0
        lint_gate = next((g for g in raw_result.get("gates", []) if g["name"] == "Linting"), None)
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

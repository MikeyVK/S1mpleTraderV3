"""Markdown validator implementation."""
import re
from pathlib import Path

from .base import BaseValidator, ValidationResult, ValidationIssue


class MarkdownValidator(BaseValidator):
    """Validator for Markdown files."""

    def __init__(self) -> None:
        """Initialize Markdown validator."""
        self.link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        self.heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)

    def __repr__(self) -> str:
        """Return string representation."""
        return "MarkdownValidator()"

    async def validate(self, path: str, content: str | None = None) -> ValidationResult:
        """
        Validate Markdown content.

        Checks:
        1. Existence of H1 title.
        2. Broken local file links.
        """
        issues: list[ValidationIssue] = []
        file_path = Path(path)

        # Read content
        if content is None:
            if not file_path.exists():
                return ValidationResult(passed=False, score=0.0, issues=[
                    ValidationIssue("File not found")
                ])
            try:
                text = file_path.read_text(encoding="utf-8")
            except OSError as e:
                return ValidationResult(passed=False, score=0.0, issues=[
                    ValidationIssue(f"Failed to read file: {e}")
                ])
        else:
            text = content

        # Check 1: H1 Title
        h1_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if not h1_match:
            issues.append(ValidationIssue(
                message="Missing H1 title (start line with '# ')",
                severity="error"
            ))

        # Check 2: Broken Links
        # Only strict checks on relative file links, ignoring http/https/mailto
        for match in self.link_pattern.finditer(text):
            # link_text = match.group(1) # Unused
            link_target = match.group(2)

            # Skip external links and anchors
            if (link_target.startswith(("http:", "https:", "mailto:", "st3:")) or
                    link_target.startswith("#")):
                continue

            # Handle absolute paths (rare in md, but possible) or relative
            # If it looks like a file path...
            # Remove anchor if present
            target_file = link_target.split("#")[0]
            if not target_file:
                # Just an anchor like '#foo', we skipped it above unless it was localfile.md#foo
                continue

            # Check existence
            # Assuming relative to current file
            resolved_path = (file_path.parent / target_file).resolve()

            # Special case: The file itself might verify referencing images or other docs.
            # If strict check fails, flag it.
            if not resolved_path.exists():
                # Line calculation (approximate)
                line_no = text[:match.start()].count('\n') + 1
                issues.append(ValidationIssue(
                    message=f"Broken link: '{link_target}' not found at {resolved_path}",
                    line=line_no,
                    severity="warning"  # Warning for now, as context allows
                ))

        score = 10.0 if not issues else max(0.0, 10.0 - (len(issues) * 2))

        return ValidationResult(
            passed=not [i for i in issues if i.severity == "error"],
            score=score,
            issues=issues
        )

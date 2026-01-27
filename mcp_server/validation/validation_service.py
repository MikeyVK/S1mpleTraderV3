# mcp_server/validation/validation_service.py
"""
Validation service for orchestrating file validation.

@layer: Core
@dependencies: [ValidatorRegistry, BaseValidator, ValidationResult]
@responsibilities:
  - Register validators (extension-based and pattern-based)
  - Get applicable validators for a file with context-specific filtering
  - Run validation and aggregate results
  - Format validation issues for display
"""

# Standard library
import re
from pathlib import Path

# Project imports
from mcp_server.validation.base import BaseValidator
from mcp_server.validation.registry import ValidatorRegistry
from mcp_server.validation.python_validator import PythonSyntaxValidator
from mcp_server.validation.markdown_validator import MarkdownValidator
from mcp_server.validation.layered_template_validator import LayeredTemplateValidator
from mcp_server.validation.template_analyzer import TemplateAnalyzer


class ValidationService:
    """
    Orchestrates validation of files using registered validators.

    This service separates validation orchestration from file editing operations,
    following the Single Responsibility Principle. SafeEditTool delegates to
    this service for all validation concerns.

    Responsibilities:
    - Register validators (extension-based and pattern-based)
    - Get applicable validators for a file
    - Run validation and aggregate results
    - Apply context-specific filtering (test files, fallbacks)
    """

    def __init__(self) -> None:
        """Initialize validation service and register validators.
        
        Note: Lazy import of get_template_root to avoid circular dependency.
        """
        from mcp_server.config.template_config import get_template_root  # pylint: disable=import-outside-toplevel
        self.template_analyzer = TemplateAnalyzer(
            template_root=get_template_root()
        )
        self._setup_validators()

    def _setup_validators(self) -> None:
        """Register all validators with ValidatorRegistry."""
        # Register extension-based validators
        # For pre-write validation, use syntax-only mode (no quality.yaml needed)
        ValidatorRegistry.register(".py", PythonSyntaxValidator)
        ValidatorRegistry.register(".md", MarkdownValidator)

        # Register pattern-based validators using LayeredTemplateValidator
        ValidatorRegistry.register_pattern(
            r".*_workers?\.py$",
            LayeredTemplateValidator("worker", self.template_analyzer)
        )
        ValidatorRegistry.register_pattern(
            r".*_tools?\.py$",
            LayeredTemplateValidator("tool", self.template_analyzer)
        )
        ValidatorRegistry.register_pattern(
            r".*_dtos?\.py$",
            LayeredTemplateValidator("dto", self.template_analyzer)
        )
        ValidatorRegistry.register_pattern(
            r".*_adapters?\.py$",
            LayeredTemplateValidator("adapter", self.template_analyzer)
        )

    async def validate(self, path: str, content: str) -> tuple[bool, str]:
        """
        Validate file content using applicable validators.

        Args:
            path: File path to validate.
            content: File content to validate.

        Returns:
            Tuple of (passed, issues_text) where passed is True if all
            validators passed, and issues_text contains formatted validation
            issues (empty string if no issues).
        """
        validators = self._get_applicable_validators(path)
        return await self._run_validators(validators, path, content)

    def validate_syntax(self, path: str, content: str) -> tuple[bool, str]:
        """
        Lightweight syntax validation for pre-write checks.

        This performs fast syntax checks without heavy QA gates (no pylint/mypy).
        Used by ArtifactManager before writing scaffolded content.

        Args:
            path: File path (used to determine file type)
            content: Content to validate

        Returns:
            Tuple of (passed, issues_text)
        """
        # Determine validation based on file extension
        if path.endswith(".py"):
            # Python syntax check
            try:
                compile(content, path, "exec")
                return True, ""
            except SyntaxError as e:
                return False, f"❌ Python syntax error at line {e.lineno}: {e.msg}"

        elif path.endswith(".md"):
            # Markdown validation: check for H1 title
            h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
            if not h1_match:
                return False, "❌ Markdown missing H1 title (line must start with '# ')"
            return True, ""

        # Other file types pass (no validation)
        return True, ""

    def validate_content(self, content: str, artifact_type: str) -> tuple[bool, str]:
        """
        Validate artifact content synchronously (for pre-write validation).

        This is a simplified validation that checks basic Python syntax
        and structure without requiring a file path. Used by ArtifactManager
        before writing scaffolded content to disk.

        Args:
            content: Artifact content to validate.
            artifact_type: Artifact category ("code" or "doc") or specific type_id

        Returns:
            Tuple of (passed, issues_text) where passed is True if validation
            succeeds, and issues_text contains formatted issues if any.
        """
        # For code artifacts, do Python syntax validation
        if artifact_type == "code" or artifact_type in ["dto", "worker", "adapter", "tool", "base"]:
            try:
                # Try to compile the content to check for syntax errors
                compile(content, f"<{artifact_type}>", "exec")
                return True, ""
            except SyntaxError as e:
                return False, f"❌ Python syntax error at line {e.lineno}: {e.msg}"

        # For non-code artifacts (documents, etc.), skip validation
        # This implements WARN policy: docs pass validation (manager can log warnings)
        return True, ""

    def _get_applicable_validators(self, path: str) -> list[BaseValidator]:
        """
        Get validators with context-specific filtering.

        Applies special logic:
        - Test files: Filter out non-base LayeredTemplateValidators
        - Python files without template: Add base template as fallback

        Args:
            path: File path to get validators for.

        Returns:
            List of applicable validators.
        """
        validators = ValidatorRegistry.get_validators(path)

        # Filter for test files
        is_test = "tests/" in path.replace("\\", "/") or Path(
            path
        ).name.startswith("test_")
        if is_test:
            validators = [
                v for v in validators
                if not isinstance(v, LayeredTemplateValidator)
                or v.template_type == "base"
            ]

        # Python fallback logic: Add base template if no template validator
        if path.endswith(".py"):
            has_template_validator = any(
                isinstance(v, LayeredTemplateValidator) for v in validators
            )
            if not has_template_validator:
                validators.append(
                    LayeredTemplateValidator("base", self.template_analyzer)
                )

        return validators

    async def _run_validators(
        self, validators: list[BaseValidator], path: str, content: str
    ) -> tuple[bool, str]:
        """
        Run validators and aggregate results.

        Args:
            validators: List of validators to run.
            path: File path being validated.
            content: File content being validated.

        Returns:
            Tuple of (passed, issues_text) with formatted issues.
        """
        all_issues = []
        passed = True

        for validator in validators:
            result = await validator.validate(path, content=content)
            if not result.passed:
                passed = False

            if result.issues:
                all_issues.extend(result.issues)

        # Format issues once at the end (avoid duplication)
        issues_text = ""
        if all_issues:
            issues_text = "\n\n**Validation Issues:**\n"
            for issue in all_issues:
                icon = "❌" if issue.severity == "error" else "⚠️"
                loc = f" (line {issue.line})" if issue.line else ""
                issues_text += f"{icon} {issue.message}{loc}\n"

        return passed, issues_text

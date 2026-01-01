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
from pathlib import Path

# Project imports
from mcp_server.validation.base import BaseValidator
from mcp_server.validation.registry import ValidatorRegistry
from mcp_server.validation.python_validator import PythonValidator
from mcp_server.validation.markdown_validator import MarkdownValidator
from mcp_server.validation.template_validator import TemplateValidator


class ValidationService:  # pylint: disable=too-few-public-methods
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
        """Initialize validation service and register validators."""
        self._setup_validators()

    def _setup_validators(self) -> None:
        """Register all validators with ValidatorRegistry."""
        # Register extension-based validators
        ValidatorRegistry.register(".py", PythonValidator)
        ValidatorRegistry.register(".md", MarkdownValidator)

        # Register pattern-based validators for templates
        ValidatorRegistry.register_pattern(
            r".*_workers?\.py$", TemplateValidator("worker")
        )
        ValidatorRegistry.register_pattern(
            r".*_tools?\.py$", TemplateValidator("tool")
        )
        ValidatorRegistry.register_pattern(
            r".*_dtos?\.py$", TemplateValidator("dto")
        )
        ValidatorRegistry.register_pattern(
            r".*_adapters?\.py$", TemplateValidator("adapter")
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

    def _get_applicable_validators(self, path: str) -> list[BaseValidator]:
        """
        Get validators with context-specific filtering.

        Applies special logic:
        - Test files: Filter out non-base TemplateValidators
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
                if not isinstance(v, TemplateValidator)
                or v.template_type == "base"
            ]

        # Python fallback logic: Add base template if no template validator
        if path.endswith(".py"):
            has_template_validator = any(
                isinstance(v, TemplateValidator) for v in validators
            )
            if not has_template_validator:
                validators.append(TemplateValidator("base"))

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
        issues_text = ""
        passed = True

        for validator in validators:
            result = await validator.validate(path, content=content)
            if not result.passed:
                passed = False

            if result.issues:
                issues_text += "\n\n**Validation Issues:**\n"
                for issue in result.issues:
                    icon = "❌" if issue.severity == "error" else "⚠️"
                    loc = f" (line {issue.line})" if issue.line else ""
                    issues_text += f"{icon} {issue.message}{loc}\n"

        return passed, issues_text

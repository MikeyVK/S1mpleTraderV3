"""Template validator implementation."""
import re
from pathlib import Path
from typing import Any

from .base import BaseValidator, ValidationResult, ValidationIssue


class TemplateValidator(BaseValidator):
    """Validator for enforcing template structure (Workers, Tools, DTOs)."""


    # Validation rules per template type
    RULES: dict[str, dict[str, Any]] = {
        "worker": {
            "required_class_suffix": "Worker",
            "required_methods": ["execute"],
            "required_imports": ["BaseWorker", "TaskResult"],
            "description": "Worker components"
        },
        "tool": {
            "required_class_suffix": "Tool",
            "required_methods": ["execute"],
            "required_attrs": ["name", "description", "input_schema"],
            "description": "MCP Tools"
        },
        "dto": {
            "required_class_suffix": "DTO",
            "required_decorators": ["@dataclass"],
            "description": "Data Transfer Objects"
        },
        "adapter": {
            "required_class_suffix": "Adapter",
            "description": "External System Adapters"
        },
        "base": {
            "description": "Base Python Component",
            # Base components should at least use proper typing
            "required_imports": ["typing"]
        }
    }

    def __init__(self, template_type: str) -> None:
        """
        Initialize validator for specific template type.

        Args:
            template_type: One of 'worker', 'tool', 'dto', 'adapter'.
        """
        if template_type not in self.RULES:
            raise ValueError(f"Unknown template type: {template_type}")
        self.template_type = template_type
        self.rules = self.RULES[template_type]

    def __repr__(self) -> str:
        """Return string representation."""
        return f"TemplateValidator(type={self.template_type})"

    async def validate(self, path: str, content: str | None = None) -> ValidationResult:
        """Validate content against template rules."""
        issues: list[ValidationIssue] = []

        if content is None:
            try:
                text = Path(path).read_text(encoding="utf-8")
            except (ValueError, OSError) as e:
                # Catching specific exceptions for file reading/encoding errors
                return ValidationResult(passed=False, score=0.0, issues=[
                    ValidationIssue(f"Failed to read file: {e}")
                ])
        else:
            text = content

        issues.extend(self._validate_class_name(text))
        issues.extend(self._validate_methods(text))
        issues.extend(self._validate_attributes(text))
        issues.extend(self._validate_imports(text))
        issues.extend(self._validate_decorators(text))

        return ValidationResult(
            passed=not [i for i in issues if i.severity == "error"],
            score=10.0 if not issues else 5.0,
            issues=issues
        )

    def _validate_class_name(self, text: str) -> list[ValidationIssue]:
        """Validate class name suffix."""
        issues = []
        suffix = self.rules.get("required_class_suffix")
        if suffix:
            class_pattern = re.compile(rf"class \w+{suffix}\b")
            if not class_pattern.search(text):
                issues.append(ValidationIssue(
                    message=f"Missing class with suffix '{suffix}' "
                            f"(Required for {self.template_type})"
                ))
        return issues

    def _validate_methods(self, text: str) -> list[ValidationIssue]:
        """Validate required methods."""
        issues = []
        for method in self.rules.get("required_methods", []):
            # Support both sync and async methods
            method_pattern = re.compile(rf"(?:async\s+)?def {method}\(")
            if not method_pattern.search(text):
                issues.append(ValidationIssue(
                    message=f"Missing required method: '{method}'",
                    severity="error"
                ))
        return issues

    def _validate_attributes(self, text: str) -> list[ValidationIssue]:
        """Validate required attributes."""
        issues = []
        for attr in self.rules.get("required_attrs", []):
            # Support both assignment and property definition
            attr_pattern = re.compile(rf"(?:\b{attr}\s*=|def {attr}\()")
            if not attr_pattern.search(text):
                issues.append(ValidationIssue(
                    message=f"Missing required attribute: '{attr}'",
                    severity="error"
                ))
        return issues

    def _validate_imports(self, text: str) -> list[ValidationIssue]:
        """Validate required imports."""
        issues = []
        for imp in self.rules.get("required_imports", []):
            if imp not in text:
                issues.append(ValidationIssue(
                    message=f"Missing required import/usage: '{imp}'",
                    severity="warning"
                ))
        return issues

    def _validate_decorators(self, text: str) -> list[ValidationIssue]:
        """Validate required decorators."""
        issues = []
        for dec in self.rules.get("required_decorators", []):
            if dec not in text:
                issues.append(ValidationIssue(
                    message=f"Missing required decorator: '{dec}'",
                    severity="warning"
                ))
        return issues

"""Template validator implementation."""
import re
from pathlib import Path

from .base import BaseValidator, ValidationResult, ValidationIssue


class TemplateValidator(BaseValidator):
    """Validator for enforcing template structure (Workers, Tools, DTOs)."""
    # pylint: disable=too-few-public-methods,too-many-branches

    # Validation rules per template type
    RULES = {
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

    async def validate(self, path: str, content: str | None = None) -> ValidationResult:
        """Validate content against template rules."""
        issues: list[ValidationIssue] = []
        
        if content is None:
            try:
                text = Path(path).read_text(encoding="utf-8")
            except Exception as e:  # pylint: disable=broad-exception-caught
                return ValidationResult(passed=False, score=0.0, issues=[
                    ValidationIssue(f"Failed to read file: {e}")
                ])
        else:
            text = content

        # 1. Class Name Validation
        # Expect class Name(Suffix) or just Name matching filename
        # Naive check: Does a class exist with the required suffix?
        suffix = self.rules.get("required_class_suffix")
        if suffix:
            class_pattern = re.compile(rf"class \w+{suffix}\b")
            if not class_pattern.search(text):
                issues.append(ValidationIssue(
                    message=f"Missing class with suffix '{suffix}' "
                            f"(Required for {self.template_type})"
                ))

        # 2. Method Validation
        for method in self.rules.get("required_methods", []):
            method_pattern = re.compile(rf"def {method}\(")
            if not method_pattern.search(text):
                issues.append(ValidationIssue(
                    message=f"Missing required method: '{method}'",
                    severity="error"
                ))

        # 3. Attribute Validation (Tools)
        for attr in self.rules.get("required_attrs", []):
            attr_pattern = re.compile(rf"\b{attr}\s*=")
            if not attr_pattern.search(text):
                issues.append(ValidationIssue(
                    message=f"Missing required attribute: '{attr}'",
                    severity="error"
                ))

        # 4. Import/Decorator Validation
        for imp in self.rules.get("required_imports", []):
            if imp not in text:
                issues.append(ValidationIssue(
                    message=f"Missing required import/usage: '{imp}'",
                    severity="warning"
                ))

        for dec in self.rules.get("required_decorators", []):
            if dec not in text:
                issues.append(ValidationIssue(
                    message=f"Missing required decorator: '{dec}'",
                    severity="warning"
                ))

        return ValidationResult(
            passed=len([i for i in issues if i.severity == "error"]) == 0,
            score=10.0 if not issues else 5.0,
            issues=issues
        )

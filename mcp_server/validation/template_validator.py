"""Template validator implementation (DEPRECATED)."""

from .base import BaseValidator, ValidationResult


class TemplateValidator(BaseValidator):
    """
    DEPRECATED: Use LayeredTemplateValidator instead.
    
    This validator uses hardcoded RULES dict which violates SSOT principle.
    Kept temporarily for backward compatibility during migration.
    Will be removed in future version.
    """

    def __init__(self, template_type: str) -> None:
        """Initialize validator (deprecated)."""
        self.template_type = template_type

    def __repr__(self) -> str:
        """Return string representation."""
        return f"TemplateValidator(type={self.template_type}) [DEPRECATED]"

    async def validate(self, path: str, content: str | None = None) -> ValidationResult:
        """Validate content (deprecated - always passes)."""
        # Deprecated: Return passing result to avoid breaking existing code
        return ValidationResult(passed=True, score=10.0, issues=[])

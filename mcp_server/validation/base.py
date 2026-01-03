"""Base classes for validation."""
from abc import ABC, abstractmethod
from typing import Any, NamedTuple


class ValidationIssue(NamedTuple):
    """Represents a single validation issue."""
    message: str
    line: int | None = None
    column: int | None = None
    code: str | None = None
    severity: str = "error"


class ValidationResult(NamedTuple):
    """Result of a validation run."""
    passed: bool
    score: float  # 0.0 to 10.0
    issues: list[ValidationIssue]
    agent_hint: str | None = None
    content_guidance: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "passed": self.passed,
            "score": self.score,
            "issues": [
                {
                    "message": issue.message,
                    "line": issue.line,
                    "column": issue.column,
                    "code": issue.code,
                    "severity": issue.severity,
                }
                for issue in self.issues
            ],
            "agent_hint": self.agent_hint,
            "content_guidance": self.content_guidance,
        }


class BaseValidator(ABC):
    """
    Abstract base class for content validators.
    """
    def __repr__(self) -> str:
        """Return string representation."""
        return f"{self.__class__.__name__}()"
    @abstractmethod
    async def validate(self, path: str, content: str | None = None) -> ValidationResult:
        """
        Validate content at path.
        
        Args:
            path: Absolute path to the file.
            content: Optional content override (for checking before saving).
                     If None, reads from disk.
                     
        Returns:
            ValidationResult containing status and issues.
        """

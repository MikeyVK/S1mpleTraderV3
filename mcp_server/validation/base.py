"""Base classes for validation."""
from abc import ABC, abstractmethod
from typing import NamedTuple


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


class BaseValidator(ABC):
    """
    Abstract base class for content validators.
    """
    # pylint: disable=too-few-public-methods

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

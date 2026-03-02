"""Base scaffolder abstract class.

Defines interface for all scaffolder implementations.
Issue #56: Unified artifact system foundation.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseScaffolder(ABC):
    """Abstract base class for scaffolders.

    All scaffolder implementations must extend this class and implement
    validate() and scaffold() methods.
    """

    def __init__(self) -> None:
        """Initialize scaffolder."""
        pass

    @abstractmethod
    def validate(self, artifact_type: str, **kwargs: Any) -> bool:  # noqa: ANN401
        """Validate scaffolding arguments before execution.

        Args:
            artifact_type: Type of artifact to scaffold
            **kwargs: Context data for scaffolding

        Returns:
            True if validation passes

        Raises:
            ValidationError: If validation fails
        """

    @abstractmethod
    def scaffold(self, artifact_type: str, **kwargs: Any) -> Any:  # noqa: ANN401
        """Execute scaffolding operation.

        Args:
            artifact_type: Type of artifact to scaffold
            **kwargs: Context data for scaffolding

        Returns:
            Scaffolding result (implementation-specific)

        Raises:
            ValidationError: If validation fails
            ConfigError: If configuration invalid
        """

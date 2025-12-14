"""Scaffolding utilities."""
import re

from mcp_server.core.exceptions import ValidationError


def validate_pascal_case(name: str) -> None:
    """Validate name is PascalCase.

    Args:
        name: Name to validate

    Raises:
        ValidationError: If not PascalCase
    """
    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', name):
        raise ValidationError(
            f"Invalid name: {name}. Must be PascalCase.",
            hints=["Use PascalCase like 'OrderState' or 'ConfigDTO'"]
        )

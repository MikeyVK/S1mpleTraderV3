"""Registry for looking up validators."""
import os
import re
from typing import Type

from .base import BaseValidator


class ValidatorRegistry:
    """Registry to map file types/patterns to validators."""

    _extension_map: dict[str, Type[BaseValidator]] = {}
    _pattern_map: list[tuple[str, BaseValidator]] = []

    @classmethod
    def register(cls, extension: str, validator: Type[BaseValidator]) -> None:
        """Register a validator class for an extension."""
        cls._extension_map[extension] = validator

    @classmethod
    def register_pattern(cls, pattern: str, validator: BaseValidator) -> None:
        """Register a validator instance for a regex pattern."""
        cls._pattern_map.append((pattern, validator))

    @classmethod
    def get_validators(cls, path: str) -> list[BaseValidator]:
        """
        Get all appropriate validator instances for path.

        Args:
            path: Absolute path to the file.

        Returns:
            list[BaseValidator]: List of validators (extension match + pattern matches).
        """
        validators = []

        # 1. Extension match
        _, ext = os.path.splitext(path)
        validator_cls = cls._extension_map.get(ext)
        if validator_cls:
            validators.append(validator_cls())

        # 2. Pattern matches
        for pattern, validator_inst in cls._pattern_map:
            if re.search(pattern, path):
                validators.append(validator_inst)

        return validators

    @classmethod
    def get_validator(cls, path: str) -> BaseValidator | None:
        """
        Get primary validator (deprecated, use get_validators).
        For backward compat, returns the extension match.
        """
        validators = cls.get_validators(path)
        return validators[0] if validators else None

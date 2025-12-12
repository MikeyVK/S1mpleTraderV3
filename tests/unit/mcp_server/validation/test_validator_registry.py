# tests/unit/mcp_server/validation/test_validator_registry.py
"""
Unit tests for ValidatorRegistry.

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives
# pylint: disable=protected-access

# Standard library
from typing import Generator
from unittest.mock import MagicMock

# Third-party
import pytest

# Module under test
from mcp_server.validation.registry import ValidatorRegistry
from mcp_server.validation.base import BaseValidator


class MockValidator(BaseValidator):
    """Mock validator for testing."""
    # pylint: disable=too-few-public-methods

    async def validate(self, path: str, content: str | None = None) -> MagicMock:
        return MagicMock()


class TestValidatorRegistry:
    """Test suite for ValidatorRegistry."""

    @pytest.fixture(autouse=True)
    def clean_registry(self) -> Generator[None, None, None]:
        """Automatically reset registry state before/after each test."""
        # Setup: Backup
        orig_ext = ValidatorRegistry._extension_map.copy()
        orig_pat = ValidatorRegistry._pattern_map.copy()

        # Clear for test
        ValidatorRegistry._extension_map = {}
        ValidatorRegistry._pattern_map = []

        yield

        # Teardown: Restore
        ValidatorRegistry._extension_map = orig_ext
        ValidatorRegistry._pattern_map = orig_pat

    def test_register_extension(self) -> None:
        """Test registering a validator class for an extension."""
        ValidatorRegistry.register(".test", MockValidator)
        assert ValidatorRegistry._extension_map[".test"] == MockValidator

    def test_register_pattern(self) -> None:
        """Test registering a validator instance for a regex pattern."""
        validator_inst = MockValidator()
        ValidatorRegistry.register_pattern(r"test.*", validator_inst)
        assert (r"test.*", validator_inst) in ValidatorRegistry._pattern_map

    def test_get_validators_extension_match(self) -> None:
        """Test retrieving validators by extension."""
        ValidatorRegistry.register(".py", MockValidator)

        validators = ValidatorRegistry.get_validators("script.py")

        assert len(validators) == 1
        assert isinstance(validators[0], MockValidator)

    def test_get_validators_pattern_match(self) -> None:
        """Test retrieving validators by regex pattern."""
        validator_inst = MockValidator()
        ValidatorRegistry.register_pattern(r".*_worker\.py$", validator_inst)

        validators = ValidatorRegistry.get_validators("my_worker.py")

        assert len(validators) == 1
        assert validators[0] is validator_inst

    def test_get_validators_multiple_matches(self) -> None:
        """Test retrieving both extension and pattern validators."""
        ValidatorRegistry.register(".py", MockValidator)

        pattern_val = MockValidator()
        ValidatorRegistry.register_pattern(r".*_test\.py$", pattern_val)

        validators = ValidatorRegistry.get_validators("unit_test.py")

        # Should get 2 validators: 1 from .py extension, 1 from pattern
        assert len(validators) == 2
        assert isinstance(validators[0], MockValidator)  # Extension match first
        assert validators[1] is pattern_val              # Pattern match second

    def test_get_validator_deprecated(self) -> None:
        """Test deprecated get_validator method returns primary match."""
        ValidatorRegistry.register(".py", MockValidator)

        validator = ValidatorRegistry.get_validator("script.py")
        assert isinstance(validator, MockValidator)

    def test_get_validator_none(self) -> None:
        """Test get_validator returns None if no match found."""
        validator = ValidatorRegistry.get_validator("unknown.xyz")
        assert validator is None

    def test_get_validators_no_match(self) -> None:
        """Test get_validators returns empty list if no match found."""
        validators = ValidatorRegistry.get_validators("unknown.xyz")
        assert not validators

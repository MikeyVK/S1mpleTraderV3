# tests/unit/mcp_server/validation/test_validation_service.py
"""
Unit tests for ValidationService.

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest]
@responsibilities:
  - Test validator registration
  - Test validator retrieval with filtering
  - Test validation orchestration
  - Test aggregation of validation results
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
from unittest.mock import patch

# Third-party
import pytest

# Module under test
from mcp_server.validation.validation_service import ValidationService
from mcp_server.validation.base import ValidationResult, ValidationIssue, BaseValidator


class MockValidator(BaseValidator):
    """Mock validator for testing."""

    def __init__(
        self, passed: bool = True, issues: list[ValidationIssue] | None = None
    ):
        self.passed = passed
        self.issues = issues or []

    async def validate(
        self, path: str, content: str | None = None
    ) -> ValidationResult:
        """Mock validation."""
        return ValidationResult(
            passed=self.passed,
            score=10.0 if self.passed else 0.0,
            issues=self.issues
        )


class TestValidationService:
    """Test suite for ValidationService."""

    @pytest.fixture
    def service(self) -> ValidationService:
        """Fixture for ValidationService."""
        return ValidationService()

    def test_setup_validators_registers_extensions(
        self, service: ValidationService
    ) -> None:
        """Test that _setup_validators registers extension-based validators."""
        with patch(
            "mcp_server.validation.validation_service.ValidatorRegistry"
        ) as mock_registry:
            service._setup_validators()  # pylint: disable=protected-access

            # Verify Python and Markdown validators registered
            calls = mock_registry.register.call_args_list
            assert any(".py" in str(call) for call in calls)
            assert any(".md" in str(call) for call in calls)

    def test_setup_validators_registers_patterns(
        self, service: ValidationService
    ) -> None:
        """Test that _setup_validators registers pattern-based validators."""
        with patch(
            "mcp_server.validation.validation_service.ValidatorRegistry"
        ) as mock_registry:
            service._setup_validators()  # pylint: disable=protected-access

            # Verify pattern registrations (worker, tool, dto, adapter)
            calls = mock_registry.register_pattern.call_args_list
            assert len(calls) >= 4
            assert any("worker" in str(call) for call in calls)
            assert any("tool" in str(call) for call in calls)
            assert any("dto" in str(call) for call in calls)
            assert any("adapter" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_validate_with_passing_validators(
        self, service: ValidationService
    ) -> None:
        """Test validation with all validators passing."""
        mock_validator = MockValidator(passed=True)

        with patch.object(
            service,
            "_get_applicable_validators",
            return_value=[mock_validator]
        ):
            passed, issues_text = await service.validate("test.py", "valid code")

            assert passed is True
            assert not issues_text

    @pytest.mark.asyncio
    async def test_validate_with_failing_validators(
        self, service: ValidationService
    ) -> None:
        """Test validation with failing validators."""
        issue = ValidationIssue(message="Test error", severity="error", line=10)
        mock_validator = MockValidator(passed=False, issues=[issue])

        with patch.object(
            service,
            "_get_applicable_validators",
            return_value=[mock_validator]
        ):
            passed, issues_text = await service.validate("test.py", "invalid code")

            assert passed is False
            assert "Test error" in issues_text
            assert "line 10" in issues_text

    @pytest.mark.asyncio
    async def test_validate_aggregates_multiple_validators(
        self, service: ValidationService
    ) -> None:
        """Test that validation aggregates results from multiple validators."""
        issue1 = ValidationIssue(message="Error 1", severity="error")
        issue2 = ValidationIssue(message="Warning 1", severity="warning")

        validator1 = MockValidator(passed=False, issues=[issue1])
        validator2 = MockValidator(passed=True, issues=[issue2])

        with patch.object(
            service,
            "_get_applicable_validators",
            return_value=[validator1, validator2]
        ):
            passed, issues_text = await service.validate("test.py", "code")

            assert passed is False  # One failed
            assert "Error 1" in issues_text
            assert "Warning 1" in issues_text

    def test_get_applicable_validators_for_regular_file(
        self, service: ValidationService
    ) -> None:
        """Test validator retrieval for regular Python files."""
        mock_validator = MockValidator()

        with patch(
            "mcp_server.validation.validation_service.ValidatorRegistry"
        ) as mock_registry:
            mock_registry.get_validators.return_value = [mock_validator]

            # pylint: disable=protected-access
            validators = service._get_applicable_validators("src/module.py")

            assert mock_validator in validators

    def test_get_applicable_validators_filters_for_test_files(
        self, service: ValidationService
    ) -> None:
        """Test that template validators are filtered for test files."""
        from mcp_server.validation.layered_template_validator import (
            LayeredTemplateValidator
        )

        # Create mock validators
        python_validator = MockValidator()
        template_validator_worker = LayeredTemplateValidator(
            "worker", service.template_analyzer
        )
        template_validator_base = LayeredTemplateValidator(
            "base", service.template_analyzer
        )

        with patch(
            "mcp_server.validation.validation_service.ValidatorRegistry"
        ) as mock_registry:
            mock_registry.get_validators.return_value = [
                python_validator,
                template_validator_worker,
                template_validator_base
            ]

            # Test file in tests/ directory
            # pylint: disable=protected-access
            validators = service._get_applicable_validators(
                "tests/unit/test_worker.py"
            )

            # Should filter out non-base LayeredTemplateValidators
            assert python_validator in validators
            assert template_validator_worker not in validators
            assert template_validator_base in validators

    def test_get_applicable_validators_filters_for_test_prefix(
        self, service: ValidationService
    ) -> None:
        """Test that template validators are filtered for test_ prefix files."""
        from mcp_server.validation.layered_template_validator import (
            LayeredTemplateValidator
        )

        template_validator = LayeredTemplateValidator(
            "tool", service.template_analyzer
        )

        with patch(
            "mcp_server.validation.validation_service.ValidatorRegistry"
        ) as mock_registry:
            mock_registry.get_validators.return_value = [template_validator]

            # File with test_ prefix
            # pylint: disable=protected-access
            validators = service._get_applicable_validators(
                "src/test_something.py"
            )

            # Should filter out non-base template validators
            assert template_validator not in validators

    def test_get_applicable_validators_adds_base_fallback_for_python(
        self, service: ValidationService
    ) -> None:
        """Test that base template validator is added as fallback for Python."""
        from mcp_server.validation.layered_template_validator import (
            LayeredTemplateValidator
        )

        python_validator = MockValidator()

        with patch(
            "mcp_server.validation.validation_service.ValidatorRegistry"
        ) as mock_registry:
            mock_registry.get_validators.return_value = [python_validator]

            # pylint: disable=protected-access
            validators = service._get_applicable_validators(
                "src/random_file.py"
            )

            # Should add base LayeredTemplateValidator as fallback
            assert len(validators) == 2  # python_validator + base template
            assert any(
                isinstance(v, LayeredTemplateValidator)
                and v.template_type == "base"
                for v in validators
            )

    def test_get_applicable_validators_no_fallback_if_template_exists(
        self, service: ValidationService
    ) -> None:
        """Test that base fallback is not added if LayeredTemplateValidator exists."""
        from mcp_server.validation.layered_template_validator import (
            LayeredTemplateValidator
        )

        template_validator = LayeredTemplateValidator(
            "worker", service.template_analyzer
        )

        with patch(
            "mcp_server.validation.validation_service.ValidatorRegistry"
        ) as mock_registry:
            mock_registry.get_validators.return_value = [template_validator]

            # pylint: disable=protected-access
            validators = service._get_applicable_validators("src/my_worker.py")

            # Should NOT add base fallback (worker template already present)
            assert len(validators) == 1
            assert template_validator in validators

    @pytest.mark.asyncio
    async def test_run_validators_returns_formatted_issues(
        self, service: ValidationService
    ) -> None:
        """Test that _run_validators formats issues correctly."""
        issue = ValidationIssue(message="Test issue", severity="error", line=42)
        validator = MockValidator(passed=False, issues=[issue])

        # pylint: disable=protected-access
        passed, issues_text = await service._run_validators(
            [validator], "test.py", "code"
        )

        assert passed is False
        assert "❌" in issues_text  # Error icon
        assert "Test issue" in issues_text
        assert "line 42" in issues_text

    @pytest.mark.asyncio
    async def test_run_validators_handles_warnings(
        self, service: ValidationService
    ) -> None:
        """Test that _run_validators handles warnings correctly."""
        issue = ValidationIssue(message="Test warning", severity="warning")
        validator = MockValidator(passed=True, issues=[issue])

        # pylint: disable=protected-access
        passed, issues_text = await service._run_validators(
            [validator], "test.py", "code"
        )

        assert passed is True  # Still passed with warnings
        assert "⚠️" in issues_text  # Warning icon
        assert "Test warning" in issues_text

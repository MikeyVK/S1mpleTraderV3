# tests\mcp_server\unit\schemas\test_presentation_output.py
# template=unit_test version=8825c0bb created=2026-08-19T19:00Z updated=2026-08-19T19:05Z
"""
Unit tests for mcp_server.schemas.presentation_output.

Unit tests for PresentationResource and PresentedOutput frozen DTO models.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.schemas.presentation_output]
@responsibilities:
    - Test PresentationResource model creation, defaults, immutability, and extra fields forbidden
    - Test PresentedOutput model creation, defaults, immutability, and extra fields forbidden
"""

import pytest
from pydantic import ValidationError

from mcp_server.schemas.presentation_output import PresentationResource, PresentedOutput


class TestPresentationResource:
    """Test suite for PresentationResource DTO."""

    def test_create_resource_defaults(self) -> None:
        """Verify PresentationResource creation with default mime_type."""
        resource = PresentationResource(uri="schema://validation", content='{"type": "object"}')
        assert resource.uri == "schema://validation"
        assert resource.mime_type == "application/json"
        assert resource.content == '{"type": "object"}'

    def test_create_resource_custom_mime_type(self) -> None:
        """Verify PresentationResource creation with custom mime_type."""
        resource = PresentationResource(
            uri="text://info",
            mime_type="text/plain",
            content="Hello",
        )
        assert resource.uri == "text://info"
        assert resource.mime_type == "text/plain"
        assert resource.content == "Hello"

    def test_resource_is_frozen(self) -> None:
        """Verify PresentationResource is immutable."""
        resource = PresentationResource(uri="schema://validation", content="{}")
        with pytest.raises(ValidationError):
            resource.uri = "schema://other"  # type: ignore[misc]

    def test_resource_forbids_extra_fields(self) -> None:
        """Verify PresentationResource forbids extra fields."""
        with pytest.raises(ValidationError):
            PresentationResource(
                uri="schema://validation",
                content="{}",
                unknown_field="invalid",  # type: ignore[call-arg]
            )


class TestPresentedOutput:
    """Test suite for PresentedOutput DTO."""

    def test_create_output_defaults(self) -> None:
        """Verify PresentedOutput creation with default empty resources."""
        output = PresentedOutput(text="Success output")
        assert output.text == "Success output"
        assert output.resources == []

    def test_create_output_with_resources(self) -> None:
        """Verify PresentedOutput with embedded resources."""
        res = PresentationResource(uri="schema://validation", content="{}")
        output = PresentedOutput(text="Validation error", resources=[res])
        assert output.text == "Validation error"
        assert len(output.resources) == 1
        assert output.resources[0].uri == "schema://validation"

    def test_output_is_frozen(self) -> None:
        """Verify PresentedOutput is immutable."""
        output = PresentedOutput(text="Test")
        with pytest.raises(ValidationError):
            output.text = "New text"  # type: ignore[misc]

    def test_output_forbids_extra_fields(self) -> None:
        """Verify PresentedOutput forbids extra fields."""
        with pytest.raises(ValidationError):
            PresentedOutput(text="Test", extra_prop="invalid")  # type: ignore[call-arg]

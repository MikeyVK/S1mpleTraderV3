# tests/unit/mcp_server/schemas/test_dto_schemas.py
# template=generic version=f35abd82 created=2026-02-17T11:18Z updated=
"""TestDTOSchemas module.

Tests for DTOContext and DTORenderContext schemas (Cycle 3)

@layer: Test Infrastructure
@dependencies: [None]
@responsibilities:
    - Test DTOContext validation (happy path + error cases)
    - Test DTOContext → DTORenderContext enrichment
    - Test DTORenderContext has DTO fields + 4 lifecycle fields
    - Validate DTO-specific field validators
"""

# Standard library
import logging
from datetime import UTC, datetime
from pathlib import Path

# Third-party
import pytest
from pydantic import ValidationError

# Project modules
from mcp_server.schemas.contexts.dto import DTOContext
from mcp_server.schemas.render_contexts.dto import DTORenderContext

logger = logging.getLogger(__name__)


class TestDTOContext:
    """Test DTOContext schema validation."""

    def test_dto_context_validation_happy(self) -> None:
        """Valid DTO input should create DTOContext instance."""
        # Valid DTO context - minimal required fields
        dto_ctx = DTOContext(
            dto_name="UserDTO",
            fields=["user_id: str", "email: str", "created_at: datetime"],
        )

        # Verify fields are accessible
        assert dto_ctx.dto_name == "UserDTO"
        assert len(dto_ctx.fields) == 3
        assert "user_id: str" in dto_ctx.fields

    def test_dto_context_validation_error(self) -> None:
        """Invalid DTO input should raise ValidationError."""
        # Empty dto_name should fail
        with pytest.raises(ValidationError, match="dto_name"):
            DTOContext(
                dto_name="",  # Invalid: empty string
                fields=["user_id: str"],
            )

        # fields as string (not list) should fail
        with pytest.raises(ValidationError):
            DTOContext(
                dto_name="UserDTO",
                fields="user_id: str",  # Invalid: string not list
            )


class TestDTORenderContext:
    """Test DTORenderContext enrichment and field completeness."""

    def test_dto_render_context_enrichment(self) -> None:
        """DTORenderContext should combine DTO fields + lifecycle fields."""
        # Create RenderContext with DTO-specific + lifecycle fields
        render_ctx = DTORenderContext(
            # DTO-specific fields (from DTOContext)
            dto_name="UserDTO",
            fields=["user_id: str", "email: str"],
            # Lifecycle fields (from LifecycleMixin)
            output_path=Path("/tmp/user_dto.py"),
            scaffold_created=datetime.now(tz=UTC),
            template_id="dto",
            version_hash="abc12345",
        )

        # Verify DTO-specific fields
        assert render_ctx.dto_name == "UserDTO"
        assert len(render_ctx.fields) == 2

        # Verify lifecycle fields
        assert render_ctx.output_path == Path("/tmp/user_dto.py")
        assert render_ctx.template_id == "dto"
        assert render_ctx.version_hash == "abc12345"

    def test_dto_render_context_all_fields(self) -> None:
        """DTORenderContext must have DTO fields + 4 lifecycle fields."""
        # Expected: 2 DTO-specific + 4 lifecycle = 6 total fields
        expected_fields = {
            # DTO-specific
            "dto_name",
            "fields",
            # Lifecycle
            "output_path",
            "scaffold_created",
            "template_id",
            "version_hash",
        }

        actual_fields = set(DTORenderContext.model_fields.keys())
        assert actual_fields == expected_fields, (
            f"DTORenderContext fields mismatch. Expected {expected_fields}, got {actual_fields}"
        )

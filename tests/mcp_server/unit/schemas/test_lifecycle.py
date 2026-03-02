# tests/unit/mcp_server/schemas/test_lifecycle.py
# template=generic version=f35abd82 created=2026-02-17T09:29Z updated=
"""TestLifecycleSchemas module.

Tests for LifecycleMixin and base schema classes (Cycle 2)

@layer: Test Infrastructure
@dependencies: [None]
@responsibilities:
    - Test LifecycleMixin has 4 required fields
    - Test BaseContext instantiation
    - Test BaseRenderContext inherits LifecycleMixin
    - Test lifecycle fields are system-controlled (not user-overridable)
    - Test system can mutate lifecycle fields in controlled enrichment paths
"""

# Standard library
import logging
from datetime import UTC, datetime
from pathlib import Path

# Third-party
import pytest
from pydantic import ValidationError

# Project modules
from mcp_server.schemas.base import BaseContext, BaseRenderContext
from mcp_server.schemas.mixins.lifecycle import LifecycleMixin

logger = logging.getLogger(__name__)


class TestLifecycleMixin:
    """Test LifecycleMixin schema fields and validation."""

    def test_lifecycle_mixin_fields(self) -> None:
        """LifecycleMixin must have exactly 4 required fields."""
        expected_fields = {"output_path", "scaffold_created", "template_id", "version_hash"}
        actual_fields = set(LifecycleMixin.model_fields.keys())
        assert actual_fields == expected_fields, (
            f"LifecycleMixin fields mismatch. Expected {expected_fields}, got {actual_fields}"
        )

    def test_lifecycle_field_types(self) -> None:
        """Lifecycle fields must have correct types."""
        fields = LifecycleMixin.model_fields
        assert fields["output_path"].annotation is Path
        assert fields["scaffold_created"].annotation is datetime
        assert fields["template_id"].annotation is str
        assert fields["version_hash"].annotation is str


class TestBaseContext:
    """Test BaseContext instantiation and behavior."""

    def test_base_context_instantiation(self) -> None:
        """BaseContext can be instantiated (abstract but usable for testing)."""
        # BaseContext is abstract but should be concrete enough for inheritance tests
        ctx = BaseContext()
        assert ctx is not None
        assert isinstance(ctx, BaseContext)


class TestBaseRenderContext:
    """Test BaseRenderContext inheritance and lifecycle integration."""

    def test_base_render_context_inheritance(self) -> None:
        """BaseRenderContext must inherit from LifecycleMixin."""
        # Check MRO (Method Resolution Order)
        assert LifecycleMixin in BaseRenderContext.__mro__, (
            "BaseRenderContext must inherit LifecycleMixin"
        )

    def test_base_render_context_has_lifecycle_fields(self) -> None:
        """BaseRenderContext must have all 4 lifecycle fields from LifecycleMixin."""
        lifecycle_fields = {"output_path", "scaffold_created", "template_id", "version_hash"}
        render_ctx_fields = set(BaseRenderContext.model_fields.keys())
        assert lifecycle_fields.issubset(render_ctx_fields), (
            f"BaseRenderContext missing lifecycle fields. Has {render_ctx_fields}"
        )


class TestLifecycleSystemControl:
    """Test lifecycle fields are system-controlled (not user-overridable)."""

    def test_user_cannot_provide_lifecycle_to_context(self) -> None:
        """User-facing Context schemas must reject lifecycle fields."""
        # BaseContext should reject lifecycle fields via extra='forbid'
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            BaseContext(
                output_path=Path("/tmp/test.py"),  # Lifecycle field - should fail
            )

        # Another lifecycle field test
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            BaseContext(
                version_hash="abc12345",  # Lifecycle field - should fail
            )

    def test_system_can_provide_lifecycle_to_render_context(self) -> None:
        """System can provide lifecycle fields to RenderContext schemas."""
        # BaseRenderContext MUST accept lifecycle fields (system boundary)
        render_ctx = BaseRenderContext(
            output_path=Path("/tmp/test.py"),
            scaffold_created=datetime.now(tz=UTC),
            template_id="dto",
            version_hash="abc12345",  # Valid: 8-char lowercase hex
        )

        # Verify all lifecycle fields are accessible
        assert render_ctx.output_path == Path("/tmp/test.py")
        assert render_ctx.template_id == "dto"
        assert render_ctx.version_hash == "abc12345"
        assert isinstance(render_ctx.scaffold_created, datetime)

    def test_version_hash_strict_validation(self) -> None:
        """Version hash is strictly validated (system-calculated, never user-input)."""
        # Valid version_hash - should pass (8-char lowercase hex)
        render_ctx = BaseRenderContext(
            output_path=Path("/tmp/test.py"),
            scaffold_created=datetime.now(tz=UTC),
            template_id="dto",
            version_hash="abc12345",
        )
        assert render_ctx.version_hash == "abc12345"

        # Invalid: too short
        with pytest.raises(ValidationError, match="version_hash must be 8 chars"):
            BaseRenderContext(
                output_path=Path("/tmp/test2.py"),
                scaffold_created=datetime.now(tz=UTC),
                template_id="worker",
                version_hash="abc123",  # Invalid: only 6 chars
            )

        # Invalid: not lowercase hex
        with pytest.raises(ValidationError, match="version_hash must be lowercase hex"):
            BaseRenderContext(
                output_path=Path("/tmp/test3.py"),
                scaffold_created=datetime.now(tz=UTC),
                template_id="tool",
                version_hash="ABCD1234",  # Invalid: uppercase
            )

    def test_system_controlled_mutation_pattern(self) -> None:
        """System can mutate lifecycle fields in controlled enrichment/update paths."""
        # Create RenderContext with initial lifecycle values
        render_ctx = BaseRenderContext(
            output_path=Path("/tmp/test.py"),
            scaffold_created=datetime.now(tz=UTC),
            template_id="dto",
            version_hash="abc12345",
        )

        # System CAN mutate fields (frozen=False allows controlled mutation)
        # Example: enrichment pipeline updates output_path after template resolution
        original_path = render_ctx.output_path
        render_ctx.output_path = Path("/tmp/resolved_path.py")
        assert render_ctx.output_path != original_path
        assert render_ctx.output_path == Path("/tmp/resolved_path.py")

        # Note: version_hash and template_id are fingerprints - stricter in practice
        # (business logic would prevent mutation, but Pydantic allows it technically)
        # Future: Add 'updated' timestamp field that system CAN mutate freely

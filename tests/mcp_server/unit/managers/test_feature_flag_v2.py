# tests/unit/mcp_server/managers/test_feature_flag_v2.py
"""Test Pydantic v2 feature flag routing and schema-typed enrichment (Issue #135 Cycle 4).

Tests:
- Feature flag OFF → v1 pipeline (dict-based)
- Feature flag ON → v2 pipeline (schema-typed)
- Feature flag toggle (runtime switch)
- V1 pipeline unchanged (backward compatibility)
- V2 pipeline validates via Pydantic
- Schema-typed enrichment (_enrich_context_v2)
- Naming Convention lookup (DTOContext → DTORenderContext)
"""

# Standard library
import asyncio
import logging
import os
from pathlib import Path
from typing import Any
from unittest.mock import Mock

# Third-party
import pytest

# Project modules
from mcp_server.core.exceptions import ValidationError
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.schemas.base import BaseContext
from mcp_server.schemas.contexts.dto import DTOContext
from mcp_server.schemas.render_contexts.dto import DTORenderContext

logger = logging.getLogger(__name__)


class TestFeatureFlagV2Routing:
    """Test feature flag controls v1/v2 pipeline routing."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        """Create ArtifactManager with test workspace."""
        return ArtifactManager(workspace_root=str(tmp_path))

    def test_feature_flag_off_uses_v1_pipeline(self, manager: ArtifactManager) -> None:
        """Feature flag OFF (default) should use v1 dict-based pipeline.

        REQUIREMENT (Cycle 4): Backward compatibility - v1 pipeline unchanged.
        """
        # Arrange: Flag OFF (default behavior)
        os.environ["PYDANTIC_SCAFFOLDING_ENABLED"] = "false"

        # Spy on _enrich_context to verify v1 called
        original_v1 = manager._enrich_context
        v1_called = False

        def spy_v1(*args: Any, **kwargs: Any) -> object:  # noqa: ANN401
            nonlocal v1_called
            v1_called = True
            return original_v1(*args, **kwargs)

        manager._enrich_context = spy_v1

        # Mock scaffolder and validation to prevent real file operations
        manager.scaffolder.scaffold = Mock(return_value=Mock(content="# test"))

        # Mock async validate method
        async def mock_validate(*_args: Any, **_kwargs: Any) -> tuple[bool, str]:  # noqa: ANN401
            return (True, "")

        manager.validation_service.validate = mock_validate
        manager.fs_adapter.write_file = Mock()

        # Act: Scaffold with dict-based context
        context = {"dto_name": "TestDTO", "fields": ["id: int", "name: str"]}

        asyncio.run(
            manager.scaffold_artifact("dto", output_path="test_scaffold_output.py", **context)
        )

        # Assert: v1 pipeline was used
        assert v1_called, "V1 pipeline (_enrich_context) should be called when flag OFF"

    def test_feature_flag_on_uses_v2_pipeline(self, manager: ArtifactManager) -> None:
        """Feature flag ON should use v2 schema-typed pipeline.

        REQUIREMENT (Cycle 4): V2 pipeline uses Pydantic validation.
        """
        # Arrange: Flag ON
        os.environ["PYDANTIC_SCAFFOLDING_ENABLED"] = "true"

        # Spy on _enrich_context_v2 to verify v2 called
        original_v2 = manager._enrich_context_v2
        v2_called = False

        def spy_v2(*args: Any, **kwargs: Any) -> object:  # noqa: ANN401
            nonlocal v2_called
            v2_called = True
            return original_v2(*args, **kwargs)

        manager._enrich_context_v2 = spy_v2

        # Mock scaffolder and validation
        manager.scaffolder.scaffold = Mock(return_value=Mock(content="# test"))

        async def mock_validate(*_args: Any, **_kwargs: Any) -> tuple[bool, str]:  # noqa: ANN401
            return (True, "")

        manager.validation_service.validate = mock_validate
        manager.fs_adapter.write_file = Mock()

        # Act: Scaffold with dict-based context (will be validated to DTOContext)
        context = {"dto_name": "TestDTO", "fields": ["id: int"]}

        asyncio.run(
            manager.scaffold_artifact("dto", output_path="test_scaffold_output.py", **context)
        )

        # Assert: v2 pipeline was used
        assert v2_called, "V2 pipeline (_enrich_context_v2) should be called when flag ON"

        # Cleanup
        os.environ.pop("PYDANTIC_SCAFFOLDING_ENABLED", None)

    def test_feature_flag_toggle_runtime(self, manager: ArtifactManager) -> None:
        """Feature flag should toggle at runtime (no restart needed).

        REQUIREMENT (Cycle 4): Dynamic toggle for gradual rollout.
        """
        # Mock scaffolder and validation
        manager.scaffolder.scaffold = Mock(return_value=Mock(content="# test"))

        async def mock_validate(*_args: Any, **_kwargs: Any) -> tuple[bool, str]:  # noqa: ANN401
            return (True, "")

        manager.validation_service.validate = mock_validate
        manager.fs_adapter.write_file = Mock()

        context = {"dto_name": "TestDTO", "fields": []}

        # Test 1: Flag OFF → v1
        os.environ["PYDANTIC_SCAFFOLDING_ENABLED"] = "false"
        original_v1 = manager._enrich_context
        v1_calls = []
        manager._enrich_context = lambda *args, **kw: (
            v1_calls.append(1),
            original_v1(*args, **kw),
        )[1]

        asyncio.run(
            manager.scaffold_artifact("dto", output_path="test_scaffold_output.py", **context)
        )
        assert len(v1_calls) == 1, "V1 should be called when flag OFF"

        # Test 2: Flag ON → v2
        os.environ["PYDANTIC_SCAFFOLDING_ENABLED"] = "true"
        original_v2 = manager._enrich_context_v2
        v2_calls = []
        manager._enrich_context_v2 = lambda *args, **kw: (
            v2_calls.append(1),
            original_v2(*args, **kw),
        )[1]

        asyncio.run(
            manager.scaffold_artifact("dto", output_path="test_scaffold_output.py", **context)
        )
        assert len(v2_calls) == 1, "V2 should be called when flag ON (runtime toggle)"

        # Cleanup
        os.environ.pop("PYDANTIC_SCAFFOLDING_ENABLED", None)

    def test_v1_pipeline_unchanged(self, manager: ArtifactManager) -> None:
        """V1 pipeline behavior should be identical (regression check).

        REQUIREMENT (Cycle 4): Zero changes to v1 behavior.
        """
        # Arrange: Flag OFF
        os.environ["PYDANTIC_SCAFFOLDING_ENABLED"] = "false"

        # Mock scaffolder to capture enriched context
        captured_context = {}

        def capture_scaffold(_artifact_type: str, **kwargs: Any) -> Mock:  # noqa: ANN401
            captured_context.update(kwargs)
            return Mock(content="# test")

        manager.scaffolder.scaffold = capture_scaffold

        async def mock_validate(*_args: Any, **_kwargs: Any) -> tuple[bool, str]:  # noqa: ANN401
            return (True, "")

        manager.validation_service.validate = mock_validate
        manager.fs_adapter.write_file = Mock()

        # Act: Scaffold with v1 dict-based context
        context = {"dto_name": "TestDTO", "fields": ["id: int", "name: str"], "frozen": True}

        asyncio.run(
            manager.scaffold_artifact("dto", output_path="test_scaffold_output.py", **context)
        )

        # Assert: v1 enrichment fields present (dict-based)
        assert "template_id" in captured_context, "V1 should add template_id"
        assert "scaffold_created" in captured_context, "V1 should add scaffold_created"
        assert "output_path" in captured_context, "V1 should add output_path"
        assert captured_context["dto_name"] == "TestDTO", "User context preserved"

    def test_v2_pipeline_validates_input(self, manager: ArtifactManager) -> None:
        """V2 pipeline should validate input via Pydantic schemas.

        REQUIREMENT (Cycle 4): Pydantic catches errors (no silent | default failures).
        """
        # Arrange: Flag ON
        os.environ["PYDANTIC_SCAFFOLDING_ENABLED"] = "true"

        # Act + Assert: Invalid context (fields as string instead of list)
        invalid_context = {
            "dto_name": "TestDTO",
            "fields": "not_a_list",  # Should be list[str]!
        }

        with pytest.raises(ValidationError) as exc_info:
            asyncio.run(
                manager.scaffold_artifact(
                    "dto", output_path="test_scaffold_output.py", **invalid_context
                )
            )

        # Verify error message mentions Pydantic validation
        assert "V2 pipeline" in str(exc_info.value), "Error should mention V2 pipeline"
        assert "DTOContext" in str(exc_info.value), "Error should mention schema class"

        # Cleanup
        os.environ.pop("PYDANTIC_SCAFFOLDING_ENABLED", None)


class TestSchemaTypedEnrichment:
    """Test schema-typed _enrich_context_v2 method with Naming Convention lookup."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        """Create ArtifactManager with test workspace."""
        return ArtifactManager(workspace_root=str(tmp_path))

    def test_enrich_context_v2_dto_context_to_render_context(
        self, manager: ArtifactManager
    ) -> None:
        """_enrich_context_v2(DTOContext) should return DTORenderContext.

        REQUIREMENT (Cycle 4): Schema-typed enrichment pipeline.
        REQUIREMENT: Naming Convention lookup (DTOContext → DTORenderContext via globals()).
        """
        # Arrange: Valid DTOContext
        dto_context = DTOContext(dto_name="TestDTO", fields=["id: int", "name: str"])

        # Act: Enrich to RenderContext
        render_context = manager._enrich_context_v2(dto_context, artifact_type="dto")

        # Assert: Type transformation
        assert isinstance(render_context, DTORenderContext), "Should return DTORenderContext"
        assert render_context.dto_name == "TestDTO", "User fields preserved"
        assert len(render_context.fields) == 2, "User fields preserved"

        # Assert: Lifecycle fields added
        assert render_context.template_id == "dto", "Lifecycle: template_id"
        assert render_context.scaffold_created is not None, "Lifecycle: scaffold_created"
        assert render_context.output_path is not None, "Lifecycle: output_path"
        assert render_context.version_hash == "00000000", "Lifecycle: version_hash (placeholder)"

    def test_enrich_context_v2_adds_lifecycle_fields(self, manager: ArtifactManager) -> None:
        """_enrich_context_v2 should add 4 lifecycle fields to RenderContext.

        REQUIREMENT (Cycle 4): output_path, scaffold_created, template_id, version_hash.
        """
        # Arrange
        dto_context = DTOContext(dto_name="MyDTO", fields=["field1: str"])

        # Act
        render_context = manager._enrich_context_v2(dto_context, artifact_type="dto")

        # Assert: All 4 lifecycle fields present
        assert hasattr(render_context, "output_path"), "Missing output_path"
        assert hasattr(render_context, "scaffold_created"), "Missing scaffold_created"
        assert hasattr(render_context, "template_id"), "Missing template_id"
        assert hasattr(render_context, "version_hash"), "Missing version_hash"

        # Assert: Correct values
        assert render_context.template_id == "dto"
        assert isinstance(render_context.output_path, Path)
        assert "MyDTO.py" in str(render_context.output_path), "output_path should use dto_name"

    def test_naming_convention_lookup_success(self, manager: ArtifactManager) -> None:
        """Naming Convention should find RenderContext class via globals().

        REQUIREMENT (Cycle 4): DTOContext.__name__.replace("Context", "RenderContext")
            → DTORenderContext.
        REQUIREMENT: globals() lookup succeeds (schema imported).
        """
        # Arrange
        dto_context = DTOContext(dto_name="TestDTO", fields=[])

        # Act: _enrich_context_v2 uses Naming Convention internally
        render_context = manager._enrich_context_v2(dto_context, artifact_type="dto")

        # Assert: Correct type returned (proves globals() lookup succeeded)
        assert type(render_context).__name__ == "DTORenderContext"
        assert isinstance(render_context, DTORenderContext)

    def test_naming_convention_lookup_failure(self, manager: ArtifactManager) -> None:
        """Naming Convention lookup should fail gracefully if RenderContext not found.

        REQUIREMENT (Cycle 4): Clear error message if class not in globals().
        """
        # Arrange: Create a fake Context class not in globals()

        class FakeContext(BaseContext):
            """Fake context not exported in mcp_server.schemas.__init__."""

            test_field: str = "test"

        fake_context = FakeContext(test_field="value")

        # Act + Assert: Should raise ValidationError with clear message
        with pytest.raises(ValidationError) as exc_info:
            manager._enrich_context_v2(fake_context, artifact_type="dto")

        error_message = str(exc_info.value)
        assert "RenderContext class not found" in error_message
        assert "FakeRenderContext" in error_message, "Should mention expected class name"

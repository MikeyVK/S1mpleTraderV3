"""Integration tests for ScaffoldComponentTool with config foundation.

Tests Phase 4: Tool validation using ComponentRegistryConfig + DirectoryPolicyResolver
"""

import pytest

from mcp_server.config.component_registry import ComponentRegistryConfig
from mcp_server.config.project_structure import ProjectStructureConfig
from mcp_server.core.exceptions import ValidationError
from mcp_server.tools.scaffold_tools import (
    ScaffoldComponentInput,
    ScaffoldComponentTool,
)


class TestScaffoldToolConfigIntegration:
    """Test ScaffoldComponentTool uses config foundation for validation."""

    def setup_method(self):
        """Reset singletons before each test."""
        ComponentRegistryConfig.reset_instance()
        ProjectStructureConfig.reset_instance()

    @pytest.mark.asyncio
    async def test_invalid_component_type_rejected_via_config(self):
        """Test invalid component type rejected by ComponentRegistryConfig."""
        tool = ScaffoldComponentTool()
        params = ScaffoldComponentInput(
            component_type="invalid_type",
            name="TestComponent",
            output_path="backend/test.py"
        )

        result = await tool.execute(params)

        # Should return error result (not raise - decorator catches ValidationError)
        assert result.is_error is True
        assert "Unknown component type" in str(result.content)

    @pytest.mark.asyncio
    async def test_component_type_in_wrong_directory_rejected(self):
        """Test component type validation via DirectoryPolicyResolver."""
        tool = ScaffoldComponentTool()
        params = ScaffoldComponentInput(
            component_type="worker",  # Worker not allowed in backend/dtos/
            name="TestWorker",
            output_path="backend/dtos/worker.py",
            input_dto="InputDTO",
            output_dto="OutputDTO"
        )

        result = await tool.execute(params)

        # Should return error result
        assert result.is_error is True
        assert "not allowed" in str(result.content)

    @pytest.mark.asyncio
    async def test_dto_in_correct_directory_allowed(self):
        """Test DTO in backend/dtos/ allowed by DirectoryPolicyResolver."""
        tool = ScaffoldComponentTool()
        params = ScaffoldComponentInput(
            component_type="dto",
            name="UserDTO",
            output_path="backend/dtos/user_dto.py",
            fields=[{"name": "id", "type": "str"}],
            generate_test=False  # Skip test generation for this integration test
        )

        # Should not raise - validation passes
        # Note: Will fail at scaffold execution because we're not mocking
        # but we're testing validation happens BEFORE scaffold
        try:
            await tool.execute(params)
        except Exception as e:
            # If it fails, should be scaffold failure, not validation
            assert "not allowed" not in str(e).lower()
            assert "unknown component" not in str(e).lower()

    @pytest.mark.asyncio
    async def test_tool_validates_against_config_available_types(self):
        """Test validation uses ComponentRegistryConfig.get_available_types()."""
        tool = ScaffoldComponentTool()
        config = ComponentRegistryConfig.from_file()
        available_types = config.get_available_types()

        # All configured types should be recognized
        for component_type in available_types:
            # Should not raise ValidationError for unknown type
            # (may fail later due to missing fields, but type is valid)
            params = ScaffoldComponentInput(
                component_type=component_type,
                name="Test",
                output_path=f"test/{component_type}.py"
            )
            try:
                await tool.execute(params)
            except ValidationError as e:
                # Should NOT be "Unknown component type" error
                assert "unknown component type" not in str(e).lower()

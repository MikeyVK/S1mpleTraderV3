# tests/mcp_server/unit/test_presenter.py
# template=unit_test version=3d15d309 created=2026-06-12T20:48Z updated=2026-08-19T19:05Z
"""Unit tests for presenter subcomponents: TextPresenter, ValidationResourcePresenter.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.presenters, unittest.mock]
@responsibilities:
    - Test TextPresenter (ITextPresenter) markdown rendering and note grouping
    - Test ValidationResourcePresenter (IResourcePresenter) schema resource generation
    - Test ResponsePresenter (IPresenter) composite coordination
    - Test drift validator validate_presentation_alignment
"""

# Standard library
import json
from typing import Any, ClassVar

# Third-party
import pytest
from pydantic import BaseModel

# Project modules
from mcp_server.core.exceptions import ConfigError
from mcp_server.core.operation_notes import Note
from mcp_server.presenters.response_presenter import ResponsePresenter
from mcp_server.presenters.text_presenter import (
    TextPresenter,
    validate_presentation_alignment,
)
from mcp_server.presenters.validation_resource_presenter import (
    ValidationResourcePresenter,
)
from mcp_server.schemas.cache_publication import CachePublication
from mcp_server.schemas.error_outputs import (
    ExecutionErrorOutput,
    ValidationErrorOutput,
)
from mcp_server.schemas.presentation_output import PresentationResource, PresentedOutput
from mcp_server.schemas.tool_outputs import BaseToolOutput


class DummyOutput(BaseToolOutput):
    result: str = ""
    items: list[str] = []


class DummySimpleOutput(BaseToolOutput):
    result: str = ""


class DummyTool:
    name: ClassVar[str] = "dummy_tool"
    output_model: ClassVar[type[BaseModel]] = DummyOutput


class DummyNoOutputModelTool:
    name: ClassVar[str] = "dummy_no_model"
    output_model: ClassVar[type[BaseModel] | None] = None


class TestValidationResourcePresenter:
    """Test suite for ValidationResourcePresenter."""

    def test_present_resources_validation_error_dto(self) -> None:
        """Verify schema extraction from ValidationErrorOutput."""
        presenter = ValidationResourcePresenter()
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        dto = ValidationErrorOutput(
            error_message="Invalid input",
            validation_errors=[],
            input_schema=schema,
        )

        resources = presenter.present_resources(tool_name="dummy_tool", data=dto)

        assert len(resources) == 1
        assert resources[0].uri == "schema://validation"
        assert resources[0].mime_type == "application/json"
        assert json.loads(resources[0].content) == schema

    def test_present_resources_validation_error_dict(self) -> None:
        """Verify schema extraction from dict with error_type == 'ValidationError'."""
        presenter = ValidationResourcePresenter()
        schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
        data = {
            "error_type": "ValidationError",
            "error_message": "Invalid input",
            "validation_errors": [],
            "input_schema": schema,
        }

        resources = presenter.present_resources(tool_name="dummy_tool", data=data)

        assert len(resources) == 1
        assert resources[0].uri == "schema://validation"
        assert json.loads(resources[0].content) == schema

    def test_present_resources_non_validation_error(self) -> None:
        """Verify empty resource list for non-validation outputs."""
        presenter = ValidationResourcePresenter()
        dto = DummyOutput(success=True, result="All good")

        resources = presenter.present_resources(tool_name="dummy_tool", data=dto)

        assert resources == []


class TestResponsePresenter:
    """Test suite for ResponsePresenter composite."""

    def test_present_combines_text_and_resources(self) -> None:
        """Verify ResponsePresenter coordinates text and resource delegates."""

        class MockTextPres:
            def present_text(
                self,
                tool_name: str,
                data: Any,
                notes: Any = None,
                cache_pub: Any = None,
                success: Any = None,
            ) -> str:
                return "Rendered Markdown"

            def present_notes(self, tool_name: str, notes: Any) -> str | None:
                return None

        class MockResPres:
            def present_resources(self, tool_name: str, data: Any) -> list[PresentationResource]:
                return [PresentationResource(uri="schema://validation", content="{}")]

        presenter = ResponsePresenter(
            text_presenter=MockTextPres(),
            resource_presenter=MockResPres(),
        )

        output = presenter.present(tool_name="dummy_tool", data=DummyOutput(result="test"))

        assert isinstance(output, PresentedOutput)
        assert output.text == "Rendered Markdown"
        assert len(output.resources) == 1
        assert output.resources[0].uri == "schema://validation"


class TestTextPresenter:
    """Test suite for text_presenter."""

    @pytest.fixture
    def mock_yaml_config(self) -> dict[str, Any]:
        return {
            "global": {
                "emojis": {
                    "success": "✅",
                    "failure": "❌",
                    "warning": "⚠️",
                    "query": "📋",
                    "bootstrap": "🚀",
                },
                "default_failure_template": "Failed: {error_message}",
                "formatting": {
                    "none_value": "-",
                    "inline_sequence_separator": ", ",
                    "inline_sequence_omission_template": "… {omitted_count} more",
                    "collection_omission_template": "- … {omitted_count} more {field}",
                    "truncation_notice": "Output truncated.",
                    "cache_unavailable_truncation_notice": "Output unavailable.",
                },
                "next_instruction_texts": {
                    "test_advisory": "🚀 TEST ADVISORY WARNING",
                    "uri_reference": (
                        "*(Full details available in the structured JSON payload. "
                        "View resource: pgmcp://cache/runs/{run_id})*"
                    ),
                },
                "notes": {
                    "groups": {
                        "suggestions": {"header": "Suggestions", "emoji": "💡"},
                        "recoveries": {"header": "Recovery", "emoji": "🔧"},
                    },
                    "templates": {
                        "suggestions": {"try_this": "Try {action}"},
                    },
                },
            },
            "tools": {
                "dummy_tool": {
                    "template_success": "Success: {result}",
                    "template_failure": "Error: {error_message}",
                    "next_instructions": ["test_advisory"],
                },
                "dummy_no_model": {"template_success": "No model success message"},
            },
        }

    def test_present_text_success(self, mock_yaml_config: dict[str, Any]) -> None:
        """Test presenting success output with custom template and emoji prefix."""
        presenter = TextPresenter(config_data=mock_yaml_config)
        dto = DummyOutput(success=True, result="Operation completed")

        text = presenter.present_text(tool_name="dummy_tool", success=True, data=dto)

        assert text == "📋 Success: Operation completed\n\n🚀 TEST ADVISORY WARNING"

    def test_present_text_failure(self, mock_yaml_config: dict[str, Any]) -> None:
        """Test presenting failure output with custom template and emoji prefix."""
        presenter = TextPresenter(config_data=mock_yaml_config)
        dto = ExecutionErrorOutput(error_message="Operation failed")

        text = presenter.present_text(tool_name="dummy_tool", success=False, data=dto)

        assert text == "❌ Error: Operation failed"

    def test_present_text_default_failure_template(self, mock_yaml_config: dict[str, Any]) -> None:
        """Test presenting failure using default failure template when no specific one exists."""
        presenter = TextPresenter(config_data=mock_yaml_config)
        dto = ExecutionErrorOutput(error_message="Something crashed")

        text = presenter.present_text(tool_name="dummy_no_model", success=False, data=dto)

        assert text == "❌ Failed: Something crashed"

    def test_present_text_no_output_model(self, mock_yaml_config: dict[str, Any]) -> None:
        """Test presenting tool with no output model."""
        presenter = TextPresenter(config_data=mock_yaml_config)

        text = presenter.present_text(tool_name="dummy_no_model", success=True, data={})

        assert text == "📋 No model success message"

    def test_present_text_with_notes(self, mock_yaml_config: dict[str, Any]) -> None:
        """Test presenting with operation notes."""
        presenter = TextPresenter(config_data=mock_yaml_config)
        dto = DummyOutput(success=True, result="Done")
        notes = [
            Note(key="try_this", params={"action": "re-running the test"}),
        ]

        text = presenter.present_text(tool_name="dummy_tool", success=True, data=dto, notes=notes)

        assert "💡 Suggestions" in text
        assert "Try re-running the test" in text

    def test_present_text_fallback_run_id_none_validation_error(
        self, mock_yaml_config: dict[str, Any]
    ) -> None:
        """Test presenting fallback when run_id is None and DTO is ValidationErrorOutput."""
        presenter = TextPresenter(config_data=mock_yaml_config)
        dto = ValidationErrorOutput(
            error_message="Validation Failed",
            validation_errors=[],
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
        )

        text = presenter.present_text(
            tool_name="dummy_tool",
            data=dto,
            notes=[],
            cache_pub=CachePublication(run_id=None, success=False, error_code="write_failed"),
        )
        assert "*(Cache publication failed. Full details dumped inline)*" in text
        assert "```json" in text
        assert "Validation Failed" in text

    def test_present_text_fallback_run_id_none(self, mock_yaml_config: dict[str, Any]) -> None:
        """Test presenting when run_id is None and CachePublication.success is False."""
        presenter = TextPresenter(config_data=mock_yaml_config)
        dto = DummyOutput(success=True, result="Fallback JSON test")

        text = presenter.present_text(
            tool_name="dummy_tool",
            data=dto,
            notes=[],
            cache_pub=CachePublication(run_id=None, success=False, error_code="write_failed"),
        )
        assert "*(Cache publication failed. Full details dumped inline)*" in text
        assert "```json" in text
        assert '"result": "Fallback JSON test"' in text

    def test_present_text_fallback_run_id_none_execution_error(
        self, mock_yaml_config: dict[str, Any]
    ) -> None:
        """Test presenting when run_id is None and DTO is ExecutionErrorOutput,
        verifying traceback is stripped.
        """
        presenter = TextPresenter(config_data=mock_yaml_config)
        dto = ExecutionErrorOutput(
            error_message="Test Execution Error",
            traceback="secret_path/to_file.py: line 42",
            params={"arg1": "val1"},
        )

        text = presenter.present_text(
            tool_name="dummy_tool",
            data=dto,
            notes=[],
            cache_pub=CachePublication(run_id=None, success=False, error_code="write_failed"),
        )
        assert "*(Cache publication failed. Full details dumped inline)*" in text
        assert "```json" in text
        assert "Test Execution Error" in text
        assert "traceback" not in text

    def test_drift_validator_generic_notes_invalid_placeholder(self) -> None:
        """Test that validator raises ConfigError when placeholders in
        generic note templates do not align with expected fields.
        """
        config_data = {
            "global": {
                "formatting": {
                    "inline_sequence_omission_template": "… {omitted_count} more",
                    "collection_omission_template": "- … {omitted_count} more {field}",
                    "truncation_notice": "Output truncated.",
                    "cache_unavailable_truncation_notice": "Output unavailable.",
                },
                "notes": {
                    "templates": {
                        "suggestions": {"allowed_branch_types": "Allowed: {invalid_field}"}
                    }
                },
            },
            "tools": {},
        }
        presenter = TextPresenter(config_data=config_data)
        with pytest.raises(ConfigError) as exc_info:
            validate_presentation_alignment(presenter, [])
        assert "placeholder" in str(exc_info.value).lower()

    def test_present_text_cache_publication_failure(self, mock_yaml_config: dict[str, Any]) -> None:
        """Test presenting with CachePublication indicating failure."""
        presenter = TextPresenter(config_data=mock_yaml_config)
        dto = DummyOutput(success=True, result="Fallback JSON test")
        cache_pub = CachePublication(success=False, error_code="write_failed")
        text = presenter.present_text(
            tool_name="dummy_tool",
            data=dto,
            notes=[],
            cache_pub=cache_pub,
        )
        assert "*(Cache publication failed. Full details dumped inline)*" in text
        assert "```json" in text

    def test_present_text_dynamic_category_emoji(self) -> None:
        """Verify that custom categories and emojis configured in YAML are resolved dynamically."""
        config_data = {
            "global": {
                "emojis": {
                    "success": "✅",
                    "failure": "❌",
                    "custom_cat": "🦄",
                },
                "formatting": {
                    "inline_sequence_omission_template": "… {omitted_count} more",
                    "collection_omission_template": "- … {omitted_count} more {field}",
                    "truncation_notice": "Output truncated.",
                    "cache_unavailable_truncation_notice": "Output unavailable.",
                },
            },
            "tools": {
                "dummy_tool": {
                    "category": "custom_cat",
                    "template_success": "Success: {result}",
                }
            },
        }
        presenter = TextPresenter(config_data=config_data)
        dto = DummyOutput(success=True, result="Dynamic emoji test")
        text = presenter.present_text(
            tool_name="dummy_tool",
            data=dto,
            notes=[],
        )
        assert "🦄 Success: Dynamic emoji test" in text

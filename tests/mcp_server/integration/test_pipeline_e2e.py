# tests\mcp_server\integration\test_pipeline_e2e.py
# template=integration_test version=85ea75d4 created=2026-06-20T05:50Z updated=2026-08-19T19:05Z
"""Integration tests for pipeline_e2e.

E2E pipeline integration tests verifying decorator wrapping, caching and presenting

@layer: Tests (Integration)
@dependencies: [pytest, pytest-asyncio, tempfile, ResponseCacheManager, EnforcementRunner]
@responsibilities:
    - Test end-to-end pipeline_e2e
    - Verify full-stack integration
    - Validate file system interactions
"""

# Standard library
import re
import shutil
from unittest.mock import MagicMock

# Third-party
import pytest
from mcp.types import CallToolRequest, CallToolRequestParams
from pydantic import BaseModel

from mcp_server.core.exceptions import (
    ValidationError as CoreValidationError,
)
from mcp_server.core.interfaces.icore_tool import ICoreTool
from mcp_server.core.operation_notes import NoteContext
from mcp_server.core.tool_factory import ToolFactory
from mcp_server.managers.enforcement_runner import EnforcementRunner
from mcp_server.presenters.response_presenter import ResponsePresenter
from mcp_server.presenters.text_presenter import TextPresenter
from mcp_server.presenters.validation_resource_presenter import (
    ValidationResourcePresenter,
)
from mcp_server.schemas.cache_publication import CachePublication
from mcp_server.schemas.error_outputs import EnforcementErrorOutput
from mcp_server.state.response_cache import ResponseCacheManager
from tests.mcp_server.test_support import assert_itool_result, make_test_server


# Dummy Core Tool for E2E validation
class DummyInput(BaseModel):
    val: int


class DummyOutput(BaseModel):
    success: bool = True
    result: str


def _presentation_formatting() -> dict[str, str]:
    return {
        "inline_sequence_omission_template": "… {omitted_count} more",
        "collection_omission_template": "- … {omitted_count} more {field}",
        "truncation_notice": "Output truncated.",
        "cache_unavailable_truncation_notice": "Output unavailable.",
    }


class DummyCoreTool(ICoreTool[DummyInput, DummyOutput]):
    @property
    def name(self) -> str:
        return "dummy_core_tool"

    @property
    def description(self) -> str:
        return "Dummy core tool for E2E testing"

    @property
    def args_model(self) -> type[BaseModel] | None:
        return DummyInput

    async def execute(self, params: DummyInput, context: NoteContext) -> DummyOutput:
        del context  # Unused
        return DummyOutput(success=True, result=f"Value: {params.val}")


@pytest.fixture
def temp_workspace(tmp_path):
    """Create temporary workspace for integration testing."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    yield workspace
    if workspace.exists():
        shutil.rmtree(workspace)


class TestPipelineE2E:
    """Integration test suite for pipeline_e2e."""

    @pytest.mark.asyncio
    async def test_pipeline_e2e_flow(self, temp_workspace):
        """Test the end-to-end flow of the new pipeline structure."""
        cache_manager = ResponseCacheManager()
        enforcement_runner = MagicMock(spec=EnforcementRunner)

        # Build tool using new factory
        factory = ToolFactory(enforcement_runner=enforcement_runner, workspace_root=temp_workspace)
        decorated_tool = factory.create_tool(DummyCoreTool())

        # Set up test server
        server = make_test_server()
        server.response_cache_manager = cache_manager
        config_data = {
            "global": {
                "formatting": _presentation_formatting(),
                "next_instruction_texts": {
                    "uri_reference": (
                        "*(Full details available in the structured JSON payload. "
                        "View resource: pgmcp://cache/runs/{run_id})*"
                    )
                },
            },
            "tools": {
                "dummy_core_tool": {
                    "template_success": "Success: {result}",
                    "next_instructions": ["uri_reference"],
                }
            },
        }
        text_presenter = TextPresenter(config_data=config_data)
        server.presenter = ResponsePresenter(
            text_presenter=text_presenter,
            resource_presenter=ValidationResourcePresenter(),
        )
        server.tools = [decorated_tool]

        # Act - Trigger tool call request
        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="dummy_core_tool",
                arguments={"val": 42},
            )
        )
        response = await handler(req)

        # Assert - Verify presented output and cache
        text_content = assert_itool_result(response.root)
        assert "Value: 42" in text_content

        # Verify run_id cache resolution
        match = re.search(r"pgmcp://cache/runs/([a-f0-9\-]+)", text_content)
        assert match is not None
        run_id = match.group(1)

        cached_dto = cache_manager.get(run_id, DummyOutput)
        assert cached_dto is not None
        assert cached_dto.result == "Value: 42"

    @pytest.mark.asyncio
    async def test_pipeline_cache_fallback(self, temp_workspace):
        """Verify that the pipeline functions correctly and falls back to run_id=None
        if the cache manager returns None on put (simulating cache write failure).
        """
        cache_manager = MagicMock(spec=ResponseCacheManager)
        cache_pub_fail = CachePublication(run_id=None, success=False, error_code="write_failed")
        cache_manager.put.return_value = cache_pub_fail
        enforcement_runner = MagicMock(spec=EnforcementRunner)

        factory = ToolFactory(enforcement_runner=enforcement_runner, workspace_root=temp_workspace)
        decorated_tool = factory.create_tool(DummyCoreTool())

        server = make_test_server()
        server.response_cache_manager = cache_manager
        config_data = {
            "global": {
                "formatting": _presentation_formatting(),
                "next_instruction_texts": {
                    "uri_reference": (
                        "*(Full details available in the structured JSON payload. "
                        "View resource: pgmcp://cache/runs/{run_id})*"
                    )
                },
            },
            "tools": {
                "dummy_core_tool": {
                    "template_success": "Success: {result}",
                    "next_instructions": ["uri_reference"],
                }
            },
        }
        text_presenter = TextPresenter(config_data=config_data)
        server.presenter = ResponsePresenter(
            text_presenter=text_presenter,
            resource_presenter=ValidationResourcePresenter(),
        )
        server.tools = [decorated_tool]

        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="dummy_core_tool",
                arguments={"val": 100},
            )
        )
        response = await handler(req)

        text_content = assert_itool_result(response.root)
        assert "Value: 100" in text_content
        # Check that fallback warning and inline JSON dump are present
        assert "*(Cache publication failed. Full details dumped inline)*" in text_content
        assert '"result": "Value: 100"' in text_content
        cache_manager.put.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_enforcement_blocker(self, temp_workspace):
        """Verify that when the enforcement runner raises a ValidationError,
        the pipeline maps it to EnforcementErrorOutput DTO and returns it formatted.
        """
        cache_manager = ResponseCacheManager()
        enforcement_runner = MagicMock(spec=EnforcementRunner)
        enforcement_runner.run.side_effect = CoreValidationError(
            message="Dirty workdir detected",
            error_code="dirty_workdir",
            params={"branch": "feature-branch"},
        )

        factory = ToolFactory(enforcement_runner=enforcement_runner, workspace_root=temp_workspace)
        decorated_tool = factory.create_tool(DummyCoreTool())

        server = make_test_server()
        server.response_cache_manager = cache_manager
        config_data = {
            "global": {
                "formatting": _presentation_formatting(),
                "default_failure_template": "Failure: {error_message}",
                "emojis": {"failure": "❌"},
                "failures": {"dirty_workdir": "Branch {branch} is dirty!"},
            },
            "tools": {},
        }
        text_presenter = TextPresenter(config_data=config_data)
        server.presenter = ResponsePresenter(
            text_presenter=text_presenter,
            resource_presenter=ValidationResourcePresenter(),
        )
        server.tools = [decorated_tool]

        handler = server.server.request_handlers[CallToolRequest]
        req = CallToolRequest(
            params=CallToolRequestParams(
                name="dummy_core_tool",
                arguments={"val": 42},
            )
        )
        response = await handler(req)

        assert getattr(response.root, "is_error", False) or getattr(response.root, "isError", False)
        assert len(response.root.content) == 1
        text_content = response.root.content[0].text
        assert "❌ Branch feature-branch is dirty!" in text_content

        match = re.search(r"pgmcp://cache/runs/([a-f0-9\-]+)", text_content)
        assert match is not None
        run_id = match.group(1)

        cached_dto = cache_manager.get(run_id, EnforcementErrorOutput)
        assert cached_dto is not None
        assert cached_dto.success is False
        assert cached_dto.error_type == "EnforcementError"
        assert cached_dto.error_code == "dirty_workdir"
        assert cached_dto.params == {"branch": "feature-branch"}

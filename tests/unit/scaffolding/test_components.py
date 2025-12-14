"""Unit tests for scaffolding components."""
from unittest.mock import MagicMock

import pytest

from mcp_server.core.exceptions import ValidationError
from mcp_server.scaffolding.renderer import JinjaRenderer
from mcp_server.scaffolding.components.dto import DTOScaffolder
from mcp_server.scaffolding.components.worker import WorkerScaffolder


@pytest.fixture(name="renderer_mock")
def fixture_renderer_mock() -> MagicMock:
    """Mock JinjaRenderer."""
    renderer = MagicMock(spec=JinjaRenderer)
    renderer.render.return_value = "rendered_content"
    return renderer


class TestDTOScaffolder:
    """Tests for DTOScaffolder."""

    def test_validation(self, renderer_mock: MagicMock) -> None:
        """Test name validation."""
        scaffolder = DTOScaffolder(renderer_mock)
        with pytest.raises(ValidationError):
            scaffolder.validate(name="invalid_name")

    def test_scaffold_defaults(self, renderer_mock: MagicMock) -> None:
        """Test scaffolding with defaults."""
        scaffolder = DTOScaffolder(renderer_mock)
        result = scaffolder.scaffold(name="TestDTO", fields=[])

        assert result == "rendered_content"
        renderer_mock.render.assert_called_with(
            "components/dto.py.jinja2",
            name="TestDTO",
            fields=[],
            id_prefix="TES",  # Derived
            docstring="TestDTO data transfer object."  # Default
        )


class TestWorkerScaffolder:
    """Tests for WorkerScaffolder."""

    def test_scaffold_defaults(self, renderer_mock: MagicMock) -> None:
        """Test worker scaffolding."""
        scaffolder = WorkerScaffolder(renderer_mock)
        result = scaffolder.scaffold(
            name="MyWorker",
            input_dto="In",
            output_dto="Out"
        )

        assert result == "rendered_content"
        renderer_mock.render.assert_called_with(
            "components/worker.py.jinja2",
            name="MyWorker",
            input_dto="In",
            output_dto="Out"
        )

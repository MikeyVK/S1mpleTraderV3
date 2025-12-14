"""Unit tests for scaffolding components."""
from unittest.mock import MagicMock

import pytest

from mcp_server.core.exceptions import ExecutionError, ValidationError
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

    def test_fallback(self, renderer_mock: MagicMock) -> None:
        """Test fallback rendering."""
        renderer_mock.render.side_effect = ExecutionError("Template missing")
        scaffolder = DTOScaffolder(renderer_mock)

        result = scaffolder.scaffold(
            name="TestDTO",
            fields=[{"name": "f1", "type": "str"}]
        )

        assert "@dataclass(frozen=True)" in result
        assert "class TestDTO:" in result
        assert "f1: str" in result


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

    def test_fallback(self, renderer_mock: MagicMock) -> None:
        """Test fallback rendering."""
        renderer_mock.render.side_effect = ExecutionError("Template missing")
        scaffolder = WorkerScaffolder(renderer_mock)

        result = scaffolder.scaffold(
            name="MyWorker",
            input_dto="In",
            output_dto="Out"
        )

        assert "class MyWorker(BaseWorker[In, Out]):" in result
        assert "def process(self, input_data: In) -> Out:" in result

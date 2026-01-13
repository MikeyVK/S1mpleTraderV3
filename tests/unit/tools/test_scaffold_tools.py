"""Unit tests for scaffold_tools.py."""
import pytest
from unittest.mock import MagicMock, patch, ANY
from mcp_server.core.exceptions import ValidationError
from mcp_server.tools.scaffold_tools import (
    ScaffoldComponentTool, ScaffoldComponentInput,
    ScaffoldDesignDocTool, ScaffoldDesignDocInput
)

@pytest.fixture
def mock_renderer():
    renderer = MagicMock()
    # Mock render to return a string so casts don't fail if they check type
    renderer.render.return_value = "generated_content"
    return renderer

@pytest.fixture
def mock_write_file():
    with patch("mcp_server.tools.scaffold_tools.write_scaffold_file") as mock:
        yield mock

@pytest.mark.asyncio
async def test_scaffold_dto(mock_renderer, mock_write_file):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="dto",
        name="TestDto",
        output_path="path/to/dto.py",
        fields=[{"name": "field1", "type": "str"}]
    )

    result = await tool.execute(params)

    # Verify render called for DTO
    mock_renderer.render.assert_any_call(
        "components/dto.py.jinja2",
        name="TestDto",
        fields=[{"name": "field1", "type": "str"}],
        docstring="TestDto data transfer object.", # Default applied by scaffolder
        id_prefix=ANY # derived
    )
    
    # Verify render called for Test (default generate_test=True)
    mock_renderer.render.assert_any_call(
        "components/dto_test.py.jinja2",
        dto_name="TestDto",
        test_type="dto",
        module_path="path.to.dto",
        all_fields=[{"name": "field1", "type": "str"}],
        required_fields=[{"name": "field1", "type": "str"}],
        optional_fields=[],
        id_prefix=ANY
    )

    # Verify write called
    assert mock_write_file.call_count == 2
    mock_write_file.assert_any_call("path/to/dto.py", "generated_content")
    # Test path derivation: path/to/dto.py -> path/to/dto_test.py
    mock_write_file.assert_any_call("path/to/dto_test.py", "generated_content")

    assert "Scaffolded dto 'TestDto'" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_scaffold_component_unknown_type(mock_renderer):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="unknown_type",
        name="Test",
        output_path="path.py"
    )
    
    result = await tool.execute(params)

    assert result.is_error
    assert "Unknown component type: 'unknown_type'" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_scaffold_worker(mock_renderer, mock_write_file):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="worker",
        name="TestWorker",
        output_path="worker.py",
        input_dto="InputDto",
        output_dto="OutputDto"
    )
    
    result = await tool.execute(params)
    
    mock_renderer.render.assert_called_with(
        "components/worker.py.jinja2",
        name="TestWorker",
        input_dto="InputDto",
        output_dto="OutputDto"
    )
    mock_write_file.assert_called_once_with("worker.py", "generated_content")
    assert "Scaffolded worker 'TestWorker'" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_scaffold_worker_missing_args(mock_renderer):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="worker",
        name="TestWorker",
        output_path="worker.py"
        # Missing dtos
    )
    
    result = await tool.execute(params)

    assert result.is_error

@pytest.mark.asyncio
async def test_scaffold_adapter(mock_renderer, mock_write_file):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="adapter",
        name="TestAdapter",
        output_path="adapter.py",
        methods=[{"name": "fetch", "return": "dict"}]
    )
    
    await tool.execute(params)
    
    mock_renderer.render.assert_called_with(
        "components/adapter.py.jinja2",
        name="TestAdapter",
        methods=[{"name": "fetch", "return": "dict"}]
    )
    mock_write_file.assert_called_once()

@pytest.mark.asyncio
async def test_scaffold_tool_component(mock_renderer, mock_write_file):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="tool",
        name="TestTool",
        output_path="tool.py",
        input_schema={"type": "object"}
    )
    
    await tool.execute(params)
    
    mock_renderer.render.assert_called_with(
        "components/tool.py.jinja2",
        name="TestTool",
        description="",
        input_schema={"type": "object"},
        docstring=None
    )
    mock_write_file.assert_called_once()

@pytest.mark.asyncio
async def test_scaffold_resource(mock_renderer, mock_write_file):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="resource",
        name="TestResource",
        output_path="res.py",
        uri_pattern="test://{id}",
        mime_type="application/json"
    )

    await tool.execute(params)
    
    mock_renderer.render.assert_called_with(
        "components/resource.py.jinja2",
        name="TestResource",
        description="",
        uri_pattern="test://{id}",
        mime_type="application/json",
        docstring=None
    )
    mock_write_file.assert_called_once()

@pytest.mark.asyncio
async def test_scaffold_schema(mock_renderer, mock_write_file):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="schema",
        name="TestSchema",
        output_path="schema.py",
        models=[{"name": "M", "fields": []}]
    )

    await tool.execute(params)
    
    mock_renderer.render.assert_called_with(
        "components/schema.py.jinja2",
        name="TestSchema",
        description=None,
        models=[{"name": "M", "fields": []}],
        docstring=None
    )
    mock_write_file.assert_called_once()

@pytest.mark.asyncio
async def test_scaffold_interface(mock_renderer, mock_write_file):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="interface",
        name="ITest",
        output_path="interface.py",
        methods=[{"name": "m"}]
    )

    await tool.execute(params)
    
    mock_renderer.render.assert_called_with(
        "components/interface.py.jinja2",
        name="ITest",
        description=None,
        methods=[{"name": "m"}],
        docstring=None
    )
    mock_write_file.assert_called_once()

@pytest.mark.asyncio
async def test_scaffold_service(mock_renderer, mock_write_file):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="service",
        name="TestService",
        output_path="service.py",
        service_type="orchestrator",
        dependencies=["Dep"],
        methods=[{"name": "m"}]
    )

    await tool.execute(params)
    
    mock_renderer.render.assert_called_with(
        "components/service_orchestrator.py.jinja2",
        name="TestService",
        dependencies=["Dep"],
        methods=[{"name": "m"}],
        description=None,
        service_type="orchestrator"
    )
    mock_write_file.assert_called_once()

@pytest.mark.asyncio
async def test_scaffold_generic_component(mock_renderer, mock_write_file):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="generic",
        name="Gen",
        output_path="gen.py",
        template_name="tpl.j2",
        context={"k": "v"}
    )

    await tool.execute(params)
    
    mock_renderer.render.assert_called_with("tpl.j2", k="v")
    mock_write_file.assert_called_once()

@pytest.mark.asyncio
async def test_scaffold_generic_missing_args(mock_renderer):
    tool = ScaffoldComponentTool(renderer=mock_renderer)
    params = ScaffoldComponentInput(
        component_type="generic",
        name="Gen",
        output_path="gen.py"
    )
    
    result = await tool.execute(params)

    assert result.is_error

@pytest.mark.asyncio
async def test_scaffold_design_doc(mock_renderer, mock_write_file):
    tool = ScaffoldDesignDocTool(renderer=mock_renderer)
    params = ScaffoldDesignDocInput(
        title="My Design",
        output_path="design.md",
        doc_type="design",
        author="Me"
    )
    
    result = await tool.execute(params)
    
    mock_renderer.render.assert_called_with(
        "documents/design.md.jinja2",
        title="My Design",
        author="Me",
        summary=None,
        sections=None,
        status="DRAFT",
        doc_type="design"
    )
    mock_write_file.assert_called_with("design.md", "generated_content")
    assert "Created design document: design.md" in result.content[0]["text"]

@pytest.mark.asyncio
async def test_scaffold_generic_doc(mock_renderer, mock_write_file):
    tool = ScaffoldDesignDocTool(renderer=mock_renderer)
    params = ScaffoldDesignDocInput(
        title="Generic Doc",
        output_path="doc.md",
        doc_type="generic",
        context={"extra": "value"}
    )
    
    await tool.execute(params)
    
    mock_renderer.render.assert_called_with(
        "documents/generic.md.jinja2",
        title="Generic Doc",
        extra="value",
        doc_type="generic",
        author=None,
        summary=None,
        sections=None,
        status="DRAFT"
    )
    mock_write_file.assert_called_once()

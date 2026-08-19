"""Unit tests for label_tools.py.

@layer: Tests (Unit)
@dependencies: pytest, mcp_server.tools.label_tools, mcp_server.config.schemas
"""

from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from mcp_server.config.loader import ConfigLoader
from mcp_server.config.schemas import LabelConfig
from mcp_server.core.operation_notes import NoteContext
from mcp_server.schemas.tool_outputs import (
    CreateLabelOutput,
    DeleteLabelOutput,
    LabelOperationOutput,
    ListLabelsOutput,
)
from mcp_server.tools.label_tools import (
    AddLabelsInput,
    AddLabelsTool,
    CreateLabelInput,
    CreateLabelTool,
    DeleteLabelInput,
    DeleteLabelTool,
    ListLabelsInput,
    ListLabelsTool,
    RemoveLabelsInput,
    RemoveLabelsTool,
)
from tests.mcp_server.test_support import get_default_server_root

_PGMCP_CONFIG = Path(__file__).resolve().parents[4] / get_default_server_root() / "config"


@pytest.fixture
def mock_github_manager() -> MagicMock:
    return MagicMock()


@pytest.fixture
def test_label_config(tmp_path: Path) -> Generator[LabelConfig, None, None]:
    """Create a temp label config with test labels."""
    yaml_content = """version: "1.0.0"
labels:
  - name: "bug"
    color: "d73a4a"
  - name: "p1"
    color: "0052cc"
  - name: "new-label"
    color: "0000ff"
  - name: "type:hotfix"
    color: "ff0000"
"""
    yaml_file = tmp_path / "labels.yaml"
    yaml_file.write_text(yaml_content)

    yield ConfigLoader(_PGMCP_CONFIG).load_label_config(config_path=yaml_file)


@pytest.mark.asyncio
async def test_list_labels_tool(
    mock_github_manager: MagicMock, test_label_config: LabelConfig
) -> None:
    tool = ListLabelsTool(manager=mock_github_manager, label_config=test_label_config)
    bug_mock = MagicMock(color="red", description="Its a feature")
    bug_mock.name = "bug"
    feat_mock = MagicMock(color="green", description="")
    feat_mock.name = "feat"
    mock_github_manager.list_labels.return_value = [bug_mock, feat_mock]

    result = await tool.execute(ListLabelsInput(), NoteContext())

    mock_github_manager.list_labels.assert_called_once()
    assert isinstance(result, ListLabelsOutput)
    assert result.success is True
    assert result.total_labels == 2
    assert result.labels[0].name == "bug"
    assert result.labels[1].name == "feat"


@pytest.mark.asyncio
async def test_create_label_tool(
    mock_github_manager: MagicMock, test_label_config: LabelConfig
) -> None:
    tool = CreateLabelTool(
        manager=mock_github_manager,
        label_config=test_label_config,
        workphases_config=MagicMock(),
    )
    label_mock = MagicMock()
    label_mock.name = "type:hotfix"
    mock_github_manager.create_label.return_value = label_mock

    params = CreateLabelInput(name="type:hotfix", color="ff0000", description="Hotfix")
    result = await tool.execute(params, NoteContext())

    mock_github_manager.create_label.assert_called_with(
        name="type:hotfix", color="ff0000", description="Hotfix"
    )
    assert isinstance(result, CreateLabelOutput)
    assert result.success is True
    assert result.label_name == "type:hotfix"
    assert result.color == "ff0000"


@pytest.mark.asyncio
async def test_delete_label_tool(
    mock_github_manager: MagicMock, test_label_config: LabelConfig
) -> None:
    tool = DeleteLabelTool(manager=mock_github_manager, label_config=test_label_config)

    params = DeleteLabelInput(name="old-label")
    result = await tool.execute(params, NoteContext())

    mock_github_manager.delete_label.assert_called_with("old-label")
    assert isinstance(result, DeleteLabelOutput)
    assert result.success is True
    assert result.label_name == "old-label"


@pytest.mark.asyncio
async def test_add_labels_tool(
    mock_github_manager: MagicMock, test_label_config: LabelConfig
) -> None:
    tool = AddLabelsTool(
        manager=mock_github_manager,
        label_config=test_label_config,
        workphases_config=MagicMock(),
    )

    result = await tool.execute(
        AddLabelsInput(issue_number=10, labels=["bug", "p1"]), NoteContext()
    )

    mock_github_manager.add_labels.assert_called_with(10, ["bug", "p1"])
    assert isinstance(result, LabelOperationOutput)
    assert result.success is True
    assert result.issue_number == 10
    assert result.labels == ["bug", "p1"]


@pytest.mark.asyncio
async def test_remove_labels_tool(
    mock_github_manager: MagicMock, test_label_config: LabelConfig
) -> None:
    tool = RemoveLabelsTool(manager=mock_github_manager, label_config=test_label_config)

    result = await tool.execute(RemoveLabelsInput(issue_number=10, labels=["bug"]), NoteContext())

    mock_github_manager.remove_labels.assert_called_with(10, ["bug"])
    assert isinstance(result, LabelOperationOutput)
    assert result.success is True
    assert result.issue_number == 10
    assert result.labels == ["bug"]

"""Tests for filesystem and status components."""
import pytest
from pathlib import Path
from unittest.mock import Mock
from mcp_server.adapters.filesystem import FilesystemAdapter
from mcp_server.resources.status import StatusResource
from mcp_server.core.exceptions import ValidationError

def test_fs_adapter_read_write(tmp_path):
    adapter = FilesystemAdapter(root_path=str(tmp_path))

    adapter.write_file("test.txt", "content")
    assert (tmp_path / "test.txt").exists()
    assert adapter.read_file("test.txt") == "content"

def test_fs_adapter_security(tmp_path):
    adapter = FilesystemAdapter(root_path=str(tmp_path))

    with pytest.raises(ValidationError):
        adapter.read_file("../outside.txt")

@pytest.mark.asyncio
async def test_status_resource():
    mock_git = Mock()
    mock_git.get_status.return_value = {
        "branch": "feature/test",
        "is_clean": True
    }

    resource = StatusResource(git_adapter=mock_git)
    content = await resource.read("st3://status/phase")

    assert "Implementation" in content
    assert "feature/test" in content

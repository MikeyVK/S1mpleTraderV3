"""Tests for filesystem and status components."""

from unittest.mock import Mock

import pytest

from mcp_server.adapters.filesystem import FilesystemAdapter
from mcp_server.core.exceptions import ValidationError
from mcp_server.resources.status import StatusResource


def test_fs_adapter_read_write(tmp_path) -> None:
    """Test filesystem adapter can write and read files correctly."""
    adapter = FilesystemAdapter(root_path=str(tmp_path))

    adapter.write_file("test.txt", "content")
    assert (tmp_path / "test.txt").exists()
    assert adapter.read_file("test.txt") == "content"


def test_fs_adapter_security(tmp_path) -> None:
    """Test filesystem adapter prevents path traversal attacks."""
    adapter = FilesystemAdapter(root_path=str(tmp_path))

    with pytest.raises(ValidationError):
        adapter.read_file("../outside.txt")


@pytest.mark.asyncio
async def test_status_resource() -> None:
    """Test status resource returns branch and phase information."""
    mock_git = Mock()
    mock_git.get_status.return_value = {"branch": "feature/test", "is_clean": True}

    resource = StatusResource(git_adapter=mock_git)
    content = await resource.read("st3://status/phase")

    assert "Implementation" in content
    assert "feature/test" in content

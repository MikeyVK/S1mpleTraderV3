"""Filesystem adapter for safe operations."""
from pathlib import Path

from mcp_server.config.settings import settings
from mcp_server.core.exceptions import MCPSystemError, ValidationError


class FilesystemAdapter:
    """Adapter for safe filesystem operations."""

    def __init__(self, root_path: str | None = None) -> None:
        self.root_path = Path(root_path or settings.server.workspace_root).resolve()  # pylint: disable=no-member

    def _validate_path(self, path: str | Path) -> Path:
        """Ensure path is within workspace root."""
        full_path = (self.root_path / path).resolve()
        if not str(full_path).startswith(str(self.root_path)):
            raise ValidationError(f"Access denied: {path} is outside workspace")
        return full_path

    def read_file(self, path: str) -> str:
        """Read file content."""
        full_path = self._validate_path(path)
        try:
            return full_path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise MCPSystemError(f"File not found: {path}") from e
        except Exception as e:
            raise MCPSystemError(f"Failed to read file: {e}") from e

    def write_file(self, path: str, content: str) -> None:
        """Write file content."""
        full_path = self._validate_path(path)
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise MCPSystemError(f"Failed to write file: {e}") from e

    def list_files(self, path: str = ".") -> list[str]:
        """List files in directory."""
        full_path = self._validate_path(path)
        try:
            return [
                str(p.relative_to(self.root_path))
                for p in full_path.rglob("*")
                if p.is_file() and not any(part.startswith(".") for part in p.parts)
            ]
        except Exception as e:
            raise MCPSystemError(f"Failed to list files: {e}") from e

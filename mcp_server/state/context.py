"""Session context management."""
from typing import Any

from pydantic import BaseModel, Field


class SessionContext(BaseModel):
    """Holds the state of the current session."""
    current_task: str | None = None
    active_files: list[str] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)

    def set_task(self, task: str) -> None:
        """Set the current task."""
        self.current_task = task

    def add_file(self, path: str) -> None:
        """Add a file to the active files list."""
        if path not in self.active_files:
            self.active_files.append(path)  # pylint: disable=no-member

# Global context instance
context = SessionContext()

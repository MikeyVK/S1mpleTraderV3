"""Session context management."""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class SessionContext(BaseModel):
    """Holds the state of the current session."""
    current_task: Optional[str] = None
    active_files: list[str] = Field(default_factory=list)
    memory: Dict[str, Any] = Field(default_factory=dict)

    def set_task(self, task: str) -> None:
        self.current_task = task

    def add_file(self, path: str) -> None:
        if path not in self.active_files:
            self.active_files.append(path)

# Global context instance
context = SessionContext()

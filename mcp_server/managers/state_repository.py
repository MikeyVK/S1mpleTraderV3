# mcp_server\managers\state_repository.py
# template=generic version=f35abd82 created=2026-03-12T15:02Z updated=
"""State repository abstractions for branch workflow state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from mcp_server.utils.atomic_json_writer import AtomicJsonWriter


class BranchState(BaseModel):
    """Validated immutable branch state."""

    model_config = ConfigDict(frozen=True, extra="allow")

    branch: str
    issue_number: int | None = None
    workflow_name: str
    current_phase: str
    parent_branch: str | None = None
    transitions: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None
    current_tdd_cycle: int | None = None
    last_tdd_cycle: int | None = None
    tdd_cycle_history: list[dict[str, Any]] = Field(default_factory=list)


class FileStateRepository:
    """Filesystem-backed repository for branch state."""

    def __init__(
        self,
        state_file: Path,
        writer: AtomicJsonWriter | None = None,
    ) -> None:
        self._state_file = state_file
        self._writer = writer or AtomicJsonWriter()

    def load(self, branch: str) -> BranchState:
        """Load and validate state from disk."""
        data = json.loads(self._state_file.read_text(encoding="utf-8"))
        if "branch" not in data:
            data["branch"] = branch
        return BranchState.model_validate(data)

    def save(self, state: BranchState) -> None:
        """Persist validated state to disk."""
        payload = state.model_dump(mode="json")
        self._writer.write_json(self._state_file, payload, temp_name=".state.tmp")


class InMemoryStateRepository:
    """In-memory repository for unit tests."""

    def __init__(self) -> None:
        self._states: dict[str, BranchState] = {}

    def load(self, branch: str) -> BranchState:
        """Load previously saved state."""
        return self._states[branch]

    def save(self, state: BranchState) -> None:
        """Save state in memory."""
        self._states[state.branch] = state

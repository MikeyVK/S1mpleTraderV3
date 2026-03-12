# mcp_server\managers\state_repository.py
# template=generic version=f35abd82 created=2026-03-12T15:02Z updated=
"""State repository abstractions for branch workflow state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from mcp_server.utils.atomic_json_writer import AtomicJsonWriter


class BranchState(BaseModel):
    """Validated immutable branch state."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    branch: str
    issue_number: int | None = None
    workflow_name: str
    current_phase: str
    current_cycle: int | None = Field(
        default=None,
        validation_alias=AliasChoices("current_cycle", "current_tdd_cycle"),
    )
    last_cycle: int | None = Field(
        default=None,
        validation_alias=AliasChoices("last_cycle", "last_tdd_cycle"),
    )
    cycle_history: list[dict[str, Any]] = Field(
        default_factory=list,
        validation_alias=AliasChoices("cycle_history", "tdd_cycle_history"),
    )
    required_phases: list[str] = Field(default_factory=list)
    execution_mode: str = "normal"
    skip_reason: str | None = None
    issue_title: str | None = None
    parent_branch: str | None = None
    created_at: str | None = None
    transitions: list[dict[str, Any]] = Field(default_factory=list)
    reconstructed: bool = False

    def with_updates(self, **updates: object) -> BranchState:
        """Return a copy with updated fields."""
        return self.model_copy(update=updates)

    def get(self, key: str, default: object = None) -> object:
        """Temporary compatibility helper for legacy read access."""
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> object:
        """Temporary compatibility helper for legacy indexed access."""
        return getattr(self, key)

    def __contains__(self, key: object) -> bool:
        """Support membership checks in older tests and callers."""
        return isinstance(key, str) and hasattr(self, key)

    @property
    def current_tdd_cycle(self) -> int | None:
        """Backward-compatible alias for older callers."""
        return self.current_cycle

    @property
    def last_tdd_cycle(self) -> int | None:
        """Backward-compatible alias for older callers."""
        return self.last_cycle

    @property
    def tdd_cycle_history(self) -> list[dict[str, Any]]:
        """Backward-compatible alias for older callers."""
        return self.cycle_history


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

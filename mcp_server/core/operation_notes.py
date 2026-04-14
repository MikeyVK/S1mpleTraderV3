from __future__ import annotations

# Standard library
from dataclasses import dataclass, field
from typing import Literal, Protocol, Sequence, TypeVar, runtime_checkable

# Project modules
from mcp_server.tools.tool_result import ToolResult

T = TypeVar("T")


@runtime_checkable
class Renderable(Protocol):
    """Note variants that produce user-visible output implement this protocol.

    Variants without to_message() are machine-readable coordination notes only
    and do not appear in the rendered user-facing response.
    """

    def to_message(self) -> str: ...


@dataclass(frozen=True)
class ExclusionNote:
    """Written by EnforcementRunner when a file is confirmed tracked and identified for exclusion from the commit index."""

    kind: Literal["exclusion"] = field(default="exclusion", init=False)
    file_path: str  # workspace-relative path

    def to_message(self) -> str:
        return f"Excluded from commit index: {self.file_path}"


@dataclass(frozen=True)
class CommitNote:
    """Written by GitCommitTool after a successful commit.

    NOT Renderable: the commit hash is already in ToolResult.text(sha).
    Exists solely for type-safe test assertions via context.of_type(CommitNote).
    Implementing to_message() would duplicate the primary output -- a DRY violation.
    """

    kind: Literal["commit"] = field(default="commit", init=False)
    commit_hash: str
    # Intentionally does not implement to_message()


@dataclass(frozen=True)
class SuggestionNote:
    """Written immediately before raising an exception where the action is advisory.

    Semantic contract:
      - message is ACTIONABLE -- tells the user what to do next.
      - The exception message is DIAGNOSTIC -- describes what failed.
      - The two must not overlap. Together they are more informative than either alone.

    Example:
      Exception:      ConfigError("Phase 'foo' not found in workphases config")
      SuggestionNote: "Verify phase names in workphases.yaml"
    """

    kind: Literal["suggestion"] = field(default="suggestion", init=False)
    message: str
    subject: str | None = None  # optional named context (e.g., config file path)

    def to_message(self) -> str:
        base = f"Suggestion: {self.message}"
        return f"{base} ({self.subject})" if self.subject else base


@dataclass(frozen=True)
class BlockerNote:
    """Written immediately before raising PreflightError.

    Replaces the former PreflightError(blockers=[...]) constructor parameter.
    Each blocking condition becomes a separate BlockerNote for machine-readability.

    Semantic contract:
      - message describes a condition that BLOCKS further execution.
      - The exception message is DIAGNOSTIC -- describes that preflight failed.
      - Together: exception says "preflight failed"; BlockerNote says "because X".

    Example:
      Exception:   PreflightError("Preflight checks failed")
      BlockerNote: "Branch 'feature/42' is not in a clean state -- commit or stash changes"
    """

    kind: Literal["blocker"] = field(default="blocker", init=False)
    message: str

    def to_message(self) -> str:
        return f"Blocker: {self.message}"


@dataclass(frozen=True)
class RecoveryNote:
    """Written immediately before raising ExecutionError.

    Replaces the former ExecutionError(recovery=[...]) constructor parameter.
    Each recovery action becomes a separate RecoveryNote for machine-readability.

    Semantic contract:
      - message describes a RECOVERY ACTION the user can take.
      - The exception message is DIAGNOSTIC -- describes what execution failed.
      - Together: exception says "execution failed"; RecoveryNote says "try X".

    Example:
      Exception:    ExecutionError("Git commit failed")
      RecoveryNote: "Run 'git status' to check for unresolved merge conflicts"
    """

    kind: Literal["recovery"] = field(default="recovery", init=False)
    message: str

    def to_message(self) -> str:
        return f"Recovery: {self.message}"


@dataclass(frozen=True)
class InfoNote:
    """General informational note produced by any component."""

    kind: Literal["info"] = field(default="info", init=False)
    message: str

    def to_message(self) -> str:
        return self.message


NoteEntry = ExclusionNote | CommitNote | SuggestionNote | BlockerNote | RecoveryNote | InfoNote


@dataclass
class NoteContext:
    """Bidirectional per-call notes bus.

    Lifetime: exactly one tool invocation. Constructed as a local variable
    in handle_call_tool. Never stored as server instance state.

    Producers call produce(). Consumers call of_type(). The server calls
    render_to_response() once, unconditionally, after execution completes.
    """

    _entries: list[NoteEntry] = field(default_factory=list)

    def produce(self, note: NoteEntry) -> None:
        """Write a note. Preserves insertion order."""
        self._entries.append(note)

    def of_type(self, t: type[T]) -> Sequence[T]:
        """Return all notes of the given type, in insertion order.

        Type-safe: pyright infers the return element type from the argument.
        Example: context.of_type(ExclusionNote) -> Sequence[ExclusionNote]
        """
        return [n for n in self._entries if isinstance(n, t)]

    def render_to_response(self, base: ToolResult) -> ToolResult:
        """Append all Renderable notes as an additional TextContent block.

        Called once by the server after tool execution, on both success and
        error paths. Returns base unchanged when no Renderable entries exist.
        Insertion order is preserved.
        """
        renderable = [n for n in self._entries if isinstance(n, Renderable)]
        if not renderable:
            return base
        notes_text = "\n".join(n.to_message() for n in renderable)
        augmented = list(base.content) + [{"type": "text", "text": notes_text}]
        return base.model_copy(update={"content": augmented})

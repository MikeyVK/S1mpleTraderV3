<!-- docs/development/issue433/design.md -->
<!-- template=design version=5827e841 created=2026-07-21T10:31Z updated=2026-07-21T10:33Z -->
# Design Document: Frictionless safe_edit_file with Clean Break

**Status:** APPROVED  
**Version:** 1.0.0  
**Last Updated:** 2026-07-21  

---

## 1. Context & Requirements

### 1.1. Problem Statement

Refactor `safe_edit_file` into a frictionless string-anchored and symbol-anchored edit tool, eliminating line-number counting friction while enforcing strict file existence governance and platform safety gates.

### 1.2. Requirements

**Functional:**
- [x] Support 4 frictionless string-anchored operations: `replace`, `append`, `rewrite`, `pattern_replace`.
- [x] Enforce strict file existence (`must_exist=True`) across all operations to uphold `scaffold_artifact` governance for new file creation.
- [x] Provide `difflib` fuzzy-match diagnostic suggestions when `target_content` is not found.

**Non-Functional:**
- [x] Strict CQS compliance: pure query transformers (`_generate_new_content`, `_validate`) before atomic file I/O.
- [x] SOLID & ISP compliance: generic `IAtomicFileWriter` protocol interface supporting all file types (text, python, markdown, json, yaml).
- [x] Pydantic `model_config = ConfigDict(extra="forbid")` on all input and operation models.

### 1.3. Constraints
- **Approved Strategy**: Clean Break (direct in-place refactor of `SafeEditInput` and `SafeEditTool` without legacy parameters or shims).
- **Naming Rule**: No version numbers (e.g., "2.0") in code, docstrings, filenames, or documentation.

---

## 2. Design Options

### 2.1. Option A: Clean Break In-Place Refactor (Chosen)

Directly refactor `SafeEditInput` and `SafeEditTool` in-place to the new 4-operation model (`replace`, `append`, `rewrite`, `pattern_replace`) while retaining the exact tool interface name and MCP server registration.

**Pros:**
- Eliminates line-number friction completely in a single PR.
- Leaves zero technical debt or legacy shims in the codebase.
- Preserves existing MCP tool registration and server architecture.

**Cons:**
- Requires updating existing unit and integration test fixtures to the new input model.

### 2.2. Option B: Deprecation Shim / Dual Tools (Rejected)

Retain legacy `line_edits` and `insert_lines` fields alongside new operations or create a temporary dual-tool shim.

**Pros:**
- Avoids modifying legacy test fixtures immediately.

**Cons:**
- Violates YAGNI §9.0 (`ARCHITECTURE_PRINCIPLES.md`) by building temporary shims.
- Confuses AI callers by leaving fragile line-number fields active.

---

## 3. Chosen Design

**Decision:** Option A — In-place Clean Break refactor of `SafeEditInput` and `SafeEditTool` to the new 4-operation model (`replace`, `append`, `rewrite`, `pattern_replace`) with strict file existence enforcement (`must_exist=True`), generic `IAtomicFileWriter` abstraction, and `difflib` fuzzy-match typo diagnostics.

**Rationale:** Eliminates AI line-counting friction completely while enforcing `scaffold_artifact` governance for new files and maintaining AST validation, atomic IO, and mutex locking.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **In-place Clean Break Refactor** | Eliminates line-number friction completely in 1 PR without shims or version labels. |
| **Strict File Existence (`must_exist=True`)** | Enforces `scaffold_artifact` governance for new file creation and prevents `safe_edit_file` from bypassing template rules. |
| **Generic `IAtomicFileWriter` Interface** | Decouples atomic file writing from JSON-specific writers to support Python, Markdown, YAML, etc. (ISP / DIP). |
| **Fuzzy-Match Diagnostics** | Calculates `difflib.SequenceMatcher` similarity when `target_content` is not found, providing actionable line suggestions. |

---

## 4. Architecture & Interface Specifications

### 4.1. Generic Atomic File Writer Interface (`core/interfaces/file_writer.py`)

```python
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

@runtime_checkable
class IAtomicFileWriter(Protocol):
    """Protocol interface for atomic file operations across all file types."""

    def write_text(self, path: Path, content: str, *, temp_name: str = ".tmp") -> None:
        """Atomically write text content to path via temp file replacement."""
        ...

    def write_json(self, path: Path, payload: dict[str, Any], *, temp_name: str = ".tmp") -> None:
        """Atomically write JSON payload to path via temp file replacement."""
        ...
```

### 4.2. Concrete Atomic File Writer (`utils/atomic_file_writer.py`)

```python
class AtomicFileWriter:
    """Concrete implementation of IAtomicFileWriter with Windows permission retry logic."""

    def write_text(self, path: Path, content: str, *, temp_name: str = ".tmp") -> None:
        ...

    def write_json(self, path: Path, payload: dict[str, Any], *, temp_name: str = ".tmp") -> None:
        ...
```

### 4.3. Refactored Pydantic Input Models (`tools/safe_edit_tool.py`)

```python
from typing import Annotated, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, model_validator

class ReplaceOp(BaseModel):
    """Replace target_content with replacement."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["replace"] = "replace"
    target_content: str = Field(description="Exact string sequence to find and replace")
    replacement: str = Field(description="Replacement content")
    search_window: list[int] | None = Field(
        default=None,
        description="Optional 1-based line window [start_line, end_line] to scope search",
    )

class AppendOp(BaseModel):
    """Append content to file end (EOF) or relative to text anchor."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["append"] = "append"
    content: str = Field(description="Content to append or insert")
    anchor: str | None = Field(
        default=None,
        description="Optional target anchor string. If None, appends to EOF.",
    )
    position: Literal["after", "before"] = Field(
        default="after",
        description="Insertion position relative to anchor",
    )

class RewriteOp(BaseModel):
    """Replace entire file content (file must already exist)."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["rewrite"] = "rewrite"
    content: str = Field(description="New complete file content")

class PatternReplaceOp(BaseModel):
    """Regex pattern replacement."""

    model_config = ConfigDict(extra="forbid")

    op: Literal["pattern_replace"] = "pattern_replace"
    pattern: str = Field(description="Regex pattern to search")
    replacement: str = Field(description="Replacement string")
    regex: bool = Field(default=True, description="Treat pattern as regular expression")

OperationType = Annotated[
    Union[ReplaceOp, AppendOp, RewriteOp, PatternReplaceOp],
    Field(discriminator="op"),
]

class SafeEditInput(BaseModel):
    """Input parameters for safe_edit_file."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Path to target file (must exist)")
    operation: OperationType = Field(description="Edit operation to perform")
    mode: Literal["strict", "interactive", "verify_only"] = Field(
        default="strict",
        description="Validation mode",
    )
```

### 4.4. Refactored `SafeEditTool` (`tools/safe_edit_tool.py`)

```python
class SafeEditTool(ICoreTool[SafeEditInput, SafeEditOutput]):
    """Tool to perform safe, validated edits on existing files."""

    def __init__(
        self,
        validator: ValidationService | None = None,
        file_writer: IAtomicFileWriter | None = None,
    ) -> None:
        ...

    async def execute(self, params: SafeEditInput, context: NoteContext) -> SafeEditOutput:
        ...

    def _generate_new_content(self, original_text: str, operation: OperationType) -> str:
        """Pure query transformation of content without side effects."""
        ...

    def _find_fuzzy_matches(self, original_text: str, target_content: str) -> str | None:
        """Calculate difflib similarity ratio to suggest nearest line match on typo."""
        ...

    def _validate(self, path: Path, content: str, mode: str) -> tuple[bool, str]:
        """Delegate AST/template syntax checking to ValidationService."""
        ...
```

---

## 5. Test & Validation Strategy

### 5.1. Unit Test Requirements (`tests/mcp_server/unit/tools/test_safe_edit_tool.py`)
- Test `replace` operation: exact string replacement, out-of-window failure, fuzzy-match suggestion on typo.
- Test `append` operation: EOF append (`anchor=None`), anchor relative append (`position="after"`), anchor relative insert (`position="before"`), missing anchor error.
- Test `rewrite` operation: complete file rewrite on existing file.
- Test `pattern_replace` operation: regex matching and substitution.
- Test governance enforcement: non-existent file path rejected with `must_exist=True` governance error.
- Test `extra="forbid"`: extra parameters rejected on `SafeEditInput` and sub-models.

### 5.2. Integration Test Requirements (`tests/mcp_server/integration/mcp_server/validation/`)
- Test full tool execution with `ValidationService` in `strict`, `interactive`, and `verify_only` modes.
- Test atomic file writing via `IAtomicFileWriter` and mutex locking.

---

## Related Documentation
- [Research Document](file:///c:/temp/pgmcp/docs/development/issue433/research.md)
- [Architecture Principles](file:///c:/temp/pgmcp/docs/coding_standards/ARCHITECTURE_PRINCIPLES.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-07-21 | @imp | Complete evidence-backed design specification for Issue #433 |

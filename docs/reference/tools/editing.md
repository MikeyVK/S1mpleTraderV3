<!-- docs/reference/tools/editing.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-07-21 -->
# File Editing Tools

**Status:** DEFINITIVE  
**Version:** 4.1  
**Last Updated:** 2026-08-22  

**Source:** [mcp_server/tools/safe_edit_tool.py](../../../mcp_server/tools/safe_edit_tool.py)  
**Tests:** [tests/mcp_server/unit/tools/test_safe_edit_tool.py](../../../tests/mcp_server/unit/tools/test_safe_edit_tool.py)  

---

## Purpose

Reference documentation for file editing tools in the MCP server. The `safe_edit_file` tool is the **primary file editing mechanism** for all existing code and documentation changes, providing frictionless string-anchored editing with quality gate integration, strict file existence governance (`must_exist=True`), concurrent edit protection, and validation enforcement.

---

## Overview

The MCP server provides one file editing tool:

| Tool | Status | Purpose | Use Case |
|------|--------|---------|----------|
| `safe_edit_file` | **PRIMARY** | Frictionless 4-operation file editing with validation | Editing existing files (`replace`, `append`, `rewrite`, `pattern_replace`) |

`safe_edit_file` offers:
- **4 string/symbol-anchored operations** (`replace`, `append`, `rewrite`, `pattern_replace`) via Pydantic discriminated union (`Field(discriminator="op")`)
- **Strict file existence governance** (`must_exist=True`): `safe_edit_file` edits existing files only; new file creation is governed by `scaffold_artifact`
- **Fuzzy-match typo diagnostics**: Suggests close matching lines via `difflib.get_close_matches` when targets or anchors are not found
- **3 validation modes** (`strict`, `interactive`, `verify_only`)
- **Quality gate integration** via `ValidationService` (Python, Markdown, and Jinja2 Template validation)
- **Concurrent edit protection** with file-level `asyncio.Lock` (10ms timeout)
- **Atomic file writes** via `IAtomicFileWriter` and `AtomicFileWriter` temp-swap logic

---

## API Reference

### safe_edit_file

**MCP Name:** `safe_edit_file`  
**Class:** `SafeEditTool`  
**File:** [mcp_server/tools/safe_edit_tool.py](../../../mcp_server/tools/safe_edit_tool.py)

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | `str` | **Yes** | Absolute path to the existing file (`must_exist=True`) |
| `operation` | `OperationType` | **Yes** | Discriminated union of edit operations (`replace`, `append`, `rewrite`, `pattern_replace`) |
| `mode` | `str` | No | Validation mode: `"strict"`, `"interactive"`, `"verify_only"` — default: `"strict"` |

#### Presented and Cached Output

The bounded response reports path, mode, validation pass status, whether a write
occurred, and whether a diff is available. It renders at most ten canonical
`ValidationIssue` records with severity, message, line, column, and code.

`SafeEditOutput` preserves the same immutable validation records produced by
`ValidationService`; the tool does not collapse, parse, copy, or remap them into a
presentation-specific DTO. The complete diff remains cache-only.

---

### Four Edit Operations

#### 1. Replace Operation (`replace`)

**Purpose:** String-anchored find and replace without line number calculations.  
**Parameters:**
- `op`: `"replace"`
- `target_content` (`str`): Exact string sequence to find and replace.
- `replacement` (`str`): Replacement content.
- `search_window` (`list[int] | None`): Optional 1-based line window `[start_line, end_line]` to scope search.

**Example:**
```json
{
  "path": "/workspace/backend/services/user_service.py",
  "operation": {
    "op": "replace",
    "target_content": "def old_method(self) -> None:",
    "replacement": "def new_method(self) -> None:"
  },
  "mode": "strict"
}
```

---

#### 2. Append Operation (`append`)

**Purpose:** Append content to file end (EOF) or relative to a text anchor string.  
**Parameters:**
- `op`: `"append"`
- `content` (`str`): Content to append or insert.
- `anchor` (`str | None`): Target anchor string. If `None`, appends to EOF.
- `position` (`"after" | "before"`): Insertion position relative to anchor (default: `"after"`).

**Example (Anchored Append):**
```json
{
  "path": "/workspace/docs/README.md",
  "operation": {
    "op": "append",
    "anchor": "## Features",
    "position": "after",
    "content": "- New feature description\n"
  }
}
```

**Example (EOF Append):**
```json
{
  "path": "/workspace/docs/README.md",
  "operation": {
    "op": "append",
    "content": "<!-- End of document -->\n"
  }
}
```

---

#### 3. Rewrite Operation (`rewrite`)

**Purpose:** Replace complete file content for an existing file.  
**Parameters:**
- `op`: `"rewrite"`
- `content` (`str`): New complete file content.

**Example:**
```json
{
  "path": "/workspace/config/settings.json",
  "operation": {
    "op": "rewrite",
    "content": "{\n  \"env\": \"production\"\n}\n"
  }
}
```

---

#### 4. Pattern Replace Operation (`pattern_replace`)

**Purpose:** Regex pattern replacement across the file.  
**Parameters:**
- `op`: `"pattern_replace"`
- `pattern` (`str`): Regex pattern to search.
- `replacement` (`str`): Replacement string.
- `regex` (`bool`): Treat pattern as regular expression (default: `True`).

**Example:**
```json
{
  "path": "/workspace/backend/models.py",
  "operation": {
    "op": "pattern_replace",
    "pattern": "\"frozen\": False",
    "replacement": "\"frozen\": True"
  }
}
```

---

## Governance & Error Diagnostics

1. **`must_exist=True` Enforcement**:
   - `safe_edit_file` strictly requires target file existence.
   - If the target file does not exist, `safe_edit_file` returns a governance error instructing the caller to use `scaffold_artifact` instead.

2. **Fuzzy-Match Typo Suggestions**:
   - If `target_content` (in `replace`) or `anchor` (in `append`) is not found, `safe_edit_file` analyzes original file text using `difflib.get_close_matches` and returns actionable line suggestions:
   ```text
   ❌ File edit rejected: Pattern 'def process_item():' not found in file

   Did you mean one of these lines?
     - 'def process_items():'
   ```

---

## Resource Guidance

Use the inline validation-issue list for immediate correction. Read the cached
`SafeEditOutput` when the complete issue sequence or generated diff is required. Do not
parse the Markdown response back into validation records.

## Related Documentation

- [MCP tools navigation](README.md)
- [Presentation architecture](../presentation_architecture.md)
- [Architecture principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 4.1 | 2026-08-22 | Agent | Document canonical structured validation issues and cache-only diffs |
| 4.0 | 2026-07-21 | Agent | Document governed safe editing operations and validation modes |

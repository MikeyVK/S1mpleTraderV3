<!-- docs/reference/mcp/tools/editing.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-02-08 -->
# File Editing Tools

**Status:** DEFINITIVE  
**Version:** 2.0  
**Last Updated:** 2026-02-08  

**Source:** [mcp_server/tools/safe_edit_tool.py](../../../../mcp_server/tools/safe_edit_tool.py)  
**Tests:** [tests/unit/test_safe_edit_tool.py](../../../../tests/unit/test_safe_edit_tool.py)  

---

## Purpose

Reference documentation for file editing tools in the MCP server. The `safe_edit_file` tool is the **primary file editing mechanism** for all code and documentation changes, providing multi-mode editing with quality gate integration, concurrent edit protection, and validation enforcement.

The deprecated `create_file` tool is documented for legacy awareness only. All new code should use `safe_edit_file` with `content` mode for file creation.

---

## Overview

The MCP server provides two file editing tools:

| Tool | Status | Purpose | Use Case |
|------|--------|---------|----------|
| `safe_edit_file` | **PRIMARY** | Multi-mode editing with validation | All file edits (create, line edits, insert, search/replace) |
| `create_file` | **DEPRECATED** | Simple file creation | Legacy only — use `safe_edit_file` instead |

`safe_edit_file` is a 552-line tool offering:
- **4 mutually exclusive edit modes** (full rewrite, line edits, insert, search/replace)
- **3 validation modes** (strict, interactive, verify-only)
- **Quality gate integration** via `ValidationService` (Ruff, Pyright, markdown validation)
- **Concurrent edit protection** with file-level `asyncio.Lock` (10ms timeout)
- **Diff preview** via `difflib.unified_diff`

---

## API Reference

### safe_edit_file

**MCP Name:** `safe_edit_file`  
**Class:** `SafeEditTool`  
**File:** [mcp_server/tools/safe_edit_tool.py](../../../../mcp_server/tools/safe_edit_tool.py)

Multi-mode file editing with automatic validation and concurrent edit protection.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | `str` | **Yes** | Absolute path to the file |
| `content` | `str` | **Conditional** | Full file content (full rewrite mode) — creates file if not exists |
| `line_edits` | `list[LineEdit]` | **Conditional** | List of line-based edits (chirurgical mode) — file must exist |
| `insert_lines` | `list[InsertLine]` | **Conditional** | List of line insert operations — file must exist |
| `search` | `str` | **Conditional** | Pattern to search for (search/replace mode) — requires `replace` |
| `replace` | `str` | **Conditional** | Replacement text (search/replace mode) — requires `search` |
| `regex` | `bool` | No | Use regex pattern matching (search/replace mode) — default: `False` |
| `search_count` | `int` | No | Maximum replacements (search/replace mode) — default: `None` (all matches) |
| `search_flags` | `int` | No | Regex flags e.g. `re.IGNORECASE` (search/replace mode) — default: `0` |
| `mode` | `str` | No | Validation mode: `"strict"`, `"interactive"`, `"verify_only"` — default: `"strict"` |
| `show_diff` | `bool` | No | Show unified diff preview — default: `True` |

**⚠️ CRITICAL:** Exactly **ONE** of these parameter groups is required (enforced by Pydantic validator):
1. `content` — full rewrite mode
2. `line_edits` — chirurgical edit mode
3. `insert_lines` — insert mode
4. `search` + `replace` — search/replace mode

#### LineEdit Sub-model

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `start_line` | `int` | ≥1 | Starting line (1-based, inclusive) |
| `end_line` | `int` | ≥`start_line` | Ending line (1-based, inclusive) |
| `new_content` | `str` | — | Replacement text — **MUST include trailing `\n`** for multi-line content |

**Example:**
```json
{
  "start_line": 10,
  "end_line": 12,
  "new_content": "def new_function():\n    return 42\n"
}
```

#### InsertLine Sub-model

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `at_line` | `int` | ≥1 | Insert **before** this line (use `file_line_count + 1` to append at end) |
| `content` | `str` | — | Content to insert (can be multi-line) |

**Example:**
```json
{
  "at_line": 5,
  "content": "# New comment\n"
}
```

#### Returns

```json
{
  "success": true,
  "message": "File written successfully",
  "diff": "--- original\n+++ modified\n@@ -10,3 +10,3 @@\n-old line\n+new line\n",
  "validation_warnings": []
}
```

Or on error:

```json
{
  "success": false,
  "message": "Validation failed: pylint errors detected",
  "errors": ["line 42: E0602 undefined-variable"],
  "validation_warnings": ["line 10: W0612 unused-variable"]
}
```

---

### Four Edit Modes

#### Mode 1: Full Rewrite (`content`)

**Purpose:** Create new files or completely replace existing file content.  
**Parameters:** `content` (string)  
**File Existence:** Creates file if not exists  
**Use Cases:**
- Creating new files
- Complete file rewrites
- Migrating from `create_file` (deprecated)

**Example:**
```json
{
  "path": "/workspace/backend/dtos/my_feature.py",
  "content": "from dataclasses import dataclass\n\n@dataclass\nclass MyFeature:\n    value: int\n",
  "mode": "strict"
}
```

**Behavior:**
- Writes `content` to file (replaces entire content)
- Creates parent directories if needed
- Validates after write (respects `mode` parameter)
- Shows diff comparing old content to new content

---

#### Mode 2: Line Edits (`line_edits`)

**Purpose:** Surgical edits to specific line ranges (most efficient for targeted changes).  
**Parameters:** `line_edits` (list of `LineEdit`)  
**File Existence:** File MUST exist  
**Use Cases:**
- Updating specific functions/methods
- Fixing specific lines
- Modifying class definitions

**Example:**
```json
{
  "path": "/workspace/backend/dtos/user.py",
  "line_edits": [
    {
      "start_line": 10,
      "end_line": 12,
      "new_content": "    def updated_method(self) -> str:\n        return \"updated\"\n"
    }
  ],
  "mode": "strict"
}
```

**⚠️ CRITICAL ANTI-PATTERN:** Multiple sequential `safe_edit_file` calls on the same file will trigger mutex timeout. Bundle ALL edits for the same file in ONE call:

```json
{
  "path": "/workspace/myfile.py",
  "line_edits": [
    {"start_line": 5, "end_line": 5, "new_content": "# Edit 1\n"},
    {"start_line": 20, "end_line": 22, "new_content": "# Edit 2\ncode\n"},
    {"start_line": 50, "end_line": 50, "new_content": "# Edit 3\n"}
  ]
}
```

**Behavior:**
- Edits applied in **reverse order** (by `start_line`) to preserve line numbers
- Validates line ranges don't overlap
- Validates line numbers are within file bounds
- **Trailing `\n` required** for multi-line `new_content` (or next line merges)

---

#### Mode 3: Insert Lines (`insert_lines`)

**Purpose:** Insert content without replacing existing lines.  
**Parameters:** `insert_lines` (list of `InsertLine`)  
**File Existence:** File MUST exist  
**Use Cases:**
- Adding new imports
- Inserting new methods in a class
- Appending to files

**Example:**
```json
{
  "path": "/workspace/backend/services/user_service.py",
  "insert_lines": [
    {
      "at_line": 1,
      "content": "from typing import Optional\n"
    },
    {
      "at_line": 50,
      "content": "\n    def new_method(self):\n        pass\n"
    }
  ],
  "mode": "strict"
}
```

**Behavior:**
- Inserts BEFORE the specified line
- To append at end: use `at_line = file_line_count + 1`
- Multiple inserts processed in order
- Does not replace existing lines

---

#### Mode 4: Search/Replace (`search` + `replace`)

**Purpose:** Pattern-based find and replace operations.  
**Parameters:** `search`, `replace`, optional: `regex`, `search_count`, `search_flags`  
**File Existence:** File MUST exist  
**Use Cases:**
- Renaming variables/functions
- Updating imports
- Bulk text replacements

**Example (literal string):**
```json
{
  "path": "/workspace/backend/workers/my_worker.py",
  "search": "old_function_name",
  "replace": "new_function_name",
  "mode": "strict"
}
```

**Example (regex):**
```json
{
  "path": "/workspace/backend/config/settings.py",
  "search": "VERSION = ['\"]\\d+\\.\\d+\\.\\d+['\"]",
  "replace": "VERSION = \"2.0.0\"",
  "regex": true,
  "mode": "strict"
}
```

**Behavior:**
- `regex=False` (default): Literal string match
- `regex=True`: Python `re` module patterns
- `search_count`: Limits number of replacements (default: all matches)
- `search_flags`: Pass `re` flags (e.g., `re.IGNORECASE = 2`)
- **In strict mode:** Pattern not found returns error

---

### Three Validation Modes

| Mode | Write? | Validate? | Fail on Error? | Use Case |
|------|--------|-----------|----------------|----------|
| **`strict`** (default) | Only if valid | Yes | **Yes** | Normal editing — rejects invalid changes |
| **`interactive`** | Always | Yes (warns) | **No** | Manual override — writes regardless, logs warnings |
| **`verify_only`** | Never | Yes | N/A | Dry-run — preview diff without writing |

#### `strict` Mode (Default)

**Behavior:**
1. Read original file (if exists)
2. Apply edits (in-memory)
3. Run validation via `ValidationService`
4. **If validation passes:** Write file, return success + diff
5. **If validation fails:** Do NOT write, return error with validation messages

**Use Case:** Standard editing where you want to ensure code quality before writing.

**Example:**
```json
{
  "path": "/workspace/backend/dtos/user.py",
  "content": "invalid python syntax {",
  "mode": "strict"
}
```

**Result:**
```json
{
  "success": false,
  "message": "Validation failed",
  "errors": ["line 1: E0001 Parsing failed: invalid syntax"]
}
```

---

#### `interactive` Mode

**Behavior:**
1. Read original file (if exists)
2. Apply edits (in-memory)
3. Run validation via `ValidationService`
4. **Always write file** (regardless of validation result)
5. Return success with validation warnings (if any)

**Use Case:** Emergency fixes, bypassing quality gates, or when validation is too strict.

**Example:**
```json
{
  "path": "/workspace/backend/dtos/user.py",
  "content": "# TODO: incomplete implementation\nclass User:\n    pass\n",
  "mode": "interactive"
}
```

**Result:**
```json
{
  "success": true,
  "message": "File written (validation warnings present)",
  "validation_warnings": ["line 2: R0903 too-few-public-methods"]
}
```

---

#### `verify_only` Mode

**Behavior:**
1. Read original file (if exists)
2. Apply edits (in-memory)
3. Run validation via `ValidationService`
4. **Do NOT write file**
5. Return diff + validation results

**Use Case:** Preview changes before committing to write, CI/CD dry-run checks.

**Example:**
```json
{
  "path": "/workspace/backend/services/order_service.py",
  "search": "old_api_call",
  "replace": "new_api_call",
  "mode": "verify_only"
}
```

**Result:**
```json
{
  "success": true,
  "message": "Validation passed (no changes written)",
  "diff": "--- original\n+++ modified\n@@ -42,1 +42,1 @@\n-    old_api_call()\n+    new_api_call()\n"
}
```

---

### Concurrent Edit Protection

**Problem:** Multiple agents/tools editing the same file simultaneously causes race conditions.

**Solution:** File-level `asyncio.Lock` with immediate timeout.

#### Implementation Details

- **Lock scope:** Per resolved absolute file path
- **Timeout:** 10ms (immediate failure if lock held)
- **Lock pool:** `Dict[str, asyncio.Lock]` in `SafeEditTool` class
- **Error message:** `"Another edit operation is in progress for this file"`

#### Anti-Pattern: Sequential Edits

**❌ WRONG (triggers mutex timeout):**
```python
# Edit 1
safe_edit_file(path="file.py", line_edits=[{"start_line": 5, ...}])

# Edit 2 (will fail if Edit 1 still in progress)
safe_edit_file(path="file.py", line_edits=[{"start_line": 20, ...}])
```

**✅ CORRECT (bundle in one call):**
```python
safe_edit_file(
    path="file.py",
    line_edits=[
        {"start_line": 5, "end_line": 5, "new_content": "...\n"},
        {"start_line": 20, "end_line": 22, "new_content": "...\n"}
    ]
)
```

---

### Quality Gate Integration

`safe_edit_file` delegates validation to `ValidationService` which selects validators by file extension and content:

| File Type | Validator | Checks |
|-----------|-----------|--------|
| `*.py` | `PythonValidator` | pylint, mypy/pyright (if installed), syntax errors |
| `*.md` | `MarkdownValidator` | Structure, SCAFFOLD header format, frontmatter |
| Files with SCAFFOLD headers | `TemplateValidator` | Template conformance, required sections |

#### Python Validation Example

```python
# ValidationService detects .py extension
# Runs PythonValidator:
#   1. Syntax check (compile with ast.parse)
#   2. Pylint static analysis
#   3. Mypy/Pyright type checking (if available)
```

**Validation result** includes:
- Errors (blocking in strict mode)
- Warnings (non-blocking)
- Line numbers and error codes

---

## Common Anti-Patterns & Mistakes

### 1. Missing Trailing `\n` in `line_edits`

**Problem:** Next line merges into edited line.

**❌ WRONG:**
```json
{"start_line": 10, "end_line": 10, "new_content": "new line"}
```

**✅ CORRECT:**
```json
{"start_line": 10, "end_line": 10, "new_content": "new line\n"}
```

---

### 2. Multiple Sequential Edits on Same File

**Problem:** Mutex timeout / race condition.

**❌ WRONG:**
```python
safe_edit_file(path="file.py", line_edits=[edit1])
safe_edit_file(path="file.py", line_edits=[edit2])  # Timeout!
```

**✅ CORRECT:**
```python
safe_edit_file(path="file.py", line_edits=[edit1, edit2])
```

---

### 3. Line Edits on Non-Existent Files

**Problem:** File must exist for `line_edits` mode.

**❌ WRONG:**
```json
{"path": "/new_file.py", "line_edits": [...]}
```

**✅ CORRECT:**
```json
{"path": "/new_file.py", "content": "initial content\n"}
```

---

### 4. Overlapping Line Ranges

**Problem:** Validator rejects overlapping edits.

**❌ WRONG:**
```json
[
  {"start_line": 10, "end_line": 15, "new_content": "..."},
  {"start_line": 12, "end_line": 20, "new_content": "..."}  // Overlap!
]
```

**✅ CORRECT:**
```json
[
  {"start_line": 10, "end_line": 15, "new_content": "..."},
  {"start_line": 16, "end_line": 20, "new_content": "..."}
]
```

---

### 5. Multiple Edit Modes Simultaneously

**Problem:** Model validator rejects multiple modes.

**❌ WRONG:**
```json
{
  "path": "file.py",
  "content": "...",
  "line_edits": [...]  // Error: multiple modes
}
```

**✅ CORRECT:**
```json
{"path": "file.py", "content": "..."}
```

---

## create_file (DEPRECATED)

**MCP Name:** `create_file`  
**Class:** `CreateFileTool`  
**File:** [mcp_server/tools/code_tools.py](../../../../mcp_server/tools/code_tools.py)  
**Status:** **DEPRECATED** — Use `safe_edit_file` with `content` mode instead

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | `str` | Yes | Relative path to file |
| `content` | `str` | Yes | File content |

### Deprecation Notice

`create_file` is a legacy tool superseded by `safe_edit_file`. It lacks:
- Quality gate integration
- Validation modes
- Diff preview
- Concurrent edit protection

**Migration:**
```json
// OLD (create_file)
{"path": "backend/dtos/user.py", "content": "..."}

// NEW (safe_edit_file)
{"path": "/workspace/backend/dtos/user.py", "content": "...", "mode": "strict"}
```

---

## Configuration

No environment variables or configuration files required. Quality gate behavior is configured via [.st3/quality.yaml](../../../../.st3/quality.yaml):

```yaml
quality_gates:
  python:
    - tool: pylint
      enabled: true
    - tool: mypy
      enabled: true
```

---

## Related Documentation

- [README.md](README.md) — MCP Tools navigation index
- [quality.md](quality.md) — Quality gate tools and validation
- [scaffolding.md](scaffolding.md) — Template-based artifact generation
- [docs/reference/mcp/validation_api.md](../validation_api.md) — ValidationService API
- [docs/development/issue19/research.md](../../../development/issue19/research.md) — Tool inventory research (Section 2: SafeEditTool Deep-Dive)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-02-08 | Agent | Complete safe_edit_file deep-dive: 4 edit modes, 3 validation modes, anti-patterns, concurrent edit protection |

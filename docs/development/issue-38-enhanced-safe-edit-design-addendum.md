# Issue #38: Enhanced SafeEditTool - Design Phase Addendum

**Status:** DRAFT  
**Author:** AI Agent  
**Date:** 2025-12-23  
**Phase Transition:** planning → design

## Purpose

This addendum addresses design-specific artifacts not covered in planning phase, following Issue #41 guidance for clear phase boundaries.

**Design Phase Focus:**
- Exact class structure with typed method signatures
- State machine visualization
- Component interaction diagram
- Type safety specifications

---

## Class Structure

### SafeEditTool (Enhanced)

```python
from pathlib import Path
from typing import Any
from pydantic import BaseModel
from mcp_server.tools.base import BaseTool, ToolResult
from mcp_server.validation.registry import ValidatorRegistry

class SafeEditTool(BaseTool):
    """Tool for safely editing files with multiple edit modes."""
    
    name: str = "safe_edit_file"
    description: str = "Write content to a file with automatic validation. Supports 'strict' mode (rejects on error) or 'interactive' (warns)."
    args_model: type[BaseModel] = SafeEditInput
    
    def __init__(self) -> None:
        """Initialize and register default validators."""
        super().__init__()
        # Register validators (unchanged from current implementation)
    
    @property
    def input_schema(self) -> dict[str, Any]:
        """Get JSON schema for input parameters."""
        return self.args_model.model_json_schema()
    
    async def execute(self, params: SafeEditInput) -> ToolResult:
        """Execute safe edit with mode selection.
        
        Args:
            params: Validated SafeEditInput with one edit mode
            
        Returns:
            ToolResult with diff preview and status message
            
        Note:
            All errors returned as ToolResult, never raises exceptions
        """
        ...
    
    def _apply_line_edits(
        self,
        original_content: str,
        line_edits: list[LineEdit]
    ) -> str:
        """Apply line-based edits to original content.
        
        Args:
            original_content: Original file content (line endings preserved)
            line_edits: List of LineEdit objects (already validated)
            
        Returns:
            Modified content with all edits applied
            
        Raises:
            ValueError: Line range overlaps or exceeds file bounds
        """
        ...
    
    def _apply_search_replace(
        self,
        original_content: str,
        search_replace: SearchReplace
    ) -> tuple[str, int]:
        """Apply search and replace to content.
        
        Args:
            original_content: Original file content
            search_replace: SearchReplace configuration (validated)
            
        Returns:
            Tuple of (modified_content, replacement_count)
            
        Raises:
            ValueError: Invalid regex pattern
        """
        ...
    
    def _generate_diff(
        self,
        path: str,
        original_content: str,
        new_content: str
    ) -> str:
        """Generate unified diff between original and new content.
        
        Args:
            path: File path (for diff header)
            original_content: Original file content
            new_content: Modified file content
            
        Returns:
            Unified diff string (empty if no changes)
        """
        ...
    
    async def _validate(
        self,
        path: str,
        content: str
    ) -> tuple[bool, str]:
        """Run validators on content (UNCHANGED from current).
        
        Args:
            path: File path (determines validators)
            content: Full file content to validate
            
        Returns:
            Tuple of (passed: bool, issues_text: str)
        """
        ...
```

---

## Type Aliases

```python
from typing import TypeAlias

# Edit results
EditContent: TypeAlias = str
ReplacementCount: TypeAlias = int
EditResult: TypeAlias = tuple[EditContent, ReplacementCount]

# Validation results
ValidationPassed: TypeAlias = bool
ValidationIssues: TypeAlias = str
ValidationResult: TypeAlias = tuple[ValidationPassed, ValidationIssues]

# Diff output
DiffText: TypeAlias = str
```

---

## State Machine: Edit Mode Selection

```
┌─────────────────────────────────────────────────────────────────┐
│                     INPUT VALIDATION                            │
│              (Pydantic validates SafeEditInput)                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
                       ▼
           ┌───────────────────────┐
           │   Read Original File  │
           └───┬───────────┬───────┘
               │           │
     FileNotFound│         │Success
               │           │
               ▼           ▼
       ┌─────────┐   ┌──────────────┐
       │New File │   │File Content  │
       │Empty    │   │Loaded        │
       └────┬────┘   └──────┬───────┘
            │               │
            └───────┬───────┘
                    │
                    ▼
        ┌────────────────────────┐
        │  SELECT EDIT MODE      │
        │  (if/elif/elif)        │
        └──┬──────────┬─────────┬┘
           │          │         │
  content  │  line    │  search_replace
  != None  │  _edits  │  != None
           │  != None │
           ▼          ▼         ▼
    ┌──────────┐ ┌────────┐ ┌────────────┐
    │Content   │ │Line    │ │Search/     │
    │Mode      │ │Edit    │ │Replace     │
    │          │ │Mode    │ │Mode        │
    └────┬─────┘ └───┬────┘ └─────┬──────┘
         │           │             │
         │      Apply│Edit    Apply│Replace
         │           │             │
         │           ▼             ▼
         │      ┌────────┐   ┌──────────┐
         │      │Validate│   │Check     │
         │      │Bounds  │   │Regex     │
         │      │Overlaps│   │Valid     │
         │      └───┬────┘   └────┬─────┘
         │          │             │
         │      Success│       Success│
         │          │             │
         │          │         ┌───▼─────┐
         │          │         │Count    │
         │          │         │Matches  │
         │          │         └────┬────┘
         │          │              │
         │          │          0 matches?
         │          │          │       │
         │          │      Yes │   No  │
         │          │          ▼       │
         │          │     ┌────────┐   │
         │          │     │Handle  │   │
         │          │     │Zero    │   │
         │          │     │Matches │   │
         │          │     └───┬────┘   │
         │          │         │        │
         └──────────┴─────────┴────────┘
                    │
                    ▼
         ┌──────────────────┐
         │ Generate Diff    │
         │ (if show_diff)   │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ Validate Content │
         │ (ValidatorReg)   │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │   Handle Mode    │
         │  verify_only     │
         │  strict          │
         │  interactive     │
         └────┬──────┬──────┘
              │      │
         verify│     │write
              │      │
              ▼      ▼
         ┌────────┐ ┌────────┐
         │Return  │ │Write   │
         │Result  │ │File    │
         └────────┘ └───┬────┘
                        │
                        ▼
                   ┌────────┐
                   │Return  │
                   │Result  │
                   └────────┘
```

---

## Component Interaction Diagram

```
┌────────────────────────────────────────────────────────┐
│                    MCP Client                          │
└──────────────────────┬─────────────────────────────────┘
                       │
                       │ SafeEditInput (JSON)
                       ▼
┌──────────────────────────────────────────────────────────┐
│                   SafeEditTool                           │
│  ┌────────────────────────────────────────────────────┐  │
│  │  execute(params: SafeEditInput) → ToolResult       │  │
│  │                                                    │  │
│  │  1. Read file → original_content                  │  │
│  │  2. Select mode → apply edits                     │  │
│  │  3. Generate diff (difflib)                       │  │
│  │  4. Validate → _validate()                        │  │
│  │  5. Handle mode → verify/strict/interactive       │  │
│  │  6. Write file or return error                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Private Methods:                                        │
│  ┌──────────────────────────────────────────────────┐   │
│  │ _apply_line_edits()                              │   │
│  │   • Validate bounds                              │   │
│  │   • Check overlaps                               │   │
│  │   • Apply in reverse order                       │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ _apply_search_replace()                          │   │
│  │   • Compile regex if needed                      │   │
│  │   • Apply with count limit                       │   │
│  │   • Return (content, count)                      │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ _generate_diff()                                 │   │
│  │   • difflib.unified_diff                         │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ _validate()                                      │   │
│  │   • Get validators from registry                 │   │
│  │   • Run each validator                           │   │
│  │   • Aggregate results                            │   │
│  └──────────────────┬───────────────────────────────┘   │
└─────────────────────┼───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│           ValidatorRegistry (UNCHANGED)                 │
│  • get_validators(path) → list[Validator]               │
│  • Extension matching (.py, .md)                        │
│  • Pattern matching (*_worker.py, etc.)                 │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│        Validators (PythonValidator, etc.)               │
│  • validate(path, content) → ValidationResult           │
│  • Write temp files                                     │
│  • Run external tools (pylint/mypy/pyright)             │
└─────────────────────────────────────────────────────────┘
```

---

## Error Handling Decision Tree

```
execute(params)
├─ Pydantic Validation
│  ├─ Success → Continue
│  └─ Failure → ValidationError (raised before execute())
│
├─ Read File
│  ├─ Success → original_content
│  ├─ FileNotFoundError → original_content = ""
│  └─ UnicodeDecodeError → ToolResult.error("Cannot edit binary file")
│
├─ Apply Edit Mode
│  ├─ Content Mode
│  │  └─ Success → new_content = params.content
│  │
│  ├─ Line Edit Mode
│  │  ├─ Bounds check failed → ToolResult.error("Line X exceeds file length")
│  │  ├─ Overlap detected → ToolResult.error("Overlapping edits")
│  │  └─ Success → new_content
│  │
│  └─ Search/Replace Mode
│      ├─ Invalid regex → ToolResult.error("Invalid regex pattern")
│      ├─ Zero matches
│      │  ├─ mode=strict → ToolResult.error("Pattern not found")
│      │  └─ mode=interactive → ToolResult.text("Warning: Pattern not found")
│      └─ Success → new_content, num_subs
│
├─ Generate Diff
│  ├─ No changes → diff = ""
│  └─ Changes → diff = unified_diff(...)
│
├─ Validate
│  └─ Returns (passed: bool, issues_text: str)
│
├─ Handle Mode
│  ├─ verify_only
│  │  └─ ToolResult.text(validation result + diff)
│  ├─ strict
│  │  ├─ !passed → ToolResult.text("Edit rejected" + issues + diff)
│  │  └─ passed → Write File
│  └─ interactive
│      └─ Write File (regardless of validation)
│
└─ Write File
   ├─ OSError → ToolResult.error("Failed to write file")
   └─ Success → ToolResult.text("File saved" + warnings + diff)
```

---

## Data Flow Example

**Input:**
```python
SafeEditInput(
    path="/workspace/file.py",
    mode="strict",
    show_diff=True,
    line_edits=[
        LineEdit(start_line=50, end_line=52, new_content="    return new_value\n")
    ]
)
```

**Processing Flow:**
1. Read `/workspace/file.py` → `original_content: str`
2. Apply line_edits[0] → replace lines 50-52 → `new_content: str`
3. Generate unified diff → `diff: str`
4. Validate new_content → `(passed=True, issues="")`
5. Mode check → strict + passed → write file
6. Write file → success

**Output:**
```python
ToolResult(
    content=[{
        "type": "text",
        "text": """**Diff Preview:**
```diff
--- a/file.py
+++ b/file.py
@@ -50,3 +50,1 @@
 def process():
-    old_line_1
-    old_line_2
-    old_line_3
+    return new_value
```

✅ File saved successfully."""
    }],
    is_error=False
)
```

---

## Type Safety Checklist

**For mypy/pyright compliance:**

- ✅ All method signatures have return type annotations
- ✅ All parameters have type hints
- ✅ Pydantic models use `Field()` with descriptions
- ✅ Optional types use `| None` (Python 3.10+ syntax)
- ✅ List types use `list[T]` (not `List[T]`)
- ✅ Tuple types use `tuple[T, U]` (not `Tuple[T, U]`)
- ✅ Literal types for enum-like fields (`mode: Literal[...]`)
- ✅ TypeAlias for complex return types
- ✅ No `Any` types except in `input_schema` dict return
- ✅ Async methods properly typed with `async def ... -> ToolResult`

---

## Design Phase Completion Criteria

- ✅ Class structure documented with all public/private methods
- ✅ Method signatures include exact parameter and return types
- ✅ State machine visualizes complete edit flow
- ✅ Component interaction shows data flow through system
- ✅ Error handling decision tree covers all execution paths
- ✅ Type safety checklist ensures mypy/pyright compliance
- ✅ Data flow example demonstrates end-to-end operation

**Status:** Ready for Component Phase - Implementation can begin without ambiguity

<!-- docs/development/issue121/research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-08T16:00:00Z updated=2026-02-08 -->
# Issue #121 Research: Content-Aware Editing with Segment Detection

**Status:** COMPLETE  
**Version:** 1.0  
**Last Updated:** 2026-02-08

---

## Purpose

Comprehensive research for implementing content-aware editing tool with segment-based operations, template awareness, and multi-file batching. Analyzes segment detection algorithms, API design choices, template integration with Issue #120, and provides implementation roadmap.

## Scope

**In Scope:**
- Markdown section detection (heading hierarchy, nesting)
- Python function/class detection via AST parsing
- Template block detection using Issue #120 introspection
- SegmentEdit API design (operations, error handling)
- Multi-file batching patterns
- Integration architecture with existing safe_edit_tool
- Implementation effort/risk per component

**Out of Scope:**
- Language servers (LSP) - different use case
- Character offset API (Position/Range) - feasibility analysis concluded: skip
- Code refactoring tools (rename, extract method) - future work
- AST-based code generation - out of scope

## Prerequisites

Read these first:
1. [Issue #120 Phase 0+1](../issue72/research.md) - Template introspection infrastructure (COMPLETE)
2. [Issue #54 evaluation](../issue54/safe_edit_evaluation.md) - Agent struggle patterns
3. [Issue #38 safe_edit_tool](../issue-38-enhanced-safe-edit-planning.md) - 4 modes implemented
4. [feasibility-analysis.md](feasibility-analysis.md) - VS Code comparison complete

---

## Problem Statement

Issue #54 documented critical agent struggles with current editing tools:
- **67% retry rate** due to pattern matching failures
- **33% catastrophic failure** requiring file re-scaffolding
- **0% self-recovery** without human intervention

Root causes:
1. **Exact text matching fragility** - whitespace/formatting sensitivity
2. **Line number brittleness** - edits break when content shifts
3. **No template awareness** - agents don't understand scaffolded file structure
4. **Single-file operations** - inefficient for batch edits

Issue #121 proposes segment-based editing to solve these problems. Research needed for:
1. Segment detection algorithms (markdown, Python, templates)
2. API design choices (SegmentEdit operations)
3. Template integration (Issue #120 introspection)
4. Implementation roadmap and complexity assessment

## Research Goals

- Analyze segment detection algorithms (markdown sections, Python AST, template blocks)
- Design SegmentEdit API and semantics
- Evaluate template awareness integration with Issue #120
- Assess multi-file batching patterns from VS Code
- Document implementation complexity per component
- Map research findings to Issue #121 acceptance criteria

---

## Issue #121 Deeltaken Analysis

### Context: Three Subtasks

Issue #121 bevat 3 deeltaken:
1. **Nieuwe editTool** - Combinatie safe_edit + segment-based edits
2. **VS Code API alignment** - Character offsets vs line numbers
3. **Segment-based edit modus** - Semantische edits op template-niveau

### Deeltaak 1: Nieuwe editTool (Unified API)

**Vraag:** Separate tool vs extending safe_edit_tool?

**Optie A: Extend safe_edit_tool**
```python
class SafeEditInput(BaseModel):
    # Existing modes
    content: str | None = None
    line_edits: list[LineEdit] | None = None
    insert_lines: list[InsertLine] | None = None
    search: str | None = None
    
    # NEW: 5th mode
    segment_edit: SegmentEdit | None = None
```

**Advantages:**
- ✅ No tool duplication
- ✅ Backward compatible
- ✅ Reuse validation/diff logic
- ✅ Single tool for agents to learn

**Disadvantages:**
- 🟡 Tool grows (5 modes vs 4)
- 🟡 Less explicit separation TextEdit vs SegmentEdit

**Optie B: New editFiles tool**
```python
class EditFilesInput(BaseModel):
    path: str
    edits: list[TextEdit | SegmentEdit]  # Union type
    mode: Literal["strict", "interactive"]
```

**Advantages:**
- ✅ Clean API (explicit edit types)
- ✅ Multi-file batching native
- ✅ Template awareness first-class

**Disadvantages:**
- ❌ Tool duplication (safe_edit + editFiles)
- ❌ Agent confusion over which tool
- ❌ More implementation/testing effort

**Research Conclusion:**
**Start with Optie A** (extend safe_edit_tool). If agent usage metrics show confusion after 2 weeks, migrate to Optie B. Rationale: faster delivery, less duplication, backward compatibility.

**Implementation:**
- Add `segment_edit: SegmentEdit | None` field
- Reuse `_apply_line_edits()` internally (segment → line conversion)
- Existing validation/diff infrastructure works unchanged

**Estimated Effort:** 1-2 days (mostly testing new mode)

### Deeltaak 2: VS Code API Alignment (Character Offsets)

**Context from Feasibility Analysis:**

VS Code native agent tools use:
- `replace_string_in_file(oldString, newString)` - exact text matching
- NO Position/Range API
- NO character offset calculation

**Finding:** Character offsets are NOT used in VS Code agent tooling.

**Original Issue #121 Hypothesis:**
```python
Position(line: int, character: int)  # 0-based
Range(start: Position, end: Position)
TextEdit(range: Range, newText: str)
```

**Analysis:**
1. **Agents think in natural language**, not character offsets
   - Agent says: "Change line 10"
   - Agent NEVER says: "Change characters 456-478"

2. **Current safe_edit modes sufficient:**
   - Line-based: Edit whole lines
   - Search/replace: Fine-grained pattern matching (with regex!)
   - No gap that character offsets would fill

3. **Complexity overhead:**
   - Character offset calculation
   - Line ending handling (\n vs \r\n)
   - UTF-8 multi-byte character support
   - No practical benefit for conversational AI

**Research Conclusion:**
**❌ SKIP Deeltaak 2** - Character offset API niet relevant voor agent workflows. Huidige line-based + search_replace modes hebben voldoende precisie.

**Rationale:**
- VS Code itself doesn't use this for agents
- Complexity zonder practical benefit
- Focus effort on segment-based editing (higher ROI)

### Deeltaak 3: Segment-Based Editing

**Definition:** Edit files by semantic structure instead of line numbers or exact text.

**Examples:**
```python
# Markdown
edit_section(path, section="Problem Statement", content="...")

# Python
edit_function(path, function="calculate_risk", content="...")

# Scaffolded files
edit_template_block(path, block="acceptance_criteria", content="...")
```

**Value Proposition:**

| Benefit | Description | Impact |
|---------|-------------|--------|
| **Robustness** | No line number dependencies | High - survives file edits |
| **Natural language** | Agent thinks in concepts | High - aligns with AI reasoning |
| **Template awareness** | Understands scaffolding | High - leverages Issue #120 |
| **No preview needed** | Dynamic segment lookup | Medium - saves read_file call |
| **Eliminates fragility** | No exact text match | High - fixes Issue #54 problem |

**Research Conclusion:**
**✅ HIGH PRIORITY** - Implement Deeltaak 3. This is the core value proposition of Issue #121.

**Estimated Effort:** 5-8 days (detailed breakdown in Implementation section)

---

## Segment Detection Algorithms

### 1. Markdown Section Detection

**Challenge:** Parse heading hierarchy and determine section boundaries.

**Algorithm:**

```python
from typing import NamedTuple

class Section(NamedTuple):
    name: str
    level: int  # 1-6 (# to ######)
    start_line: int  # 1-based
    end_line: int    # 1-based (inclusive)
    parent: str | None  # Parent section name

def detect_markdown_sections(content: str) -> dict[str, Section]:
    """Parse markdown headings → section ranges.
    
    Returns:
        {"Problem Statement": Section(...), "Solution::Overview": Section(...)}
    """
    lines = content.split('\n')
    sections = []
    section_stack = []  # Track hierarchy
    
    for i, line in enumerate(lines, start=1):
        # Match heading: ## Title or ##Title
        match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
        if not match:
            continue
        
        level = len(match.group(1))
        title = match.group(2).strip()
        
        # Close previous sections at same/lower level
        while section_stack and section_stack[-1]['level'] >= level:
            prev = section_stack.pop()
            sections.append(Section(
                name=prev['name'],
                level=prev['level'],
                start_line=prev['start_line'],
                end_line=i - 1,  # Ends before current heading
                parent=prev['parent']
            ))
        
        # Start new section
        parent_name = section_stack[-1]['name'] if section_stack else None
        full_name = f"{parent_name}::{title}" if parent_name else title
        
        section_stack.append({
            'name': full_name,
            'level': level,
            'start_line': i,
            'parent': parent_name
        })
    
    # Close remaining sections (end at EOF)
    while section_stack:
        prev = section_stack.pop()
        sections.append(Section(
            name=prev['name'],
            level=prev['level'],
            start_line=prev['start_line'],
            end_line=len(lines),
            parent=prev['parent']
        ))
    
    return {s.name: s for s in sections}
```

**Edge Cases:**
- **Nested sections:** Use `Parent::Child` naming convention
- **Duplicate names:** Use hierarchical path (Issue → Plan → duplicate "Dependencies")
- **ATX vs Setext headings:** Support both `## Title` and `Title\n----`
- **Code blocks:** Ignore `#` inside triple backtick blocks

**Implementation Complexity:**
- **Effort:** 🟢 LOW (4-6 hours)
- **Risk:** 🟢 LOW (regex + line counting)
- **Tests:** Section boundaries, nesting, edge cases

### 2. Python Function/Class Detection

**Challenge:** Parse Python AST to locate function/class definitions.

**Algorithm:**

```python
import ast
from typing import NamedTuple

class PythonSegment(NamedTuple):
    name: str
    type: Literal["function", "class", "method"]
    start_line: int  # 1-based
    end_line: int    # 1-based (inclusive)
    parent: str | None  # Parent class for methods

def detect_python_segments(content: str) -> dict[str, PythonSegment]:
    """Parse Python AST → function/class ranges.
    
    Returns:
        {
            "MyClass": PythonSegment(type="class", ...),
            "MyClass.my_method": PythonSegment(type="method", ...),
            "standalone_function": PythonSegment(type="function", ...)
        }
    """
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        raise ValueError(f"Invalid Python syntax: {e}")
    
    segments = {}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Check if method (inside class)
            parent_class = _find_parent_class(node, tree)
            if parent_class:
                full_name = f"{parent_class}.{node.name}"
                seg_type = "method"
            else:
                full_name = node.name
                seg_type = "function"
            
            segments[full_name] = PythonSegment(
                name=full_name,
                type=seg_type,
                start_line=node.lineno,
                end_line=node.end_lineno,
                parent=parent_class
            )
        
        elif isinstance(node, ast.ClassDef):
            segments[node.name] = PythonSegment(
                name=node.name,
                type="class",
                start_line=node.lineno,
                end_line=node.end_lineno,
                parent=None
            )
    
    return segments

def _find_parent_class(func_node: ast.FunctionDef, tree: ast.Module) -> str | None:
    """Find parent class for a function node."""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if func_node in ast.walk(node):
                return node.name
    return None
```

**Edge Cases:**
- **Nested functions:** Use `outer_func.inner_func` naming
- **Decorators:** Include in segment range (from decorator to end)
- **Async functions:** Treat same as regular functions
- **Invalid syntax:** Return empty dict + error message

**Implementation Complexity:**
- **Effort:** 🟡 MEDIUM (1 day)
- **Risk:** 🟡 MEDIUM (AST parsing can fail on syntax errors)
- **Tests:** Functions, classes, methods, nesting, decorators, async

### 3. Template Block Detection

**Challenge:** Identify template-defined blocks in scaffolded files using Issue #120 introspection.

**Algorithm:**

```python
from mcp_server.scaffolding.template_introspector import TemplateIntrospector
from mcp_server.scaffolding.metadata_parser import ScaffoldMetadataParser

class TemplateBlock(NamedTuple):
    name: str
    type: Literal["metadata", "section", "list", "code_block"]
    start_line: int
    end_line: int
    template_id: str

def detect_template_blocks(content: str, file_path: str) -> dict[str, TemplateBlock]:
    """Parse scaffolded file → template block ranges.
    
    Integrates with Issue #120:
    1. Parse YAML frontmatter for template ID
    2. Load template schema via TemplateIntrospector
    3. Match content structure to template definition
    
    Returns:
        {
            "metadata": TemplateBlock(type="metadata", ...),
            "Problem Statement": TemplateBlock(type="section", ...),
            "Acceptance Criteria": TemplateBlock(type="list", ...)
        }
    """
    # 1. Parse frontmatter (Issue #120 Phase 0)
    try:
        metadata = ScaffoldMetadataParser.parse(content)
        template_id = metadata.template_id
    except Exception:
        raise ValueError("File is not scaffolded (no YAML frontmatter)")
    
    # 2. Load template schema (Issue #120 Phase 1)
    introspector = TemplateIntrospector()
    schema = introspector.get_schema(template_id)
    
    # 3. Detect metadata block (YAML frontmatter)
    blocks = {}
    yaml_end = _find_yaml_end(content)
    blocks["metadata"] = TemplateBlock(
        name="metadata",
        type="metadata",
        start_line=1,
        end_line=yaml_end,
        template_id=template_id
    )
    
    # 4. Detect sections based on template schema
    # Schema example: {"sections": ["Problem", "Solution", "Implementation"]}
    expected_sections = schema.get("sections", [])
    markdown_sections = detect_markdown_sections(content)
    
    for section_name in expected_sections:
        if section_name in markdown_sections:
            sec = markdown_sections[section_name]
            blocks[section_name] = TemplateBlock(
                name=section_name,
                type="section",
                start_line=sec.start_line,
                end_line=sec.end_line,
                template_id=template_id
            )
    
    # 5. Detect lists (e.g., "Acceptance Criteria", "Dependencies")
    # Schema: {"lists": ["Dependencies", "Acceptance Criteria"]}
    expected_lists = schema.get("lists", [])
    for list_name in expected_lists:
        # Find section containing list
        if list_name in markdown_sections:
            sec = markdown_sections[list_name]
            blocks[list_name] = TemplateBlock(
                name=list_name,
                type="list",
                start_line=sec.start_line,
                end_line=sec.end_line,
                template_id=template_id
            )
    
    return blocks

def _find_yaml_end(content: str) -> int:
    """Find line number where YAML frontmatter ends."""
    lines = content.split('\n')
    if not lines[0].startswith('<!--'):
        return 0
    
    # Find closing -->
    for i, line in enumerate(lines, start=1):
        if '-->' in line:
            return i
    return 0
```

**Integration with Issue #120:**
- ✅ Reuses `TemplateIntrospector` for schema extraction
- ✅ Reuses `ScaffoldMetadataParser` for frontmatter parsing
- ✅ Same template = SSOT principle (no duplication)
- ✅ Validation uses same schema as scaffolding

**Edge Cases:**
- **Template version mismatch:** Warning but allow edit
- **Manual edits:** Best-effort detection (may not match template exactly)
- **Unknown template:** Fall back to markdown section detection
- **Missing frontmatter:** Error - not a scaffolded file

**Implementation Complexity:**
- **Effort:** 🔴 HIGH (2-3 days)
- **Risk:** 🔴 HIGH (depends on Issue #120 stability)
- **Tests:** All artifact types, version handling, manual edits

---

## SegmentEdit API Design

### Core Model

```python
from enum import Enum
from pydantic import BaseModel, Field

class SegmentType(str, Enum):
    MARKDOWN_SECTION = "markdown_section"
    PYTHON_FUNCTION = "python_function"
    PYTHON_CLASS = "python_class"
    PYTHON_METHOD = "python_method"
    TEMPLATE_BLOCK = "template_block"

class SegmentEdit(BaseModel):
    """Segment-based edit operation.
    
    Edit by semantic identifier instead of line numbers or exact text.
    """
    segment_type: SegmentType
    segment_name: str = Field(
        ...,
        description="Segment identifier. Examples: 'Problem Statement' (markdown), "
                    "'calculate_risk' (Python function), 'MyClass.my_method' (method)"
    )
    new_content: str = Field(
        ...,
        description="New content for segment (will replace entire segment)"
    )
    
    @staticmethod
    def edit_section(section: str, content: str) -> "SegmentEdit":
        """Edit markdown section by name."""
        return SegmentEdit(
            segment_type=SegmentType.MARKDOWN_SECTION,
            segment_name=section,
            new_content=content
        )
    
    @staticmethod
    def edit_function(function: str, content: str) -> "SegmentEdit":
        """Edit Python function by name."""
        return SegmentEdit(
            segment_type=SegmentType.PYTHON_FUNCTION,
            segment_name=function,
            new_content=content
        )
    
    @staticmethod
    def edit_method(method: str, content: str) -> "SegmentEdit":
        """Edit Python method by qualified name (Class.method)."""
        return SegmentEdit(
            segment_type=SegmentType.PYTHON_METHOD,
            segment_name=method,
            new_content=content
        )
    
    @staticmethod
    def edit_template_block(block: str, content: str) -> "SegmentEdit":
        """Edit template block in scaffolded file."""
        return SegmentEdit(
            segment_type=SegmentType.TEMPLATE_BLOCK,
            segment_name=block,
            new_content=content
        )
```

### Usage Examples

```python
# Markdown section
SegmentEdit.edit_section(
    section="Problem Statement",
    content="## Problem Statement\n\nNew problem description..."
)

# Python function
SegmentEdit.edit_function(
    function="calculate_risk",
    content="def calculate_risk(position):\n    return position.size * 0.02"
)

# Python method
SegmentEdit.edit_method(
    method="Worker.process",
    content="async def process(self, ctx, event):\n    # New implementation\n    pass"
)

# Template block (scaffolded file)
SegmentEdit.edit_template_block(
    block="Acceptance Criteria",
    content="## Acceptance Criteria\n\n- [ ] New criterion\n- [ ] Another criterion"
)
```

### Error Handling

**Segment Not Found:**
```python
raise ValueError(
    f"Segment '{segment_name}' not found in file.\n"
    f"Available segments: {', '.join(detected_segments.keys())}\n"
    f"Tip: Check spelling and capitalization."
)
```

**Ambiguous Match:**
```python
raise ValueError(
    f"Multiple segments match '{segment_name}':\n"
    f"  - {matches[0]} (line {line1})\n"
    f"  - {matches[1]} (line {line2})\n"
    f"Use hierarchical name: 'Parent::Child'"
)
```

**Invalid Segment Type:**
```python
raise ValueError(
    f"Segment type '{segment_type}' not valid for file type.\n"
    f"File: Python (.py)\n"
    f"Valid types: python_function, python_class, python_method\n"
    f"Requested: markdown_section"
)
```

---

## Multi-File Batching

### Pattern from VS Code

VS Code's `multi_replace_string_in_file`:
```python
multi_replace_string_in_file(
    explanation="Update imports across DTOs",
    replacements=[
        {"filePath": "dto1.py", "oldString": "...", "newString": "..."},
        {"filePath": "dto2.py", "oldString": "...", "newString": "..."}
    ]
)
```

### Proposed API

**Option 1: Batch parameter on safe_edit_file**
```python
safe_edit_file(
    edits=[
        {"path": "file1.py", "segment_edit": SegmentEdit.edit_function(...)},
        {"path": "file2.py", "line_edits": [...]},
    ],
    mode="strict"
)
```

**Option 2: Separate batch tool**
```python
batch_edit_files(
    files=["file1.py", "file2.py", "file3.py"],
    edit=SegmentEdit.edit_section("Problem Statement", "..."),
    mode="strict"
)
```

### Recommendation

**Start WITHOUT batching** - add in Phase 2 if agent usage shows demand.

**Rationale:**
1. Simpler implementation (no transaction/rollback logic)
2. Validate segment editing first
3. Agent can call safe_edit_file multiple times (parallel if needed)
4. Can add batching later without breaking changes

---

## Integration Architecture

### Extension of safe_edit_tool

```python
# mcp_server/tools/safe_edit_tool.py

class SafeEditInput(BaseModel):
    # Existing modes (unchanged)
    content: str | None = None
    line_edits: list[LineEdit] | None = None
    insert_lines: list[InsertLine] | None = None
    search: str | None = None
    replace: str | None = None
    
    # NEW: 5th mode
    segment_edit: SegmentEdit | None = Field(
        None,
        description="Semantic edit by segment name (section, function, template block)"
    )
    
    @model_validator(mode="after")
    def validate_edit_modes(self) -> "SafeEditInput":
        """Validate exactly one edit mode specified."""
        modes = [
            self.content,
            self.line_edits,
            self.insert_lines,
            (self.search and self.replace),
            self.segment_edit  # NEW mode
        ]
        
        specified = sum(1 for m in modes if m)
        if specified != 1:
            raise ValueError("Must specify exactly one edit mode")
        
        return self

class SafeEditTool(BaseTool):
    async def execute(self, input: SafeEditInput) -> ToolResult:
        # ... existing logic ...
        
        # NEW: Handle segment_edit mode
        if input.segment_edit:
            content = await self._apply_segment_edit(
                path=input.path,
                edit=input.segment_edit
            )
        
        # ... validation, diff, write (unchanged) ...
    
    async def _apply_segment_edit(
        self, path: str, edit: SegmentEdit
    ) -> str:
        """Apply segment edit by converting to line edit."""
        content = Path(path).read_text()
        
        # 1. Detect segments
        if edit.segment_type == SegmentType.MARKDOWN_SECTION:
            segments = detect_markdown_sections(content)
        elif edit.segment_type in (
            SegmentType.PYTHON_FUNCTION,
            SegmentType.PYTHON_CLASS,
            SegmentType.PYTHON_METHOD
        ):
            segments = detect_python_segments(content)
        elif edit.segment_type == SegmentType.TEMPLATE_BLOCK:
            segments = detect_template_blocks(content, path)
        else:
            raise ValueError(f"Unknown segment type: {edit.segment_type}")
        
        # 2. Find target segment
        if edit.segment_name not in segments:
            available = ", ".join(segments.keys())
            raise ValueError(
                f"Segment '{edit.segment_name}' not found. "
                f"Available: {available}"
            )
        
        segment = segments[edit.segment_name]
        
        # 3. Convert to line edit (reuse existing logic!)
        line_edit = LineEdit(
            start_line=segment.start_line,
            end_line=segment.end_line,
            new_content=edit.new_content
        )
        
        # 4. Apply using existing _apply_line_edits method
        return self._apply_line_edits(content, [line_edit])
```

**Key Design Points:**
- ✅ Segment edit → line edit conversion (reuse existing logic)
- ✅ Validation/diff/write unchanged (same infrastructure)
- ✅ Backward compatible (no breaking changes)
- ✅ Single tool (no duplication)

---

## Implementation Roadmap

### Phase 0: Foundation (Already Complete)

- ✅ Issue #120 Phase 0: Template metadata in frontmatter
- ✅ Issue #120 Phase 1: TemplateIntrospector + schema caching
- ✅ Issue #38: safe_edit_tool with 4 modes
- ✅ Feasibility analysis: VS Code comparison

### Phase 1: Markdown Section Detection (4-6 hours)

**Tasks:**
- [ ] Implement `detect_markdown_sections()` function
- [ ] Handle heading hierarchy and nesting
- [ ] Edge cases: duplicate names, code blocks, ATX vs Setext
- [ ] Unit tests: 10+ test cases
- [ ] Integration test: Edit section in real design doc

**Deliverable:** Markdown section editing works

### Phase 2: SegmentEdit Model + Integration (6-8 hours)

**Tasks:**
- [ ] Define `SegmentEdit` Pydantic model
- [ ] Add `segment_edit` field to `SafeEditInput`
- [ ] Implement `_apply_segment_edit()` method
- [ ] Implement segment → line edit conversion
- [ ] Update `validate_edit_modes()` for 5th mode
- [ ] Unit tests: Model validation, conversion logic
- [ ] Integration tests: End-to-end edit with markdown

**Deliverable:** safe_edit_file supports segment_edit mode for markdown

### Phase 3: Python Function Detection (1 day)

**Tasks:**
- [ ] Implement `detect_python_segments()` using ast module
- [ ] Handle functions, classes, methods, nesting
- [ ] Edge cases: decorators, async, nested functions
- [ ] Unit tests: All Python segment types
- [ ] Integration test: Edit function in worker file

**Deliverable:** Python function/class editing works

### Phase 4: Template Block Detection (2-3 days)

**Tasks:**
- [ ] Implement `detect_template_blocks()` function
- [ ] Integration with Issue #120 TemplateIntrospector
- [ ] Integration with ScaffoldMetadataParser
- [ ] Handle template version mismatches
- [ ] Edge cases: unknown templates, manual edits
- [ ] Unit tests: All artifact types (design, research, dto, worker)
- [ ] Integration tests: Edit template blocks

**Deliverable:** Template block editing works

**Dependencies:**
- ✅ Issue #120 Phase 1 (TemplateIntrospector) - COMPLETE

### Phase 5: Error Handling (4-6 hours)

**Tasks:**
- [ ] Implement "segment not found" error messages
- [ ] List available segments in error
- [ ] Handle ambiguous matches (multiple segments same name)
- [ ] Implement file type validation (can't edit Python segments in markdown)
- [ ] Unit tests: All error scenarios
- [ ] User-friendly error messages with hints

**Deliverable:** Helpful error messages guide agents

### Phase 6: Documentation + Examples (4 hours)

**Tasks:**
- [ ] Update `docs/reference/mcp/tools/editing.md`
- [ ] Add SegmentEdit API documentation
- [ ] Add usage examples per segment type
- [ ] Document error handling patterns
- [ ] Add troubleshooting guide
- [ ] Update agent.md with segment editing guidance

**Deliverable:** Complete documentation

### Total Effort Estimate

| Phase | Effort | Risk |
|-------|--------|------|
| Phase 1: Markdown detection | 4-6h | 🟢 LOW |
| Phase 2: SegmentEdit integration | 6-8h | 🟢 LOW |
| Phase 3: Python detection | 1 day | 🟡 MEDIUM |
| Phase 4: Template detection | 2-3 days | 🔴 HIGH |
| Phase 5: Error handling | 4-6h | 🟢 LOW |
| Phase 6: Documentation | 4h | 🟢 LOW |
| **TOTAL** | **5-8 days** | **MEDIUM** |

---

## Mapping to Issue #121 Acceptance Criteria

### Issue #121 AC (from Issue Description)

**Pre-Phase 0 (Discovery Tool):**
- ✅ query_file_schema detects scaffolded files via frontmatter
- ✅ Returns template schema from #120 introspector
- ✅ Lists available SegmentEdit capabilities
- ✅ Graceful degradation for non-scaffolded/unrecognized files
- ✅ Same schema format as scaffolding errors (consistency!)

**Phase 1 (VS Code API):**
- ❌ SKIPPED - Research concluded character offsets not relevant

**Phase 2 (SegmentEdit):**
- ✅ edit_section works for markdown headings
- ✅ edit_function works for Python functions
- ✅ edit_method works for Python methods
- ✅ edit_template_block works for scaffolded files
- ✅ Reuses #120 TemplateIntrospector
- ✅ Reuses #120 ScaffoldMetadataParser

**Phase 3 (editFiles Tool):**
- 🟡 DEFERRED - Start with extending safe_edit_tool (Optie A)
- ✅ Validation via existing safe_edit infrastructure
- ✅ Diff preview via existing mechanism
- ✅ Error messages helpful and actionable

**Phase 4 (Validation):**
- ✅ Uses safe_edit_tool's existing validation modes
- ✅ Template structure validation via #120 schema
- ✅ Validation errors formatted identically

### Our Implementation Mapping

| AC | Implementation | Status | Phase |
|----|----------------|--------|-------|
| Markdown section editing | `detect_markdown_sections()` | 🟡 TODO | Phase 1 |
| Python function editing | `detect_python_segments()` | 🟡 TODO | Phase 3 |
| Template block editing | `detect_template_blocks()` | 🟡 TODO | Phase 4 |
| SegmentEdit → LineEdit | `_apply_segment_edit()` | 🟡 TODO | Phase 2 |
| 5th mode integration | `segment_edit` field | 🟡 TODO | Phase 2 |
| Error messages | Segment not found, list available | 🟡 TODO | Phase 5 |
| #120 integration | TemplateIntrospector reuse | ✅ READY | Phase 4 |
| Validation | Existing safe_edit modes | ✅ READY | All |
| Documentation | Reference docs update | 🟡 TODO | Phase 6 |

---

## Risk Assessment

### High Risk Items

**1. Template Detection Complexity (Phase 4)**
- **Risk:** Issue #120 integration may have edge cases
- **Mitigation:** Extensive testing with all artifact types
- **Fallback:** Graceful degradation to markdown section detection

**2. AST Parsing Failures (Phase 3)**
- **Risk:** Invalid Python syntax breaks detection
- **Mitigation:** Try/except with helpful error messages
- **Fallback:** Agent can use line_edits mode instead

**3. Ambiguous Segment Names**
- **Risk:** Multiple sections with same name (e.g., "Dependencies")
- **Mitigation:** Hierarchical naming (Parent::Child)
- **Fallback:** Error message lists all matches

### Medium Risk Items

**4. Performance (Large Files)**
- **Risk:** AST parsing + markdown parsing may be slow
- **Mitigation:** Cache segment detection results
- **Acceptance:** Editing 1000+ line files may take 1-2 seconds

**5. Agent Adoption**
- **Risk:** Agents may continue using line_edits (habit)
- **Mitigation:** Documentation + examples in agent.md
- **Monitoring:** Track segment_edit usage metrics

### Low Risk Items

**6. Backward Compatibility**
- **Risk:** Breaking existing safe_edit_tool users
- **Mitigation:** New mode is additive (no breaking changes)

**7. Validation Integration**
- **Risk:** Segment edits may break validation
- **Mitigation:** Reuse existing validation infrastructure

---

## Conclusions

### Key Findings

1. **Segment-based editing solves Issue #54 problems**
   - Eliminates pattern matching fragility
   - Robust against line shifts
   - Natural language alignment

2. **Implementation is incremental**
   - Start with markdown (4-6h MVP)
   - Add Python in Phase 3 (1 day)
   - Template blocks in Phase 4 (2-3 days)
   - Total: 5-8 days

3. **Reuse existing infrastructure**
   - Issue #120 template introspection
   - safe_edit_tool validation/diff
   - Line edit conversion (no new logic)

4. **Character offsets not needed**
   - VS Code doesn't use them for agents
   - Line-based + search_replace sufficient
   - Skip deeltaak 2

5. **Extend, don't replace**
   - Add 5th mode to safe_edit_tool
   - Backward compatible
   - Can add batching later

### Recommendations

#### ✅ HIGH PRIORITY

**Implement Segment-Based Editing (Deeltaak 3)**
- 5-8 days effort
- High ROI (solves core Issue #54 problem)
- Start with markdown MVP (4-6h)
- Incremental delivery

#### ✅ MEDIUM PRIORITY

**Extend safe_edit_tool (Deeltaak 1 - Optie A)**
- Add segment_edit as 5th mode
- No tool duplication
- Faster delivery than separate tool
- Can migrate to Optie B later if needed

#### ❌ SKIP

**Character Offset API (Deeltaak 2)**
- Not used by VS Code agents
- Complexity without benefit
- Focus effort on segment editing

### Next Steps

1. **Planning Phase:**
   - Detailed API design
   - Test strategy
   - Implementation tasks breakdown

2. **Phase 1 Implementation:**
   - Markdown section detection
   - SegmentEdit model
   - Integration with safe_edit_tool

3. **Validation:**
   - Agent testing with real workflows
   - Usage metrics collection
   - Iterate based on feedback

---

## References

- [Python ast module documentation](https://docs.python.org/3/library/ast.html)
- [Markdown parsing libraries](https://github.com/lepture/mistune)
- [Issue #120 TemplateIntrospector](../../mcp_server/scaffolding/template_introspector.py)
- [Issue #54 agent evaluation](../issue54/safe_edit_evaluation.md)
- [safe_edit_tool implementation](../../mcp_server/tools/safe_edit_tool.py)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-08 | Agent | Complete research: segment detection algorithms, API design, implementation roadmap |

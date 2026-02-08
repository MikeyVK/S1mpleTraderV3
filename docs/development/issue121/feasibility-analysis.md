<!-- docs/development/issue121/feasibility-analysis.md -->
<!-- template=research version=8b7bb3ab created=2026-02-08T15:30:00Z updated=2026-02-08 -->
# Issue #121 Feasibility Analysis: VS Code Edit Tools vs MCP safe_edit_tool

**Status:** COMPLETE  
**Version:** 1.0  
**Last Updated:** 2026-02-08

---

## Purpose

Analyze VS Code native editing capabilities, compare with MCP safe_edit_tool, and assess feasibility of segment-based editing approach for Issue #121 implementation.

## Scope

**In Scope:**
- VS Code native editing tools (create_file, replace_string_in_file, multi_replace_string_in_file)
- MCP safe_edit_tool capabilities (4 edit modes: content, line_edits, insert_lines, search_replace)
- Comparison: granularity, safety, batch operations, validation
- Segment-based editing feasibility (markdown sections, Python functions, template blocks)
- Implementation effort, risks, dependencies, ROI assessment

**Out of Scope:**
- Notebook editing (edit_notebook_file is separate domain)
- VS Code Extension API internals (we need agent-facing tools only)
- Alternative IDEs (Cursor, Windsurf) - focus on VS Code
- Detailed implementation design (that's for planning phase)

## Prerequisites

Read these first:
1. [Issue #54 safe_edit evaluation](../issue54/safe_edit_evaluation.md) - Agent struggle patterns documented
2. Issue #120 Phase 0+1 - Template introspection infrastructure (COMPLETE)
3. VS Code native edit tools temporarily enabled for testing
4. [Current safe_edit_tool implementation](../../../mcp_server/tools/safe_edit_tool.py) - Issue #38 complete

---

## Problem Statement

Issue #121 proposes VS Code Position/Range API alignment and segment-based editing. Research needed to determine: 
1. What editing capabilities does VS Code actually provide to agents? 
2. Is character offset precision (Position/Range) valuable for conversational AI? 
3. What is the feasibility and ROI of segment-based editing?

## Research Goals

- Document VS Code's native editing capabilities for agents
- Identify gaps between VS Code tools and MCP safe_edit_tool
- Assess value of character offset API (Position/Range) for conversational AI
- Evaluate segment-based editing feasibility (effort, risk, value)
- Provide actionable recommendations for Issue #121 implementation

---

## Methodology

### Testing Approach

1. **VS Code Tool Activation**: Temporarily enabled VS Code native edit tools (normally disabled to enforce MCP tooling)
2. **Live Testing**: Created test files and performed edits with both VS Code and MCP tools
3. **Comparison Matrix**: Documented features, limitations, and usage patterns
4. **Feasibility Analysis**: Assessed implementation effort, risks, and ROI for proposed features

### Tools Tested

**VS Code Native:**
- `create_file(filePath, content)` - Simple file creation
- `replace_string_in_file(filePath, oldString, newString)` - Context-based replacement
- `multi_replace_string_in_file(explanation, replacements[])` - Batch operations

**MCP Server:**
- `safe_edit_file(path, content/line_edits/insert_lines/search+replace, mode, show_diff)` - Multi-mode editing

---

## Findings

### 1. VS Code Native Editing Tools

#### Tool 1: `create_file`

**API:**
```python
create_file(
    filePath="/absolute/path/file.py",
    content="complete file content"
)
```

**Characteristics:**
- ✅ Simple file creation
- ❌ No validation
- ❌ No diff preview
- ❌ Overwrites without safety checks
- ❌ No quality gates

#### Tool 2: `replace_string_in_file`

**API:**
```python
replace_string_in_file(
    filePath="/absolute/path/file.py",
    oldString="exact text to find\nwith newlines\nincluding context",
    newString="replacement text\nwith newlines"
)
```

**Characteristics:**
- ✅ **Context-based matching** - requires 3-5 lines surrounding context
- ✅ Single replacement operation
- ❌ **Exact match required** - whitespace/formatting sensitive!
- ❌ No line number support (must know exact text)
- ❌ No regex support (literal strings only)
- ❌ No validation or diff preview

**⚠️ CRITICAL FINDING:** This is **exactly the same fragility** Issue #54 identified:
> "Pattern matching requires exact text match (not intuitive)" - Issue #54 Conclusion

#### Tool 3: `multi_replace_string_in_file`

**API:**
```python
multi_replace_string_in_file(
    explanation="What we're doing",
    replacements=[
        {
            "filePath": "path1.py",
            "oldString": "...",
            "newString": "..."
        },
        {
            "filePath": "path2.py",
            "oldString": "...",
            "newString": "..."
        }
    ]
)
```

**Characteristics:**
- ✅ **Batch operations** - multiple files/edits in one call
- ✅ Efficiency for multi-file changes
- ❌ Same exact matching limitations as replace_string_in_file
- ❌ No atomic rollback (partial failures possible)
- ❌ No validation

**✅ VALUABLE PATTERN:** Multi-file batching is worth adopting in MCP tools.

### 2. MCP safe_edit_tool Analysis

**Current Implementation:** [mcp_server/tools/safe_edit_tool.py](../../../mcp_server/tools/safe_edit_tool.py)

#### Mode 1: Full Rewrite
```python
safe_edit_file(
    path="/absolute/path",
    content="complete new content",
    mode="strict",
    show_diff=True
)
```

#### Mode 2: Line-Based Edits
```python
safe_edit_file(
    path="/absolute/path",
    line_edits=[
        {"start_line": 10, "end_line": 12, "new_content": "..."},
        {"start_line": 20, "end_line": 22, "new_content": "..."}
    ],
    mode="strict",
    show_diff=True
)
```

**Key characteristic:** **1-based line numbers** (human-friendly)

#### Mode 3: Line Insertions
```python
safe_edit_file(
    path="/absolute/path",
    insert_lines=[
        {"at_line": 5, "content": "new line\n"}
    ]
)
```

#### Mode 4: Search/Replace
```python
safe_edit_file(
    path="/absolute/path",
    search="old_pattern",
    replace="new_text",
    regex=True,  # ✅ Regex support!
    search_count=1  # Limit replacements
)
```

### 3. Feature Comparison Matrix

| Feature | VS Code Native | MCP safe_edit | Winner |
|---------|----------------|---------------|---------|
| **Edit by exact text match** | ✅ replace_string_in_file | ✅ search_replace mode | 🤝 Tie |
| **Edit by line numbers** | ❌ NONE | ✅ line_edits mode | 🏆 **MCP** |
| **Context-based safety** | ✅ Requires 3-5 lines context | ⚠️ Optional (search mode) | 🏆 **VS Code** (safer default) |
| **Batch operations** | ✅ multi_replace | ❌ Single file only | 🏆 **VS Code** |
| **Regex support** | ❌ Literal only | ✅ regex=True flag | 🏆 **MCP** |
| **Validation** | ❌ NONE | ✅ pylint/mypy/pyright | 🏆 **MCP** |
| **Diff preview** | ❌ NONE | ✅ unified_diff | 🏆 **MCP** |
| **Line insertions** | ❌ Must use replace | ✅ Dedicated mode | 🏆 **MCP** |
| **Concurrent safety** | ❌ No protection | ✅ asyncio.Lock | 🏆 **MCP** |
| **Error modes** | ❌ Fail or succeed | ✅ strict/interactive/verify | 🏆 **MCP** |
| **Whitespace sensitivity** | ✅ Very sensitive (safety) | ⚠️ Depends on mode | 🏆 **VS Code** (safer) |

### 4. Critical Insights

#### Insight 1: VS Code's Exact Matching = Issue #54 Problem

**VS Code `replace_string_in_file` requires exact match:**
```python
oldString="""# Line 1
# Line 2: Original content  ← Must match EXACTLY (spaces, tabs, etc.)
# Line 3"""
```

**This is PRECISELY what Issue #54 documented as agent struggle:**
- ✅ Safe (wrong replacements rejected)
- ❌ Fragile (formatting changes break edits)
- ❌ Agents struggle with this!

**MCP safe_edit has FLEXIBLE alternatives:**
- **Line numbers:** `line_edits=[{start_line: 2, end_line: 2, ...}]` → no exact match needed
- **Regex patterns:** `search="# Line 2:.*", regex=True` → flexible matching

**Validation:** This confirms segment-based editing is the right solution!

#### Insight 2: Multi-File Batching is Valuable

VS Code's `multi_replace_string_in_file` can edit **multiple files** in one call:
```python
replacements=[
    {"filePath": "file1.py", "oldString": "...", "newString": "..."},
    {"filePath": "file2.py", "oldString": "...", "newString": "..."}
]
```

**MCP safe_edit cannot do this** - single file per call.

**Recommendation:** Adopt this pattern in Issue #121 implementation.

#### Insight 3: Character Offsets NOT in VS Code Agent Tools

**Finding:** VS Code agent tools use:
- **Exact string matching** (oldString/newString)
- NO Position/Range models
- NO character offset calculation

**Implication:** Character offsets (Issue #121 original deeltaak 2) are **NOT relevant** for agent tooling!

**Conclusion:** ✅ Skip character offset API (Position/Range) - not needed.

#### Insight 4: MCP's Validation/Diff are Unique Value

VS Code tools have **no** built-in validation or preview capabilities.

Agent must manually:
1. Make edit
2. Read file to verify result
3. Check diff manually

**MCP does this automatically:**
```diff
--- a/file.py
+++ b/file.py
@@ -2,1 +2,1 @@
-# Line 2: Original
+# Line 2: MODIFIED
```

**Value proposition:** Keep and expand these capabilities!

### 5. Segment-Based Editing Feasibility

#### What is Segment-Based Editing?

Edit files by **semantic structure** instead of line numbers or text patterns:

**Markdown:**
```python
edit_section(path, section="Problem Statement", new_content="...")
```

**Python:**
```python
edit_function(path, function="calculate_risk", new_content="...")
```

**Scaffolded files:**
```python
edit_template_block(path, block="acceptance_criteria", new_content="...")
```

#### Implementation Complexity

| Component | Effort | Risk | Details |
|-----------|--------|------|---------|
| **Markdown section detector** | 🟢 LOW (4h) | 🟢 LOW | Regex for `## Heading` patterns |
| **Python function detector** | 🟡 MEDIUM (1 day) | 🟡 MEDIUM | `ast.parse()` → extract FunctionDef nodes |
| **Template block detector** | 🔴 HIGH (2-3 days) | 🔴 HIGH | Requires Issue #120 TemplateIntrospector integration |
| **edit_segment API** | 🟢 LOW (4h) | 🟢 LOW | Wrapper around line_edits mode |
| **Error handling** | 🟡 MEDIUM (1 day) | 🟡 MEDIUM | Segment not found, ambiguous matches |
| **Testing** | 🔴 HIGH (2 days) | 🟢 LOW | Edge cases, nested sections, malformed files |

**Total Effort:** 5-8 days (1 work week)

**Dependencies:**
- ✅ Issue #120 TemplateIntrospector (for template block detection)
- ✅ Python `ast` module (built-in)
- ⚠️ Markdown parsing (regex or library like `mistune`)

**Risks:**
- 🟡 Ambiguous matches (multiple sections with same name)
- 🟡 Malformed files (invalid syntax breaks AST parsing)
- 🟢 Template evolution (version-aware detection via Issue #120)

#### Value Proposition

**✅ HIGH VALUE - Directly solves Issue #54 agent struggles!**

**Benefits:**

1. **Robustness against line shifts** 🎯
   - Agent doesn't need to know line numbers
   - `edit_section("Problem Statement")` works regardless of position

2. **Natural language alignment** 🗣️
   - Agents think in semantics: "Update the problem statement"
   - No translation to line numbers needed

3. **Template awareness** 📐
   - Scaffolded files have known structure
   - `edit_template_block("acceptance_criteria")` → guaranteed correct block

4. **Eliminates pattern matching fragility** (Issue #54 #1 problem)
   - No exact text match needed
   - Whitespace/formatting changes don't break edits

5. **No content preview needed** (Issue #54 #2 problem)
   - Agent doesn't need to read file first
   - `edit_function("calculate_risk")` → tool finds it automatically

#### Comparison: Line vs Segment Editing

| Metric | Line-based | Segment-based | Winner |
|--------|------------|---------------|--------|
| **Agent effort** | Must read file + calculate line ranges | Single semantic identifier | 🏆 Segment |
| **Robustness** | Breaks on line shifts | Resilient to line shifts | 🏆 Segment |
| **Precision** | Whole lines only | Semantic blocks (variable size) | 🏆 Segment |
| **Simplicity** | Simple integers | Requires segment detection | 🏆 Line |
| **Template awareness** | None (raw text) | Understands scaffolding structure | 🏆 Segment |
| **Error recovery** | Manual re-read + retry | Auto-locate segment | 🏆 Segment |

---

## Conclusions

### Key Findings Summary

1. **VS Code's exact matching = same problem Issue #54 identified**
   - `replace_string_in_file` is whitespace/formatting sensitive
   - Agents struggle with this pattern
   - Validates need for segment-based approach

2. **Multi-file batching is valuable pattern**
   - VS Code's `multi_replace_string_in_file` efficiency is worth adopting
   - Issue #121 editFiles tool should support batch operations

3. **Character offsets NOT relevant**
   - VS Code does NOT use Position/Range in agent tools
   - Exact string matching is the pattern
   - Skip deeltaak 2 (character offset API)

4. **MCP validation/diff are unique value**
   - VS Code has no quality gates
   - Keep and expand these capabilities
   - Competitive advantage for MCP server

5. **Segment-based editing solves core problem**
   - Directly addresses Issue #54 recommendations
   - "Template-aware mode" + "Section-based editing"
   - 5-8 days effort for high ROI

### Recommendations

#### ✅ HIGH PRIORITY: Implement Segment-Based Editing (Deeltaak 3)

**Rationale:**
- Solves Issue #54 agent struggles directly
- Template awareness = core value proposition
- Robust against line shifts (dynamic segment lookup)
- Natural language alignment (agents think in semantics)

**ROI:** HIGH - 6-8 days effort for structural agent improvement

**Implementation approach:**
- Start with markdown section detection (4h MVP)
- Add Python function detection via AST (1 day)
- Integrate template block detection with Issue #120 (2-3 days)

#### ✅ MEDIUM PRIORITY: Adopt Multi-File Batching Pattern (Deeltaak 1 Enhancement)

**Rationale:**
- VS Code pattern validation
- Efficiency boost for batch operations
- API ergonomics improvement

**ROI:** MEDIUM - 2 days effort for cleaner API

**Implementation approach:**
- Extend safe_edit_tool with batch mode
- OR create new editFiles tool with multi-file support
- Reuse 90% of safe_edit_tool internals

#### ❌ LOW PRIORITY: Skip Character Offset API (Deeltaak 2)

**Rationale:**
- VS Code does NOT use this in agent tools
- Agents work with natural language, not character offsets
- search_replace mode provides sufficient fine-grained editing
- Complexity overhead without practical benefit

**Decision:** ✅ SKIP - Not valuable for conversational AI

#### ✅ KEEP: MCP safe_edit_tool strengths

- Line-based editing (less fragile than exact matching)
- Validation + diff preview (unique vs VS Code)
- Regex support (flexibility)
- Multiple validation modes (strict/interactive/verify)

### Implementation Strategy

**Recommended:** Extend safe_edit_tool (not separate tool)

**Rationale:**
- No tool duplication
- Backward compatible (existing modes unchanged)
- Faster implementation (reuse validation/diff logic)
- Single tool for agents to learn

**Add 5th mode:**
```python
class SafeEditInput(BaseModel):
    # Existing modes
    content: str | None = None
    line_edits: list[LineEdit] | None = None
    insert_lines: list[InsertLine] | None = None
    search: str | None = None
    
    # NEW MODE
    segment_edit: SegmentEdit | None = None  # 5th mode
```

**Alternative:** New editFiles tool (deferred until Optie A validated)

---

## References

- [Issue #54: Agent struggle evaluation](../issue54/safe_edit_evaluation.md) - Pattern matching sensitivity documented
- [Issue #38: Enhanced safe_edit_tool](../issue-38-enhanced-safe-edit-planning.md) - 4 edit modes implemented
- [Issue #120: Template introspection](../issue72/research.md) - Infrastructure for template awareness
- [MCP safe_edit_tool implementation](../../../mcp_server/tools/safe_edit_tool.py) - Current codebase
- [Editing tools reference](../../reference/mcp/tools/editing.md) - Documentation

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-08 | Agent | Initial feasibility analysis - VS Code comparison, segment-based evaluation, recommendations |

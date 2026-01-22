# Discovery Tool Analysis: Why Issue #121 Differs from #120

<!-- SCAFFOLD: template=research version=1.0 created=2026-01-22T16:00:00Z path=docs/development/issue121/research-discovery-tool-analysis.md -->

**Issue:** #121  
**Status:** Research  
**Version:** 1.0  
**Date:** 2026-01-22

---

## Executive Summary

In Issue #120, we **deliberately chose NOT to expose** `get_artifact_schema` as a tool because lazy discovery (schema in error messages) was sufficient for scaffolding workflows. However, **Issue #121 requires a different approach**: a proactive discovery tool (`query_file_schema`) provides measurable value for editing workflows.

**Key Insight:** The fundamental difference is **agent knowledge context**:
- **Scaffolding (#120):** Agent provides artifact type as input → always knows what to scaffold
- **Editing (#121):** Agent receives file path → often lacks context about file type/template

This research document explains why the same "no discovery tool" decision from #120 does NOT apply to #121, and provides the rationale for Pre-Phase 0 (standalone discovery tool).

---

## Context: Issue #120 vs #121

### Issue #120: Template-Driven Scaffolding

**Agent Workflow:**
```python
scaffold_artifact("dto", name="Signal", description="...")
# Agent explicitly provides artifact type: "dto"
# → System knows which template to use
# → Lazy discovery: schema in error message is sufficient
```

**Decision in #120:** NO `get_artifact_schema` tool
- Agent always knows artifact type (it's an input parameter)
- If context is missing fields → error contains template schema
- No value in pre-flight query: agent has type, error gives schema

**Result:** Lazy discovery works perfectly for scaffolding!

### Issue #121: Content-Aware Editing

**Agent Workflow:**
```python
editFiles("/path/to/unknown.py", edits=[...])
# Agent receives file path (from human, search, workspace nav)
# → Agent does NOT know file type, template, or structure
# → Must discover: Is this scaffolded? What template? What capabilities?
```

**Problem:** Lazy discovery (errors) has limitations:
- Agent must attempt edit to discover capabilities (trial-and-error)
- Batch operations repeat discovery for each file
- Planning phase requires proactive knowledge

**Hypothesis:** Proactive discovery tool has value for editing scenarios where agent lacks context.

---

## Problem Analysis

### When Does Agent Lack File Context?

| Scenario | Agent Knowledge | Example |
|----------|----------------|---------|
| **Just scaffolded** | Knows template type from scaffold call | `scaffold_artifact("dto", ...) → editFiles("dto.py", ...)` |
| **Human provides path** | NO knowledge of template/structure | User: "Edit docs/design/feature-x.md to add dependency" |
| **Search results** | NO knowledge of specific files | Agent finds 5 DTO files via grep, wants to edit all |
| **Workspace navigation** | NO knowledge until file opened | Agent browses `backend/dtos/` directory |
| **Batch operations** | Could learn once, apply N times | Edit 10 DTO files with same structure |

**Key Finding:** Unlike scaffolding, editing workflows frequently operate on files without prior context!

### Limitations of Lazy Discovery (Errors Only)

**Scenario: Agent wants to add DTO field**

**WITHOUT proactive discovery:**
1. Agent attempts ScaffoldEdit (guessing capability)
   ```python
   editFiles("dto.py", [ScaffoldEdit.append_to_list("fields", "...")])
   ```
2. Error: "File structure unknown. Use TextEdit for this file."
3. Agent retries with TextEdit
   ```python
   editFiles("dto.py", [TextEdit.replace(...)])
   ```
4. **Total: 2 calls (1 failed attempt + 1 retry)**

**WITH proactive discovery:**
1. Agent queries schema first
   ```python
   schema = query_file_schema("dto.py")
   # Returns: {"template_id": "dto", "edit_capabilities": ["ScaffoldEdit", ...]}
   ```
2. Agent makes informed edit
   ```python
   editFiles("dto.py", [ScaffoldEdit.append_to_list("fields", "...")])
   ```
3. **Total: 2 calls (no retries!)**

**Observation:** Same number of calls, but proactive prevents failed attempts!

---

## Discovery Tool Rationale

### Why Discovery Tool is Valuable for #121

**1. Agent Context Gap**
- Scaffolding: Agent provides type → no gap
- Editing: Agent receives path → gap exists!

**2. Batch Efficiency**
- Scaffolding: N/A (scaffold = create, not batch edit)
- Editing: 1 query → N edits (for files of same template)

**3. Planning Capability**
- Scaffolding: Agent knows type, no planning needed
- Editing: Agent must decide TextEdit vs ScaffoldEdit strategy

**4. MCP Design Pattern**
- Resources (file schema) ≠ Tools (edit operations)
- Discovery via query, mutation via tool = clean separation

### Efficiency Analysis: Batch Editing Scenario

**Scenario:** Agent wants to edit 5 DTO files

**WITHOUT discovery tool (lazy):**
```python
# Trial-and-error for EACH file
editFiles("dto1.py", [...])  # Possible error → retry
editFiles("dto2.py", [...])  # Possible error → retry
editFiles("dto3.py", [...])  # Possible error → retry
editFiles("dto4.py", [...])  # Possible error → retry
editFiles("dto5.py", [...])  # Possible error → retry

# Worst case: 5 errors + 5 retries = 10 calls
# Best case: 5 successful edits = 5 calls
```

**WITH discovery tool (proactive):**
```python
# One-time discovery (template knowledge is reusable!)
schema = query_file_schema("dto1.py")  
# Returns: template_id="dto"

# Agent now knows ALL DTOs have same structure
editFiles("dto1.py", [...])  # Success
editFiles("dto2.py", [...])  # Success (same template!)
editFiles("dto3.py", [...])  # Success
editFiles("dto4.py", [...])  # Success
editFiles("dto5.py", [...])  # Success

# Total: 1 query + 5 edits = 6 calls (no retries!)
```

**Performance Comparison:**
- Lazy: 5-10 calls (depends on luck)
- Proactive: 6 calls (predictable)
- **Proactive wins when N > 1 file of same template!**

### Use Case Scenarios

**Scenario A: Single edit, agent has context**
```python
# Agent just scaffolded this file
scaffold_artifact("dto", ...)  # Agent knows: template="dto"
editFiles("dto.py", [ScaffoldEdit.append_to_list(...)])  # Informed edit

# Discovery: NOT NEEDED (agent has context)
```

**Scenario B: Single edit, agent lacks context**
```python
# Human: "Edit backend/dtos/signal.py to add symbol field"
# Agent does NOT know: Is this scaffolded? What template?

# Option 1: Lazy discovery (trial-and-error)
editFiles("signal.py", [ScaffoldEdit.append_to_list(...)])  # Might fail
# → Error: "File not scaffolded, use TextEdit"
editFiles("signal.py", [TextEdit.replace(...)])  # Retry

# Option 2: Proactive discovery (planning)
schema = query_file_schema("signal.py")  # Discover capabilities
editFiles("signal.py", [ScaffoldEdit.append_to_list(...)])  # Informed

# Discovery: VALUABLE (prevents failed attempt)
```

**Scenario C: Batch edit, same template**
```python
# Agent: "Find all DTO files and add created_at field"
# Agent found: dto1.py, dto2.py, dto3.py, ...

# Option 1: Lazy (repeat discovery N times)
editFiles("dto1.py", [...])  # Discover via error
editFiles("dto2.py", [...])  # Discover AGAIN (inefficient!)
# ...

# Option 2: Proactive (discover once, reuse)
schema = query_file_schema("dto1.py")  # Once!
# Agent learns: ALL DTOs have template="dto"
editFiles("dto1.py", [...])  # Apply
editFiles("dto2.py", [...])  # Apply (no discovery!)
# ...

# Discovery: EFFICIENT (1 query vs N errors)
```

---

## Design Decision

### Decision: Provide Optional Discovery with Lazy Fallback

**Implementation:**
1. ✅ **Discovery tool available:** `query_file_schema(path)` for proactive planning
2. ✅ **editFiles works standalone:** No dependency on discovery
3. ✅ **Errors contain schema:** Lazy discovery fallback
4. ✅ **Agent chooses strategy:** Based on context availability

**Tool Design:**
```python
# Tool 1: Discovery (optional helper)
query_file_schema(path: str) -> dict:
    """Return file type, template, structure, capabilities.
    
    OPTIONAL: Agent can skip and use lazy discovery via editFiles errors.
    VALUABLE: For batch operations, planning, context-free scenarios.
    """

# Tool 2: Editing (standalone)
editFiles(path: str, edits: List[Edit], mode: str) -> ToolResult:
    """Apply edits with auto-validation.
    
    STANDALONE: Works without query_file_schema.
    LAZY FALLBACK: Errors contain schema for discovery.
    """
```

**When Agent Should Use Which:**

| Scenario | Recommended Strategy | Rationale |
|----------|---------------------|-----------|
| Single edit + has context | Lazy (skip query) | No overhead needed |
| Single edit + NO context | Proactive (query first) | Prevent trial-and-error |
| Batch edit (N files) | Proactive (query once) | Efficiency: 1 query vs N errors |
| Planning phase | Proactive (query first) | Determine edit strategy |
| Exploratory work | Lazy (interactive mode) | Fast iteration |

**Key Difference from #120:**
- #120: Lazy ALWAYS works (agent has type)
- #121: Lazy SOMETIMES works (agent may lack type)
- **Solution:** Provide both, let agent choose!

---

## Implementation Strategy

### Pre-Phase 0: Standalone Discovery Tool (1-2 hours)

**Rationale:** Deliver discovery capability BEFORE editing infrastructure:
- Validate #120 integration early (TemplateIntrospector, ScaffoldMetadataParser)
- Enable agent experimentation with schema queries
- Foundation for batch editing patterns

**Deliverable:** Read-only `query_file_schema` tool

**Interface:**
```python
class QueryFileSchemaTool(BaseTool):
    """Get file schema for content-aware editing planning.
    
    Uses Issue #120 infrastructure:
    - ScaffoldMetadataParser: Read frontmatter metadata
    - TemplateIntrospector: Extract template schema
    
    Returns same schema format as scaffolding errors (consistency!).
    """
    
    async def execute(self, path: str) -> dict:
        # 1. Parse frontmatter (from #120 Phase 0)
        frontmatter = parse_yaml_frontmatter(text)
        
        if not frontmatter or "template" not in frontmatter:
            return {"file_type": "non-scaffolded", ...}
        
        # 2. Load template schema (from #120 Phase 1)
        introspector = TemplateIntrospector()  # Reuse #120!
        schema = introspector.get_schema(frontmatter["template"])
        
        # 3. Parse document structure
        structure = parse_document_structure(text, template_id)
        
        return {
            "file_type": "scaffolded",
            "template_id": template_id,
            "structure": structure,
            "template_schema": schema,  # ← Same schema as scaffolding!
            "edit_capabilities": [...]
        }
```

**Integration Points:**
- ✅ Reuses `ScaffoldMetadataParser` from #120 Phase 0
- ✅ Reuses `TemplateIntrospector` from #120 Phase 1
- ✅ Returns schema in same format as scaffolding errors
- ✅ No editing capability (read-only, safe to deploy early)

**Success Criteria:**
- Agent can query scaffolded files and get template metadata
- Schema format matches #120 error messages (consistency)
- Graceful degradation for non-scaffolded files
- Foundation for editFiles lazy fallback (errors use same schema)

### Phase 1-4: editFiles Implementation

**Lazy Discovery Fallback:**
```python
# editFiles errors MUST contain schema (lazy discovery)
if "ScaffoldEdit" in edit_types and file_type != "scaffolded":
    return ToolResult.error(
        f"ScaffoldEdit not available for {file_type} files.\n"
        f"Available capabilities: {capabilities}\n"
        f"Use query_file_schema() to check file structure, "
        f"or use TextEdit for raw editing."
    )
```

**Design Principle:** editFiles never REQUIRES query_file_schema, but benefits from it!

---

## Conclusion

### Summary of Findings

**Why #120 Doesn't Need Discovery Tool:**
- Agent provides artifact type as input parameter
- Lazy discovery (schema in errors) is always sufficient
- No context gap to fill

**Why #121 DOES Need Discovery Tool:**
- Agent receives file paths without context
- Batch editing benefits from reusable template knowledge
- Planning phase requires proactive capability detection

**Decision:** Implement `query_file_schema` as **optional helper** with **lazy fallback** via errors.

### Key Takeaways

1. **Context is king:** Scaffolding has it, editing often doesn't
2. **Batch efficiency matters:** 1 query → N edits scales better
3. **Optional > Required:** Lazy fallback ensures no forced overhead
4. **Consistency matters:** Same schema in queries and errors (reuse #120!)

### Next Steps

1. ✅ **Issue #121 updated** with Pre-Phase 0 and discovery rationale
2. ✅ **Research documented** in this file
3. → **Implement Pre-Phase 0:** Standalone `query_file_schema` tool
4. → **Validate integration:** Test with #120 infrastructure
5. → **Document patterns:** Agent best practices for discovery vs lazy

---

**Research Status:** ✅ COMPLETE  
**Decision:** Implement optional discovery tool with lazy fallback  
**Rationale:** Editing workflows fundamentally differ from scaffolding in agent context availability
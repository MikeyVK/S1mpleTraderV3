# Safe_Edit Tool Evaluation - Issue #54

**Date:** 2026-01-09  
**Author:** GitHub Copilot (Claude Sonnet 4.5)  
**Status:** DRAFT  
**Context:** Evaluating safe_edit tool usage during Issue #54 scaffold.yaml research

---

## Evaluation Context

User specifically requested evaluation of safe_edit tool during Issue #54 work:
> "Tijdens jouw gebruik van de mcp tools (met name safe edit) wil ik dat je het gebruik ervan evalueert, ik heb het idee dat de tool zou moeten voldoen, maar dat agents toch worstelen met het gebruik ervan"

**Hypothesis:** Tool should work well, but agents struggle with correct usage

**Test Case:** Updating research.md after scaffolding via generic template

---

## Test Attempts

### Attempt #1: Search/Replace Mode
**Method:** Full document replacement using search pattern  
**Result:** ❌ Failed

**Error:**
```
Pattern '# Issue #54 Research: Scaffold Rules Configuration

**Date:** 2026-01-09...' not found in file
```

**Problem:** Agent expected clean markdown structure but scaffolded template includes:
- HTML comment blocks (`<!-- GENERATED DOCUMENT -->`)
- Template metadata (Template: generic.md.jinja2)
- Different heading structure than expected

**Agent Assumption:** Scaffolded template would match expected markdown format  
**Reality:** Generic template has extensive boilerplate not visible during scaffolding call

### Attempt #2: Content Mode
**Method:** Full file replacement (no search pattern)  
**Result:** ✅ Success

**Approach:** Used `mode="strict"` with `content` parameter only (no search/replace)

---

## Observations

### ✅ What Worked
1. **Content mode for full rewrites** - Clean, single operation
2. **Scaffolding tool integration** - Directory structure created properly
3. **Diff preview** - Shows changes clearly (when successful)

### ❌ Challenges Identified
1. **Pattern matching sensitivity** - Whitespace/formatting must match exactly
2. **Template complexity** - Generic templates have hidden structure
3. **No feedback loop** - Agent can't see actual file content before edit attempt
4. **Search mode limitations** - No fuzzy matching or smart pattern detection

---

## Root Cause Analysis

**Why did search/replace fail?**

1. **Invisible template structure** - Agent calls `scaffold_design_doc()` → receives success message → assumes clean markdown
2. **No content preview** - Tool returns "Created generic document" without showing actual structure
3. **Pattern matching is literal** - Search string must match byte-for-byte including:
   - Whitespace (spaces, newlines)
   - HTML comments
   - Template metadata
   - Exact heading format

**Agent Workflow Gap:**
- Agent should read file first with `read_file` before attempting complex edits
- But this requires extra round-trip and isn't intuitive
- Search/replace seems like it should "just work" for simple text replacement

---

## Recommendations

### For Tool Improvement

1. **Add `read_first` parameter**
   - Tool optionally reads file before edit
   - Shows agent actual content for pattern matching
   - Single round-trip instead of two separate calls

2. **Improve search matching**
   - Support regex patterns for flexible matching
   - Fuzzy/approximate matching for similar text
   - Ignore leading/trailing whitespace option

3. **Better error messages**
   - Show portion of file where pattern was expected
   - Suggest similar text found in file
   - Indicate line number range to check

4. **Template-aware mode**
   - Special handling for scaffolded files
   - Detect template metadata and ignore for matching
   - Edit by section (markdown headings) instead of raw text

5. **Section-based editing**
   - For markdown: `edit_section="Epic Context"` → updates that heading
   - For code: `edit_function="my_function"` → updates that function
   - Smarter than text pattern matching

### For Agent Workflow

**Current (prone to failure):**
```
1. scaffold_design_doc() → success message
2. safe_edit(search="expected structure", replace=content) → ❌ pattern not found
3. read_file() → see actual structure
4. safe_edit(search="correct structure", replace=content) → ✅ works
```

**Improved workflow:**
```
1. scaffold_design_doc() → success message
2. read_file() → see actual structure  
3. safe_edit(search="correct structure", replace=content) → ✅ works
```

**Best workflow (with content mode):**
```
1. scaffold_design_doc() → success message
2. safe_edit(content=full_content) → ✅ works (no search)
```

---

## Impact on Issue #54

**For research phase:**
- ✅ Research document completed successfully (2 attempts total)
- ✅ Workaround identified: use content mode for full replacement
- ⚠️ Extra round-trip not needed if content mode used from start

**For future work:**
- Use content mode for document creation/updates
- Read files first before incremental edits
- Prefer full replacements over search/replace when practical
- Evaluate line_edits mode for surgical changes

---

## Conclusion

**Tool Assessment:** ✅ Tool works correctly as designed

**User Hypothesis Confirmed:** ❌ Agents do struggle with correct usage because:
1. Pattern matching requires exact text match (not intuitive)
2. No feedback about actual file structure after scaffolding
3. Search/replace mode seems simpler than it is
4. Content mode more reliable but not obvious choice

**Recommendation:** Agents should default to **content mode** for full file updates, reserve search/replace for well-understood existing files where exact text is known.

---

**End of Evaluation**
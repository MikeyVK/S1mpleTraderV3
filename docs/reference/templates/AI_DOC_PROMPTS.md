# docs/reference/templates/AI_DOC_PROMPTS.md

**Status:** APPROVED  
**Last Updated:** November 2025

---

## Purpose

Ready-to-use prompts for AI-assisted documentation tasks. Copy-paste these when working with AI assistants to ensure consistent, high-quality documentation output.

## Scope

**In scope:** Prompts for documentation creation, updates, and maintenance  
**Out of scope:** Code generation prompts → use IDE/Copilot directly

---

## When to Use AI for Documentation

### ✅ Good Uses

- Formatting existing notes into proper Markdown
- Expanding bullet points into paragraphs
- Creating examples based on code patterns
- Generating template boilerplate
- Checking grammar/clarity
- Cross-referencing related docs

### ❌ Bad Uses

- Inventing architectural decisions (AI hallucinates)
- Documenting code AI hasn't seen (outdated info)
- Creating docs without verifying against actual code
- Copy-pasting AI output without review

---

## AI Documentation Workflow

```
1. Capture Intent (Human)     → Quick notes while coding
2. Ask AI to Expand           → Use prompts below
3. Verify Against Code (Human)→ Check AI output matches implementation
4. Integrate + Link (Human)   → Add cross-references, commit with code
```

---

## Prompts

### 1. Create Reference Doc

```
I implemented {Component} in {file_path}. Create a reference doc 
following the structure in docs/reference/README.md. 
Include:
- Overview section
- Architecture context
- API reference (for services) OR Field details (for DTOs)
- Usage patterns
- Testing strategy
- Quality metrics

Base it on docs/reference/dtos/signal.md structure but adapt for this component.
```

**Context to provide:** Paste the implementation code so AI can accurately document fields, validators, and methods.

**Example:** 
```
I implemented RiskAssessment in backend/dtos/strategy/risk_assessment.py.

[paste code here]
```

### 2. Update Implementation Status

```
I just completed {Component} with {X} tests passing, all quality gates 10/10.
Update docs/implementation/IMPLEMENTATION_STATUS.md:
- Add row to the appropriate layer table (Strategy DTOs / Execution DTOs / Platform)
- Update test count totals
- Add to Recent Updates section

Table format:
| Component | Tests | G1 | G2 | G3 | G4 | G5 | Status |
|-----------|-------|----|----|----|----|----|---------|
| MyDTO     | 22/22 | 10 | 10 | 10 | 10 | 10 | ✅ Done |
```

**Context to provide:** First read IMPLEMENTATION_STATUS.md to match exact column structure.

**Example:** `I just completed RiskAssessment with 18 tests passing`

### 3. Split Oversized Document

```
docs/{path}/{file}.md is now {X} lines (over 300 line limit).
Split it into:
1. Overview doc (keep current filename)
2-N. Sub-topic docs (suggest logical splits)

Create an index section in the overview doc linking to sub-docs.
Preserve all content, just reorganize.
```

### 4. Cleanup Duplicates

```
I found the same {concept} explanation in:
- {file1}
- {file2}
- {file3}

Keep the FULL explanation only in {authoritative_file}.
Replace duplicates with links: "See [{filename}]({relative_path})"
```

### 5. Convert Notes to First-Version Framing

```
Convert these implementation notes to documentation with first-version framing.
Remove any "previously we did X" or "changed from Y to Z" language.
Write as if this IS the authoritative first version.

Notes:
{paste your notes here}
```

### 6. Review Architecture Doc Against Code

```
Review this architecture document against the actual implementation.

Document: docs/architecture/{doc}.md
Implementation files:
- {file1}
- {file2}

Check for:
- Outdated terminology or field names
- Missing components that now exist
- Described patterns that differ from implementation
- Diagrams that don't match current flow

Provide specific corrections with line references.
```

**Context to provide:** Paste both the doc content AND the relevant code sections.

### 7. Cross-Reference Check

```
I created/updated docs/{path}/{new_doc}.md about {topic}.

Find all existing docs that:
1. Should LINK TO this new doc (they mention {topic} without linking)
2. Should BE LINKED FROM this doc (related concepts)

Search in:
- docs/architecture/
- docs/coding_standards/
- docs/reference/

Provide specific suggestions: "In {file}.md line X, add link to {new_doc}"
```

---

## Related Documentation

- [Template README](README.md) - Template selection guide
- [BASE_TEMPLATE.md](BASE_TEMPLATE.md) - Document structure
- [DOCUMENTATION_MAINTENANCE.md](../../DOCUMENTATION_MAINTENANCE.md) - Meta-rules
- [signal.md](../dtos/signal.md) - Reference DTO example

---

## Version History

| Version | Date | Changes |
|---------|------|---------|  
| 1.0 | 2025-11-27 | Initial creation, extracted from DOCUMENTATION_MAINTENANCE.md |

<!-- ═══════════════════════════════════════════════════════════════════════════
     LINK DEFINITIONS (hidden in rendered view, visible when editing)
     ═══════════════════════════════════════════════════════════════════════════ -->

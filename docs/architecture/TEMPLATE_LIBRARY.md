<!-- docs/architecture/TEMPLATE_LIBRARY.md -->
<!-- template=architecture version=8b924f78 created=2026-02-07T00:00Z updated= -->
# Template Library Architecture - S1mpleTraderV3

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-07

---

## Purpose

Define the architecture of the multi-tier Jinja2 template library used by the MCP scaffolding system: what the tiers mean, how composition works (`{% extends %}` vs `{% import %}` macro libraries), how provenance is tracked via version hashes, and how schema introspection works across an inheritance chain.

## Scope

**In Scope:**
['Tier model (Tier 0→3 + concrete) and rationale', 'Enforcement intent per tier (STRICT vs ARCHITECTURAL vs GUIDELINE)', 'Block-library composition using Jinja macro imports', 'Provenance tracking via `.st3/template_registry.json`', 'Inheritance-aware template introspection concept']

**Out of Scope:**
['Validation rule authoring details → See docs/reference/mcp/template_metadata_format.md', 'End-to-end scaffolding API usage → See docs/reference/mcp/TEMPLATE_LIBRARY_USAGE.md']

## Prerequisites

Read these first:
1. docs/development/issue72/research_summary.md (Issue #72 key decisions)
2. docs/development/issue72/planning.md (SSOT plan)
---


## 1. Core Model: 5-Level Hierarchy

The template library is split into orthogonal tiers so changes remain localized: Tier 0 (universal lifecycle metadata), Tier 1 (format structure), Tier 2 (language/syntax), Tier 3 (architectural patterns), and concrete templates (artifact-specific output).

---


## 2. Enforcement Intent by Tier

The library expresses enforcement intent via TEMPLATE_METADATA.enforcement: tiers 0–2 are STRICT foundations, tier 3 patterns are ARCHITECTURAL, concrete templates are GUIDELINE.

---


## 3. Two Kinds of Composition

Stable, layered bases use `{% extends %}`; optional architectural patterns are composed by importing Tier 3 macro libraries via `{% import %}` and calling macros at merge points.

---


## 4. Provenance & Version Hashing

Scaffolded artifacts embed a compact SCAFFOLD header containing a short version_hash. `.st3/template_registry.json` maps version_hash to the full tier chain (template_id@version per tier).

---


## 5. Inheritance-Aware Introspection

Schema extraction must walk the full `{% extends %}` chain, parse each template AST, union undeclared variables, filter system fields, and classify required vs optional fields. Macro import aliases must be excluded from agent variables.

---


## 6. Decision Tree: Where Does This Belong?

Rule-of-thumb placement: Tier 0 for universal provenance; Tier 1 for format structure; Tier 2 for language syntax; Tier 3 for composable patterns; concrete for artifact-specific details.

---

## Related Documentation
- **[docs/development/issue72/planning.md][related-1]**
- **[docs/development/issue72/research_summary.md][related-2]**
- **[docs/reference/mcp/template_metadata_format.md][related-3]**
- **[docs/reference/mcp/TEMPLATE_LIBRARY_USAGE.md][related-4]**
- **[docs/reference/mcp/TEMPLATE_LIBRARY_PATTERNS.md][related-5]**

<!-- Link definitions -->

[related-1]: docs/development/issue72/planning.md
[related-2]: docs/development/issue72/research_summary.md
[related-3]: docs/reference/mcp/template_metadata_format.md
[related-4]: docs/reference/mcp/TEMPLATE_LIBRARY_USAGE.md
[related-5]: docs/reference/mcp/TEMPLATE_LIBRARY_PATTERNS.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-07 | Agent | Initial draft |
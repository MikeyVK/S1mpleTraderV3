<!-- D:\dev\SimpleTraderV3\test_renders\research-jinja2-composition-example.md -->
<!-- template=research version=8b7bb3ab created=2026-02-05T22:06Z updated= -->
# jinja2-composition-patterns-research

**Status:** COMPLETED  
**Version:** 1.0  
**Last Updated:** 2026-02-05

---

## Purpose

Investigate Jinja2 composition patterns for template library refactoring. Understand extends, include, import, and block override mechanics.

## Scope

**In Scope:**
Jinja2 inheritance, macro composition, block override, whitespace control. Multi-tier patterns.

**Out of Scope:**
No implementation. No code gen. No performance benchmarks. No alternative engines.

## Prerequisites

Read these first:
1. Jinja2 template inheritance docs
2. Block override resolution understanding
3. tier0-tier3 structure review
---

## Problem Statement

How to inject tier3 pattern macros into tier1 base_document blocks? Need pattern for overriding blocks in concrete templates to achieve compositie parity with CODE-tak.

## Research Goals

- Identify best pattern for tier3 macro injection into tier1 blocks
- Determine whitespace stripping rules for clean markdown output
- Document trade-offs between {% include %} vs {% import %} approaches

---

## Background

Current architecture has 4-tier template system (tier0 base artifact, tier1 base document, tier2 base markdown, tier3 patterns). CODE-tak already uses pattern injection successfully (dto.py.jinja2 overrides imports_block/class_block with tier3 pattern calls). DOCUMENT-tak only used patterns for header, rest defaulted to tier1 hardcoded content.

---

## Findings

**Jinja2 Block Override Mechanics:**
- Child templates can override parent blocks with `{% block name %}...{% endblock %}`
- Concrete template (planning.md) extends tier2 → tier1 → tier0 chain
- Block defined in concrete template wins (overrides tier1 default)
- Patterns imported via `{% import "pattern.jinja2" as alias %}` provide macros
- Macros called in block override: `{% block purpose_section %}{{ ps.pattern_purpose_section(purpose) }}{% endblock %}`

**Whitespace Control Critical Rules:**
- `{%- block %}` strips whitespace BEFORE block
- `{% block -%}` strips whitespace AFTER block opening
- `{%- endblock -%}` strips whitespace BEFORE and AFTER block closing
- Comments `{#- -#}` also strip whitespace
- Missing strip on divider caused `---## Version History` bug (fixed by moving comment inside block)

**Pattern Injection Best Practice:**
- tier1 defines composable blocks with default content
- tier3 patterns define macros with parameterized content
- Concrete templates override blocks with pattern macro calls
- This achieves "merge-point driven" architecture where patterns determine output

**Trade-off Analysis:**
- `{% include %}`: Inlines template, cannot pass complex data easily
- `{% import %}`: Creates namespace, clean macro calls, better for parameterized patterns
- **Recommendation**: Use `{% import %}` for all tier3 patterns (already implemented)

## Open Questions

- **Q1:** Should tier1 blocks have NO default content to force concrete templates to override?
- Context: Currently tier1 has hardcoded defaults for backward compatibility. Could make blocks empty to enforce discipline.
- **Q2:** How to handle optional sections (e.g., prerequisites) - empty block or conditional?
- Context: tier3 patterns have if checks ({% if prereqs %}). Should tier1 also have conditional, or rely on pattern?


## Related Documentation
- **[https://jinja.palletsprojects.com/en/3.1.x/templates/#template-inheritance][related-1]**
- **[docs/architecture/template-library-architecture.md][related-2]**
- **[mcp_server/scaffolding/templates/tier1_base_document.jinja2][related-3]**

<!-- Link definitions -->

[related-1]: https://jinja.palletsprojects.com/en/3.1.x/templates/#template-inheritance
[related-2]: docs/architecture/template-library-architecture.md
[related-3]: mcp_server/scaffolding/templates/tier1_base_document.jinja2

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-05 | Agent | Initial draft |
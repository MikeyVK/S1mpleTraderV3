# docs/reference/templates/BASE_TEMPLATE.md
# {Document Title} - S1mpleTraderV3

<!--
BASE TEMPLATE - All documentation inherits from this structure
Version: 2.0

USAGE:
1. Copy this template OR a type-specific template (ARCHITECTURE/DESIGN/REFERENCE)
2. Replace all {placeholders} with actual content
3. Update the filepath comment on line 1
4. Delete sections marked [OPTIONAL] if not applicable
5. Keep all REQUIRED sections - they ensure consistency
6. Add type-specific sections at the marked location
7. Add link definitions to footer as you add references

INHERITANCE:
- ARCHITECTURE_TEMPLATE extends this with: numbered sections, diagrams, no code
- DESIGN_TEMPLATE extends this with: design options, decisions, approval
- REFERENCE_TEMPLATE extends this with: API reference, source links, examples
-->

<!-- ═══════════════════════════════════════════════════════════════════════════
     HEADER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

**Status:** {DRAFT | PRELIMINARY | APPROVED | DEFINITIVE}  
**Version:** {X.Y}  
**Last Updated:** {YYYY-MM-DD}  

<!-- TYPE-SPECIFIC HEADER FIELDS:
     Design: add Created, Implementation Phase
     Reference: add Source, Tests
-->

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTEXT SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Purpose

{One paragraph (2-4 sentences) describing:
- What this document covers
- Why it exists (the problem it solves or decision it captures)
- Who should read it (target audience)}

## Scope

**In Scope:**
- {Topic this document covers}
- {Another topic covered}

**Out of Scope:**
- {Topic NOT covered} → See [{OTHER_DOC.md}][other-doc]
- {Another exclusion} → See [{ANOTHER_DOC.md}][another-doc]

## Prerequisites

[OPTIONAL - delete entire section if no prior reading required]

Read these first:
1. [{REQUIRED_DOC_1.md}][prereq-1] - {brief reason why needed}
2. [{REQUIRED_DOC_2.md}][prereq-2] - {brief reason why needed}

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTENT SECTION (REQUIRED - structure varies by type)
     ═══════════════════════════════════════════════════════════════════════════ -->

<!-- TYPE-SPECIFIC CONTENT:
     ARCHITECTURE: Numbered conceptual sections (## 1. Concept, ### 1.1 Detail)
     DESIGN: Numbered decision sections (## 1. Context, ## 2. Options, ## 3. Decision)
     REFERENCE: Unnumbered API sections (## API Reference, ## Usage Examples)
-->

## {First Main Section}

{Content...}

### {Subsection}

{Content...}

---

## {Second Main Section}

{Content...}

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     FOOTER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Related Documentation

- **[{DOC_NAME.md}][related-1]** - {brief description}
- **[{DOC_NAME.md}][related-2]** - {brief description}

<!-- Link definitions (automatically hidden in rendered output) -->

[other-doc]: ./path/to/other.md "Description"
[another-doc]: ./path/to/another.md "Description"
[prereq-1]: ./path/to/prereq1.md "Description"
[prereq-2]: ./path/to/prereq2.md "Description"
[related-1]: ./path/to/related1.md "Description"
[related-2]: ./path/to/related2.md "Description"

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| {X.Y} | {YYYY-MM-DD} | {Name/AI} | {Brief description of changes} |
| 1.0 | {YYYY-MM-DD} | {Name/AI} | Initial document |

<!-- ═══════════════════════════════════════════════════════════════════════════
     TEMPLATE REFERENCE (delete when using)
     ═══════════════════════════════════════════════════════════════════════════

REQUIRED SECTIONS (never delete):
├── Header: Status, Version, Last Updated
├── Purpose
├── Scope (In Scope / Out of Scope)
├── Content (minimum one ## section)
├── Related Documentation
├── Link definitions
└── Version History

OPTIONAL SECTIONS:
├── Prerequisites (delete if no prior reading needed)
└── Type-specific additions (at marked locations)

HEADING CONVENTIONS:
├── # (H1): Document title only (once)
├── ## (H2): Main sections
├── ### (H3): Subsections
└── #### (H4): Details (use sparingly, max depth)

SECTION NUMBERING:
├── Architecture: Numbered (## 1. Section)
├── Design: Numbered (## 1. Context)
└── Reference: Unnumbered (## API Reference)

STATUS LIFECYCLE:
DRAFT → PRELIMINARY → APPROVED → DEFINITIVE
  │         │            │           │
  │         │            │           └── Reflects reality
  │         │            └── Ready for implementation
  │         └── Complete, pending review
  └── Work in progress, may have [TODO]

SRP FOR DOCUMENTATION:
├── Architecture: No code (link to source)
├── Design: Illustrative code only
└── Reference: Working code examples

═══════════════════════════════════════════════════════════════════════════ -->

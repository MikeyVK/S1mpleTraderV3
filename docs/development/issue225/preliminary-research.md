<!-- docs\development\issue225\preliminary-research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-19T05:56Z updated= -->
# V1 Pipeline Removal: Inventory & Migration Strategy

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-19

---

## Purpose

Provide a complete, ordered inventory that drives the TDD cycle for issue #225 without surprises mid-cycle.

## Scope

**In Scope:**
mcp_server/managers/artifact_manager.py V1 code paths, all test files with PYDANTIC_SCAFFOLDING_ENABLED or _force_v1_pipeline, all docs outside docs/development/issue135/ that mention V1/V2/feature flag

**Out of Scope:**
Adding V2 templates for artifact types beyond dto, changes to Pydantic schema definitions, issue #178 (test_cases field)

## Prerequisites

Read these first:
1. Issue #135 merged (V2 pipeline complete)
2. Full test suite green on main
---

## Problem Statement

The V1 dict-based pipeline in ArtifactManager co-exists with the V2 Pydantic-validated pipeline. V2 is now the default and covers all 16 artifact types. The V1 code path adds ~160 lines of conditional complexity, 13 test files carry dual V1/V2 test cases, and documentation still describes a feature flag that should no longer exist. Before writing a single line of refactor code we need a complete inventory of what touches V1, and a clear migration strategy per category.

## Research Goals

- Enumerate every V1 reference in mcp_server/ code with file + line
- Enumerate every V1 reference in tests/ with file + class + method
- Enumerate every V1 reference in docs/ outside docs/development/issue135/
- Determine per test file: delete vs rewrite (specifying new V2 context shapes)
- Specify final signature of _enrich_context() after V1 removal
- Confirm no other callers of _enrich_context() exist outside ArtifactManager
- Identify any V1 context shapes still used by the hermetic test harness (fixtures/artifact_test_harness.py) and plan their replacement

## Related Documentation
- **[docs/reference/schema-template-maintenance.md][related-1]**
- **[mcp_server/managers/artifact_manager.py][related-2]**
- **[tests/fixtures/artifact_test_harness.py][related-3]**

<!-- Link definitions -->

[related-1]: docs/reference/schema-template-maintenance.md
[related-2]: mcp_server/managers/artifact_manager.py
[related-3]: tests/fixtures/artifact_test_harness.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |
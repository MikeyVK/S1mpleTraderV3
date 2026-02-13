<!-- docs/development/issue108/design.md -->
<!-- template=design version=5827e841 created=2026-02-13T15:00:00Z updated= -->
# Issue #108: JinjaRenderer Extraction - Design

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-13

---

## Purpose

Document implementation design decisions for extracting JinjaRenderer to backend/services/template_engine.py, including API design, migration strategy, and test approach.

## Scope

**In Scope:**
Module structure, class API design, import strategy, test organization, migration execution plan

**Out of Scope:**
Research justification (see research.md), TDD cycle details (see planning.md), Phase 2 features (mock rendering, ChoiceLoader)

## Prerequisites

Read these first:
1. research.md v1.4 approved - MVP scope defined
2. planning.md v1.0 approved - 6 TDD cycles defined (0-5)
---

## 1. Context & Requirements

### 1.1. Problem Statement

Current JinjaRenderer location (mcp_server/scaffolding/renderer.py) creates circular dependency preventing tools/ from using template rendering. Need to extract to backend/services/ while maintaining 100% behavioral compatibility with existing scaffolding system (40 tests, 6 import sites). MVP scope: Single template root via get_template_root(), FileSystemLoader support, custom filters. No backward compatibility layer needed - direct migration.

### 1.2. Requirements

**Functional:**
- [ ] TemplateEngine class in backend/services/template_engine.py with identical API to JinjaRenderer
- [ ] Accept template_root parameter (Path or str) for single root configuration
- [ ] Support FileSystemLoader for 5-tier template inheritance (tier0→tier1→tier2→tier3→concrete)
- [ ] Provide custom filters: pascalcase, snakecase, kebabcase, validate_identifier
- [ ] Render method accepting template name + context dict, returning rendered string
- [ ] Proper error handling for missing templates (TemplateNotFound)
- [ ] Import only from: backend/, stdlib, third-party (NO mcp_server/ imports)

**Non-Functional:**
- [ ] 100% type coverage (mypy --strict passes)
- [ ] Module docstring with @layer, @dependencies, @responsibilities
- [ ] All 40 existing scaffolding tests pass without modification (except imports)
- [ ] Byte-identical output validation via Cycle 0 baselines
- [ ] Test coverage ≥90% maintained
- [ ] Zero circular dependencies (validated in Cycle 1 tests)
- [ ] All 7 quality gates pass (Format, Lint, Import Placement, Line Length, Type Checking, Tests, Coverage)

### 1.3. Constraints

**Immutability Constraint:** Existing scaffolding output must be byte-identical (no behavior changes). **Import Constraint:** TemplateEngine cannot import from mcp_server/ (would recreate circular dependency). **Compatibility Constraint:** No compatibility layer - JinjaRenderer will be deleted in Cycle 5.
---

## 2. Design Options

### 2.1. Option A: Direct Copy + Rename

Copy mcp_server/scaffolding/renderer.py to backend/services/template_engine.py, rename JinjaRenderer → TemplateEngine, fix imports.

**Pros:**
- ✅ Minimal code changes (proven stable code)
- ✅ Byte-identical output guaranteed (same logic)
- ✅ Fast implementation (copy + rename + test)
- ✅ Low risk (no behavioral changes)

**Cons:**
- ❌ Carries over any existing technical debt
- ❌ No opportunity to improve code structure
- ❌ May include unused code (if any)

### 2.2. Option B: Clean Reimplementation

Rewrite template engine from scratch with fresh design, using JinjaRenderer as specification.

**Pros:**
- ✅ Opportunity to improve code structure
- ✅ Remove any technical debt
- ✅ Modern design patterns from start

**Cons:**
- ❌ High risk of introducing behavioral changes
- ❌ Byte-identical output hard to guarantee
- ❌ Significantly more time investment
- ❌ Complex regression testing required
- ❌ Violates MVP scope (extraction, not refactor)

### 2.3. Option C: Gradual Decomposition

Extract JinjaRenderer in stages: first move, then refactor internal structure in follow-up issues.

**Pros:**
- ✅ Separates extraction risk from refactor risk
- ✅ Each stage independently testable
- ✅ Easier to isolate regression sources

**Cons:**
- ❌ Extends timeline (multiple PRs)
- ❌ Intermediate states may be suboptimal
- ❌ More coordination overhead
---

## 3. Chosen Design

**Decision:** Option A: Direct Copy + Rename

**Rationale:** MVP scope is extraction to break circular dependency, not code improvement. Direct copy guarantees byte-identical output (lowest risk), passes all 40 existing tests without modification, and enables fastest delivery. Any code improvements can be addressed in follow-up issues after extraction is stable. Research phase explicitly stated 'no backward compatibility' means no compatibility layer needed - clean migration.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Module path: backend/services/template_engine.py | Services layer appropriate for reusable utilities. Backend/ prefix ensures no mcp_server/ imports (breaks circular dependency). Follows backend/ → services/ convention. |
| Class name: TemplateEngine (not JinjaRenderer) | Rename signals new location and avoids confusion. 'Engine' implies broader applicability (future Phase 2 features). Clear break from old import path. |
| Single template root via get_template_root() | MVP scope - YAGNI principle. Multi-root (ChoiceLoader) deferred to Phase 2. Simplifies initial extraction, reduces risk. Current scaffolding only needs single root. |
| FileSystemLoader only (no ChoiceLoader) | Supports existing 5-tier inheritance (tier0→tier1→tier2→tier3→concrete). ChoiceLoader not needed for MVP (Issue #72 compatibility requires single root only). Phase 2 work. |
| Cycle 0: Baseline capture BEFORE migration | Immutable reference point for byte-identical validation. Captures current output before any changes. Enables Cycle 4 regression tests to prove zero behavioral change. |
| Import migration: 2 production + 4 test files | Research identified exact 6 sites. Split into Cycle 2 (production: base.py, template_scaffolder.py) and Cycle 3 (tests) for isolation. Production first ensures core stability. |
| Test organization: tests/unit/services/test_template_engine.py | Mirrors backend/services/ structure. Isolated unit tests (5 tests in Cycle 1) validate TemplateEngine before integration with existing scaffolding. |
| Regression strategy: 8 scenarios (5 templates + 3 structural) | Cycle 4 regression suite covers: dto/worker/tool/research/planning templates (output validation) + 5-tier inheritance/custom filters/SCAFFOLD metadata (structural validation). Validates against Cycle 0 baselines. |
| Legacy cleanup: Delete renderer.py in Cycle 5 | No compatibility layer per research decision. Clean migration: all 6 sites updated, tests green, then delete old module. Cycle 5 test validates ImportError on old path (RED discipline). |
| Quality gates: All 7 gates enforced | Cycle 1 REFACTOR phase runs: ruff format/check, mypy --strict, import order, line length, pytest (5 tests), coverage ≥90%. Ensures production quality before integration. |

## Related Documentation
- **[research.md - Research findings justifying extraction][related-1]**
- **[planning.md - TDD cycle breakdown (Cycle 0-5)][related-2]**
- **[../../coding_standards/TYPE_CHECKING_PLAYBOOK.md - Type checking standards][related-3]**

<!-- Link definitions -->

[related-1]: research.md - Research findings justifying extraction
[related-2]: planning.md - TDD cycle breakdown (Cycle 0-5)
[related-3]: ../../coding_standards/TYPE_CHECKING_PLAYBOOK.md - Type checking standards

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-13 | Agent | Initial draft |
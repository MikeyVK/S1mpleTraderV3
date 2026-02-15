<!-- D:\dev\SimpleTraderV3-parallel\docs\development\issue135\planning-pydantic-v2.md -->
<!-- template=planning version=130ac5ea created=2026-02-15T17:30:00Z updated=2026-02-15T17:45:00Z -->
# Issue #135 Pydantic-First v2 Planning

**Status:** DRAFT  
**Version:** 1.2  
**Last Updated:** 2026-02-15

---

## Purpose

Plan migration timeline, parity testing strategy, and feature flag implementation for Pydantic-First architecture that eliminates 78× defensive template patterns

## Scope

**In Scope:**
Migration phases (DTO pilot → code → docs → tests → integration → documentation), TDD cycles (7 cycles: parity framework → schemas → pilot → feature flag → code artifacts → doc artifacts → test artifacts), integration testing (pilot deployment, performance benchmarking, production scenarios), documentation deliverables (migration guide, runbooks, technical debt register), GATE 2 rationale (Naming Convention decision), schema registry structure, quality gates 0-6 enforcement

**Out of Scope:**
Implementation code examples (design phase), class diagrams (design phase), template simplification syntax (design phase)

## Prerequisites

**Source Document Verification:**
- Research document: `research-pydantic-v2.md` v1.8 (Status: COMPLETE - All 3 gates resolved)
- Last verified: 2026-02-15
- GATE 1 ✅ RESOLVED: System-managed lifecycle (Context + RenderContext pattern)
- GATE 2 ✅ RESOLVED: Naming Convention (zero maintenance, DRY)
- GATE 3 ✅ RESOLVED: 19 Tier 3 macros analyzed (OUTPUT formatters), 3 pending

**Required Reading:**
1. [research-pydantic-v2.md v1.8](research-pydantic-v2.md) - Complete architecture research with all gates resolved
2. [docs/coding_standards/QUALITY_GATES.md](../../coding_standards/QUALITY_GATES.md) - Gates 0-6 enforcement standards

---

## Summary

Migration plan for Pydantic-First v2 architecture addressing Issue #135 template introspection metadata SSOT violation. Defines 5-phase workflow (research → planning → tdd → integration → documentation) with 7 TDD cycles covering all 17 non-ephemeral artifacts (DTO: 1, Code: 8, Docs: 6, Tests: 2), integration pilot deployment (2 weeks), and complete documentation deliverables (migration guide, runbooks, technical debt register). Parity testing strategy ensures output equivalence validation. Feature flag pattern enables gradual rollout (pilot → team → production). GATE 2 rationale documents Naming Convention over Registry decision. Eliminates 78× defensive template patterns through schema-first validation. Quality gates 0-6 enforced for all schema files (34 total: 17 Context + 17 RenderContext).

---

## Migration Timeline

### Phase 1: Foundation & Pilot (Week 1-2)
**Goal:** Establish parity testing framework and validate architecture with DTO pilot

**Deliverables:**
1. **Parity Test Infrastructure**
   - Output equivalence validator (normalize whitespace/imports)
   - Error case validator (v1 vs v2 error message mapping)
   - Performance baseline (v1 template render times)
   
2. **Core Schema Components**
   - `LifecycleMixin` (4 fields: output_path, scaffold_created, template_id, version_hash)
   - `BaseContext` (empty base class for type hints)
   - `BaseRenderContext` (LifecycleMixin + BaseContext)

3. **DTO Pilot Migration**
   - `DTOContext` schema (17 fields from current template introspection)
   - `DTORenderContext` (DTOContext + LifecycleMixin via inheritance)
   - Simplified `dto.py.jinja2` v2 template (remove 41× `| default` patterns)
   - Parity tests: v1 vs v2 output equivalence for 10 test cases

**Success Criteria:**
- ✅ All 10 DTO pilot test cases pass (bit-for-bit output equivalence after normalization)
- ✅ v2 template character count reduction: 106 → 36 chars on line 95
- ✅ Zero validation errors when rendering with validated DTOContext
- ✅ Quality Gates 0-6 pass for all pilot Python files (LifecycleMixin, DTOContext, DTORenderContext, parity test framework)
  - Gate 0: Ruff Format
  - Gate 1: Ruff Strict Lint
  - Gate 2: Import Placement
  - Gate 3: Line Length (<100 chars)
  - Gate 4: Type Checking (mypy strict)
  - Gate 5: Tests Passing (100%)
  - Gate 6: Code Coverage (≥90%)

**Exit Criteria:**
- Stakeholder approval on pilot results
- Parity test framework accepted as validation standard
- Quality gates 0-6 enforced and passing (establishes standard for remaining phases)

---

### Phase 2: Code Artifacts (Week 3-4)
**Goal:** Migrate remaining 8 code artifact types from artifacts.yaml registry

**Deliverables:**
1. **Context Schemas (8 types)**
   - WorkerContext, AdapterContext, ServiceContext, InterfaceContext
   - ToolContext, ResourceContext, SchemaContext, GenericContext

2. **RenderContext Classes (8 types)**
   - All inherit from respective Context + LifecycleMixin
   - Follow Naming Convention: `WorkerContext` → `WorkerRenderContext`

3. **Template Simplification**
   - Remove defensive patterns from 8 v2 concrete templates
   - Estimated reduction: 41 total defaults across code templates

4. **Parity Testing**
   - 5-10 test cases per artifact type (minimum 40 total tests)
   - Cover: happy path, edge cases (empty lists, optional fields), error cases

**Success Criteria:**
- ✅ 100% parity test pass rate (output equivalence)
- ✅ Character count reduction measured and documented per template
- ✅ No regression in error handling (v2 schema validation ≥ v1 `| default` robustness)
- ✅ Quality Gates 0-6 pass for all 8 context schemas + 8 render context schemas (16 files total)

---

### Phase 3: Document Artifacts (Week 5)
**Goal:** Migrate 6 document artifact types from artifacts.yaml registry

**Deliverables:**
1. **Document Context Schemas (6 types)**
   - ResearchContext, PlanningContext, DesignContext
   - ArchitectureContext, TrackingContext, ReferenceContext

2. **Template Simplification**
   - Remove defensive patterns from 6 markdown templates
   - Estimated reduction: 22 total defaults across doc templates

3. **Parity Testing**
   - 3-5 test cases per document type (minimum 18 total tests)
   - Focus: section structure, metadata fields, markdown formatting

**Success Criteria:**
- ✅ 100% parity test pass rate
- ✅ Markdown structure preserved (headers, links, tables)
- ✅ Document metadata complete (version, timestamp, related_docs)
- ✅ Quality Gates 0-3 pass for all markdown templates (Gate 4-6 not applicable to docs)

---

### Phase 4: Test Artifacts (Week 6)
**Goal:** Migrate 2 test artifact types (unit_test, integration_test) from artifacts.yaml registry

**Deliverables:**
1. **Test Context Schemas (2 types)**
   - UnitTestContext, IntegrationTestContext

2. **RenderContext Classes (2 types)**
   - All inherit from respective Context + LifecycleMixin
   - Follow Naming Convention: `UnitTestContext` → `UnitTestRenderContext`

3. **Template Simplification**
   - Remove defensive patterns from test templates (if applicable)
   - Focus: test structure, fixture imports, assertion patterns

4. **Parity Testing**
   - 5 test cases per artifact type (minimum 10 total tests)
   - Cover: test method structure, fixture usage, parametrization

**Success Criteria:**
- ✅ 100% parity test pass rate (10+ tests)
- ✅ Test template structure preserved (pytest patterns)
- ✅ Quality Gates 0-6 pass for 2 test context schemas + 2 render context schemas (4 files total)

**Migration Completion:**
- **Total artifacts migrated:** 17 non-ephemeral (DTO: 1, Code: 8, Docs: 6, Tests: 2)
- **Phase 1-4 coverage:** 100% of non-ephemeral artifacts from artifacts.yaml
- **Ready for Integration Phase:** All 34 schema files (17 Context + 17 RenderContext) implemented

---

**Migration Timeline Summary:**
- **Week 1-2:** Phase 1 (Foundation + DTO pilot)
- **Week 3-4:** Phase 2 (8 code artifacts)
- **Week 5:** Phase 3 (6 document artifacts)
- **Week 6:** Phase 4 (2 test artifacts)
- **Week 7-8:** Integration Phase (pilot deployment, performance benchmarking, production scenarios - see Integration Phase section below)
- **Week 9-10:** Documentation Phase (migration guide, runbooks, technical debt register - see Documentation Phase section below)

---

---

## Parity Testing Strategy

### Equivalence Rules
**Goal:** Define when v1 and v2 outputs are "equivalent" despite minor differences

**Normalization Rules:**
1. **Whitespace:** Strip trailing whitespace, normalize line endings (CRLF → LF)
2. **Imports:** Sort import statements alphabetically (preserve grouping)
3. **Docstrings:** Ignore indentation differences (preserve content)
4. **Comments:** Preserve content, ignore alignment
5. **Timestamps:** Mask dynamic values (scaffold_created, version_hash)

**Exclusions:**
- Character-level differences OK if semantic meaning unchanged
- Comment formatting differences acceptable
- Blank line count differences (1 vs 2 blank lines) acceptable

### Test Suite Structure

```
tests/parity/
├── conftest.py                    # Shared fixtures (v1_renderer, v2_renderer)
├── normalization.py               # Output normalizer utilities
├── test_dto_parity.py            # 10 test cases
├── test_worker_parity.py         # 10 test cases
├── test_adapter_parity.py        # 5 test cases
├── ... (13 code artifact test files)
├── test_research_parity.py       # 5 test cases
├── ... (8 doc artifact test files)
└── test_edge_cases.py            # 10 edge/error test cases
```

### Error Case Handling
**Challenge:** v1 uses `| default`, v2 uses Pydantic validation errors

**Strategy:**
1. **Map v1 silent failures → v2 explicit errors**
   - v1: Missing field → render empty string → broken output
   - v2: Missing field → Pydantic ValidationError → clear error message
   
2. **Error equivalence validation**
   - v1 broken output → v2 ValidationError = ACCEPTABLE (improvement)
   - v1 working output → v2 ValidationError = REGRESSION (fix required)

3. **Test case categorization**
   - Happy path: v1 ≡ v2 (bit-for-bit after normalization)
   - Error case: v1 broken, v2 ValidationError (improvement documented)
   - Edge case: v1 ≡ v2 (lists, optionals, nested objects)

---

## Feature Flag Architecture

### Implementation Pattern

**ArtifactManager Routing Logic:**

```
# Conceptual pseudo-code (actual implementation in design phase)

IF environment_variable("PYDANTIC_SCAFFOLDING_ENABLED") == "true":
    use_v2_pipeline()
ELSE:
    use_v1_pipeline() # Current introspection-based system
```

**Decision Point:** `ArtifactManager.scaffold()` method

**Routing Options:**
1. **v1 Pipeline (Current):**
   - Introspect template via `TemplateEngine.get_template_variables()`
   - USER provides context dict
   - Template validates with `| default` filters
   
2. **v2 Pipeline (Pydantic-First):**
   - Lookup Context schema class from registry (`artifact_type → WorkerContext`)
   - Validate USER context → `WorkerContext.model_validate(user_context)`
   - Enrich validated context → `WorkerRenderContext` (add lifecycle fields)
   - Render simplified template (no `| default` needed)

**Rollout Phases:**
1. **Week 1-5:** Feature flag OFF (development/testing only, manual activation)
2. **Week 6-7:** Feature flag ON for team (pilot group, 2-week trial)
3. **Week 8:** Metrics review → Go/No-Go decision
4. **Week 9+:** Feature flag ON by default (production rollout)

**Rollback Strategy:**
- Set `PYDANTIC_SCAFFOLDING_ENABLED=false` → instant v1 revert
- Zero code changes required (flag controls routing only)
- v1 pipeline maintained until v2 proven stable (3+ months production)

---

## GATE 2 Decision Rationale

### The Question
**How to map Context class → RenderContext class for 17 artifact types?**

Context: After GATE 1 decision (LifecycleMixin solves DRY for lifecycle field inheritance), the remaining challenge is writing 1 generic enrichment method that works for all artifact types.

### Options Considered

#### Option A: Naming Convention (SELECTED ✅)
**Mechanism:** Automatic class name derivation

**Pseudo-code:**
```
def get_render_context_class(context_type):
    class_name = context_type.__name__.replace("Context", "RenderContext")
    return globals()[class_name]  # WorkerContext → WorkerRenderContext
```

**Pros:**
- ✅ **Zero maintenance:** No registry to update when adding new artifact types
- ✅ **DRY:** No duplication between schema definitions and registry
- ✅ **Automatic:** Works for any `XContext` → `XRenderContext` pair
- ✅ **Type safety:** Pydantic validates fields at instantiation (catches errors early)
- ✅ **Simple:** 3 lines of code, easy to understand/debug

**Cons:**
- ⚠️ **Convention dependency:** Requires consistent naming (`Context` suffix mandatory)
- ⚠️ **Runtime lookup:** Class name string manipulation (minor performance cost)
- ⚠️ **Import requirement:** RenderContext classes must be imported in enrichment module

**Mitigations:**
- Convention enforced by template system (all schemas scaffolded with correct naming)
- Performance cost negligible (one-time lookup per scaffold operation, memoizable)
- Import handled by schema registry `__init__.py` (wildcard import pattern)

---

#### Option B: Explicit Registry (NOT SELECTED ❌)
**Mechanism:** Manual dict mapping

**Pseudo-code:**
```
CONTEXT_TO_RENDER = {
    WorkerContext: WorkerRenderContext,
    DTOContext: DTORenderContext,
    # ... 15 more entries (17 total)
}

def get_render_context_class(context_type):
    return CONTEXT_TO_RENDER[context_type]
```

**Pros:**
- ✅ **Explicit:** Clear mapping visible in one place
- ✅ **No naming convention:** Works with any class names
- ✅ **Static lookup:** Direct dict access (marginally faster)

**Cons:**
- ❌ **Maintenance burden:** Must update registry for every new artifact type (17 entries now, 20+ future)
- ❌ **DRY violation:** Duplication between schema files + registry dict
- ❌ **Error prone:** Forgot to update registry → KeyError at runtime
- ❌ **Synchronization risk:** Schema exists but registry entry missing

**Why Not Selected:**
Violates DRY principle (core motivation of Issue #135). Maintenance burden grows linearly with artifact types. No significant benefit over Naming Convention approach given our consistent naming pattern.

---

### Decision: Naming Convention (Option A)

**Rationale:**
1. **DRY Alignment:** Issue #135 goal is eliminating duplication. Explicit registry adds duplication.
2. **Maintenance Cost:** 0 maintenance vs 17+ manual entries (scales poorly)
3. **Consistency:** Our existing codebase already uses consistent naming (`WorkerContext`, `DTOContext`, etc.)
4. **Type Safety:** Pydantic validation catches field mismatches at instantiation (no need for compile-time checking)
5. **Simplicity:** 3-line implementation vs multi-entry dict maintenance

**Risk Assessment:**
- **Risk:** Developer forgets `Context` suffix → class not found  
  **Mitigation:** Schema scaffolding enforces naming pattern automatically
  
- **Risk:** Import issues if RenderContext not in scope  
  **Mitigation:** Schema registry `__init__.py` imports all (centralized)

**Success Criteria:**
- Enrichment works for all 17 artifact types without registry updates
- No runtime errors from naming convention mismatches (validated in parity tests)
- Code maintainability improved (fewer files to update per new artifact)

---

### Original GATE 2 Complexity (Why It Got Simplified)

**Initial Question:** "How to enforce type safety at enrichment boundary?"

**Initial Options:** Protocol (duck typing), ABC (inheritance contract), Generic (TypeVar), Runtime (validation)

**User Insight (2026-02-15):**
> "Waarom wordt fingerprinting metadata niet in eigen Pydantic schema? Mogelijk vervalt complexiteit..."

**Key Realization:**
- LifecycleMixin ALREADY solves lifecycle field DRY (4 fields defined once, inherited 17×)
- GATE 2 complexity was NOT about "how to inherit from LifecycleMixin" (simple)
- GATE 2 complexity WAS about "how to write 1 generic enrichment method" (class mapping)

**Simplification:**
- Removed focus on inheritance patterns (ABC/Protocol) → already solved by LifecycleMixin
- Reframed question to class mapping problem → Naming Convention vs Registry
- Reduced 4 complex options to 2 simple options → clear winner (Naming Convention)

**Lesson:**
Original GATE 2 question asked the wrong thing. User feedback correctly identified that LifecycleMixin inheritance is trivial (standard Pydantic pattern). The REAL question is class lookup mechanism, which has a simple DRY solution (naming convention).

---

## Schema Registry Organization

### Directory Structure

```
backend/schemas/
├── __init__.py                # Wildcard imports (all contexts + render contexts)
├── mixins/
│   ├── __init__.py
│   ├── lifecycle.py          # LifecycleMixin (4 fields)
│   ├── validation.py         # Optional: common validators
│   └── metadata.py           # Optional: artifact_type, category enums
├── contexts/
│   ├── __init__.py
│   ├── base.py               # BaseContext (empty), BaseRenderContext (LifecycleMixin)
│   ├── dto.py                # DTOContext
│   ├── worker.py             # WorkerContext
│   ├── adapter.py            # AdapterContext
│   └── ... (17 total context files)
└── render_contexts/
    ├── __init__.py
    ├── dto.py                # DTORenderContext (DTOContext + LifecycleMixin)
    ├── worker.py             # WorkerRenderContext (WorkerContext + LifecycleMixin)
    ├── adapter.py            # AdapterRenderContext (AdapterContext + LifecycleMixin)
    └── ... (17 total render context files)
```

### Import Pattern

**`backend/schemas/__init__.py`:**
```python
# Import all contexts and render contexts for global scope access
from .contexts import *
from .render_contexts import *
from .mixins.lifecycle import LifecycleMixin

__all__ = [
    "LifecycleMixin",
    "BaseContext", "BaseRenderContext",
    "WorkerContext", "WorkerRenderContext",
    "DTOContext", "DTORenderContext",
    # ... remaining 15 pairs
]
```

**Purpose:** Enables Naming Convention lookup via `globals()` in enrichment method

---

### File Count

| Category | Count | Notes |
|----------|-------|-------|
| Mixin files | 1 core + 2 optional = 3 | LifecycleMixin required, validation/metadata optional |
| Base files | 1 | base.py (BaseContext + BaseRenderContext) |
| Context files | 17 | One per non-ephemeral artifact type |
| RenderContext files | 17 | One per non-ephemeral artifact type |
| **Total** | **38 schema files** | Plus 3 `__init__.py` files = 41 total |

**Not Included:**
- 3 ephemeral artifacts (commit/pr/issue) use TypedDict (no lifecycle fields, defined in single file `ephemeral.py`)

---

## Risk Assessment

### High Risks

**R1: Parity tests too strict → false negatives**
- **Impact:** Valid v2 improvements flagged as regressions
- **Probability:** Medium
- **Mitigation:** 
  - Clear normalization rules documented
  - Manual review process for "failures" (semantic equivalence check)
  - Whitelist known acceptable differences (e.g., improved error messages)
- **Owner:** TDD phase

**R2: Performance overhead exceeds 20% threshold**
- **Impact:** v2 adoption blocked, rollback to v1 required
- **Probability:** Low (Pydantic validation fast)
- **Mitigation:**
  - Benchmark early (Phase 1 pilot)
  - Profile hotspots (memoize RenderContext class lookups if needed)
  - Acceptance criteria: 20% overhead is UPPER BOUND (expect 5-10% actual)
- **Owner:** Phase 4 integration

### Medium Risks

**R3: Naming Convention breaks on future artifact type**
- **Impact:** Runtime error when new artifact doesn't follow `XContext` → `XRenderContext` pattern
- **Probability:** Low (scaffolding enforces naming)
- **Mitigation:**
  - Schema scaffolding template enforces naming convention
  - Validation in `validate_architecture` tool (checks all schemas follow pattern)
  - Parity tests catch issues early (fail fast on class lookup error)
- **Owner:** Ongoing (schema validation)

**R4: Ephemeral artifacts confusion**
- **Impact:** Developer tries to use LifecycleMixin on commit/pr/issue (doesn't make sense)
- **Probability:** Low
- **Mitigation:**
  - Documentation clearly segregates ephemeral vs persistent artifacts
  - TypedDict for ephemeral (no .model_validate() method → obvious difference)
  - Code review checklist: "Is lifecycle tracking needed?"
- **Owner:** Documentation phase

### Low Risks

**R5: Import scope issues with globals() lookup**
- **Impact:** RenderContext class not found in globals() → NameError
- **Probability:** Very Low
- **Mitigation:**
  - Centralized import in `backend/schemas/__init__.py` (wildcard pattern)
  - Test coverage: verify all 17 RenderContext classes importable
  - Fallback: explicit import in enrichment module if needed
- **Owner:** Phase 2 integration

**R6: 41+ schema files feels heavy**
- **Impact:** Developer overwhelmed by file count, maintenance intimidating
- **Probability:** Low (structured organization mitigates)
- **Mitigation:**
  - Clear directory structure (mixins/ contexts/ render_contexts/)
  - Each file single-purpose (one schema per file)
  - Scaffolding automates creation (no manual file creation)
- **Owner:** Design phase (diagrams clarify structure)

---

## TDD Cycles

### Cycle 1: Parity Test Framework

**Goal:** Establish output equivalence validation infrastructure

**Tests:**
- `test_normalizer_whitespace()` - strips trailing, normalizes CRLF/LF
- `test_normalizer_imports()` - sorts imports alphabetically
- `test_normalizer_timestamps()` - masks dynamic values
- `test_equivalence_identical()` - identical strings → equivalent
- `test_equivalence_normalized()` - normalized strings → equivalent
- `test_equivalence_semantic_diff()` - semantic changes → NOT equivalent

**Success Criteria:**
- Normalizer handles edge cases (empty strings, no imports, etc.)
- Equivalence validator clear pass/fail
- Test framework reusable for all artifact types

---

### Cycle 2: LifecycleMixin + Base Classes

**Goal:** Core schema infrastructure working

**Tests:**
- `test_lifecycle_mixin_fields()` - 4 required fields present
- `test_base_context_instantiation()` - empty base class works
- `test_base_render_context_inheritance()` - inherits LifecycleMixin correctly
- `test_lifecycle_fields_immutable()` - system-managed (no user override)

**Success Criteria:**
- LifecycleMixin validates correctly (required fields, types)
- BaseRenderContext has 4 lifecycle fields
- Foundation ready for concrete schemas

---

### Cycle 3: DTO Pilot (Context + RenderContext)

**Goal:** End-to-end pilot for 1 artifact type

**Tests:**
- `test_dto_context_validation_happy()` - valid input → DTOContext instance
- `test_dto_context_validation_error()` - invalid input → ValidationError
- `test_dto_render_context_enrichment()` - DTOContext → DTORenderContext (adds lifecycle)
- `test_dto_render_context_all_fields()` - 17 artifact + 4 lifecycle = 21 total
- `test_dto_template_v2_render()` - DTORenderContext → rendered output
- `test_dto_parity_happy_path()` - v1 vs v2 output equivalent (10 test cases)

**Success Criteria:**
- All 10 DTO parity tests pass
- Pydantic validation catches errors (no more silent `| default` failures)
- Template character count reduced (line 95: 106 → 36 chars)

---

### Cycle 4: Feature Flag Integration

**Goal:** ArtifactManager routes v1/v2 correctly

**Tests:**
- `test_feature_flag_off_uses_v1()` - env var false → v1 pipeline
- `test_feature_flag_on_uses_v2()` - env var true → v2 pipeline
- `test_feature_flag_toggle()` - runtime toggle works (no restart needed)
- `test_v1_pipeline_unchanged()` - v1 behavior identical (regression check)
- `test_v2_pipeline_validates()` - v2 uses Pydantic validation

**Success Criteria:**
- Feature flag controls routing correctly
- v1 pipeline ZERO changes (backward compatibility)
- v2 pipeline functional (DTO pilot works)

---

### Cycle 5: Remaining Code Artifacts (8 types)

**Goal:** Scale to all code artifact types

**Tests (per artifact type):**
- `test_{type}_context_validation()` - schema validates correctly
- `test_{type}_render_context_enrichment()` - enrichment adds lifecycle
- `test_{type}_parity_happy_path()` - v1 vs v2 output equivalent (5-10 cases)

**Success Criteria:**
- 8 context schemas implemented (worker, adapter, service, tool, resource, schema, interface, generic)
- 8 render context classes implemented (naming convention followed)
- 40+ parity tests pass (5 per type minimum)

---

### Cycle 6: Document Artifacts (6 types)

**Goal:** Extend to markdown document artifacts

**Tests (per artifact type):**
- `test_{type}_context_validation()` - schema validates correctly
- `test_{type}_render_context_enrichment()` - enrichment adds lifecycle
- `test_{type}_parity_structure()` - markdown structure preserved (3-5 cases)

**Success Criteria:**
- 6 document context schemas implemented (research, planning, design, architecture, tracking, reference)
- 6 document render context classes implemented
- 18+ parity tests pass (3 per type minimum)

---

### Cycle 7: Test Artifacts (2 types)

**Goal:** Complete coverage with test artifact types

**Tests (per artifact type):**
- `test_{type}_context_validation()` - schema validates correctly
- `test_{type}_render_context_enrichment()` - enrichment adds lifecycle
- `test_{type}_parity_test_structure()` - test template structure preserved (5 cases)

**Success Criteria:**
- 2 test context schemas implemented (unit_test, integration_test)
- 2 test render context classes implemented (naming convention followed)
- 10+ parity tests pass (5 per type minimum)
- **Migration complete:** All 17 non-ephemeral artifacts covered (DTO: 1, Code: 8, Docs: 6, Tests: 2)

---

## Integration Phase

### Real-World Validation & Pilot Deployment

**Goal:** End-to-end validation with production-like scenarios, pilot deployment with team

**Deliverables:**

1. **Full System Smoke Tests**
   - Scaffold all 17 non-ephemeral artifact types with real-world context
   - Validate naming convention lookup (all RenderContext classes found via globals())
   - Verify import scope completeness (all schemas importable from backend.schemas)
   
2. **Performance Benchmarking**
   - Baseline measurement: v1 template render times (median/p95/p99)
   - V2 measurement: Pydantic validation overhead + simplified template render
   - Comparative analysis: v2 vs v1 performance (target: ≤1.2× v1 median time)
   - Hotspot profiling: identify bottlenecks if overhead >20%
   
3. **Pilot Deployment (2 weeks)**
   - Feature flag: PYDANTIC_SCAFFOLDING_ENABLED=true for team (5-10 users)
   - Real-world usage: scaffold 50+ artifacts during normal development
   - Error tracking: collect ValidationError occurrences, categorize (schema issue vs user input)
   - Feedback collection: usability survey (schema API clarity, error messages, documentation)
   
4. **Regression Testing**
   - V1 pipeline validation: existing template_engine.py tests pass unchanged
   - Backward compatibility: v1/v2 toggle verified (no side effects)
   - Edge case coverage: empty lists, optional fields, nested objects, unicode, special chars
   
5. **Production-Like Scenarios**
   - Multi-artifact workflows: scaffold DTO → Worker → Test in sequence
   - Complex context: nested Pydantic models, cross-references, large field counts (20+ fields)
   - Error recovery: simulate invalid context, validate error messages clarity
   - Concurrent scaffolding: 10 parallel scaffold operations (thread safety)

**Acceptance Criteria:**

- ✅ **All 17 artifact types scaffold successfully** (v2 pipeline: DTO + 8 code + 6 docs + 2 test)
- ✅ **Naming Convention works** (no NameError on class lookup across 17 types)
- ✅ **Performance within acceptable range** (v2 ≤ 1.2× v1 median time, p95 ≤ 1.3× v1)
- ✅ **Error handling superior to v1** (explicit ValidationError > silent `| default` failures)
- ✅ **Pilot feedback positive** (≥80% satisfaction rate, <5 critical issues reported)
- ✅ **Zero backward compatibility breaks** (v1 pipeline operates identically with flag OFF)
- ✅ **Quality Gates 0-6 pass** for all integration test code (smoke tests, performance tests)

**Measurable Evidence:**

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Artifact success rate | 100% (17/17) | Smoke test suite execution |
| Performance overhead | ≤20% (median) | cProfile + pytest-benchmark |
| Pilot error rate | <5 critical bugs | GitHub issue tracking (label: pilot-issue) |
| User satisfaction | ≥80% | Post-pilot survey (SUS score) |
| V1 regression | 0 failures | Existing test suite (200+ tests) |
| Code coverage | ≥90% | pytest-cov report |

**Exit Criteria:**

- 2-week pilot period completed without rollback
- Performance benchmarks within acceptable range (measured, documented)
- Pilot feedback incorporated (high-priority issues resolved)
- Go/No-Go decision documented with stakeholder approval
- Rollback plan tested (feature flag deactivation, v1 pipeline verified)

---

## Documentation Phase

### Migration Guide, Runbooks, and Cleanup

**Goal:** Deliver complete documentation for v2 adoption, establish maintenance procedures, document technical debt

**Deliverables:**

1. **User Documentation**
   - **Context Schema Creation Guide**
     - Step-by-step: How to create new Context/RenderContext pair
     - Field types reference: Pydantic types, validators, examples
     - Naming convention rules: XContext → XRenderContext enforcement
     - Common patterns: optional fields, nested models, unions
   - **Migration Runbook**
     - V1 → V2 upgrade procedure (feature flag activation)
     - Rollback procedure (v1 reversion steps)
     - Troubleshooting guide: common Pydantic ValidationError patterns
     - FAQ: "Why ValidationError instead of broken output?", "How to add lifecycle field?"
   - **Template Simplification Guide**
     - Before/after examples: dto.py line 95 (106 → 36 chars)
     - Pattern removal: `| default` → Pydantic field defaults
     - Testing checklist: parity tests, quality gates

2. **Technical Documentation**
   - **Architecture Decision Record (ADR)**
     - GATE 1 decision: System-managed lifecycle (rationale, alternatives)
     - GATE 2 decision: Naming Convention (rationale, Registry comparison)
     - GATE 3 decision: Tier 3 macro reuse (19 analyzed, 3 pending)
   - **Schema Registry Documentation**
     - Directory structure: mixins/ contexts/ render_contexts/
     - Import pattern: backend.schemas wildcard exports
     - Maintenance: Adding new artifact type (5-step checklist)
   - **Performance Baseline**
     - V1 benchmarks: template render times (documented for future comparison)
     - V2 benchmarks: validation + render times (profiling results)
     - Optimization notes: memoization opportunities, bottlenecks

3. **Operational Runbooks**
   - **CI/CD Integration Guide**
     - Quality gates enforcement: Ruff/mypy commands for schema files
     - Parity test execution: automated test suite in pipeline
     - Feature flag management: environment variable configuration
   - **Monitoring & Alerting**
     - Metrics to track: scaffold success rate, ValidationError frequency, performance p95
     - Alert thresholds: >5% error rate, >30% performance degradation
     - Incident response: rollback procedure, hotfix process
   - **Maintenance Schedule**
     - Monthly: Review pending Tier 3 macros (assertions, log_enricher, translator)
     - Quarterly: Audit schema coverage (new artifact types, missing RenderContext)
     - Annually: Performance re-baseline (hardware changes, Python version upgrades)

4. **Cleanup & Technical Debt**
   - **V1 Deprecation Roadmap**
     - Timeline: 3-month stability period before v1 removal consideration
     - Deprecation warnings: add to v1 pipeline (e.g., "v1 deprecated, migrate to v2")
     - Removal criteria: 95% v2 adoption rate, zero critical v2 bugs for 3 months
   - **Outstanding Technical Debt**
     - Issue #107: Remove scaffolder_class/scaffolder_module from artifacts.yaml (LEGACY fields)
     - Issue #121: Add 'updated' field to LifecycleMixin (future enhancement)
     - 3 pending Tier 3 macros: assertions, log_enricher, translator (categorization deferred)
   - **Cleanup Tasks**
     - Remove `| default` patterns from v1 templates (when v1 deprecated)
     - Consolidate template_engine.py introspection code (v2 doesn't need it)
     - Archive research/planning docs (move to docs/archive/issue135/)

5. **Training Materials (Optional)**
   - Brownbag session slides: "Pydantic-First Scaffolding V2" (30 min presentation)
   - Video walkthrough: Context schema creation demo (10 min screencast)
   - Code review checklist: schema quality standards (Gate 0-6 enforcement)

**Acceptance Criteria:**

- ✅ **Migration guide complete** (5+ sections, examples, troubleshooting)
- ✅ **Runbooks tested** (dry-run upgrade/rollback procedures successful)
- ✅ **ADRs documented** (GATE 1-3 decisions with rationale)
- ✅ **Technical debt catalogued** (3+ issues documented with priority)
- ✅ **Quality Gates 0-3 pass** for all markdown documentation files

**Deliverables Checklist:**

- [ ] Migration runbook (upgrade + rollback)
- [ ] Context schema creation guide (step-by-step + examples)
- [ ] Troubleshooting guide (common ValidationError patterns)
- [ ] Architecture Decision Records (GATE 1-3)
- [ ] Schema registry documentation (directory structure + maintenance)
- [ ] Performance baseline documentation (v1/v2 benchmarks)
- [ ] CI/CD integration guide (quality gates + parity tests)
- [ ] Monitoring & alerting runbook (metrics + thresholds)
- [ ] Maintenance schedule (monthly/quarterly/annual tasks)
- [ ] Technical debt register (Issue #107, #121, 3 pending macros)
- [ ] Cleanup task list (v1 deprecation roadmap)

**Exit Criteria:**

- All deliverables completed and reviewed (stakeholder sign-off)
- Documentation published (internal wiki or docs/ directory)
- Runbooks validated (dry-run successful, feedback incorporated)
- Technical debt prioritized (backlog grooming session completed)
- Training delivered (brownbag session or video walkthrough)

---

## Related Documentation
- **[research-pydantic-v2.md][related-1]** - Architecture research, GATE 1-3 decisions
- **[docs/architecture/TEMPLATE_LIBRARY.md][related-2]** - Template library architecture
- **[docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md][related-3]** - Type checking standards
- **[docs/coding_standards/QUALITY_GATES.md][related-4]** - Quality gates 0-6 enforcement

<!-- Link definitions -->

[related-1]: research-pydantic-v2.md
[related-2]: ../../architecture/TEMPLATE_LIBRARY.md
[related-3]: ../../coding_standards/TYPE_CHECKING_PLAYBOOK.md
[related-4]: ../../coding_standards/QUALITY_GATES.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Agent | Initial draft with GATE 2 rationale documented |
| 1.1 | 2026-02-15 | Agent | Workflow phases restructured: TDD cycles 1-6, Integration phase (Cycle 7 → pilot deployment with measurable criteria), Documentation phase (migration guide, runbooks, technical debt register) |
| 1.2 | 2026-02-15 | Agent | Governance consolidation: Removed Phase 4 duplication (Integration & Rollout merged into separate Integration Phase), removed Documentation from Phase 4 (now only in Documentation Phase), added TDD Cycle 7 for test artifacts (unit_test, integration_test), complete artifact coverage: 17 non-ephemeral (DTO:1 + Code:8 + Docs:6 + Tests:2) |

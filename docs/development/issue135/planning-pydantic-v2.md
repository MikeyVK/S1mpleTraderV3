<!-- D:\dev\SimpleTraderV3-parallel\docs\development\issue135\planning-pydantic-v2.md -->
<!-- template=planning version=130ac5ea created=2026-02-15T17:30:00Z updated=2026-02-15T17:45:00Z -->
# Issue #135 Pydantic-First v2 Planning

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-15

---

## Purpose

Plan migration timeline, parity testing strategy, and feature flag implementation for Pydantic-First architecture that eliminates 78× defensive template patterns

## Scope

**In Scope:**
Migration phases (DTO pilot → code → docs), parity test requirements (output equivalence), feature flag integration (ArtifactManager), GATE 2 rationale (Naming Convention decision), schema registry structure

**Out of Scope:**
Implementation code examples (design phase), class diagrams (design phase), template simplification syntax (design phase), test implementation (TDD phase)

## Prerequisites

Read these first:
1. Research phase complete (research-pydantic-v2.md v1.7)
2. GATE 1 resolved (system-managed lifecycle)
3. GATE 2 resolved (Naming Convention)
4. GATE 3 resolved (19 macros analyzed)

---

## Summary

Migration plan for Pydantic-First v2 architecture addressing Issue #135 template introspection metadata SSOT violation. Defines 4-phase rollout (DTO pilot → code artifacts → docs → remaining), parity testing strategy (output equivalence validation), feature flag integration pattern, and GATE 2 rationale (Naming Convention over Registry). Eliminates 78× defensive template patterns through schema-first validation.

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

**Exit Criteria:**
- Stakeholder approval on pilot results
- Parity test framework accepted as validation standard

---

### Phase 2: Code Artifacts (Week 3-4)
**Goal:** Migrate remaining 13 code artifact types (worker, adapter, service, etc.)

**Deliverables:**
1. **Context Schemas (13 types)**
   - WorkerContext, AdapterContext, ServiceContext, InterfaceContext, ToolContext, ResourceContext, SchemaContext
   - ManagerContext, ValidatorContext, ConfigContext, UtilsContext, TestContext, HandlerContext

2. **RenderContext Classes (13 types)**
   - All inherit from respective Context + LifecycleMixin
   - Follow Naming Convention: `WorkerContext` → `WorkerRenderContext`

3. **Template Simplification**
   - Remove defensive patterns from 13 v2 concrete templates
   - Estimated reduction: 41 total defaults across code templates

4. **Parity Testing**
   - 5-10 test cases per artifact type (minimum 65 total tests)
   - Cover: happy path, edge cases (empty lists, optional fields), error cases

**Success Criteria:**
- ✅ 100% parity test pass rate (output equivalence)
- ✅ Character count reduction measured and documented per template
- ✅ No regression in error handling (v2 schema validation ≥ v1 `| default` robustness)

---

### Phase 3: Document Artifacts (Week 5)
**Goal:** Migrate 8 document artifact types (research, planning, design, architecture, etc.)

**Deliverables:**
1. **Document Context Schemas (8 types)**
   - ResearchContext, PlanningContext, DesignContext, ArchitectureContext, TrackingContext
   - GenericContext, ApiContext, TutorialContext

2. **Template Simplification**
   - Remove defensive patterns from 8 markdown templates
   - Estimated reduction: 22 total defaults across doc templates

3. **Parity Testing**
   - 3-5 test cases per document type (minimum 24 total tests)
   - Focus: section structure, metadata fields, markdown formatting

**Success Criteria:**
- ✅ 100% parity test pass rate
- ✅ Markdown structure preserved (headers, links, tables)
- ✅ Document metadata complete (version, timestamp, related_docs)

---

### Phase 4: Integration & Rollout (Week 6)
**Goal:** Feature flag activation, full validation, performance benchmarking

**Deliverables:**
1. **Feature Flag Integration**
   - ArtifactManager v1/v2 routing logic
   - Environment variable: `PYDANTIC_SCAFFOLDING_ENABLED` (default: false)
   - Gradual rollout: pilot users → team → production

2. **Full Validation Suite**
   - 100+ parity tests (DTO: 10, Code: 65+, Docs: 24+, Edge: 10+)
   - Smoke tests: scaffold 20 artifact types with real-world context
   - Regression suite: existing template_engine.py tests must pass unchanged

3. **Performance Benchmarking**
   - v1 baseline: current template render times (median/p95)
   - v2 measurement: Pydantic validation overhead + simplified render
   - Acceptance: v2 ≤ 1.2× v1 median time (20% overhead acceptable)

4. **Documentation**
   - Migration guide: "How to create new Context schema"
   - Troubleshooting: common Pydantic validation errors
   - Rollback plan: feature flag deactivation procedure

**Success Criteria:**
- ✅ Feature flag tested in isolation (v1/v2 toggle)
- ✅ Performance overhead within acceptable range (≤20%)
- ✅ Zero critical bugs in production pilot (2 week monitoring)

**Exit Criteria:**
- 2-week pilot period with PYDANTIC_SCAFFOLDING_ENABLED=true for team
- Metrics: error rate, performance, user feedback
- Go/No-Go decision for default=true rollout

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

### Cycle 5: Remaining Code Artifacts (13 types)

**Goal:** Scale to all code artifact types

**Tests (per artifact type):**
- `test_{type}_context_validation()` - schema validates correctly
- `test_{type}_render_context_enrichment()` - enrichment adds lifecycle
- `test_{type}_parity_happy_path()` - v1 vs v2 output equivalent (5-10 cases)

**Success Criteria:**
- 13 context schemas implemented (worker, adapter, service, etc.)
- 13 render context classes implemented (naming convention followed)
- 65+ parity tests pass (5 per type minimum)

---

### Cycle 6: Document Artifacts (8 types)

**Goal:** Extend to markdown document artifacts

**Tests (per artifact type):**
- `test_{type}_context_validation()` - schema validates correctly
- `test_{type}_render_context_enrichment()` - enrichment adds lifecycle
- `test_{type}_parity_structure()` - markdown structure preserved (3-5 cases)

**Success Criteria:**
- 8 document context schemas implemented (research, planning, design, etc.)
- 8 document render context classes implemented
- 24+ parity tests pass (3 per type minimum)

---

### Cycle 7: Full Validation Smoke Test

**Goal:** End-to-end validation with production-like scenarios

**Tests:**
- `test_all_artifacts_scaffoldable()` - scaffold 20 artifact types (smoke test)
- `test_naming_convention_lookup()` - all 17 RenderContext classes found via globals()
- `test_import_scope_complete()` - all schemas importable from backend.schemas
- `test_performance_benchmark()` - v2 ≤ 1.2× v1 render time
- `test_error_messages_improved()` - v2 ValidationError > v1 silent failure

**Success Criteria:**
- All 20 artifact types scaffold successfully (v2 pipeline)
- Naming Convention works (no NameError on class lookup)
- Performance within acceptable range (≤20% overhead)
- Error handling better than v1 (explicit failures, clear messages)

---

## Related Documentation
- **[research-pydantic-v2.md][related-1]** - Architecture research, GATE 1-3 decisions
- **[docs/architecture/template_system.md][related-2]** - Multi-tier template architecture (Issue #72)
- **[docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md][related-3]** - Type checking standards

<!-- Link definitions -->

[related-1]: research-pydantic-v2.md
[related-2]: ../../architecture/template_system.md
[related-3]: ../../coding_standards/TYPE_CHECKING_PLAYBOOK.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Agent | Initial draft with GATE 2 rationale documented |

<!-- docs/development/issue108/planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-13T14:30:00Z updated= -->
# Issue #108: JinjaRenderer Extraction - Planning

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-13

---

## Purpose

Break down JinjaRenderer extraction into TDD cycles with clear test boundaries and success criteria. Ensure zero regression in existing scaffolding output.

## Scope

**In Scope:**
TDD cycle breakdown for extraction, import migration strategy (6 sites), regression validation approach, test organization

**Out of Scope:**
Implementation details (code examples), design decisions (already in research), Phase 2 features (mock rendering, ChoiceLoader)

## Prerequisites

Read these first:
1. Research document approved (research.md v1.4)
2. MVP scope defined (single root, FileSystemLoader only)
3. All 6 import sites identified (2 production, 4 test)
---

## Summary

Planning phase for extracting JinjaRenderer from mcp_server/scaffolding/renderer.py to backend/services/template_engine.py. Focus: Breaking circular dependency while maintaining behavioral/output compatibility (identical scaffolding output, no compatibility layer needed). MVP scope: Basic rendering, single template root, FileSystemLoader support.

---

## Dependencies

- backend/services/ directory structure exists
- mcp_server/config/template_config.py get_template_root() function
- Existing scaffolding tests (40 tests) remain green throughout

---

## TDD Cycles

> **Workflow Model:** Each cycle follows RED→GREEN→REFACTOR pattern (agent.md:103-120)
> - **RED:** Write failing test, commit with `phase="red"`
> - **GREEN:** Implement minimal code to pass, commit with `phase="green"`  
> - **REFACTOR:** Clean up + quality gates, commit with `phase="refactor"`

### Cycle 0: Baseline Capture

**Goal:** Capture baseline scaffolding output BEFORE any migration, enabling byte-identical regression validation

**Tests:**
- test_capture_baseline_dto: Scaffold dto with known context, save output to tests/baselines/
- test_capture_baseline_worker: Scaffold worker with known context, save output
- test_capture_baseline_tool: Scaffold tool with known context, save output
- test_capture_baseline_research: Scaffold research.md with known context, save output
- test_capture_baseline_planning: Scaffold planning.md with known context, save output

**Success Criteria:**
- 5 baseline files captured in tests/baselines/ directory
- Baselines committed to git (immutable reference point)
- Documentation: How to regenerate baselines if needed
- All existing tests (40) pass without modification

**RED→GREEN→REFACTOR:**
1. **RED:** Write test_capture_baselines.py (fails - no baselines yet)
2. **GREEN:** Run current scaffolding, capture outputs to tests/baselines/
3. **REFACTOR:** Add baseline regeneration documentation, commit baselines

**Phase Gate:** ✅ Entry to TDD phase (planning→tdd transition)
### Cycle 1: Extract TemplateEngine Module

**Goal:** Create backend/services/template_engine.py with TemplateEngine class (renamed from JinjaRenderer) maintaining identical API

**Tests:**
- test_template_engine_initialization: Verify TemplateEngine accepts template_root parameter
- test_render_basic_template: Render simple template with context variables
- test_render_with_inheritance: Render tier2 → tier1 → tier0 inheritance chain
- test_custom_filters_available: Verify pascalcase, snakecase, kebabcase, validate_identifier filters present
- test_template_not_found_error: Verify proper error handling for missing templates

**Success Criteria:**
- TemplateEngine class exists in backend/services/template_engine.py
- All 5 tests pass independently (no existing code affected yet)
- Module docstring follows coding standards (@layer, @dependencies, @responsibilities)
- 100% type coverage (mypy --strict passes)

**RED→GREEN→REFACTOR:**
1. **RED:** Write tests/unit/services/test_template_engine.py (5 tests, all fail)
2. **GREEN:** Copy JinjaRenderer to backend/services/template_engine.py, rename class
3. **REFACTOR:** Fix imports (backend/ only), add docstring, mypy --strict

**Dependencies:** Cycle 0: Baseline Capture

### Cycle 2: Update Production Import Sites

**Goal:** Update 2 production files to use TemplateEngine while maintaining identical behavior

**Tests:**
- test_base_scaffolder_uses_template_engine: Verify mcp_server/scaffolding/base.py imports TemplateEngine
- test_template_scaffolder_uses_template_engine: Verify mcp_server/scaffolders/template_scaffolder.py imports TemplateEngine
- test_existing_scaffolding_still_works: Run full scaffolding test suite (40 tests) - all must pass

**Success Criteria:**
- Both production files updated: base.py, template_scaffolder.py
- All 40 existing scaffolding tests remain green
- No changes to scaffolded output (byte-identical validation vs Cycle 0 baselines)

**RED→GREEN→REFACTOR:**
1. **RED:** Write tests for import verification (2 tests fail - old imports still there)
2. **GREEN:** Update base.py + template_scaffolder.py imports only (minimal change)
3. **REFACTOR:** Run full test suite (40 tests) + quality gates, validate no output changes

**Dependencies:** Cycle 1: Extract TemplateEngine Module


### Cycle 3: Update Test Import Sites

**Goal:** Update 4 test files to use TemplateEngine, ensuring test isolation maintained

**Tests:**
- test_template_scaffolder_unit_tests: Verify tests/unit/scaffolders/test_template_scaffolder.py uses TemplateEngine
- test_components_unit_tests: Verify tests/unit/scaffolding/test_components.py uses TemplateEngine
- test_concrete_templates_integration: Verify tests/integration/test_concrete_templates.py uses TemplateEngine
- test_artifact_harness_fixtures: Verify tests/fixtures/artifact_test_harness.py uses TemplateEngine

**Success Criteria:**
- All 4 test files updated with new import
- All tests pass without modification beyond import change
- Test coverage remains ≥90%

**RED→GREEN→REFACTOR:**
1. **RED:** Write test_import_migration.py verifying 4 test files use TemplateEngine (fails)
2. **GREEN:** Update 4 test file imports (minimal change)
3. **REFACTOR:** Run pytest with coverage, validate ≥90% maintained

**Dependencies:** Cycle 2: Update Production Import Sites
### Cycle 4: Regression Validation Suite

**Goal:** Create regression tests validating byte-identical output for 8 representative scenarios
**Tests:**
- test_regression_dto_template: Baseline vs current output for dto.py.jinja2
- test_regression_worker_template: Baseline vs current output for worker.py.jinja2
- test_regression_tool_template: Baseline vs current output for tool.py.jinja2
- test_regression_research_doc: Baseline vs current output for research.md.jinja2
- test_regression_planning_doc: Baseline vs current output for planning.md.jinja2
- test_regression_5tier_inheritance: Verify tier0→tier1→tier2→concrete chain preserved
- test_regression_custom_filters: Verify pascalcase/snakecase/kebabcase output identical
- test_regression_template_metadata: Verify SCAFFOLD headers unchanged

**Success Criteria:**
- 8 regression tests created covering code + doc templates
- All regression tests pass (byte-identical output vs Cycle 0 baselines)
- Regression suite added to CI pipeline
- Documentation: How to run regression suite

**RED→GREEN→REFACTOR:**
1. **RED:** Write tests/regression/test_extraction_regression.py (8 tests, compare to baselines)
2. **GREEN:** Tests should pass (baselines from Cycle 0, no output changes expected)
3. **REFACTOR:** Add CI integration (.st3/workflows.yaml or GitHub Actions)

**Dependencies:** Cycle 3: Update Test Import Sites

### Cycle 5: Cleanup Legacy Module

**Goal:** Remove mcp_server/scaffolding/renderer.py after confirming zero references remain

**Tests:**
- test_no_renderer_imports: Grep search confirms zero 'from mcp_server.scaffolding.renderer' references
- test_full_test_suite_passes: All 40+ tests pass with old module deleted
- test_import_error_on_old_path: Verify ImportError raised if old path accidentally used

**Success Criteria:**
- mcp_server/scaffolding/renderer.py deleted
- Full test suite (40+ tests) passes
- No grep matches for old import path
- Documentation updated (if renderer.py was documented)


**RED→GREEN→REFACTOR:**
1. **RED:** Write test_import_error_on_old_path.py (expects ImportError, fails - module still exists)
2. **GREEN:** Delete mcp_server/scaffolding/renderer.py (test now passes - ImportError raised)
3. **REFACTOR:** Run full test suite (40+ tests) + grep validation, update docs if needed

**Dependencies:** Cycle 4: Regression Validation Suite

**Phase Gate:** ✅ Exit from TDD phase (tdd→integration transition)
## Risks & Mitigation

- **Risk:** Circular dependency resurfaces if TemplateEngine imports from mcp_server/scaffolding/
  - **Mitigation:** Strict import validation in Cycle 1 tests - TemplateEngine must only import from backend/, stdlib, and third-party
- **Risk:** Byte-identical output assumption fails due to Jinja2 version differences or environment factors
  - **Mitigation:** Regression tests capture baseline BEFORE any changes. If baseline differs, investigate environment first before proceeding
- **Risk:** Existing tests have hidden coupling to JinjaRenderer class name or internal structure
  - **Mitigation:** Cycle 2-3 validate ALL tests pass with minimal changes (import only). Any test requiring logic changes flags coupling issue
- **Risk:** Phase 2 scope creep (mock rendering, ChoiceLoader) leaks into TDD cycles
  - **Mitigation:** Each cycle explicitly validates MVP-only scope. Any mention of mock/parsing/multi-root is OUT OF SCOPE for this issue

---

## Milestones

- **Cycle 0 complete:** Baseline outputs captured, planning→tdd phase transition approved
- **Cycle 1 complete:** TemplateEngine exists and passes independent tests
- **Cycle 3 complete:** All 6 import sites migrated, full test suite green
- **Cycle 4 complete:** Regression suite passes (byte-identical validation)
- **Cycle 5 complete:** Legacy module removed, tdd→integration phase transition

## Related Documentation
- **[research.md](research.md)** - Research findings and MVP scope decision
- **[../../reference/mcp/scaffolding.md](../../reference/mcp/scaffolding.md)** - Scaffolding system architecture
- **[../../coding_standards/TYPE_CHECKING_PLAYBOOK.md](../../coding_standards/TYPE_CHECKING_PLAYBOOK.md)** - Type checking standards

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-13 | Agent | Initial draft |
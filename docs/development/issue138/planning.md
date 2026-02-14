<!-- D:\dev\SimpleTraderV3\.st3\workflow-first-vertical-cycles.md -->
<!-- template=planning version=130ac5ea created=2026-02-14T18:25:00+00:00 updated= -->
# Issue #138 Implementation Planning - Workflow-First Vertical Cycles

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-14T18:25:00+00:00

---

## Purpose

Break down workflow-first architecture into vertical delivery cycles, each producing working system with graceful degradation

## Scope

**In Scope:**
Vertical slice planning (phase-resolution + fallback first), Exit criteria (functional + compatibility + observability), No-regression contracts, Issues #117/#139 integration, Test strategy

**Out of Scope:**
Design details (HOW to implement), Code structure, Implementation approaches, Detailed schemas (those go in design phase)

## Prerequisites

Read these first:
1. Issue #138 research v2.1 complete
2. Workflow-first architecture chosen
3. Graceful degradation as non-negotiable
4. User feedback: vertical cycles not horizontal layers
---

## Summary

Vertical slice implementation of workflow-first commit conventions. Each cycle delivers working functionality: (1) Phase resolution with fallback, (2) Scope encoding/decoding, (3) Tool integration (#117/#139), (4) Consolidation. Non-negotiable: old commits never block tools.

---

## Dependencies

- workphases.yaml schema (minimal for Cycle 1)
- Scope parser library (re module)
- GitConfig singleton pattern (existing)

---

## TDD Cycles

### Cycle 1: Phase Resolution + Graceful Degradation

**Goal:** Old commits work, tools don't break on missing/invalid scope

**Deliverables:**
1. workphases.yaml (minimal SSOT - research, tdd, integration, documentation phases)
2. Scope parser with fallback (ScopeDecoder.extract_from_commit())
3. get_work_context integration (#117 fix)
4. Contract tests for parser (valid scopes, invalid scopes, missing scopes)
5. Integration test: old commit format ("test: add tests" → fallback to type heuristic)

**Exit Criteria:**
- **Functional:** get_work_context parses new scope format OR falls back to type-based heuristic
- **Compatibility:** All existing branches/commits continue working (no blocking errors)
- **Observability:** Clear logging when fallback used (not error, just info)

**No-Regression Contract:**
```python
# OLD FORMAT - MUST WORK
commit_message = "test: add validation tests"  # No scope
scope = decoder.extract_from_commit(commit_message)
assert scope is None  # Graceful: returns None, doesn't throw

# Tools fallback to type-based heuristic
phase = detect_phase_from_commit(commit_message)
assert phase == "tdd"  # Heuristic: type="test" → phase="tdd"
```

---

### Cycle 2: Scope Encoding + New Commit Format

**Goal:** NEW commits use workflow-first format, tools accept both old and new

**Deliverables:**
1. Scope encoder utility (ScopeEncoder.encode(phase, subphase, cycle))
2. GitManager.commit_with_scope(type, scope, message, files)
3. GitCommitInput schema update (workflow_phase, sub_phase, commit_type fields)
4. git.yaml extension (commit_types, scope_format specification)
5. Integration test: new commit workflow (full git_add_or_commit cycle)

**Exit Criteria:**
- **Functional:** git_add_or_commit accepts workflow phases, generates P_PHASE_SP_SUBPHASE scope
- **Compatibility:** GitManager handles mixed commit history (old + new formats)
- **Observability:** Validation errors show correct format examples (Issue #121 lesson)

**Example:**
```python
# NEW FORMAT - GENERATED
git_add_or_commit(
    workflow_phase="tdd",
    sub_phase="red",
    cycle=1,
    commit_type="test",
    message="add validation tests"
)
# → Generates: "test(P_TDD_SP_C1_RED): add validation tests"
```

---

### Cycle 3: Tool Integration + Issue #139 Fix

**Goal:** get_project_plan shows current_phase from git history, all tools workflow-aware

**Deliverables:**
1. get_project_plan integration (#139 fix - extract phase from last commit)
2. workflows.yaml phase_source reference (points to workphases.yaml)
3. GitConfig deprecation notices (tdd_phases, commit_prefix_map marked deprecated)
4. End-to-end test: full workflow cycle (research → planning → tdd → integration)

**Exit Criteria:**
- **Functional:** get_project_plan extracts phase from last commit scope
- **Compatibility:** No tool regressions (GitConfig, workflows.yaml references)
- **Observability:** Tools report phase source (git scope vs state.json fallback)

**Coupled Issues:**
- Issue #117: get_work_context parses scope (not just type)
- Issue #139: get_project_plan shows current_phase from git
- Both use same ScopeDecoder utility (DRY)

---

### Cycle 4: Consolidation + Documentation

**Goal:** Complete system documented, migration notes, cleanup temporary code

**Deliverables:**
1. agent.md updates (Tool Priority Matrix, Phase 2.3 TDD cycle examples with new format)
2. Migration notes for old branches (how to handle mixed history)
3. Deprecation cleanup (remove commit_tdd_phase, commit_docs methods)
4. Full test suite validation (1798+ tests pass)
5. PR description with breaking changes

**Exit Criteria:**
- **Functional:** All 1798+ tests pass, quality gates green
- **Compatibility:** Backward compatibility validated across test suite
- **Observability:** agent.md updated, examples clear, error messages helpful

**Consolidation Tasks:**
- agent.md: Update commit examples to use new scope format
- CHANGELOG: Document breaking changes (GitManager API)
- Migration guide: "Working with old branches" section
- Cleanup: Remove deprecated code paths (commit_tdd_phase)

---

## Risks & Mitigation
- **Risk:** Old commits blocking tools despite fallback
  - **Mitigation:** Comprehensive contract tests for parser, test with actual old branches (fix/138, feature/137)
- **Risk:** Scope format too complex for agents
  - **Mitigation:** Clear examples in agent.md, validation errors with concrete format hints (Issue #121 lesson)
- **Risk:** Test blast radius too large (210+ assertions)
  - **Mitigation:** Contract tests first (parser isolation), then integration tests (tool boundaries)

## Related Documentation
- **[research.md v2.1][related-1]**
- **[docs/coding_standards/README.md][related-2]**
- **[Issue #117 (get_work_context)][related-3]**
- **[Issue #139 (get_project_plan)][related-4]**

<!-- Link definitions -->

[related-1]: research.md v2.1
[related-2]: docs/coding_standards/README.md
[related-3]: Issue #117 (get_work_context)
[related-4]: Issue #139 (get_project_plan)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-14T18:25:00+00:00 | Agent | Initial draft |
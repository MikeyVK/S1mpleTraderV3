<!-- D:\dev\SimpleTraderV3\.st3\workflow-first-vertical-cycles.md -->
<!-- template=planning version=130ac5ea created=2026-02-14T18:25:00+00:00 updated= -->
# Issue #138 Implementation Planning - Workflow-First Vertical Cycles

**Status:** DRAFT  
**Version:** 1.1
**Last Updated:** 2026-02-14T19:00:00+00:00

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
1. Issue #138 research v2.2 complete
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

### Cycle 1: Phase Resolution + Graceful Degradation (Dual-Source)

**Goal:** Commit-scope parsing met state.json fallback, oude commits blijven werken

**Deliverables:**
1. workphases.yaml (minimal SSOT - phase definitions only)
2. Scope parser/decoder (ScopeDecoder.extract_from_commit())
3. Precedence resolver (commit-scope > state.json > type-heuristic)
4. get_work_context integration (#117 fix - met precedence)
5. Contract tests (scope parsing + fallback scenarios)
6. Integration test: old commit format graceful handling

**Exit Criteria:**
- **Functional:** get_work_context implements commit-scope > state.json > type-heuristic precedence
- **Compatibility:** All existing branches/commits continue working (no blocking errors)
- **Observability:** Clear logging van bron (scope, state.json, heuristic)

**No-Regression Contract:**
```python
# NEW FORMAT - Commit-scope primary
commit_message = "test(P_TDD_SP_C1_RED): add tests"
scope = decoder.extract_from_commit(commit_message)
assert scope is not None  # Parses correctly
assert scope.phase == "tdd"

# OLD FORMAT - Graceful fallback
commit_message = "test: add tests"  # No scope
scope = decoder.extract_from_commit(commit_message)
assert scope is None  # Returns None, doesn't throw

# Fallback chain in get_work_context
phase = get_work_context().current_phase
# 1. Try commit-scope (None voor old commits)
# 2. Try state.json (if exists)
# 3. Fallback type-heuristic (type="test" → "tdd")
assert phase == "tdd"  # Works via fallback
```

**Critical:** state.json blijft authoritative voor transition_phase (niet gewijzigd in Cycle 1)
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

**Goal:** get_project_plan implements commit-scope > state.json precedence, all tools workflow-aware

**Deliverables:**
1. get_project_plan integration (#139 fix - commit-scope met state.json fallback)
2. workflows.yaml phase_source reference (points to workphases.yaml)
3. GitConfig deprecation notices (tdd_phases, commit_prefix_map marked deprecated)
4. End-to-end test: full workflow cycle (research → planning → tdd → integration)

**Exit Criteria:**
- **Functional:** get_project_plan implements commit-scope > state.json precedence (consistent met Cycle 1)
- **Compatibility:** No tool regressions (GitConfig, workflows.yaml references)
- **Observability:** Tools report phase source (git scope vs state.json fallback)

**Coupled Issues:**
- Issue #117: get_work_context parses commit-scope met state.json fallback (Cycle 1)
- Issue #139: get_project_plan parses commit-scope met state.json fallback (Cycle 3)
- Both use same ScopeDecoder utility with precedence logic (DRY)

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

---

## Acceptatiecriteria (User-Specified)

1. **Geen blocking errors op legacy commitformaten**
   - Test: Old commits (`test: add tests`) behandeling zonder errors
   - Graceful fallback naar type-heuristic of state.json

2. **Deterministische source precedence per tooltype**
   - Transition tools: state.json > commit-scope > type-heuristic
   - Context tools: commit-scope > state.json > type-heuristic
   - Expliciet getest per tool

3. **Consistente phase-output tussen tools**
   - get_work_context, get_project_plan, git_add_or_commit gebruiken zelfde resolver
   - DRY: Single ScopeDecoder utility met precedence logic

4. **Audit/transition gedrag via state-engine blijft intact**
   - transition_phase valideert tegen state.json
   - force_phase_transition tracked skip_reason + human_approval
   - PhaseStateEngine contracts ongewijzigd

---

## Referentiepunten

- **[docs/reference/mcp/tools/project.md](../../reference/mcp/tools/project.md):** Runtime-state rationale, PhaseStateEngine
- **[docs/reference/mcp/tools/git.md](../../reference/mcp/tools/git.md):** Git-tooling huidige TDD-focus
- **[.gitignore:74](../../../.gitignore):** state.json bewust niet-versioned
- **[mcp_server/managers/phase_state_engine.py](../../../mcp_server/managers/phase_state_engine.py):** Forced transitions, audit trail
- **[mcp_server/tools/project_tools.py](../../../mcp_server/tools/project_tools.py):** Initialize project, state contracts
- **[tests/.../test_initialize_project_tool.py](../../../tests/unit/mcp_server/tools/test_initialize_project_tool.py):** State contracts
- **[docs/coding_standards/README.md][related-2]**
- **[Issue #117 (get_work_context)][related-3]**
- **[Issue #139 (get_project_plan)][related-4]**

<!-- Link definitions -->
[related-1]: research.md
[related-2]: ../../coding_standards/README.md
[related-3]: https://github.com/owner/SimpleTraderV3/issues/117
[related-4]: https://github.com/owner/SimpleTraderV3/issues/139

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-02-14T19:00:00+00:00 | Agent | Correcties: research v2.2 refs, link definitions, Cycle 3 precedence expliciet |
| 1.0 | 2026-02-14T18:25:00+00:00 | Agent | Initial draft |

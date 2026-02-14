# Issue #138 Implementation Planning - Workflow-First Vertical Cycles

**Status:** DRAFT  
**Version:** 1.3
**Last Updated:** 2026-02-14

---

## Purpose

Break down workflow-first architecture into vertical delivery cycles, each producing working system with **deterministic phase detection** (NO type-heuristic guessing).

## Scope

**In Scope:**
Vertical slice planning (phase-resolution + fallback to unknown), Exit criteria (functional + compatibility + observability), No-regression contracts, Issues #117/#139 integration, Test strategy, **strict sub_phase validation**, **coordination phase support**

**Out of Scope:**
Design details (HOW to implement), Code structure, Implementation approaches, Detailed schemas (those go in design phase)

## Prerequisites

Read these first:
1. Issue #138 research v2.3 complete (deterministic detection)
2. Workflow-first architecture chosen (dual-source model)
3. **Deterministic phase detection** as non-negotiable (no guessing)
4. User feedback: vertical cycles not horizontal layers
---

## Summary

Vertical slice implementation of workflow-first commit conventions with **deterministic phase detection**. Each cycle delivers working functionality: (1) Phase resolution with fallback to unknown, (2) Scope encoding/decoding with strict validation, (3) Tool integration (#117/#139), (4) Consolidation. Non-negotiable: old commits never block tools, unknown phase is acceptable outcome.

---

## Dependencies

- workphases.yaml schema (includes coordination phase, subphase whitelists)
- Scope parser library (re module)
- GitConfig singleton pattern (existing)

---

## TDD Cycles

### Cycle 1: Phase Resolution + Deterministic Detection (Dual-Source)

**Goal:** Commit-scope parsing met state.json fallback, **NO type-heuristic guessing**, oude commits blijven werken

**Deliverables:**
1. workphases.yaml (config-SSOT voor phase definitions + subphase whitelists - runtime state blijft in state.json)
2. Scope parser/decoder (ScopeDecoder.extract_from_commit())
3. **Deterministic precedence resolver (commit-scope > state.json > unknown)**
4. get_work_context integration (#117 fix - met deterministische precedence)
5. PhaseDetectionResult met error_message field (actionable recovery instructions)
6. Contract tests (scope parsing + fallback scenarios + unknown handling)
7. Integration test: old commit format graceful handling → unknown phase acceptable

**Exit Criteria:**
- **Functional:** get_work_context implements **deterministic precedence: commit-scope > state.json > unknown** (NO type-heuristic)
- **Compatibility:** All existing branches/commits continue working (no blocking errors, unknown phase logged)
- **Observability:** Clear logging van bron (scope, state.json, unknown) + error_message met recovery actions

**No-Regression Contract:**
```python
# NEW FORMAT - Commit-scope primary
commit_message = "test(P_TDD_SP_C1_RED): add tests"
result = decoder.detect_phase(commit_message)
assert result.workflow_phase == "tdd"
assert result.sub_phase == "c1_red"
assert result.source == "commit-scope"
assert result.confidence == "high"

# OLD FORMAT - Graceful fallback to state.json or unknown
commit_message = "test: add tests"  # No scope
result = decoder.detect_phase(commit_message, fallback_to_state=True)
# Try 1: Parse scope → None
# Try 2: Read state.json → "tdd" (if exists)
# Try 3: NO type-heuristic → unknown (if state.json missing)
assert result.workflow_phase in ["tdd", "unknown"]  # Depends on state.json availability
assert result.source in ["state.json", "unknown"]
if result.source == "unknown":
    assert result.error_message is not None  # Must include recovery action

# Unknown phase with actionable error
commit_message = "feat: implement X"  # No scope, no state.json
result = decoder.detect_phase(commit_message, fallback_to_state=False)
assert result.workflow_phase == "unknown"
assert result.source == "unknown"
assert "Recovery:" in result.error_message  # Actionable instructions
assert "transition_phase" in result.error_message or "P_PHASE" in result.error_message
```

**Critical:** state.json blijft authoritative voor transition_phase (niet gewijzigd in Cycle 1)

---

### Cycle 2: Scope Encoding + Strict Validation

**Goal:** NEW commits use workflow-first format, **strict sub_phase validation**, coordination phase support

**Deliverables:**
1. Scope encoder utility (ScopeEncoder.encode(phase, subphase, cycle))
2. **Strict sub_phase validation** (must exist in workphases.yaml[phase].subphases)
3. GitManager.commit_with_scope(type, scope, message, files)
4. GitCommitInput schema update (workflow_phase, sub_phase, commit_type fields)
5. **coordination phase** added to workphases.yaml (for epic delegation)
6. git.yaml extension (commit_types, scope_format specification)
7. **Actionable error messages** (Issue #121): what failed, valid values, exact recovery
8. Integration test: new commit workflow (full git_add_or_commit cycle)

**Exit Criteria:**
- **Functional:** git_add_or_commit accepts 7 workflow phases (including coordination), **validates sub_phase strictly**
- **Compatibility:** GitManager handles mixed commit history (old + new formats)
- **Observability:** Validation errors show **what failed, valid values, recovery action** (Issue #121 lesson)

**Example:**
```python
# NEW FORMAT - GENERATED with strict validation
git_add_or_commit(
    workflow_phase="tdd",
    sub_phase="red",  # Must be in ["red", "green", "refactor"]
    cycle=1,
    commit_type="test",
    message="add validation tests"
)
# → Generates: "test(P_TDD_SP_C1_RED): add validation tests"

# COORDINATION phase (epic delegation)
git_add_or_commit(
    workflow_phase="coordination",
    sub_phase="delegation",  # Must be in ["delegation", "sync", "review"]
    message="delegate to child issues"
)
# → Generates: "chore(P_COORDINATION_SP_DELEGATION): delegate to child issues"

# ERROR: Invalid sub_phase
git_add_or_commit(
    workflow_phase="tdd",
    sub_phase="invalid",  # NOT in configured subphases
    message="test"
)
# → ValueError with actionable message:
#    "Invalid sub_phase 'invalid' for workflow phase 'tdd'
#     Valid subphases for tdd: red, green, refactor
#     Example: [...example commit...]
#     Recovery: Use one of the valid subphases listed above."
```

---

### Cycle 3: Tool Integration + Issue #139 Fix

**Goal:** get_project_plan implements deterministic precedence, all tools workflow-aware

**Deliverables:**
1. get_project_plan integration (#139 fix - commit-scope met state.json fallback → unknown)
2. workflows.yaml phase_source reference (points to workphases.yaml)
3. GitConfig deprecation notices (tdd_phases, commit_prefix_map marked deprecated)
4. End-to-end test: full workflow cycle (research → planning → design → tdd → integration → documentation)
5. **coordination phase** integrated in workflows (epic workflow type)

**Exit Criteria:**
- **Functional:** get_project_plan implements **deterministic precedence: commit-scope > state.json > unknown** (consistent met Cycle 1)
- **Compatibility:** No tool regressions (GitConfig, workflows.yaml references)
- **Observability:** Tools report phase source (commit-scope, state.json, unknown) + error_message if unknown

**Coupled Issues:**
- Issue #117: get_work_context parses commit-scope met state.json fallback → unknown (Cycle 1)
- Issue #139: get_project_plan parses commit-scope met state.json fallback → unknown (Cycle 3)
- Both use same ScopeDecoder utility with **deterministic precedence** (DRY)

---

### Cycle 4: Consolidation + Documentation

**Goal:** Complete system documented, migration notes, cleanup temporary code

**Deliverables:**
1. agent.md updates (Tool Priority Matrix, Phase 2.3 TDD cycle examples with new format, coordination phase)
2. Migration notes for old branches (mixed history OK, unknown phase logged)
3. Deprecation cleanup (remove commit_tdd_phase, commit_docs methods)
4. Full test suite validation (1798+ tests pass)
5. PR description with breaking changes

**Exit Criteria:**
- **Functional:** All 1798+ tests pass, quality gates green
- **Compatibility:** Backward compatibility validated across test suite
- **Observability:** agent.md updated, examples clear, **actionable error messages** with recovery steps

**Consolidation Tasks:**
- agent.md: Update commit examples to use new scope format (including coordination)
- CHANGELOG: Document breaking changes (GitManager API, strict sub_phase validation, type-heuristic removal)
- Migration guide: "Working with old branches" section (unknown phase is OK)
- Cleanup: Remove deprecated code paths (commit_tdd_phase, _detect_tdd_phase)

---

## Risks & Mitigation
- **Risk:** Old commits blocking tools despite fallback
  - **Mitigation:** Comprehensive contract tests for parser, test with actual old branches (fix/138, feature/137), unknown phase acceptable outcome
- **Risk:** Unknown phase confusing for agents
  - **Mitigation:** **Actionable error messages** with exact recovery steps (Issue #121 lesson), examples in agent.md
- **Risk:** Test blast radius too large (210+ assertions)
  - **Mitigation:** Contract tests first (parser isolation), then integration tests (tool boundaries)

## Related Documentation
- **[research.md v2.3][related-1]** (updated for deterministic detection)
- **[design.md v1.1][related-2]** (updated for strict validation)

---

## Acceptatiecriteria (User-Specified)

1. **Geen blocking errors op legacy commitformaten**
   - Test: Old commits (`test: add tests`) behandeling zonder errors
   - **Deterministic fallback: commit-scope > state.json > unknown** (NO type-heuristic guessing)

2. **Deterministische source precedence per tooltype**
   - Transition tools: **state.json ONLY** (no fallback, no commit parsing)
   - Context tools: **commit-scope > state.json > unknown** (NO type-heuristic)
   - Expliciet getest per tool

3. **Consistente phase-output tussen tools**
   - get_work_context, get_project_plan, git_add_or_commit gebruiken zelfde resolver
   - DRY: Single ScopeDecoder utility met **deterministische precedence** logic

4. **Audit/transition gedrag via state-engine blijft intact**
   - transition_phase valideert tegen state.json ONLY
   - force_phase_transition tracked skip_reason + human_approval
   - PhaseStateEngine contracts ongewijzigd

5. **Strict sub_phase validation** (NEW)
   - sub_phase must exist in workphases.yaml[phase].subphases
   - **Actionable error messages** (what failed, valid values, recovery action)
   - No free strings, prevents typos

6. **coordination phase support** (NEW)
   - Epic delegation workflow enabled
   - workphases.yaml includes coordination phase
   - Subphases: delegation, sync, review

---

## Referentiepunten

- **[docs/reference/mcp/tools/project.md](../../reference/mcp/tools/project.md):** Runtime-state rationale, PhaseStateEngine
- **[docs/reference/mcp/tools/git.md](../../reference/mcp/tools/git.md):** Git-tooling huidige TDD-focus
- **[.gitignore:74](../../../.gitignore):** state.json bewust niet-versioned
- **[mcp_server/managers/phase_state_engine.py](../../../mcp_server/managers/phase_state_engine.py):** Forced transitions, audit trail
- **[mcp_server/tools/project_tools.py](../../../mcp_server/tools/project_tools.py):** Initialize project, state contracts
- **[tests/.../test_initialize_project_tool.py](../../../tests/unit/mcp_server/tools/test_initialize_project_tool.py):** State contracts
- **[docs/coding_standards/README.md][related-3]**
- **[Issue #117 (get_work_context)][related-4]**
- **[Issue #139 (get_project_plan)][related-5]**

<!-- Link definitions -->
[related-1]: research.md
[related-2]: design.md
[related-3]: ../../coding_standards/README.md
[related-4]: https://github.com/owner/SimpleTraderV3/issues/117
[related-5]: https://github.com/owner/SimpleTraderV3/issues/139

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.3 | 2026-02-14 | Agent | **BREAKING:** Remove type-heuristic, add strict sub_phase validation, add coordination phase, deterministic precedence |
| 1.2 | 2026-02-14 | Agent | Fix: research v2.2 ref, verduidelijk workphases.yaml config-SSOT |
| 1.1 | 2026-02-14 | Agent | Correcties: research v2.2 refs, link definitions, Cycle 3 precedence expliciet |
| 1.0 | 2026-02-14 | Agent | Initial draft |

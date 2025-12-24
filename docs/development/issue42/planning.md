# Issue #42: Implementation Plan - Phase Workflow TDD Contradiction

**Issue:** #42 - Phase workflow contradicts TDD principles  
**Date:** 2025-12-25  
**Phase:** Planning  
**Status:** IN PROGRESS

## Executive Summary

Implement 8-phase flat model to replace current 7-phase SDLC workflow. This provides the foundation for Issue #18 enforcement implementation by establishing correct phase semantics (research → planning → design → red → green → refactor → integration → documentation).

**Scope:** Foundational phase structure changes only. Enforcement logic remains in Issue #18.

## Objectives

### Primary Goal
Create working 8-phase system that:
1. Uses semantically correct phase names (red/green/refactor instead of component/tdd)
2. Supports multiple TDD cycles per issue (refactor → red transition)
3. Properly separates design (docs) from implementation (code)
4. Provides foundation for Issue #18 enforcement

### Non-Goals (Out of Scope)
- ❌ PolicyEngine implementation (Issue #18)
- ❌ Scaffold enforcement logic (Issue #18)
- ❌ Commit gating enforcement (Issue #18)
- ❌ Quality gates integration (Issue #18)
- ❌ Artifact validation enforcement (Issue #18)

## Work Packages

### WP1: Update PHASE_TEMPLATES
**Deliverable:** Modified `mcp_server/managers/project_manager.py`

**Changes:**
- Rename "discovery" → "research"
- Replace "component" → "red", "green", "refactor"
- Update all 5 issue type templates (feature, bug, docs, refactor, hotfix)
- Update phase counts and descriptions

**Acceptance Criteria:**
- [ ] All 5 templates use new 8-phase names
- [ ] Feature template: research → planning → design → red → green → refactor → integration → documentation
- [ ] Bug template: research → planning → red → green → refactor → integration → documentation (skip design)
- [ ] Refactor template: research → planning → red → green → refactor → integration → documentation (skip design)
- [ ] Docs template: research → planning → design → documentation (skip TDD phases)
- [ ] Hotfix template: red → green → refactor (minimal, requires approval)

**Dependencies:** None (independent work package)

**Estimate:** Small (1-2 hours)

---

### WP2: Update PhaseStateEngine Transitions
**Deliverable:** Modified `mcp_server/core/phase_state_engine.py`

**Changes:**
- Add "research" phase to transition map
- Replace "component"/"tdd" validation with red/green/refactor
- Add `refactor → red` transition (multiple TDD cycles)
- Update transition validation logic

**Acceptance Criteria:**
- [ ] `_is_valid_transition()` accepts research → planning
- [ ] `_is_valid_transition()` accepts design → red (enter TDD)
- [ ] `_is_valid_transition()` accepts red → green → refactor
- [ ] `_is_valid_transition()` accepts refactor → red (next cycle)
- [ ] `_is_valid_transition()` accepts refactor → integration (exit TDD)
- [ ] `_is_valid_transition()` rejects invalid transitions (e.g., green → integration)

**Dependencies:** None (independent work package)

**Estimate:** Small (1-2 hours)

---

### WP3: Test New Phase Structure
**Deliverable:** New test file `tests/unit/mcp_server/test_8_phase_model.py`

**Test Coverage:**
1. **PHASE_TEMPLATES tests:**
   - Feature template has 8 phases
   - Bug template skips design (7 phases)
   - Docs template skips TDD phases (4 phases)
   - All templates use correct phase names

2. **PhaseStateEngine transition tests:**
   - Valid transitions succeed
   - Invalid transitions fail with descriptive error
   - Multiple TDD cycles work (refactor → red → green → refactor)
   - Transition history tracked correctly

3. **InitializeProjectTool tests:**
   - Project initialized with new phase names
   - `.st3/projects.json` contains correct phases
   - First phase is "research" (not "discovery")

4. **TransitionPhaseTool tests:**
   - Transitions work with new phase names
   - Phase guidance available for all 8 phases (stub data OK for now)

**Acceptance Criteria:**
- [ ] All PHASE_TEMPLATES tests pass
- [ ] All PhaseStateEngine transition tests pass
- [ ] All tool integration tests pass
- [ ] Test coverage ≥ 90% for modified code

**Dependencies:** WP1 + WP2 (tests validate changes)

**Estimate:** Medium (4-6 hours)

---

### WP4: Update Documentation
**Deliverable:** Updated phase documentation

**Changes:**
1. Update `docs/mcp_server/PHASE_WORKFLOWS.md` (if exists)
2. Add phase transition diagram
3. Document 8-phase model in README/architecture docs
4. Update Issue #18 V2 plan references (mark as outdated, point to new model)

**Acceptance Criteria:**
- [ ] Phase documentation reflects 8-phase model
- [ ] Transition diagram shows all valid transitions
- [ ] Multiple TDD cycles documented (refactor → red)
- [ ] Issue #18 V2 plan has disclaimer about phase naming

**Dependencies:** WP1 + WP2 (document what exists)

**Estimate:** Small (2-3 hours)

---

### WP5: Integration Testing
**Deliverable:** Working end-to-end workflow

**Test Scenario:**
1. Initialize project with new issue type
2. Transition through all phases (research → planning → design → red)
3. Execute multiple TDD cycles (red → green → refactor → red → green → refactor)
4. Complete integration and documentation phases
5. Verify state tracking throughout

**Acceptance Criteria:**
- [ ] `initialize_project` creates correct phase list
- [ ] `transition_phase` works for all valid transitions
- [ ] Multiple TDD cycles execute successfully
- [ ] `.st3/state.json` tracks all transitions
- [ ] `.st3/projects.json` remains consistent

**Dependencies:** WP1 + WP2 + WP3 (all components working)

**Estimate:** Small (2-3 hours)

---

## Dependency Graph

```
WP1: PHASE_TEMPLATES ─┐
                       ├─→ WP3: Tests ─→ WP5: Integration
WP2: PhaseStateEngine ─┘       ↓
                            WP4: Docs
```

**Critical Path:** WP1 → WP3 → WP5 (sequential)  
**Parallel Work:** WP2 can run parallel with WP1, WP4 can run parallel with WP3

## Execution Strategy

### Phase 1: Design (Next Phase)
**Goal:** Design technical implementation for WP1 and WP2

**Activities:**
- Design new PHASE_TEMPLATES structure
- Design PhaseStateEngine transition map
- Identify edge cases and validation rules
- Plan backward compatibility (if needed)

**Deliverable:** Design document with code examples

---

### Phase 2: Red (Test-First)
**Goal:** Write tests for new 8-phase model (WP3)

**Activities:**
- Write PHASE_TEMPLATES tests (expected phase lists)
- Write PhaseStateEngine transition tests (valid/invalid)
- Write tool integration tests (initialize + transition)

**Deliverable:** Failing tests that specify desired behavior

---

### Phase 3: Green (Implementation)
**Goal:** Implement changes to make tests pass (WP1 + WP2)

**Activities:**
- Update PHASE_TEMPLATES in project_manager.py
- Update transitions in phase_state_engine.py
- Run tests until all pass

**Deliverable:** Working 8-phase model with passing tests

---

### Phase 4: Refactor (Code Quality)
**Goal:** Improve code quality and add documentation

**Activities:**
- Refactor for readability (if needed)
- Add inline comments explaining phase logic
- Update docstrings

**Deliverable:** Clean, maintainable code

---

### Phase 5: Integration (System Test)
**Goal:** Validate complete workflow (WP5)

**Activities:**
- Execute end-to-end test scenario
- Test multiple TDD cycles
- Verify state persistence
- Check for regressions

**Deliverable:** Verified working system

---

### Phase 6: Documentation (User-Facing)
**Goal:** Update all documentation (WP4)

**Activities:**
- Update PHASE_WORKFLOWS.md
- Add transition diagram
- Update architecture docs
- Mark Issue #18 V2 plan as outdated

**Deliverable:** Complete documentation

---

## Risk Management

### Risk 1: Breaking Changes in Active Branches
**Risk:** Issue #18 branch may have conflicts with phase name changes

**Mitigation:**
1. Coordinate merge strategy with Issue #18 work
2. Consider feature flag for gradual rollout
3. Document migration guide for active branches

**Contingency:** Rebase Issue #18 branch after #42 merge

---

### Risk 2: Existing .st3/projects.json Files
**Risk:** Existing project files use old phase names

**Mitigation:**
1. No enforced projects exist yet (confirmed in research)
2. If needed: write migration script to update phase names
3. PhaseStateEngine can validate against both old/new names temporarily

**Contingency:** Manual update of .st3/projects.json for test projects

---

### Risk 3: Test Coverage Gaps
**Risk:** Edge cases not covered in initial tests

**Mitigation:**
1. Comprehensive test plan in WP3
2. Integration testing in WP5
3. Manual testing of phase transitions

**Contingency:** Add tests as issues discovered

---

## Success Criteria

### Functional Requirements
- [ ] All 5 issue types use 8-phase model
- [ ] PhaseStateEngine validates new phase transitions
- [ ] InitializeProjectTool creates projects with new phases
- [ ] TransitionPhaseTool works with all phase transitions
- [ ] Multiple TDD cycles supported (refactor → red)

### Quality Requirements
- [ ] Test coverage ≥ 90% for modified code
- [ ] No regressions in existing functionality
- [ ] All existing tests still pass (or updated appropriately)
- [ ] Documentation complete and accurate

### Integration Requirements
- [ ] Changes compatible with Issue #18 enforcement plans
- [ ] Clean merge path from #42 → main → #18
- [ ] No breaking changes to MCP tool interfaces

## Timeline Estimate

| Work Package | Effort | Dependencies |
|--------------|--------|--------------|
| WP1: PHASE_TEMPLATES | 1-2h | None |
| WP2: PhaseStateEngine | 1-2h | None |
| WP3: Tests | 4-6h | WP1 + WP2 |
| WP4: Documentation | 2-3h | WP1 + WP2 |
| WP5: Integration | 2-3h | WP1 + WP2 + WP3 |
| **Total** | **10-16h** | Sequential: WP1/WP2 → WP3 → WP5 |

**Parallel execution:** WP1 and WP2 can run simultaneously, reducing to ~12h total

## Handover to Design Phase

### Completed Artifacts
- ✅ Research document (problem analysis, alternatives, decision)
- ✅ Planning document (this document)

### Ready for Design
- ✅ Work packages defined and scoped
- ✅ Dependencies mapped
- ✅ Acceptance criteria clear
- ✅ Risks identified with mitigations

### Design Phase Goals
1. Design PHASE_TEMPLATES structure (exact dict format)
2. Design PhaseStateEngine transition map (state machine diagram)
3. Design test cases (concrete test scenarios)
4. Design migration strategy (if backward compatibility needed)

**Status:** Planning phase COMPLETE. Ready for Design phase.

## Appendix: Scope Boundaries

### In Scope (Issue #42)
- ✅ PHASE_TEMPLATES modification
- ✅ PhaseStateEngine transition updates
- ✅ Basic tests for phase structure
- ✅ Documentation of new model
- ✅ Integration testing

### Out of Scope (Issue #18)
- ❌ PolicyEngine implementation
- ❌ Scaffold validation ENFORCEMENT
- ❌ Commit gating logic
- ❌ Quality gates integration
- ❌ Artifact validation logic
- ❌ Tool usage tracking
- ❌ Human approval workflows

### Gray Area (Discuss)
- ⚠️ Scaffold validation RULES (define in #42, enforce in #18?)
- ⚠️ Phase guidance content (stub in #42, complete in #18?)
- ⚠️ TransitionPhaseTool enhancements (basic in #42, approval in #18?)

**Resolution:** Document rules/guidance in #42, implement enforcement in #18.

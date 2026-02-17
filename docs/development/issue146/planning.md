<!-- docs/development/issue146/planning.md -->
<!-- template=planning version=130ac5ea created=2026-02-17T10:30:00Z updated= -->
# Issue #146 TDD Cycle Tracking & Validation - Planning

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-17T10:30:00Z

---

## Purpose

Define architecture decisions, component design, and implementation strategy for TDD cycle tracking system

## Scope

**In Scope:**
Schema design, validation logic, state management, discovery tool enhancements, transition semantics, error handling

**Out of Scope:**
Implementation code, test writing, integration testing (TDD phase)

## Prerequisites

Read these first:
1. Research questions answered (Q1-Q8)
2. User decisions documented
3. Section 5 alternatives evaluated
---

## Summary

Planning document for TDD cycle tracking feature. Answers 8 research questions, defines comprehensive schema with cycle+phase exit criteria, strict validation strategy, persistent state matching PhaseStateEngine patterns, discovery tool enhancements with dual JSON/text output, and forward-only transitions with force override support.

---

## TDD Cycles

### Cycle 1: Schema & Storage
**Goal:** Define and implement planning deliverables and state management schemas

**Deliverables:**
- ProjectManager.planning_deliverables schema
- PhaseStateEngine.tdd_cycle_* fields

**Tests:**
- Schema validation catches malformed planning_deliverables
- State management correctly initializes/clears cycle fields

**Exit Criteria:** Schema validated, tests pass

---

### Cycle 2: Validation Logic
**Goal:** Implement cycle number validation and planning deliverables checks

**Deliverables:**
- Cycle number validation
- Planning deliverables checks
- Error messages

**Tests:**
- Missing cycle_number rejected
- Out-of-range cycle_number rejected
- Exit criteria validation works

**Exit Criteria:** All validation scenarios covered

---

### Cycle 3: Discovery Tools
**Goal:** Enhance get_work_context and get_project_plan with cycle info

**Deliverables:**
- get_work_context enhancement
- get_project_plan enhancement
- JSON+text formatting

**Tests:**
- Tools show cycle info when planning exists
- Tools omit cycle info when planning missing
- Dual-format output validated

**Exit Criteria:** Tools return cycle info correctly

---

### Cycle 4: Transition Tools
**Goal:** Implement transition_cycle and force_cycle_transition tools

**Deliverables:**
- transition_cycle tool
- force_cycle_transition tool
- Entry/exit hooks

**Tests:**
- Forward transitions work
- Backward transitions blocked
- Force transitions create audit trail

**Exit Criteria:** All transition patterns working

---

## Architecture Decisions (Research Q&A)

### Q1: Per-Cycle Deliverables Structure
**Decision:** ✅ Full deliverables list (not just cycle names)

**Rationale:**
- Enables exit criteria validation per cycle
- Supports TDD cycle planning workflow
- Provides clear tracking of what needs to be built

**Schema:**
```json
{
  "cycle": 1,
  "name": "Schema Design",
  "deliverables": [
    "ProjectManager.planning_deliverables schema",
    "PhaseStateEngine.tdd_cycle_* fields"
  ],
  "exit_criteria": "All schema tests pass"
}
```

---

### Q2: Exit Criteria Levels
**Decision:** ✅ Both cycle-level AND phase-level exit criteria

**Clarification:** Phase-level exit criteria (not "project-level" - we're talking phase transitions).

**Rationale:**
- **Cycle-level:** Granular checkpoints prevent incomplete cycles
- **Phase-level:** Overall TDD phase completion gatekeeping
- **Transition blocking:** Force transitions required when criteria not met

**Schema:**
```json
{
  "planning_deliverables": {
    "tdd_cycles": {
      "total": 4,
      "cycles": [
        {
          "cycle": 1,
          "exit_criteria": "Schema validated, tests pass"  // Cycle-level
        }
      ],
      "phase_exit_criteria": "All 4 cycles complete, quality gates green"  // Phase-level
    }
  }
}
```

**Enforcement:**
- `transition_cycle(to_cycle=2)` → validates cycle 1 exit criteria (blocking)
- `transition_phase(to_phase="integration")` → validates TDD phase exit criteria (blocking)
- Failures require force tool with reason + human_approval

---

### Q3: Cycle Number Requirement Scope
**Decision:** ✅ ALL TDD commits require cycle_number

**Rationale:**
- All work during TDD happens within a cycle context (even if total_cycles=1)
- Prevents ambiguity about which cycle work belongs to
- Consistent with strict enforcement philosophy

**Examples:**
```python
# Sub-phase commits (RED/GREEN/REFACTOR)
git_add_or_commit(
    workflow_phase="tdd",
    sub_phase="red",
    cycle_number=2,  # REQUIRED
    message="add failing test"
)

# General TDD commits (docs, chores)
git_add_or_commit(
    workflow_phase="tdd",
    cycle_number=2,  # ALSO REQUIRED
    message="update cycle documentation"
)
```

---

### Q4: Planning Deliverables Enforcement Timing
**Decision:** ✅ Block at phase/cycle entry (not at first commit)

**Aangescherpt Model:** Planning deliverables lifecycle

**Workflow:**
```
1. initialize_project(issue_number=146, workflow_name="feature")
   → Creates projects.json entry with:
      - workflow_name, required_phases from workflows.yaml
      - expected_deliverables (templates):
        * research: ["research.md"]
        * planning: ["planning.md", "planning_deliverables"]
   → NO actual planning outcomes yet (tdd_cycles, validation_plan)

2. transition_phase(to_phase="planning")
   → Check: research.md exists
   
3. [During planning phase: answer Q1-Q8, define TDD cycles]

4. [End of planning: finalize planning deliverables]
   → Update projects.json with actual planning outcomes:
      - planning_deliverables.tdd_cycles (defined cycles)
      - planning_deliverables.validation_plan
      - planning_deliverables.documentation_plan
   → Creates planning.md

5. transition_phase(to_phase="design")
   → Check: planning.md exists
   
6. transition_phase(to_phase="tdd")
   → BLOCKS if planning_deliverables not in projects.json
   → Error: "Cannot enter TDD phase without planning deliverables"
   
7. transition_cycle(to_cycle=2)
   → BLOCKS if cycle 1 exit criteria not met
   → Requires: force_cycle_transition with reason + approval
```

**Key Distinction:**
- **initialize_project**: Sets expectations (template/schema requirements)
- **Planning phase**: Defines actual deliverables (tdd_cycles content)
- **TDD entry validation**: Checks planning outcomes exist (not just templates)

**Entry Validation:**
- TDD phase entry: Check planning_deliverables.tdd_cycles exists and total > 0
- Cycle transition: Check previous cycle exit criteria met
- Preventive (not reactive) - catch missing planning BEFORE work starts

---

### Q5: Cycle Info Visibility in Discovery Tools
**Decision:** ✅ Conditional on TDD phase (matches research.md:314)

**Clarification:** `get_work_context` is agent tool, not direct user output.

**Behavior:**
```json
// During DESIGN phase (planning exists, but NOT in TDD)
{
  "workflow_phase": "design"
  // NO tdd_cycle_info shown (not in TDD yet)
}

// During TDD phase (planning exists AND in TDD)
{
  "workflow_phase": "tdd",
  "tdd_cycle_info": {
    "current": 2,
    "total": 4,
    "name": "Validation Logic",
    "status": "in_progress"
  }
}
```

**Rationale:**
- Cycle info only relevant during TDD phase (when cycles are active)
- Outside TDD: get_project_plan shows full planning_deliverables (if needed)
- Consistent with research.md:314 conditional visibility decision
- Reduces noise in get_work_context for non-TDD phases

---

### Q6: Output Formatting Strategy
**Decision:** ✅ Both JSON (agents) + human-readable text (developers)

**Implementation:**

**A. get_work_context (frequent, agent-focused)**
- Compact JSON for token efficiency:
```json
"tdd_cycle_info": {
  "current": 2,
  "total": 4,
  "name": "Validation Logic",
  "status": "in_progress"
}
```

**B. Terminal output (transition confirmations, errors)**
- Human-readable text:
```
✅ Transitioned to TDD Cycle 2/4: Validation Logic

Deliverables:
  - Cycle number validation
  - Planning deliverables checks
Exit criteria: All validation scenarios covered
```

---

### Q7: Skip Cycle Transition Requirements
**Decision:** ✅ Yes - skip_reason + human_approval required

**Pattern:** Mirror `force_phase_transition` exactly

**Implementation:**
```python
# Skip transition
transition_cycle(to_cycle=3)  # 1→3 (skip cycle 2)
→ ERROR: "Non-sequential cycle transition. Use force_cycle_transition."

# Force transition
force_cycle_transition(
    to_cycle=3,
    skip_reason="Cycle 2 covered by epic parent tests",
    human_approval="User: John approved 2026-02-17"
)
→ ✅ Allowed (audit trail created)
```

---

### Q8: Re-Entry Behavior After TDD Phase Exit
**Decision:** ✅ Always possible with force_transition

**Workflow:**
```
TDD (cycles 1-4) → Integration → [bug found]

force_phase_transition(
    to_phase="tdd",
    skip_reason="Critical bug found during integration",
    human_approval="User: John approved 2026-02-17"
)
→ ✅ Allowed

# State after re-entry
{
  "current_tdd_cycle": 5,  // Smart resume: last_tdd_cycle + 1
  "last_tdd_cycle": 4      // Historical record
}

# Auto-resumed from last_tdd_cycle + 1 (if within total_planned_cycles)
# ✅ Assumes planning has total_cycles >= 5
```

---

## Schema Design

### Planning Deliverables Schema (projects.json)

**Location:** `.st3/projects.json[<issue_number>]["planning_deliverables"]`

**Structure:**
```json
{
  "146": {
    "issue_number": 146,
    "workflow_name": "feature",
    "planning_deliverables": {
      "tdd_cycles": {
        "total": 4,
        "phase_exit_criteria": "All cycles complete, quality gates green",
        "cycles": [
          {
            "cycle": 1,
            "name": "Schema & Storage",
            "deliverables": [
              "ProjectManager.planning_deliverables schema",
              "PhaseStateEngine.tdd_cycle_* fields"
            ],
            "exit_criteria": "Schema validated, tests pass",
            "status": "completed"
          }
        ]
      },
      "validation_plan": {
        "objectives": ["Smoke tests", "Performance"],
        "exit_criteria": "All smoke tests green"
      },
      "documentation_plan": {
        "sections": ["API Docs", "Architecture Update"],
        "exit_criteria": "Docs reviewed and merged"
      }
    }
  }
}
```

**Validation Rules:**
- `tdd_cycles.total` must match `len(tdd_cycles.cycles)`
- Each cycle must have unique `cycle` number (1-based sequential)
- `deliverables` array must not be empty
- `exit_criteria` string must not be empty
- `status`: "planned" | "in_progress" | "completed" | "skipped"

---

### State Management Schema (state.json)

**Location:** `.st3/state.json`

**New Fields:**
```json
{
  "branch": "feature/146-tdd-cycle-tracking",
  "current_phase": "tdd",
  
  "current_tdd_cycle": 2,           // Active cycle (null if not in TDD)
  "last_tdd_cycle": 2,              // Historical (persists after TDD exit)
  
  "tdd_cycle_history": [
    {
      "cycle": 1,
      "name": "Schema & Storage",
      "entered": "2026-02-15T10:00:00Z",
      "completed": "2026-02-16T14:30:00Z",
      "forced": false
    },
    {
      "cycle": 2,
      "name": "Validation Logic",
      "entered": "2026-02-16T14:35:00Z",
      "completed": null,
      "forced": false
    }
  ]
}
```

**Lifecycle:**
1. **TDD entry (first time):** `current_tdd_cycle` = 1 (auto-initialize)
2. **TDD entry (re-entry, incomplete):** `current_tdd_cycle` = last_tdd_cycle + 1 (smart resume)
3. **TDD entry (re-entry, complete):** BLOCKED - requires replanning or new issue
4. **During TDD:** `current_tdd_cycle` = N (1-based)
5. **TDD exit:** `current_tdd_cycle` = null, `last_tdd_cycle` = N (retained)

## Validation Strategy

### Planning Deliverables Validation

**Trigger:** Phase transitions, cycle transitions

**Logic:**
```python
def validate_planning_deliverables(issue_number: int):
    project = load_project(issue_number)
    
    if "planning_deliverables" not in project:
        raise ValidationError("Planning deliverables not found")
    
    cycles = project["planning_deliverables"]["tdd_cycles"]
    
    if cycles["total"] != len(cycles["cycles"]):
        raise ValidationError(f"total mismatch: {cycles['total']} != {len(cycles['cycles'])}")
    
    for cycle_data in cycles["cycles"]:
        if not cycle_data.get("deliverables"):
            raise ValidationError(f"Cycle {cycle_data['cycle']}: deliverables missing")
```

---

### Cycle Number Validation

**Trigger:** `git_add_or_commit()` with `workflow_phase="tdd"`

**Logic:**
```python
def validate_cycle_number(cycle_number: int | None, issue_number: int):
    if cycle_number is None:
        raise ValidationError("cycle_number required for all TDD commits")
    
    project = load_project(issue_number)
    if "planning_deliverables" not in project:
        raise ValidationError("Cannot commit to TDD without planning deliverables")
    
    total_cycles = project["planning_deliverables"]["tdd_cycles"]["total"]
    
    if cycle_number < 1 or cycle_number > total_cycles:
        raise ValidationError(f"cycle_number {cycle_number} out of range (1-{total_cycles})")
```

---

### Exit Criteria Validation

**Trigger:** `transition_cycle()`, `transition_phase(from="tdd")`

**Logic:**
```python
def validate_exit_criteria(issue_number: int, cycle_number: int):
    project = load_project(issue_number)
    cycle_data = get_cycle_data(project, cycle_number)
    
    # Check deliverables completed (implementation TBD in TDD phase)
    for deliverable in cycle_data["deliverables"]:
        if not is_deliverable_complete(deliverable):
            raise ValidationError(f"Deliverable incomplete: {deliverable}")
    
    # Check exit criteria (implementation TBD in TDD phase)
    if not check_exit_criteria(cycle_data["exit_criteria"]):
        raise ValidationError(f"Exit criteria not met: {cycle_data['exit_criteria']}")
```

---

## Discovery Tool Enhancements

### get_work_context Enhancement

**Changes:**
- Add `tdd_cycle_info` section (conditional on TDD phase only)
- Compact JSON format
- Graceful degradation if planning_deliverables missing

**Output (during TDD phase):**
```json
{
  "workflow_phase": "tdd",
  "tdd_cycle_info": {
    "current": 2,
    "total": 4,
    "name": "Validation Logic",
    "status": "in_progress",
    "deliverables": ["Cycle validation", "Error messages"],
    "exit_criteria": "All validation scenarios covered"
  }
}
```

---

### get_project_plan Enhancement

**Changes:**
- Add `planning_deliverables` section (full structure)

**Output:**
```json
{
  "issue_number": 146,
  "workflow_name": "feature",
  "current_phase": "tdd",
  "planning_deliverables": {
    "tdd_cycles": {
      "total": 4,
      "phase_exit_criteria": "All cycles complete",
      "cycles": [...]
    }
  }
}
```

---

## Transition Semantics

### transition_cycle Tool

**Signature:**
```python
def transition_cycle(
    to_cycle: int,
    issue_number: int | None = None
) -> TransitionResult
```

**Validation:**
1. Check current phase = "tdd"
2. Check planning_deliverables exists
3. Check `to_cycle > current_cycle` (forward-only)
4. Check previous cycle exit criteria met
5. Update state.json

**Example:**
```python
transition_cycle(to_cycle=2)
→ ✅ Success (forward, sequential)

transition_cycle(to_cycle=4)
→ ❌ ERROR: "Non-sequential. Use force_cycle_transition."
```

---

### force_cycle_transition Tool

**Signature:**
```python
def force_cycle_transition(
    to_cycle: int,
    skip_reason: str,
    human_approval: str,
    issue_number: int | None = None
) -> TransitionResult
```

**Audit Trail:**
```json
{
  "cycle": 4,
  "entered": "2026-02-17T11:00:00Z",
  "forced": true,
  "skip_reason": "Cycles 2-3 covered by epic",
  "human_approval": "User: John approved 2026-02-17",
  "skipped_cycles": [2, 3]
}
```

---

### Phase Entry/Exit Hooks

**TDD Phase Entry:**
```python
def on_enter_tdd_phase(issue_number: int):
    """Smart resume or auto-initialize based on last_tdd_cycle."""
    validate_planning_deliverables(issue_number)
    
    total_cycles = get_total_cycles(issue_number)
    last_cycle = state.get("last_tdd_cycle")
    
    if last_cycle:
        # Re-entry: check if complete
        if last_cycle >= total_cycles:
            raise PhaseTransitionError("TDD complete - requires replanning or new issue")
        state["current_tdd_cycle"] = last_cycle + 1  # Smart resume
    else:
        state["current_tdd_cycle"] = 1  # First entry
    
    state["tdd_cycle_history"] = []
```
**TDD Phase Exit:**
```python
def on_exit_tdd_phase():
    state["last_tdd_cycle"] = state["current_tdd_cycle"]
    state["current_tdd_cycle"] = null
    validate_phase_exit_criteria()
```

---

## Error Handling Patterns

### Missing Planning Deliverables

**Trigger:** `transition_phase(to_phase="tdd")`

**Error:**
```
❌ Cannot enter TDD phase without planning deliverables

Context: Planning deliverables NOT FOUND in projects.json

Recovery: Update projects.json with planning_deliverables
```

---

### Missing Cycle Number

**Trigger:** `git_add_or_commit(workflow_phase="tdd")` without cycle_number

**Error:**
```
❌ cycle_number required for TDD commits

Current: test(P_TDD_SP_RED): add test
Required: test(P_TDD_SP_C2_RED): add test

Recovery: Add cycle_number parameter
```

---

### Invalid Cycle Number

**Trigger:** cycle_number > total_cycles

**Error:**
```
❌ cycle_number exceeds planned cycles

Attempted: 5
Allowed: 1-4

Recovery:
1. Fix commit message
2. Update planning_deliverables.tdd_cycles.total
```

---

### Exit Criteria Not Met

**Trigger:** `transition_cycle()` when criteria incomplete

**Error:**
```
❌ Cycle 2 exit criteria not met

Exit Criteria: "All validation scenarios covered"

Incomplete:
  ❌ Error message templates

Recovery:
1. Complete deliverables (recommended)
2. force_cycle_transition with reason + approval
```

---

## Integration with Existing Systems

### PhaseStateEngine
- Mirror transition patterns (forward-only, force with approval)
- Extend phase_history for tdd_cycle_history
- Reuse validation logic

### GitManager
- Add cycle_number validation to commit workflow
- Generate scope: `P_TDD_SP_C{N}_{SUBPHASE}`
- Error messages integrated

### Discovery Tools
- Extend GetWorkContextTool with cycle info (conditional on TDD phase)
- Extend GetProjectPlanTool with planning_deliverables
- Graceful degradation when planning_deliverables missing (read-only tools only)

---

## Open Questions for Design Phase

### 1. Planning Deliverables Finalization Tool
**Context:** planning.md:214-218 describes workflow step "update projects.json with planning outcomes" and "creates planning.md", but no existing tool contract exists.

**Design Tasks:**
- Define tool signature (e.g., `finalize_planning_deliverables(issue_number, planning_deliverables)`)
- Determine tool location (ProjectManager? Separate planning tools module?)
- Schema validation for planning_deliverables input
- Error handling when planning.md already exists or planning_deliverables already set
- Integration with transition_phase validation (check planning complete before TDD entry)

**Note:** This is NEW functionality - not extending existing tool.

---

### 2. Integration → Validation Phase Rename
**Context:** Research.md:621-647 + original issue body #146 identified "integration" phase terminology as confusing. E2E tests are per TDD cycle (works well), but "integration" phase should be "validation" (real-life proven operation).

**Design Tasks:**
- Update workflows.yaml: Rename "integration" → "validation" in all workflows
- Migration strategy for existing projects.json with "integration" phase
- Update PhaseStateEngine transition logic (if hardcoded phase names exist)
- Update GitManager scope encoding (P_INTEGRATION → P_VALIDATION)
- Update all documentation references
- Create migration script for existing projects

**Note:** Part of Issue #146 scope - NOT separate issue.

---
- **[research.md][related-1]**
- **[../issue144/planning.md][related-2]**
- **[../../reference/mcp/phase_state_engine.md][related-3]**

<!-- Link definitions -->

[related-1]: research.md
[related-2]: ../issue144/planning.md
[related-3]: ../../reference/mcp/phase_state_engine.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-17T10:30:00Z | Agent | Initial draft |
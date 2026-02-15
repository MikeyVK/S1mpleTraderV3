<!-- docs/development/issue146/research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-15T20:45:00Z updated= -->
<!-- Demo: Auto-phase detection in integration fase -->
# tdd-cycle-tracking

**Status:** DRAFT  
**Version:** 1.2  
**Last Updated:** 2026-02-15

---

## Purpose

Design TDD cycle tracking as state machine extension, aligned with planning phase outcomes and existing phase transition architecture

## Scope

**In Scope:**
Schema design (projects.json + state.json), tool contracts (finalize_planning, transition_cycle, force_cycle_transition), validation rules, scope format impact, breaking change strategy, error message templates

**Out of Scope:**
Implementation details, test strategies, migration tooling, documentation updates (those are planning/design)

## Prerequisites

Read these first:
1. Issue #138 complete (workflow-first architecture)
2. projects.json schema understood
3. state.json schema understood
4. PhaseStateEngine patterns (transition/force_transition)

---

## Problem Statement

TDD cycle tracking is absent from workflow state machine. Planning phase outputs cycle breakdown (e.g., Issue #138 had 4 cycles), but no storage (projects.json), no live tracking (state.json), no validation (cycle_number unvalidated), no transition tools. This causes agent confusion and prevents deterministic progression.

## Research Goals

- Design projects.json tdd_cycles schema
- Design state.json cycle tracking fields
- Define tool contracts (finalize_planning, transition_cycle, force_cycle_transition)
- Establish validation rules for cycle_number
- Plan scope format breaking change strategy
- Create error message templates

## Related Documentation
- **[mcp_server/managers/phase_state_engine.py:127-170 - transition/force_transition patterns][related-1]**
- **[.st3/projects.json - Project metadata (needs tdd_cycles)][related-2]**
- **[.st3/state.json - Live state (needs current_tdd_cycle)][related-3]**
- **[backend/core/scope_encoder.py:57 - cycle_number parameter][related-4]**
- **[mcp_server/tools/git_tools.py:145 - cycle_number in GitCommitInput][related-5]**

<!-- Link definitions -->

[related-1]: mcp_server/managers/phase_state_engine.py:127-170 - transition/force_transition patterns
[related-2]: .st3/projects.json - Project metadata (needs tdd_cycles)
[related-3]: .st3/state.json - Live state (needs current_tdd_cycle)
[related-4]: backend/core/scope_encoder.py:57 - cycle_number parameter
[related-5]: mcp_server/tools/git_tools.py:145 - cycle_number in GitCommitInput

---

## Research Questions

### Q1: Planning Phase Deliverables - Broader Scope

**Finding (User Feedback):** Planning fase levert niet alleen TDD cycle breakdown, maar ook:
- **TDD Cycles:** Implementatie work packages met deliverables + exit criteria
- **Integration Plan:** MAAR - E2E tests zitten al in TDD cycles! Wat is integration fase dan?
- **Documentation Plan:** Artifacts + exit criteria voor documentation fase

**Current Problem:** Integration fase "wringt" - E2E testing gebeurt al per TDD cycle (werkt goed, geen context drift).

**Proposed Solution:**
- **Hernoemvoorstel:** Integration → "Validation" / "Acceptance" / "Real-life Testing"
- **Nieuwe definitie:** Niet E2E tests (al gedaan), maar:
  - Deployment naar staging
  - Smoke tests in productie-achtige omgeving
  - Performance validation
  - Real-world scenario's (proven operation)
  - Regression checks tegen bestaande functionaliteit

**Schema Impact:**
```json
"planning_deliverables": {
  "tdd_cycles": {
    "total": 4,
    "cycles": [
      {
        "cycle": 1,
        "name": "Phase Resolution",
        "deliverables": ["ScopeDecoder", "E2E test voor detection"],
        "integration_tests": ["test_scope_detection_e2e.py"],  // ← E2E PER CYCLE
        "exit_criteria": "Contract tests pass, E2E detection works"
      }
    ]
  },
  "validation_plan": {  // ← Hernoemd van "integration"
    "objectives": [
      "Deploy to staging environment",
      "Smoke tests (happy path scenarios)",
      "Performance baseline validation",
      "Regression against Issue #117, #139"
    ],
    "exit_criteria": "All smoke tests green, no performance regressions"
  },
  "documentation_plan": {
    "artifacts": [
      "agent.md updates (Tool Priority Matrix)",
      "Migration guide (breaking changes)",
      "CHANGELOG entry"
    ],
    "exit_criteria": "All docs reviewed, agent.md tested"
  }
}
```

**Decision:** Integration fase hernoemen naar **"validation"** (USER CONFIRMED)

**Rationale:**
- E2E tests per TDD cycle werken goed (geen context drift)
- Separate "validation" fase voor real-life proven operation
- Duidelijk onderscheid: TDD (unit+E2E per cycle) vs Validation (staging+smoke tests)
- Consistent met industry terms (acceptance testing, validation testing)
- Workflows.yaml impact: "integration" → "validation" in alle workflow definitions

---

### Q2: Force Cycle Transition Scope (CORRECTIE)

**Error in Initial Research:** Recovery option suggested `force_cycle_transition` for commits - FOUT!

**Correct Semantics:**
- `force_cycle_transition` = **STATE transition** (skip cycle 3, go to cycle 4)
- Commit errors = manual fix (amend commit message)

**Corrected Error Message:**
```
ValidationError: Commit scope missing cycle number

Current scope: P_TDD_SP_RED
Required scope: P_TDD_C{N}_SP_RED

Context:
- Current phase: tdd
- Project has 4 planned cycles (1-4)
- Current cycle: 3 (from state.json)

Valid examples:
- test(P_TDD_C3_SP_RED): add test for cycle 3
- feat(P_TDD_C3_SP_GREEN): implement feature
- refactor(P_TDD_C3_SP_REFACTOR): clean code

Recovery options:
1. Fix commit message: git commit --amend -m "test(P_TDD_C3_SP_RED): ..."
2. Update state to match commit: transition_cycle(to_cycle=expected_cycle)
3. Skip cycle (state only): force_cycle_transition(to_cycle=4, skip_reason="Cycle 3 not applicable")

Note: force_cycle_transition updates STATE, NOT commits. For commit message issues, use option 1.
```

**Impact:** Validation must be clear that forced transitions bypass cycle progression, not commit format.

---

### Q3: Schema Design - projects.json

**Planning Outcome Storage:**

```json
{
  "146": {
    "issue_title": "TDD Cycle Tracking",
    "workflow_name": "feature",
    "required_phases": ["research", "planning", "design", "tdd", "validation", "documentation"],
    
    // NEW: Planning deliverables (output van planning fase)
    "planning_deliverables": {
      "tdd_cycles": {
        "total": 3,
        "cycles": [
          {
            "cycle": 1,
            "name": "Schema Design",
            "deliverables": ["projects.json schema", "state.json schema"],
            "integration_tests": ["test_cycle_schema_validation.py"],
            "exit_criteria": "Schema validated, tests pass"
          },
          {
            "cycle": 2,
            "name": "Tool Implementation",
            "deliverables": ["finalize_planning tool", "transition_cycle tool"],
            "integration_tests": ["test_cycle_transitions_e2e.py"],
            "exit_criteria": "Tools functional, E2E test passes"
          },
          {
            "cycle": 3,
            "name": "Validation & Breaking Change",
            "deliverables": ["cycle_number validation", "scope format enforcement"],
            "integration_tests": ["test_scope_with_cycle_e2e.py"],
            "exit_criteria": "Validation strict, error messages actionable"
          }
        ]
      },
      "validation_plan": {
        "objectives": [
          "Smoke test: Create project with cycles",
          "Smoke test: Transition through cycles",
          "Regression: Old projects without cycles still work",
          "Performance: No slowdown in git operations"
        ],
        "exit_criteria": "All smoke tests green"
      },
      "documentation_plan": {
        "artifacts": [
          "agent.md: Phase 2.3 TDD Cycle examples",
          "Migration guide: Breaking changes",
          "CHANGELOG: v2.0.0 cycle tracking"
        ],
        "exit_criteria": "Docs reviewed + tested by user"
      }
    },
    
    "created_at": "2026-02-15T20:40:00Z"
  }
}
```

**Key Design Decisions:**
1. **Nested structure:** `planning_deliverables.tdd_cycles` (not top-level)
2. **Integration per cycle:** E2E tests tracked per TDD cycle (prevents context drift)
3. **Validation rename:** "integration_plan" → "validation_plan" for clarity
4. **Documentation plan:** Explicit artifacts + exit criteria

---

### Q4: Schema Design - state.json

**Live Cycle Tracking:**

```json
{
  "branch": "feature/146-cycle-tracking",
  "issue_number": 146,
  "workflow_name": "feature",
  "current_phase": "tdd",
  
  // NEW: Cycle tracking (only set when in TDD phase)
  "current_tdd_cycle": 2,
  
  // NEW: Cycle transition audit trail
  "tdd_cycle_transitions": [
    {
      "from_cycle": null,
      "to_cycle": 1,
      "timestamp": "2026-02-15T21:00:00Z",
      "human_approval": null,
      "forced": false,
      "deliverables_completed": ["projects.json schema", "state.json schema"]
    },
    {
      "from_cycle": 1,
      "to_cycle": 2,
      "timestamp": "2026-02-16T10:30:00Z",
      "human_approval": "User confirmed schema complete",
      "forced": false,
      "deliverables_completed": ["finalize_planning tool"]
    }
  ],
  
  "transitions": [ /* phase transitions blijven zoals nu */ ],
  "created_at": "2026-02-15T20:45:00Z"
}
```

**Key Design Decisions:**
1. **Conditional field:** `current_tdd_cycle` only exists when `current_phase == "tdd"`
2. **Separate audit trail:** `tdd_cycle_transitions` (parallel to phase `transitions`)
3. **Auto-initialize:** On first TDD entry, set `current_tdd_cycle = 1`
4. **Clear on exit:** On TDD → next phase, `current_tdd_cycle` retained for historical record

---

### Q5: Tool Contracts

#### **finalize_planning Tool**

```python
def finalize_planning(
    issue_number: int,
    tdd_cycles: list[dict[str, Any]],
    validation_plan: dict[str, Any],      # ← NEW
    documentation_plan: dict[str, Any],   # ← NEW
    human_approval: str | None = None
) -> dict[str, Any]:
    """Store planning deliverables in projects.json.
    
    Called at end of planning phase (or early design phase).
    
    Args:
        issue_number: Issue being planned
        tdd_cycles: List of cycle definitions
        validation_plan: Objectives + exit criteria for validation phase
        documentation_plan: Artifacts + exit criteria for documentation
        human_approval: Optional approval message
    
    Returns:
        Success + stored deliverables summary
    
    Raises:
        ValidationError: If current_phase not in ["planning", "design"]
        ValidationError: If cycles malformed (missing cycle number, name, etc.)
    """
```

#### **transition_cycle Tool**

```python
def transition_cycle(
    branch: str,
    to_cycle: int,
    deliverables_completed: list[str] | None = None,
    human_approval: str | None = None
) -> dict[str, Any]:
    """Validated sequential cycle transition.
    
    Args:
        branch: Branch name
        to_cycle: Target cycle (must be current + 1)
        deliverables_completed: Optional list of completed deliverables
        human_approval: Optional approval message
    
    Returns:
        Success + from_cycle + to_cycle
    
    Raises:
        ValidationError: If current_phase != "tdd"
        ValidationError: If to_cycle != current + 1 (non-sequential)
        ValidationError: If to_cycle > total cycles in project plan
    
    Example:
        transition_cycle("feature/146", to_cycle=2, deliverables_completed=["schema"])
    """
```

#### **force_cycle_transition Tool**

```python
def force_cycle_transition(
    branch: str,
    to_cycle: int,
    skip_reason: str,
    human_approval: str,
    deliverables_completed: list[str] | None = None
) -> dict[str, Any]:
    """Forced non-sequential cycle transition.
    
    Bypasses validation (e.g., skip cycle 3, jump to 4).
    DOES NOT affect commits - only state machine.
    
    Args:
        branch: Branch name
        to_cycle: Target cycle (any valid cycle)
        skip_reason: Reason for bypass (REQUIRED for audit)
        human_approval: Approval message (REQUIRED)
        deliverables_completed: Optional completed deliverables
    
    Returns:
        Success + from_cycle + to_cycle + forced=True + skip_reason
    
    Raises:
        ValidationError: If current_phase != "tdd"
        ValidationError: If to_cycle invalid (> total or < 1)
    
    Example:
        force_cycle_transition(
            "feature/146",
            to_cycle=4,
            skip_reason="Cycle 3 scope moved to Issue #147",
            human_approval="User approved skip on 2026-02-16"
        )
    """
```

---

## Version History

### v1.2 (2026-02-15)
- **Decision confirmed:** Integration phase renamed to "validation" (user approved)
- **Rationale added:** E2E per cycle vs validation as real-life testing
- **Impact documented:** workflows.yaml changes (integration → validation)

### v1.1 (2026-02-15)
- **Q1 expanded:** Planning phase delivers 3 components (tdd_cycles, validation_plan, documentation_plan)
- **Q2 corrected:** force_cycle_transition semantics (state-only, NOT for commit fixes)
- **Q3-Q5 added:** Complete schema designs for projects.json, state.json, tool contracts

### v1.0 (2026-02-15)
- Initial research structure
- Problem statement and research goals
- Basic research questions Q1-Q2

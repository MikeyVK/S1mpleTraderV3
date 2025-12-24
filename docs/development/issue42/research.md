# Issue #42: Research - Phase Workflow TDD Contradiction

**Issue:** Phase workflow contradicts TDD principles: component→tdd sequence  
**Date:** 2025-12-25  
**Phase:** Research  
**Status:** COMPLETED

## Problem Statement

The current 7-phase SDLC workflow enforces this sequence:
```
discovery → planning → design → component → tdd → integration → documentation
```

**Contradiction:** This implies "build first, test later" which contradicts Test-Driven Development where tests are written BEFORE implementation (RED → GREEN → REFACTOR).

### Evidence from Issue #38

During Issue #38 (SafeEditTool enhancement), proper TDD was applied during the **component phase**:
- Tests written first (RED)
- Implementation followed (GREEN)
- Code refactored (REFACTOR)
- Result: 35 passing tests, quality gates 9.95/10

When transitioning to **tdd phase**, all tests were already complete → the phase had no purpose!

## Root Cause Analysis

### Two Incompatible Phase Models

Investigation of Issue #18 V2 documentation revealed **two conflicting phase models**:

#### 1. SDLC-Level Phases (PHASE_TEMPLATES)
```python
PHASE_TEMPLATES = {
    "feature": ("discovery", "planning", "design", "component", "tdd", "integration", "documentation"),
    "bug": ("discovery", "planning", "component", "tdd", "integration", "documentation"),
    # ...
}
```

#### 2. TDD Sub-Phases (PhaseStateEngine)
```python
transitions = {
    "approved": ["red"],  # TDD entry
    "red": ["green"],     # RED → GREEN
    "green": ["refactor", "red"],  # GREEN → REFACTOR or next cycle
    "refactor": ["integration", "red"],  # REFACTOR → Integration or next cycle
}
```

### The Contradiction

| Aspect | PHASE_TEMPLATES | PhaseStateEngine |
|--------|-----------------|------------------|
| Implementation | "component" | NOT IN STATE MACHINE |
| Testing | "tdd" | NOT IN STATE MACHINE |
| TDD subfases | Not defined | red/green/refactor |
| Scaffold validation | DTOs in "component", tests in "tdd" | - |
| Commit enforcement | - | Per red/green/refactor |

**Result:** The system has two conflicting mental models that cannot coexist.

## Research: TDD Sub-Phases as Top-Level Phases

### Investigation Questions

1. **Flat vs Hierarchical:** Should red/green/refactor be top-level phases or sub-phases?
   - **Decision:** FLAT (top-level phases)
   - **Rationale:** Each has distinct tool usage, enforcement rules, and human-in-loop decision points

2. **Multiple Cycles:** Should multiple RED→GREEN→REFACTOR cycles be allowed per issue?
   - **Decision:** YES
   - **Rationale:** Complex features require multiple TDD cycles; enforce via `refactor → red` transition

3. **Backwards Compatibility:** Must existing projects remain compatible?
   - **Decision:** NO
   - **Rationale:** No enforced projects exist yet; clean slate allows proper design

4. **Scaffold Timing:** When can DTOs be scaffolded?
   - **Decision:** GREEN phase only
   - **Rationale:** Design ≠ Code. Design phase = documentation only, code starts in GREEN (after tests exist)

### Phase Naming: Discovery → Research

**Problem:** "Discovery" suggests only finding/searching, not documenting findings.

**Solution:** Rename to "Research" to reflect:
- Investigation of alternatives
- Technical feasibility analysis
- Decision documentation
- Context creation for planning/design

**Artifact:** Research docs serve as handover to planning phase.

## Proposed Solution: 8-Phase Flat Model

### New Phase Sequence

```
research → planning → design → red → green → refactor → integration → documentation
                                 ↑______________|
                                (multiple cycles via refactor→red)
```

### Phase Responsibilities

| Phase | Purpose | Artifacts | Scaffolding Allowed |
|-------|---------|-----------|---------------------|
| **research** | Investigation & alternatives | Research docs, decision docs | `design_doc`: research, alternatives, decision |
| **planning** | Implementation strategy | Implementation plans, tracking | `design_doc`: implementation_plan, tracking |
| **design** | Technical architecture | Design docs, architecture | `design_doc`: design, architecture |
| **red** | Write failing tests | Test files | `test`: unit, integration |
| **green** | Make tests pass | Implementation code | `dto`, `worker`, `adapter`, `manager`, `tool` |
| **refactor** | Improve code quality | None (edits only) | NONE - only `safe_edit_file` |
| **integration** | System integration | Integration tests | `test`: integration, e2e |
| **documentation** | User documentation | API docs, user guides | `design_doc`: reference, api, user_guide |

### Scaffold Rules (Complete)

```python
SCAFFOLD_RULES = {
    "research": {
        "design_doc": ["research", "alternatives", "decision"],
    },
    "planning": {
        "design_doc": ["implementation_plan", "tracking"],
    },
    "design": {
        "design_doc": ["design", "architecture"],
    },
    "red": {
        "test": ["unit", "integration"],
    },
    "green": {
        "dto": ["request", "response", "domain"],
        "worker": ["processor", "handler"],
        "adapter": ["api", "database", "external"],
        "manager": ["service", "orchestrator"],
        "tool": ["mcp_tool"],
    },
    "refactor": {},  # NO scaffolding - edits only
    "integration": {
        "test": ["integration", "e2e"],
        "adapter": ["integration"],
    },
    "documentation": {
        "design_doc": ["reference", "api", "user_guide"],
    }
}
```

### Commit Enforcement Rules

```python
COMMIT_ENFORCEMENT = {
    "red": {
        "requires": ["test_changes"],  # Must include test file changes
        "tests_may_fail": True,
        "quality_gates": False,  # Not checked
    },
    "green": {
        "requires": ["implementation_changes"],
        "tests_must_pass": True,
        "quality_gates": False,  # Not required yet
    },
    "refactor": {
        "requires": ["code_changes"],
        "tests_must_pass": True,
        "quality_gates_must_pass": True,  # Coverage, linting, etc.
        "only_edits_allowed": True,  # No new files
    },
}
```

### Phase Transitions

```python
VALID_TRANSITIONS = {
    "research": ["planning"],
    "planning": ["design"],
    "design": ["red"],  # Enter TDD cycle
    "red": ["green"],
    "green": ["refactor"],
    "refactor": ["red", "integration"],  # Next cycle OR done with TDD
    "integration": ["documentation"],
    "documentation": ["done"],
}
```

**Key feature:** `refactor → red` allows multiple TDD cycles within single issue.

## Artifact Validation Strategy

### Problem

Current artifacts (issue bodies, commit messages, PR descriptions) have ad-hoc structure. No enforcement of consistency across project.

### Solution: Structured Artifacts

#### Issue Body Template
```markdown
## Problem Statement
[Clear description]

## Context
[Why important? What triggered this?]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Research Phase Artifacts
- [ ] Research doc completed
- [ ] Alternatives evaluated
- [ ] Decision documented

## Related Issues
- Parent: #X
- Blocked by: #Y
```

#### Commit Message Structure (Phase-Specific)

**RED Phase:**
```
red: Add tests for user authentication
- test_user_login_success
- test_user_login_invalid_credentials
- test_user_login_account_locked
```

**GREEN Phase:**
```
green: Implement user authentication
- UserAuthenticationWorker
- AuthenticationDTO (request/response)
- Tests passing: 3/3
```

**REFACTOR Phase:**
```
refactor: Extract authentication logic to separate method
- Improved readability in UserAuthenticationWorker
- Added type hints
- Tests still passing: 3/3
- Quality gates: 9.8/10
```

#### PR Body Template
```markdown
## Changes Summary
[Brief description]

## Implementation Details
- Changed files: X
- New components: Y
- Tests added/modified: Z

## Testing
- [ ] All tests pass
- [ ] Quality gates pass (score: X/10)
- [ ] Manual testing completed

## Phase Checklist
- [ ] Research docs completed
- [ ] Design docs completed
- [ ] TDD cycles completed (RED→GREEN→REFACTOR)
- [ ] Integration tests pass
- [ ] Documentation updated

## Related Issues
Closes #X
```

### Validation Enforcement Points

| Artifact | Tool | Validation |
|----------|------|------------|
| Issue body | `create_issue` | Template compliance (required sections) |
| Commit message | `git_add_or_commit` | Phase-specific structure |
| PR body | `create_pr` | Template + checklist completion |
| Issue comments | `update_issue` | Structured updates for decisions |

## Impact Analysis

### Components Requiring Changes

| Component | Current State | Required Change | Impact Level |
|-----------|--------------|-----------------|--------------|
| **PHASE_TEMPLATES** | 5 templates with "component"/"tdd" | Update to 8-phase model | HIGH |
| **PhaseStateEngine** | Transitions include red/green/refactor | Remove "component"/"tdd" validation | LOW |
| **ProjectManager** | Initialize with 7-phase templates | Update to 8-phase templates | MEDIUM |
| **Scaffold validation** | Valid phases dict (V2 plan) | New rules per phase | HIGH |
| **Commit enforcement** | Per red/green/refactor (V2 plan) | Add quality gates checks | MEDIUM |
| **TransitionPhaseTool** | Guidance for 7 phases | Guidance for 8 phases | MEDIUM |
| **Artifact validation** | No validation | NEW component needed | HIGH |
| **Issue #18 docs** | 6,000+ lines with old phases | Update references | LARGE |

### Breaking Changes

1. ✅ **PHASE_TEMPLATES structure** - All 5 issue types change
2. ✅ **Phase names** - "component"/"tdd" → "red"/"green"/"refactor"
3. ✅ **Scaffold rules** - DTOs move from "component" to "green"
4. ✅ **Phase count** - 7 → 8 phases
5. ✅ **Artifact structure** - New validation requirements

**Mitigation:** No existing enforced projects exist; clean implementation possible.

## Alternatives Considered

### Alternative A: Hierarchical Sub-Phases

Keep "component"/"tdd" as SDLC-level phases, treat red/green/refactor as internal sub-phases.

**Rejected because:**
- ❌ Complex two-tier phase model
- ❌ Scaffold validation becomes ambiguous
- ❌ Tool usage permissions unclear
- ❌ Human-in-loop decision points hidden

### Alternative B: Rename Only (No Structure Change)

Rename "component" → "implementation", "tdd" → "verification", keep 7-phase model.

**Rejected because:**
- ❌ Doesn't solve TDD enforcement problem
- ❌ Still implies test-after-development
- ❌ Misses opportunity for proper TDD cycle enforcement
- ❌ No multiple-cycle support

### Alternative C: Single "implementation-tdd" Phase

Merge component and tdd into one phase with internal TDD enforcement.

**Rejected because:**
- ❌ Phase becomes too broad (loses focus)
- ❌ Hard to track progress (where in TDD cycle?)
- ❌ Human approval points unclear
- ❌ Scaffold validation complex

## Decision: 8-Phase Flat Model

**Selected Approach:** Promote red/green/refactor to top-level phases (8 total).

**Rationale:**
1. ✅ **Clear tool usage** - Each phase has distinct scaffold rules
2. ✅ **Explicit enforcement** - Commit rules per phase (tests required in red, passing in green, quality gates in refactor)
3. ✅ **Multiple cycles** - `refactor → red` transition enables iterative development
4. ✅ **Human-in-loop** - Phase transitions can require approval
5. ✅ **Aligns with existing code** - PhaseStateEngine already models red/green/refactor
6. ✅ **Semantic clarity** - Phase names reflect actual activities

## Next Steps (Planning Phase)

### Planning Phase Goals

1. **Design PHASE_TEMPLATES migration**
   - Update all 5 issue type templates
   - Define phase sequences per type
   - Document skip reasons

2. **Design PhaseStateEngine updates**
   - Update transition validation
   - Remove "component"/"tdd" references
   - Add "research" phase

3. **Design Scaffold Validation**
   - Implement SCAFFOLD_RULES dict
   - Create phase-based permission checks
   - Add descriptive error messages

4. **Design Artifact Validation**
   - Create ArtifactValidator component
   - Define template structures
   - Plan enforcement points

5. **Design Test Strategy**
   - Identify test coverage needs
   - Plan integration test scenarios
   - Define acceptance criteria

### Handover Artifacts

- ✅ Research doc (this document)
- ✅ Problem analysis complete
- ✅ Alternatives evaluated
- ✅ Technical decision made (8-phase flat model)
- ✅ Impact analysis complete
- ✅ Scaffold rules defined
- ✅ Artifact validation strategy outlined

**Status:** Research phase COMPLETE. Ready for Planning phase.

## References

- **Issue #42:** https://github.com/[repo]/issues/42
- **Issue #18:** Parent issue for TDD enforcement
- **Issue #38:** Evidence of TDD contradiction (working example)
- **V2 Plan:** `docs/development/mcp_server/ISSUE_18_IMPLEMENTATION_PLAN_V2.md`
- **PhaseStateEngine:** Existing transitions in V2 plan (lines 894-920)
- **Scaffold rules:** V2 plan section D.2 (lines 1410-1450)

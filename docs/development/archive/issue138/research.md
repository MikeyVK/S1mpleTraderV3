# Issue #138: Workflow-First Commit Convention Architecture

**Status:** COMPLETE  
**Version:** 2.3  
**Last Updated:** 2026-02-14

---

## Purpose

Research architectural approach for workflow-first commit conventions using Conventional Commits format, respecting dual-source model (state.json for runtime, commit-scope for history), establishing **deterministic phase detection** (NO type-heuristic guessing), and defining strict validation requirements.

## Scope

**In Scope:**
Problem analysis (dual phase systems), Breaking points in existing tools (GitManager, GitConfig, get_work_context), Dual-source model (state.json vs commit-scope), **Deterministic source precedence** per tool type (NO guessing), Backward compatibility requirements, **Strict sub_phase validation**, **coordination phase** support

**Out of Scope:**
Implementation design, Complete schemas, Code examples, Migration strategies, Test plans

## Prerequisites

1. Issue #138 v1.0 research-v1-archived.md (two phase systems analysis)
2. Issue #39 infrastructure (PhaseStateEngine, state.json persistence)
3. User requirement: workflow phases in commit-scope (not replacing state.json)
4. User requirement: **deterministic dual-source model** with explicit precedence per tool type (NO type-heuristic guessing)

---

## Problem Statement

**Current State:** Two independent phase systems exist:
- **TDD phases** (git.yaml): red, green, refactor, docs
- **Workflow phases** (workflows.yaml): research, planning, design, tdd, integration, documentation, **coordination**

**Problem:** `git_add_or_commit` only accepts TDD phases. Agents cannot commit during research/planning/integration phases. `get_work_context._detect_tdd_phase()` uses **non-deterministic type-based guessing**.

**User Vision:** Workflow phases should be visible in commit messages (Conventional Commits scope field), while state.json remains primary for runtime/enforcement. **Phase detection must be deterministic** - unknown is acceptable outcome, guessing is not.

**Critical Requirement:** Tools must handle old commits gracefully (no blocking errors), but **phase detection must be deterministic** (unknown > incorrect guess).

---

## Current Breaking Points

### 1. GitManager - TDD-Only Commit Methods

```python
# mcp_server/managers/git_manager.py (lines 88-120)

def commit_tdd_phase(self, phase: str, message: str, files: list[str] | None = None) -> str:
    """Commit with TDD phase prefix."""
    # ❌ BREAKS: Only validates against git_config.tdd_phases
    if not self._git_config.has_phase(phase):
        raise PreflightError(f"Invalid phase: {phase}")
    
    prefix = self._git_config.commit_prefix_map[phase]  # ❌ Hardcoded TDD mapping
    commit_message = f"{prefix}: {message}"
    # ...

def commit_docs(self, message: str, files: list[str] | None = None) -> str:
    """Special case for docs commits."""
    commit_message = f"docs: {message}"  # ❌ Special case, not extensible
    # ...
```

**Problem:** Methods assume TDD phases are the only valid phases. Workflow phases rejected.

---

### 2. GitConfig - TDD Phase Validation

```python
# mcp_server/config/git_config.py (lines 60-85)

class GitConfig(BaseModel):
    tdd_phases: list[str] = ["red", "green", "refactor", "docs"]  # ❌ Only TDD
    commit_prefix_map: dict[str, str] = {  # ❌ Hardcoded TDD → type mapping
        "red": "test",
        "green": "feat",
        "refactor": "refactor",
        "docs": "docs"
    }
    
    def has_phase(self, phase: str) -> bool:
        """Check if phase is valid TDD phase."""
        return phase in self.tdd_phases  # ❌ Rejects workflow phases
```

**Problem:** Validation model doesn't know about workflow phases or coordination phase.

---

### 3. GitCommitInput - Restrictive Schema

```python
# mcp_server/tools/git_tools.py (lines 125-150)

class GitCommitInput(BaseModel):
    phase: str = Field(..., description="TDD phase (red/green/refactor/docs)")
    message: str
    files: list[str] | None = None
    
    @field_validator("phase")
    @classmethod
    def validate_phase(cls, value: str) -> str:
        git_config = GitConfig.from_file()
        if not git_config.has_phase(value):  # ❌ Only accepts TDD phases
            raise ValueError(
                f"Invalid phase '{value}'. Valid phases: {git_config.tdd_phases}"
            )
        return value
```

**Problem:** Tool schema prevents workflow phases at input level. No sub_phase validation.

---

### 4. get_work_context - Non-Deterministic Type-Based Guessing

```python
# mcp_server/tools/context_tools.py (Issue #117)

def _detect_tdd_phase(self) -> str:
    """Detect TDD phase from last commit prefix."""
    last_commit = git_adapter.get_last_commit_message()
    
    # ❌ Non-deterministic guessing from commit type, ignores scope
    if last_commit.startswith("test:"):
        return "red"  # Could be green, refactor, or integration!
    elif last_commit.startswith("feat:"):
        return "green"  # Could be tdd, integration, or coordination!
    # ...
```

**Problem:** Parses commit **type** (feat/test/docs), not **scope** (workflow phase). Guessing is non-deterministic - `test:` could be red, green, refactor, or integration phase. Cannot detect research/planning/integration/coordination phases.

---

## Dual-Source Model (Issue #39 Architecture)

**CORRECTION TO INITIAL RESEARCH:** workphases.yaml is NOT absolute SSOT. Issue #39 established dual-source architecture that must be preserved.

### Source Hierarchy

**1. Runtime/Enforcement Primary:** `.st3/state.json`
- **Purpose:** Current phase tracking, workflow validation, audit trail
- **Contents:**
  - current_phase (authoritative for transitions)
  - workflow_name (cached from project for performance)
  - transitions array with forced flag
  - skip_reason + human_approval (forced transition audit)
  - parent_branch tracking
- **Not version-controlled:** .gitignore:74 - runtime state only
- **Manager:** PhaseStateEngine (mcp_server/managers/phase_state_engine.py)
- **Used by:** transition_phase, force_phase_transition, initialize_project

**2. History/Context Primary:** Git commit scope
- **Purpose:** Workflow phase visible in git history, context detection
- **Format:** Conventional Commits `type(scope): message`
- **Contents:** `P_PHASE` or `P_PHASE_SP_SUBPHASE` encoding
- **Fallback:** **Deterministic chain: commit-scope > state.json > unknown** (NO type-heuristic guessing)
- **Used by:** get_work_context, get_project_plan (context/reporting tools)

**3. Configuration Source:** workphases.yaml
- **Purpose:** Phase metadata (display names, descriptions, commit type hints, **subphase whitelists**)
- **Referenced by:** workflows.yaml (sequences), git.yaml (conventions)
- **Not runtime state:** Just definitions + validation rules, not current phase

### Source Precedence (EXPLICIT - Deterministic)

**Transition/Enforcement Tools** (state.json authoritative):
```python
transition_phase()        → state.json ONLY (runtime state authoritative, NO commit parsing)
force_phase_transition()  → state.json ONLY (audit trail required, NO commit parsing)
initialize_project()      → state.json WRITE (creates runtime state)
```

**Context/Reporting Tools** (deterministic precedence, NO guessing):
```python
get_work_context()   → commit-scope > state.json > unknown (NO type-heuristic)
get_project_plan()   → commit-scope > state.json > unknown (NO type-heuristic)
git_log analysis     → commit-scope ONLY (historical trace)
```

**Why NO type-heuristic:**
- `test:` could be red, green, refactor, or integration → non-deterministic
- `feat:` could be tdd/green, integration, or coordination → non-deterministic
- `unknown` phase is acceptable outcome (with actionable error message)
- **Determinism > false confidence**

### Rationale

**Why state.json remains primary for enforcement:**
1. **Audit trail:** Forced transitions track skip_reason + human_approval (compliance requirement)
2. **Performance:** workflow_name cached (avoids repeated project lookups)
3. **Atomic transitions:** PhaseStateEngine validates against workflow rules
4. **Runtime-only:** Not part of git history (.gitignore:74 - deliberate choice)

**Why commit-scope is primary for context:**
1. **Git history:** `git log --oneline` shows workflow progression without external files
2. **Branch switching:** state.json not tracked, context tools need fallback
3. **Observability:** Phase visible in every commit message (self-documenting)
4. **Historical analysis:** No dependency on runtime state files

**Why NO type-heuristic guessing:**
1. **Non-deterministic:** `test:` could be multiple phases (red, green, refactor, integration)
2. **False confidence:** Better to return unknown with clear error than incorrect guess
3. **Actionable errors:** Unknown phase includes recovery steps (transition_phase or proper commit)
4. **Determinism:** Predictable behavior > silent incorrect guessing

---

## Critical Requirements

### 1. Deterministic Phase Detection (MUST HAVE)

**Requirement:** Phase detection must be deterministic. Unknown is acceptable, guessing is not.

**Reason:** Type-heuristic is non-deterministic:
- `test:` could be red, green, refactor, or integration
- `feat:` could be tdd/green, integration, or coordination
- `docs:` could be research, planning, design, or documentation

**Implication:** 
- ✅ **Deterministic precedence: commit-scope > state.json > unknown**
- ✅ Unknown phase returns actionable error message with recovery steps
- ✅ NO type-heuristic guessing (removed entirely)
- ❌ Tools must NOT guess phase from commit type

**Example Behavior:**
```python
# New format (high confidence)
commit_message = "test(P_TDD_SP_C1_RED): add tests"
result = decoder.detect_phase(commit_message)
# → PhaseDetectionResult(workflow_phase="tdd", sub_phase="c1_red", source="commit-scope", confidence="high")

# Old format with state.json (medium confidence)
commit_message = "test: add tests"  # No scope
result = decoder.detect_phase(commit_message, fallback_to_state=True)
# → Try commit-scope: None
# → Try state.json: "tdd" (if exists)
# → PhaseDetectionResult(workflow_phase="tdd", sub_phase=None, source="state.json", confidence="medium")

# Old format without state.json (unknown - deterministic outcome)
commit_message = "test: add tests"  # No scope, no state.json
result = decoder.detect_phase(commit_message, fallback_to_state=True)
# → Try commit-scope: None
# → Try state.json: FileNotFoundError
# → PhaseDetectionResult(
#      workflow_phase="unknown", 
#      source="unknown", 
#      confidence="unknown",
#      error_message="Phase detection failed. Recovery: Run transition_phase(to_phase='<phase>') or commit with scope 'type(P_PHASE): message'. Valid phases: research, planning, design, tdd, integration, documentation, coordination"
#    )
```

---

### 2. Strict sub_phase Validation (MUST HAVE)

**Requirement:** sub_phase must exist in workphases.yaml[phase].subphases. No free strings.

**Reason:** Prevents typos and ensures consistency.

**Implication:**
- ✅ workphases.yaml defines subphase whitelist per phase
- ✅ ScopeEncoder validates sub_phase against whitelist
- ✅ Error message includes valid subphases + example
- ❌ Free strings like "invalid" or "test123" rejected

**Example:**
```yaml
# workphases.yaml
phases:
  tdd:
    subphases: ["red", "green", "refactor"]  # Whitelist
  coordination:
    subphases: ["delegation", "sync", "review"]  # New phase
```

**Validation:**
```python
# Valid
encoder.generate_scope("tdd", "red")  # ✅ "red" in whitelist
encoder.generate_scope("coordination", "delegation")  # ✅ "delegation" in whitelist

# Invalid
encoder.generate_scope("tdd", "invalid")  # ❌ ValueError with actionable message
```

---

### 3. Graceful Degradation (MUST HAVE)

**Requirement:** Tools must handle old commits without blocking errors.

**Reason:** Existing branches have commits like:
- `docs: add research findings` (no scope)
- `feat: implement service` (no scope)
- `test(user): add tests` (wrong scope format)

**Implication:** 
- ✅ Scope parsing must be **optional**, not required
- ✅ Tools must fallback to state.json or return unknown (NO type-heuristic guessing)
- ✅ New commits should use new format, old commits continue working
- ❌ Tools must NOT throw errors when encountering old format

---

### 4. No Backward Compatibility for Commit History

**User Requirement:** No migration of existing commits needed.

**Implication:**
- ❌ No rewriting git history
- ❌ No migration tooling for old commits
- ✅ Tools work with mixed-format history (old + new commits)
- ✅ All new commits use new format going forward

---

### 5. Respect State.json Audit Trail

**Non-Negotiable:** PhaseStateEngine audit trail must remain intact.

**Implications:**
- ✅ Forced transitions still track skip_reason + human_approval in state.json
- ✅ transition_phase validates against state.json current_phase (NOT commit-scope)
- ✅ Commit-scope does NOT replace state.json for enforcement
- ✅ Dual-source model: both sources serve different purposes

---

### 6. Coordination Phase Support (NEW)

**Requirement:** Add coordination phase for epic-level work.

**Use Cases:**
- Epic issue delegation to child issues
- Cross-issue synchronization
- Epic-level review and approval

**Implication:**
- ✅ workphases.yaml includes coordination phase
- ✅ workflows.yaml supports coordination in epic workflow
- ✅ Subphases: delegation, sync, review

---

## Trade-Offs Analysis

### Option 1: Dual-Source Model with Deterministic Detection (Selected)

**Approach:** state.json for runtime/enforcement, commit-scope for history/context, **NO type-heuristic guessing**

**Pros:**
- ✅ Preserves Issue #39 audit trail infrastructure
- ✅ Git history self-documenting (scope shows workflow state)
- ✅ Conventional Commits compliant
- ✅ Clear separation: enforcement vs observability
- ✅ **Deterministic behavior** (unknown > incorrect guess)
- ✅ **Actionable error messages** when phase unknown

**Cons:**
- ⚠️ Two sources of truth (requires explicit precedence rules)
- ⚠️ Potential divergence if not synchronized correctly
- ⚠️ Tools must implement precedence correctly (more complex)
- ⚠️ Unknown phase requires user action (but with clear instructions)

---

### Option 2: state.json-Only (Rejected)

**Approach:** Keep state.json as only source, don't change commits

**Why Rejected:**
- ❌ Doesn't solve Issue #138 (agents still can't commit with workflow phases)
- ❌ Git history remains opaque (workflow state hidden in state.json)
- ❌ Violates user vision (workflow phases should be visible)

---

### Option 3: Commit-Scope-Only (Rejected - Violates Issue #39)

**Approach:** Make commit-scope absolute SSOT, deprecate state.json

**Why Rejected:**
- ❌ Loses forced transition audit trail (compliance requirement)
- ❌ Loses workflow_name cache (performance degradation)
- ❌ Breaks PhaseStateEngine contracts (test failures)
- ❌ Violates Issue #39 architecture decisions

---

## Related Issues

### Issue #117: get_work_context Non-Deterministic Detection

**Current Problem:** Parses commit **type** (feat/test/docs) with non-deterministic guessing.

**Fix:** Parse commit-scope with state.json fallback, **NO type-heuristic** (return unknown instead).

**Source Precedence:** commit-scope > state.json > unknown

---

### Issue #139: get_project_plan Missing current_phase

**Current Problem:** current_phase only in state.json, not visible in git history.

**Benefit:** With commit-scope, `git log` shows workflow progression.

**Source Precedence:** commit-scope > state.json > unknown

---

### Issue #121: Cryptic Validation Errors

**Lesson Learned:** Validation errors must include concrete examples + recovery actions.

**Applied Here:** When scope format invalid or phase unknown:
```
Invalid scope format: "RESEARCH"
Expected: P_PHASE or P_PHASE_SP_SUBPHASE
Examples:
  - P_RESEARCH
  - P_TDD_SP_C1_RED
  - P_COORDINATION_SP_DELEGATION

Recovery: Use git_add_or_commit with workflow_phase parameter
```

---

## Dependency Graph

**Tools Consuming Commit Conventions:**

1. **GitManager** (mcp_server/managers/git_manager.py)
   - Methods: commit_tdd_phase(), commit_docs()
   - Impact: Major refactor (replace with unified commit method)

2. **GitConfig** (mcp_server/config/git_config.py)
   - Fields: tdd_phases, commit_prefix_map
   - Methods: has_phase(), get_prefix()
   - Impact: Deprecate TDD-specific fields

3. **GitCommitInput** (mcp_server/tools/git_tools.py)
   - Schema: phase field validation
   - Impact: Major refactor (new schema with strict sub_phase validation)

4. **get_work_context** (mcp_server/tools/context_tools.py)
   - Method: _detect_tdd_phase() (remove entirely - non-deterministic)
   - Impact: Parse scope with state.json fallback → unknown (NO guessing)

5. **get_project_plan** (mcp_server/tools/project_tools.py)
   - Method: Extract current_phase
   - Impact: Parse commit-scope with state.json fallback → unknown

6. **Tests** (tests/...)
   - Files: test_git_manager.py, test_git_tools_config.py (20+ files)
   - Impact: ~210 assertions need updates

---

## Architecture Decision Record

### ADR-001: Dual-Source Model with Deterministic Detection

**Decision:** Use state.json for runtime/enforcement, commit-scope for history/context, with **deterministic phase detection** (NO type-heuristic guessing).

**Rationale:**
1. **Preserves Issue #39:** PhaseStateEngine audit trail remains intact
2. **Self-documenting history:** `git log` shows complete workflow trace
3. **Standards compliance:** Conventional Commits format preserved
4. **Clear separation:** Enforcement (state.json) vs Observability (commit-scope)
5. **Determinism:** Unknown phase with actionable error > incorrect guess

**Consequences:**
- ✅ Fixes Issue #138 (workflow phase commits with strict validation)
- ✅ Fixes Issue #117 (deterministic detection: commit-scope > state.json > unknown)
- ✅ Improves Issue #139 (visible state in git history)
- ✅ Preserves audit trail (forced transitions, skip_reason, human_approval)
- ✅ Enables coordination phase (epic delegation)
- ⚠️ Requires explicit precedence per tool type (documented above)
- ⚠️ Tools must implement dual-source correctly (test coverage required)
- ⚠️ Unknown phase requires user action (but with clear recovery instructions)

**Rejected Alternatives:**
- state.json-only: Doesn't solve Issue #138, git history opaque
- commit-scope-only: Violates Issue #39, loses audit trail
- Type-heuristic fallback: Non-deterministic, false confidence

---

## Acceptatiecriteria (User-Specified - Updated)

1. **Geen blocking errors op legacy commitformaten**
   - Old commits (`test: add tests`) must not throw errors
   - **Deterministic fallback: commit-scope > state.json > unknown** (NO type-heuristic guessing)

2. **Deterministische source precedence per tooltype**
   - Transition tools: **state.json ONLY** (no fallback, no commit parsing)
   - Context tools: **commit-scope > state.json > unknown** (NO type-heuristic)
   - Explicitly documented and tested

3. **Consistente phase-output tussen tools**
   - get_work_context, get_project_plan, git_add_or_commit all use same resolver
   - DRY: Single ScopeDecoder utility with **deterministic precedence** logic

4. **Audit/transitiongedrag via state-engine blijft intact**
   - transition_phase validates against state.json ONLY
   - force_phase_transition tracks skip_reason + human_approval
   - PhaseStateEngine contracts unchanged

5. **Strict sub_phase validation** (NEW)
   - sub_phase must exist in workphases.yaml[phase].subphases
   - **Actionable error messages** (what failed, valid values, recovery action)
   - No free strings, prevents typos

6. **coordination phase support** (NEW)
   - Epic delegation workflow enabled
   - workphases.yaml includes coordination phase
   - Subphases: delegation, sync, review

---

## Open Questions for Planning Phase

1. **Cycle tracking:** How to increment TDD cycle numbers? **→ RESOLVED: Manual input (simpler)**
2. **Validation UX:** What error messages for invalid scopes? **→ RESOLVED: Valid list + example + recovery action (Issue #121)**
3. **State synchronization:** How to keep commit-scope and state.json aligned? **→ RESOLVED: git_add_or_commit syncs automatically**
4. **Sub-phase validation:** Strict or flexible? **→ RESOLVED: Strict whitelist (prevents typos)**
5. **Test strategy:** Contract tests for precedence logic? **→ Deferred to planning phase**

---

## Referentiepunten

- **[docs/reference/mcp/tools/project.md](../../reference/mcp/tools/project.md):** Runtime-state rationale, PhaseStateEngine
- **[docs/reference/mcp/tools/git.md](../../reference/mcp/tools/git.md):** Git-tooling huidige TDD-focus
- **[.gitignore:74](../../../.gitignore):** state.json is bewust niet-versioned
- **[mcp_server/managers/phase_state_engine.py](../../../mcp_server/managers/phase_state_engine.py):** Forced transitions, audit trail
- **[mcp_server/tools/project_tools.py](../../../mcp_server/tools/project_tools.py):** Initialize project, state contracts
- **[tests/.../test_initialize_project_tool.py](../../../tests/unit/mcp_server/tools/test_initialize_project_tool.py):** State contracts

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.3 | 2026-02-14 | Agent | **BREAKING:** Remove type-heuristic (deterministic detection), add strict sub_phase validation, add coordination phase, resolve all open questions |
| 2.2 | 2026-02-14 | Agent | Corrected to dual-source model (state.json + commit-scope), added acceptatiecriteria, referentiepunten |
| 2.1 | 2026-02-14 | Agent | Refactored: removed implementation details, focused on research only, added graceful degradation requirement |
| 2.0 | 2026-02-14 | Agent | Complete architectural design (too broad - contained design/implementation) |
| 1.0 | 2026-02-14 | Agent | Two phase systems analysis (archived as research-v1-archived.md) |

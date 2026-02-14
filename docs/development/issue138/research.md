<!-- D:\dev\SimpleTraderV3\docs\development\issue138\research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-14T17:30:00+00:00 updated=2026-02-14T18:50:00+00:00 -->
# Issue #138: Workflow-First Commit Convention Architecture

**Status:** COMPLETE  
**Version:** 2.2  
**Last Updated:** 2026-02-14T18:50:00+00:00

---

## Purpose

Research architectural approach for workflow-first commit conventions using Conventional Commits format, respecting dual-source model (state.json for runtime, commit-scope for history), and establishing graceful degradation requirements.

## Scope

**In Scope:**
Problem analysis (dual phase systems), Breaking points in existing tools (GitManager, GitConfig, get_work_context), Dual-source model (state.json vs commit-scope), Source precedence per tool type, Backward compatibility requirements

**Out of Scope:**
Implementation design, Complete schemas, Code examples, Migration strategies, Test plans

## Prerequisites

1. Issue #138 v1.0 research-v1-archived.md (two phase systems analysis)
2. Issue #39 infrastructure (PhaseStateEngine, state.json persistence)
3. User requirement: workflow phases in commit-scope (not replacing state.json)
4. User requirement: dual-source model with explicit precedence per tool type

---

## Problem Statement

**Current State:** Two independent phase systems exist:
- **TDD phases** (git.yaml): red, green, refactor, docs
- **Workflow phases** (workflows.yaml): research, planning, design, tdd, integration, documentation, coordination

**Problem:** `git_add_or_commit` only accepts TDD phases. Agents cannot commit during research/planning/integration phases.

**User Vision:** Workflow phases should be visible in commit messages (Conventional Commits scope field), while state.json remains primary for runtime/enforcement.

**Critical Requirement:** Tools must handle old commits gracefully (no blocking errors when parsing commits without proper scope format).

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

**Problem:** Validation model doesn't know about workflow phases.

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

**Problem:** Tool schema prevents workflow phases at input level.

---

### 4. get_work_context - Type-Based Guessing

```python
# mcp_server/tools/context_tools.py (Issue #117)

def _detect_tdd_phase(self) -> str:
    """Detect TDD phase from last commit prefix."""
    last_commit = git_adapter.get_last_commit_message()
    
    # ❌ Guesses from commit type, ignores scope
    if last_commit.startswith("test:"):
        return "red"
    elif last_commit.startswith("feat:"):
        return "green"
    # ...
```

**Problem:** Parses commit **type** (feat/test/docs), not **scope** (workflow phase). Cannot detect research/planning/integration phases.

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
- **Fallback:** Type-based heuristic for old commits
- **Used by:** get_work_context, get_project_plan (context/reporting tools)

**3. Configuration Source:** workphases.yaml
- **Purpose:** Phase metadata (display names, descriptions, commit type hints)
- **Referenced by:** workflows.yaml (sequences), git.yaml (conventions)
- **Not runtime state:** Just definitions, not current phase

### Source Precedence (EXPLICIT)

**Transition/Enforcement Tools** (state.json authoritative):
```python
transition_phase()        → state.json ONLY (runtime state authoritative)
force_phase_transition()  → state.json ONLY (audit trail required)
initialize_project()      → state.json WRITE (creates runtime state)
```

**Context/Reporting Tools** (commit-scope preferred, state.json fallback):
```python
get_work_context()   → commit-scope > state.json > type-heuristic
get_project_plan()   → commit-scope > state.json > type-heuristic
git_log analysis     → commit-scope ONLY (historical trace)
```

### Rationale

**Why state.json remains primary for enforcement:**
1. **Audit trail:** Forced transitions track skip_reason + human_approval (compliance requirement)
2. **Performance:** workflow_name cached (avoids repeated project lookups)
3. **Atomic transitions:** PhaseStateEngine validates against workflow rules
4. **Runtime-only:** Not part of git history (.gitignore:74 - deliberate choice)

**Why commit-scope is primary for context:**
1. **Git history:** `git log --oneline` shows workflow progression without external files
2. **Branch switching:** state.json deleted on `git checkout` (context tools need fallback)
3. **Observability:** Phase visible in every commit message (self-documenting)
4. **Historical analysis:** No dependency on runtime state files

---

## Critical Requirements

### 1. Graceful Degradation (MUST HAVE)

**Requirement:** Tools must handle old commits without proper scope format.

**Reason:** Existing branches have commits like:
- `docs: add research findings` (no scope)
- `feat: implement service` (no scope)
- `test(user): add tests` (wrong scope format)

**Implication:** 
- ✅ Scope parsing must be **optional**, not required
- ✅ Tools must fallback to type-based heuristic if scope missing/invalid
- ✅ New commits should use new format, old commits continue working
- ❌ Tools must NOT throw errors when encountering old format

**Example Behavior:**
```python
# New format (preferred)
commit_message = "test(P_TDD_SP_C1_RED): add tests"
scope = decoder.extract_from_commit(commit_message)
# → WorkflowScope(phase="tdd", subphase="red", cycle=1)

# Old format (graceful fallback)
commit_message = "test: add tests"
scope = decoder.extract_from_commit(commit_message)
# → None (fallback to type-based heuristic: type="test" → phase="tdd")

# state.json fallback
if scope is None and state.json exists:
    phase = state["current_phase"]  # Use runtime state
```

---

### 2. No Backward Compatibility for Commit History

**User Requirement:** No migration of existing commits needed.

**Implication:**
- ❌ No rewriting git history
- ❌ No migration tooling for old commits
- ✅ Tools work with mixed-format history (old + new commits)
- ✅ All new commits use new format going forward

---

### 3. Respect State.json Audit Trail

**Non-Negotiable:** PhaseStateEngine audit trail must remain intact.

**Implications:**
- ✅ Forced transitions still track skip_reason + human_approval in state.json
- ✅ transition_phase validates against state.json current_phase (not commit-scope)
- ✅ Commit-scope does NOT replace state.json for enforcement
- ✅ Dual-source model: both sources serve different purposes

---

## Trade-Offs Analysis

### Option 1: Dual-Source Model (Selected)

**Approach:** state.json for runtime/enforcement, commit-scope for history/context

**Pros:**
- ✅ Preserves Issue #39 audit trail infrastructure
- ✅ Git history self-documenting (scope shows workflow state)
- ✅ Conventional Commits compliant
- ✅ Clear separation: enforcement vs observability

**Cons:**
- ⚠️ Two sources of truth (requires explicit precedence rules)
- ⚠️ Potential divergence if not synchronized correctly
- ⚠️ Tools must implement precedence correctly (more complex)

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

### Issue #117: get_work_context TDD-Only Detection

**Current Problem:** Parses commit **type** (feat/test/docs), not **scope**.

**Fix:** Parse commit-scope with state.json fallback, type-heuristic as last resort.

**Source Precedence:** commit-scope > state.json > type-heuristic

---

### Issue #139: get_project_plan Missing current_phase

**Current Problem:** current_phase only in state.json, not visible in git history.

**Benefit:** With commit-scope, `git log` shows workflow progression.

**Source Precedence:** commit-scope > state.json

---

### Issue #121: Cryptic Validation Errors

**Lesson Learned:** Validation errors must include concrete examples.

**Applied Here:** When scope format invalid, error message should show correct format:
```
Invalid scope format: "RESEARCH"
Expected: P_PHASE or P_PHASE_SP_SUBPHASE
Examples:
  - P_RESEARCH
  - P_TDD_SP_C1_RED
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
   - Impact: Major refactor (new schema)

4. **get_work_context** (mcp_server/tools/context_tools.py)
   - Method: _detect_tdd_phase()
   - Impact: Parse scope with state.json fallback

5. **get_project_plan** (mcp_server/tools/project_tools.py)
   - Method: Extract current_phase
   - Impact: Parse commit-scope with state.json fallback

6. **Tests** (tests/...)
   - Files: test_git_manager.py, test_git_tools_config.py (20+ files)
   - Impact: ~210 assertions need updates

---

## Architecture Decision Record

### ADR-001: Dual-Source Model for Phase Tracking

**Decision:** Use state.json for runtime/enforcement, commit-scope for history/context.

**Rationale:**
1. **Preserves Issue #39:** PhaseStateEngine audit trail remains intact
2. **Self-documenting history:** `git log` shows complete workflow trace
3. **Standards compliance:** Conventional Commits format preserved
4. **Clear separation:** Enforcement (state.json) vs Observability (commit-scope)

**Consequences:**
- ✅ Fixes Issue #138 (workflow phase commits)
- ✅ Fixes Issue #117 (commit-scope-based detection with fallback)
- ✅ Improves Issue #139 (visible state in git history)
- ✅ Preserves audit trail (forced transitions, skip_reason, human_approval)
- ⚠️ Requires explicit precedence per tool type (documented above)
- ⚠️ Tools must implement dual-source correctly (test coverage required)

**Rejected Alternatives:**
- state.json-only: Doesn't solve Issue #138, git history opaque
- commit-scope-only: Violates Issue #39, loses audit trail

---

## Acceptatiecriteria (User-Specified)

1. **Geen blocking errors op legacy commitformaten**
   - Old commits (`test: add tests`) must not throw errors
   - Graceful fallback to type-heuristic or state.json

2. **Deterministische source precedence per tooltype**
   - Transition tools: state.json > commit-scope > type-heuristic
   - Context tools: commit-scope > state.json > type-heuristic
   - Explicitly documented and tested

3. **Consistente phase-output tussen tools**
   - get_work_context, get_project_plan, git_add_or_commit all use same resolver
   - DRY: Single ScopeDecoder utility with precedence logic

4. **Audit/transitiongedrag via state-engine blijft intact**
   - transition_phase validates against state.json
   - force_phase_transition tracks skip_reason + human_approval
   - PhaseStateEngine contracts unchanged

---

## Open Questions for Planning Phase

1. **ScopeDecoder precedence:** How to implement commit-scope > state.json > type-heuristic cleanly?
2. **Cycle tracking:** How to increment TDD cycle numbers? (Manual input or auto-detect from last commit?)
3. **Validation UX:** What error messages for invalid scopes? (Issue #121 lesson)
4. **Test strategy:** Contract tests for precedence logic? Integration tests for tool boundaries?
5. **State synchronization:** How to keep commit-scope and state.json aligned? (git_add_or_commit responsibility?)

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
| 2.2 | 2026-02-14T18:50:00+00:00 | Agent | Corrected to dual-source model (state.json + commit-scope), added acceptatiecriteria, referentiepunten |
| 2.1 | 2026-02-14T18:20:00+00:00 | Agent | Refactored: removed implementation details, focused on research only, added graceful degradation requirement |
| 2.0 | 2026-02-14T17:45:00+00:00 | Agent | Complete architectural design (too broad - contained design/implementation) |
| 1.0 | 2026-02-14T15:00:00+00:00 | Agent | Two phase systems analysis (archived as research-v1-archived.md) |

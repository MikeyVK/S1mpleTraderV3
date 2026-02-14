<!-- D:\dev\SimpleTraderV3\docs\development\issue138\research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-14T17:30:00+00:00 updated=2026-02-14T18:15:00+00:00 -->
# Issue #138: Workflow-First Commit Convention Architecture

**Version:** 2.1
**Last Updated:** 2026-02-14T18:20:00+00:00
**Last Updated:** 2026-02-14T18:15:00+00:00

---

## Purpose

Research architectural approach for workflow-first commit conventions using Conventional Commits format, identifying breaking points in current codebase and establishing requirements for graceful degradation.

## Scope

**In Scope:**
Problem analysis (dual phase systems), Breaking points in existing tools (GitManager, GitConfig, get_work_context), Architecture trade-offs (workflow-first vs TDD-first), Backward compatibility requirements (old commits must not block work)

**Out of Scope:**
Implementation design (moved to planning/design phases), Complete schemas (workphases.yaml design), Code examples (ScopeEncoder/Decoder implementation), Migration strategies, Test plans

## Prerequisites

1. Issue #138 v1.0 research-v1-archived.md (two phase systems analysis)
2. User requirement: workflow phases should be primary (not TDD phases)
3. User requirement: old commits without proper format must not block tools
4. Coding standards understood (DRY principles)

---

## Problem Statement

**Current State:** Two independent phase systems exist:
- **TDD phases** (git.yaml): red, green, refactor, docs
- **Workflow phases** (workflows.yaml): research, planning, design, tdd, integration, documentation, coordination

**Problem:** `git_add_or_commit` only accepts TDD phases. Agents cannot commit during research/planning/integration phases.

**User Vision:** Workflow phases should drive commit messages, encoded in Conventional Commits scope field.

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

**Problem:** Validation model doesn't know about workflow phases. Single source of truth missing.

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

## Architectural Vision (High-Level)

### Core Principle

**Workflow phases are PRIMARY, encoded in Conventional Commits scope field.**

### Format

```
type(scope): description

Examples:
  docs(P_RESEARCH): complete dependency analysis
  test(P_TDD_SP_C1_RED): add validation tests
  feat(P_TDD_SP_C1_GREEN): implement validation
```

**Key Insight:** Conventional Commits already supports hierarchical scopes. We don't need a new format, just a new convention for what goes in the scope field.

### Configuration Hierarchy

```
workphases.yaml        → SSOT: All phase definitions (research, tdd, integration, etc.)
        ↓
workflows.yaml         → References phases (defines sequences)
        ↓
git.yaml               → References phases (commit conventions)
```

**Single source of truth** eliminates drift between git.yaml and workflows.yaml.

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
- ✅ Tools must fallback to type-based guessing if scope missing/invalid
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
# → None (fallback to type-based heuristic: type="test" → assume phase="tdd")
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

### 3. Single Source of Truth (workphases.yaml)

**Problem:** Currently phases defined in 2 places:
- git.yaml: `tdd_phases: [red, green, refactor, docs]`
- workflows.yaml: `phases: [research, planning, design, tdd, ...]`

**Solution:** Define once in workphases.yaml, reference everywhere else.

**Benefits:**
- Adding new phase = config change only (no code changes)
- No drift between files
- Clear hierarchy: workphase → workflow sequence → commit format

---

## Trade-Offs Analysis

### Option 1: Workflow-First (Selected)

**Pros:**
- ✅ Git history self-documenting (scope shows workflow state)
- ✅ Conventional Commits compliant (GitHub/GitLab tools work)
- ✅ Single source of truth (DRY)
- ✅ Extensible (new phases via config)

**Cons:**
- ⚠️ Scope strings longer (`P_TDD_SP_C1_RED` vs `test:`)
- ⚠️ Agents must learn new format
- ⚠️ Requires encoder/decoder utilities

---

### Option 2: Hybrid Validation (v1.0 - Rejected)

**Approach:** Accept both TDD and workflow phases, map workflow → TDD prefix

**Example:**
```python
# GitCommitInput accepts "research"
git_add_or_commit(phase="research", message="...")
# Maps to: "docs: complete research"
```

**Why Rejected:**
- ❌ Perpetuates dual system (TDD still primary)
- ❌ Workflow phase hidden (only in state.json, not git history)
- ❌ Hardcoded mapping (code changes for new phases)
- ❌ Doesn't solve Issue #117 (get_work_context still can't detect workflow phase)

---

### Option 3: Keep TDD-First (Status Quo - Rejected)

**Approach:** Keep current system, don't change anything

**Why Rejected:**
- ❌ Doesn't solve Issue #138 (agents can't commit during research/planning)
- ❌ Violates user vision (workflow should be primary)
- ❌ Issue #117 persists (get_work_context guessing)

---

## Related Issues

### Issue #117: get_work_context TDD-Only Detection

**Current Problem:** Parses commit **type** (feat/test/docs), not **scope**.

**Fix:** Parse scope field for workflow phase.

**Example:**
```python
# OLD: commit_message = "test: add validation"
#      → Guesses phase="red" from type="test" (wrong!)

# NEW: commit_message = "test(P_TDD_SP_C2_RED): add validation"
#      → Parses scope="P_TDD_SP_C2_RED" → phase="tdd", cycle=2 (correct!)
```

---

### Issue #139: get_project_plan Missing current_phase

**Current Problem:** current_phase only in state.json, not visible in git history.

**Benefit:** With workflow-first, `git log` shows workflow progression without state.json dependency.

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
   - Impact: Parse scope instead of type

5. **Tests** (tests/...)
   - Files: test_git_manager.py, test_git_tools_config.py (20+ files)
   - Impact: ~210 assertions need updates

---

## Architecture Decision Record

### ADR-001: Workflow-First Commit Convention

**Decision:** Encode workflow phases in Conventional Commits scope field.

**Rationale:**
1. **Self-documenting history:** `git log` shows complete workflow trace
2. **Standards compliance:** Conventional Commits format preserved
3. **Single source of truth:** workphases.yaml eliminates dual system
4. **Extensibility:** New phases = config change only

**Consequences:**
- ✅ Fixes Issue #138 (workflow phase commits)
- ✅ Fixes Issue #117 (scope-based detection)
- ✅ Improves Issue #139 (visible state in git history)
- ⚠️ Requires encoder/decoder utilities (DRY)
- ⚠️ Migration effort: ~14 files, ~210 test assertions
- ✅ Graceful degradation for old commits (fallback to type-based heuristic)

---

## Open Questions for Planning Phase

1. **workphases.yaml schema:** What metadata fields needed? (display_name, description, commit_type_hints, etc.)
2. **Encoder/decoder location:** New module mcp_server/core/scope_formatter.py? Or extend GitConfig?
3. **Cycle tracking:** How to increment TDD cycle numbers? (Manual input or auto-detect from last commit?)
4. **Validation UX:** What error messages for invalid scopes? (Learned from Issue #121)
5. **Test strategy:** Unit tests for encoder/decoder? Integration tests for full workflow?

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.1 | 2026-02-14T18:20:00+00:00 | Agent | Refactored: removed implementation details, focused on research only, added graceful degradation requirement |
| 2.0 | 2026-02-14T17:45:00+00:00 | Agent | Complete architectural design (too broad - contained design/implementation) |
| 1.0 | 2026-02-14T15:00:00+00:00 | Agent | Two phase systems analysis (archived as research-v1-archived.md) |

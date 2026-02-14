# Issue #138 Design - Dual-Source Phase Detection

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-14

---

## Purpose

Define HOW to implement dual-source phase detection: class structures, schemas, data flows, precedence logic, interface contracts.

## Scope

**In Scope:**
- Class structures (ScopeDecoder, ScopeEncoder)
- workphases.yaml schema definition
- Precedence resolver logic with explicit contracts
- Tool integration interfaces
- GitCommitInput schema changes
- Data flow diagrams
- Failure modes and error handling strategy

**Out of Scope:**
- Implementation code (covered in TDD phase)
- Test plans (covered in TDD phase)
- Migration tooling (no backward compatibility needed)

## Prerequisites

Read these first:
1. [research.md](research.md) - Dual-source model architecture (v2.2)
2. [planning.md](planning.md) - 4 vertical cycles breakdown (v1.2)
3. [docs/reference/mcp/tools/project.md](../../reference/mcp/tools/project.md) - PhaseStateEngine rationale
4. [docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md](../../coding_standards/TYPE_CHECKING_PLAYBOOK.md) - Type checking rules

---

## 1. Context & Requirements

### 1.1. Problem Statement

`git_add_or_commit` only accepts TDD phases (`red`, `green`, `refactor`, `docs`), blocking agents from committing during workflow phases (`research`, `planning`, `integration`, `documentation`). 

Current implementation validates phase via `GitConfig.has_phase()` which rejects workflow phases. `get_work_context._detect_tdd_phase()` uses type-based guessing that cannot detect workflow phases.

**Core issue:** Two independent phase systems (TDD vs workflows) with no integration.

### 1.2. Requirements

**Functional:**
- [ ] Parse commit-scope format: `type(P_PHASE)` or `type(P_PHASE_SP_SUBPHASE)`
- [ ] Implement fallback chain: commit-scope → state.json → type-heuristic
- [ ] Generate scope strings from workflow phase + optional subphase
- [ ] `get_work_context` uses commit-scope as primary source
- [ ] `get_project_plan` uses commit-scope as primary source
- [ ] `transition_phase` uses state.json as authoritative source (NO parsing)
- [ ] Old commits without scope work gracefully (no blocking errors)

**Non-Functional:**
- [ ] Performance: No regression vs current system (~same complexity)
- [ ] Usability: Clear error messages with examples (Issue #121 lesson)
- [ ] Compatibility: Mixed commit history supported (old + new formats coexist)
- [ ] Maintainability: DRY - single ScopeDecoder utility (no duplication)
- [ ] Observability: Log phase source (commit-scope / state.json / heuristic)

### 1.3. Constraints

1. **Issue #39 PhaseStateEngine contracts:** state.json audit trail (forced transitions, skip_reason, human_approval), workflow_name cache for performance, atomic validation via PhaseStateEngine.transition()
2. **No backward compatibility:** No migration scripts, mixed commit history supported (graceful degradation), old commits use type-heuristic fallback
3. **Graceful degradation non-negotiable:** Tools must not block on missing/invalid commit-scope, always provide best-effort phase detection
4. **DRY principle mandatory:** Single precedence resolver (no duplicated fallback logic), reusable scope parser/encoder utilities

---

## 2. Design Options

### 2.1. Option A: state.json-only (Rejected ❌)

Keep current architecture, add workflow phases to `GitConfig.tdd_phases`.

**Pros:**
- ✅ Simple, single source of truth
- ✅ Preserves Issue #39 audit trail
- ✅ No git parsing complexity

**Cons:**
- ❌ Git history remains opaque (phases not visible in `git log`)
- ❌ Doesn't solve Issue #138 (workflow phases remain second-class)
- ❌ Branch switching: state.json not tracked, tools may lose context

**Verdict:** Does not meet Issue #138 goals (workflow-first, git observability).

---

### 2.2. Option B: commit-scope-only (Rejected ❌)

Deprecate state.json, parse all phase info from commit-scope.

**Pros:**
- ✅ Self-documenting git history
- ✅ Standards compliant (Conventional Commits)
- ✅ Branch switching resilience

**Cons:**
- ❌ Loses audit trail (forced transitions, skip_reason, human_approval)
- ❌ Breaks Issue #39 architecture (PhaseStateEngine contracts violated)
- ❌ workflow_name cache lost (performance regression)

**Verdict:** Violates Issue #39 non-negotiable requirements.

---

### 2.3. Option C: Dual-source (SELECTED ✅)

state.json remains authoritative for runtime/enforcement, commit-scope becomes primary for history/context, with explicit precedence per tool type.

**Pros:**
- ✅ Best of both worlds (Issue #39 + Issue #138)
- ✅ Preserves audit trail (forced transitions, workflow_name cache)
- ✅ Self-documenting git history
- ✅ Branch switching resilience (context tools use commit-scope fallback)

**Cons:**
- ❌ More complex (requires precedence rules)
- ❌ Synchronization needed (commit must reflect state.json)

**Verdict:** Only option that meets all requirements.

---

## 3. Chosen Design

**Decision:** Implement dual-source phase detection with per-tool-type precedence: state.json authoritative for runtime/enforcement (transitions), commit-scope primary for history/context (reporting).

**Rationale:** Dual-source preserves Issue #39 audit trail (forced transitions, workflow_name cache, atomic validation) while adding git history visibility. Per-tool-type precedence ensures correct behavior: transition tools stay authoritative on state.json (atomic validation), context tools prefer commit-scope (git history, branch switching resilience).

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Dual-source model (not absolute SSOT) | Separates runtime enforcement (state.json) from historical observability (commit-scope) |
| Per-tool-type precedence | Transition tools need atomicity (state.json), context tools need observability (commit-scope) |
| ScopeDecoder with fallback chain | DRY: Single utility for commit-scope → state.json → type-heuristic precedence |
| workphases.yaml as config-SSOT | Phase metadata (display names, descriptions) - NOT runtime state |
| Graceful degradation mandatory | Old commits without scope use type-heuristic (no blocking errors) |

---

## 4. Architecture Overview

### 4.1. Source Precedence Matrix

| Tool Type | Source Order | Rationale |
|-----------|--------------|-----------|
| **Transition Tools** (`transition_phase`, `force_phase_transition`) | state.json ONLY | Atomic validation, audit trail, workflow_name cache |
| **Context Tools** (`get_work_context`, `get_project_plan`) | commit-scope → state.json → type-heuristic | Git history observable, branch switching resilience |
| **Commit Tools** (`git_add_or_commit`) | state.json → user input | Synchronization point: commit reflects current state |

### 4.2. Component Contracts

#### ScopeDecoder Interface

**Responsibility:** Parse commit-scope with graceful fallback chain.

```python
class PhaseDetectionResult(TypedDict):
    workflow_phase: str
    sub_phase: Optional[str]
    source: Literal["commit-scope", "state.json", "type-heuristic", "unknown"]
    confidence: Literal["high", "medium", "low"]
    raw_scope: Optional[str]  # Original scope string for debugging

class ScopeDecoder:
    def detect_phase(
        self,
        commit_message: Optional[str] = None,
        fallback_to_state: bool = True,
        fallback_to_type: bool = True
    ) -> PhaseDetectionResult:
        """
        Detect phase with explicit precedence.
        
        Returns:
            PhaseDetectionResult - Always succeeds (returns 'unknown' if all fail)
        
        Raises:
            Never (graceful degradation mandatory)
        """
```

**Contract:**
- MUST NOT raise exceptions (graceful degradation)
- MUST return valid `PhaseDetectionResult` even if all sources fail
- confidence=high: commit-scope match with valid phase
- confidence=medium: state.json read success
- confidence=low: type-heuristic guess or unknown
- raw_scope included for debugging/logging

---

#### ScopeEncoder Interface

**Responsibility:** Generate valid scope strings for commits.

```python
class ScopeEncoder:
    def generate_scope(
        self,
        workflow_phase: str,
        sub_phase: Optional[str] = None,
        cycle_number: Optional[int] = None,
    ) -> str:
        """
        Generate scope: P_PHASE or P_PHASE_SP_SUBPHASE.
        
        Args:
            workflow_phase: Must exist in workphases.yaml
            sub_phase: Any string (flexible validation)
            cycle_number: Prepends C{N}_ if provided
        
        Returns:
            Scope string (e.g., "P_TDD_SP_C1_RED")
        
        Raises:
            ValueError: If workflow_phase unknown (with valid list)
        """
```

**Contract:**
- MUST validate workflow_phase against workphases.yaml
- MUST raise ValueError with clear message + valid phase list
- sub_phase: NO validation (flexible - enables custom cycles)
- cycle_number: Optional, format `C{N}_` if provided

---

### 4.3. Data Flow: Context Tool Phase Detection

```
get_work_context()
    ↓
Git: git log -1 --oneline
    ↓
"docs(P_PLANNING_SP_C1): update planning"
    ↓
ScopeDecoder.detect_phase()
    ↓
 ┌─────────────────────────────┐
 │ Try 1: Parse commit-scope   │
 │ Regex: P_(?<phase>[A-Z_]+) │
 │ (?:_SP_(?<subphase>[A-Z0-9_]+))?│
 └─────────────────────────────┘
    ↓ Match?
   YES → PhaseDetectionResult(workflow_phase="planning", sub_phase="c1", source="commit-scope", confidence="high")
    ↓ NO
 ┌─────────────────────────────┐
 │ Try 2: Read state.json      │
 │ Path: .st3/state.json       │
 │ Field: current_phase        │
 └─────────────────────────────┘
    ↓ Success?
   YES → PhaseDetectionResult(workflow_phase="tdd", sub_phase=None, source="state.json", confidence="medium")
    ↓ NO (FileNotFoundError)
 ┌─────────────────────────────┐
 │ Try 3: Type heuristic       │
 │ Regex: ^(test|docs|feat):  │
 │ Map: test→tdd, docs→docs    │
 └─────────────────────────────┘
    ↓ Match?
   YES → PhaseDetectionResult(workflow_phase="tdd", sub_phase=None, source="type-heuristic", confidence="low")
    ↓ NO
 PhaseDetectionResult(workflow_phase="unknown", sub_phase=None, source="unknown", confidence="low")
```

---

### 4.4. Data Flow: Commit Synchronization

```
git_add_or_commit(message="update planning", workflow_phase="planning", sub_phase="c1")
    ↓
ScopeEncoder.generate_scope("planning", "c1", cycle_number=None)
    ↓
Validate: "planning" in workphases.yaml?
    ↓ YES
Format: f"P_{phase.upper()}_SP_{sub_phase.upper()}"
    ↓
"P_PLANNING_SP_C1"
    ↓
Get commit_type from workphases.yaml["planning"]["commit_type"] → "docs"
    ↓
GitManager.commit_with_scope(type="docs", scope="P_PLANNING_SP_C1", message="update planning")
    ↓
Format: f"{type}({scope}): {message}"
    ↓
git commit -m "docs(P_PLANNING_SP_C1): update planning"
```

---

## 5. workphases.yaml Schema

**Location:** `.st3/workphases.yaml`

**Purpose:** Config-SSOT for phase metadata. NOT runtime state.

**Schema:**

```yaml
# workphases.yaml - Workflow Phase Metadata
# Purpose: Config-SSOT (display names, commit type hints)
# NOT runtime state (that's state.json, managed by PhaseStateEngine)

phases:
  research:
    display_name: "🔍 Research"
    description: "Investigate requirements, technical constraints, alternatives"
    commit_type: "docs"  # Default commit type for this phase
    
  planning:
    display_name: "📋 Planning"
    description: "Break down work into cycles, define deliverables"
    commit_type: "docs"
    
  design:
    display_name: "🎨 Design"
    description: "Class structures, schemas, data flows"
    commit_type: "docs"
    
  tdd:
    display_name: "🔴🟢🔵 TDD"
    description: "RED-GREEN-REFACTOR cycles"
    commit_type: "test"  # Most common, can be overridden per commit
    subphases:  # Optional: known subphases (NOT enforced)
      - red
      - green
      - refactor
    
  integration:
    display_name: "🔗 Integration"
    description: "End-to-end testing, system integration"
    commit_type: "test"
    
  documentation:
    display_name: "📚 Documentation"
    description: "Reference docs, agent.md updates"
    commit_type: "docs"

version: "1.0"
```

**Usage:**
- **Referenced by:** workflows.yaml (phase sequences), git.yaml (commit conventions)
- **Parsed by:** ScopeDecoder (validate phase names), ScopeEncoder (generate scopes)
- **NOT used by:** transition_phase (uses state.json + workflows.yaml only)

**Validation Rules:**
- `phases` keys must match workflow phase names in workflows.yaml
- `commit_type` must be valid Conventional Commits type (test, docs, feat, fix, refactor, chore)
- `subphases` is optional metadata (NOT enforced by ScopeEncoder)

---

## 6. Tool Integration Specifications

### 6.1. get_work_context Changes

**File:** `mcp_server/tools/context_tools.py`

**Current Implementation (Issue #117):**
```python
def _detect_tdd_phase(self, commit_message: str) -> Optional[str]:
    """Parse commit type (test:/feat:/docs:) → phase guess."""
    # Only detects TDD phases via type-based heuristic
```

**New Implementation (Cycle 1):**

```python
from mcp_server.utils.scope_decoder import ScopeDecoder, PhaseSource

def get_work_context(self, include_closed_recent: bool = False) -> dict:
    """Get active work context with commit-scope primary phase detection."""
    
    last_commit = self._get_last_commit()  # git log -1 --oneline
    
    decoder = ScopeDecoder(self.workphases_config, self.state_json_path)
    detection = decoder.detect_phase(
        commit_message=last_commit,
        fallback_to_state=True,
        fallback_to_type=True
    )
    
    logger.info(
        f"Phase detected: {detection.workflow_phase} "
        f"(source: {detection.source}, confidence: {detection.confidence})"
    )
    
    return {
        "active_issue": self._get_active_issue(),
        "current_phase": detection.workflow_phase,
        "sub_phase": detection.sub_phase,
        "phase_source": detection.source,  # NEW
        "phase_confidence": detection.confidence,  # NEW
        "recent_commits": self._get_recent_commits(10),
        "blockers": self._check_blockers(),
    }
```

**Breaking Changes:**
- Remove `_detect_tdd_phase()` method
- Add `phase_source` and `phase_confidence` to output dict
- Logging: Always log phase source for debugging

**Acceptance Criteria:**
- Old commits without scope work (type-heuristic fallback)
- Workflow phases visible from commit-scope
- state.json fallback when commit missing scope
- No blocking errors (graceful degradation)

---

### 6.2. get_project_plan Changes

**File:** `mcp_server/tools/project_tools.py`

**Current Implementation (Issue #139):**
```python
def get_project_plan(self, issue_number: int) -> dict:
    # current_phase only from state.json
```

**New Implementation (Cycle 3):**

```python
def get_project_plan(self, issue_number: int) -> dict:
    """Get project plan with commit-scope primary phase detection."""
    
    workflow_name = self._get_workflow_name(issue_number)
    workflow_phases = self._load_workflow_phases(workflow_name)
    
    last_commit = self._get_last_commit()
    decoder = ScopeDecoder(self.workphases_config, self.state_json_path)
    detection = decoder.detect_phase(
        commit_message=last_commit,
        fallback_to_state=True,
        fallback_to_type=False  # No guessing for project plan
    )
    
    return {
        "issue_number": issue_number,
        "workflow_name": workflow_name,
        "phases": workflow_phases,
        "current_phase": detection.workflow_phase,  # NOW VISIBLE
        "phase_source": detection.source,  # NEW
        "completed_phases": self._get_completed_phases(issue_number),
    }
```

**Breaking Changes:**
- Add `current_phase` to output (was missing in Issue #139)
- Add `phase_source` for transparency
- NO type-heuristic fallback (project plan needs accuracy)

---

### 6.3. GitCommitInput Schema Changes

**File:** `mcp_server/tools/git_tools.py`

**Current Schema:**
```python
@tool
def git_add_or_commit(
    phase: str = Field(..., description="TDD phase: red | green | refactor | docs"),
    message: str,
    files: List[str] = Field(default_factory=list),
) -> ToolResult:
    # Validates phase via GitConfig.has_phase() (TDD-only)
```

**New Schema (Cycle 2):**

```python
@tool
def git_add_or_commit(
    message: str = Field(..., description="Commit message (without type/scope prefix)"),
    files: List[str] = Field(default_factory=list),
    
    # NEW: Workflow-first fields
    workflow_phase: Optional[str] = Field(
        None, 
        description="Workflow phase (research|planning|design|tdd|integration|documentation). Auto-detected from state.json if omitted."
    ),
    sub_phase: Optional[str] = Field(
        None,
        description="Sub-phase (e.g., 'red', 'green', 'refactor', 'c1'). Optional."
    ),
    commit_type: Optional[str] = Field(
        None,
        description="Commit type (test|docs|feat|fix|refactor). Auto-detected from workphases.yaml if omitted."
    ),
    cycle_number: Optional[int] = Field(
        None,
        description="Cycle number (e.g., 1, 2, 3). Optional, used in multi-cycle TDD."
    ),
    
    # DEPRECATED: Backward compatibility
    phase: Optional[str] = Field(
        None,
        deprecated=True,
        description="DEPRECATED: Use workflow_phase + sub_phase instead."
    ),
) -> ToolResult:
    """
    Stage and commit with workflow phase scope.
    
    Examples:
        # Workflow phase (auto-detect commit_type from workphases.yaml)
        git_add_or_commit(
            message="complete research",
            workflow_phase="research"
        )
        → Commit: docs(P_RESEARCH): complete research
        
        # TDD cycle with explicit tracking
        git_add_or_commit(
            message="add user tests",
            workflow_phase="tdd",
            sub_phase="red",
            cycle_number=1
        )
        → Commit: test(P_TDD_SP_C1_RED): add user tests
        
        # Backward compatible (old format)
        git_add_or_commit(
            phase="red",
            message="add user tests"
        )
        → Commit: test: add user tests (legacy format)
    """
```

**Breaking Changes:**
- `phase` parameter deprecated (retained for backward compat)
- Add 4 new parameters: `workflow_phase`, `sub_phase`, `commit_type`, `cycle_number`
- Auto-detection: Read workflow_phase from state.json if omitted
- Auto-detection: Read commit_type from workphases.yaml if omitted

**Validation:**
- `workflow_phase` MUST exist in workphases.yaml
- Error message MUST include valid phase list + example commit (Issue #121)
- `sub_phase`: NO validation (flexible for custom cycles)
- `commit_type`: MUST be valid Conventional Commits type

---

## 7. Failure Modes & Error Handling

### 7.1. Missing Commit Scope

**Scenario:** Old commit without `P_PHASE` scope.

**Behavior:**
1. ScopeDecoder._parse_commit_scope() returns None
2. Fallback to state.json (if exists)
3. Fallback to type-heuristic (test: → tdd)
4. Final fallback: unknown (confidence=low)

**User Impact:** ✅ No blocking errors, tools continue working.

**Logging:** `logger.info("Phase detection: type-heuristic (confidence: low)")`

---

### 7.2. Invalid Phase Name in Scope

**Scenario:** Commit with `P_INVALIDPHASE` scope.

**Behavior:**
1. ScopeDecoder parses scope, extracts "invalidphase"
2. Validates against workphases.yaml → NOT FOUND
3. Returns None, activates state.json fallback
4. Tool continues (graceful degradation)

**User Impact:** ✅ No blocking errors, phase detected from state.json.

**Logging:** `logger.warning("Invalid phase 'invalidphase' in commit scope, using state.json fallback")`

---

### 7.3. state.json Missing (Branch Switch)

**Scenario:** User switches branch, state.json deleted (not tracked).

**Behavior:**
1. ScopeDecoder reads commit-scope → SUCCESS (primary source)
2. state.json fallback not needed
3. Tool returns phase from git history

**User Impact:** ✅ Branch switching resilient (commit-scope primary for context tools).

**Logging:** `logger.info("Phase detection: commit-scope (confidence: high)")`

---

### 7.4. Unknown Workflow Phase in git_add_or_commit

**Scenario:** Agent calls `git_add_or_commit(workflow_phase="invalid_phase", ...)`.

**Behavior:**
1. ScopeEncoder.generate_scope() validates against workphases.yaml
2. Phase NOT FOUND → Raises ValueError
3. Error message includes valid phase list + example commit

**User Impact:** ❌ Blocking error (intentional - prevent bad commits).

**Example Error Message (Issue #121 compliance):**
```
ValueError: Unknown workflow phase: 'invalid_phase'

Valid phases: research, planning, design, tdd, integration, documentation

Example:
  git_add_or_commit(
      message="complete research",
      workflow_phase="research"
  )
```

---

## 8. Open Questions

| # | Question | Options | Status | Decision Needed By |
|---|----------|---------|--------|--------------------|
| 1 | Cycle number tracking: manual or auto? | **A)** Manual input (simpler)<br>**B)** Auto-increment in state.json | 🟡 Suggest A | TDD Cycle 2 |
| 2 | Error message format for invalid scopes? | **A)** Show valid phases only<br>**B)** Show example commit | 🟡 Suggest both | TDD Cycle 2 |
| 3 | State.json sync: automatic or explicit? | **A)** git_add_or_commit syncs<br>**B)** Separate tool | 🟡 Suggest A | TDD Cycle 2 |
| 4 | Sub-phase validation: strict or flexible? | **A)** Whitelist subphases<br>**B)** Accept any string | 🟡 Suggest B | TDD Cycle 1 |

---

## Related Documentation

- [research.md](research.md) - Dual-source model rationale (v2.2)
- [planning.md](planning.md) - 4 vertical delivery cycles (v1.2)
- [../../reference/mcp/tools/project.md](../../reference/mcp/tools/project.md) - PhaseStateEngine contracts
- [../../reference/mcp/tools/git.md](../../reference/mcp/tools/git.md) - Git tooling TDD-focus
- [../../coding_standards/TYPE_CHECKING_PLAYBOOK.md](../../coding_standards/TYPE_CHECKING_PLAYBOOK.md) - Type checking rules

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-14 | Agent | Initial draft with complete architecture, interface contracts, data flows, failure modes |

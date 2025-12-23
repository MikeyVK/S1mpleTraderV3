# Issue #18 Implementation Plan: Tooling-Enforced Lifecycle Workflow

**Status:** ACTIVE IMPLEMENTATION  
**Branch:** `feature/issue-18-choke-point-enforcement`  
**Created:** 2025-12-22  
**Last Updated:** 2025-12-23  
**Issue:** #18  
**Plan Doc:** [ISSUE_18_CHOKE_POINT_ENFORCEMENT_PLAN.md](ISSUE_18_CHOKE_POINT_ENFORCEMENT_PLAN.md)  
**Phase 0 Complete:** ✅ [PROJECT_INITIALIZATION_DESIGN.md](PROJECT_INITIALIZATION_DESIGN.md)

---

## 1. Executive Summary

We implement deterministic, tooling-enforced workflow across **all 7 SDLC phases** where:
- **Phase state is stored, not inferred** (`.st3/state.json` tracks current phase + history)
- **Choke points enforce phase transitions** (transition_phase/commit/PR/close tools block invalid operations)
- **MCP tools are mandatory** (file creation, scaffolding, testing enforced via PolicyEngine)
- **GitHub labels auto-sync** (phase transitions automatically update issue labels)
- **SafeEdit stays fast** (no subprocess QA on edit; enforcement at choke points)
- **Output format is identical per agent** (policy engine decides, tools execute, same errors/success per scenario)

### Key Principle
> "Agent input = creative thinking + coding. Process control = tooling, not instructions."

### Integration with ST3 Development Lifecycle

This plan implements enforcement for the **complete 7-phase SDLC model** documented in [PHASE_WORKFLOWS.md](../../mcp_server/PHASE_WORKFLOWS.md):

| Phase | Name | GitHub Label Transition | Entry Requirement | Exit Requirement |
|-------|------|------------------------|-------------------|------------------|
| 0 | Discovery | `phase:discovery` → `phase:discussion` | Issue created | Research complete |
| 1 | Planning | `phase:discussion` → `phase:design` | Discussion approved | Plan document exists |
| 2 | Architectural Design | `phase:design` → `phase:review` | Plan approved | Arch doc exists (or pass-through) |
| 3 | Component Design | `phase:review` → `phase:approved` | Arch reviewed | Component design exists |
| **4** | **TDD Implementation** | **`phase:approved` → `phase:red` → `phase:green` → `phase:refactor`** | Design approved | Tests + QA pass |
| 5 | Integration | `phase:refactor` → `phase:review` | REFACTOR done | Integration tests pass |
| 6 | Documentation | `phase:review` → `phase:documentation` → `phase:done` | Integration done | Reference docs exist |

**Phase 4 (TDD) has three sub-phases:**
- **4a: RED** (label: `phase:red`, commit: `test:`) - Write failing tests
- **4b: GREEN** (label: `phase:green`, commit: `feat:`) - Minimal implementation
- **4c: REFACTOR** (label: `phase:refactor`, commit: `refactor:`) - Quality improvement

**Human-in-the-loop pass-through:** Project lead can skip phases (e.g., no arch doc for trivial changes) via explicit `transition_phase` command with `pass_through=True` flag.

---

## 2. Current State Analysis

### 2.1 What Exists Today

| Component | Status | Notes |
|-----------|--------|-------|
| **Phase 0: Bootstrap Tooling** | ✅ **COMPLETE** | `ProjectManager`, `ValidateProjectStructureTool`, 72 tests, 10/10 quality |
| Project initialization | ✅ Implemented | Creates milestone, parent issue, sub-issues from spec |
| Validation tooling | ✅ Implemented | Validates project structure against GitHub API |
| Structured logging | ✅ Implemented | 16 methods instrumented (ProjectManager + GitHubAdapter) |
| State persistence | ✅ Implemented | `.st3/projects.json` with atomic writes |
| Phase concepts | ✅ Documented | `docs/mcp_server/PHASE_WORKFLOWS.md` + GitHub labels |
| Scaffolding tools | ✅ Implemented | `scaffold_component`, `scaffold_design_doc` exist |
| `st3://status/phase` resource | ✅ Implemented | Infers phase from branch name (weak) |
| TDD phase in commit tool | ✅ Basic | `git_add_or_commit` takes `phase` param, only affects prefix |
| Quality gates | ✅ Implemented | `QAManager` runs pylint/mypy/pyright |
| Test runner | ✅ Implemented | `run_tests` tool exists |
| Tool Priority Matrix | ✅ Documented | `AGENT_PROMPT.md` Phase 4 |
| 7-phase state machine | ❌ Missing | No phase transition enforcement |
| Phase state persistence | ❌ Missing | No `.st3/state.json` (but `.st3/projects.json` exists) |
| Protected branch logic | ❌ Missing | Can commit to `main` today |
| Commit-time gating | ❌ Missing | No test/QA enforcement |
| PR/close gating | ❌ Missing | No artifact/QA enforcement |
| MCP tool enforcement | ❌ Missing | Can use `create_file` instead of `scaffold_component` |
| Label auto-sync | ❌ Missing | Labels not updated on phase transitions |

### 2.2 Gaps vs Issue #18 Requirements

| Requirement | Gap | Blocker? |
|-------------|-----|----------|
| FR1: Block commits on `main` | No check exists | 🔴 YES |
| FR2: 7-phase state machine | No phase transition enforcement | 🔴 YES |
| FR3: Phase-aware commit gating | No test/QA enforcement | 🔴 YES |
| FR4: PR/close artifact enforcement | No validation hooks | 🔴 YES |
| FR5: Persistent phase state | No `.st3/state.json` | 🔴 YES |
| FR6: MCP tool enforcement | No file creation blocking | 🔴 YES |
| FR7: Label auto-sync | No GitHub label updates | 🔴 YES |
| FR8: Actionable error messages | Exists but incomplete | 🟡 Medium |

### 2.3 Tool Priority Matrix Enforcement

Per [AGENT_PROMPT.md](../../../AGENT_PROMPT.md) Phase 4, these operations **must** use MCP tools:

| Operation | ✅ Required Tool | ❌ Forbidden | Enforcement Point |
|-----------|-----------------|-------------|-------------------|
| Create branch | `create_feature_branch` | `git checkout -b` | Git wrapper |
| Commit | `git_add_or_commit` | `git commit` | Git wrapper |
| Scaffold doc | `scaffold_design_doc` | `create_file` | File creation tools |
| Scaffold code | `scaffold_component` | `create_file` | File creation tools |
| Run tests | `run_tests` | `pytest` terminal | Commit choke point |
| Quality gates | `run_quality_gates` | Manual pylint | Commit choke point |

---

## 3. Implementation Phases

### Phase 0: Bootstrap Tooling ✅ **COMPLETE**

**Status:** ✅ **100% COMPLETE** (2025-12-23)  
**Branch:** `feature/issue-18-choke-point-enforcement`  
**Design Doc:** [PROJECT_INITIALIZATION_DESIGN.md](PROJECT_INITIALIZATION_DESIGN.md)  
**Commits:** `757945593c7` (structured logging), `28f0c4a36e5` (validation tool)

**Goal:** Build foundational project initialization infrastructure to enable automated Issue #18 implementation tracking.

**Why this phase:** Before enforcing Issue #18 workflow, we need tooling to initialize the project structure itself. This creates the bootstrap: Issue #18 can use `initialize_project` to create its own milestone + sub-issues.

#### 0.1 What Was Delivered

**Core Components:**
- ✅ **`ProjectManager.initialize_project()`** - Creates milestone, parent issue, sub-issues from ProjectSpec
- ✅ **`ValidateProjectStructureTool`** - MCP tool to validate project structure against GitHub
- ✅ **Structured Logging** - Complete audit trail (ProjectManager + GitHubAdapter, 16 instrumented methods)
- ✅ **Duplicate Detection** - Fuzzy matching with SequenceMatcher (80% threshold)
- ✅ **Dependency Validation** - Cycle detection via DependencyGraphValidator
- ✅ **Atomic Persistence** - `.st3/projects.json` with `.tmp` file pattern

**DTOs (all Pydantic models):**
- ✅ `ProjectSpec` - Input specification (title, phases, parent_issue_number, force_create_parent)
- ✅ `PhaseSpec` - Phase definition (phase_id, title, depends_on, blocks, labels)
- ✅ `ProjectMetadata` - Persisted state (project_id, milestone_id, parent_issue_number, phases)
- ✅ `SubIssueMetadata` - Per-phase tracking (issue_number, url, depends_on, blocks, status)
- ✅ `ProjectSummary` - Output result (includes dependency_graph)
- ✅ `ValidationResult` - Validation output (valid, errors, warnings)
- ✅ `ValidationError` - Structured error (error_type, message, details)

**Test Coverage:**
- ✅ **72 tests passing** (67 existing + 11 new for validation tool)
- ✅ **Quality:** ProjectManager 10/10 pylint, GitHubAdapter 9.74/10, mypy clean
- ✅ **Integration test:** Dogfood test with Issue #18 scenario

**Key Features:**
1. **Duplicate Prevention:** Searches GitHub for similar titles (>80% = error, >60% = warning)
2. **Parent Issue Validation:** Can use existing parent or create new with `[PARENT]` prefix
3. **Dependency Graph:** Validates acyclic, builds phase_id → blocked_phases mapping
4. **Atomic Writes:** `.st3/projects.json` updated via `.tmp` file to prevent corruption
5. **Comprehensive Logging:** Every GitHub operation logged (INFO/DEBUG/ERROR levels)

**Example Usage:**
```python
# Initialize Issue #18 project using this tooling:
spec = ProjectSpec(
    project_title="Issue #18: Choke Point Enforcement",
    parent_issue_number=18,  # Use existing issue
    phases=[
        PhaseSpec(phase_id="0", title="Bootstrap", depends_on=[], blocks=["A"]),
        PhaseSpec(phase_id="A", title="State Engine", depends_on=["0"], blocks=["B"]),
        PhaseSpec(phase_id="B", title="Transition Tool", depends_on=["A"], blocks=["C"]),
        # ... etc
    ]
)
result = await manager.initialize_project(spec)
# Creates milestone, validates parent issue #18, creates sub-issues, persists to .st3/projects.json
```

#### 0.2 Integration with Issue #18

**How Phase 0 Enables Issue #18:**

1. **Self-Initialization:** Issue #18 implementation can use `initialize_project` to create its own tracking structure
2. **Validation Foundation:** `ValidateProjectStructureTool` provides pattern for future validation tools
3. **Logging Infrastructure:** Structured logging established for all future components
4. **State Persistence:** `.st3/projects.json` pattern established for state management (Phase A will extend with `.st3/state.json`)
5. **GitHub Integration:** GitHubAdapter with comprehensive error handling provides foundation for label sync (Phase C)

**Phase Mapping:**
- Phase 0 (Bootstrap) → Provides tools to initialize Issue #18 project structure
- Phase A (State Engine) → Will use similar state persistence pattern (`.st3/state.json`)
- Phase C (Label Sync) → Will extend GitHubAdapter logging patterns
- Phase D (Commit Gating) → Will use validation patterns from ValidateProjectStructureTool

#### 0.3 Lessons for Future Phases

**Design Patterns Established:**
1. **Manager Pattern:** ProjectManager orchestrates, adapters handle I/O
2. **Pydantic DTOs:** Type-safe, validated data models
3. **Async Tools:** Non-blocking MCP tool execution
4. **Atomic I/O:** `.tmp` file pattern for safe state updates
5. **Comprehensive Testing:** Unit tests + dogfood integration tests

**Challenges Solved:**
1. Async/await in pytest (use `@pytest.mark.asyncio`)
2. ToolResult dict access (`content[0]["text"]`)
3. Fuzzy matching thresholds (tuned via real-world testing)
4. Duplicate detection user experience (actionable error messages)
5. Quality gates at 10/10 (line length, trailing whitespace)

---

### Phase A: Foundation (Full Lifecycle State Engine + Policy) 🏗️

**Goal:** Add 7-phase state machine + policy decision layer WITHOUT changing tool behavior (feature-flagged).

**Why this phase:** Establish testable state transitions and decision logic before wiring into tools. TDD foundation first.

**Builds on Phase 0:** Uses similar patterns (Pydantic DTOs, atomic `.st3/` persistence, structured logging, comprehensive testing).

#### A.1 Tasks

- [ ] **A.1.1 RED:** Write unit tests for `PhaseStateEngine` (7-phase lifecycle)
  - [ ] Test: read empty state → returns phase 0 (Discovery)
  - [ ] Test: write phase 1 state for branch → persists to `.st3/state.json`
  - [ ] Test: read state for branch → returns stored phase
  - [ ] Test: transition 0→1 (Discovery→Planning) → succeeds
  - [ ] Test: transition 1→3 (skip phase 2) without pass_through flag → fails
  - [ ] Test: transition 1→3 with pass_through=True → succeeds, logs skip
  - [ ] Test: transition 4.red→4.green (TDD sub-phase) → succeeds
  - [ ] Test: transition 4.red→4.refactor (skip GREEN) → fails
  - [ ] Test: concurrent branch states don't interfere
  - [ ] Test: malformed JSON → recovers gracefully
  - [ ] Test: phase history tracking → records all transitions
  - [ ] Test: tool usage tracking → increments counters

- [ ] **A.1.2 RED:** Write unit tests for `PolicyEngine` (full lifecycle)
  - [ ] Test: commit on `main` → deny with "use feature branch" message
  - [ ] Test: transition to phase 2 without phase 1 artifacts → deny
  - [ ] Test: transition to phase 4 without phase 3 approval → deny
  - [ ] Test: GREEN commit + failing tests → deny with "run tests" message
  - [ ] Test: GREEN commit + passing tests → allow
  - [ ] Test: REFACTOR commit + failing QA → deny with "run quality_gates" message
  - [ ] Test: REFACTOR commit + passing QA → allow
  - [ ] Test: RED commit + no test files changed → deny
  - [ ] Test: RED commit + test files changed → allow (even if tests fail)
  - [ ] Test: file creation in `docs/**/*.md` without scaffold metadata → deny
  - [ ] Test: file creation in `backend/**/*.py` without scaffold metadata → deny
  - [ ] Test: PR creation from phase 3 (not finished REFACTOR) → deny
  - [ ] Test: issue close from phase 5 (not finished docs) → deny
  - [ ] Test: issue label mismatch (phase:red, trying GREEN commit) → deny

- [ ] **A.1.3 GREEN:** Implement `PhaseStateEngine`
  - [ ] Create `mcp_server/core/phase_state.py`
  - [ ] Data model: `PhaseState` with fields:
    - `current_phase: int` (0-6)
    - `tdd_subphase: str | None` ("red"/"green"/"refactor" for phase 4)
    - `issue_number: int | None`
    - `phase_history: list[PhaseTransition]`
    - `tool_usage: dict[str, int]`
    - `updated_at: datetime`
  - [ ] Class: `PhaseStateEngine` with methods:
    - `get_state(branch: str) -> PhaseState`
    - `set_phase(branch: str, phase: int, subphase: str | None, issue_number: int | None) -> None`
    - `can_transition(from_phase: PhaseState, to_phase: int, to_subphase: str | None, pass_through: bool) -> tuple[bool, str]`
    - `record_transition(branch: str, to_phase: int, to_subphase: str | None, pass_through: bool) -> None`
    - `increment_tool_usage(branch: str, tool_name: str) -> None`
  - [ ] Persistence: read/write `.st3/state.json` (gitignored)
  - [ ] All RED tests pass

- [ ] **A.1.4 GREEN:** Implement `PolicyEngine`
  - [ ] Create `mcp_server/core/policy.py`
  - [ ] Data classes (from plan doc + extensions):
    ```python
    @dataclass(frozen=True)
    class PolicyContext:
        operation: Operation  # COMMIT | TRANSITION | CREATE_PR | CLOSE_ISSUE | CREATE_FILE
        branch: str
        phase: PhaseState
        changed_files: tuple[str, ...]
        staged_files: tuple[str, ...]
        issue_number: int | None = None
        issue_labels: tuple[str, ...] = ()
        target_phase: int | None = None
        target_subphase: str | None = None
        pass_through: bool = False
        file_path: str | None = None  # For CREATE_FILE operation
        scaffold_metadata: dict[str, Any] | None = None
    ```
  - [ ] Class: `PolicyEngine` with methods:
    - `decide(ctx: PolicyContext) -> PolicyDecision`
    - `_check_protected_branch(ctx) -> tuple[bool, list[str]]`
    - `_check_phase_transition(ctx) -> tuple[bool, list[str]]`
    - `_check_artifact_requirements(ctx) -> tuple[bool, list[str]]`
    - `_check_tdd_gates(ctx) -> tuple[bool, list[str]]`
    - `_check_label_sync(ctx) -> tuple[bool, list[str]]`
    - `_check_tool_compliance(ctx) -> tuple[bool, list[str]]`
  - [ ] Decision matrix implementation:
    - Protected branch check
    - Phase transition validation (0→1→2→3→4→5→6)
    - Artifact requirements per phase (see section 3.1 below)
    - GitHub label phase check (if issue_number provided)
    - Phase transition validation (cannot skip without pass_through)
    - TDD sub-phase transitions (red→green→refactor)
    - Commit message prefix validation (test:/feat:/refactor:)
    - Staged files analysis for RED "test-only" check
    - MCP tool usage validation (file creation must use scaffold)
  - [ ] All RED tests pass

- [ ] **A.1.5 REFACTOR:** Quality gates + docs
  - [ ] Pylint 10/10 on new modules
  - [ ] Mypy + Pyright pass
  - [ ] Docstrings on all public methods
  - [ ] Add unit test file paths to git (tests committed)

#### A.2 Exit Criteria

- [ ] Unit tests: 30+ passing for phase_state + policy modules
- [ ] Quality gates: pass on new modules
- [ ] `.st3/state.json` structure documented
- [ ] `.st3/` added to `.gitignore`
- [ ] NO behavior change in any tool yet (just infrastructure)

#### A.3 Deliverables

- `mcp_server/core/phase_state.py` (PhaseStateEngine with 7-phase support)
- `mcp_server/core/policy.py` (PolicyEngine + extended data models)
- `tests/unit/mcp_server/core/test_phase_state.py` (lifecycle tests)
- `tests/unit/mcp_server/core/test_policy.py` (full lifecycle tests)
- `.gitignore` entry for `.st3/`

---

### 3.1 Artifact Requirements Per Phase

PolicyEngine validates these artifacts exist before allowing phase transitions:

| Phase Transition | Required Artifacts | Validation Tool | Block If Missing? |
|-----------------|-------------------|-----------------|-------------------|
| 0→1 (Discovery→Planning) | None (research only) | N/A | No |
| 1→2 (Planning→Arch Design) | Plan document OR pass_through | `validate_document_structure` | Yes |
| 2→3 (Arch→Component Design) | Arch document OR pass_through | `validate_document_structure` | Yes |
| 3→4 (Component→TDD) | Component design + test scenarios | `validate_template` | Yes |
| 4→5 (TDD→Integration) | Tests passing + QA 10/10 | `run_tests` + `run_quality_gates` | Yes |
| 5→6 (Integration→Documentation) | Integration tests passing | `run_tests` | Yes |
| 6→done | Reference docs exist | File existence check | Yes |

**Artifact paths convention:**
```
docs/development/issues/{issue_number}/
  ├── 01_discovery_notes.md          (Phase 0, optional)
  ├── 02_implementation_plan.md      (Phase 1, required)
  ├── 03_architectural_design.md     (Phase 2, required or pass_through)
  ├── 04_component_design.md         (Phase 3, required)
  ├── 05_walkthrough.md              (Phase 6, required)
  └── test_scenarios.md              (Phase 3, required)
```

---

### Phase B: Phase Transition Tool 🔄

**Goal:** Add `transition_phase` tool for explicit phase transitions with enforcement.

**Why this phase:** Core mechanism for moving through lifecycle. Must work before commit/PR/close tools can enforce.

#### B.1 Tasks

- [ ] **B.1.1 RED:** Write integration tests for phase transitions
  - [ ] Test: transition 0→1 without plan doc → error, suggests scaffold_design_doc
  - [ ] Test: transition 0→1 with plan doc → succeeds, updates state + label
  - [ ] Test: transition 1→3 without pass_through → error, explains phase 2 required
  - [ ] Test: transition 1→3 with pass_through=True → succeeds, logs skip
  - [ ] Test: transition 3→4 (enter TDD) → succeeds, sets subphase=red
  - [ ] Test: transition from phase 4.red to 4.green → succeeds (handled by commit tool)
  - [ ] Test: transition 4→5 while in RED subphase → error, must finish REFACTOR
  - [ ] Test: transition with issue label mismatch → auto-syncs label via update_issue

- [ ] **B.1.2 GREEN:** Implement `TransitionPhaseTool`
  - [ ] Create tool in `mcp_server/tools/workflow_tools.py`
  - [ ] Parameters:
    - `issue_number: int` (required)
    - `to_phase: int` (0-6, required)
    - `pass_through: bool = False` (skip phase if allowed)
  - [ ] Logic:
    1. Get current branch + issue
    2. Get current phase state from PhaseStateEngine
    3. Build PolicyContext with operation=TRANSITION
    4. Call PolicyEngine.decide(ctx)
    5. If denied: raise error with actionable message
    6. If allowed:
       - Record transition in PhaseStateEngine
       - Auto-sync GitHub label via update_issue tool
       - Log transition with reason
    7. Return success message

- [ ] **B.1.3 GREEN:** Wire GitHubAdapter for label updates
  - [ ] Method: `update_issue_labels(issue_number: int, add_labels: list[str], remove_labels: list[str]) -> None`
  - [ ] Logic: call GitHub API to update labels
  - [ ] Error handling: if API fails, log but don't block transition

- [ ] **B.1.4 REFACTOR:** Quality gates + error messages
  - [ ] All error messages reference correct MCP tools
  - [ ] Pylint 10/10
  - [ ] Mypy + Pyright pass
  - [ ] Integration tests pass

#### B.2 Exit Criteria

- [ ] Can transition through all 7 phases with valid artifacts
- [ ] Cannot skip phases without pass_through flag
- [ ] GitHub labels auto-sync on phase transitions
- [ ] Error messages actionable (suggest scaffold tools, artifact paths)

#### B.3 Deliverables

- `mcp_server/tools/workflow_tools.py` (TransitionPhaseTool)
- Updated `mcp_server/adapters/github_adapter.py` (label update method)
- `tests/unit/tools/test_workflow_tools.py` (transition tests)

---

### Phase C: Commit Choke Point (TDD Sub-Phases) 🚧

**Goal:** Enforce TDD sub-phase transitions (red→green→refactor) in `git_add_or_commit` with auto-label-sync.

**Why this phase:** Highest ROI enforcement point. Stops bad commits immediately.

#### C.1 Tasks

- [ ] **C.1.1 RED:** Write integration tests for commit enforcement
  - [ ] Test: commit to `main` → tool returns error, explains "create feature branch"
  - [ ] Test: GREEN commit, tests fail → tool returns error, explains "run tests"
  - [ ] Test: GREEN commit, tests pass, label is phase:red → succeeds, auto-updates label to phase:green
  - [ ] Test: REFACTOR commit, QA fails → tool returns error, explains "run quality_gates"
  - [ ] Test: REFACTOR commit, QA passes → tool succeeds, auto-updates label to phase:refactor
  - [ ] Test: RED commit, no test changes → tool returns error
  - [ ] Test: RED commit with test changes → tool succeeds (even if tests fail), sets label phase:red
  - [ ] Test: commit message without correct prefix → error, explains test:/feat:/refactor:
  - [ ] Test: GREEN commit when not in phase 4 → error, explains "use transition_phase to enter TDD"

- [ ] **C.1.2 GREEN:** Wire `PolicyEngine` into `GitManager.commit_tdd_phase`
  - [ ] Add `policy: PolicyEngine` + `phase_state: PhaseStateEngine` dependencies to `GitManager.__init__`
  - [ ] Before commit:
    1. Get current phase state
    2. Validate commit message prefix matches phase (test:/feat:/refactor:)
    3. Build PolicyContext with operation=COMMIT
    4. Call `policy.decide(ctx)` with:
       - branch=current
       - phase=current phase state
       - staged_files=from adapter
       - issue_number=from branch or state
       - issue_labels=from GitHub API
    5. If `decision.allow == False`: raise `PreflightError` with `decision.reasons`
    6. If `decision.allow == True`: run `decision.required_gates`:
       - "tests" → call `run_tests` tool
       - "quality" → call `QAManager.run_quality_gates`
  - [ ] After successful commit:
    1. Update TDD subphase in PhaseStateEngine
    2. Auto-sync GitHub label via GitHubAdapter
    3. Increment tool usage counter

- [ ] **C.1.3 GREEN:** Add gate execution helpers to `GitManager`
  - [ ] Method: `_run_tests_gate() -> tuple[bool, str]`
    - Runs `pytest` via subprocess
    - Returns (passed, output_summary)
  - [ ] Method: `_run_quality_gate(files) -> tuple[bool, str]`
    - Calls `QAManager.run_quality_gates(files)`
    - Returns (passed, output_summary)
  - [ ] Method: `_validate_commit_prefix(phase: str, message: str) -> tuple[bool, str]`
    - Checks message starts with correct prefix
    - Returns (valid, error_message)

- [ ] **C.1.4 GREEN:** Update `GitAdapter` to expose staged files
  - [ ] Method: `get_staged_files() -> list[str]`
    - Uses `repo.index.diff("HEAD")`
    - Returns list of staged file paths

- [ ] **C.1.5 REFACTOR:** Error messages + quality
  - [ ] All error messages reference ST3 tools (not manual git/terminal)
  - [ ] Pylint 10/10
  - [ ] Mypy + Pyright pass
  - [ ] Integration tests pass

#### C.2 Exit Criteria

- [ ] Cannot commit to `main` via `git_add_or_commit`
- [ ] Cannot commit GREEN without passing tests
- [ ] Cannot commit REFACTOR without passing QA
- [ ] RED commits succeed with test changes (tests may fail)
- [ ] GitHub labels auto-sync on TDD sub-phase transitions
- [ ] Commit message prefix validated (test:/feat:/refactor:)
- [ ] Phase state persists to `.st3/state.json` after commit
- [ ] Error messages guide to correct tool

#### C.3 Deliverables

- Updated `mcp_server/managers/git_manager.py` (enforcement logic)
- Updated `mcp_server/adapters/git_adapter.py` (staged files method)
- `tests/unit/mcp_server/managers/test_git_manager.py` (new enforcement tests)
- Integration tests in `tests/unit/mcp_server/integration/test_git.py`

---

### Phase D: File Creation Enforcement (MCP Tools Only) 📁

**Goal:** Block manual file creation, enforce `scaffold_component` and `scaffold_design_doc`.

**Why this phase:** Ensures all files follow templates and conventions. Critical for deterministic output.

#### D.1 Tasks

- [ ] **D.1.1 RED:** Write tests for file creation enforcement
  - [ ] Test: `create_file` for `docs/**/*.md` → error, suggests scaffold_design_doc
  - [ ] Test: `create_file` for `backend/**/*.py` → error, suggests scaffold_component
  - [ ] Test: `safe_edit_file` to create new doc → error, suggests scaffold_design_doc
  - [ ] Test: `safe_edit_file` to create new code → error, suggests scaffold_component
  - [ ] Test: `scaffold_design_doc` → succeeds, increments tool usage
  - [ ] Test: `scaffold_component` → succeeds, increments tool usage

- [ ] **D.1.2 GREEN:** Add file creation validation to PolicyEngine
  - [ ] Method: `_check_file_creation_compliance(ctx: PolicyContext) -> tuple[bool, list[str]]`
    - If `ctx.operation == CREATE_FILE`:
      - Check `ctx.file_path` against patterns
      - If `docs/**/*.md`: require scaffold metadata
      - If `backend/**/*.py` or `tests/**/*.py`: require scaffold metadata
      - If `mcp_server/**/*.py`: require scaffold metadata
    - Return (allowed, reasons)

- [ ] **D.1.3 GREEN:** Wire enforcement into file creation tools
  - [ ] Update `create_file` tool wrapper (if exists) to check policy first
  - [ ] Update `safe_edit_file` to check policy if creating new file
  - [ ] On policy denial: raise error with scaffold tool suggestion

- [ ] **D.1.4 GREEN:** Update scaffold tools to mark files
  - [ ] `scaffold_component`: add metadata comment to generated files
  - [ ] `scaffold_design_doc`: add metadata frontmatter to generated docs
  - [ ] Metadata format:
    ```python
    # Generated by scaffold_component v1.0 on 2025-12-22
    ```
    ```markdown
    ---
    generated_by: scaffold_design_doc
    template: tracking
    generated_at: 2025-12-22T10:30:00Z
    ---
    ```

- [ ] **D.1.5 REFACTOR:** Quality gates
  - [ ] Tests pass
  - [ ] Pylint 10/10
  - [ ] Error messages actionable

#### D.2 Exit Criteria

- [ ] Cannot create files in `docs/` without `scaffold_design_doc`
- [ ] Cannot create files in `backend/` or `tests/` without `scaffold_component`
- [ ] Scaffold tools mark generated files with metadata
- [ ] PolicyEngine validates metadata presence
- [ ] Tool usage tracked in `.st3/state.json`

#### D.3 Deliverables

- Updated `mcp_server/core/policy.py` (file creation checks)
- Updated scaffold tools (metadata generation)
- Wrapper or validation hooks for `create_file` and `safe_edit_file`
- `tests/unit/mcp_server/core/test_file_creation_enforcement.py`

---

### Phase E: PR + Close Choke Points (Lifecycle Exit Gates) 🎯

**Goal:** Enforce phase-appropriate artifacts and completion at PR creation and issue close.

**Why this phase:** Prevents incomplete work from being marked "done" or merged.

#### E.1 Tasks

- [ ] **E.1.1 RED:** Write tests for PR artifact enforcement
  - [ ] Test: `create_pr` from phase 3 (not in phase 4) → error, explains "enter TDD phase first"
  - [ ] Test: `create_pr` from phase 4.red (not finished) → error, explains "complete REFACTOR"
  - [ ] Test: `create_pr` from phase 4.refactor without required docs → error, lists missing files
  - [ ] Test: `create_pr` from phase 4.refactor with valid docs + passing QA → succeeds, transitions to phase 5
  - [ ] Test: `create_pr` with valid docs + failing QA → error (blocking)

- [ ] **E.1.2 RED:** Write tests for issue close enforcement
  - [ ] Test: `close_issue` from phase 5 (not finished docs) → error, explains "complete documentation phase"
  - [ ] Test: `close_issue` from phase 6 without reference docs → error, lists missing files
  - [ ] Test: `close_issue` from phase 6 with docs → succeeds, adds summary comment, updates label to phase:done

- [ ] **E.1.3 GREEN:** Implement `ArtifactValidator`
  - [ ] Create `mcp_server/managers/artifact_validator.py`
  - [ ] Class: `ArtifactValidator`
  - [ ] Method: `validate_phase_artifacts(issue_number: int, phase: int) -> tuple[bool, list[str]]`
    - Check required artifacts per phase (see section 3.1)
    - Validate structure via `validate_document_structure` tool
    - Validate template compliance via `validate_template` tool
    - Check for template placeholders still present (e.g., `{COMPONENT_NAME}`)
    - Returns (valid, missing_or_invalid_files)

- [ ] **E.1.4 GREEN:** Wire enforcement into `CreatePRTool`
  - [ ] Before creating PR:
    1. Get current phase state
    2. Validate phase >= 4 and subphase == "refactor"
    3. Call `ArtifactValidator.validate_phase_artifacts(issue_number, 4)`
    4. If invalid: return error with missing files + suggest scaffold tools
    5. Run `QAManager.run_quality_gates` on changed files
    6. If QA fails: **block** with error (not warning)
  - [ ] After successful PR creation:
    1. Call `transition_phase(issue_number, to_phase=5)`
    2. Update label to `phase:review`

- [ ] **E.1.5 GREEN:** Wire enforcement into `CloseIssueTool`
  - [ ] Before closing:
    1. Get current phase state
    2. Validate phase >= 6
    3. Call `ArtifactValidator.validate_phase_artifacts(issue_number, 6)`
    4. If invalid: return error
  - [ ] If valid:
    1. Generate closing summary comment from artifacts
    2. Add comment via GitHub API
    3. Update label to `phase:done`
    4. Close issue

- [ ] **E.1.6 REFACTOR:** Quality gates
  - [ ] Pylint 10/10
  - [ ] Mypy + Pyright pass
  - [ ] All tests pass

#### E.2 Exit Criteria

- [ ] Cannot create PR unless in phase 4.refactor with passing QA
- [ ] Cannot create PR without required phase 4 artifacts
- [ ] Cannot close issue unless in phase 6 with required docs
- [ ] PR creation auto-transitions to phase 5
- [ ] Issue close auto-updates label to phase:done
- [ ] Error messages guide to scaffold tools

#### E.3 Deliverables

- `mcp_server/managers/artifact_validator.py` (new)
- Updated `mcp_server/tools/github_tools.py` (`CreatePRTool`, `CloseIssueTool`)
- `tests/unit/mcp_server/managers/test_artifact_validator.py` (new)
- Updated `tests/unit/tools/test_github_tools.py`

---

### Phase F: SafeEdit Fast-Only Alignment 🚀

**Goal:** Ensure SafeEdit never runs slow subprocess QA; move all gating to choke points.

**Why this phase:** Improves UX and ensures enforcement consistency.

#### F.1 Tasks

- [ ] **F.1.1 Audit:** Review `safe_edit_file` current behavior
  - [ ] Document which code paths trigger subprocess QA today
  - [ ] Identify any "full QA" calls

- [ ] **F.1.2 RED:** Write tests for fast-only behavior
  - [ ] Test: Python edit runs syntax check only (no pylint/mypy/pyright subprocess)
  - [ ] Test: Python edit runs cheap formatting checks (final newline, trailing whitespace, line length)
  - [ ] Test: Markdown edit runs link validation only
  - [ ] Test: Template validation stays (already fast)

- [ ] **F.1.3 GREEN:** Remove subprocess QA from SafeEdit
  - [ ] Update validator classes to skip subprocess calls in "fast" mode
  - [ ] Keep syntax checks (AST parse)
  - [ ] Keep cheap Python formatting checks (line-by-line)
  - [ ] Keep link validation for markdown

- [ ] **F.1.4 REFACTOR:** Quality gates
  - [ ] Tests pass
  - [ ] Pylint 10/10
  - [ ] Confirm no subprocess calls in fast mode (test + manual smoke test)

#### F.2 Exit Criteria

- [ ] SafeEdit for Python: no subprocess calls (syntax + cheap checks only)
- [ ] SafeEdit for Markdown: link validation only
- [ ] All enforcement moved to commit/PR/close choke points

#### F.3 Deliverables

- Updated `mcp_server/tools/safe_edit.py` (if direct), or
- Updated validator classes in `mcp_server/validation/` or `mcp_server/managers/`
- Updated tests

---

### Phase G: Code Quality & Coverage Gates 📊

**Goal:** Enforce code quality metrics and test coverage at commit choke points with configurable thresholds.

**Why this phase:** Non-negotiable quality standards. Maximize maintainability through objective, measurable metrics.

#### G.1 Configuration

**Quality gates configuration via YAML:** `mcp_server/config/quality_gates.yaml`

```yaml
quality_gates:
  # Test Coverage
  coverage:
    line_coverage_min: 90        # % minimum line coverage
    branch_coverage_min: 80      # % minimum branch coverage
    
  # Code Complexity
  complexity:
    cyclomatic_max_warn: 11      # Warning threshold
    cyclomatic_max_block: 16     # Blocking threshold
    
  # Code Size Limits
  size:
    function_length_warn: 51     # Lines per function (warning)
    function_length_block: 76    # Lines per function (blocking)
    class_methods_warn: 11       # Methods per class (warning)
    class_methods_block: 16      # Methods per class (blocking)
    class_length_warn: 201       # Lines per class (warning)
    class_length_block: 301      # Lines per class (blocking)
    module_length_warn: 401      # Lines per module (warning)
    module_length_block: 501     # Lines per module (blocking)
    
  # Code Duplication
  duplication:
    max_percent_warn: 6          # % code duplication (warning)
    max_percent_block: 11        # % code duplication (blocking)
    min_duplicate_lines: 6       # Minimum lines to consider duplicate
    
  # Coupling Metrics
  coupling:
    max_imports_warn: 16         # Import count per module (warning)
    max_imports_block: 21        # Import count per module (blocking)

# Enforcement rules per phase
enforcement:
  green:
    show_warnings: true
    block_on_warnings: false
  refactor:
    show_warnings: true
    block_on_warnings: true       # Warnings become blocking
```

#### G.2 Tasks

- [ ] **G.2.1 RED:** Write tests for code quality metrics
  - [ ] Test: parse pytest-cov JSON output (line + branch coverage)
  - [ ] Test: coverage below threshold → fails gate
  - [ ] Test: coverage above threshold → passes gate
  - [ ] Test: parse radon complexity output
  - [ ] Test: function complexity > blocking threshold → fails gate
  - [ ] Test: function length > blocking threshold → fails gate
  - [ ] Test: class methods > blocking threshold → fails gate
  - [ ] Test: code duplication > blocking threshold → fails gate
  - [ ] Test: import count > blocking threshold → fails gate
  - [ ] Test: warning thresholds → pass with warnings
  - [ ] Test: load thresholds from YAML config
  - [ ] Test: missing config → use sensible defaults

- [ ] **G.2.2 RED:** Write tests for quality gate integration
  - [ ] Test: GREEN commit with warnings → succeeds, logs warnings
  - [ ] Test: REFACTOR commit with warnings → blocks with violations
  - [ ] Test: REFACTOR commit under all thresholds → succeeds
  - [ ] Test: error messages reference specific violations with line numbers

- [ ] **G.2.3 GREEN:** Create quality gates configuration
  - [ ] Create `mcp_server/config/quality_gates.yaml` with default thresholds
  - [ ] Create `mcp_server/config/quality_settings.py` to load YAML
  - [ ] Data class: `QualityGatesConfig` with threshold fields
  - [ ] Method: `load_quality_config() -> QualityGatesConfig`
  - [ ] Validation: all thresholds are positive integers
  - [ ] Validation: blocking thresholds >= warning thresholds

- [ ] **G.2.4 GREEN:** Implement code quality analyzers in `QAManager`
  - [ ] Add dependencies: `radon`, `coverage`
  - [ ] Method: `_check_coverage(files, config) -> dict[str, Any]`
    - Run `pytest --cov --cov-report=json --cov-branch`
    - Parse JSON output
    - Check line coverage % vs `config.coverage.line_coverage_min`
    - Check branch coverage % vs `config.coverage.branch_coverage_min`
    - Return violations + warnings with uncovered line ranges
  - [ ] Method: `_check_complexity(files, config) -> dict[str, Any]`
    - Use `radon.complexity.cc_visit()` to analyze functions
    - Check cyclomatic complexity vs config thresholds
    - Return violations + warnings with function names + complexity scores
  - [ ] Method: `_check_code_size(files, config) -> dict[str, Any]`
    - Parse AST to count function/class/module lines
    - Check against size thresholds
    - Return violations + warnings with entity names + line counts
  - [ ] Method: `_check_duplication(files, config) -> dict[str, Any]`
    - Run `pylint --enable=duplicate-code` with config min lines
    - Parse output for duplication percentage
    - Return violations + warnings with duplicate code locations
  - [ ] Method: `_check_coupling(files, config) -> dict[str, Any]`
    - Parse AST to count imports per module
    - Check against coupling thresholds
    - Return violations + warnings with module names + import counts

- [ ] **G.2.5 GREEN:** Implement unified code quality gate
  - [ ] Method: `run_code_quality_gate(files, phase, config) -> dict[str, Any]`
    - Load thresholds from config based on phase ("green" or "refactor")
    - Run all analyzers: coverage, complexity, size, duplication, coupling
    - Aggregate results into violations (blocking) and warnings
    - Return:
      ```python
      {
          "passed": bool,  # True if no blocking violations
          "violations": list[str],  # Blocking issues (REFACTOR phase)
          "warnings": list[str],    # Advisory issues (GREEN phase)
          "metrics": {
              "coverage": {"line": 92.5, "branch": 85.0},
              "complexity": {"max": 12, "violations": [...]},
              "size": {"max_function": 68, "violations": [...]},
              "duplication": {"percent": 3.2},
              "coupling": {"max_imports": 14}
          },
          "details": str  # Human-readable report
      }
      ```

- [ ] **G.2.6 GREEN:** Wire code quality gate into PolicyEngine
  - [ ] Update `PolicyDecision` data class:
    - Add `warnings: tuple[str, ...] = ()` field for soft issues
  - [ ] Update `PolicyEngine.decide()` for COMMIT operation:
    - GREEN phase: add "code_quality" to required_gates (warnings only)
    - REFACTOR phase: add "code_quality" to required_gates (blocking)
  - [ ] Update error messages:
    - Include specific violation details (function names, line numbers)
    - Reference config file for threshold adjustments
    - Suggest refactoring strategies (extract method, split class)

- [ ] **G.2.7 GREEN:** Wire code quality gate into GitManager
  - [ ] Update `GitManager.commit_tdd_phase()` gate execution:
    - Load quality config
    - Run `qa_manager.run_code_quality_gate(files, phase, config)`
    - If REFACTOR + violations: raise PreflightError with details
    - If GREEN + warnings: log warnings but allow commit
  - [ ] Update commit success message to include quality summary:
    ```
    Commit succeeded!
    Coverage: 92.5% line, 85.0% branch ✅
    Complexity: max 12 (threshold 15) ✅
    Code size: all functions <75 lines ✅
    ```

- [ ] **G.2.8 REFACTOR:** Quality gates + documentation
  - [ ] Pylint 10/10 on new modules
  - [ ] Mypy + Pyright pass
  - [ ] All tests pass
  - [ ] Update AGENT_PROMPT.md with quality gate info
  - [ ] Update CODE_STYLE.md with configurable thresholds reference
  - [ ] Add example: adjusting thresholds for legacy code migration

#### G.3 Exit Criteria

- [ ] Coverage measured at commit choke point (line + branch)
- [ ] Complexity analyzed (cyclomatic complexity per function)
- [ ] Code size checked (function/class/module length)
- [ ] Duplication detected (percentage + locations)
- [ ] Coupling measured (import count per module)
- [ ] All metrics configurable via YAML
- [ ] Warnings shown in GREEN phase (non-blocking)
- [ ] Violations block REFACTOR phase
- [ ] Error messages actionable with specific line numbers
- [ ] Quality summary shown on successful commit

#### G.4 Deliverables

- `mcp_server/config/quality_gates.yaml` (new, configurable thresholds)
- `mcp_server/config/quality_settings.py` (new, config loader)
- Updated `mcp_server/managers/qa_manager.py` (5 new analyzer methods + unified gate)
- Updated `mcp_server/core/policy.py` (code_quality gate in decision matrix)
- Updated `mcp_server/managers/git_manager.py` (wire code quality gate)
- `tests/unit/mcp_server/config/test_quality_settings.py` (new)
- `tests/unit/mcp_server/managers/test_qa_manager_quality.py` (new, ~20 tests)
- Updated `requirements-dev.txt` (add radon, update coverage)
- Updated `docs/coding_standards/CODE_STYLE.md` (reference configurable thresholds)

---

## 4. Testing Strategy

### 4.1 Test Pyramid

| Test Level | Count Target | Focus |
|------------|--------------|-------|
| Unit | 60-80 | Policy decisions, phase transitions, state management, quality metrics, helpers |
| Integration | 25-35 | Tool orchestration, end-to-end lifecycle flows, label auto-sync, quality gate enforcement |
| Smoke | 5-10 | Manual verification of error messages, full lifecycle walkthrough |

### 4.2 Critical Test Scenarios

1. **Full lifecycle progression**
   - Create issue → phase 0 (Discovery)
   - Transition 0→1→2→3 with artifacts → succeeds
   - Transition 1→3 with pass_through → succeeds, logs skip
   - Enter phase 4 (TDD) → sets subphase=red, updates label

2. **TDD sub-phase enforcement**
   - RED commit with test changes → allowed, label → phase:red
   - GREEN commit with failing tests → blocked
   - GREEN commit with passing tests → allowed, label auto-syncs to phase:green
   - REFACTOR commit with failing QA → blocked
   - REFACTOR commit with passing QA → allowed, label → phase:refactor

3. **Protected branch enforcement**
   - Attempt commit to `main` → blocked
   - Attempt commit to `feature/x` → allowed (if gates pass)

4. **MCP tool enforcement**
   - `create_file` for `docs/*.md` → blocked, suggests scaffold_design_doc
   - `create_file` for `backend/*.py` → blocked, suggests scaffold_component
   - `scaffold_component` → succeeds, increments tool usage counter

5. **Artifact enforcement**
   - PR creation from phase 3 → blocked, explains "finish TDD first"
   - PR creation from phase 4.red → blocked, explains "complete REFACTOR"
   - PR creation from phase 4.refactor without docs → blocked, lists missing files
   - PR creation from phase 4.refactor with docs + passing QA → succeeds, transitions to phase 5
   - Issue close from phase 5 → blocked, explains "complete documentation"
   - Issue close from phase 6 with docs → succeeds, updates label to phase:done

6. **Label auto-sync**
   - Commit in RED phase with label mismatch → auto-syncs to phase:red
   - Transition 1→2 → label updates from phase:discussion to phase:design
   - PR creation → label updates to phase:review
   - Issue close → label updates to phase:done

7. **Code quality enforcement**
   - GREEN commit with function complexity 12 → warning logged, commit succeeds
   - REFACTOR commit with function complexity 18 → blocked, suggests extraction
   - REFACTOR commit with 85% coverage → blocked, shows uncovered lines
   - REFACTOR commit with 95% coverage + low complexity → succeeds

8. **Error message quality**
   - All errors reference ST3 tools, not manual commands
   - All errors are actionable (what to do next)
   - All errors include relevant artifact paths or tool names
   - Quality violations include specific line numbers and metrics

---

## 5. Success Metrics

### 5.1 Functional Metrics

- [ ] ✅ Cannot commit to `main` via any ST3 tool
- [ ] ✅ Cannot skip phases without explicit pass_through flag
- [ ] ✅ Cannot commit GREEN with failing tests
- [ ] ✅ Cannot commit REFACTOR with failing QA
- [ ] ✅ Cannot create files without scaffold tools
- [ ] ✅ Cannot create PR unless in phase 4.refactor with artifacts
- [ ] ✅ Cannot close issue unless in phase 6 with docs
- [ ] ✅ Phase state persists across sessions
- [ ] ✅ GitHub labels auto-sync on all phase transitions
- [ ] ✅ Tool usage tracked in `.st3/state.json`
- [ ] ✅ Code quality metrics enforced at REFACTOR choke point
- [ ] ✅ Coverage ≥ 90% line, ≥ 80% branch required
- [ ] ✅ Complexity, size, duplication thresholds enforced
- [ ] ✅ All quality thresholds configurable via YAML

### 5.2 Process Metrics

- [ ] ✅ Zero manual git commands needed for normal workflow
- [ ] ✅ Zero manual file creation needed (scaffold enforced)
- [ ] ✅ Error messages guide to correct tool 100% of time
- [ ] ✅ Same input = same output across all agents
- [ ] ✅ Phase history auditable in `.st3/state.json`
- [ ] ✅ Quality metrics objective and deterministic
- [ ] ✅ Threshold violations provide specific line numbers
- [ ] ✅ Quality config adjustable without code changes

### 5.3 Performance Metrics

- [ ] ✅ SafeEdit remains <500ms for typical edits
- [ ] ✅ Commit choke point <10s for typical changes (without code quality)
- [ ] ✅ REFACTOR commit choke point <30s (includes code quality analysis)
- [ ] ✅ PR creation choke point <15s
- [ ] ✅ Phase transition <5s (includes label sync)
- [ ] ✅ Code quality analysis <20s for typical module (radon + coverage)

---

## 6. Rollout Plan

### 6.1 Feature Flag Strategy

**Phase A:** No flag needed (adding infrastructure + tests, no behavior change)

**Phase B-G:** Enforcement enabled by default (no flag). If critical issues arise, can add emergency disable flag to PolicyEngine.

### 6.2 Rollback Plan

If critical issues arise:
1. Revert enforcement commits (keep infrastructure)
2. Add feature flag to `PolicyEngine.decide` (always return allow=True)
3. Fix issues
4. Re-enable

---

## 7. Decisions & Resolved Questions

### 7.1 Design Decisions (Finalized)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Phase state location** | `.st3/state.json` (gitignored) | Per-branch state, no git conflicts |
| **State scope** | Full lifecycle (0-6) + TDD sub-phases + tool usage + history | Complete audit trail, supports all phases |
| **Label sync strategy** | Auto-sync (Optie C) | Zero friction, deterministic, no agent deviation |
| **MCP tool enforcement** | Blocking (not warnings) | Immediate compliance, template consistency guaranteed |
| **RED enforcement strictness** | Test files must change, tests may fail | Allows TDD "failing test first" |
| **Artifact paths** | `docs/development/issues/<issue_number>/` | Consistent, discoverable |
| **Pass-through mechanism** | Explicit `pass_through=True` flag | Human-in-the-loop control, audit trail |
| **Quality gate thresholds** | Configurable via YAML | Flexibility for legacy code, project-specific standards |
| **Coverage thresholds** | 90% line, 80% branch (configurable) | Industry best practice, Phase G |
| **Complexity threshold** | 16 blocking, 11 warning (configurable) | Based on research, prevents God functions |
| **Function length** | 75 lines blocking, 50 warning (configurable) | SRP enforcement, testability |
| **Code duplication** | 11% blocking, 6% warning (configurable) | DRY principle enforcement |
| **Commit prefix validation** | Strict (test:/feat:/refactor:) | Enforces TDD discipline |

### 7.2 Known Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Phase state git conflicts | Low | Gitignore `.st3/`, reconstruct from commits/labels if needed |
| Test execution timeouts | Low | Bounded timeout (60s), clear error |
| RED "test-only" false positives | Medium | Start permissive, tighten based on usage |
| GitHub API rate limiting | Medium | Cache label state, batch updates where possible |
| Agent confusion on pass-through | Medium | Clear error messages, document in AGENT_PROMPT.md |
| Label sync failures | Medium | Log error but continue (label drift acceptable temporarily) |
| Code quality analysis timeouts | Low | 30s timeout, degrade gracefully (skip analysis, log warning) |
| False positives from quality metrics | Medium | Configurable thresholds, allow override in special cases |
| Legacy code migration | Medium | Adjust YAML thresholds temporarily, document technical debt |

### 7.3 Dependencies

- ✅ **Phase 0 (Bootstrap Tooling)** - Complete (2025-12-23)
  - ProjectManager provides initialization patterns
  - ValidateProjectStructureTool provides validation patterns
  - Structured logging establishes audit trail patterns
  - `.st3/` persistence patterns established
  - Comprehensive testing patterns (72 tests, 10/10 quality)
- Issue #24 (selective staging) not blocking, but improves UX ✅ Merged
- Existing QAManager must remain stable

---

## 8. Phase 0 Integration Summary

**Completed Infrastructure (2025-12-23):**

Phase 0 delivered the foundational tooling that Issue #18 builds upon:

1. **State Persistence Pattern**
   - `.st3/projects.json` established
   - Atomic writes via `.tmp` files
   - JSON serialization with Pydantic models
   - Phase A will extend with `.st3/state.json` using same patterns

2. **Validation Infrastructure**
   - `ValidateProjectStructureTool` provides validation template
   - DependencyGraphValidator for cycle detection
   - ValidationResult/ValidationError DTOs for structured output
   - Phase B will extend for phase transition validation

3. **Structured Logging**
   - Module-level loggers (`logging.getLogger(__name__)`)
   - INFO/DEBUG/ERROR levels for operations
   - Complete GitHub operation audit trail
   - All future phases will follow same logging patterns

4. **Manager Pattern**
   - ProjectManager orchestrates complex operations
   - Adapters handle I/O (GitHubAdapter)
   - Clear separation of concerns
   - Phase A PolicyEngine will follow same orchestration pattern

5. **Comprehensive Testing**
   - 72 tests passing (unit + integration)
   - Dogfood testing with Issue #18 scenario
   - Quality gates at 10/10 pylint
   - All future phases require same test coverage

**Issue #18 Can Now:**
- Use `initialize_project` to create its own milestone + sub-issues
- Validate project structure with `validate_project_structure` tool
- Extend `.st3/` persistence for phase state tracking
- Follow established logging/testing patterns

**Next Steps:**
- Phase A: Implement PhaseStateEngine (extends Phase 0 persistence patterns)
- Phase B: Implement transition_phase tool (uses Phase 0 validation patterns)
- Phase C: Extend GitHubAdapter label sync (builds on Phase 0 logging)
- Existing test runner must remain stable
- GitHub API access required for label updates
- `radon` package for complexity analysis (Phase G)
- `coverage` package for test coverage (Phase G)
- YAML parser for quality config (Phase G)

---

## 8. Progress Tracking

### 8.1 Current Phase
**Phase A: Foundation (Full Lifecycle State Engine + Policy)**

### 8.2 Phase Checklist

- [ ] Phase A: Foundation (Full Lifecycle State Engine + Policy)
- [ ] Phase B: Phase Transition Tool
- [ ] Phase C: Commit Choke Point (TDD Sub-Phases)
- [ ] Phase D: File Creation Enforcement (MCP Tools Only)
- [ ] Phase E: PR + Close Choke Points (Lifecycle Exit Gates)
- [ ] Phase F: SafeEdit Fast-Only Alignment
- [ ] Phase G: Code Quality & Coverage Gates

### 8.3 Commit Strategy

Each sub-phase gets its own commit with proper TDD prefix:
- A.1.1-A.1.2 RED → `test: Add tests for 7-phase state engine + policy`
- A.1.3 GREEN → `feat: Implement PhaseStateEngine with full lifecycle support`
- A.1.4 GREEN → `feat: Implement PolicyEngine with 7-phase + MCP tool validation`
- A.1.5 REFACTOR → `refactor: Quality gates + docs for policy/state`
- B.1.1 RED → `test: Add tests for phase transition tool`
- B.1.2-B.1.3 GREEN → `feat: Implement transition_phase tool with label auto-sync`
- B.1.4 REFACTOR → `refactor: Error messages + quality for phase transitions`
- C.1.1 RED → `test: Add tests for TDD commit choke point enforcement`
- C.1.2-C.1.4 GREEN → `feat: Wire policy enforcement into git_add_or_commit with label sync`
- C.1.5 REFACTOR → `refactor: Improve commit error messages + quality`
- D.1.1 RED → `test: Add tests for file creation enforcement`
- D.1.2-D.1.4 GREEN → `feat: Block manual file creation, enforce scaffold tools`
- D.1.5 REFACTOR → `refactor: File creation error messages + quality`
- E.1.1-E.1.2 RED → `test: Add tests for PR/close artifact enforcement`
- E.1.3-E.1.5 GREEN → `feat: Wire artifact validation into PR/close tools`
- E.1.6 REFACTOR → `refactor: Artifact validation quality`
- F.1.1-F.1.3 GREEN → `feat: Remove subprocess QA from SafeEdit`
- F.1.4 REFACTOR → `refactor: SafeEdit fast-only quality verification`
- G.2.1-G.2.2 RED → `test: Add tests for code quality metrics + integration`
- G.2.3 GREEN → `feat: Add quality gates YAML configuration`
- G.2.4-G.2.5 GREEN → `feat: Implement code quality analyzers + unified gate`
- G.2.6-G.2.7 GREEN → `feat: Wire code quality gate into policy + git manager`
- G.2.8 REFACTOR → `refactor: Code quality gate quality + docs`

---

## 9. Success Criteria Summary

**Issue #18 is complete when:**

1. ✅ All 7 phases (A-G) implemented and tested
2. ✅ All functional metrics met (see 5.1)
3. ✅ All process metrics met (see 5.2)
4. ✅ All performance metrics met (see 5.3)
5. ✅ Full lifecycle smoke test passes (phase 0 → phase 6 → close)
6. ✅ Documentation updated:
   - [AGENT_PROMPT.md](../../../AGENT_PROMPT.md) references new enforcement
   - [PHASE_WORKFLOWS.md](../../mcp_server/PHASE_WORKFLOWS.md) updated with choke points
   - [TOOLS.md](../../mcp_server/TOOLS.md) documents transition_phase tool
7. ✅ This plan doc marked COMPLETE

**Then:**
- Close issue #18 via `close_issue` tool (will validate artifacts exist)
- Merge PR via GitHub
- Update project board

---

## 10. Integration with Existing Documentation

This plan implements enforcement mechanisms for workflows documented in:

- **[AGENT_PROMPT.md](../../../AGENT_PROMPT.md):**
  - Phase 1: Orientation Protocol (st3:// resources)
  - Phase 2: Execution Protocols (scaffold workflows) ← **Enforced by Phase D**
  - Phase 3: Critical Directives (TDD non-negotiable) ← **Enforced by Phase C**
  - Phase 4: Tool Priority Matrix ← **Enforced throughout**

- **[PHASE_WORKFLOWS.md](../../mcp_server/PHASE_WORKFLOWS.md):**
  - 7-phase SDLC model (Phase 0-6) ← **Enforced by Phase A + B**
  - Label transition map ← **Auto-synced by all phases**
  - TDD sub-phase details (RED/GREEN/REFACTOR) ← **Enforced by Phase C**

- **[QUALITY_GATES.md](../../coding_standards/QUALITY_GATES.md):**
  - 5 mandatory quality gates ← **Enforced at REFACTOR commit choke point**

- **[GIT_WORKFLOW.md](../../coding_standards/GIT_WORKFLOW.md):**
  - Feature branch workflow ← **Enforced by protected branch checks**
  - Commit message conventions ← **Enforced by commit prefix validation**

---

**End of Implementation Plan**

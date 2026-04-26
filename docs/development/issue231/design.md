<!-- c:\temp\st3\docs\development\issue231\design.md -->
<!-- template=design version=5827e841 created=2026-04-26T18:44Z updated=2026-04-26 -->
# Workflow State Hardening — WorkflowStatusResolver and Conflict-Safe State Mutation

**Status:** DRAFT  
**Version:** 2.4  
**Last Updated:** 2026-04-26

---

## Purpose

Define the revised design for issue #231 and issue #292 after reopening #292 beyond QA-state isolation, while still avoiding a broad workflow-state redesign.

## Scope

**In Scope:**
Issue #231 read-side unification through one injected read-only `WorkflowStatusResolver` for the user-facing consumers that currently assemble workflow status themselves; issue #292 ownership split for QA baseline state, coordinated workflow-state mutation semantics, and explicit operator-facing conflict feedback plus recovery notes; composition-root wiring and focused test migration for the affected seams.

**Out of Scope:**
Full CQRS redesign; migration of every workflow reader and writer at once; cross-process or distributed coordination beyond the current server process; branch submission atomicity and unrelated epic #290 items; backward-compatibility shims for mixed `quality_gates` data inside `.st3/state.json`; replacing existing engine-centric `PhaseStateEngine.get_state()` callers in `mcp_server/tools/git_tools.py` and `mcp_server/tools/git_pull_tool.py` with the new resolver.

## Prerequisites

Read these first:
1. docs/development/issue231/research.md version 2.1
2. docs/development/issue290/research-issue292-state-mutation-concurrency.md
3. docs/development/issue290/research-issue231-state-snapshot.md
4. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
5. Current branch transitioned to the design phase
---

## 1. Context & Requirements

### 1.1. Problem Statement

The platform currently assembles branch workflow status in multiple user-facing places and still lets multiple mutation paths compete over workflow-related JSON state.

For issue #231, the immediate problem is not that the platform lacks a grand state-snapshot subsystem. The immediate problem is that [mcp_server/managers/project_manager.py](mcp_server/managers/project_manager.py) and [mcp_server/tools/discovery_tools.py](mcp_server/tools/discovery_tools.py) each assemble the effective branch status themselves.

For issue #292, the problem is broader than the earlier minimal slice. The platform must stop [mcp_server/managers/qa_manager.py](mcp_server/managers/qa_manager.py) from persisting QA baseline state into the same file that [mcp_server/managers/state_repository.py](mcp_server/managers/state_repository.py) treats as strict workflow state, and it must also stop successful workflow mutations from silently overwriting unrelated valid changes through blind full-document replacement.

### 1.2. Requirements

**Functional:**
- [ ] Introduce a small immutable `WorkflowStatusDTO` carrying `current_phase`, `sub_phase`, `current_cycle`, `phase_source`, `phase_confidence`, and `phase_detection_error`.
- [ ] Introduce an injected read-only `WorkflowStatusResolver` that is the single status assembler used by `ProjectManager.get_project_plan()` and `GetWorkContextTool`.
- [ ] Keep `ProjectManager` and `GetWorkContextTool` public output fields stable while switching them to the shared resolver.
- [ ] Keep `ProjectManager.get_project_plan()` formatting `current_phase` as `phase:sub_phase` when a sub-phase exists.
- [ ] Keep cycle-detail lookup outside the resolver and outside literal phase-name branching.
- [ ] Introduce a narrow read-only git context seam for current-branch and recent-commit reads used by the resolver and QA manager.
- [ ] Introduce a commit-only phase detection seam for the resolver so it never performs an implicit raw `state.json` read through `ScopeDecoder`.
- [ ] Introduce one shared `BranchValidatedStateReader` adapter so current-branch `IStateReader.load(branch)` usage rejects mismatched `state.branch` instead of leaving the check to each caller.
- [ ] Introduce a dedicated `QualityState` model and `.st3/quality_state.json` file for QA `baseline_sha` and `failed_files` persistence.
- [ ] Remove direct QA baseline persistence into `.st3/state.json` from `QAManager`.
- [ ] Introduce an explicit coordinated workflow-state mutation seam so workflow writes no longer rely on stale load-modify-save windows.
- [ ] Ensure quality-state mutations are also coordinated, not left as ad hoc load-modify-save on the new file.
- [ ] Ensure all workflow writes are inside the coordinated mutation boundary, including implementation-phase hook writes from `on_enter_implementation_phase()` and `on_exit_implementation_phase()`.
- [ ] Emit explicit operator-facing conflict feedback plus a recovery note when workflow or quality-state mutation cannot complete safely.
- [ ] Add `.st3/quality_state.json` to `merge_policy.branch_local_artifacts` so `submit_pr` neutralizes it through existing config-driven behavior.
- [ ] Wire the new resolver, mutation collaborator, git read seam, and QA repository through `mcp_server/server.py` and matching test-support factories.
- [ ] Limit read-side consumer adoption to the researched user-facing paths rather than migrating all workflow readers at once.

**Non-Functional:**
- [ ] Preserve the narrowed issue split from research: #231 stays read-side, #292 owns write integrity and ownership boundaries.
- [ ] Reuse existing persistence infrastructure such as `AtomicJsonWriter` and existing note types such as `RecoveryNote` instead of inventing parallel mechanisms.
- [ ] Keep read-only consumers on read-only interfaces.
- [ ] Keep write coordination explicit and injectable from the composition root.
- [ ] Keep blast radius localized to the researched files and tests.
- [ ] Avoid broad subsystem drift into CQRS services, envelope models, or all-reader migration.

### 1.3. Constraints

- Do not introduce a broad `get_state_snapshot` subsystem in this slice.
- Do not make `WorkflowStatusResolver` depend on `PhaseStateEngine` or any write-capable interface.
- Do not make the resolver pretend to resolve arbitrary branches when the current Git contract is HEAD-based.
- Do not let the resolver invoke `ScopeDecoder` in a way that falls back to raw `.st3/state.json` reads.
- Do not leave `QAManager` with raw JSON access to workflow-owned state such as `parent_branch`.
- Do not remove `workspace_root` from `PhaseStateEngine`; the current engine still owns state-file path derivation and uncommitted-state warnings.
- Do not solve #292 with QA-state isolation alone.
- Do not leave implementation-phase hook saves outside the coordinated mutation boundary.
- Do not treat internal logging as sufficient operator feedback for write conflicts; the tool result and `NoteContext` must both participate.
- All constructor signature changes introduced by this design are breaking. No default fallbacks, optional backwards-compatible parameters, or deprecated constructors are introduced for `PhaseStateEngine`, `QAManager`, `ProjectManager`, or `GetWorkContextTool`. Instantiation outside the composition root must be updated to match the new signatures.
- Do not widen this design into submit_pr atomicity, create_branch hardening, or unrelated epic #290 concerns.

---

## 2. Design Options

### 2.1. Option A — Keep the Earlier Minimal Slice

Keep the earlier design: a read-side resolver for #231 plus a dedicated `QualityStateRepository` for #292, without changing workflow-state mutation semantics.

**Pros:**
- Smallest code change.
- Removes the active QA/workflow schema conflict quickly.
- Keeps #231 and #292 highly localized.

**Cons:**
- No longer matches issue #292 or the revised research.
- Leaves successful workflow mutations able to silently overwrite unrelated valid state changes.
- Would require reopening design again immediately for the remaining write-integrity problem.

### 2.2. Option B — Read-Only Resolver Plus Coordinated State Mutation

Adopt a read-only `WorkflowStatusResolver` for #231, a dedicated QA state file and repository, one explicit coordinated mutation contract for workflow-state writes, and explicit tool feedback plus `RecoveryNote` output on mutation conflicts.

**Pros:**
- Matches the reopened research scope.
- Keeps #231 narrow and read-side only.
- Fixes both halves of #292: ownership split and write integrity.
- Reuses existing server concepts such as `NoteContext`, `RecoveryNote`, `AtomicJsonWriter`, and composition-root injection.

**Cons:**
- Larger than the earlier minimal slice.
- Adds one new git read seam and one new write seam.
- Requires focused updates in transition, cycle, QA, engine, repository, and server-wiring tests.

### 2.3. Option C — Broad CQRS Workflow-State Redesign

Split the subsystem into larger query services, command handlers, shared snapshot envelopes, and wider reader migration.

**Pros:**
- Strong long-term architecture story.
- Could unify more read and write concerns at once.

**Cons:**
- Reopens the broad exploratory CQRS direction that research explicitly demoted to historical context.
- Creates unnecessary blast radius for the current production-hardening goal.
- Solves more than the active issues require.

### 2.4. Chosen — Option B

Option B is the smallest serious design that resolves the reopened problem statements without sliding back into a full subsystem redesign.

---

## 3. Chosen Design

**Decision:** Adopt a two-track design: issue #231 is solved by an injected read-only `WorkflowStatusResolver` returning a small immutable `WorkflowStatusDTO` for `ProjectManager` and `GetWorkContextTool`, while issue #292 is solved by combining QA-state ownership split with coordinated state mutation semantics for workflow and QA writes, plus explicit conflict feedback in tool results and `RecoveryNote` output.

**Rationale:** This design removes the user-facing read ambiguity where it is actually surfaced, restores clean ownership boundaries for QA state, and makes successful state mutation mean something trustworthy again. It stays below the threshold of a broad CQRS redesign because it centralizes only the high-value seams that the reopened research justified.

### 3.1. Design Overview

The approved design has two complementary but separate tracks.

**Issue #231 read path:**
- Add `WorkflowStatusDTO` as a small immutable typed status object.
- Add `WorkflowStatusResolver` as the only component that assembles effective current-branch workflow status for the researched user-facing consumers.
- Add one narrow read-only git context seam and one commit-only phase detection seam so the resolver does not rely on broad mutable collaborators or implicit raw state fallback.
- Enforce one explicit branch-match rule for state reads used by the resolver and QA manager.
- Inject the resolver into `ProjectManager` and `GetWorkContextTool` from the composition root.
- Preserve existing public response shapes.

**Issue #292 write path:**
- Add `QualityState` as a typed QA baseline state model stored separately from workflow state.
- Add `IQualityStateRepository` and `FileQualityStateRepository` for QA baseline persistence.
- Add `IWorkflowStateMutator` and a concrete serialized mutator for coordinated workflow-state writes.
- Reuse one shared per-file mutation runner internally so workflow-state writes and quality-state writes both avoid ad hoc stale load-modify-save behavior.
- Explicitly route implementation-phase hook writes through the same coordinated mutation boundary.
- Inject the mutator and repositories from the composition root.
- Update mutation tools to return explicit conflict errors and emit `RecoveryNote` hints through `NoteContext`.

### 3.2. Issue #231 Read-Only Git and Phase Seams

The resolver should not depend directly on the broad mutable `GitManager`, and it should not depend on a `ScopeDecoder` path that can still read `.st3/state.json` behind its back.

**Git read interface location:**
`mcp_server/core/interfaces/__init__.py`

**Git read contract:**

```python
class IGitContextReader(Protocol):
    def get_current_branch(self) -> str: ...
    def get_recent_commits(self, limit: int = 5) -> list[str]: ...
```

`GitManager` satisfies this interface at the composition root.

**Commit-only phase detector location:**
`mcp_server/core/commit_phase_detector.py`

**Commit-only detector contract:**

```python
class CommitPhaseDetector:
    def detect_from_commit(self, commit_message: str | None) -> PhaseDetectionResult: ...
```

**Commit-only detector rule:**
- The detector wraps `ScopeDecoder.detect_phase(..., fallback_to_state=False)`.
- The resolver never calls `ScopeDecoder` in a way that performs an implicit second state read.
- This keeps `ScopeDecoder` reusable elsewhere without letting the resolver path silently violate its claimed read-only boundary.

### 3.3. Branch-Validated Workflow State Reads

Current-branch reads must not silently accept stale state from a different branch.

**Approved implementation path:**
- Introduce `BranchValidatedStateReader` in `mcp_server/managers/state_repository.py`.
- `BranchValidatedStateReader.load(branch)` delegates to an inner `IStateReader`, then enforces `loaded_state.branch == branch`.
- `BranchValidatedStateReader` raises `StateBranchMismatchError` on mismatch, and `PhaseStateEngine.get_state()` propagates that exception without translation.
- The composition root builds this wrapper once and injects that same instance into `WorkflowStatusResolver`, `QAManager`, and `PhaseStateEngine`.
- `FileStateRepository.load()` remains a raw deserialize-and-validate repository operation; branch-safety is not reimplemented ad hoc at individual call sites.

**Applies to:**
- `WorkflowStatusResolver`
- `QAManager` branch-scope resolution
- `PhaseStateEngine.get_state()` and the existing engine-query callers that stay in scope
- `PhaseStateEngine.get_current_phase()` and the git commit auto-detection path that depends on it

### 3.4. Issue #231 Contract

`WorkflowStatusDTO` is intentionally small. It is not a general workflow snapshot and it is not a replacement for `BranchState`.

**Location:**
`mcp_server/state/workflow_status.py`

**Storage rule:**
- `WorkflowStatusDTO` does not live in `mcp_server/schemas`, because that package is already used for request, config, and render-validation models rather than workflow read models.
- The repo has a strong DTO convention under `backend/dtos`, but there is no established `mcp_server/dtos` package today.
- For this slice the closest existing MCP-side home is `mcp_server/state`, where internal workflow read models and persisted state payloads can live without being mislabeled as schemas.

**Model shape:**

```python
class WorkflowStatusDTO(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    current_phase: str
    sub_phase: str | None = None
    current_cycle: int | None = None
    phase_source: Literal["commit-scope", "state.json", "unknown"]
    phase_confidence: Literal["high", "medium", "unknown"]
    phase_detection_error: str | None = None
```

**Why these fields and not more:**
- `current_phase`, `sub_phase`, `phase_source`, `phase_confidence`, and `phase_detection_error` cover the existing workflow-status fields surfaced by `GetWorkContextTool` and `ProjectManager`.
- `current_cycle` is included as a read-only pass-through from persisted workflow state, not as a phase-specific computed special case.
- No planning or deliverables fields are included. Those remain owned by `ProjectManager` and `GetWorkContextTool`.
- No broad branch metadata or reconstruction payload is included. That would reintroduce the larger snapshot design explicitly kept out of scope.

### 3.5. Issue #231 Resolver

**Location:**
`mcp_server/managers/workflow_status_resolver.py`

**Type:**
Concrete injected read-only service. No resolver Protocol is introduced in this slice.

**Constructor dependencies:**
- `IGitContextReader`
- `IStateReader`
- `CommitPhaseDetector`

**Method contract:**

```python
class WorkflowStatusResolver:
    def resolve_current(self) -> WorkflowStatusDTO: ...
```

**Why current-branch only:**
- The git read seam is intentionally limited to HEAD/current-branch context.
- The researched consumers both need current-branch operator context, not arbitrary branch resolution.
- A `resolve(branch)` signature would over-promise behavior the current Git seam does not support.

**Resolution algorithm:**
1. Resolve the current branch through `IGitContextReader.get_current_branch()`.
2. Load persisted branch state through a branch-validated `IStateReader` path.
3. Read the latest HEAD commit message through `IGitContextReader.get_recent_commits(limit=1)`.
4. Detect workflow phase through `CommitPhaseDetector.detect_from_commit(...)`.
5. Fill `current_cycle` directly from loaded persisted state when present.
6. If commit-derived phase data is unavailable or low-confidence, fall back to persisted workflow state for `current_phase` while preserving explicit `phase_source`, `phase_confidence`, and `phase_detection_error` semantics.
7. Return one immutable `WorkflowStatusDTO`.

**Important design boundaries:**
- `WorkflowStatusResolver` does not depend on `PhaseStateEngine`.
- `WorkflowStatusResolver` does not depend on `GitManager` directly.
- `WorkflowStatusResolver` does not write state, reconstruct state, or emit notes.
- The resolver does not branch on literal phase names such as `implementation`.
- The resolver is responsible only for current-branch workflow status, not planning deliverables, GitHub issue context, or write orchestration.

### 3.6. Issue #231 Consumer Changes

**ProjectManager:**
- Remove local phase-detection assembly from `get_project_plan()`.
- Use `WorkflowStatusResolver.resolve_current()` instead.
- Preserve the current output contract:
  - `current_phase` remains `phase` or `phase:sub_phase`
  - `phase_source` remains a string
  - `phase_detection_error` remains optional text

**GetWorkContextTool:**
- Remove local phase-detection assembly from `execute()`.
- Use `WorkflowStatusResolver.resolve_current()` instead.
- Map DTO fields directly into:
  - `workflow_phase`
  - `sub_phase`
  - `phase_source`
  - `phase_confidence`
  - `phase_error_message`
- Preserve TDD cycle-detail lookup outside the resolver without hardcoded phase-name branching:
  - treat `current_cycle is not None` as the gate for cycle-detail enrichment
  - use existing planning data only when that gate is satisfied
  - do not reintroduce `workflow_phase == "implementation"` in the revised tool path

**Explicit non-adoption boundary:**
- `PhaseStateEngine.get_state()` remains in place as the engine-owned query API.
- The existing direct `get_state()` callers in `mcp_server/tools/git_tools.py` and `mcp_server/tools/git_pull_tool.py`, plus the `get_current_phase()`-based GitCommitTool auto-detection path in `mcp_server/tools/git_tools.py`, remain out of scope for issue #231 resolver adoption, but their `StateBranchMismatchError` handling is in scope for this breaking change.
- Implementors should not refactor those call sites to `WorkflowStatusResolver`; #231 only replaces the duplicated user-facing status assembly in `ProjectManager` and `GetWorkContextTool`.

### 3.7. Issue #292 QA State Contract

`QualityState` is a separate typed persistence model for QA baseline lifecycle state.

**Location:**
`mcp_server/state/quality_state.py`

**Storage rule:**
- `QualityState` lives alongside other MCP runtime state types rather than under `mcp_server/schemas`.
- This keeps persisted QA file payloads separate from request/config/render validation models and aligns the state-oriented types for this slice under one explicit MCP-side home.

**Model shape:**

```python
class QualityState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    baseline_sha: str | None = None
    failed_files: list[str] = Field(default_factory=list)
```

**Repository interface location:**
`mcp_server/core/interfaces/__init__.py`

**Repository contract:**

```python
class IQualityStateRepository(Protocol):
    def load(self) -> QualityState: ...
    def apply(self, mutate: Callable[[QualityState], QualityState]) -> None: ...
```

**File-backed implementation location:**
`mcp_server/managers/quality_state_repository.py`

**Implementation rules:**
- Backing file is `.st3/quality_state.json`.
- The repository reuses `AtomicJsonWriter`.
- `load()` returns `QualityState()` when the file is absent or empty.
- `apply()` executes mutation under the same serialized per-file coordination pattern used for workflow-state mutation, so the design does not merely move the race to a second file.
- The repository persists only the typed QA state payload.

### 3.8. Issue #292 Workflow Mutation Contract

Workflow-state writes need an explicit command seam instead of ad hoc stale load-modify-save windows.

**Interface location:**
`mcp_server/core/interfaces/__init__.py`

**Contract:**

```python
class IWorkflowStateMutator(Protocol):
    def apply(
        self,
        branch: str,
        mutate: Callable[[BranchState], BranchState],
    ) -> None: ...
```

**Concrete implementation location:**
`mcp_server/managers/workflow_state_mutator.py`

**Conflict error contract:**
- Introduce a dedicated `StateMutationConflictError` carrying:
  - a diagnostic message suitable for `ToolResult.error(...)`
  - one recovery message suitable for `RecoveryNote(...)`

**Implementation rules:**
- Acquire a per-state-file in-process lock before reading mutable state.
- Load the freshest workflow state under that lock.
- For command paths that currently reconstruct missing or invalid state, perform reconstruction inside the coordinated mutation flow rather than outside it.
- Invoke the supplied mutation callback against the fresh loaded `BranchState`.
- Validate branch identity and persist through `IStateRepository.save()`.
- Release the lock after persistence completes.
- Raise `StateMutationConflictError` on lock timeout, unrecoverable invalid state, or any mutation condition that would otherwise degrade into silent last-writer-wins behavior.

**Why this is the chosen write mechanism:**
- It fixes the currently observed race within the current server-process model.
- It keeps mutation semantics explicit without redesigning the full repository model.
- It preserves CQS at the seam: `apply(...)` is a command that mutates state and returns no value.

### 3.9. Issue #292 PhaseStateEngine Changes

`PhaseStateEngine` keeps ownership of workflow transition rules and gate orchestration, but it stops owning the unsafe mutation window.

**Constructor dependencies after this design:**
- `workspace_root`
- `ProjectManager`
- `GitConfig`
- `WorkflowConfig`
- `WorkphasesConfig`
- `IStateReader`
- `IWorkflowStateMutator`
- `IWorkflowGateRunner`

**Behavior changes:**
- `get_state()` remains a pure query through the injected branch-validated `IStateReader`, and it propagates `StateBranchMismatchError` without translating it to `FileNotFoundError`.
- `get_current_phase()` remains a thin query wrapper over `get_state()`, so it also propagates `StateBranchMismatchError`.
- `initialize_branch()` uses `IWorkflowStateMutator.apply(...)` instead of directly saving a freshly created state object.
- `transition()`, `force_transition()`, `transition_cycle()`, and `force_cycle_transition()` express their branch updates through `IWorkflowStateMutator.apply(...)`.
- implementation-phase hook writes from `on_enter_implementation_phase()` and `on_exit_implementation_phase()` are explicitly inside the same coordinated mutation boundary; the hooks therefore become pure state-transform helpers or delegate their saves through the mutator rather than calling `_save_state()` directly.
- reconstruction-triggered command saves move behind the same mutator so recovery writes are also coordinated.
- uncommitted-state warnings and state-file path derivation remain inside the engine because they are still workspace-root concerns of the current implementation.
- Existing direct engine-query callers in `mcp_server/tools/git_tools.py` and `mcp_server/tools/git_pull_tool.py` remain on `PhaseStateEngine.get_state()` rather than `WorkflowStatusResolver`, but their exception handling changes in this slice and must catch `StateBranchMismatchError` directly.
- `GitCommitTool` continues to use `PhaseStateEngine.get_current_phase()` for auto-detection rather than the resolver, but it must also catch `StateBranchMismatchError` directly and preserve the existing operator-facing guidance to provide `workflow_phase` explicitly when no usable branch state is available.
- Public method signatures and high-level engine responsibilities remain stable.

### 3.10. Issue #292 QAManager Changes

`QAManager` keeps ownership of QA lifecycle behavior, but it stops owning raw JSON state persistence and raw workflow-state reads.

**Constructor dependencies after this design:**
- `workspace_root`
- `QualityConfig`
- `IQualityStateRepository`
- `IStateReader`
- `IGitContextReader`

**Methods that move away from raw file I/O:**
- `_advance_baseline_on_all_pass()` mutates quality state through `IQualityStateRepository.apply(...)`
- `_accumulate_failed_files_on_failure()` mutates quality state through `IQualityStateRepository.apply(...)`
- `_resolve_auto_scope()` reads from `IQualityStateRepository.load()` instead of `.st3/state.json`
- `_resolve_branch_scope()` resolves the current branch through `IGitContextReader.get_current_branch()` and then reads `parent_branch` through a branch-validated `IStateReader.load(branch)` path instead of raw JSON

**Behavior that stays unchanged:**
- sorting and deduplication of `failed_files` remain in `QAManager`
- branch scope still uses workflow-owned `parent_branch`
- quality-gate execution and compact result rendering remain owned by `QAManager` and `RunQualityGatesTool`

### 3.11. Tool Feedback Contract

The reopened research makes operator-facing conflict behavior a hard requirement.

**Transition and cycle tools:**
- `TransitionPhaseTool`, `ForcePhaseTransitionTool`, `TransitionCycleTool`, and `ForceCycleTransitionTool` stop discarding `NoteContext`.
- On `StateMutationConflictError`, they must:
  - return `ToolResult.error(<explicit diagnostic>)`
  - emit `RecoveryNote(<recovery hint>)` through the provided `NoteContext`
- Existing non-conflict success output remains unchanged.

**Quality tool:**
- `RunQualityGatesTool` keeps its structured result contract for successful runs.
- On quality-state mutation conflict, it must return explicit error output and emit a `RecoveryNote` through `NoteContext`.

**Why this design uses notes:**
- [mcp_server/core/operation_notes.py](mcp_server/core/operation_notes.py) already defines `RecoveryNote` and `NoteContext` as the user-visible coordination path.
- The issue requires explicit explanation plus recovery hinting. Returning only an error string would leave the existing note architecture unused where it is directly relevant.

### 3.12. Composition Root

**`mcp_server/server.py` responsibilities after this design:**
- Build one `ScopeDecoder` for legacy callers that still need its current behavior.
- Build one `CommitPhaseDetector` for the resolver path.
- Build one raw repository-backed state reader and wrap it once in `BranchValidatedStateReader`.
- Build one `WorkflowStatusResolver` from `IGitContextReader`, the shared `BranchValidatedStateReader`, and `CommitPhaseDetector`.
- Inject that resolver into `ProjectManager` and `GetWorkContextTool`.
- Build one `FileQualityStateRepository` pointing at `.st3/quality_state.json`.
- Build one `WorkflowStateMutator` from the workflow state repository and the existing reconstruction collaborator.
- Inject the QA repository plus the shared `BranchValidatedStateReader` and `IGitContextReader` into `QAManager`.
- Inject the workflow mutator plus the shared `BranchValidatedStateReader` into `PhaseStateEngine`.

**Expected wiring shape:**

```python
scope_decoder = ScopeDecoder(workphases_config)
commit_phase_detector = CommitPhaseDetector(scope_decoder=scope_decoder)
branch_validated_state_reader = BranchValidatedStateReader(
    inner=self.state_reader,
)
workflow_status_resolver = WorkflowStatusResolver(
    git_reader=self.git_manager,
    state_reader=branch_validated_state_reader,
    commit_phase_detector=commit_phase_detector,
)
quality_state_repository = FileQualityStateRepository(
    state_file=workspace_root / ".st3" / "quality_state.json",
    writer=AtomicJsonWriter(),
)
workflow_state_mutator = WorkflowStateMutator(
    state_repository=self.state_repository,
    state_reconstructor=self.state_reconstructor,
)
```

### 3.13. Module Layout

```text
mcp_server/
  core/
    interfaces/
      __init__.py                      ← add IGitContextReader, IWorkflowStateMutator, and IQualityStateRepository
    commit_phase_detector.py           ← NEW
  managers/
    state_repository.py                ← MODIFIED (add BranchValidatedStateReader and StateBranchMismatchError)
    workflow_status_resolver.py        ← NEW
    workflow_state_mutator.py          ← NEW
    quality_state_repository.py        ← NEW
    project_manager.py                 ← MODIFIED
    phase_state_engine.py              ← MODIFIED
    qa_manager.py                      ← MODIFIED
  state/
    workflow_status.py                 ← NEW
    quality_state.py                   ← NEW
  tools/
    discovery_tools.py                 ← MODIFIED
    git_tools.py                       ← MODIFIED
    git_pull_tool.py                   ← MODIFIED
    phase_tools.py                     ← MODIFIED
    cycle_tools.py                     ← MODIFIED
    quality_tools.py                   ← MODIFIED
  server.py                            ← MODIFIED
.st3/
  config/
    phase_contracts.yaml               ← MODIFIED (.st3/quality_state.json added)
```

### 3.14. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `WorkflowStatusDTO` lives in `mcp_server/state/workflow_status.py` | `backend/dtos` is the repo's DTO convention, but `mcp_server` has no established `dtos` package and `schemas` is reserved for validation models |
| One shared `BranchValidatedStateReader` is the only approved branch-safe read path | Removes per-implementer freedom and keeps mismatch semantics identical across resolver, QA, and engine queries |
| `WorkflowStatusResolver` depends on `IGitContextReader`, `IStateReader`, and `CommitPhaseDetector` only | Makes the read-only seam real instead of claimed |
| `CommitPhaseDetector` wraps `ScopeDecoder` with `fallback_to_state=False` | Prevents hidden second state reads in the resolver path |
| `resolve_current()` is current-branch only | Matches the actual Git contract instead of over-promising arbitrary branch resolution |
| `current_cycle` is a pass-through field, not a phase-specific special case | Avoids hardcoding phase-name branching in the shared read seam |
| `GetWorkContextTool` gates cycle enrichment on `current_cycle is not None` | Removes the existing hardcoded `implementation` branch from the revised consumer path |
| Existing engine-centric phase queries in `git_tools.py` and `git_pull_tool.py` stay on `PhaseStateEngine.get_state()` or `get_current_phase()` and adopt direct `StateBranchMismatchError` handling where needed | Keeps the resolver adoption boundary explicit while making the clean-break exception contract uniform |
| `QAManager` receives `IGitContextReader` and `IStateReader` for workflow-owned reads | Removes raw JSON access while keeping ownership boundaries clear |
| `QualityState` moves to its own file | Removes the active schema and ownership conflict with workflow state |
| `IWorkflowStateMutator` is introduced | Makes write coordination explicit instead of hiding it inside stale load-modify-save paths |
| Hook-driven implementation-phase saves are explicitly inside the mutator boundary | Closes a real write path that would otherwise remain outside #292 hardening |
| `IQualityStateRepository.apply(...)` is coordinated | Prevents the design from merely moving mutation races from one file to another |
| Conflict paths use `ToolResult.error(...)` plus `RecoveryNote` | Implements the hard operator-facing contract using existing runtime mechanisms |
| The broad CQRS document is not the target architecture | Keeps the reopened design disciplined and aligned with research |

### 3.15. Test Impact Expected by This Design

**Primary test updates:**
- `tests/mcp_server/unit/managers/test_project_manager.py`
- `tests/mcp_server/unit/tools/test_discovery_tools.py`
- `tests/mcp_server/unit/managers/test_baseline_advance.py`
- `tests/mcp_server/unit/managers/test_auto_scope_resolution.py`
- `tests/mcp_server/unit/managers/test_phase_state_engine.py`
- `tests/mcp_server/unit/managers/test_phase_state_engine_c1.py`
- `tests/mcp_server/managers/test_phase_state_engine_async.py`
- `tests/mcp_server/unit/managers/test_state_repository.py`
- `tests/mcp_server/unit/tools/test_transition_phase_tool.py`
- `tests/mcp_server/unit/tools/test_force_phase_transition_tool.py`
- `tests/mcp_server/unit/tools/test_cycle_tools.py`
- `tests/mcp_server/unit/tools/test_cycle_tools_legacy.py`
- `tests/mcp_server/unit/tools/test_git_tools.py`
- `tests/mcp_server/unit/tools/test_git_checkout_state_sync.py`
- `tests/mcp_server/unit/tools/test_git_pull_tool_behavior.py`
- `tests/mcp_server/integration/test_submit_pr_atomic_flow.py`
- `tests/mcp_server/unit/test_server.py`
- `tests/mcp_server/test_support.py`

**Likely low or no direct change:**
- `tests/mcp_server/core/test_phase_detection.py` if `CommitPhaseDetector` simply wraps existing commit parsing without altering `ScopeDecoder` semantics for other callers
- read-path tests outside the selected #231 consumers
- submit_pr implementation tests beyond the configured artifact-set addition

**Factory/test-support expectation:**
- add one workflow-status resolver factory or test double path
- add one git-context-reader fake path
- add one workflow-state mutator fake or test helper path
- add one quality-state repository fake or file-backed test helper path
- add one branch-validated state-reader test helper or explicit repository contract assertion path
- keep the rest of the workflow-state scaffolding intact unless it directly touches the revised seams

---

## Related Documentation
- **[docs/development/issue231/research.md][related-1]**
- **[docs/development/issue290/research-issue292-state-mutation-concurrency.md][related-2]**
- **[docs/development/issue290/research-issue231-state-snapshot.md][related-3]**
- **[mcp_server/core/operation_notes.py][related-4]**
- **[.st3/config/phase_contracts.yaml][related-5]**
- **[mcp_server/managers/project_manager.py][related-6]**
- **[mcp_server/tools/discovery_tools.py][related-7]**
- **[mcp_server/managers/phase_state_engine.py][related-8]**
- **[mcp_server/managers/qa_manager.py][related-9]**
- **[mcp_server/managers/state_repository.py][related-10]**

<!-- Link definitions -->

[related-1]: docs/development/issue231/research.md
[related-2]: docs/development/issue290/research-issue292-state-mutation-concurrency.md
[related-3]: docs/development/issue290/research-issue231-state-snapshot.md
[related-4]: mcp_server/core/operation_notes.py
[related-5]: .st3/config/phase_contracts.yaml
[related-6]: mcp_server/managers/project_manager.py
[related-7]: mcp_server/tools/discovery_tools.py
[related-8]: mcp_server/managers/phase_state_engine.py
[related-9]: mcp_server/managers/qa_manager.py
[related-10]: mcp_server/managers/state_repository.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial approved design for the minimal #231 WorkflowStatusDTO resolver and the minimal #292 QualityStateRepository isolation slice |
| 2.0 | 2026-04-26 | Agent | Reopened design after revised research: kept #231 read-only and narrow, broadened #292 to ownership split plus conflict-safe state mutation and explicit operator feedback |
| 2.1 | 2026-04-26 | Agent | Fixed seam precision after QA review: added a real read-only git seam, commit-only phase detection, explicit QA branch resolution, preserved engine workspace-root needs, and widened the documented test blast radius |
| 2.2 | 2026-04-26 | Agent | Added explicit branch-validation for current-branch reads and made implementation-phase hook writes part of the coordinated mutation boundary |
| 2.3 | 2026-04-26 | Agent | Clarified DTO/state model placement under `mcp_server/state`, replaced branch-validation implementation freedom with one mandated adapter path, and made the out-of-scope `PhaseStateEngine.get_state()` callers explicit |
| 2.4 | 2026-04-26 | Agent | Removed FileNotFoundError translation shim (clean break: StateBranchMismatchError propagates from get_state()), brought git_tools.py and git_pull_tool.py error-handling into scope, and made all constructor-signature changes explicit breaking changes. |

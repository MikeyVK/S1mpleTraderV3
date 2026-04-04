<!-- docs\development\issue257\design_threshold_b_minimal_refactor.md -->
<!-- template=design version=5827e841 created=2026-04-03T19:41Z updated=2026-04-04 -->
# Threshold B Minimal Refactor Design

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-04-04

---

## Purpose

Define the minimum design needed to complete one final Threshold B refactor cycle on issue #257 using the exact current MCP server code status as the starting point.

## Scope

**In Scope:**
PhaseStateEngine transition ownership, branch-state reconstruction ownership, PhaseContractResolver transition usage, DeliverableChecker integration, cycle transition orchestration, tool enforcement scope, and the role of phase_contracts.yaml versus workphases.yaml in the final refactor cycle.

**Out of Scope:**
Detailed implementation sequencing, test-by-test planning, commit strategy, generic effect systems, generalized hook frameworks, and broader config-layer redesign beyond what is needed for the final Threshold B cycle.

## Prerequisites

Read these first:
1. Research baseline on minimal refactor scope completed
2. Threshold B selected as the mandatory branch exit criterion
3. Current MCP server transition, gate, and enforcement paths re-read against the live codebase
---

## 1. Context & Requirements

### 1.1. Problem Statement

The current MCP server has the core components needed for cleaner phase and cycle orchestration, but runtime ownership is still split across old and new paths. `PhaseStateEngine` still owns hardcoded phase gates, `cycle_tools.py` still bypasses orchestration, `PhaseContractResolver.resolve()` is still dead on the transition path, and `get_state()` still violates command-query separation through implicit persistence on reconstruction. The design must make the current system workable and remove `PhaseStateEngine` as a God Class without expanding into unnecessary general-purpose abstraction.

### 1.2. Requirements

**Functional:**
- [ ] Phase and cycle gate evaluation must move onto a single runtime gate path instead of remaining embedded in `PhaseStateEngine` and `cycle_tools.py`
- [ ] `PhaseContractResolver.resolve()` must become authoritative for transition-time gate resolution
- [ ] Concrete gate execution must continue to use the existing `DeliverableChecker` check primitives
- [ ] Cycle transitions must stop writing state through protected `PhaseStateEngine` methods and must stop performing direct deliverable validation in the tool layer
- [ ] The forced transition path must remain explicit bypass plus audit rather than becoming a soft form of enforcement
- [ ] Branch-state reconstruction must leave `PhaseStateEngine` so that transition orchestration and reconstruction no longer change for the same reasons
- [ ] State retrieval must become a pure query with no implicit persistence side effect
- [ ] `state.json` remains git-tracked, but transition-time state persistence is no longer implemented through automatic post-transition commits

**Non-Functional:**
- [ ] Threshold B is mandatory: after refactoring, `PhaseStateEngine` is no longer a God Class
- [ ] The design must comply with SRP, OCP, CQS, DIP, Law of Demeter, and Config-First requirements from `ARCHITECTURE_PRINCIPLES.md`
- [ ] The design must prefer the smallest viable set of new components and avoid introducing generalized effect or hook frameworks
- [ ] The design must preserve explicit runtime behavior and fail-fast configuration semantics
- [ ] The resulting orchestration path must be testable with injected dependencies and without direct filesystem dependence in unit tests

### 1.3. Constraints

- Do not introduce a generalized EffectRunner in this cycle.
- Do not preserve direct tool access to protected state-engine methods.
- Do not leave branch-state reconstruction inside `PhaseStateEngine` if Threshold B is required.
- Do not let enforcement semantics carry post-success state persistence behavior.
- Do not depend on `workphases.yaml` as the long-term gate contract source when `phase_contracts.yaml` already models gate contracts.

---

## 2. Design Options

### Option A — Minimal wiring inside existing owners

Wire `PhaseContractResolver.resolve()` into the current `on_exit_*` logic, keep cycle validation in `cycle_tools.py`, and leave reconstruction in `PhaseStateEngine`.

**Rejected.**
This would activate one dormant component, but it would not satisfy Threshold B. The PSE would still own hardcoded dispatch, cycle tools would still bypass orchestration, and `get_state()` would still violate CQS.

### Option B — Full runner architecture rollout

Introduce a full multi-runner architecture with a generic gate runner, effect runner, hook semantics, and expanded YAML families for all lifecycle behavior.

**Rejected.**
This overreaches the branch goal and violates YAGNI. The current codebase does not need a generalized effect framework to resolve the concrete ownership and CQS problems already identified.

### Option C — Targeted Threshold B decomposition around existing components

Use the components already built, narrow the existing enforcement path, add only the missing gate owner and reconstruction helper, and move cycle transitions onto the same orchestration path as phases.

**Chosen.**
This is the smallest design that makes the current system workable and also clears Threshold B.

---

## 3. Chosen Design

**Decision:** Adopt a targeted Threshold B refactor: narrow `EnforcementRunner` back to tool guards only; introduce one dedicated workflow-gate orchestration component that combines `PhaseContractResolver` and `DeliverableChecker` for both phase and cycle boundaries; move cycle transition orchestration behind the same domain path used for phases; keep recovery orchestration explicitly inside `PhaseStateEngine.transition()`; extract branch-state reconstruction itself out of `PhaseStateEngine`; and remove automatic state-file commits from enforcement without replacing them with a generalized post-transition service. Do not introduce a generic effect system in this branch cycle.

**Rationale:** This design uses the components that already exist, restores clear ownership boundaries, and satisfies the architectural requirement that `PhaseStateEngine` stop being a God Class. It is smaller than a full runner-architecture rollout, but stronger than a one-line wiring fix because it also removes the remaining direct tool-layer bypasses, restores a pure query boundary for `get_state()`, and avoids introducing new infrastructure where explicit orchestration is sufficient.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **A** — `EnforcementRunner` returns to tool guards only | Enforcement remains true enforcement. State-file commits and forced-transition warnings no longer distort its role. |
| **B** — Introduce `WorkflowGateRunner` as the single gate owner and add protocol interfaces | Gate orchestration needs one runtime owner between transition orchestration and raw `CheckSpec` execution, with explicit DI contracts in `core/interfaces/`. |
| **C** — `PhaseContractResolver` remains a query object, but becomes authoritative via `WorkflowGateRunner` | Existing resolver logic is already sufficient for gate resolution; it only lacks a real caller and runtime issue context. |
| **D** — Phase and cycle transitions share one orchestration layer and the PSE if-chain is removed | The cycle path must stop bypassing the transition architecture, and the phase-name dispatch chain must disappear as an OCP consequence. |
| **E** — `StateReconstructor` owns reconstruction; recovery orchestration stays explicit inside `PhaseStateEngine.transition()` | Threshold B requires removing reconstruction responsibility from `PhaseStateEngine`, while CQS requires `get_state()` to become a pure query. |
| **F** — Automatic state-file commits are removed, not replaced | `commit_state_files` leaves `enforcement.yaml`, and normal workflow commits remain the only git persistence mechanism. |
| **G** — `phase_contracts.yaml` becomes the gate contract source; `workphases.yaml` becomes metadata-only for the refactor target | This resolves current overlap and aligns gate logic with the component designed to consume it. |

---

## 4. Detailed Design Decisions

### A — Narrow `EnforcementRunner` to true tool guards

`EnforcementRunner` remains part of the architecture, but its scope becomes strict again.

**Design decision:**
- `enforcement.yaml` continues to model only tool-level guards.
- `check_branch_policy` remains a valid enforcement action.
- `commit_state_files` leaves the enforcement action registry.
- Transition and force-transition tools no longer rely on shared enforcement events for state persistence or warnings.

**Consequences:**
- `server.py` no longer needs `tool.name.startswith("force_")` heuristics.
- This is an explicit named consequence of Decision A, not a side effect discovered later in the refactor.
- `EnforcementRunner` drops dependencies that existed only because of `commit_state_files`.
- Tool enforcement again means "may this tool start?" and not "what else should happen after success?"

### B — Introduce `WorkflowGateRunner` as the runtime gate owner

A dedicated gate owner is the central missing component.

**Responsibilities:**
- accept transition boundary context: workflow name, current phase, cycle number when relevant, issue context, and planning deliverables context
- build a resolver context for the active issue and workflow boundary
- use `PhaseContractResolver.resolve()` to obtain `CheckSpec` instances
- execute resolved checks through `DeliverableChecker`
- provide both blocking and inspection behavior

**Two modes are required:**
- **Enforce mode** for normal phase and cycle transitions: failing checks raise and block the transition
- **Inspect mode** for forced transitions: returns which gates would pass and which would block, without owning the decision to bypass

**Protocol interfaces and DI:**
- `IWorkflowGateRunner` is added to `mcp_server/core/interfaces/__init__.py` as the protocol contract for `WorkflowGateRunner`.
- `IStateReconstructor` is added to `mcp_server/core/interfaces/__init__.py` as the protocol contract for `StateReconstructor`.
- All new components are injected into `PhaseStateEngine` via constructor injection in line with DI rule §11 from `ARCHITECTURE_PRINCIPLES.md`.

This preserves the existing force-transition semantics while moving gate knowledge to the correct owner.

### C — Keep `PhaseContractResolver` pure, but give it per-call issue context

The resolver should not become a stateful manager.

**Design decision:**
- `PhaseContractResolver` remains a pure query object over `PhaseConfigContext`
- `WorkflowGateRunner` constructs the resolver context per evaluation, supplying current planning-deliverables data for the active issue
- `resolve_commit_type()` remains independently usable for the git-commit path

**Rationale:**
This fixes the current dead-path problem without turning the resolver into an orchestration object or a mutable singleton.

### D — Move cycle transitions onto the same orchestration path as phases

The current cycle tools bypass the architecture the phase side is trying to establish.

**Design decision:**
- `cycle_tools.py` becomes thin like `phase_tools.py`
- cycle tools delegate to domain transition orchestration instead of validating directly
- direct `DeliverableChecker` instantiation disappears from `cycle_tools.py`
- direct `state_engine._save_state()` calls disappear from `cycle_tools.py`
- forced cycle transitions use the same gate-inspection path as forced phase transitions
- the hardcoded dispatch-chain in `PhaseStateEngine.transition()` over `planning`, `research`, `design`, `validation`, `documentation`, and `implementation` is removed completely
- the replacement is a single gate call: `workflow_gate_runner.enforce(workflow, from_phase, cycle, issue_context)`

**Design intent:**
`PhaseStateEngine` remains the workflow transition orchestrator for this cycle, even though it now orchestrates both phase and cycle transitions. That is acceptable because both belong to the same domain responsibility: workflow state transition orchestration.

The removal of the phase-name if-chain is the direct OCP consequence of introducing `WorkflowGateRunner`. New gate-carrying workflow boundaries must no longer require modification of `PhaseStateEngine.transition()`.

### E — Split branch-state query, recovery, and reconstruction

Threshold B cannot be satisfied while `PhaseStateEngine` still owns branch-state reconstruction.

**Design decision:**
- Introduce a dedicated `StateReconstructor` component whose only responsibility is to reconstruct `BranchState` from git and project context.
- `PhaseStateEngine` remains the transition orchestrator.
- Recovery orchestration lives explicitly inside `PhaseStateEngine.transition()`; no separate recovery service is introduced.
- `PhaseStateEngine.transition()` calls `IStateRepository.load()` first.
- On load failure, `PhaseStateEngine.transition()` calls `IStateReconstructor.reconstruct()`.
- `PhaseStateEngine.transition()` saves the reconstructed state through `IStateRepository.save()` and then continues with the normal transition flow.
- `PhaseStateEngine.get_state()` becomes a pure query that delegates only to `IStateRepository.load()`.
- If `get_state()` encounters a load failure, it raises an exception and never calls `save()` or reconstruction logic.

**Ownership split after refactor:**
- `IStateRepository` owns persistence
- `IStateReconstructor` owns reconstruction logic
- `PhaseStateEngine.transition()` owns explicit recovery orchestration
- `PhaseStateEngine.get_state()` owns pure query access with no side effects

This satisfies both SRP and CQS.

### F — Remove automatic state-file commits completely

The current system persists `.st3/state.json` through `commit_state_files` enforcement hooks. That behavior is removed completely.

**Design decision:**
- `commit_state_files` is removed from `enforcement.yaml`, including both post-hooks for `transition_phase` and `transition_cycle`.
- No separate transition-state commit service is introduced.
- `state.json` remains git-tracked and is not re-added to `.gitignore`.
- `state.json` is committed through the normal development workflow, not through an automatic mechanism.

**Rationale:**
- Auto-commit without auto-push does not solve cross-machine recovery.
- `IStateReconstructor` makes the belt-and-suspenders role of auto-commit redundant.
- §8 Explicit over Implicit means implicit git history is not a defensible recovery mechanism.
- The rest of the workflow also does not auto-commit, so keeping special auto-commit behavior here would introduce asymmetry without sufficient justification.

### G — Clarify config ownership

The refactor needs an explicit source-of-truth decision.

**Design decision:**
- `workflows.yaml` remains the source of truth for legal phase movement
- `phase_contracts.yaml` becomes the source of truth for phase and cycle gate contracts and commit-type mappings
- `workphases.yaml` remains for phase metadata and subphase whitelist concerns, but not as the long-term gate contract source
- issue-specific hardcoded paths are removed from `phase_contracts.yaml`; gate contracts must be workflow-generic and accept issue context through runtime data

This lets the runtime ask one config family what to check and another config family what movement is legal.

---

## 5. Resulting Runtime Flows

### 5.1 Strict phase transition

1. `TransitionPhaseTool` validates input and delegates to `PhaseStateEngine`.
2. `PhaseStateEngine.transition()` loads current state through `IStateRepository.load()`.
3. If the load fails, `PhaseStateEngine.transition()` invokes `IStateReconstructor.reconstruct()`, saves the reconstructed state through `IStateRepository.save()`, and continues.
4. `WorkflowConfig` validates that the requested phase movement is legal.
5. `IWorkflowGateRunner` enforces exit gates for the current boundary using `PhaseContractResolver` plus `DeliverableChecker`.
6. `PhaseStateEngine` mutates and saves branch state through the repository path.
7. Result is returned to the tool layer.

### 5.2 Forced phase transition

1. `ForcePhaseTransitionTool` validates required human inputs and delegates to `PhaseStateEngine`.
2. `PhaseStateEngine` loads current state for the forced command path.
3. `IWorkflowGateRunner` inspects the relevant gates and returns pass/block information without blocking.
4. `PhaseStateEngine` records the forced transition and audit metadata.
5. The tool returns explicit bypass plus audit information.

### 5.3 Strict cycle transition

1. `TransitionCycleTool` delegates to domain transition orchestration instead of validating inline.
2. The transition orchestrator validates cycle-sequencing invariants.
3. `IWorkflowGateRunner` enforces any cycle-boundary gate contract resolved for the current implementation cycle.
4. State mutation and persistence happen through the normal orchestrated path, not through direct tool access.

### 5.4 Forced cycle transition

1. `ForceCycleTransitionTool` delegates to domain transition orchestration.
2. The transition orchestrator computes skipped-cycle context.
3. `IWorkflowGateRunner` inspects relevant cycle gates and returns pass/block audit information.
4. State mutation and persistence follow the same orchestrated path as other transitions.

---

## 6. Component Responsibility Matrix After Refactor

| Component | Responsibility After Refactor |
|-----------|-------------------------------|
| `EnforcementRunner` | Tool-level blocking guards only |
| `IWorkflowGateRunner` | Protocol contract for runtime gate orchestration in `core/interfaces/` |
| `WorkflowGateRunner` | Runtime gate orchestration for phase and cycle boundaries |
| `PhaseContractResolver` | Pure resolution of commit-type and gate contract data |
| `DeliverableChecker` | Concrete execution of `CheckSpec` primitives |
| `PhaseStateEngine` | Workflow transition orchestration, explicit recovery orchestration in `transition()`, and state mutation |
| `IStateReconstructor` | Protocol contract for reconstruction in `core/interfaces/` |
| `StateReconstructor` | Branch-state reconstruction from external sources |
| `IStateRepository` | Persistence contract for branch state |
| `phase_tools.py` | Thin MCP wrappers for phase transition orchestration |
| `cycle_tools.py` | Thin MCP wrappers for cycle transition orchestration |

---

## 7. Design Boundaries For Planning

This design intentionally leaves the following to planning and implementation, not to design:

- exact method signatures
- file-by-file change ordering
- test case inventory
- commit strategy
- whether helper creation and legacy deletion occur in one patch series or several small patches

The design is complete once the ownership model, component boundaries, and runtime flows are clear enough that planning can turn them into one final Threshold B refactor cycle.

## Related Documentation
- **[docs/development/issue257/research_minimal_refactor_scope.md][related-1]**
- **[docs/development/issue257/research_runner_architecture_baseline.md][related-2]**
- **[docs/development/issue257/research_enforcement_analysis.md][related-3]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/development/issue257/research_minimal_refactor_scope.md
[related-2]: docs/development/issue257/research_runner_architecture_baseline.md
[related-3]: docs/development/issue257/research_enforcement_analysis.md
[related-4]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-04-04 | imp | Applied 5 design decisions from QA dialogue: removed StateRecoveryService, removed TransitionStateCommitter, explicit recovery in PSE.transition(), explicit if-chain removal, protocol interfaces added |
| 1.0 | 2026-04-03 | imp | Initial Threshold B design for the final minimal refactor cycle |

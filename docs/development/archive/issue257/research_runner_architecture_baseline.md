<!-- docs\development\issue257\research_runner_architecture_baseline.md -->
<!-- template=research version=8b7bb3ab created=2026-03-29T18:29Z updated=2026-03-29 -->
# Runner Architecture Baseline

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-29

---

## Purpose

Establish the baseline runner architecture for issue #257 by separating tool guards, phase and cycle gates, and post-success effects, and by inventorying which existing tools and managers should depend on each runner.

## Scope

**In Scope:**
EnforcementRunner, a future PhaseGateRunner, a future EffectRunner, server.py tool dispatch, PhaseStateEngine, phase_tools, cycle_tools, phase_contracts.yaml, enforcement.yaml, deliverables.json, and current effect-like side effects embedded in managers and tools.

**Out of Scope:**
Detailed implementation design, final YAML schemas, test implementation, and migration work at cycle granularity.

## Prerequisites

Read these first:
1. Existing enforcement and phase contract analysis reviewed
2. Current issue257 research and planning documents reviewed
3. Current production wiring in server.py, phase_state_engine.py, phase_tools.py, cycle_tools.py, and enforcement_runner.py inspected
---

## Problem Statement

The current codebase uses the word enforcement for several different kinds of behavior: blocking tool guards, phase and cycle exit gates, post-success side effects, and force-transition warnings. This has led to mixed ownership, duplicated config, and code paths that know too much about tool names or file paths.

## Research Goals

- Separate true enforcement from phase and cycle gates and from post-success effects
- Inventory which existing tools and managers should depend on each runner
- Identify which current responsibilities should remain in core orchestration rather than in runner config
- Establish a stable research baseline for later planning and design work

---

## Background

The current implementation already contains partial building blocks: EnforcementRunner is wired for tool events, PhaseContractResolver exists and resolves phase and cycle checks, and PhaseStateEngine plus cycle tools still contain hardcoded exit checks and direct state persistence. The main problem is not missing concepts but mixed responsibilities and incomplete wiring.

---

## Findings

### 1. Three runner responsibilities are structurally distinct

| Runner | Purpose | Trigger source | Configuration source | Failure model |
|--------|---------|----------------|----------------------|---------------|
| `EnforcementRunner` | Block invalid tool calls before they execute | Tool event | `enforcement.yaml` | Blocking only |
| `PhaseGateRunner` | Evaluate whether a phase or cycle is allowed to complete | Workflow invariant inside orchestration | `phase_contracts.yaml` + issue deliverables | Blocking only |
| `EffectRunner` | Execute configurable post-success side effects | Successful tool or transition event | `effects.yaml` | Non-blocking by default unless explicitly designed otherwise |

The key distinction is semantic, not technical.

- Enforcement answers: "May this tool call start?"
- Phase gating answers: "May this workflow boundary be crossed?"
- Effects answer: "What should happen after success?"

Treating these as one concept causes the current drift where a runner named enforcement also performs git commits and where forced transitions inherit rule behavior intended for strict transitions.

### 2. Not every hook belongs in a runner

The scan confirms that the runner layer is only part of the architecture. The following responsibilities should remain outside runner config.

| Responsibility | Correct owner | Why it is not a runner concern |
|---------------|---------------|--------------------------------|
| Sequential workflow validation | `WorkflowConfig` + `PhaseStateEngine` | This is core domain logic, not a configurable hook |
| Core branch state mutation | `PhaseStateEngine` or a dedicated state-transition service | Updating the canonical state model is part of the domain operation itself |
| Forced transition audit reporting | Force transition path | Audit of skipped gates is informational, not enforcement or effect execution |
| Commit-type resolution | `PhaseContractResolver.resolve_commit_type()` | This is a query service, not a dispatch runner |

This means the runner architecture is complete with three runners, but it does not replace the orchestration layer. The orchestration layer still owns domain state changes and force-transition audit behavior.

### 3. `enforcement.yaml` is only appropriate for tool-level guards

Current `enforcement.yaml` rules mix two concerns.

| Current rule | Real category | Should remain in `enforcement.yaml`? |
|-------------|---------------|--------------------------------------|
| `create_branch` + `check_branch_policy` | Tool guard | Yes |
| `transition_phase` + `commit_state_files` | Post-success effect | No |
| `transition_cycle` + `commit_state_files` | Post-success effect | No |

The `check_branch_policy` rule is a proper enforcement rule because it blocks an invalid tool invocation before the tool executes.

The `commit_state_files` rule is not enforcement. It does not decide whether a tool call is legal. It performs a side effect after success. Its presence in `enforcement.yaml` is the main reason the current runner requires extra dependencies such as `PhaseStateEngine` and `GitManager`, and the main reason the server grew special-case logic for forced tools.

### 4. `phase_contracts.yaml` is the correct source for phase and cycle gates

The earlier scan already showed that `PhaseContractResolver.resolve()` was built for exactly this job.

- It resolves workflow-level exit requirements from `phase_contracts.yaml`.
- It merges cycle-specific checks when `cycle_number` is provided.
- It merges issue-specific recommended checks from deliverables data.
- It already models the difference between immutable required checks and overridable recommended checks.

That makes `phase_contracts.yaml` the correct home for "what must be checked when leaving phase X or cycle Y".

The trigger itself is not config-driven. A phase transition always has to evaluate its gates. Therefore the correct relationship is:

1. The orchestrator reaches a workflow boundary.
2. It always invokes `PhaseGateRunner`.
3. `PhaseGateRunner` asks `PhaseContractResolver` which checks apply.
4. `PhaseGateRunner` executes those checks.

This is why the correct gate source of truth is `phase_contracts.yaml`, not `enforcement.yaml`.

### 5. `workphases.yaml` currently overlaps with phase gating and should be treated as transitional

The code scan confirms three sources currently describe workflow boundary behavior.

| Source | What it currently describes |
|--------|-----------------------------|
| `workflows.yaml` | Which phase transitions are sequentially valid |
| `workphases.yaml` | Exit requirements and entry expectations |
| `phase_contracts.yaml` | Phase and cycle exit contracts, plus commit-type rules |

For runner architecture purposes, `workflows.yaml` and `phase_contracts.yaml` have clear roles.

- `workflows.yaml` describes allowed movement.
- `phase_contracts.yaml` describes checks at boundaries.

`workphases.yaml` currently overlaps with gate semantics already represented elsewhere. That makes it transitional from the perspective of this research. The document does not prescribe immediate deletion, but it does establish that the runner baseline should lean on `phase_contracts.yaml` for gate resolution rather than on ad hoc `workphases.yaml` parsing inside `PhaseStateEngine`.

### 6. Current code inventory by component

#### 6.1 `server.py`

Current role:
- Composition root for managers and tools
- Runs `_run_tool_enforcement()` before and after tool execution
- Contains a `tool.name.startswith("force_")` special case to downgrade post-enforcement failures to warnings

Target role:
- Compose the runner layer
- Invoke `EnforcementRunner` for tool-level pre-call guards
- Optionally invoke `EffectRunner` for tool-level post-success effects if the event is tool-scoped
- Stop owning business semantics about forced tools

Implication:
`server.py` should know that a runner exists, but it should not know that tools whose names start with `force_` need different treatment.

#### 6.2 `EnforcementRunner`

Current role:
- Correctly dispatches tool-level rules from `enforcement.yaml`
- Incorrectly also owns `commit_state_files`
- Depends on `GitManager`, `ProjectManager`, and `PhaseStateEngine`

Target role:
- Execute blocking tool guards only
- Depend only on the collaborators needed by actual guard actions
- Drop dependencies introduced solely by post-success effects

Implication:
Once `commit_state_files` moves out, the current `ProjectManager` dependency is clearly dead, and the `PhaseStateEngine` dependency should disappear entirely from this runner.

#### 6.3 `PhaseContractResolver`

Current role:
- Resolves commit types for `GitCommitTool`
- Resolves phase and cycle checks but is not wired into transition orchestration

Target role:
- Remain a query service
- Feed `PhaseGateRunner` for phase and cycle gate resolution
- Continue feeding commit-type resolution independently

Implication:
The resolver is not itself a runner. It is a dependency of the future `PhaseGateRunner`.

#### 6.4 `PhaseStateEngine`

Current role:
- Validates sequential phase movement
- Mutates branch state
- Implements hardcoded phase enter and exit hooks
- Reads project data and invokes `DeliverableChecker` directly
- Computes skipped gate audit in `force_transition()` directly

Target role:
- Orchestrate transitions
- Always invoke `PhaseGateRunner` at the relevant workflow boundary
- Perform core state mutation itself
- Invoke `EffectRunner` where transition-success effects are part of orchestration
- Stop embedding per-phase gate implementation logic

Implication:
The state engine remains the domain orchestrator. It should delegate guards and effects, not become one of the runners.

#### 6.5 `phase_tools.py`

Current role:
- Thin wrapper around `PhaseStateEngine.transition()` and `force_transition()`
- Exposes `enforcement_event = "transition_phase"` for both strict and forced tools

Target role:
- Remain thin wrappers
- Stop sharing runner semantics that are no longer equivalent
- Let strict and forced paths diverge through the state engine rather than through tool-name heuristics in the server

Implication:
The phase tools should depend on the state engine only. They should not carry hidden enforcement semantics.

#### 6.6 `cycle_tools.py`

Current role:
- Performs validation inline
- Reads planning deliverables directly
- Uses `DeliverableChecker` directly in the forced path
- Calls `state_engine._save_state()` directly
- Exposes `enforcement_event = "transition_cycle"` for both strict and forced tools

Target role:
- Become thin orchestration wrappers like `phase_tools.py`
- Delegate cycle gate evaluation through the same phase and cycle gate path used elsewhere
- Stop calling private state-engine methods
- Stop mixing validation, persistence, audit, and tool I/O in one class

Implication:
`cycle_tools.py` is currently the strongest signal that a shared runner architecture is still missing on the cycle path.

### 7. Inventory of who should depend on each runner

| Component | Should depend on `EnforcementRunner` | Should depend on `PhaseGateRunner` | Should depend on `EffectRunner` | Notes |
|-----------|--------------------------------------|------------------------------------|---------------------------------|-------|
| `server.py` | Yes | No | Possibly for tool-scoped effects | Composition root and tool dispatch |
| `PhaseStateEngine` | No | Yes | Yes | Domain transition orchestrator |
| `PhaseContractResolver` | No | No | No | Dependency of `PhaseGateRunner`, not a runner |
| `DeliverableChecker` | No | No | No | Dependency used by `PhaseGateRunner` |
| `phase_tools.py` | Indirect only via server | Indirect only via PSE | Indirect only via PSE | Should stay thin |
| `cycle_tools.py` | Indirect only via server if tool guards exist | Indirect via transition orchestration | Indirect via transition orchestration | Should stop direct checking and persistence |
| `CreateBranchTool` | Indirect only via server | No | No | Proper tool-guard consumer |
| `TransitionPhaseTool` | Indirect only via server pre-call | Indirect via PSE | Indirect via PSE | Strict path |
| `ForcePhaseTransitionTool` | No special enforcement semantics | Indirect via force-transition audit path if needed | Indirect via PSE if configured | Force path is not soft enforcement |
| `TransitionCycleTool` | Indirect only via server if tool guards exist | Indirect via cycle transition orchestration | Indirect via cycle transition orchestration | Needs central orchestration |
| `ForceCycleTransitionTool` | No special enforcement semantics | Indirect via force-cycle audit path if needed | Indirect via cycle transition orchestration | Current direct deliverable checks should move |

### 8. No fourth runner is required, but one important boundary must be preserved

The scan does not reveal a missing fourth runner. The missing boundary is different:

- Do not force core state mutation into `effects.yaml` just because it happens after success.
- Do not force force-transition warnings into `enforcement.yaml` just because they refer to skipped checks.
- Do not force commit-type resolution into a runner just because it is configuration-driven.

A good rule is:

- If the behavior decides whether an operation may proceed, it is a guard or gate.
- If the behavior executes optional or configurable side effects after success, it is an effect.
- If the behavior updates the canonical domain state needed for correctness, it remains orchestration.
- If the behavior only reports bypassed checks, it remains audit.

### 9. Candidate baseline architecture

The following baseline is consistent with the current codebase and with the research conclusions.

1. `EnforcementRunner` remains the tool-guard runner and uses `enforcement.yaml` only.
2. `PhaseGateRunner` becomes the workflow-boundary gate runner and resolves checks from `phase_contracts.yaml` plus issue deliverables.
3. `EffectRunner` becomes the configurable post-success side-effect runner and uses `effects.yaml`.
4. `PhaseStateEngine` remains the domain orchestrator for phase transitions and delegates to `PhaseGateRunner` and `EffectRunner`.
5. The cycle transition path is refactored so that it uses the same orchestration model instead of embedding checks and state persistence directly in `cycle_tools.py`.
6. Forced transition and forced cycle logic stay separate from enforcement semantics and are modelled as explicit bypass plus audit, not as soft enforcement.

This baseline gives the codebase a structured runner architecture without turning every piece of behavior into a runner concern.

---

## Recommended Baseline

- Keep `enforcement.yaml` narrow: tool guards only.
- Treat `phase_contracts.yaml` as the gate contract source for phase and cycle boundaries.
- Introduce `effects.yaml` only for configurable post-success effects, not for mandatory core state mutation.
- Keep audit of forced transitions out of enforcement semantics.
- Converge both phase and cycle transitions on one orchestration path before adding more hook concepts.

---

## Open Questions

- Should all file-based side effects move to `effects.yaml` while core state mutation stays inside `PhaseStateEngine`?
- Should cycle transitions remain tool-owned or move behind a state-engine method so the same gate and effect orchestration path is reused?
- How aggressively should `workphases.yaml` be reduced once `phase_contracts.yaml` becomes the gate source of truth?
- Should `EffectRunner` be invoked from `server.py`, from `PhaseStateEngine`, or from both depending on whether the effect is tool-scoped or transition-scoped?


## Related Documentation
- **[docs/development/issue257/research_enforcement_analysis.md][related-1]**
- **[docs/development/issue257/research.md][related-2]**
- **[docs/development/issue257/planning.md][related-3]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/development/issue257/research_enforcement_analysis.md
[related-2]: docs/development/issue257/research.md
[related-3]: docs/development/issue257/planning.md
[related-4]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-29 | imp | Initial runner architecture baseline research |

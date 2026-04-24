<!-- docs\development\issue257\research_minimal_refactor_scope.md -->
<!-- template=research version=8b7bb3ab created=2026-04-03T18:47Z updated=2026-04-03 -->
# Minimal Refactor Scope For Issue 257

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-03

---

## Purpose

Capture the minimum viable refactor scope for the current branch based on the exact MCP server code status, so that later design and planning can focus on one final refactor cycle without overreaching.

## Scope

**In Scope:**
Current production wiring for server.py, EnforcementRunner, PhaseContractResolver, PhaseStateEngine, phase_tools.py, cycle_tools.py, enforcement.yaml, phase_contracts.yaml, workphases.yaml, and DeliverableChecker.

**Out of Scope:**
Detailed class design, method signatures, YAML schema redesign, test plan, migration sequencing, and implementation task breakdown.

## Prerequisites

Read these first:
1. Current issue257 research documents reviewed
2. Current runtime wiring in server.py, phase_state_engine.py, phase_tools.py, and cycle_tools.py inspected
3. Current enforcement.yaml, phase_contracts.yaml, and workphases.yaml contents inspected
---

## Problem Statement

The current MCP server already contains the core components needed to reduce PhaseStateEngine ownership, but those components are only partially wired. The open question is not how to generalize the architecture further, but what the minimum code changes are to make the current design workable while staying within the architectural principles.

## Research Goals

- Identify the minimum concrete changes required to make the existing components carry real runtime responsibility
- Separate missing wiring from optional future abstractions
- Establish which parts of the current behavior must remain in orchestration rather than move into new runner layers
- Define expected outcomes that design and planning can treat as success criteria without leaking implementation details

---

## Background

The codebase already has an active EnforcementRunner for tool guards, an active commit-type resolver path for GitCommitTool, an inactive phase and cycle gate resolver path in PhaseContractResolver.resolve(), and a large amount of phase and cycle gate logic still embedded directly in PhaseStateEngine and cycle_tools. This creates a gap between built components and actual runtime ownership.

---

## Findings

### 1. Exact runtime ownership is still split across old and new paths

The current production code shows five distinct ownership facts.

1. Tool-level guard execution is already live.
   `server.py` calls `self.enforcement_runner.run(...)` before and after tool execution when a tool exposes `enforcement_event`.

2. Only one part of the phase-contract design is actually live.
   `PhaseContractResolver.resolve_commit_type()` is wired into the Git commit path, but `PhaseContractResolver.resolve()` is not called from any phase or cycle transition path.

3. Phase gate execution still belongs to `PhaseStateEngine`.
   `PhaseStateEngine.transition()` contains a hardcoded dispatch chain over `planning`, `research`, `design`, `validation`, `documentation`, and `implementation`, and the concrete gate logic still lives in the `on_exit_*` methods.

4. Cycle gate execution still belongs to the tool layer.
   `cycle_tools.py` validates cycle conditions inline, writes branch state through `state_engine._save_state()`, and directly instantiates `DeliverableChecker` in the forced path.

5. Enforcement still carries non-enforcement behavior.
   `commit_state_files` remains registered in `EnforcementRunner` and is triggered from `enforcement.yaml` after phase and cycle transitions, even though it is a post-success side effect rather than a blocking guard.

The practical consequence is that the codebase has already built the core pieces for a cleaner architecture, but the runtime still trusts the old owners for the most important transition behavior.

### 2. The minimum missing pieces are about ownership, not about inventing new abstractions

Based on the current code status, the missing pieces are narrower than a full runner framework.

#### 2.1 Missing gate-execution owner

There is no dedicated runtime owner for phase and cycle gate execution that sits between orchestration and the raw check primitives.

Today:
- `PhaseContractResolver` can resolve gate specs
- `DeliverableChecker` can execute concrete check types
- `PhaseStateEngine` and `cycle_tools.py` still own the actual gate workflow

This is the central missing component. Without this ownership handoff, the newer components remain informative rather than authoritative.

#### 2.2 Missing runtime context for issue-specific checks

`PhaseContractResolver.resolve()` supports issue-specific checks through planning deliverables, but the current resolver instance in `server.py` is created without runtime planning deliverable context. That means the issue-specific branch of the resolver design still lacks the context needed to become authoritative during transitions.

#### 2.3 Missing contract completeness in `phase_contracts.yaml`

The current `phase_contracts.yaml` does not yet cover the active workflow boundaries that the code already enforces, and some paths are still hardcoded to `issue257`. This means the config source intended to become authoritative cannot yet fully replace the embedded logic.

#### 2.4 Missing shared cycle orchestration path

The cycle path is still structurally separate from the phase path.

- Strict cycle transition validates inline in `cycle_tools.py`
- Forced cycle transition validates skipped deliverables inline in `cycle_tools.py`
- Both cycle tools write state directly through a protected state-engine method

As long as that remains true, the phase side can be cleaned up while the cycle side still bypasses the new ownership model.

#### 2.5 Missing boundary cleanup in tool enforcement

The current enforcement path still conflates true blocking guards with post-success side effects. This is the reason the server needs a forced-tool name heuristic and the reason EnforcementRunner still depends on collaborators that exist only for side effects.

#### 2.6 Missing CQS boundary in branch-state access

`PhaseStateEngine.get_state()` is currently not a pure query.

When loading state fails, `get_state()` reconstructs branch state and immediately persists the reconstructed value back through `_save_state()`. That means a read method performs hidden mutation.

This is not only part of the broader God Class problem, but also a direct violation of the architectural CQS rule that query methods must not call save behavior.

### 3. Not everything needs to be solved in the final branch cycle

The current code status does not justify a larger abstraction push.

The following items are not required to make the existing design workable.

- A generic effect runner
- A new `effects.yaml`
- A generic hook framework
- A new check language beyond `CheckSpec` plus `DeliverableChecker`
- Immediate deletion of `workphases.yaml`
- A complete runner architecture rollout across every kind of side effect in the server

The current system already has enough machinery to solve the main architectural drift. What is missing is ownership transfer, config completeness, and removal of direct tool-level bypasses.

### 4. Research conclusion on the minimum viable refactor

If the goal is only to make the current design workable and make the existing components carry real responsibility, the minimum viable refactor is:

- phase and cycle gate evaluation stop being implemented directly in `PhaseStateEngine` and `cycle_tools.py`
- `PhaseContractResolver.resolve()` becomes part of the real runtime path
- concrete checks continue to be executed through the current `DeliverableChecker`
- the tool layer stops calling `_save_state()` and stops directly instantiating `DeliverableChecker`
- enforcement becomes narrow again and stops carrying state-commit behavior as if it were a guard

This is still a substantial refactor, but it is materially smaller than introducing a fully generalized multi-runner framework.

### 5. Research conclusion on the PSE god-class question

There are two thresholds, and they should not be confused.

#### Threshold A: existing components are really used

This threshold is reached when gate execution no longer lives in the old owners and the resolver path is authoritative at runtime.

#### Threshold B: `PhaseStateEngine` is no longer fairly described as a God Class under the architectural principles

This threshold is stricter.

Even after gate logic is removed, `PhaseStateEngine` still contains:
- transition orchestration
- branch-state access and save wrapping
- branch-state reconstruction from git and project state

That means the class may still carry more than one reason to change unless the reconstruction responsibility also leaves the class.

There is also a stricter architectural consequence: as long as reconstruction remains embedded in `get_state()`, the class continues to violate command-query separation because query access still performs persistence as a side effect.

Research conclusion: wiring the gate path is the minimum needed to make the current design work, but wiring alone is not enough if the branch exit criterion is explicitly "PSE is no longer a God Class".

---

## Expected Results

The following expected results are intentionally stated as outcomes, not as implementation instructions.

### Expected results required to make the current design workable

1. Phase and cycle gate evaluation use the newer gate-oriented component path at runtime instead of being implemented directly in `PhaseStateEngine` or `cycle_tools.py`.
2. `PhaseContractResolver.resolve()` is part of the real transition path, not dead architecture.
3. `phase_contracts.yaml` is complete enough for the workflow boundaries that are actually enforced in production and no longer contains issue-specific hardcoded paths for this branch-only case.
4. The tool layer no longer performs direct deliverable validation and no longer writes transition state through protected state-engine methods.
5. Tool enforcement once again means blocking tool guards only, without forced-tool name heuristics and without carrying state-file commit behavior as if it were validation.

### Additional expected result required if the branch exit criterion includes "PSE is no longer a God Class"

6. Branch-state reconstruction no longer lives inside `PhaseStateEngine`; otherwise the class still mixes orchestration with reconstruction responsibility even after gate logic is removed.
7. Branch-state query access is pure again; retrieving state no longer persists reconstructed state as a hidden side effect.

### Expected results explicitly not required for this branch cycle

- No generalized effect system
- No new YAML family for non-essential post-success side effects
- No full redesign of the config layer around hooks
- No attempt to solve every possible future transition or extension point

---

## Open Questions

- How much of `workphases.yaml` should remain authoritative during the final refactor cycle?
- Should cycle transitions be pulled behind `PhaseStateEngine` as part of the same refactor cycle or only wired to shared gate evaluation?
- Should post-transition state-file commits remain explicit orchestration behavior for now or be removed from the current enforcement path in the same cycle?

## Decision Record

- Branch exit criterion for the final refactor cycle on this branch is **Threshold B**: after refactoring, `PhaseStateEngine` is no longer allowed to remain a God Class.
- Design may introduce additional narrowly-scoped helpers if they are required to satisfy Threshold B while staying within the architectural principles.


## Related Documentation
- **[docs/development/issue257/research_enforcement_analysis.md][related-1]**
- **[docs/development/issue257/research_runner_architecture_baseline.md][related-2]**
- **[docs/development/issue257/research.md][related-3]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/development/issue257/research_enforcement_analysis.md
[related-2]: docs/development/issue257/research_runner_architecture_baseline.md
[related-3]: docs/development/issue257/research.md
[related-4]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-04-03 | imp | Added explicit CQS finding for `get_state()` and recorded Threshold B as branch exit criterion |
| 1.0 | 2026-04-03 | imp | Initial research document for minimum viable refactor scope and expected results |

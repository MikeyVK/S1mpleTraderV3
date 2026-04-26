<!-- c:\temp\st3\docs\development\issue290\research-issue293-cycle-boundary-semantics.md -->
<!-- template=research version=8b7bb3ab created=2026-04-26T12:50Z updated=2026-04-26 -->
# Research — Issue #293 Cycle Boundary Semantics

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-04-26

---

## Purpose

Document the root cause, viable solution directions, architectural fit, findings, and expected results for issue #293 within epic #290.

## Scope

**In Scope:**
Cycle transition semantics, gate resolution behavior for cycle-based phases, and the distinction between phase-exit gates and cycle-exit gates.

**Out of Scope:**
State persistence concurrency, read-side snapshot unification, and submit_pr/create_branch atomicity.

## Prerequisites

Read these first:
1. Issue #290 epic context
2. Issue #293 description
3. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
4. Current implementations of PhaseContractResolver, WorkflowGateRunner, PhaseStateEngine, and cycle transition tools

---

## Problem Statement

Internal cycle transitions currently resolve both phase exit requirements and cycle-specific exit requirements for the active implementation phase. This conflates two distinct workflow boundaries and allows phase-exit gates to block ordinary cycle-to-cycle movement.

## Research Goals

- Identify the absolute core problem behind issue #293 instead of treating it as a generic gate misconfiguration.
- Map the code path from cycle tools through WorkflowGateRunner into PhaseContractResolver.
- Evaluate solution directions against docs/coding_standards/ARCHITECTURE_PRINCIPLES.md.
- Define expected results that planning and design can implement without mixing boundary semantics with persistence fixes.

---

## Background

The platform already models cycle-based phases explicitly through phase_contracts.yaml with cycle_based, subphases, commit_type_map, exit_requires, and cycle_exit_requires. However, the current resolver API receives only workflow_name, phase, and optional cycle_number, and uses that to resolve a combined check set for both phase exits and cycle exits.

That means the system currently infers boundary intent indirectly from the presence of `cycle_number`, rather than from an explicit statement of which workflow boundary is being crossed.

---

## Findings

### Finding 1 — The core defect is semantic overloading in the resolver contract

Issue #293 is not primarily a bad config problem. The deeper issue is that `PhaseContractResolver.resolve()` is answering two different questions through one implicit API:

- What checks are required to leave this phase?
- What checks are required to move between cycles inside this phase?

Those are different workflow boundaries. The current API does not model that distinction directly.

### Finding 2 — The live code path proves internal cycle hops inherit phase-exit gates

The current path is straightforward:

1. cycle tool calls `PhaseStateEngine.transition_cycle()` or `force_cycle_transition()`
2. the engine calls `WorkflowGateRunner.enforce()` or `inspect()` with `phase=current_phase` and `cycle_number=current_cycle`
3. `WorkflowGateRunner` delegates to `PhaseContractResolver.resolve()`
4. `PhaseContractResolver.resolve()` always starts with `phase_contract.exit_requires`
5. if `cycle_number` is present, it appends `phase_contract.cycle_exit_requires[cycle_number]`

That means an internal cycle hop does not request cycle-boundary checks only. It requests phase-exit checks plus cycle-exit checks.

### Finding 3 — The bug is active in the real repository configuration, not only in fixtures

The live `refactor` workflow marks `implementation` as `cycle_based: true` and also defines an `exit_requires` gate: `implementation-test-suite`.

That means the current resolver behavior can block ordinary implementation cycle transitions on a gate that semantically belongs to leaving implementation for validation, not to moving from one implementation cycle to the next.

### Finding 4 — The existing unit tests currently encode the conflated behavior as correct

The resolver tests explicitly expect a cycle-numbered resolution for implementation to include both:

- the phase-level required gate
- the cycle-level required gate

This means the current bug is partly protected by tests. Fixing #293 will require changing tests that currently bless the mixed-boundary result.

### Finding 5 — The intended semantics are boundary-based, not field-based

A normal `transition()` from implementation to validation crosses a phase boundary and should enforce phase-exit requirements.

A `transition_cycle()` or `force_cycle_transition()` call stays inside implementation and should enforce cycle-boundary requirements only.

The current implementation loses this distinction because it treats `cycle_number is not None` as "phase checks plus extra cycle checks" rather than as "this is a cycle-boundary resolution".

---

## Architecture Check

### Alignment with Explicit over Implicit

This is the strongest architectural violation in #293. Boundary type is currently implicit in call shape instead of explicit in the resolver contract. The system hides a critical semantic distinction behind the presence of `cycle_number`, which is too indirect for such an important rule.

### Alignment with SRP and Cohesion

A resolver method that simultaneously models phase exit and cycle exit is handling two related but distinct responsibilities. Separating those questions would improve cohesion and make the resulting behavior easier to reason about and test.

### Alignment with OCP

An explicit boundary contract is more extensible than hardwiring mixed behavior into one method. If the platform later adds entry checks, merge checks, or other boundary types, a boundary-aware API scales better than more implicit branching inside one resolver path.

### Alignment with YAGNI

The smallest compliant fix is not a larger workflow engine rewrite. The smallest compliant fix is one explicit distinction between phase-boundary resolution and cycle-boundary resolution.

---

## Solution Directions

### Direction A — Split boundary resolution explicitly

Introduce explicit resolution paths for different boundary types. Two obvious options are:

- separate methods such as `resolve_phase_exit(...)` and `resolve_cycle_exit(...)`
- one method with an explicit boundary parameter such as `boundary="phase_exit" | "cycle_exit"`

Either direction is better than the current overloaded meaning of `cycle_number`.

### Direction B — Make cycle transitions request cycle-boundary checks only

`transition_cycle()` and `force_cycle_transition()` should ask for cycle-boundary enforcement only. They should not inherit the active phase's normal `exit_requires` set.

### Direction C — Keep phase transitions responsible for phase-exit checks only

Normal phase transitions out of implementation should continue to enforce the implementation phase's `exit_requires`. That keeps the meaning of `implementation-test-suite` and similar gates attached to leaving the phase, not moving inside it.

### Direction D — Update tests and documentation to match boundary semantics

The resolver tests and any integration tests that currently expect combined phase-plus-cycle resolution must be updated. Otherwise #293 will appear fixed in production code but still fail against stale behavioral assertions.

---

## Expected Results

This research supports the following expected outcomes for issue #293:

- The platform has an explicit distinction between phase-boundary checks and cycle-boundary checks.
- `transition_cycle` and `force_cycle_transition` no longer evaluate ordinary phase exit requirements during internal cycle hops.
- Ordinary phase transitions out of implementation still evaluate implementation phase exit requirements.
- Tests no longer encode mixed phase-plus-cycle resolution as the expected behavior for cycle transitions.
- The resolver API communicates boundary intent directly instead of hiding it behind `cycle_number` presence.

## Open Questions

- Should the distinction be modeled as separate resolver methods or as one method with an explicit boundary enum/string?
- Should issue-specific cycle deliverables continue to merge only into cycle-boundary resolution, or is any cross-boundary reuse intended?
- Are there any other consumers besides cycle transitions that currently rely on the accidental combined behavior?

## Related Documentation

- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[.st3/config/phase_contracts.yaml][related-2]**
- **[mcp_server/managers/phase_contract_resolver.py][related-3]**
- **[mcp_server/managers/workflow_gate_runner.py][related-4]**
- **[mcp_server/managers/phase_state_engine.py][related-5]**
- **[mcp_server/tools/cycle_tools.py][related-6]**
- **[tests/mcp_server/unit/managers/test_phase_contract_resolver.py][related-7]**
- **[tests/mcp_server/unit/managers/test_phase_state_engine_c4_issue257.py][related-8]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: .st3/config/phase_contracts.yaml
[related-3]: mcp_server/managers/phase_contract_resolver.py
[related-4]: mcp_server/managers/workflow_gate_runner.py
[related-5]: mcp_server/managers/phase_state_engine.py
[related-6]: mcp_server/tools/cycle_tools.py
[related-7]: tests/mcp_server/unit/managers/test_phase_contract_resolver.py
[related-8]: tests/mcp_server/unit/managers/test_phase_state_engine_c4_issue257.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial scaffolded draft |
| 1.1 | 2026-04-26 | Agent | Added root-cause analysis, architecture check, solution directions, and expected results for issue #293 |

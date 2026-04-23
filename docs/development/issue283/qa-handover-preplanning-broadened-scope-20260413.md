# QA Handover — Pre-Planning Review for Broadened Scope (Issue #283)

**From:** QA (@qa)
**To:** Implementer (@imp)
**Date:** 2026-04-13
**Branch:** `refactor/283-ready-phase-enforcement`
**Primary design file:** `docs/development/issue283/design-git-add-commit-regression-fix.md` (DRAFT v9.0)
**Related docs:** `docs/development/issue283/research-git-add-or-commit-regression.md` (DRAFT v1.5), `docs/development/issue283/design-ready-phase-enforcement.md` (FINAL v2.0)
**Verdict:** NO-GO for planning as-is. Broadened scope is accepted as an explicit product decision, but the design still needs tighter invariants, sharper boundary policy, cleaner SRP ownership, and clearer document authority before planning can start safely.

---

## Executive Summary

This handover reflects a clarified QA position after discussion with the user.

The objection is **not** that issue #283 has become too broad. The broadened scope is accepted intentionally because the user sees strategic value in resolving the regression and adjacent contract debt in one coherent pass.

The design is still blocked because several core parts are not yet specified precisely enough for a broadened refactor:

1. The merge-safety invariant is currently modeled with the wrong proxy.
2. The path-boundary policy is not yet stated consistently across research, design, and guardrails.
3. The central new abstraction (`NoteContext`) still needs a sharper SRP story.
4. The note/exception migration is conceptually clear, but parts of the design text still contradict that contract.
5. The current runtime has mixed exception/result patterns that the broadened refactor must explicitly normalize or consciously leave alone.
6. The document set still has conflicting sources of truth.

### Accepted User Decisions (binding for next design revision)

- **Scope broadening is intentional.** QA should review for correctness and architecture fitness, not argue for minimizing scope by default.
- **Absolute end goal:** the state of excluded branch-local artifacts on a child branch must never change the state of the parent branch at merge time.
  - `main` must remain free of these tracked workflow artifacts.
  - Epic or other parent branches may have their own tracked workflow artifacts, and child branches must not overwrite or alter that parent state through merge.
- **Path-boundary policy preference:** the user strongly prefers **no hardcoded paths in production or test code for any purpose**. If any exception is proposed, it must be justified explicitly and convincingly.

---

## Finding 1 — Merge Invariant Is Still Specified via the Wrong Proxy

### QA Position

The design currently specifies the `create_pr` gate using a **history-touch** proxy instead of the true merge-safety invariant.

Current design section:

- `git log merge_base..HEAD -- path` in `design-git-add-commit-regression-fix.md` §3.9

That proxy answers:

- "Did any commit on this branch touch this path?"

But the actual accepted product goal is:

- "Would merging this child branch change the parent branch state for this artifact path?"

Those are not the same question.

### Why This Matters

For this issue, the accepted end state is branch-state preservation at merge:

- On `main`, these artifacts must remain absent.
- On epic-parent branches, their own tracked artifact state must remain intact and unmodified by child branches.

A child branch can legitimately touch an artifact path during its own history and still end with **zero net delta** against the parent branch. In that case, the merge is safe and should not be blocked.

### Evidence

QA validated this in a temporary git repository outside production code:

1. Create branch from `main`
2. Commit `.st3/state.json`
3. Remove `.st3/state.json` in a later commit
4. Inspect:
   - `git log merge_base..HEAD -- .st3/state.json` -> non-empty
   - `git diff --name-only merge_base..HEAD -- .st3/state.json` -> empty
   - merge into `main` -> `.st3/state.json` absent in merged tree

Observed result:

- **History touch detected**
- **No net delta remained**
- **Merge result stayed clean**

So the current design would falsely block a clean branch and force unnecessary history rewriting.

### Required Correction

The design must be revised to express and check the correct invariant:

- **A child branch must not produce a net merge-result state change for branch-local artifact paths on the chosen parent branch.**

The gate must therefore use a proxy aligned with merge-result delta, not historical touch alone.

### Impact on Planning

Do not plan implementation cycles from the current §3.9 as written. Its central behavioral contract is wrong for the explicitly accepted end goal.

---

## Finding 2 — Path-Boundary Policy Must Be Made Explicit and Then Applied Consistently

### QA Position

The user's stated policy preference is stricter than the current research baseline:

- **No hardcoded paths in production code**
- **No hardcoded paths in test code**
- Preferably no exceptions at all

That policy is defensible, but it is **not yet expressed consistently** across the current document set.

### Current Misalignment

The research document still allows display-only `.st3/config/...` constants as legitimate:

- `research-git-add-or-commit-regression.md` says display-only config-path strings are acceptable

The design document then introduces a structural test that bans any `.st3/config/` string literal in production code.

So the problem is no longer "the design is too strict".

The problem is:

- research, design, and guardrails do **not yet describe the same policy**

### Why This Matters

If the strict no-raw-path policy is truly intended, then the design must state that clearly and consistently.

That affects more than YAML-open callsites. It also affects:

- display-path constants in errors
- source-path strings in user-visible notes
- structural tests
- test fixtures and assertions that currently embed raw paths

Under the user's preferred boundary, those are not automatically exempt.

### Required Correction

The next design revision must choose one policy explicitly:

1. **Absolute policy:** no raw path literals anywhere in production or tests
2. **Scoped boundary policy:** no runtime rediscovery/opening of config paths after composition root, with narrowly documented display-only exceptions

Given the user's stated preference, QA recommends designing against option 1 unless a concrete exception is required and defended.

### Impact on Planning

Planning must not assume the current structural guard is correct merely because it is stricter. First align the policy, then define the guardrail.

---

## Finding 3 — The Broadened Design Still Needs a Sharper SRP Story Around `NoteContext`

### QA Position

With scope broadening accepted, the key architectural concern is no longer "this is too broad".

The concern is:

- **Does the new central abstraction pass SRP and cohesion?**

The current design gives `NoteContext` three distinct responsibilities:

1. Store produced notes
2. Expose typed query access (`of_type()`)
3. Render user-facing response content (`render_to_response()`)

### Why This Matters

That is a potential SRP and cohesion problem under `ARCHITECTURE_PRINCIPLES.md`:

- one reason to change should map to one class responsibility
- methods should belong to the domain that owns the knowledge they use

Today the design does not yet explain convincingly why these three concerns belong in one runtime component.

### Clarified QA Meaning

This finding is **not** a recommendation to shrink scope automatically.

It is a requirement that the broadened runtime contract be designed cleanly enough to satisfy architecture law.

### Required Correction

The next design revision must do one of the following explicitly:

1. **Defend the single-component design against SRP**
   - define the single reason to change for `NoteContext`
   - explain why storage, query, and rendering are one cohesive runtime concern

2. **Split responsibilities more sharply**
   - for example into note collection vs. rendering vs. querying, if that is what the architecture truly demands

### Impact on Planning

Do not plan implementation from the assumption that `NoteContext` is automatically architecturally sound just because it is symmetric and convenient.

---

## Finding 4 — The Removal of `blockers=` / `recovery=` Is Conceptually Clear, but the Design Text Is Not Yet Fully Consistent

### QA Position

The user is correct that lines 122 and 123 in the design are conceptually clear:

- the old exception constructor constraints are removed
- raise sites become explicitly responsible for producing `BlockerNote` and `RecoveryNote`

That core rule is not the problem.

### Actual QA Concern

The inconsistency is elsewhere in the same design document: later code examples still use the removed legacy pattern in some snippets.

So the issue is not that the constraint statement is unclear.

The issue is:

- the design still contains examples that contradict the constraint statement

### Required Correction

Normalize the document so that all snippets, examples, and structural tests reinforce the same contract:

- no `blockers=` constructor usage after the flag-day
- no `recovery=` constructor usage after the flag-day
- all recovery/blocker guidance comes from explicit note production at raise site

### Impact on Planning

Planning may proceed only once the design document itself is internally consistent on this migration rule.

---

## Finding 5 — Exception-Flow Normalization Must Be Explicit in the Broadened Runtime Contract

### QA Position

The design reasons primarily from the decorator-centered exception path, but the current tool layer is not uniform.

Today the codebase includes mixed patterns:

- decorator-based exception translation
- tools that catch exceptions themselves and return `ToolResult.error(...)` directly

This matters because the broadened notes contract assumes a more uniform flow than the current runtime actually provides.

### Why This Matters

If the refactor introduces a new cross-cutting notes protocol, then the design must explicitly decide whether these mixed tool patterns are also in scope.

Without that decision, the implementation risks ending up in a half-migrated state where:

- some flows can participate in the new note contract
- other flows bypass it or degrade it

### Required Correction

The next design revision must say explicitly:

1. Whether self-catching tools are part of the migration scope
2. Whether those tools must be normalized to the same exception/result model
3. Which flows are guaranteed to participate in the new notes contract by the end of issue #283

### Impact on Planning

Do not plan the `NoteContext` migration as if the current tool layer were already uniform. It is not.

---

## Finding 6 — Document Authority Must Be Repaired Before Planning

### QA Position

The issue-283 document set still contains conflicting authority signals.

The old ready-phase design remains `FINAL`, while the new regression-fix design is `DRAFT` and deliberately contradicts the old enforcement-only boundary.

### Why This Matters

The old `FINAL` design still states that tool `execute()` methods are not modified.

The new broadened design requires broader contract changes, including tool execution signatures and response flow.

If both remain active without explicit supersession, implementer, planner, and QA can each end up following a different source of truth.

That is a planning risk, not a cosmetic documentation issue.

### Required Correction

Before planning starts, the document set must state clearly which artifact is authoritative.

Recommended minimum:

- mark the old ready-phase design as superseded for the new broadened initiative
- state explicitly that the new issue-283 direction is both bug-fix and platform-contract refactor
- ensure planning references only the chosen authoritative design set

### Impact on Planning

No planning should begin from mixed-authority inputs.

---

## Recommended Handover to @imp

Treat the next revision as a design-clarification pass, not as immediate implementation planning.

### Priority Order

1. Define the correct merge invariant in terms of parent-branch state preservation.
2. Lock the path-boundary policy as an explicit law across research, design, tests, and runtime.
3. Rework or explicitly defend `NoteContext` against SRP concerns.
4. Make the blocker/recovery migration internally consistent everywhere in the document.
5. State the intended exception-flow normalization scope.
6. Repair document authority before planning cycles are written.

### Practical Implication

The broadened scope can be valid and valuable, but only if the next design revision becomes more exact than the current one. The blockers are now about **precision and architectural coherence**, not about breadth itself.

<!-- c:\temp\st3\docs\development\issue290\research-issue295-submit-pr-atomicity.md -->
<!-- template=research version=8b7bb3ab created=2026-04-26T12:52Z updated=2026-04-26 -->
# Research — Issue #295 SubmitPR Atomicity

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-04-26

---

## Purpose

Document the root cause, viable solution directions, architectural fit, findings, and expected results for issue #295 within epic #290.

## Scope

**In Scope:**
SubmitPRTool execution ordering, preflight coverage, rollback expectations, and operator-facing behavior when submission fails after local mutation.

**Out of Scope:**
Branch creation hardening, read-side workflow intelligence, and state persistence concurrency.

## Prerequisites

Read these first:
1. Issue #290 epic context
2. Issue #295 description
3. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
4. Current implementations of SubmitPRTool, GitManager.push, and GitAdapter.push

---

## Problem Statement

SubmitPRTool claims an atomic branch-submission flow but performs local branch mutations before transport prerequisites and PR creation are guaranteed to succeed. In the upstream-missing case this leaves the branch partially mutated even though the tool returns an error.

## Research Goals

- Identify the absolute core problem behind issue #295 instead of treating it as a simple missing-upstream bug.
- Map the submit_pr execution path and the failure boundary between local mutation and remote publication.
- Evaluate solution directions against docs/coding_standards/ARCHITECTURE_PRINCIPLES.md.
- Define expected results that planning and design can implement without depending on issue #297 to paper over submit_pr's own contract breach.

---

## Background

The intended flow of SubmitPRTool is neutralize branch-local artifacts, commit ready-state changes, push, create the PR, and then record PRStatus.OPEN. The current implementation performs the first local mutation steps before verifying that the current branch can actually be pushed successfully.

The push path also shows why the upstream-missing case is significant: SubmitPRTool calls `GitManager.push()` with the default `set_upstream=False`, and the push path does not perform a submit-pr-specific preflight that guarantees the branch is publishable before local mutations begin.

---

## Findings

### Finding 1 — The core defect is transactional ordering, not merely missing upstream configuration

Issue #295 should not be treated as a narrow usability bug around upstream tracking. The deeper defect is that SubmitPRTool mutates local branch state before verifying that later steps in the same claimed atomic flow can succeed.

That means upstream absence is only one trigger. Any later failure after neutralize or commit can produce the same contract breach.

### Finding 2 — The current flow mutates locally before the first transport risk is checked

The execution order is currently:

1. detect branch-local artifacts with net diff
2. neutralize them to base
3. commit with ready-phase scope
4. push
5. create PR
6. record PRStatus.OPEN

The first transport-dependent step is push, but by that point the branch tip may already have been changed by neutralization and commit creation. This is exactly the wrong side of the boundary for an operation that presents itself as atomic.

### Finding 3 — SubmitPRTool has no rollback path for post-mutation failures

When push or PR creation fails, SubmitPRTool emits a RecoveryNote warning that the branch tip may have been modified. That is useful as a warning, but it is also an admission that the tool has already broken its own atomicity claim.

There is currently no compensating action that restores the branch to its pre-submit state when failure occurs after local mutation.

### Finding 4 — The current tests verify sequence and note production, but not transactional recovery

The integration tests for submit_pr assert the intended happy-path order and they assert that partial failures produce a RecoveryNote.

They do not assert either of the stronger atomicity guarantees that matter most:

- preflight rejection before local mutation when prerequisites are missing
- rollback to the original branch tip when a later step fails after mutation

That means the current test suite documents the intended sequence, but not the transactional safety contract the tool description implies.

### Finding 5 — Issue #297 is a companion, not a substitute

Hardening `create_branch` to establish upstream tracking earlier will reduce the chance of the specific upstream-missing failure mode.

It does not eliminate #295. SubmitPRTool still needs its own fail-fast or rollback protection because create_branch cannot guarantee that every later submit failure mode disappears.

---

## Architecture Check

### Alignment with Fail-Fast

The current implementation violates fail-fast. A missing upstream or other push-blocking condition is detectable before local mutation, but the tool discovers it only after local state has already changed.

### Alignment with Explicit over Implicit

Atomicity should not be implicit marketing language. If a tool calls itself atomic, either the whole sequence completes or the user is left in the same local state as before. Returning an error plus a note that the branch tip may have changed is explicit diagnostics, but it is not explicit atomic behavior.

### Alignment with CQS and Command Integrity

A branch-mutating command should have a clear success contract. The current behavior blurs that contract: command failure does not imply state preservation, and command success is not the only condition under which the branch may be changed.

### Alignment with YAGNI

The smallest compliant fix is not a general transaction framework across all git tools. The smallest compliant fix is to protect SubmitPRTool's own command boundary with preflight and, if still needed, a narrow rollback path.

---

## Solution Directions

### Direction A — Add submit-pr-specific preflight before any local mutation

Before neutralizing artifacts or creating a ready commit, SubmitPRTool should verify the prerequisites required for the rest of the flow. At minimum this includes:

- origin remote exists
- current branch is publishable
- upstream exists or the tool has an explicit strategy to create it

This is the simplest path to restoring fail-fast behavior.

### Direction B — If preflight is incomplete, add rollback for post-mutation failures

If any local mutation still must occur before all remaining failure modes are excluded, SubmitPRTool should capture the original branch tip and restore it on failure before PR creation completes.

The important design point is not the exact git mechanism. The important point is that a failed submit_pr must not strand the branch in a partially submitted state.

### Direction C — Treat auto-upstream as optional mitigation, not the full fix

SubmitPRTool may choose to auto-publish or set upstream when absent. That is a valid mitigation, but it should not replace explicit preflight reasoning or rollback guarantees. Otherwise the tool remains brittle when other later steps fail.

### Direction D — Strengthen tests around the actual atomicity contract

The test suite should prove at least one of these strong guarantees:

- missing prerequisites block before neutralize/commit
- or post-mutation failures restore the original branch tip

Without that, future regressions will reintroduce the same class of partial-submit failure.

---

## Expected Results

This research supports the following expected outcomes for issue #295:

- SubmitPRTool no longer mutates the local branch before known publish/transport prerequisites are checked.
- A failed submit_pr call cannot leave the branch in a partially submitted local state.
- RecoveryNote remains a diagnostic aid, but it is no longer the primary protection against partial mutation.
- Tests verify fail-fast preflight or verified rollback semantics rather than only sequence and note production.
- Issue #297 can remain a complementary branch-creation hardening measure without being the only protection against submit_pr partial failure.

## Open Questions

- Is preflight alone sufficient for current real-world failure modes, or do we still need rollback after neutralize/commit for later PR-creation failures?
- If rollback is added, what is the narrowest safe restore target: original HEAD only, or a more structured neutralization transaction state?
- Should submit_pr gain an explicit capability to set upstream itself when safe, or should that remain purely a create-branch responsibility?

## Related Documentation

- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[docs/mcp_server/architectural_diagrams/04_enforcement_layer.md][related-2]**
- **[mcp_server/tools/pr_tools.py][related-3]**
- **[mcp_server/managers/git_manager.py][related-4]**
- **[mcp_server/adapters/git_adapter.py][related-5]**
- **[tests/mcp_server/integration/test_submit_pr_atomic_flow.py][related-6]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: docs/mcp_server/architectural_diagrams/04_enforcement_layer.md
[related-3]: mcp_server/tools/pr_tools.py
[related-4]: mcp_server/managers/git_manager.py
[related-5]: mcp_server/adapters/git_adapter.py
[related-6]: tests/mcp_server/integration/test_submit_pr_atomic_flow.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial scaffolded draft |
| 1.1 | 2026-04-26 | Agent | Added transactional root-cause analysis, solution directions, and expected results for issue #295 |

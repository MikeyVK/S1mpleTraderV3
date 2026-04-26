<!-- c:\temp\st3\docs\development\issue290\research-issue297-create-branch-upstream-hardening.md -->
<!-- template=research version=8b7bb3ab created=2026-04-26T12:53Z updated=2026-04-26 -->
# Research — Issue #297 CreateBranch Upstream Hardening

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-04-26

---

## Purpose

Document the root cause, viable solution directions, architectural fit, findings, and expected results for issue #297 within epic #290.

## Scope

**In Scope:**
CreateBranch tool/manager/adapter behavior, upstream publication expectations, rollback semantics for failed branch setup, and the boundary between branch creation and later workflow commands.

**Out of Scope:**
SubmitPRTool rollback semantics, read-side workflow intelligence, and state persistence concurrency.

## Prerequisites

Read these first:
1. Issue #290 epic context
2. Issue #297 description
3. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
4. Current implementations of CreateBranchTool, GitManager.create_branch, GitAdapter.create_branch, and push(set_upstream=True) support

---

## Problem Statement

CreateBranch currently succeeds after local branch creation and checkout only. It does not establish upstream tracking or publish the branch to origin, so later workflow steps discover that missing prerequisite only after more work has been performed.

## Research Goals

- Identify the absolute core problem behind issue #297 instead of treating it as a cosmetic workflow convenience.
- Map the current create_branch responsibilities across tool, manager, and adapter layers.
- Evaluate solution directions against docs/coding_standards/ARCHITECTURE_PRINCIPLES.md.
- Define expected results that planning and design can implement without conflating branch-creation invariants with submit_pr recovery semantics.

---

## Background

The current stack already supports pushing with set_upstream=True as a separate operation. However, create_branch itself only validates naming, checks for a clean working tree, creates the local branch, and checks it out. The workflow therefore treats upstream publication as an optional later step rather than a branch-creation invariant.

---

## Findings

### Finding 1 — The core defect is that create_branch stops too early for the intended workflow contract

Issue #297 is not just about convenience. It is about what success from `create_branch` is supposed to mean in this workflow.

Today success means only:

- branch name/type validated
- working tree was clean
- local branch created
- local branch checked out

For a workflow that later depends on remote publication and upstream tracking, that is an incomplete success contract.

### Finding 2 — The current stack already has the pieces for upstream publication, but not inside the create_branch command boundary

The platform already supports `push(set_upstream=True)` as a separate operation. That means the missing capability is not technical impossibility. The missing capability is command composition.

The system currently spreads one logical workflow action across two commands:

1. create local branch
2. later remember to publish and set upstream

That gap is exactly what allowed the missing-upstream prerequisite to survive far enough to hurt later commands.

### Finding 3 — Current tests and tool behavior encode local-only success as sufficient

The existing create-branch tests verify parameter passing, branch naming, and success messaging for local branch creation. They do not assert remote publication, upstream tracking, or rollback behavior.

That means the current behavior is not only implemented this way; it is also the currently tested contract.

### Finding 4 — If create_branch is hardened, it must become all-or-nothing

A hardened create_branch cannot simply add a remote push step and still return partial success on failure. If remote publication fails after local creation/checkout, the tool would otherwise create a new half-initialized branch state of its own.

That means a hardened create_branch needs both:

- preflight for remote publishability where possible
- rollback to the previous branch plus deletion of the new local branch if publication fails after creation

### Finding 5 — Issue #297 is preventative and complements #295, but does not replace it

Hardening create_branch is the earliest sensible place to enforce the upstream invariant. That makes it a high-leverage preventative fix.

It is still not a replacement for #295. Later commands like submit_pr must remain robust even if the branch setup invariant was missed historically or if another publish-related failure occurs later.

---

## Architecture Check

### Alignment with Fail-Fast

The current create_branch behavior allows a missing remote-tracking prerequisite to survive into later workflow steps. That is the opposite of fail-fast. If upstream is part of the branch-ready contract, it should be established or rejected at branch creation time.

### Alignment with Explicit over Implicit

The tool result should match the real state of the branch. Returning success for a branch that is only locally created but not remotely usable is an implicit, weaker contract than the workflow appears to expect.

### Alignment with CQS and Command Integrity

A branch-creation command should have a crisp postcondition. If the intended postcondition is "workflow-usable branch", the command must either produce that state fully or fail without residue. Partial success is not a good command contract here.

### Alignment with YAGNI

The smallest compliant hardening is not a large new orchestration system. The smallest compliant hardening is to extend the existing create_branch flow with explicit publish/upstream semantics and rollback on failure.

---

## Solution Directions

### Direction A — Make create_branch establish upstream as part of success

The strongest workflow-aligned option is for create_branch to:

1. create the local branch
2. publish it to origin
3. set upstream tracking
4. return success only after all four steps complete

That gives the command a useful invariant: branch creation success means later remote-dependent commands start from a sound baseline.

### Direction B — Add rollback if publish fails after local creation

If the branch is created and checked out locally but remote publication fails, the command should:

- return to the original branch
- remove the newly created local branch
- surface a clear failure explaining that upstream setup did not complete

Without rollback, the hardening attempt would simply move the partial-failure problem earlier.

### Direction C — Add publishability preflight where feasible

Before creating or switching branches, the command can reduce failure risk by checking conditions such as:

- origin remote exists
- current repository state is suitable for pushing
- the target branch name does not already exist remotely in a conflicting way

Preflight will not catch every failure mode, but it should eliminate the obvious ones before mutation begins.

### Direction D — Update tests to encode the new branch-ready contract

Any hardening must be captured in tests. The current local-only success tests should be expanded so the new contract is explicit and regression-resistant.

---

## Expected Results

This research supports the following expected outcomes for issue #297:

- A successful create_branch call leaves the branch locally created, published, and upstream-tracked.
- A failed create_branch call does not strand the user on a half-initialized local branch.
- Missing remote/upstream prerequisites are detected as early as possible.
- Tests verify remote publication/upstream behavior and rollback semantics, not just local branch creation.
- The create_branch command becomes the earliest enforcement point for the upstream invariant, while later commands remain independently robust.

## Open Questions

- Should upstream publication be mandatory for all branch types, or only for the workflow-executed types used by MCP tooling?
- Is rollback safe in every failure mode once the branch has been created locally, or are there cases where a more conservative recovery strategy is needed?
- Should remote branch-name collision be handled as a preflight validation or delegated to the push failure path?

## Related Documentation

- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[mcp_server/managers/git_manager.py][related-2]**
- **[mcp_server/adapters/git_adapter.py][related-3]**
- **[tests/mcp_server/unit/tools/test_git_tools.py][related-4]**
- **[tests/mcp_server/unit/managers/test_git_manager.py][related-5]**
- **[tests/mcp_server/unit/adapters/test_git_adapter.py][related-6]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: mcp_server/managers/git_manager.py
[related-3]: mcp_server/adapters/git_adapter.py
[related-4]: tests/mcp_server/unit/tools/test_git_tools.py
[related-5]: tests/mcp_server/unit/managers/test_git_manager.py
[related-6]: tests/mcp_server/unit/adapters/test_git_adapter.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | Agent | Initial scaffolded draft |
| 1.1 | 2026-04-26 | Agent | Added invariant-focused root-cause analysis, solution directions, and expected results for issue #297 |

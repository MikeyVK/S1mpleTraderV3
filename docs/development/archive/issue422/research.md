<!-- docs\development\issue422\research.md -->
<!-- template=research version=8b7bb3ab created=2026-07-08T18:46Z updated= -->
# Dirty worktree defect in git_add_or_commit

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-07-08

---

## Purpose

Resolve the dirty worktree regression in git_add_or_commit while adhering to ARCHITECTURE_PRINCIPLES.md.

## Scope

**In Scope:**
GitCommitTool execution flow, GitAdapter commit behavior, state.json update sequence, and regression test suites.

**Out of Scope:**
GitHub PR submission flow, project plan transitions, and general Git commands in the terminal.

## Prerequisites

Read these first:
1. Issue #422 description
2. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
3. docs/coding_standards/DOCUMENTATION_STANDARD.md
---

## Problem Statement

The commit tool (git_add_or_commit) writes phase and commit metadata to .pgmcp/state.json after creating the Git commit. This leaves the workspace dirty (modified: .pgmcp/state.json), requiring manual commits or workarounds to restore a clean worktree.

## Research Goals

- Investigate the root cause of the dirty worktree issue in git_add_or_commit
- Identify affected code paths, boundaries, and test suites
- Establish architectural constraints and a clean, compliant fix strategy
- Define expected results and verification baseline

---

## Background

The regression was introduced in commit 242e4143f5a313276949abefdd9d6be9005963d8 (Issue #298) on May 5, 2026. That commit placed the record_sub_phase() call after the Git commit transaction. Mocked unit tests failed to catch the resulting dirty working tree on disk.

---

## Findings

The root cause is the order of operations in GitCommitTool.execute() (state.json updated after commit) combined with the lack of staging state.json when committing a specific files list. To fix this cleanly: 1) Update state.json first with a rollback handler if the commit fails. 2) In GitCommitTool.execute(), if a specific files list is provided, explicitly append the relative path of state.json to the list. GitAdapter remains generic and unaware of state.json to prevent domain leakage.

---

## Approved Strategy

No special migration policy required. The fix will be fully backwards-compatible and local to GitCommitTool.execute(), preserving the generic interface of GitAdapter.

---

## Expected Results

A clean working tree is maintained after every git_add_or_commit invocation (both with and without a specific files list). All tests pass. rollback_push and PR submission remain unaffected.

## Related Documentation
- **[Commit 242e4143f5a313276949abefdd9d6be9005963d8][related-1]**

<!-- Link definitions -->

[related-1]: Commit 242e4143f5a313276949abefdd9d6be9005963d8

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-08 | Agent | Initial draft |
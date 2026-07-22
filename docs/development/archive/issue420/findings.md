<!-- docs\development\issue420\findings.md -->
<!-- template=generic_doc version=43c84181 created=2026-07-08T05:54Z updated= -->
# Findings: git_add_or_commit state.json Synchronization Defect

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-07-08

---

## Purpose

Document architectural findings and defects regarding the git_add_or_commit tool and state.json synchronization.

---

## Summary

Analysis of the out-of-sync behavior between the Git commit tool and the workspace phase state file.





---

## Observations

During the implementation of Issue #420, we observed that running `git_add_or_commit` leaves `.pgmcp/state.json` in a modified state in the Git worktree.

Specifically, when a cycle is transitioned, `state.json` resets `current_sub_phase` to `null`. When `git_add_or_commit` is executed, it stages and commits all modified files (including the updated `state.json`), but then immediately performs a post-commit write to `state.json` to record the sub-phase.

This results in a cycle where:
1. `git_add_or_commit` stages and commits files.
2. `git_add_or_commit` writes to `state.json` *after* the Git commit is created.
3. The worktree is left with a modified `state.json` immediately after a successful commit.

## Analysis & Architectural Defects

There are two fundamental issues identified with this behavior:

### A. Phase State Registration Responsibility
It is highly questionable that a Git commit tool (`git_add_or_commit`) has the responsibility to perform state mutations (`record_sub_phase`) in `state.json`. Under a clean Separation of Concerns (SoC) model, Git tools should only interact with Git repository operations, while state engine modifications should be handled exclusively by dedicated lifecycle/state mutator components.

### B. Execution Ordering Defect
If the Git commit tool is required to record the sub-phase in `state.json`, the execution order is logically incorrect. The write operation to `state.json` must happen *before* the staging and committing operations. By writing to the file *after* committing, the commit itself is rendered incomplete as it does not capture the final state written by the tool, leaving the worktree dirty.

## Proposed Recommendations

To resolve this defect, the codebase should implement one of the following strategies in a future issue:
1. **Remove State Modification from Git Tool**: Refactor `git_add_or_commit` so it does not call `record_sub_phase` on the state engine. State transitions should be initiated by the runner or implementer before the commit is made.
2. **Re-order Tool Operations**: If the git tool must manage the state, re-order the operations within `git_add_or_commit.execute()` so that `state_engine.record_sub_phase()` is called prior to `git commit`.

## Related Documentation
- **[docs/development/issue420/research.md][related-1]**
- **[docs/development/issue420/design.md][related-2]**

<!-- Link definitions -->

[related-1]: docs/development/issue420/research.md
[related-2]: docs/development/issue420/design.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-08 | Agent | Initial draft |
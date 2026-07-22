<!-- docs\development\issue422\pr.md -->
<!-- template=pr version=93bb9b4e created=2026-07-08T19:22Z updated= -->
# Fix dirty worktree defect in git_add_or_commit

Resolves the dirty worktree defect in git_add_or_commit where .pgmcp/state.json was left modified after successful commits. Adheres to all ARCHITECTURE_PRINCIPLES.md (zero domain leakage, SSOT, CQS).
## Changes
Reordered record_sub_phase to execute before commit_with_scope in GitCommitTool.execute(). Implemented a transactional rollback handler to restore the subphase on Git commit failure. Dynamically resolved state.json relative path using the repository root and state engine paths to prevent hardcoding. Explicitly appended the resolved relative path of state.json to the targeted files list during explicit file commits.

## Testing
Executed the full test suite (2879 passed). Quality gates overall PASS on the branch. Added unit tests for order of operations and rollback handler correctness.
## Checklist

- [ ] Unit tests pass
- [ ] Quality gates pass
- [ ] Working tree remains clean after git_add_or_commit execution

## ⚠️ Breaking Changes

None
## Deferred Work

None
## Related Documentation
- **[docs/development/issue422/validation.md][related-1]**

---

Closes: #422
<!-- docs\development\issue422\planning.md -->
<!-- template=planning version=130ac5ea created=2026-07-08T18:57Z updated= -->
# Planning for fixing dirty worktree defect in git_add_or_commit

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-07-08

---

## Purpose

Sequential cycle plan to implement the bug fix for the dirty worktree defect.

## Scope

**In Scope:**
Cycles definition, exit criteria, TDD test definitions, regression strategy, quality-gate rules, and planning-deliverables payload.

**Out of Scope:**
Actual code changes, pipeline builds, and PR review.

## Prerequisites

Read these first:
1. Issue #422 description
2. docs/development/issue422/design.md
3. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
4. docs/coding_standards/DOCUMENTATION_STANDARD.md
5. docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md
---

## Summary

Sequential TDD cycle plan to fix the dirty worktree defect in git_add_or_commit. The plan is divided into two cycles: Cycle 1 focuses on transaction rollback and mutation order, and Cycle 2 focuses on dynamic state.json path resolution and staging.

---

## TDD Cycles


### Cycle 1: Cycle 1: Mutation Order and Rollback

**Goal:** Correct the order of operations in GitCommitTool.execute() and implement a rollback mechanism to restore the subphase on commit failure.

**Tests:**
- test_git_commit_tool_calls_record_sub_phase_before_commit in tests/mcp_server/unit/tools/test_git_tools.py
- test_git_commit_tool_rolls_back_sub_phase_on_commit_failure in tests/mcp_server/unit/tools/test_git_tools.py

**Success Criteria:**
- record_sub_phase() is called before commit_with_scope() during execute()
- If commit_with_scope() raises an exception, record_sub_phase() is called with the original subphase value to restore it, and the exception is re-raised



### Cycle 2: Cycle 2: Dynamic Staging and SSOT Compliance

**Goal:** Dynamically resolve the relative path of state.json relative to the repository root, and explicitly append it to the files list if specific files are targeted.

**Tests:**
- test_git_commit_tool_appends_state_json_to_files_list in tests/mcp_server/unit/tools/test_git_tools.py
- Update existing mock tests in test_git_tools.py to accommodate the appended state.json file in commit assertions

**Success Criteria:**
- state.json path is resolved dynamically relative to self.manager.adapter.repo_path
- If params.files is not None, the relative path of state.json is appended to the list before calling commit_with_scope()
- All unit and integration tests pass successfully

**Dependencies:** Cycle 1: Mutation Order and Rollback

---

## Risks & Mitigation

- **Risk:** Existing unit tests mock commit_with_scope and assert exact call arguments. Appending state.json to files will break these assertions.
  - **Mitigation:** Cycle 2 planning includes updating these test assertions as a core deliverable.

---

## Milestones

- Cycle 1 complete: Transactional order and rollback verified
- Cycle 2 complete: Workspace remains clean after explicit file commits

## Related Documentation
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[docs/development/issue422/design.md][related-2]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: docs/development/issue422/design.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-08 | Agent | Initial draft |
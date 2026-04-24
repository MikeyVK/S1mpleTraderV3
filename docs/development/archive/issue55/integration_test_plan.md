# Issue #55 Integration Test Plan

**Date:** 2026-01-15
**Phase:** Integration
**Branch:** refactor/55-git-yaml

---

## Test Strategy

### Approach
1. Create custom `.st3/git.yaml` with non-standard values
2. Restart MCP server to load new config
3. Execute E2E smoke tests for all 11 conventions via MCP tools
4. Verify custom config is used (not defaults)
5. Restore original config and cleanup

### Custom Test Config

```yaml
# .st3/git.yaml.test - Custom values for integration testing
branch_types:
  - epic        # Keep from default
  - hotfix      # NEW: Not in default
  - experiment  # NEW: Not in default

tdd_phases:
  - test        # Renamed from "red"
  - impl        # Renamed from "green"
  - refactor    # Keep from default

commit_prefix_map:
  test: test       # Maps test→test
  impl: feat       # Maps impl→feat
  refactor: refactor

protected_branches:
  - main
  - staging      # NEW: Not in default

branch_name_pattern: "^[a-z0-9_-]+$"  # Allow underscores (not in default)

default_base_branch: develop  # Changed from "main"
```

---

## Convention Tests

### Convention #1: Branch Types (GitManager)
**Test:** Create branch with "hotfix" type
**Tool:** `create_branch`
**Expected:** ✅ Success (hotfix allowed in custom config)
**Verify:** Branch created: `hotfix/99-integration-test`

### Convention #2: TDD Phases (GitManager)
**Test:** Commit with "impl" phase
**Tool:** `git_add_or_commit`
**Expected:** ✅ Success (impl allowed, maps to "feat:")
**Verify:** Commit message starts with "feat:"

### Convention #3: Commit Prefix Map (GitManager)
**Test:** Verify "impl" → "feat:" mapping
**Tool:** `git_add_or_commit`
**Expected:** ✅ Commit message = "feat: integration test"
**Verify:** Check git log

### Convention #4: Protected Branches (GitManager)
**Test:** Try to delete "staging" branch
**Tool:** `git_delete_branch`
**Expected:** ❌ Error (staging protected in custom config)
**Verify:** Error message mentions "staging"

### Convention #5: Branch Name Pattern (GitManager)
**Test:** Create branch with underscore: "hotfix/99-integration_test"
**Tool:** `create_branch`
**Expected:** ✅ Success (underscores allowed in custom config)
**Verify:** Branch created with underscore

### Convention #6: TDD Commit Prefixes (PolicyEngine)
**Test:** Commit with "feat:" prefix
**Tool:** `git_add_or_commit` (via PolicyEngine validation)
**Expected:** ✅ Allowed (feat: derived from commit_prefix_map)
**Verify:** PolicyEngine accepts message

### Convention #7: Branch Type Regex (git_tools)
**Test:** Create branch with "experiment" type
**Tool:** `create_branch` (uses CreateBranchInput validator)
**Expected:** ✅ Success (experiment in custom branch_types)
**Verify:** Branch created: `experiment/99-test`

### Convention #8: Phase Regex (git_tools)
**Test:** Commit with "test" phase
**Tool:** `git_add_or_commit` (uses GitCommitInput validator)
**Expected:** ✅ Success (test in custom tdd_phases)
**Verify:** Commit created with "test:" prefix

### Convention #9-11: Default Base Branch (pr_tools)
**Test:** Create PR without specifying base
**Tool:** `create_pr` (with base omitted)
**Expected:** ✅ PR targets "develop" (custom default_base_branch)
**Verify:** PR base = "develop"

---

## Test Execution Plan

### Phase 1: Setup
1. ✅ Backup original `.st3/git.yaml`
2. ✅ Create custom `.st3/git.yaml` with test values
3. ✅ Restart MCP server (load new config)
4. ✅ Verify server restarted successfully

### Phase 2: Execute Tests
1. ✅ Convention #7: Create `experiment/99-integration-test` branch
2. ✅ Convention #5: Create `hotfix/99-test_underscore` branch
3. ✅ Convention #1: Verify hotfix type accepted
4. ✅ Convention #8: Commit with "test" phase
5. ✅ Convention #2: Commit with "impl" phase
6. ✅ Convention #3: Verify "feat:" prefix in commit
7. ✅ Convention #6: PolicyEngine accepts "feat:" prefix
8. ✅ Convention #4: Try delete "staging" branch (should fail)
9. ✅ Convention #9-11: Create PR without base (should default to "develop")

### Phase 3: Cleanup
1. ✅ Delete test branches
2. ✅ Restore original `.st3/git.yaml`
3. ✅ Restart MCP server (reload original config)
4. ✅ Delete test commits (if needed)
5. ✅ Verify workspace clean

---

## Success Criteria

- All 11 conventions tested with custom config
- Custom values used (not defaults)
- No errors from valid operations
- Expected errors from invalid operations
- Workspace restored to clean state
- Server running with original config

---

## Test Results

_To be filled during execution_

### Convention #1: Branch Types
- Status: 
- Result: 
- Notes: 

### Convention #2: TDD Phases
- Status: 
- Result: 
- Notes: 

### Convention #3: Commit Prefix Map
- Status: 
- Result: 
- Notes: 

### Convention #4: Protected Branches
- Status: 
- Result: 
- Notes: 

### Convention #5: Branch Name Pattern
- Status: 
- Result: 
- Notes: 

### Convention #6: TDD Commit Prefixes
- Status: 
- Result: 
- Notes: 

### Convention #7: Branch Type Regex
- Status: 
- Result: 
- Notes: 

### Convention #8: Phase Regex
- Status: 
- Result: 
- Notes: 

### Convention #9-11: Default Base Branch
- Status: 
- Result: 
- Notes: 

---

## Final Verdict

- Overall Status: 
- Issues Found: 
- Blockers: 
- Ready for Documentation Phase: 

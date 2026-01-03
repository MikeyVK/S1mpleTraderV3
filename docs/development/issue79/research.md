# Issue #79 Research: Parent Branch Tracking

**Date:** 2026-01-03  
**Branch:** feature/79-parent-branch-tracking  
**Status:** Research Phase  
**Parent Branch:** epic/76-quality-gates-tooling

---

## Executive Summary

Investigation into adding parent_branch tracking to the state management system. Current tooling captures `base_branch` parameter during branch creation but does not persist this information to state.json, making it impossible to programmatically determine merge targets.

**Key Finding:** The infrastructure already exists - we just need to wire `base_branch` through the initialization chain.

---

## Current State Flow Analysis

### 1. Branch Creation Flow (create_branch tool)

**File:** `mcp_server/tools/git_tools.py:32-75`

```python
# User provides base_branch
params = CreateBranchInput(
    name="79-parent-branch-tracking",
    branch_type="feature",
    base_branch="epic/76-quality-gates-tooling"  # ✅ Captured here
)

# But NOT stored anywhere!
branch_name = self.manager.create_branch(
    params.name,
    params.branch_type,
    params.base_branch  # ❌ Lost after branch creation
)
```

**Gap:** `base_branch` is used to create the branch via GitManager, but never persisted.

### 2. Project Initialization Flow (initialize_project tool)

**File:** `mcp_server/tools/project_tools.py:75-130`

```python
# Step 1: Create projects.json
result = self.manager.initialize_project(...)

# Step 2: Get CURRENT branch (not parent!)
branch = self.git_manager.get_current_branch()

# Step 3: Initialize state WITHOUT parent info
self.state_engine.initialize_branch(
    branch=branch,
    issue_number=params.issue_number,
    initial_phase=first_phase
    # ❌ No parent_branch parameter!
)
```

**Gap:** `initialize_branch()` has no concept of parent branch.

### 3. State Structure (PhaseStateEngine)

**File:** `mcp_server/managers/phase_state_engine.py:100-110`

```python
state: dict[str, Any] = {
    "branch": branch,
    "issue_number": issue_number,
    "workflow_name": project["workflow_name"],
    "current_phase": initial_phase,
    "transitions": [],
    "created_at": datetime.now(UTC).isoformat()
    # ❌ No parent_branch field!
}
```

**Current state.json example:**
```json
{
  "feature/79-parent-branch-tracking": {
    "branch": "feature/79-parent-branch-tracking",
    "issue_number": 79,
    "workflow_name": "feature",
    "current_phase": "research",
    "transitions": [],
    "created_at": "2026-01-03T14:10:37.070163+00:00"
  }
}
```

### 4. Branch Checkout Sync (git_checkout tool)

**File:** `mcp_server/tools/git_tools.py:205-240`

```python
# After branch switch, sync state
state = engine.get_state(params.branch)
current_phase = state.get('current_phase', 'unknown')

# Returns phase info but could also return parent_branch!
return ToolResult.text(
    f"Switched to branch: {params.branch}\n"
    f"Current phase: {current_phase}"
    # Could add: f"Parent branch: {parent_branch}"
)
```

**Opportunity:** Already syncing state on checkout, can display parent_branch.

---

## Discovery: How Parent Branch Was Found

For Issue #77, parent branch was discovered via `git reflog`:

```bash
git reflog show --all | Select-String -Pattern "checkout.*77"

# Output showed:
# 59910bb HEAD@{13}: checkout: moving from epic/76-quality-gates-tooling to bug/77-git-checkout-sync
```

**Problem with git reflog:**
- Not persistent across machines
- Limited history (typically 90 days)
- Requires parsing and pattern matching
- Unreliable for old branches

---

## Proposed Solution Architecture

### Option 1: Thread base_branch through initialization chain ⭐ RECOMMENDED

**Changes Required:**
1. `PhaseStateEngine.initialize_branch()` - Add `parent_branch` parameter
2. `InitializeProjectTool` - Accept optional `parent_branch`, default to current branch
3. Update `state.json` schema to include `parent_branch`
4. `git_checkout` tool - Display parent_branch in output

**Workflow:**
```python
# User creates branch with explicit parent
create_branch(
    name="79-feature",
    base_branch="epic/76"  # Captured
)

# Later, during initialize_project
initialize_project(
    issue_number=79,
    parent_branch="epic/76"  # Explicitly provided OR auto-detected
)

# PhaseStateEngine stores it
state = {
    "branch": "feature/79-feature",
    "parent_branch": "epic/76",  # ✅ Persisted!
    ...
}
```

**Pros:**
- Minimal changes
- Uses existing parameter that's already captured
- No new tools needed
- Clean data flow

**Cons:**
- Requires two-step process (create_branch + initialize_project)
- User must remember to pass parent_branch

### Option 2: Auto-capture in create_branch tool

**Changes Required:**
1. `create_branch` tool - Capture current branch BEFORE creating new branch
2. Immediately call `PhaseStateEngine.initialize_branch()` with parent
3. Add state initialization to create_branch workflow

**Workflow:**
```python
# In CreateBranchTool.execute()
current_branch = self.manager.get_current_branch()  # NEW: Capture parent

branch_name = self.manager.create_branch(...)

# NEW: Initialize state immediately
engine.initialize_branch(
    branch=branch_name,
    parent_branch=current_branch,  # Auto-detected
    issue_number=...,  # Extract from branch name?
    initial_phase="research"
)
```

**Pros:**
- Automatic - user doesn't need to remember
- Single step process
- Parent always captured

**Cons:**
- Tight coupling between branch creation and state initialization
- What if user creates branch without project? (edge case)
- Need to extract issue_number from branch name

### Option 3: Store in projects.json instead of state.json

**Changes Required:**
1. Add `parent_branch` field to projects.json
2. Keep per-project instead of per-branch
3. Read from projects.json when needed

**Workflow:**
```json
// projects.json
{
  "79": {
    "issue_title": "...",
    "workflow_name": "feature",
    "parent_branch": "epic/76",  // NEW
    "required_phases": [...]
  }
}
```

**Pros:**
- Survives branch deletion
- Project-level metadata (not branch-level)
- Already have projects.json infrastructure

**Cons:**
- Parent branch is really branch metadata, not project metadata
- What if same project has multiple branches? (each from different parent)
- Less discoverable during branch checkout

### Option 4: Hybrid - Store in both + git reflog fallback

**Changes Required:**
1. Add `parent_branch` to state.json (primary)
2. Add `parent_branch` to projects.json (backup)
3. Add `get_parent_branch()` tool that tries:
   - state.json (preferred)
   - projects.json (fallback)
   - git reflog (last resort)
   - Manual input (user override)

**Pros:**
- Most robust
- Multiple fallback strategies
- Handles migration of existing branches

**Cons:**
- Most complex
- Data duplication
- Maintenance burden

---

## Recommended Approach: Option 1 + Migration

**Phase 1: Add parent_branch to state schema**
1. Update `PhaseStateEngine.initialize_branch()` signature:
   ```python
   def initialize_branch(
       self, 
       branch: str, 
       issue_number: int, 
       initial_phase: str,
       parent_branch: str | None = None  # NEW optional parameter
   ) -> dict[str, Any]:
   ```

2. Store in state:
   ```python
   state = {
       "branch": branch,
       "issue_number": issue_number,
       "workflow_name": project["workflow_name"],
       "current_phase": initial_phase,
       "parent_branch": parent_branch,  # NEW
       "transitions": [],
       "created_at": datetime.now(UTC).isoformat()
   }
   ```

**Phase 2: Update initialize_project tool**
1. Add optional `parent_branch` parameter to `InitializeProjectInput`
2. If not provided, attempt to detect from git (get_current_branch before creation)
3. Pass to `initialize_branch()`

**Phase 3: Wire through create_branch workflow**
1. Capture current branch before creating new branch
2. Store in tool result or intermediate variable
3. User provides to initialize_project, or we auto-detect

**Phase 4: Add retrieval tools**
1. `get_parent_branch(branch)` - Read from state.json
2. Update `git_checkout` to display parent_branch
3. Add `merge_to_parent()` helper tool

**Phase 5: Migration for existing branches**
1. For branches without parent_branch:
   - Try git reflog first
   - Default to "main" if not found
   - Log warning
   - Allow manual override

---

## Alternative: Issue Metadata Storage

**User suggestion:** Could parent_branch be stored in GitHub Issue description/metadata?

**Analysis:**
```markdown
## Issue #79: Feature Title

**Parent Branch:** epic/76-quality-gates-tooling
<!-- Auto-generated metadata -->

... issue description ...
```

**Pros:**
- Survives local state deletion
- Visible in GitHub UI
- Easy to audit
- Can store in issue body or custom fields

**Cons:**
- Requires GitHub API calls
- Slower than local state.json
- What if issue closed but branch still active?
- Duplication with state.json

**Verdict:** Good as BACKUP/AUDIT but not primary storage. Use state.json for fast local access, sync to GitHub issue for persistence.

---

## Data Flow Diagram

```
Current Flow (NO parent tracking):
┌─────────────────┐
│  create_branch  │  base_branch="epic/76" ✅ captured
└────────┬────────┘
         │ git checkout -b feature/79 epic/76
         ↓
┌─────────────────┐
│ GitManager      │  ❌ base_branch lost here
└────────┬────────┘
         │
         ↓
┌──────────────────────┐
│ initialize_project   │  ❌ No parent_branch parameter
└────────┬─────────────┘
         │
         ↓
┌──────────────────────┐
│ PhaseStateEngine     │  ❌ No parent_branch in state
│ initialize_branch()  │
└────────┬─────────────┘
         │
         ↓
    state.json (missing parent_branch)


Proposed Flow (WITH parent tracking):
┌─────────────────┐
│  create_branch  │  base_branch="epic/76" ✅
└────────┬────────┘
         │ 
         │ 1. current_branch = get_current_branch()  ← NEW
         │ 2. git checkout -b feature/79 epic/76
         ↓
┌─────────────────┐
│ GitManager      │  ✅ Return parent_branch in result
└────────┬────────┘
         │
         ↓
┌──────────────────────┐
│ initialize_project   │  parent_branch="epic/76" ✅
└────────┬─────────────┘
         │
         ↓
┌──────────────────────┐
│ PhaseStateEngine     │  parent_branch="epic/76" ✅
│ initialize_branch()  │
└────────┬─────────────┘
         │
         ↓
    state.json WITH parent_branch ✅
```

---

## Next Steps

1. ✅ **Research Complete** - Understand current state flow
2. ⏭️ **Planning** - Decide on Option 1 architecture
3. ⏭️ **Design** - Detailed implementation plan
4. ⏭️ **TDD** - Write tests for parent_branch storage/retrieval
5. ⏭️ **Integration** - Update all tools
6. ⏭️ **Documentation** - Update tool docs

---

## Questions for Planning Phase

1. Should parent_branch be REQUIRED or optional in state.json?
   - Optional = backward compatible
   - Required = cleaner but needs migration

2. How to handle branches created before this feature?
   - Git reflog fallback?
   - Default to "main"?
   - Prompt user?

3. Should we validate parent_branch exists?
   - Check git branch list?
   - Allow any string?

4. Should parent_branch be mutable?
   - What if user wants to rebase to different parent?
   - Add `update_parent_branch()` tool?

5. Should we sync to GitHub issues?
   - For audit/backup?
   - Performance cost?

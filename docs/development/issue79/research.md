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

## CRITICAL: How state.json Actually Works (Cross-Machine Sync)

### Reality Check - Auto-Recovery System

**Key Discovery:** state.json is in `.gitignore` BUT auto-recovery makes cross-machine work possible!

#### The Flow After Branch Switch:

```python
# git_checkout tool calls:
state = engine.get_state(params.branch)
```

#### What get_state() Does (PhaseStateEngine.get_state):

```python
def get_state(self, branch: str) -> dict[str, Any]:
    # Step 1: Check if state.json exists
    if not self.state_file.exists():
        self.state_file.write_text(json.dumps({}, indent=2))  # Create empty
        states = {}
    else:
        states = json.loads(self.state_file.read_text())
    
    # Step 2: Check if branch in state.json
    if branch not in states:
        # AUTO-RECOVERY MODE 2: Reconstruct from git!
        state = self._reconstruct_branch_state(branch)
        self._save_state(branch, state)  # Save for next time
        return state
    
    return states[branch]
```

#### Auto-Recovery Sources (Mode 2):

**File:** `phase_state_engine.py:298-340` (`_reconstruct_branch_state`)

1. **Issue Number** - Extracted from branch name:
   ```python
   # Branch: feature/79-parent-branch-tracking
   # Extract: 79
   match = re.match(r'^(?:feature|fix|bug|docs|refactor|hotfix)/(\d+)-', branch)
   issue_number = int(match.group(1))
   ```

2. **Workflow Definition** - From projects.json (IN GIT):
   ```python
   project = self.project_manager.get_project_plan(issue_number)
   # Returns: {"workflow_name": "feature", "required_phases": [...]}
   ```

3. **Current Phase** - Inferred from git commits:
   ```python
   commits = git log --max-count=50 --pretty=%s branch
   # Search for: phase:red, phase:tdd, phase:integration, etc.
   current_phase = self._detect_phase_label(commits, workflow_phases)
   ```

#### Reconstructed State Structure:

```json
{
  "branch": "feature/79-parent-branch-tracking",
  "issue_number": 79,
  "workflow_name": "feature",
  "current_phase": "research",  // From git commits OR fallback to first phase
  "transitions": [],  // ❌ Cannot reconstruct history
  "created_at": "2026-01-03T14:10:37.070163+00:00",
  "reconstructed": true  // ✅ Audit flag
}
```

### Cross-Machine Scenario:

```
Machine A:
1. Create branch feature/79-test
2. Work, make commits with phase:red, phase:green labels
3. Push to GitHub
4. state.json stays local (in .gitignore)

Machine B:
1. git pull
2. git checkout feature/79-test
3. No state.json for this branch!
4. get_state() auto-recovery:
   - Read projects.json (IS in git) ✅
   - Extract issue number from branch name ✅
   - Scan git commits for phase:labels ✅
   - Reconstruct state.json locally ✅
5. Continue working!
```

### What IS in Git vs What Is NOT:

| File | In Git? | Purpose | Source of Truth |
|------|---------|---------|-----------------|
| `projects.json` | ✅ YES | Workflow definitions per issue | SSOT for workflows |
| `state.json` | ❌ NO (.gitignore) | Current phase per branch (local cache) | Reconstructable from git |
| Git commits | ✅ YES | phase:label in commit messages | SSOT for phase history |
| Branch name | ✅ YES | Contains issue number | Used for reconstruction |

### Critical Insight for parent_branch:

**Question:** Where can parent_branch be stored to survive cross-machine?

**Options:**

1. ✅ **projects.json** - IN GIT, survives cross-machine
   - Pro: Persistent, shared across machines
   - Con: Project-level, not branch-level
   - Verdict: Good for "canonical" parent

2. ❌ **state.json** - NOT in git, lost on machine switch
   - Pro: Branch-level metadata
   - Con: Needs reconstruction like current_phase
   - Verdict: Needs reconstruction source!

3. ✅ **Git commits** - IN GIT via commit metadata
   - Pro: Already reconstructible source
   - Con: Need to add parent_branch label to first commit
   - Verdict: Best for auto-recovery!

4. ✅ **Branch name** - IN GIT inherently
   - Pro: Always available
   - Con: Can't change branch names to encode parent
   - Verdict: Not feasible

5. ✅ **GitHub Issue** - IN GitHub, accessible anywhere
   - Pro: Survives everything
   - Con: Requires API calls, slower
   - Verdict: Good for audit/backup

### Recommended Storage Strategy:

**Primary Storage (Fast Local Cache):**
- state.json with parent_branch field
- Good for current session
- Lost on machine switch → needs reconstruction

**Reconstruction Source (SSOT):**
- Add parent_branch to projects.json
- OR encode in first commit on branch
- OR store in GitHub issue metadata

**Reconstruction Flow:**
```python
def _reconstruct_branch_state(self, branch: str) -> dict[str, Any]:
    # Existing code...
    issue_number = self._extract_issue_from_branch(branch)
    project = self.project_manager.get_project_plan(issue_number)
    current_phase = self._infer_phase_from_git(branch, workflow_phases)
    
    # NEW: Reconstruct parent_branch
    parent_branch = self._reconstruct_parent_branch(branch, project)
    
    state = {
        "branch": branch,
        "issue_number": issue_number,
        "workflow_name": project["workflow_name"],
        "current_phase": current_phase,
        "parent_branch": parent_branch,  # ✅ Reconstructed
        "transitions": [],
        "created_at": datetime.now(UTC).isoformat(),
        "reconstructed": True
    }
    return state
```

**Where to get parent_branch for reconstruction:**

Option A: From projects.json
```json
{
  "79": {
    "issue_title": "...",
    "workflow_name": "feature",
    "parent_branch": "epic/76-quality-gates-tooling",  // NEW
    "required_phases": [...]
  }
}
```

Option B: From git commit metadata
```bash
# First commit on branch feature/79:
git log --max-count=1 --pretty=%B feature/79

# Output should contain:
parent:epic/76-quality-gates-tooling
```

Option C: From git reflog + git merge-base
```python
# Find where branch was created
result = subprocess.run(
    ["git", "reflog", "show", "--all"],
    capture_output=True, text=True
)
# Parse: "checkout: moving from <parent> to <branch>"
```

---

## Next Steps

1. ✅ **Research Complete** - Understand current state flow AND auto-recovery
2. ⏭️ **Planning** - Decide where to store parent_branch for reconstruction
3. ⏭️ **Design** - Detailed implementation plan
4. ⏭️ **TDD** - Write tests for parent_branch storage/retrieval/reconstruction
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

# Issue #39 Research: InitializeProjectTool State Management Gap

**Issue:** InitializeProjectTool does not initialize branch state in PhaseStateEngine  
**Date:** 2025-12-30  
**Status:** Research Phase

---

## Problem Statement

`initialize_project` tool creates project plan metadata in `.st3/projects.json` but **does not initialize branch phase state** in `.st3/state.json`, causing:

1. **Manual workarounds required** - Users must manually initialize state.json
2. **JSON format incompatibility** - PowerShell vs Python JSON formatting causes tool failures
3. **Broken atomicity** - Projects.json updates but state.json doesn't
4. **Workflow friction** - Every new issue requires manual intervention

**Historical Evidence:**
- Issue #51 (2025-12-27): Manual state.json editing via PowerShell
- Issue #64 (2025-12-29): JSON format mismatch caused transition_phase failures
- Issue #68 (2025-12-30): Fixed parameter mismatch symptom, not root cause

---

## Current Implementation Analysis

### 1. InitializeProjectTool (mcp_server/tools/project_tools.py)

**What it does:**
```python
async def execute(self, params: InitializeProjectInput) -> ToolResult:
    result = self.manager.initialize_project(
        issue_number=params.issue_number,
        issue_title=params.issue_title,
        workflow_name=params.workflow_name,
        options=options
    )
    return ToolResult.text(json.dumps(result, indent=2))
```

**What it creates:**
- ✅ `.st3/projects.json` - Project plan with workflow and phases
- ❌ `.st3/state.json` - **NOT CREATED**

**Missing dependencies:**
- No `PhaseStateEngine` import or usage
- No `GitManager` import for branch detection
- No atomicity handling (rollback if partial failure)

### 2. ProjectManager (mcp_server/managers/project_manager.py)

**Responsibility:** Project plan persistence to projects.json

**What it does:**
```python
def initialize_project(...) -> dict[str, Any]:
    # 1. Validate workflow exists
    workflow = workflow_config.get_workflow(workflow_name)
    
    # 2. Determine execution mode and phases
    required_phases = opts.custom_phases or tuple(workflow.phases)
    
    # 3. Create ProjectPlan dataclass
    plan = ProjectPlan(...)
    
    # 4. Save to projects.json
    self._save_project_plan(plan)
    
    # 5. Return result dict
    return {"success": True, "workflow_name": ..., ...}
```

**What it creates:**
- ✅ `.st3/projects.json` with structure:
```json
{
  "39": {
    "issue_title": "InitializeProjectTool...",
    "workflow_name": "bug",
    "execution_mode": "interactive",
    "required_phases": ["research", "planning", "tdd", "integration", "documentation"],
    "skip_reason": null,
    "created_at": "2025-12-30T..."
  }
}
```

**Scope boundary:** ProjectManager is **only** responsible for projects.json  
**Out of scope:** Branch state management (state.json) - that's PhaseStateEngine's job

### 3. PhaseStateEngine (mcp_server/managers/phase_state_engine.py)

**Responsibility:** Branch phase state management in state.json

**What it expects:**
```python
def initialize_branch(self, branch: str, issue_number: int, initial_phase: str):
    # 1. Get project plan (REQUIRES projects.json to exist!)
    project = self.project_manager.get_project_plan(issue_number)
    if not project:
        raise ValueError(f"Project {issue_number} not found. Initialize project first.")
    
    # 2. Create branch state with workflow caching
    state = {
        "branch": branch,
        "issue_number": issue_number,
        "workflow_name": project["workflow_name"],  # From projects.json
        "current_phase": initial_phase,
        "transitions": [],
        "created_at": datetime.now(UTC).isoformat()
    }
    
    # 3. Save to state.json
    self._save_state(branch, state)
```

**What it creates:**
- ✅ `.st3/state.json` with structure:
```json
{
  "branches": {
    "fix/39-initialize-project-tool": {
      "branch": "fix/39-initialize-project-tool",
      "issue_number": 39,
      "workflow_name": "bug",
      "current_phase": "research",
      "transitions": [],
      "created_at": "2025-12-30T..."
    }
  }
}
```

**Dependency:** MUST be called AFTER ProjectManager.initialize_project()  
**Requires:** projects.json must exist (for workflow lookup)

### 4. GitManager (mcp_server/managers/git_manager.py)

**Relevant API:**
```python
def get_current_branch(self) -> str:
    """Get the current branch name.
    
    Returns:
        Current branch name (e.g., 'fix/39-initialize-project-tool')
    """
    return self.adapter.get_current_branch_name()
```

---

## State.json Lifecycle Analysis

### History: What Happened to state.json in Git

**Commit:** `59729f9` (2025-12-29, branch: fix/64-create-branch-from-head)
```
commit 59729f9ff5f513832f3a655b2a796cc24018c662
Author: MikeyVK <michel@1voudig.com>
Date:   Mon Dec 29 23:22:26 2025 +0100

    docs: Update state after completing Issue #64 implementation

diff --git a/.st3/state.json b/.st3/state.json
deleted file mode 100644
```

**Analysis:**
- ✅ **This deletion is CORRECT**
- state.json is **runtime state**, not source code
- Contains branch-specific workflow state (current phase, transitions)
- Should be **generated dynamically** by PhaseStateEngine
- Should **NOT be version controlled** (like .venv/, __pycache__)

### Current Git Status

**File tracking:**
```bash
$ git ls-files .st3/state.json
# (no output - file not tracked)
```

**.gitignore status:**
```bash
$ grep -r "state" .gitignore
# (no matches - NOT in .gitignore yet!)
```

**⚠️ Problem:** state.json should be in .gitignore but isn't  
**⚠️ Risk:** Future commits might accidentally re-add it to git

### Runtime Behavior

**When PhaseStateEngine.initialize_branch() is called:**
1. Creates `.st3/` directory if missing
2. Creates or updates `state.json` with branch entry
3. File persists on disk (runtime state)
4. Used by `transition_phase` tool for workflow validation

**File location:** `{workspace_root}/.st3/state.json`  
**Format:** Python-generated JSON (via json.dump())  
**Encoding:** UTF-8

---

## Root Cause Analysis

### Gap 1: Missing State Initialization (Single Machine)

**Current Flow:**
```
User calls initialize_project
    ↓
InitializeProjectTool.execute()
    ↓
ProjectManager.initialize_project()
    ↓
✅ projects.json created
❌ state.json NOT created
    ↓
User must manually call PhaseStateEngine.initialize_branch()
OR manually edit state.json
```

**Expected Flow:**
```
User calls initialize_project
    ↓
InitializeProjectTool.execute()
    ↓
1. ProjectManager.initialize_project()
   ✅ projects.json created
    ↓
2. GitManager.get_current_branch()
   ✅ branch name detected
    ↓
3. PhaseStateEngine.initialize_branch(branch, issue, first_phase)
   ✅ state.json created
    ↓
✅ Both files created atomically
✅ Ready for transition_phase immediately
```

### Gap 2: Missing State Recovery (Cross-Machine Scenario)

**Critical Discovery:** During research, cross-machine scenario revealed fundamental gap in state management architecture.

**Scenario:**
```
Machine A (Development):
├─ Create branch: fix/39-initialize-project-tool
├─ Initialize project: projects.json ✅ + state.json ✅
├─ Work on issue: current_phase = "planning"
├─ Commit and push code
└─ Only projects.json committed (state.json in .gitignore)

Git (SSOT for code):
├─ .st3/projects.json ✅ (version controlled)
└─ .st3/state.json ❌ (NOT version controlled - runtime state)

Machine B (Fresh clone/pull):
├─ Pull latest code
├─ Has: .st3/projects.json ✅
├─ Missing: .st3/state.json ❌
└─ Problem: Current phase information LOST
```

**Analysis of Existing Architecture:**

Checked Issue #42 documentation (8-phase model design):
- ✅ Extensive design for PhaseStateEngine responsibilities
- ✅ Clear SRP: ProjectManager (projects.json) vs PhaseStateEngine (state.json)
- ❌ **NO documentation for cross-machine state recovery**
- ❌ **NO scenario handling for missing state.json**

Checked PhaseStateEngine implementation:
```python
def get_state(self, branch: str) -> dict[str, Any]:
    """Get full state for branch."""
    if not self.state_file.exists():
        raise ValueError("State file not found. Initialize branch first.")
    
    if branch not in states:
        raise ValueError(f"Branch '{branch}' not found. Initialize branch first.")
    
    return state
```

**Current behavior:** **FAILS HARD** if state.json missing
- No auto-recovery mechanism
- No reconstruction from git history
- Error message suggests "initialize branch" (incorrect - initialization already happened on Machine A)

**Architectural Assumption (Implicit):**
- ✅ projects.json in git (SSOT for workflow definitions)
- ✅ state.json NOT in git (runtime state principle)
- ❌ **state.json always exists** (WRONG - breaks on machine switch)
- ❌ **No recovery strategy defined**

**Conclusion:** Cross-machine state recovery is a **GAP** in current architecture, not existing business logic

### Why Manual Workarounds Fail

**Issue:** Manual state.json creation causes format incompatibility

**PowerShell JSON generation:**
```powershell
@{branches=@{...}} | ConvertTo-Json -Depth 10 | Set-Content ".st3/state.json"
```

**Problems:**
- Different whitespace/indentation than Python json.dump()
- Different line endings (CRLF vs LF)
- Different key ordering
- UTF-8 BOM vs UTF-8

**Result:** `transition_phase` tool fails with:
```
❌ Transition failed: Expecting value: line 1 column 1 (char 0)
```

**Why:** Python's json.loads() expects Python's json.dump() formatting

**Solution:** Let PhaseStateEngine create state.json - never manual editing

### Git Commit History as Phase Indicator

**Observation:** Git commit messages already contain phase information!

```bash
$ git log --oneline --grep="phase"
456514d docs: Complete research phase for Issue #39
1123b6b docs: Planning phase #67: Design cache invalidation solution
4920f0e test: Research phase #67: Analyze singleton stale cache bug
0e6d8d8 test: Complete planning phase for Issue #64
```

**Pattern:** Many commits explicitly mention phase transitions
- "Complete research phase"
- "Planning phase #67"
- "test: Research phase"

**Insight:** Git history contains phase progression information that could be used for state reconstruction when state.json is missing

---

---

## Proposed Solution: Dual-Mode State Management

### Overview

Fix both scenarios with comprehensive state management:

**Mode 1: Normal Initialization** (Single machine, new project)
- InitializeProjectTool creates both projects.json AND state.json atomically
- Branch name auto-detected via GitManager
- First phase auto-detected from workflow

**Mode 2: Auto-Recovery** (Cross-machine, missing state.json)
- PhaseStateEngine.get_state() detects missing branch state
- Reconstructs state from projects.json + git commit history
- Transparent to user (no manual intervention)

### Mode 1: Enhanced InitializeProjectTool

**Implementation Strategy:**

**1. Add Required Dependencies**
```python
class InitializeProjectTool(BaseTool):
    def __init__(self, workspace_root: Path | str):
        super().__init__()
        self.workspace_root = Path(workspace_root)
        self.project_manager = ProjectManager(workspace_root=workspace_root)
        self.git_manager = GitManager()  # NEW: For branch detection
        self.phase_engine = PhaseStateEngine(  # NEW: For state initialization
            workspace_root=workspace_root,
            project_manager=self.project_manager
        )
```

**2. Execute Method with Atomic Initialization**
```python
async def execute(self, params: InitializeProjectInput) -> ToolResult:
    try:
        # Step 1: Create project plan
        result = self.project_manager.initialize_project(...)
        
        # Step 2: Get current branch
        branch = self.git_manager.get_current_branch()
        
        # Step 3: Get first phase from workflow
        first_phase = result["required_phases"][0]
        
        # Step 4: Initialize branch state
        self.phase_engine.initialize_branch(
            branch=branch,
            issue_number=params.issue_number,
            initial_phase=first_phase
        )
        
        return ToolResult.text(
            f"✅ Project initialized\n"
            f"✅ Branch state initialized: {branch} @ {first_phase}\n"
            f"📝 Projects: .st3/projects.json\n"
            f"📝 State: .st3/state.json"
        )
    except (ValueError, OSError) as e:
        return ToolResult.error(str(e))
```

### Mode 2: PhaseStateEngine Auto-Recovery

**Problem:** On machine switch, state.json is missing but git + projects.json have all info needed

**Strategy:** Transparent auto-recovery when state missing

**Implementation in PhaseStateEngine:**

```python
def get_state(self, branch: str) -> dict[str, Any]:
    """Get branch state with transparent auto-recovery.
    
    If state.json missing or branch not found:
    1. Reconstruct state from projects.json (SSOT for workflow)
    2. Infer current phase from git commit messages
    3. Initialize state.json with reconstructed data
    4. Return state
    
    This handles cross-machine scenarios automatically.
    """
    # Check if state file exists
    if not self.state_file.exists():
        logger.info("State file missing, reconstructing from git...")
        # Create empty state file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({}, indent=2))
    
    # Load state
    states = json.loads(self.state_file.read_text())
    
    # Check if branch exists
    if branch not in states:
        logger.info(f"Branch '{branch}' not in state, reconstructing...")
        state = self._reconstruct_branch_state(branch)
        self._save_state(branch, state)
        return state
    
    return states[branch]

def _reconstruct_branch_state(self, branch: str) -> dict[str, Any]:
    """Reconstruct missing branch state from projects.json + git history.
    
    Recovery algorithm:
    1. Extract issue number from branch name (e.g., fix/39-name → 39)
    2. Load project plan from projects.json (SSOT for workflow)
    3. Infer current phase from git commit messages
    4. Create state with empty transition history (cannot reconstruct)
    
    Returns:
        Reconstructed state dict
    
    Raises:
        ValueError: If issue number can't be extracted or project not found
    """
    # Step 1: Extract issue number from branch name
    issue_number = self._extract_issue_from_branch(branch)
    if not issue_number:
        raise ValueError(
            f"Cannot extract issue number from branch '{branch}'. "
            "Expected format: <type>/<number>-<description>"
        )
    
    # Step 2: Get project plan (SSOT for workflow definition)
    project = self.project_manager.get_project_plan(issue_number)
    if not project:
        raise ValueError(
            f"Project plan not found for issue #{issue_number}. "
            "Run initialize_project first."
        )
    
    # Step 3: Infer current phase from git commits
    current_phase = self._infer_phase_from_git(
        branch=branch,
        workflow_phases=project["required_phases"]
    )
    
    # Step 4: Create reconstructed state
    logger.info(
        f"Reconstructed state for {branch}: "
        f"issue={issue_number}, phase={current_phase}"
    )
    
    return {
        "branch": branch,
        "issue_number": issue_number,
        "workflow_name": project["workflow_name"],
        "current_phase": current_phase,
        "transitions": [],  # Cannot reconstruct history
        "created_at": datetime.now(UTC).isoformat(),
        "reconstructed": True  # Flag for debugging/audit
    }

def _extract_issue_from_branch(self, branch: str) -> int | None:
    """Extract issue number from branch name.
    
    Supported formats:
    - feature/42-description → 42
    - fix/39-description → 39
    - refactor/49-description → 49
    
    Returns:
        Issue number or None if not found
    """
    import re
    match = re.match(r'^[a-z]+/(\d+)-', branch)
    return int(match.group(1)) if match else None

def _infer_phase_from_git(
    self, branch: str, workflow_phases: list[str]
) -> str:
    """Infer current phase from git commit messages.
    
    Algorithm:
    1. Get recent commits on current branch (limit 50)
    2. Search commit messages for phase keywords
    3. Return most recent phase found (latest = current)
    4. If no phase commits found, default to first phase (safe)
    
    Commit message patterns recognized:
    - "Complete research phase for Issue #39"
    - "Planning phase #67: Design cache invalidation"
    - "test: Research phase #67"
    
    Args:
        branch: Branch name
        workflow_phases: List of valid phases from workflow
    
    Returns:
        Inferred current phase (or first phase as fallback)
    """
    try:
        # Get recent commits (GitAdapter method)
        commits = self.git_adapter.get_recent_commits(branch, limit=50)
        
        # Search commits in reverse chronological order
        for commit in commits:
            message_lower = commit.message.lower()
            
            # Check each phase in reverse order (later phases take precedence)
            for phase in reversed(workflow_phases):
                if phase in message_lower:
                    logger.info(
                        f"Inferred phase '{phase}' from commit {commit.sha[:7]}: "
                        f"{commit.message[:60]}..."
                    )
                    return phase
        
        # No phase found in commits - use first phase (safe default)
        first_phase = workflow_phases[0]
        logger.warning(
            f"No phase commits found for {branch}, "
            f"defaulting to first phase: {first_phase}"
        )
        return first_phase
        
    except Exception as e:
        # Git error - fallback to first phase
        first_phase = workflow_phases[0]
        logger.warning(
            f"Could not infer phase from git ({e}), "
            f"using first phase: {first_phase}"
        )
        return first_phase
```

**User Experience:**
```
Machine B (after git pull):
User: transition_phase(to="integration")
    ↓
PhaseStateEngine.get_state(branch)
    ↓
[INFO] Branch 'fix/39-initialize-project-tool' not in state, reconstructing...
[INFO] Inferred phase 'planning' from commit 456514d
    ↓
Validate transition: planning → integration
    ↓
✅ Transition successful
```

**Tradeoffs Accepted:**
- ⚠️ Transition history lost (empty array after reconstruction)
- ⚠️ May be "behind" if mid-phase work uncommitted (last committed phase returned)
- ⚠️ Requires commit message conventions (phase keywords in messages)

**Benefits:**
- ✅ Transparent - no user action required
- ✅ Works across machines automatically
- ✅ Git commit history is SSOT for phase progression
- ✅ projects.json is SSOT for workflow definition
- ✅ Graceful degradation (defaults to first phase if inference fails)

---

## Integration Points Summary

## Integration Points Summary

### Components Requiring Updates

**1. InitializeProjectTool** (mcp_server/tools/project_tools.py)
- **Add:** GitManager dependency for branch detection
- **Add:** PhaseStateEngine dependency for state initialization
- **Update:** execute() method to call both ProjectManager AND PhaseStateEngine
- **Purpose:** Atomic initialization of both projects.json and state.json

**2. PhaseStateEngine** (mcp_server/managers/phase_state_engine.py)
- **Add:** GitAdapter dependency for commit history access
- **Add:** `_reconstruct_branch_state()` method
- **Add:** `_infer_phase_from_git()` method
- **Add:** `_extract_issue_from_branch()` method
- **Update:** `get_state()` method to auto-recover when branch missing
- **Purpose:** Transparent cross-machine state reconstruction

**3. GitAdapter** (mcp_server/adapters/git_adapter.py)
- **Verify:** `get_recent_commits(branch, limit)` method exists
- **Add if missing:** Method to retrieve commit history with messages
- **Purpose:** Provide commit data for phase inference

**4. .gitignore**
- **Add:** `.st3/state.json` exclusion
- **Purpose:** Prevent accidental version control of runtime state

### Data Flow Summary

**Initialization Flow (Mode 1):**
```
InitializeProjectTool
    ├─> ProjectManager.initialize_project()
    │       └─> Creates .st3/projects.json
    ├─> GitManager.get_current_branch()
    │       └─> Returns branch name
    └─> PhaseStateEngine.initialize_branch()
            └─> Creates .st3/state.json
```

**Recovery Flow (Mode 2):**
```
PhaseStateEngine.get_state(branch)
    ├─> State file missing OR branch not in state
    ├─> _reconstruct_branch_state(branch)
    │       ├─> _extract_issue_from_branch() → issue number
    │       ├─> ProjectManager.get_project_plan() → workflow
    │       ├─> _infer_phase_from_git() → current phase
    │       │       └─> GitAdapter.get_recent_commits()
    │       └─> Create reconstructed state dict
    └─> _save_state() → Write to state.json
```

---

## Proposed Solution Summary

### Complete Fix Scope

**Problem 1: Single Machine Initialization**
- ✅ InitializeProjectTool creates both projects.json AND state.json
- ✅ Atomic operation (both files together)
- ✅ No manual state.json editing required

**Problem 2: Cross-Machine State Recovery**
- ✅ PhaseStateEngine auto-recovers missing state
- ✅ Reconstructs from projects.json (workflow) + git log (phase)
- ✅ Transparent to user (no manual sync needed)

**Problem 3: JSON Format Incompatibility**
- ✅ Only Python creates state.json (consistent formatting)
- ✅ No PowerShell/manual editing

**Problem 4: Git Tracking**
- ✅ state.json added to .gitignore
- ✅ Prevents accidental commits

### Acceptance Criteria

**Mode 1 (Initialization):**
- [ ] InitializeProjectTool creates both projects.json AND state.json
- [ ] Branch name auto-detected via GitManager
- [ ] First phase auto-detected from workflow
- [ ] State.json format compatible with transition_phase tool
- [ ] Works for all workflow types (feature, bug, docs, refactor, hotfix, custom)

**Mode 2 (Recovery):**
- [ ] PhaseStateEngine.get_state() auto-recovers missing state
- [ ] Reconstructs state from projects.json (SSOT for workflow)
- [ ] Infers current phase from git commit messages
- [ ] Defaults to first phase if no commits found
- [ ] Logs reconstruction actions (audit trail)
- [ ] Sets `reconstructed: true` flag in state

**Both Modes:**
- [ ] No manual editing required (either scenario)
- [ ] state.json added to .gitignore
- [ ] Error handling for edge cases (invalid branch format, missing project plan, git errors)
- [ ] Comprehensive tests for both initialization and recovery

### Edge Cases to Handle

**Case 1: Mid-phase uncommitted work**
- Git shows: Last commit = "Complete research phase"
- Reality: Developer halfway through planning
- Recovery: Returns "research" (last committed phase)
- Impact: Developer must re-transition to planning (idempotent, safe)

**Case 2: No phase commits yet**
- Git shows: No commits with phase keywords
- Recovery: Returns first phase from workflow
- Impact: Correct - project just started

**Case 3: Branch name format invalid**
- Branch: "weird-branch-name" (no issue number)
- Error: "Cannot extract issue number from branch"
- Impact: User must use proper branch naming convention

**Case 4: Project plan missing**
- State.json missing, projects.json also missing
- Error: "Project plan not found, run initialize_project first"
- Impact: User must initialize (correct behavior)

**Case 5: Git adapter failure**
- Git command fails (detached HEAD, corrupt repo, etc.)
- Fallback: Default to first phase
- Log: Warning about git error
- Impact: Safe degradation

---

## Benefits of Complete Solution

**1. Single Machine User Experience**
- ✅ Single tool call initializes complete project state
- ✅ No manual file editing required
- ✅ Immediate transition_phase usage after initialization
- ✅ Atomic operation (both files or neither)

**2. Cross-Machine User Experience**
- ✅ State reconstructs automatically on machine switch
- ✅ No manual sync commands required
- ✅ Git is SSOT (commit history + projects.json)
- ✅ Transparent recovery (user doesn't notice)

**3. System Integrity**
- ✅ Consistent JSON formatting (Python → Python)
- ✅ No format incompatibility issues
- ✅ state.json never in git (proper separation)
- ✅ Graceful degradation on errors

**4. Epic #49 Impact**
- ✅ Completes project initialization infrastructure
- ✅ Enables smooth Phase 2 work (#52, #53, #54)
- ✅ Fixes recurring pain point before future issues
- ✅ Establishes pattern for cross-machine scenarios

---

## Next Steps (Planning Phase)

**Planning Phase Goals:**

1. **Design Atomic Initialization Flow**
   - Detailed InitializeProjectTool changes
   - Error handling and rollback strategy
   - Success/failure messages

2. **Design Auto-Recovery Flow**
   - PhaseStateEngine.get_state() enhancement
   - Git commit parsing algorithm
   - Reconstruction logic and edge cases

3. **Design GitAdapter API**
   - Verify or design get_recent_commits() method
   - Define Commit dataclass structure
   - Error handling for git failures

4. **Plan Test Strategy**
   - Mode 1 tests: Initialization scenarios
   - Mode 2 tests: Recovery scenarios
   - Integration tests: End-to-end workflows
   - Edge case tests: Error conditions

5. **Plan .gitignore Update**
   - Add state.json exclusion
   - Verify no existing tracked state.json
   - Document reasoning

**Handover Artifacts:**
- ✅ Research document complete (this document)
- ✅ Problem analysis: Two gaps identified (initialization + recovery)
- ✅ Architecture analysis: Existing design lacks recovery
- ✅ Solution proposed: Dual-mode state management
- ✅ Integration points identified: 4 components
- ✅ Benefits documented: UX + system integrity
- ✅ Edge cases identified: 5 scenarios

**Status:** Research phase COMPLETE. Ready for Planning phase.

---

## Related Files

**Core Implementation:**
- `mcp_server/tools/project_tools.py` - InitializeProjectTool (needs update)
- `mcp_server/managers/project_manager.py` - ProjectManager (no changes)
- `mcp_server/managers/phase_state_engine.py` - PhaseStateEngine (no changes)
- `mcp_server/managers/git_manager.py` - GitManager (no changes)

**Configuration:**
- `.gitignore` - Add state.json exclusion

**Tests:**
- `tests/unit/mcp_server/tools/test_project_tools.py` - Add integration tests
- `tests/unit/mcp_server/managers/test_phase_state_engine.py` - Reference existing tests

---

## Research Complete ✅

**Key Findings:**

1. **Root Cause Identified:** Two distinct gaps in state management
   - Gap 1: InitializeProjectTool doesn't create state.json (single machine issue)
   - Gap 2: PhaseStateEngine has no recovery mechanism (cross-machine issue)

2. **Architecture Gap Discovered:** Cross-machine state recovery not in original design
   - Issue #42 docs: No recovery strategy documented
   - PhaseStateEngine code: Fails hard when state.json missing
   - Implicit assumption: state.json always exists (breaks on machine switch)

3. **Solution Approach:** Dual-mode state management
   - Mode 1: Enhanced initialization (InitializeProjectTool creates both files)
   - Mode 2: Auto-recovery (PhaseStateEngine reconstructs from git + projects.json)

4. **Git as Partial SSOT:** Commit messages contain phase progression
   - Pattern: "Complete research phase", "Planning phase #67"
   - Can infer current phase from commit history
   - Safe fallback: Default to first phase if no commits found

5. **Integration Points:** 4 components need updates
   - InitializeProjectTool: Add GitManager + PhaseStateEngine
   - PhaseStateEngine: Add reconstruction methods + git commit parsing
   - GitAdapter: Verify/add get_recent_commits() method
   - .gitignore: Add state.json exclusion

**Ready for Planning Phase:** Complete implementation design for both modes
2. state.json deletion from git was correct - it's runtime state
3. Manual workarounds cause JSON format incompatibility
4. Fix requires GitManager + PhaseStateEngine integration
5. state.json must be added to .gitignore

**Ready for:** Planning Phase
# Cross-Machine State Recovery Strategy

**Issue #39 - Additional Research: State Synchronization**  
**Date:** 2025-12-30

---

## Problem: State.json Not in Git

**Scenario:**
```
Developer A (Machine A):
├─ Work on Issue #39
├─ state.json exists: {"fix/39": {"current_phase": "planning", ...}}
├─ Commit and push code
└─ state.json NOT pushed (in .gitignore)

Developer B (Machine B):
├─ Pull latest code
├─ Has projects.json ✅
└─ Missing state.json ❌
└─ Question: What phase are we in?
```

**Core Challenge:** How to reconstruct state.json when git is SSOT?

---

## Solution Options

### Option 1: Git Commit Messages as State Source ⭐ RECOMMENDED

**Observation:** Commit messages already contain phase info!
```bash
$ git log --oneline
456514d docs: Complete research phase for Issue #39
1123b6b docs: Planning phase #67: Design cache invalidation solution
4920f0e test: Research phase #67: Analyze singleton stale cache bug
```

**Pattern:** Commits include phase keywords (research, planning, tdd, integration, docs)

**Strategy:**
```python
def reconstruct_state_from_git(branch: str, issue_number: int) -> str:
    """Reconstruct current phase from git commit messages.
    
    Algorithm:
    1. Get commits on current branch
    2. Find most recent commit mentioning phase transition
    3. Extract phase from commit message
    4. If no phase commits found, default to first phase from projects.json
    """
    # Get commits for current branch
    commits = git.log(branch)
    
    # Phase keywords in order
    phases = ["research", "planning", "tdd", "integration", "docs"]
    
    # Find most recent phase mention
    for commit in commits:
        for phase in reversed(phases):  # Check later phases first
            if phase in commit.message.lower():
                return phase
    
    # Default: First phase from workflow
    project = project_manager.get_project_plan(issue_number)
    return project["required_phases"][0]
```

**Benefits:**
- ✅ Git is true SSOT (commit history never lies)
- ✅ Works across machines automatically
- ✅ No additional sync mechanism needed
- ✅ Audit trail already exists in git log

**Limitations:**
- ⚠️ Assumes commit messages follow convention
- ⚠️ Requires parsing commit messages (fragile)
- ⚠️ Mid-phase work lost (if researching but not committed)

---

### Option 2: PhaseStateEngine Auto-Recovery

**Strategy:** When state.json missing, auto-reconstruct on first access

```python
class PhaseStateEngine:
    def get_state(self, branch: str) -> dict[str, Any]:
        """Get branch state with auto-recovery.
        
        If state.json missing or branch not found:
        1. Look up project in projects.json
        2. Reconstruct state from git commits OR default to first phase
        3. Initialize state.json with reconstructed data
        4. Return state
        """
        if not self.state_file.exists():
            # Auto-recover: Create empty state file
            self._save_state_file({})
        
        states = self._load_state_file()
        
        if branch not in states:
            # Auto-recover: Reconstruct missing branch state
            state = self._reconstruct_branch_state(branch)
            self._save_state(branch, state)
            return state
        
        return states[branch]
    
    def _reconstruct_branch_state(self, branch: str) -> dict[str, Any]:
        """Reconstruct state from projects.json + git history."""
        # 1. Extract issue number from branch name
        issue_number = self._extract_issue_number(branch)
        
        # 2. Get project plan
        project = self.project_manager.get_project_plan(issue_number)
        if not project:
            raise ValueError(f"No project plan for branch {branch}")
        
        # 3. Reconstruct current phase from git
        current_phase = self._infer_phase_from_git(branch, project)
        
        # 4. Create state
        return {
            "branch": branch,
            "issue_number": issue_number,
            "workflow_name": project["workflow_name"],
            "current_phase": current_phase,
            "transitions": [],  # Lost - can't reconstruct history
            "created_at": datetime.now(UTC).isoformat(),
            "reconstructed": True  # Flag for debugging
        }
```

**Benefits:**
- ✅ Transparent to users (auto-recovers)
- ✅ Works on machine switch automatically
- ✅ No manual intervention required

**Limitations:**
- ❌ Transition history lost (empty transitions array)
- ⚠️ May guess wrong phase if git history unclear

---

### Option 3: Explicit Sync Tool

**Strategy:** Provide `sync_state` tool to manually reconstruct

```python
class SyncStateTool(BaseTool):
    """Synchronize state.json from git and projects.json.
    
    Use when:
    - Switching machines
    - state.json accidentally deleted
    - Pulling someone else's branch
    """
    
    async def execute(self) -> ToolResult:
        # 1. Get current branch
        branch = git_manager.get_current_branch()
        
        # 2. Check if state exists
        if phase_engine.has_state(branch):
            return ToolResult.text("State already synchronized")
        
        # 3. Reconstruct state
        state = phase_engine.reconstruct_state(branch)
        
        # 4. Report reconstruction
        return ToolResult.text(
            f"✅ State reconstructed for {branch}\n"
            f"📝 Current phase: {state['current_phase']}\n"
            f"⚠️  Transition history lost (reconstructed from git)"
        )
```

**Benefits:**
- ✅ Explicit user control
- ✅ Clear what happened (reconstruction message)
- ✅ Can be called anytime

**Limitations:**
- ❌ Requires manual invocation
- ❌ User must remember to run it
- ❌ Extra cognitive overhead

---

### Option 4: State in Git (Alternative Approach)

**Strategy:** Keep state.json in git, accept merge conflicts

**Structure Change:**
```json
{
  "branches": {
    "fix/39-initialize-project-tool": {
      "workflow_name": "bug",
      "required_phases": ["research", "planning", "tdd"],
      "current_phase": "planning",
      "last_updated_by": "Machine-A",
      "last_updated_at": "2025-12-30T..."
    }
  }
}
```

**Merge Conflict Resolution:**
```
Machine A: current_phase = "planning"
Machine B: current_phase = "tdd"
    ↓
Git merge conflict
    ↓
Resolve: Take latest timestamp or merge transitions
```

**Benefits:**
- ✅ True SSOT in git
- ✅ No reconstruction needed
- ✅ Full audit trail preserved

**Limitations:**
- ❌ Merge conflicts on multi-machine work
- ❌ Pollutes git history with state changes
- ❌ Not truly "runtime state" anymore

**Verdict:** ❌ Rejected - Violates principle that state.json is runtime, not source

---

## Recommended Approach: Hybrid (Option 1 + 2)

**Primary:** PhaseStateEngine auto-recovery (Option 2)  
**Fallback:** Git commit message inference (Option 1)

### Implementation Plan

**1. PhaseStateEngine.get_state() Enhancement**
```python
def get_state(self, branch: str) -> dict[str, Any]:
    """Get branch state with transparent auto-recovery."""
    # Load state file (create if missing)
    states = self._load_or_create_state_file()
    
    # Check if branch exists in state
    if branch not in states:
        logger.info(f"State not found for {branch}, reconstructing...")
        state = self._reconstruct_branch_state(branch)
        self._save_state(branch, state)
        return state
    
    return states[branch]
```

**2. Reconstruction Logic**
```python
def _reconstruct_branch_state(self, branch: str) -> dict[str, Any]:
    """Reconstruct state from projects.json + git history."""
    # Extract issue number from branch
    issue_number = self._parse_issue_from_branch(branch)
    
    # Get project plan (SSOT for workflow)
    project = self.project_manager.get_project_plan(issue_number)
    if not project:
        raise ValueError(f"Project plan not found for issue {issue_number}")
    
    # Infer current phase from git commits
    current_phase = self._infer_phase_from_commits(
        branch=branch,
        workflow_phases=project["required_phases"]
    )
    
    return {
        "branch": branch,
        "issue_number": issue_number,
        "workflow_name": project["workflow_name"],
        "current_phase": current_phase,
        "transitions": [],  # Cannot reconstruct
        "created_at": datetime.now(UTC).isoformat(),
        "reconstructed": True
    }

def _infer_phase_from_commits(
    self, branch: str, workflow_phases: list[str]
) -> str:
    """Infer current phase from git commit messages.
    
    Algorithm:
    1. Get commits on current branch
    2. Find most recent commit containing phase keyword
    3. Return that phase
    4. If no phase found, return first phase (safe default)
    """
    try:
        # Get recent commits on this branch
        commits = self.git_adapter.get_commits(branch, limit=50)
        
        # Search commits in reverse chronological order
        for commit in commits:
            message = commit.message.lower()
            
            # Check each phase in reverse order (later phases first)
            for phase in reversed(workflow_phases):
                if phase in message:
                    logger.info(f"Inferred phase '{phase}' from commit: {commit.sha[:7]}")
                    return phase
        
        # No phase found in commits, default to first phase
        logger.warning(f"No phase commits found for {branch}, defaulting to first phase")
        return workflow_phases[0]
        
    except Exception as e:
        logger.warning(f"Could not infer phase from git: {e}, using first phase")
        return workflow_phases[0]
```

**3. User Experience**
```
Machine B pulls code
    ↓
User calls: transition_phase(to="integration")
    ↓
PhaseStateEngine.get_state(branch)
    ↓
State not found → Auto-reconstruct
    ↓
[INFO] State reconstructed for fix/39-initialize-project-tool
[INFO] Inferred phase 'planning' from commit 456514d
    ↓
Validate transition: planning → integration
    ↓
✅ Transition successful
```

**4. Edge Cases**

**Case 1: Mid-phase work (uncommitted)**
- Git shows: Last commit = "Complete research phase"
- Actual: Developer halfway through planning
- Reconstruction: Returns "research" (last committed phase)
- Impact: Developer must transition to planning again (idempotent, safe)

**Case 2: No phase commits yet**
- Git shows: No commits with phase keywords
- Reconstruction: Returns first phase from workflow ("research")
- Impact: Correct - project just started

**Case 3: Branch name parsing fails**
- Branch: "feature/weird-name-no-number"
- Error: Cannot extract issue number
- Fallback: Prompt user to call initialize_project manually

**Case 4: Projects.json missing**
- State.json exists but projects.json doesn't
- Error: "Project plan not found, run initialize_project first"
- Impact: User must initialize (correct behavior)

---

## Benefits of Hybrid Approach

**Transparency:**
- ✅ Auto-recovery happens transparently
- ✅ Logging shows what happened
- ✅ No user action required

**Correctness:**
- ✅ Git commits are SSOT for completed phases
- ✅ Projects.json is SSOT for workflow definition
- ✅ Safe defaults when inference fails

**Robustness:**
- ✅ Works across machines automatically
- ✅ Handles missing state.json gracefully
- ✅ Degrades gracefully (defaults to first phase)

**Tradeoffs:**
- ⚠️ Transition history lost (empty array after reconstruction)
- ⚠️ May be "behind" if mid-phase work uncommitted
- ⚠️ Requires commit message conventions (docs phase, tdd phase, etc.)

---

## Implementation Checklist

### Phase State Engine Updates
- [ ] Add `_reconstruct_branch_state()` method
- [ ] Add `_infer_phase_from_commits()` method
- [ ] Add `_parse_issue_from_branch()` method
- [ ] Modify `get_state()` to auto-recover
- [ ] Add logging for reconstruction events
- [ ] Add `reconstructed` flag to state dict

### Git Adapter Updates
- [ ] Add `get_commits(branch, limit)` method (if not exists)
- [ ] Return commit objects with message and sha

### Testing
- [ ] Test reconstruction from clean checkout
- [ ] Test phase inference from commit messages
- [ ] Test default to first phase when no commits
- [ ] Test error handling (invalid branch name, missing projects.json)
- [ ] Test idempotent reconstruction (calling twice)

### Documentation
- [ ] Document reconstruction behavior in README
- [ ] Add troubleshooting guide for state sync
- [ ] Document commit message conventions

---

## Alternative: Pre-flight Check (Rejected)

**Idea:** Tools check state.json existence and prompt before operations

```python
def transition_phase(...):
    if not state_exists(branch):
        return ToolResult.error(
            "State not initialized. Run sync_state or initialize_project first."
        )
```

**Rejected because:**
- ❌ Requires manual user action
- ❌ Breaks workflow (extra step)
- ❌ Auto-recovery is better UX

---

## Conclusion

**Recommendation:** Implement **Hybrid Auto-Recovery** (Option 1 + 2)

**Rationale:**
1. Git is SSOT for completed work (commit messages)
2. Projects.json is SSOT for workflow definition
3. State.json is ephemeral runtime cache
4. Auto-recovery provides best UX
5. Graceful degradation when inference fails

**Trade-off Accepted:**
- Transition history lost after reconstruction
- May require re-transitioning if mid-phase
- These are acceptable for improved cross-machine DX

**Next Step:** Add this to Issue #39 scope in planning phase
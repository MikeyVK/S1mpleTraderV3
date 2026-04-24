# Issue #79 Planning: Parent Branch Tracking Implementation

**Date:** 2026-01-03  
**Branch:** feature/79-parent-branch-tracking  
**Phase:** Planning  
**Parent Branch:** epic/76-quality-gates-tooling  
**Selected Architecture:** Option A - projects.json storage with auto-recovery

---

## Executive Summary

Implementation plan for adding `parent_branch` tracking to state management system. Will store parent_branch in projects.json (IN git) and reconstruct to state.json (local cache) using existing auto-recovery infrastructure.

**Key Decision:** Use projects.json as SSOT for parent_branch to enable cross-machine synchronization.

---

## Architecture Decision: Option A - projects.json Storage

### Rationale

1. **projects.json already in git** ✅
   - Survives machine switches
   - Already part of auto-recovery flow
   - No new files needed

2. **Follows existing patterns** ✅
   - workflow_name already stored in projects.json
   - Same reconstruction pattern as current_phase
   - Minimal disruption

3. **Project-level makes sense** ✅
   - One parent branch per issue/project
   - Parent branch is decided at project initialization
   - Rare that same project needs multiple parents

### Trade-offs Accepted

- **Project-level not branch-level:** If same issue has multiple branches with different parents, they share one parent in projects.json
- **Mitigation:** State.json can override if needed (manual edge case)

---

## Implementation Plan

### Phase 1: Update projects.json Schema ✅ CRITICAL

**File:** `.st3/projects.json`

**Current Schema:**
```json
{
  "79": {
    "issue_title": "Feature: Add parent_branch tracking to state management",
    "workflow_name": "feature",
    "execution_mode": "interactive",
    "required_phases": ["research", "planning", "design", "tdd", "integration", "documentation"],
    "skip_reason": null,
    "created_at": "2026-01-03T14:10:37.070163+00:00"
  }
}
```

**New Schema:**
```json
{
  "79": {
    "issue_title": "Feature: Add parent_branch tracking to state management",
    "workflow_name": "feature",
    "parent_branch": "epic/76-quality-gates-tooling",  // ← NEW FIELD
    "execution_mode": "interactive",
    "required_phases": ["research", "planning", "design", "tdd", "integration", "documentation"],
    "skip_reason": null,
    "created_at": "2026-01-03T14:10:37.070163+00:00"
  }
}
```

**Changes Required:**
- Add `parent_branch: str | None` field
- Optional to maintain backward compatibility
- Default to None for existing projects

---

### Phase 2: Update ProjectManager.initialize_project()

**File:** `mcp_server/managers/project_manager.py`

**Current Method Signature:**
```python
def initialize_project(
    self,
    issue_number: int,
    issue_title: str,
    workflow_name: str,
    options: ProjectInitOptions | None = None
) -> dict[str, Any]:
```

**New Method Signature:**
```python
def initialize_project(
    self,
    issue_number: int,
    issue_title: str,
    workflow_name: str,
    parent_branch: str | None = None,  // ← NEW PARAMETER
    options: ProjectInitOptions | None = None
) -> dict[str, Any]:
```

**Implementation:**
```python
def initialize_project(
    self,
    issue_number: int,
    issue_title: str,
    workflow_name: str,
    parent_branch: str | None = None,
    options: ProjectInitOptions | None = None
) -> dict[str, Any]:
    """Initialize project with workflow definition.
    
    Args:
        issue_number: GitHub issue number
        issue_title: Issue title
        workflow_name: Workflow from workflows.yaml
        parent_branch: Optional parent branch (e.g., 'epic/76-qa-tooling')
        options: Optional custom phases
    """
    # Get workflow
    workflow = workflow_config.get_workflow(workflow_name)
    
    # Build project entry
    project = {
        "issue_title": issue_title,
        "workflow_name": workflow_name,
        "parent_branch": parent_branch,  # ← STORE HERE
        "execution_mode": workflow.execution_mode,
        "required_phases": list(workflow.required_phases),
        "skip_reason": options.skip_reason if options else None,
        "created_at": datetime.now(UTC).isoformat()
    }
    
    # Save to projects.json
    self._save_project(issue_number, project)
    
    return project
```

**Test Coverage:**
- Test with parent_branch provided
- Test with parent_branch=None (backward compat)
- Test retrieval via get_project_plan()

---

### Phase 3: Update InitializeProjectTool

**File:** `mcp_server/tools/project_tools.py`

**Current Input Schema:**
```python
class InitializeProjectInput(BaseModel):
    issue_number: int
    issue_title: str
    workflow_name: str
    custom_phases: tuple[str, ...] | None = None
    skip_reason: str | None = None
```

**New Input Schema:**
```python
class InitializeProjectInput(BaseModel):
    issue_number: int
    issue_title: str
    workflow_name: str
    parent_branch: str | None = Field(
        default=None,
        description=(
            "Parent branch this feature/bug branches from. "
            "If not provided, attempts auto-detection from current branch."
        )
    )  # ← NEW FIELD
    custom_phases: tuple[str, ...] | None = None
    skip_reason: str | None = None
```

**Implementation Strategy:**
```python
async def execute(self, params: InitializeProjectInput) -> ToolResult:
    # Determine parent_branch
    parent_branch = params.parent_branch
    if parent_branch is None:
        # Auto-detect: Use current branch before we switch
        # (initialize_project is called AFTER branch creation)
        # So we need to detect from git reflog or user must provide
        parent_branch = self._detect_parent_branch()
    
    # Initialize project WITH parent_branch
    result = self.manager.initialize_project(
        issue_number=params.issue_number,
        issue_title=params.issue_title,
        workflow_name=params.workflow_name,
        parent_branch=parent_branch,  # ← PASS IT
        options=options
    )
    
    # Rest of initialization...
```

**Auto-Detection Strategy:**

**Option 3a: Git reflog parsing (RECOMMENDED for Phase 1)**
```python
def _detect_parent_branch(self) -> str | None:
    """Detect parent branch from git reflog.
    
    Returns:
        Parent branch name or None if not detectable
    """
    try:
        # Get current branch
        current_branch = self.git_manager.get_current_branch()
        
        # Search reflog for branch creation
        result = subprocess.run(
            ["git", "reflog", "show", "--all"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Pattern: "checkout: moving from <parent> to <current>"
        pattern = f"checkout: moving from (.+) to {re.escape(current_branch)}"
        for line in result.stdout.splitlines():
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        
        return None
    except Exception as e:
        logger.warning("Could not auto-detect parent branch: %s", e)
        return None
```

**Option 3b: Capture in create_branch tool (BETTER, Phase 2)**
- Modify create_branch to return parent_branch in result
- User passes to initialize_project

**Test Coverage:**
- Test with explicit parent_branch
- Test with auto-detection success
- Test with auto-detection failure (None)
- Test backward compatibility (no parent_branch)

---

### Phase 4: Update PhaseStateEngine Auto-Recovery

**File:** `mcp_server/managers/phase_state_engine.py`

**Current _reconstruct_branch_state():**
```python
def _reconstruct_branch_state(self, branch: str) -> dict[str, Any]:
    issue_number = self._extract_issue_from_branch(branch)
    project = self.project_manager.get_project_plan(issue_number)
    current_phase = self._infer_phase_from_git(branch, workflow_phases)
    
    state = {
        "branch": branch,
        "issue_number": issue_number,
        "workflow_name": project["workflow_name"],
        "current_phase": current_phase,
        "transitions": [],
        "created_at": datetime.now(UTC).isoformat(),
        "reconstructed": True
    }
    return state
```

**New _reconstruct_branch_state():**
```python
def _reconstruct_branch_state(self, branch: str) -> dict[str, Any]:
    issue_number = self._extract_issue_from_branch(branch)
    project = self.project_manager.get_project_plan(issue_number)
    current_phase = self._infer_phase_from_git(branch, workflow_phases)
    
    # NEW: Extract parent_branch from project
    parent_branch = project.get("parent_branch")  # ← READ FROM projects.json
    
    state = {
        "branch": branch,
        "issue_number": issue_number,
        "workflow_name": project["workflow_name"],
        "current_phase": current_phase,
        "parent_branch": parent_branch,  # ← ADD TO STATE
        "transitions": [],
        "created_at": datetime.now(UTC).isoformat(),
        "reconstructed": True
    }
    return state
```

**Also Update initialize_branch():**
```python
def initialize_branch(
    self,
    branch: str,
    issue_number: int,
    initial_phase: str,
    parent_branch: str | None = None  # ← NEW PARAMETER
) -> dict[str, Any]:
    """Initialize branch state with parent_branch.
    
    Args:
        branch: Branch name
        issue_number: Issue number
        initial_phase: Starting phase
        parent_branch: Optional parent branch (falls back to project)
    """
    project = self.project_manager.get_project_plan(issue_number)
    
    # Use provided parent_branch OR fallback to project's parent_branch
    if parent_branch is None:
        parent_branch = project.get("parent_branch")
    
    state = {
        "branch": branch,
        "issue_number": issue_number,
        "workflow_name": project["workflow_name"],
        "current_phase": initial_phase,
        "parent_branch": parent_branch,  # ← STORE IN STATE
        "transitions": [],
        "created_at": datetime.now(UTC).isoformat()
    }
    
    self._save_state(branch, state)
    return {"success": True, "branch": branch, "current_phase": initial_phase}
```

**Test Coverage:**
- Test reconstruction with parent_branch in projects.json
- Test reconstruction without parent_branch (None)
- Test initialize_branch with explicit parent_branch
- Test initialize_branch with fallback to projects.json

---

### Phase 5: Update git_checkout Tool Display

**File:** `mcp_server/tools/git_tools.py`

**Current Output:**
```python
return ToolResult.text(
    f"Switched to branch: {params.branch}\n"
    f"Current phase: {current_phase}"
)
```

**New Output:**
```python
state = engine.get_state(params.branch)
current_phase = state.get('current_phase', 'unknown')
parent_branch = state.get('parent_branch')  # ← NEW

output = f"Switched to branch: {params.branch}\n"
output += f"Current phase: {current_phase}"

if parent_branch:
    output += f"\nParent branch: {parent_branch}"  # ← DISPLAY

return ToolResult.text(output)
```

**Test Coverage:**
- Test display with parent_branch present
- Test display with parent_branch=None
- Test display after reconstruction

---

### Phase 6: New Helper Tool - get_parent_branch

**File:** `mcp_server/tools/git_tools.py` OR new `mcp_server/tools/branch_tools.py`

**Purpose:** Retrieve parent_branch for current or specified branch

**Input Schema:**
```python
class GetParentBranchInput(BaseModel):
    branch: str | None = Field(
        default=None,
        description="Branch name (defaults to current branch)"
    )
```

**Implementation:**
```python
class GetParentBranchTool(BaseTool):
    """Tool to get parent branch for a branch."""
    
    name = "get_parent_branch"
    description = "Get the parent branch that a feature/bug branch was created from"
    args_model = GetParentBranchInput
    
    async def execute(self, params: GetParentBranchInput) -> ToolResult:
        branch = params.branch
        if branch is None:
            branch = GitManager().get_current_branch()
        
        # Get state (triggers auto-recovery if needed)
        workspace_root = Path.cwd()
        project_manager = ProjectManager(workspace_root=workspace_root)
        engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=project_manager
        )
        
        state = engine.get_state(branch)
        parent_branch = state.get('parent_branch')
        
        if parent_branch:
            return ToolResult.text(
                f"Branch: {branch}\n"
                f"Parent: {parent_branch}"
            )
        else:
            return ToolResult.text(
                f"Branch: {branch}\n"
                f"Parent: unknown (not set during initialization)"
            )
```

**Test Coverage:**
- Test with current branch
- Test with specified branch
- Test with parent_branch set
- Test with parent_branch=None

---

### Phase 7: Migration Strategy for Existing Projects

**Goal:** Handle projects.json entries without parent_branch field

**Strategy:**

1. **Graceful Degradation:**
   ```python
   parent_branch = project.get("parent_branch")  # Returns None if missing
   ```

2. **Optional Backfill Tool:**
   ```python
   class BackfillParentBranchInput(BaseModel):
       issue_number: int
       parent_branch: str
   
   class BackfillParentBranchTool(BaseTool):
       """Backfill parent_branch for existing projects."""
       
       async def execute(self, params: BackfillParentBranchInput) -> ToolResult:
           # Update projects.json
           project = self.project_manager.get_project_plan(params.issue_number)
           project["parent_branch"] = params.parent_branch
           self.project_manager._save_project(params.issue_number, project)
           
           return ToolResult.text(
               f"Updated issue {params.issue_number} with parent_branch: {params.parent_branch}"
           )
   ```

3. **Git Reflog Fallback:**
   - If parent_branch is None in projects.json
   - Try git reflog detection as last resort
   - Log warning if unsuccessful

---

## Data Flow Diagrams

### New Flow with parent_branch:

```
1. User creates branch:
   ┌──────────────────┐
   │  create_branch   │
   │  base="epic/76"  │
   └────────┬─────────┘
            │
            ↓ (captures current branch before switch)
   ┌──────────────────┐
   │ Current: epic/76 │  ← Parent captured
   └────────┬─────────┘
            │
            ↓ git checkout -b feature/79 epic/76
   ┌──────────────────┐
   │ New: feature/79  │
   └────────┬─────────┘
            │
            ↓

2. User initializes project:
   ┌────────────────────────┐
   │  initialize_project    │
   │  parent_branch=epic/76 │
   └────────┬───────────────┘
            │
            ↓
   ┌────────────────────────┐
   │  ProjectManager        │
   │  .initialize_project() │
   └────────┬───────────────┘
            │
            ↓
   ┌─────────────────────────────────┐
   │  projects.json (IN GIT)         │
   │  {                               │
   │    "79": {                       │
   │      "parent_branch": "epic/76"  │  ← STORED
   │    }                             │
   │  }                               │
   └────────┬────────────────────────┘
            │
            ↓
   ┌────────────────────────┐
   │  PhaseStateEngine      │
   │  .initialize_branch()  │
   └────────┬───────────────┘
            │
            ↓
   ┌─────────────────────────────────┐
   │  state.json (LOCAL CACHE)       │
   │  {                               │
   │    "feature/79": {               │
   │      "parent_branch": "epic/76"  │  ← CACHED
   │    }                             │
   │  }                               │
   └─────────────────────────────────┘

3. Cross-machine scenario:
   Machine B:
   ┌──────────────────┐
   │  git checkout    │
   │  feature/79      │
   └────────┬─────────┘
            │
            ↓
   ┌──────────────────────────┐
   │  state.json missing!     │
   └────────┬─────────────────┘
            │
            ↓
   ┌────────────────────────────┐
   │  PhaseStateEngine          │
   │  .get_state(feature/79)    │
   └────────┬───────────────────┘
            │
            ↓ Branch not in state.json
   ┌────────────────────────────┐
   │  ._reconstruct_branch      │
   │  _state()                  │
   └────────┬───────────────────┘
            │
            ↓
   ┌─────────────────────────────────┐
   │  Read projects.json (IN GIT)    │
   │  {                               │
   │    "79": {                       │
   │      "parent_branch": "epic/76"  │  ← SSOT
   │    }                             │
   │  }                               │
   └────────┬────────────────────────┘
            │
            ↓
   ┌─────────────────────────────────┐
   │  state.json RECONSTRUCTED       │
   │  {                               │
   │    "feature/79": {               │
   │      "parent_branch": "epic/76"  │  ← FROM projects.json
   │      "reconstructed": true       │
   │    }                             │
   │  }                               │
   └─────────────────────────────────┘
```

---

## Testing Strategy

### Unit Tests

1. **ProjectManager:**
   - `test_initialize_project_with_parent_branch()`
   - `test_initialize_project_without_parent_branch()`
   - `test_get_project_plan_returns_parent_branch()`

2. **PhaseStateEngine:**
   - `test_initialize_branch_with_parent_branch()`
   - `test_reconstruct_includes_parent_branch()`
   - `test_reconstruct_handles_missing_parent_branch()`

3. **InitializeProjectTool:**
   - `test_with_explicit_parent_branch()`
   - `test_with_auto_detection()`
   - `test_backward_compatibility()`

4. **GetParentBranchTool:**
   - `test_get_parent_for_current_branch()`
   - `test_get_parent_for_specified_branch()`
   - `test_handle_missing_parent()`

### Integration Tests

1. **Full Workflow:**
   - Create branch → Initialize project → Verify parent in projects.json
   - Checkout branch → Verify parent in state.json
   - Delete state.json → Checkout → Verify reconstruction

2. **Cross-Machine Simulation:**
   - Create project on "Machine A" with parent
   - Delete state.json (simulate machine switch)
   - Reconstruct state
   - Verify parent_branch present

### Edge Cases

1. Parent branch doesn't exist anymore
2. Multiple branches for same issue
3. Circular parent references
4. Invalid branch names
5. Migration from old projects without parent_branch

---

## Implementation Order

**Phase 1: Core Infrastructure** (2-3 hours)
1. Update projects.json schema
2. Update ProjectManager.initialize_project()
3. Update PhaseStateEngine.initialize_branch()
4. Update PhaseStateEngine._reconstruct_branch_state()
5. Unit tests for above

**Phase 2: Tool Integration** (1-2 hours)
6. Update InitializeProjectTool
7. Update git_checkout display
8. Add GetParentBranchTool
9. Integration tests

**Phase 3: Migration & Polish** (1 hour)
10. Add parent_branch detection helper
11. Test backward compatibility
12. Update documentation

**Total Estimate:** 4-6 hours

---

## Success Criteria

✅ parent_branch stored in projects.json  
✅ parent_branch cached in state.json  
✅ Auto-recovery reconstructs parent_branch from projects.json  
✅ git_checkout displays parent_branch  
✅ get_parent_branch tool works  
✅ Cross-machine scenario tested and working  
✅ Backward compatibility with existing projects  
✅ All tests passing (unit + integration)  
✅ Documentation updated  

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Projects.json becomes bloated | Low | Parent branch is small string, negligible |
| Same issue, multiple parents | Medium | Document as known limitation, state.json can override |
| Git reflog auto-detection fails | Low | Make parent_branch optional, None is valid |
| Breaking existing tooling | High | Thorough testing, optional field, backward compat |

---

## Next Phase: Design

After planning approval, move to design phase to create:
- Detailed class diagrams
- Sequence diagrams
- API specifications
- Error handling strategies

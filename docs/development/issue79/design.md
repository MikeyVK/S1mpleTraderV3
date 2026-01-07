# Issue #79 Design: Parent Branch Tracking Technical Specification

**Date:** 2026-01-03  
**Branch:** feature/79-parent-branch-tracking  
**Phase:** Design  
**Parent Branch:** epic/76-quality-gates-tooling  

---

## Table of Contents

1. [Data Models](#data-models)
2. [API Specifications](#api-specifications)
3. [Implementation Details](#implementation-details)
4. [Error Handling](#error-handling)
5. [Testing Strategy](#testing-strategy)
6. [Migration Plan](#migration-plan)

---

## Data Models

### 1. projects.json Schema Extension

**Location:** `.st3/projects.json`

**Type Definition:**
```python
class ProjectPlan(TypedDict):
    """Project plan stored in projects.json."""
    issue_title: str
    workflow_name: str
    parent_branch: str | None  # NEW - optional for backward compat
    execution_mode: str
    required_phases: list[str]
    skip_reason: str | None
    created_at: str
```

**JSON Schema:**
```json
{
  "type": "object",
  "patternProperties": {
    "^[0-9]+$": {
      "type": "object",
      "properties": {
        "issue_title": {"type": "string"},
        "workflow_name": {"type": "string"},
        "parent_branch": {"type": ["string", "null"]},
        "execution_mode": {"type": "string"},
        "required_phases": {
          "type": "array",
          "items": {"type": "string"}
        },
        "skip_reason": {"type": ["string", "null"]},
        "created_at": {"type": "string", "format": "date-time"}
      },
      "required": [
        "issue_title",
        "workflow_name",
        "execution_mode",
        "required_phases",
        "created_at"
      ]
    }
  }
}
```

**Example:**
```json
{
  "79": {
    "issue_title": "Feature: Add parent_branch tracking to state management",
    "workflow_name": "feature",
    "parent_branch": "epic/76-quality-gates-tooling",
    "execution_mode": "interactive",
    "required_phases": ["research", "planning", "design", "tdd", "integration", "documentation"],
    "skip_reason": null,
    "created_at": "2026-01-03T14:10:37.070163+00:00"
  }
}
```

### 2. state.json Schema Extension

**Location:** `.st3/state.json`

**Type Definition:**
```python
class BranchState(TypedDict):
    """Branch state stored in state.json."""
    branch: str
    issue_number: int
    workflow_name: str
    current_phase: str
    parent_branch: str | None  # NEW - optional
    transitions: list[dict[str, Any]]
    created_at: str
    reconstructed: bool | None  # Only present when auto-recovered
```

**Example:**
```json
{
  "feature/79-parent-branch-tracking": {
    "branch": "feature/79-parent-branch-tracking",
    "issue_number": 79,
    "workflow_name": "feature",
    "current_phase": "design",
    "parent_branch": "epic/76-quality-gates-tooling",
    "transitions": [
      {
        "from_phase": "research",
        "to_phase": "planning",
        "timestamp": "2026-01-03T14:25:00.000000+00:00",
        "human_approval": null,
        "forced": false,
        "skip_reason": null
      }
    ],
    "created_at": "2026-01-03T14:10:37.070163+00:00"
  }
}
```

---

## API Specifications

### 1. ProjectManager.initialize_project()

**File:** `mcp_server/managers/project_manager.py`

**Signature:**
```python
def initialize_project(
    self,
    issue_number: int,
    issue_title: str,
    workflow_name: str,
    parent_branch: str | None = None,
    options: ProjectInitOptions | None = None
) -> dict[str, Any]:
    """Initialize project with workflow definition and parent branch.
    
    Args:
        issue_number: GitHub issue number (e.g., 79)
        issue_title: Issue title for documentation
        workflow_name: Workflow from workflows.yaml (feature/bug/docs/etc)
        parent_branch: Parent branch this was created from (e.g., 'epic/76-qa')
                      Optional - will be None for existing projects
        options: Optional custom phases configuration
    
    Returns:
        dict containing:
            - issue_title: str
            - workflow_name: str
            - parent_branch: str | None
            - execution_mode: str
            - required_phases: list[str]
            - skip_reason: str | None
    
    Raises:
        ValueError: If workflow_name not found in workflows.yaml
    
    Example:
        >>> manager.initialize_project(
        ...     issue_number=79,
        ...     issue_title="Add parent_branch tracking",
        ...     workflow_name="feature",
        ...     parent_branch="epic/76-quality-gates-tooling"
        ... )
        {
            'issue_title': 'Add parent_branch tracking',
            'workflow_name': 'feature',
            'parent_branch': 'epic/76-quality-gates-tooling',
            'execution_mode': 'interactive',
            'required_phases': ['research', 'planning', 'design', 'tdd', ...]
        }
    """
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
    # Validate workflow exists
    workflow = workflow_config.get_workflow(workflow_name)
    
    # Handle custom phases
    if options and options.custom_phases:
        required_phases = list(options.custom_phases)
        skip_reason = options.skip_reason
    else:
        required_phases = list(workflow.required_phases)
        skip_reason = None
    
    # Build project entry with parent_branch
    project = {
        "issue_title": issue_title,
        "workflow_name": workflow_name,
        "parent_branch": parent_branch,  # Store (can be None)
        "execution_mode": workflow.execution_mode,
        "required_phases": required_phases,
        "skip_reason": skip_reason,
        "created_at": datetime.now(UTC).isoformat()
    }
    
    # Save to projects.json
    self._save_project(issue_number, project)
    
    logger.info(
        "Initialized project %s with parent_branch=%s",
        issue_number, parent_branch
    )
    
    return project
```

### 2. PhaseStateEngine.initialize_branch()

**File:** `mcp_server/managers/phase_state_engine.py`

**Signature:**
```python
def initialize_branch(
    self,
    branch: str,
    issue_number: int,
    initial_phase: str,
    parent_branch: str | None = None
) -> dict[str, Any]:
    """Initialize branch state with parent branch tracking.
    
    Args:
        branch: Branch name (e.g., 'feature/79-parent-tracking')
        issue_number: GitHub issue number
        initial_phase: Starting phase (e.g., 'research')
        parent_branch: Optional parent branch - if None, reads from projects.json
    
    Returns:
        dict with:
            - success: bool
            - branch: str
            - current_phase: str
            - parent_branch: str | None
    
    Raises:
        ValueError: If project not found in projects.json
    
    Example:
        >>> engine.initialize_branch(
        ...     branch="feature/79-test",
        ...     issue_number=79,
        ...     initial_phase="research",
        ...     parent_branch="epic/76-qa"
        ... )
        {
            'success': True,
            'branch': 'feature/79-test',
            'current_phase': 'research',
            'parent_branch': 'epic/76-qa'
        }
    """
```

**Implementation:**
```python
def initialize_branch(
    self,
    branch: str,
    issue_number: int,
    initial_phase: str,
    parent_branch: str | None = None
) -> dict[str, Any]:
    # Get project plan (SSOT for workflow)
    project = self.project_manager.get_project_plan(issue_number)
    if not project:
        msg = f"Project {issue_number} not found. Initialize project first."
        raise ValueError(msg)
    
    # Determine parent_branch:
    # 1. Use explicit parameter if provided
    # 2. Otherwise use project's parent_branch (from projects.json)
    if parent_branch is None:
        parent_branch = project.get("parent_branch")
    
    # Create initial state
    state: dict[str, Any] = {
        "branch": branch,
        "issue_number": issue_number,
        "workflow_name": project["workflow_name"],
        "current_phase": initial_phase,
        "parent_branch": parent_branch,  # Store (can be None)
        "transitions": [],
        "created_at": datetime.now(UTC).isoformat()
    }
    
    # Save state
    self._save_state(branch, state)
    
    logger.info(
        "Initialized branch %s with parent_branch=%s",
        branch, parent_branch
    )
    
    return {
        "success": True,
        "branch": branch,
        "current_phase": initial_phase,
        "parent_branch": parent_branch
    }
```

### 3. PhaseStateEngine._reconstruct_branch_state()

**File:** `mcp_server/managers/phase_state_engine.py`

**Modifications:**
```python
def _reconstruct_branch_state(self, branch: str) -> dict[str, Any]:
    """Reconstruct branch state from projects.json + git commits.
    
    Mode 2: Cross-machine scenario - state.json missing after git pull.
    NOW INCLUDES parent_branch reconstruction from projects.json.
    
    Args:
        branch: Branch name (e.g., 'fix/39-test')
    
    Returns:
        Reconstructed state dict with:
            - branch: str
            - issue_number: int
            - workflow_name: str
            - current_phase: str (inferred from git)
            - parent_branch: str | None (from projects.json)
            - transitions: list (empty - cannot reconstruct)
            - created_at: str
            - reconstructed: bool (always True)
    
    Raises:
        ValueError: If branch format invalid or project not found
    """
    logger.info("Reconstructing state for branch '%s'...", branch)
    
    # Step 1: Extract issue number from branch
    issue_number = self._extract_issue_from_branch(branch)
    
    # Step 2: Get project plan (SSOT for workflow AND parent_branch)
    project = self.project_manager.get_project_plan(issue_number)
    if not project:
        msg = f"Project plan not found for issue {issue_number}"
        raise ValueError(msg)
    
    # Step 3: Infer current phase from git commits
    workflow_phases = project["required_phases"]
    current_phase = self._infer_phase_from_git(branch, workflow_phases)
    
    # Step 4: Extract parent_branch from project (NEW)
    parent_branch = project.get("parent_branch")
    
    # Step 5: Create reconstructed state
    state: dict[str, Any] = {
        "branch": branch,
        "issue_number": issue_number,
        "workflow_name": project["workflow_name"],
        "current_phase": current_phase,
        "parent_branch": parent_branch,  # NEW - from projects.json
        "transitions": [],  # Cannot reconstruct history
        "created_at": datetime.now(UTC).isoformat(),
        "reconstructed": True  # Audit flag
    }
    
    logger.info(
        "Reconstructed state: issue=%s, phase=%s, workflow=%s, parent=%s",
        issue_number, current_phase, project["workflow_name"], parent_branch
    )
    
    return state
```

### 4. InitializeProjectTool with Auto-Detection

**File:** `mcp_server/tools/project_tools.py`

**Input Schema Update:**
```python
class InitializeProjectInput(BaseModel):
    """Input for initialize_project tool."""
    
    issue_number: int = Field(..., description="GitHub issue number")
    issue_title: str = Field(..., description="Issue title")
    workflow_name: str = Field(
        ...,
        description="Workflow from workflows.yaml: feature/bug/docs/refactor/hotfix/custom"
    )
    parent_branch: str | None = Field(
        default=None,
        description=(
            "Parent branch this feature/bug branches from. "
            "If not provided, attempts auto-detection from git reflog. "
            "Example: 'epic/76-quality-gates-tooling'"
        )
    )
    custom_phases: tuple[str, ...] | None = Field(
        default=None,
        description="Custom phase list (required if workflow_name=custom)"
    )
    skip_reason: str | None = Field(
        default=None,
        description="Reason for custom phases"
    )
```

**Auto-Detection Helper:**
```python
def _detect_parent_branch_from_reflog(self, current_branch: str) -> str | None:
    """Detect parent branch from git reflog.
    
    Searches reflog for "checkout: moving from <parent> to <current>"
    
    Args:
        current_branch: Current branch name
    
    Returns:
        Parent branch name or None if not detectable
    
    Example:
        >>> _detect_parent_branch_from_reflog("feature/79-test")
        'epic/76-quality-gates-tooling'
    """
    try:
        # Get reflog output
        result = subprocess.run(
            ["git", "reflog", "show", "--all"],
            cwd=self.workspace_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10
        )
        
        # Pattern: "checkout: moving from <parent> to <current>"
        pattern = f"checkout: moving from (.+?) to {re.escape(current_branch)}"
        
        # Search most recent first
        for line in result.stdout.splitlines():
            match = re.search(pattern, line)
            if match:
                parent = match.group(1)
                logger.info("Detected parent branch from reflog: %s", parent)
                return parent
        
        logger.warning("No parent branch found in reflog for %s", current_branch)
        return None
        
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.warning("Git reflog failed: %s", e)
        return None
```

**Updated execute() Method:**
```python
async def execute(self, params: InitializeProjectInput) -> ToolResult:
    """Execute project initialization with parent branch tracking."""
    try:
        # Determine parent_branch
        parent_branch = params.parent_branch
        
        if parent_branch is None:
            # Auto-detect from git reflog
            current_branch = self.git_manager.get_current_branch()
            parent_branch = self._detect_parent_branch_from_reflog(current_branch)
            
            if parent_branch:
                logger.info(
                    "Auto-detected parent_branch: %s for %s",
                    parent_branch, current_branch
                )
        
        # Step 1: Create projects.json (with parent_branch)
        options = None
        if params.custom_phases or params.skip_reason:
            options = ProjectInitOptions(
                custom_phases=params.custom_phases,
                skip_reason=params.skip_reason
            )
        
        result = self.manager.initialize_project(
            issue_number=params.issue_number,
            issue_title=params.issue_title,
            workflow_name=params.workflow_name,
            parent_branch=parent_branch,  # Pass through
            options=options
        )
        
        # Step 2: Get current branch from git
        branch = self.git_manager.get_current_branch()
        
        # Step 3: Determine first phase from workflow
        first_phase = result["required_phases"][0]
        
        # Step 4: Initialize branch state (inherits parent from project)
        self.state_engine.initialize_branch(
            branch=branch,
            issue_number=params.issue_number,
            initial_phase=first_phase
            # parent_branch inherits from project automatically
        )
        
        # Step 5: Build success message
        success_message = {
            "success": True,
            "issue_number": params.issue_number,
            "workflow_name": params.workflow_name,
            "branch": branch,
            "initial_phase": first_phase,
            "parent_branch": parent_branch,  # Include in output
            "required_phases": result["required_phases"],
            "execution_mode": result["execution_mode"],
            "files_created": [
                ".st3/projects.json (workflow definition)",
                ".st3/state.json (branch state)"
            ]
        }
        
        if result["workflow_name"] == "custom":
            success_message["description"] = (
                f"Custom workflow with {len(result['required_phases'])} phases"
            )
        else:
            success_message["description"] = workflow_config.get_workflow(
                result["workflow_name"]
            ).description
        
        return ToolResult.json(success_message)
        
    except ValueError as e:
        return ToolResult.error(str(e))
```

### 5. GetParentBranchTool (New)

**File:** `mcp_server/tools/branch_tools.py` (NEW FILE)

**Full Implementation:**
```python
"""Branch metadata tools."""
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from mcp_server.managers.git_manager import GitManager
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager
from mcp_server.tools.base import BaseTool, ToolResult


class GetParentBranchInput(BaseModel):
    """Input for get_parent_branch tool."""
    
    branch: str | None = Field(
        default=None,
        description="Branch name (defaults to current branch if not specified)"
    )


class GetParentBranchTool(BaseTool):
    """Tool to get the parent branch for a feature/bug branch.
    
    Retrieves parent_branch from state.json (triggers auto-recovery if needed).
    Useful for determining merge targets and understanding branch relationships.
    """
    
    name = "get_parent_branch"
    description = (
        "Get the parent branch that a feature/bug branch was created from. "
        "Returns the parent branch name or indicates if not set."
    )
    args_model = GetParentBranchInput
    
    def __init__(self, workspace_root: Path | str):
        """Initialize tool.
        
        Args:
            workspace_root: Path to workspace root directory
        """
        super().__init__()
        self.workspace_root = Path(workspace_root)
        self.git_manager = GitManager()
    
    @property
    def input_schema(self) -> dict[str, Any]:
        return GetParentBranchInput.model_json_schema()
    
    async def execute(self, params: GetParentBranchInput) -> ToolResult:
        """Execute get_parent_branch.
        
        Args:
            params: Input with optional branch name
        
        Returns:
            ToolResult with parent branch info or error
        """
        try:
            # Determine target branch
            branch = params.branch
            if branch is None:
                branch = self.git_manager.get_current_branch()
            
            # Get state (triggers auto-recovery if needed)
            project_manager = ProjectManager(workspace_root=self.workspace_root)
            engine = PhaseStateEngine(
                workspace_root=self.workspace_root,
                project_manager=project_manager
            )
            
            state = engine.get_state(branch)
            parent_branch = state.get('parent_branch')
            issue_number = state.get('issue_number')
            
            # Build response
            if parent_branch:
                return ToolResult.text(
                    f"Branch: {branch}\n"
                    f"Parent: {parent_branch}\n"
                    f"Issue: #{issue_number}"
                )
            else:
                return ToolResult.text(
                    f"Branch: {branch}\n"
                    f"Parent: (not set during initialization)\n"
                    f"Issue: #{issue_number}\n"
                    f"\n"
                    f"Hint: parent_branch was not provided when project was initialized."
                )
                
        except ValueError as e:
            return ToolResult.error(f"Could not get parent branch: {e}")
```

### 6. git_checkout Display Update

**File:** `mcp_server/tools/git_tools.py`

**Updated execute() Method:**
```python
async def execute(self, params: GitCheckoutInput) -> ToolResult:
    # 1. Switch branch
    self.manager.checkout(params.branch)
    
    # 2. Try to sync PhaseStateEngine state
    from pathlib import Path
    from mcp_server.managers.phase_state_engine import PhaseStateEngine
    from mcp_server.managers.project_manager import ProjectManager
    
    try:
        workspace_root = Path.cwd()
        project_manager = ProjectManager(workspace_root=workspace_root)
        engine = PhaseStateEngine(
            workspace_root=workspace_root,
            project_manager=project_manager
        )
        state = engine.get_state(params.branch)
        
        # Extract state info
        current_phase = state.get('current_phase', 'unknown')
        parent_branch = state.get('parent_branch')  # NEW
        reconstructed = state.get('reconstructed', False)
        
        # Build output
        output = f"Switched to branch: {params.branch}\n"
        output += f"Current phase: {current_phase}"
        
        if parent_branch:
            output += f"\nParent branch: {parent_branch}"  # NEW
        
        if reconstructed:
            output += "\n(State reconstructed from git)"
        
        return ToolResult.text(output)
        
    except Exception as e:
        logger.warning(
            "Branch switched but state sync failed",
            extra={"props": {"branch": params.branch, "error": str(e)}}
        )
        return ToolResult.text(
            f"Switched to branch: {params.branch}\n"
            f"(State sync unavailable: {str(e)})"
        )
```

---

## Error Handling

### 1. Missing projects.json Entry

**Scenario:** Branch exists but no project initialized

**Handling:**
```python
# In _reconstruct_branch_state()
project = self.project_manager.get_project_plan(issue_number)
if not project:
    msg = f"Project plan not found for issue {issue_number}"
    raise ValueError(msg)  # Caught by error_handler decorator
```

**User Impact:** Clear error message directing to initialize project first

### 2. Invalid Branch Name Format

**Scenario:** Branch doesn't match pattern `<type>/<number>-<title>`

**Handling:**
```python
# In _extract_issue_from_branch()
match = re.match(r'^(?:feature|fix|bug|docs|refactor|hotfix)/(\d+)-', branch)
if not match:
    msg = f"Cannot extract issue number from branch '{branch}'. "
    msg += "Expected format: <type>/<number>-<title>"
    raise ValueError(msg)
```

**User Impact:** Informative error about expected branch naming

### 3. Git Reflog Auto-Detection Failure

**Scenario:** Cannot detect parent from reflog

**Handling:**
```python
parent_branch = self._detect_parent_branch_from_reflog(current_branch)
if parent_branch is None:
    logger.info("Could not auto-detect parent branch, will be None")
    # Continue with parent_branch=None (valid state)
```

**User Impact:** parent_branch will be None, can be manually set later

### 4. Parent Branch Doesn't Exist Anymore

**Scenario:** Stored parent branch was deleted

**Handling:**
- Store string value, don't validate existence
- Let git operations fail naturally if user tries to merge
- get_parent_branch returns stored value regardless

**User Impact:** User gets parent name, can manually handle if gone

---

## Testing Strategy

### Unit Tests

**File:** `tests/unit/mcp_server/managers/test_project_manager_parent_branch.py`

```python
"""Unit tests for parent_branch in ProjectManager."""
import pytest
from mcp_server.managers.project_manager import ProjectManager


class TestProjectManagerParentBranch:
    """Test parent_branch functionality in ProjectManager."""
    
    def test_initialize_project_with_parent_branch(self, tmp_path):
        """Test initializing project with explicit parent_branch."""
        manager = ProjectManager(workspace_root=tmp_path)
        
        result = manager.initialize_project(
            issue_number=79,
            issue_title="Test",
            workflow_name="feature",
            parent_branch="epic/76-qa"
        )
        
        assert result["parent_branch"] == "epic/76-qa"
        
        # Verify persisted
        project = manager.get_project_plan(79)
        assert project["parent_branch"] == "epic/76-qa"
    
    def test_initialize_project_without_parent_branch(self, tmp_path):
        """Test initializing project without parent_branch (backward compat)."""
        manager = ProjectManager(workspace_root=tmp_path)
        
        result = manager.initialize_project(
            issue_number=80,
            issue_title="Test",
            workflow_name="bug"
        )
        
        assert result["parent_branch"] is None
        
        # Verify persisted as None
        project = manager.get_project_plan(80)
        assert project["parent_branch"] is None
```

**File:** `tests/unit/mcp_server/managers/test_phase_state_engine_parent_branch.py`

```python
"""Unit tests for parent_branch in PhaseStateEngine."""
import pytest
from mcp_server.managers.phase_state_engine import PhaseStateEngine
from mcp_server.managers.project_manager import ProjectManager


class TestPhaseStateEngineParentBranch:
    """Test parent_branch in PhaseStateEngine."""
    
    def test_initialize_branch_with_parent_branch(self, tmp_path, mock_git):
        """Test initializing branch with explicit parent_branch."""
        # Setup
        pm = ProjectManager(workspace_root=tmp_path)
        pm.initialize_project(79, "Test", "feature", parent_branch="main")
        
        engine = PhaseStateEngine(workspace_root=tmp_path, project_manager=pm)
        
        # Execute
        result = engine.initialize_branch(
            branch="feature/79-test",
            issue_number=79,
            initial_phase="research",
            parent_branch="epic/76-qa"  # Override project's parent
        )
        
        # Verify
        assert result["parent_branch"] == "epic/76-qa"
        
        state = engine.get_state("feature/79-test")
        assert state["parent_branch"] == "epic/76-qa"
    
    def test_reconstruct_includes_parent_branch(self, tmp_path, mock_git):
        """Test reconstruction includes parent_branch from projects.json."""
        # Setup - create project with parent
        pm = ProjectManager(workspace_root=tmp_path)
        pm.initialize_project(
            79, "Test", "feature",
            parent_branch="epic/76-qa"
        )
        
        engine = PhaseStateEngine(workspace_root=tmp_path, project_manager=pm)
        
        # Mock git commits to detect phase
        mock_git.return_value = ["feat: initial commit phase:research"]
        
        # Execute - get_state on non-existent branch triggers reconstruction
        state = engine.get_state("feature/79-test")
        
        # Verify
        assert state["parent_branch"] == "epic/76-qa"
        assert state["reconstructed"] is True
```

### Integration Tests

**File:** `tests/integration/mcp_server/test_parent_branch_workflow.py`

```python
"""Integration tests for parent_branch full workflow."""
import pytest
from pathlib import Path


@pytest.mark.asyncio
async def test_full_parent_branch_workflow(tmp_workspace):
    """Test complete workflow with parent_branch tracking."""
    # Step 1: Initialize project with parent
    init_tool = InitializeProjectTool(workspace_root=tmp_workspace)
    result = await init_tool.execute(InitializeProjectInput(
        issue_number=79,
        issue_title="Test Feature",
        workflow_name="feature",
        parent_branch="epic/76-qa"
    ))
    
    assert result.is_error is False
    data = json.loads(result.content[0]["text"])
    assert data["parent_branch"] == "epic/76-qa"
    
    # Step 2: Verify in projects.json
    projects_file = tmp_workspace / ".st3" / "projects.json"
    projects = json.loads(projects_file.read_text())
    assert projects["79"]["parent_branch"] == "epic/76-qa"
    
    # Step 3: Verify in state.json
    state_file = tmp_workspace / ".st3" / "state.json"
    state = json.loads(state_file.read_text())
    branch = list(state.keys())[0]
    assert state[branch]["parent_branch"] == "epic/76-qa"
    
    # Step 4: Simulate cross-machine (delete state.json)
    state_file.unlink()
    
    # Step 5: Reconstruct via get_parent_branch tool
    get_tool = GetParentBranchTool(workspace_root=tmp_workspace)
    result = await get_tool.execute(GetParentBranchInput(branch=branch))
    
    assert result.is_error is False
    assert "epic/76-qa" in result.content[0]["text"]
    
    # Step 6: Verify state.json reconstructed
    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert state[branch]["parent_branch"] == "epic/76-qa"
    assert state[branch]["reconstructed"] is True
```

---

## Migration Plan

### Backward Compatibility

**Existing Projects Without parent_branch:**
```python
# projects.json before migration
{
  "50": {
    "issue_title": "Old Feature",
    "workflow_name": "feature",
    # NO parent_branch field
    "required_phases": [...]
  }
}

# After migration (no change needed!)
# get() returns None gracefully
parent_branch = project.get("parent_branch")  # Returns None
```

**Existing state.json Without parent_branch:**
```python
# Old state.json
{
  "feature/50-old": {
    "branch": "feature/50-old",
    "issue_number": 50,
    # NO parent_branch field
    "current_phase": "tdd"
  }
}

# After reconstruction
# New state includes parent_branch=None
state = engine.get_state("feature/50-old")
assert state["parent_branch"] is None
```

### Manual Backfill (Optional)

For users who want to add parent_branch to old projects:

```bash
# Via Python
from mcp_server.managers.project_manager import ProjectManager

pm = ProjectManager(".")
project = pm.get_project_plan(50)
project["parent_branch"] = "main"
pm._save_project(50, project)
```

Or via new tool (if we implement it):
```python
backfill_tool = BackfillParentBranchTool()
await backfill_tool.execute(BackfillParentBranchInput(
    issue_number=50,
    parent_branch="main"
))
```

---

## Implementation Checklist

- [ ] Update projects.json schema (add parent_branch field)
- [ ] Update ProjectManager.initialize_project() signature
- [ ] Update PhaseStateEngine.initialize_branch() signature  
- [ ] Update PhaseStateEngine._reconstruct_branch_state()
- [ ] Update InitializeProjectTool input schema
- [ ] Add _detect_parent_branch_from_reflog() helper
- [ ] Update git_checkout display with parent_branch
- [ ] Create branch_tools.py with GetParentBranchTool
- [ ] Write unit tests for ProjectManager
- [ ] Write unit tests for PhaseStateEngine
- [ ] Write unit tests for InitializeProjectTool
- [ ] Write integration test for full workflow
- [ ] Test backward compatibility
- [ ] Update tool documentation
- [ ] Commit with phase:design label

---

## Success Criteria

✅ All type annotations correct and mypy clean  
✅ All docstrings complete with examples  
✅ Error handling comprehensive  
✅ Backward compatibility verified  
✅ Test coverage >90% for new code  
✅ No breaking changes to existing APIs  
✅ Documentation clear and complete  

Ready for TDD phase implementation! 🚀

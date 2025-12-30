# Issue #39 Design: Dual-Mode State Management Technical Specification

**Status:** DRAFT  
**Author:** AI Agent  
**Created:** 2025-12-30  
**Last Updated:** 2025-12-30  
**Issue:** #39

---

## 1. Overview

### 1.1 Purpose

Technical specification for dual-mode state management implementation:
- **Mode 1:** Atomic initialization (InitializeProjectTool creates both files)
- **Mode 2:** Auto-recovery (PhaseStateEngine reconstructs missing state from git)

This document provides detailed method signatures, algorithms, class interactions, error handling, and test specifications.

### 1.2 Scope

**In Scope:**
- Method signatures for all component changes
- Phase detection algorithm implementation
- Error handling flows and rollback strategies
- Sequence diagrams for both modes
- Test case specifications
- Performance considerations

**Out of Scope:**
- Epic #18 enforcement implementation
- GetWorkContextTool enhancement
- UI/UX considerations (CLI tool only)

### 1.3 Related Documents

- [Research Document](research.md) - Problem analysis and solution selection
- [Planning Document](planning.md) - Implementation goals and sequence
- [Issue #42](../issue42/) - 8-phase model design
- [PhaseStateEngine](../../../mcp_server/managers/phase_state_engine.py) - Current implementation

---

## 2. Architecture Overview

### 2.1 Component Interaction

```
Mode 1: Initialization
┌─────────────────────┐
│ InitializeProject   │
│ Tool                │
└──────┬──────────────┘
       │ 1. initialize_project()
       ↓
┌──────────────────────┐
│ ProjectManager       │ → Creates .st3/projects.json
└──────┬───────────────┘
       │ 2. get_current_branch()
       ↓
┌──────────────────────┐
│ GitManager           │ → Returns: "fix/39-name"
└──────┬───────────────┘
       │ 3. initialize_branch()
       ↓
┌──────────────────────┐
│ PhaseStateEngine     │ → Creates .st3/state.json
└──────────────────────┘

Mode 2: Auto-Recovery
┌─────────────────────┐
│ TransitionPhaseTool │
└──────┬──────────────┘
       │ get_state(branch)
       ↓
┌──────────────────────┐
│ PhaseStateEngine     │
│ - Detect missing     │
│ - Reconstruct        │
└──────┬───────────────┘
       │ get_project_plan()
       ↓
┌──────────────────────┐
│ ProjectManager       │ → Workflow definition
└──────────────────────┘
       ↓
┌──────────────────────┐
│ GitManager           │ → Commit messages
└──────────────────────┘
       ↓
       Phase inferred → State created
```

### 2.2 Data Flow

**Initialization Flow:**
```
User Input → ProjectManager → projects.json ✓
          ↘ GitManager → branch name
                       ↘ PhaseStateEngine → state.json ✓
```

**Recovery Flow:**
```
Missing state.json → Extract issue from branch
                  → Load projects.json (workflow)
                  → Scan git commits (phase)
                  → Create state.json with reconstructed data
```

---

## 3. Mode 1: Atomic Initialization Design

### 3.1 InitializeProjectTool Enhancement

**File:** `mcp_server/tools/project_tools.py`

#### Current Implementation
```python
class InitializeProjectTool(BaseTool):
    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root)
        self.manager = ProjectManager(workspace_root=workspace_root)
```

#### New Implementation
```python
class InitializeProjectTool(BaseTool):
    """Initialize project with atomic projects.json + state.json creation."""
    
    def __init__(self, workspace_root: Path | str):
        self.workspace_root = Path(workspace_root)
        self.project_manager = ProjectManager(workspace_root=workspace_root)
        self.git_manager = GitManager()  # NEW
        self.phase_engine = PhaseStateEngine(  # NEW
            workspace_root=workspace_root,
            project_manager=self.project_manager
        )
    
    async def execute(self, params: InitializeProjectInput) -> ToolResult:
        """Initialize project with both projects.json and state.json.
        
        Algorithm:
        1. Create projects.json via ProjectManager
        2. Detect current branch via GitManager
        3. Initialize state.json via PhaseStateEngine
        4. Return success with both file paths
        
        Args:
            params: InitializeProjectInput with issue_number, title, workflow
            
        Returns:
            ToolResult with success message or error
            
        Error Handling:
        - If projects.json creation fails: Return error immediately
        - If state.json creation fails: Return error with guidance
        - No rollback of projects.json (user can retry, idempotent)
        """
        try:
            # Step 1: Create project plan (projects.json)
            result = self.project_manager.initialize_project(
                issue_number=params.issue_number,
                issue_title=params.issue_title,
                workflow_name=params.workflow_name,
                options=InitializeProjectOptions(
                    custom_phases=params.custom_phases,
                    skip_reason=params.skip_reason
                )
            )
            
            # Step 2: Get current branch
            try:
                branch = self.git_manager.get_current_branch()
            except Exception as e:
                return ToolResult.error(
                    f"❌ Failed to detect branch: {e}\n"
                    f"Projects.json created at .st3/projects.json\n"
                    f"Manually create state.json or fix git issue and retry"
                )
            
            # Step 3: Get first phase from workflow
            first_phase = result["required_phases"][0]
            
            # Step 4: Initialize branch state (state.json)
            try:
                self.phase_engine.initialize_branch(
                    branch=branch,
                    issue_number=params.issue_number,
                    initial_phase=first_phase
                )
            except Exception as e:
                return ToolResult.error(
                    f"❌ Failed to initialize state: {e}\n"
                    f"Projects.json created at .st3/projects.json\n"
                    f"State.json creation failed - retry or contact support"
                )
            
            # Step 5: Success
            return ToolResult.text(
                f"✅ Project initialized\n"
                f"Issue: #{params.issue_number}\n"
                f"Workflow: {params.workflow_name}\n"
                f"Branch: {branch}\n"
                f"Initial phase: {first_phase}\n\n"
                f"📝 Created:\n"
                f"  - .st3/projects.json (workflow definition)\n"
                f"  - .st3/state.json (branch state @ {first_phase})"
            )
            
        except ValueError as e:
            return ToolResult.error(f"❌ Initialization failed: {e}")
```

#### Changes Summary
- **Added:** GitManager dependency for branch detection
- **Added:** PhaseStateEngine dependency for state initialization
- **Changed:** Execute method now 3-step atomic operation
- **Changed:** Error messages distinguish between projects.json and state.json failures

---

## 4. Mode 2: Auto-Recovery Design

### 4.1 PhaseStateEngine Enhancement

**File:** `mcp_server/managers/phase_state_engine.py`

#### Enhanced get_state() Method
```python
def get_state(self, branch: str) -> dict[str, Any]:
    """Get branch state with transparent auto-recovery.
    
    If state.json missing or branch not found:
    1. Detect missing state
    2. Reconstruct from projects.json + git commits
    3. Save reconstructed state
    4. Return state with reconstructed=True flag
    
    Args:
        branch: Branch name (e.g., 'fix/39-initialize-project-tool')
        
    Returns:
        State dict with keys: branch, issue_number, workflow_name,
        current_phase, transitions, created_at, reconstructed (optional)
        
    Raises:
        ValueError: If branch name invalid or projects.json missing
        
    Performance:
        - File exists check: O(1)
        - Git commit scan: O(n) where n = last 50 commits
        - Typical recovery time: <100ms
    """
    # Check if state file exists
    if not self.state_file.exists():
        logger.info("State file not found, creating...")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps({}, indent=2))
    
    # Load existing states
    states = json.loads(self.state_file.read_text())
    
    # Check if branch exists in state
    if branch not in states:
        logger.info(f"Branch '{branch}' not in state, reconstructing...")
        state = self._reconstruct_branch_state(branch)
        self._save_state(branch, state)
        return state
    
    return states[branch]
```

#### New Reconstruction Method
```python
def _reconstruct_branch_state(self, branch: str) -> dict[str, Any]:
    """Reconstruct missing branch state from projects.json + git history.
    
    Algorithm:
    1. Extract issue number from branch name (regex match)
    2. Load project plan from projects.json (SSOT for workflow)
    3. Infer current phase from git commit messages
    4. Create state dict with empty transitions array
    5. Set reconstructed=True flag for audit
    
    Args:
        branch: Branch name in format '<type>/<number>-<description>'
        
    Returns:
        Reconstructed state dict
        
    Raises:
        ValueError: If issue number can't be extracted
        ValueError: If project plan not found in projects.json
        
    Example:
        Input: "fix/39-initialize-project-tool"
        Output: {
            "branch": "fix/39-initialize-project-tool",
            "issue_number": 39,
            "workflow_name": "bug",
            "current_phase": "research",  # From git or fallback
            "transitions": [],  # Cannot reconstruct history
            "created_at": "2025-12-30T20:00:00Z",
            "reconstructed": True  # Audit flag
        }
    """
    # Step 1: Extract issue number from branch name
    issue_number = self._extract_issue_from_branch(branch)
    if not issue_number:
        raise ValueError(
            f"Cannot extract issue number from branch '{branch}'. "
            f"Expected format: <type>/<number>-<description>\n"
            f"Examples: fix/39-description, feature/42-name"
        )
    
    # Step 2: Get project plan (SSOT for workflow definition)
    project = self.project_manager.get_project_plan(issue_number)
    if not project:
        raise ValueError(
            f"Project plan not found for issue #{issue_number}. "
            f"Run initialize_project first:\n"
            f"  initialize_project(issue={issue_number}, workflow='bug', ...)"
        )
    
    # Step 3: Infer current phase from git commits
    workflow_phases = project["required_phases"]
    current_phase = self._infer_phase_from_git(branch, workflow_phases)
    
    # Step 4: Create reconstructed state
    logger.info(
        f"✅ Reconstructed state for {branch}: "
        f"issue={issue_number}, workflow={project['workflow_name']}, "
        f"phase={current_phase}"
    )
    
    return {
        "branch": branch,
        "issue_number": issue_number,
        "workflow_name": project["workflow_name"],
        "current_phase": current_phase,
        "transitions": [],  # Cannot reconstruct transition history
        "created_at": datetime.now(UTC).isoformat(),
        "reconstructed": True  # Audit flag for debugging
    }
```

---

## 5. Phase Detection Algorithm

### 5.1 Multi-Strategy Detection

```python
def _infer_phase_from_git(
    self, 
    branch: str, 
    workflow_phases: list[str]
) -> str:
    """Infer current phase using multi-strategy detection.
    
    Strategy Priority:
    1. Explicit phase keywords (highest confidence)
    2. Conventional commit prefixes (medium confidence)
    3. Fallback to first phase (safe default)
    
    Args:
        branch: Branch name for git log filtering
        workflow_phases: Valid phases from projects.json
        
    Returns:
        Phase name (guaranteed to be in workflow_phases)
        
    Performance:
        - Git log scan: O(n) where n = 50 commits
        - Pattern matching: O(m) where m = number of phases (typically <10)
        - Total: O(n*m) ≈ O(50*8) = 400 operations max
    """
    try:
        # Get recent commits on this branch
        commits = self.git_manager.get_recent_commits(limit=50)
        
        # Strategy 1: Explicit phase keywords (e.g., "Complete research phase")
        phase = self._detect_explicit_phase_keywords(commits, workflow_phases)
        if phase:
            logger.info(f"Phase detected via explicit keywords: {phase}")
            return phase
        
        # Strategy 2: Conventional commits (e.g., "test:" → red)
        phase = self._detect_conventional_commits(commits)
        if phase and phase in workflow_phases:
            logger.info(f"Phase detected via conventional commits: {phase}")
            return phase
        
        # Strategy 3: Safe fallback
        fallback = workflow_phases[0]
        logger.warning(
            f"No phase detected in commits, defaulting to first phase: {fallback}"
        )
        return fallback
        
    except Exception as e:
        # Git error: Fall back safely
        fallback = workflow_phases[0]
        logger.warning(
            f"Git error during phase detection: {e}. "
            f"Defaulting to first phase: {fallback}"
        )
        return fallback
```

### 5.2 Explicit Keyword Detection

```python
def _detect_explicit_phase_keywords(
    self, 
    commits: list[str], 
    workflow_phases: list[str]
) -> str | None:
    """Detect phase from explicit keywords in commit messages.
    
    Patterns Matched:
    - "Complete {phase} phase"
    - "{phase} phase #XX"
    - "{phase}: description"
    - "Start {phase} phase"
    
    Args:
        commits: List of commit messages (most recent first)
        workflow_phases: Valid phases to match against
        
    Returns:
        Phase name or None if not found
        
    Algorithm:
        Iterate commits from newest to oldest, checking each phase
        in reverse order (later phases more likely to be current)
    """
    for commit in commits:
        commit_lower = commit.lower()
        
        # Check each phase (reverse order: later phases first)
        for phase in reversed(workflow_phases):
            patterns = [
                f"complete {phase}",
                f"{phase} phase",
                f"start {phase}",
                f"{phase}:",  # Prefix style
            ]
            
            if any(pattern in commit_lower for pattern in patterns):
                return phase
    
    return None
```

### 5.3 Conventional Commit Detection

```python
def _detect_conventional_commits(self, commits: list[str]) -> str | None:
    """Detect phase from conventional commit prefixes.
    
    Mappings:
    - test: → red
    - feat: → green
    - refactor: → refactor
    - docs: → documentation
    
    Args:
        commits: List of commit messages
        
    Returns:
        Phase name or None if not matched
        
    Limitations:
        Only works for TDD cycle phases. Cannot detect research, planning,
        design, or integration phases.
    """
    if not commits:
        return None
    
    latest = commits[0].lower()
    
    if latest.startswith("test:") or "failing test" in latest:
        return "red"
    if latest.startswith("feat:") or "pass" in latest:
        return "green"
    if latest.startswith("refactor:"):
        return "refactor"
    if latest.startswith("docs:"):
        return "documentation"
    
    return None
```

### 5.4 Branch Name Parsing

```python
def _extract_issue_from_branch(self, branch: str) -> int | None:
    """Extract issue number from branch name.
    
    Supported Formats:
    - feature/42-description → 42
    - fix/39-bug-name → 39
    - refactor/49-cleanup → 49
    - docs/12-update-readme → 12
    
    Args:
        branch: Branch name
        
    Returns:
        Issue number or None if format doesn't match
        
    Regex: ^[a-z]+/(\d+)-
    """
    import re
    match = re.match(r'^[a-z]+/(\d+)-', branch)
    return int(match.group(1)) if match else None
```

---

## 6. Error Handling

### 6.1 Error Scenarios

| Scenario | Detection | Response | User Impact |
|----------|-----------|----------|-------------|
| Invalid branch name | Regex match fails | ValueError with format guidance | Must fix branch name |
| Missing projects.json | File not found | ValueError with init guidance | Must run initialize_project |
| Git command failure | Exception from GitManager | Warning + fallback to first phase | Auto-recovery with safe default |
| State file corrupted | JSON parse error | Delete + recreate empty | Auto-recovery (data loss) |
| Issue number mismatch | Project not found | ValueError | Must initialize correct project |

### 6.2 Error Messages

```python
# Invalid branch format
raise ValueError(
    f"Cannot extract issue number from branch '{branch}'. "
    f"Expected format: <type>/<number>-<description>\n"
    f"Examples:\n"
    f"  ✅ fix/39-bug-description\n"
    f"  ✅ feature/42-new-feature\n"
    f"  ❌ {branch} (invalid)"
)

# Missing project plan
raise ValueError(
    f"Project plan not found for issue #{issue_number}.\n"
    f"Initialize project first:\n"
    f"  initialize_project(\n"
    f"    issue={issue_number},\n"
    f"    workflow='bug',\n"
    f"    title='Your issue title'\n"
    f"  )"
)

# Git error (warning, not error)
logger.warning(
    f"Git command failed: {e}. "
    f"Falling back to first phase '{workflow_phases[0]}'. "
    f"This is safe but you may need to manually transition phases."
)
```

---

## 7. Sequence Diagrams

### 7.1 Mode 1: Atomic Initialization

```
User                InitializeTool    ProjectManager    GitManager    PhaseEngine
  |                       |                 |               |             |
  |--initialize_project-->|                 |               |             |
  |                       |                 |               |             |
  |                       |--init_project-->|               |             |
  |                       |                 |               |             |
  |                       |<--result--------|               |             |
  |                       | (projects.json created)         |             |
  |                       |                 |               |             |
  |                       |--get_current_branch()---------->|             |
  |                       |                 |               |             |
  |                       |<--branch name-------------------|             |
  |                       |                 |               |             |
  |                       |--initialize_branch()----------------------->|
  |                       | (branch, issue, first_phase)    |             |
  |                       |                 |               |             |
  |                       |<--success------------------------------------|
  |                       | (state.json created)            |             |
  |                       |                 |               |             |
  |<--success message-----|                 |               |             |
  | "Both files created"  |                 |               |             |
```

### 7.2 Mode 2: Auto-Recovery

```
User              TransitionTool   PhaseEngine      ProjectManager   GitManager
  |                    |               |                 |              |
  |--transition------->|               |                 |              |
  |                    |               |                 |              |
  |                    |--get_state--->|                 |              |
  |                    |               |                 |              |
  |                    |               |--(check file)   |              |
  |                    |               |--(branch missing)|             |
  |                    |               |                 |              |
  |                    |               |--get_project--->|              |
  |                    |               |<--workflow------|              |
  |                    |               |                 |              |
  |                    |               |--get_commits------------------->|
  |                    |               |<--commit msgs------------------|
  |                    |               |                 |              |
  |                    |               |--(infer phase)  |              |
  |                    |               |--(create state) |              |
  |                    |               |--(save file)    |              |
  |                    |               |                 |              |
  |                    |<--state-------|                 |              |
  |                    | (reconstructed=True)            |              |
  |                    |               |                 |              |
  |<--transition OK----|               |                 |              |
  | (seamless)         |               |                 |              |
```

---

## 8. Testing Strategy

### 8.1 Unit Tests

#### Test: InitializeProjectTool
```python
class TestInitializeProjectTool:
    """Unit tests for Mode 1 atomic initialization."""
    
    def test_creates_both_files(self):
        """Verify both projects.json and state.json created."""
        # Arrange
        tool = InitializeProjectTool(workspace_root=tmp_path)
        params = InitializeProjectInput(
            issue_number=39,
            issue_title="Test issue",
            workflow_name="bug"
        )
        
        # Act
        result = await tool.execute(params)
        
        # Assert
        assert result.is_success
        assert (tmp_path / ".st3/projects.json").exists()
        assert (tmp_path / ".st3/state.json").exists()
    
    def test_branch_detection_failure(self):
        """Verify error handling if git fails."""
        # Arrange: Mock GitManager to raise exception
        
        # Act
        result = await tool.execute(params)
        
        # Assert
        assert result.is_error
        assert "Failed to detect branch" in result.content
        assert (tmp_path / ".st3/projects.json").exists()  # Partial success
    
    def test_first_phase_determined_from_workflow(self):
        """Verify first phase set correctly per workflow."""
        # Test feature workflow → research
        # Test bug workflow → research
        # Test hotfix workflow → tdd
```

#### Test: PhaseStateEngine Recovery
```python
class TestPhaseStateEngineRecovery:
    """Unit tests for Mode 2 auto-recovery."""
    
    def test_missing_state_triggers_reconstruction(self):
        """Verify recovery when state.json missing."""
        # Arrange: Delete state.json
        # Create projects.json with test data
        
        # Act
        state = engine.get_state("fix/39-test")
        
        # Assert
        assert state["reconstructed"] is True
        assert state["issue_number"] == 39
        assert "current_phase" in state
    
    def test_phase_inferred_from_explicit_keywords(self):
        """Test Strategy 1: Explicit phase detection."""
        # Arrange: Mock git commits with "Complete planning phase"
        
        # Act
        state = engine.get_state(branch)
        
        # Assert
        assert state["current_phase"] == "planning"
    
    def test_phase_inferred_from_conventional_commits(self):
        """Test Strategy 2: Conventional commits."""
        # Arrange: Mock git commits with "test: Add failing test"
        
        # Act
        state = engine.get_state(branch)
        
        # Assert
        assert state["current_phase"] == "red"
    
    def test_fallback_to_first_phase(self):
        """Test Strategy 3: Safe fallback."""
        # Arrange: Mock git with no phase-related commits
        
        # Act
        state = engine.get_state(branch)
        
        # Assert
        assert state["current_phase"] == "research"  # First phase
    
    def test_invalid_branch_name_raises_error(self):
        """Verify error on invalid branch format."""
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot extract issue"):
            engine.get_state("invalid-branch-name")
    
    def test_missing_project_plan_raises_error(self):
        """Verify error if projects.json missing project."""
        # Arrange: Empty projects.json
        
        # Act & Assert
        with pytest.raises(ValueError, match="Project plan not found"):
            engine.get_state("fix/999-nonexistent")
```

### 8.2 Integration Tests

```python
class TestDualModeIntegration:
    """End-to-end tests for both modes."""
    
    def test_initialize_then_transition(self):
        """Test Mode 1 → normal usage."""
        # Initialize project
        result = await initialize_tool.execute(params)
        assert result.is_success
        
        # Transition phase
        result = await transition_tool.execute(...)
        assert result.is_success
    
    def test_cross_machine_scenario(self):
        """Test Mode 2 recovery scenario."""
        # Machine A: Initialize + work
        await initialize_tool.execute(params)
        # Simulate git commit
        # Delete state.json (simulate machine switch)
        
        # Machine B: Transition (triggers recovery)
        result = await transition_tool.execute(...)
        assert result.is_success
        assert "reconstructed" in engine.get_state(branch)
    
    def test_recovery_idempotent(self):
        """Verify recovery can be called multiple times."""
        # Delete state.json
        state1 = engine.get_state(branch)
        state2 = engine.get_state(branch)
        
        assert state1 == state2
```

### 8.3 Edge Case Tests

```python
def test_mid_phase_uncommitted_work():
    """User in planning phase, uncommitted work."""
    # Last commit: "Complete research phase"
    # Actual phase: planning (uncommitted)
    # Recovery should: Return "research" (safe)
    
def test_no_commits_yet():
    """Brand new project, no commits."""
    # Recovery should: Return first phase of workflow
    
def test_git_detached_head():
    """Git in detached HEAD state."""
    # Recovery should: Warn + fallback to first phase
    
def test_concurrent_initialization():
    """Two tools initialize simultaneously."""
    # Verify atomic file creation (no race condition)
```

---

## 9. Performance Considerations

### 9.1 Performance Targets

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Initialize both files | <200ms | File I/O + git call |
| Auto-recovery (state exists) | <10ms | JSON parse + dict lookup |
| Auto-recovery (missing state) | <150ms | Git log + JSON write |
| Phase detection from git | <100ms | 50 commit scan |

### 9.2 Optimization Strategies

**Git Commit Limiting:**
- Only scan last 50 commits (reasonable for phase detection)
- Avoid full git log (could be thousands of commits)

**Caching:**
- No caching needed (state.json is the cache)
- File system operations fast enough (<10ms)

**Lazy Loading:**
- GitManager instantiated only when needed
- PhaseStateEngine created on-demand

---

## 10. Implementation Checklist

### Phase 1: Preparation
- [ ] Add `.st3/state.json` to .gitignore
- [ ] Verify GitManager.get_recent_commits() exists
- [ ] Review PhaseStateEngine.initialize_branch() signature

### Phase 2: Mode 1 Implementation
- [ ] Update InitializeProjectTool.__init__() with dependencies
- [ ] Implement enhanced execute() method
- [ ] Add error handling for git failures
- [ ] Write unit tests for atomic creation
- [ ] Test all workflow types

### Phase 3: Mode 2 Implementation
- [ ] Enhance PhaseStateEngine.get_state() with detection
- [ ] Implement _reconstruct_branch_state() method
- [ ] Implement _extract_issue_from_branch() method
- [ ] Implement _infer_phase_from_git() method
- [ ] Implement _detect_explicit_phase_keywords() method
- [ ] Implement _detect_conventional_commits() method
- [ ] Write unit tests for each strategy
- [ ] Test edge cases (invalid branch, missing project, git errors)

### Phase 4: Integration Testing
- [ ] Test initialize → transition flow
- [ ] Test cross-machine recovery scenario
- [ ] Test idempotent recovery
- [ ] Performance testing
- [ ] Edge case testing

### Phase 5: Documentation
- [ ] Update InitializeProjectTool docstrings
- [ ] Document auto-recovery behavior
- [ ] Add troubleshooting guide
- [ ] Update commit message conventions

---

## 11. Open Design Questions

### Q1: GitManager.get_recent_commits() API
**Question:** What is the exact signature of get_recent_commits()?

**Options:**
A. `get_recent_commits(limit: int) -> list[str]` (commit messages only)
B. `get_recent_commits(limit: int) -> list[Commit]` (commit objects)

**Decision:** Check existing implementation, adapt accordingly. If B, use `commit.message`.

### Q2: Rollback Strategy for InitializeProjectTool
**Question:** Should we rollback projects.json if state.json creation fails?

**Decision:** NO - Keep it simple. Report error, let user retry. Projects.json creation is idempotent.

### Q3: Reconstructed Flag Persistence
**Question:** Should `reconstructed: true` flag persist forever or be cleared on next transition?

**Decision:** Clear on first successful transition (indicates state now "owned" by this machine).

---

**Status:** Design Complete ✅  
**Ready for:** TDD Implementation Phase (red → green → refactor)

---

*Design Date: 2025-12-30*  
*Based on: Research findings, planning goals, existing codebase patterns*

# Issue #64 Implementation Plan: Fix create_branch Tool

**Status:** DRAFT  
**Author:** AI Agent  
**Date:** 2025-12-29  
**Phase:** planning  
**Decision:** Option B - Fully Explicit base_branch parameter

---

## Overview

Fix the `create_feature_branch` MCP tool to:
1. Remove unsafe `base="main"` default
2. Add explicit `base_branch` required parameter
3. Rename tool from `create_feature_branch` to `create_branch`
4. Add comprehensive logging at all layers

**Approach:** Bottom-up implementation (Adapter → Manager → Tool → Tests)

---

## Implementation Steps

### Step 1: Update Adapter Layer
**File:** `mcp_server/adapters/git_adapter.py`

**Changes:**
1. Add logging import
2. Remove `base="main"` default
3. Add HEAD resolution logic
4. Add structured logging

**Before:**
```python
def create_branch(self, branch_name: str, base: str = "main") -> None:
    """Create a new branch."""
    try:
        if branch_name in self.repo.heads:
            raise ExecutionError(f"Branch {branch_name} already exists")
        
        new_branch = self.repo.create_head(branch_name, base)
        new_branch.checkout()
    except Exception as e:
        raise ExecutionError(f"Failed to create branch {branch_name}: {e}") from e
```

**After:**
```python
from mcp_server.core.logging import get_logger

logger = get_logger("adapters.git")

def create_branch(self, branch_name: str, base: str) -> None:
    """Create a new branch from base (must be explicit).
    
    Args:
        branch_name: Name of the new branch
        base: Base branch, commit hash, or "HEAD" for current branch
    
    Raises:
        ExecutionError: If branch already exists or creation fails
    """
    # Resolve base reference
    if base == "HEAD":
        base_ref = self.repo.head.commit
        resolved_base = f"HEAD ({base_ref.hexsha[:7]})"
    else:
        base_ref = base
        resolved_base = base
    
    logger.debug(
        "Creating git branch",
        extra={"props": {
            "branch_name": branch_name,
            "base": base,
            "resolved_base": resolved_base,
            "current_branch": self.get_current_branch()
        }}
    )
    
    try:
        if branch_name in self.repo.heads:
            raise ExecutionError(f"Branch {branch_name} already exists")
        
        new_branch = self.repo.create_head(branch_name, base_ref)
        new_branch.checkout()
        
        logger.info(
            "Created and checked out branch",
            extra={"props": {
                "branch_name": branch_name,
                "base": resolved_base
            }}
        )
    except ExecutionError:
        raise
    except Exception as e:
        logger.error(
            "Failed to create branch",
            extra={"props": {
                "branch_name": branch_name,
                "base": base,
                "error": str(e)
            }}
        )
        raise ExecutionError(f"Failed to create branch {branch_name}: {e}") from e
```

### Step 2: Update Manager Layer
**File:** `mcp_server/managers/git_manager.py`

**Changes:**
1. Add logging import
2. Rename method: `create_feature_branch` → `create_branch`
3. Add `base_branch` required parameter
4. Add structured logging

**Before:**
```python
def create_feature_branch(self, name: str, branch_type: str = "feature") -> str:
    """Create a new feature branch enforcing naming conventions."""
    # ... validation ...
    
    self.adapter.create_branch(full_name)
    return full_name
```

**After:**
```python
from mcp_server.core.logging import get_logger

logger = get_logger("managers.git")

def create_branch(self, name: str, branch_type: str, base_branch: str) -> str:
    """Create a new branch enforcing naming conventions.
    
    Args:
        name: Branch name in kebab-case
        branch_type: Type (feature, fix, refactor, docs)
        base_branch: Base branch to create from (required!)
    
    Returns:
        Full branch name (e.g., "feature/123-my-feature")
    
    Raises:
        ValidationError: If name or type invalid
        PreflightError: If working directory not clean
    """
    # Validation
    if branch_type not in ["feature", "fix", "refactor", "docs"]:
        raise ValidationError(
            f"Invalid branch type: {branch_type}",
            hints=["Use feature, fix, refactor, or docs"]
        )

    if not re.match(r"^[a-z0-9-]+$", name):
        raise ValidationError(
            f"Invalid branch name: {name}",
            hints=["Use kebab-case (lowercase, numbers, hyphens only)"]
        )

    full_name = f"{branch_type}/{name}"
    
    current_branch = self.adapter.get_current_branch()
    
    logger.info(
        "Creating branch",
        extra={"props": {
            "full_name": full_name,
            "branch_type": branch_type,
            "base_branch": base_branch,
            "current_branch": current_branch
        }}
    )

    # Pre-flight check
    if not self.adapter.is_clean():
        raise PreflightError(
            "Working directory is not clean",
            blockers=["Commit or stash changes before creating a new branch"]
        )

    self.adapter.create_branch(full_name, base=base_branch)
    
    logger.info(
        "Branch created successfully",
        extra={"props": {
            "full_name": full_name,
            "base_branch": base_branch
        }}
    )
    
    return full_name
```

**Note:** Keep `create_feature_branch` as deprecated wrapper for backward compatibility during transition:
```python
def create_feature_branch(self, name: str, branch_type: str = "feature") -> str:
    """DEPRECATED: Use create_branch() with explicit base_branch parameter."""
    import warnings
    warnings.warn(
        "create_feature_branch is deprecated, use create_branch with base_branch parameter",
        DeprecationWarning,
        stacklevel=2
    )
    # Default to HEAD for backward compatibility
    return self.create_branch(name, branch_type, base_branch="HEAD")
```

### Step 3: Update Tool Layer
**File:** `mcp_server/tools/git_tools.py`

**Changes:**
1. Add logging import
2. Rename tool: `create_feature_branch` → `create_branch`
3. Add `base_branch` required field to input schema
4. Update tool description
5. Add structured logging

**Before:**
```python
class CreateBranchInput(BaseModel):
    """Input for CreateBranchTool."""
    name: str = Field(..., description="Branch name (kebab-case)")
    branch_type: str = Field(
        default="feature",
        description="Branch type",
        pattern="^(feature|fix|refactor|docs)$"
    )

class CreateBranchTool(BaseTool):
    """Tool to create a git branch."""
    
    name = "create_feature_branch"
    description = "Create a new feature branch"
    args_model = CreateBranchInput
    
    async def execute(self, params: CreateBranchInput) -> ToolResult:
        branch_name = self.manager.create_feature_branch(params.name, params.branch_type)
        return ToolResult.text(f"Created and switched to branch: {branch_name}")
```

**After:**
```python
from mcp_server.core.logging import get_logger

logger = get_logger("tools.git")

class CreateBranchInput(BaseModel):
    """Input for CreateBranchTool."""
    name: str = Field(..., description="Branch name (kebab-case)")
    branch_type: str = Field(
        default="feature",
        description="Branch type",
        pattern="^(feature|fix|refactor|docs)$"
    )
    base_branch: str = Field(
        ...,
        description="Base branch to create from (e.g., 'HEAD', 'main', 'refactor/51-labels-yaml')"
    )

class CreateBranchTool(BaseTool):
    """Tool to create a git branch from specified base."""
    
    name = "create_branch"  # Renamed!
    description = "Create a new branch from specified base branch"
    args_model = CreateBranchInput
    
    async def execute(self, params: CreateBranchInput) -> ToolResult:
        logger.info(
            "Branch creation requested",
            extra={"props": {
                "name": params.name,
                "branch_type": params.branch_type,
                "base_branch": params.base_branch
            }}
        )
        
        try:
            branch_name = self.manager.create_branch(
                params.name,
                params.branch_type,
                params.base_branch
            )
            return ToolResult.text(f"✅ Created and switched to branch: {branch_name}")
        except Exception as e:
            logger.error(
                "Branch creation failed",
                extra={"props": {
                    "name": params.name,
                    "error": str(e)
                }}
            )
            raise
```

### Step 4: Update Test Files

**File:** `tests/unit/mcp_server/adapters/test_git_adapter.py`

Add tests for:
- ✅ Create branch with explicit base (branch name)
- ✅ Create branch with HEAD
- ✅ Create branch with commit hash
- ✅ Error when branch already exists
- ✅ HEAD resolution works correctly

**File:** `tests/unit/mcp_server/managers/test_git_manager.py`

Update existing tests:
- ✅ Update `test_create_feature_branch_valid` → `test_create_branch_valid`
- ✅ Add `base_branch` parameter to all test calls
- ✅ Add test for deprecated `create_feature_branch` warning

**File:** `tests/unit/mcp_server/tools/test_git_tools.py`

Update existing tests:
- ✅ Update mock calls to include `base_branch`
- ✅ Test required `base_branch` validation

**File:** `tests/unit/mcp_server/integration/test_git.py`

Update integration tests:
- ✅ Add `base_branch` parameter to all calls
- ✅ Test branching from different bases

### Step 5: Update Tool Registration
**File:** `mcp_server/server.py` (or wherever tools are registered)

Update tool name in registry from `create_feature_branch` to `create_branch`.

### Step 6: Find and Update All Callers

Search codebase for usages:
```bash
grep -r "create_feature_branch" --include="*.py"
```

Expected locations:
- Integration tests
- Any workflow automation scripts
- Documentation examples

---

## Test Strategy

### Unit Tests (TDD - Write First)

**Adapter Layer:**
```python
def test_create_branch_requires_explicit_base():
    """Should fail when base parameter missing."""
    adapter = GitAdapter()
    with pytest.raises(TypeError):
        adapter.create_branch("test-branch")  # Missing base parameter

def test_create_branch_with_head():
    """Should create from current HEAD."""
    adapter = GitAdapter()
    adapter.create_branch("test-branch", base="HEAD")
    # Assert branch created from current commit

def test_create_branch_with_branch_name():
    """Should create from specified branch."""
    adapter = GitAdapter()
    adapter.create_branch("test-branch", base="main")
    # Assert branch created from main

def test_create_branch_with_commit_hash():
    """Should create from specific commit."""
    adapter = GitAdapter()
    adapter.create_branch("test-branch", base="abc123f")
    # Assert branch created from that commit
```

**Manager Layer:**
```python
def test_create_branch_requires_base_branch():
    """Should require base_branch parameter."""
    manager = GitManager()
    with pytest.raises(TypeError):
        manager.create_branch("test", "feature")  # Missing base_branch

def test_create_branch_passes_base_to_adapter():
    """Should pass base_branch to adapter."""
    mock_adapter = Mock()
    manager = GitManager(adapter=mock_adapter)
    
    manager.create_branch("test", "feature", "refactor/51")
    
    mock_adapter.create_branch.assert_called_once_with(
        "feature/test",
        base="refactor/51"
    )

def test_deprecated_create_feature_branch_warns():
    """Should emit deprecation warning."""
    manager = GitManager()
    with pytest.warns(DeprecationWarning):
        manager.create_feature_branch("test", "feature")
```

**Tool Layer:**
```python
def test_create_branch_tool_requires_base_branch():
    """Should validate base_branch as required field."""
    with pytest.raises(ValidationError):
        CreateBranchInput(name="test", branch_type="feature")  # Missing base_branch

def test_create_branch_tool_calls_manager():
    """Should call manager with all parameters."""
    mock_manager = Mock()
    tool = CreateBranchTool(manager=mock_manager)
    
    params = CreateBranchInput(
        name="test",
        branch_type="feature",
        base_branch="main"
    )
    
    await tool.execute(params)
    
    mock_manager.create_branch.assert_called_once_with(
        "test", "feature", "main"
    )
```

### Integration Tests

**Real Git Operations:**
```python
def test_full_branch_creation_flow():
    """Test complete flow from tool to git."""
    # Setup real git repo
    # Call tool with base_branch
    # Verify branch created from correct base
    # Verify logging captured

def test_branch_from_different_bases():
    """Test branching from main, HEAD, and other branches."""
    # Create from main
    # Create from HEAD  
    # Create from another branch
    # Verify all correct
```

### Logging Tests

```python
def test_logging_at_adapter_level(caplog):
    """Should log branch creation at adapter."""
    adapter = GitAdapter()
    adapter.create_branch("test", base="main")
    
    assert "Creating git branch" in caplog.text
    assert "test" in caplog.text
    assert "main" in caplog.text

def test_logging_shows_base_mismatch(caplog):
    """Should log when base differs from current branch."""
    # On refactor/51
    manager.create_branch("test", "fix", "main")
    
    # Should log: current=refactor/51, base=main
    assert "current_branch" in caplog.text
    assert "base_branch" in caplog.text
```

---

## Breaking Changes

### Tool Name Change
**Old:** `create_feature_branch`  
**New:** `create_branch`

**Impact:** All MCP clients calling this tool must update

**Migration:**
```python
# OLD
create_feature_branch(name="test", branch_type="fix")

# NEW
create_branch(name="test", branch_type="fix", base_branch="HEAD")
```

### Required Parameter
**Old:** No base parameter (implicit main)  
**New:** `base_branch` required parameter

**Impact:** All callers must explicitly specify base

### Manager Method Signature
**Old:** `create_feature_branch(name, branch_type="feature")`  
**New:** `create_branch(name, branch_type, base_branch)`

**Impact:** Internal callers must update (with deprecation wrapper for transition)

### Known Callers to Update

From search results:
```
mcp_server/managers/git_manager.py:19:    def create_feature_branch(...)  # Keep as deprecated
tests/unit/mcp_server/integration/test_git.py:20  # Update to new API
tests/unit/mcp_server/integration/test_git.py:31  # Update to new API
tests/unit/mcp_server/integration/test_git.py:37  # Update to new API
tests/unit/mcp_server/managers/test_git_manager.py:43  # Update to new API
tests/unit/mcp_server/managers/test_git_manager.py:47  # Update to new API
tests/unit/mcp_server/managers/test_git_manager.py:53  # Update to new API
tests/unit/mcp_server/managers/test_git_manager.py:58  # Update to new API
tests/unit/mcp_server/managers/test_git_manager.py:63  # Update to new API
tests/unit/tools/test_git_tools.py:24  # Update mock
tests/unit/tools/test_git_tools.py:29  # Update assertion
```

**Estimated:** 10-12 files to update

---

## Risk Analysis

### High Risk

**1. Breaking existing workflows**
- **Risk:** MCP clients using old tool name fail
- **Mitigation:** 
  - Keep deprecated wrapper with warning
  - Clear migration guide in docs
  - Version bump (breaking change notice)

**2. Logging performance**
- **Risk:** Too much logging slows down operations
- **Mitigation:**
  - Use appropriate log levels (DEBUG for details, INFO for operations)
  - Structured logging already optimized

### Medium Risk

**3. HEAD resolution edge cases**
- **Risk:** Detached HEAD or unusual states
- **Mitigation:**
  - Test detached HEAD scenario
  - Graceful error handling

**4. Test coverage gaps**
- **Risk:** Missing edge cases
- **Mitigation:**
  - Comprehensive test plan above
  - Run full test suite before merge

### Low Risk

**5. Merge conflicts**
- **Risk:** Changes conflict with other branches
- **Mitigation:**
  - Branch from branch 63 (already has Issue #62 work)
  - Limited scope (only git tools affected)

---

## Rollout Plan

### Phase 1: Implementation (TDD)
1. Write failing tests (RED)
2. Implement adapter changes
3. Implement manager changes
4. Implement tool changes
5. All tests passing (GREEN)
6. Refactor if needed

### Phase 2: Integration Testing
1. Run full test suite
2. Test with real git operations
3. Verify logging output
4. Check log file creation

### Phase 3: Update Callers
1. Update integration tests
2. Update manager tests
3. Update tool tests
4. Search for any other usages

### Phase 4: Documentation
1. Update tool documentation
2. Add migration guide
3. Update changelog
4. Note breaking changes

### Phase 5: Merge Strategy
1. Merge to branch 63 (fix/63-legacy-phase-tools)
2. Test both Issue #64 and #63 work together
3. Merge branch 63 to branch 51 (refactor/51-labels-yaml)
4. Eventually merge branch 51 to main

---

## Success Criteria

- [ ] All adapter tests passing with explicit base parameter
- [ ] All manager tests passing with new create_branch method
- [ ] All tool tests passing with base_branch required field
- [ ] Logging captured at all 3 layers (adapter/manager/tool)
- [ ] All existing callers updated and working
- [ ] Tool renamed to `create_branch`
- [ ] Deprecated `create_feature_branch` emits warning
- [ ] No regression in existing git functionality
- [ ] Documentation updated
- [ ] Full test suite passing (921+ tests)

---

## Next Steps

1. Transition to **TDD phase**
2. Write failing tests first (RED)
3. Implement changes to make tests pass (GREEN)
4. Refactor and commit
5. Move to integration phase for full testing

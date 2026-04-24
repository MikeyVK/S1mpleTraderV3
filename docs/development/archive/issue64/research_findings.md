# Issue #64 Research Findings: create_branch Tool Analysis

**Status:** DRAFT  
**Author:** AI Agent  
**Date:** 2025-12-29  
**Issue:** #64 - Bug: create_feature_branch has incorrect name and unsafe default base  
**Phase:** research

---

## Problem Statement

The `create_feature_branch` MCP tool has two critical issues discovered during development of Issues #62 and #63:

1. **Incorrect Default Base:** Tool creates branches from `main` instead of current HEAD, causing both fix/62 and fix/63 to branch from main instead of their intended parent branch `refactor/51-labels-yaml`
2. **Misleading Tool Name:** Named `create_feature_branch` but creates all branch types (feature, fix, refactor, docs)

### Impact
- Data loss risk: Child branches missing parent branch commits
- Confusion: Tool name doesn't match functionality
- Inconsistent with git standard behavior

---

## Current Implementation Analysis

### Layer 1: Adapter (git_adapter.py)

**Location:** `mcp_server/adapters/git_adapter.py` lines 57-70

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

**Issues:**
- ❌ Default `base="main"` hardcoded
- ❌ No logging
- ❌ Doesn't match GitPython's own API (which defaults to HEAD)

### Layer 2: Manager (git_manager.py)

**Location:** `mcp_server/managers/git_manager.py` lines 19-50

```python
def create_feature_branch(self, name: str, branch_type: str = "feature") -> str:
    """Create a new feature branch enforcing naming conventions."""
    # Validation
    if branch_type not in ["feature", "fix", "refactor", "docs"]:
        raise ValidationError(...)
    
    if not re.match(r"^[a-z0-9-]+$", name):
        raise ValidationError(...)
    
    full_name = f"{branch_type}/{name}"
    
    # Pre-flight check
    if not self.adapter.is_clean():
        raise PreflightError(...)
    
    self.adapter.create_branch(full_name)  # NO base parameter passed!
    return full_name
```

**Issues:**
- ❌ Method name `create_feature_branch` misleading (handles all types)
- ❌ Never passes `base` parameter to adapter (uses implicit default)
- ❌ No logging
- ❌ Good: Validation and pre-flight checks present

### Layer 3: Tool (git_tools.py)

**Location:** `mcp_server/tools/git_tools.py` lines 16-42

```python
class CreateBranchInput(BaseModel):
    """Input for CreateBranchTool."""
    name: str = Field(..., description="Branch name (kebab-case)")
    branch_type: str = Field(
        default="feature",
        description="Branch type",
        pattern="^(feature|fix|refactor|docs)$"
    )
    # NO base_branch field!

class CreateBranchTool(BaseTool):
    """Tool to create a git branch."""
    
    name = "create_feature_branch"  # Misleading name
    description = "Create a new feature branch"
    args_model = CreateBranchInput
    
    async def execute(self, params: CreateBranchInput) -> ToolResult:
        branch_name = self.manager.create_feature_branch(params.name, params.branch_type)
        return ToolResult.text(f"Created and switched to branch: {branch_name}")
```

**Issues:**
- ❌ Tool name `create_feature_branch` doesn't match functionality
- ❌ No `base_branch` input parameter (user can't specify!)
- ❌ No logging

---

## Git Standard Behavior Comparison

### Standard Git Commands

**Creating branch from current HEAD:**
```bash
$ git checkout -b new-branch
# Creates from current HEAD, NOT from main!
```

**Creating branch from specific base:**
```bash
$ git checkout -b new-branch origin/main
$ git checkout -b hotfix/123 main
$ git checkout -b feature/456 refactor/51-labels-yaml
```

**Key Observation:** Git ALWAYS defaults to HEAD, never to "main"

### Practical Test

```bash
# On branch fix/64-create-branch-from-head (commit 98bc368)
$ git checkout -b test-git-behavior
# Result: test-git-behavior created from 98bc368 (current HEAD)
# NOT from main!
```

**Conclusion:** Our implementation violates git standard behavior

---

## GitPython API Investigation

### GitPython's create_head Signature

```python
Repo.create_head(
    path: PathLike,
    commit: Union[SymbolicReference, str] = 'HEAD',  # Default is HEAD!
    force: bool = False,
    logmsg: Optional[str] = None
) -> Head
```

**Key Finding:** GitPython itself defaults to `commit='HEAD'`, NOT `'main'`!

**Our Implementation:**
```python
def create_branch(self, branch_name: str, base: str = "main"):
    new_branch = self.repo.create_head(branch_name, base)
```

We override GitPython's sensible default with our own broken default!

---

## Logging Analysis

### Current State: NO LOGGING

**Files checked:**
- ✅ `mcp_server/core/logging.py` - Logging infrastructure EXISTS
- ✅ `logs/mcp_audit.log` - File logging configured
- ❌ `mcp_server/adapters/git_adapter.py` - NO logging imports
- ❌ `mcp_server/managers/git_manager.py` - NO logging imports
- ❌ `mcp_server/tools/git_tools.py` - NO logging imports

### Logging Infrastructure Available

```python
# mcp_server/core/logging.py
class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
def setup_logging() -> None:
    """Configure logging based on settings."""
    # Console handler (stderr)
    # File handler (logs/mcp_audit.log)

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"mcp_server.{name}")
```

### What We Missed (Issue #62 & #63)

**With logging, we would have seen:**
```json
{
  "timestamp": "2025-12-29T17:15:00",
  "level": "INFO",
  "logger": "mcp_server.managers.git_manager",
  "message": "Creating branch fix/62-phase-agnostic-tests",
  "props": {
    "branch_name": "fix/62-phase-agnostic-tests",
    "branch_type": "fix",
    "base_branch": "main",
    "current_branch": "refactor/51-labels-yaml"
  }
}
```

The mismatch between `base_branch: "main"` and `current_branch: "refactor/51-labels-yaml"` would have been immediately visible!

---

## Findings Summary

### Problem 1: Incorrect Default Base
- **Current:** `base: str = "main"` (hardcoded)
- **Git standard:** Defaults to HEAD
- **GitPython API:** Defaults to HEAD
- **Our code:** Violates both standards

### Problem 2: Misleading Tool Name
- **Current:** `create_feature_branch`
- **Reality:** Creates feature, fix, refactor, docs branches
- **Git analogy:** Git has `git branch`, not `git feature-branch`

### Problem 3: Implicit Defaults Unsafe
- **Philosophy:** MCP tools are for agents, not interactive humans
- **Agents need:** Explicit parameters (self-documenting)
- **Current:** No way to specify base branch (missing parameter)

### Problem 4: No Logging
- **Infrastructure:** Exists and configured
- **Usage:** Completely absent in git tools
- **Impact:** Blind to branching behavior (as seen in #62 and #63)

### Real-World Impact
- **Issue #62:** fix/62 branched from main instead of refactor/51
- **Issue #63:** fix/63 initially branched from main instead of refactor/51
- **Root cause:** Implicit default + no logging = invisible failure

---

## Recommendations

### Option A: Follow Git Standard (HEAD default)
```python
def create_branch(self, branch_name: str, base: str = "HEAD") -> None:
```
**Pros:** Consistent with git behavior  
**Cons:** Still implicit default (against our philosophy)

### Option B: Fully Explicit (RECOMMENDED)
```python
# Adapter
def create_branch(self, branch_name: str, base: str) -> None:  # NO DEFAULT

# Manager  
def create_branch(self, name: str, branch_type: str, base_branch: str) -> str:

# Tool
class CreateBranchInput(BaseModel):
    name: str = Field(...)
    branch_type: str = Field(default="feature", ...)
    base_branch: str = Field(..., description="Base: 'HEAD', branch name, or commit")
```

**Pros:**
- Forces conscious decision
- Self-documenting code
- Prevents silent failures
- Consistent with agent-first philosophy

**Cons:**
- Less "convenient" than git CLI
- Breaking change (acceptable - tool is already broken)

### Why Option B for MCP Tools

**Humans vs Agents:**
- **Humans:** Context-aware, visual feedback, interactive → convenience valuable
- **Agents:** Stateless, script-based, no visual context → explicitness valuable

**Example:**
```python
# Unclear with defaults:
create_branch("fix-63", "fix")  # From where? 

# Crystal clear with explicit params:
create_branch("fix-63", "fix", base_branch="refactor/51-labels-yaml")
```

### Logging Additions

Add structured logging at all 3 layers:

**Adapter (technical):**
```python
logger.debug("Creating git branch", extra={"props": {
    "branch_name": branch_name,
    "base": base,
    "current_head": self.repo.head.commit.hexsha
}})
```

**Manager (business logic):**
```python
logger.info("Creating feature branch", extra={"props": {
    "full_name": full_name,
    "branch_type": branch_type,
    "base_branch": base_branch,
    "current_branch": self.adapter.get_current_branch()
}})
```

**Tool (user interaction):**
```python
logger.info("Branch creation requested", extra={"props": {
    "name": params.name,
    "type": params.branch_type,
    "base": params.base_branch
}})
```

### Tool Rename

**Current:** `create_feature_branch`  
**Proposed:** `create_branch`

Matches functionality (all branch types) and follows git naming conventions.

---

## Next Steps

1. **Planning Phase:** Create detailed implementation plan
2. **TDD Phase:** Write tests first (RED)
3. **Implementation:** Apply fixes with logging
4. **Integration:** Update all callers
5. **Documentation:** Update tool documentation

**Breaking Change Notice:** This is a breaking change - all existing callers must be updated to provide `base_branch` parameter.

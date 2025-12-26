# Issue #50 Discovery: Workflow Configuration System

**Status:** IN PROGRESS
**Issue:** #50 - Config: Workflow Configuration System (workflows.yaml)
**Parent:** Epic #49 - MCP Platform Configurability
**Phase:** Discovery/Research
**Date:** 2025-12-26

---

## Purpose

Research and document current PHASE_TEMPLATES implementation, usage patterns, coding standards, and requirements for migration to workflows.yaml configuration.

**Research Focus:** Objective observation of existing code, not design proposals.

## Scope

**In Scope:**
- Current PHASE_TEMPLATES structure and usage
- Execution mode requirements (from Issue #42)
- Phase transition behavior
- Existing coding patterns (Enums, Pydantic, error handling)
- Success criteria

**Out of Scope:**
- YAML schema design (belongs in Planning)
- Pydantic model design (belongs in Planning)
- Implementation details (belongs in TDD)
- Validation rules configuration (Issue #52/53/54)

---

## 1. Current State Analysis

### 1.1 PHASE_TEMPLATES Location

**File:** `mcp_server/managers/project_manager.py` (lines 11-39)

**Structure:**
```python
PHASE_TEMPLATES = {
    "feature": {
        "required_phases": ("discovery", "planning", "design", "component", "tdd", "integration", "documentation"),
        "description": "Full 7-phase workflow for new features"
    },
    "bug": {
        "required_phases": ("discovery", "planning", "component", "tdd", "integration", "documentation"),
        "description": "6-phase workflow (skip design)"
    },
    "docs": {
        "required_phases": ("discovery", "planning", "component", "documentation"),
        "description": "4-phase workflow (skip tdd + integration)"
    },
    "refactor": {
        "required_phases": ("discovery", "planning", "tdd", "integration", "documentation"),
        "description": "5-phase workflow (skip design + component)"
    },
    "hotfix": {
        "required_phases": ("component", "tdd", "integration"),
        "description": "Minimal 3-phase workflow (requires approval for all operations)"
    }
}
```

### 1.2 Data Structure

**Per Template:**
- **`required_phases`**: `tuple[str, ...]` - Ordered phase sequence
- **`description`**: `str` - Human-readable workflow description

**Missing:**
- Execution mode specification
- Phase transition rules
- Validation settings
- Custom metadata

### 1.3 Issue Types

**Current:** 5 predefined + 1 custom
- `feature` (7 phases)
- `bug` (6 phases)
- `docs` (4 phases)
- `refactor` (5 phases)
- `hotfix` (3 phases)
- `custom` (user-defined)

---

## 2. Usage Patterns

### 2.1 Where PHASE_TEMPLATES is Used

**Finding:** PHASE_TEMPLATES is used **ONLY** during project initialization. After initialization, stored data in `.st3/projects.json` is used exclusively.

#### A. ProjectManager.initialize_project()

**Location:** `project_manager.py:78-140`

**Operations:**
1. Validate `issue_type` against `PHASE_TEMPLATES.keys()`
2. Read `template["required_phases"]`
3. Read `template["description"]`
4. Create `ProjectPlan` with copied data
5. Store in `.st3/projects.json`

**Code:**
```python
valid_types = list(PHASE_TEMPLATES.keys()) + ["custom"]
if issue_type not in valid_types:
    raise ValueError(f"Invalid issue_type: {issue_type}...")

template = PHASE_TEMPLATES[issue_type]
required_phases = tuple(template["required_phases"])
```

#### B. InitializeProjectTool

**Location:** `mcp_server/tools/project_tools.py`

**Purpose:** MCP protocol wrapper for `ProjectManager.initialize_project()`

#### C. After Initialization

**Key Finding:** PHASE_TEMPLATES is **never referenced again**:
- `PhaseStateEngine` → reads `.st3/state.json`
- `PolicyEngine` → reads `.st3/projects.json`
- No validation against original templates

### 2.2 Data Flow

```
User/Agent
    ↓
InitializeProjectTool
    ↓
ProjectManager.initialize_project()
    ↓ (READS PHASE_TEMPLATES - only time)
Creates ProjectPlan
    ↓
Stores in .st3/projects.json
    ↓
// PHASE_TEMPLATES never used again
    ↓
PolicyEngine → validates against stored plan
PhaseStateEngine → tracks transitions
```

---

## 3. Coding Standards Research

### 3.1 Enum vs Literal Usage

**Finding:** Codebase **does NOT use Enums**. Uses `Literal` type hints instead.

**Example:** `mcp_server/tools/issue_tools.py`
```python
from typing import Literal

IssueState = Literal["open", "closed", "all"]
```

**Guidance (from `docs/architecture/ARCHITECTURAL_SHIFTS.md`):**
- **Use Enum when:** Type safety and exhaustive checking critical
- **Use Literal when:** Runtime flexibility needed (e.g., plugin-based systems)

**Pattern for Issue #50:**
- Issue types: Could use `IssueType = Literal["feature", "bug", "docs", "refactor", "hotfix", "custom"]`
- Phase names: Could use `Phase = Literal["discovery", "planning", ...]`
- Execution modes: Could use `ExecutionMode = Literal["autonomous", "interactive"]`

### 3.2 Pydantic BaseModel Patterns

**Reference:** `mcp_server/config/settings.py`

**Pattern 1: Nested Models**
```python
class LogSettings(BaseModel):
    level: str = "INFO"
    audit_log: str = "logs/mcp_audit.log"

class ServerSettings(BaseModel):
    name: str = "st3-workflow"
    version: str = "1.0.0"
    workspace_root: str = Field(default_factory=os.getcwd)

class Settings(BaseModel):
    server: ServerSettings = ServerSettings()
    logging: LogSettings = LogSettings()
```

**Pattern 2: Class Method Loader**
```python
@classmethod
def load(cls, config_path: str | None = None) -> "Settings":
    """Load settings from YAML file."""
    path = Path(config_path or os.environ.get("MCP_CONFIG_PATH", "mcp_config.yaml"))
    
    if path.exists():
        with open(path, encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}
    
    return cls(**config_data)
```

**Pattern 3: Global Instance**
```python
# Global settings instance
settings = Settings.load()
```

**Pattern 4: Field Validators**

From `mcp_server/tools/safe_edit_tool.py`:
```python
class LineEdit(BaseModel):
    start_line: int = Field(..., description="Starting line number")
    end_line: int = Field(..., description="Ending line number")

    @model_validator(mode='after')
    def validate_line_range(self) -> "LineEdit":
        if self.start_line < 1:
            raise ValueError("start_line must be >= 1")
        if self.start_line > self.end_line:
            raise ValueError("start_line must be <= end_line")
        return self
```

**Pattern 5: Field Patterns**
```python
mode: str = Field(
    default="strict",
    pattern="^(strict|interactive|verify_only)$"
)
```

### 3.3 Module Structure

**Current Config Directory:**
```
mcp_server/config/
├── __init__.py
└── settings.py       # Single settings file
```

**Loading Pattern:**
- Settings loaded **once** at module import
- Global instance: `settings = Settings.load()`
- Accessed via: `from mcp_server.config.settings import settings`

**For Issue #50:**
- New file: `mcp_server/config/workflow_config.py`
- Pattern: `workflow_config = WorkflowConfig.load()`

### 3.4 Error Handling

**Custom Exception Hierarchy:** `mcp_server/exceptions.py`

```python
class MCPError(Exception):
    """Base class."""
    def __init__(self, message: str, code: str, hints: list[str] | None = None):
        self.message = message
        self.code = code
        self.hints = hints or []

class ValidationError(MCPError):
    """Input validation fails."""
    def __init__(self, message: str, hints: list[str] | None = None):
        super().__init__(message, code="ERR_VALIDATION", hints=hints)
```

**Usage Pattern:**
```python
if branch_type not in ["feature", "fix", "refactor", "docs"]:
    raise ValidationError(
        f"Invalid branch type: {branch_type}",
        hints=["Use feature, fix, refactor, or docs"]
    )
```

**For Issue #50:**
- Use `ValidationError` for invalid config YAML
- Provide hints for common mistakes
- Fail fast at config load time

### 3.5 Constants Management

**Pattern 1: Module-Level Dict Constants**
```python
PHASE_TEMPLATES = {
    "feature": {...},
    "bug": {...}
}
```

**Pattern 2: Type Alias Constants**
```python
IssueState = Literal["open", "closed", "all"]
```

**Pattern 3: Inline Constants with Validation**
```python
protected_branches = ["main", "master", "develop"]
if branch_name in protected_branches:
    raise ValidationError(...)
```

**For Issue #50:** Replace module-level dict with YAML + Pydantic loader

---

## 4. Missing Capabilities

### 4.1 Execution Modes

**Requirement (from Issue #42):**
- **Autonomous Mode**: Agent-driven, rigid sequential phases
- **Interactive Mode**: Human-in-the-loop, flexible workflow

**Current State:** NO execution mode support found

**What Exists:**
- `human_approval: str | None` in transitions (audit trail only)
- `PolicyDecision.requires_human_approval: bool` (policy violation flag)

**What's Missing:**
- No mode configuration
- No mode-aware PolicyEngine
- No automatic vs manual distinction
- No mode selection at initialization

### 4.2 Phase Transitions

**Current State:** `PhaseStateEngine` allows **ANY** transition

**Validation:**
- ✅ `from_phase` must match current state
- ❌ No `to_phase` validation
- ❌ No transition graph
- ❌ No sequential enforcement

**Example:**
```python
# This SUCCEEDS (no graph validation):
engine.transition(branch="feature/42", from_phase="discovery", to_phase="integration")
# Skips planning, design, component, tdd
```

**Issue #42 Need:** Enforce sequential transitions in autonomous mode

### 4.3 Validation Configuration

**Observation:** Validation rules (TDD prefixes, scaffold phases, file policies) are hardcoded in:
- `policy_engine.py` - TDD commit prefixes
- `policy_engine.py` - Scaffold phases
- `git_manager.py` - Branch types

**Clarification for 5.5:** 
- **workflows.yaml** should define ONLY phase sequences and execution modes
- **Validation rules** belong in separate configs (Issues #52, #53, #54)
- No overlap - clean separation of concerns

---

## 5. Requirements Analysis

### 5.1 Must Support (Current Functionality)

1. **5 Predefined Issue Types**
   - feature, bug, docs, refactor, hotfix

2. **Custom Issue Type**
   - User-defined phase sequence

3. **Phase Sequences**
   - Required phases per type
   - Phase ordering

4. **Descriptions**
   - Human-readable workflow descriptions

### 5.2 Must Add (Issue #42)

1. **Execution Modes**
   - Autonomous: rigid, sequential
   - Interactive: flexible, approval-based

2. **Phase Transitions**
   - Define allowed transitions per type
   - Enforce sequential in autonomous mode
   - Allow flexible in interactive mode

3. **Mode Configuration**
   - Selected at project initialization
   - Stored in project plan

### 5.3 Out of Scope

**Explicitly NOT in workflows.yaml:**
- Validation rules → Issue #52 (validation.yaml)
- Quality gates → Issue #53 (quality.yaml)
- Scaffold rules → Issue #54 (scaffold.yaml)
- Git conventions → Issue #55 (git.yaml)
- Phase-specific tooling requirements

**Rationale:** Clean separation - workflows define WHAT phases exist, other configs define HOW to validate/execute within those phases.

---

## 6. Success Criteria

**Discovery Phase Complete When:**
- [x] PHASE_TEMPLATES structure documented
- [x] Usage patterns identified
- [x] Coding standards researched
- [x] Missing capabilities identified
- [x] Requirements documented
- [ ] Open questions listed for Planning

**Overall Issue #50 Success:**
- [ ] All PHASE_TEMPLATES functionality migrated to workflows.yaml
- [ ] Execution modes supported (autonomous/interactive)
- [ ] Phase transitions configurable
- [ ] No hardcoded workflow logic in Python
- [ ] Pydantic validation enforces schema
- [ ] All tests passing
- [ ] Config loaded at startup (fail fast)

---

## Open Questions for Planning

### Q1: Execution Mode Selection

How is execution mode chosen?
- Option A: Per-project at initialization (recommended)
- Option B: Changeable per phase
- Option C: Global setting

### Q2: Transition Graph Flexibility

For autonomous mode:
- Option A: Strict sequential only
- Option B: Allow defined jumps
- Option C: Fully flexible (current)

Recommendation: A for autonomous, C for interactive

### Q3: Custom Workflow Support

Should custom workflows be:
- Pre-defined in YAML?
- Programmatically via API (current)?
- Both?

Recommendation: Support both

### Q4: Literal vs Enum

For type safety:
- Use `Literal` (matches codebase pattern)?
- Use `Enum` (stronger type safety)?

Recommendation: `Literal` (consistency with existing patterns)

### Q5: Config Loading

When to load workflows.yaml:
- Startup (global instance pattern)?
- Per-request (lazy loading)?

Recommendation: Startup with global instance (matches settings pattern)

---

## Next Steps

**Planning Phase:**
1. Answer open questions
2. Design YAML schema structure
3. Design Pydantic models (WorkflowConfig, ExecutionMode, Transitions)
4. Define migration strategy
5. Create implementation plan

**NOT in Discovery:**
- Concrete YAML examples (belongs in Planning)
- Pydantic class definitions (belongs in Planning)
- Implementation details (belongs in TDD)

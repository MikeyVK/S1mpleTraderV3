# Issue #50 Discovery: Workflow Configuration System

**Status:** IN PROGRESS
**Author:** AI Agent
**Created:** 2025-12-26
**Issue:** #50 - Config: Workflow Configuration System (workflows.yaml)
**Parent:** Epic #49 - MCP Platform Configurability

---

## 1. Current PHASE_TEMPLATES Analysis

### 1.1 Location & Structure

**File:** `mcp_server/managers/project_manager.py` (lines 11-39)

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

### 1.2 Fields Per Template

| Field | Type | Purpose |
|-------|------|---------|
| `required_phases` | `tuple[str, ...]` | Ordered sequence of phases for issue type |
| `description` | `str` | Human-readable workflow description |

**Missing Fields:**
- No execution mode (autonomous vs interactive)
- No phase transition rules
- No validation settings
- No custom metadata

---

## 2. Usage Patterns

### 2.1 Where is PHASE_TEMPLATES Used?

**Summary:** Used ONLY during project initialization, then stored data takes over.

#### A. ProjectManager.initialize_project()

**Location:** `project_manager.py:78-140`

**Usage:**
1. Validate `issue_type` in `PHASE_TEMPLATES.keys()`
2. Read `template["required_phases"]`
3. Read `template["description"]`
4. Create `ProjectPlan` with copied data
5. Store in `.st3/projects.json`

**Code:**
```python
# Validate issue type
valid_types = list(PHASE_TEMPLATES.keys()) + ["custom"]
if issue_type not in valid_types:
    raise ValueError(f"Invalid issue_type: {issue_type}...")

# Copy template data
template = PHASE_TEMPLATES[issue_type]
required_phases = tuple(template["required_phases"])
```

#### B. InitializeProjectTool

**Location:** `mcp_server/tools/project_tools.py`

**Usage:**
- Wraps `ProjectManager.initialize_project()`
- Adds `description` to tool response
- Exposes via MCP protocol

#### C. After Initialization

**CRITICAL Finding:** PHASE_TEMPLATES is **NEVER** referenced again after `initialize_project()`:
- PhaseStateEngine uses stored state (`.st3/state.json`)
- PolicyEngine uses stored plan (`.st3/projects.json`)
- No validation against original templates

### 2.2 Data Flow

```
User/Agent
    ↓
InitializeProjectTool
    ↓
ProjectManager.initialize_project()
    ↓ (reads PHASE_TEMPLATES)
Creates ProjectPlan
    ↓
Stores in .st3/projects.json
    ↓
// PHASE_TEMPLATES never used again
    ↓
PolicyEngine validates against stored plan
PhaseStateEngine tracks transitions in state
```

---

## 3. Missing Capabilities (Issue #42 Requirements)

### 3.1 Execution Modes

**Requirement (from Issue #42):**
- **Autonomous Mode**: Agent-driven, rigid phase sequence, automatic execution
- **Interactive Mode**: Human-in-the-loop, flexible, requires approval

**Current State:** NO execution mode distinction found in code

**What EXISTS:**
- `human_approval` field in transitions (audit trail only)
- `PolicyDecision.requires_human_approval` flag (policy violation signal)

**What's MISSING:**
- No mode configuration (autonomous/interactive flag)
- No mode-aware PolicyEngine rules
- No automatic vs manual execution distinction
- No mode selection at initialization

### 3.2 Phase Transitions

**Current State:** PhaseStateEngine allows ANY phase transition

**Validation:**
- ✅ From-phase must match current state
- ❌ No target phase validation
- ❌ No transition graph (allowed paths)
- ❌ No sequential enforcement

**Example:**
```python
# This is ALLOWED (no graph validation):
engine.transition(branch="feature/42", from_phase="discovery", to_phase="integration")
# ✅ Success - skips planning, design, component, tdd phases
```

**Issue #42 Requirement:** Enforce sequential transitions in autonomous mode

### 3.3 Validation Settings

**Current State:** PolicyEngine has hardcoded validation rules

**Examples:**
- TDD commit prefixes hardcoded (`red:`, `green:`, `refactor:`)
- Scaffold phases hardcoded (`component`, `tdd`)
- File policies hardcoded

**Missing:** Per-workflow validation configuration

---

## 4. Requirements for workflows.yaml

### 4.1 Must Support (Current Functionality)

1. **Issue Types**
   - 5 predefined: feature, bug, docs, refactor, hotfix
   - 1 custom (user-defined phases)

2. **Phase Sequences**
   - Required phases per issue type
   - Phase ordering

3. **Descriptions**
   - Human-readable workflow descriptions

4. **Backward Compatibility**
   - None needed (no enforced projects in production)

### 4.2 Must Add (Issue #42 Requirements)

1. **Execution Modes**
   ```yaml
   feature:
     execution_mode: autonomous  # or interactive
     required_phases: [...]
   ```

2. **Phase Transitions**
   ```yaml
   feature:
     transitions:
       discovery: [planning]  # Only planning allowed after discovery
       planning: [design]
       design: [component]
       # etc.
   ```

3. **Mode-Specific Behaviors**
   ```yaml
   autonomous:
     enforce_sequential: true
     require_approval: false
   interactive:
     enforce_sequential: false
     require_approval: true
   ```

### 4.3 Nice to Have

1. **Phase Metadata**
   ```yaml
   phases:
     discovery:
       description: "Research and planning"
       min_duration: null
       max_duration: null
   ```

2. **Validation Configuration**
   ```yaml
   feature:
     validations:
       quality_gates: required
       test_coverage: 80
   ```

3. **Custom Fields**
   ```yaml
   feature:
     custom:
       team: backend
       priority: high
   ```

---

## 5. Open Questions

### 5.1 Execution Mode Selection

**Question:** How is execution mode selected?
- **Option A:** At project initialization (fixed for entire workflow)
- **Option B:** Changeable per phase
- **Option C:** Global setting (all projects same mode)

**Recommendation:** Option A (per-project, set at initialization)

### 5.2 Transition Graph Flexibility

**Question:** Should transition graph be:
- **Option A:** Strict sequential only (discovery → planning → design)
- **Option B:** Allow defined jumps (discovery → [planning, design])
- **Option C:** Fully flexible with no restrictions

**Current:** Option C exists
**Issue #42:** Wants Option A for autonomous mode

**Recommendation:** Mode-dependent (A for autonomous, C for interactive)

### 5.3 Custom Workflow Support

**Question:** How flexible should custom workflows be?

**Current:**
```python
initialize_project(
    issue_type="custom",
    custom_phases=("phase1", "phase2", "phase3")
)
```

**Future with Config:**
- Should custom workflows be pre-defined in YAML?
- Or still programmatically via API?

**Recommendation:** Support both (pre-defined templates + runtime custom)

### 5.4 Phase Name Standardization

**Issue #42 Concern:** Phase names contradict TDD (tdd vs red/green/refactor)

**Question:** Should workflows.yaml:
- Define both old and new phase names?
- Include migration path?
- Support aliases?

**Recommendation:** Address in Issue #42 implementation, not here

### 5.5 Validation Integration

**Question:** Should workflows.yaml include validation rules?

**Example:**
```yaml
feature:
  phases: [...]
  validations:
    tdd:
      - require_commit_prefix: true
      - require_tests: true
```

**Recommendation:** NO - keep validation in separate config (Issue #52/53/54)

---

## 6. Proposed YAML Schema (Draft)

```yaml
# config/workflows.yaml

workflows:
  feature:
    description: "Full 7-phase workflow for new features"
    execution_mode: autonomous  # NEW
    required_phases:
      - discovery
      - planning
      - design
      - component
      - tdd
      - integration
      - documentation
    transitions:  # NEW - optional, for strict mode
      discovery: [planning]
      planning: [design]
      design: [component]
      component: [tdd]
      tdd: [integration]
      integration: [documentation]
      documentation: []  # terminal state
  
  bug:
    description: "6-phase workflow (skip design)"
    execution_mode: autonomous
    required_phases:
      - discovery
      - planning
      - component
      - tdd
      - integration
      - documentation
    transitions:
      discovery: [planning]
      planning: [component]
      component: [tdd]
      tdd: [integration]
      integration: [documentation]
      documentation: []
  
  # ... other issue types

execution_modes:  # NEW - mode definitions
  autonomous:
    enforce_sequential: true
    require_approval: false
    description: "Agent-driven with strict phase enforcement"
  
  interactive:
    enforce_sequential: false
    require_approval: true
    description: "Human-in-the-loop with flexible workflow"
```

---

## 7. Migration Impact

### 7.1 Files to Modify

| File | Changes Required |
|------|------------------|
| `project_manager.py` | Remove PHASE_TEMPLATES, load from config |
| `mcp_server/config/workflow_config.py` | NEW - Pydantic models + loader |
| `phase_state_engine.py` | Add transition graph validation |
| `policy_engine.py` | Add mode-aware validation |
| `project_tools.py` | Update to use WorkflowConfig |

### 7.2 Backward Compatibility

**None needed** - no enforced projects exist in production

**Strategy:** Fail fast if `config/workflows.yaml` missing

---

## 8. Success Criteria

- [ ] All PHASE_TEMPLATES functionality migrated
- [ ] Execution modes supported (autonomous/interactive)
- [ ] Phase transitions configurable
- [ ] No hardcoded workflow logic in Python
- [ ] Pydantic validation enforces schema
- [ ] All tests passing

---

## Next Steps

1. **Planning Phase:**
   - Finalize YAML schema design
   - Design Pydantic models
   - Define migration strategy

2. **TDD Phase:**
   - Write tests for config loading
   - Write tests for execution modes
   - Write tests for transition validation
   - Implement WorkflowConfig
   - Update ProjectManager
   - Update PhaseStateEngine

3. **Integration Phase:**
   - End-to-end workflow tests
   - Verify no hardcoded PHASE_TEMPLATES remains

4. **Documentation Phase:**
   - Config reference documentation
   - Execution mode guide

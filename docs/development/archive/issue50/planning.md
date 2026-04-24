# Issue #50 Planning: Workflow Configuration System

**Status:** DRAFT  
**Version:** 0.1  
**Last Updated:** 2025-12-27

---

## Purpose

Planning document for migrating hardcoded PHASE_TEMPLATES dict to workflows.yaml configuration file. This document makes key decisions (answers 5 open questions from discovery), defines work breakdown, establishes implementation sequence, and estimates timeline.

**Critical Boundary**: This document defines **WHAT** and **WHEN**, NOT **HOW**. Concrete schemas, Pydantic models, and implementation details belong in [design.md](design.md).

## Scope

**In Scope:**
- Answering 5 open questions from discovery (execution modes, transition graphs, custom workflows, type hints, loading strategy)
- Work breakdown (list of tasks for design/TDD/integration phases)
- Implementation sequence (order of work)
- Timeline estimates

**Out of Scope:**
- Concrete YAML schema structure → design.md
- Pydantic model definitions → design.md
- Class diagrams → design.md
- Migration code details → TDD phase

## Prerequisites

- [discovery.md](discovery.md) - Research complete (PHASE_TEMPLATES usage, coding standards, requirements)

---

## 1. Decision Log

### Decision 1.1: Execution Mode Selection

**Question**: Should execution mode selection be per-project, per-phase, or global?

**Options**:
- **A. Per-Project**: Each issue chooses mode at initialization
- **B. Per-Phase**: Each phase can use different mode
- **C. Global**: Single mode for entire server

**Decision**: **Option A - Per-Project**

**Rationale**:
- Matches existing pattern (initialization sets project context once)
- Most flexible (hotfix = autonomous, feature = interactive)
- Simpler state management (no mode switching mid-project)
- Aligns with Config Over Code (workflow defines defaults, project overrides)

**Consequences**:
- WorkflowConfig needs `default_execution_mode` field
- ProjectManager.initialize() takes optional `execution_mode` param
- `.st3/projects.json` stores mode per project
- PhaseStateEngine reads mode from project context, not config

---

### Decision 1.2: Transition Graph Flexibility

**Question**: Should phase transitions be strictly sequential, allow jumps, or fully flexible?

**Options**:
- **A. Strict Sequential**: Only next phase allowed (discovery → planning, planning → design, etc.)
- **B. Allow Jumps**: Can skip phases (discovery → design if planning not needed)
- **C. Fully Flexible**: Any transition allowed (current behavior)

**Decision**: **Option A - Strict Sequential (separate tool for non-standard transitions)**

**Rationale**:
- Enforces workflow discipline (matches user's "niet op een bierviltje" philosophy)
- Prevents accidental phase skips
- **Security model**: Standard transitions vs dangerous operations
  - `transition_phase`: Always allowed within session (strict sequential only)
  - `force_phase_transition`: Requires per-use human approval (skip/jump capability)
- Clear separation between normal flow and exceptional cases

**Consequences**:
- WorkflowConfig has `phases: list[str]` defining sequence
- PhaseStateEngine validates transition against workflow graph
- **Two separate tools**:
  - `transition_phase(to_phase)`: Only allows next phase in sequence
  - `force_phase_transition(to_phase, reason)`: Allows any transition, requires explicit approval
- Transition validation checks current_phase index vs target_phase index
- Force transitions marked with `forced: true` flag in transitions array

**Example**:
```yaml
# Strict sequential: feature workflow
phases: [discovery, planning, design, tdd, integration, documentation]
# transition_phase("planning") from discovery ✅ (next phase)
# transition_phase("design") from discovery ❌ (not next phase)
# force_phase_transition("design", "Planning not needed for hotfix") ✅ (with approval)
```

---

### Decision 1.3: Custom Workflow Support

**Question**: Should custom workflows be pre-defined only, programmatically created, or both?

**Options**:
- **A. Pre-Defined Only**: workflows.yaml has fixed list (feature, bug, hotfix, refactor, docs)
- **B. Programmatic API**: Code can create workflows dynamically
- **C. Both**: YAML for defaults, API for edge cases

**Decision**: **Option A - Pre-Defined Only (consistent with Decision 1.2 security model)**

**Rationale**:
- **Security model alignment**: Same principle as Decision 1.2
  - Standard workflows (pre-defined) = normal operations
  - Custom workflows (if needed) = exceptional operations requiring YAML edit + restart
- Matches Config Over Code principle (YAML is SSOT)
- Prevents ad-hoc workflow creation during session (discipline enforcement)
- Unknown workflows blocked at initialization (fail fast, not fallback)
- Edge cases: Edit workflows.yaml, restart server (deliberate action)

**Consequences**:
- WorkflowConfig.workflows: Dict[str, WorkflowTemplate] loaded from YAML
- ProjectManager.initialize() **rejects** unknown workflow names (ValidationError)
- No programmatic workflow creation API
- No fallback workflow (forces explicit YAML definition)
- To add workflow: Edit YAML → restart server → initialize with new workflow name

**Example**:
```python
# Standard workflow (allowed)
initialize_project(issue_number=50, workflow_name="feature")  # ✅

# Unknown workflow (rejected)
initialize_project(issue_number=60, workflow_name="custom-flow")  # ❌ ValidationError

# To use custom workflow:
# 1. Edit workflows.yaml, add "custom-flow" definition
# 2. Restart MCP server
# 3. initialize_project(issue_number=60, workflow_name="custom-flow")  # ✅
```

---

### Decision 1.4: Type Hints Approach

**Question**: Use Literal for constants vs Enum vs Config as SSOT?

**Options**:
- **A. Literal**: `phase: Literal["discovery", "planning", ...]`
- **B. Enum**: `class Phase(Enum): DISCOVERY = "discovery"`
- **C. Config as SSOT**: Load valid values from workflows.yaml

**Decision**: **Option C - Config as SSOT (with Literal for IDE support)**

**Rationale**:
- User feedback: "Laat enums maar achterwege"
- Codebase pattern: No Enums used anywhere
- Config Over Code: YAML defines valid phases, not code
- IDE support: Use Literal in type hints, validate dynamically against config

**Consequences**:
- Type hints: `phase: str` (not Literal, since values come from config)
- Runtime validation: `WorkflowConfig.validate_phase(phase)` checks against loaded workflows
- IDE autocomplete sacrificed for flexibility
- No hardcoded phase constants in code

**Example**:
```python
# NO:
class Phase(str, Enum):
    DISCOVERY = "discovery"
    
# NO:
PhaseType = Literal["discovery", "planning", "design", ...]

# YES:
def transition_phase(branch: str, to_phase: str):  # str, not Literal
    workflow = get_workflow(branch)
    if to_phase not in workflow.phases:
        raise ValidationError(...)
```

---

### Decision 1.5: Config Loading Strategy

**Question**: Load configuration at startup or lazily on first use?

**Options**:
- **A. Startup**: Load workflows.yaml during server initialization
- **B. Lazy**: Load when first workflow operation happens
- **C. Hybrid**: Load at startup, cache, reload on change

**Decision**: **Option A - Startup**

**Rationale**:
- Fail fast (config errors detected immediately, not mid-operation)
- Matches existing pattern (settings.py loads at import time)
- Simpler state management (single load point)
- Performance not critical (config loaded once per server start)

**Consequences**:
- WorkflowConfig singleton initialized at module import
- Config errors crash server startup (visible immediately)
- No hot-reload (server restart required for config changes)
- `.load()` classmethod pattern (matches Settings.load())

**Example**:
```python
# mcp_server/config/workflows.py
class WorkflowConfig(BaseModel):
    @classmethod
    def load(cls, path: Path = DEFAULT_PATH) -> "WorkflowConfig":
        ...
        
workflow_config = WorkflowConfig.load()  # Module-level init
```

---

## 2. Work Breakdown

### Phase: Design

**Tasks**:
1. Define workflows.yaml schema structure (YAML format)
2. Design Pydantic models (WorkflowConfig, WorkflowTemplate, ExecutionMode)
3. Design validation rules (phase sequences, transition graphs)
4. Design migration strategy (update ProjectManager, PhaseStateEngine)
5. Create class diagrams (config loading flow, validation flow)
6. Define error messages (validation failures, migration errors)

**Deliverable**: [design.md](design.md) with complete schemas and architecture

---

### Phase: TDD

**Tasks**:
1. **RED**: Write test_workflow_config.py (loading, validation, CRUD)
2. **RED**: Write test_project_manager_workflows.py (initialization with workflows)
3. **RED**: Write test_phase_state_transitions.py (strict sequential validation)
4. **RED**: Write test_phase_state_force_transitions.py (force transition mechanism)
5. **GREEN**: Implement WorkflowConfig + Pydantic models
6. **GREEN**: Update ProjectManager.initialize() (workflow param, validation)
7. **GREEN**: Update PhaseStateEngine.transition() (strict graph validation)
8. **GREEN**: Add PhaseStateEngine.force_transition() (any transition with flag)
9. **REFACTOR**: Extract validation logic, optimize lookups

**Deliverable**: Passing tests + implementation

---

### Phase: Integration

**Tasks**:
1. Create workflows.yaml with 5 default workflows (feature, bug, hotfix, refactor, docs)
2. Migrate existing projects to new format (`.st3/projects.json` updates)
3. Update initialize_project tool (add workflow_name param)
4. Keep transition_phase tool strict (no skip parameter, next phase only)
5. **NEW**: Create force_phase_transition tool (skip/jump capability, requires approval)
6. Smoke test existing branches (fix/42, feature/38, refactor/49, refactor/50)
7. Update error messages in tools

**Deliverable**: Working system with all tools updated

---

### Phase: Documentation

**Tasks**:
1. Update [USAGE.md](../../USAGE.md) (workflow selection examples)
2. Update [ARCHITECTURE.md](../../ARCHITECTURE.md) (WorkflowConfig section)
3. Create [WORKFLOWS.md](../../WORKFLOWS.md) (workflow definitions reference)
4. Update tool docstrings (initialize_project, transition_phase, force_phase_transition)
5. Add YAML comments (workflows.yaml inline documentation)
6. Document security model (when to use transition_phase vs force_phase_transition)

**Deliverable**: Complete user + developer documentation

---

## 3. Implementation Sequence

**Rationale**: Bottom-up approach (models → managers → tools → docs)

### Step 1: Design Phase (2 days)
- Define all schemas and models
- No code implementation yet
- Output: design.md

### Step 2: TDD Phase - Models (1 day)
- WorkflowConfig loading + validation
- Pydantic models + validators
- Unit tests for config layer

### Step 3: TDD Phase - Managers (1.5 days)
- ProjectManager updates (workflow integration)
- PhaseStateEngine updates (transition validation)
- Integration tests for manager layer

### Step 4: TDD Phase - Force Transitions (0.5 days)
- Force transition mechanism implementation (separate from standard transition)
- Edge case handling (unknown workflows, invalid transitions)
- End-to-end tests for both standard and forced transitions

### Step 5: Integration Phase (1 day)
- workflows.yaml creation
- Tool updates (initialize_project, transition_phase strict validation, new force_phase_transition)
- Migration of existing projects
- Smoke tests

### Step 6: Documentation Phase (1 day)
- User docs (USAGE.md, WORKFLOWS.md)
- Developer docs (ARCHITECTURE.md)
- Tool docstrings

**Total Estimated: 7 days**

---

## 4. Timeline & Milestones

### Milestone 1: Planning Complete ✅
- **Date**: 2025-12-27
- **Criteria**: All 5 decisions made, work breakdown defined
- **Status**: IN PROGRESS

### Milestone 2: Design Complete
- **Date**: 2025-12-29 (2 days)
- **Criteria**: design.md finalized, schemas validated, architecture reviewed
- **Status**: NOT STARTED

### Milestone 3: TDD Complete
- **Date**: 2025-12-31 (3 days after design)
- **Criteria**: All tests passing, WorkflowConfig implemented, managers updated
- **Status**: NOT STARTED

### Milestone 4: Integration Complete
- **Date**: 2026-01-01 (1 day after TDD)
- **Criteria**: workflows.yaml created, tools updated, existing projects migrated
- **Status**: NOT STARTED

### Milestone 5: Documentation Complete
- **Date**: 2026-01-02 (1 day after integration)
- **Criteria**: All docs updated, tool docstrings complete, WORKFLOWS.md created
- **Status**: NOT STARTED

### Milestone 6: Issue #50 Closed
- **Date**: 2026-01-02
- **Criteria**: All phases complete, PR merged to main
- **Status**: NOT STARTED

---

## Appendix A: Open Questions from Discovery

*These questions were raised in discovery.md and answered in Section 1 (Decision Log).*

**Q1: Execution Mode Selection**  
→ **Answered**: Per-project (Decision 1.1)

**Q2: Transition Graph Flexibility**  
→ **Answered**: Strict sequential with explicit skip (Decision 1.2)

**Q3: Custom Workflow Support**  
→ **Answered**: Pre-defined only, YAML is SSOT (Decision 1.3)

**Q4: Type Hints Approach**  
→ **Answered**: Config as SSOT, no Enums/Literal (Decision 1.4)

**Q5: Config Loading Strategy**  
→ **Answered**: Startup loading (Decision 1.5)

---

## Appendix B: Dependencies

**Blocked By**:
- None (discovery complete)

**Blocks**:
- Issue #51 (labels.yaml) - Depends on Pydantic config pattern established here
- Issue #52 (validation.yaml) - Depends on WorkflowConfig validation approach

**Related**:
- Epic #49 (MCP Platform Configurability) - Parent epic
- Issue #42 (Phase naming) - Will benefit from workflow validation

---

## Related Documentation

- **[discovery.md](discovery.md)** - Research findings and open questions
- **[design.md](design.md)** - Design schemas and models (next phase)
- **[Epic #49 planning.md](../issue49/planning.md)** - Parent epic planning

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-12-27 | GitHub Copilot | Initial planning: 5 decisions made, work breakdown defined, sequence established |

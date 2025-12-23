# Issue #18 Implementation Plan V2: Retrofit-Based Enforcement

**Status:** ACTIVE PLANNING  
**Branch:** `feature/issue-18-choke-point-enforcement`  
**Created:** 2025-12-23  
**Version:** 2.0 (Complete rewrite based on gap analysis)  
**Issue:** #18  
**Gap Analysis:** [ISSUE_18_TOOLING_GAP_ANALYSIS.md](ISSUE_18_TOOLING_GAP_ANALYSIS.md)  
**Original Plan:** [ISSUE_18_CHOKE_POINT_ENFORCEMENT_PLAN.md](ISSUE_18_CHOKE_POINT_ENFORCEMENT_PLAN.md)

---

## Document Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-22 | Original plan (proposed new tools) |
| 2.0 | 2025-12-23 | **Complete rewrite** after gap analysis: Retrofit strategy instead of duplication |

**Key Changes V1 → V2:**
- ❌ REMOVED: Proposals for duplicate tools (commit_tdd_phase, CreatePRTool, CloseIssueTool)
- ✅ ADDED: Retrofit strategy for 31 existing tools
- ✅ ADDED: Dependency injection pattern for PolicyEngine
- ✅ ADDED: Backward compatibility guarantees
- ✅ ADDED: Integration tasks per phase
- ✅ REDUCED: Scope (no new tools, just enforcement layer)

---

## 1. Executive Summary

### 1.1 Vision

**Before (Current State):**
```
Agent → GitCommitTool → GitManager.commit_tdd_phase() → GitAdapter.commit()
                         ↓
                    NO validation
                    NO phase checking
                    NO quality gates
                    Agent decides workflow
```

**After (Enforced State):**
```
Human → initialize_project(issue_type="feature", phases=[0,1,2,3,4,5,6])
         ↓
       Project plan stored (.st3/projects.json)
         ↓
Agent → GitCommitTool → PolicyEngine.decide() → Allow/Deny (strict)
                         ↓ (if allow)
                    GitManager.commit_tdd_phase() → tests + QA → GitAdapter.commit()
                         ↓ (on success)
                    PhaseStateEngine.record_commit()
                         ↓
Agent → transition_phase() → PolicyEngine.validate_prerequisites() → Allow/Deny
         ↓ (if deny)
       Human approval required
```

### 1.2 Core Principles

**1. Strict Enforcement (No Opt-Out):**
- ALL tools MUST go through PolicyEngine
- NO backward compatibility mode (policy=None removed)
- NO agent autonomy in workflow decisions
- Agent cannot bypass enforcement under any circumstance

**2. Human-in-the-Loop Phase Selection:**
- Human decides required phases DURING project initialization
- Different issue types have different phase requirements:
  - **Feature:** All 7 phases (0→1→2→3→4→5→6→done)
  - **Bug:** Skip architecture (0→1→3→4→5→6→done)
  - **Docs:** Skip TDD (0→1→2→6→done)
  - **Refactor:** Skip design (0→1→4→5→6→done)
  - **Custom:** Human selects specific phases
- Phase plan stored in project metadata
- Agent CANNOT deviate from plan without human approval

**3. Retrofit, Don't Duplicate:

**Problem Identified:**
Original plan proposed creating **NEW** tools (commit_tdd_phase, CreatePRTool, CloseIssueTool) while 31 existing tools already provide the same functionality.

**Solution:**
**RETROFIT** existing tools with enforcement layer via dependency injection:
1. Create PolicyEngine (NEW component)
2. Create PhaseStateEngine (NEW component)
3. **Inject** PolicyEngine into existing managers (GitManager, GitHubManager)
4. Add policy checks at START of existing manager methods
5. Add state updates at END (on success)
6. Result: **Zero duplication**, all 31 tools automatically enforced

### 1.3 Success Metrics

| Metric | Target | Rationale |
|--------|--------|-----------|
| Code duplication | 0 duplicate tool classes | Reuse existing 31 tools |
| Tool coverage | 31/31 tools with MANDATORY enforcement | No bypass paths, no opt-out |
| Enforcement strictness | 100% operations blocked without approval | Agent cannot deviate from workflow |
| Phase plan adherence | 100% operations follow project phase plan | Human-selected phases enforced |
| Test coverage | 90%+ on new enforcement code | Quality gate |
| Performance | Commit choke <10s, SafeEdit <500ms | User experience |
| Integration effort | Max 50 LOC changed per tool | Minimize risk |
| Human approval tracking | 100% deviations logged in audit trail | Accountability |

---

## 2. Architecture

### 2.1 Current Architecture (31 Tools, 6 Managers, 3 Adapters)

```
┌─────────────────────────────────────────────────────────────────┐
│                    TOOLS LAYER (31 tools)                       │
│  Git(8) | Issue(5) | PR(3) | Label(5) | Milestone(3)           │
│  Scaffold(7) | Quality(2) | Project(2) | Docs(1) | SafeEdit(1) │
└────────────────────────┬────────────────────────────────────────┘
                         │ (no enforcement)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 MANAGERS LAYER (6 managers)                     │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                 │
│  │GitManager  │ │GitHubMgr   │ │QAManager   │                 │
│  │- commit_tdd│ │- create_pr │ │- run_gates │                 │
│  │- create_br │ │- create_iss│ │            │                 │
│  └─────┬──────┘ └─────┬──────┘ └─────┬──────┘                 │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                 │
│  │ProjectMgr  │ │DocManager  │ │DepGraphVal │                 │
│  └────────────┘ └────────────┘ └────────────┘                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ADAPTERS LAYER (3 adapters)                    │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                 │
│  │GitAdapter  │ │GitHubAdapt │ │FilesystemA │                 │
│  └────────────┘ └────────────┘ └────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Target Architecture (WITH Enforcement Layer)

```
┌─────────────────────────────────────────────────────────────────┐
│                    TOOLS LAYER (31 tools)                       │
│               **NO CHANGES** (tools stay same)                  │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│              **NEW: ENFORCEMENT LAYER**                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  PolicyEngine                                            │  │
│  │  - decide(ctx: PolicyContext) → PolicyDecision          │  │
│  │  - Rules: protected branch, phase prereqs, artifacts    │  │
│  │  - Gates: tests, QA, coverage, docs                     │  │
│  └────────────────┬─────────────────────────────────────────┘  │
│  ┌────────────────▼─────────────────────────────────────────┐  │
│  │  PhaseStateEngine                                       │  │
│  │  - get_phase(branch) → Phase                           │  │
│  │  - transition(branch, from, to)                        │  │
│  │  - record_commit(phase, commit_hash)                   │  │
│  │  - persist to .st3/state.json                          │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                         │ **INJECTED into managers**
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│          MANAGERS LAYER (6 managers, **RETROFITTED**)           │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ GitManager (policy: PolicyEngine | None)               │    │
│  │   def commit_tdd_phase(phase, message, files):        │    │
│  │     if self.policy:  # ← NEW                          │    │
│  │       decision = self.policy.decide(...)              │    │
│  │       if not decision.allow: raise Error              │    │
│  │     # EXISTING logic (unchanged)                      │    │
│  │     commit_hash = self.adapter.commit(...)            │    │
│  │     if self.policy:  # ← NEW                          │    │
│  │       self.policy.phase_state.record_commit(...)      │    │
│  └────────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │ GitHubManager (policy: PolicyEngine | None)            │    │
│  │   def create_pr(title, body, head, base, draft):      │    │
│  │     if self.policy:  # ← NEW                          │    │
│  │       decision = self.policy.decide(...)              │    │
│  │       if not decision.allow: raise Error              │    │
│  │     # EXISTING logic (unchanged)                      │    │
│  │     return self.adapter.create_pr(...)                │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

**Key Architectural Decisions:**
, project_plan)
   - Output: PolicyDecision (allow/deny, reasons, required_gates, requires_human_approval)
   - Validates operations against project-specific phase plan
   - Does NOT execute gates (just decides which to run)

2. **PhaseStateEngine manages persistent state:**
   - Single source of truth: `.st3/state.json`
   - Per-branch phase tracking + project phase plan
   - Tool usage counters
   - Phase transition history
   - Human approval audit trail

3. **ProjectPhaseSelector (NEW) determines required phases:**
   - Human selects issue_type during project initialization
   - Templates for common patterns (feature/bug/docs/refactor)
   - Custom phase selection for edge cases
   - Phase plan stored in `.st3/projects.json` (from Phase 0)
   - Phase plan is IMMUTABLE without human approval

4. **Managers ALWAYS use PolicyEngine (NO opt-out):**
   - `policy: PolicyEngine` (REQUIRED, not optional)
   - NO `if self.policy:` checks (enforcement is mandatory)
   - Initialization fails if PolicyEngine not provided
   - Tests MUST use PolicyEngine (can use permissive test config)

5. **Tools are unchanged:**
   - No changes to tool classes
   - Enforcement happens in managers (one layer down)
   - All 31 tools automatically get MANDATORY enforcement
, "transition_phase"]
    branch: str
    phase: str  # Current phase from PhaseStateEngine
    files: tuple[str, ...]  # Changed files
    project_plan: ProjectPhasePlan  # Required phases for this project
    metadata: dict[str, Any]  # Operation-specific data (includes force_request: bool)
```

#### PolicyDecision (Output from PolicyEngine)
```python
@dataclass(frozen=True)
class PolicyDecision:
    """Policy decision result."""
    allow: bool
    reasons: tuple[str, ...]  # Human-readable explanations (for errors)
    required_gates: tuple[str, ...]  # Gates to run: ["tests", "pylint", "mypy", "coverage"]
    requires_human_approval: bool  # True if agent requests deviation
    warnings: tuple[str, ...] = ()  # Non-blocking warnings
```

#### ProjectPhasePlan (Stored in .st3/projects.json)
```python
@dataclass(frozen=True)
class ProjectPhasePlan:
    """Phase plan for a project (human-selected)."""
    issue_type: str  # "feature" | "bug" | "docs" | "refactor" | "custom"
    required_phases: tuple[str, ...]  # e.g. ("discovery", "planning", "design", "tdd", "integration", "documentation")
    optional_phases: tuple[str, ...] = ()  # Phases that can be skipped with approval
    skip_reason: str | None = None  # Human reason for phase selection
```

#### PhaseState (Persisted in .st3/state.json)
```python
@dataclass
class PhaseState:
    """Phase state for a branch."""
    current_phase: str  # "red" | "green" | "refactor" | "discovery" | etc.
    phase_history: list[PhaseTransition]
    issue_number: int
    project_plan: ProjectPhasePlan  # Human-selected phase plan
    tool_usage: dict[str, int]  # {"scaffold_component": 3, "run_tests": 5}
    last_commit_hash: str | None
    human_approvals: list[HumanApproval]  # Audit trail
```

#### HumanApproval (Audit Trail)
```python
@dataclass
class HumanApproval:
    """Record of human approval for deviation."""
    timestamp: str  # ISO 8601
    requested_action: str  # e.g., "Skip architecture phase"
    reason: str  # Human explanation
    approved_by: str  # Username/email
    request_context: dict[str, Any]  # Original PolicyContext"
    allow: bool
    reasons: tuple[str, ...]  # Human-readable explanations (for errors)
    required_gates: tuple[str, ...]  # Gates to run: ["tests", "pylint", "mypy", "coverage"]
    warnings: tuple[str, ...] = ()  # Non-blocking warnings
```

#### PhaseState (Persisted in .st3/state.json)
```python
@dataclass
class PhaseState:
    """Phase state for a branch."""
    current_phase: str  # "red" | "green" | "refactor" | "discovery" | etc.
    phase_history: list[PhaseTransition]
    issue_number: int | None
    tool_usage: dict[str, int]  # {"scaffold_component": 3, "run_tests": 5}
    last_commit_hash: str | None
```

---

## 3. Implementation Phases (Revised)

### Phase 0: Bootstrap Tooling ✅ **COMPLETE**

**Status:** ✅ 100% Complete (2025-12-23)  
**Deliverables:** ProjectManager, ValidateProjectStructureTool, 72 tests passing  
**Lessons Learned:**
- Manager pattern works well (orchestration + delegation)
- Pydantic DTOs provide excellent type safety
- Atomic .st3/ persistence with .tmp files prevents corruption
- Structured logging (INFO/DEBUG/ERROR) aids debugging

**Reusable Patterns for Phase 0.5 & A:**
- State persistence pattern (`.st3/state.json` similar to `.st3/projects.json`)
- Manager initialization (REQUIRED dependencies, no optional)
- Comprehensive unit tests (30+ tests per component)
- Quality gates (pylint 10/10, mypy clean)

---

### Phase 0.5: Project Type Selection & Phase Planning 🆕

**Goal:** Enable human to select issue type and required phases BEFORE work begins.

**Status:** NOT STARTED  
**Dependencies:** Phase 0 (uses ProjectManager pattern)  
**Estimated Effort:** 2 days  
**Risk Level:** 🟢 LOW (extends existing ProjectManager)

**Why This Phase:**
This is the CRITICAL gate that enables strict enforcement. Without phase planning, agent cannot know which phases are required. Human decides upfront what type of work this is and what phases must be completed.

#### 0.5.1 Components

##### ProjectPhaseSelector
**File:** `mcp_server/managers/project_phase_selector.py`

**Responsibilities:**
1. Provide templates for common issue types
2. Allow human to select required phases
3. Store phase plan in project metadata
4. Validate phase plan completeness

**Interface:**
```python
# Phase templates (pre-defined for common patterns)
PHASE_TEMPLATES = {
    "feature": {
        "description": "New feature development",
        "required_phases": ("discovery", "planning", "design", "component", "tdd", "integration", "documentation"),
        "rationale": "Full lifecycle with architecture and design"
    },
    "bug": {
        "description": "Bug fix",
        "required_phases": ("discovery", "planning", "component", "tdd", "integration", "documentation"),
        "rationale": "Skip architecture (system design unchanged)"
    },
    "refactor": {
        "description": "Code refactoring",
        "required_phases": ("discovery", "planning", "tdd", "integration", "documentation"),
        "rationale": "Skip design phases (behavior unchanged)"
    },
    "docs": {
        "description": "Documentation only",
        "required_phases": ("discovery", "planning", "design", "documentation"),
        "rationale": "No code changes, skip TDD and integration"
    },
    "hotfix": {
        "description": "Emergency hotfix",
        "required_phases": ("planning", "tdd", "documentation"),
        "rationale": "Minimal process for urgent fixes (requires approval)"
    },
    "custom": {
        "description": "Custom phase selection",
        "required_phases": (),  # Human specifies
        "rationale": "Edge cases requiring custom workflow"
    }
}

class ProjectPhaseSelector:
    def get_template(self, issue_type: str) -> dict[str, Any]:
        """Get phase template for issue type."""
        if issue_type not in PHASE_TEMPLATES:
            raise ValidationError(
                f"Unknown issue type: {issue_type}",
                hints=[f"Valid types: {list(PHASE_TEMPLATES.keys())}"]
            )
        return PHASE_TEMPLATES[issue_type]
    
    def create_phase_plan(
        self,
        issue_type: str,
        custom_phases: tuple[str, ...] | None = None,
        skip_reason: str | None = None
    ) -> ProjectPhasePlan:
        """Create phase plan from template or custom selection."""
        template = self.get_template(issue_type)
        
        if issue_type == "custom":
            if not custom_phases:
                raise ValidationError(
                    "Custom issue type requires explicit phase list",
                    hints=["Provide custom_phases parameter"]
                )
            required_phases = custom_phases
        else:
            required_phases = template["required_phases"]
        
        # Validate phase names
        valid_phases = {
            "discovery", "planning", "design", "component",
            "tdd", "integration", "documentation"
        }
        invalid = [p for p in required_phases if p not in valid_phases]
        if invalid:
            raise ValidationError(
                f"Invalid phase names: {invalid}",
                hints=[f"Valid phases: {sorted(valid_phases)}"]
            )
        
        return ProjectPhasePlan(
            issue_type=issue_type,
            required_phases=required_phases,
            skip_reason=skip_reason or template.get("rationale", "")
        )
```

##### Extended ProjectManager.initialize_project()
**File:** `mcp_server/managers/project_manager.py`

**Add issue_type parameter:**
```python
def initialize_project(
    self,
    spec: ProjectSpec,
    issue_type: str = "feature",  # NEW parameter
    custom_phases: tuple[str, ...] | None = None,  # NEW parameter
    skip_reason: str | None = None  # NEW parameter
) -> ProjectSummary:
    """Initialize project with phase plan."""
    logger.info("Initializing project: %s (type: %s)", spec.project_title, issue_type)
    
    # NEW: Create phase plan
    phase_selector = ProjectPhaseSelector()
    phase_plan = phase_selector.create_phase_plan(
        issue_type=issue_type,
        custom_phases=custom_phases,
        skip_reason=skip_reason
    )
    logger.info("Phase plan: %s", phase_plan.required_phases)
    
    # Existing logic (validation, milestone, parent, sub-issues)
    # ...
    
    # NEW: Store phase plan in metadata
    metadata = ProjectMetadata(
        project_id=project_id,
        milestone_id=milestone_id,
        parent_issue_number=parent_number,
        phases=sub_issues,
        created_at=datetime.now(UTC).isoformat(),
        phase_plan=phase_plan  # NEW field
    )
    
    self._persist_project_metadata(metadata)
    
    return summary
```

##### InitializeProjectTool Update
**File:** `mcp_server/tools/project_tools.py`

**Add issue_type to input:**
```python
class InitializeProjectInput(BaseModel):
    project_title: str
    phases: list[PhaseInput]
    parent_issue_number: int | None = None
    force_create_parent: bool = False
    issue_type: str = Field(
        default="feature",
        description="Issue type (feature/bug/docs/refactor/hotfix/custom)"
    )
    custom_phases: list[str] | None = Field(
        default=None,
        description="Custom phase list (required if issue_type=custom)"
    )
    skip_reason: str | None = Field(
        default=None,
        description="Reason for custom phase selection"
    )

class InitializeProjectTool(BaseTool):
    async def execute(self, params: InitializeProjectInput) -> ToolResult:
        # ... existing validation ...
        
        summary = self.manager.initialize_project(
            spec=spec,
            issue_type=params.issue_type,
            custom_phases=tuple(params.custom_phases) if params.custom_phases else None,
            skip_reason=params.skip_reason
        )
        
        return ToolResult.text(
            f"✅ Initialized project: {params.project_title}\n"
            f"Issue type: {params.issue_type}\n"
            f"Required phases: {', '.join(summary.project_metadata.phase_plan.required_phases)}\n"
            f"Milestone: #{summary.milestone_id}\n"
            f"Parent issue: #{summary.parent_issue_number}\n"
            f"Sub-issues created: {len(summary.sub_issues)}"
        )
```

#### 0.5.2 Tasks (TDD Order)

##### 0.5.2.1 RED: Write Tests
- [ ] Test: get_template("feature") → returns all 7 phases
- [ ] Test: get_template("bug") → returns 6 phases (no design)
- [ ] Test: get_template("docs") → returns 4 phases (no tdd/integration)
- [ ] Test: get_template("custom", custom_phases=[...]) → uses custom list
- [ ] Test: create_phase_plan with invalid phase name → error
- [ ] Test: initialize_project with issue_type → stores phase_plan in metadata
- [ ] Test: Phase plan persists to .st3/projects.json

##### 0.5.2.2 GREEN: Implement
- [ ] Create ProjectPhaseSelector class
- [ ] Add PHASE_TEMPLATES constant
- [ ] Update ProjectManager.initialize_project()
- [ ] Update InitializeProjectTool input schema
- [ ] Update ProjectMetadata DTO (add phase_plan field)

##### 0.5.2.3 REFACTOR: Quality
- [ ] Pylint 10/10, mypy clean
- [ ] Add docstrings explaining each template
- [ ] Integration test: Full project init with phase plan

#### 0.5.3 Exit Criteria

- [ ] 7+ tests passing
- [ ] Phase templates defined for 5 common types
- [ ] Phase plan stored in project metadata
- [ ] InitializeProjectTool accepts issue_type parameter
- [ ] Documentation: Phase template rationales

#### 0.5.4 Human Interaction Example

```bash
# Human initializes project and selects issue type:
initialize_project \
  --project-title "Issue #25: Add logging framework" \
  --issue-type "feature" \
  --phases '[
    {"phase_id": "0", "title": "Research logging libraries"},
    {"phase_id": "1", "title": "Design logging architecture"},
    ...
  ]'

# Output:
# ✅ Initialized project: Issue #25: Add logging framework
# Issue type: feature
# Required phases: discovery, planning, design, component, tdd, integration, documentation
# Milestone: #5
# Parent issue: #25
# Sub-issues created: 7
#
# ⚠️  STRICT ENFORCEMENT ENABLED
# Agent MUST complete all phases in order.
# Phase skipping requires human approval via approve_deviation tool.
```

**Key Point:** Once phase plan is set, agent CANNOT deviate without explicit human approval.

---

### Phase A: Enforcement Foundation (PolicyEngine + PhaseStateEngine)

**Goal:** Build enforcement layer WITH strict validation against project phase plan.

**Status:** NOT STARTED  
**Dependencies:** Phase 0, 0.5  
**Estimated Effort:** 4-5 days  
**Risk Level:** 🟢 LOW (no breaking changes to tools, strict enforcement from start)

#### A.1 Components

##### A.1.1 PolicyEngine
**File:** `mcp_server/core/policy.py`

**Responsibilities:**
1. Decide if operation is allowed based on:
   - Protected branch rules (block commits to main/master)
   - **Phase plan compliance** (validate current phase is in project's required_phases)
   - Phase prerequisites (e.g., can't commit GREEN without RED phase)
   - Required artifacts (e.g., PR needs design doc)
   - Tool usage requirements (e.g., must use scaffold_component)

2. Determine which gates to run:
   - Tests (pytest)
   - Quality (pylint/mypy/pyright)
   - Coverage (pytest-cov)
   - Artifacts (file existence + validation)

3. Return actionable errors OR human approval requests:
   - "Cannot commit to main. Use: create_feature_branch"
   - "GREEN phase requires passing tests. Run: run_tests"
   - **"Phase 'design' not in project plan. Request human approval via: request_deviation"**
   - "REFACTOR requires QA 10/10. Fix: [file.py:10] E501 line too long"

**Interface:**
```python
class PolicyEngine:
    def __init__(self, phase_state: PhaseStateEngine, qa_manager: QAManager):
        self.phase_state = phase_state
        self.qa_manager = qa_manager
    
    def decide(self, ctx: PolicyContext) -> PolicyDecision:
        """Make policy decision for operation with STRICT validation."""
        # 1. Check protected branch (always enforced)
        if ctx.operation == "commit" and ctx.branch in ["main", "master"]:
            return PolicyDecision(
                allow=False,
                reasons=("Cannot commit directly to main branch.",
                         "Create feature branch: create_feature_branch"),
                required_gates=(),
                requires_human_approval=False
            )
        
        # 2. Validate current phase is in project plan
        if ctx.phase not in ctx.project_plan.required_phases:
            # Agent is in a phase not approved for this project
            if ctx.metadata.get("force_request", False):
                # Agent explicitly requests deviation
                return PolicyDecision(
                    allow=False,
                    reasons=(f"Phase '{ctx.phase}' not in project plan: {ctx.project_plan.required_phases}",
                             "Human approval required.",
                             "Reason: " + (ctx.metadata.get("force_reason") or "Not specified")),
                    required_gates=(),
                    requires_human_approval=True  # Escalate to human
                )
            else:
                # Agent tried to bypass (ERROR)
                return PolicyDecision(
                    allow=False,
                    reasons=(f"Phase '{ctx.phase}' not in project plan: {ctx.project_plan.required_phases}",
                             "Cannot proceed without phase plan update.",
                             "To request deviation: use transition_phase with force=True"),
                    required_gates=(),
                    requires_human_approval=False
                )
        
        # 3. Check phase prerequisites
        if ctx.operation == "commit":
            return self._decide_commit(ctx)
        elif ctx.operation == "create_pr":
            return self._decide_create_pr(ctx)
        elif ctx.operation == "transition_phase":
            return self._decide_transition(ctx)
        # ... etc
    
    def _decide_transition(self, ctx: PolicyContext) -> PolicyDecision:
        """Decide for phase transition (validates against plan)."""
        target_phase = ctx.metadata["target_phase"]
        
        # Check if target phase is in project plan
        if target_phase not in ctx.project_plan.required_phases:
            if ctx.metadata.get("force_request", False):
                # Human approval flow
                return PolicyDecision(
                    allow=False,
                    reasons=(f"Phase '{target_phase}' not in project plan",
                             "Awaiting human approval"),
                    required_gates=(),
                    requires_human_approval=True
                )
            else:
                return PolicyDecision(
                    allow=False,
                    reasons=(f"Phase '{target_phase}' not in project plan: {ctx.project_plan.required_phases}",
                             "Use force=True to request deviation"),
                    required_gates=(),
                    requires_human_approval=False
                )
        
        # Validate transition order (state machine)
        # ...
        
        return PolicyDecision(allow=True, reasons=(), required_gates=(), requires_human_approval=False)
```
    
    def _decide_commit(self, ctx: PolicyContext) -> PolicyDecision:
        """Decide for commit operation."""
        phase = ctx.phase
        
        # RED phase: allow test commits (tests may fail)
        if phase == "red":
            # Require test changes
            test_files = [f for f in ctx.files if "test_" in f or "/tests/" in f]
            if not test_files:
                return PolicyDecision(
                    allow=False,
                    reasons=("RED phase requires test changes.",
                             "Add tests before committing."),
                    required_gates=()
                )
            return PolicyDecision(allow=True, reasons=(), required_gates=())
        
        # GREEN phase: require passing tests
        if phase == "green":
            return PolicyDecision(
                allow=True,
                reasons=(),
                required_gates=("tests",)  # Will run pytest
            )
        
        # REFACTOR phase: require tests + QA
        if phase == "refactor":
            return PolicyDecision(
                allow=True,
                reasons=(),
                required_gates=("tests", "pylint", "mypy", "pyright")
            )
        
        # Unknown phase
        return PolicyDecision(
            allow=False,
            reasons=(f"Unknown phase: {phase}",
                     "Use: transition_phase to set phase"),
            required_gates=()
        )
```

##### A.1.2 PhaseStateEngine
**File:** `mcp_server/core/phase_state.py`

**Responsibilities:**
1. Track current phase per branch + validate against project phase plan
2. Validate phase transitions (e.g., can't skip RED → REFACTOR)
3. **Enforce phase plan compliance** (block transitions to phases not in plan)
4. Persist state to `.st3/state.json`
5. Track tool usage counters (for policy decisions)
6. Maintain phase history (audit trail)
7. **Track human approvals** (deviation audit trail)

**Interface:**
```python
class PhaseStateEngine:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.state_file = workspace_root / ".st3" / "state.json"
    
    def get_phase(self, branch: str) -> str:
        """Get current phase for branch."""
        state = self._load_state()
        return state["branches"].get(branch, {}).get("current_phase", "discovery")
    
    def get_project_plan(self, branch: str) -> ProjectPhasePlan:
        """Get project phase plan for branch."""
        state = self._load_state()
        branch_state = state["branches"].get(branch)
        if not branch_state or "project_plan" not in branch_state:
            raise ValidationError(
                f"No project plan found for branch: {branch}",
                hints=["Initialize project with: initialize_project"]
            )
        return ProjectPhasePlan(**branch_state["project_plan"])
    
    def transition(
        self,
        branch: str,
        from_phase: str,
        to_phase: str,
        issue_number: int,
        project_plan: ProjectPhasePlan,
        human_approval: HumanApproval | None = None
    ) -> None:
        """Transition to new phase with STRICT validation against plan."""
        # 1. Validate transition (state machine)
        if not self._is_valid_transition(from_phase, to_phase):
            raise ValidationError(
                f"Invalid transition: {from_phase} → {to_phase}",
                hints=[f"Valid transitions: {self._get_valid_transitions(from_phase)}"]
            )
        
        # 2. STRICT: Validate target phase is in project plan
        if to_phase not in project_plan.required_phases:
            if human_approval is None:
                raise ValidationError(
                    f"Phase '{to_phase}' not in project plan: {project_plan.required_phases}",
                    hints=["Human approval required", "Use: request_deviation"]
                )
            # Human approved deviation - log it
            logger.warning(
                "DEVIATION APPROVED: %s → %s (Reason: %s)",
                from_phase, to_phase, human_approval.reason
            )
        
        # 3. Update state
        state = self._load_state()
        if branch not in state["branches"]:
            state["branches"][branch] = {
                "current_phase": to_phase,
                "phase_history": [],
                "issue_number": issue_number,
                "project_plan": project_plan.__dict__,
                "tool_usage": {},
                "last_commit_hash": None,
                "human_approvals": []
            }
        
        branch_state = state["branches"][branch]
        branch_state["current_phase"] = to_phase
        branch_state["phase_history"].append({
            "phase": to_phase,
            "entered": datetime.now(UTC).isoformat(),
            "commits": [],
            "deviation_approved": human_approval is not None
        })
        
        # 4. Record human approval if present
        if human_approval:
            branch_state["human_approvals"].append(human_approval.__dict__)
        
        self._save_state(state)
    
    def record_human_approval(self, branch: str, approval: HumanApproval) -> None:
        """Record human approval in audit trail."""
        state = self._load_state()
        if branch in state["branches"]:
            state["branches"][branch]["human_approvals"].append(approval.__dict__)
            self._save_state(state)
```

##### A.1.3 ApproveDeviationTool (NEW)
**File:** `mcp_server/tools/workflow_tools.py`

**Responsibilities:**
- Allow human to explicitly approve phase plan deviations
- Record approval in audit trail
- Unblock agent operations waiting for approval

**Interface:**
```python
class ApproveDeviationInput(BaseModel):
    branch: str = Field(..., description="Branch name")
    requested_action: str = Field(..., description="What agent requested (e.g., 'Skip design phase')")
    reason: str = Field(..., description="Human reason for approval")
    approved_by: str = Field(..., description="Username/email of approver")

class ApproveDeviationTool(BaseTool):
    name = "approve_deviation"
    description = "Human approval for phase plan deviation (strict enforcement bypass)"
    args_model = ApproveDeviationInput
    
    def __init__(self, phase_state: PhaseStateEngine):
        self.phase_state = phase_state
    
    async def execute(self, params: ApproveDeviationInput) -> ToolResult:
        approval = HumanApproval(
            timestamp=datetime.now(UTC).isoformat(),
            requested_action=params.requested_action,
            reason=params.reason,
            approved_by=params.approved_by,
            request_context={}  # Can be populated with PolicyContext if needed
        )
        
        self.phase_state.record_human_approval(params.branch, approval)
        
        return ToolResult.text(
            f"✅ Deviation approved by {params.approved_by}\n"
            f"Action: {params.requested_action}\n"
            f"Reason: {params.reason}\n"
            f"Timestamp: {approval.timestamp}\n\n"
            f"⚠️  Approval recorded in audit trail (.st3/state.json)"
        )
```
    
    def record_commit(self, branch: str, phase: str, commit_hash: str) -> None:
        """Record commit in phase history."""
        state = self._load_state()
        if branch in state["branches"]:
            history = state["branches"][branch]["phase_history"]
            if history and history[-1]["phase"] == phase:
                history[-1]["commits"].append(commit_hash)
            state["branches"][branch]["last_commit_hash"] = commit_hash
            self._save_state(state)
    
    def increment_tool_usage(self, branch: str, tool_name: str) -> None:
        """Track tool usage for policy decisions."""
        state = self._load_state()
        if branch in state["branches"]:
            usage = state["branches"][branch]["tool_usage"]
            usage[tool_name] = usage.get(tool_name, 0) + 1
            self._save_state(state)
    
    def _is_valid_transition(self, from_phase: str, to_phase: str) -> bool:
        """Validate phase transition against state machine."""
        # 7-phase lifecycle + TDD sub-phases
        transitions = {
            "discovery": ["discussion"],  # Phase 0
            "discussion": ["design"],  # Phase 1
            "design": ["review"],  # Phase 2
            "review": ["approved"],  # Phase 3
            "approved": ["red"],  # Phase 4 entry
            "red": ["green"],  # TDD: RED → GREEN
            "green": ["refactor", "red"],  # TDD: GREEN → REFACTOR (or back to RED)
            "refactor": ["integration", "red"],  # TDD: REFACTOR → Integration (or back to RED)
            "integration": ["documentation"],  # Phase 5 → 6
            "documentation": ["done"]  # Phase 6 → Done
        }
        return to_phase in transitions.get(from_phase, [])
    
    def _load_state(self) -> dict[str, Any]:
        """Load state from .st3/state.json."""
        if not self.state_file.exists():
            return {"version": "1.0", "branches": {}}
        return json.loads(self.state_file.read_text())
    
    def _save_state(self, state: dict[str, Any]) -> None:
        """Atomic save to .st3/state.json."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = self.state_file.with_suffix(".json.tmp")
        tmp_file.write_text(json.dumps(state, indent=2))
        tmp_file.replace(self.state_file)
```

#### A.2 Tasks (TDD Order)

##### A.2.1 RED: Write Tests for PhaseStateEngine
**File:** `tests/unit/mcp_server/core/test_phase_state.py`

- [ ] Test: Load empty state → returns default "discovery" phase
- [ ] Test: Transition discovery → discussion → valid
- [ ] Test: Transition discovery → refactor → error (invalid)
- [ ] Test: Transition red → green → green → refactor → valid (TDD loop)
- [ ] Test: Record commit updates phase history
- [ ] Test: Increment tool usage updates counter
- [ ] Test: State persists to .st3/state.json
- [ ] Test: Atomic write (no corruption on failure)
- [ ] Test: Multiple branches tracked independently
- [ ] Test: Phase history maintains order

**Expected:** 10+ failing tests

##### A.2.2 RED: Write Tests for PolicyEngine
**File:** `tests/unit/mcp_server/core/test_policy.py`

- [ ] Test: Commit to main → deny with branch creation suggestion
- [ ] Test: Commit to feature branch (phase=red, no test files) → deny
- [ ] Test: Commit to feature branch (phase=red, test files) → allow, no gates
- [ ] Test: Commit (phase=green) → allow, require "tests" gate
- [ ] Test: Commit (phase=refactor) → allow, require ["tests", "pylint", "mypy", "pyright"]
- [ ] Test: Create PR (phase=approved, no design doc) → deny
- [ ] Test: Create PR (phase=refactor, has design doc) → allow
- [ ] Test: Close issue (phase=integration) → deny (need docs phase)
- [ ] Test: Close issue (phase=documentation, has docs) → allow
- [ ] Test: Create file in backend/ → deny, suggest scaffold_component
- [ ] Test: Unknown phase → deny with transition_phase suggestion

**Expected:** 11+ failing tests

##### A.2.3 GREEN: Implement PhaseStateEngine
**File:** `mcp_server/core/phase_state.py`

- [ ] Implement all methods from interface
- [ ] Use atomic writes (.tmp file pattern from Phase 0)
- [ ] Validate phase transitions with state machine
- [ ] All RED tests pass

##### A.2.4 GREEN: Implement PolicyEngine
**File:** `mcp_server/core/policy.py`

- [ ] Implement decide() method with operation routing
- [ ] Implement _decide_commit() with phase-specific rules
- [ ] Implement _decide_create_pr() with artifact checks
- [ ] Implement _decide_close_issue() with docs checks
- [ ] Implement _decide_create_file() with scaffold enforcement
- [ ] All RED tests pass

##### A.2.5 REFACTOR: Quality Gates + Documentation
- [ ] Pylint 10/10 on both modules
- [ ] Mypy clean (no type errors)
- [ ] Add docstrings to all public methods
- [ ] Document .st3/state.json schema in comments
- [ ] Add integration test: PolicyEngine + PhaseStateEngine together

#### A.3 Exit Criteria

- [ ] 30+ unit tests passing (10 PhaseStateEngine + 11 PolicyEngine + 9 integration)
- [ ] Pylint 10/10, mypy clean
- [ ] `.st3/state.json` persists state across Python sessions
- [ ] NO changes to existing tools/managers (enforcement not wired yet)
- [ ] Documentation: PolicyEngine interface, PhaseStateEngine state machine diagram

#### A.4 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| State file corruption | Low | High | Atomic writes with .tmp pattern |
| Phase transition bugs | Medium | High | Comprehensive state machine tests |
| PolicyEngine complexity | Low | Medium | Keep rules simple, add gradually |
| Performance (state file I/O) | Low | Low | Cache in-memory, write only on change |

---

### Phase B: Phase Transition Tool (TransitionPhaseTool + Label Sync)

**Goal:** Enable explicit phase transitions with GitHub label synchronization.

**Status:** NOT STARTED  
**Dependencies:** Phase A  
**Estimated Effort:** 2 days  
**Risk Level:** 🟡 MEDIUM (GitHub API integration)

#### B.1 Components

##### B.1.1 TransitionPhaseTool
**File:** `mcp_server/tools/workflow_tools.py`

**Responsibilities:**
1. Validate phase transition (via PhaseStateEngine)
2. Check prerequisites (e.g., artifacts exist)
3. Update phase state
4. Sync GitHub issue labels
5. Return success/error with actionable messages

**Interface:**
```python
class TransitionPhaseInput(BaseModel):
    phase: str = Field(..., description="Target phase")
    issue_number: int | None = Field(default=None, description="Issue number to label")
    pass_through: bool = Field(default=False, description="Skip artifact checks (lead approval)")

class TransitionPhaseTool(BaseTool):
    name = "transition_phase"
    description = "Transition to a new phase with validation and label sync"
    args_model = TransitionPhaseInput
    
    def __init__(self, phase_state: PhaseStateEngine, 
                 github_adapter: GitHubAdapter,
                 git_adapter: GitAdapter):
        self.phase_state = phase_state
        self.github_adapter = github_adapter
        self.git_adapter = git_adapter
    
    async def execute(self, params: TransitionPhaseInput) -> ToolResult:
        branch = self.git_adapter.get_current_branch()
        current_phase = self.phase_state.get_phase(branch)
        
        # Validate transition
        try:
            self.phase_state.transition(branch, current_phase, params.phase, 
                                        params.issue_number)
        except ValidationError as e:
            return ToolResult.error(str(e))
        
        # Sync GitHub labels (if issue_number provided)
        if params.issue_number:
            try:
                self._sync_labels(params.issue_number, params.phase)
            except Exception as e:
                # Log but don't fail (label sync is non-critical)
                logger.warning(f"Label sync failed: {e}")
        
        return ToolResult.text(
            f"✅ Transitioned {branch} to phase: {params.phase}\n"
            f"Previous: {current_phase} → Current: {params.phase}"
        )
    
    def _sync_labels(self, issue_number: int, phase: str) -> None:
        """Sync GitHub issue labels."""
        # Remove all phase:* labels
        issue = self.github_adapter.get_issue(issue_number)
        old_labels = [l.name for l in issue.labels if l.name.startswith("phase:")]
        
        if old_labels:
            self.github_adapter.remove_labels(issue_number, old_labels)
        
        # Add new phase label
        new_label = f"phase:{phase}"
        self.github_adapter.add_labels(issue_number, [new_label])
```

##### B.1.2 GitHubAdapter.update_issue_labels()
**File:** `mcp_server/adapters/github_adapter.py`

**New method:**
```python
def update_issue_labels(self, issue_number: int, 
                       add_labels: list[str], 
                       remove_labels: list[str]) -> None:
    """Atomically update issue labels."""
    issue = self.get_issue(issue_number)
    
    # Remove labels
    if remove_labels:
        self.remove_labels(issue_number, remove_labels)
    
    # Add labels
    if add_labels:
        self.add_labels(issue_number, add_labels)
    
    logger.info(f"Updated labels for #{issue_number}: +{add_labels} -{remove_labels}")
```

#### B.2 Tasks (TDD Order)

##### B.2.1 RED: Write Tests for TransitionPhaseTool
- [ ] Test: Valid transition (discovery → discussion) → success
- [ ] Test: Invalid transition (discovery → refactor) → error
- [ ] Test: Transition with issue_number → labels updated
- [ ] Test: Transition without issue_number → no label update
- [ ] Test: GitHub API fails → tool still succeeds (logs warning)
- [ ] Test: pass_through=True skips artifact checks

##### B.2.2 GREEN: Implement TransitionPhaseTool
- [ ] Implement tool class with execute() method
- [ ] Wire PhaseStateEngine, GitHubAdapter, GitAdapter
- [ ] Implement label sync logic
- [ ] All tests pass

##### B.2.3 REFACTOR: Quality + Integration
- [ ] Pylint 10/10, mypy clean
- [ ] Add integration test: Full transition workflow with label sync
- [ ] Document tool in TOOLS.md

#### B.3 Exit Criteria

- [ ] Can transition through all 7 phases
- [ ] GitHub labels auto-sync (phase:red, phase:green, etc.)
- [ ] Invalid transitions blocked with helpful errors
- [ ] 6+ tests passing
- [ ] Tool registered in MCP server

---

### Phase C: Commit Enforcement (Retrofit git_add_or_commit)

**Goal:** Add enforcement to existing `git_add_or_commit` tool via PolicyEngine injection.

**Status:** NOT STARTED  
**Dependencies:** Phase A, B  
**Estimated Effort:** 2-3 days  
**Risk Level:** 🟡 MEDIUM (modifies core commit flow)

#### C.1 Changes Required

##### C.1.1 GitManager.__init__() - Add PolicyEngine (REQUIRED)
**File:** `mcp_server/managers/git_manager.py`

**Before:**
```python
class GitManager:
    def __init__(self, adapter: GitAdapter | None = None) -> None:
        self.adapter = adapter or GitAdapter()
```

**After:**
```python
class GitManager:
    def __init__(self, adapter: GitAdapter, policy: PolicyEngine) -> None:
        """Initialize GitManager with REQUIRED PolicyEngine.
        
        Args:
            adapter: Git adapter for subprocess operations
            policy: Policy engine for enforcement (REQUIRED, no opt-out)
        
        Raises:
            TypeError: If policy is None (strict enforcement)
        """
        self.adapter = adapter
        if policy is None:
            raise TypeError("PolicyEngine is REQUIRED. No opt-out mode available.")
        self.policy = policy  # MANDATORY enforcement
```

**Key Change:** `policy` is now REQUIRED parameter (no `| None`, no default value).

##### C.1.2 GitManager.commit_tdd_phase() - Add Enforcement
**File:** `mcp_server/managers/git_manager.py`

**Before:**
```python
def commit_tdd_phase(self, phase: str, message: str, files: list[str] | None = None) -> str:
    if phase not in ["red", "green", "refactor"]:
        raise ValidationError(f"Invalid TDD phase: {phase}", ...)
    
    if files is not None and not files:
        raise ValidationError("Files list cannot be empty", ...)
    
    prefix_map = {"red": "test", "green": "feat", "refactor": "refactor"}
    full_message = f"{prefix_map[phase]}: {message}"
    return self.adapter.commit(full_message, files=files)
```

**After:**
```python
def commit_tdd_phase(self, phase: str, message: str, files: list[str] | None = None) -> str:
    # Existing validation
    if phase not in ["red", "green", "refactor"]:
        raise ValidationError(f"Invalid TDD phase: {phase}", ...)
    
    if files is not None and not files:
        raise ValidationError("Files list cannot be empty", ...)
    
    # ──────────────── STRICT Policy Check (ALWAYS runs) ────────────────
    branch = self.adapter.get_current_branch()
    staged_files = files or self.adapter.get_staged_files()
    project_plan = self.policy.phase_state.get_project_plan(branch)
    
    ctx = PolicyContext(
        operation="commit",
        branch=branch,
        phase=self.policy.phase_state.get_phase(branch),
        files=tuple(staged_files),
        project_plan=project_plan,  # NEW: Pass project plan
        metadata={"commit_phase": phase}
    )
    
    decision = self.policy.decide(ctx)
    
    if decision.requires_human_approval:
        # Agent requested deviation, escalate to human
        raise ValidationError(
            "Human approval required:\n" + "\n".join(decision.reasons),
            hints=["Contact project lead for approval",
                   "Use: approve_deviation to grant approval"]
        )
    
    if not decision.allow:
        raise ValidationError(
            "Commit blocked by policy:\n" + "\n".join(decision.reasons),
            hints=["Fix issues above and retry commit"]
        )
    
    # Run required gates (MANDATORY, no skip)
    if "tests" in decision.required_gates:
        test_result = self._run_tests_gate()
        if not test_result:
            raise ValidationError(
                "Tests failed. Fix failing tests before committing.",
                hints=["Run: run_tests to see failures"]
            )
    
    if any(gate in decision.required_gates for gate in ["pylint", "mypy", "pyright"]):
        qa_result = self._run_qa_gate(staged_files)
        if not qa_result["overall_pass"]:
            issues_summary = "\n".join([
                f"  - {issue['file']}:{issue['line']} [{issue['code']}] {issue['message']}"
                for gate in qa_result["gates"] if not gate["passed"]
                for issue in gate.get("issues", [])[:5]  # Show first 5
            ])
            raise ValidationError(
                f"Quality gates failed:\n{issues_summary}",
                hints=["Fix issues above", "Run: run_quality_gates to see all"]
            )
    # ──────────────── End Policy Check ────────────────
    
    # Existing logic (unchanged)
    prefix_map = {"red": "test", "green": "feat", "refactor": "refactor"}
    full_message = f"{prefix_map[phase]}: {message}"
    commit_hash = self.adapter.commit(full_message, files=files)
    
    # ──────────────── MANDATORY State Update ────────────────
    self.policy.phase_state.record_commit(branch, phase, commit_hash)
    # ──────────────── End State Update ────────────────
    
    return commit_hash

def _run_tests_gate(self) -> bool:
    """Run tests and return pass/fail."""
    # Use existing RunTestsTool or call pytest directly
    import subprocess
    result = subprocess.run(["pytest", "-x"], capture_output=True)
    return result.returncode == 0

def _run_qa_gate(self, files: list[str]) -> dict[str, Any]:
    """Run quality gates and return results."""
    from mcp_server.managers.qa_manager import QAManager
    qa_manager = QAManager()
    return qa_manager.run_quality_gates(files)
```

##### C.1.3 GitAdapter.get_staged_files() - New Method
**File:** `mcp_server/adapters/git_adapter.py`

**Add method:**
```python
def get_staged_files(self) -> list[str]:
    """Get list of staged files."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
        cwd=self.repo_path
    )
    return [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
```

##### C.1.4 GitCommitTool - Wire PolicyEngine
**File:** `mcp_server/tools/git_tools.py`

**Before:**
```python
class GitCommitTool(BaseTool):) -> None:
        """Initialize with GitManager (must have PolicyEngine).
        
        Args:
            manager: GitManager with REQUIRED PolicyEngine
        
        Note: No policy=None mode. Enforcement is MANDATORY.
        """
        self.manager = manager
```

**Key Change:** No more optional policy parameter. Manager MUST have PolicyEngine
        # Create manager with policy injection
        if manager is None:
            adapter = GitAdapter()
            manager = GitManager(adapter=adapter, policy=policy)
        self.manager = manager
```

**Note:** Policy is passed from server.py when registering tools (Phase C.3).

#### C.2 Tasks (TDD Order)

##### C.2.1 RED: Write Tests for Commit Enforcement
- [ ] Test: Commit to main → error, suggests create_feature_branch
- [ ] Test: Commit RED without test files → error
- [ ] Test: Commit RED with test files → success (no gate execution)
- [ ] Test: Commit GREEN with failing tests → error
- [ ] Test: Commit GREEN with passing tests → success
- [ ] Test: Commit REFACTOR with failing QA → error (show issues)
- [ ] **Test: Commit to phase NOT in project plan → error (requires human approval)**
- [ ] **Test: Commit after human approval → success (logged in audit trail)**
- [ ] Test: Phase state updated after successful commit
- [ ] Test: policy=None → no enforcement (backward compat)

##### C.2.2 GREEN: Implement Changes
- [ ] Update GitManager.__init__()
- [ ] Update GitManager.commit_tdd_phase()
- [ ] Add GitAdapter.get_staged_files()
- [ ] Update GitCommitTool.__init__()
- [ ] All tests pass

##### C.2.3 REFACTOR: Quality + Integration
- [ ] Pylint 10/10, mypy clean
- [ ] Integration test: Full commit workflow (RED → GREEN → REFACTOR)
- [ ] Performance test: Commit <10s with QA gates

#### C.3 Integration with Server
**File:** `mcp_server/server.py`

```python (MANDATORY, no opt-out)
from mcp_server.core.policy import PolicyEngine
from mcp_server.core.phase_state import PhaseStateEngine
from mcp_server.managers.qa_manager import QAManager

phase_state = PhaseStateEngine(workspace_root=Path.cwd())
policy_engine = PolicyEngine(phase_state=phase_state, qa_manager=QAManager())

# Register tools with REQUIRED policy enforcement
git_adapter = GitAdapter()
git_manager = GitManager(adapter=git_adapter, policy=policy_engine)  # REQUIRED

github_adapter = GitHubAdapter()
github_manager = GitHubManager(adapter=github_adapter, policy=policy_engine)  # REQUIRED

tools = [
    GitCommitTool(manager=git_manager),
    CreatePRTool(manager=github_manager),
    TransitionPhaseTool(phase_state=phase_state, github_adapter=github_adapter, git_adapter=git_adapter),
    ApproveDeviationTool(phase_state=phase_state),  # NEW: Human approval tool
    # ... other tools
]
```

**Key Point:** NO environment variable toggle. Enforcement is ALWAYS enabled.
```**Cannot commit to phase not in project plan (without human approval)**
- [ ] Phase state persists after commit
- [ ] Error messages actionable (reference specific tools)
- [ ] **Human approval requests escalate properly**
- [ ] **Approved deviations logged in audit trail**
- [ ] 11+ tests passing (9 original + 2 new for phase plan enforcement)
- [ ] NO opt-out mode (policy=None removed)
- [ ] Cannot commit to main branch
- [ ] Cannot commit GREEN without passing tests
- [ ] Cannot commit REFACTOR without passing QA gates
- [ ] RED commits allowed with test changes (tests may fail)
- [ ] Phase state persists after commit
- [ ] Error messages actionable (reference specific tools)
- [ ] 9+ tests passing
- [ ] Backward compatibility: policy=None disables enforcement

---

### Phase D: File Creation Enforcement (Path-Based Selective Enforcement)

**Goal:** **Enforce scaffold tools for backend/tests Python**, allow direct creation for config/utility files.

**Status:** NOT STARTED  
**Dependencies:** Phase A  
**Estimated Effort:** 2 days  
**Risk Level:** 🟡 MEDIUM (path-based rules complexity)

#### D.1 Problem Statement

**Current State:** Agents bypass MCP tooling by using:
- `create_file` (VS Code tool) - creates files without validation
- Direct file writes in terminal commands
- Result: Workflow enforcement bypassed for backend/tests code

**Target State (Nuanced):** 
- **Backend/tests Python** → MUST use scaffold_component (enforced)
- **Design docs** → MUST use scaffold_design_doc (enforced)
- **Config files** (YAML, JSON, TOML) → CAN use create_file (allowed)
- **Scripts** (utility Python, shell) → CAN use create_file (allowed)
- **Future TS/JS** → Extend scaffold_component or allow create_file (TBD)

#### D.2 File Type Matrix

| File Pattern | Tool Required | Rationale |
|--------------|--------------|----------|
| `backend/**/*.py` (not `__*.py`) | `scaffold_component` | Enforces architecture (DTO, Worker, Adapter) |
| `tests/**/test_*.py` | `scaffold_component` | Enforces test structure |
| `docs/architecture/**/*.md` | `scaffold_design_doc` | Enforces doc templates |
| `docs/implementation/**/*.md` | `scaffold_design_doc` | Enforces doc templates |
| `*.yml, *.yaml, *.json, *.toml, *.ini` | `create_file` | Config files, no template needed |
| `requirements*.txt, *.lock` | `create_file` | Dependency files, no template |
| `scripts/**/*.py, *.sh` | `create_file` | Utility scripts, no architecture |
| `*.ts, *.js, *.tsx, *.jsx` (future) | `create_file` OR extend scaffold | TBD based on frontend architecture |

#### D.3 Implementation Strategy

##### D.3.1 KEEP create_file, ADD Path-Based PolicyEngine Check
**Action:** Keep `create_file` tool, but intercept with PolicyEngine

**File:** `mcp_server/tools/file_tools.py` (NEW)
```python
class CreateFileTool(BaseTool):
    """Wrapper around VS Code create_file with policy enforcement."""
    
    def __init__(self, policy: PolicyEngine, git_adapter: GitAdapter):
        if policy is None:
            raise TypeError("PolicyEngine is REQUIRED")
        self.policy = policy
        self.git_adapter = git_adapter
    
    async def execute(self, params: CreateFileInput) -> ToolResult:
        # ──────────────── MANDATORY Policy Check ────────────────
        branch = self.git_adapter.get_current_branch()
        current_phase = self.policy.phase_state.get_phase(branch)
        project_plan = self.policy.phase_state.get_project_plan(branch)
        
        ctx = PolicyContext(
            operation="create_file",
            branch=branch,
            phase=current_phase,
            files=(params.filePath,),
            project_plan=project_plan,
            metadata={"content_length": len(params.content)}
        )
        
        decision = self.policy.decide(ctx)
        
        if decision.requires_human_approval:
            raise ValidationError(
                "Human approval required:\n" + "\n".join(decision.reasons),
                hints=["Use: approve_deviation to grant approval"]
            )
        
        if not decision.allow:
            raise ValidationError(
                "File creation blocked by policy:\n" + "\n".join(decision.reasons),
                hints=decision.reasons  # Includes scaffold tool suggestion
            )
        # ──────────────── End Policy Check ────────────────
        
        # Delegate to actual file creation (VS Code API or filesystem)
        Path(params.filePath).parent.mkdir(parents=True, exist_ok=True)
        Path(params.filePath).write_text(params.content)
        
        return ToolResult.text(f"✅ Created: {params.filePath}")
```

**Rationale:** PolicyEngine decides per path - no blanket removal.

##### D.2.2 ADD Policy Validation to Scaffold Tools
**File:** `mcp_server/tools/scaffold_tools.py`

```python
class ScaffoldComponentTool(BaseTool):
    def __init__(self, manager: ProjectManager):
        """Manager MUST have PolicyEngine (no opt-out)."""
        if manager.policy is None:
            raise TypeError("PolicyEngine is REQUIRED")
        self.manager = manager
    
    async def execute(self, params: ScaffoldComponentInput) -> ToolResult:
        # ──────────────── MANDATORY Policy Check ────────────────
        branch = self.manager.git_adapter.get_current_branch()
        current_phase = self.manager.policy.phase_state.get_phase(branch)
        project_plan = self.manager.policy.phase_state.get_project_plan(branch)
        
        ctx = PolicyContext(
            operation="scaffold",
            branch=branch,
            phase=current_phase,
            files=(params.output_path,),
            project_plan=project_plan,
            metadata={"component_type": params.component_type}
        )
        
        decision = self.manager.policy.decide(ctx)
        
        if decision.requires_human_approval:
            raise ValidationError(
                "Human approval required:\n" + "\n".join(decision.reasons),
                hints=["Use: approve_deviation to grant approval"]
            )
        
        if not decision.allow:
            raise ValidationError(
                "Scaffold blocked by policy:\n" + "\n".join(decision.reasons),
                hints=["Transition to correct phase first", "Use: transition_phase"]
            )
        # ──────────────── End Policy Check ────────────────
        
        # EXISTING scaffold logic (unchanged)
        result = self.manager.scaffold_component(
            component_type=params.component_type,
            name=params.name,
            output_path=params.output_path
        )
        
        # Track tool usage
        self.manager.policy.phase_state.increment_tool_usage(branch, "scaffold_component")
        
        return result
```

##### D.3.2 UPDATE PolicyEngine._decide_create_file() (NEW)
**File:** `mcp_server/core/policy.py`

```python
def _decide_create_file(self, ctx: PolicyContext) -> PolicyDecision:
    """Path-based enforcement for file creation."""
    from pathlib import Path
    
    file_path = Path(ctx.files[0])
    phase = ctx.phase
    
    # ──────────────── Backend Python: MUST use scaffold ────────────────
    if file_path.match("backend/**/*.py"):
        # Allow __init__.py, __main__.py (package files)
        if file_path.name.startswith("__"):
            return PolicyDecision(allow=True, reasons=())
        
        return PolicyDecision(
            allow=False,
            reasons=(
                f"Cannot create backend Python file directly: {file_path}",
                "Backend code requires architecture compliance",
                "Use: scaffold_component --type dto|worker|adapter|manager"
            ),
            required_gates=()
        )
    
    # ──────────────── Tests: MUST use scaffold ────────────────
    if file_path.match("tests/**/*.py") and file_path.stem.startswith("test_"):
        return PolicyDecision(
            allow=False,
            reasons=(
                f"Cannot create test file directly: {file_path}",
                "Tests require structure validation",
                "Use: scaffold_component --type test"
            ),
            required_gates=()
        )
    
    # ──────────────── Design docs: MUST use scaffold ────────────────
    if file_path.match("docs/architecture/**/*.md") or file_path.match("docs/implementation/**/*.md"):
        return PolicyDecision(
            allow=False,
            reasons=(
                f"Cannot create design doc directly: {file_path}",
                "Design docs require template compliance",
                "Use: scaffold_design_doc --type design|architecture|tracking"
            ),
            required_gates=()
        )
    
    # ──────────────── Config files: ALLOWED ────────────────
    config_extensions = {".yml", ".yaml", ".json", ".toml", ".ini", ".txt", ".lock"}
    if file_path.suffix in config_extensions:
        return PolicyDecision(
            allow=True,
            reasons=(f"Config file allowed: {file_path.suffix}",),
            required_gates=()
        )
    
    # ──────────────── Scripts: ALLOWED ────────────────
    if file_path.match("scripts/**/*"):
        return PolicyDecision(
            allow=True,
            reasons=("Utility script allowed",),
            required_gates=()
        )
    
    # ──────────────── Proof of concepts: ALLOWED ────────────────
    if file_path.match("proof_of_concepts/**/*"):
        return PolicyDecision(
            allow=True,
            reasons=("POC file allowed",),
            required_gates=()
        )
    
    # ──────────────── Other docs (not design): ALLOWED ────────────────
    if file_path.match("docs/**/*.md"):
        return PolicyDecision(
            allow=True,
            reasons=("General documentation allowed",),
            required_gates=()
        )
    
    # ──────────────── Unknown/Future files: PERMISSIVE ────────────────
    # Future TS/JS, new file types → allow by default (can tighten later)
    return PolicyDecision(
        allow=True,
        reasons=(f"Unknown file type allowed (permissive): {file_path.suffix}",),
        required_gates=()
    )
```

**Key Design:** 
- **Explicit blocks** for backend/tests Python (must scaffold)
- **Explicit allows** for configs, scripts, docs
- **Permissive default** for unknown file types (extensible for future TS/JS)

##### D.3.3 UPDATE PolicyEngine._decide_scaffold()
**File:** `mcp_server/core/policy.py`

```python
def _decide_scaffold(self, ctx: PolicyContext) -> PolicyDecision:
    """Decide for scaffold operations."""
    phase = ctx.phase
    project_plan = ctx.project_plan
    component_type = ctx.metadata.get("component_type")
    
    # Validate phase is in project plan
    if project_plan and phase not in project_plan.required_phases:
        return PolicyDecision(
            allow=False,
            reasons=(
                f"Phase '{phase}' not in project plan (issue_type={project_plan.issue_type})",
                f"Project phases: {', '.join(project_plan.required_phases)}",
                "Human approval required to deviate"
            ),
            required_gates=(),
            requires_human_approval=True
        )
    
    # Valid phases for scaffolding by component type
    valid_phases = {
        "dto": ["planning", "design", "component"],
        "worker": ["component", "tdd"],
        "adapter": ["component"],
        "manager": ["component"],
        "test": ["tdd"],
        "design_doc": ["planning", "design"],
        "architecture_doc": ["design"]
    }
    
    allowed = valid_phases.get(component_type, [])
    if phase not in allowed:
        return PolicyDecision(
            allow=False,
            reasons=(
                f"Cannot scaffold {component_type} in phase: {phase}",
                f"Valid phases: {', '.join(allowed)}",
                "Use: transition_phase to advance"
            ),
            required_gates=()
        )
    
    return PolicyDecision(allow=True, reasons=(), required_gates=())
```

#### D.4 Tasks (TDD Order)

##### D.4.1 RED: Write Tests for Path-Based Enforcement
**File:** `tests/unit/mcp_server/core/test_policy_file_creation.py`

- [ ] Test: create_file("backend/core/new_service.py") → blocked, suggests scaffold_component
- [ ] Test: create_file("backend/__init__.py") → allowed (package file)
- [ ] Test: create_file("tests/test_new_feature.py") → blocked, suggests scaffold_component
- [ ] Test: create_file("pyproject.toml") → allowed (config file)
- [ ] Test: create_file("requirements.txt") → allowed (dependency file)
- [ ] Test: create_file("scripts/migrate.py") → allowed (utility script)
- [ ] Test: create_file("docs/architecture/DESIGN.md") → blocked, suggests scaffold_design_doc
- [ ] Test: create_file("docs/TODO.md") → allowed (general doc)
- [ ] Test: create_file("proof_of_concepts/test_poc.py") → allowed (POC)
- [ ] Test: create_file("frontend/app.ts") → allowed (future TS, permissive default)
- [ ] Test: scaffold_component(type="dto", phase="planning") → success
- [ ] Test: scaffold_component(type="dto", phase="tdd") → error (wrong phase)
- [ ] Test: scaffold_component when phase NOT in project plan → requires_human_approval=True

##### D.4.2 GREEN: Implement Path-Based Enforcement
- [ ] Add PolicyEngine._decide_create_file() method with path rules
- [ ] Add PolicyEngine._decide_scaffold() method with phase validation
- [ ] Create CreateFileTool wrapper (intercepts create_file with policy check)
- [ ] Update ScaffoldComponentTool to require PolicyEngine
- [ ] Update ScaffoldDesignDocTool to require PolicyEngine
- [ ] Register CreateFileTool in server.py (replaces direct create_file)
- [ ] All tests pass

##### D.4.3 REFACTOR: Update Documentation
- [ ] Update AGENT_PROMPT.md:
  * **ADD path-based rules: "backend/tests Python → MUST scaffold"**
  * **ADD: "Config files (YAML, JSON) → CAN use create_file"**
  * **ADD: "Scripts → CAN use create_file"**
  * Add file type decision tree
- [ ] Update TOOLS.md:
  * Document create_file path restrictions
  * Document scaffold_component enforcement rules
  * Document valid phases per component type
- [ ] Pylint 10/10, mypy clean

#### D.5 Exit Criteria

- [ ] ✅ create_file intercepted by PolicyEngine (path-based enforcement)
- [ ] ✅ Backend Python (backend/**/*.py) → BLOCKED, must use scaffold_component
- [ ] ✅ Test files (tests/test_*.py) → BLOCKED, must use scaffold_component
- [ ] ✅ Design docs (docs/architecture/*.md) → BLOCKED, must use scaffold_design_doc
- [ ] ✅ Config files (*.yml, *.json, *.toml) → ALLOWED via create_file
- [ ] ✅ Scripts (scripts/**) → ALLOWED via create_file
- [ ] ✅ Unknown file types (future TS/JS) → ALLOWED (permissive default)
- [ ] ✅ scaffold_component validates phase via PolicyEngine
- [ ] ✅ Scaffolding outside project plan requires human approval
- [ ] ✅ Tool usage tracked in .st3/state.json
- [ ] ✅ 13+ tests passing (10 path-based + 3 scaffold)

#### D.6 Agent Training Update (Nuanced)

**Add to AGENT_PROMPT.md:**
```markdown
## File Creation Rules (Path-Based)

**BACKEND/TESTS PYTHON (Enforced):**
- ❌ NEVER use create_file for backend/**/*.py (except __*.py)
- ❌ NEVER use create_file for tests/test_*.py
- ✅ ALWAYS use scaffold_component for:
  * backend/**/*.py (DTOs, workers, adapters, managers)
  * tests/**/*.py (test files)

**DESIGN DOCS (Enforced):**
- ❌ NEVER use create_file for docs/architecture/*.md or docs/implementation/*.md
- ✅ ALWAYS use scaffold_design_doc for:
  * docs/architecture/*.md
  * docs/implementation/*.md

**CONFIG/SCRIPTS (Allowed):**
- ✅ CAN use create_file for:
  * *.yml, *.yaml, *.json, *.toml, *.ini, *.txt (config files)
  * requirements*.txt, *.lock (dependency files)
  * scripts/**/* (utility scripts)
  * docs/**/*.md (general docs, not design/architecture)
  * proof_of_concepts/**/* (POC files)

**FUTURE FILE TYPES (Permissive):**
- ✅ CAN use create_file for:
  * *.ts, *.js, *.tsx, *.jsx (TypeScript/JavaScript - until scaffold templates exist)
  * Unknown file types (extensible)

**Decision Tree:**
```
Need new file?
  ├─ Backend Python (backend/**/*.py)?
  │   └─ Use: scaffold_component --type dto|worker|adapter|manager
  ├─ Test file (tests/test_*.py)?
  │   └─ Use: scaffold_component --type test
  ├─ Design doc (docs/architecture/*.md)?
  │   └─ Use: scaffold_design_doc --type design|architecture
  ├─ Config file (*.yml, *.json, *.toml)?
  │   └─ Use: create_file (allowed)
  ├─ Script (scripts/*)?
  │   └─ Use: create_file (allowed)
  └─ Other?
      └─ Use: create_file (permissive default)
```
```

---

### Phase E: PR/Close Enforcement (Retrofit create_pr/close_issue)

**Goal:** Add artifact validation to PR creation and issue closing.

**Status:** NOT STARTED  
**Dependencies:** Phase A  
**Estimated Effort:** 2 days  
**Risk Level:** 🟡 MEDIUM (artifact validation complexity)

#### E.1 Changes Required

##### E.1.1 GitHubManager.create_pr() - Add Enforcement
**Before:**
```python
def create_pr(self, title, body, head, base="main", draft=False):
    pr = self.adapter.create_pr(title=title, body=body, head=head, base=base, draft=draft)
    return {"number": pr.number, "url": pr.html_url, "title": pr.title}
```

**After:**
```python
def create_pr(self, title, body, head, base="main", draft=False):
    # NEW: Policy check
    if self.policy:
        ctx = PolicyContext(
            operation="create_pr",
            branch=head,
            phase=self.policy.phase_state.get_phase(head),
            files=(),
            metadata={"title": title, "base": base}
        )
        decision = self.policy.decide(ctx)
        if not decision.allow:
            raise ValidationError("\n".join(decision.reasons))
    
    # EXISTING logic (unchanged)
    pr = self.adapter.create_pr(title=title, body=body, head=head, base=base, draft=draft)
    return {"number": pr.number, "url": pr.html_url, "title": pr.title}
```

##### E.1.2 GitHubManager.close_issue() - Add Enforcement
**Before:**
```python
def close_issue(self, issue_number: int) -> None:
    self.adapter.update_issue(issue_number, state="closed")
```

**After:**
```python
def close_issue(self, issue_number: int) -> None:
    # NEW: Policy check
    if self.policy:
        # Get current branch (assume issue tied to branch)
        from mcp_server.adapters.git_adapter import GitAdapter
        git_adapter = GitAdapter()
        branch = git_adapter.get_current_branch()
        
        ctx = PolicyContext(
            operation="close_issue",
            branch=branch,
            phase=self.policy.phase_state.get_phase(branch),
            files=(),
            metadata={"issue_number": issue_number}
        )
        decision = self.policy.decide(ctx)
        if not decision.allow:
            raise ValidationError("\n".join(decision.reasons))
    
    # EXISTING logic (unchanged)
    self.adapter.update_issue(issue_number, state="closed")
```

##### E.1.3 PolicyEngine._decide_create_pr() - Artifact Validation
```python
def _decide_create_pr(self, ctx: PolicyContext) -> PolicyDecision:
    """Decide for PR creation."""
    phase = ctx.phase
    
    # Must be in REFACTOR phase (completed TDD)
    if phase not in ["refactor", "integration"]:
        return PolicyDecision(
            allow=False,
            reasons=(f"Cannot create PR from phase: {phase}",
                     "Complete TDD cycle (RED→GREEN→REFACTOR) first",
                     "Use: transition_phase to advance"),
            required_gates=()
        )
    
    # Check required artifacts (Phase 4)
    issue_number = self.phase_state.get_issue_number(ctx.branch)
    if issue_number:
        artifacts_dir = Path(f"docs/development/issues/{issue_number}")
        required_files = [
            artifacts_dir / "implementation_plan.md",
            artifacts_dir / "component_design.md"
        ]
        missing = [f for f in required_files if not f.exists()]
        if missing:
            return PolicyDecision(
                allow=False,
                reasons=(f"Missing required artifacts: {[str(f) for f in missing]}",
                         "Create with: scaffold_design_doc"),
                required_gates=()
            )
    
    # Require passing tests + QA
    return PolicyDecision(
        allow=True,
        reasons=(),
        required_gates=("tests", "pylint", "mypy", "pyright")
    )
```

#### E.2 Tasks (TDD Order)

##### E.2.1 RED: Write Tests
- [ ] Test: create_pr from phase=approved → error (not in TDD yet)
- [ ] Test: create_pr from phase=refactor, no artifacts → error
- [ ] Test: create_pr from phase=refactor, has artifacts, failing QA → error
- [ ] Test: create_pr from phase=refactor, has artifacts, passing QA → success
- [ ] Test: close_issue from phase=integration → error (need docs phase)
- [ ] Test: close_issue from phase=documentation, has docs → success

##### E.2.2 GREEN: Implement Changes
- [ ] Update GitHubManager.create_pr()
- [ ] Update GitHubManager.close_issue()
- [ ] Add PolicyEngine._decide_create_pr()
- [ ] Add PolicyEngine._decide_close_issue()
- [ ] All tests pass

##### E.2.3 REFACTOR: Quality
- [ ] Pylint 10/10, mypy clean
- [ ] Integration test: Full workflow (commit → PR → close)

#### E.3 Exit Criteria

- [ ] Cannot create PR unless in REFACTOR phase with artifacts
- [ ] Cannot close issue unless in DOCUMENTATION phase with docs
- [ ] Error messages reference scaffold tools
- [ ] 6+ tests passing

---

### Phase F: File Editing Enforcement (Extend SafeEdit Validators)

**Goal:** **Extend safe_edit_file to support diverse file types**, make it the preferred editing tool.

**Status:** NOT STARTED  
**Dependencies:** Phase A, Phase D  
**Estimated Effort:** 3 days  
**Risk Level:** 🟡 MEDIUM (validator extension complexity)

#### F.1 Problem Statement

**Current State:** 
- `safe_edit_file` only validates Python, Markdown, Template
- Agents use `replace_string_in_file` for YAML, JSON, TypeScript (no validation available)
- Result: No syntax checking for non-Python files

**Target State (Nuanced):**
- **Extend safe_edit_file validators** to support:
  * Python (existing: ast.parse)
  * Markdown (existing: structure check)
  * YAML (new: yaml.safe_load)
  * JSON (new: json.loads)
  * TOML (new: toml.loads)
  * TypeScript/JavaScript (future: quick-lint-js or skip validation)
- **Keep replace_string_in_file available** for:
  * Emergency edits (validation fails but human knows it's correct)
  * Unknown file types (not yet supported by safe_edit_file)
  * Batch operations (multi_replace still useful)
- **Encourage safe_edit_file via AGENT_PROMPT.md** (preferred, not mandatory)

#### F.2 Implementation Strategy

##### F.2.1 EXTEND SafeEdit Validators (ADD Support for More File Types)
**File:** `mcp_server/tools/safe_edit_tool.py`

**Add new validators:**
```python
class YAMLValidator:
    """Fast YAML syntax validation."""
    
    def validate(self, content: str) -> tuple[bool, str]:
        import yaml
        try:
            yaml.safe_load(content)  # Parse only, ~10-50ms
            return (True, "Valid YAML")
        except yaml.YAMLError as e:
            return (False, f"YAML syntax error: {e}")

class JSONValidator:
    """Fast JSON syntax validation."""
    
    def validate(self, content: str) -> tuple[bool, str]:
        import json
        try:
            json.loads(content)  # Parse only, ~1-10ms
            return (True, "Valid JSON")
        except json.JSONDecodeError as e:
            return (False, f"JSON syntax error at line {e.lineno}: {e.msg}")

class TOMLValidator:
    """Fast TOML syntax validation."""
    
    def validate(self, content: str) -> tuple[bool, str]:
        try:
            import tomllib  # Python 3.11+
        except ImportError:
            import tomli as tomllib  # Fallback
        
        try:
            tomllib.loads(content)  # Parse only, ~10-30ms
            return (True, "Valid TOML")
        except Exception as e:
            return (False, f"TOML syntax error: {e}")

class TypeScriptValidator:
    """Fast TypeScript/JavaScript syntax validation (future)."""
    
    def validate(self, content: str) -> tuple[bool, str]:
        # Option 1: quick-lint-js (fast linter, ~50-100ms)
        # Option 2: Skip validation (permissive for now)
        # Option 3: Basic check (balanced braces/parens)
        
        # For now: SKIP validation (too complex, agents can iterate)
        return (True, "TypeScript validation skipped (not implemented)")
```

**Update SafeEditTool to dispatch validators:**
```python
class SafeEditTool(BaseTool):
    def __init__(self):
        self.validators = {
            ".py": PythonValidator(),
            ".md": MarkdownValidator(),
            ".yml": YAMLValidator(),
            ".yaml": YAMLValidator(),
            ".json": JSONValidator(),
            ".toml": TOMLValidator(),
            ".ts": TypeScriptValidator(),
            ".js": TypeScriptValidator(),
            ".tsx": TypeScriptValidator(),
            ".jsx": TypeScriptValidator(),
        }
    
    async def execute(self, params: SafeEditInput) -> ToolResult:
        file_path = Path(params.filePath)
        validator = self.validators.get(file_path.suffix)
        
        if validator is None:
            # Unknown file type: SKIP validation (permissive)
            Path(params.filePath).write_text(params.content)
            return ToolResult.text(f"✅ Written (no validation): {params.filePath}")
        
        # Fast validation
        is_valid, message = validator.validate(params.content)
        if not is_valid:
            return ToolResult.error(f"Validation failed:\n{message}")
        
        # Atomic write
        tmp_file = file_path.with_suffix(file_path.suffix + ".tmp")
        tmp_file.write_text(params.content)
        tmp_file.replace(file_path)
        
        return ToolResult.text(f"✅ Written: {params.filePath}")
```

##### F.2.2 KEEP replace_string_in_file (Emergency/Batch Edits)
**Action:** Keep `replace_string_in_file` available, but discourage in AGENT_PROMPT.md

**Rationale:**
- Useful for batch operations (multi_replace_string_in_file)
- Emergency edits when validation incorrectly fails
- Unknown file types not yet supported by safe_edit_file

##### F.2.3 UPDATE Agent Prompt (Encourage, Not Mandate)

**Existing behavior (KEEP AS-IS):**
```python
class SafeEditTool(BaseTool):
    """Fast-only validation (NO subprocess calls, NO policy checks)."""
    
    async def execute(self, params: SafeEditInput) -> ToolResult:
        # 1. Fast validation ONLY:
        #    - ast.parse() for Python syntax (NO pylint/mypy)
        #    - Markdown structure check (NO linting)
        #    - Template variable check (NO rendering)
        
        # 2. NO PolicyEngine check (orthogonal to workflow)
        #    - Edits don't change phase
        #    - Edits don't require gates
        #    - Validation is about syntax, not workflow
        
        # 3. Write file if validation passes
        #    - Atomic write (.tmp pattern)
        #    - Fast (<500ms target)
        
        return result
```

**Key Insight:** SafeEdit provides **syntax validation**, not **workflow enforcement**. This is correct - file edits should be fast and not blocked by phase rules. The enforcement comes from:
1. **Cannot CREATE files** without scaffold tools (Phase D)
2. **Cannot COMMIT files** without passing gates (Phase C)

##### F.2.3 UPDATE Agent Prompt (CRITICAL)
**File:** `AGENT_PROMPT.md`

**Add guidelines (not hard rules):**
```markdown
## File Editing Best Practices

**PREFERRED: safe_edit_file (Validated)**
- ✅ PREFER safe_edit_file for:
  * Python (ast.parse validation)
  * Markdown (structure validation)
  * YAML (yaml.safe_load validation)
  * JSON (json.loads validation)
  * TOML (toml.loads validation)
- Benefits: Catches syntax errors before writing, atomic writes

**ALLOWED: replace_string_in_file (Unvalidated)**
- ⚠️  CAN use replace_string_in_file for:
  * Batch operations (multi_replace_string_in_file)
  * Emergency edits (when validation incorrectly fails)
  * Unknown file types (not yet supported by safe_edit_file)
- Caution: No validation, ensure edits are correct

**Decision Tree:**
```
Need to edit file?
  ├─ Python/Markdown/YAML/JSON/TOML?
  │   └─ PREFER: safe_edit_file (catches syntax errors)
  ├─ Batch operation (10+ edits)?
  │   └─ USE: multi_replace_string_in_file (efficiency)
  ├─ Unknown file type?
  │   └─ USE: replace_string_in_file (no validator available)
  └─ Validation incorrectly failing?
      └─ USE: replace_string_in_file (bypass validation)
```
```

#### F.3 Tasks (TDD Order)

##### F.3.1 RED: Write Tests for Extended Validators
**File:** `tests/unit/mcp_server/tools/test_safe_edit_validators.py`

- [ ] Test: safe_edit_file with valid Python → success (existing)
- [ ] Test: safe_edit_file with invalid Python syntax → error (existing)
- [ ] Test: safe_edit_file with valid YAML → success (NEW)
- [ ] Test: safe_edit_file with invalid YAML syntax → error (NEW)
- [ ] Test: safe_edit_file with valid JSON → success (NEW)
- [ ] Test: safe_edit_file with invalid JSON (missing comma) → error (NEW)
- [ ] Test: safe_edit_file with valid TOML → success (NEW)
- [ ] Test: safe_edit_file with invalid TOML → error (NEW)
- [ ] Test: safe_edit_file with TypeScript → success (skip validation for now)
- [ ] Test: safe_edit_file with unknown extension (.xyz) → success (skip validation)
- [ ] Test: safe_edit_file performance benchmark (<500ms target)

##### F.3.2 GREEN: Implement Validators
- [ ] Add YAMLValidator to safe_edit_tool.py
- [ ] Add JSONValidator to safe_edit_tool.py
- [ ] Add TOMLValidator to safe_edit_tool.py
- [ ] Add TypeScriptValidator (skip validation for now)
- [ ] Update SafeEditTool to dispatch by file extension
- [ ] Handle unknown file types (skip validation, permissive)
- [ ] Add tomli to requirements-dev.txt (Python <3.11 fallback)
- [ ] All tests pass

##### F.3.3 REFACTOR: Update Documentation
- [ ] Update AGENT_PROMPT.md:
  * Add file editing best practices (prefer safe_edit_file)
  * Document supported file types (Python, Markdown, YAML, JSON, TOML)
  * Clarify replace_string_in_file is allowed (not forbidden)
  * Add decision tree (when to use which tool)
- [ ] Update TOOLS.md:
  * Document safe_edit_file validators per file type
  * Document performance characteristics (<500ms)
  * Document when to use replace_string_in_file (batch/emergency/unknown)
- [ ] Pylint 10/10, mypy clean

#### F.4 Exit Criteria

- [ ] ✅ safe_edit_file supports Python (existing)
- [ ] ✅ safe_edit_file supports Markdown (existing)
- [ ] ✅ safe_edit_file supports YAML (new validator)
- [ ] ✅ safe_edit_file supports JSON (new validator)
- [ ] ✅ safe_edit_file supports TOML (new validator)
- [ ] ✅ safe_edit_file skips validation for TypeScript/unknown types (permissive)
- [ ] ✅ replace_string_in_file KEPT available (emergency/batch use)
- [ ] ✅ AGENT_PROMPT.md encourages safe_edit_file (not mandates)
- [ ] ✅ Performance <500ms per edit (fast validation)
- [ ] ✅ 11+ tests passing (10 validators + 1 performance)

#### F.5 Why NO PolicyEngine in SafeEdit? (Unchanged)

**Question:** Why doesn't SafeEdit call PolicyEngine.decide()?

**Answer:** File edits are **orthogonal to workflow phases**:
1. **Edits don't change phase** - Editing a file doesn't advance RED→GREEN→REFACTOR
2. **Enforcement happens at commit** - PolicyEngine blocks commits with invalid edits via QA gates
3. **Fast validation is critical** - SafeEdit must be <500ms, PolicyEngine.decide() + gates would be 10-30s
4. **Syntax vs Workflow** - SafeEdit validates syntax (ast.parse, yaml.safe_load), PolicyEngine validates workflow (phase rules)
```
Agent edits file → safe_edit_file (syntax validation, <500ms)
                                 ↓
Agent commits changes → git_add_or_commit (PolicyEngine validation, QA gates, 10-30s)
                                          ↓
                                   Blocked if tests/QA fail
```

**Result:** SafeEdit is fast (agent productivity), enforcement happens at commit (workflow integrity).

**Phases D-G:** Follow same strict enforcement pattern as Phase C:

- **Phase D (File Creation - Path-Based Enforcement):** 
  * ✅ KEEP create_file, ADD PolicyEngine path-based interception
  * ❌ BLOCK backend/**/*.py (except __*.py) → MUST use scaffold_component
  * ❌ BLOCK tests/test_*.py → MUST use scaffold_component
  * ❌ BLOCK docs/architecture/*.md → MUST use scaffold_design_doc
  * ✅ ALLOW *.yml, *.json, *.toml (config files)
  * ✅ ALLOW scripts/**/* (utility scripts)
  * ✅ ALLOW unknown file types (permissive for future TS/JS)
  * Result: Selective enforcement - architecture files must scaffold, config files can use create_file

- **Phase E (PR/Close):** CreatePRTool validates integration phase in project plan, CloseIssueTool validates documentation phase (NO backward compatibility)

- **Phase F (File Editing - Extend SafeEdit Validators):**
  * ✅ EXTEND safe_edit_file validators: Python, Markdown, YAML, JSON, TOML (TypeScript skip for now)
  * ✅ KEEP replace_string_in_file (allowed for batch/emergency/unknown types)
  * ✅ ENCOURAGE safe_edit_file via AGENT_PROMPT.md (preferred, not mandatory)
  * ✅ Enforcement happens at COMMIT (PolicyEngine + QA gates), not at edit
  * Result: Fast validation for common file types, permissive for edge cases

- **Phase G (Quality):** Mandatory coverage/complexity gates in REFACTOR phase (NO skip option)

**Key Principle Across All Phases:**
```python
# EVERYWHERE in managers (NO exceptions):
class Manager:
    def __init__(self, adapter, policy: PolicyEngine):  # REQUIRED
        if policy is None:
            raise TypeError("PolicyEngine is REQUIRED. No opt-out mode.")
        self.policy = policy

# EVERYWHERE in tools (NO opt-out):
decision = manager.policy.decide(ctx)
if decision.requires_human_approval:
    raise ValidationError("Human approval required:\n" + "\n".join(decision.reasons))
if not decision.allow:
    raise ValidationError("Operation blocked:\n" + "\n".join(decision.reasons))
```

**NO Opt-Out:** All `policy=None` checks removed, all `if self.policy:` conditions removed. Enforcement is unconditional and mandatory.

**Goal:** Add coverage, complexity, size checks to QAManager and integrate into REFACTOR commits.

**Status:** NOT STARTED  
**Dependencies:** Phase C  
**Estimated Effort:** 3 days  
**Risk Level:** 🟡 MEDIUM (new metrics, integration complexity)

#### G.1 Components

##### G.1.1 QAManager Extensions
**File:** `mcp_server/managers/qa_manager.py`

**New methods:**
```python
def run_coverage(self, test_path: str = "tests/") -> dict[str, Any]:
    """Run pytest with coverage reporting."""
    result = subprocess.run(
        ["pytest", test_path, "--cov=backend", "--cov-report=json"],
        capture_output=True,
        text=True
    )
    
    # Parse coverage.json
    coverage_data = json.loads(Path("coverage.json").read_text())
    return {
        "line_coverage": coverage_data["totals"]["percent_covered"],
        "branch_coverage": coverage_data["totals"]["percent_covered_branches"],
        "missing_lines": coverage_data["totals"]["missing_lines"]
    }

def run_complexity(self, files: list[str]) -> dict[str, Any]:
    """Run radon complexity check."""
    import radon.complexity as radon_cc
    
    results = []
    for file in files:
        code = Path(file).read_text()
        complexity = radon_cc.cc_visit(code)
        results.append({
            "file": file,
            "functions": [
                {"name": c.name, "complexity": c.complexity, "line": c.lineno}
                for c in complexity
            ]
        })
    return {"results": results}
```

##### G.1.2 PolicyEngine Integration
**File:** `mcp_server/core/policy.py`

**Update _decide_commit() for REFACTOR phase:**
```python
def _decide_commit(self, ctx: PolicyContext) -> PolicyDecision:
    # ... existing logic ...
    
    if phase == "refactor":
        # Require tests + QA + coverage + complexity
        return PolicyDecision(
            allow=True,
            reasons=(),
            required_gates=("tests", "pylint", "mypy", "pyright", "coverage", "complexity")
        )
```

**Update GitManager.commit_tdd_phase() to run new gates:**
```python
if "coverage" in decision.required_gates:
    coverage = qa_manager.run_coverage()
    if coverage["line_coverage"] < 90:
        raise ValidationError(
            f"Coverage below 90%: {coverage['line_coverage']:.1f}%",
            hints=["Add tests to increase coverage"]
        )

if "complexity" in decision.required_gates:
    complexity = qa_manager.run_complexity(staged_files)
    high_complexity = [
        f"{r['file']}:{f['name']} (complexity {f['complexity']})"
        for r in complexity["results"]
        for f in r["functions"]
        if f["complexity"] > 10
    ]
    if high_complexity:
        raise ValidationError(
            f"High complexity functions:\n" + "\n".join(high_complexity),
            hints=["Refactor functions with complexity > 10"]
        )
```

#### G.2 Tasks (TDD Order)

##### G.2.1 RED: Write Tests
- [ ] Test: run_coverage() returns line + branch coverage
- [ ] Test: run_complexity() returns per-function complexity
- [ ] Test: REFACTOR commit with coverage <90% → error
- [ ] Test: REFACTOR commit with complexity >10 → error
- [ ] Test: REFACTOR commit with coverage ≥90% + complexity ≤10 → success

##### G.2.2 GREEN: Implement
- [ ] Add run_coverage() to QAManager
- [ ] Add run_complexity() to QAManager
- [ ] Update PolicyEngine._decide_commit()
- [ ] Update GitManager.commit_tdd_phase()
- [ ] Add radon to requirements-dev.txt

##### G.2.3 REFACTOR: Quality
- [ ] Pylint 10/10, mypy clean
- [ ] Integration test: Full REFACTOR commit with all gates

#### G.3 Exit Criteria

- [ ] Coverage measured at REFACTOR commit
- [ ] Complexity measured at REFACTOR commit
- [ ] REFACTOR blocked if coverage <90% or complexity >10
- [ ] Error messages actionable
- [ ] 5+ tests passing

---

## 4. Testing Strategy

### 4.1 Test Pyramid (Strict Enforcement Focus)

| Level | Count | Focus |
|-------|-------|-------|
| Unit | 75+ | PolicyEngine decisions, PhaseStateEngine transitions (WITH project plan validation), manager methods (MANDATORY enforcement) |
| Integration | 30+ | Full workflows (init → phase select → enforce → approve → commit), label sync, artifact validation, human approval workflow |
| Smoke | 8 | Manual verification of error messages, performance, audit trail completeness |

### 4.2 Critical Test Scenarios

1. **Project Initialization & Phase Selection:**
   - initialize_project(issue_type="feature") → 7-phase plan created
   - initialize_project(issue_type="bug") → 6-phase plan (skip design)
   - initialize_project(issue_type="docs") → 4-phase plan (skip tdd + integration)
   - initialize_project(issue_type="hotfix") → 3-phase minimal plan (requires approval for all operations)
   - Project plan persists in .st3/projects.json

2. **Strict Enforcement:**
   - Commit to phase NOT in project plan → requires_human_approval=True
   - Commit to main → blocked
   - Commit GREEN without tests → blocked
   - Commit REFACTOR without QA gates → blocked
   - Create PR from TDD phase → blocked (must be in integration phase per plan)
   - Close issue from REFACTOR phase → blocked (must be in documentation phase per plan)
   - scaffold_design_doc when project_plan.issue_type="bug" → blocked (design skipped for bugs)

3. **Human Approval Workflow:**
   - Agent requests deviation → raises ValidationError with requires_human_approval
   - Human calls approve_deviation → approval recorded in audit trail
   - Agent retries operation with approval → succeeds
   - Approval logged: timestamp, requested_action, reason, approved_by
   - Multiple approvals tracked per branch

4. **Phase Plan Adherence:**
   - Feature project (7 phases): discovery → planning → design → component → tdd → integration → documentation
   - Bug project (6 phases): discovery → planning → component → tdd → integration → documentation (skip design)
   - Docs project (4 phases): discovery → planning → component → documentation (skip tdd + integration)
   - Custom project: Human-specified phase sequence

5. **Error Message Quality:**
   - All errors reference specific ST3 tools (not manual commands)
   - File paths are clickable (VS Code links)
   - Line numbers included for QA violations
   - Human approval errors include exact approval command to run

### 4.3 Performance Benchmarks

| Operation | Target | Measurement |
|-----------|--------|-------------|
| SafeEdit | <500ms | Time from tool call to response (no enforcement) |
| Commit (RED) | <2s | No gate execution |
| Commit (GREEN) | <10s | Tests execution |
| Commit (REFACTOR) | <30s | Tests + QA + coverage |
| Phase transition | <5s | State update + label sync + project plan validation |
| Project initialization | <3s | Phase plan creation + metadata write |
| Human approval | <1s | Audit trail write |

### 4.4 NO Backward Compatibility Tests

**REMOVED:** All tests for `policy=None` mode (no opt-out mechanism exists)

**ADDED:** Tests for strict enforcement:
- `test_manager_requires_policy()` - Verify TypeError when policy=None
- `test_commit_without_approval_blocked()` - Verify deviation escalation
- `test_human_approval_unblocks_operation()` - Verify approval workflow
- `test_project_plan_enforcement()` - Verify phase plan adherence

---

## 5. Rollout Plan (Breaking Change)

### 5.1 Migration Strategy

**Phase 0-A: Core Infrastructure (Weeks 1-3)**
- Deploy PolicyEngine, PhaseStateEngine, ProjectPhaseSelector
- Add `project_plan` field to existing `.st3/phase_state.json`
- **Breaking Change:** All managers now require `policy` parameter (no `| None`)
- **Migration Script:** Existing projects get default phase plan:
  ```python
  # scripts/migrate_to_strict_enforcement.py
  for project_dir in find_st3_projects():
      metadata = load_project_metadata(project_dir)
      if "project_plan" not in metadata:
          # Assign default feature template (most permissive)
          metadata["project_plan"] = {
              "issue_type": "feature",
              "required_phases": ["discovery", "planning", "design", "component", "tdd", "integration", "documentation"],
              "skip_reason": "Migrated from pre-enforcement project"
          }
          save_project_metadata(project_dir, metadata)
  ```

**Phase B-C: Tool Updates (Weeks 4-5)**
- Update GitCommitTool, CreatePRTool, CloseIssueTool with strict enforcement
- Deploy ApproveDeviationTool, TransitionPhaseTool
- Update server.py to inject PolicyEngine into all managers (MANDATORY)
- **NO feature flags** - enforcement is always on
- **NO rollback mechanism** - breaking change by design

**Phase D-G: Remaining Tools (Weeks 6-8)**
- Update ScaffoldTool with phase awareness (validate project plan)
- SafeEditTool remains unchanged (no enforcement needed)
- Integrate QA gates (mandatory in REFACTOR phase, no skip)
- Deploy label sync automation

### 5.2 Training & Documentation

**For Developers Using MCP Server:**
1. **Project Initialization Guide:**
   - When to use `issue_type="feature"` (full 7-phase workflow)
   - When to use `issue_type="bug"` (skip design phase)
   - When to use `issue_type="docs"` (skip tdd + integration)
   - When to use `issue_type="refactor"` (skip design + component)
   - When to use `issue_type="hotfix"` (minimal 3-phase, requires approval)
   - Custom phase selection for edge cases

2. **Phase Selection Decision Tree:**
   ```
   ┌─────────────────────────────────────┐
   │ What type of work?                  │
   └─────────────────────────────────────┘
                     │
         ┌───────────┼───────────┬───────────┬──────────┐
         │           │           │           │          │
      Feature      Bug       Refactor     Docs      Hotfix
         │           │           │           │          │
      7 phases   6 phases   5 phases   4 phases   3 phases
    (all steps) (no design) (no design  (no tdd  (minimal,
                             /component) /integ)  approval)
   ```

3. **Human Approval Workflow:**
   - Agent error: "Human approval required: Phase 'X' not in project plan"
   - Human investigates: Is deviation justified?
   - Human approves: `approve_deviation(branch, action, reason, approved_by)`
   - Agent retries operation with approval token
   - Deviation logged in audit trail (.st3/state.json → human_approvals[])

4. **Audit Trail Access:**
   ```python
   # Query all approvals for branch
   state = PhaseStateEngine.load_state()
   approvals = state["branches"]["feature/issue-42"]["human_approvals"]
   for approval in approvals:
       print(f"{approval['timestamp']}: {approval['approved_by']} approved '{approval['requested_action']}'")
       print(f"  Reason: {approval['reason']}")
   ```

**For AI Agents:**
1. **Strict Enforcement Rules:**
   - Cannot bypass PolicyEngine under any circumstance
   - Cannot use `policy=None` (removed from codebase)
   - Must follow project-specific phase plan
   - Cannot self-approve deviations

2. **Phase Plan Adherence:**
   - Read project plan: `policy.phase_state.get_project_plan(branch)`
   - Validate operation: `decision = policy.decide(ctx)` (includes project_plan in ctx)
   - If `decision.requires_human_approval`, escalate to human (raise ValidationError)
   - Never proceed without human approval when flagged

3. **Escalation Protocol:**
   ```python
   # When PolicyEngine returns requires_human_approval=True:
   raise ValidationError(
       f"Human approval required:\n" + "\n".join(decision.reasons),
       hints=[
           "Contact project lead for approval",
           f"Run: approve_deviation(branch='{branch}', action='...', reason='...', approved_by='...')",
           "Then retry this operation"
       ]
   )
   ```

4. **Error Interpretation:**
   - `"Phase 'X' not in project plan"` → Need human approval to deviate
   - `"Tests failing (N)"` → Fix failing tests before committing
   - `"Quality gates failed"` → Fix pylint/mypy issues before REFACTOR commit
   - All errors include actionable hints (specific tool commands to run)

### 5.3 Monitoring & Metrics

**Track Enforcement Effectiveness:**
- **Enforcement Rate:** 100% operations go through PolicyEngine (metric: count(decide() calls) / count(manager method calls))
- **Human Approval Rate:** % operations requiring human approval (target: <20%)
- **Phase Plan Adherence:** % projects following their phase plan without deviations (target: >80%)
- **Deviation Reasons:** Top 5 reasons for approved deviations (identify phase plan misconfiguration)
- **Audit Trail Completeness:** % approvals logged with full context (target: 100%)

**Alerts:**
- ❌ **PolicyEngine bypass detected** (should be impossible, but log TypeError when policy=None)
- ⚠️ **High human approval rate** (>20% may indicate phase plan templates need refinement)
- ⚠️ **Missing project plan** (all projects must have phase plan after migration)
- ⚠️ **Unapproved deviation attempt** (agent tried to force operation without approval)

**Dashboards:**
```python
# scripts/enforcement_metrics.py
def generate_dashboard():
    all_projects = find_st3_projects()
    metrics = {
        "total_projects": len(all_projects),
        "projects_with_plan": sum(1 for p in all_projects if has_project_plan(p)),
        "total_approvals": sum(count_approvals(p) for p in all_projects),
        "approval_reasons": aggregate_approval_reasons(all_projects),
        "phase_plan_distribution": {
            "feature": count_by_issue_type(all_projects, "feature"),
            "bug": count_by_issue_type(all_projects, "bug"),
            "docs": count_by_issue_type(all_projects, "docs"),
            # ...
        }
    }
    return metrics
```

### 5.4 Rollback Plan (NONE)

**NO ROLLBACK MECHANISM EXISTS.**

- This is a **breaking change by design** (no backward compatibility)
- Projects cannot opt-out of enforcement
- No feature flags, no environment variables to disable enforcement
- PolicyEngine is REQUIRED parameter (TypeError if None)

**If critical issues found:**

1. **Use Built-in Bypass Mechanisms:**
   - `issue_type="hotfix"` for urgent fixes (3-phase minimal process)
   - `approve_deviation` to bypass specific restrictions
   - Custom phase plans for edge cases

2. **Fix Bugs in PolicyEngine Logic:**
   - Update policy rules (not disable enforcement)
   - Add new decision paths in `PolicyEngine.decide()`
   - Refine PHASE_TEMPLATES if templates too restrictive

3. **Emergency Override (Last Resort):**
   - Temporarily modify PolicyEngine.decide() to always return allow=True
   - Deploy hotfix with permissive policy
   - Fix root cause issue
   - Restore strict enforcement

**Rationale:** User requirement is "strikte enforcement" with "human in the loop" phase selection. The goal is to eliminate agent autonomy in workflow decisions. Rollback defeats this purpose. If enforcement is wrong, fix the rules, don't remove enforcement.
2. Phase C-E: Enable for feature branches only (not main)
3. Phase G: Enable for all branches

---

## 6. Success Metrics (Updated for Strict Enforcement)

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Code duplication | 0 new tool classes | Code review: No CreatePRTool, CloseIssueTool, etc. |
| Tool coverage | 31/31 tools with enforcement | Audit: All tools go through managers with PolicyEngine (REQUIRED) |
| Enforcement strictness | 100% operations enforced | CI: All managers raise TypeError if policy=None |
| Phase plan adherence | 100% operations follow project plan | Audit: All PolicyEngine decisions validate project_plan |
| Human approval tracking | 100% deviations logged | Audit: All human_approvals[] persisted in .st3/state.json |
| Test coverage | 95%+ on new code | pytest-cov: policy.py, phase_state.py, project_phase_selector.py |
| Performance | <10s commit (GREEN), <30s (REFACTOR) | Time measurement in integration tests |
| Enforcement bypass attempts | 0 bypass paths (no opt-out) | Security audit: No policy=None checks, no if self.policy: conditions |
| Error message quality | 100% reference ST3 tools | Manual review: No "run git commit" messages, all errors actionable |

**Key Changes from Original V2:**
- ❌ REMOVED: "Backward compatibility: 100% tests pass with policy=None" (no opt-out mode)
- ✅ ADDED: "Enforcement strictness: 100% operations enforced" (mandatory enforcement)
- ✅ ADDED: "Phase plan adherence: 100% operations follow project plan"
- ✅ ADDED: "Human approval tracking: 100% deviations logged"

---

## 7. Risk Assessment (Updated)

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| State file corruption | Low | High | Atomic writes with .tmp files (proven in Phase 0) |
| Phase transition bugs | Medium | High | Comprehensive state machine tests (10+ scenarios) + project plan validation tests (8+ scenarios) |
| Performance regression | Low | Medium | Benchmark tests, async subprocess calls, project plan cached in memory |
| GitHub API rate limits | Low | Medium | Retry logic, exponential backoff, label sync non-critical |
| Breaking change resistance | Medium | High | Migration script (default phase plans), training documentation, human approval workflow |
| Phase plan misconfiguration | Medium | Medium | Template validation, human can adjust with custom phases, metrics dashboard (high approval rate = bad template) |
| Tool proliferation confusion | Low | Low | Clear documentation, deprecate duplicates |

**New Risks (Strict Enforcement):**
- **Breaking change resistance:** Some users may resist mandatory enforcement. Mitigation: Migration script assigns default "feature" plan to existing projects (most permissive), training docs explain approval workflow.
- **Phase plan misconfiguration:** Templates may not fit all workflows. Mitigation: Custom phase plans supported, metrics track high approval rates (indicates template needs refinement).

---

## 8. Documentation Requirements

### 8.1 New Documents

1. **PolicyEngine Reference** (`docs/reference/POLICY_ENGINE.md`)
   - Decision matrix (all operations)
   - How to add new rules
   - How to debug policy decisions
   - **NEW:** Project plan validation logic
   - **NEW:** Human approval escalation protocol

2. **PhaseStateEngine Reference** (`docs/reference/PHASE_STATE_ENGINE.md`)
   - State machine diagram
   - .st3/state.json schema
   - How to query phase state
   - How to reset state (emergency)
   - **NEW:** Project plan storage schema
   - **NEW:** Human approval audit trail format

3. **Enforcement Integration Guide** (`docs/development/ENFORCEMENT_INTEGRATION.md`)
   - How to add enforcement to new tools
   - Dependency injection pattern (PolicyEngine REQUIRED)
   - Testing strict enforcement (no policy=None tests)
   - **REMOVED:** Backward compatibility guidelines (no opt-out)

4. **Project Phase Selection Guide** (`docs/reference/PROJECT_PHASE_SELECTION.md`) - NEW
   - Decision tree: When to use feature/bug/docs/refactor/hotfix
   - Custom phase plan creation
   - Phase template reference (all 5 templates)
   - Examples: "Documentation-only change" → docs template (4 phases)

5. **Human Approval Workflow** (`docs/reference/HUMAN_APPROVAL_WORKFLOW.md`) - NEW
   - When agent requires approval (decision tree)
   - How to use approve_deviation tool
   - How to query audit trail
   - Best practices: When to approve vs reject

### 8.2 Updated Documents

1. **AGENT_PROMPT.md:**
   - Add transition_phase tool
   - Add approve_deviation tool (human-only)
   - Add initialize_project with issue_type parameter
   - Remove create_file references
   - Update commit workflow (must transition phases according to project plan)
   - **NEW:** Add escalation protocol (requires_human_approval errors)

2. **TOOLS.md:**
   - Document transition_phase
   - Document approve_deviation
   - Document enforcement behavior per tool (MANDATORY, no opt-out)
   - Add troubleshooting section (policy errors, approval workflow)
   - **REMOVED:** policy=None documentation (no longer supported)

3. **PHASE_WORKFLOWS.md:**
   - Add enforcement behavior per phase
   - Update transition diagrams (show policy checks + project plan validation)
   - Add examples (RED→GREEN with enforcement, deviation approval)
   - **NEW:** Add phase plan templates (feature/bug/docs/refactor/hotfix)

---

## 9. Conclusion

**Key Achievements:**
- ✅ **Zero duplication:** Reuse all 31 existing tools via retrofit
- ✅ **Minimal changes:** <50 LOC per tool (dependency injection only)
- ✅ **Strict enforcement:** NO opt-out, PolicyEngine REQUIRED in all managers
- ✅ **Human-in-the-loop:** Phase selection at initialization, approval workflow for deviations
- ✅ **Comprehensive enforcement:** All choke points covered (commit/PR/close/file creation) with project plan validation
- ✅ **Maintainable:** Single PolicyEngine, single PhaseStateEngine, single ProjectPhaseSelector, clear separation

**Differences from V1 Plan:**
- ❌ REMOVED: 10+ duplicate tool proposals
- ✅ ADDED: Retrofit strategy with dependency injection
- ✅ REDUCED: Development time (~40% less code)
- ❌ REMOVED: Backward compatibility (breaking change by design)
- ✅ ADDED: Project phase selection (human-in-the-loop)
- ✅ ADDED: Human approval workflow (deviation tracking)
- ✅ CLARIFIED: Integration strategy for existing tools

**Critical Requirements Met:**
1. ✅ **"Strikte enforcement"** - NO policy=None, NO opt-out, ALL operations enforced
2. ✅ **"Human in the loop kan bepalen om af te wijken"** - approve_deviation tool, audit trail
3. ✅ **"Initialisatie fase besloten worden welke fases"** - ProjectPhaseSelector, issue_type templates
4. ✅ **"Voor AL het werk"** - Enforcement applies to ALL operations (docs, code, bugs, features)

**Next Steps:**
1. Review and approve this plan
2. Start Phase 0.5 (ProjectPhaseSelector + phase templates)
3. Start Phase A (PolicyEngine + PhaseStateEngine with project plan validation)
4. TDD-first implementation (RED → GREEN → REFACTOR)
5. Deploy migration script (assign default phase plans to existing projects)
6. Train developers on human approval workflow

---

**END OF IMPLEMENTATION PLAN V2 (Strict Enforcement Edition)**

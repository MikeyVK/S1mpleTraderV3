<!-- D:\dev\SimpleTraderV3\docs\development\issue138\research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-14T08:00:00+00:00 updated=2026-02-14T16:55:00+00:00 -->
# Issue #138: git_add_or_commit Workflow Phases Research

**Status:** COMPLETE  
**Version:** 1.0  
**Last Updated:** 2026-02-14T16:55:00+00:00

---

## Purpose

Investigate why git_add_or_commit only accepts TDD phases and not workflow phases, preventing commits during non-TDD workflow phases

## Scope

**In Scope:**
Current phase systems (TDD vs workflow), validation logic in git_tools.py and git_config.py, configuration files (git.yaml, workflows.yaml, state.json), related issues (#117, #139) dependency analysis, architecture decision points for phase mapping

**Out of Scope:**
Implementation details, code changes, test design, PR strategy, UI/UX concerns, performance optimization, deployment procedures

## Prerequisites

Read these first:
1. Issue #138 created and triaged with priority:high, type:bug, scope:architecture labels
2. Branch fix/138-git-commit-workflow-phases created from main
3. Project initialized with bug workflow (6 phases: research → planning → design → tdd → integration → documentation)
4. Current phase: research

---

## Problem Statement

The git_add_or_commit tool rejects workflow phases (research, planning, integration, documentation, coordination) because GitCommitInput validation only checks tdd_phases from git.yaml. This forces agents to use inappropriate TDD phases during non-TDD workflow phases or violate protocol by using run_in_terminal.

## Research Goals

- Understand the distinction between TDD phases (commit-level) and workflow phases (branch state-level)
- Identify all workflow phases across 6 workflow types
- Analyze validation logic in GitCommitInput and GitConfig.has_phase()
- Map dependencies between issues #117, #138, and #139
- Identify architectural gaps in phase system integration
- Document decision points for phase mapping strategy
- Determine optimal configuration location for workflow-to-TDD phase mapping

## Related Documentation

- **Issue #117**: get_work_context only detects TDD phase, not full workflow phases
- **Issue #139**: get_project_plan does not return current_phase from state.json  
- **Issue #50**: Workflows configuration
- **Epic #49**: MCP Platform Configurability
- mcp_server/tools/git_tools.py lines 125-180: GitCommitInput validation
- mcp_server/config/git_config.py lines 100-150: GitConfig.has_phase() implementation

---

## Current State Analysis

### Two Parallel Phase Systems

The codebase currently maintains **two distinct phase systems** that operate independently:

**1. TDD Cycle Phases (Commit-level granularity)**
- **Source:** `.st3/git.yaml` → `tdd_phases` list
- **Purpose:** **Commit message prefixing** (Convention #2, #8)
- **Phases:** `red`, `green`, `refactor`, `docs`
- **Mapping:** Each phase maps to a commit prefix via `commit_prefix_map`
  - `red` → `test:` (failing test commits)
  - `green` → `feat:` (implementation commits)
  - `refactor` → `refactor:` (refactoring commits)
  - `docs` → `docs:` (documentation commits)

**2. Workflow Phases (Branch state-level granularity)**
- **Source:** `.st3/workflows.yaml` → 6 workflow definitions
- **Purpose:** **Branch state tracking** and workflow progression
- **Phases:** `research`, `planning`, `design`, `tdd`, `integration`, `documentation`, `coordination`
- **Tracking:** Current phase stored in `.st3/state.json` → `current_phase` field
- **Transitions:** Managed by `transition_phase` tool (enforces sequential progression)

### Architectural Gap

**No mapping exists between these two systems:**
- TDD phases are designed for the micro RED → GREEN → REFACTOR cycle within the `tdd` workflow phase
- Workflow phases represent macro project stages (research, planning, integration, etc.)
- **Problem:** Commits during workflow phases (e.g., `research`) have no clear TDD phase mapping

### Current Workaround (Anti-pattern)

Agents currently must:
1. During `research` phase → use `phase="docs"` (misleading)
2. During `planning` phase → use `phase="docs"` (misleading)
3. During `integration` phase → use `phase="green"` or `phase="refactor"` (inconsistent)
4. Or violate protocol: `run_in_terminal("git commit -m \"feat: ...\"")` (bypasses MCP tools)

---

## Configuration Inventory

### `.st3/git.yaml` (80 lines)

**Purpose:** Central configuration for git conventions (Conventions #1-#5)

**Relevant sections:**
```yaml
# Convention #1: Branch Types
branch_types:
  - feature
  - fix
  - refactor
  - docs
  - epic

# Convention #2: TDD Phases
tdd_phases:
  - red      # Write failing test
  - green    # Implement feature
  - refactor # Clean up code
  - docs     # Documentation updates

# Convention #3: Commit Prefix Mapping
commit_prefix_map:
  red: test
  green: feat
  refactor: refactor
  docs: docs

# Convention #4: Protected Branches
protected_branches:
  - main
  - master
  - develop
```

**Key characteristics:**
- **Granularity:** Commit-level (micro cycle)
- **Domain:** Git commit message formatting
- **Consumers:** `GitConfig.has_phase()`, `GitConfig.get_prefix()`, `GitCommitInput.validate_phase()`

### `.st3/workflows.yaml` (100+ lines)

**Purpose:** Define workflow phase sequences for different issue types (Convention #6)

**Workflow inventory:**

| Workflow | Phases | Description |
|----------|--------|-------------|
| **feature** | research → planning → design → tdd → integration → documentation | New functionality (6 phases) |
| **bug** | research → planning → design → tdd → integration → documentation | Bug fixes (6 phases) |
| **hotfix** | tdd → integration → documentation | Urgent fixes (3 phases) |
| **refactor** | research → planning → tdd → integration → documentation | Code improvements (5 phases, no design) |
| **docs** | planning → documentation | Documentation work (2 phases) |
| **epic** | research → planning → design → coordination → documentation | Large initiatives (5 phases) |

**Phase usage matrix:**

| Phase | feature | bug | hotfix | refactor | docs | epic | Total Usage |
|-------|---------|-----|--------|----------|------|------|-------------|
| `research` | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | 4/6 workflows |
| `planning` | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | 5/6 workflows |
| `design` | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | 3/6 workflows |
| `tdd` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | 4/6 workflows |
| `integration` | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | 4/6 workflows |
| `documentation` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | 6/6 workflows |
| `coordination` | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | 1/6 workflows (epic-only) |

**Key characteristics:**
- **Granularity:** Branch state-level (macro stages)
- **Domain:** Project workflow and phase progression
- **Consumers:** `transition_phase`, `PhaseStateEngine`, `.st3/state.json`
- **Total unique phases:** 7

### `.st3/state.json` (dynamic)

**Purpose:** Track current branch workflow state

**Structure:**
```json
{
  "branch": "fix/138-git-commit-workflow-phases",
  "issue_number": 138,
  "workflow_name": "bug",
  "current_phase": "research",
  "transitions": [
    {
      "from_phase": null,
      "to_phase": "research",
      "timestamp": "2026-02-14T07:30:00+00:00",
      "forced": false
    }
  ]
}
```

**Key characteristics:**
- **Granularity:** Branch state-level (matches workflows.yaml)
- **Domain:** Current workflow state and phase history
- **Consumers:** `transition_phase`, `PhaseStateEngine`, (SHOULD: `get_work_context`, `get_project_plan`)

---

## Phase Systems Comparison

### Conceptual Model

```
┌─────────────────────────────────────────────────────────────┐
│ WORKFLOW PHASES (Branch State - Macro)                      │
├─────────────────────────────────────────────────────────────┤
│ research → planning → design → tdd → integration → docs     │
│                                  │                           │
│                                  ▼                           │
│              ┌──────────────────────────────────────┐       │
│              │ TDD CYCLE (Commit - Micro)       │       │
│              ├──────────────────────────────────────┤       │
│              │ RED → GREEN → REFACTOR → (docs)  │       │
│              └──────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

**Key insight:** The `tdd` workflow phase **contains** the RED/GREEN/REFACTOR cycle, but other workflow phases do NOT map to TDD phases.

### Granularity Comparison

| Aspect | TDD Phases | Workflow Phases |
|--------|------------|-----------------|
| **Scope** | Single commit | Branch lifecycle |
| **Duration** | Minutes (< 1 hour) | Hours to days |
| **Purpose** | Commit message prefix | State tracking |
| **Quantity per branch** | 10-100+ commits | 3-6 phases |
| **Example** | "test: add validator" | "In tdd phase" |
| **Configured in** | `.st3/git.yaml` | `.st3/workflows.yaml` |
| **Tracked in** | Git commit history | `.st3/state.json` |

### Current Integration Points

**Where TDD phases are used:**
1. ✅ `git_add_or_commit` → Validates phase, generates commit prefix
2. ✅ `GitManager.commit_tdd_phase()` → Creates commit with prefix
3. ✅ `get_work_context` → Detects TDD phase from last commit prefix (Issue #117)

**Where workflow phases are used:**
1. ✅ `transition_phase` → Updates `.st3/state.json` `current_phase`
2. ✅ `PhaseStateEngine` → Validates phase transitions
3. ❌ `get_work_context` → SHOULD read from state.json, currently doesn't (Issue #117)
4. ❌ `get_project_plan` → SHOULD return current_phase, currently doesn't (Issue #139)
5. ❌ `git_add_or_commit` → SHOULD accept workflow phases, currently doesn't (Issue #138)

---

## Validation Logic Analysis

### GitCommitInput Phase Validation

**Location:** [mcp_server/tools/git_tools.py](mcp_server/tools/git_tools.py#L139-L148)

```python
class GitCommitInput(BaseModel):
    """Input for git_add_or_commit tool."""
    
    phase: str = Field(
        ...,
        description="TDD phase (red=test, green=feat, refactor, docs)"
    )
    
    @field_validator("phase")
    @classmethod
    def validate_phase(cls, value: str) -> str:
        """Validate phase against GitConfig (Convention #8)."""
        git_config = GitConfig.from_file()
        if not git_config.has_phase(value):  # ← ONLY checks tdd_phases
            valid_phases = ", ".join(git_config.tdd_phases)
            raise ValueError(
                f"Invalid phase '{value}'. "
                f"Valid phases from git.yaml: {valid_phases}"
            )
        return value
```

**Problems:**
1. **Field description misleading:** Says "TDD phase" but agent.md says use "workflow phases"
2. **Hardcoded assumption:** Only TDD phases are valid for commits
3. **No context awareness:** Doesn't check current workflow phase from state.json
4. **Restrictive validation:** Rejects 3 of 7 workflow phases outright

### GitConfig.has_phase() Implementation

**Location:** [mcp_server/config/git_config.py](mcp_server/config/git_config.py#L130)

```python
def has_phase(self, phase: str) -> bool:
    """Check if phase is valid TDD phase (Convention #2)."""
    return phase in self.tdd_phases  # ← ONLY checks self.tdd_phases
```

**Problems:**
1. **Single source truth:** Only aware of git.yaml tdd_phases
2. **No workflow awareness:** Doesn't read workflows.yaml or state.json
3. **No mapping logic:** Can't translate workflow phase → TDD phase

### GitCommitTool.execute() Behavior

**Location:** [mcp_server/tools/git_tools.py](mcp_server/tools/git_tools.py#L160-L178)

```python
async def execute(self, params: GitCommitInput) -> ToolResult:
    """Execute git add and commit."""
    try:
        # Phase already validated by GitCommitInput.validate_phase()
        
        if params.phase == "docs":
            # Special case: docs commits
            result = await anyio.to_thread.run_sync(
                self.manager.commit_docs,
                params.message,
                params.files
            )
        else:
            # All other TDD phases (red, green, refactor)
            result = await anyio.to_thread.run_sync(
                self.manager.commit_tdd_phase,
                params.phase,
                params.message,
                params.files
            )
```

**Observation:** Code treats `docs` as special case vs other TDD phases, suggesting early awareness that "docs" != "documentation" workflow phase.

---

## Related Issues Analysis

### Issue #117: get_work_context only detects TDD phase

**Problem:** 
- Tool detects TDD phase from commit message prefixes (`test:`, `feat:`, etc.)
- Ignores `.st3/state.json` `current_phase` field (authoritative workflow state)
- Agent sees "TDD Phase: 📝 docs" when state.json says `current_phase: "planning"`

**Root Cause:**
- `_detect_tdd_phase()` function only examines commit history
- No integration with `PhaseStateEngine` or state.json reading

**Shared Architecture Gap:**
Same problem as Issue #138 - tools are TDD-phase-only, no workflow phase awareness

### Issue #139: get_project_plan doesn't return current_phase

**Problem:**
- `get_project_plan` returns workflow definition from `.st3/projects.json`
- But OMITS `current_phase` from `.st3/state.json`
- Agent must manually read state.json to know "where are we?"

**Root Cause:**
- `GetProjectPlanTool` only calls `ProjectManager.get_project_plan()`
- `ProjectManager` reads projects.json, NOT state.json
- `PhaseStateEngine.get_current_phase()` exists but isn't called

### Dependency Graph

```
┌────────────────────────────────────────────────────────────────┐
│ ROOT CAUSE: Two Phase Systems Without Mapping Layer           │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  TDD Phases (git.yaml)          Workflow Phases (workflows.yaml)│
│  ↓ commit-level                 ↓ branch-level               │
│  │                               │                             │
│  ├─ Issue #138 ─────────────────┼─ git_add_or_commit rejects │
│  │  (validation)                 │   workflow phases          │
│  │                               │                             │
│  ├─ Issue #117 ─────────────────┼─ get_work_context reads    │
│  │  (detection)                  │   commits, not state.json  │
│  │                               │                             │
│  └───────────────────────────────┼─────────────────────────── │
│                                  │                             │
│                                  ├─ Issue #139                │
│                                  │  (state integration)        │
│                                  │  get_project_plan omits     │
│                                  │  current_phase from state   │
└────────────────────────────────────────────────────────────────┘
```

**Classification:**

| Issue | Category | Root Cause |
|-------|----------|------------|
| **#138** | Phase Mapping | TDD-only validation, no workflow phase support |
| **#117** | Phase Detection + State Integration | Commit parsing instead of state.json reading |
| **#139** | State Integration | projects.json without state.json merge |

**Shared Infrastructure Needs:**
1. **Phase Resolution Layer:** Workflow phase → TDD phase mapping
2. **State Integration Pattern:** Tools must read `.st3/state.json` for current_phase
3. **Configuration Unification:** GitConfig + WorkflowConfig should be aware of each other

**Fix Priority:**
- **#138 (HIGH):** Blocks workflow usage immediately (validation error)
- **#117 (MEDIUM):** Causes confusion but has workaround
- **#139 (MEDIUM):** Requires manual state.json read, but not blocking

---

## Architecture Decision Points

### Decision 1: Where Should Workflow → TDD Phase Mapping Live?

**Option A: Add to `.st3/git.yaml`**
```yaml
# git.yaml
workflow_phase_map:
  research: docs
  planning: docs
  design: docs
  tdd: null  # Use granular TDD phases (red/green/refactor)
  integration: green
  documentation: docs
  coordination: docs
```

**Pros:**
- Single source of truth for commit-related configuration
- GitConfig already loaded by git_add_or_commit
- Mapping is commit-domain concern

**Cons:**
- Mixes commit-level concerns (TDD phases) with workflow-level concerns
- Violates separation: git.yaml = git conventions, workflows.yaml = project workflows
- Requires GitConfig to be aware of workflow phases

---

**Option B: Add to `.st3/workflows.yaml`**
```yaml
# workflows.yaml
phase_commit_mapping:
  research: docs
  planning: docs
  design: docs
  tdd: granular  # Special: use red/green/refactor
  integration: green
  documentation: docs
  coordination: docs
```

**Pros:**
- Workflow domain stays in workflows.yaml
- Clear separation: workflows.yaml defines phases, also defines their commit behavior
- Workflow authors control commit strategy

**Cons:**
- GitCommitInput must now load WorkflowConfig (cross-domain dependency)
- Mapping is really about commits, not workflow logic

---

**Option C: Hybrid - GitCommitInput Smart Resolution**

GitCommitInput accepts BOTH TDD and workflow phases:
1. If phase in tdd_phases (red/green/refactor/docs) → use directly
2. If phase in workflow phases → map to TDD phase
3. Mapping logic: hardcoded in GitCommitInput or PhaseManager

```python
# Pseudo-code
WORKFLOW_TO_TDD_MAP = {
    "research": "docs",
    "planning": "docs",
    "design": "docs",
    "integration": "green",
    "documentation": "docs",
    "coordination": "docs",
    # "tdd" → require granular phases
}

if phase in ["red", "green", "refactor", "docs"]:
    tdd_phase = phase
elif phase in WORKFLOW_TO_TDD_MAP:
    tdd_phase = WORKFLOW_TO_TDD_MAP[phase]
elif phase == "tdd":
    raise ValueError("During 'tdd' phase, use: red, green, or refactor")
else:
    raise ValueError(f"Unknown phase: {phase}")
```

**Pros:**
- Backward compatible (TDD phases still work)
- No configuration changes needed initially
- Agents can use intuitive workflow phase names
- Simple mapping: most workflow phases → "docs"

**Cons:**
- Hardcoded mapping (less flexible)
- If workflow phases change, code must change
- No per-workflow customization (e.g., epic coordination might want "chore:" prefix)

---

**RECOMMENDATION: Option C (Hybrid) for MVP, Option B (workflows.yaml) for v2**

**Rationale:**
- **Quick win:** Issue #138 can be fixed TODAY with hardcoded mapping in GitCommitInput
- **Pragmatic:** 90% of workflow phases logically map to "docs" prefix
- **Future-proof:** Add configuration to workflows.yaml later if custom mappings needed
- **Agent-friendly:** Agents can now use natural language: `git_add_or_commit(phase="research", ...)`

### Decision 2: Should TDD Phase "docs" Be Renamed?

**Current Situation:**
- TDD phase: `docs` (4 characters, lowercase)
- Workflow phase: `documentation` (13 characters, lowercase)
- Conflict: `git_add_or_commit(phase="docs", ...)` is ambiguous

**Option A: Keep status quo**
- Accept that `docs` (TDD) != `documentation` (workflow)
- Hybrid validation: accept BOTH
- Let context determine meaning

**Option B: Rename TDD phase `docs` → `doc`**
- Change git.yaml: `tdd_phases: [red, green, refactor, doc]`
- Update commit_prefix_map: `doc: docs`
- Disambiguate: `doc` (TDD phase for small doc changes), `documentation` (workflow phase)

**RECOMMENDATION: Option A (status quo)**
- Renaming breaks existing branches/commits
- "docs" is conventional in commit prefixes (docs:, test:, feat:)
- Context (TDD vs workflow) is clear from usage

### Decision 3: Should state.json Integration Be Automatic?

**Current:** Tools like `get_work_context` and `get_project_plan` DON'T read state.json

**Proposal:** 
- **ALWAYS** read state.json when branch-specific information is needed
- Tools report BOTH workflow phase (state.json) AND last commit type (git history)

**Example get_work_context output:**
```
Current Branch: fix/138-git-commit-workflow-phases
Workflow Phase: 📋 research
Last Commit: docs: Add configuration analysis (3 minutes ago)
```

**RECOMMENDATION: Yes - state.json should be primary source for "current phase"**
- Fixes Issue #117 and #139 simultaneously
- Aligns with "state.json is authoritative" principle
- Tools must gracefully handle missing state.json (fallback to commit detection)

---

## Key Findings

### 1. Two Phase Systems Coexist Without Integration

**Finding:** TDD phases (commit-level) and workflow phases (branch-level) operate independently with no mapping layer.

**Evidence:**
- `.st3/git.yaml` defines 4 TDD phases: red, green, refactor, docs
- `.st3/workflows.yaml` defines 7 workflow phases across 6 workflow types
- No configuration file maps workflow phases → TDD phases
- GitCommitInput validation ONLY checks git.yaml tdd_phases

**Impact:** 
- Agents cannot use natural workflow phase names in `git_add_or_commit`
- Forces workaround: use "docs" during research/planning (misleading)
- Workflow phases tracked in state.json, but not usable for commits

### 2. Conceptual Model: Nested vs Parallel Phases

**Finding:** The `tdd` workflow phase **contains** the RED/GREEN/REFACTOR cycle, but other workflow phases do NOT nest TDD phases.

**Evidence:**
```
Workflow: research → planning → design → [TDD cycle: red→green→refactor] → integration → docs
                                          ↑ Only here do TDD phases apply naturally
```

**Implications:**
- **During `tdd` phase:** Use granular TDD phases (red/green/refactor) - agent.md Section 2.3
- **During other phases:** Need coarser commit type - typically "docs" for planning/research, "feat/test" for integration

**Architecture Decision:** 
- Workflow phases are NOT a superset of TDD phases
- They represent different granularity levels that occasionally overlap (tdd phase)

### 3. Majority of Workflow Phases Map to "docs" Commit Prefix

**Finding:** 5 of 7 workflow phases logically map to `docs:` commit prefix.

**Analysis:**

| Workflow Phase | Typical Commits | Logical TDD Phase | Commit Prefix |
|----------------|-----------------|-------------------|---------------|
| `research` | Research notes, analysis, questions | `docs` | `docs:` |
| `planning` | Planning documents, task breakdown | `docs` | `docs:` |
| `design` | Design documents, architecture | `docs` | `docs:` |
| `tdd` | Tests + implementation | red/green/refactor | varies |
| `integration` | Integration tests, wiring code | `green` | `feat:` |
| `documentation` | Reference docs, README | `docs` | `docs:` |
| `coordination` | Epic management, issue tracking | `docs` | `docs:` |

**Implication:** 
- Simple hardcoded mapping covers 5/7 phases: → docs
- `tdd` phase: require granular (red/green/refactor)
- `integration` phase: → green (or could be test for integration tests)

**Quick Win:** Hybrid validation accepting workflow phases with this mapping solves 80% of Issue #138

### 4. Issue #117, #138, #139 Share Root Cause: Missing State Integration

**Finding:** All three issues stem from tools not reading `.st3/state.json` for authoritative phase state.

**Shared Pattern:**

| Issue | Tool | What It Reads | What It SHOULD Read |
|-------|------|---------------|---------------------|
| #138 | `git_add_or_commit` | git.yaml (tdd_phases only) | ✅ git.yaml + workflows.yaml |
| #117 | `get_work_context` | Git commit history | ✅ state.json (current_phase) then commit history |
| #139 | `get_project_plan` | projects.json only | ✅ projects.json + state.json (current_phase) |

**Architectural Principle Violation:**
- **Stated:** `.st3/state.json` is authoritative source for current workflow state
- **Reality:** Tools ignore it, rely on indirect signals (commit prefixes, etc.)

**Unified Fix:**
1. Tools must integrate `PhaseStateEngine` to read state.json
2. Workflow phase is PRIMARY, commit type is SECONDARY
3. Agents see consistent phase information across all tools

### 5. Validation is Too Restrictive, Not Future-Proof

**Finding:** GitCommitInput hardcodes validation to ONLY git.yaml tdd_phases, blocking extensibility.

**Evidence:**
```python
# git_tools.py:141
if not git_config.has_phase(value):  # ← Closed for extension
    raise ValueError(...)
```

**Problems:**
- Adding workflow phase support requires code change (not just config)
- No "phase resolution strategy" - just binary check
- Field description says "TDD phase" but should accept workflow phases per agent.md

**Better Architecture:**
```python
# Proposed
def resolve_phase(user_input: str, current_workflow_phase: str | None) -> tuple[str, str]:
    """
    Resolve user input to (tdd_phase, commit_prefix).
    
    Args:
        user_input: Phase from agent (could be TDD or workflow phase)
        current_workflow_phase: From state.json (or None if not available)
    
    Returns:
        (tdd_phase for commit, commit_prefix for message)
    """
    if user_input in TDD_PHASES:
        return (user_input, get_prefix(user_input))
    elif user_input in WORKFLOW_PHASES:
        mapped_tdd = WORKFLOW_TO_TDD_MAP[user_input]
        return (mapped_tdd, get_prefix(mapped_tdd))
    else:
        raise ValueError(...)
```

**Benefit:** Extensible, testable, separates concerns (validation vs resolution)

### 6. Commit Prefixes vs State Tracking Serve Different Purposes

**Finding:** Commit message prefixes (Conventional Commits) optimize for git history readability, NOT workflow state tracking.

**Purpose Comparison:**

| Aspect | Commit Prefixes (TDD) | Workflow Phases (State) |
|--------|----------------------|-------------------------|
| **Audience** | Humans reading `git log` | Agents orchestrating work |
| **Granularity** | Per-commit (seconds) | Per-phase (hours/days) |
| **Changeability** | Immutable (git history) | Mutable (state transitions) |
| **Convention** | Conventional Commits spec | Project-specific workflows |
| **Validation** | Prefix syntax rules | Sequential phase progression |

**Insight:** 
- **git.yaml (commit prefixes):** Optimizes for "what happened in this commit?"
- **workflows.yaml (phases):** Optimizes for "what stage is this branch in?"
- These are COMPLEMENTARY, not redundant

**Implication:** 
- Don't try to unify them into one system
- Instead: create **mapping/translation layer** between them
- Tools like `git_add_or_commit` should accept EITHER and translate as needed

### 7. "docs" TDD Phase Overloaded

**Finding:** The `docs` TDD phase serves triple duty: (1) TDD cycle docs, (2) fallback for all workflow phases, (3) documentation workflow phase.

**Current Usage:**
```yaml
# git.yaml
tdd_phases: [red, green, refactor, docs]  # <- TDD cycle docs

# workflows.yaml
documentation:  # <- Workflow phase (confusingly similar name)
```

**Confusion Matrix:**

| Context | User Says | Tool Interprets | Actual Meaning |
|---------|-----------|-----------------|----------------|
| TDD cycle | `phase="docs"` | ✅ TDD phase | Small doc change during dev |
| Research phase | `phase="research"` | ❌ Invalid phase | Should map to "docs" TDD phase |
| Documentation phase | `phase="documentation"` | ❌ Invalid phase | Should map to "docs" TDD phase |
| Workaround | `phase="docs"` | ✅ TDD phase | Actually in "research" workflow phase |

**Problem:** 
- Agents confused about when to use "docs" vs "documentation"
- Issue #108 session: User explicitly noted this confusion
- "docs" becomes catch-all for "not test/feat/refactor"

**Recommendation:** 
- Keep naming as-is (changing would break history)
- But DOCUMENT clearly: 
  - `docs` (TDD phase) = commit prefix for documentation changes
  - `documentation` (workflow phase) = branch state for docs work
  - During `research`/`planning`/`design`/`documentation` workflow phases → use workflow phase name, tool maps to "docs" TDD phase

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-14T16:55:00+00:00 | Agent | Complete research analysis with all sections |

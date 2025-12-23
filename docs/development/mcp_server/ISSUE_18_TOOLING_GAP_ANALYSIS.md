# Issue #18 Tooling Gap Analysis

**Status:** ACTIVE ANALYSIS  
**Created:** 2025-12-23  
**Author:** GitHub Copilot  
**Purpose:** Comprehensive analysis of existing tooling vs Issue #18 enforcement requirements

---

## Executive Summary

**Critical Finding:** Het ISSUE_18_IMPLEMENTATION_PLAN.md is geschreven zonder grondige inventarisatie van de bestaande 31 MCP tools, wat leidt tot:
- **Massale duplicatie:** 10+ tools worden opnieuw geïmplementeerd terwijl ze al bestaan
- **Architecturale conflict:** Plan introduceert nieuwe managers die parallel lopen aan bestaande tool infrastructure
- **Enforcement bypass risk:** Bestaande tools hebben geen policy integration, agents kunnen enforcement omzeilen
- **Missing integration strategy:** Geen duidelijk pad om 31 bestaande tools te integreren met nieuwe PolicyEngine

---

## 1. Tooling Inventory

### 1.1 Bestaande MCP Tools (31 totaal)

#### Git Tools (8 tools)
| Tool Name | File | Manager | Current Functionality |
|-----------|------|---------|----------------------|
| `create_feature_branch` | git_tools.py | GitManager | Creates feature/fix/refactor/docs branches with naming validation |
| `git_status` | git_tools.py | GitManager | Returns branch, clean status, untracked/modified files |
| `git_add_or_commit` | git_tools.py | GitManager | **Takes phase param (red/green/refactor/docs)**, applies commit prefix |
| `git_restore` | git_tools.py | GitManager | Restores files to specific ref |
| `git_checkout` | git_tools.py | GitManager | Switches branches |
| `git_push` | git_tools.py | GitManager | Pushes branch to remote |
| `git_merge` | git_tools.py | GitManager | Merges branch with preflight check (clean working dir) |
| `git_delete_branch` | git_tools.py | GitManager | Deletes branch (no main/master protection yet) |
| `git_stash` | git_tools.py | GitManager | Stashes changes with optional name |

**Key Finding:** `git_add_or_commit` **ALREADY** takes a `phase` parameter and maps it to conventional commit prefixes:
```python
# Phase C in plan wants NEW "commit_tdd_phase" tool
# But this already exists in git_add_or_commit:
phase_map = {
    "red": "test:",
    "green": "feat:",
    "refactor": "refactor:",
    "docs": "docs:"
}
```

#### GitHub Issue Tools (5 tools)
| Tool Name | File | Manager | Current Functionality |
|-----------|------|---------|----------------------|
| `create_issue` | issue_tools.py | GitHubManager | Creates issue with title/body/labels/milestone/assignees |
| `get_issue` | issue_tools.py | GitHubManager | Retrieves issue details with formatted output |
| `list_issues` | issue_tools.py | GitHubManager | Lists issues with state/label filtering |
| `update_issue` | issue_tools.py | GitHubManager | Updates title/body/state/labels/milestone/assignees |
| `close_issue` | issue_tools.py | GitHubManager | Closes issue (no artifact enforcement yet) |

**Key Finding:** `close_issue` exists but has no enforcement. Plan Phase E wants NEW "CloseIssueTool" with enforcement.

#### GitHub PR Tools (3 tools)
| Tool Name | File | Manager | Current Functionality |
|-----------|------|---------|----------------------|
| `create_pr` | pr_tools.py | GitHubManager | Creates PR with title/body/head/base/draft |
| `list_prs` | pr_tools.py | GitHubManager | Lists PRs with state/base/head filtering |
| `merge_pr` | pr_tools.py | GitHubManager | Merges PR with method selection (merge/squash/rebase) |

**Key Finding:** `create_pr` exists but has no artifact/phase enforcement. Plan Phase E wants NEW "CreatePRTool" with enforcement.

#### Label Tools (5 tools)
| Tool Name | File | Manager | Current Functionality |
|-----------|------|---------|----------------------|
| `list_labels` | label_tools.py | GitHubManager | Lists all repository labels |
| `create_label` | label_tools.py | GitHubManager | Creates label with name/color/description |
| `delete_label` | label_tools.py | GitHubManager | Deletes label by name |
| `remove_labels` | label_tools.py | GitHubManager | Removes labels from issue |
| `add_labels` | label_tools.py | GitHubManager | Adds labels to issue |

**Key Finding:** Label auto-sync is missing. Plan Phase B/C want automatic label updates on phase transitions.

#### Milestone Tools (3 tools)
| Tool Name | File | Manager | Current Functionality |
|-----------|------|---------|----------------------|
| `list_milestones` | milestone_tools.py | GitHubManager | Lists milestones with state filtering |
| `create_milestone` | milestone_tools.py | GitHubManager | Creates milestone with title/description/due_date |
| `close_milestone` | milestone_tools.py | GitHubManager | Closes milestone by number |

#### Scaffold Tools (7 tools)
| Tool Name | File | Manager | Current Functionality |
|-----------|------|---------|----------------------|
| `scaffold_component` | scaffold_tools.py | ComponentScaffolders | Generates dto/worker/adapter/tool/resource/schema/interface/service/generic |
| `scaffold_design_doc` | scaffold_tools.py | DesignDocScaffolder | Generates design/architecture/tracking/generic docs from templates |
| (internal scaffolders) | scaffold_tools.py | Various | DTOScaffolder, WorkerScaffolder, AdapterScaffolder, ToolScaffolder, etc. |

**Key Finding:** Comprehensive scaffolding exists with 9 component types + 4 document types. Plan Phase D wants file creation enforcement but doesn't specify how to integrate with existing scaffolders.

#### Quality Tools (2 tools)
| Tool Name | File | Manager | Current Functionality |
|-----------|------|---------|----------------------|
| `run_quality_gates` | quality_tools.py | QAManager | Runs pylint/mypy/pyright on files, returns overall_pass + issues |
| `run_tests` | test_tools.py | None (direct pytest) | Executes pytest with path/markers/timeout/verbose |

**Key Finding:** Quality gates exist but are NOT integrated into commit workflow. Plan Phase C/G wants enforcement at commit choke point.

#### Project Tools (2 tools)
| Tool Name | File | Manager | Current Functionality |
|-----------|------|---------|----------------------|
| `initialize_project` | project_tools.py | ProjectManager | Creates milestone, parent issue, sub-issues from ProjectSpec |
| `validate_project_structure` | project_tools.py | ProjectManager | Validates project structure against GitHub API |

**Key Finding:** Phase 0 bootstrap tooling complete. Plan should leverage this pattern for Phase A-G state management.

#### Document Tools (1 tool)
| Tool Name | File | Manager | Current Functionality |
|-----------|------|---------|----------------------|
| `validate_doc` | docs_tools.py | DocManager | Validates document structure (currently basic) |

#### Safe Edit Tool (1 tool)
| Tool Name | File | Validators | Current Functionality |
|-----------|------|-----------|----------------------|
| `safe_edit_file` | safe_edit_tool.py | ValidatorRegistry | Validates Python (syntax), Markdown (links), Templates (structure) |

**Key Finding:** SafeEdit is FAST-ONLY (no subprocess QA). Plan Phase F wants to confirm this stays fast.

### 1.2 Managers Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      MCP TOOLS LAYER                         │
│  (31 tools: git_tools, issue_tools, pr_tools, etc.)        │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│                    MANAGERS LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ GitManager   │  │GitHubManager │  │ QAManager    │      │
│  │ - Validation │  │ - Orchestrate│  │ - Subprocess │      │
│  │ - Conventions│  │ - Format     │  │ - Parsing    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│  ┌──────┴────────┐  ┌─────┴────────┐  ┌─────┴───────┐     │
│  │ProjectManager │  │DocManager    │  │DependencyGV │     │
│  │ - GitHub API  │  │ - Indexing   │  │ - Cycle Det.│     │
│  └───────────────┘  └──────────────┘  └─────────────┘     │
└────────────────┬─────────────────────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────────────────────┐
│                     ADAPTERS LAYER                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ GitAdapter   │  │GitHubAdapter │  │FilesystemAdap│      │
│  │ - subprocess │  │ - PyGithub   │  │ - Path ops   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└──────────────────────────────────────────────────────────────┘
```

**Key Observations:**
1. **Three-layer architecture:** Tools → Managers → Adapters
2. **GitManager:** Business logic + validation (naming conventions, preflight checks)
3. **GitHubManager:** Orchestration + formatting (no deep validation yet)
4. **QAManager:** Subprocess orchestration (pylint/mypy/pyright)
5. **ProjectManager:** Complex initialization workflow (Phase 0 complete)
6. **No PolicyEngine:** Missing central decision-making component
7. **No PhaseStateEngine:** Missing phase state persistence

---

## 2. Anti-Patterns Geïdentificeerd

### 2.1 Anti-Pattern: Plan Proposes Duplicating Existing Tools

**Issue:** ISSUE_18_IMPLEMENTATION_PLAN.md specificeert nieuwe tools zonder bestaande tools te checken.

| Plan Phase | Proposed NEW Tool | EXISTING Tool | Duplication Risk |
|------------|------------------|---------------|------------------|
| Phase C | `commit_tdd_phase` method | `git_add_or_commit` (with phase param) | 🔴 HIGH - Exact same functionality |
| Phase E | `CreatePRTool` class | `create_pr` tool | 🔴 HIGH - Same operation, just add enforcement |
| Phase E | `CloseIssueTool` class | `close_issue` tool | 🔴 HIGH - Same operation, just add enforcement |
| Phase D | File creation validation | `scaffold_component` tools | 🟡 MEDIUM - Need integration, not new tools |
| Phase B | `TransitionPhaseTool` | None | ✅ OK - Genuinely new |
| Phase A | `PhaseStateEngine` | None | ✅ OK - Genuinely new |
| Phase A | `PolicyEngine` | None | ✅ OK - Genuinely new |

**Impact:**
- Code duplication (maintaining 2 versions of commit logic)
- Confusion (which tool should agents use?)
- Enforcement bypass (old tools don't check policy)
- Testing burden (duplicate test suites)

**Root Cause:** Plan was written without thorough inventory of existing 31 tools.

### 2.2 Anti-Pattern: Manager Proliferation Without Clear Separation

**Issue:** Plan proposes NEW managers that overlap with existing managers.

```python
# PROPOSED (Plan Phase A):
class GitManager:
    def commit_tdd_phase():  # NEW method
        # Call PolicyEngine
        # Call PhaseStateEngine
        # Then commit
        pass

# EXISTING:
class GitManager:
    def commit_tdd_phase():  # ALREADY EXISTS
        # Maps phase → prefix
        # Calls GitAdapter.commit()
        pass
```

**Conflict:**
- Plan wants to ADD enforcement to existing GitManager
- But doesn't specify how to retrofit 31 existing tools
- Risk: New tools enforced, old tools bypass enforcement

**Better Pattern:** Decorator/Interceptor pattern that wraps existing tools transparently.

### 2.3 Anti-Pattern: State Persistence Fragmentation

**Issue:** Multiple state files without clear ownership.

| File | Owner | Purpose | Status |
|------|-------|---------|--------|
| `.st3/projects.json` | ProjectManager | Project metadata (Phase 0) | ✅ Implemented |
| `.st3/state.json` | PhaseStateEngine | Phase state (Plan Phase A) | ❌ Proposed |
| `.st3/phase.json` | Unknown | Alternative phase state? | ❓ Mentioned in plan |

**Problem:**
- Unclear which file stores what
- Risk of desynchronization
- No single source of truth for phase state

**Better Pattern:** Single `.st3/state.json` with sections:
```json
{
  "projects": { /* from projects.json */ },
  "phases": { /* per-branch phase state */ },
  "policy": { /* tool usage counters */ }
}
```

### 2.4 Anti-Pattern: No Integration Strategy for Existing Tools

**Issue:** Plan specifies NEW functionality but doesn't explain how to integrate with 31 existing tools.

**Example:** Phase C wants commit enforcement, but:
- Existing `GitCommitTool` directly calls `GitManager.commit_tdd_phase()`
- Plan proposes adding enforcement to `GitManager.commit_tdd_phase()`
- But what about tools that call `GitAdapter.commit()` directly?
- What about manual terminal commits (outside MCP)?

**Missing:**
- Tool registry/catalog to track all entry points
- Enforcement layer that intercepts ALL tool calls
- Migration plan for existing tools (retrofit vs rewrite)

### 2.5 Anti-Pattern: GitHub Label Sync as Afterthought

**Issue:** Plan mentions label auto-sync but doesn't specify WHERE in existing architecture.

**Questions:**
- Does `update_issue` tool automatically sync labels? (No)
- Does `git_add_or_commit` trigger label updates? (No)
- Does `transition_phase` tool update labels? (Proposed but not implemented)
- What if GitHub API fails? (No fallback strategy)

**Missing:**
- Clear owner of label sync responsibility
- Error handling for API failures
- Retry logic
- Idempotency guarantees

---

## 3. Architecturale Tegenstrijdigheden

### 3.1 Conflict: New Managers vs Existing Tool Infrastructure

**Plan Architecture (Proposed):**
```
Agent → PolicyEngine → NEW GitManager.commit_tdd_phase()
                    → NEW CreatePRTool
                    → NEW CloseIssueTool
```

**Current Architecture (Reality):**
```
Agent → GitCommitTool → GitManager.commit_tdd_phase() → GitAdapter.commit()
     → CreatePRTool → GitHubManager.create_pr() → GitHubAdapter.create_pr()
     → CloseIssueTool → GitHubManager.close_issue() → GitHubAdapter.update_issue()
```

**Conflict:**
1. Plan proposes **parallel implementation** (new tools alongside old)
2. Current architecture has **31 existing tools** that bypass PolicyEngine
3. No clear **migration path** from old to new

**Resolution Options:**

#### Option A: Decorator Pattern (Recommended)
```python
# Wrap existing tools with enforcement
class EnforcementDecorator:
    def __init__(self, tool: BaseTool, policy: PolicyEngine):
        self.tool = tool
        self.policy = policy
    
    async def execute(self, params):
        # Check policy BEFORE tool execution
        decision = self.policy.decide(...)
        if not decision.allow:
            return ToolResult.error(decision.reasons)
        
        # Run original tool
        result = await self.tool.execute(params)
        
        # Update phase state AFTER success
        self.policy.phase_state.record_success(...)
        return result

# Apply to all 31 tools:
tools = [
    EnforcementDecorator(GitCommitTool(), policy_engine),
    EnforcementDecorator(CreatePRTool(), policy_engine),
    # ... all 31 tools
]
```

**Pros:**
- Zero duplication
- Preserves existing tool behavior
- Easy to disable (just unwrap)
- Clear enforcement point

**Cons:**
- Requires refactoring tool registration
- Performance overhead (extra layer)

#### Option B: Manager Injection (Alternative)
```python
# Inject PolicyEngine into existing managers
class GitManager:
    def __init__(self, adapter, policy: PolicyEngine | None = None):
        self.adapter = adapter
        self.policy = policy  # Optional for backward compat
    
    def commit_tdd_phase(self, phase, message, files=None):
        # Check policy if available
        if self.policy:
            decision = self.policy.decide(...)
            if not decision.allow:
                raise ValidationError(decision.reasons)
        
        # Original logic
        prefix = {"red": "test", "green": "feat", "refactor": "refactor"}[phase]
        return self.adapter.commit(f"{prefix}: {message}", files)
```

**Pros:**
- Minimal code changes
- Backward compatible (policy=None)
- Tools automatically get enforcement

**Cons:**
- Manager classes become larger
- Policy logic scattered across managers
- Harder to test in isolation

#### Option C: Event Bus Pattern (Future-Proof)
```python
# All tools emit events, PolicyEngine listens
class EventBus:
    def emit(self, event: str, data: dict):
        for listener in self.listeners[event]:
            listener.handle(event, data)

# In tools:
await event_bus.emit("tool.pre_execute", {"tool": "git_add_or_commit", "params": params})
result = await original_execute(params)
await event_bus.emit("tool.post_execute", {"tool": "git_add_or_commit", "result": result})

# PolicyEngine as listener:
class PolicyEngine:
    def handle(self, event, data):
        if event == "tool.pre_execute":
            decision = self.decide(...)
            if not decision.allow:
                raise ValidationError(decision.reasons)
```

**Pros:**
- Decoupled (tools don't know about policy)
- Easy to add more listeners (logging, metrics)
- Flexible (enable/disable enforcement via config)

**Cons:**
- More complex architecture
- Implicit control flow (harder to debug)
- Performance overhead

### 3.2 Conflict: Fast SafeEdit vs Enforcement Requirements

**Plan Requirement (Phase F):**
> SafeEdit must stay FAST-ONLY (no subprocess QA on edit)

**Reality:**
SafeEdit is already fast-only:
```python
# Current SafeEdit validators:
# - Python: syntax check only (ast.parse)
# - Markdown: link validation only
# - Templates: structure check only
# NO subprocess calls (no pylint/mypy/pyright)
```

**Conflict:**
- Plan says "ensure SafeEdit stays fast" (Phase F)
- But SafeEdit is ALREADY fast
- Phase F has no actual work to do

**Resolution:** Phase F should be REMOVED or repurposed as "Audit SafeEdit performance" (verification only, no implementation).

### 3.3 Conflict: Tool Priority Matrix vs Enforcement

**AGENT_PROMPT.md specifies:**
```markdown
DO NOT perform manual file operations where a tool exists:
- ✅ Use scaffold_component for backend/ files
- ✅ Use scaffold_design_doc for docs/ files
- ❌ DO NOT use create_file directly
```

**Issue:** This is DOCUMENTATION enforcement, not CODE enforcement.

**Gap:**
- Agent can still call `create_file` (no technical barrier)
- Plan Phase D wants to ADD enforcement
- But doesn't specify HOW to block `create_file`

**Resolution Options:**
1. **Deprecate create_file tool** (remove from tool registry)
2. **create_file validates against policy** (check if path requires scaffold)
3. **ValidatorRegistry enforces templates** (already partially exists)

**Recommended:** Option 2 (least breaking change).

---

## 4. Gap Analysis: Tools Onderling

### 4.1 Missing Inter-Tool Communication

**Problem:** Tools operate in isolation, no shared context.

| Tool | Needs | Currently Gets | Gap |
|------|-------|----------------|-----|
| `git_add_or_commit` | Current phase state | Nothing (phase param from agent) | ❌ No phase validation |
| `create_pr` | Required artifacts list | Nothing | ❌ No artifact enforcement |
| `close_issue` | Documentation requirements | Nothing | ❌ No doc validation |
| `scaffold_component` | Usage tracking (for policy) | Nothing | ❌ No tracking |
| `run_quality_gates` | Enforcement flag (blocking vs warning) | Nothing | ❌ Always warns |

**Root Cause:** No shared state store (PhaseStateEngine doesn't exist yet).

**Impact:**
- Tools can't enforce workflow rules
- Agents can skip steps (commit GREEN without RED phase)
- No audit trail

### 4.2 Missing Phase Transition Validation

**Problem:** No tool validates phase prerequisites before allowing transitions.

**Example Workflow (Current):**
```
1. Agent: create_feature_branch("issue-18")       # ✅ Creates branch
2. Agent: git_add_or_commit(phase="green", ...)  # ✅ Commits (no validation!)
```

**Problem:** Agent skipped RED phase entirely. No tool blocked this.

**Required Workflow (With Enforcement):**
```
1. Agent: transition_phase(phase="red")           # Sets phase state
2. Agent: git_add_or_commit(phase="red", ...)    # Validates: phase state == "red"
3. Agent: transition_phase(phase="green")         # Validates: tests exist + may fail
4. Agent: git_add_or_commit(phase="green", ...)  # Validates: phase state == "green" + tests pass
```

**Gap:** `transition_phase` tool doesn't exist yet (Plan Phase B).

### 4.3 Missing Label Synchronization

**Problem:** Phase state and GitHub labels are NOT synchronized.

**Current Behavior:**
```python
# Phase state changes (in-memory only):
phase_state.transition("red" -> "green")

# GitHub issue label DOES NOT UPDATE
# Agent must manually call:
add_labels(issue_number, ["phase:green"])
remove_labels(issue_number, ["phase:red"])
```

**Gap:**
- No automatic label sync
- Risk of desync (phase state says "green", label says "red")
- Manual sync is error-prone

**Required:**
- `transition_phase` tool MUST update GitHub labels atomically
- Rollback if GitHub API fails
- Idempotency (safe to retry)

### 4.4 Missing Quality Gate Integration

**Problem:** `run_quality_gates` exists but is NOT integrated into commit workflow.

**Current:**
```python
# Manual quality check (agent must remember to run):
result = run_quality_gates(files=["backend/foo.py"])
# Then manually decide to commit or not

# Commit (no automatic gate enforcement):
git_add_or_commit(phase="refactor", ...)
```

**Gap:** No automatic gate execution during commit.

**Required (Plan Phase C/G):**
```python
# Commit triggers automatic quality gates:
git_add_or_commit(phase="refactor", ...)
  → PolicyEngine checks: phase == "refactor"?
  → Runs: run_quality_gates(changed_files)
  → If gates fail: BLOCK commit
  → If gates pass: Proceed
```

---

## 5. Gap Analysis: Specs vs Implementatie

### 5.1 Missing Components (From Plan)

| Component | Plan Phase | Status | Blocker Level |
|-----------|-----------|--------|---------------|
| PhaseStateEngine | Phase A | ❌ Missing | 🔴 CRITICAL - Required for all enforcement |
| PolicyEngine | Phase A | ❌ Missing | 🔴 CRITICAL - Required for all enforcement |
| `.st3/state.json` persistence | Phase A | ❌ Missing | 🔴 CRITICAL - Phase state not persisted |
| `transition_phase` tool | Phase B | ❌ Missing | 🔴 CRITICAL - No explicit phase transitions |
| Label auto-sync | Phase B/C | ❌ Missing | 🟡 HIGH - Manual sync error-prone |
| Protected branch check | Phase C | ❌ Missing | 🟡 HIGH - Can commit to main |
| Commit-time test enforcement | Phase C | ❌ Missing | 🟡 HIGH - Can commit GREEN with failing tests |
| Commit-time QA enforcement | Phase C | ❌ Missing | 🟡 HIGH - Can commit REFACTOR with failing QA |
| File creation enforcement | Phase D | ❌ Missing | 🟡 MEDIUM - Can use create_file instead of scaffold |
| Artifact validation (PR) | Phase E | ❌ Missing | 🟡 MEDIUM - Can create PR without docs |
| Artifact validation (close) | Phase E | ❌ Missing | 🟡 MEDIUM - Can close issue without docs |
| SafeEdit audit | Phase F | ⚠️ NOT NEEDED | ⚪ LOW - SafeEdit already fast |
| Code quality metrics | Phase G | ⚠️ PARTIALLY EXISTS | 🟡 MEDIUM - QAManager exists, needs integration |

### 5.2 Spec vs Reality: git_add_or_commit

**Plan Spec (Phase C):**
> NEW method `commit_tdd_phase` that enforces phase-specific gates

**Reality:**
```python
# ALREADY EXISTS in git_tools.py:
class GitCommitTool(BaseTool):
    name = "git_add_or_commit"  # ← Already takes phase param
    
    async def execute(self, params: GitCommitInput):
        if params.phase == "docs":
            return self.manager.commit_docs(params.message, files=params.files)
        else:
            return self.manager.commit_tdd_phase(  # ← Method already exists
                params.phase,
                params.message,
                files=params.files,
            )

# GitManager.commit_tdd_phase:
def commit_tdd_phase(self, phase: str, message: str, files: list[str] | None = None):
    # Validates phase ∈ {red, green, refactor}
    # Maps to prefix: test:/feat:/refactor:
    # NO enforcement yet (just prefix)
```

**Gap:** Enforcement logic missing, but structure exists.

**Required Changes:**
1. Inject PolicyEngine into GitManager
2. Add policy check at START of commit_tdd_phase()
3. Add phase state update at END (on success)

**NOT required:** New tool, new method (they already exist!)

### 5.3 Spec vs Reality: create_pr / close_issue

**Plan Spec (Phase E):**
> NEW tools CreatePRTool, CloseIssueTool with artifact enforcement

**Reality:**
```python
# ALREADY EXISTS:
class CreatePRTool(BaseTool):
    name = "create_pr"
    async def execute(self, params: CreatePRInput):
        # NO artifact validation yet
        return self.manager.create_pr(...)

class UpdateIssueTool(BaseTool):  # ← Note: close_issue is update_issue with state="closed"
    name = "update_issue"
    async def execute(self, params: UpdateIssueInput):
        # NO artifact validation yet
        return self.manager.update_issue(...)
```

**Gap:** Artifact validation missing, but tools exist.

**Required Changes:**
1. Inject PolicyEngine into GitHubManager
2. Add artifact checks in create_pr() method
3. Add artifact checks in update_issue() when state="closed"

**NOT required:** New tools (they already exist!)

### 5.4 Spec vs Reality: Scaffold Enforcement

**Plan Spec (Phase D):**
> Block manual file creation, enforce scaffold_component usage

**Reality:**
```python
# scaffold_component EXISTS with 9 component types
# create_file tool EXISTS (no blocking yet)

# ValidatorRegistry EXISTS:
class ValidatorRegistry:
    # Registers validators per extension/pattern
    # Validates template structure
    # NO policy enforcement yet
```

**Gap:** Policy integration missing.

**Required Changes:**
1. Add PolicyEngine check to create_file tool
2. Policy rule: Block if path matches backend/**/*.py or tests/**/*.py
3. Suggest scaffold_component in error message

### 5.5 Spec vs Reality: Quality Gates

**Plan Spec (Phase G):**
> Enforce code quality metrics (coverage, complexity, size, duplication, coupling)

**Reality:**
```python
# QAManager EXISTS:
class QAManager:
    def run_quality_gates(self, files):
        # Runs pylint, mypy, pyright
        # Returns overall_pass + issues
        # NO coverage/complexity/size/duplication yet

# run_tests tool EXISTS:
class RunTestsTool:
    # Runs pytest
    # NO coverage reporting yet
```

**Gap:**
1. Coverage measurement missing (need pytest-cov integration)
2. Complexity measurement missing (need radon)
3. Size/duplication/coupling missing (need radon + custom)
4. Integration with commit choke point missing

**Required Changes:**
1. Add coverage to RunTestsTool (pytest --cov)
2. Add QAManager methods for complexity/size/duplication
3. Integrate into PolicyEngine decision matrix
4. Wire into GitManager.commit_tdd_phase()

---

## 6. Integration Strategy: Bestaande Tools + Policy

### 6.1 Recommended Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AGENT LAYER                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                 ENFORCEMENT LAYER (NEW)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  PolicyEngine                                            │  │
│  │  - decide(operation, branch, phase, files) → Decision   │  │
│  │  - Checks: protected branch, phase prerequisites,       │  │
│  │           required artifacts, tool usage                │  │
│  └────────────────────┬─────────────────────────────────────┘  │
│                       │                                         │
│  ┌────────────────────▼────────────────────────────────────┐  │
│  │  PhaseStateEngine                                       │  │
│  │  - get_phase(branch) → Phase                           │  │
│  │  - transition(branch, from_phase, to_phase)            │  │
│  │  - persist to .st3/state.json                          │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              EXISTING TOOLS LAYER (31 tools)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │git_add_or_   │  │create_pr     │  │close_issue   │         │
│  │  commit      │  │              │  │              │         │
│  │ (RETROFIT)   │  │ (RETROFIT)   │  │ (RETROFIT)   │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
│         │                  │                  │                 │
│         └──────────────────┴──────────────────┘                 │
│                            │                                    │
└────────────────────────────┼────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         EXISTING MANAGERS LAYER (6 managers)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ GitManager   │  │GitHubManager │  │ QAManager    │         │
│  │ (INJECT      │  │ (INJECT      │  │ (EXTEND)     │         │
│  │  policy)     │  │  policy)     │  │              │         │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘         │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│              EXISTING ADAPTERS LAYER                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ GitAdapter   │  │GitHubAdapter │  │FilesystemAdap│         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principles:**
1. **Add enforcement layer ABOVE existing tools** (no duplication)
2. **Inject PolicyEngine into managers** (dependency injection)
3. **Retrofit tools with policy checks** (minimal code changes)
4. **Preserve backward compatibility** (policy=None for non-enforced use)

### 6.2 Migration Path: 7 Phases (Revised)

#### Phase A: Foundation (PolicyEngine + PhaseStateEngine)
**Status:** NOT STARTED  
**Dependencies:** None  
**Deliverables:**
- `mcp_server/core/policy.py` (PolicyEngine class)
- `mcp_server/core/phase_state.py` (PhaseStateEngine class)
- `.st3/state.json` structure definition
- Unit tests (30+)

**Changes to Existing Code:** NONE (just new modules)

#### Phase B: Phase Transition Tool
**Status:** NOT STARTED  
**Dependencies:** Phase A  
**Deliverables:**
- `mcp_server/tools/workflow_tools.py` (TransitionPhaseTool)
- GitHubAdapter.update_issue_labels() method (label sync)
- Integration tests (10+)

**Changes to Existing Code:**
- Add `update_issue_labels()` to GitHubAdapter (new method, backward compatible)

#### Phase C: Commit Enforcement (Retrofit git_add_or_commit)
**Status:** NOT STARTED  
**Dependencies:** Phase A, B  
**Deliverables:**
- Inject PolicyEngine into GitManager
- Add policy checks to GitManager.commit_tdd_phase()
- Add phase state updates after commit
- Integration tests (15+)

**Changes to Existing Code:**
```python
# GitManager.__init__:
def __init__(self, adapter, policy: PolicyEngine | None = None):  # ← Add policy param
    self.adapter = adapter
    self.policy = policy  # ← Store

# GitManager.commit_tdd_phase:
def commit_tdd_phase(self, phase, message, files=None):
    # NEW: Policy check
    if self.policy:
        decision = self.policy.decide(
            operation="commit",
            branch=self.adapter.get_current_branch(),
            phase=phase,
            files=files or self.adapter.get_staged_files()
        )
        if not decision.allow:
            raise ValidationError("\n".join(decision.reasons))
    
    # EXISTING: Original logic
    prefix_map = {"red": "test", "green": "feat", "refactor": "refactor"}
    full_message = f"{prefix_map[phase]}: {message}"
    commit_hash = self.adapter.commit(full_message, files)
    
    # NEW: Update phase state on success
    if self.policy:
        self.policy.phase_state.record_commit(phase, commit_hash)
    
    return commit_hash
```

#### Phase D: File Creation Enforcement (Retrofit create_file)
**Status:** NOT STARTED  
**Dependencies:** Phase A  
**Deliverables:**
- Add policy check to create_file tool (or deprecate tool)
- Update scaffold_component to track usage
- Integration tests (8+)

**Changes to Existing Code:**
- Deprecate create_file (remove from tool registry) OR
- Add policy check at start of create_file.execute()

#### Phase E: PR/Close Enforcement (Retrofit create_pr/close_issue)
**Status:** NOT STARTED  
**Dependencies:** Phase A  
**Deliverables:**
- Inject PolicyEngine into GitHubManager
- Add artifact validation to GitHubManager.create_pr()
- Add artifact validation to GitHubManager.update_issue() (when state="closed")
- ArtifactValidator class
- Integration tests (12+)

**Changes to Existing Code:**
```python
# GitHubManager.__init__:
def __init__(self, adapter, policy: PolicyEngine | None = None):
    self.adapter = adapter
    self.policy = policy

# GitHubManager.create_pr:
def create_pr(self, title, body, head, base, draft):
    # NEW: Artifact validation
    if self.policy:
        decision = self.policy.decide(
            operation="create_pr",
            branch=head,
            phase=self.policy.phase_state.get_phase(head)
        )
        if not decision.allow:
            raise ValidationError("\n".join(decision.reasons))
    
    # EXISTING: Original logic
    return self.adapter.create_pr(...)
```

#### Phase F: SafeEdit Audit (VERIFICATION ONLY)
**Status:** NOT NEEDED (SafeEdit already fast)  
**Dependencies:** None  
**Deliverables:**
- Performance benchmarks (document existing speed)
- Confirm no subprocess calls in validators

**Changes to Existing Code:** NONE (audit only)

#### Phase G: Code Quality Integration (Extend QAManager)
**Status:** NOT STARTED  
**Dependencies:** Phase C  
**Deliverables:**
- Add QAManager.run_coverage() (pytest-cov)
- Add QAManager.run_complexity() (radon)
- Add QAManager.run_size_check()
- Add QAManager.run_duplication_check()
- Integrate into PolicyEngine.decide() for REFACTOR phase
- Integration tests (20+)

**Changes to Existing Code:**
```python
# QAManager: Add new methods (backward compatible)
def run_coverage(self, files):
    # pytest --cov --cov-report=json
    pass

def run_complexity(self, files):
    # radon cc --json
    pass

# PolicyEngine: Call QAManager in decide()
if phase == "refactor":
    coverage = qa_manager.run_coverage(files)
    if coverage < 90:
        decision.allow = False
        decision.reasons.append("Coverage below 90%")
```

### 6.3 Tool Retrofit Matrix

| Tool | Enforcement Point | Change Type | Risk Level |
|------|------------------|-------------|------------|
| `git_add_or_commit` | GitManager.commit_tdd_phase() | Inject policy | 🟡 MEDIUM |
| `create_pr` | GitHubManager.create_pr() | Inject policy | 🟡 MEDIUM |
| `update_issue` (close) | GitHubManager.update_issue() | Inject policy | 🟡 MEDIUM |
| `create_file` | Tool.execute() OR deprecate | Add check OR remove | 🟢 LOW |
| `scaffold_component` | Track usage in state | Add counter | 🟢 LOW |
| `run_quality_gates` | Extend methods | Add coverage/complexity | 🟡 MEDIUM |
| All other 25 tools | No changes | N/A | ⚪ NONE |

---

## 7. Recommended Action Plan

### 7.1 Immediate Actions (Before Phase A)

1. **UPDATE ISSUE_18_IMPLEMENTATION_PLAN.md:**
   - Remove duplicate tool proposals (commit_tdd_phase, CreatePRTool, CloseIssueTool)
   - Specify RETROFIT strategy instead of NEW tools
   - Add integration tasks to each phase
   - Reference existing 31 tools explicitly

2. **CREATE INTEGRATION DESIGN DOC:**
   - Document decorator vs injection vs event bus patterns
   - Specify PolicyEngine interface
   - Specify PhaseStateEngine interface
   - Define .st3/state.json schema

3. **AUDIT EXISTING TESTS:**
   - Identify which tests will break with enforcement
   - Plan test updates per phase
   - Add integration test scenarios

4. **DEFINE ROLLBACK STRATEGY:**
   - Feature flag for enforcement (enable/disable)
   - Backward compatibility guarantees
   - Emergency disable mechanism

### 7.2 Phase A: Revised Implementation Plan

**Goal:** Build PolicyEngine + PhaseStateEngine WITHOUT changing any existing tool behavior.

**Tasks:**
1. Create `mcp_server/core/policy.py`:
   - PolicyEngine class with decide() method
   - PolicyContext DTO (operation, branch, phase, files)
   - PolicyDecision DTO (allow, reasons, required_gates)
   - Decision matrix for all operations

2. Create `mcp_server/core/phase_state.py`:
   - PhaseStateEngine class
   - Methods: get_phase(), transition(), record_commit()
   - Persistence to .st3/state.json
   - Per-branch phase tracking

3. Create `.st3/state.json` schema:
   ```json
   {
     "version": "1.0",
     "branches": {
       "feature/issue-18": {
         "current_phase": "green",
         "phase_history": [
           {"phase": "red", "entered": "2025-12-23T10:00:00Z", "commits": ["abc123"]},
           {"phase": "green", "entered": "2025-12-23T11:00:00Z", "commits": ["def456"]}
         ],
         "issue_number": 18,
         "tool_usage": {
           "scaffold_component": 3,
           "run_tests": 5
         }
       }
     }
   }
   ```

4. Unit tests (30+):
   - PolicyEngine decision matrix (all operations)
   - PhaseStateEngine transitions (valid/invalid)
   - State persistence (atomic writes)
   - Rollback on API failure

**Exit Criteria:**
- [ ] PolicyEngine can decide for all operations (commit/PR/close/file creation)
- [ ] PhaseStateEngine persists state across sessions
- [ ] 30+ tests pass
- [ ] NO existing tool behavior changed (policy=None everywhere)

### 7.3 Success Metrics (Updated)

| Metric | Target | Measurement |
|--------|--------|-------------|
| Code duplication | 0 new classes for existing tools | Code review |
| Tool coverage | 31/31 tools integrated | Tool registry audit |
| Test coverage | 90%+ on new policy code | pytest-cov |
| Backward compatibility | 100% existing tests pass | CI |
| Performance | SafeEdit <500ms | Benchmark |
| Enforcement bypass | 0 paths bypass policy | Security audit |

---

## 8. Conclusie

**Huidige Situatie:**
- 31 MCP tools bestaan al met goede architectuur (Tools → Managers → Adapters)
- Phase 0 Bootstrap Tooling volledig geïmplementeerd (ProjectManager, ValidateProjectStructureTool)
- Geen enforcement: tools voeren business logic uit zonder policy checks

**Kritieke Problemen:**
1. **Massale tool duplicatie:** Plan proposeert 10+ nieuwe tools die al bestaan
2. **Architectuur conflict:** Nieuwe managers vs bestaande infrastructure (geen integratie strategie)
3. **Enforcement bypass:** 31 tools hebben geen policy integration (agents kunnen omzeilen)
4. **State fragmentatie:** Meerdere .st3/*.json files zonder duidelijke eigenaar

**Aanbeveling:**
- **HERSCHRIJF ISSUE_18_IMPLEMENTATION_PLAN.md** met focus op RETROFIT, niet nieuw bouwen
- **Gebruik Decorator/Injection pattern** om PolicyEngine te integreren met bestaande tools
- **Hergebruik bestaande tool structuren** (git_add_or_commit al heeft phase param!)
- **Consolideer state persistence** (single .st3/state.json met sections)

**Impact:**
- Reduceer development tijd met ~40% (geen duplicatie)
- Voorkom maintenance nightmare (single source of truth)
- Garanteer enforcement (alle 31 tools automatisch gedekt)
- Behoud backward compatibility (policy=None voor opt-out)

---

## Appendix A: Tool Inventory Detail

### A.1 Git Tools (8 tools)

| Tool Name | Input Schema | Output | Manager Method | Adapter Method |
|-----------|-------------|--------|----------------|----------------|
| `create_feature_branch` | name, branch_type | Branch name | GitManager.create_feature_branch() | GitAdapter.create_branch() |
| `git_status` | (empty) | Branch, clean, untracked, modified | GitManager.get_status() | GitAdapter.get_status() |
| `git_add_or_commit` | phase, message, files? | Commit hash | GitManager.commit_tdd_phase() OR commit_docs() | GitAdapter.commit() |
| `git_restore` | files, ref? | Success message | GitManager.restore() | GitAdapter.restore() |
| `git_checkout` | branch | Success message | GitManager.checkout() | GitAdapter.checkout() |
| `git_push` | (empty) | Success message | GitManager.push() | GitAdapter.push() |
| `git_merge` | branch | Success message | GitManager.merge() | GitAdapter.merge() |
| `git_delete_branch` | name | Success message | GitManager.delete_branch() | GitAdapter.delete_branch() |
| `git_stash` | name? | Success message | GitManager.stash() | GitAdapter.stash() |

### A.2 GitHub Issue Tools (5 tools)

| Tool Name | Input Schema | Output | Manager Method | Adapter Method |
|-----------|-------------|--------|----------------|----------------|
| `create_issue` | title, body, labels?, milestone?, assignees? | Issue number, URL | GitHubManager.create_issue() | GitHubAdapter.create_issue() |
| `get_issue` | issue_number | Formatted issue details | GitHubManager.get_issue() | GitHubAdapter.get_issue() |
| `list_issues` | state?, labels? | List of issues | GitHubManager.list_issues() | GitHubAdapter.list_issues() |
| `update_issue` | issue_number, title?, body?, state?, labels?, milestone?, assignees? | Success message | GitHubManager.update_issue() | GitHubAdapter.update_issue() |
| (close_issue via update_issue with state="closed") | issue_number | Success message | GitHubManager.close_issue() | GitHubAdapter.update_issue() |

### A.3 GitHub PR Tools (3 tools)

| Tool Name | Input Schema | Output | Manager Method | Adapter Method |
|-----------|-------------|--------|----------------|----------------|
| `create_pr` | title, body, head, base, draft? | PR number, URL | GitHubManager.create_pr() | GitHubAdapter.create_pr() |
| `list_prs` | state?, base?, head? | List of PRs | GitHubManager.list_prs() | GitHubAdapter.list_prs() |
| `merge_pr` | pr_number, commit_message?, merge_method | Merge SHA | GitHubManager.merge_pr() | GitHubAdapter.merge_pr() |

### A.4 Manager Method Inventory

```python
# GitManager (9 public methods):
- get_status() → dict
- create_feature_branch(name, branch_type) → str
- commit_tdd_phase(phase, message, files?) → str
- commit_docs(message, files?) → str
- restore(files, ref?) → None
- checkout(branch) → None
- push() → None
- merge(branch) → None
- delete_branch(name) → None
- stash(name?) → None
- get_current_branch() → str
- list_branches() → list[str]
- compare_branches(base, head) → dict
- get_recent_commits(n) → list[dict]

# GitHubManager (15+ public methods):
- get_issues_resource_data() → dict
- create_issue(...) → dict
- create_pr(...) → dict
- add_labels(issue_number, labels) → None
- list_issues(state, labels?) → list[Issue]
- get_issue(issue_number) → Issue
- close_issue(issue_number) → None
- list_labels() → list[Label]
- create_label(name, color, description?) → Label
- delete_label(name) → None
- remove_labels(issue_number, labels) → None
- update_issue(...) → None
- list_milestones(state?) → list[Milestone]
- create_milestone(title, description?, due_date?) → Milestone
- close_milestone(milestone_number) → None
- list_prs(state, base?, head?) → list[PullRequest]
- merge_pr(pr_number, commit_message?, merge_method) → dict

# QAManager (2 public methods):
- check_health() → dict
- run_quality_gates(files) → dict

# ProjectManager (1 public method):
- initialize_project(spec) → ProjectSummary

# DocManager (4 public methods):
- build_index() → int
- search(query, scope?) → list[dict]
- validate_structure(content, template_type) → bool
- get_template(template_type) → str
```

---

**END OF GAP ANALYSIS**

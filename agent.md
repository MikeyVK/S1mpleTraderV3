# S1mpleTrader V3 - Agent Cooperation Protocol

**Note:** This document is the full reference. For auto-loaded instructions in VS Code, see [.github/.copilot-instructions.md](.github/.copilot-instructions.md) which contains the critical subset of these rules.
**Status:** Active | **Type:** Bootloader | **Context:** High-Frequency Trading Platform

> **🛑 STOP & READ:** You are an autonomous developer agent. Your goal is precision and efficiency. **DO NOT ask the user for context we already have.** Follow this protocol to orient yourself and begin work.

---

## 🚀 Phase 1: Orientation Protocol

If you need the big-picture MCP server context (vision, architecture, roadmap), read:
- [docs/reference/mcp/mcp_vision_reference.md](docs/reference/mcp/mcp_vision_reference.md)

**Running this protocol allows you to "download" the current project state into your context.**

### 1.1 Tool Activation (Execute FIRST)

> **⚡ CRITICAL:** VS Code Copilot uses lazy loading for MCP tools. Tools appear "disabled" until activated.

**Activate all tool categories before proceeding:**

```
activate_file_editing_tools              → create_file, safe_edit_file, scaffold_artifact (unified tool for code+docs)
activate_git_workflow_management_tools   → 15 git/PR tools (create_branch, git_status, etc.)
activate_branch_phase_management_tools   → phase transition tools
activate_issue_management_tools          → 6 issue tools (create_issue, list_issues, etc.)
activate_label_management_tools          → 5 label tools
activate_milestone_and_pr_management_tools → milestone + PR list tools
activate_project_initialization_tools    → initialize_project, get_project_plan
activate_code_validation_tools           → 4 validation tools
```

**Why:** Tools are dynamically loaded by VS Code based on semantic name analysis. Without activation, they appear as "disabled by user" (misleading error message). This is a VS Code 1.108+ feature (Dec 2025), not part of MCP specification.

### 1.2 State Synchronization (Execute Immediately)

Don't guess the phase or status. **Query the system:**

1.  **Read Coding Standards:**
    *   `st3://rules/coding_standards` → *Loads TDD rules, Style, Quality Gates.*
    *   Also follow [docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md](docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md) for typing-issue resolution consistency (no global disables; targeted ignores only as last resort).
2.  **Check Development Phase:**
    *   `st3://status/phase` → *Tells you current_phase, active_branch, is_clean.*
3.  **Check Work Context:**
    *   `get_work_context` → *Retrieves active issue, blockers, and recent changes.*

---

## 🔄 Phase 2: Issue-First Development Workflow

**GOLDEN RULE:** Never commit directly to `main`. All work starts with an issue.

### 2.1 Starting New Work

**Workflow Sequence:**
```
1. create_issue          → Create GitHub issue (labels validated against .st3/labels.yaml)
2. create_branch         → Create feature/bug/docs/refactor/hotfix branch
3. git_checkout          → Switch to new branch  
4. initialize_project    → Set up workflow, phase state, parent tracking
5. get_project_plan      → Verify workflow phases loaded
```

**Workflow Types (from `.st3/workflows.yaml`):**

| **feature** | 6 phases: research → planning → design → tdd → integration → documentation | New functionality |
| **bug** | 6 phases: research → planning → design → tdd → integration → documentation | Bug fixes |
| **docs** | 2 phases: planning → documentation | Documentation work |
| **refactor** | 5 phases: research → planning → tdd → integration → documentation | Code improvements |
| **hotfix** | 3 phases: tdd → integration → documentation | Urgent fixes |
| **epic** | 5 phases: research → planning → design → tdd → integration | Large multi-issue initiatives |

**Epic Support:**
- Large issues use `type:epic` label
- Research phase identifies child issues
- Child issues reference parent epic (parent branch tracking)
- Epic hierarchy: `main → epic/76 → feature/77, feature/78`

### 2.2 Phase Progression

**Sequential Transitions (Strict Enforcement):**
```python
transition_phase(branch="feature/42-name", to_phase="design")
# Validates against workflow definition in .st3/workflows.yaml
# Must follow sequential order defined in workflow
```

**Forced Transitions (Requires Human Approval):**
```python
force_phase_transition(
    branch="feature/42-name",
    to_phase="ready",
    skip_reason="Skipping integration - already covered by epic tests",
    human_approval="User: John approved on 2026-01-09"
)
# Creates audit trail in .st3/state.json
# Only use when documented reason exists
```

### 2.3 TDD Cycle Within Phase

**RED → GREEN → REFACTOR Loop (Multiple cycles within `tdd` phase):**

1. **RED Phase:**
   - Write failing test
   - Commit: `git_add_or_commit(workflow_phase="tdd", sub_phase="red", message="add test for X")`
   - **Auto-detect:** `git_add_or_commit(message="add test for X")` (detects workflow_phase from state.json)
   - **Legacy:** `git_add_or_commit(phase="red", message="...")` (DEPRECATED but still works)

2. **GREEN Phase:**
   - Implement minimum code to pass
   - Commit: `git_add_or_commit(workflow_phase="tdd", sub_phase="green", message="implement X")`

3. **REFACTOR Phase:**
   - Clean up code
   - Run quality gates: `run_quality_gates(files=[...])`
   - Commit: `git_add_or_commit(workflow_phase="tdd", sub_phase="refactor", message="refactor X")`

4. **Test Execution:**
   - **During TDD:** `run_tests(path="tests/specific_test.py")` for targeted tests
   - **End of TDD phase:** `run_tests(path="tests/")` for full suite validation
   - **Note:** Full suite (1000+ tests) generates significant output - see Issue #103 for enhancements

5. **Phase Transition:**
   - After TDD cycles complete: `transition_phase(to_phase="integration")`

### 2.4 Documentation Phases

**Pre-Development Documentation (research/planning/design phases):**
- Output location: `docs/development/issueXX/` (XX = active issue number)
- Tool: `scaffold_artifact(artifact_type="design|architecture|tracking", name="...", context={...})`
  - Unified tool for ALL artifacts (code + docs)
  - Auto-resolves paths from artifacts.yaml registry

**Documentation Phase (after integration):**
- Focus: Reference docs, project documentation updates
- Tasks: Update issue content, generate PR description, finalize docs
- Quality gate: `validate_architecture(scope="all")`


## 🔧 Phase 5: Tool Priority Matrix (MANDATORY)

> **🛑 CRITICAL RULE:** Use ST3 MCP tools for ALL operations. NEVER use terminal/CLI or create_file where an MCP tool exists.

### Project Initialization & Planning
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|------------|
| Initialize project | `initialize_project(issue_number, workflow_name)` | Manual branch setup |
| Get workflow phases | `get_project_plan(issue_number)` | Read workflows.yaml manually |
| Detect parent branch | `get_parent_branch(branch)` | Manual git reflog parsing |

### Phase Management
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|------------|
| Sequential transition | `transition_phase(branch, to_phase)` | Manual state update |
| Forced transition | `force_phase_transition(branch, to_phase, skip_reason, human_approval)` | Skip validation |

### Git Operations
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|------------|
| Create branch | `create_branch(branch_type, name, base_branch)` | `run_in_terminal("git checkout -b")` |
| Switch branch | `git_checkout(branch)` | `run_in_terminal("git checkout")` |
| Check status | `git_status()` | `run_in_terminal("git status")` |
| Stage & Commit | `git_add_or_commit(message, workflow_phase?, sub_phase?, commit_type?)` | `run_in_terminal("git add/commit")` |
| List branches | `git_list_branches(verbose, remote)` | `run_in_terminal("git branch")` |
| Push to remote | `git_push(set_upstream)` | `run_in_terminal("git push")` |
| Pull from remote | `git_pull(rebase)` | `run_in_terminal("git pull")` |
| Fetch from remote | `git_fetch(remote, prune)` | `run_in_terminal("git fetch")` |
| Merge branches | `git_merge(branch)` | `run_in_terminal("git merge")` |
| Delete branch | `git_delete_branch(branch, force)` | `run_in_terminal("git branch -d")` |
| Stash changes | `git_stash(action, message, include_untracked)` | `run_in_terminal("git stash")` |
| Restore files | `git_restore(files, source)` | `run_in_terminal("git restore")` |
| Diff statistics | `git_diff_stat(source_branch, target_branch)` | `run_in_terminal("git diff --stat")` |

**Note on git_add_or_commit:**
- **New (Recommended):** `git_add_or_commit(message, workflow_phase?, sub_phase?, commit_type?)`  
  - Generates scoped commits: `test(P_TDD_SP_RED): message`
  - Auto-detects workflow_phase from state.json if omitted
  - Supports all workflow phases (research, planning, design, tdd, integration, documentation)
- **Legacy (DEPRECATED):** `git_add_or_commit(phase="red/green/refactor/docs", message)`  
  - Legacy format: `test: message` (no scope)
  - Backward compatible but will be removed in future version
  - Use workflow_phase instead

### GitHub Issues
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|------------|
| Create issue | `create_issue(title, body, labels, assignees, milestone)` | GitHub CLI / manual |
| List issues | `list_issues(state, labels)` | `run_in_terminal("gh issue list")` |
| Get issue details | `get_issue(issue_number)` | `run_in_terminal("gh issue view")` |
| Update issue | `update_issue(issue_number, title, body, state, labels)` | GitHub CLI / manual |
| Close issue | `close_issue(issue_number, comment)` | `run_in_terminal("gh issue close")` |

### GitHub Labels
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|------------|
| Create label | `create_label(name, color, description)` | GitHub CLI / manual |
| Delete label | `delete_label(name)` | GitHub CLI / manual |
| List labels | `list_labels()` | `run_in_terminal("gh label list")` |
| Add labels to issue/PR | `add_labels(issue_number, labels)` | GitHub CLI / manual |
| Remove labels | `remove_labels(issue_number, labels)` | GitHub CLI / manual |

### GitHub Milestones
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|------------|
| Create milestone | `create_milestone(title, description, due_on)` | GitHub CLI / manual |
| List milestones | `list_milestones(state)` | `run_in_terminal("gh milestone list")` |
| Close milestone | `close_milestone(milestone_number)` | GitHub CLI / manual |

### Pull Requests
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|------------|
| Create PR | `create_pr(title, body, head, base, draft)` | `run_in_terminal("gh pr create")` |
| List PRs | `list_prs(state, base, head)` | `run_in_terminal("gh pr list")` |
| Merge PR | `merge_pr(pr_number, commit_message, merge_method)` | `run_in_terminal("gh pr merge")` |

### Code Scaffolding (Jinja2 Templates)
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|------------|
| Any artifact (code or doc) | `scaffold_artifact(artifact_type="dto|worker|adapter|design|...", name="...", output_path="...", context={...})` | `create_file` with manual code |

**Common artifact types:**
- **Code:** dto, worker, adapter, interface, tool, resource, schema, service
- **Docs:** design, architecture, tracking, generic, research, planning

**Registry:** `.st3/artifacts.yaml` defines all artifact types and their templates.

**Template System (Issue #72 - Multi-Tier Architecture):**
- **5-tier Jinja2 hierarchy:** Tier 0 (universal SCAFFOLD) → Tier 1 (CODE/DOCUMENT/CONFIG format) → Tier 2 (Python/Markdown/YAML language) → Tier 3 (component/data/tool specialization) → Concrete (worker.py, research.md)
- **Inheritance-aware introspection:** `introspect_template(name, with_inheritance=True)` returns complete variable schema (all tiers)
- **SCAFFOLD metadata:** All scaffolded files include 1-line header: `# SCAFFOLD: {type}:{hash} | {timestamp} | {path}`
- **Template registry:** `.st3/template_registry.json` maps version hashes to tier chains
- **Validation integration:** All generated code passes Issue #52 validation (TEMPLATE_METADATA enforcement)

**Context Requirements:**
- **Code artifacts:** Variables from all tiers (concrete + Tier 3 + Tier 2 + Tier 1 + Tier 0)
- **Document artifacts:** Standard sections (purpose, scope, related_docs) + artifact-specific fields
- **Missing variables:** Scaffolding will fail with clear error listing required fields
- **System variables:** Auto-populated (timestamp, version_hash, output_path, artifact_type)

**Example:**
```python
# Worker scaffolding (Python CODE artifact)
scaffold_artifact(
    artifact_type="worker",
    name="ProcessWorker",
    context={
        # Tier 4 (concrete): worker-specific
        "worker_name": "ProcessWorker",
        "worker_description": "Processes incoming events",
        "input_type": "EventDTO",
        "output_type": "ResultDTO",
        
        # Tier 3 (component): lifecycle pattern (if IWorkerLifecycle validated)
        "config_type": "WorkerConfig",
        "uses_async": True,
        
        # Tier 2 (language): Python syntax (often inferred from tier 3)
        # Tier 1 (format): CODE structure (auto-provided by template)
        # Tier 0 (universal): SCAFFOLD metadata (auto-generated)
    }
)

# Research doc scaffolding (Markdown DOCUMENT artifact)
scaffold_artifact(
    artifact_type="research",
    name="multi-tier-templates",
    context={
        # Document-specific
        "title": "Issue #72 Multi-Tier Template Research",
        "purpose": "Investigate template hierarchy to eliminate DRY violations",
        "scope_in": "5-tier architecture, inheritance introspection, registry format",
        "scope_out": "Implementation details, performance optimization",
        "prerequisites": ["Research questions defined", "MVP validated"],
        "related_docs": ["planning.md", "design.md"],
        
        # Optional: Custom sections
        "sections": ["Background", "Alternatives", "Decision Rationale"],
    }
)
```

**Design Reference:** [docs/development/issue72/design.md](docs/development/issue72/design.md) - Complete 5-tier architecture specification

### Quality & Testing
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|------------|
| Run tests | `run_tests(path, markers, timeout, verbose)` | `run_in_terminal("pytest")` |
| Quality gates | `run_quality_gates(files)` | `run_in_terminal("ruff/mypy/pylint")` |
| Validate template | `validate_template(path, template_type)` | Manual validation |
| Validate architecture | `validate_architecture(scope)` | Manual review |

### Discovery & Context
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|------------|
| Get work context | `get_work_context(include_closed_recent)` | Manual file reading |
| Search docs | `search_documentation(query, scope)` | `grep_search` on docs/ |
| Health check | `health_check()` | N/A |

### MCP Server Management
| Action | ✅ USE THIS | ❌ NEVER USE | Notes |
|--------|-------------|------------|-------|
| Hot-reload server | `restart_server()` | Manual process kill | **Use after code changes to MCP tools/server. ⏳ WAIT 3 SECONDS after restart before calling next tool.** Zero client downtime. See [reference](docs/reference/mcp/proxy_restart.md) |

### File Editing
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|------------|
| Edit file (multi-mode) | `safe_edit_file(path, content/line_edits/insert_lines/search+replace, mode)` | Manual file editing |
| Create generic file | `create_file(path, content)` | VS Code create_file (deprecated) |

> **📌 Remember:** The ST3 MCP tools use Jinja2 templates that ensure consistency, correct imports, proper structure, and automatic test file generation. Manual file creation bypasses all these benefits.

---

## 🚫 run_in_terminal Restrictions (CRITICAL)

**`run_in_terminal` is ONLY allowed for:**

✅ **Permitted (rare cases):**
- Development servers where no MCP tool exists (e.g., `npm run dev`, `python -m http.server`)
- Build commands explicitly requested by user
- Smoke tests / exploratory commands approved by user
- Python package installations via pip (when not using install_python_packages tool)

❌ **FORBIDDEN (use MCP tool instead):**
- **File operations** → use `create_file` / `safe_edit_file`
- **Git operations** → use `git_*` tools (see matrix above)
- **Test execution** → use `run_tests` tool
- **File copy/move/delete** → use file editing tools or ask user
- **Quality gates** → use `run_quality_gates` tool
- **Python execution** → use appropriate MCP tool or ask user

**Default rule: If unsure, ask yourself "Is there an MCP tool for this?" If yes → use it. If no → ask user permission first.**

**This restriction prevents bypassing:**
- Template validation
- SCAFFOLD metadata tracking
- Quality gate enforcement
- Audit trail in MCP workflow
- Provenance tracking in template registry

**Common mistakes to avoid:**
```powershell
# ❌ WRONG
run_in_terminal("Set-Content file.py ...")
run_in_terminal("git add .")
run_in_terminal("pytest tests/")
run_in_terminal("Copy-Item source.py dest.py")

# ✅ CORRECT
create_file(path="file.py", content=...)
git_add_or_commit(phase="red", message="...")
run_tests(path="tests/")
# For copy: read original, create new with create_file
```

---

## 🏁 Ready State

**If you have run Phase 1: Orientation, you are now READY.**
*   "What is my next task?" → Check `get_work_context`.
*   "How do I build X?" → Check `st3://rules/coding_standards`.
*   "What phase am I in?" → Check `st3://status/phase`.
*   "Which tool should I use?" → **Consult Phase 5: Tool Priority Matrix.**
*   "How do I start work?" → **Follow Phase 2: Issue-First Development Workflow.**

> **Start now by running Phase 1.**
### 2.5 Work Completion

**PR Creation & Merge:**
```
1. create_pr(head="feature/42", base="main", title="...", body="...")
2. Wait for human approval (ALWAYS REQUIRED)
3. merge_pr(pr_number=X) - only after human approval
4. Branch cleanup - discuss with human (context-dependent)
   - State cleanup (.st3/state.json) is automatic on git_checkout
```

---

## 🛠️ Phase 3: Execution Protocols

**Use the specific protocol for your assigned task. DO NOT perform manual file operations where a tool exists.**

### A. "Implement a New Component" (DTO, Worker, Adapter)
1.  **Scaffold Code:**
    *   `scaffold_artifact(artifact_type="dto|worker|adapter", name="ComponentName", context={...})`
    *   Unified tool for generating code and documentation artifacts
    *   Auto-resolves paths from artifacts.yaml registry
    *   *Result:* Creates impl file with proper structure.
2.  **TDD Loop (Strict):**
    *   Follow Section 2.3 RED → GREEN → REFACTOR cycle
3.  **Phase Transition:**
    *   `transition_phase(to_phase="integration")` after TDD complete

### B. "Create Documentation" (Architecture, Design, Plan)
1.  **Scaffold Document:**
    *   `scaffold_artifact(artifact_type="design|architecture|tracking", name="document-name", context={...})`
    *   Same unified tool as code artifacts
    *   Auto-resolves docs/development/issueXX/ from artifacts.yaml
    *   *Result:* Creates perfectly structured markdown file.
2.  **Validate:**

### C. "Manage Labels & Milestones"
1.  **Create Label:**
    *   `create_label(name="type:feature", color="0e8a16", description="...")`
    *   Labels validated against `.st3/labels.yaml`
2.  **Detect Drift:**

---

## ⚠️ Phase 4: Critical Directives (The "Prime Directives")

1.  **Issue-First Development:** Never work directly on `main`. Always start with `create_issue`.
2.  **Workflow Enforcement:** Always `initialize_project` before work. Use `transition_phase` for progression.
3.  **TDD is Non-Negotiable:** If you write code without a test, you are violating protocol.
4.  **Tools > Manual:** Never manually create a file if `scaffold_*` exists. Never manually parse status if `st3://status/*` exists.
5.  **English Artifacts, Dutch Chat:**
    *   Write Code/Docs/Commits in **English**.
    *   Talk to the User in **Dutch** (Nederlands).
6.  **Human-in-the-Loop:** PR merge ALWAYS requires human approval. `force_phase_transition` requires approval + reason.
7.  **Quality Gates:** Run before phase transitions and before PR creation.

---
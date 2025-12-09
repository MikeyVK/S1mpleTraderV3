# S1mpleTrader V3 - Agent Cooperation Protocol

**Status:** Active | **Type:** Bootloader | **Context:** High-Frequency Trading Platform

> **🛑 STOP & READ:** You are an autonomous developer agent. Your goal is precision and efficiency. **DO NOT ask the user for context we already have.** Follow this protocol to orient yourself and begin work.

---

## 🚀 Phase 1: Orientation Protocol

**Running this protocol allows you to "download" the current project state into your context.**

### 1.1 State Synchronization (Execute Immediately)
Don't guess the phase or status. **Query the system:**

1.  **Read Coding Standards:**
    *   `read_resource("st3://rules/coding_standards")` -> *Loads TDD rules, Style, Quality Gates.*
2.  **Check Development Phase:**
    *   `read_resource("st3://status/phase")` -> *Tells you if we are Planning, Designing, or Implementing.*
3.  **Check Implementation Status:**
    *   `read_resource("st3://status/implementation")` -> *Shows what's done and what's failing.*
4.  **Check Work Context:**
    *   `call_tool("get_work_context")` -> *Retrieves active issue, blockers, and recent chages.*

---

## 🛠️ Phase 2: Execution Protocols

**Use the specific protocol for your assigned task. DO NOT perform manual file operations where a tool exists.**

### A. "Implement a New Component" (DTO, Worker, Adapter)
1.  **Scaffold Code:**
    *   `call_tool("scaffold_component", { "type": "...", "name": "..." })`
    *   *Result:* Creates impl file AND test file. Updates `__init__.py`.
2.  **TDD Loop (Strict):**
    *   `RED`: Run tests -> Fail.
    *   `GREEN`: Write code -> Pass.
    *   `REFACTOR`: Run Quality Gates.
3.  **Update Status:**
    *   `call_tool("update_implementation_status", { ... })` -> *Critical for project tracking.*

### B. "Create Documentation" (Architecture, Design, Plan)
1.  **Select Template:**
    *   Query `read_resource("st3://templates/list")` if unsure.
2.  **Scaffold Document:**
    *   `call_tool("scaffold_document", { "template": "design", "name": "..." })`
    *   *Result:* Creates perfectly structured markdown file.
3.  **Validate:**
    *   `call_tool("validate_document_structure", { "path": "..." })`

### C. "Manage Tasks" (Issues, Planning)
1.  **Create Issue:**
    *   `call_tool("create_issue", { "title": "...", "body": "..." })`
2.  **Start Work:**
    *   `call_tool("start_work_on_issue", { "issue_number": ... })` -> *Creates branch & updates board.*

---

## ⚠️ Phase 3: Critical Directives (The "Prime Directives")

1.  **TDD is Non-Negotiable:** If you write code without a test, you are violating protocol.
2.  **Tools > Manual:** Never manually create a file if `scaffold_*` exists. Never manually parse status if `st3://status/*` exists.
3.  **English Artifacts, Dutch Chat:**
    *   Write Code/Docs/Commits in **English**.
    *   Talk to the User in **Dutch** (Nederlands).
4.  **Objective Facts:** ContextWorkers produce data (Facts). Consumers interpret it (Opinions). Never mix them.
5.  **No "Loose" Files:** Every new file must be part of the module structure (`__init__.py` export) and documented.

---

## 🔧 Phase 4: Tool Priority Matrix (MANDATORY)

> **🛑 CRITICAL RULE:** Use ST3 MCP tools for ALL operations. NEVER use terminal/CLI or create_file where an MCP tool exists.

### Git Operations
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|--------------|
| Create branch | `mcp_st3-workflow_create_feature_branch` | `run_in_terminal("git checkout -b")` |
| Switch branch | `mcp_st3-workflow_git_checkout_branch` | `run_in_terminal("git checkout")` |
| Check status | `mcp_st3-workflow_git_status` | `run_in_terminal("git status")` |
| Stage & Commit | `mcp_st3-workflow_git_add_or_commit` | `run_in_terminal("git add/commit")` |
| Push to remote | `mcp_st3-workflow_git_push` | `run_in_terminal("git push")` |
| Merge branches | `mcp_st3-workflow_git_merge` | `run_in_terminal("git merge")` |
| Delete branch | `mcp_st3-workflow_git_delete_branch` | `run_in_terminal("git branch -d")` |
| Stash changes | `mcp_st3-workflow_git_stash` | `run_in_terminal("git stash")` |

### GitHub Issues
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|--------------|
| Create issue | `mcp_st3-workflow_create_issue` | GitHub CLI / manual |
| List issues | `mcp_st3-workflow_list_issues` | `run_in_terminal("gh issue list")` |
| Get issue details | `mcp_st3-workflow_get_issue` | `run_in_terminal("gh issue view")` |
| Close issue | `mcp_st3-workflow_close_issue` | `run_in_terminal("gh issue close")` |
| Add labels | `mcp_st3-workflow_add_labels` | GitHub CLI / manual |

### Pull Requests
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|--------------|
| Create PR | `mcp_st3-workflow_create_pr` | `run_in_terminal("gh pr create")` |

### Code Scaffolding (Jinja2 Templates)
| Component Type | ✅ USE THIS | ❌ NEVER USE |
|----------------|-------------|--------------|
| DTO | `mcp_st3-workflow_scaffold_component(type="dto")` | `create_file` with manual code |
| Worker | `mcp_st3-workflow_scaffold_component(type="worker")` | `create_file` with manual code |
| Adapter | `mcp_st3-workflow_scaffold_component(type="adapter")` | `create_file` with manual code |
| Interface | `mcp_st3-workflow_scaffold_component(type="interface")` | `create_file` with manual code |
| Tool | `mcp_st3-workflow_scaffold_component(type="tool")` | `create_file` with manual code |
| Resource | `mcp_st3-workflow_scaffold_component(type="resource")` | `create_file` with manual code |
| Schema | `mcp_st3-workflow_scaffold_component(type="schema")` | `create_file` with manual code |
| Service (Query) | `mcp_st3-workflow_scaffold_component(type="service_query")` | `create_file` with manual code |
| Service (Command) | `mcp_st3-workflow_scaffold_component(type="service_command")` | `create_file` with manual code |
| Service (Orchestrator) | `mcp_st3-workflow_scaffold_component(type="service_orchestrator")` | `create_file` with manual code |
| Generic Python file | `mcp_st3-workflow_scaffold_component(type="generic")` | `create_file` with manual code |

### Document Scaffolding (Jinja2 Templates)
| Document Type | ✅ USE THIS | ❌ NEVER USE |
|---------------|-------------|--------------|
| Architecture doc | `mcp_st3-workflow_scaffold_design_doc(template="architecture")` | `create_file` with markdown |
| Design doc | `mcp_st3-workflow_scaffold_design_doc(template="design")` | `create_file` with markdown |
| Reference doc | `mcp_st3-workflow_scaffold_design_doc(template="reference")` | `create_file` with markdown |
| Tracking doc | `mcp_st3-workflow_scaffold_design_doc(template="tracking")` | `create_file` with markdown |
| Generic doc | `mcp_st3-workflow_scaffold_design_doc(template="generic")` | `create_file` with markdown |

### Quality & Testing
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|--------------|
| Run tests | `mcp_st3-workflow_run_tests` | `run_in_terminal("pytest")` |
| Quality gates | `mcp_st3-workflow_run_quality_gates` | `run_in_terminal("ruff/mypy/pylint")` |
| Validate DTO | `mcp_st3-workflow_validate_dto` | Manual validation |
| Validate document | `mcp_st3-workflow_validate_document_structure` | Manual check |
| Validate architecture | `mcp_st3-workflow_validate_architecture` | Manual review |

### Discovery & Context
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|--------------|
| Get work context | `mcp_st3-workflow_get_work_context` | Manual file reading |
| Search docs | `mcp_st3-workflow_search_documentation` | `grep_search` on docs/ |
| Health check | `mcp_st3-workflow_health_check` | N/A |

### File Creation (Only when no scaffold exists)
| Action | ✅ USE THIS | ❌ NEVER USE |
|--------|-------------|--------------|
| Create generic file | `mcp_st3-workflow_create_file` | `create_file` (VS Code tool) |

> **📌 Remember:** The ST3 MCP tools use Jinja2 templates that ensure consistency, correct imports, proper structure, and automatic test file generation. Manual file creation bypasses all these benefits.

---

## 🏁 Ready State

**If you have run Phase 1: Orientation, you are now READY.**
*   "What is my next task?" -> Check `get_work_context`.
*   "How do I build X?" -> Check `st3://rules/coding_standards`.
*   "Where is the plan?" -> Check `st3://status/phase`.
*   "Which tool should I use?" -> **Consult Phase 4: Tool Priority Matrix.**

> **Start now by running Phase 1.**

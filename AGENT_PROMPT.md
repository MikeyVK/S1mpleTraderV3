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

## 🏁 Ready State

**If you have run Phase 1: Orientation, you are now READY.**
*   "What is my next task?" -> Check `get_work_context`.
*   "How do I build X?" -> Check `st3://rules/coding_standards`.
*   "Where is the plan?" -> Check `st3://status/phase`.

> **Start now by running Phase 1.**

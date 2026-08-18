<!-- docs/reference/copilot-agent-instructions-model.md -->
<!-- template=generic_doc version=43c84181 created=2026-05-17 updated=2026-05-24 -->
# Copilot Agent Instructions Model

**Status:** DEFINITIVE
**Version:** 1.2
**Last Updated:** 2026-05-24

---

## Purpose

This document explains in one place how the GitHub Copilot instruction files and the
`phase-gate-mcp` server cooperate to enforce workflow discipline in VS Code. It is intended
for developers, integrators, and any AI agent starting fresh on this project.

After reading this document you will understand:
- which instruction files exist and what each one does
- how VS Code decides what to inject into a chat session
- where the `phase-gate-mcp` server fits into that flow
- how `phase_instructions` and `sub_role_hint` from `get_work_context` override static
  instructions at runtime
- what the three-agent model looks like and why the tools are restricted the way they are

## Scope

**In Scope:**
- VS Code instruction primitive hierarchy and loading mechanics
- Project-specific file roles (`AGENTS.md`, `.agent.md` files)
- Three-agent model (`@co`, `@imp`, `@qa`) and tool restrictions
- `get_work_context` integration: `phase_instructions` and `sub_role_hint`
- Context loading order per session type
- Design decisions

**Out of Scope:**
- MCP tool API details \u2014 see [tools/README.md][tools-ref]
- Phase-gate enforcement internals (EnforcementRunner, contracts.yaml) \u2014 see [mcp_vision_reference.md][vision-ref]
- Git workflow mechanics — see [AGENTS.md][agents-md]

## Prerequisites

Read these first:
1. [mcp_vision_reference.md][vision-ref] \u2014 what the MCP server is and why it exists
2. [AGENTS.md][agents-md] \u2014 single always-on instruction file

---

## 1. VS Code Instruction Primitive Hierarchy

GitHub Copilot in VS Code supports several instruction primitives. They differ in when they
are loaded and what they are for.

| Primitive | File pattern | When loaded | Purpose |
|-----------|-------------|-------------|---------|
| **Agent instructions** | `AGENTS.md` or `copilot-instructions.md` | **Always** \u2014 every chat interaction | Workspace-wide standards |
| **Custom agent** | `.github/agents/*.agent.md` | On demand \u2014 when that `@agent` is invoked | Role-specific persona, tools, startup |
| **File instructions** | `.github/instructions/*.instructions.md` | When file matches `applyTo:` glob | File-type or folder-specific guidelines |
| **Prompts** | `.github/prompts/*.prompt.md` | On demand \u2014 when invoked as `/command` | Single focused task with parameters |

### 1.1 Agent Instructions (Always-On)

Microsoft documents two file choices \u2014 use exactly one:

| File | Location | VS Code precedence | Generation |
|------|----------|--------------------|-----------|
| `AGENTS.md` | repo root | **Higher** \u2014 checked first | New (VS Code 1.99, April 2025) |
| `copilot-instructions.md` | `.github/` | Lower \u2014 fallback | Legacy (GitHub.com origin) |

**This project uses `AGENTS.md` only.** See Section 2.

**Microsoft's design intent:** minimal, concise, actionable. Only what is relevant to every
interaction. Link to detailed docs rather than embedding them.

**Core principles (from Microsoft reference docs):**
1. Minimal by default \u2014 only what matters for *every* task
2. Concise and actionable \u2014 every line should guide behavior
3. Link, don't embed \u2014 reference docs instead of copying content
4. Keep current \u2014 update when practices change

### 1.2 Custom Agents (`.agent.md`)

An `.agent.md` file defines a named agent available in the VS Code agent picker (`@name`).
It is loaded **only** when that agent is explicitly invoked in a chat session.

Key frontmatter fields:
```yaml
description: "..."          # Discovery surface \u2014 how parent agents find this agent
tools: [...]                # Tool allowlist \u2014 enforced by VS Code at runtime
argument-hint: "..."        # Guidance shown to the user in the picker
handoffs: [...]             # Transitions to other agents
```

The `tools:` list is the primary enforcement mechanism. VS Code silently blocks any tool
call not in the list. This is how `@qa`'s read-only constraint is enforced \u2014 not by
text instruction, but by omitting mutation tools from the frontmatter.

---

## 2. This Project's Instruction File Architecture

This project uses **`AGENTS.md` as the single always-on instruction file**. This follows
Microsoft's "use only one" guidance and aligns with VS Code's loading order (`AGENTS.md`
takes precedence over `copilot-instructions.md`).

| File | Role | Content |
|------|------|---------|
| `AGENTS.md` (root) | **Always-on** \u2014 operational reference + coordination manifest | Tool priority matrix, TDD protocol, quality gates, architecture contract, three-agent model, sub-roles, hand-over formats |
| `.github/agents/co.agent.md` | **@co role** | Coordination and epic-lifecycle startup, `@co` sub-roles, and the narrow epic allowlist |
| `.github/agents/imp.agent.md` | **@imp role** | Implementation startup, scope lock, architecture contract, hand-over format |
| `.github/agents/qa.agent.md` | **@qa role** | Review startup, suppression audit, verification workflow, tool allowlist (read-only) |

> **Historical note:** `.github/copilot-instructions.md` was the original always-on file.
> Its content has been consolidated into `AGENTS.md`. The file no longer exists in the
> project.

### Why AGENTS.md over copilot-instructions.md?

`AGENTS.md` is the newer standard (VS Code 1.99, April 2025), designed for agentic
workflows. VS Code checks `AGENTS.md` before `copilot-instructions.md` in its loading
order. It is also the format referenced by the AI agent community. Having a single
always-on file eliminates drift risk and halves context token usage for the always-on
layer.

### What should NOT be in the always-on file

Per Microsoft's "minimal by default" principle, `AGENTS.md` must not contain:
- Detailed startup protocols for specific agent roles (belongs in `.agent.md`)
- Phase-specific workflow instructions (served dynamically by `get_work_context`)
- Duplicated content that lives in linked reference documents

---

## 3. The Three-Agent Model

### Agent Roles

| Agent | Invocation | Mission | File |
|-------|-----------|---------|------|
| `@co` | `@co <sub-role>: <task>` | Coordination authority and epic workflow owner \u2014 owned-branch epic execution or background coordination around child work | [co.agent.md][co-agent] |
| `@imp` | `@imp <sub-role>: <task>` | Implementation executor \u2014 code, tests, commits, phase and cycle transitions | [imp.agent.md][imp-agent] |
| `@qa` | `@qa <sub-role>: <task>` | QA authority \u2014 read-only review, test runs, verdicts | [qa.agent.md][qa-agent] |

### Sub-Roles

Each agent has sub-roles that bind to a phase of the workflow:

**`@co`:** coordination: `triager` (default), `backlog-reviewer`, `tracker`, `issue-author`; epic lifecycle: `epic-researcher`, `epic-planner`, `epic-designer`, `epic-coordinator`, `epic-documenter`, `epic-releaser`

**`@imp`:** `researcher` (default), `planner`, `designer`, `implementer`, `validator`, `documenter`

**`@qa`:** `design-reviewer` (default), `plan-verifier`, `verifier`, `validation-reviewer`, `doc-reviewer`

### Tool Restrictions by Agent

Tool restrictions are enforced by VS Code at the frontmatter level, not by text instruction.

| Capability | `@co` | `@imp` | `@qa` |
|------------|-------|--------|-------|
| Read files, search | \u2705 | \u2705 | \u2705 |
| Run tests | \u274c | \u2705 | \u2705 |
| Run quality gates | \u2705 on epic-owned branches | \u2705 | \u2705 |
| Edit files (`safe_edit_file`) | \u2705 epic docs/contracts/prompts only | \u2705 (via MCP) | \u274c |
| Git operations | \u2705 narrow epic-owned lifecycle ops | \u2705 (via MCP) | \u274c read-only |
| GitHub issue/label/milestone | \u2705 | \u2705 (via MCP) | \u274c read-only |
| Phase transitions | \u2705 on epic-owned branches | \u2705 (via MCP) | \u274c |
| PR submission / merge | \u2705 on epic-owned branches | \u2705 (via MCP) | \u274c |
| All `phase-gate-mcp/*` tools | \u274c (explicit allowlist) | \u2705 (wildcard) | \u274c (explicit allowlist) |

`@imp` uses `tools: ["phase-gate-mcp/*"]` \u2014 all MCP tools. `@co` and `@qa` use explicit
per-tool allowlists. `@co`'s allowlist intentionally includes the narrow mutation set
needed for epic-owned branches, while `@qa` remains hard read-only.

### Two-Chat Model

Use separate VS Code chat sessions for each role. This prevents role contamination:

```
User \u2192 @co triager: assess incoming issue \u2192 Co\u2192Imp hand-over
User \u2192 @co epic-designer: refine epic contract surfaces \u2192 QA findings route back to @co
User \u2192 @imp implementer: execute child issue cycle X \u2192 Imp\u2192QA hand-over
User \u2192 @qa verifier: review latest hand-over \u2192 GO/NOGO verdict
```

Never mix roles in one session. Fresh context prevents authority confusion and scope drift.
Epic-owned branch review and lifecycle continuation stay with `@co`; child technical work
still routes `@imp` \u2192 `@qa`.

---

## 4. Phase-Gate MCP Integration

### 4.1 `get_work_context` \u2014 the runtime context bridge

The `get_work_context` MCP tool is the bridge between the static instruction files and the
dynamic workflow state. It reads the active branch, branch-local `.pgmcp/state.json`,
and `.pgmcp/config/contracts.yaml`, then returns a formatted orientation response that

**Key fields returned or rendered:**

| Field | Type | Purpose |
|-------|------|---------|
| `current_branch` | string | Active git branch |
| `workflow_name` | string | Active workflow type (feature/bug/docs/refactor/hotfix/chore/epic) |
| `phase` | string | Active workflow phase from branch state |
| `issue_number` | integer | Bound issue number when available |
| `parent_branch` | string | Parent branch when available |
| `current_cycle` / `sub_phase` | integer / string | Active TDD cycle or sub-phase when applicable |
| `sub_role_hint` | string | Suggested sub-role for the active workflow-phase contract |
| `phase_instructions` | string | **Operational script for the current workflow-phase** |
| `handover_template` | string | Optional ready-to-use hand-over block from the active contract |

When branch state points to a known workflow but an invalid phase, `get_work_context`
remains non-error and renders a recovery warning before the `### \ud83c\udfaf Phase Instructions`
block instead of failing hard.

### 4.2 `phase_instructions` \u2014 dynamic operational script

`phase_instructions` is a multi-line string that contains the operational TODO list for the
GetWorkContextTool resolves the active workflow and
phase from branch state, then reads the matching instruction block from
`.pgmcp/config/contracts.yaml`.
**Example output for `(bug, implementation)` phase:**

```
[ ] Call get_project_plan to load TDD cycle deliverables
[ ] Identify the active TDD cycle from the planning document
[ ] Write the failing test (RED sub-phase) ...
[ ] Commit with sub_phase="red", cycle_number=N
...
[ ] Produce the Imp\u2192QA hand-over block
```

**Why this matters:** agents can execute phase-specific work without relying on stale static
prompt text. The contract lives in configuration, is returned at invocation time, and can
evolve without changing the `.agent.md` files.

### 4.3 `sub_role_hint` \u2014 sub-role guidance

`sub_role_hint` is config-driven and comes from the same workflow-phase contract entry as
`phase_instructions`.

| Workflow / phase | Example sub-role hint |
|------------------|-----------------------|
| `feature` / `implementation` | `implementer` |
| `feature` / `documentation` | `documenter` |
| `bug` / `research` | `researcher` |
| `epic` / `research` | `epic-researcher` |
| `epic` / `design` | `epic-designer` |
| `epic` / `coordination` | `epic-coordinator` |
| `epic` / `ready` | `epic-releaser` |

This ensures the agent declares the correct sub-role without guessing from the phase name.

### 4.4 How `@imp` uses these fields

The `imp.agent.md` precedence chain is:

```
1. Runtime-injected system instructions
2. phase_instructions from get_work_context  \u2190 overrides 3\u20135 when present
3. AGENTS.md
4. imp.agent.md (this file)
5. Latest user request
```

`phase_instructions` sits at precedence #2. When present, it is the authoritative
operational script for the session. The agent reads all lower-priority documents only
when `phase_instructions` is absent or explicitly directs it to do so.

---

## 5. Context Loading Order Per Session Type

### Default Copilot chat (no `@agent` invoked)

```
Always loaded:
  AGENTS.md                      \u2190 operational reference + coordination manifest
```

### `@co` session

```
Always loaded:
  AGENTS.md

On @co invocation:
  .github/agents/co.agent.md     \u2190 role persona, tool allowlist, sub-roles

Normal startup sequence (per co.agent.md):
  1. get_work_context
  2. Follow returned phase_instructions / sub_role_hint when present
  3. Use list_issues, get_issue, and the narrow @co allowlist only as required by the active coordination or epic-lifecycle task

Lifecycle-boundary exception:
  - /open-issue and /close-issue may run their scripted bootstrap / exit sequence before control returns to a normal get_work_context-first session
```

### `@imp` session

```
Always loaded:
  AGENTS.md

On @imp invocation:
  .github/agents/imp.agent.md    \u2190 role persona, full MCP tool access

Startup sequence (per imp.agent.md):
  Precondition: branch must be pre-initialized by @co
  └─ create_branch + git_checkout + initialize_project already done
  └─ if .pgmcp/state.json absent → stop and report; do NOT call initialize_project
  1. get_work_context
     └─ if phase_instructions present → follow it as operational script
     └─ if absent → read AGENTS.md, then proceed
  2. ARCHITECTURE_PRINCIPLES.md  ← always binding
  3. [conditional] get_project_plan
  4. Inspect worktree for existing changes
  5. Inspect latest QA verdict
```

### `@qa` session

```
Always loaded:
  AGENTS.md

On @qa invocation:
  .github/agents/qa.agent.md     ← role persona, read-only tool allowlist

Startup sequence (per qa.agent.md):
  1. AGENTS.md                        ← always read first
  2. ARCHITECTURE_PRINCIPLES.md
  3. get_work_context
  4. get_project_plan for active issue
  5. Read active planning document
  6. Read changed files in worktree
  7. Read latest implementation hand-over
```

---

## 6. Instruction File Interaction Map

```
                            \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
                            \u2502         VS Code Chat Session         \u2502
                            \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518
                                           \u2502 always injected
                                 \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u25bc\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
                                 \u2502     AGENTS.md       \u2502
                                 \u2502                     \u2502
                                 \u2502  \u2022 Tool matrix      \u2502
                                 \u2502  \u2022 TDD protocol     \u2502
                                 \u2502  \u2022 Quality gates    \u2502
                                 \u2502  \u2022 Architecture     \u2502
                                 \u2502  \u2022 3-agent model    \u2502
                                 \u2502  \u2022 Hand-overs       \u2502
                                 \u2502  \u2022 Sub-roles        \u2502
                                 \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518
                                           \u2502 when @agent invoked
                               \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u25bc\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
                               \u2502   *.agent.md           \u2502
                               \u2502  co / imp / qa         \u2502
                               \u2502                        \u2502
                               \u2502  \u2022 tools: [...]        \u2502
                               \u2502  \u2022 startup proto       \u2502
                               \u2502  \u2022 role boundary       \u2502
                               \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518
                                          \u2502 @imp calls
                                \u250c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u25bc\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2510
                                \u2502  get_work_context   \u2502
                                \u2502  (MCP tool)         \u2502
                                \u2502                     \u2502
                                \u2502  \u2192 sub_role_hint    \u2502
                                \u2502  \u2192 phase_instruc-   \u2502
                                \u2502    tions  [#2 prec] \u2502
                                \u2514\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2518
```

---

## 7. Operating Modes For Agent Use

The repo supports two practical operating variants for agents. This is a **configuration and prompt posture** distinction, not a schema-level mode switch. `contracts.yaml` still requires `instructions` in both variants — the difference is created by enforcement configuration and agent prompt pressure.

### Variant A — Orchestrated Workflow Mode

Use this mode when the branch should actively steer the agent through workflow state.

**Setup actions:**
1. Keep `check_context_loaded` enabled in `.pgmcp/config/enforcement.yaml` for `branch_mutating` tools.
2. Keep `.github/agents/*.agent.md` and lifecycle prompts explicit that `get_work_context()` is the required first in-phase read.
3. Keep phase `instructions` present and directive enough to drive session behavior.
4. Preserve lifecycle-boundary exceptions (issue #268 — open-issue and end-issue are explicit lifecycle boundaries that run before the normal `get_work_context`-first session).

**Usage pattern:**
1. Initialize the branch or transition through the correct lifecycle boundary.
2. Call `get_work_context()` at session start for in-phase work.
3. Follow the returned `sub_role_hint`, `phase_instructions`, and hand-over contract before branch-mutating actions.
4. Rely on enforcement to block writes until context is loaded.

This is the current default operating mode for this repository.

### Variant B — Gated Non-Enforced Workflow Mode

Use this mode when the repo should retain workflow guardrails without forcing agent orchestration.

**Setup actions:**
1. Disable `check_context_loaded` (e.g., `enabled: false` in `enforcement.yaml`) while retaining other policy gates (`check_branch_policy`, `check_pr_status`, `check_phase_readiness`) as desired.
2. Keep `instructions` present in `contracts.yaml` (schema requires it), but make them compact, informational, and non-prescriptive rather than imperative session scripts.
3. Rewrite `.github/agents/*.agent.md` and lifecycle prompts so `get_work_context()` is optional or situational, not a hard first step.
4. Treat `get_work_context()` as an operator aid for context lookup, not as a mandatory bootstrap barrier.

**Usage pattern:**
1. Work may start from the local task anchor without first calling `get_work_context()`.
2. Agents call `get_work_context()` only when workflow state, phase guidance, or hand-over context is actually needed.
3. Branch-mutating tools remain governed by the remaining enforcement rules, but not by context-loaded bootstrap gating.

> **Boundary note:** Treat this distinction as an operating method and configuration posture, not as proof that the current repo already has a first-class `without_orchestration` config switch. No such switch exists; switching modes requires manual changes to `enforcement.yaml` and agent instruction files.

### How `check_context_loaded` and `contracts.yaml` interact in these modes

| Component | Variant A (Orchestrated) | Variant B (Gated non-enforced) |
|-----------|--------------------------|--------------------------------|
| `check_context_loaded` in `enforcement.yaml` | Enabled for `branch_mutating` tools | Disabled |
| `instructions` in `contracts.yaml` | Directive, drives session | Present (schema required), but non-prescriptive |
| `get_work_context()` call | Mandatory first action | Optional |
| Agent prompt posture | `*.agent.md` enforces startup protocol | `*.agent.md` makes it situational |
| Enforcement blocks | Write-blocked until context loaded | Only `check_branch_policy`, `check_pr_status`, `check_phase_readiness` |

---

## 8. Design Decisions and Rationale

### Why AGENTS.md as the single always-on file?

`AGENTS.md` is newer than `copilot-instructions.md` and was designed specifically for
agentic VS Code workflows (introduced VS Code 1.99, April 2025). VS Code checks `AGENTS.md`
before `copilot-instructions.md` in its loading order, making it the natural primary.

Using a single always-on file:
- Eliminates the drift risk between two files that must stay synchronized
- Halves the context token cost for the always-on instruction layer
- Follows Microsoft's "use only one" guidance
- Makes the project's instruction architecture visible and understandable to a developer
  reading the repo root

The content previously in `copilot-instructions.md` (tool priority matrix, TDD protocol,
quality gates, architecture contract) has been merged into `AGENTS.md`. That file no
longer exists in the project.

### Why `phase_instructions` via MCP and not in the `.agent.md` file?

Three reasons:
1. **Dynamic**: phase instructions change as workflow contracts evolve without requiring
   agent-file changes. The active workflow-phase entry in `.pgmcp/config/contracts.yaml`
   is the source of truth.
2. **Per-workflow**: different workflows can attach different instructions and sub-role
   hints to the same phase name. A static file cannot express this cleanly without
   embedding contract logic.
3. **Precedence position**: by returning `phase_instructions` at runtime, the active agent
   can place them at precedence #2 (above all static files), making the loaded contract the
   highest-authority script for the session.

### Why is `@qa` read-only enforced at the tool level, not by text?

Text instructions can be overridden by an autonomous agent under task pressure.
Tool restrictions in `tools:` frontmatter are enforced by VS Code before the model runs.
An `@qa` session physically cannot call `safe_edit_file` or `git_add_or_commit` because
those tools are not in its allowlist. This is hard enforcement, not soft guidance.

### Why does `@imp` use `tools: ["phase-gate-mcp/*"]` (wildcard)?

`@imp` is the implementation executor. It needs the full MCP surface. Maintaining an
explicit per-tool allowlist would require updating the agent file every time a new MCP
tool is added. The wildcard future-proofs the agent. The `@imp` role boundary is enforced
by the `.agent.md` body instructions and by QA review \u2014 not by tool restriction.

---

## 9. Adding a New Workflow Phase

If a workflow gains a new phase, update the contract layer that `get_work_context` reads:

1. Add or adjust the workflow-phase entry in `.pgmcp/config/contracts.yaml`, including
   `sub_role`, `phase_instructions`, and any `handover_template` text.
2. If the change also alters global workflow metadata or role ownership semantics, align the
   corresponding reference docs and startup instructions.
3. Test with `get_work_context` on a branch in that workflow-phase to verify the rendered
   orientation header, instructions, sub-role hint, and hand-over template.

No `.agent.md` or `AGENTS.md` changes are required for ordinary phase-script updates unless
the new phase changes a global role boundary, ownership model, or lifecycle exception.

---

## Related Documentation

- **[tools/README.md][tools-ref]** \u2014 all 49 MCP tools with parameters and examples
- **[mcp_vision_reference.md][vision-ref]** \u2014 MCP server architecture and vision
- **[AGENTS.md][agents-md]** \u2014 single always-on instruction file
- **[.github/agents/imp.agent.md][imp-agent]** \u2014 implementation agent full spec
- **[.github/agents/qa.agent.md][qa-agent]** \u2014 QA agent full spec
- **[.github/agents/co.agent.md][co-agent]** \u2014 coordination agent full spec
- **[ARCHITECTURE_PRINCIPLES.md][arch-principles]** \u2014 binding architecture contract
- **[AGENTS.md][agents-md]** — branch and commit conventions

<!-- Link definitions -->
[tools-ref]: tools/README.md
[vision-ref]: mcp_vision_reference.md
[agents-md]: ../../../AGENTS.md
[imp-agent]: ../../../.github/agents/imp.agent.md
[qa-agent]: ../../../.github/agents/qa.agent.md
[co-agent]: ../../../.github/agents/co.agent.md
[arch-principles]: ../../coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.3 | 2026-07-20 | Agent | Fix stale reference/mcp/ path in header comment |
| 1.2 | 2026-05-24 | Agent | Update the three-agent model reference for `@co` epic ownership, config-driven `get_work_context`, and lifecycle-boundary startup exceptions |
| 1.1 | 2026-05-17 | Agent | Consolidation decision: single always-on file (AGENTS.md); remove copilot-instructions.md references; update diagram, precedence chain, loading order, rationale |
| 1.0 | 2026-05-17 | Agent | Initial document — covers instruction hierarchy, three-agent model, MCP integration, context loading order |

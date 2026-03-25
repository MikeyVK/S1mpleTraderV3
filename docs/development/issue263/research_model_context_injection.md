<!-- docs\development\issue263\research_model_context_injection.md -->
<!-- template=research version=8b7bb3ab created=2026-03-25T21:00Z updated=2026-03-25 -->
# Model Context Injection — Research

**Status:** FINAL  
**Version:** 2.0  
**Last Updated:** 2026-03-25

---

## Purpose

Document the exact behaviour of VS Code Copilot hook outputs with respect to what
actually enters the language model context versus what is merely displayed to the user.
This research was triggered by a live observation: a QA agent could not self-identify its
active sub-role without performing a file lookup, despite hooks running on every prompt.

## Scope

**In Scope:**
Official Microsoft VS Code hook documentation (March 2026), mapping of hook output fields
to model context versus UI display, SessionStart timing analysis, identification of the
architectural constraint that prevents reliable sub-role injection.

**Out of Scope:**
Implementation of a fix, design of alternative injection strategies, undocumented or
experimental hook behaviour that may work today but has no contract guarantee.

## Prerequisites

1. Microsoft VS Code Copilot documentation:
   - https://code.visualstudio.com/docs/copilot/customization/hooks
   - https://code.visualstudio.com/docs/copilot/customization/custom-agents
   - https://code.visualstudio.com/docs/copilot/customization/custom-instructions
2. Existing project research: `research.md` (Gap A identification), `research_sub_role_descriptions.md`
3. Source files: `detect_sub_role.py`, `notify_compaction.py`, `session_start.py`, `session_start_imp.py`

---

## Finding 1 — hookSpecificOutput.additionalContext is the ONLY documented model injection path

**Source:** https://code.visualstudio.com/docs/copilot/customization/hooks — "Hook-specific output format"

The Microsoft documentation defines two output categories for hooks:

| Output type | Field | Documented behaviour |
|---|---|---|
| **Common** | `systemMessage` | *"Warning message displayed to the user"* — UI only |
| **Hook-specific** | `additionalContext` | *"Context added to the agent's conversation"* — enters model |

Only a subset of hook events supports `hookSpecificOutput` with `additionalContext`:

| Hook event | Supports `additionalContext`? |
|---|---|
| `SessionStart` | **Yes** |
| `PreToolUse` | **Yes** |
| `PostToolUse` | **Yes** |
| `SubagentStart` | **Yes** |
| `UserPromptSubmit` | **No** — *"uses the common output format only"* |
| `PreCompact` | **No** — *"uses the common output format only"* |
| `Stop` | **No** — *"uses the common output format only"* |

**Conclusion:** `UserPromptSubmit` and `PreCompact` can only return `systemMessage`, which is
displayed as a warning to the user in the UI. It is **not** documented as entering the model's
conversation context.

---

## Finding 2 — Our UPS hook relies on undocumented behaviour

**File:** `src/copilot_orchestration/hooks/detect_sub_role.py`, function `build_ups_output()`

The current implementation returns:

```python
{
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "systemMessage": "\n\n".join(parts),   # sub-role description + crosschat block
    }
}
```

Per Finding 1, `UserPromptSubmit` only supports the common output format. The
`hookSpecificOutput` wrapper is not documented for this event. Whether VS Code silently
accepts this and injects the `systemMessage` into the model is **undocumented behaviour**.

The same issue applies to `notify_compaction.py` (PreCompact), which returns:

```python
{
    "systemMessage": "..."   # sub-role context re-injection after compaction
}
```

PreCompact also only supports common output. There is no documented path for this
`systemMessage` to enter the model context.

---

## Finding 3 — Exit code 2 stderr is the only documented UPS→model path

**Source:** https://code.visualstudio.com/docs/copilot/customization/hooks — "Common output format"

The documentation states that when a hook exits with code 2 (soft failure), *"stderr is
shown to the model as context."* This is the **only** documented mechanism by which a
`UserPromptSubmit` hook can inject content into the model conversation.

This is a fragile path: it conflates error reporting with context injection and is
semantically inappropriate for routine sub-role identity information.

---

## Finding 4 — SessionStart timing and the architectural dead-end

**Source:** https://code.visualstudio.com/docs/copilot/customization/hooks — "SessionStart"

### Timing

SessionStart fires *after* the user submits their first prompt (i.e., after pressing Enter
in a new chat). It does **not** fire when the chat panel is merely opened.

### Input schema

The documented `SessionStart` input contains:

```json
{
  "source": "new"   // or "history"
}
```

Critically, there is **no `prompt` field** in the SessionStart input. The user's first
prompt text is not available to this hook.

### The architectural tension

| Requirement | Event that satisfies it | Limitation |
|---|---|---|
| Inject context into the model | `SessionStart` (`additionalContext`) | Does **not** receive prompt text → cannot detect sub-role |
| Detect sub-role from prompt | `UserPromptSubmit` (`prompt` field) | **Cannot** inject model context (no `additionalContext`) |

This creates a fundamental dead-end within the official hook contract:

- The event that **can** inject model context (`SessionStart`) does not know the sub-role.
- The event that **knows** the sub-role (`UserPromptSubmit`) cannot officially inject model context.

This finding confirms the original "Gap A" identified in `research.md` (2026-03-17).

---

## Finding 5 — What DOES reliably enter the model

Based on the official documentation, the following content **does** reliably enter model
context at various lifecycle points:

### At new chat start

1. **Agent body text** (`.agent.md` Markdown body) — always present for `@imp` / `@qa` chats
2. **Custom instructions** (`.copilot-instructions.md`, `.instructions.md`) — loaded per `applyTo` rules
3. **Prompt files** (`.prompt.md`) when explicitly invoked
4. **`SessionStart` hook `additionalContext`** — our workspace and agent SessionStart hooks use this correctly (branch info, changed files, snapshot recovery)

### On every prompt

5. **User's prompt text** — the message itself
6. **Tool call results** — outputs from tool invocations
7. **`PreToolUse` / `PostToolUse` `additionalContext`** — if configured
8. **`SubagentStart` `additionalContext`** — if configured

### After compaction

9. **Compacted summary** — VS Code's built-in compaction summary
10. *No documented mechanism* for hooks to inject additional context post-compaction via `PreCompact`

---

## Finding 6 — Observed versus documented behaviour

During live testing, sub-role descriptions injected via `UserPromptSubmit.systemMessage`
**sometimes** appear to influence model behaviour. However:

- A QA agent transcript showed the agent **could not** reliably self-identify its sub-role
  —  it resorted to name-inference heuristics rather than stating exact sub-role knowledge.
- The `systemMessage` may be surfaced to the model in some VS Code builds as an
  implementation detail, but this is **not contractually guaranteed**.
- Any reliance on this behaviour is fragile and may break across VS Code updates.

---

## Summary of Architectural Constraint

```
┌─────────────────────┐     ┌─────────────────────────┐
│   SessionStart      │     │   UserPromptSubmit       │
│                     │     │                          │
│ ✅ additionalContext │     │ ✅ prompt text available  │
│    → enters model   │     │    → can detect sub-role │
│                     │     │                          │
│ ❌ no prompt text    │     │ ❌ no additionalContext   │
│    → can't detect   │     │    → can't inject model  │
│    sub-role         │     │    context               │
└─────────────────────┘     └─────────────────────────┘
```

The sub-role detection and model context injection capabilities are split across two
events with no officially documented bridge between them.

---

## Potential Officially-Conforming Alternatives (for future design)

These are noted for completeness — not evaluated or recommended here:

1. **PreToolUse/PostToolUse `additionalContext`** — fires on every tool call; could inject
   sub-role context read from the state file written by UPS.
2. **Richer static agent body text** — embed sub-role awareness directly in `.agent.md`.
3. **`.instructions.md` files** — create sub-role-specific instruction files.
4. **SubagentStart `additionalContext`** — inject sub-role context when spawning subagents.
5. **Exit code 2 stderr path** — semantically inappropriate but technically documented.

---

## Finding 7 — Stop hook `reason` empirically confirmed dead (2026-03-25)

**Method:** Live instrumentation — added `logger.debug("stop hook: reason sent to model=\n%s", reason)`
to `stop_handover_guard.py` and triggered a BLOCK response in a live session.

**Observed in `orchestration.log`:**
```
20:31:56 INFO  BLOCK stop: role='imp' sub_role='researcher'
20:31:56 DEBUG stop hook: reason sent to model=
  Write NOW.
  [researcher] End your response with this block: ...
```

**Observation:** The `reason` text was written to the hook output correctly. The agent
(`@imp`, sub-role `researcher`) did **not** produce a handover block. A new user prompt
arrived 49 seconds later, starting a new session — no handover block was ever generated.

**Conclusion:** The `Stop` hook `decision: block` + `reason` mechanism does not cause the
model to produce additional output before the session ends. Microsoft has implemented
`Stop` as a single-entry, fire-and-forget hook. The hook can prevent the session from
closing (side-effect visible to VS Code), but the `reason` field does not trigger a new
model turn. **The stop hook is effectually dead code for any model-communication purpose.**

---

## Finding 8 — Agent file approach works; hooks approach does not

**Empirical observation (2026-03-25):**

The `@imp.agent.md` and `@qa.agent.md` role files **do** reliably influence model behaviour:
- QA agents consistently stay read-only when the agent body specifies it.
- Role identity (imp/qa) is reliably respected.
- Sub-role declarations in the invocation argument reach the model via the user prompt itself.

The hooks approach failed on all three injection targets:
- `UserPromptSubmit.systemMessage` → UI warning only (not model context)
- `PreCompact.systemMessage` → UI warning only (not model context)
- `Stop.hookSpecificOutput.reason` → never triggers a model turn (empirically dead)

**Conclusion:** The hooks architecture for orchestration is a confirmed dead end.
Agent files + MCP tools are the viable path forward.

---

## Implications for Current Codebase (Updated)

### Confirmed dead (hooks layer)

The following files implement an approach that has no effect on model context:

| File | Purpose | Status |
|---|---|---|
| `hooks/detect_sub_role.py` | UPS → sub-role systemMessage | Dead — systemMessage is UI-only |
| `hooks/notify_compaction.py` | PreCompact → context re-injection | Dead — systemMessage is UI-only |
| `hooks/stop_handover_guard.py` | Stop → block + reason | Dead — reason never triggers model turn |

These files can be removed or left as inert infrastructure. They cause no harm but
provide no orchestration benefit.

### Reusable (config + contracts layer)

The following remain valuable as backend for future MCP tool implementation:

| File | Reusable for |
|---|---|
| `config/requirements_loader.py` | Loading sub-role specs in MCP tools |
| `contracts/interfaces.py` | `SubRoleSpec` datatype for tool schemas |
| `.copilot/sub-role-requirements.yaml` | Sub-role config, target mapping, handover fields |
| `utils/_paths.py` | State file path resolution |

### Recommended next architecture: MCP-tool-first

Replace hooks with two MCP server tools:

1. **`get_work_context`** (extend existing) — returns work context + active role + sub-role
   spec in a single tool call. Guaranteed model context via tool-response path.

2. **`create_handover`** (new) — validates handover fields against `SubRoleSpec`, stores
   the handover document. Input schema is driven by the sub-role's `required_fields` from
   YAML config. Missing fields → validation error with exact field names.

This approach eliminates all hook dependency. Model context injection is 100% reliable
because tool-call responses are a documented, contractually guaranteed model context path.

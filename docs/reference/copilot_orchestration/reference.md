<!-- docs/reference/copilot_orchestration/reference.md -->
<!-- template=generic_doc version=43c84181 created=2026-03-21T00:00:00Z updated= -->
# Copilot Orchestration — Package Reference

**Status:** DEFINITIVE  
**Version:** 1.0  
**Last Updated:** 2026-03-21

---

## Purpose

Reference documentation for the `copilot_orchestration` package. This package enforces structured hand-over discipline in VS Code Copilot chats via hook-driven sub-role detection and stop enforcement.

## Scope

**In Scope:**
Hook architecture, sub-role table, enforcement matrix, session state files, `@imp` / `@qa` agent scope, follow-up interaction behaviour, slash command use cases.

**Out of Scope:**
Internal implementation details, external workflow tooling, coding standards.

---

## Summary

The `copilot_orchestration` package provides three VS Code Copilot hooks that together enforce structured output at the end of implementation and QA sessions. Hooks are **agent-scoped**: they only fire when the `@imp` or `@qa` custom agent is in use. Normal chat windows and other custom agents are unaffected.





---

## Architecture Overview

Three hooks collaborate to detect, persist, and enforce sub-role state per session.

| Hook event | Script | Responsibility |
|------------|--------|----------------|
| `UserPromptSubmit` | `detect_sub_role.py` | Detects sub-role from first user prompt text; writes `.copilot/session-sub-role.json` once per session (idempotent via `session_id` check). |
| `Stop` | `stop_handover_guard.py` | On every agent response: reads `.copilot/session-sub-role.json`; if sub-role has `requires_crosschat_block: true`, blocks the response until the agent adds the structured hand-over block. |
| `PreCompact` | `notify_compaction.py` + `pre_compact_agent.py` | Writes a transcript snapshot to `.copilot/sessions/` and injects a compaction warning into context. |

**Key property:** `detect_sub_role.py` is idempotent — if `session_id` in the state file matches the incoming session, it exits immediately. The sub-role is determined once at session start and remains locked for the entire session, including all follow-up interactions.

## Session File Duality

Two distinct state files live in `.copilot/`. They serve different purposes and must not be confused.

| File | Written by | Purpose |
|------|------------|----------|
| `.copilot/session-sub-role.json` | `detect_sub_role.py` (v2) | Active sub-role for the current session. Used by `stop_handover_guard.py` to determine enforcement profile. Format: `{session_id, role, sub_role, detected_at}`. |
| `.copilot/session-state.json` | `pre_compact_agent.py` (v1) | Transcript snapshot written before compaction for SessionStart recovery. Used by session-start scripts to restore context after compaction. Format varies. |

> **Rule of thumb:** If you need to know _what role_ is active → read `session-sub-role.json`. If you need to know _what was discussed_ → read `session-state.json`.

## Sub-Role Table

Sub-role names are the authoritative keys in `.copilot/sub-role-requirements.yaml`. The `default_sub_role` is used when no sub-role is detected in the first prompt.

### `@imp` — Implementation agent

Default sub-role: **implementer**

| Sub-role | `requires_crosschat_block` | Heading enforced |
|----------|--------------------------|------------------|
| `researcher` | `false` | Research Output |
| `planner` | `false` | Planning Output |
| `designer` | `false` | Design Output |
| `implementer` | **`true`** | Implementation Hand-Over |
| `validator` | **`true`** | Validation Hand-Over |
| `documenter` | `false` | Documentation Output |

### `@qa` — QA agent

Default sub-role: **verifier**

| Sub-role | `requires_crosschat_block` | Heading enforced |
|----------|--------------------------|------------------|
| `plan-reviewer` | `false` | Planning Review |
| `design-reviewer` | `false` | Design Review |
| `verifier` | **`true`** | Verification Review |
| `validation-reviewer` | `false` | Validation Review |
| `doc-reviewer` | `false` | Documentation Review |

## Enforcement Scope

**Hooks are agent-scoped.** `UserPromptSubmit` and `Stop` hooks are only defined in the YAML frontmatter of `.github/agents/imp.agent.md` and `.github/agents/qa.agent.md`. They do not fire in any other context.

| Context | `UserPromptSubmit` fires | `Stop` enforces hand-over | `PreCompact` fires |
|---------|--------------------------|---------------------------|--------------------|
| `@imp` chat | Yes | Yes (if sub-role enforced) | Yes (agent-scoped) |
| `@qa` chat | Yes | Yes (if sub-role enforced) | Yes (agent-scoped) |
| Normal chat (no agent) | No | No | Global only |
| Other custom agent | No (unless configured) | No | No |

**Consequence:** Work performed outside `@imp`/`@qa` is not guarded. The enforcement state in `.copilot/session-sub-role.json` is not corrupted by normal chats — it is simply not written or read.

## Follow-Up Interaction Behaviour

A common question: does the stop hook fire reliably during follow-up questions, not just the first response?

**Yes.** The `Stop` hook fires on **every** agent response within a session. The sub-role is locked at session start (first prompt), so every subsequent response — including follow-up questions about the work — is evaluated against the same enforcement profile.

**Why `/prepare-handover` is still useful even when `Stop` auto-enforces:**

| Situation | Auto-enforcement covers it? | Use `/prepare-handover`? |
|-----------|-----------------------------|---------------------------|
| `implementer` or `validator` sub-role active | Yes | Only if handover quality is insufficient |
| `researcher`, `planner`, `designer`, `documenter` sub-role | No (`requires_crosschat_block: false`) | **Yes** — only way to get a structured hand-over |
| Session without `@imp`/`@qa` (normal chat, prompt file) | No hooks fire | **Yes** — the only enforcement path |
| Agent produced compliant block but content is thin | Technically yes | **Yes** — to produce a richer, explicit hand-over |

**In summary:** Auto-enforcement guarantees structure; `/prepare-handover` addresses quality and covers sub-roles / contexts where enforcement is off.

## Slash Command Use Cases

The `.github/prompts/` directory contains prompt files invocable from any VS Code Copilot chat via `/command`.

| Command | Agent | When to use |
|---------|-------|-------------|
| `/start-work` | `@imp` | Begin a new implementation session. Activates startup protocol, establishes sub-role. |
| `/resume-work` | `@imp` | Re-enter an existing session after context loss or compaction. Reads `session-sub-role.json` to restore enforcement context. |
| `/prepare-handover` | `@imp` | Explicitly request a structured hand-over block. Use when auto-enforcement does not apply or hand-over quality needs improvement. |
| `/request-review` | `@qa` | Begin a QA review session. Activates QA startup protocol, establishes sub-role. |
| `/prepare-implementation-brief` | `@qa` | After verification, produce a structured directive for the implementation agent to action QA findings. |

> **Note:** Sub-role is detected from the argument passed to the command. If no sub-role is provided, the prompt instructs the agent to ask the user.

## Related Documentation
- **[src/copilot_orchestration/README.md][related-1]**
- **[.copilot/sub-role-requirements.yaml][related-2]**
- **[.github/agents/imp.agent.md][related-3]**
- **[.github/agents/qa.agent.md][related-4]**

<!-- Link definitions -->

[related-1]: src/copilot_orchestration/README.md
[related-2]: .copilot/sub-role-requirements.yaml
[related-3]: .github/agents/imp.agent.md
[related-4]: .github/agents/qa.agent.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-21 | Agent | Initial draft |
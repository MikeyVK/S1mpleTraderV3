# VS Code Orchestration Usage Guide

**Status:** WORKING GUIDE  
**Created:** 2026-03-17  
**Updated:** 2026-03-17  
**Scope:** How to use the lightweight implementation orchestration on this branch with hooks, custom agents, and slash prompts.

---

## 1. What This Gives You

On this branch, the orchestration layer is intentionally small.

It gives you:
- `@imp` for implementation work
- `@qa` for read-only verification
- `SessionStart` context injection when you open a new chat
- `PreCompact` snapshotting before context compaction
- slash prompts for starting work, resuming after compaction, preparing handover, and requesting QA review

It does not give you:
- automatic issue-phase routing
- `.st3`-driven orchestration
- full workflow management inside VS Code

Think of it as an implementation cockpit, not a workflow engine.

---

## 2. First-Time Setup For Testing

When you want to test the orchestration on this branch:

1. Open a new Copilot chat.
2. If the custom agents do not appear, run `Developer: Reload Window`.
3. Use the new chat for testing. Do not rely on an old chat tab.

Why:
- `SessionStart` runs on a new chat session.
- Custom agents and prompt files are more reliably picked up after a window reload than inside an old live chat.

---

## 3. What Your First Prompt Should Be

For a fresh implementation session, use one of these two entry patterns.

### Option A: Plain first prompt

Use this when you want to be explicit yourself:

```text
@imp Implement [brief task].
Work only within these files if possible: [file list].
Before editing, restate the active goal, files in scope, assumptions, and first concrete step.
```

Example:

```text
@imp Implement the next event bus cleanup.
Work only within these files if possible: backend/core/eventbus.py and tests/backend/test_eventbus.py.
Before editing, restate the active goal, files in scope, assumptions, and first concrete step.
```

### Option B: Slash-prompt first prompt

Use this when you want the tool to structure the opening for you:

```text
/start-implementation Implement the next event bus cleanup in backend/core/eventbus.py and tests/backend/test_eventbus.py.
```

This is the recommended default starting point.

---

## 4. Recommended Human Flow

### Preferred Mode: Two Separate Chats

This branch should currently be used with two separate chats:
- one implementation chat with `@imp`
- one QA chat with `@qa`

Recommended sequence:
1. Start or continue an implementation chat.
2. Use `/start-implementation` with the task.
3. Let `@imp` establish scope.
4. Let `@imp` implement the change.
5. Use `/prepare-handover`.
6. Copy the hand-over if needed.
7. Start or continue a separate QA chat.
8. Use `/request-qa-review` there, or paste your own stricter QA prompt.

### After compaction

1. Continue in a new or recovered chat.
2. Use `/resume-implementation` in the implementation chat or restate the QA goal in the QA chat.
3. Confirm the recovered goal and files in scope.
4. Continue only within that role.

### About chat buttons and role switching

If you see a role-switch button inside the chat window, that came from agent handoff metadata from an earlier configuration state.
That button is not the intended operating model for this branch.
Use separate chats instead.
If the button still appears after these changes, open a new chat or run `Developer: Reload Window`.

### Manual QA review

If you do not want to use the QA slash prompt, you can still start with:

```text
@qa Review the latest implementation handover and changed files. Give findings first and then a GO, NOGO, or CONDITIONAL GO verdict.
```

---

## 5. Slash Prompts Available On This Branch

### `/start-implementation`

Use when:
- you start a fresh implementation session
- you want `@imp` to restate scope before coding

### `/resume-implementation`

Use when:
- context compaction happened
- you want to rebuild goal, file scope, and next step before coding further

### `/prepare-handover`

Use when:
- implementation work is done for now
- you want a structured handover that QA can actually verify

### `/request-qa-review`

Use when:
- a handover exists
- you want `@qa` to review the latest implementation state with findings first
- you want the QA review to end with a reusable implementation brief block

### `/prepare-qa-brief`

Use when:
- you want `@imp` to generate a deeper QA-ready prompt block
- you do not want to depend on spontaneous hand-over quality

### `/prepare-implementation-brief`

Use when:
- you want `@qa` to generate a deeper implementation-ready fix brief
- you want a deterministic copy-paste prompt back to the implementation chat

---

## 6. Small Rules That Make The Flow Work Better

- Start a new chat when testing `SessionStart`.
- Use `@imp` for coding and `@qa` for verification.
- Do not expect hidden workflow state to fill in missing scope for you.
- Give file paths when you can. The orchestration is stronger when scope is explicit.
- Use `/prepare-handover` before handing work to QA.
- In the implementation chat, expect the final hand-over to end with a fenced copy-paste prompt for the QA chat.
- In the QA chat, expect the final review to end with a fenced copy-paste prompt for the implementation chat when fixes are needed.
- Treat those fenced prompt blocks as the primary human-facing exchange format between the two chats.

---

## 7. Fastest Practical Test

If you want to test the branch quickly, do this:

1. Open a new chat.
2. Run:

```text
/start-implementation Implement a tiny no-op documentation-only change in docs/development/issue263/usage.md.
```

3. Confirm that `@imp` responds with goal, scope, assumptions, and next step.
4. Ask `@imp` to make the tiny change.
5. Run:

```text
/prepare-handover
```

6. Run:

```text
/request-qa-review
```

If that flow feels natural, the orchestration is already doing its job.

---

## 8. Session State And Recovery

The file `.copilot/session-state.json` is created by the `PreCompact` hook.

That means:
- it is written when VS Code triggers `PreCompact` before context compaction
- it can also be written during explicit synthetic tests when the hook script is invoked manually
- it is not the primary source of truth for the project
- it is a small orchestration-private recovery cache

What it is good for:
- restoring the last user goal after compaction
- restoring files in scope
- restoring a pending hand-over summary
- restoring a copy-paste handoff prompt block when one was present in the transcript

What it is not good for:
- replacing the explicit hand-over between the two chats
- carrying formal workflow state
- acting as the only evidence source for QA

Recommended rule:
- use the fenced copy-paste prompt blocks as the primary exchange format between `@imp` and `@qa`
- use `.copilot/session-state.json` as recovery support when compaction happens

To reduce stale-state confusion, the SessionStart hook now ignores snapshots unless they are both recent and relevant to the current changed files.
That means a fresh chat with no meaningful current worktree delta should not automatically hydrate itself from old recovery state.

## 9. Fallback If Hooks Or Agents Feel Stale

If the new behavior does not show up immediately:

1. Open a new chat.
2. Run `Developer: Reload Window`.
3. Try again.
4. Use [role_reset_snippets.md](../../../role_reset_snippets.md) if you want to force a clean role reset manually.

That fallback remains useful until the new orchestration is fully trusted.

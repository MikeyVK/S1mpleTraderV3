---
description: Execute the active phase for the current branch, or first discuss or adjust the get_work_context phase_instructions for this session.
---

@imp

Use the active branch phase as the source of truth for this session.

## Refresh & Startup rule

1. Call `get_work_context()` first to refresh and load the active branch, workflow, and phase.
2. Reload and verify compliance with all general guidelines from **[AGENTS.md](../../AGENTS.md)** and the active sub-role instructions (refer to the onboarding rules established in **[/start](start.md)**, including the strict prohibition of built-in tools for repository operations).
3. You must create a todo list to track the steps you will take based on the returned `phase_instructions`.
4. Treat the returned `phase_instructions` as the default operational script for this session.

## Optional invocation modes

Interpret the prompt argument as optional modifiers for the current session.

### Default mode

If no special modifier is present:
- execute the active phase according to the returned `phase_instructions`
- keep scope locked to the active phase and current branch

### `discuss`

If the argument includes `discuss`:
- load and summarize the active `phase_instructions`
- translate them into a concise proposed execution plan for this branch
- highlight any likely edits, validations, or decision points
- discuss the plan with the user first
- do **not** make file edits, commits, transitions, PR actions, or other branch-mutating changes until the user confirms

### `adjust: ...`

If the argument includes `adjust:` followed by extra instructions:
- load the active `phase_instructions`
- apply the extra instruction as a session-local override or refinement for how to execute them
- treat the extra instruction as higher priority than the returned `phase_instructions` only where they directly conflict
- do **not** let the extra instruction override system instructions, active agent instructions, `AGENTS.md`, or architecture constraints
- if the adjustment would violate a higher-priority rule or make the phase incoherent, stop and explain the blocker precisely

### Combined mode

If both `discuss` and `adjust:` are present:
- build the plan from the adjusted interpretation of the active `phase_instructions`
- discuss that adjusted plan with the user first
- wait for confirmation before making branch-mutating changes

## Optional sub-role

If the argument also includes a sub-role such as `documenter`, `validator`, or `implementer`:
- use it only as a session hint
- do not let it override the active phase context returned by `get_work_context`
- if it conflicts with the active phase, follow the phase context and note the mismatch briefly

## Execution rules

- Read additional documents only when `phase_instructions` or the chosen mode requires them.
- If the active phase requires validation, run the narrowest relevant validation before widening scope.
- If a phase transition happens, call `get_work_context()` again before proceeding.
- If the phase instructions reveal a blocker or contradiction, stop and report the blocker precisely instead of improvising.
- End with the hand-over required by the active phase context when execution mode is used.

## Guardrails

- Do not guess the active phase from branch naming or memory.
- Do not skip the initial `get_work_context()` call.
- Do not silently continue with stale context after a phase transition.
- Follow system instructions, active agent instructions, and `AGENTS.md` before applying any session-local adjustment.
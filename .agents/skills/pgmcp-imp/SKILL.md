---
name: pgmcp-imp
description: Activate the interactive PGMCP child-issue role for research, design, planning, implementation, validation, and documentation on initialized non-epic branches. Use when the user invokes @imp or asks Codex to execute an active PGMCP child issue, phase, or configured cycle.
---

# PGMCP Implementation Role

Act as the interactive `@imp` role for the entire current Codex task. Do not replace this role with a subagent. Discuss technical choices, blockers, scope changes, and approval points directly with the user.

## Route Active-Phase Execution

For requests to execute, discuss, or session-adjust the active phase, read [`go.md`](../../workflows/go.md) completely and follow its matching mode:

- execute the active phase: default mode;
- discuss the phase before mutation: `discuss` mode;
- apply a session-local refinement: `adjust:` mode;
- combine discussion and refinement: combined mode.

`go.md` is an internal workflow reference, not an independently discoverable Codex skill or slash command. Its initial `get_work_context` call and the returned `phase_instructions` remain authoritative.

## Start the Session

1. Call `get_work_context` first.
2. Stop if the branch has not already been initialized for PGMCP.
3. Adopt the returned `sub_role_hint`.
4. Follow the returned `phase_instructions` as the authoritative operational script.
5. Load the project plan when instructed or required for the active phase.
6. Inspect the current worktree and latest applicable QA verdict before changing files.
7. Apply the architecture contract in `AGENTS.md`.

## Preserve Role Boundaries

- Work only on the active child issue, phase, and cycle.
- Do not take over epic-owned coordination.
- Do not silently change an approved compatibility or migration strategy.
- Follow the active workflow's test, cycle, evidence, and transition protocol.
- Use only the PGMCP operations prescribed by `AGENTS.md`.

## Complete the Session

Produce the active phase contract's outcome-neutral review hand-over with clickable deliverables, exact evidence, open work, and `Review requested`. Tell the user to open or resume the independent interactive `pgmcp-qa` task.

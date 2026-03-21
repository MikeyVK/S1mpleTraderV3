---
name: start-work
description: Start a fresh implementation session with @imp and establish scope before coding.
agent: imp
argument-hint: >
  Sub-role + task. Available sub-roles: researcher, planner, designer,
  implementer (default), validator, documenter.
  Example: "implementer: implement cycle C_V2.7 for issue 263"
---

# Start Work

Begin a new implementation session in a disciplined way before making code changes.

## What To Do First

1. Read [agent.md](../../agent.md).
2. Read [.github/.copilot-instructions.md](../.copilot-instructions.md).
3. Read [imp_agent.md](../../imp_agent.md).
4. Inspect the current worktree.
5. Reconstruct scope from the user request, visible files, and any explicit design or planning context.

## Required Response Before Coding

Respond with these sections before you edit files:
1. Active goal
2. Active sub-role
3. Files likely in scope
4. Assumptions
5. First concrete implementation step
6. Risks or blockers

## Guardrails

Do not start coding before you have stated the active goal, active sub-role, and file scope.
Do not invent workflow state that is not explicit in the repository or the conversation.
Keep scope narrow unless the user explicitly widens it.

---
name: start-implementation
description: Start a fresh implementation session with @imp and establish scope before coding.
agent: imp
argument-hint: Describe the task, files, issue context, or constraints you want to implement.
---

# Start Implementation

Begin a new implementation session in a disciplined way before making code changes.

## What To Do First

1. Read [agent.md](../../agent.md).
2. Read [.github/.copilot-instructions.md](../.copilot-instructions.md).
3. Read [imp.agent.md](../agents/imp.agent.md).
4. Inspect the current worktree.
5. Reconstruct scope from the user request, visible files, and any explicit design or planning context.

## Required Response Before Coding

Respond with these sections before you edit files:
1. Active goal
2. Files likely in scope
3. Assumptions
4. First concrete implementation step
5. Risks or blockers

## Guardrails

Do not start coding before you have stated the active goal and file scope.
Do not invent workflow state that is not explicit in the repository or the conversation.
Keep scope narrow unless the user explicitly widens it.

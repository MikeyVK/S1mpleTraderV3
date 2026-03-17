---
name: resume-implementation
description: Rebuild implementation context after compaction without relying on hidden workflow state.
agent: imp
argument-hint: Optionally add the exact task or file set you want to resume.
---

# Resume Implementation

Reconstruct the active implementation context before making changes.

## Recovery Protocol

1. Read [agent.md](../../agent.md).
2. Read [.github/.copilot-instructions.md](../.copilot-instructions.md).
3. Read [imp.agent.md](../agents/imp.agent.md).
4. Read [docs/coding_standards/ARCHITECTURE_PRINCIPLES.md](../../docs/coding_standards/ARCHITECTURE_PRINCIPLES.md).
5. Read `.copilot/session-state.json` if it exists.
6. Inspect the current worktree before editing anything.
7. Reconstruct scope from the latest user request, the current conversation, visible files in scope, and any explicit plan or handover.

## Required Output

Respond with these sections before you continue implementation:
1. Recovered goal
2. Files in scope
3. Verification state
4. Next concrete step
5. Missing context or blockers

## Guardrails

Do not invent workflow phase, issue state, or deliverables from hidden assumptions.
Use repository guidance when it exists, but do not make `.st3` a required runtime dependency for recovery.
If recovery is partial, say so explicitly before proceeding.

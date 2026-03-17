---
name: request-qa-review
description: Start a separate QA review chat for the latest implementation hand-over.
agent: qa
argument-hint: Paste the latest implementation hand-over or the QA brief block if available.
---

# Request QA Review

Use qa_agent.md as the project-specific QA guide.

## Startup Protocol

1. Read agent.md, .github/.copilot-instructions.md, and qa_agent.md.
2. Inspect the current worktree and changed files before trusting any recovered snapshot state.
3. If recovered snapshot state conflicts with the user prompt, pasted hand-over, or current changed files, ignore the snapshot and say so explicitly.
4. Prefer the pasted hand-over or QA brief block over `.copilot/session-state.json`.

## Review Task

Review the latest implementation hand-over against the actual changed files and the proof provided.
Focus on correctness, regression risk, architectural compliance, and missing validation.

## Required Output

Return these sections in order:
1. Findings
2. Open Questions
3. Verdict
4. Copy-Paste Prompt For Implementation Chat

## Output Rules

- Findings must come first.
- Reference concrete files when possible.
- Distinguish verified proof from claims.
- If proof is missing or weak, say so plainly.
- Under `Copy-Paste Prompt For Implementation Chat`, end with exactly one fenced `text` block that is directly reusable in a separate implementation chat.

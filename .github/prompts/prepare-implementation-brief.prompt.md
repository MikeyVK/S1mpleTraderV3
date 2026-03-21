---
name: prepare-implementation-brief
description: Produce a deep, copy-paste-ready implementation prompt block for a separate implementation chat.
agent: qa
argument-hint: Optionally state the exact findings or files that must be emphasized for implementation.
---

# Prepare Implementation Brief

Produce a deep, copy-paste-ready prompt for a separate implementation chat.

## Required Output

Return two parts in this order:
1. A short note stating what the implementation brief covers.
2. Exactly one fenced `text` block titled `Copy-Paste Prompt For Implementation Chat`.

## Required Prompt Content

Inside the fenced block, include:
- task statement (include active sub-role: `implementer` for code changes, `validator` for e2e/acceptance tests)
- files likely in scope as a numbered list
- required fixes as a numbered list
- explicit out-of-scope reminders where useful
- required proof on return
- instruction to prepare an updated hand-over for QA using the required marker headings: `Scope`, `Files Changed`, `Proof`, `Ready-for-QA`

## Guardrails

Do not produce a vague summary.
Do not ask implementation to widen scope.
Keep the block directly usable in a separate implementation chat with minimal editing.

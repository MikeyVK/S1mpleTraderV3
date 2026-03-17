---
name: prepare-handover
description: Prepare a structured implementation hand-over for a separate QA chat.
agent: imp
argument-hint: Optionally state the exact files, claim, and proof that must be highlighted.
---

# Prepare Handover

Use imp_agent.md as the project-specific implementation guide.

## Required Sections

Return these sections in order:
1. Scope Completed
2. Files Changed
3. Implementation Claim
4. Proof
5. Known Gaps
6. QA Focus
7. Copy-Paste Prompt For QA Chat

## Section Rules

- `Scope Completed`: concise list of what was actually finished.
- `Files Changed`: real file paths only.
- `Implementation Claim`: precise statement of what now works.
- `Proof`: exact tests, checks, and outcomes.
- `Known Gaps`: explicit unverified, deferred, or risky items.
- `QA Focus`: what QA should validate first.
- `Copy-Paste Prompt For QA Chat`: end with exactly one fenced `text` block that is directly reusable in a separate QA chat.

## Guardrails

- Do not claim validation that did not happen.
- Do not omit known gaps.
- Do not produce a shallow QA prompt block.
- The fenced QA prompt block must include files in scope, implementation claim, proof provided, and explicit QA focus.

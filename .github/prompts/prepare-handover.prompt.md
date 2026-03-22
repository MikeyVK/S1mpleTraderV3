---
name: prepare-handover
description: Prepare a structured implementation hand-over for a separate QA chat.
agent: imp
argument-hint: Optionally state the exact files, claim, and proof that must be highlighted.
---

# Prepare Handover

Section headings below are the **required markers** matched by the Stop hook against
`.copilot/sub-role-requirements.yaml` for sub-role `implementer`. Use these exact headings.

## Required Sections

Return these sections in order:
1. Scope
2. Files Changed
3. Deliverables
4. Proof
5. Open Blockers
6. Ready-for-QA
7. Copy-Paste Prompt For QA Chat

## Section Rules

- `Scope`: concise list of what was actually finished; what was intentionally kept out of scope.
- `Files Changed`: real file paths only, grouped by role.
- `Deliverables`: which authoritative deliverables are now satisfied.
- `Proof`: exact tests run, gate commands or MCP checks run, exact outcomes.
- `Open Blockers`: explicit list of unverified, deferred, or risky items. Say `none` only if none remain.
- `Ready-for-QA`: `yes` or `no`.
- `Copy-Paste Prompt For QA Chat`: end with exactly one fenced `text` block starting with `@qa verifier` that is directly reusable in a separate QA chat.

## Guardrails

- Do not claim validation that did not happen.
- Do not omit known gaps.
- Do not produce a shallow QA prompt block.
- The fenced QA prompt block must include files in scope, implementation claim, proof provided, and explicit QA focus.

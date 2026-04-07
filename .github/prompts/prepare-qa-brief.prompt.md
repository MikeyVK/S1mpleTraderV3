---
name: prepare-qa-brief
description: Produce a deep, copy-paste-ready QA prompt block for a separate QA chat.
agent: imp
argument-hint: Optionally state the exact files, claim, or proof that should be emphasized for QA.
---

# Prepare QA Brief

Produce a deep, copy-paste-ready prompt for a separate QA chat.

## Required Output

Return two parts in this order:
1. A short note stating what the QA brief covers.
2. Exactly one fenced `text` block titled `Copy-Paste Prompt For QA Chat`.

## Required Prompt Content

Inside the fenced block, include:
- opening line: `@qa verifier: Review the implementation handover for [branch/cycle]`
- branch or work context if known
- files in scope as a numbered list
- precise implementation claim under review
- exact proof provided so far (using `Scope`, `Files Changed`, `Proof`, `Ready-for-QA` headings as reference)
- unverified or deferred items
- explicit QA focus

## Guardrails

Do not produce a shallow summary.
Do not omit proof gaps.
Keep the block directly usable in a separate QA chat with minimal editing.

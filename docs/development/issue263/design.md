# VS Code Implementation Orchestration — Compact Design

**Status:** PRELIMINARY  
**Version:** 1.0  
**Created:** 2026-03-17  
**Updated:** 2026-03-17  
**Author:** Design phase  
**Scope:** Ultra-light implementation-only orchestration using native VS Code hooks and custom agents, without MCP workflow coupling.

---

## 1. Executive Summary

This design defines the smallest orchestration layer that is still worth having for implementation work in VS Code Copilot.

It is intentionally narrow.

It covers only:
- implementation work
- QA verification
- context recovery after compaction
- structured handover between `@imp` and `@qa`

It explicitly does not cover:
- issue or project workflow management
- phase tracking
- `.st3` state
- MCP workflow orchestration
- planning, research, writer, or coordination roles
- repo-specific path conventions as orchestration inputs

The design goal is not to build a workflow engine. The goal is to create an implementation cockpit.

---

## 2. Design Goals

### 2.1 Primary Goals

1. Keep implementation context alive across compaction.
2. Make the `@imp` and `@qa` roles explicit inside VS Code.
3. Preserve strong scope, proof, and truthfulness discipline.
4. Avoid coupling to repository workflow state or server-specific orchestration.
5. Keep the solution portable and mechanically simple.

### 2.2 Non-Goals

This design does not try to:
- replace `agent.md`
- replace `.github/.copilot-instructions.md`
- infer issue number, cycle, or formal project phase
- enforce repository workflow transitions
- decide what is in scope from `.st3/projects.json`
- route work across research, planning, design, documentation, or coordination
- block tools based on project-specific lifecycle rules

---

## 3. Architectural Principles

This design follows the binding architecture contract in `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md`.

### 3.1 SRP

Each part has one job:
- `SessionStart` injects immediate context.
- `PreCompact` stores a minimal recovery snapshot.
- `@imp` executes implementation work.
- `@qa` verifies implementation claims.
- optional prompts structure recovery and handover.

No part owns repository workflow logic.

### 3.2 No Workflow Coupling

The orchestration layer must not depend on:
- `.st3/state.json`
- `.st3/projects.json`
- phase names
- issue folders as runtime inputs
- MCP resource state
- branch naming conventions

If such information happens to exist, it may still be used by the human or by the active repo instructions, but it is not part of the orchestration mechanism itself.

### 3.3 Explicit Over Implicit

The system should prefer explicit role prompts and explicit handovers over hidden workflow assumptions.

### 3.4 Minimal Persistence

Persistence exists only to survive compaction. It is not a business state model.

---

## 4. Solution Overview

The compact model has four moving parts:

1. `SessionStart` hook
2. `PreCompact` hook
3. `@imp` custom agent
4. `@qa` custom agent

Optional but recommended:
- `/start-implementation` prompt
- `/resume-implementation` prompt
- `/prepare-handover` prompt
- `/request-qa-review` prompt

### 4.1 Runtime Model

```text
user request
  -> SessionStart injects immediate context
  -> user works with @imp for implementation
  -> @imp produces structured handover
  -> user switches to @qa
  -> @qa verifies claims and gives GO / NOGO / CONDITIONAL GO
  -> PreCompact preserves minimal recovery state when context is compressed
```

This is enough to support the real implementation scenario without pretending to manage the whole repository workflow.

---

## 5. Hook Design

### 5.1 SessionStart Hook

**Responsibility:** inject a short, implementation-focused context summary at the start of a chat session.

**Inputs:**
- VS Code hook event payload
- local lightweight recovery snapshot if present
- git working tree summary if available

**Output:**
A short instruction block such as:
- current branch if detectable
- changed files summary if detectable
- active role if previously known
- pending handover presence if known
- recommendation to use `@imp` for coding or `@qa` for verification

**Must not do:**
- load project workflow state
- infer issue phases
- parse repo-specific manifests
- decide deliverables

### 5.2 PreCompact Hook

**Responsibility:** store the minimum information needed to resume implementation work after compaction.

**What it stores:**
- timestamp
- active role
- last user goal summary
- files in scope mentioned in conversation
- optional pending handover summary

**What it must not store:**
- project workflow phase
- formal issue progress
- branch policy decisions
- derived business state

### 5.3 Storage Boundary

The recovery snapshot belongs to the orchestration layer itself, not to the repository workflow system.

Preferred storage properties:
- package-owned
- tiny JSON payload
- replaceable or disposable
- safe to delete without corrupting project state

The exact storage location may be decided in implementation, but it must remain orchestration-private and must not become a new project source of truth.

---

## 6. Agent Design

### 6.1 `@imp` Role

`@imp` is the implementation producer.

It should preserve the quality bar already present in `.github/agents/imp.agent.md`:
- startup discipline after compaction
- scope lock
- TDD-first implementation behavior when relevant
- architectural obedience
- explicit proof expectations
- precise and falsifiable handover
- no self-approval

For this compact model, `@imp` should derive scope from:
- the latest user request
- the currently discussed files
- the active repository instructions
- any explicit plan or handover in the conversation

It should not require MCP workflow metadata to function.

### 6.2 `@qa` Role

`@qa` is the verifier.

It should preserve the quality bar already present in `.github/agents/qa.agent.md`:
- read-only default behavior
- skeptical verification
- findings-first output
- distrust of unsupported claims
- architecture-first review standard
- explicit GO / NOGO / CONDITIONAL GO

For this compact model, `@qa` should derive review scope from:
- the latest user request
- the latest implementation handover
- changed files and direct evidence
- explicit claims made by `@imp`

It should not depend on formal project phase state.

---

## 7. Handover Contract

The handover is the core coordination artifact.

The compact design keeps the existing strong shape but removes workflow-specific dependencies.

### 7.1 Required Sections

Every implementation handover should contain:
1. Scope
2. Files
3. What changed
4. Proof
5. Out-of-scope
6. Open blockers
7. Ready-for-QA

### 7.2 Proof Rules

Proof must remain precise:
- exact tests run
- exact checks run
- exact outcome
- explicit gaps if something was not verified

### 7.3 Truthfulness Rules

Never claim:
- full suite green unless it was run
- architecture clean unless checked against the real changed surface
- no blockers if important unknowns remain

This preserves the spirit of `.github/agents/imp.agent.md`, `.github/agents/qa.agent.md`, and `agent.md` without requiring MCP workflow context.

---

## 8. Prompt Support

### 8.1 `/resume-implementation`

Purpose:
- restore working discipline after compaction
- remind the active agent to re-read the core instruction files
- inspect the current worktree before acting
- restore the active file scope from the minimal snapshot

### 8.2 `/prepare-handover`

Purpose:
- force a structured handover before QA review
- standardize proof claims
- reduce ambiguity in role switches

These prompts are useful because they encode behavior, not project-specific state.

---

## 9. Minimal File Set

The compact design needs only this file family:

- `.github/hooks/session-start.json`
- `.github/hooks/pre-compact.json`
- `.github/agents/imp.agent.md`
- `.github/agents/qa.agent.md`
- optional `.github/prompts/resume-implementation.prompt.md`
- optional `.github/prompts/prepare-handover.prompt.md`
- a tiny hook implementation package or script folder

Not required:
- researcher or writer agents
- pre-tool-use gating
- issue-aware prompts
- workflow-aware prompt families
- repo lifecycle configuration

---

## 10. Quality Bar

This design must not lower the quality bar already established in:
- `agent.md`
- `.github/agents/imp.agent.md`
- `.github/agents/qa.agent.md`
- `.github/.copilot-instructions.md`
- `role_reset_snippets.md`

The compactness is structural, not intellectual.

What stays strong:
- startup protocol
- scope discipline
- architecture contract
- truthfulness requirements
- skeptical QA
- explicit handover
- compaction recovery

What becomes smaller:
- number of roles
- number of hooks
- number of prompts
- number of assumptions
- amount of workflow knowledge embedded in the orchestration layer

---

## 11. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Recovery snapshot is too weak | Agent resumes with missing context | Keep explicit file scope and last user goal in the snapshot |
| No workflow state means less formal scope derivation | Scope drift risk | Counter with stronger handover discipline and explicit user request grounding |
| Git metadata may be unavailable | Session summary is thinner | Degrade gracefully; do not fail the hook |
| Users may expect full lifecycle routing | Misuse of the compact layer | State clearly that this design is implementation-only |
| Role prompts may drift from repo guidance | Inconsistent behavior | Keep `agent.md`, `.github/.copilot-instructions.md`, `.github/agents/imp.agent.md`, and `.github/agents/qa.agent.md` as normative source material |

---

## 12. Implementation Plan

### Step 1
Create `SessionStart` and `PreCompact` hooks with no `.st3` dependency.

### Step 2
Create or adapt `@imp` and `@qa` custom agents so they reference the existing repository guidance rather than re-implementing it.

### Step 3
Add one recovery prompt and one handover prompt.

### Step 4
Test the following scenarios manually:
- new implementation session
- role switch from `@imp` to `@qa`
- compaction during active implementation work
- QA review after compaction recovery

### Step 5
Only after this proves useful, consider whether any extra orchestration is needed.

---

## 13. Decision

The active design for issue 263 is now:
- implementation-only
- native VS Code hooks plus custom agents
- no MCP workflow coupling
- no repo-specific orchestration state
- strong role guidance, strong handover, minimal persistence

Any broader orchestration ideas remain research, not active design.

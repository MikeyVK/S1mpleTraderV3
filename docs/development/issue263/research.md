# VS Code Agent Orchestration — Research Baseline

**Status:** PRELIMINARY RESEARCH  
**Version:** 1.0  
**Created:** 2026-03-17  
**Updated:** 2026-03-17  
**Author:** Research phase  
**Scope:** Preserve the broader orchestration exploration before narrowing to an implementation-only design.

---

## 1. Purpose

This document preserves the broader orchestration direction that was explored before the scope was deliberately reduced. It exists so the project does not lose the reasoning, patterns, and rejected options behind issue 263 when the active design is narrowed to an ultra-light implementation-only approach.

The previous document mixed several concerns:
- VS Code hooks
- custom agents
- prompt files
- instructions files
- workphase orchestration across the full development lifecycle
- MCP workflow integration
- `.st3` state usage
- role routing and tool gating

That broader exploration was useful as research, but too wide and too coupled to remain the active design for the current goal.

---

## 2. Research Goal

The original exploration tried to answer this question:

How far can VS Code Copilot native capabilities be used to create structured agent cooperation, compaction recovery, and phase-aware work guidance inside this repository?

The answer is: quite far technically, but not without architectural tradeoffs.

---

## 3. What Was Explored

### 3.1 Hooks as Lifecycle Bridges

The research confirmed that VS Code hook files are a viable primitive for:
- session-start context injection
- pre-compaction state capture
- optional pre-tool warnings or blocking

This is valuable because hooks are editor-native and require no custom UX layer.

### 3.2 Custom Agents as Role Containers

The research also confirmed that custom agents are a workable way to encode role behavior. The main explored role model was:
- `@researcher`
- `@imp`
- `@writer`
- `@qa`

This made the producer/verifier pattern explicit and reusable.

### 3.3 Prompt Files as Repeatable Workflows

Prompt files were explored as a way to standardize recurring tasks:
- recovery after compaction
- handover generation
- QA verification
- research/planning/design starts
- implementation and validation starts
- documentation and coordination starts

This is useful, but only if the surrounding workflow model is stable enough.

### 3.4 Instructions as Context Filters

The research explored `.instructions.md` files as a way to move domain rules out of a single large `.copilot-instructions.md` file and load them only when relevant.

That direction remains valid, but it is orthogonal to the immediate implementation-only orchestration goal.

---

## 4. Valuable Findings

### 4.1 Producer/Verifier Is the Strongest Reusable Pattern

The single strongest pattern from the broader exploration is the explicit producer/verifier split:
- one role produces change
- one role verifies claims
- handover is explicit
- approval authority stays outside implementation

This pattern maps cleanly onto the `.github/agents/imp.agent.md` and `.github/agents/qa.agent.md` guides.

### 4.2 Compaction Recovery Needs a Small Persistent Memory

The research strongly supports lightweight persistence across compaction. Without it, the agent loses:
- current user goal
- files in scope
- current role
- pending handover intent

That does not require MCP workflow state. It only requires a very small context snapshot.

### 4.3 Handover Quality Matters More Than Agent Count

The quality of the implementation handover and QA verification contract is more important than the number of roles. The strongest existing material in this repository is already centered on:
- startup discipline after compaction
- scope lock
- truthfulness rules
- explicit proof expectations
- read-only QA boundaries

Those principles should survive intact in a reduced design.

### 4.4 Native VS Code Features Are Sufficient for an Ultra-Light Model

The research indicates that a useful orchestration layer does not need:
- issue/phase awareness from MCP state
- branch naming rules
- planning-cycle state in `.st3`
- cross-phase routing
- repository-specific orchestration infrastructure

Hooks plus two custom agents can already cover the implementation scenario effectively.

---

## 5. Why the Broad Design Was Too Coupled

### 5.1 MCP Workflow Coupling

The broad design assumed `.st3/state.json`, `.st3/projects.json`, and related workflow state as runtime dependencies for hook behavior. That creates coupling to a specific server-side workflow engine.

That is a problem because the current objective is specifically to support hooks and custom agents even when no MCP workflow orchestration exists.

### 5.2 Hardcoded Workflow Knowledge

The broad design introduced explicit mappings such as:
- phase to agent
- phase to tool restrictions
- workflow type to role sequence

That violates the direction of the architecture contract when such knowledge is embedded directly into implementation code instead of remaining configurable or being removed from scope.

### 5.3 Repo-Specific Path Knowledge

The broad design assumed repository-specific folders and state conventions, especially around `.st3/`, issue folders, and workflow documents.

For an implementation-only orchestration layer, that is unnecessary and makes the solution less portable.

### 5.4 Too Many Responsibilities in One Layer

The broad design tried to solve at once:
- lifecycle recovery
- role routing
- workflow enforcement
- documentation orchestration
- issue coordination
- state persistence
- tool gating

That is not SRP-friendly. The current need is narrower and should be designed as such.

---

## 6. Patterns Worth Preserving

The following ideas from the broader exploration should be preserved in the compact design:

1. Session-start context injection.
2. Pre-compaction snapshotting.
3. Explicit implementation agent versus QA agent split.
4. Strong startup protocol after compaction.
5. Structured handover contract.
6. Skeptical read-only QA verification.
7. Minimal editor-native configuration through hooks, agents, and optional prompts.

The following ideas should be removed from the active design:

1. Full lifecycle orchestration beyond implementation.
2. Phase-aware routing.
3. MCP workflow state as an orchestration dependency.
4. `.st3` as a required runtime boundary.
5. Research, planning, writer, and coordination agents.
6. Tool gating based on repository workflow phases.

---

## 7. Research Conclusion

The broad orchestration concept was useful research, not the right active design.

Its main contribution is not the exact file layout or workflow coupling. Its contribution is the recognition that a small implementation cockpit can be built from native VS Code primitives if it keeps only the strongest invariants:
- implementation has scope and proof discipline
- QA is read-only and skeptical
- compaction must not erase the active task
- handover must be explicit and falsifiable

That conclusion directly informs the compact design in `design.md`.

---

## 8. Inputs for the Compact Design

The compact design should now optimize for these constraints:
- implementation scenario only
- no MCP workflow dependency
- no `.st3` dependency
- no hardcoded project workflow model
- no path-bound domain logic
- minimal persistence only for compaction recovery
- high-quality role guidance at the level of `agent.md`, `.github/agents/imp.agent.md`, `.github/agents/qa.agent.md`, `.github/.copilot-instructions.md`, and `role_reset_snippets.md`

---

## 9. Deferred Ideas

The following ideas are intentionally deferred and not part of the compact design:
- multi-phase lifecycle orchestration
- documentation/research/writer role family
- client-side phase gating for tools
- issue-aware routing
- MCP resource-backed orchestration state
- broad prompt library for all workphases
- repo-specific orchestration packages

If those are ever revisited, they should return as a new design iteration after the lightweight implementation-only model has proven itself useful.

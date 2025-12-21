# Issue 18 Plan: Choke-Point Enforcement + Phase State Engine

**Status:** DRAFT
**Author:** Copilot (GPT-5.2)
**Created:** 2025-12-21
**Last Updated:** 2025-12-21
**Issue:** #18

---

## 1. Overview

### 1.1 Purpose

Implement deterministic workflow enforcement via **tooling choke points** (commit/PR/merge/close) and a **phase state engine** that makes the TDD loop enforceable.

Important constraint: `safe_edit_tool` remains **fast-only**. Deep checks (tests, QA gates, coverage) are enforced at choke points, not on every edit.

### 1.2 Scope

**In Scope:**
- Implement a policy decision layer used by choke-point tools.
- Add enforceable rules to:
    - `git_add_or_commit` (commit gate)
    - `create_pr` (PR gate)
    - `merge_pr` (merge gate)
    - `close_issue` (closure gate)
- Add a phase state engine with persistence (repo-backed) and deterministic transitions.
- Add docs/artifact enforcement via templates + validation at choke points.

**Out of Scope:**
- Making `safe_edit_tool` run full QA (explicitly rejected).
- Large refactors across unrelated modules.
- Relying on GitHub UI branch protection as the primary mechanism (tooling enforcement is primary).

### 1.3 Related Documents

- [Agent Protocol (canonical workflow)](../../../AGENT_PROMPT.md)
- [Quality Gates](../../coding_standards/QUALITY_GATES.md)
- [TDD Workflow (legacy reference)](../../coding_standards/TDD_WORKFLOW.md)
- [Core Principles](../../architecture/CORE_PRINCIPLES.md)
- [Architectural Shifts](../../architecture/ARCHITECTURAL_SHIFTS.md)

---

## 2. Background

### 2.1 Current State

- The documented workflow in `AGENT_PROMPT.md` is clear, but is not enforceable.
- Tools exist for git/PR/issue actions, but they do not yet enforce tests/quality/docs as hard gates.
- `safe_edit_tool` is intentionally fast-only (cheap formatting + syntax checks). This improves UX, but increases the need for strict choke-point enforcement.

### 2.2 Problem Statement

Agents and humans skip steps under time pressure. Without deterministic enforcement:
- TDD phases drift (RED/GREEN/REFACTOR gets skipped or reordered).
- Tests/QA/coverage/docs requirements become “optional in practice”.
- Work can be committed/merged without the expected quality level.

### 2.3 Requirements

#### Functional Requirements
- [ ] **FR1:** Block commits on protected branches (`main`/`master`).
- [ ] **FR2:** Enforce phase-aware commit gating:
    - `red`: allow test-only commits (tests may fail), but must include test changes.
    - `green`: require tests passing.
    - `refactor`: require tests passing + quality gates passing.
- [ ] **FR3:** Enforce required docs/artifacts at PR creation and/or issue close.
- [ ] **FR4:** Provide a phase state engine that is deterministic and persists in-repo.
- [ ] **FR5:** Provide actionable error messages (what failed + how to fix via ST3 tools).

#### Non-Functional Requirements
- [ ] **NFR1:** Performance - choke-point checks can be slower, but must be bounded and have clear timeouts.
- [ ] **NFR2:** Determinism - same repo state yields same decision.
- [ ] **NFR3:** Testability - policy decisions and gate orchestration are unit-testable.

---

## 3. Design

### 3.1 Architecture Position

Where this component fits in the overall architecture.

```
Enforcement is centralized in policy + QA managers, and invoked by choke-point tools.

```
Developer/Agent
    |
    v
ST3 Tools (choke points)
    - git_add_or_commit
    - create_pr
    - merge_pr
    - close_issue
    |
    v
Policy Engine (NEW)
    |
    +--> Phase State Engine (NEW, repo-backed)
    |
    +--> Gates
                - tests (pytest)
                - quality (pylint/mypy/pyright)
                - coverage (future)
                - docs/artifacts (validate_doc + file existence)
```
```

### 3.2 Component Design

#### 3.2.1 Policy Engine

**Purpose:** Map `(operation + branch + phase + repo state)` → required gates + allow/deny.

**Responsibilities:**
- Evaluate protected-branch rules.
- Decide which gates must run for the operation.
- Provide a structured decision for tool orchestration.

**Dependencies:**
- Git state introspection (branch, changed/staged files).
- Phase state engine.

#### 3.2.2 Phase State Engine

**Purpose:** Provide explicit phase state (RED/GREEN/REFACTOR) and allowed transitions.

**Key rule:** Do not infer phase from "what the agent says"; store it.

**Persistence options (choose one):**
1) Repo-backed file: `.st3/phase.json` (preferred)
2) Commit-message inference fallback (best-effort)

#### 3.2.3 Docs/Artifacts Enforcement

**Purpose:** Ensure documentation is created consistently via tooling.

**Approach:**
- Use `scaffold_design_doc` (template-backed) to create required docs.
- Use `validate_doc` (structure/links) at choke points.
- Enforce presence + validation at `create_pr` and/or `close_issue`.

Note: `safe_edit_tool` is for safe edits; it should not be the primary enforcement mechanism for "docs must exist". Enforce at choke points instead.

### 3.3 Data Model

Policy input and decision (illustrative):

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Operation(str, Enum):
    COMMIT = "commit"
    CREATE_PR = "create_pr"
    MERGE_PR = "merge_pr"
    CLOSE_ISSUE = "close_issue"


class TDDPhase(str, Enum):
    RED = "red"
    GREEN = "green"
    REFACTOR = "refactor"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class PolicyContext:
    operation: Operation
    branch: str
    phase: TDDPhase
    changed_files: tuple[str, ...]
    staged_files: tuple[str, ...]


@dataclass(frozen=True)
class PolicyDecision:
    allow: bool
    reasons: tuple[str, ...]
    required_gates: tuple[str, ...]
```

### 3.4 Interface Design

```python
from __future__ import annotations

from typing import Protocol


class IPolicyEngine(Protocol):
    def decide(self, ctx: PolicyContext) -> PolicyDecision:
        ...
```

---

## 4. Implementation Plan

### 4.1 Phases

#### Phase 1: Policy + Phase State Foundation (no behavior change yet)

**Goal:** Introduce policy + phase state engine with unit tests, but keep choke points permissive (feature-flagged).

**Tasks (TDD-first):**
- [ ] RED: tests for phase persistence and policy decisions.
- [ ] GREEN: implement `.st3/phase.json` read/write + policy decision function.
- [ ] REFACTOR: tighten types, add helpful error messages.

**Exit Criteria:**
- [ ] Unit tests cover decision matrix.
- [ ] No choke-point behavior changes without explicit flag/config.

#### Phase 2: Commit Gate (`git_add_or_commit`)

**Goal:** Make correct workflow unavoidable at commit time.

**Tasks:**
- [ ] Branch protection: deny commits on `main`/`master`.
- [ ] Phase-aware gating:
    - `green` → require tests passing
    - `refactor` → require tests passing + quality gates passing
    - `red` → require that commit includes tests (and optionally allow failing tests)

**Exit Criteria:**
- [ ] Tool refuses commit on protected branch.
- [ ] GREEN cannot commit with failing tests.
- [ ] REFACTOR cannot commit with failing quality gates.

#### Phase 3: PR + Merge + Close gates

**Goal:** Gate PR creation/merge/issue close on artifacts and project QA.

**Tasks:**
- [ ] `create_pr`: require required docs/artifacts exist and validate.
- [ ] `merge_pr`: require quality gates pass (or assert PR was created with passing gates).
- [ ] `close_issue`: require docs exist + add a summary comment.

**Exit Criteria:**
- [ ] Tools refuse action when artifacts missing.
- [ ] Error messages guide user to the correct tool to fix.

#### Phase 4: Coverage gate (optional / follow-up)

**Goal:** Add coverage enforcement where it is stable and deterministic.

**Note:** Coverage is intentionally not forced at edit-time; apply at choke points.

### 4.2 Testing Strategy

| Test Type | Scope | Goals |
|-----------|-------|-------|
| Unit | Policy engine | Decision matrix correctness |
| Unit | Phase state engine | Read/write, transitions, edge cases |
| Unit | Choke-point tools | Proper gating calls + failure messages |
| Integration | Minimal flow | smoke tests for commit/PR/close orchestration |

---

## 5. Alternatives Considered

### Alternative A

**Description:** Enforce everything during `safe_edit_tool`.

**Pros:** Fast feedback.

**Cons:** Bad UX and slow; forces unrelated fixes; encourages bypassing tools.

**Decision:** Rejected. SafeEdit stays fast-only.

---

## 6. Open Questions

- [ ] Should phase state be branch-scoped or repo-scoped?
- [ ] How strict should RED be? (e.g., allow failing tests but require only tests changed)
- [ ] Standard paths/names for required docs/artifacts.
- [ ] Which gates run at `merge_pr` vs enforced at `create_pr`.

---

## 7. Relationship to Issue #24 (Tooling Debt)

Issue #24 is not a hard blocker for implementing enforcement logic, but it affects ergonomics and the ability to keep everything inside the ST3 tool ecosystem:

- **Not blocking:** We can implement choke-point gating in the existing tools without needing selective staging/restore.
- **Will bite later:** Without selective add/commit/restore, it’s harder to keep clean, scoped commits (docs vs code) using only tools.

Recommendation:
- Proceed with #18 on this branch.
- Treat #24 as a follow-up branch to remove remaining “escape hatches” and reduce friction.

---

## 7. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-21 | Enforce at choke points | Mood-proof enforcement at unavoidable operations |
| 2025-12-21 | Keep SafeEdit fast-only | Avoid latency and thrash during iteration |

---

## 8. References

- [Agent Protocol (canonical workflow)](../../../AGENT_PROMPT.md)
- [Quality Gates](../../coding_standards/QUALITY_GATES.md)
- [TDD Workflow (legacy reference)](../../coding_standards/TDD_WORKFLOW.md)

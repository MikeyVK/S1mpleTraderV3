# SafeEditTool Integration and Enforced TDD Workflow

**Status:** DRAFT
**Author:** ST3 Agent (Copilot)
**Created:** 2025-12-21
**Last Updated:** 2025-12-21
**Issues:** #20, #18, #14

---

## 1. Overview

### 1.1 Purpose

Define how SafeEditTool is integrated into the ST3 development flow, while making correct behavior **tooling-enforced** rather than “agent-mood dependent”.

This document formalizes:
- How the existing **RED / GREEN / REFACTOR** loop is mapped to tool entry points.
- Which validations are mandatory at which “choke points” (especially commit/PR/close).
- A concrete change set for SafeEditTool (performance + granularity).

### 1.2 Scope

**In Scope:**
- Enforcement rules for the following ST3 tools:
    - `scaffold_component` (new code creation)
    - `safe_edit_tool` (editing)
    - `git_add_or_commit` (commit gate)
    - `create_pr` (PR gate)
    - `close_issue` (issue closure gate)
- A small “policy model” that decides which gates apply based on context (operation + phase + branch + changeset).
- Minimal new parameters needed to activate enforcement deterministically.

**Out of Scope:**
- Large refactors across unrelated modules.
- Changing the overall architecture of the trading platform.
- GitHub branch protection settings in GitHub UI (this design focuses on **tooling**, not manual repo settings).

### 1.3 Related Documents

- [Core Principles](../../architecture/CORE_PRINCIPLES.md)
- [Architectural Shifts](../../architecture/ARCHITECTURAL_SHIFTS.md)
- [Coding Standards](../../coding_standards/README.md)
- [Quality Gates](../../coding_standards/QUALITY_GATES.md)
- [Agent Protocol](../../../agent.md)

---

## 2. Background

### 2.1 Current State

Today, `safe_edit_tool` can run full QA validation per edit, which creates latency during rapid refactoring and discourages usage. Meanwhile, correctness of the workflow depends too much on whether an agent/human “chooses” the right tool.

We already have a documented flow in [Agent Protocol](../../../agent.md):
- Use `scaffold_*` for creation.
- Do TDD loop (RED → GREEN → REFACTOR).
- Use tool priority matrix (never manual if a tool exists).

However, documentation alone cannot enforce behavior.

### 2.2 Problem Statement

We need a deterministic workflow where:
- The right validations run at the right time (fast feedback during edits, strict gates during commit/PR/close).
- The process does **not** depend on the “bui” of an agent/human.
- New files and tests are created through standardized scaffolding.
- Committing directly to `main` is technically prevented.

### 2.3 Requirements

#### Functional Requirements
- [ ] **FR1:** SafeEditTool supports multiple validation profiles (fast vs full) to reduce latency.
- [ ] **FR2:** SafeEditTool strict mode can block only on **critical** findings and/or **newly introduced** findings.
- [ ] **FR2.1:** In `FAST` profile for Python files, enforce cheap, high-signal formatting rules:
    - final newline present
    - no trailing whitespace
    - max line length 100
- [ ] **FR3:** `git_add_or_commit` enforces branch protection (cannot commit on `main`/`master`).
- [ ] **FR4:** `git_add_or_commit` enforces TDD phase gates:
    - RED: require at least one failing test (or explicitly marked failing test)
    - GREEN: require tests passing
    - REFACTOR: require tests passing + quality gates
- [ ] **FR5:** `create_pr` and/or `close_issue` enforce required artifacts (Issue #14): `walkthrough.md` + `implementation_plan.md`.
- [ ] **FR6:** `scaffold_component` remains the only supported “new code creation” path for typed components (DTO/worker/adapter/etc) and produces test stubs.

#### Non-Functional Requirements
- [ ] **NFR1:** Performance - fast edit validation should feel near-instant for single-file edits.
- [ ] **NFR2:** Determinism - results must be consistent across agents/humans.
- [ ] **NFR3:** Testability - policy decisions and tool gates are unit-testable (mockable external calls).
- [ ] **NFR4:** Safety - commit/PR/close gates must remain strict even if edit-time validation is relaxed.

---

## 3. Design

### 3.1 Architecture Position

This design introduces a **Policy Engine** concept that is used by tools to decide what validations (“gates”) must run.

```
                +-------------------+
                |  Developer/Agent  |
                +---------+---------+
                          |
                          v
     +--------------------+--------------------+
     | Entry Points (ST3 Tools)                |
     |  - scaffold_component                   |
     |  - safe_edit_tool                       |
     |  - git_add_or_commit   (CHOKE POINT)    |
     |  - create_pr           (CHOKE POINT)    |
     |  - close_issue         (CHOKE POINT)    |
     +--------------------+--------------------+
                          |
                          v
                 +--------+--------+
                 |  Policy Engine  |
                 +--------+--------+
                          |
                          v
                 +--------+--------+
                 | Gates / Checks  |
                 | - tests         |
                 | - quality       |
                 | - coverage      |
                 | - artifacts     |
                 +-----------------+
```

Key rule: **Enforcement happens at choke points** (commit/PR/close), not only during editing.

### 3.2 Component Design

#### 3.2.1 Policy Engine (New)

**Purpose:**
Deterministically map (operation + phase + branch + changeset) → required gates.

**Responsibilities:**
- Decide which validations must run for a given tool execution.
- Provide a structured decision that tools can enforce.

**Dependencies:**
- Repo state introspection (branch name, changed files, staged files).
- Configuration (thresholds, artifact paths, branch rules).

#### 3.2.2 Gates (Existing + Extended)

**Purpose:**
Encapsulate checks like unit tests, quality gates, coverage thresholds, and artifact presence.

**Notes:**
- For edits, use lighter gates (fast/critical-only) when configured.
- For commit/PR/close, use strict gates.

**Lightweight Edit Gate (Python):**
Even in `FAST` mode we enforce a tiny set of rules that prevent recurring “paper-cut” issues:
- Ensure file ends with a final newline.
- Reject or auto-fix trailing whitespace.
- Enforce max line length 100.

Rationale: these checks are deterministic, cheap to compute ($O(n)$ over the content), and remove the most frustrating trivial failures while still keeping `FAST` fast.

### 3.3 Data Model

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class TDDPhase(str, Enum):
    RED = "red"
    GREEN = "green"
    REFACTOR = "refactor"


class ValidationProfile(str, Enum):
    FAST = "fast"           # syntax + minimal checks (+ cheap Python formatting gate)
    CRITICAL = "critical"   # syntax + critical-only
    FULL = "full"           # full QA manager (tests + lint/type)


@dataclass(frozen=True)
class PolicyContext:
    operation: str  # e.g. "safe_edit", "git_commit", "create_pr", "close_issue", "scaffold"
    phase: TDDPhase
    branch: str
    changed_files: tuple[str, ...]
    staged_files: tuple[str, ...]


@dataclass(frozen=True)
class PolicyDecision:
    allow: bool
    reasons: tuple[str, ...]
    required_gates: tuple[str, ...]
    validation_profile: ValidationProfile
```

### 3.4 Interface Design

```python
from __future__ import annotations

from typing import Protocol


class IPolicyEngine(Protocol):
    def decide(self, context: PolicyContext) -> PolicyDecision:
        """Return a deterministic policy decision for the given context."""
        ...
```

Tools use the policy decision to run the required gates and fail early with actionable feedback.

---

## 4. Implementation Plan

### 4.1 Phases

#### Phase 1: Commit Choke Point Enforcement (Highest ROI)

**Goal:** Make correct behavior unavoidable at commit time.

**Tasks:**
- [ ] Extend `git_add_or_commit` with branch protection: deny commits on `main`/`master`.
- [ ] Add phase-aware gating logic (RED/GREEN/REFACTOR).
- [ ] Add a minimal configuration surface (thresholds, branch names, required artifacts).

**Exit Criteria:**
- [ ] Tool refuses commit on `main`.
- [ ] GREEN requires passing tests.
- [ ] REFACTOR requires passing tests + quality gates.

#### Phase 2: SafeEditTool Profiles (Issue #20)

**Goal:** Make SafeEditTool usable in rapid iteration without losing safety.

**Tasks:**
- [ ] Add `validation_profile` parameter (FAST/CRITICAL/FULL).
- [ ] Implement `FAST` profile “cheap formatting gate” for Python:
    - final newline
    - no trailing whitespace
    - max line length 100
- [ ] Implement “new-findings-only” blocking for strict mode (or “critical-only”).
- [ ] Add short-circuit rules (no-op edits, whitespace-only changes).

**Exit Criteria:**
- [ ] FAST profile is meaningfully faster than FULL.
- [ ] Strict mode does not force fixing unrelated legacy issues (when configured).

#### Phase 3: PR/Close Artifact Gates (Issue #14)

**Goal:** Ensure consistent paper trail for completed work.

**Tasks:**
- [ ] `create_pr` gate: require GREEN (tests pass) + required artifacts exist.
- [ ] `close_issue` gate: require artifacts + post summary comment with links.

**Exit Criteria:**
- [ ] Tool refuses PR/close when artifacts are missing.

### 4.2 Testing Strategy

| Test Type | Scope | Target |
|-----------|-------|--------|
| Unit | Policy Engine decisions | Cover all phase/operation combinations |
| Unit | SafeEditTool profiles | FAST vs FULL vs CRITICAL behavior |
| Unit | Commit gate | branch protection + phase gating |
| Integration | Tool flows | smoke tests for safe_edit → commit → PR |

---

## 5. Alternatives Considered

### Alternative A

**Description:** Enforce everything only via SafeEditTool (block all edits that violate standards).

**Pros:**
- Centralized.

**Cons:**
- Poor UX during refactors (latency, forces unrelated fixes).
- Does not cover manual edits (humans can bypass tool).

**Decision:** Rejected. Enforcement must live at commit/PR/close choke points.

### Alternative B

**Description:** Enforce only in CI.

**Pros:**
- Strong and centralized.

**Cons:**
- Feedback is too late; agents still thrash locally.

**Decision:** Rejected as sole mechanism; acceptable as additional layer.

### Alternative C

**Description:** Git hooks.

**Pros:**
- Runs locally, unavoidable if installed.

**Cons:**
- Harder to standardize cross-platform, and agents can bypass.

**Decision:** Not primary; tooling-based choke points are preferred.

---

## 6. Open Questions

- [ ] Where should phase state live: explicit tool parameter, or a repo-backed state (e.g., `.st3/phase.json`)?
- [ ] How do we reliably detect a “RED commit” (intentionally failing tests) without false positives?
- [ ] Coverage enforcement strategy: changed-files only vs package thresholds.
- [ ] Required artifact paths: do we standardize locations per issue/feature branch?

---

## 7. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-21 | Enforce via choke points | Commit/PR/close is unavoidable |
| 2025-12-21 | Add SafeEditTool profiles | Fast iteration without losing safety |

---

## 8. References

- [Coding Standards](../../coding_standards/README.md)
- [Quality Gates](../../coding_standards/QUALITY_GATES.md)
- [Agent Protocol](../../../agent.md)

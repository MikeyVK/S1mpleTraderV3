# MCP Server - Phase Workflows

> **Document Version**: 2.0
> **Last Updated**: 2025-12-08
> **Parent**: [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Development Phases](#2-development-phases)
3. [Phase 0: Discovery](#3-phase-0-discovery)
4. [Phase 1: Planning](#4-phase-1-planning)
5. [Phase 2: Architectural Design](#5-phase-2-architectural-design)
6. [Phase 3: Component Design](#6-phase-3-component-design)
7. [Phase 4: TDD Implementation](#7-phase-4-tdd-implementation)
8. [Phase 5: Integration](#8-phase-5-integration)
9. [Phase 6: Documentation](#9-phase-6-documentation)
10. [MCP Tool Mapping](#10-mcp-tool-mapping)
11. [Workflow Automation](#11-workflow-automation)

---

## 1. Overview

This document defines the 7 development phases that ST3 follows, including entry/exit criteria, GitHub workflow integration, and which MCP tools are used per phase.

### 1.1 Design Principles

```
┌─────────────────────────────────────────────────────────────────────┐
│  Documentation-Driven Development (DDD) meets Test-Driven (TDD)    │
├─────────────────────────────────────────────────────────────────────┤
│  1. Design before code                                              │
│  2. Tests before implementation                                     │
│  3. Documentation as first-class artifact                          │
│  4. GitHub Issues as single source of truth                        │
│  5. MCP automates the ceremony, not the decisions                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.2 Phase Flow Diagram

```
┌─────────────┐    ┌─────────────┐    ┌─────────────────┐
│  Discovery  │───▶│  Planning   │───▶│  Architectural  │
│   Phase 0   │    │   Phase 1   │    │    Phase 2      │
└─────────────┘    └─────────────┘    └────────┬────────┘
                                               │
┌─────────────┐    ┌─────────────┐    ┌────────▼────────┐
│Documentation│◀───│ Integration │◀───│   Component     │
│   Phase 6   │    │   Phase 5   │    │    Phase 3      │
└─────────────┘    └─────────────┘    └────────┬────────┘
                                               │
                                      ┌────────▼────────┐
                                      │ TDD Implement.  │
                                      │    Phase 4      │
                                      │  RED→GREEN→     │
                                      │   REFACTOR      │
                                      └─────────────────┘
```

---

## 2. Development Phases

### 2.1 Phase Summary Table

| Phase | Name | Purpose | GitHub Issue Template | Key MCP Tools |
|-------|------|---------|----------------------|---------------|
| 0 | Discovery | Problem exploration | `type:discussion` | `search_documentation` |
| 1 | Planning | Work breakdown | `type:feature` | `create_issue` |
| 2 | Architectural | System design | Architecture Design | `validate_document_structure` |
| 3 | Component | Detailed design | Component Design | `validate_document_structure` |
| 4 | TDD | Implementation | TDD Task | `run_quality_gates`, `run_tests` |
| 5 | Integration | Wiring & testing | TDD Task | `test_integration_run` |
| 6 | Documentation | Reference docs | Reference Documentation | `scaffold_document` |

### 2.2 Label Transitions

```yaml
# Each phase maps to a GitHub label that tracks progress
phase_transitions:
  discovery:    "phase:discovery"   → "phase:discussion"
  planning:     "phase:discussion"  → "phase:design"
  architecture: "phase:design"      → "phase:review"
  component:    "phase:review"      → "phase:approved"
  tdd:          "phase:red" → "phase:green" → "phase:refactor"
  integration:  "phase:refactor"    → "phase:review"
  documentation: "phase:documentation" → "phase:done"
```

---

## 3. Phase 0: Discovery

### 3.1 Purpose

Exploration of a problem, requirement, or idea. No commitments, just building understanding.

### 3.2 Entry Criteria

- [ ] A problem, question, or feature idea exists
- [ ] Sufficient context to start a discussion

### 3.3 Activities

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Create Discussion | Open GitHub Issue with `type:discussion` | `create_issue` |
| Explore Codebase | Understand existing structure | `search_documentation` |
| Guidelines Check | Research patterns and standards | `st3://rules/coding_standards` |

### 3.4 Exit Criteria

- [ ] Problem statement is clearly defined
- [ ] Scope is determined (in/out)
- [ ] Decision: proceed to Planning or abandon
- [ ] Issue label updated to `phase:discussion`

---

## 4. Phase 1: Planning

### 4.1 Purpose

Work breakdown and resource planning. From idea to actionable items.

### 4.2 Entry Criteria

- [ ] Discovery phase completed
- [ ] Problem statement approved
- [ ] High-level approach determined

### 4.3 Activities

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Create Feature Issue | Main issue with acceptance criteria | `create_issue` |
| Work Breakdown | Split into sub-issues | `create_issue` |
| Assign Milestone | Link to planning | `update_issue` |
| Estimate Effort | T-shirt sizing | Manual (in issue) |

### 4.4 Exit Criteria

- [ ] Feature issue created with clear scope
- [ ] Sub-issues for each discrete work unit
- [ ] Milestone assigned
- [ ] Priority labels added
- [ ] Dependencies identified

---

## 5. Phase 2: Architectural Design

### 5.1 Purpose

System-level design decisions. How do components fit together?

### 5.2 Entry Criteria

- [ ] Planning phase completed
- [ ] Scope clearly defined
- [ ] Relevant stakeholders identified

### 5.3 Activities

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Review Existing Arch | Understand current architecture | `search_documentation` |
| Draft Design | Write architectural design | `scaffold_document` |
| Validate Patterns | Check against ST3 patterns | `check_arch_compliance` |
| Request Review | Assign reviewers | `update_issue` |

### 5.4 Exit Criteria

- [ ] Design document in `docs/architecture/`
- [ ] Mermaid diagrams for key flows
- [ ] Architecture validation passed
- [ ] Review completed and approved
- [ ] Label updated to `phase:approved`

---

## 6. Phase 3: Component Design

### 6.1 Purpose

Detailed design of individual components. Ready for implementation.

### 6.2 Entry Criteria

- [ ] Architectural design approved
- [ ] Component scope clear
- [ ] Interface contracts defined

### 6.3 Activities

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Design DTOs | Define data contracts | `validate_dto` |
| Design Interfaces | Protocol definitions | Manual |
| Plan Tests | Identify test scenarios | Manual |
| Validate Naming | Check naming conventions | `check_arch_compliance` |
| Document Behavior | Expected behavior spec | Issue description |

### 6.4 Exit Criteria

- [ ] DTO schemas defined and validated
- [ ] Interface/ABC documented
- [ ] Test scenarios identified
- [ ] File locations determined
- [ ] Review completed and approved
- [ ] Ready for TDD RED phase

---

## 7. Phase 4: TDD Implementation

### 7.1 Purpose

Implementation via strict TDD: RED → GREEN → REFACTOR.

### 7.2 Entry Criteria

- [ ] Component design approved
- [ ] Test scenarios defined
- [ ] DTOs and interfaces established
- [ ] Feature branch created

### 7.3 Sub-Phase: RED

**Goal**: Write failing tests that define expected behavior.

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Create Test File | In correct location | `scaffold_component` |
| Write Test Cases | Based on scenarios | Manual + AI assist |
| Run Tests | Verify they fail | `run_tests` |

### 7.4 Sub-Phase: GREEN

**Goal**: Minimal implementation to make tests pass.

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Create Source File | In correct location | `scaffold_component` |
| Implement Minimal | Just enough to pass | Manual + AI assist |
| Run Tests | Verify they pass | `run_tests` |

### 7.5 Sub-Phase: REFACTOR

**Goal**: Improve code quality without changing behavior.

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Code Review | Self-review for smells | Manual |
| Run Quality Checks | Pyright, lint | `run_quality_gates` |
| Run Tests | Verify still passing | `run_tests` |
| Commit | With conventional message | `git_commit` |

### 7.6 Exit Criteria

- [ ] All tests passing
- [ ] Coverage ≥ 80%
- [ ] Pyright clean (0 errors)
- [ ] Code committed with conventional message
- [ ] Ready for integration

---

## 8. Phase 5: Integration

### 8.1 Purpose

Wire component into system, run integration tests.

### 8.2 Entry Criteria

- [ ] TDD phase complete
- [ ] Unit tests passing
- [ ] Component isolated and tested

### 8.3 Activities

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Wire Component | Connect to system | Manual |
| Run Int. Tests | Verify integration | `run_tests` |
| Create PR | Open pull request | `create_issue` (PR is issue type in GitHub) |

### 8.4 Exit Criteria

- [ ] Integration tests passing
- [ ] PR created with proper template
- [ ] PR review approved
- [ ] All CI checks green
- [ ] Ready for merge

---

## 9. Phase 6: Documentation

### 9.1 Purpose

Create/update reference documentation after implementation.

### 9.2 Entry Criteria

- [ ] PR merged to main
- [ ] Feature complete and stable
- [ ] API/behavior finalized

### 9.3 Activities

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Identify Doc Gaps | What needs documenting | `st3://docs/inventory` |
| Write Reference | API docs, guides | `scaffold_document` |
| Update Existing | Keep docs in sync | Manual |
| Close Issue | Mark as done | `update_issue` |

### 9.4 Exit Criteria

- [ ] New public APIs documented
- [ ] Existing docs updated if changed
- [ ] Issue closed with documentation link
- [ ] Label set to `phase:done`

---

## 10. Workflow Automation

### 10.1 GitHub Actions Integration

Automations run on GitHub to enforce phases:

- **Labeler**: Applies labels based on changed files.
- **Release Drafter**: Drafts release notes based on labels.
- **CI/CD**: Runs tests and quality gates on every push.

### 10.2 MCP Integration

The MCP server supports this workflow by:
1. Providing context (`get_work_context`)
2. Enforcing rules (`run_quality_gates`)
3. Scaffolding compliant files (`scaffold_document`)
4. Managing GitHub state (`update_issue`)

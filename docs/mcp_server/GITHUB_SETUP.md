# ST3 Workflow MCP Server - GitHub Configuration

**Status:** DRAFT
**Version:** 2.0
**Last Updated:** 2025-12-08

---

## 1. Overview

This document specifies the mandatory GitHub configuration required to support the ST3 Workflow MCP Server. The server's tools (e.g., `create_issue`, `start_work_on_issue`) rely on the existence of specific labels, project structures, and branch protection rules defined here.

---

## 2. Global Repository Settings

### 2.1 General
- **Default Branch:** `main`
- **Features:**
  - [x] Issues
  - [x] Projects
  - [ ] Wiki (Documentation is in-repo `docs/`)
  - [ ] Discussions (Communication is via Issues/PRs)

### 2.2 Branch Protection Rules (`main`)
These rules enforce the Quality Gates defined in `QUALITY_GATES.md`.

- **Require a pull request before merging:**
  - [x] Require approvals: 0 (Solo dev, but PR flow enforced) or 1 (if pairing)
  - [x] Dismiss stale pull request approvals when new commits are pushed
- **Require status checks to pass before merging:**
  - `test (3.11)` (CI - returns pass/fail from pytest)
  - `lint` (CI - returns pass/fail from pylint/mypy)
  - `check-title` (Semantic PR title check)
- **Require conversation resolution before merging:** [x]
- **Require linear history:** [x] (Rebase or Squash merge only)
- **Include administrators:** [x] (Rules apply to everyone)

---

## 3. Project V2 Configuration

The MCP Server uses the **Project V2** API to track sprint progress and velocity.

**Project Name:** `S1mpleTraderV3 Development`

### 3.1 Custom Fields

| Field Name | Type | Options / Format | Usage |
|------------|------|------------------|-------|
| **Status** | Single Select | `Backlog`, `Todo`, `In Progress`, `In Review`, `Done` | Workflow stage tracking |
| **Priority** | Single Select | `🔴 Critical`, `🟠 High`, `🟡 Medium`, `🟢 Low` | Sorting/Filtering |
| **Size** | Number | Fibonacci (1, 2, 3, 5, 8, 13) | Story points for velocity |
| **Layer** | Single Select | `Strategy`, `Execution`, `Data`, `Infra`, `Docs` | Component categorization |
| **Sprint** | Iteration | 2-week intervals | Time-boxing |

### 3.2 Views

1.  **Sprint Board** (Kanban)
    -   *Filter:* `Sprint: @current`
    -   *Columns:* Status
    -   *Swimlanes:* Priority
2.  **Backlog Refinement** (Table)
    -   *Filter:* `Status: Backlog`, `Sprint: <empty>`
    -   *Sort:* Priority (desc)
3.  **Roadmap** (Timeline)
    -   *Group by:* Milestone
    -   *Markers:* Sprint

---

## 4. Label Taxonomy

Labels are critical for the `read_task_context` and `search_issues` tools. They are grouped by color and prefix to act as metadata tags.

### 4.1 Type (`#1D76DB` - Blue)
Describes the clear intent of the work (matches Git commit types).

- `type:feature`: New functionality
- `type:bug`: Fix for broken functionality
- `type:refactor`: Code change that neither fixes a bug nor adds a feature
- `type:docs`: Documentation only changes
- `type:infra`: CI/CD, scripts, or tooling
- `type:test`: Adding missing tests or correcting existing ones
- `type:design`: Architectural or component design work
- `type:discussion`: explorative discussions
- `type:tech-debt`: Recognized technical debt to be addressed
- `type:validation`: Validation tasks

### 4.2 Priority (`#B60205` - Red Scale)
Determines order of execution.

- `priority:critical`: Blocks development or production issue (SLA: Immediate)
- `priority:high`: Must be in current sprint
- `priority:medium`: Can wait for next sprint
- `priority:low`: Nice to have
- `priority:triage`: Needs prioritization

### 4.3 Phase (`#0E8A16` - Green)
Aligns with MCP Server `st3://status/phase` and `PHASE_WORKFLOWS.md`.

- `phase:discovery`: Problem exploration
- `phase:discussion`: Active discussion
- `phase:planning`: Work breakdown
- `phase:design`: Solution design
- `phase:review`: Design/Code review
- `phase:approved`: Design approved
- `phase:red`: TDD failing test
- `phase:green`: TDD passing test
- `phase:refactor`: TDD refactoring
- `phase:implementation`: General coding (fallback)
- `phase:verification`: QA, manual testing
- `phase:documentation`: Finalizing docs
- `phase:done`: Completed

### 4.4 Status (`#FBCA04` - Yellow)
Automated bot triggers or blocked states.

- `status:blocked`: Cannot proceed (needs `blocked-by` comment)
- `status:needs-info`: Waiting on user input
- `status:ready-for-review`: PR open and checks passed
- `needs:discussion`: Requires team input
- `scope:architecture`: Affects system design
- `scope:component`: Affects single component

---

## 5. Milestone Strategy

Milestones organize issues into logical high-level deliverables, distinct from Sprints (iterations).

**Convention:** `Phase <Letter>: <Name>`

**Examples:**
- `Phase E: MCP Server Design`
- `Phase F: GitHub Configuration`
- `Phase G: Implementation Plan`
- `v3.1.0: Strategy Engine Core`

**Usage:**
- Issues MUST belong to a Milestone.
- Pull Requests inherit the Milestone from the linked Issue.

---

## 6. Issue Templates

To ensure the MCP Server has structured input, issue templates are mandatory.

*[Note: Full YAML content for templates is maintained in `.github/ISSUE_TEMPLATE/`]*

### 6.1 List of Templates

1. **Feature Request**: `feature_request.yml`
2. **Bug Report**: `bug_report.yml`
3. **Design Discussion**: `design_discussion.yml`
4. **Discussion / Brainstorm**: `discussion.yml`
5. **Architecture Design**: `architecture_design.yml`
6. **Component Design**: `component_design.yml`
7. **Design Validation**: `design_validation.yml`
8. **Reference Documentation**: `reference_documentation.yml`
9. **Technical Debt**: `tech_debt.yml`

### 6.2 Template Structure Principle

All templates follow this structure to support AI parsing:
1. **Summary/Context**: Machine-readable context
2. **Acceptance Criteria**: Checkbox list (the "Definition of Done")
3. **Constraints**: Limits or requirements
4. **Labels**: Pre-filled `type:*` and `phase:*` labels

---

## 7. Automation & Workflows

### 7.1 Auto-Labeling (`.github/workflows/labeler.yml`)
Automatically applies `layer:*` labels based on paths changed in PRs.

```yaml
# Configuration in .github/labeler.yml
layer:strategy:
  - changed-files:
    - any-glob-to-any-file: 'backend/strategies/**'
    - any-glob-to-any-file: 'backend/dtos/strategy/**'

layer:docs:
  - changed-files:
    - any-glob-to-any-file: 'docs/**'
    - any-glob-to-any-file: '**/*.md'
```

### 7.2 Release Drafter (`.github/workflows/release-drafter.yml`)
Drafts release notes based on merged PR labels.

```yaml
template: |
  ## Change Log
  $CHANGES
categories:
  - title: '🚀 Features'
    labels:
      - 'type:feature'
  - title: '🐛 Bug Fixes'
    labels:
      - 'type:bug'
  - title: '🧰 Maintenance'
    labels:
      - 'type:refactor'
      - 'type:infra'
```

---

## 8. Alignment with MCP Tools

| MCP Tool | GitHub Config Dependency | Impact if Missing |
|----------|--------------------------|-------------------|
| `create_issue` | Labels, Issue Template structure | Tool may fail or create unstructured spam |
| `start_work_on_issue` | Branch Protection, Labels | Branch might not be linkable; PR might bypass Check |
| `st3://github/project` | Project V2 Custom Fields | Velocity/Burn-down metrics will be empty |
| `st3://status/phase` | Milestones | `current_phase` derivation will fail |
| `submit_pr` | PR Template, Branch Protection | Check failure on PR creation |

---

## 9. Setup Checklist

1. [ ] Create Project V2 "S1mpleTraderV3 Development"
2. [ ] Define Custom Fields (Size, Layer, Sprint)
3. [ ] Delete default labels & run `gh label create` script (to be created)
4. [ ] Configure Branch Protection on `main`
5. [ ] Commit `.github/ISSUE_TEMPLATE/*.yml`
6. [ ] Commit `.github/workflows/*.yml`

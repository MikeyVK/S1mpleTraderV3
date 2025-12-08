# MCP Server - Phase Workflows

> **Document Version**: 1.0  
> **Last Updated**: 2025-01-21  
> **Status**: Design Phase  
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

Dit document definieert de 7 development phases die ST3 volgt, inclusief entry/exit criteria, GitHub workflow integratie, en welke MCP tools per fase worden ingezet.

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
| 0 | Discovery | Problem exploration | `type:discussion` | `project_analyze_structure` |
| 1 | Planning | Work breakdown | `type:feature` | `issue_create`, `issue_link` |
| 2 | Architectural | System design | Architecture Design | `architecture_validate` |
| 3 | Component | Detailed design | Component Design | `dto_validate` |
| 4 | TDD | Implementation | TDD Task | `test_*`, `code_*` |
| 5 | Integration | Wiring & testing | TDD Task | `test_integration_run` |
| 6 | Documentation | Reference docs | Reference Documentation | `docs_*` |

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

Exploratie van een probleem, requirement, of idee. Geen commitments, alleen begrip bouwen.

### 3.2 Entry Criteria

- [ ] Een probleem, vraag, of feature idee bestaat
- [ ] Voldoende context om een discussion te starten

### 3.3 Activities

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Create Discussion | Open GitHub Issue met `type:discussion` | `issue_create` |
| Explore Codebase | Begrijp bestaande structuur | `project_analyze_structure` |
| Gather Requirements | Leg requirements vast in issue comments | `issue_add_comment` |
| Research | Onderzoek bestaande patterns, docs | `resource:coding-standards` |

### 3.4 Exit Criteria

- [ ] Problem statement is duidelijk gedefinieerd
- [ ] Scope is bepaald (wat wel/niet)
- [ ] Decision: proceed to Planning of abandon
- [ ] Issue label updated naar `phase:discussion`

### 3.5 GitHub Workflow

```yaml
# Issue created with template: Discussion/Brainstorm
labels:
  - type:discussion
  - phase:discovery
  
# On completion, add:
labels:
  - phase:discussion  # replaces phase:discovery
  
# Link to new Planning issue when proceeding
```

### 3.6 MCP Commands

```python
# Start discovery phase
await mcp.call_tool("issue_create", {
    "title": "Discussion: [topic]",
    "template": "discussion",
    "labels": ["type:discussion", "phase:discovery"]
})

# Analyze project structure for context
context = await mcp.read_resource("project://structure")
```

---

## 4. Phase 1: Planning

### 4.1 Purpose

Work breakdown en resource planning. Van idee naar actionable items.

### 4.2 Entry Criteria

- [ ] Discovery fase afgerond
- [ ] Problem statement goedgekeurd
- [ ] High-level approach bepaald

### 4.3 Activities

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Create Feature Issue | Hoofdissue met acceptatiecriteria | `issue_create` |
| Work Breakdown | Split in sub-issues | `issue_create` + `issue_link` |
| Assign Milestone | Koppel aan planning | `milestone_assign` |
| Estimate Effort | T-shirt sizing | Manual (in issue) |
| Identify Dependencies | Link related issues | `issue_link` |

### 4.4 Exit Criteria

- [ ] Feature issue aangemaakt met duidelijke scope
- [ ] Sub-issues voor elke discrete work unit
- [ ] Milestone assigned
- [ ] Priority labels toegevoegd
- [ ] Dependencies geïdentificeerd en gelinkt

### 4.5 GitHub Workflow

```yaml
# Create parent feature issue
- template: feature_request.yml
- labels: [type:feature, priority:*, scope:*]
- milestone: vX.Y.Z

# Create child issues (linked)
- template: varies by work type
- labels: [phase:design OR phase:red]
- parent: feature issue (via tasklist)

# Project board automation
- Add to "To Do" column when created
- Move to "In Progress" when assigned
```

### 4.6 MCP Commands

```python
# Create feature with work breakdown
feature = await mcp.call_tool("issue_create", {
    "title": "Feature: [name]",
    "template": "feature_request",
    "milestone": "v0.1.0",
    "labels": ["type:feature", "priority:high"]
})

# Create linked design task
design = await mcp.call_tool("issue_create", {
    "title": "Design: [component]",
    "template": "architecture_design",
    "labels": ["type:design", "phase:design"]
})

await mcp.call_tool("issue_link", {
    "parent_issue": feature["number"],
    "child_issue": design["number"],
    "link_type": "subtask"
})
```

---

## 5. Phase 2: Architectural Design

### 5.1 Purpose

System-level design beslissingen. Hoe passen componenten samen?

### 5.2 Entry Criteria

- [ ] Planning fase afgerond
- [ ] Scope duidelijk gedefinieerd
- [ ] Relevante stakeholders identified

### 5.3 Activities

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Review Existing Arch | Begrijp huidige architectuur | `resource:architecture` |
| Draft Design | Schrijf architectural design | Manual + AI assist |
| Validate Patterns | Check tegen ST3 patterns | `architecture_validate` |
| Create ADR | Document decision rationale | `docs_create_adr` |
| Request Review | Assign reviewers | `issue_assign_reviewer` |

### 5.4 Design Artifacts

```yaml
required_artifacts:
  - component_diagram: "Mermaid diagram in issue description"
  - data_flow: "Beschrijving van data flow"
  - integration_points: "Hoe integreert met bestaande systeem"
  - anti_patterns_avoided: "Expliciete check tegen anti-patterns"
  
optional_artifacts:
  - adr: "Architecture Decision Record in docs/"
  - sequence_diagram: "Voor complexe flows"
  - interface_contracts: "DTO definitions"
```

### 5.5 Exit Criteria

- [ ] Design document in issue beschreven
- [ ] Mermaid diagrams voor key flows
- [ ] Architecture validation passed
- [ ] Review completed en approved
- [ ] Label updated naar `phase:approved`

### 5.6 GitHub Workflow

```yaml
# Design issue lifecycle
labels_progression:
  - phase:design      # Writing design
  - phase:review      # Awaiting review
  - phase:approved    # Ready for component design

# Reviewers checklist in template:
- [ ] Follows CORE_PRINCIPLES.md
- [ ] No circular dependencies
- [ ] Clear separation of concerns
- [ ] DTOs properly scoped
- [ ] Event-driven where appropriate
```

### 5.7 MCP Commands

```python
# Load architecture context
arch = await mcp.read_resource("standards://architecture")
patterns = await mcp.read_resource("standards://patterns")

# Validate design against rules
result = await mcp.call_tool("architecture_validate", {
    "design_text": issue_body,
    "check_anti_patterns": True
})

# Create ADR if significant decision
await mcp.call_tool("docs_create", {
    "type": "adr",
    "title": "ADR-XXX: [Decision Title]",
    "content": adr_content
})
```

---

## 6. Phase 3: Component Design

### 6.1 Purpose

Detailed design van individuele componenten. Klaar voor implementatie.

### 6.2 Entry Criteria

- [ ] Architectural design approved
- [ ] Component scope duidelijk
- [ ] Interface contracts gedefinieerd

### 6.3 Activities

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Design DTOs | Define data contracts | `dto_validate` |
| Design Interfaces | ABC/Protocol definitions | Manual |
| Plan Tests | Identify test scenarios | Manual |
| Validate Naming | Check naming conventions | `naming_validate` |
| Document Behavior | Expected behavior spec | Issue description |

### 6.4 Design Artifacts

```yaml
required_artifacts:
  dto_definitions:
    format: "Pydantic v2 class with docstrings"
    validation: "Run through dto_validate"
    
  interface_definition:
    format: "ABC with abstract methods"
    docstrings: "Complete method docs"
    
  test_scenarios:
    format: "Bullet list in issue"
    coverage: "Happy path + edge cases"
    
  file_locations:
    format: "Exact paths where code will live"
    convention: "Per LAYERED_ARCHITECTURE.md"
```

### 6.5 Exit Criteria

- [ ] DTO schemas gedefinieerd en gevalideerd
- [ ] Interface/ABC gedocumenteerd
- [ ] Test scenarios identified
- [ ] File locations bepaald
- [ ] Review completed en approved
- [ ] Ready voor TDD RED phase

### 6.6 GitHub Workflow

```yaml
# Component design validation
validation_checklist:
  - [ ] DTO uses Pydantic v2 BaseModel
  - [ ] Fields have type hints
  - [ ] Optional fields have defaults
  - [ ] Docstrings present
  - [ ] Naming follows conventions
  - [ ] Located in correct layer
```

### 6.7 MCP Commands

```python
# Validate DTO definition
await mcp.call_tool("dto_validate", {
    "dto_code": dto_definition,
    "check_naming": True,
    "check_docstrings": True
})

# Validate naming conventions
await mcp.call_tool("naming_validate", {
    "names": ["MyNewDTO", "process_data", "EventHandler"],
    "types": ["class", "function", "class"]
})

# Update issue with validation results
await mcp.call_tool("issue_add_comment", {
    "issue_number": 42,
    "body": "✅ Component design validation passed"
})
```

---

## 7. Phase 4: TDD Implementation

### 7.1 Purpose

Implementatie via strict TDD: RED → GREEN → REFACTOR.

### 7.2 Entry Criteria

- [ ] Component design approved
- [ ] Test scenarios defined
- [ ] DTOs en interfaces vastgelegd
- [ ] Feature branch created

### 7.3 Sub-Phase: RED

**Goal**: Write failing tests that define expected behavior.

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Create Test File | In correct location | `code_create_file` |
| Write Test Cases | Based on scenarios | Manual + AI assist |
| Run Tests | Verify they fail | `test_run` |
| Validate Structure | Check test conventions | `test_validate_structure` |

```python
# MCP commands for RED phase
await mcp.call_tool("git_branch_create", {
    "name": "feature/42-my-feature",
    "from": "main"
})

await mcp.call_tool("code_create_file", {
    "path": "tests/unit/test_my_component.py",
    "content": test_template
})

result = await mcp.call_tool("test_run", {
    "path": "tests/unit/test_my_component.py",
    "expect_failure": True
})

# Update issue label
await mcp.call_tool("issue_update_labels", {
    "issue_number": 42,
    "add": ["phase:red"],
    "remove": ["phase:approved"]
})
```

### 7.4 Sub-Phase: GREEN

**Goal**: Minimal implementation to make tests pass.

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Create Source File | In correct location | `code_create_file` |
| Implement Minimal | Just enough to pass | Manual + AI assist |
| Run Tests | Verify they pass | `test_run` |
| Check Coverage | Ensure coverage | `test_run` with coverage |

```python
# MCP commands for GREEN phase
await mcp.call_tool("code_create_file", {
    "path": "backend/core/my_component.py",
    "content": implementation
})

result = await mcp.call_tool("test_run", {
    "path": "tests/unit/test_my_component.py",
    "coverage": True
})

# Verify all tests pass
assert result["passed"] == result["total"]

# Update issue label
await mcp.call_tool("issue_update_labels", {
    "issue_number": 42,
    "add": ["phase:green"],
    "remove": ["phase:red"]
})
```

### 7.5 Sub-Phase: REFACTOR

**Goal**: Improve code quality without changing behavior.

| Activity | Description | MCP Tool |
|----------|-------------|----------|
| Code Review | Self-review for smells | Manual |
| Apply Patterns | Use ST3 patterns | Manual + AI assist |
| Run Quality Checks | Pyright, lint | `code_quality_check` |
| Run Tests | Verify still passing | `test_run` |
| Commit | With conventional message | `git_commit` |

```python
# MCP commands for REFACTOR phase
quality = await mcp.call_tool("code_quality_check", {
    "path": "backend/core/my_component.py"
})

# Must pass before committing
assert quality["pyright"]["errors"] == 0
assert quality["coverage"] >= 80

await mcp.call_tool("git_commit", {
    "message": "feat(core): add MyComponent with full test coverage",
    "files": ["backend/core/my_component.py", "tests/unit/test_my_component.py"]
})

# Update issue label
await mcp.call_tool("issue_update_labels", {
    "issue_number": 42,
    "add": ["phase:refactor"],
    "remove": ["phase:green"]
})
```

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
| Write Int. Tests | Test interactions | Manual |
| Run Int. Tests | Verify integration | `test_integration_run` |
| Create PR | Open pull request | `pr_create` |
| Request Review | Assign reviewers | PR template |

### 8.4 Exit Criteria

- [ ] Integration tests passing
- [ ] PR created with proper template
- [ ] PR review approved
- [ ] All CI checks green
- [ ] Ready for merge

### 8.5 MCP Commands

```python
# Run integration tests
result = await mcp.call_tool("test_integration_run", {
    "scope": "affected"  # Only tests affected by changes
})

# Create PR
pr = await mcp.call_tool("pr_create", {
    "title": "feat(core): add MyComponent",
    "body": pr_body,
    "base": "main",
    "head": "feature/42-my-feature",
    "labels": ["type:feature"],
    "milestone": "v0.1.0"
})

# Link PR to issue
await mcp.call_tool("issue_add_comment", {
    "issue_number": 42,
    "body": f"PR #{pr['number']} created for this issue."
})
```

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
| Identify Doc Gaps | What needs documenting | `docs_check_coverage` |
| Write Reference | API docs, guides | Manual + AI assist |
| Update Existing | Keep docs in sync | `docs_update` |
| Validate Links | Check for broken links | `docs_validate_links` |
| Close Issue | Mark as done | `issue_close` |

### 9.4 Documentation Types

```yaml
reference_documentation:
  - api_docs: "Function/class reference"
  - architecture_docs: "System design docs"
  - guides: "How-to guides"
  - adrs: "Architecture Decision Records"

update_triggers:
  - new_public_api: "Requires API docs"
  - behavior_change: "Update existing docs"
  - new_pattern: "Add to patterns guide"
  - breaking_change: "Update migration guide"
```

### 9.5 Exit Criteria

- [ ] New public APIs documented
- [ ] Existing docs updated if changed
- [ ] All doc links valid
- [ ] Issue closed with documentation link
- [ ] Label set to `phase:done`

### 9.6 MCP Commands

```python
# Check documentation coverage
gaps = await mcp.call_tool("docs_check_coverage", {
    "paths": ["backend/core/my_component.py"]
})

# Create documentation issue if gaps found
if gaps["missing"]:
    await mcp.call_tool("issue_create", {
        "title": "Docs: Document MyComponent API",
        "template": "reference_documentation",
        "labels": ["type:docs", "scope:reference"]
    })

# Close implementation issue
await mcp.call_tool("issue_close", {
    "issue_number": 42,
    "comment": "✅ Implemented and documented. See PR #43."
})
```

---

## 10. MCP Tool Mapping

### 10.1 Tools per Phase

```yaml
phase_0_discovery:
  primary:
    - project_analyze_structure
    - issue_create
  resources:
    - project://structure
    - standards://coding-standards
    
phase_1_planning:
  primary:
    - issue_create
    - issue_link
    - milestone_assign
  resources:
    - github://issues
    - github://milestones

phase_2_architecture:
  primary:
    - architecture_validate
    - docs_create (ADR)
  resources:
    - standards://architecture
    - standards://patterns
    
phase_3_component:
  primary:
    - dto_validate
    - naming_validate
  resources:
    - standards://dto-patterns
    - templates://dto

phase_4_tdd:
  primary:
    - git_branch_create
    - code_create_file
    - test_run
    - code_quality_check
    - git_commit
  resources:
    - templates://test
    - templates://implementation

phase_5_integration:
  primary:
    - test_integration_run
    - pr_create
  resources:
    - templates://pr
    - github://pull-requests

phase_6_documentation:
  primary:
    - docs_check_coverage
    - docs_create
    - docs_validate_links
    - issue_close
  resources:
    - docs://reference
    - docs://architecture
```

### 10.2 Automation Matrix

| Tool | Fully Automated | AI Assisted | Manual |
|------|-----------------|-------------|--------|
| `issue_create` | ✅ | - | - |
| `issue_link` | ✅ | - | - |
| `test_run` | ✅ | - | - |
| `git_commit` | ✅ | - | - |
| `architecture_validate` | ✅ | - | - |
| `code_create_file` | - | ✅ | - |
| `pr_create` | - | ✅ | - |
| Design decisions | - | - | ✅ |
| Code review | - | - | ✅ |

---

## 11. Workflow Automation

### 11.1 GitHub Actions Integration

```yaml
# .github/workflows/phase-automation.yml
name: Phase Automation

on:
  issues:
    types: [labeled]

jobs:
  phase-transition:
    runs-on: ubuntu-latest
    steps:
      - name: Handle phase:red
        if: contains(github.event.label.name, 'phase:red')
        run: |
          # Notify that TDD RED phase started
          # Could trigger branch creation
          
      - name: Handle phase:green
        if: contains(github.event.label.name, 'phase:green')
        run: |
          # Verify tests pass before allowing this label
          
      - name: Handle phase:done
        if: contains(github.event.label.name, 'phase:done')
        run: |
          # Close issue, update project board
```

### 11.2 MCP Server Hooks

```python
# MCP server can subscribe to phase transitions
@mcp.on_resource_change("github://issues")
async def handle_issue_change(change: ResourceChange):
    """React to issue label changes."""
    if "phase:red" in change.labels_added:
        # Suggest creating feature branch
        await suggest_branch_creation(change.issue_number)
    
    elif "phase:green" in change.labels_added:
        # Verify tests pass
        test_result = await run_tests_for_issue(change.issue_number)
        if not test_result.all_passed:
            await remove_label(change.issue_number, "phase:green")
            await add_comment("Tests must pass before GREEN phase")
```

### 11.3 Workflow Triggers

```yaml
# MCP can trigger workflows based on project state
triggers:
  - condition: "issue.labels contains 'phase:approved'"
    action: "suggest_tdd_start"
    
  - condition: "pr.checks.all_passed AND pr.reviews.approved"
    action: "suggest_merge"
    
  - condition: "pr.merged AND issue.labels contains 'type:feature'"
    action: "suggest_documentation"
```

---

## Appendix A: Quick Reference

### A.1 Phase Checklist Summary

```
□ DISCOVERY
  □ Problem statement defined
  □ Scope determined
  □ Decision to proceed

□ PLANNING
  □ Feature issue created
  □ Sub-issues created
  □ Milestone assigned
  □ Dependencies linked

□ ARCHITECTURE
  □ Design documented
  □ Diagrams created
  □ Validation passed
  □ Review approved

□ COMPONENT
  □ DTOs defined
  □ Interface documented
  □ Test scenarios listed
  □ File locations planned

□ TDD
  □ RED: Failing tests written
  □ GREEN: Tests passing
  □ REFACTOR: Quality improved
  □ Committed

□ INTEGRATION
  □ Wired into system
  □ Integration tests passing
  □ PR created and approved
  □ Merged

□ DOCUMENTATION
  □ API documented
  □ Existing docs updated
  □ Links validated
  □ Issue closed
```

### A.2 Label Quick Reference

| Phase | Entry Label | Exit Label |
|-------|-------------|------------|
| Discovery | `phase:discovery` | `phase:discussion` |
| Planning | `phase:discussion` | `phase:design` |
| Architecture | `phase:design` | `phase:approved` |
| Component | `phase:design` | `phase:approved` |
| TDD-Red | `phase:red` | `phase:green` |
| TDD-Green | `phase:green` | `phase:refactor` |
| TDD-Refactor | `phase:refactor` | PR created |
| Integration | PR review | PR merged |
| Documentation | `phase:documentation` | `phase:done` |

---

*This document is part of the ST3 MCP Server Design Documentation.*

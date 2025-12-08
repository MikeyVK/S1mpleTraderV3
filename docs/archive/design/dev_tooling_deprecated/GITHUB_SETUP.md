# docs/dev_tooling/GITHUB_SETUP.md
# ST3 Workflow MCP Server - GitHub Setup

**Status:** PRELIMINARY  
**Version:** 1.0  
**Created:** 2025-12-08  
**Last Updated:** 2025-12-08  

---

## Purpose

Complete GitHub configuration for the ST3 project, including issue templates, PR templates, labels, milestones, project board setup, and branch protection rules. All configurations are designed to integrate with the MCP server automation.

---

## 1. Issue Templates

Create these files in `.github/ISSUE_TEMPLATE/` directory.

### 1.1 Feature Request

```yaml
# .github/ISSUE_TEMPLATE/feature_request.yml
name: "🚀 Feature Request"
description: "Request a new feature or enhancement"
title: "[Feature]: "
labels: ["type:feature", "phase:discovery"]
body:
  - type: markdown
    attributes:
      value: |
        ## Feature Request
        Thank you for suggesting a new feature! Please fill out the sections below.

  - type: input
    id: summary
    attributes:
      label: Summary
      description: "One-line description of the feature"
      placeholder: "Implement Signal DTO with confidence field"
    validations:
      required: true

  - type: textarea
    id: motivation
    attributes:
      label: Motivation
      description: "Why is this feature needed? What problem does it solve?"
      placeholder: |
        - Current limitation: ...
        - Use case: ...
        - Expected benefit: ...
    validations:
      required: true

  - type: textarea
    id: proposed_solution
    attributes:
      label: Proposed Solution
      description: "Describe the solution you'd like"
      placeholder: |
        - Create DTO with fields: ...
        - Add validation for: ...
        - Integrate with: ...
    validations:
      required: true

  - type: dropdown
    id: component
    attributes:
      label: Component
      description: "Which component does this affect?"
      options:
        - "DTOs (backend/dtos/)"
        - "Core (backend/core/)"
        - "Workers (plugins/)"
        - "Platform (backend/platform/)"
        - "Tests (tests/)"
        - "Documentation (docs/)"
        - "Configuration"
        - "Other"
    validations:
      required: true

  - type: textarea
    id: acceptance_criteria
    attributes:
      label: Acceptance Criteria
      description: "What must be true for this feature to be complete?"
      placeholder: |
        - [ ] DTO created with all required fields
        - [ ] Validation rules implemented
        - [ ] 20+ tests passing
        - [ ] All quality gates 10/10
        - [ ] Documentation updated
    validations:
      required: true

  - type: textarea
    id: additional_context
    attributes:
      label: Additional Context
      description: "Any other context, mockups, or references"
      placeholder: "Related issues, architecture docs, examples..."
    validations:
      required: false
```

### 1.2 Bug Report

```yaml
# .github/ISSUE_TEMPLATE/bug_report.yml
name: "🐛 Bug Report"
description: "Report a bug or unexpected behavior"
title: "[Bug]: "
labels: ["type:bug", "priority:triage"]
body:
  - type: markdown
    attributes:
      value: |
        ## Bug Report
        Please provide as much detail as possible to help reproduce and fix the issue.

  - type: input
    id: summary
    attributes:
      label: Summary
      description: "Brief description of the bug"
      placeholder: "Signal DTO validation fails for valid confidence values"
    validations:
      required: true

  - type: textarea
    id: steps_to_reproduce
    attributes:
      label: Steps to Reproduce
      description: "Detailed steps to reproduce the behavior"
      placeholder: |
        1. Create Signal DTO with confidence=0.5
        2. Call validate()
        3. Observe error: ...
    validations:
      required: true

  - type: textarea
    id: expected_behavior
    attributes:
      label: Expected Behavior
      description: "What should happen?"
    validations:
      required: true

  - type: textarea
    id: actual_behavior
    attributes:
      label: Actual Behavior
      description: "What actually happens?"
    validations:
      required: true

  - type: textarea
    id: error_output
    attributes:
      label: Error Output
      description: "Paste any error messages, stack traces, or logs"
      render: shell
    validations:
      required: false

  - type: dropdown
    id: severity
    attributes:
      label: Severity
      options:
        - "Critical (blocks all work)"
        - "High (blocks feature)"
        - "Medium (workaround exists)"
        - "Low (cosmetic/minor)"
    validations:
      required: true

  - type: input
    id: version
    attributes:
      label: Version/Commit
      description: "Git commit hash or version"
      placeholder: "abc123d or v3.0.0"
    validations:
      required: false
```

### 1.3 Design Discussion

```yaml
# .github/ISSUE_TEMPLATE/design_discussion.yml
name: "📐 Design Discussion"
description: "Propose or discuss an architectural decision"
title: "[Design]: "
labels: ["type:design", "needs:discussion"]
body:
  - type: markdown
    attributes:
      value: |
        ## Design Discussion
        Use this template for architectural decisions that need discussion before implementation.

  - type: input
    id: summary
    attributes:
      label: Summary
      description: "One-line description of the design decision"
      placeholder: "StrategyCache singleton vs dependency injection"
    validations:
      required: true

  - type: textarea
    id: context
    attributes:
      label: Context
      description: "Background and why this decision is needed now"
      placeholder: |
        - Current state: ...
        - Problem: ...
        - Trigger: ...
    validations:
      required: true

  - type: textarea
    id: options
    attributes:
      label: Options Considered
      description: "List the options with pros/cons"
      placeholder: |
        **Option A: Singleton**
        - ✅ Pro: Simple access
        - ❌ Con: Hard to test
        
        **Option B: Dependency Injection**
        - ✅ Pro: Testable
        - ❌ Con: More boilerplate
    validations:
      required: true

  - type: textarea
    id: recommendation
    attributes:
      label: Recommendation
      description: "Your recommended option and reasoning"
    validations:
      required: false

  - type: textarea
    id: impact
    attributes:
      label: Impact Analysis
      description: "What existing code/docs need to change?"
      placeholder: |
        - Files affected: ...
        - Breaking changes: ...
        - Migration needed: ...
    validations:
      required: false

  - type: checkboxes
    id: checklist
    attributes:
      label: Pre-Implementation Checklist
      options:
        - label: "Reviewed against CORE_PRINCIPLES.md"
        - label: "Checked for conflicts with ARCHITECTURAL_SHIFTS.md"
        - label: "Discussed with team (if applicable)"
```

### 1.4 Discussion / Brainstorm

```yaml
# .github/ISSUE_TEMPLATE/discussion.yml
name: "💬 Discussion / Brainstorm"
description: "Open-ended discussion or brainstorming session"
title: "[Discussion]: "
labels: ["type:discussion", "phase:discovery"]
body:
  - type: markdown
    attributes:
      value: |
        ## Discussion / Brainstorm
        Use this for exploratory discussions before formal design.

  - type: input
    id: topic
    attributes:
      label: Topic
      description: "What do you want to discuss?"
      placeholder: "How should we handle multi-strategy execution?"
    validations:
      required: true

  - type: textarea
    id: context
    attributes:
      label: Context & Background
      description: "What prompted this discussion?"
      placeholder: |
        - Current situation: ...
        - Questions to explore: ...
        - Related concepts: ...
    validations:
      required: true

  - type: textarea
    id: initial_thoughts
    attributes:
      label: Initial Thoughts
      description: "Your preliminary ideas (optional)"
      placeholder: |
        Some initial directions to consider:
        1. ...
        2. ...
    validations:
      required: false

  - type: textarea
    id: questions
    attributes:
      label: Open Questions
      description: "What needs to be answered?"
      placeholder: |
        - [ ] Question 1?
        - [ ] Question 2?
    validations:
      required: true

  - type: dropdown
    id: outcome_type
    attributes:
      label: Expected Outcome
      description: "What should this discussion produce?"
      options:
        - "Architecture Design document"
        - "Component Design document"
        - "Decision record (ADR)"
        - "Feature request(s)"
        - "No document needed (just alignment)"
    validations:
      required: true

  - type: textarea
    id: participants
    attributes:
      label: Stakeholders / Expertise Needed
      description: "Who should be involved in this discussion?"
      placeholder: "@username or expertise areas"
    validations:
      required: false
```

### 1.5 Architecture Design

```yaml
# .github/ISSUE_TEMPLATE/architecture_design.yml
name: "🏛️ Architecture Design"
description: "Create or update system-level architecture documentation"
title: "[Arch Design]: "
labels: ["type:design", "scope:architecture", "phase:design"]
body:
  - type: markdown
    attributes:
      value: |
        ## Architecture Design
        For system-level design that spans multiple components.
        Output: Document in `docs/architecture/`

  - type: input
    id: title
    attributes:
      label: Design Title
      description: "Name for the architecture document"
      placeholder: "Event-Driven Worker Communication"
    validations:
      required: true

  - type: textarea
    id: problem_statement
    attributes:
      label: Problem Statement
      description: "What architectural challenge are we solving?"
      placeholder: |
        - Current limitation: ...
        - Why existing approach doesn't work: ...
        - Scale/complexity factors: ...
    validations:
      required: true

  - type: textarea
    id: scope
    attributes:
      label: Scope
      description: "What is in/out of scope for this design?"
      placeholder: |
        **In Scope:**
        - ...
        
        **Out of Scope:**
        - ... (covered in [OTHER_DOC])
    validations:
      required: true

  - type: textarea
    id: constraints
    attributes:
      label: Constraints & Principles
      description: "What constraints must the design respect?"
      placeholder: |
        - Must follow CORE_PRINCIPLES.md
        - Must not violate ARCHITECTURAL_SHIFTS.md
        - Performance requirement: ...
    validations:
      required: true

  - type: textarea
    id: options
    attributes:
      label: Design Options to Explore
      description: "What approaches should be evaluated?"
      placeholder: |
        1. Option A: ...
        2. Option B: ...
        3. Option C: ...
    validations:
      required: false

  - type: checkboxes
    id: checklist
    attributes:
      label: Architecture Design Checklist
      options:
        - label: "Reviewed CORE_PRINCIPLES.md"
        - label: "Reviewed ARCHITECTURAL_SHIFTS.md"
        - label: "Identified affected components"
        - label: "Considered backward compatibility"
        - label: "Identified migration path (if breaking)"

  - type: textarea
    id: related
    attributes:
      label: Related Documentation
      description: "Links to related architecture docs"
      placeholder: |
        - [CORE_PRINCIPLES.md](docs/architecture/CORE_PRINCIPLES.md)
        - [Related design](#issue)
    validations:
      required: false
```

### 1.6 Component Design

```yaml
# .github/ISSUE_TEMPLATE/component_design.yml
name: "🧩 Component Design"
description: "Design a specific component before implementation"
title: "[Component Design]: "
labels: ["type:design", "scope:component", "phase:design"]
body:
  - type: markdown
    attributes:
      value: |
        ## Component Design
        For detailed design of a specific component (DTO, Worker, Service).
        Output: Document in `docs/development/` then implementation.

  - type: input
    id: component_name
    attributes:
      label: Component Name
      description: "Name of the component to design"
      placeholder: "SignalDetector Worker"
    validations:
      required: true

  - type: dropdown
    id: component_type
    attributes:
      label: Component Type
      options:
        - "DTO (Data Transfer Object)"
        - "Worker (Plugin)"
        - "Platform Service"
        - "Factory"
        - "Adapter"
        - "Validator"
        - "Configuration Schema"
        - "Other"
    validations:
      required: true

  - type: textarea
    id: responsibility
    attributes:
      label: Single Responsibility
      description: "What is this component's ONE job?"
      placeholder: "Detect trading signals based on context data and publish Signal DTOs"
    validations:
      required: true

  - type: textarea
    id: interfaces
    attributes:
      label: Interfaces & Contracts
      description: "What does it consume and produce?"
      placeholder: |
        **Inputs:**
        - EMAOutputDTO from StrategyCache
        - RSIOutputDTO from StrategyCache
        
        **Outputs:**
        - Signal DTO (via DispositionEnvelope PUBLISH)
        
        **Dependencies:**
        - IStrategyCache (injected)
    validations:
      required: true

  - type: textarea
    id: design_decisions
    attributes:
      label: Key Design Decisions
      description: "Important choices to make during design"
      placeholder: |
        - [ ] Immutable or mutable?
        - [ ] Validation strategy?
        - [ ] Error handling approach?
    validations:
      required: true

  - type: textarea
    id: test_strategy
    attributes:
      label: Test Strategy
      description: "How will this component be tested?"
      placeholder: |
        - Unit tests: creation, validation, edge cases
        - Integration tests: with StrategyCache
        - Minimum test count: 20+
    validations:
      required: true

  - type: checkboxes
    id: checklist
    attributes:
      label: Component Design Checklist
      options:
        - label: "Follows WORKER_TAXONOMY.md (if worker)"
        - label: "Follows CODE_STYLE.md conventions"
        - label: "Has json_schema_extra examples (if DTO)"
        - label: "Identified all dependencies"
        - label: "Defined validation rules"
        - label: "Test strategy documented"
```

### 1.7 Design Validation

```yaml
# .github/ISSUE_TEMPLATE/design_validation.yml
name: "✅ Design Validation"
description: "Validate a design document before implementation"
title: "[Validate]: "
labels: ["type:validation", "phase:review"]
body:
  - type: markdown
    attributes:
      value: |
        ## Design Validation
        Use this to request formal validation of a design document.

  - type: input
    id: design_doc
    attributes:
      label: Design Document
      description: "Path or link to the design document"
      placeholder: "docs/development/SIGNAL_DETECTOR_DESIGN.md or #42"
    validations:
      required: true

  - type: dropdown
    id: design_type
    attributes:
      label: Design Type
      options:
        - "Architecture Design"
        - "Component Design"
        - "API Design"
        - "Configuration Design"
    validations:
      required: true

  - type: textarea
    id: validation_scope
    attributes:
      label: Validation Scope
      description: "What aspects need validation?"
      placeholder: |
        - [ ] Architectural compliance
        - [ ] Interface correctness
        - [ ] Naming conventions
        - [ ] Test coverage plan
        - [ ] Documentation completeness
    validations:
      required: true

  - type: checkboxes
    id: self_review
    attributes:
      label: Self-Review Checklist
      description: "Confirm you've checked these before requesting validation"
      options:
        - label: "Design follows ARCHITECTURE_TEMPLATE.md or DESIGN_TEMPLATE.md"
          required: true
        - label: "All sections complete (no TODOs)"
          required: true
        - label: "Cross-references to related docs added"
          required: true
        - label: "Diagrams (Mermaid) included where helpful"
        - label: "Design decisions documented with rationale"
          required: true

  - type: textarea
    id: concerns
    attributes:
      label: Areas of Concern
      description: "Specific areas where you want feedback"
      placeholder: |
        - Unsure about: ...
        - Alternative considered but rejected: ...
        - Need input on: ...
    validations:
      required: false

  - type: textarea
    id: implementation_plan
    attributes:
      label: Implementation Plan
      description: "How will this be implemented after approval?"
      placeholder: |
        1. Create feature branch
        2. RED: Write tests for...
        3. GREEN: Implement...
        4. REFACTOR: Quality gates...
    validations:
      required: false
```

### 1.8 Reference Documentation

```yaml
# .github/ISSUE_TEMPLATE/reference_documentation.yml
name: "📚 Reference Documentation"
description: "Create or update reference documentation for implemented code"
title: "[Ref Doc]: "
labels: ["type:docs", "scope:reference", "phase:documentation"]
body:
  - type: markdown
    attributes:
      value: |
        ## Reference Documentation
        Post-implementation documentation for `docs/reference/`.

  - type: input
    id: component
    attributes:
      label: Component to Document
      description: "Which implemented component needs documentation?"
      placeholder: "Signal DTO"
    validations:
      required: true

  - type: input
    id: source_file
    attributes:
      label: Source File
      description: "Path to the implementation"
      placeholder: "backend/dtos/strategy/signal.py"
    validations:
      required: true

  - type: input
    id: test_file
    attributes:
      label: Test File
      description: "Path to the test file"
      placeholder: "tests/unit/dtos/strategy/test_signal.py"
    validations:
      required: true

  - type: textarea
    id: documentation_scope
    attributes:
      label: Documentation Scope
      description: "What should the reference doc cover?"
      placeholder: |
        - [ ] API Reference (all public methods/fields)
        - [ ] Usage Examples (2-3 scenarios)
        - [ ] Validation Rules
        - [ ] Error Handling
        - [ ] Integration patterns
    validations:
      required: true

  - type: checkboxes
    id: prerequisites
    attributes:
      label: Prerequisites
      description: "Confirm implementation is complete"
      options:
        - label: "Implementation merged to main"
          required: true
        - label: "All tests passing"
          required: true
        - label: "All quality gates 10/10"
          required: true
        - label: "Code has docstrings"
          required: true

  - type: dropdown
    id: template
    attributes:
      label: Documentation Template
      description: "Which template to use?"
      options:
        - "REFERENCE_TEMPLATE.md (standard)"
        - "DTO reference (signal.md style)"
        - "Worker reference"
        - "Platform component reference"
    validations:
      required: true

  - type: textarea
    id: related_docs
    attributes:
      label: Related Documentation
      description: "What docs should link to this?"
      placeholder: |
        - Update: docs/architecture/README.md
        - Link from: docs/architecture/WORKER_TAXONOMY.md
    validations:
      required: false
```

### 1.9 Technical Debt

```yaml
# .github/ISSUE_TEMPLATE/tech_debt.yml
name: "🔧 Technical Debt"
description: "Track technical debt or code improvement"
title: "[Tech Debt]: "
labels: ["type:tech-debt", "priority:low"]
body:
  - type: markdown
    attributes:
      value: |
        ## Technical Debt
        Track code that works but needs improvement.

  - type: input
    id: summary
    attributes:
      label: Summary
      description: "Brief description of the debt"
      placeholder: "Missing json_schema_extra in EntryPlan DTO"
    validations:
      required: true

  - type: textarea
    id: current_state
    attributes:
      label: Current State
      description: "What's the current problematic situation?"
    validations:
      required: true

  - type: textarea
    id: desired_state
    attributes:
      label: Desired State
      description: "What should it look like after fixing?"
    validations:
      required: true

  - type: dropdown
    id: debt_type
    attributes:
      label: Debt Type
      options:
        - "Missing tests"
        - "Missing documentation"
        - "Code quality (linting/formatting)"
        - "Architecture violation"
        - "Performance"
        - "Security"
        - "Outdated dependencies"
        - "Other"
    validations:
      required: true

  - type: input
    id: effort
    attributes:
      label: Estimated Effort
      description: "How long to fix? (e.g., '30 min', '2 hours', '1 day')"
      placeholder: "1 hour"
    validations:
      required: false
```

### 1.5 Config File

```yaml
# .github/ISSUE_TEMPLATE/config.yml
blank_issues_enabled: false
contact_links:
  - name: "📖 Documentation"
    url: "https://github.com/MikeyVK/S1mpleTraderV3/tree/main/docs"
    about: "Check the documentation before creating an issue"
  - name: "🏛️ Architecture Docs"
    url: "https://github.com/MikeyVK/S1mpleTraderV3/tree/main/docs/architecture"
    about: "Review architecture docs for design questions"
```

---

## 2. Pull Request Template

```markdown
<!-- .github/PULL_REQUEST_TEMPLATE.md -->
## Description

<!-- Brief description of changes -->

## Related Issue

Closes #<!-- issue number -->

## Type of Change

- [ ] 🚀 Feature (new functionality)
- [ ] 🐛 Bug fix (non-breaking fix)
- [ ] ♻️ Refactor (no functional change)
- [ ] 📝 Documentation
- [ ] 🔧 Configuration/tooling

## TDD Checklist

- [ ] **RED**: Failing tests committed (`test:` commit)
- [ ] **GREEN**: Implementation committed (`feat:` commit)
- [ ] **REFACTOR**: Quality improvements committed (`refactor:` commit)

## Quality Gates

| Gate | Status | Score |
|------|--------|-------|
| G1: Whitespace | ⬜ | /10 |
| G2: Imports | ⬜ | /10 |
| G3: Line Length | ⬜ | /10 |
| G4: Type Check | ⬜ | /10 |
| G5: Tests | ⬜ | /total |

<!-- Replace ⬜ with ✅ when passing -->

## Test Coverage

- **New tests added:** <!-- number -->
- **Total tests after merge:** <!-- number -->
- **Test file:** `tests/unit/.../test_*.py`

## Documentation

- [ ] Code has docstrings (Google style)
- [ ] `json_schema_extra` examples added (for DTOs)
- [ ] README/docs updated (if applicable)
- [ ] IMPLEMENTATION_STATUS.md updated

## Architecture Compliance

- [ ] No direct EventBus access in workers
- [ ] Returns DispositionEnvelope (workers)
- [ ] Uses Pydantic DTOs (no dicts)
- [ ] Follows naming conventions

## Screenshots/Output

<!-- If applicable, add screenshots or command output -->

## Additional Notes

<!-- Any other context for reviewers -->
```

---

## 3. Labels

### 3.1 Label Definitions

```yaml
# Label configuration for GitHub
labels:
  # ═══ Type Labels ═══
  - name: "type:feature"
    color: "0e8a16"
    description: "New feature or enhancement"
  
  - name: "type:bug"
    color: "d73a4a"
    description: "Something isn't working"
  
  - name: "type:discussion"
    color: "c5def5"
    description: "Open-ended discussion or brainstorm"
  
  - name: "type:design"
    color: "5319e7"
    description: "Architecture or component design"
  
  - name: "type:validation"
    color: "0052cc"
    description: "Design validation request"
  
  - name: "type:docs"
    color: "0075ca"
    description: "Documentation (reference, guide)"
  
  - name: "type:tech-debt"
    color: "fbca04"
    description: "Technical debt or code improvement"
  
  - name: "type:refactor"
    color: "d4c5f9"
    description: "Code refactoring (no functional change)"

  # ═══ Scope Labels ═══
  - name: "scope:architecture"
    color: "1d76db"
    description: "System-level architecture"
  
  - name: "scope:component"
    color: "1d76db"
    description: "Single component design"
  
  - name: "scope:reference"
    color: "1d76db"
    description: "Reference documentation"

  # ═══ Development Phase Labels ═══
  - name: "phase:discovery"
    color: "f9d0c4"
    description: "Initial exploration / requirements"
  
  - name: "phase:discussion"
    color: "c5def5"
    description: "Open discussion / brainstorm"
  
  - name: "phase:design"
    color: "5319e7"
    description: "Architecture or component design"
  
  - name: "phase:review"
    color: "fbca04"
    description: "Design validation / review"
  
  - name: "phase:approved"
    color: "0e8a16"
    description: "Design approved, ready for implementation"
  
  - name: "phase:red"
    color: "b60205"
    description: "TDD RED - writing failing tests"
  
  - name: "phase:green"
    color: "0e8a16"
    description: "TDD GREEN - minimal implementation"
  
  - name: "phase:refactor"
    color: "1d76db"
    description: "TDD REFACTOR - quality improvements"
  
  - name: "phase:documentation"
    color: "0075ca"
    description: "Writing reference documentation"
  
  - name: "phase:done"
    color: "0e8a16"
    description: "Completed and merged"

  # ═══ Priority Labels ═══
  - name: "priority:critical"
    color: "b60205"
    description: "Blocks all other work"
  
  - name: "priority:high"
    color: "d93f0b"
    description: "Important, address soon"
  
  - name: "priority:medium"
    color: "fbca04"
    description: "Normal priority"
  
  - name: "priority:low"
    color: "c5def5"
    description: "Nice to have"
  
  - name: "priority:triage"
    color: "d4c5f9"
    description: "Needs prioritization"

  # ═══ Component Labels ═══
  - name: "component:dto"
    color: "bfd4f2"
    description: "Data Transfer Objects"
  
  - name: "component:core"
    color: "bfd4f2"
    description: "Core platform components"
  
  - name: "component:worker"
    color: "bfd4f2"
    description: "Worker plugins"
  
  - name: "component:config"
    color: "bfd4f2"
    description: "Configuration system"
  
  - name: "component:docs"
    color: "bfd4f2"
    description: "Documentation"

  # ═══ Status Labels ═══
  - name: "needs:discussion"
    color: "d876e3"
    description: "Requires team discussion"
  
  - name: "needs:design"
    color: "d876e3"
    description: "Requires design document"
  
  - name: "needs:info"
    color: "d876e3"
    description: "Waiting for more information"
  
  - name: "blocked"
    color: "b60205"
    description: "Blocked by another issue"
  
  - name: "wontfix"
    color: "ffffff"
    description: "This will not be worked on"
  
  - name: "duplicate"
    color: "cfd3d7"
    description: "This issue already exists"

  # ═══ Effort Labels ═══
  - name: "effort:small"
    color: "c2e0c6"
    description: "< 2 hours"
  
  - name: "effort:medium"
    color: "fef2c0"
    description: "2-8 hours"
  
  - name: "effort:large"
    color: "f9d0c4"
    description: "> 8 hours"
```

### 3.2 Label Setup Script

```powershell
# scripts/setup_github_labels.ps1
# Run this script to create/update all labels

$owner = "MikeyVK"
$repo = "S1mpleTraderV3"

# Requires: gh cli authenticated
# Usage: ./scripts/setup_github_labels.ps1

$labels = @(
    # Type
    @{ name = "type:feature"; color = "0e8a16"; description = "New feature or enhancement" },
    @{ name = "type:bug"; color = "d73a4a"; description = "Something isn't working" },
    @{ name = "type:design"; color = "5319e7"; description = "Architectural decision or design discussion" },
    @{ name = "type:tech-debt"; color = "fbca04"; description = "Technical debt or code improvement" },
    @{ name = "type:docs"; color = "0075ca"; description = "Documentation only" },
    @{ name = "type:refactor"; color = "d4c5f9"; description = "Code refactoring (no functional change)" },
    
    # TDD Phase
    @{ name = "phase:discovery"; color = "f9d0c4"; description = "Requirements gathering phase" },
    @{ name = "phase:red"; color = "b60205"; description = "TDD RED phase - writing failing tests" },
    @{ name = "phase:green"; color = "0e8a16"; description = "TDD GREEN phase - minimal implementation" },
    @{ name = "phase:refactor"; color = "1d76db"; description = "TDD REFACTOR phase - quality improvements" },
    @{ name = "phase:review"; color = "5319e7"; description = "Ready for review" },
    @{ name = "phase:done"; color = "0e8a16"; description = "Completed and merged" },
    
    # Priority
    @{ name = "priority:critical"; color = "b60205"; description = "Blocks all other work" },
    @{ name = "priority:high"; color = "d93f0b"; description = "Important, address soon" },
    @{ name = "priority:medium"; color = "fbca04"; description = "Normal priority" },
    @{ name = "priority:low"; color = "c5def5"; description = "Nice to have" },
    @{ name = "priority:triage"; color = "d4c5f9"; description = "Needs prioritization" },
    
    # Component
    @{ name = "component:dto"; color = "bfd4f2"; description = "Data Transfer Objects" },
    @{ name = "component:core"; color = "bfd4f2"; description = "Core platform components" },
    @{ name = "component:worker"; color = "bfd4f2"; description = "Worker plugins" },
    @{ name = "component:config"; color = "bfd4f2"; description = "Configuration system" },
    @{ name = "component:docs"; color = "bfd4f2"; description = "Documentation" },
    
    # Status
    @{ name = "needs:discussion"; color = "d876e3"; description = "Requires team discussion" },
    @{ name = "needs:design"; color = "d876e3"; description = "Requires design document" },
    @{ name = "needs:info"; color = "d876e3"; description = "Waiting for more information" },
    @{ name = "blocked"; color = "b60205"; description = "Blocked by another issue" },
    @{ name = "wontfix"; color = "ffffff"; description = "This will not be worked on" },
    @{ name = "duplicate"; color = "cfd3d7"; description = "This issue already exists" },
    
    # Effort
    @{ name = "effort:small"; color = "c2e0c6"; description = "< 2 hours" },
    @{ name = "effort:medium"; color = "fef2c0"; description = "2-8 hours" },
    @{ name = "effort:large"; color = "f9d0c4"; description = "> 8 hours" }
)

foreach ($label in $labels) {
    Write-Host "Creating/updating label: $($label.name)"
    gh label create $label.name --color $label.color --description $label.description --force
}

Write-Host "Done! Created/updated $($labels.Count) labels."
```

---

## 4. Milestones

### 4.1 Milestone Structure

```yaml
milestones:
  - title: "Week 0: Foundation"
    description: |
      Core DTOs and infrastructure
      - Signal, Risk, StrategyDirective DTOs
      - CausalityChain, Origin, DispositionEnvelope
      - All quality gates passing
    due_date: null  # Completed
    state: closed

  - title: "Week 1: Config Schemas"
    description: |
      Configuration validation layer
      - PlatformConfig schema
      - OperationConfig schema
      - StrategyConfig schema
      - ConfigValidator
    due_date: "2025-12-15"
    state: open

  - title: "Week 2: Bootstrap"
    description: |
      Application bootstrap process
      - ConfigLoader
      - ConfigTranslator
      - BuildSpec generation
    due_date: "2025-12-22"
    state: open

  - title: "Week 3: Factories"
    description: |
      Component assembly
      - WorkerFactory
      - EventAdapterFactory
      - WiringFactory
    due_date: "2025-12-29"
    state: open

  - title: "Week 4: Platform"
    description: |
      Core platform services
      - OperationService
      - FlowInitiator
      - StrategyCache implementation
    due_date: "2026-01-05"
    state: open

  - title: "MCP Server v1.0"
    description: |
      Workflow automation MCP server
      - Core resources and tools
      - GitHub integration
      - Quality gate automation
    due_date: "2026-01-31"
    state: open
```

### 4.2 Milestone Setup Script

```powershell
# scripts/setup_github_milestones.ps1

$milestones = @(
    @{
        title = "Week 1: Config Schemas"
        description = "Configuration validation layer: PlatformConfig, OperationConfig, StrategyConfig schemas"
        due_on = "2025-12-15T23:59:59Z"
    },
    @{
        title = "Week 2: Bootstrap"
        description = "Application bootstrap: ConfigLoader, ConfigTranslator, BuildSpec generation"
        due_on = "2025-12-22T23:59:59Z"
    },
    @{
        title = "Week 3: Factories"
        description = "Component assembly: WorkerFactory, EventAdapterFactory, WiringFactory"
        due_on = "2025-12-29T23:59:59Z"
    },
    @{
        title = "Week 4: Platform"
        description = "Core platform: OperationService, FlowInitiator, StrategyCache"
        due_on = "2026-01-05T23:59:59Z"
    },
    @{
        title = "MCP Server v1.0"
        description = "Workflow automation: resources, tools, GitHub integration"
        due_on = "2026-01-31T23:59:59Z"
    }
)

foreach ($milestone in $milestones) {
    Write-Host "Creating milestone: $($milestone.title)"
    gh api repos/{owner}/{repo}/milestones -f title="$($milestone.title)" -f description="$($milestone.description)" -f due_on="$($milestone.due_on)"
}
```

---

## 5. Project Board

### 5.1 Project Structure

```yaml
project:
  name: "ST3 Development"
  description: "S1mpleTrader V3 development tracking"
  
  columns:
    - name: "📋 Backlog"
      description: "Prioritized work items"
      automation:
        - preset: "to_do"
        - move_issues_here: "when issue opened with phase:discovery"
    
    - name: "🔴 RED Phase"
      description: "Writing failing tests"
      automation:
        - move_issues_here: "when label phase:red added"
    
    - name: "🟢 GREEN Phase"
      description: "Minimal implementation"
      automation:
        - move_issues_here: "when label phase:green added"
    
    - name: "🔵 REFACTOR Phase"
      description: "Quality improvements"
      automation:
        - move_issues_here: "when label phase:refactor added"
    
    - name: "👀 Review"
      description: "Ready for review/PR"
      automation:
        - move_issues_here: "when PR opened"
        - move_issues_here: "when label phase:review added"
    
    - name: "✅ Done"
      description: "Completed and merged"
      automation:
        - preset: "done"
        - move_issues_here: "when issue closed"
        - move_issues_here: "when PR merged"
```

### 5.2 Project Setup via GitHub CLI

```powershell
# scripts/setup_github_project.ps1

# Create project
gh project create --owner MikeyVK --title "ST3 Development"

# Note: Column setup requires GraphQL API
# The MCP server will handle this via PyGithub
```

---

## 6. Branch Protection

### 6.1 Main Branch Protection

```yaml
# Branch protection rules for 'main'
branch_protection:
  branch: main
  
  rules:
    # Require pull request before merging
    required_pull_request_reviews:
      required_approving_review_count: 0  # Solo developer, self-merge OK
      dismiss_stale_reviews: true
      require_code_owner_reviews: false
    
    # Require status checks
    required_status_checks:
      strict: true  # Branch must be up to date
      contexts:
        - "quality-gates"      # GitHub Action
        - "tests"              # GitHub Action
    
    # Enforce for admins too
    enforce_admins: false  # Allow admin bypass for emergencies
    
    # Require linear history (optional)
    required_linear_history: false
    
    # Allow force pushes (disabled)
    allow_force_pushes: false
    
    # Allow deletions (disabled)
    allow_deletions: false
    
    # Require conversation resolution
    required_conversation_resolution: true
```

### 6.2 Branch Protection Setup Script

```powershell
# scripts/setup_branch_protection.ps1

$owner = "MikeyVK"
$repo = "S1mpleTraderV3"
$branch = "main"

# Using GitHub CLI with API
gh api repos/$owner/$repo/branches/$branch/protection -X PUT -f '{
  "required_status_checks": {
    "strict": true,
    "contexts": ["quality-gates", "tests"]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}'
```

---

## 7. GitHub Actions (CI/CD)

### 7.1 Quality Gates Workflow

```yaml
# .github/workflows/quality-gates.yml
name: Quality Gates

on:
  push:
    branches: [main]
    paths:
      - 'backend/**/*.py'
      - 'tests/**/*.py'
  pull_request:
    branches: [main]
    paths:
      - 'backend/**/*.py'
      - 'tests/**/*.py'

jobs:
  quality-gates:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt
          pip install -e .
      
      - name: Gate 1 - Whitespace
        run: |
          python -m pylint backend/ tests/ --disable=all --enable=trailing-whitespace,superfluous-parens --recursive=y
      
      - name: Gate 2 - Import Placement
        run: |
          python -m pylint backend/ tests/ --disable=all --enable=import-outside-toplevel --recursive=y
      
      - name: Gate 3 - Line Length
        run: |
          python -m pylint backend/ tests/ --disable=all --enable=line-too-long --max-line-length=100 --recursive=y
      
      - name: Gate 4 - Type Checking
        run: |
          python -m mypy backend/dtos/ --strict --no-error-summary
      
      - name: Gate 5 - Tests
        run: |
          pytest tests/ -v --tb=short --cov=backend --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          fail_ci_if_error: false
```

### 7.2 Test Count Badge

```yaml
# .github/workflows/test-badge.yml
name: Test Badge

on:
  push:
    branches: [main]

jobs:
  update-badge:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          pip install -e .
      
      - name: Count tests
        id: count
        run: |
          count=$(pytest tests/ --collect-only -q 2>/dev/null | tail -1 | grep -oE '^[0-9]+')
          echo "test_count=$count" >> $GITHUB_OUTPUT
      
      - name: Create badge
        uses: schneegans/dynamic-badges-action@v1.7.0
        with:
          auth: ${{ secrets.GIST_TOKEN }}
          gistID: YOUR_GIST_ID
          filename: test-count.json
          label: tests
          message: ${{ steps.count.outputs.test_count }} passing
          color: green
```

---

## 8. Verification Checklist

After running the setup scripts, verify:

- [ ] **Issue Templates**: Create test issue with each template
- [ ] **Labels**: All 28 labels visible in repository
- [ ] **Milestones**: All milestones created with due dates
- [ ] **Project Board**: Columns visible, automation working
- [ ] **Branch Protection**: Cannot push directly to main
- [ ] **GitHub Actions**: Workflows trigger on push/PR
- [ ] **PR Template**: Template appears when creating PR

---

## 9. MCP Server Integration

The MCP server uses these GitHub configurations via:

```yaml
mcp_integration:
  issue_templates:
    - tool: create_issue
      uses: type parameter to select template
      auto_labels: Applied based on type
  
  labels:
    - tool: update_issue
      manages: phase:* labels for TDD tracking
    - resource: st3://github/issues
      reads: labels for filtering
  
  project_board:
    - tool: move_project_card
      moves: cards based on TDD phase
    - resource: st3://github/project
      reads: board state
  
  branch_protection:
    - Enforces quality gates before merge
    - MCP server verifies status before merge_to_main
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-08 | Initial GitHub setup specification |

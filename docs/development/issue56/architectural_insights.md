# Architectural Insights: Unified Artifact System

**Date:** 2026-01-16  
**Status:** DEFINITIVE  
**Context:** Brainstorm session during Issue #56 research  
**Purpose:** Foundation for revised research approach  
**Scope Impact:** Issues #52, #54, #56 (overlapping concerns)

---

## Executive Summary

During research for Issue #56 (Document Templates Configuration), fundamental architectural insights emerged that change the scope from "externalize document templates" to "create unified artifact system". This document captures the key insights that will guide the revised research and planning phases.

**Key Discovery:** Documents are not fundamentally different from code components in the context of the MCP server's role as process orchestrator. Both are **artifacts** created during development workflows, requiring similar configuration patterns for scaffolding, validation, and lifecycle management.

---

## 1. Core Philosophical Insights

### 1.1 MCP Server Purpose

**The MCP server's mission:**
> Enable human and AI to work in harmony on **creative content**, while software handles **workflow orchestration, project structure, and quality assurance**.

**Translation:**
- Human/Agent focus: Content creation (code logic, documentation content)
- MCP Server handles: When to create, where to place, how to structure, quality gates

**Evidence from experience:**
> "Referring agents to agent.md text files is insufficient to guarantee structured development of complex projects."

**Implication:** All workflow mechanics must be **enforced through tooling**, not documentation.

### 1.2 Code vs Documents: Similarities Override Differences

**Initial incorrect view:**
- Code = executes → HARD enforcement
- Documents = don't execute → SOFT metadata

**Correct view:**
Both are **artifacts in the development process** that require:

| Concern | Code | Documents | Same Pattern? |
|---------|------|-----------|---------------|
| **WAT** (Registry) | What components exist | What doc types exist | ✅ YES |
| **WANNEER** (Phase) | When can scaffold | When can create | ✅ YES |
| **WAAR** (Directory) | Where files go | Where docs go | ✅ YES |
| **HOE** (Structure) | Templates + validation | Templates + validation | ✅ YES |
| **Enforcement Level** | BLOCK violations | WARN violations | ❌ Different |

**Key Insight:** Enforcement **level** differs, but enforcement **presence** is the same.

**Documents follow workflows just like code:**
- research.md created in research phase
- design.md created in design/planning phase  
- Code components created in tdd phase
- All require structure, placement rules, lifecycle

### 1.3 Epic #49 vs Epic #18 Distinction

**Critical misunderstanding corrected:**

**Epic #49: Platform Configurability**
- **Purpose**: Externalize HARDCODED data to YAML
- **Scope**: Move dicts/literals from Python → config files
- **NOT about**: Enforcement logic (that's Epic #18)

**Examples:**
- Issue #50: `PHASE_TEMPLATES` dict → workflows.yaml
- Issue #54: `SCAFFOLDERS` dict → components.yaml
- Issue #55: `VALID_BRANCHES` list → git.yaml
- Issue #56: `TEMPLATES` dict → artifacts.yaml (REVISED scope)

**Epic #18: TDD & Policy Enforcement**
- **Purpose**: USE configs to enforce policies
- **Scope**: PolicyEngine blocks operations based on config rules
- **Timing**: AFTER Epic #49 completes

**Evidence from Issue #54:**
> "Directory-specific phase policies are DEFERRED to Epic #18"

**Implication:** Issue #56 focuses on DATA externalization, not enforcement implementation.

---

## 2. Architectural Decisions

### 2.1 Unified Artifact Registry (artifacts.yaml)

**Decision:** Merge `components.yaml` + `documents.yaml` → `artifacts.yaml`

**Rationale:**
1. **Consistency**: All scaffoldable items in one registry
2. **SRP**: Single source for "what can be created"
3. **Extensibility**: Easy to add new artifact types (tests, configs, git texts)
4. **Pattern reuse**: Same config structure for all types

**Structure:**
```yaml
# artifacts.yaml
artifact_types:
  # Code artifacts
  - type: code
    name: dto
    template: components/dto.py.jinja2
    base_path: backend/dtos
    state_machine:
      states: [...]
      initial_state: ...
      valid_transitions: [...]
  
  # Document artifacts
  - type: doc
    name: research
    template: documents/research.md.jinja2
    base_path: docs/development
    state_machine:
      states: [DRAFT, APPROVED, DEFINITIVE]
      initial_state: DRAFT
      valid_transitions:
        - from: DRAFT
          to: [APPROVED, DEFINITIVE]
  
  # Git text artifacts
  - type: git
    name: issue_description
    template: git/issue_description.md.jinja2
    output_target: github_issue
  
  # Test artifacts (future)
  - type: test
    name: unit_test
    template: tests/unit_test.py.jinja2
    base_path: tests
```

**Impact on existing issues:**
- Issue #54 (components.yaml) → Rename to artifacts.yaml, extend structure
- Issue #56 (documents.yaml) → Merge into artifacts.yaml as doc type

### 2.2 Template-Driven Everything

**Decision:** ALL scaffoldable artifacts use Jinja2 templates

**Scope expansion:**
- ✅ Code components (existing)
- ✅ Documents (existing)
- ✅ Git issue descriptions (NEW)
- ✅ Git PR descriptions (NEW)
- ✅ Git commit messages (NEW)
- ✅ Test files (future)

**Rationale:**
1. **Consistency**: Single scaffolding mechanism
2. **Maintainability**: Templates in one location (mcp_server/templates/)
3. **Testability**: Template rendering separately testable
4. **Integration**: Issue #52 validation applies to ALL templates
5. **Flexibility**: Easy to customize per project

**Example - Git issue template:**
```jinja2
{# git/issue_description.md.jinja2 #}
## Objective
{{ objective }}

## Context
{{ context }}

## Acceptance Criteria
{% for criterion in acceptance_criteria %}
- [ ] {{ criterion }}
{% endfor %}

## Related Issues
{% if related_issues %}
{% for issue in related_issues %}
- #{{ issue }}
{% endfor %}
{% endif %}
```

**Unified scaffolding API:**
```python
scaffold_artifact(
    type="git",
    name="issue_description",
    context={"objective": "...", "acceptance_criteria": [...]}
)
```

### 2.3 SRP Config Separation (3-Config Model)

**Decision:** Separate concerns across three configuration files

#### Config 1: artifacts.yaml - "WAT + State Machine Structure"

**Responsibility:** Artifact definitions + valid state transitions

**Contains:**
- Artifact type registry (code, doc, git, test)
- Template paths
- Base paths / output targets
- State machine definitions:
  - Available states (no hardcoded literals!)
  - Initial state
  - Valid transitions (structural rules)

**Does NOT contain:**
- When to trigger state changes (that's policies.yaml)
- Where artifacts are allowed (that's project_structure.yaml)

#### Config 2: policies.yaml - "WANNEER Triggers"

**Responsibility:** Event → State Change Trigger mapping

**Contains:**
```yaml
artifact_state_triggers:
  phase_exit:
    research:
      - artifact_pattern: "*/research.md"
        transition: { from: DRAFT, to: APPROVED }
  
  issue_lifecycle:
    issue_closed:
      - artifact_pattern: "*"
        transition: { to: DEFINITIVE }
    
    pr_merged:
      - artifact_pattern: "*"
        transition: { to: DEFINITIVE }
```

**Purpose:** Define WHEN state transitions are triggered, not which are valid

#### Config 3: project_structure.yaml - "WAAR Artifacts"

**Responsibility:** Directory structure + allowed artifacts per location

**Extends existing:**
```yaml
directories:
  - path: backend/dtos
    parent: backend
    allowed_artifacts: [dto, schema]  # Code artifacts
  
  - path: docs/development
    parent: docs
    allowed_artifacts: [research, planning, design]  # Doc artifacts
  
  - path: docs/reference
    parent: docs
    allowed_artifacts: [tracking, reference]
```

**Purpose:** Define WHERE artifacts can be placed

### 2.4 State Machine Design

**Decision:** Flexible, per-artifact state machines with no hardcoded statuses

**Problem we're solving:**
- Different artifact types need different status sets
- Status transitions vary by artifact
- Multiple triggers can cause same transition
- No manual status ceremony wanted

**Solution: Two-layer validation**

**Layer 1 - Structural validation (artifacts.yaml):**
```yaml
state_machine:
  states: [DRAFT, APPROVED, DEFINITIVE]
  valid_transitions:
    - from: DRAFT
      to: [APPROVED, DEFINITIVE]  # Both paths allowed
    - from: APPROVED
      to: [DEFINITIVE]
```

**Purpose:** "Which transitions are structurally possible?"

**Layer 2 - Business triggers (policies.yaml):**
```yaml
artifact_state_triggers:
  phase_exit:
    research:
      transition: { from: DRAFT, to: DEFINITIVE }  # Skip APPROVED
```

**Purpose:** "When do we trigger which transition?"

**Validation flow:**
1. Policy triggers transition: DRAFT → DEFINITIVE
2. artifacts.yaml validates: "Is this transition in valid_transitions?" → YES
3. Execute transition

**Benefits:**
- ✅ No hardcoded status literals
- ✅ Guard rails prevent invalid transitions
- ✅ Flexible trigger definitions
- ✅ Can skip states when valid

**Special case - LIVING DOCUMENT:**
```yaml
state_machine:
  states: [LIVING DOCUMENT]
  initial_state: LIVING DOCUMENT
  valid_transitions: []  # No transitions allowed
```

### 2.5 Automated Status Changes (No Manual Ceremony)

**Decision:** Status changes are side-effects of workflow events, not manual operations

**Anti-pattern (ceremony):**
```python
# NO manual status tool
update_document_status(doc="research.md", status="APPROVED")
```

**Correct pattern (automated):**
```python
# Status changes triggered by workflow events
transition_phase(to="planning")
  → Triggers: phase_exit.research
    → Auto-approves: research.md (DRAFT → APPROVED)

close_issue(issue=56)
  → Triggers: issue_lifecycle.issue_closed
    → Finalizes: all artifacts (→ DEFINITIVE)
```

**Multiple trigger types:**
- **phase_exit**: Phase transitions
- **issue_lifecycle**: Issue closed, PR merged
- **manual**: Explicit agent decision (rare)
- **time_based**: Never (for LIVING DOCUMENT types)

**Implementation (Epic #18):**
```python
def transition_phase(to_phase):
    # Normal transition logic
    
    # Get state change triggers for this event
    triggers = policies_config.artifact_state_triggers.phase_exit[current_phase]
    
    for trigger in triggers:
        artifacts = find_artifacts(trigger.artifact_pattern)
        
        for artifact in artifacts:
            # Validate against state machine
            artifact_def = artifacts_config.get_artifact(artifact.type)
            if artifact_def.state_machine.is_valid_transition(trigger.transition):
                artifact.update_state(trigger.transition.to)
```

---

## 3. Integration with Existing Issues

### 3.1 Issue #52 (Template Validation Config)

**Status:** ✅ Complete

**What it provides:**
- Template YAML metadata (in Jinja2 comment blocks)
- ValidationService + LayeredTemplateValidator
- Three-tier validation (STRICT → ARCHITECTURAL → GUIDELINE)
- Template inheritance (base → specific templates)

**Integration with artifacts.yaml:**
- artifacts.yaml defines WHICH templates exist
- Issue #52 defines HOW templates are validated
- No duplication of validation rules

**Example:**
```yaml
# artifacts.yaml
- type: doc
  name: architecture
  template: documents/architecture.md.jinja2  # ← Points to template
```

```jinja2
{# documents/architecture.md.jinja2 #}
{# TEMPLATE_METADATA
enforcement: STRICT
validates:
  strict:
    - rule: numbered_sections
    - rule: mermaid_diagrams
#}
```

**Clear separation:**
- artifacts.yaml: "This artifact type uses this template"
- Template metadata: "This template requires these structures"

### 3.2 Issue #54 (Config Foundation)

**Status:** ✅ Complete

**What it provides:**
- components.yaml (9 component types)
- project_structure.yaml (15 directories)
- policies.yaml (operation policies)
- DirectoryPolicyResolver utility

**Changes needed:**
- **Rename components.yaml → artifacts.yaml**
- **Extend structure** to support doc/git/test types
- **Add state_machine** section to artifact definitions
- **Extend project_structure.yaml** with document directories

**Migration path:**
```yaml
# OLD: components.yaml
component_types:
  - name: dto
    scaffolder_class: DTOScaffolder
    base_path: backend/dtos

# NEW: artifacts.yaml
artifact_types:
  - type: code
    name: dto
    template: components/dto.py.jinja2
    base_path: backend/dtos
    state_machine:
      states: [CREATED]  # Code has simpler lifecycle
      initial_state: CREATED
      valid_transitions: []
```

### 3.3 Issue #56 (Document Templates Configuration)

**Original scope:** Externalize TEMPLATES and SCOPE_DIRS dicts from DocManager

**Revised scope:** 
1. **Merge into artifacts.yaml** (doc type artifacts)
2. **Extend policies.yaml** with document state triggers
3. **Extend project_structure.yaml** with document directories
4. **NO separate documents.yaml** (violates SRP, duplicates structure)

**What changes:**
- DocManager loads artifacts.yaml instead of hardcoded dicts
- Document types become artifact registry entries
- State management via artifact state machine
- Directory policies via project_structure.yaml

**What stays the same:**
- Template validation (Issue #52 already complete)
- Jinja2 template rendering
- ValidationService integration

---

## 4. Scope Implications

### 4.1 Issue #56 Expanded Scope

**Beyond original scope:**
- Not just "externalize TEMPLATES dict"
- Part of larger **unified artifact system**
- Requires **components.yaml refactoring**
- Adds **state machine infrastructure**
- Integrates with **policies.yaml** for triggers

**New deliverables:**
1. artifacts.yaml (replaces components.yaml + documents.yaml)
2. Extended project_structure.yaml (document directories)
3. Extended policies.yaml (document state triggers)
4. ArtifactConfig Pydantic model (replaces ComponentRegistryConfig)
5. State machine validation infrastructure
6. DocManager refactoring (use ArtifactConfig)
7. ScaffoldManager refactoring (unified artifact scaffolding)

### 4.2 Issues Requiring Revision

**Issue #52:** ✅ No changes needed
- Template validation stays separate (correct SRP)
- Integration point well-defined

**Issue #54:** ⚠️ Requires updates
- components.yaml → artifacts.yaml (rename + extend)
- ComponentRegistryConfig → ArtifactConfig
- Add state machine support
- **Breaking change**: Existing code references components.yaml

**Issue #56:** 🔄 Scope redefined
- No separate documents.yaml
- Becomes "artifact system unification"
- Broader impact than originally planned

### 4.3 Migration Considerations

**Backward compatibility:**
- ❌ NOT preserved (clean break, like Issue #50)
- components.yaml → artifacts.yaml is breaking change
- All references must be updated

**Migration path:**
1. Create artifacts.yaml with unified structure
2. Migrate component types → code artifact type
3. Add document artifact types
4. Update all references (ScaffoldManager, tools)
5. Delete components.yaml
6. Update tests

**Risk:** Higher complexity than originally anticipated

---

## 5. Design Principles Established

### 5.1 Single Responsibility Principle (SRP)

**Applied rigorously:**
- artifacts.yaml: WAT + state structure
- policies.yaml: WANNEER triggers
- project_structure.yaml: WAAR placement
- validation.yaml (Issue #52): HOE validation

**Anti-pattern avoided:** Mixing concerns in single config

### 5.2 No Hidden Metadata

**Principle:** All important configuration must be explicit, not nested/hidden

**Applied:**
- ❌ NOT: lifecycle nested as "metadata" in artifacts
- ✅ YES: state_machine as top-level concern in artifact definition

### 5.3 No Hardcoded Literals

**Principle:** All enums/constants must be data-driven

**Applied:**
- ❌ NOT: Hardcoded status literals (DRAFT, APPROVED, etc.)
- ✅ YES: States defined per artifact type in config
- ❌ NOT: Hardcoded phase names in transition logic
- ✅ YES: Phase names from workflows.yaml

### 5.4 Template-Driven Scaffolding

**Principle:** If it's scaffoldable, it uses a Jinja2 template

**Applied:**
- ✅ Code components
- ✅ Documents
- ✅ Git texts (issues, PRs, commits)
- ✅ Tests (future)

**Consistency:** Same rendering engine, same validation approach

### 5.5 Automation Over Ceremony

**Principle:** Minimize manual steps, automate workflow mechanics

**Applied:**
- ✅ Status changes triggered by events (not manual updates)
- ✅ Document creation via scaffolding (not manual files)
- ✅ Structure validation automatic (not manual checks)
- ✅ Phase transitions trigger side-effects automatically

---

## 6. Open Questions for Research Phase

### 6.1 State Machine Implementation

**Question:** Where does state machine validation logic live?

**Options:**
1. In ArtifactConfig Pydantic model (validation at config load)
2. Separate StateMachineValidator utility
3. In artifact manager (runtime validation)

**Decision needed:** Research phase must determine best approach

### 6.2 Trigger Execution Order

**Question:** If multiple triggers fire for same event, what's the order?

**Example:**
```yaml
phase_exit.research:
  - artifact_pattern: "*/research.md"
    transition: { to: APPROVED }
  - artifact_pattern: "*"
    transition: { to: DEFINITIVE }
```

**Both match research.md - which wins?**

**Options:**
1. First match wins (order matters)
2. Most specific pattern wins
3. All triggers execute (multiple transitions)
4. Error on ambiguity

### 6.3 State Storage

**Question:** Where are artifact states persisted?

**Options:**
1. In document frontmatter (for docs)
2. In .st3/artifact_states.json
3. In git metadata
4. Derived from git history

**Trade-offs:** Durability vs Portability vs Simplicity

### 6.4 Backward Compatibility Strategy

**Question:** How to migrate existing components.yaml users?

**Options:**
1. Breaking change (Issue #50 pattern)
2. Support both for transition period
3. Auto-migration script
4. Manual migration guide

**Impact:** All existing projects need migration

### 6.5 Testing Strategy

**Question:** How to test state machine validation?

**Considerations:**
- Unit tests for state machine logic
- Integration tests for trigger execution
- End-to-end tests for workflow scenarios
- Config validation tests

---

## 7. Next Steps

### 7.1 Immediate Actions

1. **Create revised research.md** based on these insights
2. **Analyze existing codebase** for all hardcoded artifact data
3. **Design artifacts.yaml schema** with full state machine support
4. **Map all integration points** across Issues #52, #54, #56
5. **Create migration plan** from components.yaml → artifacts.yaml

### 7.2 Research Phase Focus

**Key questions to answer:**
1. What hardcoded artifact data exists? (Complete inventory)
2. What state machines are needed per artifact type?
3. What triggers are required in policies.yaml?
4. What directory mappings need extending?
5. What's the migration impact on existing code?
6. How do we test the unified system?

### 7.3 Planning Phase Focus

**Design deliverables:**
1. Complete artifacts.yaml schema
2. ArtifactConfig Pydantic models
3. State machine validator design
4. Trigger execution engine design
5. Migration strategy document
6. Test strategy document

---

## 8. Success Criteria

**This architectural foundation succeeds if:**

1. ✅ **SRP maintained** - Each config has single responsibility
2. ✅ **No duplication** - No overlap between configs
3. ✅ **Template-driven** - All artifacts use Jinja2 templates
4. ✅ **No hardcoded data** - All artifact definitions in config
5. ✅ **State machines work** - Valid transitions enforced
6. ✅ **Automation achieved** - Minimal manual ceremony
7. ✅ **Integration clean** - Issue #52 and #54 integrate smoothly
8. ✅ **Extensible** - Easy to add new artifact types
9. ✅ **Testable** - Clear boundaries enable thorough testing
10. ✅ **Migration possible** - Existing projects can upgrade

---

## Conclusion

What started as "externalize document templates" revealed a fundamental architectural opportunity: **unified artifact system**. By recognizing that documents, code, and git texts are all artifacts in the development process, we can apply consistent patterns across the entire MCP server.

**Core insight:** The MCP server orchestrates artifact creation through workflows. ALL artifacts should follow the same configuration patterns, using templates for scaffolding, state machines for lifecycle, and policies for triggers.

**This is the foundation for Issue #56 research.**

---

**Document Status:** DEFINITIVE  
**Next Action:** Create revised research.md for Issue #56  
**Scope:** Issues #52, #54, #56 (integrated approach)

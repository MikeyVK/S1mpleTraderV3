# Template Library Management - SCAFFOLD Metadata Rollout

<!-- SCAFFOLD: template=research version=1.0 created=2026-01-22T17:00:00Z path=docs/development/issue72/research.md -->

**Issue:** #72  
**Epic:** Template Library Management  
**Status:** Research Phase  
**Date:** 2026-01-22

---

## Executive Summary

**Problem:** Issue #120 Phase 0 is only 8% complete - only 2 of 24 templates have SCAFFOLD metadata, blocking Issue #121 (Content-Aware Edit Tool) and violating core architecture principles.

**Root Cause:** Issue #52 built validation infrastructure but Issue #72 (template metadata rollout) was never executed.

**Decision:** Issue #121 superseded by #72 - discovery tool is naturally part of template library completeness.

**Solution:** Complete SCAFFOLD metadata rollout using inheritance strategy:
- 3 base templates → affects 11 children automatically
- 9 standalone templates → individual updates
- Total: 12 template updates (~4-6h) + validation

**Architectural Alignment:**
- ✅ **Config Over Code** - Templates as SSOT (not hardcoded RULES dict)
- ✅ **DRY** - Base template inheritance eliminates duplication
- ✅ **SRP** - Templates define both scaffolding AND validation
- ✅ **Contract-Driven** - SCAFFOLD metadata as typed contract

---

## Problem Analysis

### Context: Template-Driven Architecture (Issue #52)

Issue #52 established **templates as Single Source of Truth**:
- Templates define both scaffolding structure AND validation rules
- Eliminates duplicate RULES dict (Config Over Code)
- TEMPLATE_METADATA contains validation contracts

**From Issue #52 design.md:**
```yaml
# TEMPLATE_METADATA in dto.py.jinja2
validates:
  strict:
    - rule: required_imports
      pattern: "from pydantic import BaseModel"
  architectural:
    - rule: base_class
      pattern: "class \\w+\\(BaseModel\\):"
  guidelines:
    - rule: docstring
      hint: "Add class docstring for clarity"
```

**Benefit:** Template changes = validation follows automatically (SSOT principle).

### Issue #120 Phase 0: Incomplete Implementation

**Claim in #120:**
> "All scaffolded files have `template`, `version` in YAML frontmatter"

**Reality:**
```powershell
Get-ChildItem mcp_server\templates -Recurse -Filter *.jinja2 | 
  Select-String "SCAFFOLD:" | Measure-Object

Count: 2  # Only dto.py + commit-message.txt
Total templates: 24
Completion: 8% ❌
```

**Impact:**
- ❌ query_file_schema() fails for 91% of files
- ❌ Issue #121 (discovery tool) blocked
- ❌ Unified architecture (#120 + #121) broken
- ❌ Templates are NOT functioning as SSOT

### Issue #121 Discovery Analysis

**Issue #121 research revealed:**
- Discovery tool (`query_file_schema`) valuable for editing workflows
- Unlike scaffolding (agent provides type), editing often lacks context
- Batch operations benefit from proactive discovery (40% efficiency)

**Key Insight:** Discovery tool is **part of template completeness**, not separate feature.

**Decision:** Fold #121 into #72 - once all templates have metadata, discovery works automatically.

---

## Template Architecture Audit

### Inheritance Analysis

**From Issue #121 research (template-inheritance-analysis.md):**

| Template Type | Count | Strategy |
|--------------|-------|----------|
| **Base templates** | 3 | Add SCAFFOLD → affects 11 children |
| **Templates using extends** | 11 | Auto-inherit from base |
| **Standalone templates** | 11 | Individual updates |
| **Already complete** | 2 | dto.py, commit-message.txt |

**Base Template Impact:**
1. `base/base_component.py.jinja2` → 9 children inherit automatically
   - generic.py, interface.py, resource.py, schema.py
   - service_command.py, service_orchestrator.py, service_query.py
   - tool.py, worker.py (if it used extends - currently standalone)

2. `base/base_document.md.jinja2` → 2 children inherit
   - architecture.md, reference.md

3. `base/base_test.py.jinja2` → 0 children (orphaned base)

**DRY Principle Applied:**
- Update 3 base templates = 11 templates fixed automatically
- Inheritance eliminates metadata duplication
- Follows docs/coding_standards principle: "Don't repeat yourself"

### Templates Requiring Direct Updates

**Standalone templates (no extends):**

**Components (5):**
1. adapter.py - Adapter pattern components
2. dto.py - ✅ Already complete
3. worker.py - Worker base classes
4. dto_test.py - DTO test scaffolds
5. worker_test.py - Worker test scaffolds

**Documents (6):**
1. commit-message.txt - ✅ Already complete
2. design.md - Design documents
3. generic.md - **Critical:** Used for research/planning docs!
4. tracking.md - Issue tracking docs
5. integration_test.py - Integration test scaffolds
6. unit_test.py - Unit test scaffolds

---

## Core Principles Alignment

### Principle 1: Config Over Code

**Violation (Before Issue #52):**
```python
# mcp_server/validators/template_validator.py
RULES = {
    "worker": {
        "required_methods": ["execute"],
        "base_class": "BaseWorker"
    },
    "dto": {
        "required_fields": ["model_config"],
        "base_class": "BaseModel"
    }
}
# ❌ Hardcoded rules duplicate template structure
```

**Solution (After Issue #52):**
```jinja
{# worker.py.jinja2 - Templates as SSOT #}
{# TEMPLATE_METADATA
validates:
  architectural:
    - rule: required_methods
      pattern: "async def process\\(self, input_data: \\w+\\) -> \\w+"
#}

class {{ name }}(BaseWorker):
    async def process(self, input_data: {{ input_dto }}) -> {{ output_dto }}:
        """Process input and return result."""
```

**Benefit:**
- ✅ Template change → validation follows automatically
- ✅ No RULES dict maintenance burden
- ✅ Single source of truth for structure

**Issue #72 Goal:** Complete metadata rollout = full SSOT realization.

### Principle 2: DRY (Don't Repeat Yourself)

**Current State:**
```jinja
{# 9 component templates all duplicate same header structure #}
{% extends "base/base_component.py.jinja2" %}
```

**Without SCAFFOLD in base:**
- Each child would need individual SCAFFOLD metadata ❌
- 9x duplication of same metadata structure

**With SCAFFOLD in base:**
```jinja
{# base/base_component.py.jinja2 #}
# SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created_at }} path={{ output_path }}
"""
{{ name }} - {{ description }}.
"""
{% block content %}
{% endblock %}
```

**Result:**
- ✅ All 9 children inherit metadata automatically
- ✅ Single point of maintenance (base template)
- ✅ Follows docs/coding_standards DRY principle

**Issue #72 Goal:** Leverage inheritance to maximize DRY.

### Principle 3: SRP (Single Responsibility Principle)

**Template Responsibility:**
- Define structure (scaffolding)
- Define validation rules (quality)
- Provide agent hints (documentation)

**Current Violation:**
```python
# Two separate systems for same concept:
1. Templates define structure (scaffolding)
2. RULES dict defines validation (quality)  # ❌ Duplicate responsibility
```

**After Issue #52 + #72:**
```jinja
{# Template = single responsibility for artifact definition #}
{# TEMPLATE_METADATA
structure:  # Scaffolding
  - section: fields
    repeatable: true
validates:  # Quality
  strict:
    - rule: docstring
guidance:   # Documentation
  agent_hints:
    - "DTOs represent system contracts"
#}
```

**Benefit:**
- ✅ Template owns entire artifact lifecycle
- ✅ No split between scaffolding and validation
- ✅ Follows docs/coding_standards SRP principle

**Issue #72 Goal:** Complete template ownership of artifact definition.

### Principle 4: Contract-Driven Development

**From docs/architecture/CORE_PRINCIPLES.md:**
> All data-uitwisseling wordt gevalideerd door strikte Pydantic-schema's

**Applied to Templates:**
- SCAFFOLD metadata = typed contract for file structure
- Template introspection = runtime validation of contract
- Agent discovery = contract querying before mutation

**Issue #121 Use Case:**
```python
# Agent queries file contract
schema = query_file_schema("backend/dtos/signal.py")
# Returns:
{
    "template_id": "dto",           # ← From SCAFFOLD metadata
    "template_version": "1.0",      # ← Contract version
    "structure": { ... },           # ← From template introspection
    "edit_capabilities": ["ScaffoldEdit"]  # ← Based on contract
}

# Agent makes contract-aware edit
editFiles("signal.py", [
    ScaffoldEdit.append_to_list("fields", ...)  # ← Uses contract
])
```

**Without SCAFFOLD metadata:**
- ❌ No contract to query
- ❌ Discovery returns "non-scaffolded"
- ❌ Agent forced to use trial-and-error

**Issue #72 Goal:** Enable contract-driven file editing workflows.

---

## Research Findings

### Finding 1: Template Metadata Gap

**Audit Results:**
- ✅ 2 templates complete: dto.py, commit-message.txt
- ❌ 22 templates missing metadata
- ❌ 91% of scaffolded files undetectable

**Verification Command:**
```powershell
Get-ChildItem mcp_server\templates -Recurse -Filter *.jinja2 | ForEach-Object {
    $content = Get-Content $_.FullName -Raw
    if ($content -match 'SCAFFOLD:') {
        Write-Host "✅ $($_.Name)"
    } else {
        Write-Host "❌ $($_.Name)"
    }
}
```

**Impact:** Blocks Issue #121 discovery tool, violates SSOT principle.

### Finding 2: Inheritance Optimization

**User Insight:** "Why not use base templates?"

**Analysis:**
- 11 templates use `{% extends %}`
- Updating 3 base templates = 11 templates fixed
- Efficiency: 67% reduction (12 updates vs 22)

**Architecture Benefit:**
- Base template = single point of maintenance
- Child templates auto-inherit metadata
- Follows DRY principle naturally

**Recommendation:** Prioritize base template updates first.

### Finding 3: Issue #121 Superseded by #72

**Issue #121 Goal:** Content-Aware Edit Tool with discovery
**Blocker:** No template metadata to discover

**Key Insight:**
> Discovery tool is not a separate feature - it's a **natural consequence** of template completeness.

**Logic:**
1. All templates have SCAFFOLD metadata (Issue #72)
2. All scaffolded files have template reference
3. query_file_schema() can introspect any file
4. Discovery "just works" ✅

**Decision:**
- Close Issue #121 as superseded by #72
- Discovery implementation becomes part of #72 validation
- Unified architecture: templates → metadata → discovery → editing

### Finding 4: Template Quality Issues (Issue #74)

**Issue #74 Status:** OPEN - DTO and Tool template validation failures

**E2E Test Results (from Issue #52):**
```
Integration Tests: 4/5 passing ✅
E2E Tests: 1/3 passing ⚠️
- Template validation failures in DTO/Tool scaffolds
```

**Scope Clarification:**
- Issue #72: SCAFFOLD metadata rollout
- Issue #74: Template structure/quality fixes
- **Dependencies:** #72 enables #74 validation (needs metadata to validate)

**Recommendation:** Complete #72 first, then tackle #74 with full validation.

---

## Implementation Strategy

### Phase 1: Base Templates (High Impact)

**Scope:** 3 base templates → 11 children fixed automatically

**Files:**
1. `mcp_server/templates/base/base_component.py.jinja2`
2. `mcp_server/templates/base/base_document.md.jinja2`
3. `mcp_server/templates/base/base_test.py.jinja2`

**Format:**
```jinja
{# Python templates #}
# SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created_at }} path={{ output_path }}

{# Markdown templates #}
<!-- SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created_at }} path={{ output_path }} -->
```

**Validation:**
```powershell
# Scaffold a tool (uses base_component)
scaffold_artifact tool name="TestTool"

# Verify metadata inherited
Select-String -Path "backend/tools/test_tool.py" -Pattern "SCAFFOLD:"
# Expected: Match found ✅
```

**Effort:** 1-2 hours (3 templates + inheritance verification)

### Phase 2: Standalone Templates (Completion)

**Scope:** 9 standalone templates (2 already done)

**Critical Path:**
1. **generic.md** - Used for research/planning docs (this doc uses it!)
2. design.md - Design documents
3. worker.py - Worker scaffolds
4. adapter.py - Adapter scaffolds

**Lower Priority:**
5. dto_test.py, worker_test.py - Test scaffolds
6. tracking.md - Issue tracking
7. integration_test.py, unit_test.py - Test templates

**Validation:**
```powershell
# Scaffold research doc
scaffold_artifact research name="TestResearch"

# Verify metadata present
Select-String -Path "docs/development/test/research.md" -Pattern "SCAFFOLD:"
# Expected: Match found ✅
```

**Effort:** 2-3 hours (9 templates + verification)

### Phase 3: Discovery Tool Integration

**Scope:** Enable query_file_schema() with full template coverage

**Implementation:**
```python
# mcp_server/tools/query_file_schema.py
class QueryFileSchemaTool(BaseTool):
    """Discover file template metadata for content-aware editing."""
    
    async def execute(self, path: str) -> dict:
        # 1. Parse SCAFFOLD metadata (from Phase 1+2)
        frontmatter = parse_yaml_frontmatter(read_file(path))
        
        if not frontmatter or "template" not in frontmatter:
            return {"file_type": "non-scaffolded"}
        
        # 2. Introspect template schema (Issue #120 infrastructure)
        introspector = TemplateIntrospector()
        schema = introspector.get_schema(frontmatter["template"])
        
        return {
            "file_type": "scaffolded",
            "template_id": frontmatter["template"],
            "template_version": frontmatter["version"],
            "structure": schema,
            "edit_capabilities": ["ScaffoldEdit", "TextEdit"]
        }
```

**Validation:**
```python
# Test discovery on all template types
templates = ["dto", "worker", "research", "design", "tool"]
for template in templates:
    schema = query_file_schema(f"path/to/{template}.py")
    assert schema["file_type"] == "scaffolded"
    assert schema["template_id"] == template
```

**Effort:** 1-2 hours (leverages Issue #120 infrastructure)

### Phase 4: Documentation & Handoff

**Scope:** Document template metadata format and discovery patterns

**Deliverables:**
1. Update docs/reference/mcp/template_metadata_format.md
2. Add discovery examples to docs/reference/mcp/content_aware_editing.md
3. Update Issue #120 status: "Phase 0 COMPLETE"
4. Close Issue #121: "Superseded by #72"
5. Enable Issue #74: "Template quality validation"

**Effort:** 1 hour

---

## Timeline & Effort

| Phase | Scope | Effort | Dependencies |
|-------|-------|--------|--------------|
| Phase 1 | 3 base templates | 1-2h | Issue #120 Phase 1 (TemplateIntrospector) |
| Phase 2 | 9 standalone templates | 2-3h | Phase 1 complete |
| Phase 3 | Discovery tool | 1-2h | Phase 1+2 complete |
| Phase 4 | Documentation | 1h | Phase 3 complete |
| **Total** | **12 templates + tool + docs** | **5-8h** | Sequential execution |

**Critical Path:**
1. Base templates first (high leverage via inheritance)
2. generic.md next (unblocks current research workflow!)
3. Remaining standalone templates
4. Discovery tool integration
5. Documentation handoff

---

## Success Criteria

**Technical:**
- ✅ All 24 templates have SCAFFOLD metadata
- ✅ Audit script shows 24/24 pass rate
- ✅ query_file_schema() works for all template types
- ✅ Scaffolded files have template reference in frontmatter
- ✅ Issue #120 Phase 0 status: COMPLETE

**Architectural:**
- ✅ Templates function as SSOT (Config Over Code)
- ✅ Base template inheritance maximized (DRY)
- ✅ Template owns scaffolding + validation (SRP)
- ✅ SCAFFOLD metadata enables contract-driven editing

**Downstream:**
- ✅ Issue #121 closed as superseded
- ✅ Issue #74 unblocked (validation needs metadata)
- ✅ Future editing tools work out-of-the-box

---

## Risk Analysis

### Risk 1: Template Variable Availability

**Risk:** SCAFFOLD metadata requires variables (template_id, version, created_at) that may not be available in all scaffold contexts.

**Mitigation:**
- Review ScaffoldManager to ensure variables passed
- Add variables to artifact definitions in artifacts.yaml
- Default values for missing variables (e.g., version="1.0")

**Likelihood:** MEDIUM  
**Impact:** LOW (fixable in scaffold infrastructure)

### Risk 2: Inheritance Chain Complexity

**Risk:** Base template changes affect 11 children - unintended side effects possible.

**Mitigation:**
- Test scaffolding for each child template type after base update
- Use integration tests from Issue #52 (E2E scaffold + validate)
- Incremental rollout: base_component → verify 9 children → proceed

**Likelihood:** LOW  
**Impact:** MEDIUM (requires rollback if broken)

### Risk 3: Discovery Tool Performance

**Risk:** query_file_schema() must parse file + introspect template on every call.

**Mitigation:**
- Cache TemplateIntrospector schema results (templates don't change at runtime)
- Lightweight frontmatter parsing (YAML only at top of file)
- Agent best practice: Query once, batch edit N files

**Likelihood:** LOW  
**Impact:** LOW (acceptable for read-only tool)

---

## Dependencies

**Issue #120:**
- ✅ Phase 0: SCAFFOLD metadata format defined
- ✅ Phase 1: TemplateIntrospector + ScaffoldMetadataParser

**Issue #52:**
- ✅ TEMPLATE_METADATA format established
- ✅ LayeredTemplateValidator infrastructure
- ✅ Three-tier enforcement model

**artifacts.yaml:**
- Must contain template_id and version for all artifact types
- ScaffoldManager must pass these variables to templates

**Blocks:**
- Issue #121 (Content-Aware Edit Tool) - superseded by #72
- Issue #74 (Template Quality) - needs #72 metadata for validation

---

## Open Questions

### Q1: Should base_test.py get metadata despite having no children?

**Context:** base_test.py is orphaned (no templates extend it).

**Options:**
- A: Add metadata for consistency (future-proof)
- B: Skip (no current benefit)

**Recommendation:** Option A - consistency and potential future use.

### Q2: How to handle template versioning going forward?

**Context:** SCAFFOLD metadata includes version field.

**Options:**
- A: Manual version bumps in artifacts.yaml
- B: Automated versioning (git tag based)
- C: Semantic versioning with breaking changes

**Recommendation:** Start with Option A (manual), evolve to C if needed.

### Q3: Should discovery tool be read-only or include validation?

**Context:** query_file_schema() could validate file against template.

**Options:**
- A: Read-only (discovery only)
- B: Include validation results
- C: Separate validate_file() tool

**Recommendation:** Option A for #72, Option C for #74 (template quality).

---

## Next Steps

### Research Phase Transition

**Research Complete When:**
- ✅ Problem statement validated
- ✅ Architecture alignment confirmed
- ✅ Implementation strategy defined
- ✅ Success criteria established
- ✅ Risks identified and mitigated
- ✅ Dependencies mapped

**Transition to Planning:**
1. Break down phases into specific tasks
2. Define file changes for each template
3. Create testing strategy for inheritance validation
4. Specify commit sequence (atomic per phase)
5. Document rollback procedures

### Planning Phase Preview

**Goals:**
1. **Goal 1:** Update 3 base templates with SCAFFOLD metadata
2. **Goal 2:** Verify inheritance for 11 child templates
3. **Goal 3:** Update 9 standalone templates
4. **Goal 4:** Implement query_file_schema() tool
5. **Goal 5:** Integration testing (scaffold → discover → validate)
6. **Goal 6:** Documentation and handoff

**Testing Strategy:**
- Unit tests: SCAFFOLD metadata parsing
- Integration tests: Inheritance verification per child
- E2E tests: Scaffold → query_file_schema → edit workflow
- Quality gates: All 24 templates pass audit

---

## References

### Related Issues
- **Issue #120:** Template-Driven Validation - Phase 0 incomplete
- **Issue #121:** Content-Aware Edit Tool - Superseded by #72
- **Issue #52:** Template-Driven Validation Infrastructure - Foundation
- **Issue #74:** Template Quality Fixes - Blocked by #72

### Documentation
- docs/development/issue121/template-metadata-audit.md
- docs/development/issue121/template-inheritance-analysis.md
- docs/development/issue121/research-discovery-tool-analysis.md
- docs/development/issue52/research.md (SSOT architecture)
- docs/architecture/CORE_PRINCIPLES.md (Config Over Code, DRY, SRP)
- docs/coding_standards/CODE_STYLE.md (Style conventions)

### Code References
- mcp_server/templates/base/ (3 base templates)
- mcp_server/templates/components/ (13 component templates)
- mcp_server/templates/documents/ (6 document templates)
- mcp_server/templates/tests/ (2 test templates)
- mcp_server/validation/template_analyzer.py (TemplateIntrospector)
- mcp_server/validation/layered_template_validator.py (Validation)

---

**Research Status:** ✅ COMPLETE  
**Next Phase:** Planning  
**Estimated Effort:** 5-8 hours total  
**Architecture Impact:** High (enables SSOT, completes #120 Phase 0, unblocks #74)
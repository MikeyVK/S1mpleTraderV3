# Issue #52 Research: Template-Driven Validation Architecture

**Issue:** Migrate validation rules to template metadata (SSOT)  
**Epic:** #49 - MCP Platform Configurability  
**Status:** Complete  
**Date:** 2025-12-31  
**Author:** AI Agent

---

## Executive Summary

**The Problem:**
Validation rules are hardcoded in `RULES` dict (template_validator.py), creating a duplicate source of truth. Templates generate code via scaffolding, but validation rules live separately. When templates change, validation must be manually updated.

**The Solution:**
Use templates as Single Source of Truth (SSOT) with layered enforcement:
- **Base templates** enforce format (STRICT - imports, docstrings, structure)
- **Specific templates** define architecture + guidelines (MIXED - contracts + best practices)
- Templates contain metadata frontmatter with validation rules

**The Innovation:**
Three-tier enforcement model separates format (universally strict), architecture (system-critical), and guidelines (best practices), preventing both rigidity and chaos.

**Impact:**
- ✅ Templates become authoritative source for scaffolding AND validation
- ✅ No duplicate maintenance (template change → validation follows)
- ✅ Flexible enforcement (strict where needed, guided where helpful)
- ✅ Agent guidance embedded (templates teach what content belongs where)

---

## Scope: Template-Driven Validation System

**What This Issue Delivers:**

**Phase 1: Template Foundation**
- ✅ Create missing critical templates (research.md, planning.md, unit_test.py)
- ✅ Fix worker template (two-phase initialization pattern)
- ✅ Add metadata frontmatter to core templates (worker, dto, tool)
- ✅ Define three-tier enforcement model (format, architectural, guideline)

**Phase 2: Validation Infrastructure**
- ✅ Build TemplateAnalyzer (reads metadata from templates)
- ✅ Build LayeredTemplateValidator (enforces format → architectural → guidelines)
- ✅ Integrate with SafeEditTool and ValidatorRegistry
- ✅ Remove hardcoded RULES dict

**Phase 3: Documentation & Guidance**
- ✅ Document template metadata format
- ✅ Add agent guidance to document templates
- ✅ Create template quality standards
- ✅ Define template governance process (quarterly review)

**What This Issue Does NOT Deliver:**
- ❌ validation.yaml config file (would create duplicate SSOT)
- ❌ All 21 templates with metadata (only core 6: worker, dto, tool, research, planning, unit_test)
- ❌ AST-based validation (keep current regex, improve incrementally)
- ❌ Epic #18 enforcement tooling (depends on this foundation)

---

## Problem Statement

### Current Architecture: Duplicate Sources of Truth

**Templates (Scaffolding):**
```
mcp_server/templates/components/worker.py.jinja2
└── Generates: class {{name}} with process() method
```

**Validation Rules (Separate):**
```python
mcp_server/validators/template_validator.py
RULES = {
    "worker": {
        "required_methods": ["execute"],  # ← Hardcoded!
        "required_imports": ["BaseWorker"]
    }
}
```

**The Problem:**
1. Template changes → Manual validation update required
2. Validation rules don't reflect actual template output
3. No single authoritative source for "what is a Worker?"
4. Templates and validators can drift apart

### Discovery: Template Quality Issues

**Template Inventory:** 21 templates (73KB total)

**Critical Gaps Found:**
1. ❌ No research.md template (5+ research docs exist in codebase)
2. ❌ No planning.md template (4+ planning docs exist in codebase)
3. ❌ No unit_test.py template (dozens of unit tests exist)
4. ⚠️ Worker template uses outdated pattern (single-phase init, should be IWorkerLifecycle)

**Quality Assessment:**
- ⭐⭐⭐⭐⭐ dto.py.jinja2 - Excellent, matches backend/dtos patterns perfectly
- ⭐⭐⭐⭐ tool.py.jinja2 - Good, clean BaseTool pattern
- ⭐⭐⭐⭐ base_test.py.jinja2 - Excellent structure, enforces conventions
- ⚠️ worker.py.jinja2 - Outdated, doesn't match IWorkerLifecycle protocol

**Code Pattern Analysis:**
```python
# Actual backend pattern (backend/core/interfaces/worker.py):
class IWorkerLifecycle(Protocol):
    """Two-phase initialization:
    1. __init__(build_spec) - Construction
    2. initialize(strategy_cache) - Runtime injection
    """

# Current template generates (WRONG):
def __init__(self, strategy_cache, deps):
    self._strategy_cache = strategy_cache  # ← Should be None, injected in initialize()

# Should generate:
def __init__(self, build_spec: BuildSpec):
    self._manifest = build_spec.manifest
    self._strategy_cache: IStrategyCache | None = None
    
def initialize(self, strategy_cache: IStrategyCache):
    self._strategy_cache = strategy_cache
```

### Architectural Insight: Format vs Content

**User Requirement:**
"I want strict enforcement of format, but flexibility in content. Format is universal (imports, docstrings), but content varies by purpose (research vs planning vs design)."

**Example:**
- **Format (STRICT):** All docs must have frontmatter, separator, grouped links
- **Content (GUIDED):** Research docs analyze problems, planning docs define goals
  - Research doc with code implementation → WARNING (wrong phase)
  - Planning doc without Goals section → WARNING (guideline)

This led to discovery of **three-tier enforcement model**.

---

## Research Findings

### Finding 1: Templates Already Use Inheritance

**Current Structure:**
```
base/base_component.py.jinja2     ← Base format template
    ↓ extends
components/worker.py.jinja2       ← Specific component template
    ↓ extends
components/tool.py.jinja2         ← Specific component template
```

**Insight:** Inheritance naturally maps to enforcement tiers!
- Base templates → Format enforcement (STRICT)
- Specific templates → Architectural + Guidelines (MIXED)

### Finding 2: Three Types of Rules

**Analysis of RULES dict and template patterns:**

**Type 1: Format Rules (Universal)**
- Import order: stdlib → third-party → local
- Docstring presence and structure
- Type hints on all functions
- File header with metadata

**Violation Impact:** Inconsistent codebase, harder to read/maintain
**Severity:** ERROR (always enforce)
**Location:** Base templates

**Type 2: Architectural Rules (System-Critical)**
- Worker must inherit BaseWorker[InputDTO, OutputDTO]
- Worker must implement process() as async
- Tool must have name, description, input_schema properties
- DTO must use Pydantic BaseModel with frozen=True

**Violation Impact:** System breaks, runtime errors, protocol violations
**Severity:** ERROR (always enforce)
**Location:** Specific templates (strict section)

**Type 3: Guidelines (Best Practices)**
- Worker class name ends with "Worker" suffix
- DTO fields ordered: causality → id → timestamp → data
- Docstrings include "Responsibilities" section
- Research docs have "Executive Summary" section

**Violation Impact:** Style inconsistency, harder to navigate
**Severity:** WARNING (guide, don't block)
**Location:** Specific templates (guidelines section)

### Finding 3: Agent Guidance Needed

**Problem:** AI agents may confuse document purposes.

**Examples:**
- Agent puts implementation code in research doc (should be analysis)
- Agent puts problem analysis in planning doc (should be goals)
- Agent uses ASCII art in design doc (should be Mermaid)

**Solution:** Embed guidance in template metadata.

**Template Metadata Structure:**
```jinja
{# TEMPLATE_METADATA
enforcement: GUIDELINE
level: content
extends: base/base_document.md.jinja2

purpose: |
  Research documents analyze problems and gather information.
  They answer: "What is the situation?" and "What should we do?"

content_guidance:
  includes:
    - Problem analysis and root cause investigation
    - Findings from code/documentation analysis
    - Recommendations for next steps
  
  excludes:
    - Implementation details (that's planning phase)
    - Code designs or class structures (that's design docs)
    - Test plans (that's planning phase)

agent_hint: |
  Focus on WHY and WHAT, not HOW. You're a detective gathering
  evidence, not an architect designing solutions.

validates:
  guidelines:
    - recommended_sections: ["Executive Summary", "Problem Statement", "Recommendations"]
    - content_type: "Analysis and investigation, not implementation"
#}
```

**Validator Response:**
```json
{
  "warnings": [{
    "message": "Research doc contains implementation code",
    "hint": "Research focuses on analysis. Save implementation for planning phase."
  }],
  "agent_hint": "Focus on WHY and WHAT, not HOW. Think detective, not architect.",
  "content_guidance": {
    "includes": ["Problem analysis", "Findings", "Recommendations"],
    "excludes": ["Implementation details", "Code designs"]
  }
}
```

### Finding 4: Jinja2 Template Introspection Capabilities

**Investigation:** Can Jinja2 read template structure programmatically?

**Findings:**
- ✅ `Environment.parse()` - Parse template to AST without rendering
- ✅ `meta.find_undeclared_variables()` - Extract variables template expects
- ✅ `meta.find_referenced_templates()` - Find extends/includes
- ❌ Cannot determine output without rendering (e.g., `{{name}}Worker` → can't resolve to "SignalDetectorWorker")

**Solution:** Hybrid approach
- **Static analysis:** Jinja2 AST for template structure, inheritance chains
- **Metadata parsing:** Regex extract frontmatter YAML from comments
- **Pattern matching:** Regex on template source for output patterns (class {{name}}Worker)

**Implementation:**
```python
from jinja2 import Environment
from jinja2.meta import find_undeclared_variables
import yaml
import re

def extract_template_metadata(template_path: Path) -> dict:
    """Extract validation metadata from template."""
    source = template_path.read_text()
    env = Environment()
    
    # Parse Jinja2 AST
    ast = env.parse(source)
    variables = find_undeclared_variables(ast)
    
    # Extract frontmatter metadata
    match = re.search(r'\{#\s*TEMPLATE_METADATA\s*(.*?)\s*#\}', source, re.DOTALL)
    if not match:
        return {"variables": list(variables)}
    
    metadata_yaml = match.group(1)
    metadata = yaml.safe_load(metadata_yaml)
    metadata["variables"] = list(variables)
    
    # Extract inheritance
    base_template = None
    extends_match = re.search(r'\{%\s*extends\s+"([^"]+)"\s*%\}', source)
    if extends_match:
        metadata["extends"] = extends_match.group(1)
    
    return metadata
```

### Finding 5: Template Governance Concerns

**User Concern:**
"How do we prevent template maintenance from becoming a daily job? I want quality but fear rigidity."

**Analysis:**
- Current: 21 templates exist
- Risk: Template explosion (50+ templates becomes unmanageable)
- Risk: Over-enforcement (blocking innovation)
- Risk: Constant updates (templates too specific)

**Mitigation Strategies:**

**1. Template Growth Control**
```yaml
# Maximum templates per category
limits:
  component_templates: 10
  document_templates: 5
  test_templates: 3

# Rule of Three: Pattern must appear 3+ times before creating template
```

**2. Escape Hatch Mechanism**
```python
# In source file:
# TEMPLATE_OVERRIDE: strict
# Reason: Experimenting with async generator pattern
# Issue: #123
# Approved-by: architect

# Validator logs override for quarterly review
```

**3. Template Versioning**
```jinja
{# TEMPLATE_METADATA
version: "2.0"
backwards_compatible: false
migration_guide: "docs/migrations/worker_v1_to_v2.md"
#}

# Validator accepts both v1.0 and v2.0, validates appropriately
```

**4. Quarterly Review Process**
```markdown
# Template Health Check (Q1 2025)

Usage Stats:
- worker.py: 47 files ✅
- service_orchestrator.py: 0 files ❌ (REMOVE)

Override Analysis:
- 3 overrides (all justified)
- No pattern suggesting template too strict

Template Updates:
- worker.py v2.0: IWorkerLifecycle pattern
```

---

## Proposed Architecture

### Three-Tier Layered Enforcement

```
┌─────────────────────────────────────────────────────────────┐
│ TIER 1: BASE TEMPLATES (Format - STRICT)                    │
│ ============================================================ │
│ Validates: Import order, docstrings, type hints, structure  │
│ Severity: ERROR (blocks save)                                │
│ Rationale: Universal code quality, non-negotiable           │
│                                                              │
│ Examples:                                                    │
│ - base/base_component.py.jinja2  (Python format)            │
│ - base/base_test.py.jinja2       (Test format)              │
│ - base/base_document.md.jinja2   (Doc format)               │
└─────────────────────────────────────────────────────────────┘
                              ▼ extends
┌─────────────────────────────────────────────────────────────┐
│ TIER 2: SPECIFIC TEMPLATES (Architectural - MIXED)          │
│ ============================================================ │
│ STRICT Section: Architectural rules (breaks system)         │
│   - Base class inheritance                                   │
│   - Required methods with signatures                         │
│   - Protocol compliance                                      │
│   Severity: ERROR (blocks save)                              │
│                                                              │
│ GUIDELINES Section: Best practices (doesn't break)          │
│   - Naming conventions                                       │
│   - Docstring format                                         │
│   - Field ordering                                           │
│   Severity: WARNING (saves, notifies)                        │
│                                                              │
│ Examples:                                                    │
│ - components/worker.py.jinja2    (strict + guidelines)      │
│ - components/dto.py.jinja2       (strict + guidelines)      │
│ - components/tool.py.jinja2      (strict + guidelines)      │
└─────────────────────────────────────────────────────────────┘
                              ▼ extends
┌─────────────────────────────────────────────────────────────┐
│ TIER 3: DOCUMENT TEMPLATES (Content Guidance - LOOSE)       │
│ ============================================================ │
│ Format (from base): STRICT via base_document.md.jinja2      │
│   - Frontmatter presence/fields                              │
│   - Separator structure                                      │
│   - Links grouped at end                                     │
│                                                              │
│ Content: GUIDELINES with agent hints                         │
│   - Recommended sections                                     │
│   - Content type guidance (what belongs in this doc)         │
│   - Agent hints (focus on WHY vs HOW)                        │
│   Severity: WARNING (never blocks)                           │
│                                                              │
│ Examples:                                                    │
│ - documents/research.md.jinja2   (analysis, not code)       │
│ - documents/planning.md.jinja2   (goals, not details)       │
│ - documents/design.md.jinja2     (structure, use Mermaid)   │
└─────────────────────────────────────────────────────────────┘
```

### Metadata Format Specification

**Base Template (Format Enforcement):**
```jinja
{# TEMPLATE_METADATA
enforcement: STRICT
level: format
validates:
  strict:
    - import_order: "stdlib → third-party → local"
    - docstring_presence: required
    - type_hints: required
    - file_header: required
#}
```

**Specific Template (Architectural + Guidelines):**
```jinja
{# TEMPLATE_METADATA
enforcement: ARCHITECTURAL
level: content
extends: base/base_component.py.jinja2
validates:
  strict:
    - base_class: "BaseWorker[InputDTO, OutputDTO]"
    - required_methods:
        - name: "__init__"
          params: ["build_spec: BuildSpec"]
        - name: "initialize"
          params: ["strategy_cache: IStrategyCache"]
        - name: "process"
          async: true
          params: ["input_data: InputDTO"]
          returns: "OutputDTO"
    - required_imports:
        - "backend.core.interfaces.base_worker.BaseWorker"
        - "backend.core.interfaces.worker.IWorkerLifecycle"
  guidelines:
    - naming_convention: "No enforced suffix (flexible)"
    - docstring_format: "Responsibilities section recommended"
#}
```

**Document Template (Content Guidance):**
```jinja
{# TEMPLATE_METADATA
enforcement: GUIDELINE
level: content
extends: base/base_document.md.jinja2

purpose: |
  Research documents analyze problems and gather information.
  They answer: "What is the situation?" and "What should we do?"

content_guidance:
  includes:
    - Problem analysis and root cause
    - Findings from investigation
    - Recommendations for next steps
  excludes:
    - Implementation details (that's planning)
    - Code designs (that's design docs)

agent_hint: |
  Focus on WHY and WHAT, not HOW. Think detective, not architect.

validates:
  guidelines:
    - recommended_sections: ["Executive Summary", "Problem Statement", "Recommendations"]
    - content_type: "Analysis, not implementation"
#}
```

### Validation Flow

```python
class LayeredTemplateValidator:
    def validate(self, file_path: Path, template: Template) -> ValidationResult:
        results = []
        
        # Layer 1: Base template format (STRICT - blocks on error)
        base = self._get_base_template(template)
        if base:
            format_result = self._validate_format(file_path, base)
            if not format_result.passed:
                return format_result  # Stop immediately
            results.append(format_result)
        
        # Layer 2: Architectural rules (STRICT - blocks on error)
        arch_result = self._validate_architectural(file_path, template)
        if not arch_result.passed:
            return arch_result  # Stop immediately
        results.append(arch_result)
        
        # Layer 3: Guidelines (LOOSE - warnings only, never blocks)
        guide_result = self._validate_guidelines(file_path, template)
        results.append(guide_result)  # Always continues
        
        return self._combine_results(results)
```

### Template Priority Matrix

**Phase 1 (Issue #52): Core 6 Templates**

| Template | Tier | Enforcement | Priority | Rationale |
|----------|------|-------------|----------|-----------|
| base_component.py | Base | STRICT | CRITICAL | Universal Python format |
| base_test.py | Base | STRICT | CRITICAL | Universal test format |
| base_document.md | Base | STRICT | CRITICAL | Universal doc format |
| worker.py | Specific | MIXED | HIGH | Most used component (47+ files) |
| dto.py | Specific | MIXED | HIGH | Most used data structure (89+ files) |
| tool.py | Specific | MIXED | HIGH | MCP platform core |

**Phase 2 (Post #52): Additional Templates**

| Template | Tier | Enforcement | Priority | Condition |
|----------|------|-------------|----------|-----------|
| research.md | Document | GUIDELINE | HIGH | Every issue needs research |
| planning.md | Document | GUIDELINE | HIGH | Every issue needs planning |
| unit_test.py | Specific | MIXED | MEDIUM | Many unit tests exist |
| integration_test.py | Specific | MIXED | LOW | Wait for 3+ examples |
| adapter.py | Specific | MIXED | LOW | Wait for 3+ examples |

**Deferred (Rule of Three):**
- service_*.py templates (0 usage in backend/)
- interface.py template (verify usage first)
- resource.py, schema.py templates (low priority)

---

## Recommendations

### Immediate Actions (Issue #52 Scope)

**1. Create Missing Base Template (CRITICAL)**
```
✅ Create: base/base_document.md.jinja2
   - Frontmatter enforcement (STRICT)
   - Separator structure (STRICT)
   - Links grouped at end (STRICT)
   - Content agnostic (extended by specific docs)
```

**2. Fix Worker Template (HIGH)**
```
✅ Update: components/worker.py.jinja2
   - Implement IWorkerLifecycle two-phase initialization
   - Match backend/core/interfaces/worker.py pattern
   - Add metadata with strict + guidelines sections
```

**3. Add Metadata to Core Templates (HIGH)**
```
✅ Update: components/dto.py.jinja2
   - Add metadata frontmatter
   - Strict: Pydantic BaseModel, frozen=True
   - Guidelines: Field ordering (causality → id → timestamp)

✅ Update: components/tool.py.jinja2
   - Add metadata frontmatter
   - Strict: BaseTool inheritance, required properties
   - Guidelines: Docstring format
```

**4. Create Document Templates (HIGH)**
```
✅ Create: documents/research.md.jinja2
   - Extends base_document.md.jinja2
   - Content guidance for analysis/investigation
   - Agent hint: "Detective, not architect"

✅ Create: documents/planning.md.jinja2
   - Extends base_document.md.jinja2
   - Content guidance for goals/sequencing
   - Agent hint: "Project manager, not developer"
```

**5. Build Validation Infrastructure (CRITICAL)**
```
✅ Create: mcp_server/validators/template_analyzer.py
   - extract_template_metadata(template_path)
   - get_base_template(template)
   - get_inheritance_chain(template)

✅ Update: mcp_server/validators/template_validator.py
   - Implement LayeredTemplateValidator
   - Replace RULES dict with template metadata
   - Support three-tier enforcement

✅ Update: mcp_server/tools/safe_edit_tool.py
   - Use template metadata for validation
   - Pass agent hints to response
```

**6. Remove Hardcoded Rules (CLEANUP)**
```
✅ Delete: RULES dict from template_validator.py (30 lines)
✅ Update: Tests to use template metadata
✅ Update: ValidatorRegistry to load from templates
```

### Template Quality Standards

**Before Creating New Template:**
1. ✅ Pattern appears 3+ times in codebase (Rule of Three)
2. ✅ Compare against 3+ real examples
3. ✅ Generate sample and verify quality gates pass
4. ✅ Add metadata with validation rules
5. ✅ Document all template variables in header
6. ✅ Test with scaffold_component tool

**Template Metadata Checklist:**
- [ ] Enforcement level specified (STRICT/ARCHITECTURAL/GUIDELINE)
- [ ] Inheritance chain declared (extends field)
- [ ] Validation rules categorized (strict vs guidelines)
- [ ] Agent hints provided (for document templates)
- [ ] Content guidance specified (includes/excludes)
- [ ] Version specified (for migration tracking)

### Template Governance

**Quarterly Review Process:**
```markdown
# Template Health Check Template

## Usage Statistics
- List all templates with file counts
- Identify unused templates (0 files) → Consider removal
- Identify heavily used (50+) → Ensure high quality

## Override Analysis
- Review all TEMPLATE_OVERRIDE instances
- Check for patterns (same reason multiple times)
- Pattern detected → Template may be too strict

## Template Updates
- List templates needing updates (new patterns emerged)
- Create migration guide for breaking changes
- Update version numbers

## New Template Requests
- Evaluate requests against Rule of Three
- Architect approval required
- Document decision rationale
```

**Growth Control:**
```yaml
template_limits:
  base_templates: 5       # Format universals (rarely change)
  component_templates: 10 # Architectural patterns
  document_templates: 5   # Content guidance
  test_templates: 3       # Test patterns

# Total target: ~20-25 templates (manageable)
# Current: 21 templates (healthy)
# After Issue #52: 24 templates (within limits)
```

**Escape Hatch Usage:**
```python
# In experimental code:
# TEMPLATE_OVERRIDE: architectural
# Reason: Prototyping async generator streaming pattern
# Issue: #145
# Approved: architect (2025-12-31)
# Review: Q2-2026

# This allows innovation while maintaining audit trail
```

### Success Criteria

**Must Have:**
- [ ] base_document.md.jinja2 created
- [ ] worker.py.jinja2 fixed (IWorkerLifecycle)
- [ ] Metadata added to: worker, dto, tool
- [ ] research.md.jinja2 created with agent guidance
- [ ] planning.md.jinja2 created with agent guidance
- [ ] TemplateAnalyzer extracts metadata from templates
- [ ] LayeredTemplateValidator enforces three tiers
- [ ] RULES dict removed from code
- [ ] All tests passing (30+ tests)
- [ ] Pylint 10/10 (no exceptions)

**Quality Gates:**
- [ ] Templates match actual codebase patterns
- [ ] Generated code passes quality gates
- [ ] No hardcoded validation rules outside templates
- [ ] Documentation complete (metadata format, governance)
- [ ] Agent hints tested with actual agent workflows

**Governance:**
- [ ] Template growth limits documented
- [ ] Quarterly review process defined
- [ ] Escape hatch mechanism implemented
- [ ] Template versioning strategy defined

---

## Impact Assessment

### Effort Estimation

**Original Scope:** Migrate RULES dict to validation.yaml (1-2 days)  
**Revised Scope:** Template-driven SSOT architecture (3-4 days)

**Breakdown:**
- Day 1: Template creation and fixes
  - Create base_document.md.jinja2 (2 hours)
  - Fix worker.py.jinja2 (2 hours)
  - Create research.md, planning.md (2 hours)
  - Add metadata to worker, dto, tool (2 hours)

- Day 2: Validation infrastructure
  - Build TemplateAnalyzer (4 hours)
  - Build LayeredTemplateValidator (4 hours)

- Day 3: Integration and testing
  - Update SafeEditTool (2 hours)
  - Remove RULES dict (1 hour)
  - Write tests (3 hours)
  - Quality gates (2 hours)

- Day 4: Documentation and polish
  - Document metadata format (2 hours)
  - Document governance process (2 hours)
  - Agent guidance testing (2 hours)
  - Buffer for issues (2 hours)

### Benefits

**Immediate:**
- ✅ Single source of truth (templates)
- ✅ Template changes automatically update validation
- ✅ No manual synchronization needed
- ✅ Cleaner architecture (no duplicate rules)

**Long-term:**
- ✅ Scalable template growth (governance prevents explosion)
- ✅ Flexible enforcement (strict where needed, guided where helpful)
- ✅ Agent-friendly (guidance embedded in templates)
- ✅ Maintainable (quarterly review, not daily updates)

**Foundation for Epic #18:**
- ✅ Enables TDD enforcement (templates define contracts)
- ✅ Enables quality gates (template compliance checks)
- ✅ Enables architectural validation (protocol compliance)

### Risks and Mitigation

**Risk 1: Template Complexity**
- Concern: Metadata makes templates harder to maintain
- Mitigation: Metadata is optional YAML in comments (doesn't affect rendering)
- Mitigation: Clear documentation and examples

**Risk 2: Over-Enforcement**
- Concern: Strict rules block innovation
- Mitigation: Three-tier model (guidelines don't block)
- Mitigation: Escape hatch with approval process

**Risk 3: Template Explosion**
- Concern: 50+ templates becomes unmanageable
- Mitigation: Growth limits (20-25 templates target)
- Mitigation: Rule of Three (3+ occurrences before template)
- Mitigation: Quarterly review removes unused templates

**Risk 4: Migration Burden**
- Concern: Existing code doesn't match new templates
- Mitigation: Template versioning (v1.0 and v2.0 both valid)
- Mitigation: Gradual migration (no breaking changes)
- Mitigation: Migration guides for major updates

---

## Next Steps

### Phase Transition

**Research Phase Complete:**
- ✅ Problem analyzed (duplicate SSOT)
- ✅ Solution designed (template-driven validation)
- ✅ Architecture specified (three-tier enforcement)
- ✅ Templates inventoried and assessed
- ✅ Gaps identified and prioritized
- ✅ Governance strategy defined

**Transition to Planning Phase:**
- Create planning.md with implementation goals
- Define file changes and affected components
- Specify testing strategy (30+ tests)
- Create rollout sequence
- Define success metrics

### Planning Phase Preview

**Implementation Goals:**
1. Template Infrastructure (base templates, metadata)
2. Analyzer Infrastructure (TemplateAnalyzer)
3. Validator Infrastructure (LayeredTemplateValidator)
4. Integration (SafeEditTool, ValidatorRegistry)
5. Cleanup (remove RULES dict)
6. Documentation (metadata format, governance)

**Testing Strategy:**
- Unit tests: TemplateAnalyzer metadata extraction
- Unit tests: LayeredTemplateValidator enforcement logic
- Integration tests: SafeEditTool with template validation
- End-to-end tests: Scaffold → Edit → Validate cycle
- Quality gates: Pylint 10/10, 100% coverage

**Rollout Plan:**
- Phase 1: Non-breaking additions (new templates, analyzer)
- Phase 2: Integration updates (validator, safe_edit_tool)
- Phase 3: Deprecation (RULES dict removal)
- Phase 4: Documentation and governance

---

## References

### Code Analysis
- backend/core/interfaces/worker.py - IWorkerLifecycle protocol
- backend/dtos/strategy/signal.py - DTO pattern example
- mcp_server/validators/template_validator.py - Current RULES dict
- mcp_server/templates/ - All 21 existing templates

### Documentation
- docs/development/issue39/research.md - Research doc pattern
- docs/development/issue39/planning.md - Planning doc pattern
- docs/architecture/CORE_PRINCIPLES.md - Architectural principles

### Related Issues
- Issue #50: workflows.yaml configuration (three-tier pattern established)
- Issue #51: labels.yaml configuration (three-tier pattern refined)
- Epic #49: MCP Platform Configurability (parent epic)
- Epic #18: TDD Enforcement Tooling (depends on this foundation)

---

**Research Complete.** Ready for planning phase transition.

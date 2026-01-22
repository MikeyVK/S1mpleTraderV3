# Template Library Management - Base Template Architecture Redesign

<!-- SCAFFOLD: template=research version=1.0 created=2026-01-22T17:00:00Z path=docs/development/issue72/research.md -->

**Issue:** #72  
**Epic:** Template Library Management  
**Status:** Research Phase  
**Date:** 2026-01-22  
**Architectural Principles:** Config Over Code, SSOT, DRY, SRP

---

## Executive Summary

**Problem:** Issue #120 Phase 0 incomplete (8% done) + current base template architecture violates DRY principle by requiring SCAFFOLD metadata duplication across 3 base templates.

**Root Cause:** Base template architecture was designed tactically (per-language) rather than strategically (universal artifact taxonomy).

**Decision:** Redesign base template hierarchy using **universal artifact dimensions** to enable:
- ✅ **Single SCAFFOLD metadata definition** (DRY - define once, inherit everywhere)
- ✅ **Language-agnostic extensibility** (Python today, C#/TypeScript/Go tomorrow)
- ✅ **Template inheritance without duplication** (DRY between bases)
- ✅ **Config Over Code** (templates as SSOT, not hardcoded logic)

**Solution:** Multi-tier base template architecture with **orthogonal dimensions**:
1. **Tier 0 (Universal):** `base_artifact.jinja2` - SCAFFOLD metadata + lifecycle (ALL artifacts)
2. **Tier 1 (Format):** `base_code.jinja2`, `base_document.jinja2` - Format-specific structure
3. **Tier 2 (Language):** `base_python.jinja2`, `base_markdown.jinja2` - Syntax-specific features
4. **Tier 3 (Specialization):** Current templates extend appropriate tier

**Impact:** 24 templates → 1 SCAFFOLD definition (DRY), extensible to 100+ templates across languages.

---

## Problem Analysis

### Current Architecture: Tactical Design

**Existing base templates (3):**
```
base/
├── base_component.py.jinja2    # Python components (9 children)
├── base_document.md.jinja2     # Markdown docs (2 children)
└── base_test.py.jinja2         # Python tests (0 children - orphaned)
```

**Issues with current design:**

1. **DRY Violation:** SCAFFOLD metadata must be duplicated 3 times
   ```jinja
   {# base_component.py.jinja2 #}
   # SCAFFOLD: template={{ template_id }} ...
   
   {# base_document.md.jinja2 #}
   <!-- SCAFFOLD: template={{ template_id }} ... -->
   
   {# base_test.py.jinja2 #}
   # SCAFFOLD: template={{ template_id }} ...  # DUPLICATE!
   ```

2. **Limited Extensibility:** What about TypeScript? C#? Java? Go?
   - Need `base_typescript.jinja2` → duplicate SCAFFOLD metadata AGAIN
   - Need `base_csharp.jinja2` → duplicate SCAFFOLD metadata AGAIN
   - Result: N languages = N duplications (anti-pattern!)

3. **Missing Orthogonal Dimensions:** Current bases mix concerns:
   - `base_component.py` = Python syntax + code structure + component specifics
   - Should separate: artifact metadata ← code structure ← language syntax ← specialization

4. **No Cross-Language Reuse:** Document concepts (research, design, architecture) are universal but implementation is language-specific

### Core Architectural Principles (docs/coding_standards/)

**From CORE_PRINCIPLES.md:**
- **Config Over Code:** Configuration drives behavior, not hardcoded logic
- **DRY (Don't Repeat Yourself):** Single source of truth, no duplication
- **SRP (Single Responsibility Principle):** Each template has ONE concern
- **Contract-Driven Development:** Types and interfaces define contracts

**From ARCHITECTURAL_SHIFTS.md:**
- Templates are SSOT for both scaffolding AND validation
- Configuration files (artifacts.yaml) drive template selection
- Inheritance enables reuse without duplication

**Issue #72 must align with these principles!**

---

## Deep Research: Universal Artifact Taxonomy

### Research Question

**What are the FUNDAMENTAL dimensions of artifacts that software development agents scaffold?**

Context:
- Current: 17 artifact types (Python-only)
- Future: 100+ artifact types (multi-language)
- Scope: MCP server as compiled VS Code extension (C#, TypeScript, Java, Go, Rust, etc.)

### Artifact Dimension Analysis

**Dimension 1: Artifact Lifecycle** (UNIVERSAL - all artifacts)
```
Properties:
- template_id: Artifact type identifier
- version: Template semantic version
- created: Scaffolding timestamp
- path: File system location
- state: Lifecycle state (CREATED, MODIFIED, DEPRECATED)
```

**Dimension 2: Format Category** (CODE vs DOCUMENT)
```
CODE:
- Executable/compilable
- Has imports/dependencies
- Type-checked
- Test coverage required
- Examples: Python, C#, TypeScript

DOCUMENT:
- Human-readable
- Structured sections
- Links/references
- Version control metadata
- Examples: Markdown, reStructuredText, AsciiDoc
```

**Dimension 3: Language/Syntax** (Python, C#, TypeScript, Markdown, etc.)
```
PYTHON:
- Comment: #
- Docstring: """
- Imports: from/import
- Type hints: : Type

C#:
- Comment: //
- Docstring: ///
- Imports: using
- Type hints: Type name

TYPESCRIPT:
- Comment: //
- Docstring: /** */
- Imports: import/from
- Type hints: : Type

MARKDOWN:
- Comment: <!-- -->
- Sections: ##
- Links: [text](url)
- Code blocks: ```
```

**Dimension 4: Artifact Specialization** (Component, Document, Test)
```
COMPONENT (business logic):
- Worker, Adapter, Service, DTO
- Has dependencies
- Lifecycle methods
- Domain-specific contracts

DOCUMENT (knowledge):
- Research, Planning, Design, Architecture
- Structured sections
- Decision records
- Cross-references

TEST (validation):
- Unit, Integration, E2E
- Fixtures/mocks
- Assertions
- Coverage tracking
```

### Cross-Dimensional Matrix

| Artifact | Lifecycle | Format | Language | Specialization |
|----------|-----------|---------|----------|----------------|
| Worker | ✅ | CODE | Python | Component |
| DTO | ✅ | CODE | Python | Component |
| Research | ✅ | DOCUMENT | Markdown | Document |
| Unit Test | ✅ | CODE | Python | Test |
| TypeScript Worker | ✅ | CODE | TypeScript | Component |
| C# Service | ✅ | CODE | C# | Component |
| Go Adapter | ✅ | CODE | Go | Component |

**Key Insight:** Current base templates mix Dimension 2 (Format) + Dimension 3 (Language) + Dimension 4 (Specialization), **missing Dimension 1 (Lifecycle) entirely!**

---

## Proposed Solution: Multi-Tier Base Template Hierarchy

### Architecture Design

```
Tier 0 (Universal - ALL artifacts)
├── base_artifact.jinja2
│   └── SCAFFOLD metadata (template_id, version, created, path)
│   └── Artifact lifecycle contract
│   └── NO language/format specifics
│
Tier 1 (Format Category)
├── base_code.jinja2 (extends base_artifact)
│   └── Code-specific: imports, dependencies, type hints
│   └── Test generation hooks
│
└── base_document.jinja2 (extends base_artifact)
    └── Document-specific: sections, links, metadata headers
    └── NO base_code concepts (orthogonal!)

Tier 2 (Language/Syntax)
├── base_python.jinja2 (extends base_code)
│   └── Python syntax: # comments, """ docstrings, from/import
│   └── Python tooling: type hints, Pylint pragmas
│
├── base_typescript.jinja2 (extends base_code)
│   └── TypeScript syntax: // comments, /** */ docstrings, import/from
│   └── TypeScript tooling: type annotations, ESLint pragmas
│
└── base_markdown.jinja2 (extends base_document)
    └── Markdown syntax: <!-- comments, ## sections, [links]
    └── Frontmatter: YAML/TOML metadata

Tier 3 (Specialization)
├── base_python_component.jinja2 (extends base_python)
│   └── Component patterns: dependencies, layer annotations
│
├── base_python_test.jinja2 (extends base_python)
│   └── Test patterns: fixtures, assertions, coverage
│
└── Current 24 templates extend appropriate tier
```

### Inheritance Flow Example: Worker Template

```jinja
{# components/worker.py.jinja2 #}
{% extends "base/base_python_component.jinja2" %}

{# Inherits from base_python_component:
   - Component patterns (dependencies, layer annotations)
   
   Which extends base_python:
   - Python syntax (# comments, """ docstrings, imports)
   
   Which extends base_code:
   - Code structure (imports section, type hints)
   
   Which extends base_artifact:
   - SCAFFOLD metadata (template_id, version, created, path) ← DRY!
#}

{% block template_id %}worker{% endblock %}
{% block specialization %}
class {{ name }}Worker(BaseWorker[{{ input_dto }}, {{ output_dto }}]):
    """{{ description }}."""
    
    async def process(self, input_data: {{ input_dto }}) -> {{ output_dto }}:
        # Worker logic
{% endblock %}
```

**Result:** Worker template gets SCAFFOLD metadata **automatically** without duplication!

### DRY Achievement: Single SCAFFOLD Definition

**Current (3 duplications):**
```jinja
{# base_component.py.jinja2 #}
# SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created }} path={{ path }}

{# base_document.md.jinja2 #}
<!-- SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created }} path={{ path }} -->

{# base_test.py.jinja2 #}
# SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created }} path={{ path }}
```

**Proposed (1 definition):**
```jinja
{# base/base_artifact.jinja2 #}
{% block scaffold_metadata -%}
{%- if format == 'code' -%}
# SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created }} path={{ path }}
{%- elif format == 'document' -%}
<!-- SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created }} path={{ path }} -->
{%- endif -%}
{% endblock %}
```

**All children inherit this ONE definition!**

---

## Template Redesign Strategy

### Phase 1: Create Tier 0 - Universal Base

**File:** `base/base_artifact.jinja2` (NEW)

```jinja
{# base_artifact.jinja2 - Universal base for ALL artifacts
   
   Enforces:
   - SCAFFOLD metadata (template_id, version, created, path)
   - Artifact lifecycle contract
   - NO language/format specifics
   
   Children: base_code.jinja2, base_document.jinja2
#}

{# TEMPLATE_METADATA
enforcement: STRICT
level: lifecycle
version: "3.0"

validates:
  strict:
    - rule: scaffold_metadata_presence
      description: "All artifacts must have SCAFFOLD metadata"
      pattern: "SCAFFOLD: template=\\w+ version=[\\d.]+ created=[\\d\\-T:Z]+ path=.+"
      
    - rule: template_version_semantic
      description: "Template version must follow semver (X.Y.Z)"
      pattern: "version=[\\d]+\\.[\\d]+(?:\\.[\\d]+)?"

purpose: |
  Universal base template providing lifecycle metadata for ALL artifacts.
  Defines SCAFFOLD metadata structure that all templates inherit (DRY principle).

variables:
  - template_id: Artifact type identifier (from artifacts.yaml)
  - version: Template semantic version
  - created: ISO 8601 timestamp when scaffolded
  - path: Absolute file system path
  - format: 'code' or 'document' (determines comment syntax)
#}

{# ═══════════════════════════════════════════════════════════════════════════
   SCAFFOLD METADATA - SINGLE SOURCE OF TRUTH
   ═══════════════════════════════════════════════════════════════════════════ #}
{% block scaffold_metadata -%}
{%- if format == 'code' -%}
# SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created }} path={{ path }}
{%- elif format == 'document' -%}
<!-- SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created }} path={{ path }} -->
{%- else -%}
{# SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created }} path={{ path }} #}
{%- endif -%}
{% endblock %}

{# ═══════════════════════════════════════════════════════════════════════════
   ARTIFACT CONTENT (override in children)
   ═══════════════════════════════════════════════════════════════════════════ #}
{% block artifact_content %}
{# Children override this block #}
{% endblock %}
```

### Phase 2: Create Tier 1 - Format Bases

**File:** `base/base_code.jinja2` (NEW)

```jinja
{# base_code.jinja2 - Base for all code artifacts
   
   Extends: base_artifact.jinja2
   Children: base_python.jinja2, base_typescript.jinja2, base_csharp.jinja2, etc.
#}
{% extends "base/base_artifact.jinja2" %}

{# Set format for SCAFFOLD metadata #}
{% set format = 'code' %}

{% block artifact_content %}
{# ═══════════════════════════════════════════════════════════════════════════
   FILE HEADER (language-agnostic structure)
   ═══════════════════════════════════════════════════════════════════════════ #}
{% block file_header %}
{% block module_docstring %}{{ description }}{% endblock %}
{% endblock %}

{# ═══════════════════════════════════════════════════════════════════════════
   IMPORTS SECTION (language defines syntax)
   ═══════════════════════════════════════════════════════════════════════════ #}
{% block imports %}
{% block stdlib_imports %}{% endblock %}
{% block thirdparty_imports %}{% endblock %}
{% block project_imports %}{% endblock %}
{% endblock %}

{# ═══════════════════════════════════════════════════════════════════════════
   MAIN CONTENT
   ═══════════════════════════════════════════════════════════════════════════ #}
{% block code_content %}
{# Children define code structure #}
{% endblock %}
{% endblock %}
```

**File:** `base/base_document.jinja2` (REFACTOR)

```jinja
{# base_document.jinja2 - Base for all document artifacts
   
   Extends: base_artifact.jinja2
   Children: base_markdown.jinja2, base_restructuredtext.jinja2, etc.
#}
{% extends "base/base_artifact.jinja2" %}

{# Set format for SCAFFOLD metadata #}
{% set format = 'document' %}

{% block artifact_content %}
{# ═══════════════════════════════════════════════════════════════════════════
   DOCUMENT STRUCTURE (language-agnostic)
   ═══════════════════════════════════════════════════════════════════════════ #}
{% block document_header %}
{% block title %}{{ title }}{% endblock %}
{% block metadata %}
**Status:** {{ status }}
**Version:** {{ version }}
**Last Updated:** {{ updated }}
{% endblock %}
{% block separator %}---{% endblock %}
{% endblock %}

{% block document_sections %}
{% block purpose_section %}
## Purpose
{{ purpose }}
{% endblock %}

{% block scope_section %}
## Scope
{{ scope }}
{% endblock %}

{% block content_sections %}
{# Children define document-specific sections #}
{% endblock %}
{% endblock %}

{% block document_footer %}
{% block related_docs %}
## Related Documentation
{% endblock %}
{% endblock %}
{% endblock %}
```

### Phase 3: Create Tier 2 - Language Bases

**File:** `base/base_python.jinja2` (NEW)

```jinja
{# base_python.jinja2 - Base for all Python code
   
   Extends: base_code.jinja2
   Children: base_python_component.jinja2, base_python_test.jinja2
#}
{% extends "base/base_code.jinja2" %}

{# Python-specific template ID #}
{% block template_id %}python_{{ super() }}{% endblock %}

{% block file_header %}
# {{ path }}
"""
{{ name }} - {{ description }}.

{{ extended_description | default('') }}

@layer: {{ layer | default('Platform') }}
@dependencies: [{{ dependencies | join(', ') }}]
"""
{% block pyright_suppressions %}{% endblock %}
{% endblock %}

{# Python import syntax #}
{% block stdlib_imports %}
# Standard library
from datetime import datetime, timezone
from typing import Any
{% endblock %}

{% block thirdparty_imports %}
# Third-party
{% endblock %}

{% block project_imports %}
# Project modules
{% endblock %}
```

**File:** `base/base_markdown.jinja2` (NEW - extends base_document)

```jinja
{# base_markdown.jinja2 - Base for all Markdown documents
   
   Extends: base_document.jinja2
   Children: research.md, planning.md, design.md, etc.
#}
{% extends "base/base_document.jinja2" %}

{# Markdown-specific comment syntax #}
{% block scaffold_metadata %}
<!-- SCAFFOLD: template={{ template_id }} version={{ version }} created={{ created }} path={{ path }} -->
{% endblock %}

{# Markdown title syntax #}
{% block title %}# {{ title }}{% endblock %}

{# Markdown section syntax #}
{% block purpose_section %}
## Purpose

{{ purpose }}
{% endblock %}
```

### Phase 4: Create Tier 3 - Specialization Bases

**File:** `base/base_python_component.jinja2` (REFACTOR existing base_component)

```jinja
{# base_python_component.jinja2 - Base for Python components
   
   Extends: base_python.jinja2
   Children: worker, adapter, service_*, tool, etc.
#}
{% extends "base/base_python.jinja2" %}

{# Component-specific patterns #}
{% block code_content %}
{% block component_class %}
class {{ name }}:
    """{{ description }}."""
    
    {% block component_methods %}
    # Component methods
    {% endblock %}
{% endblock %}
{% endblock %}
```

**File:** `base/base_python_test.jinja2` (REFACTOR existing base_test)

```jinja
{# base_python_test.jinja2 - Base for Python tests
   
   Extends: base_python.jinja2
   Children: unit_test, integration_test, etc.
#}
{% extends "base/base_python.jinja2" %}

{% block stdlib_imports %}
{{ super() }}
from unittest.mock import Mock, patch
{% endblock %}

{% block thirdparty_imports %}
import pytest
{% endblock %}

{% block code_content %}
{% block test_fixtures %}
# Test fixtures
{% endblock %}

{% block test_cases %}
# Test cases
{% endblock %}
{% endblock %}
```

### Phase 5: Refactor Current Templates

All 24 existing templates change `{% extends %}` to point to appropriate tier:

**Before:**
```jinja
{# components/worker.py.jinja2 #}
# SCAFFOLD: template=worker ...  # Duplicate metadata!
# worker.py content
```

**After:**
```jinja
{# components/worker.py.jinja2 #}
{% extends "base/base_python_component.jinja2" %}

{% block template_id %}worker{% endblock %}
{% block component_class %}
class {{ name }}Worker(BaseWorker[{{ input_dto }}, {{ output_dto }}]):
    # Worker-specific content
{% endblock %}

{# SCAFFOLD metadata inherited from base_artifact! NO DUPLICATION! #}
```

**Template Refactor Matrix:**

| Current Template | New Extends | Tier Level |
|-----------------|-------------|------------|
| worker.py | base_python_component | 3 |
| adapter.py | base_python_component | 3 |
| dto.py | base_python_component | 3 |
| tool.py | base_python_component | 3 |
| service_*.py | base_python_component | 3 |
| unit_test.py | base_python_test | 3 |
| integration_test.py | base_python_test | 3 |
| research.md | base_markdown | 2 |
| planning.md | base_markdown | 2 |
| design.md | base_markdown | 2 |
| architecture.md | base_markdown | 2 |

---

## Extensibility: Future Language Support

### Adding TypeScript Support (Example)

**Step 1:** Create `base/base_typescript.jinja2`
```jinja
{% extends "base/base_code.jinja2" %}

{% block file_header %}
// {{ path }}
/**
 * {{ name }} - {{ description }}.
 * @module {{ module_name }}
 */
{% endblock %}

{% block imports %}
{% block stdlib_imports %}
// Node.js standard library
import { EventEmitter } from 'events';
{% endblock %}

{% block thirdparty_imports %}
// Third-party
{% endblock %}

{% block project_imports %}
// Project modules
{% endblock %}
{% endblock %}
```

**Step 2:** Create `base/base_typescript_component.jinja2`
```jinja
{% extends "base/base_typescript.jinja2" %}

{% block code_content %}
export class {{ name }} {
    {% block component_methods %}
    // Component methods
    {% endblock %}
}
{% endblock %}
```

**Step 3:** Create `components/worker.ts.jinja2`
```jinja
{% extends "base/base_typescript_component.jinja2" %}

{% block template_id %}typescript_worker{% endblock %}
{% block component_methods %}
async process(input: {{ input_dto }}): Promise<{{ output_dto }}> {
    // TypeScript worker logic
}
{% endblock %}

{# SCAFFOLD metadata inherited from base_artifact! ZERO DUPLICATION! #}
```

**Result:** TypeScript workers get SAME SCAFFOLD metadata as Python workers, NO NEW CODE!

### Language Support Matrix (Extensibility Proof)

| Language | Tier 2 Base | Effort | Reuses base_artifact? |
|----------|-------------|--------|----------------------|
| Python | base_python.jinja2 | ✅ Done | ✅ Yes |
| TypeScript | base_typescript.jinja2 | 2-4h | ✅ Yes |
| C# | base_csharp.jinja2 | 2-4h | ✅ Yes |
| Go | base_golang.jinja2 | 2-4h | ✅ Yes |
| Java | base_java.jinja2 | 2-4h | ✅ Yes |
| Rust | base_rust.jinja2 | 2-4h | ✅ Yes |

**Key insight:** SCAFFOLD metadata defined ONCE in `base_artifact.jinja2`, works for ALL languages!

---

## Architectural Principles Validation

### Config Over Code ✅

**Before (hardcoded RULES dict):**
```python
RULES = {
    "worker": {"required_methods": ["execute"]},  # Code
    "dto": {...},
}
```

**After (templates as SSOT):**
```jinja
{# TEMPLATE_METADATA in template #}
validates:
  strict:
    - rule: required_methods
```

**Issue #72 completion:** All templates have metadata → Config Over Code achieved!

### DRY (Don't Repeat Yourself) ✅

**Before:** SCAFFOLD metadata duplicated in 3 base templates (+ N languages = 3N duplications)

**After:** SCAFFOLD metadata defined ONCE in `base_artifact.jinja2`, inherited by ALL

**Proof:**
- Current: 24 templates × 1 SCAFFOLD line = 24 duplications
- Proposed: 1 `base_artifact.jinja2` × 1 SCAFFOLD line = 1 definition
- **Reduction: 24→1 = 96% duplication eliminated**

### SRP (Single Responsibility Principle) ✅

**Before:** `base_component.py` mixed concerns:
- SCAFFOLD metadata (lifecycle concern)
- Python syntax (language concern)
- Component patterns (specialization concern)

**After:** Separated into 4 tiers:
- Tier 0: Lifecycle (SCAFFOLD metadata)
- Tier 1: Format (code vs document)
- Tier 2: Language (Python syntax)
- Tier 3: Specialization (component patterns)

**Each tier has ONE responsibility!**

### Templates as SSOT ✅

**Before:** TemplateIntrospector extracts metadata from 2 templates (8%)

**After:** TemplateIntrospector extracts metadata from ALL templates (100%)

**Result:** query_file_schema() works for ALL artifact types (Issue #121 unblocked)

---

## Implementation Plan

### Goal 1: Multi-Tier Base Template Architecture (6-8h)

**Tasks:**
1. Create `base/base_artifact.jinja2` (Tier 0 - universal) - 1h
2. Refactor `base/base_code.jinja2` (Tier 1 - extends base_artifact) - 1h
3. Refactor `base/base_document.md.jinja2` (Tier 1 - extends base_artifact) - 1h
4. Create `base/base_python.jinja2` (Tier 2 - extends base_code) - 1h
5. Create `base/base_markdown.jinja2` (Tier 2 - extends base_document) - 1h
6. Refactor `base/base_python_component.jinja2` (Tier 3 - extends base_python) - 1h
7. Create `base/base_python_test.jinja2` (Tier 3 - extends base_python) - 1h
8. Write unit tests for inheritance chain - 1-2h

**Success Criteria:**
- SCAFFOLD metadata defined ONCE in base_artifact.jinja2
- All tiers tested and working
- Inheritance chain validated (Tier 0 → 1 → 2 → 3)

### Goal 2: Refactor Existing Templates (4-6h)

**Tasks:**
1. Update 9 component templates (worker, adapter, dto, tool, service_*, generic) - 2h
2. Update 5 document templates (research, planning, design, architecture, reference) - 1h
3. Update 3 test templates (unit_test, integration_test, dto_test) - 1h
4. Update standalone templates (commit-message, tracking, generic.md) - 1h
5. Verify all templates scaffold correctly - 1-2h

**Success Criteria:**
- All 24 templates use new inheritance hierarchy
- All scaffolded files have SCAFFOLD metadata
- No template contains duplicate SCAFFOLD definitions

### Goal 3: Validation & Documentation (2-3h)

**Tasks:**
1. Run audit script: verify 24/24 templates have metadata - 0.5h
2. Test TemplateIntrospector with new hierarchy - 1h
3. Update template documentation (reference/templates/) - 1h
4. Create extensibility guide (TypeScript example) - 0.5h

**Success Criteria:**
- 100% template metadata coverage (was 8%)
- TemplateIntrospector works with all templates
- Documentation shows how to add new languages

### Goal 4: Issue #74 - Template Quality Fixes (included)

**Tasks:**
1. Fix DTO template validation failures - 1h
2. Fix Tool template validation failures - 1h
3. Run E2E tests (scaffold → validate cycle) - 0.5h

**Success Criteria:**
- E2E tests pass (was 1/3, should be 3/3)
- All scaffolded code passes validation

---

## Testing Strategy

### Unit Tests (Base Template Inheritance)

```python
def test_base_artifact_scaffold_metadata():
    """Test SCAFFOLD metadata inherited by all templates."""
    template = env.get_template("base/base_artifact.jinja2")
    rendered = template.render(
        template_id="test",
        version="1.0",
        created="2026-01-22T17:00:00Z",
        path="/tmp/test.py",
        format="code"
    )
    assert "# SCAFFOLD: template=test version=1.0" in rendered

def test_worker_inherits_scaffold_metadata():
    """Test worker template inherits SCAFFOLD from base_artifact."""
    template = env.get_template("components/worker.py.jinja2")
    rendered = template.render(name="Test", input_dto="Input", output_dto="Output")
    assert "# SCAFFOLD:" in rendered  # Inherited!
    assert "class TestWorker(BaseWorker" in rendered

def test_research_inherits_scaffold_metadata():
    """Test research.md inherits SCAFFOLD from base_artifact."""
    template = env.get_template("documents/research.md.jinja2")
    rendered = template.render(title="Test Research")
    assert "<!-- SCAFFOLD:" in rendered  # Inherited, different syntax!
```

### Integration Tests (TemplateIntrospector)

```python
def test_introspector_extracts_metadata_all_templates():
    """Test TemplateIntrospector extracts metadata from ALL 24 templates."""
    introspector = TemplateIntrospector()
    
    for artifact_type in artifacts.yaml:
        template_id = artifact_type["type_id"]
        metadata = introspector.get_metadata(template_id)
        
        assert metadata is not None, f"{template_id} missing metadata"
        assert "template_id" in metadata
        assert "version" in metadata

def test_query_file_schema_all_artifacts():
    """Test query_file_schema() works for all artifact types (Issue #121)."""
    for artifact_type in ["worker", "dto", "research", "planning", "tool"]:
        schema = query_file_schema(f"test_{artifact_type}.py")
        assert schema["file_type"] == "scaffolded"
        assert schema["template_id"] == artifact_type
```

### E2E Tests (Scaffold → Validate Cycle)

```python
def test_scaffold_validate_all_artifact_types():
    """Test all artifact types scaffold with metadata and pass validation."""
    test_cases = [
        ("worker", "TestWorker", {"input_dto": "Input", "output_dto": "Output"}),
        ("dto", "TestDTO", {"fields": [{"name": "field1", "type": "str"}]}),
        ("research", "test-research", {"title": "Test Research"}),
        ("planning", "test-planning", {"title": "Test Planning"}),
    ]
    
    for artifact_type, name, context in test_cases:
        # Scaffold
        result = scaffold_artifact(artifact_type, name, **context)
        assert result.success
        
        # Validate metadata present
        content = read_file(result.path)
        assert "SCAFFOLD:" in content
        
        # Validate template introspection works
        schema = query_file_schema(result.path)
        assert schema["template_id"] == artifact_type
        
        # Validate code passes validation (if code artifact)
        if artifact_type in ["worker", "dto", "tool"]:
            validation = run_quality_gates([result.path])
            assert validation.success
```

---

## Success Metrics

### Quantitative Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Templates with SCAFFOLD metadata | 2/24 (8%) | 24/24 (100%) | 100% |
| SCAFFOLD definition duplications | 3 | 1 | 1 |
| Base templates (Python) | 3 | 7 (4 tiers) | 7 |
| Lines to add new language | N/A | ~100 | <200 |
| query_file_schema() coverage | 8% | 100% | 100% |
| E2E test pass rate | 1/3 (33%) | 3/3 (100%) | 100% |

### Qualitative Metrics

- ✅ **DRY:** SCAFFOLD metadata defined once, inherited everywhere
- ✅ **SRP:** Each tier has single responsibility (lifecycle, format, language, specialization)
- ✅ **Extensibility:** Adding TypeScript requires <200 lines, reuses base_artifact
- ✅ **Config Over Code:** Templates are SSOT, no hardcoded RULES dict
- ✅ **Issue #121 Unblocked:** Discovery tool works for all artifact types

---

## Risks & Mitigations

### Risk 1: Breaking Changes to Existing Templates

**Risk:** Refactoring 24 templates could break existing scaffolding workflows.

**Mitigation:**
- Incremental migration: Test each tier before refactoring children
- Comprehensive test suite: Unit + integration + E2E tests
- Rollback plan: Git branch, can revert if issues found

### Risk 2: Jinja2 Inheritance Complexity

**Risk:** 4-tier inheritance might be hard to debug or maintain.

**Mitigation:**
- Clear documentation: Inheritance chain diagrams
- Block naming convention: `scaffold_metadata`, `code_content`, `component_class`
- Template analyzer tool: Visualize inheritance chain

### Risk 3: Performance Impact of Deep Inheritance

**Risk:** 4-tier inheritance might slow down template rendering.

**Mitigation:**
- Benchmark: Measure rendering time before/after
- Jinja2 caching: Template compilation cached automatically
- Expected: <1ms overhead (Jinja2 inheritance is fast)

---

## Related Work

### Issue #52 - Template-Driven Validation

**Status:** CLOSED (infrastructure complete)
**Deliverable:** TemplateIntrospector, LayeredTemplateValidator
**Gap:** Only 2/24 templates have metadata → Issue #72 completes this!

### Issue #120 - Template Introspection

**Status:** CLOSED (Phase 1 complete)
**Deliverable:** ScaffoldMetadataParser, TemplateIntrospector
**Gap:** Phase 0 incomplete (8% metadata coverage) → Issue #72 completes this!

### Issue #121 - Content-Aware Edit Tool

**Status:** OPEN (blocked by Issue #72)
**Dependency:** Requires query_file_schema() to work for all artifact types
**Unblock:** Issue #72 completion enables 100% discovery coverage

### Epic #73 - Template Governance

**Status:** OPEN (depends on Issue #72)
**Dependency:** Template limits and review process need stable base architecture
**Unblock:** Issue #72 completion establishes foundation for governance

---

## Conclusion

### Summary

**Issue #72 is NOT "add metadata to templates"** - it's a **fundamental architecture redesign** to achieve:

1. **DRY:** SCAFFOLD metadata defined ONCE (base_artifact.jinja2), inherited by ALL
2. **SRP:** Separation of concerns across 4 tiers (lifecycle, format, language, specialization)
3. **Extensibility:** Multi-language support without duplication (Python today, TypeScript/C#/Go tomorrow)
4. **Config Over Code:** Templates as SSOT, eliminating hardcoded logic
5. **Issue #121 Unblocked:** Discovery tool works for 100% of artifact types

### Key Decisions

| Decision | Rationale |
|----------|-----------|
| Multi-tier hierarchy (4 tiers) | Orthogonal dimensions: lifecycle → format → language → specialization |
| base_artifact.jinja2 as Tier 0 | SCAFFOLD metadata defined ONCE, universal across all languages |
| Format split (code vs document) | Different validation concerns, orthogonal to language |
| Language tier (Python, TypeScript, etc.) | Syntax-specific features without duplicating lifecycle/format logic |
| Specialization tier (component, test) | Domain patterns without duplicating language features |

### Next Steps

1. ✅ **Research complete** - Multi-tier architecture designed
2. → **Transition to Planning** - Break down implementation into TDD goals
3. → **Design Phase** - Technical specifications, interface contracts
4. → **TDD Phase** - Implement Tier 0 → 1 → 2 → 3, refactor 24 templates
5. → **Integration** - E2E tests, Issue #121 unblocked
6. → **Documentation** - Extensibility guide, template reference updates

---

**Research Status:** ✅ COMPLETE  
**Architectural Alignment:** Config Over Code, SSOT, DRY, SRP  
**Scope:** Universal artifact taxonomy + multi-tier base template hierarchy  
**Impact:** 24 templates → 1 SCAFFOLD definition, extensible to 100+ templates across languages

**Ready for Planning Phase.**
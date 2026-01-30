<!-- D:\dev\SimpleTraderV3\.st3\phase3-tier3-template-requirements.md -->
<!-- template=research version=d994bd87 created=2026-01-30T10:04:36Z updated=2026-01-30T12:45:00Z -->
# Phase 3 Tier 3 Template Requirements Analysis
**Status:** REVISED  
**Version:** 2.0  
**Last Updated:** 2026-01-30  

---

## Purpose

Complete architectural revision of Tier 3 template strategy based on SRP (Single Responsibility Principle) analysis. Shifts from monolithic tier3 templates to composable BLOCK LIBRARY pattern templates with strict validation hierarchy and cross-branch pattern sharing.

## Scope

**In Scope:**
- SRP-based tier3 pattern decomposition (17 pattern templates)
- Validation level hierarchy (STRICT → ARCHITECTURAL → GUIDELINE)
- Tier 2 justification analysis (syntax layer value)
- CONFIG tak elimination (YAML as DATA, not templates)
- Cross-branch pattern sharing (docs ↔ tracking)
- Block library composition via {% import %} (not extends)
- Concrete template refactoring for cherry-picking patterns

**Out of Scope:**
- Template implementation details
- Jinja2 {% import %} mechanics
- Test implementation
- Phase 3B tasks (deferred features)

## Prerequisites

Read these first:
1. Phase 1 complete (tier0-tier2 + 9 concrete templates)
2. Phase 2 complete (IWorkerLifecycle audit + Backend Pattern Catalog: 12 patterns)
3. Original research (v1.0) identifying monolithic tier3 as anti-pattern
---

## Problem Statement (REVISED)

**Original Problem:** Phase 3 tier3 templates were planned as monolithic (e.g., tier3_base_python_component with 6 patterns), forcing concrete templates to inherit ALL patterns even if only needing 2-3.

**Revised Problem:** Need SRP-based pattern composition where:
1. Each tier3 pattern = 1 architectural pattern (IWorkerLifecycle, Pydantic, Error Handling, etc.)
2. Concrete templates cherry-pick patterns via {% import %} blocks
3. Validation hierarchy: tier0-2 STRICT (syntax), tier3 ARCHITECTURAL (patterns), concrete GUIDELINE (best practices)
4. Syntax explicitly in tier3 names: `tier3_pattern_python_lifecycle.jinja2` (not ambiguous)

## Research Goals (REVISED)

- Decompose 12 backend patterns into 17 granular tier3 pattern templates (9 CODE + 8 DOCUMENT)
- Justify tier2 layer existence (syntax deduplication: type hints, async, docstrings)
- Eliminate CONFIG tak (YAML files are DATA validated by Pydantic schemas, not scaffoldable)
- Define cross-branch patterns (tier3_pattern_related_docs used by docs + tracking)
- Establish validation hierarchy: STRICT (tier0-2) → ARCHITECTURAL (tier3) → GUIDELINE (concrete)
- Provide block library composition examples ({% import %} not {% extends %})

---

## Background

### Context from Previous Phases

**Phase 1 Achievements (✅ COMPLETE):**
- Tier 0: Universal SCAFFOLD (2-line format)
- Tier 1: 3 of 4 base types implemented (CODE, DOCUMENT, CONFIG exists but will be removed)
- Tier 2: 3 language syntax templates (Python, Markdown, YAML)
- Concrete: 9 templates (4 CODE, 5 DOCUMENT)

**Phase 2 Achievements (✅ COMPLETE):**
- Task 2.2: IWorkerLifecycle audit → MANDATORY pattern (1/3 workers use it)
- Task 2.3: Backend Pattern Catalog → **12 patterns identified**
  - Tier 2 (4): Module Header, Import Org, Type Hints, Async/Await
  - Tier 3 (8): Lifecycle, Pydantic, Error, Logging, Typed ID, DI, LogEnricher, Translator

### Original Planning (v1.0) - SUPERSEDED

**Monolithic Approach (REJECTED):**
```
tier3_base_python_component.jinja2  ← 6 patterns bundled
tier3_base_python_data_model.jinja2 ← 3 patterns bundled
tier3_base_python_tool.jinja2       ← 3 patterns bundled
```

**Problem:** Worker template forced to inherit ALL 6 component patterns, even if only needing lifecycle + error handling.

### Key Insights from Architectural Discussion (2026-01-30)

**Insight 1: CONFIG Tak = Misclassification**
- YAML files (workflows.yaml, labels.yaml, artifacts.yaml) are **DATA**, not templates
- 8 of 9 YAML files have Pydantic schemas (WorkflowConfig, LabelConfig, etc.)
- Validation happens via Pydantic (CODE), not template syntax
- **Conclusion:** Scrap tier1_base_config, tier3_base_yaml_policy → Add config_schema.py to CODE tak

**Insight 2: Tier3 Patterns = SRP Composition**
- Each pattern = 1 architectural concern (lifecycle, error, logging)
- Concrete templates cherry-pick via {% import %} blocks
- Tool.py now justified (2 patterns = lightweight enough)
- **Conclusion:** 12 backend patterns → 17 tier3 pattern templates (includes document patterns)

**Insight 3: Validation Hierarchy**
- Tier 0-2: STRICT (syntax must exist: `"^class "`, `"^from typing import"`)
- Tier 3: ARCHITECTURAL (pattern presence: IWorkerLifecycle exists, Pydantic validators exist)
- Concrete: GUIDELINE (suggestions: "Consider logging", "Add error handling if needed")
- **Current bug:** worker.py has `enforcement: STRICT` but validates architectural patterns (wrong!)

**Insight 4: Tier2 Justification**
- Tier1 = FORMAT (code vs document structure)
- Tier2 = SYNTAX (Python type hints, async, docstrings vs Java/TypeScript syntax)
- Without tier2: Every concrete template duplicates `from typing import`, `async def` syntax
- **Conclusion:** Tier2 prevents syntax duplication (4 features: type hints, async, dunder, base classes)

**Insight 5: Cross-Branch Patterns**
- `tier3_pattern_related_docs.jinja2` used by research.md, planning.md, pr.md, issue.md
- Related Documentation section = UNIVERSAL (docs + tracking share it)
- **Conclusion:** Some tier3 patterns transcend tier1 boundaries

**Insight 6: template_registry.yaml → .json**
- Machine-generated file for provenance tracking
- JSON better parsability, no YAML ambiguity
- **Conclusion:** Update registry format in Phase 3

---

## Findings

### Finding 1: Tier 3 Monoliths Violate SRP

**Evidence:**
```jinja
{# tier3_base_python_component.jinja2 (ORIGINAL - REJECTED) #}
{% block lifecycle %}
    def __init__(self, build_spec): ...
    def initialize(self, **capabilities): ...
    def shutdown(self): ...
{% endblock %}

{% block di %}
    def __init__(self, capabilities: Capabilities): ...
{% endblock %}

{% block error_handling %}
    try: ... except: logger.exception()
{% endblock %}

{% block logging %}
    self._logger = logging.getLogger(__name__)
{% endblock %}

{# Problem: Worker inherits ALL 6 patterns, even if only needs 2! #}
```

**Impact:**
- Concrete templates cannot selective patterns (all-or-nothing inheritance)
- Tool.py too heavyweight (needs error+logging, not lifecycle+di+enricher)
- Maintenance burden: Changing 1 pattern affects all inheritors

**Revised Approach:**
```jinja
{# tier3_pattern_python_lifecycle.jinja2 (1 PATTERN ONLY) #}
{% block pattern_lifecycle_imports %}
from backend.core.interfaces.worker import IWorkerLifecycle
{% endblock %}

{% block pattern_lifecycle_init %}
def __init__(self, build_spec: BuildSpec):
    self._initialized = False
{% endblock %}

{# tier3_pattern_python_error.jinja2 (1 PATTERN ONLY) #}
{% block pattern_error_wrapper %}
try:
    {{ caller() }}
except Exception as e:
    self._logger.exception("Error in {{ method_name }}")
    raise
{% endblock %}

{# concrete/worker.py - CHERRY-PICKS 4 patterns #}
{% extends "tier2_base_python.jinja2" %}
{% import "tier3_pattern_python_lifecycle.jinja2" as lifecycle %}
{% import "tier3_pattern_python_error.jinja2" as error %}
{% import "tier3_pattern_python_logging.jinja2" as logging %}
{% import "tier3_pattern_python_di.jinja2" as di %}

{% block imports_section %}
{{ super() }}
{{ lifecycle.pattern_lifecycle_imports() }}
{{ di.pattern_di_imports() }}
{% endblock %}

{% block class_structure %}
class {{ class_name }}({{ lifecycle.pattern_lifecycle_base_class() }}):
    {{ lifecycle.pattern_lifecycle_init() }}
    {{ di.pattern_di_constructor_params() }}
    {{ error.pattern_error_wrapper() }}
    {{ logging.pattern_logging_setup() }}
{% endblock %}
```

**Benefit:** Worker cherry-picks 4 patterns, tool.py cherry-picks 2 (error+logging), dto.py cherry-picks 3 (pydantic+typed_id+logging).

**Recommendation:**
- Create 17 granular tier3 pattern templates (9 CODE + 8 DOCUMENT)
- Use {% import %} for block composition (not {% extends %})
- Each pattern = 1 architectural concern (SRP)

---

### Finding 2: CONFIG Tak = Architectural Misclassification

**Evidence:**

**9 YAML files in .st3/:**
| YAML File | Pydantic Schema | Purpose | Hand-Written? |
|-----------|----------------|---------|---------------|
| workflows.yaml | WorkflowConfig (193 lines) | Phase validation | ✅ YES |
| labels.yaml | LabelConfig (341 lines) | GitHub label sync | ✅ YES |
| artifacts.yaml | ArtifactRegistryConfig | Template registry | ✅ YES |
| project_structure.yaml | ProjectStructureConfig | Path configuration | ✅ YES |
| policies.yaml | OperationPoliciesConfig | Validation rules | ✅ YES |
| quality.yaml | QualityConfig | Gate thresholds | ✅ YES |
| git.yaml | GitConfig | Git settings | ✅ YES |
| scaffold_metadata.yaml | ScaffoldMetadataConfig | Template metadata | ✅ YES |
| template_registry.yaml | ❌ NO SCHEMA | Provenance tracking | ⚠️ Machine-gen |

**Reality Check:**
- ❌ 0 YAML files ever scaffolded via MCP tools
- ✅ 8 of 9 have Pydantic validation schemas (CODE, not CONFIG)
- ❌ 0 CONFIG artifacts defined in artifacts.yaml
- ✅ All YAML files are hand-written or machine-generated

**Correct Classification:**
```
YAML FILE (DATA)
   ↓ validated by
PYDANTIC SCHEMA (CODE)
   ↓ scaffolded via
tier2_base_python → tier3_pattern_python_pydantic → concrete/config_schema.py
```

**Impact:**
- tier1_base_config serves no purpose (YAML syntax = tier2_base_yaml already exists)
- tier3_base_yaml_policy has no patterns to encapsulate (YAML has no "lifecycle" or "DI")
- Pydantic schemas ARE the templates we should scaffold (8 schemas share patterns)

**Recommendation:**
- ❌ **SCRAP tier1_base_config** (save ~2h)
- ❌ **SCRAP tier3_base_yaml_policy** (save 3h)
- ✅ **ADD concrete/config_schema.py** (Pydantic schema template, 2h)
- ✅ **KEEP tier2_base_yaml** (syntax layer for machine-generated YAML)
- ✅ **CHANGE template_registry.yaml → template_registry.json** (better parsability)

---

### Finding 3: Validation Hierarchy Mismatch in Concrete Templates

**Evidence:**

**Current concrete/worker.py.jinja2:**
```yaml
TEMPLATE_METADATA:
  enforcement: STRICT  ← WRONG!
  validates:
    strict:
      - "class.*\\(IWorker, IWorkerLifecycle\\):"  ← ARCHITECTURAL!
      - "def initialize\\(self, strategy_cache"    ← ARCHITECTURAL!
```

**Problem:** Worker validates ARCHITECTURAL patterns (IWorkerLifecycle) with STRICT enforcement (syntax level).

**Correct Hierarchy:**

| Tier | Enforcement | What Validates | Example |
|------|-------------|----------------|---------|
| **Tier 0** | STRICT | SCAFFOLD present | `<!-- path -->`, `<!-- metadata -->` |
| **Tier 1** | STRICT | FORMAT structure | Has docstring, imports, class sections |
| **Tier 2** | STRICT | SYNTAX compliance | `from typing import`, `async def`, `"""..."""` |
| **Tier 3** | ARCHITECTURAL | PATTERN presence | IWorkerLifecycle exists, Pydantic validators exist |
| **Concrete** | GUIDELINE | BEST PRACTICES | "Consider logging", "Add error handling" |

**Analysis:**

**tier1_base_code (STRICT - CORRECT):**
```yaml
validates:
  strict:
    - "^import "   # Syntax check: import statement exists
    - "^from "     # Syntax check: from statement exists
    - "^class "    # Syntax check: class definition exists
```

**tier2_base_python (STRICT - CORRECT):**
```yaml
validates:
  strict:
    - "^class "           # Duplicated from tier1 (could optimize)
    - "from typing import" # Python-specific type hints
    - "^    \"\"\"" # Python docstring format (4-space indent + triple quotes)
```

**tier3_pattern_python_lifecycle (ARCHITECTURAL - NEW):**
```yaml
validates:
  architectural:
    - "IWorkerLifecycle" in base_classes  # Pattern presence check
    - "def initialize" exists             # Pattern method exists
    - "def shutdown" exists               # Pattern method exists
```

**concrete/worker.py (GUIDELINE - REVISED):**
```yaml
enforcement: GUIDELINE  ← FIXED!
validates:
  guidelines:
    - "Workers should implement IWorkerLifecycle for two-phase init"
    - "Consider adding LogEnricher for context-aware logging"
    - "Use Capabilities for dependency injection"
    - "Add comprehensive error handling in async methods"
```

**Impact:**
- All 9 concrete templates currently have wrong enforcement level
- Tier2 duplicates some tier1 validations (optimization opportunity)
- No distinction between "must have" (strict) vs "should have" (guideline)

**Recommendation:**
- Update all concrete templates: `enforcement: STRICT → GUIDELINE`
- Add tier3 pattern templates with `enforcement: ARCHITECTURAL`
- Document validation hierarchy in Phase 3 deliverables

---

### Finding 4: Tier 2 Prevents Syntax Duplication

**Question:** Is tier2 necessary or could tier1 → tier3 directly?

**Analysis:**

**What tier1_base_code provides:**
```python
# Generic code structure (language-agnostic)
- Module docstring (@layer, @dependencies)
- Import section (3-group: stdlib/3rd/project)
- Class definition placeholder
- Method blocks
```

**What tier2_base_python ADDS:**
```python
# Python-SPECIFIC syntax
- from typing import ...  # Type hints (not in Java/TypeScript)
- """...""" docstrings    # Triple quotes (not /* */ like Java)
- async def, await        # Python async (different from JS)
- def __init__(self, x: Type):  # Typed parameters
- class X(BaseModel):     # Base class syntax
- def __str__, __repr__   # Dunder methods
```

**Without tier2: Duplication Analysis**

| Feature | Used By | Without Tier2 | With Tier2 |
|---------|---------|---------------|------------|
| Type hints | 9 templates | 9× `from typing import` | 1× in tier2 |
| Async syntax | 3 templates | 3× `async def`, `await` | 1× in tier2 |
| Dunder methods | 4 templates | 4× `__init__`, `__str__` | 1× in tier2 |
| Base classes | 6 templates | 6× `class X(Y):` syntax | 1× in tier2 |

**Total Duplication Prevented: 22 instances across 9 concrete templates**

**Comparison: tier2_base_markdown**

| Feature | Used By | Without Tier2 | With Tier2 |
|---------|---------|---------------|------------|
| Code blocks | 5 templates | 5× ``` syntax | 1× in tier2 |
| Link definitions | 5 templates | 5× `[ref]: url` | 1× in tier2 |

**Total Duplication Prevented: 10 instances across 5 concrete templates**

**Conclusion:**
- Tier2 prevents **32 syntax duplications** across 14 concrete templates
- Tier2 = SYNTAX layer (Python vs TypeScript vs Java specific features)
- Without tier2: Tier1 → concrete templates would explode with language-specific syntax

**Recommendation:**
- ✅ **KEEP tier2 layer** (justification: prevents 32 syntax duplications)
- Document tier2 value in architecture guide

---

### Finding 5: 17 Granular Tier3 Pattern Templates Required

**Decomposition: 12 Backend Patterns → 17 Tier3 Templates**

#### **CODE Tak: 9 Pattern Templates**

| # | Template Name | Pattern | Lines | Complexity | Used By | Justified? |
|---|---------------|---------|-------|------------|---------|------------|
| 1 | tier3_pattern_python_async.jinja2 | Async/Await | 15 | MEDIUM | worker, adapter, service (3) | ✅ |
| 2 | tier3_pattern_python_lifecycle.jinja2 | IWorkerLifecycle | 30 | HIGH | worker, adapter (2) | ✅ |
| 3 | tier3_pattern_python_pydantic.jinja2 | Pydantic DTO | 40 | HIGH | dto, schema, config_schema (3) | ✅ |
| 4 | tier3_pattern_python_error.jinja2 | Error Handling | 20 | MEDIUM | worker, adapter, service, tool (4) | ✅ |
| 5 | tier3_pattern_python_logging.jinja2 | Logging | 10 | LOW | ALL (9) | ✅ Universal |
| 6 | tier3_pattern_python_typed_id.jinja2 | Typed ID | 10 | LOW | dto, schema (2) | ✅ |
| 7 | tier3_pattern_python_di.jinja2 | DI via Capabilities | 15 | MEDIUM | worker, adapter, service (3) | ✅ |
| 8 | tier3_pattern_python_log_enricher.jinja2 | LogEnricher | 15 | MEDIUM | worker, adapter (2) | ✅ |
| 9 | tier3_pattern_python_translator.jinja2 | Translator/i18n | 15 | MEDIUM | worker, adapter, service (3) | ✅ |

**Total: 9 pattern templates, preventing 40+ pattern duplications**

#### **DOCUMENT Tak: 8 Pattern Templates**

| # | Template Name | Pattern | Lines | Found In | Justified? |
|---|---------------|---------|-------|----------|------------|
| 1 | tier3_pattern_markdown_status_header.jinja2 | Status/Version/Date | 5 | ALL (5) | ✅ Universal |
| 2 | tier3_pattern_markdown_purpose_scope.jinja2 | Purpose + In/Out Scope | 15 | ALL (5) | ✅ Universal |
| 3 | tier3_pattern_markdown_prerequisites.jinja2 | Numbered "Read first" | 10 | research, planning, arch (3) | ✅ |
| 4 | tier3_pattern_markdown_agent_hints.jinja2 | Agent hints block | 30 | research, planning, design (3) | ✅ |
| 5 | tier3_pattern_markdown_related_docs.jinja2 | Link list + definitions | 10 | ALL (5) + pr, issue (7) | ✅ **CROSS-BRANCH!** |
| 6 | tier3_pattern_markdown_version_history.jinja2 | Table Date/Author | 10 | ALL (5) | ✅ Universal |
| 7 | tier3_pattern_markdown_open_questions.jinja2 | "❓ Question" list | 8 | research, design (2) | ✅ |
| 8 | tier3_pattern_markdown_dividers.jinja2 | "---" separators | 3 | ALL (5) | ✅ Universal |

**Total: 8 pattern templates, preventing 30+ section duplications**

**Cross-Branch Pattern:**
- `tier3_pattern_markdown_related_docs` used by:
  - **Documents:** research.md, planning.md, design.md, architecture.md, reference.md
  - **Tracking:** pr.md, issue.md (need context links)
- **First tier3 pattern transcending tier1 boundaries!**

**Recommendation:**
- Create 17 tier3 pattern templates (9 CODE + 8 DOCUMENT)
- Each template = 1 architectural pattern (SRP)
- Use {% import %} for composition (not {% extends %})
- Document cross-branch patterns explicitly

---

### Finding 6: Tier3 Patterns = Block Libraries (Not Inheritance)

**Question:** Should tier3_pattern_python_lifecycle **extend** tier2_base_python?

**Analysis:**

**Option A: Tier3 extends Tier2 (REJECTED)**
```jinja
{# tier3_pattern_python_lifecycle.jinja2 #}
{% extends "tier2_base_python.jinja2" %}

{% block lifecycle_init %}
def __init__(self, build_spec: BuildSpec):
    self._initialized = False
{% endblock %}

{# concrete/worker.py #}
{% extends "tier3_pattern_python_lifecycle.jinja2" %}
{# Problem: Worker inherits LIFECYCLE, cannot cherry-pick ERROR or LOGGING! #}
```

**Problem:** Tier3 as inheritance = single-pattern forced inheritance (no composition)

**Option B: Tier3 as Block Library (SELECTED)**
```jinja
{# tier3_pattern_python_lifecycle.jinja2 - STANDALONE BLOCKS #}
{# NO extends! Just block definitions for import #}

{% block pattern_lifecycle_imports %}
from backend.core.interfaces.worker import IWorkerLifecycle
{% endblock %}

{% block pattern_lifecycle_base_class %}
IWorkerLifecycle
{% endblock %}

{% block pattern_lifecycle_init %}
def __init__(self, build_spec: BuildSpec):
    """Initialize with build spec only (no dependencies)."""
    self._build_spec = build_spec
    self._initialized = False
{% endblock %}

{% block pattern_lifecycle_initialize %}
async def initialize(self, strategy_cache, **capabilities):
    """Initialize with dependencies (DI injection)."""
    if self._initialized:
        raise RuntimeError("Already initialized")
    self._initialized = True
{% endblock %}

{% block pattern_lifecycle_shutdown %}
async def shutdown(self):
    """Cleanup resources."""
    self._initialized = False
{% endblock %}

{# concrete/worker.py - CHERRY-PICKS via import #}
{% extends "tier2_base_python.jinja2" %}  {# Gets Python syntax #}
{% import "tier3_pattern_python_lifecycle.jinja2" as lifecycle %}
{% import "tier3_pattern_python_error.jinja2" as error %}

{% block imports_section %}
{{ super() }}  {# tier2 Python imports #}
{{ lifecycle.pattern_lifecycle_imports() }}  {# Cherry-pick lifecycle imports #}
{% endblock %}

{% block class_structure %}
class {{ class_name }}(IWorker, {{ lifecycle.pattern_lifecycle_base_class() }}):
    """{{ docstring }}"""
    
    {{ lifecycle.pattern_lifecycle_init() | indent(4) }}
    {{ lifecycle.pattern_lifecycle_initialize() | indent(4) }}
    {{ lifecycle.pattern_lifecycle_shutdown() | indent(4) }}
{% endblock %}
```

**Benefit:**
- Worker cherry-picks 4 patterns: lifecycle, error, logging, di
- Tool cherry-picks 2 patterns: error, logging (no lifecycle!)
- DTO cherry-picks 3 patterns: pydantic, typed_id, logging

**Jinja2 Mechanics:**
```jinja
{% import "template.jinja2" as namespace %}
{{ namespace.block_name() }}  # Calls block from imported template
{{ namespace.block_name() | indent(4) }}  # With indentation
```

**Syntax in Tier3 Name:**
- `tier3_pattern_python_lifecycle` (not `tier3_pattern_lifecycle`)
- **Reason:** Makes Python syntax assumption explicit
- **Alternative:** Generic `tier3_pattern_lifecycle` could work for Python + TypeScript (but different syntax)

**Recommendation:**
- ✅ Tier3 patterns = BLOCK LIBRARIES (standalone, no extends)
- ✅ Concrete templates import patterns: `{% import "tier3_pattern_python_X.jinja2" as X %}`
- ✅ Syntax in name: `tier3_pattern_python_*` and `tier3_pattern_markdown_*`
- Document {% import %} composition pattern in Phase 3 deliverables

---

### Finding 7: Tracking Tak Correctly Has No Tier3

**Analysis:**

**Tracking Tier Structure:**
```
tier1_base_tracking
├─ tier2_tracking_text.jinja2      # Plain text (commit messages)
│  └─ concrete/commit.txt
│
└─ tier2_tracking_markdown.jinja2  # Markdown (PR, issue, milestone)
   ├─ {% import "tier3_pattern_markdown_related_docs.jinja2" %}  ← CROSS-BRANCH!
   └─ concrete/
      ├─ pr.md (uses related_docs)
      ├─ issue.md (uses related_docs)
      ├─ milestone.md
      ├─ changelog.md
      └─ release_notes.md
```

**Why No Tier3 for Tracking?**

| Concrete Template | Unique Structure | Shared Patterns |
|-------------------|------------------|-----------------|
| commit.txt | Type prefix (feat:, fix:) | ❌ None |
| pr.md | Changes, Testing, Checklist | ✅ related_docs |
| issue.md | Problem, Expected, Actual | ✅ related_docs |
| milestone.md | Goals, Issues list | ❌ None |
| changelog.md | Added/Changed/Fixed grouping | ❌ None |

**Pattern Analysis:**
- Each tracking artifact has UNIQUE structure (no shared architectural patterns)
- Only shared pattern: `related_docs` (already captured in tier3_pattern_markdown_related_docs)
- Tracking = FORMATTING (Conventional Commits, PR template), not ARCHITECTURE

**Tier 2 Sufficiency:**
```jinja
{# tier2_tracking_text.jinja2 #}
- Line breaks
- No markup
- Conventional Commits format

{# tier2_tracking_markdown.jinja2 #}
- Headers (H1-H3)
- Lists (- item, 1. item)
- Checkboxes (- [ ] task)
- Bold/italic
- Code blocks
```

**Recommendation:**
- ✅ **NO tier3 for tracking** (tier2 syntax sufficient)
- ✅ Tracking can import `tier3_pattern_markdown_related_docs` (cross-branch pattern)
- Document tracking as "tier2-only branch" in architecture guide

---

## Revised Tier Hierarchy (ALL BRANCHES)

### **Complete 5-Tier Structure:**

```
tier0_base_artifact.jinja2 (UNIVERSAL SCAFFOLD - 2 lines)
│
├─ tier1_base_code.jinja2 (FORMAT: Code file structure)
│  └─ tier2_base_python.jinja2 (SYNTAX: Python type hints, async, docstrings)
│     ├─ tier3_pattern_python_async.jinja2 (BLOCK LIBRARY - import only)
│     ├─ tier3_pattern_python_lifecycle.jinja2
│     ├─ tier3_pattern_python_pydantic.jinja2
│     ├─ tier3_pattern_python_error.jinja2
│     ├─ tier3_pattern_python_logging.jinja2
│     ├─ tier3_pattern_python_typed_id.jinja2
│     ├─ tier3_pattern_python_di.jinja2
│     ├─ tier3_pattern_python_log_enricher.jinja2
│     ├─ tier3_pattern_python_translator.jinja2
│     │
│     └─ concrete/ (extends tier2, imports tier3 patterns via {% import %})
│        ├─ worker.py (7 patterns: lifecycle, async, error, logging, di, enricher, translator)
│        ├─ adapter.py (7 patterns: same as worker)
│        ├─ dto.py (3 patterns: pydantic, typed_id, logging)
│        ├─ schema.py (3 patterns: pydantic, typed_id, logging)
│        ├─ config_schema.py (3 patterns: pydantic, typed_id, logging) ← NEW!
│        ├─ service.py (5 patterns: async, error, logging, di, translator)
│        ├─ tool.py (2 patterns: error, logging) ← NOW JUSTIFIED!
│        └─ generic.py (1-2 patterns: logging, optional error)
│
├─ tier1_base_document.jinja2 (FORMAT: Document structure)
│  └─ tier2_base_markdown.jinja2 (SYNTAX: Markdown headers, code blocks, links)
│     ├─ tier3_pattern_markdown_status_header.jinja2 (BLOCK LIBRARY)
│     ├─ tier3_pattern_markdown_purpose_scope.jinja2
│     ├─ tier3_pattern_markdown_prerequisites.jinja2
│     ├─ tier3_pattern_markdown_agent_hints.jinja2
│     ├─ tier3_pattern_markdown_related_docs.jinja2 ← CROSS-BRANCH!
│     ├─ tier3_pattern_markdown_version_history.jinja2
│     ├─ tier3_pattern_markdown_open_questions.jinja2
│     ├─ tier3_pattern_markdown_dividers.jinja2
│     │
│     └─ concrete/ (extends tier2, imports tier3 patterns)
│        ├─ research.md (7 patterns: status, purpose, prereq, hints, related, history, questions)
│        ├─ planning.md (6 patterns: status, purpose, prereq, hints, related, history)
│        ├─ design.md (8 patterns: all except questions)
│        ├─ architecture.md (6 patterns: status, purpose, related, history, dividers, hints)
│        └─ reference.md (5 patterns: status, purpose, related, history, dividers)
│
└─ tier1_base_tracking.jinja2 (FORMAT: Tracking artifacts - ephemeral, no versioning)
   ├─ tier2_tracking_text.jinja2 (SYNTAX: Plain text line breaks)
   │  └─ concrete/commit.txt (Conventional Commits format)
   │
   └─ tier2_tracking_markdown.jinja2 (SYNTAX: Markdown headers, lists, checkboxes)
      ├─ {% import "tier3_pattern_markdown_related_docs.jinja2" %} ← CROSS-BRANCH IMPORT!
      └─ concrete/
         ├─ pr.md (uses related_docs pattern)
         ├─ issue.md (uses related_docs pattern)
         ├─ milestone.md
         ├─ changelog.md
         └─ release_notes.md
```

**KEY CHANGES:**
1. ❌ tier1_base_config REMOVED (YAML = DATA, not templates)
2. ❌ tier3_base_yaml_policy REMOVED (no architectural patterns)
3. ✅ tier3_pattern_* templates are BLOCK LIBRARIES ({% import %}, not {% extends %})
4. ✅ config_schema.py added to CODE tak (scaffolds Pydantic schemas)
5. ✅ tier3_pattern_markdown_related_docs = CROSS-BRANCH (docs + tracking)
6. ✅ tool.py now justified (2 patterns = lightweight)

---

## Validation Hierarchy (Issue #52 Integration)

### **Enforcement Levels:**

| Tier | Enforcement | Validates | Example | Failure = |
|------|-------------|-----------|---------|-----------|
| **Tier 0** | STRICT | SCAFFOLD present | `<!-- path -->`<br>`<!-- metadata -->` | Build error |
| **Tier 1** | STRICT | FORMAT structure | Has docstring<br>Has imports<br>Has class | Build error |
| **Tier 2** | STRICT | SYNTAX compliance | `from typing import`<br>`async def`<br>`"""..."""` | Build error |
| **Tier 3** | ARCHITECTURAL | PATTERN presence | `IWorkerLifecycle`<br>Pydantic validators<br>Error handlers | Warning (quality gate) |
| **Concrete** | GUIDELINE | BEST PRACTICES | "Consider logging"<br>"Add error handling" | Suggestion only |

### **Bug Fix Required:**

**Current concrete/worker.py (WRONG):**
```yaml
TEMPLATE_METADATA:
  enforcement: STRICT  ← Should be GUIDELINE!
  validates:
    strict:  ← Should be guidelines!
      - "class.*\\(IWorker, IWorkerLifecycle\\):"  ← ARCHITECTURAL pattern!
```

**Corrected concrete/worker.py:**
```yaml
TEMPLATE_METADATA:
  enforcement: GUIDELINE
  validates:
    guidelines:
      - "Workers should implement IWorkerLifecycle for two-phase initialization"
      - "Consider adding LogEnricher for context-aware logging"
      - "Use Capabilities for dependency injection pattern"
      - "Add error handling in async methods for robustness"
```

**Tier3 Pattern Validation (NEW):**
```yaml
# tier3_pattern_python_lifecycle.jinja2
TEMPLATE_METADATA:
  enforcement: ARCHITECTURAL
  validates:
    architectural:
      - "IWorkerLifecycle" in base_classes  # Pattern present in class signature
      - "def initialize" in method_list     # Pattern method exists
      - "def shutdown" in method_list       # Pattern method exists
      - "_initialized" in instance_vars     # Pattern state tracking
```

**Integration with Issue #52:**
- Tier 0-2: Template validation (syntax exists)
- Tier 3: Pattern validation (architecture compliance)
- Concrete: Quality gates (best practices)
- Issue #52 validation hooks at each tier level

---

## Phase 3 Task Breakdown (REVISED)

### **Tasks REMOVED:**

| Task | Original | Reason |
|------|----------|--------|
| Task 1.2c | Create tier1_base_config (2h) | CONFIG tak eliminated |
| Task 3.3 | Create tier3_base_python_tool (6h) | Monolithic approach rejected |
| Task 3.4 | Create tier3_base_markdown_knowledge (4h) | Monolithic approach rejected |
| Task 3.6 | Create tier3_base_yaml_policy (3h) | CONFIG tak eliminated |

**Savings: 15h**

### **Tasks ADDED:**

#### **CODE Pattern Templates (9 tasks × 2h = 18h):**
- Task 3.1a: Create tier3_pattern_python_async.jinja2 (2h)
- Task 3.1b: Create tier3_pattern_python_lifecycle.jinja2 (2h)
- Task 3.1c: Create tier3_pattern_python_pydantic.jinja2 (2h)
- Task 3.1d: Create tier3_pattern_python_error.jinja2 (2h)
- Task 3.1e: Create tier3_pattern_python_logging.jinja2 (2h)
- Task 3.1f: Create tier3_pattern_python_typed_id.jinja2 (2h)
- Task 3.1g: Create tier3_pattern_python_di.jinja2 (2h)
- Task 3.1h: Create tier3_pattern_python_log_enricher.jinja2 (2h)
- Task 3.1i: Create tier3_pattern_python_translator.jinja2 (2h)

#### **DOCUMENT Pattern Templates (8 tasks × 1.5h = 12h):**
- Task 3.4a: Create tier3_pattern_markdown_status_header.jinja2 (1.5h)
- Task 3.4b: Create tier3_pattern_markdown_purpose_scope.jinja2 (1.5h)
- Task 3.4c: Create tier3_pattern_markdown_prerequisites.jinja2 (1.5h)
- Task 3.4d: Create tier3_pattern_markdown_agent_hints.jinja2 (1.5h)
- Task 3.4e: Create tier3_pattern_markdown_related_docs.jinja2 (1.5h) ← CROSS-BRANCH!
- Task 3.4f: Create tier3_pattern_markdown_version_history.jinja2 (1.5h)
- Task 3.4g: Create tier3_pattern_markdown_open_questions.jinja2 (1.5h)
- Task 3.4h: Create tier3_pattern_markdown_dividers.jinja2 (1.5h)

#### **Refactoring Tasks (8 tasks × 1h = 8h):**
- Task 3.7a: Refactor worker.py to cherry-pick 7 patterns (1h)
- Task 3.7b: Refactor dto.py to cherry-pick 3 patterns (1h)
- Task 3.7c: Refactor research.md to cherry-pick 7 patterns (1h)
- Task 3.7d: Refactor planning.md to cherry-pick 6 patterns (1h)
- Task 3.7e: Refactor design.md to cherry-pick 8 patterns (1h)
- Task 3.7f: Add config_schema.py concrete template (1h)
- Task 3.7g: Fix concrete template enforcement levels (9 templates × 15min = 2h)
- Task 3.7h: Change template_registry.yaml → template_registry.json (1h)

#### **KEEP (Adjusted):**
- Task 3.5: Create tier1_base_tracking + tier2_tracking_text/markdown (11h) ← UNCHANGED
- Task 3.8: Documentation (16h) ← Expanded to cover new patterns

**New Effort: 18h + 12h + 8h + 11h + 16h = 65h**

### **Revised Phase 3 Effort Summary:**

| Category | Original | Revised | Delta |
|----------|----------|---------|-------|
| Tier 1 | 6h | 6h (tracking only) | 0h |
| Tier 3 (monolithic) | 24h | 0h | -24h |
| Tier 3 (patterns) | 0h | 30h | +30h |
| Concrete refactoring | 3h | 8h | +5h |
| Documentation | 16h | 16h | 0h |
| Misc (registry, validation) | 0h | 5h | +5h |
| **TOTAL** | **49h** | **65h** | **+16h** |

**Breakdown by Priority:**
- **P0 (CRITICAL):** 49h (pattern templates + refactoring + tracking)
- **P1 (Important):** 16h (documentation)

**Estimated Duration:** 4-5 weeks (1 developer)

---

## Open Questions (REVISED)

### Q1: Should tier2 validations be deduplicated from tier1?

**Context:** tier2_base_python validates `"^class "` (duplicates tier1_base_code)

**Options:**
1. **KEEP duplication** (defensive validation, clear tier boundaries)
2. **REMOVE from tier2** (tier1 already validates, trust hierarchy)

**Recommendation:** KEEP (tier2 validates Python-specific class syntax, tier1 validates generic code structure)

**Impact:** LOW (1-2 regex patterns per tier2 template)

---

### Q2: Should tier3 patterns support multiple languages?

**Context:** `tier3_pattern_python_lifecycle` is Python-specific, but lifecycle pattern exists in TypeScript/Java

**Options:**
1. **Language-specific patterns:** `tier3_pattern_python_lifecycle`, `tier3_pattern_typescript_lifecycle`
2. **Generic patterns with language param:** `tier3_pattern_lifecycle(language="python")`

**Recommendation:** Language-specific (Python is only language in Phase 3, generalization deferred to Phase 4+)

**Impact:** MEDIUM (future multi-language support requires new pattern templates)

---

### Q3: Should cross-branch patterns live in tier2 or tier3?

**Context:** `tier3_pattern_markdown_related_docs` used by docs + tracking (both Markdown)

**Options:**
1. **tier2_base_markdown** (syntax level, Markdown-specific)
2. **tier3_pattern_markdown_related_docs** (architectural level, cross-branch)

**Recommendation:** tier3 (Related Docs = architectural pattern for context linking, not syntax)

**Impact:** LOW (pattern works in both locations, tier3 more explicit about cross-branch nature)

---

### Q4: Should config_schema.py be in CODE tak or new CONFIG_CODE tak?

**Context:** config_schema.py scaffolds Pydantic schemas (CODE), but validates CONFIG files (YAML)

**Options:**
1. **CODE tak** (Pydantic = Python code, type: code)
2. **New CONFIG_CODE tak** (distinct from CODE, type: config_schema)

**Recommendation:** CODE tak (Pydantic schemas are Python code, validated via tier2_base_python)

**Impact:** LOW (classification clarity, no technical difference)

---

## Conclusions

### Summary of Architectural Decisions

1. **SRP for Tier 3:** Monolithic tier3 templates rejected, decomposed into 17 granular pattern templates (9 CODE + 8 DOCUMENT)

2. **Block Library Composition:** Tier3 patterns are BLOCK LIBRARIES ({% import %}), not inheritance chain ({% extends %})

3. **CONFIG Tak Elimination:** YAML files are DATA validated by Pydantic schemas (CODE), not scaffoldable templates

4. **Validation Hierarchy:** Tier 0-2 STRICT (syntax), Tier 3 ARCHITECTURAL (patterns), Concrete GUIDELINE (best practices)

5. **Tier 2 Justification:** Prevents 32 syntax duplications (type hints, async, docstrings, base classes) across 14 concrete templates

6. **Cross-Branch Patterns:** `tier3_pattern_markdown_related_docs` shared by documents + tracking (first cross-branch pattern)

7. **Concrete Template Corrections:** All 9 concrete templates need `enforcement: STRICT → GUIDELINE` fix

8. **Tool Template Justified:** tool.py cherry-picks 2 patterns (error + logging), lightweight enough for tier3 composition

9. **Tracking No Tier3:** Tracking artifacts have unique structures, tier2 syntax sufficient (can import cross-branch patterns)

10. **Template Registry Format:** template_registry.yaml → template_registry.json (better parsability)

### Revised Phase 3 Scope

**Create (30h):**
- 9 CODE pattern templates (tier3_pattern_python_*)
- 8 DOCUMENT pattern templates (tier3_pattern_markdown_*)
- 1 concrete template (config_schema.py)
- tier1_base_tracking + tier2_tracking_text/markdown

**Refactor (8h):**
- 5 concrete CODE templates (cherry-pick patterns)
- 3 concrete DOCUMENT templates (cherry-pick patterns)
- 9 concrete templates (fix enforcement levels)
- template_registry.yaml → .json

**Document (16h):**
- Block library composition guide ({% import %} patterns)
- Validation hierarchy integration (Issue #52)
- Cross-branch pattern documentation
- Tier 2 justification (syntax deduplication)

**Remove (0h):**
- tier1_base_config (not created)
- tier3_base_yaml_policy (not created)
- Monolithic tier3 templates (not created)

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| {% import %} complexity | MEDIUM | HIGH | Prototype 2-3 patterns first, validate composition |
| Pattern granularity too fine | LOW | MEDIUM | Each pattern = 1 architectural concern (validated in finding) |
| Cross-branch pattern confusion | MEDIUM | LOW | Document explicitly, provide examples |
| Validation hierarchy enforcement | LOW | HIGH | Integrate with Issue #52 quality gates |
| Effort underestimation | MEDIUM | MEDIUM | 17 pattern templates = systematic work, allow buffer |

### Success Criteria

1. ✅ All 17 tier3 pattern templates created with ARCHITECTURAL enforcement
2. ✅ Worker.py cherry-picks 7 patterns via {% import %} (no monolithic inheritance)
3. ✅ Tool.py cherry-picks 2 patterns (lightweight, justified)
4. ✅ Config_schema.py scaffolds Pydantic schemas (replaces CONFIG tak)
5. ✅ Tracking imports cross-branch `tier3_pattern_markdown_related_docs`
6. ✅ All concrete templates have GUIDELINE enforcement (not STRICT for architectural patterns)
7. ✅ template_registry.json format (not .yaml)
8. ✅ Documentation covers block library composition pattern

### Next Steps (Phase 3 Execution Order)

**Week 1-2: Pattern Templates (30h)**
1. Create 9 CODE pattern templates (tier3_pattern_python_*)
2. Create 8 DOCUMENT pattern templates (tier3_pattern_markdown_*)
3. Prototype worker.py refactoring with 2-3 patterns (validate {% import %} approach)

**Week 3: Refactoring (8h)**
4. Refactor 5 CODE concrete templates (worker, dto, service, tool, config_schema)
5. Refactor 3 DOCUMENT concrete templates (research, planning, design)
6. Fix 9 concrete template enforcement levels (STRICT → GUIDELINE)
7. Convert template_registry.yaml → template_registry.json

**Week 4: Tracking + Documentation (27h)**
8. Create tier1_base_tracking + tier2_tracking_text/markdown (11h)
9. Write documentation: block library guide, validation hierarchy, cross-branch patterns (16h)

**Week 5: Testing + Validation (buffer)**
10. Integration testing with Issue #52 quality gates
11. Validation hierarchy enforcement testing
12. Cherry-picking pattern composition testing

**Total: 65h (5 weeks)**

## Quick Reference: Tier Element Matrix

### Master Template Inventory (All Tiers)

| Tier | Template File | Elements Provided | Rationale | Enforcement |
|------|--------------|-------------------|-----------|-------------|
| **0** | tier0_base_artifact.jinja2 | `<!-- path -->`<br>`<!-- metadata -->` | Universal 2-line SCAFFOLD for all files | STRICT |
| **1** | tier1_base_code.jinja2 | Module docstring<br>Import sections (3-group)<br>Class structure placeholder<br>Method blocks | Format: "This is a CODE file" (vs doc/tracking) | STRICT |
| **1** | tier1_base_document.jinja2 | Status/Version/Date header<br>Purpose section<br>Scope (In/Out)<br>Prerequisites (numbered)<br>Related Docs<br>Version History table | Format: "This is a DOCUMENT file" | STRICT |
| **1** | tier1_base_tracking.jinja2 | Workflow metadata<br>No versioning<br>No status lifecycle<br>Ephemeral structure | Format: "This is a TRACKING file" (VCS artifacts) | STRICT |
| **2** | tier2_base_python.jinja2 | `from typing import`<br>`"""..."""` docstrings<br>`async def`, `await`<br>`class X(BaseModel):`<br>`__init__`, `__str__`, `__repr__` | Syntax: Python-specific features (vs Java/TS) | STRICT |
| **2** | tier2_base_markdown.jinja2 | ` ``` language ``` ` code blocks<br>`[ref]: url` link definitions<br>`# ## ###` headers<br>`---` dividers | Syntax: Markdown-specific formatting | STRICT |
| **2** | tier2_base_yaml.jinja2 | 2-space indentation<br>`key: value` format<br>`- list` syntax<br>Comment format `#` | Syntax: YAML-specific rules | STRICT |
| **2** | tier2_tracking_text.jinja2 | Line breaks (no markup)<br>Plain text format | Syntax: Text-specific (commit messages) | STRICT |
| **2** | tier2_tracking_markdown.jinja2 | Markdown syntax (same as tier2_base_markdown)<br>Checkboxes `- [ ]`<br>Bold/italic | Syntax: Markdown for tracking (PR, issue) | STRICT |
| **3** | tier3_pattern_python_async.jinja2 | `async def` methods<br>`await` calls<br>Async context managers | Pattern: Async/Await architectural pattern | ARCHITECTURAL |
| **3** | tier3_pattern_python_lifecycle.jinja2 | `IWorkerLifecycle` interface<br>`__init__(build_spec)`<br>`initialize(**capabilities)`<br>`shutdown()`<br>`_initialized` flag | Pattern: Two-phase initialization | ARCHITECTURAL |
| **3** | tier3_pattern_python_pydantic.jinja2 | `BaseModel` inheritance<br>`Field()` validators<br>`@model_validator`<br>Immutability config | Pattern: Pydantic DTO validation | ARCHITECTURAL |
| **3** | tier3_pattern_python_error.jinja2 | `try-except` wrapper<br>`logger.exception()`<br>Custom exceptions<br>Error propagation | Pattern: Error handling | ARCHITECTURAL |
| **3** | tier3_pattern_python_logging.jinja2 | `logging.getLogger(__name__)`<br>Logger setup<br>Contextual logging calls | Pattern: Logging infrastructure | ARCHITECTURAL |
| **3** | tier3_pattern_python_typed_id.jinja2 | `uuid4()` generation<br>`generate_id()` methods<br>ID type hints | Pattern: Typed ID generation | ARCHITECTURAL |
| **3** | tier3_pattern_python_di.jinja2 | `Capabilities` parameter<br>Constructor injection<br>`**capabilities` kwargs | Pattern: Dependency Injection | ARCHITECTURAL |
| **3** | tier3_pattern_python_log_enricher.jinja2 | `LogEnricher.enrich()` calls<br>Context propagation | Pattern: Context-aware logging | ARCHITECTURAL |
| **3** | tier3_pattern_python_translator.jinja2 | `Translator.translate()` calls<br>i18n keys<br>Locale handling | Pattern: Internationalization | ARCHITECTURAL |
| **3** | tier3_pattern_markdown_status_header.jinja2 | `**Status:** DRAFT`<br>`**Version:** 1.0`<br>`**Last Updated:**` | Pattern: Document status tracking | ARCHITECTURAL |
| **3** | tier3_pattern_markdown_purpose_scope.jinja2 | `## Purpose`<br>`## Scope`<br>In Scope / Out of Scope | Pattern: Document scoping | ARCHITECTURAL |
| **3** | tier3_pattern_markdown_prerequisites.jinja2 | `## Prerequisites`<br>Numbered list "Read these first" | Pattern: Dependency documentation | ARCHITECTURAL |
| **3** | tier3_pattern_markdown_agent_hints.jinja2 | `agent_hints:` block<br>phase, purpose, belongs_here, pitfalls | Pattern: Agent guidance metadata | ARCHITECTURAL |
| **3** | tier3_pattern_markdown_related_docs.jinja2 | `## Related Documentation`<br>`- [doc][ref]`<br>`[ref]: path` | Pattern: Cross-referencing (CROSS-BRANCH!) | ARCHITECTURAL |
| **3** | tier3_pattern_markdown_version_history.jinja2 | `## Version History`<br>Table: Version/Date/Author/Changes | Pattern: Change tracking | ARCHITECTURAL |
| **3** | tier3_pattern_markdown_open_questions.jinja2 | `## Open Questions`<br>`- ❓ Question` list | Pattern: Knowledge gaps documentation | ARCHITECTURAL |
| **3** | tier3_pattern_markdown_dividers.jinja2 | `---` section separators<br>Visual structure | Pattern: Document sectioning | ARCHITECTURAL |
| **Concrete** | worker.py.jinja2 | Specific imports<br>Worker name/layer<br>Responsibilities list<br>Capability requirements | Implementation: Specific worker logic | GUIDELINE |
| **Concrete** | dto.py.jinja2 | Specific fields<br>Field types<br>Validators<br>Default values | Implementation: Specific DTO structure | GUIDELINE |
| **Concrete** | tool.py.jinja2 | MCP tool contract<br>`execute()` method<br>Tool-specific logic | Implementation: Specific tool functionality | GUIDELINE |
| **Concrete** | research.md.jinja2 | `## Problem Statement`<br>`## Research Goals`<br>`## Findings`<br>Specific content | Implementation: Research document content | GUIDELINE |
| **Concrete** | commit.txt.jinja2 | Conventional Commits format<br>`type(scope): message`<br>Body/footer | Implementation: Commit message format | GUIDELINE |

---

### CODE Tak: Element Flow (Tier 0 → Concrete)

| Element | Tier 0 | Tier 1 (CODE) | Tier 2 (Python) | Tier 3 (Pattern) | Concrete (worker.py) |
|---------|--------|---------------|-----------------|------------------|----------------------|
| **SCAFFOLD** | ✅ 2 lines | Inherited | Inherited | Inherited | Inherited |
| **Module docstring** | ❌ | ✅ Generic (@layer) | Inherited | Inherited | ✅ Specific responsibilities |
| **Imports: stdlib/3rd/project** | ❌ | ✅ 3-group structure | Inherited | Imported patterns add | ✅ Specific imports |
| **Type hints** | ❌ | ❌ | ✅ `from typing import` | Inherited | ✅ Specific types |
| **Docstring format** | ❌ | ✅ Generic | ✅ `"""..."""` Python | Inherited | ✅ Specific descriptions |
| **Class definition** | ❌ | ✅ `class X:` | ✅ `class X(Y):` support | Imported patterns add interfaces | ✅ `class SignalWorker(IWorker, IWorkerLifecycle):` |
| **Async syntax** | ❌ | ❌ | ✅ `async def`, `await` | ✅ tier3_pattern_python_async | ✅ Async methods |
| **Lifecycle pattern** | ❌ | ❌ | ❌ | ✅ tier3_pattern_python_lifecycle | ✅ Cherry-picked |
| **Error handling** | ❌ | ❌ | ❌ | ✅ tier3_pattern_python_error | ✅ Cherry-picked |
| **Logging** | ❌ | ❌ | ❌ | ✅ tier3_pattern_python_logging | ✅ Cherry-picked |
| **DI pattern** | ❌ | ❌ | ❌ | ✅ tier3_pattern_python_di | ✅ Cherry-picked |
| **Specific fields** | ❌ | ❌ | ❌ | ❌ | ✅ Worker-specific logic |

**Key Insight:** Each tier adds a layer of specificity. Tier 3 patterns are IMPORTED (cherry-picked), not inherited.

---

### DOCUMENT Tak: Element Flow (Tier 0 → Concrete)

| Element | Tier 0 | Tier 1 (DOCUMENT) | Tier 2 (Markdown) | Tier 3 (Pattern) | Concrete (research.md) |
|---------|--------|-------------------|-------------------|------------------|------------------------|
| **SCAFFOLD** | ✅ 2 lines | Inherited | Inherited | Inherited | Inherited |
| **Status header** | ❌ | ✅ Generic header | Inherited | ✅ tier3_pattern_markdown_status_header | ✅ Cherry-picked |
| **Purpose section** | ❌ | ✅ Generic Purpose | Inherited | ✅ tier3_pattern_markdown_purpose_scope | ✅ Specific purpose |
| **Scope (In/Out)** | ❌ | ✅ Generic scope | Inherited | ✅ tier3_pattern_markdown_purpose_scope | ✅ Specific scope |
| **Prerequisites** | ❌ | ✅ Numbered list | Inherited | ✅ tier3_pattern_markdown_prerequisites | ✅ Specific prereqs |
| **Code blocks** | ❌ | ❌ | ✅ ` ``` language ``` ` | Inherited | ✅ Specific code examples |
| **Link definitions** | ❌ | ❌ | ✅ `[ref]: url` | Inherited | ✅ Specific links |
| **Related Docs** | ❌ | ✅ Generic section | Inherited | ✅ tier3_pattern_markdown_related_docs | ✅ Specific related docs |
| **Version History** | ❌ | ✅ Generic table | Inherited | ✅ tier3_pattern_markdown_version_history | ✅ Specific versions |
| **Agent hints** | ❌ | ❌ | ❌ | ✅ tier3_pattern_markdown_agent_hints | ✅ Research-specific hints |
| **Open Questions** | ❌ | ❌ | ❌ | ✅ tier3_pattern_markdown_open_questions | ✅ Specific questions |
| **Findings section** | ❌ | ❌ | ❌ | ❌ | ✅ Research-specific content |

**Key Insight:** DOCUMENT tier1 provides more structure than CODE tier1 (Purpose, Scope, Version History are document-specific).

---

### TRACKING Tak: Element Flow (Tier 0 → Concrete)

| Element | Tier 0 | Tier 1 (TRACKING) | Tier 2 (Markdown) | Tier 3 (Pattern) | Concrete (pr.md) |
|---------|--------|-------------------|-------------------|------------------|------------------|
| **SCAFFOLD** | ✅ 2 lines | Inherited | Inherited | Imported | Inherited |
| **No versioning** | ❌ | ✅ Tracking characteristic | Inherited | N/A | Inherited |
| **No status lifecycle** | ❌ | ✅ Tracking characteristic | Inherited | N/A | Inherited |
| **Workflow metadata** | ❌ | ✅ Branch, issue, labels | Inherited | N/A | ✅ Specific PR metadata |
| **Markdown headers** | ❌ | ❌ | ✅ `# ## ###` | Inherited | ✅ PR sections |
| **Checkboxes** | ❌ | ❌ | ✅ `- [ ] task` | Inherited | ✅ PR checklist |
| **Related Docs** | ❌ | ❌ | ❌ | ✅ tier3_pattern_markdown_related_docs (IMPORTED!) | ✅ Related issues/docs |
| **PR-specific sections** | ❌ | ❌ | ❌ | ❌ | ✅ Changes, Testing, Breaking |

**Key Insight:** Tracking has NO tier3 patterns of its own, but can IMPORT cross-branch patterns (related_docs).

---

### Decision Tree: "Where Does This Element Go?"

| If Element Is... | Then Tier... | Example | Why? |
|-----------------|--------------|---------|------|
| **Present in ALL files** | Tier 0 | SCAFFOLD metadata | Universal requirement |
| **Defines file TYPE** (code vs doc vs tracking) | Tier 1 | Module docstring vs Purpose section | Format-level distinction |
| **Language/format SYNTAX** | Tier 2 | `from typing import` (Python)<br>` ``` code ``` ` (Markdown) | Syntax-specific, not semantic |
| **Architectural PATTERN** (2+ templates share) | Tier 3 | IWorkerLifecycle, Pydantic, Related Docs | Reusable design pattern |
| **Specific IMPLEMENTATION** | Concrete | Worker name, DTO fields, Research findings | Unique to this artifact |
| **Best practice SUGGESTION** | Concrete (guideline) | "Consider logging" | Optional recommendation |

---

### Pattern Cherry-Picking: Concrete Template Composition

| Concrete Template | Extends | Imports (Cherry-Picked Patterns) | Total Patterns |
|-------------------|---------|----------------------------------|----------------|
| **worker.py** | tier2_base_python | async, lifecycle, error, logging, di, log_enricher, translator | 7 |
| **adapter.py** | tier2_base_python | async, lifecycle, error, logging, di, log_enricher, translator | 7 |
| **dto.py** | tier2_base_python | pydantic, typed_id, logging | 3 |
| **schema.py** | tier2_base_python | pydantic, typed_id, logging | 3 |
| **config_schema.py** | tier2_base_python | pydantic, typed_id, logging | 3 |
| **service.py** | tier2_base_python | async, error, logging, di, translator | 5 |
| **tool.py** | tier2_base_python | error, logging | 2 |
| **generic.py** | tier2_base_python | logging | 1 |
| **research.md** | tier2_base_markdown | status_header, purpose_scope, prerequisites, agent_hints, related_docs, version_history, open_questions | 7 |
| **planning.md** | tier2_base_markdown | status_header, purpose_scope, prerequisites, agent_hints, related_docs, version_history | 6 |
| **design.md** | tier2_base_markdown | status_header, purpose_scope, agent_hints, related_docs, version_history, open_questions, dividers | 7 |
| **architecture.md** | tier2_base_markdown | status_header, purpose_scope, related_docs, version_history, dividers, agent_hints | 6 |
| **reference.md** | tier2_base_markdown | status_header, purpose_scope, related_docs, version_history, dividers | 5 |
| **pr.md** | tier2_tracking_markdown | related_docs (CROSS-BRANCH!) | 1 |
| **issue.md** | tier2_tracking_markdown | related_docs (CROSS-BRANCH!) | 1 |
| **commit.txt** | tier2_tracking_text | (none) | 0 |

**Key Insight:** Concrete templates cherry-pick 0-7 patterns depending on complexity. Tool.py = 2 patterns (lightweight), Worker.py = 7 patterns (complex).

---

### Validation Hierarchy: What Each Tier Checks

| Tier | Enforcement | Checks | Passes If... | Fails If... | Example |
|------|-------------|--------|--------------|-------------|---------|
| **Tier 0** | STRICT | SCAFFOLD present | Both lines exist:<br>`<!-- path -->`<br>`<!-- metadata -->` | Missing or malformed SCAFFOLD | Build error |
| **Tier 1** | STRICT | FORMAT structure | Has required sections:<br>- CODE: docstring, imports, class<br>- DOC: Purpose, Scope, Version History | Missing required section | Build error |
| **Tier 2** | STRICT | SYNTAX compliance | Language-specific syntax:<br>- Python: `from typing import`, `"""`<br>- Markdown: ` ``` `, `[ref]:` | Invalid syntax for language | Build error |
| **Tier 3** | ARCHITECTURAL | PATTERN presence | Pattern implemented:<br>- IWorkerLifecycle: has `initialize()`<br>- Pydantic: has `Field()` validators | Pattern missing or incomplete | Warning (quality gate) |
| **Concrete** | GUIDELINE | BEST PRACTICES | Follows recommendations:<br>- Logging added<br>- Error handling present | Suggestion not followed | Info message only |

**Key Insight:** Only tier 0-2 cause build failures. Tier 3 = quality gate warnings. Concrete = suggestions.

---

### Cross-Branch Pattern: Related Docs

| Branch | Template | Uses Related Docs Pattern? | Why? |
|--------|----------|----------------------------|------|
| **DOCUMENT** | research.md | ✅ YES | Links to planning.md, design.md for phase flow |
| **DOCUMENT** | planning.md | ✅ YES | Links to research.md, design.md |
| **DOCUMENT** | design.md | ✅ YES | Links to planning.md, architecture.md |
| **DOCUMENT** | architecture.md | ✅ YES | Links to design docs, reference docs |
| **DOCUMENT** | reference.md | ✅ YES | Links to related API docs |
| **TRACKING** | pr.md | ✅ YES | Links to related issues, design docs |
| **TRACKING** | issue.md | ✅ YES | Links to related PRs, documentation |
| **TRACKING** | milestone.md | ❌ NO | Milestone = aggregate view, not contextual |
| **TRACKING** | changelog.md | ❌ NO | Changelog = chronological, not cross-referencing |
| **TRACKING** | commit.txt | ❌ NO | Commit = atomic, no links |

**Total Usage: 7 of 15 concrete templates = 47% adoption**

**Key Insight:** `tier3_pattern_markdown_related_docs` is the ONLY cross-branch pattern (used by DOCUMENT + TRACKING branches).

---

## Related Documentation
- **[planning.md](planning.md)** - Original Phase 3 tasks (superseded by this research)
- **[phase2-task22-iworkerlifecycle-audit.md](phase2-task22-iworkerlifecycle-audit.md)** - IWorkerLifecycle pattern analysis
- **[phase2-task23-backend-pattern-catalog.md](phase2-task23-backend-pattern-catalog.md)** - 12 backend patterns catalog
- **[tracking-type-architecture.md](tracking-type-architecture.md)** - Tracking as 4th tier1 type
- **[tdd-planning.md](tdd-planning.md)** - Phase 1 TDD cycles (document template MVP)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-01-30 | Agent | Complete SRP revision: monolithic → granular patterns, block library composition, CONFIG tak elimination, validation hierarchy, cross-branch patterns |
| 1.0 | 2026-01-30 | Agent | Initial draft identifying monolithic tier3 as anti-pattern |

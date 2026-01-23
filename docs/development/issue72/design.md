# Issue #72 Multi-Tier Template Architecture - Design

<!-- SCAFFOLD: design:v1 | 2026-01-23 | docs/development/issue72/design.md -->

**Status:** DRAFT  
**Phase:** Design (Transitioned from Planning)  
**Date:** 2026-01-23  
**Input:** [planning.md](planning.md) (766 lines), [research_summary.md](research_summary.md) (719 lines)

---

## 1. Overview

### 1.1 Purpose

Define **technical architecture** for 5-tier Jinja2 template system that:
- Eliminates DRY violation (SCAFFOLD metadata once, inherited by all)
- Enables language-agnostic extensibility (TypeScript = 1 Tier 2 template, not 13+ duplicates)
- Provides inheritance-aware introspection (complete variable schema from all tiers)
- Integrates with validation infrastructure (Issue #52 TEMPLATE_METADATA format)

**Scope Distinction:**
- ✅ **Design = HOW to architect (API specs, data structures, algorithms)**
- ❌ **Design ≠ Implementation (actual code written in TDD phase)**

### 1.2 Scope

**In Scope:**
- Jinja2 template tier structure (5 levels: Tier 0→1→2→3→Concrete)
- Inheritance introspection API (`introspect_template(name, with_inheritance=True)`)
- Template registry format (`.st3/template_registry.yaml` structure)
- SCAFFOLD metadata generation (1-line format, comment syntax adaptation)
- Validation integration (TEMPLATE_METADATA per Issue #52)
- Migration strategy (24 legacy templates → multi-tier)

**Out of Scope (Reserved for TDD Phase):**
- Jinja2 template implementation code
- Introspection algorithm Python implementation
- Registry read/write Python code
- Performance optimization (caching, AST walking efficiency)
- UI/UX for scaffolding tool (command-line interface)

### 1.3 Prerequisites

1. ✅ **Planning Phase Complete:**
   - [planning.md](planning.md) - 24 tasks, 183h effort, 3-week timeline
   - Critical path identified: Introspection (12h) → Tier 2 (9h) → Tier 3 (8h)
   
2. ✅ **Research Phase Complete:**
   - [research_summary.md](research_summary.md) - Final decisions on 8 open questions
   - MVP validated: [mvp/](mvp/) - 67% variable coverage improvement proven
   
3. ✅ **Issue #52 Format Documented:**
   - TEMPLATE_METADATA structure: `enforcement` / `level` / `validates.strict` / `validates.guidelines`
   - Validation tiers: STRICT (errors) vs GUIDELINES (warnings)

4. ⚠️ **Critical Blockers (from Planning):**
   - Blocker #1: Inheritance introspection (P0, 12h)
   - Blocker #2: IWorkerLifecycle audit (P0, 6h)
   - Blocker #3: Backend pattern inventory (P1, 16h)

### 1.4 Related Documents

- [research.md](research.md) - Full research with alternatives (2500+ lines)
- [research_summary.md](research_summary.md) - Final decisions and blockers
- [planning.md](planning.md) - Task breakdown, effort estimates, risks
- [mvp/](mvp/) - 5-tier template proof-of-concept
- Issue #52 - Template validation infrastructure (HARD DEPENDENCY)
- Issue #74 - E2E template tests (DTO/Tool validation failures)
- [agent.md](../../agent.md) - Agent cooperation protocol
- [docs/coding_standards/](../../coding_standards/) - Python quality gates

---

## 2. Background

### 2.1 Current State (Problems)

**Problem 1: DRY Violation in SCAFFOLD Metadata**
- **Evidence:** 24 templates each duplicate SCAFFOLD header generation
- **Impact:** Adding new field requires 24-file update
- **Example:**
  ```jinja2
  {# worker.py.jinja2 #}
  # SCAFFOLD: worker:v1.2 | 2026-01-23 | src/workers/MyWorker.py
  
  {# adapter.py.jinja2 #}
  # SCAFFOLD: adapter:v1.1 | 2026-01-23 | src/adapters/MyAdapter.py
  
  {# dto.py.jinja2 #}
  # SCAFFOLD: dto:v2.0 | 2026-01-23 | src/dtos/MyDTO.py
  ```
  → **24x duplication** of SCAFFOLD logic

**Problem 2: Python-Only Architecture**
- **Evidence:** Adding TypeScript requires duplicating 13+ templates (worker, adapter, service, etc.)
- **Root Cause:** Language-specific syntax mixed with format-agnostic structure
- **Projection:** 10 languages × 13 templates = **130 templates** (unmaintainable)

**Problem 3: Incomplete SCAFFOLD Coverage**
- **Evidence:** Only 6 of 29 templates (21%) have SCAFFOLD metadata
- **Impact:** Version tracing incomplete, template detection unreliable
- **Migration Effort:** 24 templates × 1h = 24h manual work

**Problem 4: Template Introspection Misses 67% of Variables**
- **Evidence:** MVP shows single-template introspection returns 2 vars, actual schema has 8 vars
- **Root Cause:** Current `introspect_template()` analyzes single file, ignores parent templates
- **Impact:**
  - Scaffolding cannot validate user input against complete schema
  - Missing required parent variables cause runtime failures
  - Cannot detect which template was used (parent variables missing)

### 2.2 Problem Statement

**Core Issue:** Current single-file template architecture violates DRY and blocks extensibility.

**Business Impact:**
- **Development Velocity:** 10x effort for new languages (130 templates vs 13)
- **Maintenance Cost:** 24-file updates for metadata changes
- **Quality Risk:** Incomplete introspection → invalid scaffolding → production failures

**Technical Constraints:**
- Must maintain backward compatibility during migration (feature flag)
- Must integrate with Issue #52 validation (HARD RELEASE BLOCKER per planning)
- Must pass all 5 quality gates (10/10 Pylint, mypy strict for DTOs)

### 2.3 Requirements (from AC Coverage Analysis)

#### Functional Requirements (9/13 Proven in Research)

**Architecture Requirements (✅ Designed):**
- **FR1:** 5-level template hierarchy implemented (Tier 0→1→2→3→Concrete)
  - _Evidence:_ MVP demonstrates tier chain in `docs/development/issue72/mvp/templates/`
- **FR2:** Base templates cover 3 Tier 1 categories (CODE, DOCUMENT, CONFIG)
  - _Evidence:_ Research Q1 dimensional analysis proves orthogonality
- **FR3:** Template registry operational with hash-based versioning
  - _Evidence:_ Research Q8b defines `.st3/template_registry.yaml` structure
- **FR4:** SCAFFOLD metadata = 1 line (ultra-compact format)
  - _Evidence:_ `# SCAFFOLD: {type}:{hash} | {timestamp} | {path}` proven

**Extensibility Requirements (✅ Proven):**
- **FR5:** Adding new language = 1 Tier 2 template (not 13+ duplicates)
  - _Evidence:_ TypeScript extrapolation from Python MVP
- **FR6:** Adding new format = 1 Tier 1 template
  - _Evidence:_ CONFIG identified as third Tier 1 category
- **FR7:** SCAFFOLD defined once (Tier 0), inherited by all
  - _Evidence:_ MVP `tier0_base_artifact.jinja2` provides `scaffold_metadata` block

**Quality Requirements (⚠️ Blockers Remain):**
- **FR8:** Worker uses IWorkerLifecycle pattern
  - _Status:_ ⚠️ BLOCKER #2 - Hypothesis unvalidated, audit required (planning Task 2.2)
- **FR9:** All backend patterns reflected in templates
  - _Status:_ 🔴 BLOCKER #3 - No inventory exists (planning Task 2.3)
- **FR10:** Research/planning/test templates include agent hints
  - _Status:_ 🔴 GAP - Format undefined (planning Task 2.4, P2 priority)
- **FR11:** Documentation covers usage/patterns
  - _Status:_ 🔴 GAP - Structure undefined (planning Task 3.7, 16h effort)
- **FR12:** All scaffolded code passes validation (Issue #52 integration)
  - _Status:_ ⚠️ DEPENDENCY - Requires #52 completion (HARD RELEASE BLOCKER)
- **FR13:** Template library documented
  - _Status:_ Linked to FR11

#### Non-Functional Requirements

- **NFR1: Performance** - 5-tier introspection <100ms per template (planning Risk #5)
  - _Target:_ Introspection overhead < 10x current single-file approach
  - _Mitigation:_ Caching introspection results, optimize AST walking
  
- **NFR2: Testability** - All generated code passes 5 quality gates (10/10)
  - _Gates:_ Trailing whitespace, import placement, line length <100, mypy strict (DTOs), tests pass
  - _Validation:_ `run_quality_gates(files=[...])` before every commit
  
- **NFR3: Maintainability** - Migration script automates ≥80% of refactoring
  - _Target:_ 24 templates migrated in 13h (1h manual per template)
  - _Automation:_ Mechanical conversion of single-file → multi-tier extends chain
  
- **NFR4: Reliability** - Feature flag enables safe rollback
  - _Mechanism:_ `use_legacy_templates=true` during migration (planning Risk #4)
  - _Rollback Cost:_ 1-2 days to revert, debug, re-deploy

---

## 3. Design

### 3.1 Architecture Position

**System Context:**
```
┌─────────────────────────────────────────────────────────────┐
│ S1mpleTraderV3 MCP Server                                   │
├─────────────────────────────────────────────────────────────┤
│  Scaffolding System                                         │
│  ├── scaffold_artifact(type, name, context) ← Agent calls  │
│  │   ├── Template Selection (artifacts.yaml registry)      │
│  │   ├── Introspection (introspect_template w/ inheritance)│
│  │   ├── Rendering (Jinja2 multi-tier extends)             │
│  │   └── Validation (Issue #52 integration)                │
│  │                                                           │
│  ├── Template Library (THIS DESIGN SCOPE)                  │
│  │   ├── Tier 0: tier0_base_artifact.jinja2               │
│  │   ├── Tier 1: tier1_base_{code,document,config}.jinja2 │
│  │   ├── Tier 2: tier2_base_{python,markdown,yaml}.jinja2 │
│  │   ├── Tier 3: tier3_base_{component,data,tool,...}      │
│  │   └── Concrete: worker.py.jinja2, research.md.jinja2... │
│  │                                                           │
│  ├── Template Registry (.st3/template_registry.yaml)       │
│  │   └── Hash → Full Version Chain Mapping                 │
│  │                                                           │
│  └── Validation Integration (Issue #52)                    │
│      └── TEMPLATE_METADATA: enforcement/level/validates    │
└─────────────────────────────────────────────────────────────┘
```

**Dependency Flow:**
```
Agent (agent.md scaffold_artifact guidance)
  ↓
scaffold_artifact() tool
  ↓
artifacts.yaml (artifact_type → template_file mapping)
  ↓
introspect_template(name, with_inheritance=True)  ← CRITICAL BLOCKER #1
  ↓ (returns complete variable schema from all tiers)
Jinja2 Environment (render with context)
  ↓ (multi-tier {% extends %} chain)
Generated File (with SCAFFOLD metadata header)
  ↓
Issue #52 Validation (TEMPLATE_METADATA rules)  ← HARD RELEASE BLOCKER
  ↓
Quality Gates (5 gates, 10/10 required)
  ↓
Commit (via git_add_or_commit with TDD phase prefix)
```

### 3.2 Component Design

#### 3.2.1 Template Tier Structure

**5-Level Hierarchy (Orthogonal Dimensions):**

```
Tier 0: Universal (Lifecycle Metadata)
  └── base_artifact.jinja2
      ├── SCAFFOLD metadata block (1-line header)
      ├── Comment syntax adaptation (# vs <!-- vs //)
      └── Timestamp generation

Tier 1: Format Category (Structural Differences)
  ├── base_code.jinja2        → Imports, classes, functions structure
  ├── base_document.jinja2    → Heading hierarchy, sections
  └── base_config.jinja2      → Key-value format, schema validation hooks

Tier 2: Language Syntax (Language-Specific Patterns)
  ├── base_python.jinja2      → Type hints, async/await, docstrings
  ├── base_markdown.jinja2    → Link format, code blocks
  ├── base_yaml.jinja2        → Indentation, key format
  └── base_typescript.jinja2  → (extensibility proof, planning Task 5.1)

Tier 3: Specialization (Domain-Specific Patterns)
  ├── base_python_component.jinja2   → IWorkerLifecycle (if validated)
  ├── base_python_data_model.jinja2  → Immutable, validated DTOs
  ├── base_python_tool.jinja2        → MCP API contracts
  ├── base_markdown_knowledge.jinja2 → Research/planning docs
  ├── base_markdown_ephemeral.jinja2 → Commit messages, PR bodies
  └── base_yaml_policy.jinja2        → GitHub workflows, labels

Tier 4: Concrete (Artifact-Specific Implementation)
  ├── worker.py.jinja2        → Worker-specific logic
  ├── dto.py.jinja2           → DTO-specific fields
  ├── research.md.jinja2      → Research-specific sections
  └── workflows.yaml.jinja2   → Workflow-specific triggers
```

**Tier Responsibility Matrix:**

| Tier | Provides | Examples | Validation Level |
|------|----------|----------|------------------|
| **Tier 0** | SCAFFOLD metadata, timestamp, output_path | 1-line header generation | N/A (universal) |
| **Tier 1** | Format structure blocks | `imports_section`, `heading_h1`, `yaml_root` | STRICT (format correctness) |
| **Tier 2** | Language syntax patterns | `python_type_hint`, `markdown_link`, `yaml_indent` | STRICT (syntax correctness) |
| **Tier 3** | Domain pattern blocks | `lifecycle_init`, `dto_validation`, `mcp_api_contract` | GUIDELINES (best practices) |
| **Tier 4** | Concrete artifact content | `worker_name`, `dto_fields`, `research_sections` | N/A (user-provided) |

**Jinja2 Inheritance Mechanism:**

```jinja2
{# worker.py.jinja2 (Concrete) #}
{% extends "tier3_base_python_component.jinja2" %}

{% block worker_name %}{{ worker_name }}{% endblock %}
{% block worker_logic %}
    # Concrete implementation here
{% endblock %}


{# tier3_base_python_component.jinja2 (Specialization) #}
{% extends "tier2_base_python.jinja2" %}

{% block lifecycle_init %}
    def __init__(self, config: {{ config_type }}):
        self._config = config
        self._client = None
{% endblock %}

{% block lifecycle_initialize %}
    async def initialize(self) -> None:
        self._client = await create_async_client(self._config.url)
{% endblock %}


{# tier2_base_python.jinja2 (Language) #}
{% extends "tier1_base_code.jinja2" %}

{% block type_hints %}from typing import Any, Optional{% endblock %}
{% block async_imports %}import asyncio{% endblock %}


{# tier1_base_code.jinja2 (Format) #}
{% extends "tier0_base_artifact.jinja2" %}

{% block imports_section %}
# Standard library imports
{{ super() }}  {# Calls parent's imports if any #}

# Third-party imports

# Project imports
{% endblock %}

{% block class_structure %}
class {{ class_name }}:
    \"\"\"{{ class_docstring }}\"\"\"
{% endblock %}


{# tier0_base_artifact.jinja2 (Universal) #}
{% block scaffold_metadata %}
{%- if format == "python" -%}
# SCAFFOLD: {{ artifact_type }}:{{ version_hash }} | {{ timestamp }} | {{ output_path }}
{%- elif format == "markdown" -%}
<!-- SCAFFOLD: {{ artifact_type }}:{{ version_hash }} | {{ timestamp }} | {{ output_path }} -->
{%- elif format == "yaml" -%}
# SCAFFOLD: {{ artifact_type }}:{{ version_hash }} | {{ timestamp }} | {{ output_path }}
{%- endif -%}
{% endblock %}
```

**Key Design Decisions:**
1. **Use `{% extends %}` not `{% include %}`** - Ensures single inheritance chain (no diamond problem)
2. **Blocks are override points** - Child templates override parent blocks selectively
3. **`{{ super() }}` for composition** - Child can extend parent block content (not just replace)
4. **Empty blocks in parents** - Provide structure without forcing content

#### 3.2.2 Inheritance-Aware Introspection API

**Problem:** Current `introspect_template(name)` returns only variables from concrete template (2 vars), missing parent variables (6 vars from Tier 0-3).

**Solution:** AST walking via `jinja2.nodes.Extends` to build complete schema.

**API Signature:**

```python
def introspect_template(
    template_name: str,
    *,
    with_inheritance: bool = False,
    env: jinja2.Environment | None = None,
) -> dict[str, Any]:
    """
    Introspect Jinja2 template to extract variable schema.
    
    Args:
        template_name: Template filename (e.g., "worker.py.jinja2")
        with_inheritance: If True, walk {% extends %} chain to collect
                          all variables from parent tiers (CRITICAL for
                          multi-tier templates, default False for
                          backward compatibility)
        env: Jinja2 environment (uses default if None)
    
    Returns:
        Dictionary with:
        - "variables": Set[str] - All undeclared variables
        - "tier_chain": List[str] - Parent template names (if with_inheritance)
        - "blocks": List[str] - Block names defined in template
        - "system_fields": Set[str] - Auto-provided vars (timestamp, version_hash, etc.)
    
    Example:
        >>> schema = introspect_template("worker.py.jinja2", with_inheritance=True)
        >>> schema["variables"]
        {'worker_name', 'worker_description', 'config_type', 'timestamp',
         'version_hash', 'output_path', 'artifact_type'}  # 8 vars (not 2)
        >>> schema["tier_chain"]
        ['tier3_base_python_component.jinja2', 'tier2_base_python.jinja2',
         'tier1_base_code.jinja2', 'tier0_base_artifact.jinja2']
    """
```

**Algorithm (Pseudo-Code):**

```python
def introspect_template_with_inheritance(env, template_name):
    all_vars = set()
    all_blocks = set()
    tier_chain = []
    current = template_name
    
    while current:
        # Load template source
        source, _, _ = env.loader.get_source(env, current)
        
        # Parse AST
        parsed = env.parse(source)
        
        # Extract variables from this tier
        tier_vars = meta.find_undeclared_variables(parsed)
        all_vars.update(tier_vars)
        
        # Extract block names
        for node in parsed.find_all(nodes.Block):
            all_blocks.add(node.name)
        
        # Find parent template ({% extends "parent.jinja2" %})
        extends_nodes = list(parsed.find_all(nodes.Extends))
        if extends_nodes:
            parent_node = extends_nodes[0]  # Only one {% extends %} allowed
            current = parent_node.template.value  # Extract parent filename
            tier_chain.append(current)
        else:
            current = None  # Reached root (Tier 0 has no parent)
    
    # Filter out system-provided variables (auto-populated by scaffolding)
    SYSTEM_FIELDS = {"timestamp", "version_hash", "output_path", "artifact_type"}
    user_vars = all_vars - SYSTEM_FIELDS
    
    return {
        "variables": user_vars,  # User must provide these
        "tier_chain": tier_chain,
        "blocks": list(all_blocks),
        "system_fields": SYSTEM_FIELDS,
    }
```

**Integration Point:**

```python
# In scaffold_artifact() tool implementation
def scaffold_artifact(artifact_type, name, context):
    # 1. Lookup template from artifacts.yaml
    template_file = artifacts_registry[artifact_type]["template"]
    
    # 2. Introspect with inheritance (CRITICAL FIX)
    schema = introspect_template(template_file, with_inheritance=True)
    
    # 3. Validate user context against schema
    required_vars = schema["variables"]
    missing = required_vars - context.keys()
    if missing:
        raise ValueError(f"Missing required variables: {missing}")
    
    # 4. Add system fields (auto-populated)
    full_context = context.copy()
    full_context.update({
        "timestamp": datetime.now().isoformat(),
        "version_hash": compute_version_hash(template_file, schema["tier_chain"]),
        "output_path": resolve_output_path(artifact_type, name),
        "artifact_type": artifact_type,
    })
    
    # 5. Render template
    rendered = env.get_template(template_file).render(full_context)
    
    # 6. Write output + update registry
    write_file(full_context["output_path"], rendered)
    update_template_registry(artifact_type, schema["tier_chain"], full_context["version_hash"])
```

**Testing Requirements (from Planning Task 2.1):**

```python
# Unit Test: Introspection returns complete schema
def test_introspection_with_inheritance():
    schema = introspect_template("worker.py.jinja2", with_inheritance=True)
    
    # Should return 8 vars (2 from concrete + 6 from parents)
    assert len(schema["variables"]) == 8
    assert "worker_name" in schema["variables"]  # Concrete
    assert "config_type" in schema["variables"]  # Tier 3
    
    # Should return tier chain
    assert schema["tier_chain"] == [
        "tier3_base_python_component.jinja2",
        "tier2_base_python.jinja2",
        "tier1_base_code.jinja2",
        "tier0_base_artifact.jinja2",
    ]

# E2E Test: Scaffolding validates against complete schema
def test_scaffolding_rejects_missing_parent_var():
    context = {"worker_name": "MyWorker"}  # Missing config_type from Tier 3
    
    with pytest.raises(ValueError, match="Missing required variables: {'config_type'}"):
        scaffold_artifact("worker", "MyWorker", context)
```

#### 3.2.3 Template Registry Format

**Purpose:** Map version hashes to full tier version chains for traceability.

**File Location:** `.st3/template_registry.yaml`

**Structure:**

```yaml
# .st3/template_registry.yaml
# Auto-generated by scaffold_artifact() - DO NOT EDIT MANUALLY

version: 1.0  # Registry format version
last_updated: "2026-01-23T10:30:00Z"

# Hash → Tier Version Chain Mapping
hashes:
  a3f7b2c1:  # 8-char SHA256 hex (collision-safe per artifact_type)
    artifact_type: "worker"
    created: "2026-01-22T15:45:00Z"
    tier_versions:
      - template: "tier0_base_artifact.jinja2"
        version: "1.0.0"
        checksum: "e8f3a1b9c2d4..."  # Full SHA256 of template file
      - template: "tier1_base_code.jinja2"
        version: "1.1.0"
        checksum: "d4c2b1a9e8f3..."
      - template: "tier2_base_python.jinja2"
        version: "2.0.0"
        checksum: "c1b2a3e4f5d6..."
      - template: "tier3_base_python_component.jinja2"
        version: "1.2.0"
        checksum: "b3c4d5e6f7a8..."
      - template: "worker.py.jinja2"
        version: "3.1.0"
        checksum: "a1b2c3d4e5f6..."
    # Hash input: "worker|tier0_base_artifact.jinja2@1.0.0|tier1_base_code.jinja2@1.1.0|tier2_base_python.jinja2@2.0.0|tier3_base_python_component.jinja2@1.2.0|worker.py.jinja2@3.1.0"
    hash_input: "worker|tier0@1.0.0|tier1_code@1.1.0|tier2_python@2.0.0|tier3_component@1.2.0|worker@3.1.0"

  b4e8f3c2:  # Different hash for research.md
    artifact_type: "research"
    created: "2026-01-23T09:15:00Z"
    tier_versions:
      - template: "tier0_base_artifact.jinja2"
        version: "1.0.0"
        checksum: "e8f3a1b9c2d4..."  # Same Tier 0 as worker
      - template: "tier1_base_document.jinja2"
        version: "1.0.0"
        checksum: "f5d4c3b2a1e9..."  # Different Tier 1 (DOCUMENT not CODE)
      - template: "tier2_base_markdown.jinja2"
        version: "1.5.0"
        checksum: "a2b3c4d5e6f7..."
      - template: "tier3_base_markdown_knowledge.jinja2"
        version: "1.0.0"
        checksum: "c5d6e7f8a9b1..."
      - template: "research.md.jinja2"
        version: "2.0.0"
        checksum: "e7f8a9b1c2d3..."
    hash_input: "research|tier0@1.0.0|tier1_document@1.0.0|tier2_markdown@1.5.0|tier3_knowledge@1.0.0|research@2.0.0"

# Artifact Type → Current Hash Mapping (quick lookup)
current_versions:
  worker: "a3f7b2c1"
  adapter: "c2d3e4f5"
  dto: "d5e6f7a8"
  research: "b4e8f3c2"
  planning: "e7f8a9b1"
  # ... (29 artifact types total after migration)

# Template Version Catalog (all base templates)
templates:
  tier0_base_artifact.jinja2:
    current_version: "1.0.0"
    version_history:
      - version: "1.0.0"
        released: "2026-01-20"
        checksum: "e8f3a1b9c2d4..."
        changes: "Initial release - SCAFFOLD metadata block"
  
  tier1_base_code.jinja2:
    current_version: "1.1.0"
    version_history:
      - version: "1.1.0"
        released: "2026-01-22"
        checksum: "d4c2b1a9e8f3..."
        changes: "Add async import block"
      - version: "1.0.0"
        released: "2026-01-20"
        checksum: "c3b2a1e9f8d4..."
        changes: "Initial release - imports/class/function structure"
  
  # ... (37 templates total: 1 Tier 0 + 3 Tier 1 + 3 Tier 2 + 6 Tier 3 + 24 Concrete)
```

**Hash Calculation Algorithm:**

```python
def compute_version_hash(template_file: str, tier_chain: list[str]) -> str:
    """
    Compute 8-char SHA256 hash of tier version chain.
    
    Collision safety: Includes artifact_type prefix, unique per type.
    
    Args:
        template_file: Concrete template (e.g., "worker.py.jinja2")
        tier_chain: Parent template chain from introspection
    
    Returns:
        8-character hex hash (e.g., "a3f7b2c1")
    """
    # Build full chain (parents + concrete)
    full_chain = tier_chain + [template_file]
    
    # Get artifact type from concrete template filename
    artifact_type = template_file.replace(".jinja2", "").split("/")[-1]
    
    # Build hash input: "{type}|{tier}@{version}|..."
    parts = [artifact_type]
    for template_name in full_chain:
        version = get_template_version(template_name)  # From templates catalog
        short_name = template_name.replace("_base_", "_").replace(".jinja2", "")
        parts.append(f"{short_name}@{version}")
    
    hash_input = "|".join(parts)
    
    # SHA256 truncated to 8 chars (4 bytes = 2^32 possibilities per artifact type)
    full_hash = hashlib.sha256(hash_input.encode()).hexdigest()
    return full_hash[:8]


# Example:
# Input: template_file="worker.py.jinja2", tier_chain=[...]
# Output: "worker|tier0@1.0.0|tier1_code@1.1.0|tier2_python@2.0.0|tier3_component@1.2.0|worker@3.1.0"
# Hash: SHA256("worker|...") → "a3f7b2c14e5f6789abcdef..." → "a3f7b2c1" (first 8 chars)
```

**Registry API (Planning Task 1.1):**

```python
class TemplateRegistry:
    """
    Read/write operations for .st3/template_registry.yaml.
    
    Responsibilities:
    - Load registry from disk (YAML parsing)
    - Lookup hash → tier chain mapping
    - Save new version entry (after scaffolding)
    - Detect hash collisions (within artifact_type namespace)
    """
    
    def __init__(self, registry_path: Path = Path(".st3/template_registry.yaml")):
        self.registry_path = registry_path
        self._data: dict[str, Any] = self._load()
    
    def _load(self) -> dict[str, Any]:
        """Load registry YAML or initialize if missing."""
        if not self.registry_path.exists():
            return {"version": "1.0", "hashes": {}, "current_versions": {}, "templates": {}}
        with self.registry_path.open() as f:
            return yaml.safe_load(f)
    
    def save_version(
        self,
        artifact_type: str,
        version_hash: str,
        tier_chain: list[tuple[str, str]],  # [(template_name, version), ...]
    ) -> None:
        """
        Save new version entry to registry.
        
        Args:
            artifact_type: "worker", "research", etc.
            version_hash: 8-char hex hash
            tier_chain: Full tier chain with versions
        
        Raises:
            ValueError: If hash collision detected (different tier chain for same hash)
        """
        # Check collision
        if version_hash in self._data["hashes"]:
            existing = self._data["hashes"][version_hash]
            if existing["artifact_type"] != artifact_type:
                # Collision across artifact types (CRITICAL ERROR)
                raise ValueError(
                    f"Hash collision: {version_hash} used by {existing['artifact_type']} and {artifact_type}"
                )
            # Same artifact type, check if tier chain matches
            existing_chain = [
                (tier["template"], tier["version"])
                for tier in existing["tier_versions"]
            ]
            if existing_chain == tier_chain:
                # Exact match, no-op
                return
            else:
                # Collision within artifact type (version changed)
                raise ValueError(
                    f"Hash collision: {version_hash} for {artifact_type} maps to different tier versions"
                )
        
        # Save entry
        self._data["hashes"][version_hash] = {
            "artifact_type": artifact_type,
            "created": datetime.now().isoformat(),
            "tier_versions": [
                {"template": name, "version": ver, "checksum": get_checksum(name)}
                for name, ver in tier_chain
            ],
            "hash_input": self._build_hash_input(artifact_type, tier_chain),
        }
        self._data["current_versions"][artifact_type] = version_hash
        self._persist()
    
    def lookup_hash(self, version_hash: str) -> dict[str, Any] | None:
        """
        Lookup tier chain by hash.
        
        Returns:
            Dict with artifact_type, tier_versions, created timestamp
            or None if hash not found
        """
        return self._data["hashes"].get(version_hash)
    
    def get_current_version(self, artifact_type: str) -> str | None:
        """Get current hash for artifact type."""
        return self._data["current_versions"].get(artifact_type)
    
    def _persist(self) -> None:
        """Write registry to disk."""
        self._data["last_updated"] = datetime.now().isoformat()
        with self.registry_path.open("w") as f:
            yaml.safe_dump(self._data, f, sort_keys=False)
```

#### 3.2.4 SCAFFOLD Metadata Generation

**Tier 0 Responsibility:** Provide 1-line header that adapts to output format.

**Template Block (tier0_base_artifact.jinja2):**

```jinja2
{# tier0_base_artifact.jinja2 #}
{% block scaffold_metadata -%}
{%- set comment_start = "#" if format in ["python", "yaml", "shell"] else "<!--" -%}
{%- set comment_end = "" if format in ["python", "yaml", "shell"] else " -->" -%}
{{comment_start}} SCAFFOLD: {{artifact_type}}:{{version_hash}} | {{timestamp}} | {{output_path}}{{comment_end}}
{%- endblock %}

{% block content -%}
{# Child templates override this block #}
{%- endblock %}
```

**Output Examples:**

```python
# Python file (worker.py)
# SCAFFOLD: worker:a3f7b2c1 | 2026-01-23T10:30:00Z | src/workers/MyWorker.py

class MyWorker:
    ...
```

```markdown
<!-- Markdown file (research.md) -->
<!-- SCAFFOLD: research:b4e8f3c2 | 2026-01-23T09:15:00Z | docs/development/issue72/research.md -->

# Issue #72 Research
...
```

```yaml
# YAML file (workflows.yaml)
# SCAFFOLD: workflow:c5d6e7f8 | 2026-01-23T11:00:00Z | .github/workflows/ci.yaml

name: CI Pipeline
...
```

**Validation (Issue #52 Integration):**

All base templates (Tier 1-3) include TEMPLATE_METADATA for validation hooks:

```jinja2
{# tier1_base_code.jinja2 #}
{% extends "tier0_base_artifact.jinja2" %}

{#
TEMPLATE_METADATA:
  enforcement: STRICT
  level: format
  validates:
    strict:
      - rule: "scaffold_header"
        pattern: "^# SCAFFOLD: "
        message: "Missing SCAFFOLD metadata header"
      - rule: "imports_at_top"
        pattern: "^(from |import )"
        message: "Imports must be at top-level"
#}

{% block imports_section -%}
# Standard library imports

# Third-party imports

# Project imports

{%- endblock %}
```

**Integration with Issue #52 (HARD DEPENDENCY):**

```python
# After scaffolding, validate output
def validate_scaffolded_file(output_path: Path, artifact_type: str) -> ValidationResult:
    """
    Validate scaffolded file against TEMPLATE_METADATA rules.
    
    Integrates with Issue #52 validation infrastructure.
    
    Args:
        output_path: Generated file path
        artifact_type: "worker", "research", etc.
    
    Returns:
        ValidationResult with errors (STRICT failures) and warnings (GUIDELINE suggestions)
    """
    # Load TEMPLATE_METADATA from template
    template_file = artifacts_registry[artifact_type]["template"]
    metadata = extract_template_metadata(template_file)
    
    # Validate against rules (Issue #52 API)
    result = validation_service.validate_file(
        file_path=output_path,
        enforcement=metadata["enforcement"],  # STRICT or ARCH or GUIDELINE
        level=metadata["level"],              # format, syntax, architecture
        rules=metadata["validates"]["strict"],  # Error rules
    )
    
    return result
```

**Validation Tiers (from Issue #52 Alignment section):**

| Tier | Enforcement | validates.strict (Errors) | validates.guidelines (Warnings) |
|------|-------------|---------------------------|----------------------------------|
| **Tier 0** | N/A | SCAFFOLD header format | N/A |
| **Tier 1** | STRICT | Format structure (imports, headings, keys) | N/A |
| **Tier 2** | STRICT | Language syntax (type hints, link format) | N/A |
| **Tier 3** | GUIDELINES | N/A | Architectural patterns (lifecycle, DI) |
| **Tier 4** | N/A | N/A | N/A (concrete content) |

---

## 4. Implementation Plan

### 4.1 Phases (from Planning Doc)

Implementation follows TDD phase in 5 sub-phases:

#### Phase 1: Foundation (Infrastructure) - 2 weeks

**Planning Tasks:**
- Task 1.1: Template Registry Infrastructure (8h)
- Task 1.2: Tier 0 Base (2h)
- Task 1.3: Tier 1 Bases (6h)
- Task 1.4: Tier 2 Bases (9h)
- Task 1.5: Issue #52 Alignment (6h)

**TDD Approach:**
1. **RED:** Write tests for `TemplateRegistry` class (save_version, lookup_hash)
2. **GREEN:** Implement YAML read/write logic
3. **REFACTOR:** Add hash collision detection
4. **RED:** Write tests for Tier 0-2 templates (inheritance chain correctness)
5. **GREEN:** Create Jinja2 template files with extends chains
6. **REFACTOR:** Extract common blocks, optimize variable passing

**Exit Criteria:**
- [ ] All unit tests passing (TemplateRegistry: 20+ tests)
- [ ] Tier 0-2 templates scaffold correctly (E2E test: 3 formats × 3 languages = 9 tests)
- [ ] Quality gates passed (10/10 Pylint, mypy strict)

#### Phase 2: Blocker Resolution (Critical Path) - 1 week

**Planning Tasks:**
- Task 2.1: Fix Inheritance Introspection (12h) - **P0 CRITICAL**
- Task 2.2: IWorkerLifecycle Audit (6h) - **P0 BLOCKER**
- Task 2.3: Backend Pattern Inventory (16h) - P1
- Task 2.4: Agent Hint Format Prototype (6h) - P2

**TDD Approach:**
1. **RED:** Test `introspect_template(with_inheritance=True)` returns 8 vars (not 2)
2. **GREEN:** Implement AST walking via `jinja2.nodes.Extends`
3. **REFACTOR:** Optimize performance (<100ms per template)
4. **RED:** Test scaffolding rejects missing parent variable
5. **GREEN:** Integrate introspection into `scaffold_artifact()`
6. **REFACTOR:** Add caching for introspection results

**Exit Criteria:**
- [ ] Introspection returns complete schema (worker.py: 8 vars)
- [ ] Scaffolding validates against inherited variables
- [ ] IWorkerLifecycle audit complete (decision: include or remove from AC5)
- [ ] Backend pattern catalog complete (80% coverage minimum)

#### Phase 3: Tier 3 Specialization (Quality) - 1.5 weeks

**Planning Tasks:**
- Task 3.1: Tier 3 Python Component (8h)
- Task 3.2: Tier 3 Python Data Model (6h)
- Task 3.3: Tier 3 Python Tool (6h)
- Task 3.4: Tier 3 Markdown Knowledge (4h)
- Task 3.5: Tier 3 Markdown Ephemeral (3h)
- Task 3.6: Tier 3 YAML Policy (3h)
- Task 3.7: Documentation (16h)

**TDD Approach:**
1. **RED:** Test worker template generates IWorkerLifecycle methods (if validated)
2. **GREEN:** Create Tier 3 component template with lifecycle blocks
3. **REFACTOR:** Extract DI patterns to reusable blocks
4. **RED:** Test DTO template generates immutable Pydantic model
5. **GREEN:** Create Tier 3 data model template with validation hooks
6. **REFACTOR:** Optimize for readability (100-char line limit)

**Exit Criteria:**
- [ ] All 6 Tier 3 templates created and tested
- [ ] Generated code passes all 5 quality gates
- [ ] Documentation complete (architecture guide + usage examples)

#### Phase 4: Migration (Legacy Conversion) - 1.5 weeks

**Planning Tasks:**
- Task 4.1: Migration Script (12h)
- Task 4.2: Migrate CODE Templates (13h)
- Task 4.3: Migrate DOCUMENT Templates (9h)
- Task 4.4: Create CONFIG Templates (4h)
- Task 4.5: E2E Testing (16h) - **Coordinate with Issue #74**
- Task 4.6: Feature Flag Cleanup (4h)

**TDD Approach:**
1. **RED:** Test migration script converts worker.py.jinja2 to multi-tier
2. **GREEN:** Implement AST transformation (single-file → extends chain)
3. **REFACTOR:** Handle edge cases (custom blocks, SCAFFOLD metadata)
4. **RED:** Test all 24 templates scaffold correctly
5. **GREEN:** Migrate templates one-by-one with validation
6. **REFACTOR:** Remove feature flag, delete legacy templates

**Exit Criteria:**
- [ ] Migration script handles 80% of refactoring automatically
- [ ] All 24 legacy templates migrated to multi-tier
- [ ] Zero validation failures (Issue #74 test suite passes)
- [ ] Feature flag removed (codebase uses only multi-tier templates)

#### Phase 5: Extensibility Proof (Final Validation) - 3 days

**Planning Tasks:**
- Task 5.1: Add TypeScript Language (4h) - **AC10 proof**
- Task 5.3: Extensibility Documentation (4h)

**TDD Approach:**
1. **RED:** Test TypeScript worker scaffolds with 1 new template (not 13+)
2. **GREEN:** Create Tier 2 TypeScript template
3. **REFACTOR:** Verify no duplication (DRY validation)

**Exit Criteria:**
- [ ] TypeScript Tier 2 proves language extensibility
- [ ] CONFIG Tier 1 proves format extensibility (completed in Phase 4)
- [ ] "How to Add a New Language" guide complete

### 4.2 Testing Strategy

| Test Type | Scope | Count Target | Example |
|-----------|-------|--------------|---------|
| **Unit** | TemplateRegistry | 20+ | `test_save_version_detects_collision()` |
| **Unit** | Introspection | 15+ | `test_introspect_with_inheritance_returns_8_vars()` |
| **Integration** | Template Rendering | 30+ | `test_worker_template_extends_tier_3_component()` |
| **E2E** | Scaffolding | 29+ | `test_scaffold_worker_passes_quality_gates()` (1 per artifact type) |
| **E2E** | Migration | 24+ | `test_migrate_legacy_worker_to_multitier()` (1 per legacy template) |
| **Performance** | Introspection | 3+ | `test_introspection_completes_under_100ms()` |

**Quality Gates (Mandatory 10/10):**

```powershell
# Gate 1: Trailing whitespace & parentheses
(Get-Content mcp_server/scaffolding/template_introspector.py) | ForEach-Object { $_.TrimEnd() } | Set-Content mcp_server/scaffolding/template_introspector.py

# Gate 2: Import placement (top-level only)
Select-String -Path "mcp_server/**/*.py" -Pattern "^\s+(from |import )" -NotMatch

# Gate 3: Line length (<100 chars)
Get-Content mcp_server/scaffolding/*.py | Where-Object { $_.Length -gt 100 }

# Gate 4: Type checking (mypy strict for DTOs)
mypy --strict mcp_server/dtos/

# Gate 5: Tests passing (100%)
pytest tests/ -v
```

---

## 5. Alternatives Considered

### Alternative A: Single-File Templates with Macros

**Description:** Keep single-file templates, use Jinja2 `{% macro %}` for shared logic.

**Pros:**
- Simpler mental model (no inheritance chain)
- Existing templates require minimal changes
- No introspection complexity (single file = complete schema)

**Cons:**
- Still requires 13+ templates per language (TypeScript duplication)
- Macro calls explicit in every template (not automatic inheritance)
- SCAFFOLD metadata still duplicated (macro call ≠ block override)
- Mixing macro definitions and usage reduces readability

**Decision:** Rejected - Does not solve DRY violation or extensibility problem.

---

### Alternative B: Code Generation (No Jinja2 Templates)

**Description:** Python functions generate code programmatically (like Black's AST builder).

**Pros:**
- Full Python type safety (no template string errors)
- Easier to test (pure functions, no Jinja2 environment)
- No template parsing overhead

**Cons:**
- High implementation cost (24 templates × 100+ lines = 2400 LOC)
- Less readable than declarative templates (imperative string building)
- Harder for non-developers to contribute (Python knowledge required)
- No visual preview of generated output

**Decision:** Rejected - Implementation cost too high, reduces contribution accessibility.

---

### Alternative C: 3-Tier Hierarchy (Not 5-Tier)

**Description:** Flatten to Universal → Language → Concrete (skip Format and Specialization tiers).

**Pros:**
- Simpler tier structure (fewer extends levels)
- Faster introspection (shorter chain)

**Cons:**
- Mixes format and language concerns (Python CODE vs Python YAML in same tier)
- Cannot add TypeScript without duplicating format structure (back to 13+ templates)
- Loses specialization patterns (IWorkerLifecycle, DTO validation shared across languages)

**Decision:** Rejected - Loses extensibility benefits, regresses to original problem.

---

### Alternative D: Template Composition (Not Inheritance)

**Description:** Use `{% include %}` instead of `{% extends %}` for multi-tier.

**Pros:**
- More flexible (can include multiple partial templates)
- Order-independent (includes don't require parent-child relationship)

**Cons:**
- Diamond problem (multiple includes of same partial → duplicate code)
- No block override mechanism (cannot customize parent behavior)
- Harder to introspect (includes are dynamic, extends are static)

**Decision:** Rejected - Inheritance cleaner for single-chain tier structure.

---

## 6. Open Questions

### OQ-D1: IWorkerLifecycle Pattern Validation

**Question:** Should Tier 3 `base_python_component.jinja2` include IWorkerLifecycle blocks?

**Status:** ⚠️ BLOCKER - Requires audit (Planning Task 2.2, 6h effort)

**Impact:** Affects Tier 3 component template design (Phase 3, Task 3.1)

**Audit Checklist:**
- [ ] Count workers implementing IWorkerLifecycle (X out of Y)
- [ ] Locate IWorkerLifecycle interface definition (if exists)
- [ ] Document two-phase init rationale (or reasons to reject)
- [ ] Check if current `worker.py.jinja2` generates lifecycle code
- [ ] Verify cross-language applicability (TypeScript workers?)

**Decision Deadline:** End of Week 1 (before Phase 3 starts)

---

### OQ-D2: Agent Hint Format

**Question:** How should document templates embed agent guidance?

**Example (from Research OQ-P2):**
```markdown
## Problem Statement
<!-- AGENT_HINT: Analyze issue deeply. Ask: What broken? Why matters? Who impacted? -->

{%- block problem_statement -%}
{{ problem_description | default("TODO") }}
{%- endblock -%}
```

**Status:** 🟡 P2 Priority - Not blocking MVP

**Impact:** Affects Tier 3 `base_markdown_knowledge.jinja2` (Planning Task 3.4)

**Prototype Plan:**
- [ ] Define hint syntax (comment format, keywords)
- [ ] Add hints to `research.md.jinja2` template
- [ ] Validate with agent run (subjective quality improvement test)

**Decision:** Can defer to Phase 3B (post-MVP enhancement)

---

### OQ-D3: Performance Optimization Strategy

**Question:** If introspection >100ms, which optimization to prioritize?

**Options:**
1. **Caching:** Store introspection results in memory (invalidate on template change)
2. **AST Optimization:** Reduce `jinja2.nodes.Extends` traversal overhead
3. **Tier Flattening:** Merge Tier 1+2 for common combinations (e.g., `tier1_2_python_code.jinja2`)

**Status:** 🟢 Low Risk - Planning estimates 10% probability (Risk #5)

**Benchmark Plan:**
- [ ] Measure baseline: 5-tier chain introspection time (Phase 2, Task 2.1)
- [ ] If <100ms: No action needed
- [ ] If 100-500ms: Implement caching
- [ ] If >500ms: Escalate, consider tier flattening

**Decision Deadline:** End of Phase 2 (after Task 2.1 complete)

---

## 7. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-20 | Use Jinja2 `{% extends %}` for tier hierarchy | Cleaner than macros, no diamond problem (vs {% include %}) |
| 2026-01-21 | 5-tier structure (not 3-tier) | Orthogonal dimensions prevent language duplication |
| 2026-01-22 | Functional `introspect_template()` API (not class-based) | Matches existing codebase (template_introspector.py module) |
| 2026-01-22 | 8-char SHA256 hash (not full 64-char) | Balance collision safety (2^32 per artifact type) vs readability |
| 2026-01-22 | YAML registry format (not JSON) | Human-readable, supports comments, standard in .st3/ |
| 2026-01-23 | AC9 validation HARD requirement | Cannot ship #72 without Issue #52 completion (planning consensus) |
| 2026-01-23 | Feature flag for migration | Safe rollback mechanism (Risk #4 mitigation, 60% probability) |

---

## Related Documentation

- [Agent Cooperation Protocol](../../agent.md) - `scaffold_artifact()` tool usage
- [Planning Document](planning.md) - 24 tasks, 183h effort, risk mitigation
- [Research Summary](research_summary.md) - Final architectural decisions
- [MVP Validation](mvp/) - 5-tier template proof-of-concept
- [Issue #52 Alignment](research_summary.md#issue-52-alignment) - TEMPLATE_METADATA format
- [Coding Standards](../../coding_standards/) - Python quality gates, file headers
- [Template Hierarchy Reference](../../reference/templates/template_hierarchy.md) - Base template standards

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-23 | AI Agent | Initial design - 5-tier Jinja2 architecture, introspection API, registry format |
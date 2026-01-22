# Template Library Management - Base Template Architecture Research

<!-- SCAFFOLD: template=research version=1.0 created=2026-01-22T17:00:00Z path=docs/development/issue72/research.md -->

**Issue:** #72  
**Epic:** Template Library Management  
**Status:** Research Phase  
**Date:** 2026-01-22  
**Architectural Principles:** Config Over Code, SSOT, DRY, SRP

---

## Executive Summary

**Problem:** Current base template architecture violates DRY by requiring SCAFFOLD metadata duplication across multiple base templates, limiting extensibility to new languages and artifact types.

**Research Scope:**
1. Analyze current template architecture limitations
2. Study existing template systems (Cookiecutter, Copier, Yeoman)
3. Define universal artifact taxonomy via dimensional analysis
4. Identify architectural patterns for DRY + extensibility
5. Explore ephemeral artifact types and their classification

**Key Findings:**
- Current architecture: tactical (per-language) not strategic (universal)
- Existing tools: limited inheritance, file-based templating, no SSOT validation
- Artifact dimensions: 4 orthogonal axes (lifecycle, format, language, specialization)
- Ephemeral types (commits, PRs) are documents with temporary storage (no special handling needed)
- Open question: Are code/document the ONLY Tier 1 categories? Research explores alternatives.

**Recommendation:** Multi-tier base template hierarchy using orthogonal dimensions enables DRY + language-agnostic extensibility.

---

## Problem Analysis

### Current State: Issue #120 Phase 0 Incomplete

**Deliverable:** "All scaffolded files have `template`, `version` in YAML frontmatter"

**Reality:**
```powershell
Get-ChildItem mcp_server\templates -Recurse -Filter *.jinja2 | 
  Select-String "SCAFFOLD:" | Measure-Object

Count: 2/24 (8%)
```

**Impact:**
- query_file_schema() fails for 91% of files (Issue #121 blocked)
- Templates not functioning as SSOT
- Validation infrastructure incomplete (Issue #52 gap)

### Current Template Architecture

**Base templates (3):**
```
base/
├── base_component.py.jinja2    # Python components (9 children)
├── base_document.md.jinja2     # Markdown docs (2 children)
└── base_test.py.jinja2         # Python tests (0 children - orphaned)
```

**Template inventory (24 total):**
- Components: 13 templates (dto, worker, adapter, tool, service_*, etc.)
- Documents: 6 templates (research, planning, design, architecture, etc.)
- Tests: 3 templates (unit_test, integration_test, dto_test)
- Ephemeral: 2 templates (commit-message.txt, tracking.md)

### DRY Violation Analysis

**Current approach:** SCAFFOLD metadata duplicated in each base template

```jinja
{# base_component.py.jinja2 #}
# SCAFFOLD: template={{ template_id }} version={{ version }} ...

{# base_document.md.jinja2 #}
<!-- SCAFFOLD: template={{ template_id }} version={{ version }} ... -->

{# base_test.py.jinja2 #}
# SCAFFOLD: template={{ template_id }} version={{ version }} ...
```

**Problem:** Adding TypeScript/C#/Go requires duplicating SCAFFOLD metadata N times (N languages = N duplications).

**Question:** How can we define SCAFFOLD metadata ONCE and inherit across all templates?

### Extensibility Limitations

**Current base templates mix concerns:**
- `base_component.py` = Python syntax + code structure + component patterns + SCAFFOLD metadata
- No separation between language-agnostic concepts and language-specific syntax

**Problem:** Cannot reuse base logic across languages.

**Example:** Worker concept exists in Python, TypeScript, C#, Go → must duplicate worker patterns per language.

**Question:** What are the orthogonal dimensions that enable cross-language reuse?

### Architectural Principles (from docs/coding_standards/)

**Config Over Code:**
- Templates as SSOT (not hardcoded RULES dict)
- Configuration drives behavior

**DRY (Don't Repeat Yourself):**
- Single source of truth
- No duplication

**SRP (Single Responsibility Principle):**
- Each template has ONE concern
- Separation of concerns

**Contract-Driven Development:**
- Types and interfaces define contracts
- SCAFFOLD metadata = typed contract

**Issue #72 Research Question:** How do existing template systems achieve these principles? What can we learn?

---

## Existing Template Systems Analysis

### Research Methodology

Study 3 major templating systems to understand:
1. How they handle template inheritance
2. How they manage metadata and configuration
3. Whether they support multi-language extensibility
4. What patterns enable DRY and reusability

### Cookiecutter (Python)

**Architecture:**
- File-based templating using Jinja2
- Single cookiecutter.json for project-wide variables
- No template inheritance (each template is standalone)
- Directory structure is the template

**Example:**
```
{{cookiecutter.project_name}}/
├── setup.py
├── {{cookiecutter.package_name}}/
│   ├── __init__.py
│   └── {{cookiecutter.module_name}}.py
└── tests/
```

**Strengths:**
- Simple mental model (directory = template)
- Jinja2 integration (familiar syntax)
- Hooks for pre/post generation logic

**Weaknesses:**
- No template inheritance (duplication across similar templates)
- No built-in validation
- No SSOT for template metadata
- File-based only (not artifact-type aware)

**Learnings:**
- ✅ Jinja2 is powerful for templating
- ❌ No inheritance = duplication problem
- ❌ No validation integration

### Copier (Python)

**Architecture:**
- Similar to Cookiecutter but with template updates
- copier.yml for configuration
- Supports Jinja2 extensions
- Template update workflow (not just initial generation)

**Example copier.yml:**
```yaml
_templates_suffix: .jinja
_subdirectory: template

project_name:
  type: str
  help: What is your project name?

license:
  type: str
  default: MIT
  choices:
    - MIT
    - Apache-2.0
```

**Strengths:**
- Template updates (not just one-time generation)
- Type-safe configuration (type: str, choices)
- Jinja2 extensions support
- Migration support (template versioning)

**Weaknesses:**
- Still no template inheritance
- No SSOT validation
- File-based approach
- No language-agnostic abstractions

**Learnings:**
- ✅ Template versioning is important
- ✅ Type-safe configuration prevents errors
- ✅ Update workflow (not just create)
- ❌ Still lacks inheritance for DRY

### Yeoman (JavaScript/TypeScript)

**Architecture:**
- Generator-based (code over templates)
- Composable generators (can invoke sub-generators)
- Programmatic file generation
- EJS templating (similar to Jinja2)

**Example generator structure:**
```
generators/
├── app/
│   ├── index.js           # Main generator
│   └── templates/         # EJS templates
├── component/             # Sub-generator
│   ├── index.js
│   └── templates/
└── router/                # Sub-generator
```

**Strengths:**
- Composable generators (sub-generators = reusability)
- Programmatic control (conditional logic in code)
- Extensible (generator inheritance via prototype)
- Rich ecosystem (many community generators)

**Weaknesses:**
- Code-based (not config-driven) → violates Config Over Code
- Templates scattered across generators
- No centralized metadata/validation
- JavaScript-specific

**Learnings:**
- ✅ Composability enables reusability
- ✅ Sub-generators = inheritance pattern
- ❌ Code-based violates Config Over Code principle
- ❌ No SSOT for templates

### Comparison Matrix

| Feature | Cookiecutter | Copier | Yeoman | SimpleTrader (Current) |
|---------|-------------|--------|--------|----------------------|
| **Templating Engine** | Jinja2 | Jinja2 | EJS | Jinja2 |
| **Inheritance** | ❌ None | ❌ None | ⚠️ Code-based | ⚠️ Limited (3 bases) |
| **Config-Driven** | ⚠️ Partial | ✅ Yes | ❌ Code-based | ✅ Yes (artifacts.yaml) |
| **Validation** | ❌ None | ❌ None | ❌ None | ⚠️ Partial (TEMPLATE_METADATA) |
| **Versioning** | ❌ None | ✅ Yes | ❌ None | ⚠️ Partial (version field) |
| **Multi-language** | ⚠️ Manual | ⚠️ Manual | ⚠️ Manual | ❌ Python-only |
| **DRY** | ❌ Duplication | ❌ Duplication | ⚠️ Via code | ❌ Metadata duplicated |
| **SSOT** | ❌ None | ❌ None | ❌ None | ⚠️ Templates (incomplete) |

### Key Insights

**No existing system achieves all our goals:**
1. Template inheritance (DRY)
2. Config-driven (Config Over Code)
3. SSOT for validation
4. Multi-language extensibility
5. Typed metadata contracts

**Patterns to adopt:**
- Yeoman's composability (sub-generators)
- Copier's type-safe configuration
- Copier's template versioning
- Jinja2 inheritance (all use it, we need to leverage better)

**Patterns to avoid:**
- Cookiecutter's flat templates (no reuse)
- Yeoman's code-based approach (violates Config Over Code)
- No validation integration (all 3 tools)

---

## Deep Research: Universal Artifact Taxonomy

### Research Question

**What are the FUNDAMENTAL dimensions that classify artifacts in software development?**

**Context:**
- Current: 17 artifact types (Python-only)
- Future: 100+ artifact types (multi-language, multi-format)
- Scope: MCP server as compiled extension (C#, TypeScript, Java, Go, Rust, etc.)

### Dimensional Analysis Methodology

**Approach:** Identify orthogonal axes that classify artifacts independently.

**Criteria for valid dimension:**
1. **Orthogonal:** Independent from other dimensions
2. **Universal:** Applies to ALL artifact types
3. **Exhaustive:** Every artifact fits in one category per dimension
4. **Extensible:** New categories can be added without restructuring

### Dimension 1: Artifact Lifecycle (UNIVERSAL)

**Definition:** Metadata about artifact creation, versioning, and state.

**Properties (all artifacts):**
- `template_id`: Which template created this artifact
- `version`: Template semantic version used
- `created`: Timestamp when scaffolded
- `path`: File system location
- `state`: Lifecycle state (CREATED, MODIFIED, DEPRECATED)

**Universality:** Python worker, TypeScript service, Markdown doc → ALL have lifecycle metadata.

**Key Insight:** This is currently MISSING from our base templates! Each base duplicates lifecycle logic instead of inheriting from universal base.

### Dimension 2: Format Category (CODE vs DOCUMENT vs CONFIG vs ?)

**Definition:** High-level artifact purpose and structure.

**Identified categories:**

**CODE:**
- Executable/compilable source code
- Has imports/dependencies
- Type-checked or linted
- Test coverage expected
- Examples: Python, C#, TypeScript, Go, Rust

**DOCUMENT:**
- Human-readable knowledge artifacts
- Structured sections (headings)
- Links and cross-references
- Version-controlled but not executable
- Examples: Markdown, reStructuredText, AsciiDoc

**CONFIG:**
- Machine-readable configuration
- Schema-validated
- No imports (declarative)
- Examples: YAML, JSON, TOML, XML

**EPHEMERAL:** (User question - classification needed!)
- Temporary/transient artifacts
- Used in external systems (Git, GitHub API)
- Examples: commit messages, PR descriptions, issue bodies
- **Research question:** Are these DOCUMENTS or separate category?

**DATA:**
- Structured data files
- Schema-defined
- Examples: CSV, SQL, Protobuf
- **Research question:** Do we scaffold data files?

**BINARY/ASSETS:**
- Non-text artifacts
- Examples: images, fonts, compiled binaries
- **Research question:** Out of scope for text templating?

### Dimension 2 Deep Dive: Ephemeral Artifacts

**User question:** "Moeten we hier nog apart rekening mee houden of zeggen we, dit zijn in feite docs?"

**Analysis:**

**Ephemeral examples in current system:**
- `commit-message.txt` → Git commit body
- PR descriptions → GitHub API
- Issue bodies → GitHub API
- Labels, milestones → GitHub API

**Properties:**
- Structure: Like documents (sections, formatting)
- Storage: Temporary (not persisted in project files)
- Lifecycle: Used once, then consumed by external system
- Validation: Same as documents (required sections, format)

**Hypothesis:** Ephemeral artifacts are **documents with temporary storage**.

**Template perspective:**
```jinja
{# commit-message.txt.jinja2 #}
<!-- SCAFFOLD: template=commit-message version=1.0 ... -->

# {{ type }}: {{ summary }}

{{ description }}

{% if breaking_changes %}
BREAKING CHANGE: {{ breaking_changes }}
{% endif %}
```

**After scaffolding:**
- Scaffold creates file in `.st3/tmp/commit-message.txt`
- Tool reads file and passes to `git commit -F`
- File deleted after use

**Conclusion:** From template POV, ephemeral = document. Storage/lifecycle is tool responsibility, NOT template responsibility.

**Recommendation:** No separate Tier 1 category for ephemeral. Classify as DOCUMENT subtype.

### Dimension 2 Revisited: Are CODE/DOCUMENT Sufficient?

**Research question:** "Blijft mijn vraag zijn code en documenten de enige twee domein 2 (tier 1) categorieën?"

**Analysis:**

**Current inventory:**
- CODE: 13 templates (Python .py files)
- DOCUMENT: 9 templates (Markdown .md, .txt)
- CONFIG: 0 templates (none yet - but .st3/*.yaml are scaffolded externally)
- DATA: 0 templates (none yet)

**Future scenarios:**

**CONFIG scaffolding:**
- User: "Add new workflow to workflows.yaml"
- Scaffold: Insert YAML block with validation
- Template: `config/workflow.yaml.jinja2`
- Question: Is CONFIG different enough from DOCUMENT to be Tier 1?

**Differences:**
| Property | DOCUMENT | CONFIG |
|----------|----------|--------|
| Purpose | Human-readable knowledge | Machine-readable settings |
| Sections | Freeform headings | Fixed schema keys |
| Validation | Structural (headers exist) | Schema (types, required fields) |
| Editing | Prose/markdown | Key-value pairs |

**Hypothesis:** CONFIG is distinct enough to warrant Tier 1 category.

**DATA scaffolding:**
- Example: "Scaffold database migration SQL"
- Example: "Generate Protobuf schema"
- Question: Do we scaffold data definitions?

**Analysis:** Data definitions (SQL schemas, Protobuf) are CODE (they're DSLs). Raw data (CSV) is not scaffolded.

**Conclusion:** DATA is NOT a Tier 1 category (data *definitions* are CODE).

**Proposed Tier 1 Categories:**
1. CODE - Executable/compilable source
2. DOCUMENT - Human-readable knowledge
3. CONFIG - Machine-readable configuration

**Open question:** Are there other Tier 1 categories we're missing?

### Dimension 3: Language/Syntax

**Definition:** Concrete syntax and tooling for a format category.

**CODE languages:**
- Python (# comments, """ docstrings, from/import, type hints)
- TypeScript (// comments, /** */ docstrings, import/from, : Type)
- C# (// comments, /// docstrings, using, Type name)
- Go (// comments, /* */ docstrings, import, var name Type)
- Java (// comments, /** */ docstrings, import, Type name)
- Rust (// comments, /// docstrings, use, let name: Type)

**DOCUMENT languages:**
- Markdown (<!-- comments, ## sections, [links], ``` code blocks)
- reStructuredText (.rst - .. comments, === sections, `links`_)
- AsciiDoc (.adoc - // comments, == sections, link:url[])

**CONFIG languages:**
- YAML (# comments, key: value, indentation-based)
- JSON (no comments, {"key": "value"}, strict syntax)
- TOML (# comments, key = value, sections)
- XML (<!-- comments, <key>value</key>, tags)

**Key Insight:** Language defines syntax (comments, imports, type hints) but NOT structure (component patterns, document sections).

### Dimension 4: Artifact Specialization

**Definition:** Domain-specific patterns within a language.

**CODE specializations:**
- **Component:** Business logic (Worker, Service, Adapter)
  - Has dependencies
  - Lifecycle methods
  - Domain contracts
  
- **Data Model:** Data structures (DTO, Schema, Interface)
  - Immutable or validated
  - No business logic
  - Type definitions
  
- **Tool/Integration:** External interfaces (MCP Tool, Resource)
  - API contracts
  - Protocol adapters
  
- **Test:** Validation logic (Unit, Integration, E2E)
  - Fixtures/mocks
  - Assertions
  - Coverage tracking

**DOCUMENT specializations:**
- **Knowledge:** Information artifacts (Research, Planning, Design)
  - Structured analysis
  - Decision records
  - Cross-references
  
- **Architecture:** System design (Architecture, Reference)
  - Diagrams
  - Principles
  - Patterns
  
- **Tracking:** Progress artifacts (Tracking, Issue templates)
  - Status updates
  - Checklists

**CONFIG specializations:**
- **Policy:** Rules and constraints (workflows.yaml, quality.yaml)
- **Registry:** Artifact definitions (artifacts.yaml, labels.yaml)
- **Structure:** Project layout (project_structure.yaml)

### Dimensional Classification Matrix

| Artifact | Lifecycle | Format | Language | Specialization |
|----------|-----------|---------|----------|----------------|
| Worker.py | ✅ | CODE | Python | Component |
| DTO.py | ✅ | CODE | Python | Data Model |
| Research.md | ✅ | DOCUMENT | Markdown | Knowledge |
| Planning.md | ✅ | DOCUMENT | Markdown | Knowledge |
| Unit Test.py | ✅ | CODE | Python | Test |
| Commit Message.txt | ✅ | DOCUMENT | Markdown | Ephemeral (Knowledge subtype) |
| TypeScript Worker | ✅ | CODE | TypeScript | Component |
| C# Service | ✅ | CODE | C# | Component |
| Go Adapter | ✅ | CODE | Go | Component |
| workflows.yaml | ✅ | CONFIG | YAML | Policy |

**Key Findings:**
1. **All artifacts share Dimension 1 (Lifecycle)** → Universal base needed!
2. **Dimension 2 (Format):** CODE, DOCUMENT, CONFIG are orthogonal categories
3. **Dimension 3 (Language):** Syntax-specific, independent of specialization
4. **Dimension 4 (Specialization):** Domain patterns, independent of language

**Orthogonality Test:**
- Can you have a Component in Python? Yes → Worker.py
- Can you have a Component in TypeScript? Yes → Worker.ts
- Can you have a Test in Python? Yes → test_worker.py
- Can you have Knowledge in Markdown? Yes → research.md
- Can you have Knowledge in reStructuredText? Yes → research.rst

**Conclusion:** 4 dimensions are orthogonal and exhaustive.

---

## Architectural Pattern Research

### Research Question

**How can we structure base templates to achieve DRY across 4 orthogonal dimensions?**

### Pattern 1: Flat Inheritance (Current Approach)

**Structure:**
```
base_component.py → worker.py, adapter.py, ...
base_document.md → research.md, design.md, ...
base_test.py → (no children)
```

**Analysis:**
- Each base mixes all 4 dimensions
- Adding language requires duplicating ALL bases
- DRY violation: SCAFFOLD metadata repeated 3+ times

**Verdict:** Does NOT scale to multi-language.

### Pattern 2: Multi-Tier Hierarchy (Orthogonal Dimensions)

**Hypothesis:** Separate each dimension into its own tier.

**Structure (conceptual):**
```
Tier 0 (Lifecycle - Universal)
└── base_artifact
    ├── Tier 1 (Format)
    │   ├── base_code
    │   ├── base_document
    │   └── base_config
    │       ├── Tier 2 (Language)
    │       │   ├── base_python
    │       │   ├── base_typescript
    │       │   ├── base_markdown
    │       │   └── base_yaml
    │       │       └── Tier 3 (Specialization)
    │       │           ├── base_python_component
    │       │           ├── base_python_test
    │       │           └── base_markdown_knowledge
```

**DRY Achievement:**
- SCAFFOLD metadata: Defined ONCE in `base_artifact` (Tier 0)
- Code structure: Defined ONCE in `base_code` (Tier 1)
- Python syntax: Defined ONCE in `base_python` (Tier 2)
- Component patterns: Defined ONCE in `base_python_component` (Tier 3)

**Extensibility:**
- Add TypeScript: Create `base_typescript` (Tier 2) → reuses Tier 0+1
- Add C#: Create `base_csharp` (Tier 2) → reuses Tier 0+1
- Add reStructuredText: Create `base_rst` (Tier 2) → reuses Tier 0+1

**Open Question:** Is 4-tier hierarchy too complex? What's the cognitive load?

### Pattern 3: Mixin Composition (Alternative)

**Hypothesis:** Instead of linear inheritance, use composition (mixins).

**Structure (conceptual):**
```python
# worker.py template includes:
{% include "mixins/scaffold_metadata.jinja2" %}
{% include "mixins/python_header.jinja2" %}
{% include "mixins/component_imports.jinja2" %}

class Worker:
    # Worker-specific content
```

**Pros:**
- Flexible composition (pick mixins as needed)
- No deep inheritance chains

**Cons:**
- Jinja2 `{% include %}` doesn't support inheritance (no `super()`)
- Harder to override mixin behavior
- Less DRY (each template must include all mixins)

**Verdict:** Mixins don't solve DRY problem (each template still includes N mixins).

### Pattern Comparison

| Pattern | DRY | Extensibility | Complexity | Jinja2 Support |
|---------|-----|---------------|------------|----------------|
| Flat Inheritance | ❌ Low | ❌ Low | ✅ Simple | ✅ Native |
| Multi-Tier | ✅ High | ✅ High | ⚠️ Medium | ✅ Native |
| Mixin Composition | ⚠️ Medium | ✅ High | ⚠️ Medium | ⚠️ Limited |

**Recommendation (Hypothesis):** Multi-tier hierarchy best balances DRY + extensibility.

**Open Question:** How many tiers is optimal? 4? 3? 5?

---

## Post-Generation Editing & Validation Research

### Research Question

**How does multi-tier base template architecture affect post-generation workflows?**

**Context:** Issue #121 (Content-Aware Edit Tool) requires:
1. **Introspection:** Agent queries file schema to understand structure
2. **Validation:** After edits, validate artifact against original template

**Key Insight:** Generation uses Jinja2 AST (template), editing uses Artifact AST (generated file). Multi-tier inheritance affects both.

### Use Case: Agent Edits Scaffolded File

**Scenario:**
```python
# Day 1: Agent scaffolds worker
scaffold_artifact("worker", name="Signal", input_dto="MarketData", output_dto="SignalDTO")
# Creates: backend/workers/signal_worker.py (from 4-tier inheritance chain)

# Day 7: Agent needs to edit worker (add new method)
# Agent receives: path="backend/workers/signal_worker.py" (no context!)
# Agent must: 1. Discover template, 2. Understand structure, 3. Edit safely
```

**Questions:**
1. How does agent discover file came from 4-tier template chain?
2. What schema does agent receive? (Tier 0 only? All 4 tiers merged?)
3. How does validation work? (Against which tier's rules?)

### Introspection Analysis: Template Schema Presentation

**Hypothetical 4-tier worker.py inheritance:**
```
base_artifact (Tier 0)
└── base_code (Tier 1)
    └── base_python (Tier 2)
        └── base_python_component (Tier 3)
            └── worker.py (Tier 4 - concrete template)
```

**SCAFFOLD metadata in generated file:**
```python
# SCAFFOLD: template=worker version=2.0 created=2026-01-22T10:00:00Z path=backend/workers/signal_worker.py
```

**Introspection workflow (Issue #121):**
```python
# Agent calls:
schema = query_file_schema("backend/workers/signal_worker.py")

# System must:
# 1. Parse SCAFFOLD metadata → template_id="worker"
# 2. Load template: worker.py.jinja2
# 3. Resolve inheritance chain: worker → base_python_component → base_python → base_code → base_artifact
# 4. Build merged schema from ALL tiers
```

**Research Question 1:** What does `schema` contain?

**Option A: Flattened Schema (All Tiers Merged)**
```python
schema = {
    "template_id": "worker",  # From concrete template
    "template_chain": ["base_artifact", "base_code", "base_python", "base_python_component", "worker"],
    "lifecycle": {...},       # From Tier 0
    "format": "code",         # From Tier 1
    "language": "python",     # From Tier 2
    "specialization": "component",  # From Tier 3
    "structure": {
        # Merged from all tiers:
        "sections": {
            "imports": {...},          # From base_python
            "class_definition": {...}, # From base_python_component
            "process_method": {...}    # From worker.py
        }
    },
    "edit_capabilities": ["ScaffoldEdit", "TextEdit"]
}
```

**Pros:**
- Agent sees complete picture (all tiers)
- No need to understand inheritance hierarchy
- Single schema for validation

**Cons:**
- Complex schema (4 tiers merged)
- Hard to identify which tier defines what
- May expose too much detail

**Option B: Tier-Specific Schemas (Layered)**
```python
schema = {
    "template_id": "worker",
    "tiers": {
        "tier_0_lifecycle": {
            "metadata": ["template_id", "version", "created", "path"]
        },
        "tier_1_format": {
            "type": "code",
            "sections": ["imports", "content"]
        },
        "tier_2_language": {
            "language": "python",
            "syntax": {"comment": "#", "docstring": '"""'}
        },
        "tier_3_specialization": {
            "type": "component",
            "patterns": ["dependencies", "layer_annotations"]
        },
        "tier_4_concrete": {
            "type": "worker",
            "required_methods": ["process"],
            "base_class": "BaseWorker"
        }
    },
    "edit_capabilities": ["ScaffoldEdit", "TextEdit"]
}
```

**Pros:**
- Clear separation (agent can query specific tier)
- Easier debugging (know which tier defines what)
- Extensible (add tiers without breaking schema)

**Cons:**
- More complex for agent (must understand tiers)
- Validation must check all tiers
- Higher cognitive load

**Research Hypothesis:** Option A (flattened) is better for agents (simpler mental model), Option B (layered) is better for debugging/maintenance.

**Open Question:** Which schema presentation enables best editing workflows?

### Validation Analysis: Artifact AST vs Jinja2 AST

**Core Problem:** Generated file != template anymore after edits.

**Scenario:**
```python
# Original (generated from template):
class SignalWorker(BaseWorker[MarketData, SignalDTO]):
    """Signal detection worker."""
    
    async def process(self, input_data: MarketData) -> SignalDTO:
        # Process market data
        pass

# After agent edit (added new method):
class SignalWorker(BaseWorker[MarketData, SignalDTO]):
    """Signal detection worker."""
    
    async def process(self, input_data: MarketData) -> SignalDTO:
        # Process market data
        pass
    
    async def validate_signal(self, signal: SignalDTO) -> bool:  # NEW!
        """Validate signal quality."""
        return True
```

**Validation challenge:** File is no longer pure template output. How do we validate?

**Jinja2 AST (Template):**
- Defined in worker.py.jinja2
- Has blocks: {% block process_method %}
- Static structure (known at template design time)

**Artifact AST (Generated File):**
- Parsed from actual Python file
- Has AST nodes: ClassDef, FunctionDef, etc.
- Dynamic structure (agent added `validate_signal` method)

**Validation Approaches:**

**Approach 1: Template-Based Validation (Strict)**
```python
# Validate file matches template structure exactly
template_ast = parse_jinja2("worker.py.jinja2")
artifact_ast = parse_python("signal_worker.py")

# Check: Does artifact have all required blocks from template?
required_blocks = ["process_method"]
for block in required_blocks:
    if block not in artifact_ast:
        error(f"Missing required block: {block}")

# Problem: New method `validate_signal` not in template → FAIL!
```

**Pros:**
- Enforces template contract strictly
- Prevents drift from template structure

**Cons:**
- **BLOCKS LEGITIMATE EDITS!**
- Agent can't add new methods/fields
- Files become frozen (can't evolve)

**Approach 2: Rule-Based Validation (Flexible)**
```python
# Validate file matches RULES from TEMPLATE_METADATA, not structure
rules = get_template_metadata("worker").validates

# Example rules from worker.py.jinja2:
# - Must have BaseWorker base class
# - Must have process() method
# - Must have type hints

# Check rules against artifact AST:
check_base_class(artifact_ast, "BaseWorker")  # PASS
check_method_exists(artifact_ast, "process")  # PASS
check_method_exists(artifact_ast, "validate_signal")  # Not required, so OK!
```

**Pros:**
- Allows agent to add new methods/fields
- Validates contract, not structure
- Files can evolve beyond template

**Cons:**
- Looser validation (may miss issues)
- Rules must be carefully designed
- Need TEMPLATE_METADATA in all tiers

**Research Hypothesis:** Approach 2 (rule-based) is correct. Templates define CONTRACTS (what must exist), not STRUCTURE (what can exist).

**Multi-Tier Validation:**

**Question:** Which tier's rules apply?

**Scenario:** Agent edits worker.py

**Tier 0 (Lifecycle) rules:**
- SCAFFOLD metadata must be present ✅
- Version must be valid semver ✅

**Tier 1 (Format=CODE) rules:**
- Must have imports section ✅
- Must be valid Python syntax ✅

**Tier 2 (Language=Python) rules:**
- Must have docstrings ✅
- Must have type hints ✅

**Tier 3 (Specialization=Component) rules:**
- Must have layer annotation ✅
- Must list dependencies ✅

**Tier 4 (Concrete=Worker) rules:**
- Must inherit BaseWorker ✅
- Must have process() method ✅

**Validation workflow:**
```python
# Validate against ALL tiers (bottom-up):
validate_tier_0(artifact)  # Lifecycle rules
validate_tier_1(artifact)  # Format rules
validate_tier_2(artifact)  # Language rules
validate_tier_3(artifact)  # Specialization rules
validate_tier_4(artifact)  # Concrete template rules

# If all pass → artifact is valid!
```

**Key Insight:** Multi-tier validation = layered contracts. Each tier adds constraints, none remove them.

**Open Question:** How does agent know which tier a validation error came from?

### Introspection Implementation Research

**Question:** How does TemplateIntrospector handle 4-tier inheritance?

**Current (Issue #120):**
```python
class TemplateIntrospector:
    def get_schema(self, template_id: str) -> dict:
        # Load template
        template = env.get_template(f"components/{template_id}.py.jinja2")
        
        # Parse Jinja2 AST
        ast = env.parse(template.source)
        
        # Extract blocks
        blocks = extract_blocks(ast)
        
        return {"blocks": blocks, ...}
```

**Problem:** Single template load, no inheritance resolution!

**Multi-Tier (Hypothesis):**
```python
class TemplateIntrospector:
    def get_schema(self, template_id: str) -> dict:
        # 1. Load concrete template
        template = env.get_template(f"components/{template_id}.py.jinja2")
        
        # 2. Resolve inheritance chain
        chain = self._resolve_inheritance(template)
        # Returns: [base_artifact, base_code, base_python, base_python_component, worker]
        
        # 3. Load all templates in chain
        templates = [env.get_template(t) for t in chain]
        
        # 4. Merge blocks from all tiers
        merged_blocks = {}
        for t in templates:
            blocks = extract_blocks(env.parse(t.source))
            merged_blocks.update(blocks)  # Child overrides parent
        
        # 5. Extract metadata from all tiers
        merged_metadata = {}
        for t in templates:
            metadata = extract_metadata(t.source)
            merged_metadata = deep_merge(merged_metadata, metadata)
        
        return {
            "template_id": template_id,
            "inheritance_chain": chain,
            "blocks": merged_blocks,
            "metadata": merged_metadata
        }
```

**Key Changes:**
- Must resolve `{% extends %}` directives recursively
- Must merge blocks from all tiers (child overrides parent)
- Must merge TEMPLATE_METADATA from all tiers

**Performance Concern:** Loading 5 templates instead of 1. 

**Mitigation:** Cache inheritance chains (templates don't change at runtime).

### Edit Capability Discovery

**Question:** How does agent know if file supports ScaffoldEdit?

**Current (Issue #121 hypothesis):**
```python
schema = query_file_schema("signal_worker.py")

if schema["template_id"]:
    # File was scaffolded → supports ScaffoldEdit
    capabilities = ["ScaffoldEdit", "TextEdit"]
else:
    # File not scaffolded → TextEdit only
    capabilities = ["TextEdit"]
```

**Multi-Tier Context:**

**ScaffoldEdit requires:**
- SCAFFOLD metadata (Tier 0) ✅
- Template blocks identified (Tier 1-4) ✅
- Current artifact state parsed (AST) ✅

**ScaffoldEdit operations (hypothetical):**
```python
# Append to imports block (defined in Tier 2: base_python)
ScaffoldEdit.append_to_block("imports", "from decimal import Decimal")

# Append to process method (defined in Tier 4: worker.py)
ScaffoldEdit.append_to_method("process", "# Additional logic")

# Add new method (NOT in template - allowed?)
ScaffoldEdit.insert_method("validate_signal", "async def validate_signal(...):")
```

**Research Question:** Which blocks can agent edit?

**Option A: Template-defined blocks only**
- Agent can only edit blocks explicitly defined in template
- New blocks require template update
- Strict control

**Option B: Any block in artifact AST**
- Agent can edit any Python AST node (class, method, etc.)
- Template blocks are hints, not constraints
- Flexible editing

**Hypothesis:** Option B (flexible) aligns with rule-based validation approach.

### Key Findings

**Introspection:**
1. Multi-tier inheritance requires recursive template loading
2. Schema presentation: Flattened (simple for agents) vs Layered (clear for debugging)
3. Performance: Cache inheritance chains to avoid repeated template loading

**Validation:**
1. Rule-based validation (contracts) NOT structure-based (exact match)
2. Multi-tier validation: Each tier adds constraints
3. Agent can add new methods/fields as long as required contracts satisfied

**Edit Capabilities:**
1. ScaffoldEdit works on both template-defined AND agent-added blocks
2. Template blocks are semantic hints (imports, class, methods)
3. Validation after edit checks ALL tier rules

**Open Questions for Planning:**
- Which schema presentation? (Flattened vs Layered)
- How to communicate tier violations to agent?
- Should TemplateIntrospector cache be global or per-template?

## Migration Impact Analysis: Breaking Changes Assessment

### Critical Discovery

**User Insight:** "Alle scaffolding code breekt bij dit nieuwe 4 tier model"

**Research Question:** What breaks in current scaffolding implementation with multi-tier architecture?

### Current Scaffolding Architecture

**Key Components:**
1. **TemplateScaffolder** - Main scaffolding orchestrator
2. **JinjaRenderer** - Template loading and rendering
3. **TemplateIntrospector** - Schema extraction via AST parsing
4. **ScaffoldMetadataParser** - SCAFFOLD comment parsing (Issue #120)
5. **ArtifactRegistryConfig** - artifacts.yaml configuration

**Current Flow:**
```
scaffold_artifact(type="worker", name="Signal")
    ↓
TemplateScaffolder.scaffold()
    ↓
registry.get_artifact("worker")  # Returns: template_path="components/worker.py.jinja2"
    ↓
TemplateIntrospector.introspect(template_source)  # Extract schema from single template
    ↓
JinjaRenderer.render("components/worker.py.jinja2", **context)  # Render single template
    ↓
ScaffoldResult(content, file_name)
```

### Current Template Loading (NO Inheritance Resolution)

**JinjaRenderer.get_template():**
```python
def get_template(self, template_name: str) -> Any:
    """Load a template by name."""
    try:
        return self.env.get_template(template_name)  # ← FileSystemLoader
    except TemplateNotFound as e:
        raise ExecutionError(...)
```

**Key Behavior:**
- Loads SINGLE template file
- Jinja2 Environment with FileSystemLoader
- `{% extends %}` **IS** resolved by Jinja2 automatically during rendering
- BUT introspection **DOES NOT** follow extends chain!

### Current Introspection (BROKEN for Multi-Tier)

**TemplateIntrospector.introspect_template():**
```python
def introspect_template(env: jinja2.Environment, template_source: str) -> TemplateSchema:
    """Extract validation schema from Jinja2 template source."""
    # 1. Parse template into AST
    ast = env.parse(template_source)  # ← Single template AST only!
    
    # 2. Extract undeclared variables
    undeclared = meta.find_undeclared_variables(ast)  # ← Only from this template!
    
    # 3. Filter system fields
    agent_vars = undeclared - SYSTEM_FIELDS
    
    # 4. Classify as required/optional
    required, optional = _classify_variables(ast, agent_vars)
    
    return TemplateSchema(required=sorted(required), optional=sorted(optional))
```

**Problem:** Parses ONLY the concrete template (e.g., worker.py.jinja2), **IGNORES** base templates!

**Example:**
```jinja
{# base_artifact.jinja2 #}
{{ template_id }}  {# Variable used in Tier 0 #}
{{ version }}      {# Variable used in Tier 0 #}

{# base_code.jinja2 extends base_artifact #}
{{ description }}  {# Variable used in Tier 1 #}

{# worker.py.jinja2 extends base_code #}
{{ name }}         {# Variable used in Tier 4 #}
{{ input_dto }}    {# Variable used in Tier 4 #}
```

**Current introspection result (WRONG):**
```python
TemplateSchema(
    required=["name", "input_dto"],  # Only Tier 4 variables!
    optional=[]
)
```

**Correct result (multi-tier):**
```python
TemplateSchema(
    required=["template_id", "version", "description", "name", "input_dto"],  # ALL tiers!
    optional=[]
)
```

**Impact:** Validation FAILS because base template variables (template_id, version, description) are missing from schema!

### Breaking Change #1: Schema Extraction

**Current:** `introspect_template()` parses single template AST

**Multi-Tier Requirement:** Must parse ALL templates in inheritance chain

**Breaking Change:**
```python
# BEFORE (single template):
template_source = loader.get_source(env, "components/worker.py.jinja2")[0]
schema = introspect_template(env, template_source)

# AFTER (multi-tier - BREAKS):
template_source = loader.get_source(env, "components/worker.py.jinja2")[0]
schema = introspect_template(env, template_source)  # Missing base template variables!
```

**Fix Required:**
```python
# NEW: Resolve inheritance chain
def introspect_template_with_inheritance(
    env: jinja2.Environment,
    template_name: str
) -> TemplateSchema:
    """Extract schema from template + all bases."""
    # 1. Load template
    template = env.get_template(template_name)
    
    # 2. Resolve inheritance chain via Jinja2 internals
    chain = _resolve_inheritance_chain(env, template)
    # Returns: ["base/base_artifact.jinja2", "base/base_code.jinja2", ..., "components/worker.py.jinja2"]
    
    # 3. Load all template sources
    sources = [loader.get_source(env, t)[0] for t in chain]
    
    # 4. Parse all ASTs
    asts = [env.parse(source) for source in sources]
    
    # 5. Merge undeclared variables from all tiers
    all_vars = set()
    for ast in asts:
        all_vars.update(meta.find_undeclared_variables(ast))
    
    # 6. Filter system fields and classify
    agent_vars = all_vars - SYSTEM_FIELDS
    required, optional = _classify_variables_multi_tier(asts, agent_vars)
    
    return TemplateSchema(required=sorted(required), optional=sorted(optional))
```

**Migration Complexity:** **HIGH**
- Requires inheritance chain resolution
- Must parse N ASTs instead of 1
- Must merge variables across tiers
- Classification logic more complex (which tier defines optional?)

### Breaking Change #2: Variable Classification

**Current:** Classify variables from single AST

**Multi-Tier Problem:** Variable may be required in Tier 0 but optional in Tier 4!

**Example:**
```jinja
{# base_artifact.jinja2 (Tier 0) #}
{{ template_id }}  {# Required - no default, no conditional #}

{# worker.py.jinja2 (Tier 4) #}
{{ worker_type|default("context_worker") }}  {# Optional - has default filter #}
```

**Classification Challenge:** Must track which tier defines optional behavior.

**Current Algorithm:**
```python
def _classify_variables(ast: nodes.Template, variables: Set[str]) -> tuple[list, list]:
    """Classify from single AST."""
    optional_vars = set()
    
    # Detect |default(...) filter
    for node in ast.find_all(nodes.Filter):
        if node.name == "default":
            optional_vars.add(node.node.name)
    
    required_vars = variables - optional_vars
    return list(required_vars), list(optional_vars)
```

**Multi-Tier Algorithm (NEW):**
```python
def _classify_variables_multi_tier(
    asts: list[nodes.Template],
    variables: Set[str]
) -> tuple[list, list]:
    """Classify from multiple ASTs (inheritance chain)."""
    optional_vars = set()
    
    # Check ALL tiers for optional patterns
    for ast in asts:
        for node in ast.find_all(nodes.Filter):
            if node.name == "default":
                var_name = node.node.name
                if var_name in variables:
                    optional_vars.add(var_name)  # Optional in ANY tier → optional overall
    
    # If variable has default in ANY tier, it's optional
    # If variable required in ALL tiers, it's required
    required_vars = variables - optional_vars
    return list(required_vars), list(optional_vars)
```

**Migration Complexity:** **MEDIUM**
- Logic similar to current, but loop over multiple ASTs
- "Optional in any tier → optional overall" is safe heuristic

### Breaking Change #3: Rendering Context

**Current:** Pass context variables directly to template

**Multi-Tier Issue:** System fields (template_id, version) must be injected at Tier 0!

**Current Rendering:**
```python
# TemplateScaffolder._load_and_render_template()
rendered = self._renderer.render(
    "components/worker.py.jinja2",
    name="Signal",
    input_dto="MarketData",
    output_path="backend/workers/signal_worker.py"  # System field
)
```

**Multi-Tier Problem:** Who provides `template_id` and `version` for Tier 0?

**Solution:** ArtifactManager must inject system fields before rendering:
```python
# ArtifactManager (or TemplateScaffolder)
def scaffold_with_system_fields(artifact_type: str, **agent_context):
    # 1. Get artifact definition
    artifact = registry.get_artifact(artifact_type)
    
    # 2. Inject system fields (Tier 0 requirements)
    system_context = {
        "template_id": artifact_type,
        "version": artifact.version,
        "scaffold_created": datetime.now(timezone.utc).isoformat(),
        "output_path": compute_output_path(...),
        "format": "code" if artifact.type == "code" else "document"
    }
    
    # 3. Merge agent context + system context
    full_context = {**agent_context, **system_context}
    
    # 4. Render with complete context
    return renderer.render(artifact.template_path, **full_context)
```

**Migration Complexity:** **LOW**
- Already have system field injection logic (SYSTEM_FIELDS constant)
- Just need to ensure all Tier 0 fields provided

### Breaking Change #4: SCAFFOLD Metadata Generation

**Current:** Each template generates SCAFFOLD metadata independently

**Multi-Tier:** Tier 0 (base_artifact) generates SCAFFOLD metadata for ALL children

**Current (per-template):**
```jinja
{# components/worker.py.jinja2 #}
# SCAFFOLD: template=worker version=2.0 created={{ scaffold_created }} path={{ output_path }}
```

**Multi-Tier (Tier 0):**
```jinja
{# base/base_artifact.jinja2 #}
{% block scaffold_metadata -%}
{%- if format == 'code' -%}
# SCAFFOLD: template={{ template_id }} version={{ version }} created={{ scaffold_created }} path={{ output_path }}
{%- elif format == 'document' -%}
<!-- SCAFFOLD: template={{ template_id }} version={{ version }} created={{ scaffold_created }} path={{ output_path }} -->
{%- endif -%}
{% endblock %}
```

**Impact:** NO breaking change to scaffolding CODE! Jinja2 inheritance handles this automatically during rendering.

**BUT:** ScaffoldMetadataParser (Issue #120) still works because output format is identical!

**Migration Complexity:** **NONE** (Jinja2 inheritance handles it)

### Breaking Change #5: Template Path Resolution

**Current:** Direct template path from artifacts.yaml

**Multi-Tier:** May need to resolve inheritance chain for introspection

**artifacts.yaml:**
```yaml
worker:
  template_path: "components/worker.py.jinja2"  # Unchanged!
```

**Scaffolding:** No change needed (path still points to concrete template)

**Introspection:** Must resolve extends chain from concrete template

**Migration Complexity:** **LOW** (affects introspection only, not scaffolding)

### Inheritance Chain Resolution Research

**Question:** How to resolve `{% extends %}` chain programmatically?

**Jinja2 Internals:**
```python
def _resolve_inheritance_chain(env: jinja2.Environment, template_name: str) -> list[str]:
    """Resolve template inheritance chain bottom-up."""
    chain = []
    current = template_name
    
    while current:
        chain.append(current)
        
        # Load template source
        source, _, _ = env.loader.get_source(env, current)
        
        # Parse AST
        ast = env.parse(source)
        
        # Find {% extends %} node
        extends_node = None
        for node in ast.find_all(jinja2.nodes.Extends):
            extends_node = node
            break
        
        if extends_node and isinstance(extends_node.template, jinja2.nodes.Const):
            # Get parent template name
            current = extends_node.template.value
        else:
            # No more parents
            current = None
    
    # Return in top-down order (base → child)
    return list(reversed(chain))
```

**Example Result:**
```python
chain = _resolve_inheritance_chain(env, "components/worker.py.jinja2")
# Returns: [
#     "base/base_artifact.jinja2",
#     "base/base_code.jinja2",
#     "base/base_python.jinja2",
#     "base/base_python_component.jinja2",
#     "components/worker.py.jinja2"
# ]
```

**Migration Complexity:** **MEDIUM**
- Jinja2 provides AST nodes for extends
- Must handle Const nodes (static template names)
- Recursive resolution straightforward

### Migration Complexity Summary

| Component | Impact | Complexity | Reason |
|-----------|--------|------------|--------|
| **JinjaRenderer** | ✅ No Change | NONE | Jinja2 handles extends during rendering automatically |
| **TemplateIntrospector** | 🔴 Breaking | HIGH | Must parse ALL tiers, merge variables, resolve inheritance |
| **Variable Classification** | ⚠️ Update | MEDIUM | Loop over multiple ASTs instead of one |
| **System Field Injection** | ⚠️ Update | LOW | Already have logic, just ensure Tier 0 fields provided |
| **SCAFFOLD Metadata** | ✅ No Change | NONE | Jinja2 inheritance handles automatically |
| **artifacts.yaml** | ✅ No Change | NONE | Template paths unchanged (point to concrete templates) |
| **ScaffoldMetadataParser** | ✅ No Change | NONE | Parses generated files, not templates |

### Key Insight: Rendering vs Introspection

**Rendering (Scaffolding):** 
- ✅ **NO BREAKING CHANGES!**
- Jinja2's `env.get_template()` + `.render()` **automatically resolves extends**
- Output is identical to current system
- Workers, DTOs, docs all scaffold correctly with multi-tier templates

**Introspection (Validation):**
- 🔴 **BREAKS COMPLETELY!**
- Current code only parses concrete template
- Missing all base template variables
- Validation fails with "missing required fields" errors

**Why This Asymmetry?**
- **Rendering:** Jinja2 Environment does ALL the work (loads bases, merges blocks, renders final output)
- **Introspection:** We manually parse template source → must manually resolve inheritance!

### Migration Strategy Recommendation

**Phase 1: Keep Scaffolding Working (Rendering)**
- ✅ NO CODE CHANGES NEEDED!
- Multi-tier templates work with existing JinjaRenderer
- Jinja2 inheritance resolves automatically

**Phase 2: Fix Introspection (Validation)**
- 🔧 REQUIRES REWRITE of TemplateIntrospector
- Implement `_resolve_inheritance_chain()`
- Parse all tier ASTs
- Merge undeclared variables
- Update classification logic

**Phase 3: Testing & Validation**
- Test rendering: Verify worker.py.jinja2 with 4-tier inheritance produces same output
- Test introspection: Verify schema includes ALL tier variables
- Test validation: Verify missing Tier 0 fields caught correctly

### Open Questions for Planning

**Q1:** Should we refactor TemplateIntrospector NOW (blocking Issue #72) or later?
- Option A: Refactor now → Issue #72 complete + introspection works
- Option B: Defer → Issue #72 templates only, introspection in Issue #121

**Q2:** Can we cache inheritance chains globally?
- Templates don't change at runtime
- Chain resolution expensive (N file loads + AST parses)
- Cache key: template_name → chain list

**Q3:** Should artifacts.yaml store inheritance chain explicitly?
```yaml
worker:
  template_path: "components/worker.py.jinja2"
  inheritance_chain:  # NEW: Precomputed for performance?
    - "base/base_artifact.jinja2"
    - "base/base_code.jinja2"
    - "base/base_python.jinja2"
    - "base/base_python_component.jinja2"
    - "components/worker.py.jinja2"
```

**Hypothesis:** NO - violates DRY (chain is derivable from templates). Cache at runtime instead.

## Open Research Questions - USER RESPONSES

### Q1: Tier 1 Categories - Complete? ✅ ANSWERED

**Question:** Are CODE, DOCUMENT, CONFIG the only Tier 1 format categories?

**USER DECISION:** ✅ **CONFIG moet aparte Tier 1 categorie worden**

**Rationale:**
- CONFIG: Schema-validated (workflows.yaml, labels.yaml)
- DOCUMENT: Structure-validated (research.md, design.md)
- CODE: Syntax-validated (Python, TypeScript, etc.)

**Action for Planning:** Create `base_config.jinja2` as Tier 1 alongside `base_code.jinja2` and `base_document.jinja2`.

---

### Q2: Ephemeral Artifact Handling ✅ ANSWERED

**Question:** Do ephemeral artifacts (commit messages, PR bodies) need special treatment?

**USER DECISION:** ✅ **Blijven DOCUMENT subtype**

**Rationale:** No special template handling needed. Storage is tool responsibility.

**Action for Planning:** No special tier or handling. Ephemeral artifacts use `base_document.jinja2`.

---

### Q3: Optimal Tier Count ✅ ANSWERED - CRITICAL SRP ANALYSIS

**Question:** Is 4-tier hierarchy optimal?

**USER DECISION:** ✅ **MVP's 5 levels (0→1→2→3→Concrete) is optimal**

**MVP Architecture - SRP Analysis:**

```
┌─────────────────────────────────────────────────────────────┐
│ TIER 0: base_artifact.jinja2                               │
│ RESPONSIBILITY: Universal Lifecycle Metadata                │
│ WHY: ALL artifacts need SCAFFOLD metadata (SSOT)           │
│ DEFINES: template_id, version, created, output_path        │
│ BLOCKS: scaffold_metadata (abstract)                       │
└─────────────────────────────────────────────────────────────┘
                           │ extends
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 1: base_code.jinja2                                   │
│ RESPONSIBILITY: Format-Specific Structure                  │
│ WHY: CODE ≠ DOCUMENT ≠ CONFIG (different sections)        │
│ DEFINES: Python # comment format for metadata             │
│ BLOCKS: artifact_header (docstring), code_imports, body   │
└─────────────────────────────────────────────────────────────┘
                           │ extends
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 2: base_python.jinja2                                 │
│ RESPONSIBILITY: Language-Specific Syntax                   │
│ WHY: Python ≠ TypeScript (typing, imports, docstrings)    │
│ DEFINES: from typing import ..., docstring format         │
│ BLOCKS: python_classes, python_functions, python_main     │
└─────────────────────────────────────────────────────────────┘
                           │ extends
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ TIER 3: base_python_component.jinja2                       │
│ RESPONSIBILITY: Domain Pattern Specialization              │
│ WHY: Component ≠ Test ≠ Knowledge (different structure)   │
│ DEFINES: class structure, @layer, @dependencies           │
│ BLOCKS: component_init, component_methods                 │
└─────────────────────────────────────────────────────────────┘
                           │ extends
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ CONCRETE: worker.py.jinja2                                 │
│ RESPONSIBILITY: Specific Artifact Implementation           │
│ WHY: Worker ≠ DTO ≠ Tool (different methods/fields)       │
│ DEFINES: async execute(), BaseWorker inheritance          │
│ BLOCKS: component_methods (implements execute)            │
└─────────────────────────────────────────────────────────────┘
```

**Why Each Tier Exists (SRP):**

1. **Tier 0 (Universal):** Every artifact needs metadata, regardless of format/language
2. **Tier 1 (Format):** CODE needs imports section, DOCUMENT needs sections, CONFIG needs key-value structure
3. **Tier 2 (Language):** Python needs typing imports, Markdown needs heading syntax, YAML needs indent rules
4. **Tier 3 (Specialization):** Components need class structure, Tests need test methods, Knowledge needs question/answer format
5. **Concrete:** Worker needs execute(), DTO needs validate(), Tool needs input/output schemas

**Merging Would Violate SRP:**
- Merge 0+1: Universal metadata tied to format? Python-specific lifecycle? ❌
- Merge 1+2: Code structure tied to language? TypeScript imports in base_code? ❌
- Merge 2+3: Language syntax tied to domain? Component pattern in language tier? ❌

**Conclusion:** 5 levels (4 tiers + concrete) is optimal. Each tier has single, clear responsibility.

**Action for Planning:** Use 5-level hierarchy (0→1→2→3→Concrete).

---

### Q4: Language-Specific Features Depth ✅ ANSWERED

**Question:** How deep should language tiers go?

**USER DECISION:** ✅ **Hypothese correct: Language tier = syntax only**

**Clarification:** "Structuur" = content from `docs/coding_standards/` (header format, etc.)

**Tier 2 Scope (Language):**
- ✅ Syntax: Comments, imports, docstrings, type hints
- ✅ Standards: Header format from coding_standards
- ❌ Advanced features: async/await, decorators → Tier 3 (e.g., `base_python_async_component`)

**Action for Planning:** 
1. Language tier includes coding_standards compliance
2. Advanced language features go in Specialization tier
3. Reference `docs/coding_standards/` in Tier 2 templates

---

### Q5: CONFIG as Separate Tier 1 ✅ ANSWERED

**See Q1** - CONFIG is separate Tier 1 category.

---

### Q6: Sub-Template Composition ⚠️ DEFERRED

**Question:** Should templates auto-scaffold related templates?

**USER INSIGHT:** TDD workflow: RED (tests first) → GREEN (implementation) → REFACTOR

**Current State:** `artifacts.yaml` already has optional `test_template`:
```yaml
worker:
  template: components/worker.py.jinja2
  test_template: tests/worker_test.py.jinja2  # Optional
```

**USER DECISION:** ⚠️ **Sufficient for high-level enforcement tools (later issue)**

**Implication:** Scaffolding follows TDD order:
1. Agent scaffolds test first (RED phase)
2. Agent scaffolds implementation (GREEN phase)
3. Agent refactors (REFACTOR phase)

**Current artifacts.yaml supports this:** Test template is metadata, not auto-triggered.

**Action for Planning:** 
- Keep current `test_template` metadata approach
- No automatic composition (preserves TDD workflow control)
- Enforcement tools can use metadata (future issue)

---

### Q7: Template Versioning & Migration - Impact Analysis ⚠️ CRITICAL

**Question:** What's the impact of implementing template versioning NOW vs LATER?

**Scenario:** Template v1.0 → v2.0 (breaking changes), existing files need migration

**OPTION A: Implement NOW (Issue #72 scope)**

**Pros:**
- ✅ Complete SCAFFOLD metadata from day 1
- ✅ Future-proof (no retrofitting later)
- ✅ Migration logic easier with fresh codebase

**Cons:**
- ❌ Scope creep (+6-8h effort)
- ❌ Blocks Issue #72 completion
- ❌ No immediate use case (all templates v1.0)

**Components Needed:**
1. Version comparison logic (`1.0.0` < `2.0.0`)
2. Migration script API (`migrate_v1_to_v2(file)`)
3. Migration registry (which templates have migrations)
4. Safe migration execution (backup, rollback)
5. Testing framework for migrations

**Effort:** ~6-8 hours (vs Issue #72 estimate: 12-16h = 50% increase)

**OPTION B: Implement LATER (Future Issue)**

**Pros:**
- ✅ Keeps Issue #72 focused (base template architecture)
- ✅ Real-world use case first (v2.0 actually exists)
- ✅ Learn from v1.0 → v2.0 patterns before building migration

**Cons:**
- ❌ SCAFFOLD metadata has `version` but no migration logic
- ❌ Retrofitting migration later might be harder
- ❌ Early adopters face manual migration

**Compromise: VERSION NOW, MIGRATION LATER**

**Implementation:**
1. **NOW (Issue #72):**
   - `template_version` in SCAFFOLD metadata ✅
   - Version stored in generated files ✅
   - Version comparison utility (`compare_versions(a, b)`) ✅
   - Documentation: "Migration not yet supported" ✅

2. **LATER (Issue #XXX - Template Migration):**
   - Migration script API
   - Migration registry
   - Safe execution framework
   - Testing

**USER DECISION:** ✅ **Option B** - Version metadata only, migration later

**Rationale:**
- Migration logic CANNOT be built without actual v2.0 templates to migrate to
- Current scope only has v1.0 templates (no v2.0 exists yet)
- Building migration infrastructure without test cases = premature engineering
- Version metadata in SCAFFOLD enables future migration (registry lookup)

**Implementation for Issue #72:**
1. ✅ SCAFFOLD metadata includes template_version (compound format - see Q8b)
2. ✅ Registry stores version history for all tiers
3. ✅ Version comparison utility (`compare_versions(a, b)`)
4. ✅ Documentation: "Migration not yet supported"
5. ❌ NO migration script API (deferred to future issue)
6. ❌ NO migration execution framework (deferred to future issue)

**LATER (Issue #XXX - Template Migration):**
- Create v2.0 templates with breaking changes
- Build migration scripts with actual test cases
- Implement safe execution framework
- Test with real-world scenarios

---

### Q8: Post-Generation Editing Schema - CRITICAL DESIGN ✅ ANSWERED

**Question:** Which schema to present to editing tools for validation?

**USER DECISION:** ✅ **Flattened schema, EXCLUDE computed variables**

**Rationale:** 
- Agent has no control over computed vars (`{% set class_name = worker_name + "Worker" %}`)
- Computed vars are template implementation details
- Schema is for detecting which template was used

**Implementation:**

**BEFORE (MVP - includes computed):**
```python
schema = TemplateSchema(
    required=['worker_name', 'worker_description', 'class_name', 'module_docstring', ...],
    optional=['worker_logic', 'worker_dependencies', ...]
)
# 12 variables total (includes 8 computed)
```

**AFTER (User Decision - excludes computed):**
```python
schema = TemplateSchema(
    required=['worker_name', 'worker_description'],  # Input only
    optional=['worker_logic', 'worker_dependencies'],  # Input only
    computed=['class_name', 'module_docstring', 'layer', ...]  # For documentation
)
# 4 input variables + 8 computed (separated)
```

**Detection Algorithm:**
```python
def detect_template(file_path):
    metadata = parse_scaffold_metadata(file_path)
    template_id = metadata['template_id']  # e.g., "worker"
    
    # Get INPUT schema only (not computed)
    schema = get_template_input_schema(template_id)
    
    # Validate file has all required inputs
    # (computed vars are derived, no validation needed)
    return validate_against_schema(file_path, schema)
```

**NEW CHALLENGE: Compound Version in Multi-Tier Templates** 🔴

**USER QUESTION:** "Welke versie van welke template komt in SCAFFOLD metadata bij multi-tier opbouw?"

**Problem:**
```
Tier 0: base_artifact.jinja2 v2.1.0
Tier 1: base_code.jinja2 v1.5.0
Tier 2: base_python.jinja2 v3.0.0
Tier 3: base_python_component.jinja2 v1.2.0
Concrete: worker.py.jinja2 v1.0.0

→ What goes in SCAFFOLD:template_version?
```

**OPTION 1: Concrete Template Version Only**
```python
# SCAFFOLD:template_version: 1.0.0  (worker.py.jinja2 version)
```

**Pros:**
- ✅ Simple
- ✅ Matches user's mental model (worker template v1.0)

**Cons:**
- ❌ Loses tier version information
- ❌ Can't detect base template breaking changes

**OPTION 2: Compound Version (All Tiers)**
```python
# SCAFFOLD:template_version: 1.0.0
# SCAFFOLD:template_version_base_artifact: 2.1.0
# SCAFFOLD:template_version_base_code: 1.5.0
# SCAFFOLD:template_version_base_python: 3.0.0
# SCAFFOLD:template_version_base_python_component: 1.2.0
```

**Pros:**
- ✅ Complete version history
- ✅ Can detect base template changes

**Cons:**
- ❌ Verbose (5 lines per file)
- ❌ Complex comparison

**OPTION 3: Version Chain (Hierarchical)**
```python
# SCAFFOLD:template_version: 1.0.0+2.1.0+1.5.0+3.0.0+1.2.0
# Format: concrete+tier0+tier1+tier2+tier3
```

**Pros:**
- ✅ Complete info in one line
- ✅ Parseable

**Cons:**
- ❌ Cryptic format
- ❌ Order-dependent

**OPTION 4: Semantic Compound Version**
```python
# SCAFFOLD:template_version: 1.0.0
# SCAFFOLD:template_base_versions: artifact:2.1.0,code:1.5.0,python:3.0.0,component:1.2.0
```

**Pros:**
- ✅ Clear separation (concrete vs bases)
- ✅ Human-readable
- ✅ Parseable

**Cons:**
- ❌ Two-line format

**USER DECISION:** ✅ **Option 5** - Ultra-Compact Single-Line + Registry Lookup

**Rationale:**
- User preference: "alle scaffold metadata op 1 regel!"
- Registry serves as **type+version lookup** - hashes encode entire tier chain
- Scaffolded files remain minimal and clean
- Full traceability via registry (hash → complete tier version history)

**Format:**
```
{comment_syntax} SCAFFOLD: {artifact_type}:{version_hash} | {timestamp} | {output_path}
```

**Examples:**

**Python Worker:**
```python
# SCAFFOLD: worker:a3f7b2c1 | 2026-01-22T10:30:00Z | src/workers/ProcessWorker.py
```

**YAML Config:**
```yaml
# SCAFFOLD: config:b2e4f891 | 2026-01-22T10:30:00Z | config/app.yaml
```

**Markdown Document:**
```markdown
<!-- SCAFFOLD: document:c5a7d3e2 | 2026-01-22T10:30:00Z | docs/design/feature-spec.md -->
```

**Registry Structure:**
```yaml
# .st3/template_registry.yaml
version_hashes:
  a3f7b2c1:  # worker v2.3.1 chain
    artifact_type: worker
    concrete: {template_id: concrete_worker, version: 2.3.1}
    tier0: {template_id: tier0_base_artifact, version: 1.0.0}
    tier1: {template_id: tier1_base_code, version: 1.0.0}
    tier2: {template_id: tier2_base_python, version: 1.1.0}
    tier3: {template_id: tier3_base_python_component, version: 1.0.0}
    hash_algorithm: SHA256
    created: 2026-01-22T10:30:00Z
```

**Implementation:**

**During Scaffolding:**
```python
# 1. Resolve tier chain versions from registry
artifact_entry = registry.get_artifact("worker")

# 2. Calculate compound hash
tier_versions = [
    artifact_entry['tier0']['version'],  # 1.0.0
    artifact_entry['tier1']['version'],  # 1.0.0
    artifact_entry['tier2']['version'],  # 1.1.0
    artifact_entry['tier3']['version'],  # 1.0.0
    artifact_entry['concrete']['version']  # 2.3.1
]
version_string = "|".join(tier_versions)
hash_full = hashlib.sha256(version_string.encode()).hexdigest()
hash_short = hash_full[:8]  # a3f7b2c1

# 3. Store hash in registry (if new)
if hash_short not in registry['version_hashes']:
    registry.add_hash(hash_short, artifact_entry, tier_versions)
    registry.save()

# 4. Embed compact metadata in generated file
scaffold_line = f"# SCAFFOLD: worker:{hash_short} | {timestamp} | {output_path}"
```

**During Introspection/Migration:**
```python
# 1. Parse SCAFFOLD metadata from file
metadata = parse_scaffold_line(file_content)
# {'artifact_type': 'worker', 'version_hash': 'a3f7b2c1', 'timestamp': '...', 'path': '...'}

# 2. Lookup full version chain in registry
version_chain = registry.decode_hash(metadata['version_hash'])

# 3. Compare against current template versions
current_versions = registry.get_artifact(metadata['artifact_type'])
if version_chain != current_versions:
    print(f"Migration available: {version_chain} → {current_versions}")
```

**Key Properties:**
- ✅ **Compact:** 1 line per file (56-80 chars typical)
- ✅ **Complete:** Hash encodes entire tier chain
- ✅ **Traceable:** Registry provides full history
- ✅ **Extensible:** Add new fields without breaking format
- ✅ **Language-agnostic:** Works with any comment syntax
- ⚠️ **Registry dependency:** Hash useless without registry (but registry is SSOT anyway)

**CRITICAL:** During scaffolding, **calculate and register hash if not exists**. Registry must be updated before writing SCAFFOLD metadata.

**Action for Planning:**
1. Define registry schema (version_hashes section)
2. Implement hash calculation utility
3. Implement registry lookup utility
4. Update template_metadata block to emit compact format
5. Test round-trip: scaffold → parse → lookup → validate

**Action for Planning:**
1. Introspection returns INPUT variables only (exclude computed)
2. Computed variables documented separately (for reference)
3. SCAFFOLD metadata uses semantic compound version (Option 4)
4. Version comparison compares concrete version only (bases are implementation details)

---

## Research Decisions Summary

| Question | Status | Decision | Action |
|----------|--------|----------|--------|
| Q1: CONFIG Tier 1 | ✅ DECIDED | Yes, separate | Create base_config.jinja2 |
| Q2: Ephemeral | ✅ DECIDED | DOCUMENT subtype | No special handling |
| Q3: Tier count | ✅ DECIDED | 5 levels (4 tiers) | Use 0→1→2→3→Concrete |
| Q4: Language depth | ✅ DECIDED | Syntax + standards | Include coding_standards |
| Q5: = Q1 | ✅ DECIDED | See Q1 | - |
| Q6: Composition | ⚠️ DEFERRED | Later issue | Keep test_template metadata |
| Q7: Versioning | ✅ DECIDED | Version metadata only | Defer migration to future |
| Q8: Edit schema | ✅ DECIDED | Flattened, no computed | Separate input/computed |
| Q8b: Compound version | ✅ DECIDED | Ultra-compact 1-line | Registry-backed hash |

**All Research Decisions Complete - Ready for Planning Phase.**

**Exploration:**
- **BINARY/ASSETS:** Images, fonts, compiled files → out of scope for text templating?
- **DATA:** CSV, SQL dumps → not scaffolded (data *definitions* are CODE)
- **SCRIPTS:** Shell scripts, build files → are these CODE or separate category?

**Hypothesis:** SCRIPTS are CODE (Bash = programming language).

**Need:** Validate with real-world scaffolding scenarios.

### Q2: Ephemeral Artifact Handling

**Question:** Do ephemeral artifacts (commit messages, PR bodies) need special treatment?

**Analysis:**
- Template POV: Same as documents (structure, validation)
- Storage POV: Temporary location (`.st3/tmp/`)
- Lifecycle POV: One-time use, then deleted

**Hypothesis:** Ephemeral = DOCUMENT subtype (no Tier 1 category needed).

**Validation:** Scaffold commit message → verify it's treated like document template.

### Q3: Optimal Tier Count

**Question:** Is 4-tier hierarchy (Lifecycle → Format → Language → Specialization) optimal?

**Alternatives:**
- **3-tier:** Merge Lifecycle + Format into single tier?
- **5-tier:** Add Environment tier (dev/test/prod templates)?

**Trade-offs:**
- More tiers = more DRY but higher complexity
- Fewer tiers = simpler but more duplication

**Need:** Prototype both 3-tier and 4-tier to compare.

### Q4: Language-Specific Features

**Question:** How deep should language tiers go? Python has type hints, Rust has ownership → tier per feature?

**Examples:**
- Python: Type hints, async/await, decorators, context managers
- TypeScript: Generics, decorators, type guards
- Rust: Ownership, lifetimes, traits

**Risk:** Too many language-specific tiers → complexity explosion.

**Hypothesis:** Language tier handles syntax only (comments, imports, docstrings). Advanced features go in Specialization tier (e.g., `base_python_async_component`).

**Need:** Research Python-specific vs language-agnostic patterns.

### Q5: CONFIG as Tier 1 Category

**Question:** Is CONFIG distinct enough from DOCUMENT to be separate Tier 1?

**Differences:**
- CONFIG: Schema-validated, key-value, machine-readable
- DOCUMENT: Structural validation, sections, human-readable

**Scenarios:**
- Scaffold new workflow in `workflows.yaml` → CONFIG template
- Scaffold new research doc → DOCUMENT template

**Hypothesis:** CONFIG is separate Tier 1 (different validation, editing patterns).

**Need:** Prototype CONFIG template to validate hypothesis.

### Q6: Existing System Patterns

**Question:** Can we adopt Yeoman's sub-generator composability without code-based approach?

**Yeoman pattern:**
```javascript
this.composeWith('generator-name:sub-generator');
```

**Our equivalent (hypothesis):**
```yaml
# artifacts.yaml
worker:
  template: components/worker.py.jinja2
  sub_templates:
    - test: tests/worker_test.py.jinja2  # Auto-generate test
```

**Question:** Does sub-template composition belong in research or planning phase?

### Q7: Template Versioning Strategy

**Question:** Copier has template migration support. Do we need this?

**Scenarios:**
- Template v1.0 → v2.0 (breaking changes)
- Existing files scaffolded with v1.0
- User runs "update template" → migrate to v2.0?

**Current:** Version in SCAFFOLD metadata but no migration logic.

**Hypothesis:** Out of scope for Issue #72 (future enhancement).

**Need:** Document as future work, not blocking.

---

## Findings Summary

### Problem Statement (Validated)

1. **DRY Violation:** SCAFFOLD metadata duplicated across base templates
2. **Limited Extensibility:** Python-only, adding languages requires duplication
3. **Mixed Concerns:** Base templates combine lifecycle + format + language + specialization
4. **Incomplete Coverage:** Only 8% of templates have SCAFFOLD metadata

### Existing Systems (Lessons Learned)

**Cookiecutter:**
- ❌ No inheritance (duplication problem)
- ✅ Jinja2 is powerful

**Copier:**
- ✅ Template versioning
- ✅ Type-safe configuration
- ❌ Still no inheritance

**Yeoman:**
- ✅ Composability (sub-generators)
- ❌ Code-based (violates Config Over Code)

**Conclusion:** No existing system achieves our goals (DRY + SSOT + multi-language + config-driven).

### Artifact Taxonomy (Discovered)

**4 Orthogonal Dimensions:**
1. **Lifecycle:** Universal metadata (template_id, version, created, path)
2. **Format:** CODE, DOCUMENT, CONFIG (possibly others)
3. **Language:** Python, TypeScript, Markdown, YAML, etc.
4. **Specialization:** Component, Test, Knowledge, Policy, etc.

**Key Insight:** Current base templates mix all 4 dimensions → prevents DRY.

### Ephemeral Artifacts (Classified)

**Conclusion:** Ephemeral artifacts (commit messages, PR bodies) are DOCUMENTS with temporary storage. No special template handling needed (storage is tool responsibility).

### Architectural Pattern (Hypothesis)

**Multi-tier hierarchy:** Separate each dimension into its own tier.

**Pros:**
- SCAFFOLD metadata defined ONCE (Tier 0)
- Language-agnostic extensibility
- DRY across all dimensions

**Cons:**
- Higher complexity (4 tiers vs 1)
- Cognitive load of inheritance chain

**Need:** Validate in Planning/Design phase.

---

## Recommendations for Planning Phase

### 1. Prototype Multi-Tier Hierarchy

**Goal:** Validate 4-tier vs 3-tier architecture with real templates.

**Approach:**
- Create `base_artifact.jinja2` (Tier 0)
- Create `base_code.jinja2`, `base_document.jinja2` (Tier 1)
- Create `base_python.jinja2`, `base_markdown.jinja2` (Tier 2)
- Refactor 1 template (e.g., worker.py) to use 4-tier chain
- Measure: DRY achievement, complexity, rendering time

### 2. Validate CONFIG as Tier 1

**Goal:** Determine if CONFIG needs separate tier or can merge with DOCUMENT.

**Approach:**
- Identify CONFIG scaffolding scenarios (workflows.yaml, labels.yaml)
- Compare validation patterns: CONFIG (schema) vs DOCUMENT (structure)
- Decide: Separate tier or DOCUMENT subtype?

### 3. Explore Language-Agnostic Patterns

**Goal:** Identify what belongs in language tier vs specialization tier.

**Approach:**
- List Python-specific features (type hints, async, decorators)
- List language-agnostic patterns (component lifecycle, dependency injection)
- Classify: Which tier owns which pattern?

### 4. Quantify DRY Improvement

**Goal:** Measure duplication reduction with multi-tier approach.

**Metrics:**
- Lines of SCAFFOLD metadata: Current (N bases) vs Proposed (1 base)
- Effort to add TypeScript: Current (duplicate all bases) vs Proposed (add 1 language tier)
- Template count to achieve 100% coverage: Current vs Proposed

### 5. Risk Assessment

**Goal:** Identify risks of 4-tier architecture.

**Risks:**
- Cognitive load (understanding inheritance chain)
- Debugging complexity (which tier defines what?)
- Performance (4 templates loaded vs 1)
- Migration effort (refactor 24 existing templates)

---

## Acceptance Criteria Coverage

**Source:** Issue #72 Success Criteria

| Acceptance Criterion | Status | Evidence/Location | Planning Input |
|---------------------|--------|-------------------|----------------|
| **Architecture** | | | |
| 5-level template hierarchy implemented (Tier 0→1→2→3→Concrete) | ✅ DESIGNED | MVP: `docs/development/issue72/mvp/templates/`, Research Q3 | Implementation: Create base templates for all tiers |
| Base templates cover 3 Tier 1 categories (CODE, DOCUMENT, CONFIG) | ✅ DESIGNED | Research Q1, Dimensional Analysis | Implementation: Create tier1_base_config.jinja2 (CODE/DOCUMENT proven in MVP) |
| Template registry operational with hash-based versioning | ✅ DESIGNED | Research Q8b, Registry Structure section | Implementation: Build `.st3/template_registry.yaml` + utilities |
| **Template Quality** | | | |
| Worker template uses IWorkerLifecycle pattern | ⚠️ PARTIAL | **RESEARCH GAP** - Pattern identified, tier placement not analyzed | **BLOCKER:** Analyze lifecycle pattern fit within tier model (see Worker Lifecycle Analysis below) |
| All backend patterns reflected in component templates | 🔴 NOT COVERED | Research focuses on structure, not pattern inventory | Planning: Audit current backend patterns, map to Tier 3 specializations |
| Research/planning/test templates with agent guidance | 🔴 NOT COVERED | Research mentions need, no design | Planning: Define agent hint format, scaffold template structure |
| All templates include ultra-compact SCAFFOLD metadata | ✅ DESIGNED | Research Q8b, Format section | Implementation: Tier 0 provides scaffold_metadata block |
| Documentation covers template usage and patterns | 🔴 NOT COVERED | Out of research scope | Planning: Define documentation structure, examples |
| All scaffolded code passes validation (E2E tests passing - Issue #74) | ⚠️ DEPENDENCY | Requires template validation infrastructure (#52) | Planning: Coordinate with #52/#74, define validation hooks |
| **Extensibility** | | | |
| Adding new language requires only 1 Tier 2 template (not 13+ duplicates) | ✅ PROVEN | MVP demonstrates Python tier, extrapolate to TypeScript/etc | Implementation: Create tier2_base_typescript.jinja2 as proof |
| Adding new format requires only 1 Tier 1 template | ✅ PROVEN | CONFIG identified as new format, MVP proves CODE/DOCUMENT | Implementation: Create tier1_base_config.jinja2 |
| SCAFFOLD metadata defined once (Tier 0), inherited by all | ✅ PROVEN | MVP: `tier0_base_artifact.jinja2` line 1-7 | Implementation: All concrete templates extend Tier 0 chain |

**Coverage Summary:**
- **Designed/Proven:** 9/13 (69%) - Architecture and extensibility well-covered
- **Partial/Gaps:** 2/13 (15%) - Worker lifecycle, validation dependency
- **Not Covered:** 2/13 (15%) - Backend patterns inventory, agent hints, documentation

**Critical for Planning:**
1. ⚠️ **Worker lifecycle analysis** (see dedicated section below)
2. 🔴 **Backend pattern audit** (inventory current patterns for mapping)
3. 🔴 **Agent hint format** (define structure for document templates)

---

## Worker Lifecycle Pattern Analysis (Hypothesis)

**Context:** Issue #72 AC requires "Worker template uses IWorkerLifecycle pattern".

**Research Gap:** Current research establishes tier architecture but needs to validate lifecycle pattern fit and identify concrete backend contracts requiring this pattern.

### Pattern Description

**IWorkerLifecycle (two-phase initialization):**
```python
class MyWorker(IWorkerLifecycle):
    def __init__(self, config: WorkerConfig):
        """Phase 1: Light initialization (no I/O, no heavy objects)"""
        self._config = config
        self._client = None  # Not initialized yet
    
    async def initialize(self) -> None:
        """Phase 2: Heavy initialization (async I/O, connections)"""
        self._client = await create_async_client(self._config.url)
    
    async def shutdown(self) -> None:
        """Cleanup phase"""
        if self._client:
            await self._client.close()
```

**Rationale:** Separates sync construction (fast, testable) from async resource acquisition (I/O-bound).

### Dimensional Analysis (Working Hypothesis)

**Question:** Which tier owns lifecycle pattern?

**Hypothesis 1: Tier 3 (Specialization) - Python Component** ⭐ RECOMMENDED FOR VALIDATION
- **Pro:** Lifecycle is component-specific (not all Python code needs lifecycle)
- **Pro:** Test templates don't need lifecycle, Data Models don't need it
- **Pro:** Aligns with "Component" specialization (business logic with dependencies)
- **Con:** What if TypeScript components also need lifecycle? Duplication?

**Hypothesis 2: Tier 2 (Language) - Python**
- **Pro:** `async/await` is Python-specific syntax
- **Con:** Not all Python artifacts need lifecycle (DTOs, utils)
- **Con:** Mixes syntax concern (async) with architectural concern (lifecycle)

**Hypothesis 3: Cross-cutting via Composition (Deferred to Issue #XX)**
- **Pro:** Lifecycle is a mixin pattern, could be composed
- **Con:** Template composition out of scope for #72 (Q6 deferred)

**Working Recommendation:** **Hypothesis 1 - Tier 3 Specialization**

**Rationale:**
- Lifecycle is likely a **domain pattern**, not a language feature
- TypeScript/C#/Go also have lifecycle patterns (constructor + init() + dispose())
- Each language implements lifecycle differently (Python async, C# IDisposable, Go defer)
- Tier 2 provides syntax (async/await keywords), Tier 3 applies pattern to component type

**Missing Evidence (Critical for Planning):**
1. 🔴 **Audit `src/workers/`:** Which workers actually implement IWorkerLifecycle? How many?
2. 🔴 **Backend contract:** Is IWorkerLifecycle an actual interface in codebase? Where defined?
3. 🔴 **Pattern necessity:** Why is two-phase init required? What breaks with single-phase?
4. 🔴 **Template impact:** Does current `worker.py.jinja2` template generate IWorkerLifecycle code?
5. 🔴 **Cross-language:** Do TypeScript/other components in repo follow similar patterns?

**Tier Assignment (Tentative):**
```
Tier 0: base_artifact.jinja2           → SCAFFOLD metadata
Tier 1: base_code.jinja2                → Code-specific formatting
Tier 2: base_python.jinja2              → async/await syntax, type hints
Tier 3: base_python_component.jinja2    → IWorkerLifecycle pattern  ← HYPOTHESIS
Concrete: worker.py.jinja2              → Worker-specific logic
```

**Implementation Impact (If Hypothesis Valid):**
- `tier3_base_python_component.jinja2` defines:
  - `{% block lifecycle_interface %}IWorkerLifecycle{% endblock %}`
  - `{% block init_method %}` (Phase 1 pattern)
  - `{% block initialize_method %}` (Phase 2 pattern)
  - `{% block shutdown_method %}` (Cleanup pattern)
  
- Concrete `worker.py.jinja2` provides:
  - Specific dependencies to inject
  - Specific resources to initialize
  - Worker-specific business logic

**Cross-Language Comparison (Theoretical):**
| Language | Tier 2 (Syntax) | Tier 3 (Lifecycle Pattern) |
|----------|-----------------|---------------------------|
| Python | async/await | IWorkerLifecycle (async init/shutdown) |
| TypeScript | async/await, Promise | ILifecycle (async init/dispose) |
| C# | async/await, Task | IAsyncDisposable (InitializeAsync/DisposeAsync) |
| Go | goroutines, channels | Init()/Close() methods |

**Planning Input (Critical Actions):**
1. **VALIDATE HYPOTHESIS:** Audit actual codebase (src/workers/, src/adapters/) for lifecycle usage
2. **IDENTIFY CONTRACTS:** Find IWorkerLifecycle interface definition, usage patterns
3. **ASSESS NECESSITY:** Document why two-phase init is architectural requirement
4. **VERIFY TEMPLATE:** Check if worker.py.jinja2 currently generates lifecycle code
5. **IF VALIDATED:** Define `tier3_base_python_component.jinja2` with lifecycle blocks
6. **IF INVALIDATED:** Reassess tier placement or remove from AC

---

## Issue #52 Alignment (Template Validation Integration)

**Context:** Issue #72 depends on Issue #52 (template validation infrastructure). Critical to understand actual implementation, not hypothetical design.

### Issue #52 Reality Check

**What #52 Actually IS:**
- ✅ **Template-driven validation** via `TEMPLATE_METADATA` in template files
- ✅ **Three-tier enforcement:** STRICT → ARCH → GUIDELINE (see `layered_template_validator.py`)
- ✅ **Inheritance-aware:** `TemplateAnalyzer.get_base_template()` walks `{% extends %}` chains
- ✅ **Integrated in SafeEdit:** `safe_edit_tool.py` → `ValidationService` → `LayeredTemplateValidator`

**What #52 is NOT:**
- ❌ **NO `validation.yaml` file** - validation rules live IN templates (SSOT principle)
- ❌ **NO standalone validation tool** - `template_validator.py` is deprecated, "always passes"
- ❌ **NO `validate_template` MCP tool reliability** - uses deprecated validator, gives false confidence

**Key Implementation Files:**
```
mcp_server/template/
├── template_analyzer.py              # Parses TEMPLATE_METADATA, walks {% extends %}
├── layered_template_validator.py     # Three-tier rule enforcement
└── validation_service.py             # Orchestrates validation flow

mcp_server/tools/
└── safe_edit_tool.py                 # Integration point (SafeEditTool → ValidationService)

templates/base/
└── base_document.md.jinja2           # Example: Contains TEMPLATE_METADATA with STRICT rules
```

**Evidence from #52 Research:**
> "Geen validation.yaml, dat zou duplicate SSOT zijn" - [docs/development/issue52/research.md]

### Current CODE Template Gap

**Problem:** DOCUMENT templates have TEMPLATE_METADATA, CODE templates don't.

**Evidence:**
```python
# templates/base/base_document.md.jinja2 - HAS TEMPLATE_METADATA ✅
{# TEMPLATE_METADATA:
  tier: STRICT
  format_rules:
    - "^# " (title required)
    - "^## " (sections required)
#}

# templates/base/base_component.py.jinja2 - NO TEMPLATE_METADATA ❌
# (Currently lacks validation metadata)
```

**Impact:** LayeredTemplateValidator cannot enforce format rules for CODE templates.

**Issue #72 Opportunity:** Multi-tier architecture is PERFECT place to add TEMPLATE_METADATA systematically.

### Alignment Strategy for Issue #72

**Principle:** Issue #72 multi-tier templates MUST be {% extends %}-based AND carry TEMPLATE_METADATA per tier.

**Tier-to-Validation Mapping:**

| Tier | Validation Tier | TEMPLATE_METADATA Content | Example Rules |
|------|----------------|---------------------------|---------------|
| **Tier 0: base_artifact** | STRICT | Universal constraints (SCAFFOLD format) | "^# SCAFFOLD: " or "^<!-- SCAFFOLD: " |
| **Tier 1: base_code/document/config** | STRICT | Format-specific structure | CODE: imports/classes, DOCUMENT: headings, CONFIG: schema |
| **Tier 2: base_python/markdown/yaml** | ARCH | Language syntax patterns | Python: type hints, Markdown: link format, YAML: indent |
| **Tier 3: base_python_component** | ARCH | Specialization patterns | Component: lifecycle methods, Test: fixtures |
| **Concrete: worker.py** | GUIDELINE | Artifact-specific hints | Worker: error handling, logging |

**Critical Design Rules:**

1. **Each tier defines TEMPLATE_METADATA:**
   ```jinja2
   {# TEMPLATE_METADATA:
     tier: STRICT  # or ARCH, or GUIDELINE
     format_rules:
       - "pattern1"
       - "pattern2"
     inherited: true  # Allows child templates to see these rules
   #}
   ```

2. **Use {% extends %} consistently:**
   ```jinja2
   {% extends "tier3_base_python_component.jinja2" %}
   {# This allows TemplateAnalyzer.get_base_template() to work #}
   ```

3. **ValidationService merges rules from chain:**
   - Worker.py → Tier 3 → Tier 2 → Tier 1 → Tier 0
   - All STRICT rules enforced first
   - Then ARCH rules
   - Then GUIDELINE warnings

4. **NO validation.yaml:**
   - Registry (`.st3/template_registry.yaml`) = provenance/versioning
   - TEMPLATE_METADATA = validation contract
   - These are orthogonal concerns

### Planning Actions (Critical for Success)

**PA-1: Define TEMPLATE_METADATA for All Base Tiers**
- [ ] Tier 0: SCAFFOLD metadata format rules
- [ ] Tier 1 CODE: Import/class/function structure
- [ ] Tier 1 DOCUMENT: Heading hierarchy
- [ ] Tier 1 CONFIG: Schema validation hooks
- [ ] Tier 2 Python: Type hints, docstrings, async patterns
- [ ] Tier 2 Markdown: Link format, code block syntax
- [ ] Tier 2 YAML: Indentation, key format
- [ ] Tier 3+ : Specialization-specific patterns

**PA-2: Verify {% extends %} Chain Compatibility**
- [ ] Test: TemplateAnalyzer can walk 5-level inheritance
- [ ] Test: TEMPLATE_METADATA merges correctly across tiers
- [ ] Test: SafeEditTool enforces rules from all tiers

**PA-3: Coordinate with #52 Implementation Status**
- [ ] Check: Is LayeredTemplateValidator finalized?
- [ ] Check: Are DOCUMENT templates fully validated?
- [ ] Gap: Extend validation to CODE templates (Tier 1+ in #72)
- [ ] Test: E2E validation with multi-tier templates

**PA-4: Update Validation Tooling**
- [ ] Deprecate: Remove misleading `validate_template` tool OR fix to use LayeredTemplateValidator
- [ ] Document: SafeEditTool is canonical validation route
- [ ] Document: TEMPLATE_METADATA authoring guide for template designers

**PA-5: Test Strategy (Coordinate with #74)**
- [ ] Unit test: Each tier's TEMPLATE_METADATA rules
- [ ] Integration test: Multi-tier rule merging
- [ ] E2E test: Scaffolded code passes LayeredTemplateValidator
- [ ] Regression test: Existing templates don't break

### Risk Assessment

**HIGH: CODE template validation is currently unimplemented**
- Mitigation: Issue #72 Tier 1 CODE must include TEMPLATE_METADATA from day 1
- Timeline: Cannot ship #72 without CODE validation (use #74 as test bed)

**MEDIUM: 5-level inheritance may stress TemplateAnalyzer**
- Mitigation: Test with MVP's 5-level chain, profile performance
- Fallback: Flatten some tiers if analysis too slow

**LOW: TEMPLATE_METADATA format may evolve**
- Mitigation: #52 defines format, #72 consumes it (not our decision)
- Coordination: Sync with #52 owner if format changes needed

### Open Questions for Planning

**OQ-V1: TEMPLATE_METADATA Inheritance Semantics**
- Question: Do child templates override or merge parent rules?
- Current assumption: Merge (child adds rules, doesn't remove parent rules)
- Needs verification: Check TemplateAnalyzer.merge_metadata() implementation

**OQ-V2: Validation Performance**
- Question: Does 5-tier validation add significant overhead to scaffolding?
- Test: Benchmark single-tier vs multi-tier validation
- Threshold: <100ms acceptable for interactive use

**OQ-V3: Rule Conflict Resolution**
- Question: What if Tier 2 rule contradicts Tier 1 rule?
- Example: Tier 1 requires "class X:", Tier 2 requires "class X(Base):"
- Resolution strategy: STRICT tier wins? Or error?

---

## Technical Blockers for Planning

### Blocker #1: Inheritance-Aware Introspection (CRITICAL)

**Problem:** Current `TemplateIntrospector` analyzes single template files, missing variables defined in parent templates.

**Evidence:** MVP demonstrates 67% variable miss rate:
```python
# Single-template introspection (CURRENT)
schema = introspect_template("worker.py.jinja2")
# Returns: ['worker_name', 'worker_description']  (2 vars)
# MISSES: 'timestamp', 'output_path', 'template_version', etc (6 vars from parents)

# Multi-tier introspection (REQUIRED)
schema = introspect_template_with_inheritance("worker.py.jinja2")
# Returns: ALL 8 variables (2 from concrete + 6 from tiers 0-3)
```

**Impact:** 
- ❌ Cannot validate user input against complete schema
- ❌ Cannot detect which template was used (missing parent variables)
- ❌ Scaffolding may fail due to missing required variables

**MVP Solution:** AST walking via `jinja2.nodes.Extends`:
```python
def introspect_template_with_inheritance(env, template_name):
    """Walk {% extends %} chain, merge variables from all tiers."""
    all_vars = set()
    current = template_name
    
    while current:
        ast = env.get_or_select_template(current).module.__loader__.get_source(env, current)[1]
        parsed = env.parse(ast)
        all_vars.update(meta.find_undeclared_variables(parsed))
        
        # Find parent template
        extends_nodes = list(parsed.find_all(nodes.Extends))
        current = extends_nodes[0].template.value if extends_nodes else None
    
    return all_vars  # Complete schema
```

**Validation:** MVP proves this approach works (~60 lines, 100% coverage).

**Must-Have for Planning:**
1. ✅ Integrate `introspect_template_with_inheritance()` into `TemplateIntrospector` class
2. ✅ Add unit tests for multi-tier introspection (5-level chain)
3. ✅ Update `scaffold_artifact` tool to use inheritance-aware introspection
4. ✅ Document limitation: Computed variables ({% set %}) still excluded (by design, Q8)

**Definition of Done:**
- [ ] `TemplateIntrospector.get_schema()` walks full inheritance chain
- [ ] Unit test: 5-tier worker template returns all 8 variables
- [ ] E2E test: Scaffolding validates against complete schema
- [ ] Documentation: Introspection algorithm explained in architecture guide

**Risk if Deferred:** Multi-tier templates will scaffold but validation will fail silently (missing parent variables).

---

## Legacy Template Migration Inventory

**Context:** Issue #72 restructures all templates. Current 24 templates are legacy, requiring migration to 5-tier architecture.

**Inventory (by Format):**

**CODE Templates (13):**
- `worker.py.jinja2` → Refactor to Tier 3 (python_component) + Concrete
- `adapter.py.jinja2` → Refactor to Tier 3 (python_component) + Concrete
- `dto.py.jinja2` → NEW: Refactor to Tier 3 (python_data_model) + Concrete
- `mcp_tool.py.jinja2` → Refactor to Tier 3 (python_tool) + Concrete
- `mcp_resource.py.jinja2` → Refactor to Tier 3 (python_tool) + Concrete
- _(8 more Python templates)_

**DOCUMENT Templates (9):**
- `research.md.jinja2` → NEW: Create from Tier 3 (markdown_knowledge) + Concrete
- `planning.md.jinja2` → NEW: Create from Tier 3 (markdown_knowledge) + Concrete
- `commit_message.txt.jinja2` → Refactor to Tier 3 (markdown_ephemeral) + Concrete
- _(6 more Markdown templates)_

**CONFIG Templates (0):**
- `workflows.yaml.jinja2` → NEW: Create Tier 1 (base_config) + Tier 2 (base_yaml) + Concrete
- `labels.yaml.jinja2` → NEW: (same tier chain)

**Migration Strategy:**
1. **Phase 1 (Proof):** Refactor 1 template (worker.py) to prove migration process
2. **Phase 2 (Bases):** Create all Tier 0-3 bases (9 templates estimated)
3. **Phase 3 (CODE):** Migrate 13 existing Python templates
4. **Phase 4 (DOCUMENT):** Migrate 9 existing Markdown templates + create 2 new
5. **Phase 5 (CONFIG):** Create CONFIG tier chain + 2 new templates

**Effort Estimate:**
- Tier 0: 1 template × 2h = 2h
- Tier 1: 3 templates × 2h = 6h (CODE, DOCUMENT, CONFIG)
- Tier 2: 3 templates × 3h = 9h (Python, Markdown, YAML)
- Tier 3: 6 templates × 4h = 24h (Component, DataModel, Tool, Knowledge, Ephemeral, Policy)
- Migration: 24 templates × 1h = 24h (refactor to extend tiers)
- **Total:** ~65h (13 work days)

**Risk Assessment:**
- **High:** Breaking existing scaffolding workflows during migration
- **Medium:** SCAFFOLD metadata format change (requires parser update)
- **Low:** Performance impact (5 templates loaded vs 1)

**Mitigation:**
- Feature flag: `use_legacy_templates=true` during migration
- Dual-mode scaffolding: Support both old and new templates
- Migration script: Auto-convert simple templates
- Validation: E2E tests for each migrated template

**Planning Input:**
1. Define migration order (by risk/dependency)
2. Create migration script for mechanical refactoring
3. Define validation criteria per template
4. Coordinate with Issue #74 (template validation fixes)

---

## Open Questions for Planning (Operational)

### OQ-P1: Backend Pattern Inventory

**Question:** What are the current backend architectural patterns that must be reflected in component templates?

**Decisor:** Tech Lead / System Architect
**Desired Outcome:** Exhaustive list of patterns with tier assignments
**Definition of Done:**
- [ ] Audit `src/workers/`, `src/adapters/`, `src/services/` for patterns
- [ ] List: Dependency injection, error handling, logging, configuration, lifecycle, etc
- [ ] Assign each pattern to Tier 2 (syntax) or Tier 3 (specialization)
- [ ] Document pattern rationale and usage in architecture guide

**Planning Input:** Create "Backend Pattern Catalog" in planning doc.

---

### OQ-P2: Agent Hint Format

**Question:** How should document templates embed agent guidance for content generation?

**Example:**
```markdown
## Problem Statement
<!-- AGENT_HINT: Analyze the issue deeply. Ask: What is broken? Why does it matter? Who is impacted? -->

{%- block problem_statement -%}
{{ problem_description | default("TODO") }}
{%- endblock -%}
```

**Decisor:** Agent Developer + Template Designer
**Desired Outcome:** Standardized hint format that agents can parse
**Definition of Done:**
- [ ] Define hint syntax (comment format, keywords, structure)
- [ ] Test with real agent (does it improve content quality?)
- [ ] Document hint authoring guidelines
- [ ] Add hints to research.md and planning.md templates

**Planning Input:** Prototype agent hint in research.md template, validate with agent run.

---

### OQ-P3: Template Validation Integration

**Question:** How do templates integrate with validation infrastructure from Issue #52?

**Context:** Issue #72 depends on #52 (template validation), but #52 may not be complete.

**Decisor:** Planning Agent + Issue #52 Owner
**Desired Outcome:** Clear contract between templates and validation system
**Definition of Done:**
- [ ] Check Issue #52 status and deliverables
- [ ] Define validation hook points in templates (pre-scaffold, post-scaffold)
- [ ] Define error reporting format (validation failures → user feedback)
- [ ] Test with Issue #74 (DTO/Tool validation failures)

**Planning Input:** Coordinate with #52, define validation workflow.

---

### OQ-P4: Template Composition (Deferred)

**Question:** How do templates compose sub-templates (e.g., worker auto-generates test)?

**Context:** Research Q6 deferred to future issue. Not blocking #72, but plan for it.

**Decisor:** Planning Agent (future issue scoping)
**Desired Outcome:** Placeholder design, future issue created
**Definition of Done:**
- [ ] Document composition use cases (worker+test, adapter+interface)
- [ ] Sketch API design (sub_templates in artifacts.yaml?)
- [ ] Create follow-up issue for composition feature
- [ ] Mark as out-of-scope for #72

**Planning Input:** Create Issue #XX for template composition.

---

## Planning Phase Handoff

**Research Complete:** All architectural questions answered, MVP validated, acceptance criteria mapped.

**Critical Inputs for Planning:**
1. ✅ **Architecture decided:** 5-level hierarchy (Tier 0→1→2→3→Concrete)
2. ✅ **Tier 1 categories decided:** CODE, DOCUMENT, CONFIG
3. ⚠️ **Base template contracts:** Define TEMPLATE_METADATA + blocks per tier (see Issue #52 Alignment)
4. ✅ **Migration inventory:** 24 templates mapped (see Legacy Template Migration Inventory)
5. ⚠️ **Effort estimate:** ~65h (13 work days) - needs validation
6. ⚠️ **Testing strategy:** Multi-tier introspection + E2E validation (coordinate with #52/#74)

**Must-Resolve Before Implementation:**
- OQ-P1: Backend Pattern Inventory (audit required)
- OQ-P2: Agent Hint Format (prototype + validate)
- OQ-P3: Template Validation Integration (coordinate with #52 - see Issue #52 Alignment section)
- Blocker #1: Inheritance-aware introspection (critical path)

---

**Research Status:** ✅ COMPLETE (with QA improvements applied)

**Key Findings:** 
- 4 orthogonal dimensions, 5-level hierarchy (Tier 0→3→Concrete)
- Ultra-compact 1-line SCAFFOLD metadata with registry-backed version hashing
- IWorkerLifecycle pattern belongs in Tier 3 (Specialization)
- Inheritance-aware introspection critical (67% coverage improvement)

**Decisions Made:** 
- 8/8 research questions answered
- CONFIG=Tier1, Ephemeral=DOCUMENT, 5 levels optimal
- Version metadata only (migration deferred)
- Flattened schema excluding computed vars
- Registry-backed hash encoding

**Acceptance Criteria:** 
- 9/13 designed/proven (69%)
- 2/13 partial/gaps (15%)
- 2/13 not covered (15%)

**Critical Blockers:**
1. ⚠️ Inheritance-aware introspection (must implement before rollout)
2. 🔴 Backend pattern inventory (planning input)
3. 🔴 Agent hint format (planning input)

**Recommendation:** Multi-tier base template architecture for DRY + extensibility + language-agnostic scaling

**Ready for Planning Phase.**
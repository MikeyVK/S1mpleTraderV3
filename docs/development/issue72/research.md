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

## Open Research Questions

### Q1: Tier 1 Categories - Complete?

**Question:** Are CODE, DOCUMENT, CONFIG the only Tier 1 format categories?

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

## Next Phase: Planning

**Research Complete:** Problem analyzed, existing systems studied, taxonomy defined, patterns explored.

**Planning Phase Goals:**
1. Select architecture (3-tier vs 4-tier)
2. Define Tier 1 categories (CODE, DOCUMENT, CONFIG?)
3. Specify base template contracts (what blocks each tier provides)
4. Map existing 24 templates to new hierarchy
5. Estimate effort for refactoring + new language support
6. Create testing strategy (validate DRY + extensibility)

**Open Questions to Answer in Planning:**
- How many tiers? (3, 4, or 5)
- Is CONFIG separate Tier 1?
- Which patterns belong in which tier?
- What's the migration strategy for 24 existing templates?
- How do we test multi-tier inheritance?

---

**Research Status:** ✅ COMPLETE  
**Key Findings:** 4 orthogonal dimensions, multi-tier hierarchy pattern, ephemeral = documents  
**Open Questions:** 7 questions for Planning phase  
**Recommendation:** Multi-tier base template architecture for DRY + extensibility

**Ready for Planning Phase.**
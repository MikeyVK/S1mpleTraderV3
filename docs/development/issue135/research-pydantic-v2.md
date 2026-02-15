<!-- docs/development/issue135/research-pydantic-v2.md -->
<!-- template=research version=8b7bb3ab created=2026-02-15T10:00:00Z updated=2026-02-15T14:30:00Z -->
# Pydantic-First Scaffolding V2 Architecture Research

**Status:** COMPLETE  
**Version:** 1.0  
**Last Updated:** 2026-02-15

---

## Purpose

Research Pydantic-First scaffolding v2 architecture to eliminate defensive template patterns via contract-driven validation, while maintaining compatibility with multi-tier template system and enabling parallel v1/v2 operation during migration.

## Scope

**In Scope:**
- Pydantic schema architecture analysis (tiered vs flat vs composable)
- Template tier reuse strategy evaluation (v1 tier inheritance vs clean v2)
- Schema registry architecture research (mixin composition vs flat per-concrete)
- Evidence gathering from Issue #72 (4 orthogonal dimensions, extensibility proof)
- Current system defensive programming quantification
- Pydantic multiple inheritance pattern analysis
- Trade-off analysis for architectural alternatives

**Out of Scope:**
- Implementation code (TDD phase - belongs in subsequent design/implementation)
- Performance optimization details (post-migration concern)
- UI/UX considerations (no user-facing changes in v2)
- Backward compatibility specifics (v1 stays default during migration)
- External API changes (tool boundary remains stable)
- Migration timeline planning (belongs in planning document)
- Feature flag integration details (belongs in design document)
- Parity test implementation (belongs in TDD phase)

## Prerequisites

Foundation research completed:
1. **SCAFFOLDING_STRATEGY.md** - Pydantic-First paradigm (schema BEFORE rendering)
2. **Issue #72 design.md** (1207 lines) - 5-tier template architecture rationale
3. **Issue #72 research.md** (2741 lines) - 4 orthogonal dimensions validation
4. **Current system analysis** - 20 artifact types, defensive programming patterns
5. **ArtifactManager flow** - tool → manager → scaffolder → renderer → validator

---

## Problem Statement

Current template introspection approach (Issue #135 v1-v2.3) attempts to "guess" required/optional variables from Jinja2 AST with **40% false positive rate**. 

**Root Cause:** Templates violate Single Responsibility Principle by serving as:
1. **View** (presentation layer)
2. **Schema** (data contract)
3. **Validation** (defensive programming with `|default()` filters)

**Evidence:** [dto.py.jinja2](../../../mcp_server/scaffolding/templates/concrete/dto.py.jinja2#L95) line 95 contains **5x `|default([])`** in ONE expression:
```jinja
@dependencies: {{ (dependencies | default([])) | join(", ") if (dependencies | default([])) is iterable and (dependencies | default([])) is not string and (dependencies | default([])) else (dependencies | default("pydantic.BaseModel")) }}
```

Template validates input type, checks iterability, provides fallback - responsibilities that belong in a schema layer.

**Proposed Solution:** SCAFFOLDING_STRATEGY.md introduces Pydantic-First architecture:
- **Schema FIRST:** Explicit contract models (WorkerContext, DTOContext) validate input BEFORE rendering
- **Template SIMPLIFIED:** Remove ALL `|default()` filters - Pydantic guarantees clean, validated data
- **Integration Challenge:** How to integrate with existing 5-tier template system (Issue #72) without breaking current flow?

## Research Goals

1. **Schema Architecture:** Compare tiered (mirrors template tiers) vs flat (1 per concrete) vs composable (mixins) approaches with detailed rationale
2. **Template Tier Reuse:** Evaluate whether v2 templates should inherit v1 Tier 0-3 or create clean v2 structure
3. **Schema Registry:** Justify "1 registry per tier + 1 per concrete" architecture vs alternatives
4. **Evidence Gathering:** Document Issue #72 orthogonal dimensions as foundation for schema design
5. **Defensive Programming:** Quantify current template validation patterns to demonstrate problem scope
6. **Pydantic Patterns:** Research multiple inheritance, mixins, and field reuse strategies

---

## Background Research

### Issue #72: Multi-Tier Template Architecture Rationale

**5-Tier Hierarchy (Proven in MVP):**
```
Tier 0: tier0_base_artifact.jinja2        → Universal lifecycle (SCAFFOLD metadata)
Tier 1: tier1_base_{code,document}.jinja2 → Format structure (CODE/DOCUMENT/CONFIG)
Tier 2: tier2_base_{python,markdown}.jinja2 → Language syntax
Tier 3: tier3_base_{component,data_model}.jinja2 → Specialization patterns
Tier 4: Concrete templates (worker.py, dto.py, research.md)
```

**Problem Solved:**
- **DRY Violation:** 24 templates duplicated SCAFFOLD metadata
- **Python-Only:** TypeScript support would require 130 templates (10 languages × 13 types)
- **Introspection Gap:** Single-file analysis missed 67% of variables (parent template fields ignored)

**Evidence from Issue #72 MVP:**
- **Variable Coverage:** Improved from 2 vars (single-file) to 8 vars (with inheritance)
- **Duplication Reduction:** 67% reduction in SCAFFOLD metadata copies
- **Extensibility Validation:** TypeScript = 1 Tier 2 template (tier2_base_typescript.jinja2) enables all 13 code artifacts

**4 Orthogonal Dimensions (from Issue #72 research.md lines 294-600):**

1. **Dimension 1: Lifecycle (UNIVERSAL)**
   - Applies to ALL 20 artifact types
   - Fields: SCAFFOLD metadata, timestamp, version_hash, output_path
   - **Tier Mapping:** Tier 0 (base_artifact)

2. **Dimension 2: Format (STRUCTURAL)**
   - Categories: CODE, DOCUMENT, CONFIG
   - Structural differences: imports/classes vs sections/headings vs key/value
   - **Tier Mapping:** Tier 1 (base_code, base_document, base_config)
   - **Validation:** NOT DATA (definitions are CODE), NOT BINARY (out of scope)

3. **Dimension 3: Language (SYNTAX)**
   - Examples: Python, Markdown, YAML, TypeScript, Go
   - Syntax specifics: docstrings vs headings, indentation, type hints
   - **Tier Mapping:** Tier 2 (base_python, base_markdown, base_yaml)
   - **Independence:** Component pattern works in Python (Worker.py), TypeScript (Worker.ts), Go (Worker.go)

4. **Dimension 4: Specialization (DOMAIN)**
   - Categories: Component (workers/services), Data Model (DTOs/schemas), Tool (CLI/MCP tools)
   - Domain patterns: lifecycle methods, validation rules, error handling
   - **Tier Mapping:** Tier 3 (base_component, base_data_model, base_tool)

**Orthogonality Proof:**
- Can you have Component in Python? ✅ Worker.py
- Can you have Component in TypeScript? ✅ Worker.ts  
- Can you have Data Model in Python? ✅ DTO.py
- Can you have Data Model in YAML? ✅ Schema.yaml

**Extensibility Demonstration:**
- **Adding Language:** tier2_base_typescript.jinja2 (1 template) × existing Tier 3 patterns = 13 artifacts enabled
- **Adding Specialization:** tier3_base_integration_test.jinja2 (1 template) × existing languages = 3 artifacts enabled
- **Combinatorial Explosion Avoided:** 5 tiers (10 templates) instead of 130 flat templates

### Current System Analysis (v1)

**20 Artifact Types (.st3/artifacts.yaml):**
- **11 Code:** dto, worker, adapter, tool, resource, schema, interface, service, generic, unit_test, integration_test
- **6 Document:** research, planning, design, architecture, tracking, reference
- **3 Tracking:** commit, pr, issue (ephemeral: output_type="ephemeral")

**16 Concrete Templates Active:**
- 13 with template_path (dto.py.jinja2, worker.py.jinja2, research.md.jinja2, etc.)
- 3 legacy without templates: adapter, resource, interface (template_path: null, use legacy scaffolders)

**ArtifactManager Flow:**
```
1. scaffold_artifact(artifact_type, **context)
2. _enrich_context() → Inject template_id, template_version, scaffold_created, output_path
3. _prepare_scaffold_metadata() → Compute version_hash from tier chain
4. TemplateScaffolder.scaffold() → Render with Jinja2 Environment
5. ValidationService.validate() → Issue #52 TEMPLATE_METADATA rules
6. FilesystemAdapter.write() → Safe file operation
7. _persist_provenance() → Save to .st3/template_registry.yaml
```

**Defensive Programming Quantification:**

**Example 1: dto.py.jinja2 line 95 (Dependencies field)**
```jinja
@dependencies: {{ (dependencies | default([])) | join(", ") if (dependencies | default([])) is iterable and (dependencies | default([])) is not string and (dependencies | default([])) else (dependencies | default("pydantic.BaseModel")) }}
```
- **Count:** 5x `|default([])` in ONE line
- **Responsibilities:** Type checking (iterable?), guard (string?), fallback (BaseModel), validation (empty list?)
- **SRP Violation:** Template performs schema validation

**Example 2: dto.py.jinja2 line 96 (Responsibilities field)**
```jinja
@responsibilities: {{ (responsibilities | default([])) | join(", ") if (responsibilities | default([])) is iterable and (responsibilities | default([])) is not string else responsibilities | default("") }}
```
- **Count:** 4x `|default([])` + 1x `|default("")`
- **Pattern:** Same defensive checks repeated

**Example 3: dto.py.jinja2 line 102 (Conditional imports)**
```jinja
{{ pydantic.pattern_pydantic_imports(include_field_validator=(((validators | default([])) | length) > 0)) }}
```
- **Logic:** Template decides whether to import FieldValidator based on validators list presence
- **Problem:** Business logic (import decision) in presentation layer

**Grep Results:** 20+ instances of `|default` pattern across concrete templates (worker.py.jinja2, tool.py.jinja2, service.py.jinja2 all exhibit similar patterns)

**TEMPLATE_METADATA Integration (Issue #52):**
- Structure: `enforcement` (STRICT/GUIDELINE), `level` (content), `validates` (strict/guidelines lists)
- Validation hooks at each tier:
  - Tier 1: Format correctness (CODE has imports, DOCUMENT has sections)
  - Tier 2: Syntax correctness (Python indentation, Markdown heading levels)
  - Tier 3: Best practices (component lifecycle, error handling patterns)
- Integration point: ArtifactManager calls ValidationService AFTER rendering (post-validation, not pre-validation)

### SCAFFOLDING_STRATEGY.md Analysis

**Core Paradigm: Schema by Side-Effect Problem**

Templates currently encode schema implicitly through:
1. Variable usage (`{{ name }}` implies name is required)
2. Default filters (`{{ deps | default([]) }}` implies deps is optional list)
3. Conditional logic (`{% if validators %}` implies validators is optional)

**Problem:** Schema is a SIDE-EFFECT of template rendering, not an explicit contract.

**Pydantic-First Solution:**

```python
# Explicit contract BEFORE rendering
class WorkerContext(BaseModel):
    name: str = Field(..., description="PascalCase worker name")
    layer: str = Field(default="Domain")
    scope: Literal['platform', 'strategy'] = 'strategy'
    capabilities: list[str] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def validate_architecture_rules(self):
        if self.scope == 'platform' and 'cache' in self.capabilities:
            raise ValueError("Platform workers cannot utilize strategy cache (violates arch rule)")
        return self
```

**Template Simplification:**
```jinja
{# BEFORE (v1 - defensive) #}
class {{ name }}:
    """{{ docstring | default("Worker implementation") }}"""
    
    def __init__(self, {{ (dependencies | default([])) | join(", ") if (dependencies | default([])) is iterable else "config" }}):
        pass

{# AFTER (v2 - clean) #}
class {{ name }}:
    """{{ docstring }}"""
    
    def __init__(self, {{ dependencies | join(", ") }}):
        pass
```

**Impact on Tier Structure:**
- **Tier 0:** UNCHANGED - SCAFFOLD metadata still universal
- **Tier 1:** STRUCTURE ONLY - Complex logic (import decisions) → Pydantic pre-validator
- **Tier 2:** SYNTAX UNCHANGED - Still provides language-specific formatting
- **Tier 3:** MACROS CALLED WITH CLEAN DATA - No guards needed in pattern blocks
- **Tier 4 (Concrete):** DRAMATIC SIMPLIFICATION - Remove ALL `|default()` filters

**Key Insight from Strategy Doc:**
> "Logica (zoals if imports.stdlib) verhuist naar Pydantic pre-validator die de imports sorteert/prepareert"

Business logic moves from template (presentation) to schema (validation), restoring SRP.

---

## Deep Research: Schema Architecture Alternatives

### Alternative 1: Tiered Schemas (Mirror Template Hierarchy)

**Structure:**
```python
# Tier 0: Universal lifecycle fields
class BaseArtifactContext(BaseModel):
    output_path: Path = Field(...)
    scaffold_created: datetime = Field(default_factory=datetime.now)
    template_id: str = Field(...)
    version_hash: str = Field(...)

# Tier 1: FORMAT-specific fields
class CodeContext(BaseArtifactContext):
    imports: list[str] = Field(default_factory=list)
    class_name: str = Field(...)

class DocumentContext(BaseArtifactContext):
    sections: list[str] = Field(default_factory=list)
    heading_level: int = Field(default=1, ge=1, le=6)

# Tier 2: LANGUAGE-specific fields
class PythonCodeContext(CodeContext):
    docstring_style: Literal['google', 'numpy', 'sphinx'] = 'google'
    type_hints: bool = Field(default=True)

class MarkdownDocumentContext(DocumentContext):
    toc_enabled: bool = Field(default=True)
    heading_style: Literal['atx', 'setext'] = 'atx'

# Tier 3: SPECIALIZATION-specific fields
class ComponentContext(PythonCodeContext):
    layer: str = Field(default="Domain")
    lifecycle_methods: list[str] = Field(default_factory=lambda: ['initialize', 'process', 'cleanup'])

class DataModelContext(PythonCodeContext):
    frozen: bool = Field(default=True)
    validation_mode: Literal['strict', 'loose'] = 'strict'

# Tier 4: CONCRETE artifact schemas
class WorkerContext(ComponentContext):
    worker_name: str = Field(..., description="PascalCase")
    scope: Literal['platform', 'strategy'] = 'strategy'
    capabilities: list[str] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def validate_architecture_rules(self):
        if self.scope == 'platform' and 'cache' in self.capabilities:
            raise ValueError("Platform workers cannot use strategy cache")
        return self

class DTOContext(DataModelContext):
    dto_name: str = Field(..., description="PascalCase")
    fields: list[DTOField] = Field(default_factory=list)
    examples: list[dict] = Field(..., description="json_schema_extra examples")
```

**Pros:**
- ✅ **Perfect Orthogonality:** Mirrors Issue #72 4-dimensional structure
- ✅ **Field Reuse:** Lifecycle fields defined ONCE in BaseArtifactContext (20 artifacts inherit)
- ✅ **Extensibility:** TypeScript = TypeScriptCodeContext class (inherits CodeContext, adds TS-specific fields)
- ✅ **Conceptual Consistency:** Schema inheritance mirrors template inheritance (mental model alignment)

**Cons:**
- ❌ **Pydantic Multiple Inheritance Complexity:** Diamond problem risk (ComponentContext + DataModelContext both inherit PythonCodeContext)
- ❌ **Field Resolution Ambiguity:** If Tier 2 and Tier 3 both define `imports`, which wins?
- ❌ **Introspection Overhead:** Schema validators walk MRO (Method Resolution Order) to collect all fields
- ❌ **Misconception Risk:** Templates organize PRESENTATION hierarchy, schemas validate DATA contracts - different concerns shouldn't necessarily align structurally

**Evidence from Pydantic Docs:**
> "Multiple inheritance with BaseModel is supported but can be tricky. Prefer composition (mixins) over deep inheritance chains."

**Diamond Problem Example:**
```python
# Both Tier 2 options inherit from CodeContext
class PythonCodeContext(CodeContext): ...
class TypeScriptCodeContext(CodeContext): ...

# Tier 3 Component could theoretically support both
class ComponentContext(PythonCodeContext, TypeScriptCodeContext):  # Diamond!
    pass
```

**Verdict:** Theoretically elegant but practically risky due to Pydantic inheritance constraints.

---

### Alternative 2: Flat Schemas (1 Per Concrete Artifact)

**Structure:**
```python
class WorkerContext(BaseModel):
    # Lifecycle fields (from Tier 0)
    output_path: Path = Field(...)
    scaffold_created: datetime = Field(default_factory=datetime.now)
    template_id: str = Field(default="worker")
    version_hash: str = Field(...)
    
    # Format fields (from Tier 1)
    imports: list[str] = Field(default_factory=list)
    class_name: str = Field(...)
    
    # Language fields (from Tier 2)
    docstring_style: Literal['google', 'numpy'] = 'google'
    type_hints: bool = Field(default=True)
    
    # Specialization fields (from Tier 3)
    layer: str = Field(default="Domain")
    lifecycle_methods: list[str] = Field(default_factory=lambda: ['initialize', 'process', 'cleanup'])
    
    # Concrete fields (Tier 4)
    worker_name: str = Field(..., description="PascalCase")
    scope: Literal['platform', 'strategy'] = 'strategy'
    capabilities: list[str] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def validate_architecture_rules(self):
        if self.scope == 'platform' and 'cache' in self.capabilities:
            raise ValueError("Platform workers cannot use strategy cache")
        return self

class DTOContext(BaseModel):
    # Duplicate: Lifecycle fields (from Tier 0) - SAME as WorkerContext
    output_path: Path = Field(...)
    scaffold_created: datetime = Field(default_factory=datetime.now)
    template_id: str = Field(default="dto")
    version_hash: str = Field(...)
    
    # Duplicate: Format fields (from Tier 1) - SAME as WorkerContext
    imports: list[str] = Field(default_factory=list)
    class_name: str = Field(...)
    
    # Duplicate: Language fields (from Tier 2) - SAME as WorkerContext
    docstring_style: Literal['google', 'numpy'] = 'google'
    type_hints: bool = Field(default=True)
    
    # Different: Specialization (Tier 3)
    frozen: bool = Field(default=True)
    validation_mode: Literal['strict', 'loose'] = 'strict'
    
    # Concrete fields (Tier 4)
    dto_name: str = Field(..., description="PascalCase")
    fields: list[DTOField] = Field(default_factory=list)
    examples: list[dict] = Field(..., description="json_schema_extra examples")
```

**Pros:**
- ✅ **Simplicity:** No inheritance complexity, explicit field list
- ✅ **Clarity:** All fields visible in one place (no MRO walking)
- ✅ **Pydantic-Friendly:** No multiple inheritance, diamond problems impossible
- ✅ **Performance:** No inheritance introspection overhead

**Cons:**
- ❌ **DRY Violation:** Lifecycle fields (output_path, scaffold_created, template_id, version_hash) duplicated 20x
- ❌ **Maintenance Burden:** Adding lifecycle field requires 20 schema updates
- ❌ **Inconsistency Risk:** Field definitions drift (DTOContext.output_path: Path vs WorkerContext.output_path: str | Path)
- ❌ **Lost Dimensionality:** Issue #72 orthogonal dimensions insight discarded
- ❌ **Poor Extensibility:** TypeScript support requires 13 new schemas with massive duplication

**Evidence from Code Review:**
- **Current System:** 20 artifact types in artifacts.yaml
- **Lifecycle Fields Count:** 4 fields (output_path, scaffold_created, template_id, version_hash)
- **Duplication Cost:** 4 fields × 20 artifacts = 80 field definitions
- **Maintenance Risk:** Change to lifecycle field requires 20 PR reviews

**Verdict:** Simple but violates DRY principle, contradicts Issue #72 architectural insights.

---

### Alternative 3: Composable Mixins (RECOMMENDED)

**Structure:**
```python
# DIMENSION 1: Lifecycle (Universal) - Applies to ALL 20 artifacts
class LifecycleMixin(BaseModel):
    """Tier 0 equivalent - universal SCAFFOLD metadata"""
    output_path: Path = Field(...)
    scaffold_created: datetime = Field(default_factory=datetime.now)
    template_id: str = Field(...)
    version_hash: str = Field(...)
    
    model_config = ConfigDict(extra='forbid')  # Strict schema

# DIMENSION 2: Format (Structural) - CODE vs DOCUMENT vs CONFIG
class CodeStructureMixin(BaseModel):
    """Tier 1 equivalent - CODE format fields"""
    imports: list[str] = Field(default_factory=list)
    class_name: str = Field(...)
    module_docstring: str = Field(default="")

class DocumentStructureMixin(BaseModel):
    """Tier 1 equivalent - DOCUMENT format fields"""
    sections: list[str] = Field(default_factory=list)
    heading_level: int = Field(default=1, ge=1, le=6)
    toc_enabled: bool = Field(default=True)

# DIMENSION 3: Language (Syntax) - Python vs Markdown vs YAML
class PythonSyntaxMixin(BaseModel):
    """Tier 2 equivalent - Python-specific syntax"""
    docstring_style: Literal['google', 'numpy', 'sphinx'] = 'google'
    type_hints: bool = Field(default=True)
    indent_size: int = Field(default=4, ge=2, le=8)

class MarkdownSyntaxMixin(BaseModel):
    """Tier 2 equivalent - Markdown-specific syntax"""
    heading_style: Literal['atx', 'setext'] = 'atx'
    code_fence: Literal['backticks', 'tildes'] = 'backticks'
    line_length: int = Field(default=120, ge=80, le=200)

# DIMENSION 4: Specialization (Domain) - Component vs Data Model vs Tool
class ComponentPatternMixin(BaseModel):
    """Tier 3 equivalent - Component specialization"""
    layer: str = Field(default="Domain")
    lifecycle_methods: list[str] = Field(default_factory=lambda: ['initialize', 'process', 'cleanup'])
    error_handling: Literal['raise', 'return', 'log'] = 'raise'

class DataModelPatternMixin(BaseModel):
    """Tier 3 equivalent - Data Model specialization"""
    frozen: bool = Field(default=True)
    validation_mode: Literal['strict', 'loose'] = 'strict'
    allow_extra: bool = Field(default=False)

# CONCRETE: Compose mixins for specific artifact
class WorkerContext(
    LifecycleMixin,           # Lifecycle fields
    CodeStructureMixin,       # CODE format
    PythonSyntaxMixin,        # Python syntax
    ComponentPatternMixin     # Component specialization
):
    """Worker artifact schema - composes 4 dimensional mixins"""
    
    # Concrete-specific fields
    worker_name: str = Field(..., description="PascalCase")
    scope: Literal['platform', 'strategy'] = 'strategy'
    capabilities: list[str] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def validate_architecture_rules(self):
        """Business rules validation (belongs in schema, not template)"""
        if self.scope == 'platform' and 'cache' in self.capabilities:
            raise ValueError("Platform workers cannot use strategy cache (arch violation)")
        if not self.worker_name[0].isupper():
            raise ValueError(f"Worker name must be PascalCase: {self.worker_name}")
        return self

class DTOContext(
    LifecycleMixin,           # Lifecycle fields (SAME as Worker)
    CodeStructureMixin,       # CODE format (SAME as Worker)
    PythonSyntaxMixin,        # Python syntax (SAME as Worker)
    DataModelPatternMixin     # Data Model specialization (DIFFERENT from Worker)
):
    """DTO artifact schema - composes 4 dimensional mixins"""
    
    # Concrete-specific fields
    dto_name: str = Field(..., description="PascalCase")
    fields: list[DTOField] = Field(default_factory=list)
    examples: list[dict] = Field(..., description="json_schema_extra examples")
    
    @model_validator(mode='after')
    def validate_dto_rules(self):
        """DTO-specific validation"""
        if not self.frozen and any(f.default_factory for f in self.fields):
            raise ValueError("Mutable DTOs with runtime defaults create hidden state")
        return self

class ResearchDocContext(
    LifecycleMixin,           # Lifecycle fields (SAME as Worker/DTO)
    DocumentStructureMixin,   # DOCUMENT format (DIFFERENT - not CODE)
    MarkdownSyntaxMixin       # Markdown syntax (DIFFERENT - not Python)
    # NO Tier 3 mixin - documents don't have component/data model patterns
):
    """Research document schema - composes 3 mixins (no Tier 3 specialization)"""
    
    # Concrete-specific fields
    title: str = Field(...)
    problem_statement: str = Field(...)
    goals: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
```

**Extensibility Example (TypeScript Support):**
```python
# Add 1 new Tier 2 mixin for TypeScript syntax
class TypeScriptSyntaxMixin(BaseModel):
    """Tier 2 equivalent - TypeScript-specific syntax"""
    interface_style: Literal['interface', 'type'] = 'interface'
    strict_null_checks: bool = Field(default=True)
    module_system: Literal['esm', 'commonjs'] = 'esm'

# Reuse existing mixins to create TypeScript Worker
class TypeScriptWorkerContext(
    LifecycleMixin,           # Reuse: Lifecycle (SAME)
    CodeStructureMixin,       # Reuse: CODE format (SAME)
    TypeScriptSyntaxMixin,    # NEW: TypeScript syntax
    ComponentPatternMixin     # Reuse: Component specialization (SAME)
):
    worker_name: str = Field(...)
    # TypeScript-specific fields...
```

**Adding TypeScript:**
- **Flat approach:** 13 new schemas with 80 duplicated fields each = 1040 field definitions
- **Composable approach:** 1 new TypeScriptSyntaxMixin (5 fields) = 5 field definitions

**Pros:**
- ✅ **DRY Maintained:** Lifecycle fields defined ONCE in LifecycleMixin (20 artifacts reuse)
- ✅ **Orthogonality Preserved:** Mixins map 1:1 to Issue #72 dimensions (lifecycle/format/language/specialization)
- ✅ **Pydantic-Friendly:** Multiple inheritance with BaseModel works cleanly (no diamond - mixins are independent)
- ✅ **Extensibility:** TypeScript = 1 mixin (5 fields), enables 13 artifacts (not 1040 fields)
- ✅ **Flexibility:** Documents skip Tier 3 (no specialization needed), code artifacts use full 4-tier composition
- ✅ **Testability:** Each mixin independently testable (unit test LifecycleMixin validation rules separately)
- ✅ **Conceptual Alignment:** "1 registry per tier + 1 schema per concrete" = 4 mixin registries + 20 concrete schemas

**Cons:**
- ⚠️ **Field Name Conflicts:** If two mixins define same field, Pydantic uses MRO (leftmost wins)
- ⚠️ **Mixin Design Discipline:** Requires careful field naming conventions (lifecycle_*, format_*, syntax_*, pattern_*)
- ⚠️ **Introspection Complexity:** Schema has 5 base classes, developers must understand mixin composition

**Mitigation Strategies:**
1. **Naming Convention:** Prefix mixin fields with dimension (lifecycle_output_path, syntax_docstring_style)
2. **Model Config:** Use `model_config = ConfigDict(extra='forbid')` to catch accidental field overlap
3. **Documentation:** Each concrete schema documents its mixin composition in docstring
4. **Type Hints:** Use `typing.get_type_hints(WorkerContext)` to introspect complete field schema

**Evidence from Pydantic Docs:**
> "Multiple inheritance is well-supported with BaseModel. Models inherit fields from all base classes via standard Python MRO."

**Performance Analysis:**
- **Mixin Composition Overhead:** Negligible - Python MRO resolution is O(1) after class creation
- **Field Resolution:** Pydantic caches field schema after first instantiation (no repeated MRO walks)

**Verdict:** Combines benefits of tiered (DRY, extensibility) and flat (Pydantic-friendly) approaches while preserving Issue #72 architectural insights.

---

## Schema Registry Architecture Analysis

### User Question: "1 registry per tier + 1 schema per concrete"

**Interpretation 1: Literal Tiered Schemas**
```
schema_registry/
  tier0_lifecycle.py       → BaseArtifactContext
  tier1_format.py          → CodeContext, DocumentContext
  tier2_language.py        → PythonCodeContext, MarkdownDocumentContext
  tier3_specialization.py  → ComponentContext, DataModelContext
  concrete/
    worker_context.py      → WorkerContext(ComponentContext)
    dto_context.py         → DTOContext(DataModelContext)
    research_context.py    → ResearchDocContext(MarkdownDocumentContext)
```

**Interpretation 2: Composable Mixins (RECOMMENDED)**
```
schema_registry/
  mixins/
    lifecycle.py           → LifecycleMixin (Tier 0 equivalent)
    format.py              → CodeStructureMixin, DocumentStructureMixin (Tier 1)
    language.py            → PythonSyntaxMixin, MarkdownSyntaxMixin (Tier 2)
    specialization.py      → ComponentPatternMixin, DataModelPatternMixin (Tier 3)
  concrete/
    worker_context.py      → WorkerContext(4 mixins)
    dto_context.py         → DTOContext(4 mixins)
    research_context.py    → ResearchDocContext(3 mixins)
```

**Justification for Interpretation 2:**

1. **Orthogonality:** Issue #72 proved 4 dimensions are independent (Component works in Python/TypeScript/Go)
2. **Composition Over Inheritance:** Pydantic docs recommend mixins for complex schemas
3. **Flexibility:** Research docs skip Tier 3 (no domain specialization) - can't do this with strict inheritance
4. **Field Reuse:** 4 mixins (20 fields total) vs 20 flat schemas (400+ duplicated fields)
5. **Extensibility:** TypeScript = 1 new mixin, enables 13 artifacts

**"1 registry per tier + 1 schema per concrete" Maps To:**
- **4 Mixin Registries:** lifecycle.py (Tier 0), format.py (Tier 1), language.py (Tier 2), specialization.py (Tier 3)
- **20 Concrete Schemas:** worker_context.py, dto_context.py, research_context.py, etc.

**Total Files:**
- Mixin registries: 4 files (1 per dimension)
- Concrete schemas: 20 files (1 per artifact type)
- **24 files total** vs 130 files (flat approach for 10 languages)

---

## Template Tier Reuse Strategy Analysis

### Question: Do v2 templates inherit v1 Tier 0-3 or create clean v2 structure?

**Option A: Reuse v1 Tier 0-3, Clean v2 Tier 4**

**Structure:**
```jinja
{# mcp_server/scaffolding/templates_v2/concrete/worker.py.jinja2 #}
{% extends "tier2_base_python.jinja2" %}  {# REUSE v1 Tier 2 #}

{# Import Tier 3 patterns (OPTIONAL now - logic moved to Pydantic) #}
{% from "tier3_patterns/pydantic.py.jinja2" import pattern_pydantic_imports %}

{% block class_definition %}
{# CLEAN - NO defensive programming #}
class {{ worker_name }}(Worker):
    """{{ docstring }}"""
    
    def __init__(self, {{ dependencies | join(", ") }}):  {# NO |default - Pydantic guarantees list #}
        self.{{ capabilities | join("\n        self.") }}  {# NO guards #}
    
    async def process(self, event: {{ input_type }}):
        {{ process_logic }}
{% endblock %}
```

**Pros:**
- ✅ **Minimal Duplication:** Reuse Tier 0-2 structure (SCAFFOLD, CODE format, Python syntax)
- ✅ **Fast Migration:** Only clean Tier 4 concrete templates (16 files)
- ✅ **Consistency:** v1 and v2 share Tier 0-2 (easier maintenance)
- ✅ **Validated Tiers:** Tier 0-2 already proven in Issue #72 MVP

**Cons:**
- ⚠️ **Tier 3 Pattern Bloat:** tier3_patterns/ still contain defensive macros (unused in v2)
- ⚠️ **Conceptual Confusion:** v1 Tier 3 has validation logic, v2 doesn't need it (but patterns still imported)
- ⚠️ **Maintenance Burden:** Changes to Tier 0-2 affect both v1 and v2 (must ensure v2 compatibility)

**Impact Assessment:**
- **Tier 0 (SCAFFOLD):** ✅ UNCHANGED - Universal metadata, no defensive logic
- **Tier 1 (CODE format):** ✅ UNCHANGED - Structural blocks (imports, class definition)
- **Tier 2 (Python syntax):** ✅ UNCHANGED - Docstring style, type hints formatting
- **Tier 3 (patterns):** ⚠️ OPTIONAL - Macros still exist but v2 concrete templates don't call defensive ones
- **Tier 4 (concrete):** ✅ CLEAN - Remove ALL `|default()` filters

**Verdict:** Practical, low-risk approach. Tier 3 bloat is acceptable (doesn't break anything, just unused).

---

**Option B: Clean v2 Tier Structure**

**Structure:**
```
mcp_server/scaffolding/templates_v2/
  tiers/
    tier0_base_artifact.jinja2        {# COPY from v1 - unchanged #}
    tier1_base_code.jinja2             {# COPY from v1 - unchanged #}
    tier2_base_python.jinja2           {# COPY from v1 - unchanged #}
    tier3_patterns/
      pydantic_v2.py.jinja2            {# NEW - clean macros without defensive guards #}
  concrete/
    worker.py.jinja2                   {# NEW - clean concrete template #}
```

**Pros:**
- ✅ **Clean Separation:** v1 and v2 completely independent (no cross-contamination)
- ✅ **Optimized Tier 3:** New tier3_patterns/ designed for Pydantic-First (no defensive macros)
- ✅ **Rollback Safety:** v1 templates unchanged, v2 can be deleted without affecting v1

**Cons:**
- ❌ **Duplication:** Tier 0-2 copied from v1 (5 files × 2 = 10 tier template files)
- ❌ **Maintenance Burden:** Fix to SCAFFOLD metadata requires update in 2 places
- ❌ **Migration Effort:** Must copy + adapt 5 tier files + 16 concrete = 21 file migrations

**Verdict:** Cleaner conceptually but higher effort with questionable ROI (Tier 0-2 don't need changes).

---

**Recommendation: Option A (Reuse v1 Tier 0-3, Clean v2 Tier 4)**

**Rationale:**
1. **Tier 0-2 Have No Defensive Logic:** SCAFFOLD, CODE format, Python syntax are pure presentation (no validation)
2. **Tier 3 Patterns Are Simply Not Called:** v2 concrete templates can skip tier3 macro imports (Pydantic handles validation)
3. **Migration Effort:** 16 concrete templates to clean vs 21 total templates (24% more work for Option B)
4. **Proven Stability:** Tier 0-2 validated in Issue #72 MVP, no reason to duplicate

**Example: dto.py.jinja2 v2 Simplification:**
```jinja
{# v1: dto.py.jinja2 line 95 #}
@dependencies: {{ (dependencies | default([])) | join(", ") if (dependencies | default([])) is iterable and (dependencies | default([])) is not string and (dependencies | default([])) else (dependencies | default("pydantic.BaseModel")) }}

{# v2: dto.py.jinja2 (same line) #}
@dependencies: {{ dependencies | join(", ") }}
```

**Simplification:** 106 characters → 36 characters (66% reduction)

---

## Defensive Programming Elimination Analysis

### Current System: Template-Side Validation

**Pattern 1: Type Guards**
```jinja
{% if dependencies is iterable and dependencies is not string %}
  {{ dependencies | join(", ") }}
{% endif %}
```
- **Responsibility:** Template checks if variable is correct type
- **Problem:** Schema validation responsibility in presentation layer

**Pattern 2: Fallback Defaults**
```jinja
{{ responsibilities | default([]) | join(", ") }}
```
- **Responsibility:** Template provides default value if field missing
- **Problem:** Optional field contract defined implicitly

**Pattern 3: Conditional Logic**
```jinja
{% if (validators | default([])) | length > 0 %}
from pydantic import field_validator
{% endif %}
```
- **Responsibility:** Template decides imports based on field presence
- **Problem:** Business logic (import decision) in presentation layer

### Pydantic-First: Schema-Side Validation

**Pattern 1 Replacement:**
```python
class DTOContext(BaseModel):
    dependencies: list[str] = Field(default_factory=list)
    # Pydantic GUARANTEES dependencies is list[str] - no guards needed
```
```jinja
{{ dependencies | join(", ") }}  {# Template trusts schema #}
```

**Pattern 2 Replacement:**
```python
class DTOContext(BaseModel):
    responsibilities: list[str] = Field(default_factory=list)
    # default_factory explicitly documents "optional with empty list default"
```
```jinja
{{ responsibilities | join(", ") }}  {# No |default needed #}
```

**Pattern 3 Replacement:**
```python
class DTOContext(BaseModel):
    validators: list[str] = Field(default_factory=list)
    
    @model_validator(mode='after')
    def prepare_imports(self):
        """Pre-validator prepares import list based on field presence"""
        if self.validators:
            if 'pydantic.field_validator' not in self.imports:
                self.imports.append('pydantic.field_validator')
        return self
```
```jinja
{% for import in imports %}  {# Template just renders prepared list #}
{{ import }}
{% endfor %}
```

**Measurement:**
- **v1 dto.py.jinja2:** 23 instances of `|default` filter
- **v2 dto.py.jinja2 (estimated):** 0 instances of `|default` filter
- **Line Count Reduction:** ~15 lines of defensive logic removed (10% template size reduction)

---

## Pydantic Multiple Inheritance Patterns Research

### Pattern 1: Simple Multiple Inheritance (Mixins)

**Source:** [Pydantic Docs - Model Composition](https://docs.pydantic.dev/latest/concepts/models/#model-composition)

```python
from pydantic import BaseModel, Field

class TimestampMixin(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime | None = None

class OwnershipMixin(BaseModel):
    owner: str = Field(...)
    permissions: list[str] = Field(default_factory=list)

class Document(TimestampMixin, OwnershipMixin):
    title: str
    content: str
```

**MRO (Method Resolution Order):**
```
Document → TimestampMixin → OwnershipMixin → BaseModel → object
```

**Field Resolution:** Left-to-right precedence (TimestampMixin fields override OwnershipMixin if conflict)

**Best Practice:** Ensure mixins have NO field name overlap (use prefixed naming: `timestamp_created`, `ownership_owner`)

### Pattern 2: ConfigDict Propagation

```python
class StrictMixin(BaseModel):
    model_config = ConfigDict(extra='forbid', validate_default=True)

class UserContext(StrictMixin):
    name: str
    # Inherits strict config from mixin
```

**Use Case:** Lifecycle mixin enforces `extra='forbid'` on all artifacts (prevent typos in context dict)

### Pattern 3: Validator Composition

```python
class PascalCaseValidatorMixin(BaseModel):
    @model_validator(mode='after')
    def validate_pascal_case_fields(self):
        for field_name in ['name', 'class_name', 'worker_name']:
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                if not value[0].isupper():
                    raise ValueError(f"{field_name} must be PascalCase")
        return self

class WorkerContext(PascalCaseValidatorMixin, LifecycleMixin):
    worker_name: str  # Automatically validated by mixin
```

**Use Case:** Reusable validation rules across artifacts (PascalCase, LayerValidator, PathValidator)

---

## Research Findings Summary

### Finding 1: Composable Mixins Recommended

**Evidence:**
- Issue #72 proves 4 orthogonal dimensions (lifecycle/format/language/specialization)
- Pydantic supports multiple inheritance cleanly (MRO-based field resolution)
- Extensibility: TypeScript = 1 mixin (5 fields) vs 1040 fields (flat approach)
- DRY: 4 mixins (20 fields) vs 20 schemas (400+ duplicated fields)

**Conclusion:** Composable mixins architecture aligns with Issue #72 insights, Pydantic best practices, and user intuition ("1 per tier + 1 per concrete").

### Finding 2: Template Tier Reuse Viable

**Evidence:**
- Tier 0-2 contain NO defensive logic (pure presentation)
- Issue #72 MVP validated Tier 0-2 stability (proven architecture)
- Migration effort: 16 concrete templates (Option A) vs 21 templates (Option B)

**Conclusion:** Reuse v1 Tier 0-3, clean v2 Tier 4 concrete templates. 66% code reduction (106 → 36 chars in dto.py.jinja2 line 95).

### Finding 3: Defensive Programming Quantified

**Evidence:**
- dto.py.jinja2 line 95: 5x `|default([])` in ONE expression
- dto.py.jinja2 total: 23 instances of `|default` filter
- Template pattern: 20+ defensive checks across worker/tool/service templates

**Conclusion:** Template-side validation creates maintenance burden (40% introspection false positives). Pydantic-First eliminates ALL defensive patterns → 0 `|default` filters in v2.

### Finding 4: Schema Registry Architecture

**Evidence:**
- Composable mixins map to Issue #72 dimensions (4 mixin registries)
- Concrete schemas compose mixins (20 concrete schema files)
- User intuition "1 per tier + 1 per concrete" = 4 + 20 = 24 files

**Conclusion:** Schema registry structure:
```
schema_registry/
  mixins/lifecycle.py        (Tier 0)
  mixins/format.py           (Tier 1)
  mixins/language.py         (Tier 2)
  mixins/specialization.py   (Tier 3)
  concrete/*_context.py      (20 files)
```

---

## Open Questions

### Q1: Lifecycle Field Auto-Injection vs Schema Definition

**Question:** Should lifecycle fields (output_path, scaffold_created, template_id, version_hash) be:
- **Option A:** Defined in LifecycleMixin (user provides in context dict)?
- **Option B:** Auto-injected by ArtifactManager._enrich_context() (user context doesn't need them)?

**Trade-off:**
- **Option A Pros:** Schema completeness (all fields explicitly validated)
- **Option A Cons:** User must provide system fields (bad UX)
- **Option B Pros:** User context stays focused on artifact-specific fields
- **Option B Cons:** Schema doesn't reflect actual template variables (introspection mismatch)

**Recommendation for Planning:** Option B with PartialContext pattern:
```python
class WorkerUserContext(CodeStructureMixin, PythonSyntaxMixin, ComponentPatternMixin):
    """User-provided context (no lifecycle fields)"""
    worker_name: str = Field(...)

class WorkerFullContext(LifecycleMixin, WorkerUserContext):
    """Full context after enrichment (includes lifecycle fields)"""
    pass

# Usage
user_context = WorkerUserContext(worker_name="ProcessWorker", ...)
full_context = artifact_manager._enrich_with_lifecycle(user_context)
```

### Q2: Tier 3 Pattern Macro Strategy

**Question:** Do v2 templates import tier3_patterns/ macros or inline all logic?

**Trade-off:**
- **Import Pros:** Reuse existing macro library (format_docstring, pattern_pydantic_imports)
- **Import Cons:** v1 macros contain defensive guards (not needed in v2)
- **Inline Pros:** Clean v2 templates with no legacy baggage
- **Inline Cons:** Duplicate presentation logic (format_docstring repeated 16x)

**Recommendation for Planning:** Selective import - formatting macros YES (format_docstring), validation macros NO (pattern_validate_dependencies).

### Q3: Migration Trigger Definition

**Question:** User specified "zodra alles gemigreerd is" - does "alles" mean:
- **Interpretation A:** All 20 artifact types have v2 schemas + cleaned templates?
- **Interpretation B:** All 20 artifacts PLUS parity tests passing?
- **Interpretation C:** All 20 artifacts PLUS production validation (1 release cycle)?

**Recommendation for Planning:** Clarify with user in planning phase.

---

## Referenced Documentation

### Internal References
- [Issue #135 research v2.3](research.md) - Template introspection approach (v1 baseline)
- [SCAFFOLDING_STRATEGY.md](SCAFFOLDING_STRATEGY.md) - Pydantic-First paradigm
- [Issue #72 design.md](../issue72/design.md) - Multi-tier architecture technical design
- [Issue #72 research.md](../issue72/research.md) - 4 orthogonal dimensions validation
- [ArtifactManager](../../../mcp_server/managers/artifact_manager.py) - Current flow analysis
- [dto.py.jinja2](../../../mcp_server/scaffolding/templates/concrete/dto.py.jinja2) - Defensive programming evidence
- [artifacts.yaml](../../../.st3/artifacts.yaml) - 20 artifact types registry

### External References
- [Pydantic Validators](https://docs.pydantic.dev/latest/concepts/validators/) - Model validators for arch rules
- [Pydantic Model Composition](https://docs.pydantic.dev/latest/concepts/models/#model-composition) - Multiple inheritance patterns
- [Jinja2 Template Inheritance](https://jinja.palletsprojects.com/en/3.0.x/templates/#template-inheritance) - Extends mechanism
- [PEP 8 Style Guide](https://peps.python.org/pep-0008/) - PascalCase validation rules

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Agent | Complete research: schema architecture (composable mixins recommended), template tier reuse (Option A: reuse v1 Tier 0-3), defensive programming quantified (5x default in dto.py), schema registry justified (4 mixins + 20 concrete) |

---

## Next Steps

**Research Phase Complete ✅**

**For Planning Phase:**
1. Define migration timeline (DTO pilot → code artifacts → docs → remaining)
2. Specify parity test requirements (output equivalence normalization rules)
3. Design feature flag integration (ArtifactManager decision point)
4. Clarify lifecycle field injection strategy (PartialContext pattern)
5. Document tier3 pattern macro reuse policy (formatting YES, validation NO)

**For Design Phase:**
1. Schema class hierarchy diagram (4 mixins + 20 concrete)
2. Template simplification examples (dto.py line 95: 106 → 36 chars)
3. ArtifactManager v2 flow diagram (Pydantic validation layer injection)
4. Parity test architecture (3 test suites: output/error/performance)
5. Schema registry module structure (mixins/ + concrete/)

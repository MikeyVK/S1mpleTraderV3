<!-- D:\dev\SimpleTraderV3\.st3\jinja-renderer-extraction.md -->
<!-- template=research version=8b7bb3ab created=2025-01-26T00:00:00Z updated= -->
# JinjaRenderer Extraction for Reusability

**Status:** COMPLETE  
**Version:** 1.0  
**Last Updated:** 2026-02-13

---

## Purpose

Investigate JinjaRenderer extraction from scaffolding to backend/services for reusability across MCP tools

## Scope

**MVP (Phase 1 - This Issue):**
- Extract JinjaRenderer to `backend/services/template_engine.py`
- Break circular dependency (tools/ can import TemplateEngine)
- Maintain API compatibility with current JinjaRenderer
- Support Issue #72 5-tier template architecture (FileSystemLoader)
- Regression validation: scaffolding output byte-identical before/after

**Follow-Up (Phase 2 - Same Issue, Future Work Package):**
- Mock rendering for template structure analysis
- Output parsing (Python AST, Markdown)
- Issue #120 integration (accurate optional field detection)
- Issue #121 integration (discover_capabilities method)

**Out of Scope:**
- Implementation details (TDD phase)
- Multiple template roots via ChoiceLoader (deferred to post-extraction)
- Tool-specific template overrides
- safe_edit template usage (separate issue)

Read these first:
1. Issue #52 archive research reviewed
2. Issue #72 multi-tier template system understanding
3. Issue #120 Phase 1 template introspection complete
---

## Problem Statement

Current JinjaRenderer is locked inside mcp_server/scaffolding/, preventing reuse by tools/ directory and blocking Issue #121 content-aware editing via mock rendering. Additionally, Issue #120 template introspection uses conservative 'required field' classification causing agent hallucination. Mock rendering capability could enable accurate optional field detection and broader template analysis across MCP system.

## Research Goals

- Understand architectural constraints preventing JinjaRenderer reuse outside scaffolding
- Validate Issue #52 mock rendering approach for Issue #121 output structure analysis
- Identify integration points with Issue #120 template introspection
- Determine optimal extraction location and responsibilities
- Define backward compatibility requirements

## Research Findings

### 1. Current JinjaRenderer Architecture

**Location:** `mcp_server/scaffolding/renderer.py` (100 lines)

**Current Implementation:**
```python
class JinjaRenderer:
    def __init__(self, template_dir: Path | None = None)
    @property env -> Environment  # Lazy initialization
    def get_template(template_name: str) -> Template
    def render(template_name: str, **kwargs) -> str
    def list_templates() -> list[str]
```

**Current Usage (6 import sites: 2 production, 4 test):**
- `mcp_server/scaffolding/base.py` - Base scaffolder infrastructure
- `mcp_server/scaffolders/template_scaffolder.py` - Template-driven scaffolding
- `tests/unit/scaffolders/test_template_scaffolder.py` - Scaffolder unit tests
- `tests/unit/scaffolding/test_components.py` - Component tests
- `tests/integration/test_concrete_templates.py` - Template integration tests
- `tests/fixtures/artifact_test_harness.py` - Test harness
**Missing Capabilities:**
- ❌ Mock rendering with mock context
- ❌ Multiple template root support
- ❌ Output structure parsing (Python AST, Markdown)
- ❌ Custom filters for metadata/formatting
- ❌ Template namespacing

---

### 2. Architectural Constraints Analysis

**Q1: What prevents tools/ from using current JinjaRenderer?**

**✅ ANSWER: Circular Dependency Risk**

**Current Dependency Chain:**
```
tools/ (MCP tools)
  ↓ imports
mcp_server/managers/ (ArtifactManager)
  ↓ imports
mcp_server/scaffolding/ (JinjaRenderer)
  ↓ would import (if tools needed it)
tools/ ← CIRCULAR DEPENDENCY!
```

**Evidence:**
- `tools/` directory has NO imports from `mcp_server/scaffolding/`
- `tools/scaffold_artifact.py` delegates to `ArtifactManager`
- `ArtifactManager` uses scaffolding infrastructure
- If tools/ imported JinjaRenderer directly → circular loop

**Impact:**
- tools/ cannot use JinjaRenderer for template-based operations
- Issue #121 content-aware editing blocked (needs template structure discovery)
- Custom template processing in tools/ requires code duplication

**Solution Path:**
Extract JinjaRenderer to `backend/services/` → breaks circular dependency
- `backend/` → `mcp_server/` ✅ (allowed)
- `mcp_server/` → `backend/` ❌ (forbidden)
- `tools/` → `backend/services/` ✅ (allowed)

---

### 3. Issue #52 Mock Rendering Research

**Q2: How does Issue #52 mock rendering apply to Issue #121?**

**✅ ANSWER: Proactive Structure Discovery**

**Issue #52 Research Location:**
`docs/development/issue52/archive/jinja2_introspection_research.md` lines 570-650

**Approach 2: Mock Rendering (from archive):**
```python
def analyze_with_mock_render(template_path: str) -> Dict:
    """Render template with mock data and analyze output."""
    env = Environment(loader=FileSystemLoader('.'))
    template = env.get_template(template_path)
    
    # Provide mock values
    mock_context = {
        'name': 'TEST',
        'input_dto': 'MockInput',
        'output_dto': 'MockOutput',
        'dependencies': []
    }
    
    output = template.render(**mock_context)
    
    # Parse rendered Python code
    import ast as python_ast
    tree = python_ast.parse(output)
    
    result = {
        'classes': [],
        'methods': {},
        'imports': []
    }
    
    for node in tree.body:
        if isinstance(node, python_ast.ClassDef):
            result['classes'].append(node.name)
            result['methods'][node.name] = [
                f.name for f in node.body 
                if isinstance(f, python_ast.FunctionDef)
            ]
    
    return result
```

**Issue #121 Application:**
- **Agent Context Gap:** Agent receives file path, doesn't know template structure
- **Discovery Need:** Which sections exist? Which are lists? Which are editable?
- **Mock Rendering Solution:** 
  1. Render template with mock context
  2. Parse output (Python AST for `.py`, Markdown structure for `.md`)
  3. Return edit capabilities (ScaffoldEdit vs TextEdit)

**Efficiency Analysis (from Issue #121 research):**

**Batch Editing without discovery:**
- Edit 5 DTO files → possible 5 errors + 5 retries = 10 calls worst case

**Batch Editing with discovery:**
- 1 query → learn template="dto" → 5 successful edits = 6 calls
- **40% call reduction** for batch operations

---

### 4. Issue #120 Template Introspection Integration

**Q3: What integration points exist with Issue #120 introspection?**

**✅ ANSWER: Mock Rendering Fixes Conservative Classification**

**Issue #120 Current Implementation:**
`mcp_server/scaffolding/template_introspector.py` lines 135-177

**Conservative Algorithm:**
```python
def _classify_variables(ast: nodes.Template, variables: set[str]) -> tuple[list[str], list[str]]:
    optional_vars = set()
    
    # Variables in {% if variable %} are optional
    # Variables with |default(...) filter are optional
    # ALL OTHER VARIABLES → REQUIRED (conservative = fail fast)
    
    required_vars = variables - optional_vars
    return list(required_vars), list(optional_vars)
```

**Problem: False Positives**
- Optional field with code-level default: `{{ field or 'default_value' }}`
- No `{% if %}`, no `|default` filter → marked **REQUIRED**
- Agent sees "required" → hallucinates value even when inappropriate

**Agent Hallucination Example:**
```yaml
# Agent thinks these are REQUIRED (but they're optional with code defaults):
optional_description: "Auto-generated description"  # HALLUCINATED!
optional_tags: ["default", "tag"]                   # HALLUCINATED!
```

**Mock Rendering Solution:**
```python
def test_optional_fields(template, required_fields, all_fields):
    """Test which fields are truly optional via rendering."""
    truly_optional = []
    
    for field in (all_fields - required_fields):
        try:
            # Try rendering WITHOUT this field
            context = {f: "MOCK" for f in required_fields}
            # Omit field being tested
            output = template.render(**context)
            
            # Rendering succeeded → field is TRULY OPTIONAL
            truly_optional.append(field)
        except Exception:
            # Rendering failed → field actually required
            pass
    
    return truly_optional
```

**Integration Point:**
- `introspect_template_with_inheritance()` returns `TemplateSchema`
- Add `mock_render_test=True` parameter
- Run mock rendering to refine optional classification
- Return accurate schema to agents

---

### 5. Issue #72 Multi-Tier Template System Impact

**Q4: How does Issue #72 affect JinjaRenderer responsibilities?**

**✅ ANSWER: Multiple Template Roots + Inheritance Chain Resolution**

**Issue #72 5-Tier Architecture:**
`docs/development/issue72/design.md` lines 1-200

**Tier Structure:**
```
Tier 0: tier0_base_artifact.jinja2 (SCAFFOLD metadata block)
  ↓ {% extends %}
Tier 1: CODE/DOCUMENT/CONFIG categories
  ↓ {% extends %}
Tier 2: Language-specific (python/typescript/rust)
  ↓ {% extends %}
Tier 3: Domain patterns (worker/adapter/dto/service)
  ↓ {% extends %}
Concrete: Actual template with specific implementation
```


**Example Inheritance Chain:**
```
mcp_server/scaffolding/templates/
├── tier0_base_artifact.jinja2          # Tier 0
├── tier1_code_artifact.jinja2          # Tier 1
├── tier2_python.jinja2                 # Tier 2
├── tier3_python_worker.jinja2          # Tier 3
└── concrete/worker.py.jinja2           # Concrete
```

**JinjaRenderer Responsibilities for Issue #72:**

1. **Single Template Root (MVP):**
   - `mcp_server/scaffolding/templates/` - All templates (5-tier architecture)
   - Multiple roots deferred to post-extraction work

2. **Inheritance Chain Resolution:**
   - Already supported via `FileSystemLoader`
   - Jinja2 `{% extends %}` handles chain automatically
   - BUT: Introspection must walk ENTIRE chain (Issue #120 Phase 1 does this)

3. **Template Registry Integration:**
   - `.st3/template_registry.yaml` maps artifact types to concrete templates
   - JinjaRenderer needs registry lookup: `artifact_type="dto"` → `concrete/dto.py.jinja2`

**Current State:**
- ✅ Jinja2 inheritance: FileSystemLoader handles `{% extends %}` correctly
- ✅ Introspection: `introspect_template_with_inheritance()` walks chain (Issue #120)
- ❌ Multiple roots: Hardcoded to single `template_dir`
- ❌ Registry integration: Not implemented yet

---

### 6. Extraction Target Location Analysis

**Q5: What are optimal extraction target locations?**

**✅ ANSWER: `backend/services/template_engine.py`**

**Option 1: `backend/services/` (RECOMMENDED)**
- ✅ Services = reusable business logic layer
- ✅ No circular dependency: `tools/` → `backend/services/` ✅ allowed
- ✅ Separation of concerns: Template engine = service, not primitive
- ✅ Existing pattern: `backend/services/` has other infrastructure

**Option 2: `backend/core/` (REJECTED)**
- ❌ Core = primitives only (enums, value objects, base classes)
- ❌ Template engine = complex service with external dependency (Jinja2)
- ❌ Violates layering: Core should have minimal dependencies

**Option 3: New `backend/rendering/` package (OVER-ENGINEERING)**
- ❌ Single class doesn't justify new package
- ❌ Would need `__init__.py`, structure overhead
- ❌ Future: If rendering grows (PDF, HTML), revisit

**Decision Matrix:**
| Criteria | backend/services/ | backend/core/ | backend/rendering/ |
|----------|-------------------|---------------|-------------------|
| Layering fit | ✅ Services | ❌ Too complex | ⚠️ Over-engineering |
| Circular deps | ✅ No cycles | ✅ No cycles | ✅ No cycles |
| Discoverability | ✅ Clear location | ❌ Misleading | ⚠️ Extra search |
| Maintenance | ✅ Standard pattern | ❌ Violates core principle | ❌ Overhead |

**Final Decision: `backend/services/template_engine.py`**

---

### 7. Migration Strategy: Direct Replacement (No Backward Compatibility)

**Q8: What backward compatibility guarantees needed?**

**✅ ANSWER: NONE - Direct Migration with Test Coverage + Regression Validation**

**Decision: NO backward compatibility layer**
- ❌ No import alias at old location
- ❌ No deprecation warnings
- ❌ No gradual transition period
- ✅ Direct file replacement + import updates
- ✅ Full test coverage ensures safety
- ✅ **Regression validation: Scaffolding output must be byte-identical before/after extraction**

**Regression Requirements (Hard Constraint):**

**Output Identity:**
- Same input context → identical rendered output (character-for-character)
- Same template → same SCAFFOLD metadata
- Same error conditions → identical error messages

**Test Strategy:**
- Capture baseline outputs from current JinjaRenderer (10 templates)
- Run same renders through TemplateEngine
- Assert byte-for-byte equality (no formatting changes, no metadata drift)
- Include error cases (missing template, invalid context)

**Validation Tests:**
- Test: DTO template → identical output
- Test: Worker template → identical output
- Test: Design doc template → identical output
- Test: Missing template → identical error message
- Test: Invalid context → identical error behavior

**Rationale:**
1. **Limited Surface Area:** Only 6 import sites (2 production, 4 test)
2. **Internal Module:** JinjaRenderer is not a public API
3. **Test Safety Net:** All functionality covered by tests
4. **Output Stability:** Regression tests prevent unintended changes
5. **Clean Cut:** No legacy baggage slowing future refactors
6. **Issue #108 Scope:** Extraction is blocking Issue #121 (high priority)

**Migration Steps:**

**Step 1: Create New Module**
```python
# backend/services/template_engine.py
"""
Template Engine - Jinja2 rendering for scaffolding.

Provides Jinja2-based template rendering for Issue #72 5-tier architecture.

@layer: Backend (Services)
@dependencies: [jinja2, pathlib]
@responsibilities:
    - Render Jinja2 templates with context variables
    - Support single template root via get_template_root()
    - Enable 5-tier template inheritance (FileSystemLoader)
    - Provide custom filters (metadata, formatting, validation)
"""
```

**Step 2: Update All Imports (6 Sites)**
```python
# BEFORE
from mcp_server.scaffolding.renderer import JinjaRenderer

# AFTER
from backend.services.template_engine import TemplateEngine
```

**Production Files (2):**
1. `mcp_server/scaffolding/base.py`
2. `mcp_server/scaffolders/template_scaffolder.py`

**Test Files (4):**
3. `tests/unit/scaffolders/test_template_scaffolder.py`
4. `tests/unit/scaffolding/test_components.py`
5. `tests/integration/test_concrete_templates.py`
6. `tests/fixtures/artifact_test_harness.py`
**Step 3: Delete Old Module**
```powershell
Remove-Item mcp_server/scaffolding/renderer.py
```

**Step 4: Verify via Quality Gates**
```powershell
# Run full test suite
pytest tests/

# Run quality gates on changed files
python -m ruff format --check backend/services/template_engine.py
python -m ruff check backend/services/template_engine.py
python -m mypy backend/services/template_engine.py --strict
```

**Risk Mitigation:**
- ✅ Run full test suite BEFORE commit
- ✅ Quality gates BEFORE commit
- ✅ All tests pass = safe to proceed
- ✅ Git history preserves old implementation (easy revert if needed)

**Estimated Effort:**
- Create new module: 4-6 hours (with mock rendering)
- Update 6 imports: 30 minutes
- Test verification: 30 minutes
- **Total: 5-7 hours**

---

### 8. Acceptance Criteria (Based on Coding Standards)

**Source:** `docs/coding_standards/` (QUALITY_GATES.md, CODE_STYLE.md, TYPE_CHECKING_PLAYBOOK.md)

#### AC1: Quality Gates (All 7 Gates Must Pass)

**Gate 0: Code Formatting**

**Requirements:**
- ✅ Consistent formatting (100 char line length)
- ✅ No formatting diffs
- ✅ Black-compatible style

**Validation:**
Run formatter in check mode (any formatter implementing these rules).
*Example using ruff:*
```powershell
python -m ruff format --isolated --check --diff --line-length=100 backend/services/template_engine.py
```

---

**Gate 1: Strict Linting**

**Requirements:**
- ✅ No lint violations (errors, warnings, style issues)
- ✅ Full type annotations on all functions/methods (ANN rules)
- ✅ No unused imports or variables

**Validation:**
Run linter in strict mode.
*Example using ruff:*
```powershell
python -m ruff check --isolated --select=E,W,F,I,N,UP,ANN,B,C4,DTZ,T10,ISC,RET,SIM,ARG,PLC --ignore=E501,PLC0415 --line-length=100 backend/services/template_engine.py
```

---

**Gate 2: Import Placement**

**Requirements:**
- ✅ All imports at module top-level
- ✅ No imports inside functions/methods

**Validation:**
Check import placement rules.
*Example using ruff:*
```powershell
python -m ruff check --isolated --select=PLC0415 backend/services/template_engine.py
```

---

**Gate 3: Line Length**

**Requirements:**
- ✅ Maximum 100 characters per line
- ✅ No exceptions (use line breaks for long strings/imports)

**Validation:**
Check line length compliance.
*Example using ruff:*
```powershell
python -m ruff check --isolated --select=E501 --line-length=100 backend/services/template_engine.py
```

---

**Gate 4: Type Checking (Strict)**

**Requirements:**
- ✅ Full type coverage (no `Any` without justification)
- ✅ No `type: ignore` without rationale comment
- ✅ Follow Type Checking Playbook resolution order

**Validation:**
Run type checker in strict mode.
*Example using mypy:*
```powershell
python -m mypy backend/services/template_engine.py --strict
```

---

**Gate 5: Tests Passing**

**Requirements:**
- ✅ All unit tests pass
- ✅ All integration tests pass
- ✅ Regression tests validate output identity
- ✅ Error case tests included

**Validation:**
Run test suite with exit code 0.
*Example using pytest:*
```powershell
pytest tests/unit/backend/services/test_template_engine.py
pytest tests/integration/ -k template_engine
```

---

**Gate 6: Code Coverage**

**Requirements:**
- ✅ ≥90% code coverage
- ✅ All public methods covered
- ✅ Error paths covered
- ✅ Edge cases covered

**Validation:**
Run coverage tool with 90% threshold.
*Example using pytest-cov:*
```powershell
pytest --cov=backend.services.template_engine --cov-report=term-missing --cov-fail-under=90
```

---
- Path comment on line 1
- Module docstring with description
- @layer annotation (Backend - Services)
- @dependencies list (jinja2, ast, re, pathlib)
- @responsibilities list (render, mock render, parse output, custom filters)

**Note:** AUTOMATED VIA SCAFFOLDING (base_component.py.jinja2)

---

#### AC3: Import Organization

**Requirement:** 3-section import structure per coding standards.

**Standards:**
- Section 1: Standard library imports
- Section 2: Third-party imports (jinja2)
- Section 3: Project modules
- Comment headers required
- Alphabetical order within sections

**Note:** AUTOMATED VIA SCAFFOLDING

---

#### AC4: Full Type Hinting

**Requirement:** All functions, methods, and properties must have complete type hints.

**Standards:**
- Parameter types required
- Return type required (including `None` for void functions)
- Private methods need type hints
- Test functions need return type annotation
- Use concrete types over `Any` where possible

**Validation:** mypy --strict must pass (Gate 4)

---

#### AC5: Type Checking Playbook Compliance

**Requirement:** Type issues resolved following resolution order from Type Checking Playbook.

**Resolution Order (docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md):**
1. Fix types at source (prefer concrete types)
2. Narrow types via runtime checks
3. Improve model/type design (Protocol, TypedDict)
4. Contain dynamic edges (parse at boundaries)
5. Targeted type: ignore (with rationale comment)
6. Casting (last resort, with runtime validation)

**Standards:**
- No blind casting
- Runtime checks before narrowing
- Rationale comments for type: ignore

---

#### AC6: Mock Rendering Functionality

**Requirement:** Support mock rendering for template structure analysis (Issue #121).

**Required Capabilities:**
- Mock render with test context
- Parse Python output via AST
- Parse Markdown structure
- Discover edit capabilities (Issue #121 integration)

**Test Coverage:**
- Test: Mock render DTO template
- Test: Parse Python AST successfully
- Test: Parse Markdown structure
- Test: Discover capabilities returns expected operations

---

---

#### AC7: Template Root Configuration (Config-First)

**Requirement:** Template root must be configurable via central config mechanism, not hardcoded paths.

**Config-First Principle:**
- ✅ Template root comes from config source (environment variable, config file, or config helper)
- ✅ No hardcoded relative paths in template engine code
- ✅ Single source of truth for template location
- ❌ NO `Path(__file__).parent.parent.parent / "mcp_server"...` constructions

**Expected Behavior:**
- Default: Use existing `get_template_root()` from `mcp_server/config/template_config.py`
- Override: Constructor accepts optional `template_root` parameter
- Validation: Raise error if configured root does not exist

**Integration Point:**
- Existing config: `mcp_server/config/template_config.py` already has `get_template_root()`
- Returns: `mcp_server/scaffolding/templates/` (can be overridden via TEMPLATE_ROOT env var)
- TemplateEngine should reuse this config mechanism

**YAGNI Note:**
- Start with single template root (sufficient for current needs)
- Multiple roots (ChoiceLoader) deferred to P1 when proven needed
- Easy upgrade path: `Path` → `list[Path]` if required later

**Test Requirements:**
- Test: Default uses `get_template_root()` value
- Test: Constructor override works
- Test: ValueError on nonexistent root
- Test: Respects TEMPLATE_ROOT environment variable (via config)

**TODO for Planning Phase:**
- [ ] Update ~50 doc references from `mcp_server/templates/` → `mcp_server/scaffolding/templates/`
  - `docs/development/issue108/research.md` (this file)
  - `docs/reference/mcp/validation_api.md`
  - `docs/reference/mcp/scaffolding.md`
  - `docs/reference/mcp/template_metadata_format.md`
  - Archive docs (issue52, issue56, issue72)
- [ ] Verify all doc examples use correct active template path
- [ ] Consider: Add redirects/notes in legacy sections

---
---
#### AC8: Custom Jinja2 Filters

**Requirement:** Provide custom Jinja2 filters for template convenience.

**Required Filters:**
- pascalcase: Convert string to PascalCase
- snakecase: Convert string to snake_case
- kebabcase: Convert string to kebab-case
- validate_identifier: Validate Python identifier

**Test Coverage:**
- Test: Each filter with valid input
- Test: Edge cases (empty strings, special characters)
- Test: Filters available in template rendering

---

#### AC9: Issue Integration

**Requirement:** Ensure extraction supports Issue #72 architecture (MVP), defer #120/#121 enhancements.

**MVP Criteria (P0 - Required for Extraction):**

**Issue #72 Integration (5-Tier Templates):**
- Template root points to `mcp_server/scaffolding/templates/`
- Jinja2 FileSystemLoader handles inheritance chain (`{% extends %}`)
- Test: Render concrete template that extends tier2 → tier1 → tier0
- Test: Template with tier3 patterns imports via `{% import %}`
- Validation: Existing scaffolding output identical before/after extraction

**Follow-Up Criteria (P1 - Post-Extraction Enhancements):**

**Issue #120 Integration (Template Introspection):**
- Mock rendering enables accurate optional field detection
- Test: Render template with/without each field
- Compare with conservative classification from `_classify_variables()`
- Note: Deferred to separate work package (depends on mock rendering)

**Issue #121 Integration (Content-Aware Editing):**
- `discover_capabilities()` method returns edit operations
- Test: Parse DTO template returns expected capabilities
- Test: Parse Markdown template returns section operations
- Note: Deferred to separate work package (depends on output parsing)

**Scope Rationale:**
- MVP scope: Extract JinjaRenderer for reusability (#72 compatibility required)
- Enhancement scope: Add mock rendering + parsing (#120/#121 integration)
- Prevents scope creep while enabling future work

---

#### AC10: Documentation

**Requirement:** Complete documentation per coding standards.

**Required Documentation:**
- Module docstring with @layer, @dependencies, @responsibilities
- Class docstring (concise one-liner)
- Method docstrings (Google style: Args/Returns/Raises/Example)
- Inline comments only for complex logic
- Type hints as primary documentation (prefer over comments)

**Validation:**
- All public methods documented
- Google style format consistent
- Examples included for non-trivial methods

---

---

## Summary of Research Updates

### Clarifications

1. **✅ NO Backward Compatibility**
   - Direct migration (no import alias, no deprecation warnings)
   - Only 6 import sites (2 production, 4 test) - direct migration feasible
   - Full test coverage ensures safety
   - Clean cut for future maintainability

2. **✅ Acceptance Criteria Defined**
   - 7 Quality Gates (Gate 0-6) must pass
   - File header standards (@layer, @dependencies, @responsibilities)
   - Import organization (3 sections)
   - Full type hinting (parameters + return types)
   - Type Checking Playbook compliance
   - Mock rendering functionality with tests
   - Multiple template roots support
   - Custom Jinja2 filters
   - Issue integration (#120, #121, #72)
   - Documentation standards

### Key Findings Remain

- **Circular Dependency Blocker:** Extract to `backend/services/template_engine.py`
- **Mock Rendering:** Solves Issue #120 hallucination + Issue #121 discovery
- **Issue #72 Integration:** Multiple template roots via ChoiceLoader
- **Output Parsing:** Python AST + Markdown structure analysis

---

### 9. Mock Rendering Capabilities

**Q9: What output parsing utilities are needed?**

**✅ ANSWER: Python AST + Markdown Structure Parsers**

**Python Template Parsing:**
- Parse rendered Python code via `ast.parse()`
- Extract: classes, functions, methods, imports, constants
- Enable discovery of edit points for Issue #121
- Handle syntax errors gracefully

**Markdown Template Parsing:**
- Parse rendered Markdown structure via regex/line scanning
- Extract: sections (H2), subsections (H3), lists, code blocks, tables
- Enable section-based editing for Issue #121
- Maintain line number mapping for edit operations

**Issue #121 Integration:**
- `discover_capabilities()` combines template mock rendering + parsing
- Returns available edit operations based on file type
- Python: append_to_list (imports, methods, fields), replace_section (classes, functions)
- Markdown: append_to_list (bullet points), replace_section (H2 sections)

**Implementation Note:** Defer concrete parsing logic to planning/design phase.

---

### 10. Custom Jinja2 Filters

**Q10: Which custom filters are needed?**

**✅ ANSWER: Case Conversion + Validation Filters**

**Required Filters:**
- **pascalcase**: Convert snake_case to PascalCase (class names)
- **snakecase**: Convert PascalCase to snake_case (function names)
- **kebabcase**: Convert to kebab-case (file paths)
- **validate_identifier**: Ensure valid Python identifier

**Usage Context:**
- Templates use filters for consistent naming conventions
- Example: `class {{ name | pascalcase }}:` ensures proper class naming
- Validation filters raise errors on invalid input (fail-fast)

**Implementation Note:** Defer filter implementations to planning/design phase.

---

### 11. Template Root Configuration Strategy

**Q11: How should template root be configured?**

**✅ ANSWER: Config-First via get_template_root() [MVP: Single Root Only]**

**MVP Scope Decision:**
- ✅ Single template root only (sufficient for extraction goal)
- ❌ Multi-root/ChoiceLoader explicitly deferred to future work
- ✅ Reuse existing `get_template_root()` infrastructure

**Current System:**
- `mcp_server/config/template_config.py` has `get_template_root()` helper
- Returns `mcp_server/scaffolding/templates/` by default
- Supports override via TEMPLATE_ROOT environment variable
- Already used by TemplateScaffolder and ValidationService

**TemplateEngine Integration (MVP):**
- Reuse existing config mechanism (DRY principle)
- Constructor parameter for test overrides
- Validate root exists (fail-fast on misconfiguration)
- FileSystemLoader (NOT ChoiceLoader)

**YAGNI Rationale:**
- Current need: Extract JinjaRenderer for reusability
- Single root satisfies extraction goal
- Multi-root adds complexity without proven requirement
- Easy upgrade path if requirements emerge

**Deferred to Future (Post-Extraction):**
- Multiple template roots via ChoiceLoader
- Template namespacing strategy
- Priority order resolution
- Tool-specific template overrides

**Implementation Note:** Use existing infrastructure, don't reinvent config.

## Summary of Key Findings

### Critical Discoveries

1. **Circular Dependency Blocker:**
   - Current location prevents tools/ from using JinjaRenderer
   - Extract to `backend/services/template_engine.py` breaks cycle
   - **No backward compatibility needed** - only 6 import sites (2 production, 4 test), direct migration
2. **Mock Rendering (Phase 2 - Follow-Up):**
   - Issue #120: Accurate optional field detection (no more hallucination)
   - Issue #121: Proactive edit capabilities discovery (40% call reduction)
   - Output structure analysis: Python AST + Markdown parsing

3. **Issue #72 Integration (MVP):**
   - 5-tier inheritance supported via FileSystemLoader
   - Single template root via `get_template_root()`
   - Compatible with existing `mcp_server/scaffolding/templates/`

4. **Quality Standards:**
   - All 7 quality gates must pass (Gate 0-6)
   - File headers with @layer, @dependencies, @responsibilities
   - Full type hinting (parameters + return types)
   - Type Checking Playbook compliance
   - ≥90% code coverage

### Acceptance Criteria Defined

**Based on:** `docs/coding_standards/` (QUALITY_GATES.md, CODE_STYLE.md, TYPE_CHECKING_PLAYBOOK.md)

**Must Pass:**
- ✅ Gate 0: Ruff Format (100 char lines)
- ✅ Gate 1: Ruff Strict Lint (ANN, E, W, F, I, N, UP, B, C4, DTZ, T10, ISC, RET, SIM, ARG, PLC)
- ✅ Gate 2: Import Placement (PLC0415 - top-level only)
- ✅ Gate 3: Line Length (E501 - max 100 chars)
- ✅ Gate 4: Type Checking (mypy --strict)
- ✅ Gate 5: Tests Passing (all tests green)
- ✅ Gate 6: Code Coverage (≥90%)

**Must Implement (MVP - Phase 1):**
- ✅ Basic Jinja2 rendering with context variables
- ✅ Single template root via `get_template_root()`
- ✅ FileSystemLoader for 5-tier inheritance support
- ✅ Custom filters (pascalcase, snakecase, kebabcase, validate_identifier)
- ✅ Issue #72 compatibility (existing scaffolding output identical)

**Follow-Up Implementation (Phase 2):**
- ⏳ Mock rendering with parse_python_output() and parse_markdown_output()
- ⏳ Multiple template roots via ChoiceLoader
- ⏳ Issue #120 integration (accurate optional detection)
- ⏳ Issue #121 integration (discover_capabilities method)
**Must Document:**
- ✅ Module header with @layer, @dependencies, @responsibilities
- ✅ Google-style docstrings (Args/Returns/Raises/Example)
- ✅ 3-section imports (standard/third-party/project)

### Unanswered Questions (Deferred to Planning)

- ⏳ **Effort estimation:** How long for each capability? (planning phase)
- ⏳ **Test strategy:** Which test scenarios cover mock rendering? (planning phase)
- ⏳ **Work package breakdown:** How to sequence implementation? (planning phase)
- ⏳ **Risk mitigation:** What are potential blockers? (planning phase)
- ⏳ **Integration testing:** How to verify Issue #120/#121 compatibility? (planning phase)


## Related Documentation
- **[Issue #52: Jinja2 introspection research (1281 lines, lines 570-650 mock rendering)][related-1]**
- **[Issue #72: Multi-tier template system (5 tiers: core-system/core-domain/domain/application/integration)][related-2]**
- **[Issue #120: Template introspection Phase 1 (conservative required classification)][related-3]**
- **[Issue #121: Content-aware editing capabilities (blocked on mock rendering)][related-4]**
- **[Issue #54: MCP tool architecture overhaul][related-5]**
- **[mcp_server/scaffolding/renderer.py: Current JinjaRenderer (100 lines)][related-6]**
- **[mcp_server/scaffolding/template_introspector.py: Conservative variable classification][related-7]**

<!-- Link definitions -->

[related-1]: Issue #52: Jinja2 introspection research (1281 lines, lines 570-650 mock rendering)
[related-2]: Issue #72: Multi-tier template system (5 tiers: core-system/core-domain/domain/application/integration)
[related-3]: Issue #120: Template introspection Phase 1 (conservative required classification)
[related-4]: Issue #121: Content-aware editing capabilities (blocked on mock rendering)
[related-5]: Issue #54: MCP tool architecture overhaul
[related-6]: mcp_server/scaffolding/renderer.py: Current JinjaRenderer (100 lines)
[related-7]: mcp_server/scaffolding/template_introspector.py: Conservative variable classification

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-13 | Agent | Initial research complete |
| 1.1 | 2026-02-13 | Agent | Added acceptance criteria (coding standards) |
| 1.2 | 2026-02-13 | Agent | Removed backward compatibility (direct migration) |
| 1.3 | 2026-02-13 | Agent | P0 feedback: MVP scope (single root), pad fixes, import count, AC9 split |
| 1.4 | 2026-02-13 | Agent | P1 feedback: Regression reqs, mock rendering deferred, tool-agnostic gates |

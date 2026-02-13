<!-- D:\dev\SimpleTraderV3\.st3\jinja-renderer-extraction.md -->
<!-- template=research version=8b7bb3ab created=2025-01-26T00:00:00Z updated= -->
# JinjaRenderer Extraction for Reusability

**Status:** COMPLETE  
**Version:** 1.0  
**Last Updated:** 2026-02-13

---

## Purpose

Investigate JinjaRenderer extraction from scaffolding to backend/services, enabling mock rendering for Issue #120/#121 and broader reuse across MCP tools

## Scope

**In Scope:**
Current JinjaRenderer architecture, Issue #52 mock rendering research, Issue #120 template introspection integration, Issue #72 multi-tier template system, circular dependency analysis, output parsing strategies

**Out of Scope:**
Implementation details (TDD phase), safe_edit template usage (separate issue), full Issue #121 implementation

## Prerequisites

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

**Current Usage (3 import sites):**
- `mcp_server/scaffolding/base.py` - Base scaffolder infrastructure
- `mcp_server/scaffolders/template_scaffolder.py` - Template-driven scaffolding
- `tests/integration/mcp_server/validation/test_scaffold_validate_e2e.py` - E2E tests

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
mcp_server/templates/
├── tier0_base_artifact.jinja2          # Tier 0
├── tier1_code_artifact.jinja2          # Tier 1
├── tier2_python.jinja2                 # Tier 2
├── tier3_python_worker.jinja2          # Tier 3
└── concrete/worker.py.jinja2           # Concrete
```

**JinjaRenderer New Responsibilities:**

1. **Multiple Template Roots:**
   - `mcp_server/templates/` - Main scaffolding templates
   - `docs/templates/` - Documentation templates (future)
   - `tools/templates/` - Tool-specific templates (future)

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

**✅ ANSWER: NONE - Direct Migration with Test Coverage**

**Decision: NO backward compatibility layer**
- ❌ No import alias at old location
- ❌ No deprecation warnings
- ❌ No gradual transition period
- ✅ Direct file replacement + import updates
- ✅ Full test coverage ensures safety

**Rationale:**
1. **Limited Surface Area:** Only 3 import sites to update
2. **Internal Module:** JinjaRenderer is not a public API
3. **Test Safety Net:** All functionality covered by tests
4. **Clean Cut:** No legacy baggage slowing future refactors
5. **Issue #108 Scope:** Extraction is blocking Issue #121 (high priority)

**Migration Steps:**

**Step 1: Create New Module**
```python
# backend/services/template_engine.py
"""
Template Engine - Jinja2 rendering with mock capabilities.

Enhanced JinjaRenderer with mock rendering for template introspection
and multi-root template support for Issue #72 5-tier architecture.

@layer: Backend (Services)
@dependencies: [jinja2, ast, pathlib]
@responsibilities:
    - Render Jinja2 templates with context variables
    - Mock render templates for structure analysis (Issue #121)
    - Support multiple template roots (Issue #72)
    - Parse rendered output (Python AST, Markdown)
    - Provide custom filters (metadata, formatting, validation)
"""
```

**Step 2: Update All Imports (3 Sites)**
```python
# BEFORE
from mcp_server.scaffolding.renderer import JinjaRenderer

# AFTER
from backend.services.template_engine import TemplateEngine
```

**Files to Update:**
1. `mcp_server/scaffolding/base.py`
2. `mcp_server/scaffolders/template_scaffolder.py`
3. `tests/integration/mcp_server/validation/test_scaffold_validate_e2e.py`

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
- Update 3 imports: 15 minutes
- Test verification: 30 minutes
- **Total: 5-7 hours**

---

### 8. Acceptance Criteria (Based on Coding Standards)

**Source:** `docs/coding_standards/` (QUALITY_GATES.md, CODE_STYLE.md, TYPE_CHECKING_PLAYBOOK.md)

#### AC1: Quality Gates (All 7 Gates Must Pass)

**Gate 0: Ruff Format**
```powershell
python -m ruff format --isolated --check --diff --line-length=100 backend/services/template_engine.py
python -m ruff format --isolated --check --diff --line-length=100 tests/unit/backend/services/test_template_engine.py
```
- ✅ Consistent formatting (100 char line length)
- ✅ No formatting diffs

**Gate 1: Ruff Strict Lint**
```powershell
python -m ruff check --isolated --select=E,W,F,I,N,UP,ANN,B,C4,DTZ,T10,ISC,RET,SIM,ARG,PLC --ignore=E501,PLC0415 --line-length=100 --target-version=py311 backend/services/template_engine.py
python -m ruff check --isolated --select=E,W,F,I,N,UP,ANN,B,C4,DTZ,T10,ISC,RET,SIM,ARG,PLC --ignore=E501,PLC0415 --line-length=100 --target-version=py311 tests/unit/backend/services/test_template_engine.py
```
- ✅ No lint violations
- ✅ Full type annotations (ANN rules)

**Gate 2: Import Placement**
```powershell
python -m ruff check --isolated --select=PLC0415 --target-version=py311 backend/services/template_engine.py
```
- ✅ All imports at module top-level
- ✅ No imports inside functions/methods

**Gate 3: Line Length**
```powershell
python -m ruff check --isolated --select=E501 --line-length=100 --target-version=py311 backend/services/template_engine.py
```
- ✅ Maximum 100 characters per line

**Gate 4: Type Checking (Strict)**
```powershell
python -m mypy backend/services/template_engine.py --strict
```
- ✅ Full type coverage (no `Any` without justification)
- ✅ No type: ignore without rationale comment
- ✅ Follow Type Checking Playbook resolution order

**Gate 5: Tests Passing**
```powershell
pytest tests/unit/backend/services/test_template_engine.py
pytest tests/integration/mcp_server/validation/test_scaffold_validate_e2e.py
```
- ✅ All tests pass (exit code 0)
- ✅ Mock rendering tests included
- ✅ Multiple template roots tests included

**Gate 6: Code Coverage**
```powershell
pytest --cov=backend.services.template_engine --cov-report=term-missing --cov-fail-under=90
```
- ✅ ≥90% code coverage
- ✅ All core methods covered (render, mock_render, parse_output)

---

#### AC2: File Header Standards

**AUTOMATED VIA SCAFFOLDING:** TemplateEngine will be scaffolded, inheriting header automatically from base_component.py.jinja2.

**Expected Module Header:**
```python
# backend/services/template_engine.py
"""
Template Engine - Jinja2 rendering with mock capabilities.

Enhanced JinjaRenderer with mock rendering for template introspection
and multi-root template support for Issue #72 5-tier architecture.

@layer: Backend (Services)
@dependencies: [jinja2, ast, re, pathlib]
@responsibilities:
    - Render Jinja2 templates with context variables
    - Mock render templates for structure analysis (Issue #121)
    - Support multiple template roots via ChoiceLoader (Issue #72)
    - Parse rendered output (Python AST for .py, Markdown for .md)
    - Provide custom filters (metadata, formatting, validation)
    - Enable accurate optional field detection (Issue #120)
"""
```

**Note:** @responsibilities block is now mandatory via base_component.py.jinja2 template.

**Class Docstrings (Concise):**
```python
class TemplateEngine:
    """Jinja2 template engine with mock rendering and multi-root support."""
```

**Method Docstrings (Google Style):**
```python
def mock_render(self, template_name: str, mock_context: dict[str, Any]) -> str:
    """Render template with mock context for structure analysis.
    
    Args:
        template_name: Relative path to template (e.g., "dto.py.jinja2")
        mock_context: Mock variable context for rendering
    
    Returns:
        Rendered template output string
    
    Raises:
        TemplateNotFound: If template does not exist
        TemplateSyntaxError: If template has invalid Jinja2 syntax
    
    Example:
        >>> engine = TemplateEngine()
        >>> output = engine.mock_render("dto.py.jinja2", {"name": "TEST"})
    """
```

---

#### AC3: Import Organization (3 Sections)

**AUTOMATED VIA SCAFFOLDING:** Base templates enforce 3-section import structure.

**Expected Structure:**
```python
# Standard library
import ast
import re
from pathlib import Path
from typing import Any, Protocol

# Third-party
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, TemplateNotFound

# Project modules
from mcp_server.core.exceptions import ExecutionError
```

**Rules (Enforced by base_component.py.jinja2):**
- ✅ 3 sections with comment headers
- ✅ Blank line between sections
- ✅ Alphabetical order within sections
- ✅ No imports inside functions

---

#### AC4: Full Type Hinting

**All Functions/Methods:**
```python
def render(self, template_name: str, **kwargs: Any) -> str:
    """Type hints for params AND return value."""
```

**Properties:**
```python
@property
def env(self) -> Environment:
    """Type hint for property return value."""
```

**Private Methods:**
```python
def _parse_python_output(self, output: str) -> dict[str, Any]:
    """Even private methods need type hints."""
```

**Test Functions:**
```python
def test_mock_render(engine: TemplateEngine) -> None:
    """Test functions need return type (None)."""
```

---

#### AC5: Type Checking Playbook Compliance

**Resolution Order:**
1. ✅ Fix types at source (prefer concrete types over Any)
2. ✅ Narrow types via runtime checks (assert, isinstance, if checks)
3. ✅ Improve model/type design (Protocol, TypedDict, NewType)
4. ✅ Contain dynamic edges (parse at boundaries)
5. ✅ Targeted ignore (with rationale comment)
6. ✅ Casting (last resort, with runtime check)

**Example:**
```python
from typing import cast

def get_template(self, name: str) -> Template:
    """Load template with proper type narrowing."""
    template = self.env.get_template(name)  # Returns Template | None
    
    # Narrow via runtime check (not blind cast!)
    if template is None:
        raise TemplateNotFound(name)
    
    # Type checker now knows template is not None
    return template
```

---

#### AC6: Mock Rendering Functionality

**Required Methods:**
```python
class TemplateEngine:
    def mock_render(self, template_name: str, mock_context: dict[str, Any]) -> str:
        """Render with mock context."""
    
    def parse_python_output(self, rendered: str) -> dict[str, Any]:
        """Parse rendered Python code via AST."""
    
    def parse_markdown_output(self, rendered: str) -> dict[str, Any]:
        """Parse rendered Markdown structure."""
    
    def discover_capabilities(self, template_name: str) -> dict[str, Any]:
        """Discover edit capabilities for Issue #121."""
```

**Test Coverage:**
```python
def test_mock_render_dto() -> None:
    """Test mock rendering of DTO template."""

def test_parse_python_output() -> None:
    """Test Python AST parsing."""

def test_parse_markdown_output() -> None:
    """Test Markdown structure parsing."""

def test_discover_capabilities() -> None:
    """Test edit capabilities discovery for Issue #121."""
```

---

#### AC7: Multiple Template Roots

**Required Implementation:**
```python
class TemplateEngine:
    def __init__(self, template_roots: list[Path] | None = None) -> None:
        """Initialize with multiple template directories.
        
        Args:
            template_roots: List of template roots (priority order)
                           Default: [mcp_server/templates, docs/templates]
        """
        if template_roots is None:
            base = Path(__file__).parent.parent.parent
            template_roots = [
                base / "mcp_server" / "templates",
                base / "docs" / "templates"
            ]
        
        loaders = [
            FileSystemLoader(str(root)) 
            for root in template_roots 
            if root.exists()
        ]
        
        self._env = Environment(loader=ChoiceLoader(loaders))
```

**Test Coverage:**
```python
def test_multiple_template_roots() -> None:
    """Test ChoiceLoader with multiple roots."""

def test_template_resolution_order() -> None:
    """Test priority order (first root wins)."""
```

---

#### AC8: Custom Jinja2 Filters

**Required Filters:**
```python
def filter_pascalcase(s: str) -> str:
    """Convert to PascalCase."""

def filter_snakecase(s: str) -> str:
    """Convert to snake_case."""

def filter_kebabcase(s: str) -> str:
    """Convert to kebab-case."""

def filter_validate_identifier(s: str) -> str:
    """Validate Python identifier."""
```

**Registration:**
```python
self._env.filters['pascalcase'] = filter_pascalcase
self._env.filters['snakecase'] = filter_snakecase
self._env.filters['kebabcase'] = filter_kebabcase
self._env.filters['validate_identifier'] = filter_validate_identifier
```

**Test Coverage:**
```python
def test_filters() -> None:
    """Test all custom filters."""
```

---

#### AC9: Issue Integration

**Issue #120 Integration:**
- ✅ Mock rendering enables accurate optional field detection
- ✅ Test: Render template with/without each field
- ✅ Compare with conservative classification from `_classify_variables()`

**Issue #121 Integration:**
- ✅ `discover_capabilities()` method returns edit operations
- ✅ Test: Parse DTO template → return `append_to_list` capabilities
- ✅ Test: Parse Markdown template → return `replace_section` capabilities

**Issue #72 Integration:**
- ✅ Multiple template roots support 5-tier architecture
- ✅ ChoiceLoader handles inheritance chain resolution
- ✅ Test: Resolve Tier 0 → Tier 1 → Tier 2 → Tier 3 → Concrete

---

#### AC10: Documentation

**Required Documentation:**
- ✅ Module docstring with @layer, @dependencies, @responsibilities
- ✅ Class docstring (concise one-liner)
- ✅ Method docstrings (Google style with Args/Returns/Raises/Example)
- ✅ Inline comments for complex logic only
- ✅ Type hints serve as documentation (prefer over comments)

**Example Usage Documentation:**
```python
"""
Example Usage:
    >>> from backend.services.template_engine import TemplateEngine
    >>> from pathlib import Path
    >>> 
    >>> # Create engine with custom roots
    >>> roots = [Path("templates"), Path("docs/templates")]
    >>> engine = TemplateEngine(template_roots=roots)
    >>> 
    >>> # Render template
    >>> output = engine.render("dto.py.jinja2", name="Signal", fields=[...])
    >>> 
    >>> # Mock render for discovery
    >>> mock_output = engine.mock_render("dto.py.jinja2", {"name": "TEST"})
    >>> structure = engine.parse_python_output(mock_output)
    >>> print(structure["classes"])  # ['TESTSignal']
"""
```

---

## Summary of Research Updates

### Clarifications

1. **✅ NO Backward Compatibility**
   - Direct migration (no import alias, no deprecation warnings)
   - Only 3 import sites to update
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

**Python AST Parsing (for .py templates):**
```python
import ast

def parse_python_output(rendered: str) -> dict:
    """Parse rendered Python code structure."""
    try:
        tree = ast.parse(rendered)
    except SyntaxError as e:
        return {"error": str(e)}
    
    result = {
        "classes": [],
        "functions": [],
        "methods": {},  # class_name -> [method_names]
        "imports": [],
        "constants": []
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            result["classes"].append(node.name)
            result["methods"][node.name] = [
                m.name for m in node.body 
                if isinstance(m, ast.FunctionDef)
            ]
        elif isinstance(node, ast.FunctionDef):
            result["functions"].append(node.name)
        elif isinstance(node, ast.Import):
            result["imports"].extend([a.name for a in node.names])
        elif isinstance(node, ast.ImportFrom):
            result["imports"].append(f"{node.module}")
    
    return result
```

**Markdown Structure Parsing (for .md templates):**
```python
import re

def parse_markdown_output(rendered: str) -> dict:
    """Parse rendered Markdown structure."""
    result = {
        "sections": [],      # H2 headers
        "subsections": {},   # H2 -> [H3 headers]
        "lists": [],         # Bullet/numbered list locations
        "code_blocks": [],   # Code block languages
        "tables": []         # Table headers
    }
    
    lines = rendered.split('\n')
    current_section = None
    
    for i, line in enumerate(lines):
        # H2 sections
        if line.startswith('## '):
            section = line[3:].strip()
            result["sections"].append(section)
            result["subsections"][section] = []
            current_section = section
        
        # H3 subsections
        elif line.startswith('### ') and current_section:
            subsection = line[4:].strip()
            result["subsections"][current_section].append(subsection)
        
        # Lists
        elif re.match(r'^[\*\-\+]\s', line) or re.match(r'^\d+\.\s', line):
            result["lists"].append(i + 1)  # Line number
        
        # Code blocks
        elif line.startswith('```'):
            lang = line[3:].strip()
            result["code_blocks"].append(lang or "plain")
    
    return result
```

**Integration with Issue #121:**
```python
def discover_edit_capabilities(file_path: str) -> dict:
    """Discover what ScaffoldEdit operations are supported."""
    # 1. Load template that generated this file
    template_id = extract_scaffold_metadata(file_path)
    
    # 2. Mock render with minimal context
    renderer = TemplateEngine()
    output = renderer.mock_render(template_id, mock_context={...})
    
    # 3. Parse structure
    if file_path.endswith('.py'):
        structure = parse_python_output(output)
        capabilities = {
            "append_to_list": ["imports", "methods", "fields"],
            "replace_section": structure["classes"] + structure["functions"]
        }
    elif file_path.endswith('.md'):
        structure = parse_markdown_output(output)
        capabilities = {
            "append_to_list": structure["lists"],
            "replace_section": structure["sections"]
        }
    
    return {
        "template_id": template_id,
        "edit_capabilities": capabilities,
        "structure": structure
    }
```

---

### 10. Custom Jinja2 Filters

**Q6: Which custom filters are needed?**

**✅ ANSWER: Metadata, Formatting, and Validation Filters**

**Metadata Filters (Issue #72 SCAFFOLD header):**
```python
def filter_scaffold_metadata(template_id: str, version: str) -> str:
    """Generate SCAFFOLD header line."""
    from datetime import datetime
    timestamp = datetime.now().isoformat()
    return f"# SCAFFOLD: {template_id}:{version} | {timestamp} | {{{{ output_path }}}}"

# Usage in Tier 0 template:
# {{ template_id | scaffold_metadata(template_version) }}
```

**Formatting Filters:**
```python
def filter_pascalcase(s: str) -> str:
    """Convert string to PascalCase."""
    return ''.join(word.capitalize() for word in s.split('_'))

def filter_snakecase(s: str) -> str:
    """Convert string to snake_case."""
    import re
    s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', s)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()

def filter_kebabcase(s: str) -> str:
    """Convert string to kebab-case."""
    return filter_snakecase(s).replace('_', '-')

# Usage:
# class {{ name | pascalcase }}:
# def {{ method_name | snakecase }}():
# docs/{{ title | kebabcase }}.md
```

**Validation Filters:**
```python
def filter_validate_identifier(s: str) -> str:
    """Validate Python identifier."""
    if not s.isidentifier():
        raise ValueError(f"Invalid Python identifier: {s}")
    return s

def filter_validate_path(s: str) -> str:
    """Validate file path safety."""
    from pathlib import Path
    if '..' in s or s.startswith('/'):
        raise ValueError(f"Unsafe path: {s}")
    return str(Path(s))

# Usage:
# class {{ name | validate_identifier }}:
# output: {{ output_path | validate_path }}
```

**Filter Registration:**
```python
class TemplateEngine:
    def __init__(self, ...):
        self._env = Environment(...)
        
        # Register custom filters
        self._env.filters['scaffold_metadata'] = filter_scaffold_metadata
        self._env.filters['pascalcase'] = filter_pascalcase
        self._env.filters['snakecase'] = filter_snakecase
        self._env.filters['kebabcase'] = filter_kebabcase
        self._env.filters['validate_identifier'] = filter_validate_identifier
        self._env.filters['validate_path'] = filter_validate_path
```

---

### 11. Multiple Template Roots Strategy

**Q7: How should multiple template roots be managed?**

**✅ ANSWER: ChoiceLoader with Priority Order**

**Current Implementation (Single Root):**
```python
class JinjaRenderer:
    def __init__(self, template_dir: Path):
        self._env = Environment(
            loader=FileSystemLoader(str(template_dir))
        )
```

**New Implementation (Multiple Roots):**
```python
from jinja2 import ChoiceLoader, FileSystemLoader

class TemplateEngine:
    def __init__(self, template_roots: list[Path] | None = None):
        """Initialize with multiple template roots.
        
        Args:
            template_roots: List of template directories (priority order)
                           Default: [mcp_server/templates, docs/templates]
        """
        if template_roots is None:
            base = Path(__file__).parent.parent.parent
            template_roots = [
                base / "mcp_server" / "templates",  # Priority 1
                base / "docs" / "templates"         # Priority 2
            ]
        
        # Create loader for each root
        loaders = [
            FileSystemLoader(str(root)) 
            for root in template_roots 
            if root.exists()
        ]
        
        # ChoiceLoader tries each loader in order until template found
        self._env = Environment(
            loader=ChoiceLoader(loaders)
        )
```

**Template Resolution Order:**
1. Check `mcp_server/templates/` first (scaffolding priority)
2. Check `docs/templates/` second (documentation templates)
3. Future: Check `tools/templates/` third (tool-specific)

**Namespacing Strategy:**
```python
# Explicit namespace prefix prevents collisions
renderer.get_template("scaffolding/dto.py.jinja2")  # From mcp_server/templates/
renderer.get_template("docs/design.md.jinja2")      # From docs/templates/
renderer.get_template("tools/fix-import.py.jinja2") # From tools/templates/
```

**Benefits:**
- ✅ No template name collisions (explicit namespace)
- ✅ Clear ownership (scaffolding/ vs docs/ vs tools/)
- ✅ Easy to add new roots (append to list)
- ✅ Fallback mechanism (ChoiceLoader tries all roots)

---

## Summary of Key Findings

### Critical Discoveries

1. **Circular Dependency Blocker:**
   - Current location prevents tools/ from using JinjaRenderer
   - Extract to `backend/services/template_engine.py` breaks cycle
   - **No backward compatibility needed** - only 3 import sites, direct migration

2. **Mock Rendering Solves Multiple Problems:**
   - Issue #120: Accurate optional field detection (no more hallucination)
   - Issue #121: Proactive edit capabilities discovery (40% call reduction)
   - Output structure analysis: Python AST + Markdown parsing

3. **Issue #72 Integration:**
   - 5-tier inheritance already supported via FileSystemLoader
   - Need multiple template roots support (ChoiceLoader)
   - Template registry integration required

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

**Must Implement:**
- ✅ Mock rendering with parse_python_output() and parse_markdown_output()
- ✅ Multiple template roots via ChoiceLoader
- ✅ Custom filters (pascalcase, snakecase, kebabcase, validate_identifier)
- ✅ Issue #120 integration (accurate optional detection)
- ✅ Issue #121 integration (discover_capabilities method)
- ✅ Issue #72 integration (5-tier template support)

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
| 1.1 | 2026-02-13 | Agent | Removed backward compatibility (direct migration) |
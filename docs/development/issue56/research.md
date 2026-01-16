# Issue #56: Document Templates Configuration - Research

**Date:** 2026-01-16  
**Phase:** Research  
**Branch:** refactor/documents-yaml  
**Status:** IN PROGRESS

## Objective

Externalize hardcoded document template configuration from `DocManager` to `.st3/documents.yaml`, following lessons learned from Issues #54 and #55.

## Research Findings

### 1. Primary Hardcoded Targets

#### A. TEMPLATES Dictionary
**Location:** `mcp_server/managers/doc_manager.py:18-22`

```python
TEMPLATES = {
    "architecture": "ARCHITECTURE_TEMPLATE.md",
    "design": "DESIGN_TEMPLATE.md",
    "reference": "REFERENCE_TEMPLATE.md",
    "tracking": "TRACKING_TEMPLATE.md"
}
```

**Usage:**
- `DocManager.get_template_content()` - line 191
- `DocManager.list_templates()` - line 206  
- `TemplatesResource.read()` - Exposes via MCP protocol

#### B. SCOPE_DIRS Dictionary
**Location:** `mcp_server/managers/doc_manager.py:24-30`

```python
SCOPE_DIRS = {
    "architecture": "architecture",
    "coding_standards": "coding_standards",
    "development": "development",
    "reference": "reference",
    "implementation": "implementation",
}
```

**Usage:**
- `DocManager.search_documentation()` - line 100-101
- `SearchDocumentationTool` - Pydantic pattern validation (line 22-25)

### 2. Complete Inventory

#### Document Template Types (5 types)
1. **architecture** → `ARCHITECTURE_TEMPLATE.md`
   - Jinja2: `documents/architecture.md.jinja2`
   - Scope: `architecture`
   - Statuses: DRAFT, PRELIMINARY, APPROVED, DEFINITIVE
   
2. **design** → `DESIGN_TEMPLATE.md`
   - Jinja2: `documents/design.md.jinja2`
   - Scope: `development`
   - Statuses: PRELIMINARY, APPROVED
   
3. **reference** → `REFERENCE_TEMPLATE.md`
   - Jinja2: `documents/reference.md.jinja2`
   - Scope: `reference`
   - Statuses: DEFINITIVE (always)
   
4. **tracking** → `TRACKING_TEMPLATE.md`
   - Jinja2: `documents/tracking.md.jinja2`
   - Scope: `reference`
   - Statuses: LIVING DOCUMENT (always)
   - Special: No version history
   
5. **generic** → (no reference template)
   - Jinja2: `documents/generic.md.jinja2`
   - Scope: `reference`
   - Statuses: DRAFT, APPROVED
   - Used as fallback in `DesignDocScaffolder`

#### Document Scope Directories (5 scopes)
1. **architecture** → `docs/architecture/`
2. **coding_standards** → `docs/coding_standards/`
3. **development** → `docs/development/`
4. **reference** → `docs/reference/`
5. **implementation** → `docs/implementation/`

**Special value:** `"all"` = no filtering (search all scopes)

### 3. Integration Points

#### A. Files Using TEMPLATES/SCOPE_DIRS

1. **mcp_server/managers/doc_manager.py** (PRIMARY)
   - Lines 18-30: Dict definitions
   - Line 191: Template validation
   - Line 206: Template listing
   
2. **mcp_server/resources/mcp_resources.py**
   - `TemplatesResource.read()` - Exposes `DocManager.TEMPLATES` via MCP
   - **⚠️ CRITICAL**: Direct dict exposure needs config integration
   
3. **mcp_server/tools/doc_tools.py**
   - `SearchDocumentationTool` - Scope validation pattern
   - `ValidateDocTool` - Uses DocManager
   
4. **mcp_server/scaffolding/components/doc.py**
   - `DesignDocScaffolder` - Template type routing
   - Line 38: Fallback to `generic` template

#### B. Pydantic Pattern Validations (Hardcoded)

**SearchDocumentationTool** (doc_tools.py:22-25):
```python
scope: str = Field(
    default="all",
    pattern="^(all|architecture|coding_standards|development|reference|implementation)$"
)
```

**ScaffoldDesignDocInput** (scaffold_tools.py):
```python
doc_type: str = Field(
    default="design",
    pattern="^(design|architecture|tracking|generic)$"
)
```

**Status validation** (scaffold_tools.py):
```python
status: str = Field(
    default="DRAFT",
    pattern="^(DRAFT|REVIEW|APPROVED)$"
)
```

### 4. Template File Inventory

#### Jinja2 Templates (21 files in mcp_server/templates/)

**Documents (5):**
- `documents/architecture.md.jinja2`
- `documents/design.md.jinja2`
- `documents/generic.md.jinja2`
- `documents/reference.md.jinja2`
- `documents/tracking.md.jinja2`

**Base:**
- `base_document.md.jinja2` - Base template for all docs

**Components (13):** adapter, dto, interface, service, tool, worker, etc.

#### Reference Markdown (16 files in docs/reference/templates/)
- `BASE_TEMPLATE.md` (v2.0) - Foundation for all templates
- `ARCHITECTURE_TEMPLATE.md` - Extends BASE
- `DESIGN_TEMPLATE.md` - Extends BASE
- `REFERENCE_TEMPLATE.md` - Extends BASE
- `TRACKING_TEMPLATE.md` - Different lifecycle (no BASE extension)
- Component templates (9 files): python_dto.md, python_adapter.md, etc.
- Meta docs: AI_DOC_PROMPTS.md, COMPONENTS_README.md

### 5. Key Findings & Issues

#### ⚠️ Critical Issues

1. **Status Inconsistency**
   - Code validates: `DRAFT|REVIEW|APPROVED`
   - Templates define per-type statuses:
     - Architecture: DRAFT, PRELIMINARY, APPROVED, DEFINITIVE
     - Design: PRELIMINARY, APPROVED
     - Reference: DEFINITIVE (only)
     - Tracking: LIVING DOCUMENT (only)
   - **Resolution needed**: Align code with template documentation

2. **Missing "generic" Type**
   - Not in `TEMPLATES` dict
   - Used in `DesignDocScaffolder` as fallback
   - Has Jinja2 template but no reference .md

3. **MCP Resource Direct Exposure**
   - `TemplatesResource` directly exposes `DocManager.TEMPLATES` dict
   - Needs update when externalized to config

4. **Hardcoded Pattern Validations**
   - 3 Pydantic `Field(pattern=...)` validations hardcoded
   - Need to be data-driven from config

#### 📋 Test Files

1. **tests/mcp_server/managers/test_doc_manager.py**
   - Line 162: `test_get_template_content` - uses "architecture"
   - Line 180: `test_list_templates` - uses "architecture"
   - Lines 168-170: Tests "unknown" template - expects `ValidationError`
   - Lines 185-187: Tests invalid template retrieval

2. **tests/mcp_server/tools/test_doc_tools.py**
   - Line 71: Uses "coding_standards" scope
   - Line 45: Mock result with `docs/coding_standards/` path

### 6. Lessons Learned from Issues #54, #55

#### Apply These Patterns

1. **Singleton Config Pattern** (from Issue #55)
   - Pydantic BaseModel with `_instance` class variable
   - `from_file()` classmethod for singleton loading
   - `reset_instance()` for testing/hot-reload

2. **Validation at Load Time** (from Issue #54)
   - Field validators (`@field_validator`)
   - Model validators (`@model_validator`)
   - Cross-validation between config sections
   - Fail-fast on invalid config

3. **Integration Points** (from both)
   - PolicyEngine injection pattern
   - Manager constructor injection
   - Tool instantiation with config
   - Test fixtures with config mocking

4. **Documentation Structure** (from Issue #55)
   - API reference (all fields, methods, examples)
   - User customization guide (with examples)
   - Integration testing notes
   - Known limitations documented

5. **TDD Methodology** (from Issue #55)
   - 10 TDD cycles (one per major convention)
   - Red → Green → Refactor per cycle
   - Quality gates after each refactor
   - Integration tests at end

### 7. Recommended DocumentConfig Model

```python
# mcp_server/config/document_config.py

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class TemplateType(BaseModel):
    """Document template type definition."""
    name: str = Field(description="Template type identifier")
    template_file: Optional[str] = Field(
        default=None,
        description="Reference .md file (None for generic)"
    )
    jinja_template: str = Field(description="Jinja2 template path")
    description: str = Field(description="Template purpose")
    default_scope: str = Field(description="Default scope directory")
    allowed_statuses: list[str] = Field(
        description="Valid status values for this type"
    )
    no_version_history: bool = Field(
        default=False,
        description="Skip version history section (tracking docs)"
    )
    
    @field_validator("allowed_statuses")
    @classmethod
    def validate_statuses(cls, v: list[str]) -> list[str]:
        """Ensure at least one status defined."""
        if not v:
            raise ValueError("At least one allowed status required")
        return v

class ScopeDirectory(BaseModel):
    """Document scope/category directory."""
    name: str = Field(description="Scope identifier")
    path: str = Field(description="Relative path from docs/")
    description: str = Field(description="Scope purpose")

class DocumentConfig(BaseModel):
    """Document templates configuration singleton."""
    
    _instance: Optional["DocumentConfig"] = None
    
    version: str = Field(default="1.0")
    template_types: list[TemplateType]
    scope_directories: list[ScopeDirectory]
    special_scopes: list[str] = Field(default=["all"])
    
    @field_validator("template_types")
    @classmethod
    def validate_template_names(cls, v: list[TemplateType]) -> list[TemplateType]:
        """Ensure unique template names."""
        names = [t.name for t in v]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate template names found")
        return v
    
    @field_validator("scope_directories")
    @classmethod
    def validate_scope_names(cls, v: list[ScopeDirectory]) -> list[ScopeDirectory]:
        """Ensure unique scope names."""
        names = [s.name for s in v]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate scope names found")
        return v
    
    @classmethod
    def from_file(cls, path: Optional[str] = None) -> "DocumentConfig":
        """Load config from YAML (singleton pattern)."""
        if cls._instance is not None:
            return cls._instance
        
        if path is None:
            path = ".st3/documents.yaml"
        
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        cls._instance = cls(**data)
        return cls._instance
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None
    
    def get_template_type(self, name: str) -> Optional[TemplateType]:
        """Get template type by name."""
        return next((t for t in self.template_types if t.name == name), None)
    
    def get_scope_directory(self, name: str) -> Optional[ScopeDirectory]:
        """Get scope directory by name."""
        return next((s for s in self.scope_directories if s.name == name), None)
    
    def validate_scope(self, scope: str) -> bool:
        """Check if scope is valid (directory or special)."""
        return (
            scope in self.special_scopes
            or any(s.name == scope for s in self.scope_directories)
        )
    
    def get_template_file_path(self, template_type: str) -> Optional[Path]:
        """Get reference template file path."""
        t = self.get_template_type(template_type)
        if t and t.template_file:
            return Path("docs/reference/templates") / t.template_file
        return None
    
    def get_jinja_template_path(self, template_type: str) -> Optional[str]:
        """Get Jinja2 template path."""
        t = self.get_template_type(template_type)
        return t.jinja_template if t else None
```

### 8. Recommended .st3/documents.yaml Structure

```yaml
version: "1.0"

# Document template types
template_types:
  - name: "architecture"
    template_file: "ARCHITECTURE_TEMPLATE.md"
    jinja_template: "documents/architecture.md.jinja2"
    description: "Conceptual system design documentation (300-1000 lines)"
    default_scope: "architecture"
    allowed_statuses:
      - "DRAFT"
      - "PRELIMINARY"
      - "APPROVED"
      - "DEFINITIVE"
    
  - name: "design"
    template_file: "DESIGN_TEMPLATE.md"
    jinja_template: "documents/design.md.jinja2"
    description: "Pre-implementation design documentation (300-600 lines)"
    default_scope: "development"
    allowed_statuses:
      - "PRELIMINARY"
      - "APPROVED"
    
  - name: "reference"
    template_file: "REFERENCE_TEMPLATE.md"
    jinja_template: "documents/reference.md.jinja2"
    description: "Post-implementation reference documentation (300-600 lines)"
    default_scope: "reference"
    allowed_statuses:
      - "DEFINITIVE"
    
  - name: "tracking"
    template_file: "TRACKING_TEMPLATE.md"
    jinja_template: "documents/tracking.md.jinja2"
    description: "Living project management documents"
    default_scope: "reference"
    allowed_statuses:
      - "LIVING DOCUMENT"
    no_version_history: true
    
  - name: "generic"
    template_file: null
    jinja_template: "documents/generic.md.jinja2"
    description: "Generic document fallback"
    default_scope: "reference"
    allowed_statuses:
      - "DRAFT"
      - "APPROVED"

# Document scope directories (where docs are organized)
scope_directories:
  - name: "architecture"
    path: "architecture"
    description: "Architectural concepts and system design"
    
  - name: "coding_standards"
    path: "coding_standards"
    description: "Code style, patterns, and conventions"
    
  - name: "development"
    path: "development"
    description: "Development guides and design documents"
    
  - name: "reference"
    path: "reference"
    description: "API documentation and component references"
    
  - name: "implementation"
    path: "implementation"
    description: "Implementation status and tracking"

# Special scope value for unfiltered searches
special_scopes:
  - "all"  # No directory filtering
```

### 9. Impact Analysis

#### Files to Modify (7 files)

1. **mcp_server/config/document_config.py** (NEW)
   - DocumentConfig Pydantic model
   - ~250 lines (based on GitConfig pattern)

2. **mcp_server/managers/doc_manager.py** (MODIFY)
   - Remove TEMPLATES and SCOPE_DIRS dicts
   - Add DocumentConfig injection
   - Update `get_template_content()` and `list_templates()`
   - ~50 lines modified

3. **mcp_server/resources/mcp_resources.py** (MODIFY)
   - Update `TemplatesResource.read()` to use config
   - ~10 lines modified

4. **mcp_server/tools/doc_tools.py** (MODIFY)
   - Dynamic pattern generation from config
   - ~30 lines modified

5. **mcp_server/scaffolding/components/doc.py** (MODIFY)
   - Use DocumentConfig for template routing
   - ~20 lines modified

6. **tests/mcp_server/config/test_document_config.py** (NEW)
   - Unit tests for DocumentConfig
   - ~200 lines (based on test_git_config.py pattern)

7. **tests/integration/test_doc_config_integration.py** (NEW)
   - Integration tests with DocManager
   - ~150 lines

**Total Estimated Impact:** ~710 lines of code

#### Test Coverage Plan

**Unit Tests (DocumentConfig):**
- Config loading from YAML
- Singleton pattern behavior
- Template type lookup
- Scope validation
- Invalid config handling
- Reset instance functionality

**Integration Tests:**
- DocManager with config injection
- SearchDocumentationTool with dynamic patterns
- ScaffoldDesignDocTool with config templates
- TemplatesResource with config exposure

### 10. Open Questions & Decisions Needed

1. **Status Inconsistency Resolution**
   - Keep template-specific statuses (more flexible)?
   - Or enforce common set (simpler validation)?
   - **Recommendation**: Keep template-specific (matches domain needs)

2. **"generic" Template**
   - Add to YAML with `template_file: null`?
   - Or keep as code fallback?
   - **Recommendation**: Add to YAML for consistency

3. **Backward Compatibility**
   - Existing code expects dict interface
   - Need compatibility layer or breaking change?
   - **Recommendation**: Breaking change with migration guide (like Issue #55)

4. **MCP Schema Caching**
   - Same limitation as Issue #55?
   - Need to document VS Code restart requirement?
   - **Recommendation**: Yes, document in user guide

### 11. Next Steps (Planning Phase)

1. Create detailed implementation plan
2. Design test strategy (TDD cycles)
3. Create migration plan for existing code
4. Document breaking changes
5. Transition to planning phase

---

**Research Complete** ✅  
**Ready for Planning Phase** 🚀

**Estimated Effort:** 7-10 TDD cycles, 350+ lines of code, 500+ lines of documentation (similar scope to Issue #55)

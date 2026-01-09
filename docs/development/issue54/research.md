# Issue #54 Research: Scaffold Rules Configuration

**Date:** 2026-01-09  
**Author:** GitHub Copilot (Claude Sonnet 4.5)  
**Status:** DRAFT  
**Issue:** #54 - Config: Scaffold Rules Configuration (scaffold.yaml)  
**Parent:** Epic #49 - MCP Platform Configurability

---

## Executive Summary

**Critical Finding:** "Scaffold configuration" is a misnomer. This issue encompasses THREE distinct configuration domains:

1. **Component Registry** - What can be scaffolded (9 types)
2. **File Creation Policies** - What requires scaffolding vs direct creation
3. **Scaffolding Phase Policies** - When scaffolding is allowed (design/tdd phases)

These domains have **different consumers**, **different purposes**, and **different reusability patterns**. Treating them as one "scaffold.yaml" would violate SRP.

**Architectural Insight:** Scaffolding is not simple file creation - it's an **architectural enforcement system** that uses templates to encode project patterns and validates compliance through metadata-driven rules.

---

## Epic Context

**Parent:** Epic #49 - MCP Platform Configurability  
**Sibling Issues:**
- #50 workflows.yaml ✅ Workflow definitions (feature/bug/docs/refactor/hotfix)
- #51 labels.yaml ✅ GitHub label management
- #52 validation.yaml ✅ Template validation rules  
- #53 quality.yaml ✅ Quality gate configuration

**Epic Goal:** Externalize all hardcoded configuration to YAML files in `.st3/` directory for runtime configurability without code changes.

**Progress:** 4/5 sibling issues closed, #54 remaining.

---

## 1. What IS Scaffolding?

### 1.1 Scaffolding vs File Creation - Fundamental Distinction

**Scaffolding is:**
- **Template-driven:** Uses Jinja2 with inheritance (base templates)
- **Metadata-enriched:** Templates contain YAML frontmatter with validation rules
- **Architecturally enforced:** Generates code following project patterns
- **Convention-applying:** Auto-derives values (e.g., id_prefix from DTO name)
- **Type-specific:** Different logic for DTOs, Workers, Adapters, Tools, etc.
- **Validated:** Output validated against template metadata (3-tier validation)

**Simple File Creation (create_file) is:**
- **Direct string → file:** No templates
- **No validation:** No pattern enforcement
- **Ad-hoc structure:** Manual convention application
- **Deprecated reason:** Bypasses architectural standards

**Key Insight:** Scaffolding is an **architectural enforcement system**, not a convenience wrapper around file I/O.

### 1.2 File Type Distinction

| File Type | Directories | Tool | Rationale |
|-----------|------------|------|-----------|
| **Backend Code** | backend/**, mcp_server/** | scaffold_component | Architectural patterns (DTOs immutable, Workers executor pattern) |
| **Test Code** | tests/** | scaffold_component | Consistency with CODE_STYLE.md standards |
| **Documentation** | docs/** | scaffold_design_doc | Structure enforcement (frontmatter, sections) |
| **Configuration** | .st3/**, config/** | create_file / safe_edit | No architectural patterns, external schemas (YAML, JSON) |
| **Scripts** | scripts/** | create_file | Ad-hoc, experimental, no patterns |
| **Proof of Concepts** | proof_of_concepts/** | create_file | Experimental, no constraints |

**PolicyEngine Enforcement:**
```python
# Blocked: MUST use scaffold
blocked_patterns = [
    ("backend", ".py"),     # Backend code follows architecture
    ("tests", ".py"),       # Tests follow conventions  
    ("mcp_server", ".py"),  # MCP tools/workers follow patterns
]

# Allowed: CAN use create_file
allowed_extensions = {".yml", ".yaml", ".json", ".toml", ".ini", ".txt", ".md", ".lock"}
allowed_dirs = {"scripts", "proof_of_concepts", "docs", "config", ".st3"}
```

---

## 2. Scaffolding System Architecture

### 2.1 Component Hierarchy

```
mcp_server/scaffolding/
├── base.py                    # BaseScaffolder, ScaffoldResult, ComponentScaffolder (Protocol)
├── renderer.py                # JinjaRenderer (template engine)
├── utils.py                   # validate_pascal_case(), write_scaffold_file()
└── components/
    ├── dto.py                 # DTOScaffolder - Immutable Pydantic models
    ├── worker.py              # WorkerScaffolder - Background workers  
    ├── adapter.py             # AdapterScaffolder - External service adapters
    ├── tool.py                # ToolScaffolder - MCP tools
    ├── resource.py            # ResourceScaffolder - MCP resources
    ├── schema.py              # SchemaScaffolder - Pydantic schemas
    ├── interface.py           # InterfaceScaffolder - Protocol definitions
    ├── service.py             # ServiceScaffolder - Service layer (3 subtypes)
    ├── generic.py             # GenericScaffolder - Generic Python from templates
    ├── doc.py                 # DesignDocScaffolder - Markdown documents
    └── test.py                # TestScaffolder - Test file generation
```

### 2.2 Template System

**Templates Location:** `mcp_server/templates/`

**Structure:**
```
templates/
├── base/
│   ├── base_component.py.jinja2   # All Python components extend this
│   ├── base_document.md.jinja2    # All docs extend this
│   └── base_test.py.jinja2        # All tests extend this
├── components/
│   ├── dto.py.jinja2              # DTO specific (extends base_component)
│   ├── worker.py.jinja2
│   ├── adapter.py.jinja2
│   └── ...
└── documents/
    ├── design.md.jinja2
    ├── architecture.md.jinja2
    └── generic.md.jinja2
```

**Template Features:**
1. **Inheritance:** `{% extends "base/base_component.py.jinja2" %}`
2. **Metadata:** YAML frontmatter with validation rules
3. **Variables:** Name, fields, docstring, layer, etc.

**Template Metadata Example:**
```jinja2
{# TEMPLATE_METADATA
enforcement: ARCHITECTURAL
level: content
extends: base/base_component.py.jinja2
version: "2.0"

validates:
  strict:
    - rule: base_class
      description: "Must inherit from BaseModel"
      pattern: "class \\w+\\(BaseModel\\)"
      severity: ERROR

purpose: |
  Generate immutable Pydantic DTOs following project conventions.

variables:
  - name
  - fields
  - docstring
#}
```

### 2.3 Data Flow

```
User Request (MCP)
    ↓
ScaffoldComponentTool / ScaffoldDesignDocTool
    ↓
ComponentScaffolder (dto, worker, adapter, etc.)
    ↓
JinjaRenderer.render(template_name, **variables)
    ↓
Template (components/dto.py.jinja2 extends base/base_component.py.jinja2)
    ↓
Generated Content (string)
    ↓
write_scaffold_file(path, content, overwrite)
    ↓
File Created on Disk
    ↓
(Later) ValidationService validates against template metadata
```

---

## 3. Hardcoded Rules Inventory

### 3.1 Component Types (scaffold_tools.py Lines 100-115)

**9 Component Types:**
```python
self.scaffolders: dict[str, ComponentScaffolder] = {
    "dto": DTOScaffolder(self.renderer),
    "worker": WorkerScaffolder(self.renderer),
    "adapter": AdapterScaffolder(self.renderer),
    "tool": ToolScaffolder(self.renderer),
    "resource": ResourceScaffolder(self.renderer),
    "schema": SchemaScaffolder(self.renderer),
    "interface": InterfaceScaffolder(self.renderer),
    "service": ServiceScaffolder(self.renderer),
    "generic": GenericScaffolder(self.renderer),
}
```

**Also Hardcoded:**
- Handlers dict (Lines 125-145): Maps component_type to methods
- Error message hints (Line 147): Lists all component types

**Consumer:** ScaffoldComponentTool (MCP tool)

**Configuration Scope:** Component registry - what CAN be scaffolded

### 3.2 Scaffold Phase Policies (policy_engine.py Lines 142-157)

**Allowed Phases:**
```python
def _decide_scaffold(self, ctx: DecisionContext) -> PolicyDecision:
    allowed_phases = {"design", "tdd"}  # HARDCODED
    
    if ctx.phase in allowed_phases:
        return PolicyDecision(allowed=True, ...)
    return PolicyDecision(allowed=False, ...)
```

**Rationale:** Scaffolding generates new components - only allowed during design/implementation, not research/documentation/integration phases.

**Consumer:** PolicyEngine (core enforcement)

**Configuration Scope:** Workflow policies - WHEN scaffolding is allowed

### 3.3 File Creation Policies (policy_engine.py Lines 165-200)

**Blocked Patterns (require scaffold):**
```python
blocked_patterns = [
    ("backend", ".py"),      # backend/**/*.py must use scaffold
    ("tests", ".py"),        # tests/**/*.py must use scaffold  
    ("mcp_server", ".py"),   # mcp_server/**/*.py must use scaffold
]
```

**Allowed Extensions (can use create_file):**
```python
allowed_extensions = {".yml", ".yaml", ".json", ".toml", ".ini", ".txt", ".md", ".lock"}
```

**Allowed Directories (can use create_file):**
```python
allowed_dirs = {"scripts", "proof_of_concepts", "docs", "config", ".st3"}
```

**Consumer:** PolicyEngine._decide_create_file() (file creation enforcement)

**Configuration Scope:** File policies - WHAT files require scaffolding vs direct creation

---

## 4. Policy Analysis - Three Distinct Domains

### 4.1 Domain 1: Component Registry

**What:** Mapping of component_type → ComponentScaffolder  
**Purpose:** Define what CAN be scaffolded  
**Current Location:** scaffold_tools.py (hardcoded dict)  
**Consumer:** ScaffoldComponentTool  

**Characteristics:**
- Dynamic: Could add new component types (e.g., "manager", "entity")
- Type-specific: Each has unique scaffolder implementation
- Tool-facing: Exposed via MCP tool schema

**Example:** User calls `scaffold_component(component_type="dto")` → routed to DTOScaffolder

### 4.2 Domain 2: File Creation Policies

**What:** Rules for which files REQUIRE scaffolding vs allow direct creation  
**Purpose:** Enforce architectural patterns on code, allow flexibility for config/scripts  
**Current Location:** policy_engine.py (_decide_create_file method)  
**Consumer:** PolicyEngine (validates all file creation operations)

**Characteristics:**
- Path-based: Enforces based on directory + extension
- Binary decision: Scaffold required OR create_file allowed
- Security-adjacent: Prevents bypassing architectural standards

**Example:** User tries `create_file("backend/foo.py")` → blocked, must use scaffold

**Sub-domains:**
1. **Blocked patterns** - Files that MUST use scaffold (backend/**.py, tests/**.py)
2. **Allowed extensions** - File types that CAN use create_file (.yml, .json)
3. **Allowed directories** - Paths that CAN use create_file (scripts/, docs/)

### 4.3 Domain 3: Scaffolding Phase Policies

**What:** Workflow phases where scaffolding is permitted  
**Purpose:** Enforce scaffolding only during design/implementation, not maintenance  
**Current Location:** policy_engine.py (_decide_scaffold method)  
**Consumer:** PolicyEngine (validates scaffold operations against current phase)

**Characteristics:**
- Phase-based: Allowed in {design, tdd}, blocked in {research, integration, documentation}
- Workflow-coupled: Depends on project workflow definition (Epic #49, Issue #50)
- Temporal: Changes throughout issue lifecycle

**Example:** Current phase = "research" → scaffold_component() blocked

---

## 5. SRP/DRY Analysis

### 5.1 SRP Violations

**Violation #1: ScaffoldComponentTool - Too Many Responsibilities**

**Location:** scaffold_tools.py  
**Mixes 6 concerns:**
1. **Routing:** component_type → handler method
2. **Validation:** Required fields per component type
3. **Execution:** Calling scaffolder
4. **File writing:** write_scaffold_file()
5. **Test generation:** DTOs get automatic test files
6. **Result formatting:** Creating ToolResult

**Analysis:** Tool is a **coordinator** but does too much. Test generation should be in DTOScaffolder, file writing abstracted.

**Violation #2: write_scaffold_file - Mixes I/O and Security**

**Location:** scaffolding/utils.py  
**Mixes 3 concerns:**
1. **Path resolution:** workspace_root / relative_path
2. **Security validation:** Overwrite checks, workspace boundaries
3. **File system I/O:** mkdir, file write

**Analysis:** Should delegate security to `WorkspaceSecurityValidator`, use generic `FileWriter`.

**Violation #3: Component Scaffolders - Mixed Business Logic and Template Selection**

**Location:** All scaffolders (dto.py, worker.py, etc.)  
**Mixes 4 concerns:**
1. **Name conventions:** Suffix logic (e.g., "Worker" suffix)
2. **Auto-derivation:** id_prefix calculation, module paths
3. **Template selection:** Main template + fallback
4. **Rendering:** Delegates to JinjaRenderer

**Analysis:** Template selection and fallback could be extracted to `TemplateResolver` class.

### 5.2 DRY Violations

**Duplication #1: Fallback Template Logic (8 instances)**

**Location:** All component scaffolders

**Pattern:**
```python
try:
    return self.renderer.render("components/dto.py.jinja2", ...)
except Exception as e:
    if "not found" in str(e).lower():
        return self.renderer.render("components/generic.py.jinja2", ...)
    raise
```

**Repeated in:** dto.py, worker.py, adapter.py, tool.py, resource.py, schema.py, interface.py, service.py

**Solution Opportunity:** Extract to BaseScaffolder.render_with_fallback()

**Duplication #2: Name Suffix Logic (4 instances)**

**Location:** WorkerScaffolder, AdapterScaffolder, ToolScaffolder, ServiceScaffolder

**Pattern:**
```python
worker_name = name if name.endswith("Worker") else f"{name}Worker"
adapter_name = name if name.endswith("Adapter") else f"{name}Adapter"
tool_name = name if name.endswith("Tool") else f"{name}Tool"
service_name = name if name.endswith("Service") else f"{name}Service"
```

**Solution Opportunity:** Extract to utility function `ensure_suffix(name, suffix)`

**Duplication #3: Test Path Derivation**

**Location:** ScaffoldComponentTool._scaffold_dto()

**Code:**
```python
test_path = params.output_path.replace(".py", "_test.py")
if "backend/" in test_path:
    test_path = test_path.replace("backend/", "tests/unit/")
```

**Analysis:** Project structure knowledge (backend/ → tests/unit/) hardcoded. Could be `PathResolver` utility.

**Duplication #4: Module Path Derivation**

**Location:** Multiple scaffolders

**Code:**
```python
module_path = params.output_path.replace("/", ".").replace("\\", ".").rstrip(".py")
```

**Analysis:** Common transformation (file path → Python module path) appears in multiple contexts.

---

## 6. Reusability Analysis

### 6.1 JinjaRenderer - HIGH Reusability

**Current State:** Scaffolding-specific  
**Potential Uses:**
1. **safe_edit_tool:** Apply templates to fix code patterns
   - Example: "Convert this class to DTO pattern" → render dto.py.jinja2
2. **Quality tools:** Generate fix suggestions from templates
   - Example: Pylint "Add docstring" → render docstring template
3. **Documentation generators:** Already used for docs/, could expand
4. **Test generators:** Generate tests from code analysis (beyond DTOs)

**Extraction Path:**
```
mcp_server/scaffolding/renderer.py
  → mcp_server/core/template_engine.py (generic)
    → Used by: scaffolding, safe_edit, quality_tools, docs_tools
```

**Configuration Needs:**
- Multiple template roots (scaffolding/, fixes/, docs/)
- Template namespaces (avoid name collisions)
- Custom Jinja2 filters (to_snake_case, to_pascal_case, derive_module_path)

### 6.2 Validation System - ALREADY Reusable

**Current State:** Decoupled from scaffolding

**Components:**
- **LayeredTemplateValidator:** Validates code against template metadata
- **TemplateAnalyzer:** Extracts metadata from templates (YAML frontmatter)
- **ValidationService:** Orchestrates multiple validators

**Current Uses:**
- safe_edit_tool: Validates edits before saving
- (Future) Quality gates: Run as CI/CD check

**Reusability Score:** HIGH - Already abstracted, just needs wider adoption

### 6.3 File Operations - MEDIUM Reusability

**Current State:** Scattered utilities

**Consolidation Opportunity:**
```python
# mcp_server/core/file_operations.py
class FileOperations:
    @staticmethod
    def write_file(path, content, workspace_root, overwrite=False):
        """Generic file write with security checks"""
        
    @staticmethod
    def derive_test_path(code_path):
        """backend/foo.py → tests/unit/foo_test.py"""
        
    @staticmethod
    def derive_module_path(file_path):
        """backend/foo.py → backend.foo"""
        
    @staticmethod
    def ensure_suffix(name, suffix):
        """Ensure name ends with suffix"""
```

**Benefit:** DRY compliance, single source of truth for project structure knowledge

### 6.4 Template Metadata - HIGH Reusability

**Current State:** Used by LayeredTemplateValidator

**Potential Uses:**
1. **Documentation generation:** Extract template purpose/variables
2. **IDE autocomplete:** Show available templates with metadata
3. **Template linting:** Validate template metadata itself
4. **Agent guidance:** Provide context on when to use each template

**Already Abstracted:** Yes (TemplateAnalyzer in mcp_server/validation/)

---

## 7. Lessons Learned from Sibling Issues

### 7.1 Issue #51 (labels.yaml) - Singleton Pattern

**Pattern:**
```python
class LabelsConfig(BaseModel):
    version: str
    labels: dict[str, LabelDef]
    
    _instance: ClassVar["LabelsConfig | None"] = None
    
    @classmethod
    def load(cls, config_path: Path | None = None) -> "LabelsConfig":
        if cls._instance is None:
            # Load YAML + Pydantic validation
            cls._instance = ...
        return cls._instance
```

**Key Takeaways:**
- Singleton ensures single source of truth
- Pydantic validation catches config errors early
- ClassVar + load() classmethod for lazy initialization
- 100% test coverage requirement

### 7.2 Issue #52 (validation.yaml) - Nested Models

**Pattern:**
```python
class TemplateRule(BaseModel):
    """Rule for single template type."""
    required_sections: list[str]
    optional_sections: list[str]

class ValidationConfig(BaseModel):
    """Validation rules for all templates."""
    version: str
    rules: dict[str, TemplateRule]  # Keyed by template type
```

**Key Takeaways:**
- Nested Pydantic models for complex structures
- Dict[str, Model] for type-specific rules
- Complete migration - no hardcoded fallbacks
- Tests ensure config loading works before deployment

### 7.3 Common Patterns Across All Issues

1. **File Location:** `.st3/` directory (NOT `config/`)
2. **Pydantic Validation:** Always use Pydantic models
3. **Singleton Pattern:** ClassVar + load() classmethod
4. **Test Coverage:** 100% requirement
5. **Documentation:** Reference docs in main documentation
6. **No Fallbacks:** Remove hardcoded values completely after migration

---

## 8. Critical Question: One Config or Three?

### 8.1 Current Assumption (Issue Title)

**Issue #54:** "Config: Scaffold Rules Configuration (scaffold.yaml)"

**Implies:** Single `.st3/scaffold.yaml` file

### 8.2 Three Distinct Configuration Domains

**Domain 1: Component Registry**
- **Consumer:** ScaffoldComponentTool
- **Purpose:** What can be scaffolded
- **Structure:** Flat list or dict
- **Coupling:** Tool-specific (MCP)

**Domain 2: File Creation Policies**
- **Consumer:** PolicyEngine
- **Purpose:** What files require scaffolding vs allow direct creation
- **Structure:** Nested (blocked_patterns, allowed_extensions, allowed_directories)
- **Coupling:** Security/enforcement layer

**Domain 3: Scaffolding Phase Policies**
- **Consumer:** PolicyEngine
- **Purpose:** When scaffolding is allowed (workflow phases)
- **Structure:** Set of phase names
- **Coupling:** Workflow system (Issue #50)

### 8.3 Architectural Decision Required

**Option A: Single `.st3/scaffold.yaml`**
```yaml
# .st3/scaffold.yaml
version: "1.0"

component_types:  # Domain 1
  - dto
  - worker
  - adapter

allowed_phases:   # Domain 3
  - design
  - tdd

file_policies:    # Domain 2
  blocked_patterns: [...]
  allowed_extensions: [...]
```

**Pros:** All scaffold-related config in one file  
**Cons:** Mixes three responsibilities, violates SRP, different consumers

**Option B: Three Separate Config Files**
```yaml
# .st3/components.yaml (Domain 1 - Component Registry)
version: "1.0"
scaffoldable_types:
  - dto
  - worker
  - adapter

# .st3/policies.yaml (Domain 2 - File Creation Policies)
version: "1.0"
file_creation:
  require_scaffold: [...]
  allow_create_file: [...]

# .st3/workflows.yaml (Domain 3 - Already exists from Issue #50!)
# Scaffolding phase policy is workflow-specific, already configured
```

**Pros:** SRP compliance, clear consumer boundaries  
**Cons:** More files (but each focused)

**Option C: Merge Domain 2 with Existing Policy System**
```yaml
# .st3/policies.yaml (NEW - file creation policies)
# Domain 2 - File policies (blocked/allowed patterns)

# .st3/components.yaml (NEW - component registry)
# Domain 1 - Scaffoldable components

# .st3/workflows.yaml (EXISTS - from Issue #50)
# Domain 3 - Phase policies (scaffolding allowed in design/tdd)
```

**Pros:** Aligns with existing Epic #49 structure, no duplication  
**Cons:** Domain 3 already solved by Issue #50

---

## 9. Relationship to Existing Configuration

### 9.1 workflows.yaml (Issue #50) - ALREADY HANDLES PHASE POLICIES

**Current Content:**
```yaml
# .st3/workflows.yaml
workflows:
  feature:
    phases:
      - research
      - planning
      - design       # ← Scaffolding allowed
      - tdd          # ← Scaffolding allowed
      - integration
      - documentation
```

**Insight:** Scaffolding phase policies (Domain 3) are **already configured** via workflow definitions!

**PolicyEngine Logic:**
```python
# Current (hardcoded):
allowed_phases = {"design", "tdd"}

# Should be (from workflow config):
workflow = WorkflowConfig.load()
current_workflow = workflow.workflows[project.workflow_name]
allowed_phases = {"design", "tdd"}  # Still hardcoded, but could reference workflow phases
```

**Question:** Should scaffolding phase policies be:
1. **Workflow-specific** - Each workflow defines scaffolding phases
2. **Global** - Scaffolding always allowed in {"design", "tdd"} regardless of workflow
3. **Hybrid** - Default {"design", "tdd"}, overridable per workflow

### 9.2 validation.yaml (Issue #52) - ALREADY HANDLES TEMPLATE VALIDATION

**Current Content:**
```yaml
# .st3/validation.yaml
version: "1.0"
rules:
  dto:
    required_sections: [...]
  worker:
    required_sections: [...]
```

**Insight:** Template validation rules are **already externalized** in Issue #52.

**Not in Scope for Issue #54:** Template validation metadata (handled by validation.yaml + template YAML frontmatter).

---

## 10. Unresolved Questions for Planning Phase

### 10.1 Configuration Scope

**Q1:** Should Issue #54 cover:
- ✅ Component registry (what can be scaffolded)
- ✅ File creation policies (what requires scaffolding)
- ❓ Scaffolding phase policies (when scaffolding allowed) - OR is this workflow-specific (Issue #50)?

**Q2:** One config file (`.st3/scaffold.yaml`) or three (components.yaml, policies.yaml, workflows.yaml extension)?

### 10.2 Policy Granularity

**Q3:** File creation policies - should they be:
- **Pattern-based** (current: directory + extension tuples)
- **Glob-based** (e.g., `backend/**/*.py`)
- **Regex-based** (e.g., `^backend/.*\.py$`)
- **Path-based** (e.g., list of exact paths)

**Q4:** Should policies support **exclusions**?  
Example: `backend/**/*.py` requires scaffold EXCEPT `backend/utils/**/*.py` (utility scripts)

### 10.3 Component Registry Extensibility

**Q5:** How should custom component types be added?
- **Via config** (register scaffolder class path)
- **Via plugins** (dynamic loading)
- **Manual** (code change + config update)

**Q6:** Should component types have metadata in config?  
Example:
```yaml
component_types:
  dto:
    description: "Data Transfer Objects"
    scaffolder: "mcp_server.scaffolding.components.dto.DTOScaffolder"
    template: "components/dto.py.jinja2"
    generates_test: true
```

### 10.4 Herbruikbaarheid Template System

**Q7:** Should JinjaRenderer be extracted to `mcp_server/core/template_engine.py` for reuse by:
- safe_edit_tool (apply templates to fix code)
- Quality tools (generate fix suggestions)
- Documentation generators

**Q8:** Should validation system be promoted to top-level service used by:
- Scaffolding (current)
- Quality gates (future)
- CI/CD (future)
- Pre-commit hooks (future)

### 10.5 SRP/DRY Refactoring

**Q9:** Should Issue #54 also address:
- **DRY violations** (fallback logic, suffix logic)
- **SRP violations** (ScaffoldComponentTool responsibilities)
- **File operation consolidation** (test path derivation, module path)

Or defer these to separate refactoring issue?

**Q10:** Should file operations be extracted to `mcp_server/core/file_operations.py` with utilities:
- `derive_test_path()`
- `derive_module_path()`
- `ensure_suffix()`
- `write_file()` (with security)

---

## 11. Research Conclusions

### 11.1 Core Findings

1. **Scaffolding ≠ File Creation**
   - Scaffolding is architectural enforcement through templates
   - File creation is data output without patterns
   - Distinction is clear and justified by project needs

2. **Three Configuration Domains**
   - Component registry (what can be scaffolded)
   - File creation policies (what requires scaffolding)
   - Scaffolding phase policies (when scaffolding allowed)
   - These have different consumers and purposes

3. **Domain 3 Already Solved**
   - Scaffolding phase policies are workflow-specific
   - Already configured in `.st3/workflows.yaml` (Issue #50)
   - PolicyEngine should reference workflow config, not hardcode {"design", "tdd"}

4. **Reusability Opportunities**
   - JinjaRenderer: HIGH (template system for safe_edit, quality tools)
   - Validation: HIGH (already abstracted, wider adoption needed)
   - File operations: MEDIUM (consolidation opportunity)
   - Template metadata: HIGH (documentation, IDE tooling)

5. **SRP/DRY Violations Exist**
   - Fallback template logic duplicated 8 times
   - Suffix logic duplicated 4 times
   - ScaffoldComponentTool mixes too many concerns
   - write_scaffold_file mixes I/O and security

### 11.2 Architectural Insights

**Insight #1:** "Scaffold configuration" is too broad - encompasses component registry, file policies, and workflow policies.

**Insight #2:** File creation policies (`blocked_patterns`, `allowed_extensions`) are **general enforcement**, not scaffold-specific - they determine when scaffolding is REQUIRED vs when direct creation is ALLOWED.

**Insight #3:** Template system (Jinja2) is **highly reusable** - currently locked in scaffolding but could power safe_edit, quality tools, and documentation generation.

**Insight #4:** Validation is already well-abstracted (LayeredTemplateValidator, TemplateAnalyzer) but underutilized - should be quality gate, CI/CD check, pre-commit hook.

**Insight #5:** Project structure knowledge (backend/ → tests/unit/, file path → module path) is **scattered** - should be centralized in PathResolver utility.

### 11.3 Planning Phase Prerequisites

Before moving to planning, must resolve:

1. **Configuration scope:** One file or three?
2. **Domain 3 handling:** Extend workflows.yaml or new config?
3. **Policy granularity:** Pattern vs glob vs regex?
4. **Component extensibility:** Via config or manual?
5. **Refactoring scope:** Address SRP/DRY in Issue #54 or defer?

---

## 12. Four Config Domains - Detailed Analysis

Based on user vision: **"Wat waar mag en wanneer!"** - we need FOUR separate configs (SRP):

### 12.1 Domain 1: WAT (Component Registry)

**Purpose:** Define what CAN be scaffolded  
**Config File:** `.st3/components.yaml` (NEW)  
**Consumer:** ScaffoldComponentTool

**Current State:**
- Hardcoded in scaffold_tools.py (9 types)
- Dict maps component_type → ComponentScaffolder instance
- Error hints list all types

**Required Metadata per Component:**
```yaml
# .st3/components.yaml
version: "1.0"

component_types:
  dto:
    description: "Immutable Pydantic Data Transfer Objects"
    scaffolder_class: "mcp_server.scaffolding.components.dto.DTOScaffolder"
    template: "components/dto.py.jinja2"
    generates_test: true
    category: "backend"  # For grouping/filtering
    
  worker:
    description: "Background workers following executor pattern"
    scaffolder_class: "mcp_server.scaffolding.components.worker.WorkerScaffolder"
    template: "components/worker.py.jinja2"
    generates_test: false
    category: "backend"
```

**Config References:**
- ← Referenced by: project_structure.yaml (allowed_components per directory)
- → References: None (leaf config)

**Issue #54 Scope:**
- ✅ Create components.yaml
- ✅ ComponentRegistryConfig Pydantic model (singleton)
- ✅ Refactor ScaffoldComponentTool to use registry

### 12.2 Domain 2: WAAR (Project Structure)

**Purpose:** Define what's allowed WHERE (directory policies)  
**Config File:** `.st3/project_structure.yaml` (NEW)  
**Consumer:** PolicyEngine._decide_create_file(), ScaffoldComponentTool (path validation)

**Current State:**
- Implicit structure (directories exist but not documented)
- PolicyEngine has hardcoded blocked_patterns, allowed_extensions, allowed_dirs
- No declarative definition of project layout

**Current Project Structure:**
```
SimpleTraderV3/
├── backend/        # Backend code (DTOs, Workers, Adapters, Services)
├── mcp_server/     # MCP tools, scaffolding, validation, core
├── tests/          # Test suite (unit, integration, e2e)
├── docs/           # Documentation (coding standards, reference, development)
├── scripts/        # Utility scripts (ad-hoc, no patterns)
├── proof_of_concepts/  # Experimental code
├── .st3/           # Platform configuration
└── tmp/            # Temporary files
```

**Required Structure Definition:**
```yaml
# .st3/project_structure.yaml
version: "1.0"

directories:
  backend:
    description: "Backend application code (DTOs, Workers, Adapters, Services)"
    allowed_component_types: [dto, worker, adapter, service]  # References components.yaml
    allowed_extensions: [.py]
    require_scaffold_for:
      - pattern: "**/*.py"
        reason: "Backend code must follow architectural patterns"
    subdirectories:
      dtos:
        allowed_component_types: [dto]
      workers:
        allowed_component_types: [worker]
      adapters:
        allowed_component_types: [adapter]
  
  mcp_server:
    description: "MCP server platform (tools, scaffolding, core)"
    allowed_component_types: [tool, resource, worker]
    allowed_extensions: [.py]
    require_scaffold_for:
      - pattern: "**/*.py"
        reason: "MCP components must follow tool/resource patterns"
  
  tests:
    description: "Test suite (unit, integration, e2e)"
    allowed_component_types: [test]
    allowed_extensions: [.py]
    require_scaffold_for:
      - pattern: "**/*.py"
        reason: "Tests must follow project conventions"
  
  docs:
    description: "Documentation (markdown, diagrams)"
    allowed_component_types: [doc]  # scaffold_design_doc
    allowed_extensions: [.md, .rst, .png, .svg, .drawio]
    require_scaffold_for: []  # Markdown can be created directly
  
  .st3:
    description: "Platform configuration (YAML/JSON only)"
    allowed_component_types: []  # No scaffolding
    allowed_extensions: [.yml, .yaml, .json]
    require_scaffold_for: []
  
  scripts:
    description: "Utility scripts (no restrictions)"
    allowed_component_types: [generic]  # Generic scaffolding allowed
    allowed_extensions: [.py, .sh, .ps1, .bat]
    require_scaffold_for: []  # Ad-hoc scripts, no enforcement
  
  proof_of_concepts:
    description: "Experimental code (no restrictions)"
    allowed_component_types: [generic]
    allowed_extensions: []  # Any extension
    require_scaffold_for: []  # No enforcement
```

**Config References:**
- → References: components.yaml (allowed_component_types)
- ← Referenced by: policies.yaml (directory-specific phase policies - future)

**Issue #54 Scope:**
- ✅ Create project_structure.yaml (describe CURRENT project)
- ✅ ProjectStructureConfig Pydantic model (singleton)
- ✅ DirectoryPolicy model (nested)
- ✅ Refactor PolicyEngine._decide_create_file() to use config
- ✅ Add directory validation to ScaffoldComponentTool

### 12.3 Domain 3: WANNEER (Phase Policies)

**Purpose:** Define what's allowed WHEN (phase-based restrictions)  
**Config File:** `.st3/policies.yaml` (NEW)  
**Consumer:** PolicyEngine._decide_scaffold(), future enforcement tools

**Current State:**
- Workflows.yaml (Issue #50) defines phase sequences
- PolicyEngine has hardcoded allowed_phases for scaffold (design, tdd)
- No declarative phase policy mapping

**Relationship to workflows.yaml:**
```yaml
# .st3/workflows.yaml (EXISTS - Issue #50)
workflows:
  feature:
    phases: [research, planning, design, tdd, integration, documentation]
  bug:
    phases: [research, planning, design, tdd, integration, documentation]
  refactor:
    phases: [research, planning, tdd, integration, documentation]  # No design
  hotfix:
    phases: [tdd, integration, documentation]  # Emergency, minimal
```

**New policies.yaml:**
```yaml
# .st3/policies.yaml
version: "1.0"

# Operation policies (WHEN operations are allowed)
operations:
  scaffold:
    description: "Component scaffolding (create new code structures)"
    allowed_phases: [design, tdd]  # Scaffolding only during creation
    reason: "Scaffolding is for new components, not maintenance"
  
  create_file:
    description: "Direct file creation (config, scripts, docs)"
    allowed_phases: []  # Empty = allowed in ALL phases
    reason: "Config/script creation needed throughout workflow"
  
  commit:
    description: "Git commit operations"
    allowed_phases: []  # Empty = allowed in ALL phases
    require_tdd_prefix: true  # Enforced via _decide_commit
    valid_prefixes: [red, green, refactor, docs]

# Directory-specific phase policies (CONFIG defined in Issue #54, ENFORCED in Epic #18)
directory_policies:
  backend:
    research:
      allowed_operations: []  # No code changes in research
      reason: "Research phase is for analysis, not implementation"
    planning:
      allowed_operations: []  # No code changes in planning
      reason: "Planning phase is for design decisions, not code"
    design:
      allowed_operations: [scaffold]  # Only scaffolding, no implementation
      reason: "Design phase creates structure, not implementation"
    tdd:
      allowed_operations: [scaffold, edit, commit]  # Full implementation
      reason: "TDD phase is for implementation with test-driven development"
    integration:
      allowed_operations: [edit, commit]  # No new scaffolding
      reason: "Integration phase refines existing code"
    documentation:
      allowed_operations: []  # No code changes in documentation
      reason: "Documentation phase is for docs/, not code"
  
  docs:
    research:
      allowed_operations: [create_file, edit, commit]  # Research docs
    planning:
      allowed_operations: [create_file, scaffold, edit, commit]  # Planning docs
    design:
      allowed_operations: [create_file, scaffold, edit, commit]  # Design docs
    # All phases allow documentation
    
  .st3:
    # Config changes allowed in all phases
    allowed_operations: [create_file, edit, commit]
```

**Config References:**
- → References: workflows.yaml (phase names must exist in workflows)
- ← Referenced by: PolicyEngine (enforcement)

**Issue #54 Scope:**
- ✅ Create policies.yaml (operation-level policies)
- ✅ OperationPoliciesConfig Pydantic model (singleton)
- ✅ Refactor PolicyEngine._decide_scaffold() to use config
- ✅ Include directory-specific phase policies in CONFIG (define the rules)
- ❌ DEFER: ENFORCEMENT of directory-specific policies (Epic #18 - enforce the rules)

### 12.4 Domain 4: HOE (Scaffold Configuration)

**Purpose:** Define HOW scaffolding works (templates, validation, rendering)  
**Config Files:** Template metadata (YAML frontmatter), validation.yaml (Issue #52)  
**Consumer:** Scaffolding system, ValidationService

**Current State:**
- ✅ Templates have YAML frontmatter (validation rules, purpose, variables)
- ✅ validation.yaml exists (Issue #52) - template validation rules
- ✅ JinjaRenderer handles template loading and rendering
- ✅ LayeredTemplateValidator uses template metadata

**Analysis:** This domain is ALREADY SOLVED by:
1. Template YAML frontmatter (embedded in .jinja2 files)
2. validation.yaml (Issue #52 - template-specific validation rules)
3. JinjaRenderer (template rendering engine)

**Issue #54 Scope:**
- ❌ NO NEW CONFIG - already handled by Issue #52 + template metadata
- ✅ Document relationship to other configs
- ✅ Consider JinjaRenderer extraction for reusability (separate issue?)

---

## 13. Config Cross-Reference Map

**Dependency Graph:**
```
components.yaml (leaf - no dependencies)
    ↑
    │ referenced by
    │
project_structure.yaml
    ↑                    ↑
    │                    │ referenced by
    │                    │
    │                policies.yaml
    │                    ↑
    │                    │ uses
    │                    │
    └────────────────→ PolicyEngine
                         (enforcement)

workflows.yaml (Issue #50)
    ↑
    │ phase names referenced by
    │
policies.yaml
```

**Integration Points:**

1. **ScaffoldComponentTool:**
   - Reads: components.yaml (component registry)
   - Reads: project_structure.yaml (validate output_path is in allowed directory)
   - Enforced by: policies.yaml (via PolicyEngine - phase check)

2. **PolicyEngine._decide_create_file():**
   - Reads: project_structure.yaml (check blocked patterns, allowed extensions/dirs)
   - Enforced by: policies.yaml (phase check - currently all phases allowed)

3. **PolicyEngine._decide_scaffold():**
   - Reads: policies.yaml (allowed_phases for scaffold operation)
   - Context: workflows.yaml (current phase from project plan)

4. **ValidationService:**
   - Reads: validation.yaml (Issue #52)
   - Reads: Template metadata (YAML frontmatter)
   - Used by: safe_edit_tool, scaffolding (future)

---

## 14. PolicyEngine Integration Strategy

**Current PolicyEngine Structure:**

```python
class PolicyEngine:
    def decide(ctx: DecisionContext) -> PolicyDecision:
        # 1. Validate project plan exists
        # 2. Validate phase matches current_phase
        # 3. Validate phase in required_phases
        # 4. Delegate to operation-specific methods
        
    def _decide_commit(ctx) -> PolicyDecision:
        # Hardcoded: TDD prefixes (red, green, refactor, docs)
        
    def _decide_scaffold(ctx) -> PolicyDecision:
        # Hardcoded: allowed_phases = {"design", "tdd"}
        
    def _decide_create_file(ctx) -> PolicyDecision:
        # Hardcoded: blocked_patterns, allowed_extensions, allowed_dirs
```

**Config-Driven Refactor Plan:**

```python
class PolicyEngine:
    def __init__(self):
        self.operation_policies = OperationPoliciesConfig.load()  # policies.yaml
        self.project_structure = ProjectStructureConfig.load()    # project_structure.yaml
        self.audit_trail = []
    
    def _decide_commit(ctx) -> PolicyDecision:
        # Use: self.operation_policies.operations["commit"]
        # Check: require_tdd_prefix, valid_prefixes
        
    def _decide_scaffold(ctx) -> PolicyDecision:
        # Use: self.operation_policies.operations["scaffold"].allowed_phases
        # Compare: ctx.phase in allowed_phases
        
    def _decide_create_file(ctx) -> PolicyDecision:
        # Use: self.project_structure.get_directory_policy(path)
        # Check: require_scaffold_for patterns, allowed_extensions
```

**Issue #54 Scope:**
- ✅ Refactor PolicyEngine to load configs (singleton pattern)
- ✅ Replace hardcoded rules with config lookups
- ✅ Maintain audit trail functionality
- ❌ DEFER: New decision methods (Epic #18 - architectural validation, phase activity)

---

## 15. Validation Role in Enforcement

**Question:** Where does validation fit in "wat, waar, wanneer, hoe"?

**Answer:** Validation is ORTHOGONAL to the four domains - it's a **quality gate** that runs AFTER operations.

**Enforcement Pipeline:**
```
1. WAT: Component registry check
   → Is this component type valid? (components.yaml)

2. WAAR: Directory policy check
   → Is this path allowed for this component? (project_structure.yaml)

3. WANNEER: Phase policy check
   → Is this operation allowed in current phase? (policies.yaml)

4. HOE: Scaffolding execution
   → Generate code from template (template metadata, JinjaRenderer)

5. QUALITY: Validation check
   → Does generated code comply with template rules? (validation.yaml, LayeredTemplateValidator)
```

**Validation is NOT config domain - it's ENFORCEMENT step.**

**Relationship:**
- **Domain 4 (HOE)** defines templates and metadata
- **Validation** enforces compliance with templates
- **policies.yaml** could define validation mode (strict, interactive, lenient) per phase

**Issue #54 Scope:**
- ✅ Document validation role in enforcement pipeline
- ❌ NO NEW VALIDATION CONFIG - already handled by Issue #52
- ✅ Consider validation.yaml integration with policies.yaml (future)

---

## 16. Issue #54 Scope - Final Definition

**In Scope:**

1. **Create components.yaml**
   - Component registry (9 types)
   - ComponentRegistryConfig Pydantic model (singleton)
   - Refactor ScaffoldComponentTool to use registry

2. **Create project_structure.yaml**
   - Directory definitions (7 directories)
   - DirectoryPolicy nested model
   - ProjectStructureConfig Pydantic model (singleton)
   - Refactor PolicyEngine._decide_create_file() to use config

3. **Create policies.yaml**
   - Operation policies (scaffold, create_file, commit)
   - Directory-specific phase policies (backend, docs, .st3, etc.)
   - OperationPoliciesConfig Pydantic model (singleton)
   - DirectoryPhasePolicy nested model
   - Refactor PolicyEngine._decide_scaffold() to use config
   - Note: CONFIG defined in Issue #54, ENFORCEMENT in Epic #18

4. **PolicyEngine Refactor**
   - Load configs via singleton pattern
   - Replace hardcoded rules with config lookups
   - Maintain audit trail
   - Add config validation (fail-fast on invalid config)

5. **Tests**
   - 100% coverage for config models
   - PolicyEngine config integration tests
   - ScaffoldComponentTool config integration tests

6. **Documentation**
   - Update AGENT_PROMPT.md with new configs
   - Document config cross-references
   - Document enforcement pipeline

**Out of Scope (Defer to Epic #18 or separate issues):**

1. ❌ ENFORCEMENT of directory-specific phase policies (Epic #18 - using config to block operations)
2. ❌ Architectural pattern validation (Epic #18 child)
3. ❌ Phase activity enforcement (Epic #18 child)
4. ❌ SRP refactoring (ScaffoldComponentTool responsibilities split)
5. ❌ DRY refactoring (fallback logic, suffix logic extraction)
6. ❌ JinjaRenderer extraction to core (separate issue for reusability)
7. ❌ File operations consolidation (PathResolver utility)
8. ❌ Project scaffolding tool (empty dir → full project)

---

## 17. Answers to Unresolved Questions

**Q1: Scope of Issue #54**
✅ ANSWERED: Component registry, project structure, operation policies configs

**Q2: Configuration structure**
✅ ANSWERED: THREE separate files (components.yaml, project_structure.yaml, policies.yaml)

**Q3: Component registry - separate or embedded**
✅ ANSWERED: Separate components.yaml (SRP)

**Q4: Phase policies - workflows.yaml or new**
✅ ANSWERED: New policies.yaml (operation-level), workflows.yaml stays unchanged

**Q5: PolicyEngine refactor scope**
✅ ANSWERED: Config-driven only (no SRP extraction in Issue #54)

**Q6: Backward compatibility**
✅ CLARIFIED: Current project becomes valid config (describe existing structure)

**Q7: Validation integration**
✅ ANSWERED: Validation is enforcement step (orthogonal), already handled by Issue #52

**Q8: Validation role**
✅ ANSWERED: Quality gate after operations, not config domain

**Q9: SRP/DRY refactoring**
✅ ANSWERED: Defer to separate issues (out of Issue #54 scope)

**Q10: File operations consolidation**
✅ ANSWERED: Defer to separate issue (PathResolver utility)

---

## 18. Foundation for Epic #18

**How Issue #54 Enables Epic #18:**

1. **Config Infrastructure:**
   - ✅ Components.yaml → What can be created
   - ✅ Project_structure.yaml → Where it can be created
   - ✅ Policies.yaml → When it can be created
   - ✅ Template metadata + validation.yaml → How quality is enforced

2. **Enforcement Hooks:**
   - PolicyEngine.decide() → Entry point for ALL enforcement
   - Config-driven decisions → Easy to extend (add new operations, directories, policies)
   - Audit trail → Track all policy decisions for debugging

3. **Future Epic #18 Features (enabled by Issue #54):**
   - **Issue #42 (8-phase model):** Can add phase-specific directory policies to policies.yaml
   - **Issue #41 (phase guidance):** Can reference configs for phase-appropriate instructions
   - **Issue #46 (git sync):** Can add git_sync operation to policies.yaml
   - **Architectural validation:** Can add architectural_validation operation with directory-specific rules
   - **Phase activity enforcement:** Can extend directory policies with per-phase allowed_operations

4. **Lego Block Pattern:**
   ```
   components.yaml → Defines WHAT
        ↓
   project_structure.yaml → Defines WHERE + references WHAT
        ↓
   policies.yaml → Defines WHEN + references WHERE
        ↓
   PolicyEngine → ENFORCES all above
   ```

**Composability:** Each config is SRP, references others declaratively, can be extended independently.

---

## Next Steps

1. **Transition to Planning Phase**
   - Design detailed YAML schemas (components, project_structure, policies)
   - Design Pydantic models (ComponentRegistryConfig, ProjectStructureConfig, OperationPoliciesConfig)
   - Design PolicyEngine refactor (config loading, decision method updates)
   - Plan migration strategy (hardcoded → config)
   - Plan test coverage (100% requirement)

2. **User Confirmation Needed:**
   - Confirm Issue #54 scope (3 configs + PolicyEngine refactor)
   - Confirm out-of-scope items deferred to Epic #18 or separate issues
   - Confirm config cross-reference approach
   - Confirm validation placement (enforcement step, not config domain)

3. **Epic #18 Preparation:**
   - Document how Issue #54 enables Epic #18 enforcement features
   - Identify PolicyEngine extension points for future operations
   - Plan policies.yaml extension strategy (directory-specific, phase-specific)

---

**End of Research Phase - Ready for Planning Phase Transition**
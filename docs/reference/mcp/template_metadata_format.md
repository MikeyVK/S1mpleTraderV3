# Template Metadata Format Reference - S1mpleTraderV3

<!--
GENERATED DOCUMENT
Template: generic.md.jinja2
Type: generic
-->

<!-- ═══════════════════════════════════════════════════════════════════════════
     HEADER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

**Status:** DRAFT
**Version:** 1.0
**Last Updated:** 2026-01-01

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTEXT SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Purpose

Complete reference documentation for the TEMPLATE_METADATA format used in Jinja2 templates for template-driven validation. This format serves as the Single Source of Truth for both scaffolding and validation.

## Scope

**In Scope:**
- YAML structure and syntax within Jinja2 comment blocks
- Enforcement levels (STRICT, ARCHITECTURAL, GUIDELINE)
- Validation rule types (strict vs guidelines)
- Template inheritance mechanism
- Variable declaration
- Integration with LayeredTemplateValidator

**Out of Scope:**
- TemplateAnalyzer implementation details
- ValidationService orchestration
- Python-specific validation rules (covered by PythonValidator)

## Prerequisites

- Understanding of Jinja2 template syntax
- Familiarity with YAML format
- Knowledge of project's layered architecture

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTENT SECTION
     ═══════════════════════════════════════════════════════════════════════════ -->

## Overview

TEMPLATE_METADATA is a YAML block embedded in Jinja2 comment syntax (`{# ... #}`) at the beginning of template files. It defines:

1. **Enforcement level** - How strictly rules are enforced
2. **Validation rules** - What to check (strict failures vs warnings)
3. **Template inheritance** - Which base template to extend
4. **Required variables** - What context variables the template needs

### Single Source of Truth

Templates serve dual purposes:
- **Scaffolding**: Generate code from templates
- **Validation**: Validate generated code against template rules

This eliminates drift between "what we generate" and "what we validate".

## YAML Structure

### Basic Structure

```jinja
{# TEMPLATE_METADATA
enforcement: <ENFORCEMENT_LEVEL>
level: content
extends: <BASE_TEMPLATE_PATH>
version: "<VERSION>"

validates:
  strict:
    - rule: <RULE_NAME>
      description: "<HUMAN_READABLE_DESCRIPTION>"
      pattern: "<REGEX_PATTERN>"  # Optional
      methods: [<METHOD_NAMES>]    # Optional
      imports: [<IMPORT_STRINGS>]  # Optional
      
  guidelines:
    - rule: <RULE_NAME>
      description: "<HUMAN_READABLE_DESCRIPTION>"
      severity: WARNING
      pattern: "<REGEX_PATTERN>"  # Optional

purpose: |
  Multi-line description of template purpose
  and what it generates.

variables:
  - <var1>
  - <var2>
#}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `enforcement` | String | Validation enforcement level (STRICT/ARCHITECTURAL/GUIDELINE) |
| `level` | String | Always `"content"` for component templates |
| `extends` | String | Path to base template (relative to templates/) |
| `version` | String | Template version (semantic versioning) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `validates` | Object | Validation rules (strict + guidelines) |
| `purpose` | String | Multi-line template description |
| `variables` | Array | Required context variables |

## Enforcement Levels

The `enforcement` field controls how strictly rules are enforced during validation.

### STRICT (Strictest)

```yaml
enforcement: STRICT
```

- **Purpose**: Enforce non-negotiable formatting/structure
- **Failure behavior**: Hard failure, score penalty
- **Use case**: Base document structure, required header fields
- **Example**: base_document.md.jinja2

**When to use STRICT:**
- File must have specific structure to be valid
- No architectural flexibility needed
- Violations make file unusable

### ARCHITECTURAL (Recommended)

```yaml
enforcement: ARCHITECTURAL
```

- **Purpose**: Enforce architectural patterns and conventions
- **Failure behavior**: Strict rules → hard failure, guidelines → warnings
- **Use case**: Workers, DTOs, Adapters, Tools
- **Example**: worker.py.jinja2, dto.py.jinja2

**When to use ARCHITECTURAL:**
- Code must follow project patterns (BaseWorker inheritance, Protocol+Adapter)
- Some flexibility allowed (naming conventions, docstring format)
- Balance between strictness and pragmatism

### GUIDELINE (Most Flexible)

```yaml
enforcement: GUIDELINE
```

- **Purpose**: Provide recommendations, not requirements
- **Failure behavior**: All violations → warnings only
- **Use case**: Style guides, optional patterns
- **Example**: (not currently used in codebase)

**When to use GUIDELINE:**
- Best practices that can be deviated from
- Style preferences vs hard requirements
- Informational feedback

## Validation Rules (Strict)

Strict rules cause hard failures when enforcement is ARCHITECTURAL or STRICT.

### Pattern Matching

Checks if regex pattern exists in file content.

```yaml
strict:
  - rule: base_class
    description: "Must inherit from BaseWorker[InputDTO, OutputDTO]"
    pattern: "class \\w+\\(BaseWorker\\[\\w+, \\w+\\]\\)"
```

**Use cases:**
- Class inheritance checks
- Required code structures
- Frozen config presence (`"frozen":\s*True`)

### Method Validation

Checks if specific methods exist in the code.

```yaml
strict:
  - rule: required_methods
    description: "Must implement process() method"
    methods:
      - "process"
```

**Use cases:**
- Abstract method implementation
- Worker process() method
- Tool execute() method

### Import Validation

Checks if required imports are present.

```yaml
strict:
  - rule: required_imports
    description: "Must import BaseModel and Field from pydantic"
    imports:
      - "from pydantic import BaseModel, Field"
```

**Use cases:**
- Required dependencies
- Type imports for validation
- Protocol imports for adapters

### Combined Rules

A single rule can combine multiple validation types:

```yaml
strict:
  - rule: protocol_interface
    description: "Must define Protocol interface named I<ClassName>"
    pattern: "class I\\w+\\(Protocol\\)"
    imports:
      - "from typing import Protocol"
```

## Validation Rules (Guidelines)

Guidelines provide warnings but never fail validation (even with STRICT enforcement).

### Structure

```yaml
guidelines:
  - rule: naming_convention
    description: "Worker class name should describe processing action"
    severity: WARNING  # Always WARNING
```

### Purpose

- **Code quality hints**: Naming conventions, docstring format
- **Best practices**: Field ordering, interface segregation
- **Non-blocking feedback**: Developer can choose to ignore

### Examples

```yaml
guidelines:
  - rule: docstring_format
    description: "Docstring should include Responsibilities and Subscribes to/Publishes sections"
    pattern: "Responsibilities:|Subscribes to:|Publishes:"
    severity: WARNING
    
  - rule: field_ordering
    description: "Fields should follow order: causality → id → timestamp → data"
    severity: WARNING
```

## Template Inheritance

Templates can extend base templates to inherit their validation rules.

### Inheritance Chain

```
base/base_component.py.jinja2  (parent)
    ↓
dto.py.jinja2  (child - inherits + adds rules)
```

### How It Works

1. **TemplateAnalyzer** resolves the inheritance chain
2. Base rules are merged with child rules
3. Child rules override base rules with same `rule` name
4. Enforcement level from child takes precedence

### Example

**base/base_component.py.jinja2:**
```jinja
{# TEMPLATE_METADATA
enforcement: ARCHITECTURAL
validates:
  strict:
    - rule: file_header
      description: "Must have module docstring with @layer"
      pattern: '@layer:'
  guidelines:
    - rule: clean_imports
      description: "Use absolute imports"
      severity: WARNING
#}
```

**dto.py.jinja2:**
```jinja
{# TEMPLATE_METADATA
enforcement: ARCHITECTURAL
extends: base/base_component.py.jinja2
validates:
  strict:
    - rule: base_class
      description: "Must inherit from BaseModel"
      pattern: "class \\w+\\(BaseModel\\)"
#}
```

**Effective rules for dto.py.jinja2:**
- `file_header` (strict) - inherited from base
- `clean_imports` (guideline) - inherited from base
- `base_class` (strict) - defined in dto

## Variables Section

Declares which context variables the template requires for rendering.

```yaml
variables:
  - name
  - description
  - layer
  - has_causality
```

### Purpose

- **Documentation**: What data does template need?
- **Validation**: (Future) Check if all required variables provided
- **IDE support**: (Future) Autocomplete in template editors

### Variable Naming

- Use snake_case
- Match parameter names in scaffolding tools
- Be specific (`input_dto` not `input`)

## Examples

### Worker Template (ARCHITECTURAL) - Actual Template

**Location:** `mcp_server/templates/components/worker.py.jinja2`

```jinja
{# TEMPLATE_METADATA
enforcement: ARCHITECTURAL
level: content
extends: base/base_component.py.jinja2
version: "2.0"

validates:
  strict:
    - rule: base_class
      description: "Must inherit from BaseWorker[InputDTO, OutputDTO]"
      pattern: "class \\w+\\(BaseWorker\\[\\w+, \\w+\\]\\)"
      
    - rule: required_methods
      description: "Must implement process() method"
      pattern: "async def process\\(self, input_data: \\w+\\) -> \\w+"
      
    - rule: required_imports
      description: "Must import BaseWorker and IStrategyCache"
      imports:
        - "backend.core.interfaces.base_worker.BaseWorker"
        - "backend.core.interfaces.strategy_cache.IStrategyCache"
  
  guidelines:
    - rule: naming_convention
      description: "Worker class name should describe processing action"
      severity: WARNING
      
    - rule: docstring_format
      description: "Docstring should include Responsibilities and Subscribes to/Publishes sections"
      pattern: "Responsibilities:|Subscribes to:|Publishes:"
      severity: WARNING
#}
```

**Key Points:**
- `ARCHITECTURAL` enforcement: Strict on base class, flexible on naming
- 3 strict rules: base class pattern, process() method, required imports
- 2 guidelines: naming convention and docstring format (WARNINGs only)
- Extends base_component for shared format rules

### Adapter Template (ARCHITECTURAL) - Actual Template

**Location:** `mcp_server/templates/components/adapter.py.jinja2`

```jinja
{# TEMPLATE_METADATA
enforcement: ARCHITECTURAL
level: content
extends: base/base_component.py.jinja2
version: "2.0"

validates:
  strict:
    - rule: protocol_interface
      description: "Must define Protocol interface (I<ClassName>)"
      pattern: "class I\\w+\\(Protocol\\)"
      
    - rule: adapter_implementation
      description: "Must implement adapter class matching protocol"
      pattern: "class \\w+Adapter:"
      
    - rule: required_imports
      description: "Must import Protocol and core exceptions"
      imports:
        - "typing.Protocol"
        - "backend.core.exceptions"
  
  guidelines:
    - rule: naming_convention
      description: "Adapter class name should end with 'Adapter' suffix"
      severity: WARNING
      
    - rule: docstring_format
      description: "Docstring should include Responsibilities and Usage example"
      pattern: "Responsibilities:|Usage:"
      severity: WARNING
      
    - rule: interface_segregation
      description: "Protocol interface should be specific, not god interface"
      severity: WARNING
#}
```

**Key Points:**
- Protocol+Adapter pattern enforcement (two classes required)
- Interface naming convention: `I<ClassName>(Protocol)`
- Adapter class validation: Must have `Adapter` suffix
- Interface Segregation Principle as guideline (WARNING only)

### Base Document Template (STRICT) - Conceptual Example

```jinja
{# TEMPLATE_METADATA
enforcement: STRICT
level: structure
version: "2.0"

validates:
  strict:
    - rule: header_fields_presence
      description: "Must have Status/Version/Last Updated header fields"
      pattern: "\\*\\*Status:\\*\\*.*\\*\\*Version:\\*\\*.*\\*\\*Last Updated:\\*\\*"
      
    - rule: separator_structure
      description: "Must have separator line (---) after header"
      pattern: "^---$"
      
    - rule: required_sections
      description: "Must have ## Purpose and ## Scope sections"
      pattern: "## Purpose|## Scope"
      
    - rule: link_definitions
      description: "Must have Related Documentation section at end"
      pattern: "## Related Documentation"

purpose: |
  Enforce consistent structure for all markdown documentation.
  Format rules apply universally, content varies by doc type.

variables:
  - title
  - doc_type
  - status
#}
```

**Key Points:**
- `STRICT` enforcement: Non-negotiable structure rules
- Applies to ALL document types (research, planning, design)
- Content flexibility maintained via inheritance
- Document-specific rules in child templates (research.md, planning.md)

## Best Practices

### 1. Choose Appropriate Enforcement Level

- **STRICT**: Only for non-negotiable structure (document header + required sections)
- **ARCHITECTURAL**: For code patterns (workers, DTOs, adapters)
- **GUIDELINE**: For style preferences (not yet used)

### 2. Strict vs Guidelines

**Use `strict` for:**
- Architectural patterns (BaseWorker inheritance)
- Required methods (process, execute)
- Safety requirements (frozen DTOs)

**Use `guidelines` for:**
- Naming conventions
- Docstring style
- Field ordering
- Code organization

### 3. Pattern Writing

```yaml
# ✓ Good: Specific, matches one thing
pattern: "class \\w+\\(BaseModel\\)"

# ✗ Bad: Too generic, many false positives
pattern: "class"

# ✓ Good: Anchored to context
pattern: '"frozen":\\s*True'

# ✗ Bad: Could match comments
pattern: "frozen.*True"
```

### 4. Rule Naming

```yaml
# ✓ Good: Descriptive, clear purpose
rule: base_class
rule: frozen_config
rule: required_methods

# ✗ Bad: Vague, unclear
rule: check1
rule: validation
rule: rule_a
```

### 5. Description Writing

```yaml
# ✓ Good: Action-oriented, specific
description: "Must inherit from BaseWorker[InputDTO, OutputDTO]"
description: "Must have frozen=True in model_config"

# ✗ Bad: Vague, non-actionable
description: "Check class"
description: "Validate configuration"
```

### 6. Template Inheritance

- Use base templates for shared rules
- Override only when necessary
- Keep inheritance chains shallow (max 2 levels)
- Document inheritance relationships

## Quick Start Guide

### Adding Validation to a New Template

**Step 1: Choose Enforcement Level**
```yaml
# Non-negotiable structure (markdown format, file structure)
enforcement: STRICT

# OR: System architecture patterns (base classes, protocols)
enforcement: ARCHITECTURAL

# OR: Style guidelines (naming, formatting)
enforcement: GUIDELINE
```

**Step 2: Define Strict Rules**
```yaml
validates:
  strict:
    - rule: base_class_inheritance
      description: "Must inherit from BaseWorker[Input, Output]"
      pattern: "class \\w+\\(BaseWorker\\[\\w+, \\w+\\]\\)"
```

**Step 3: Add Guidelines (Optional)**
```yaml
  guidelines:
    - rule: naming_convention
      description: "Class name should be descriptive (e.g., ParseMarketDataWorker)"
      severity: WARNING
```

**Step 4: Test Validation**
1. Scaffold code using template
2. Run validation via SafeEditTool
3. Verify errors block save, warnings allow save
4. Check agent hints appear in validation response

### Common Patterns

**Pattern 1: Base Class Validation**
```yaml
- rule: base_class
  description: "Must inherit from BaseModel with frozen config"
  pattern: "class \\w+\\(BaseModel\\):[\\s\\S]*frozen.*True"
```

**Pattern 2: Required Method Validation**
```yaml
- rule: process_method
  description: "Must implement async process() method"
  pattern: "async def process\\(self, input_data: \\w+\\) -> \\w+"
```

**Pattern 3: Import Validation**
```yaml
- rule: required_imports
  description: "Must import core interfaces"
  imports:
    - "backend.core.interfaces.base_worker"
    - "backend.core.interfaces.strategy_cache"
```

**Pattern 4: Document Structure Validation**
```yaml
- rule: required_sections
  description: "Must have Purpose, Scope, and Related Documentation sections"
  pattern: "## Purpose|## Scope|## Related Documentation"
```

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     FOOTER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Related Documentation

- **[validation_api.md](validation_api.md)** - TemplateAnalyzer and LayeredTemplateValidator API reference
- **[MCP_TOOLS.md](MCP_TOOLS.md)** - MCP server tool documentation
- **[template_analyzer.py](../../../mcp_server/validation/template_analyzer.py)** - Implementation of metadata parsing
- **[layered_template_validator.py](../../../mcp_server/validation/layered_template_validator.py)** - Three-tier validation logic
- **[validation_service.py](../../../mcp_server/validation/validation_service.py)** - Validation orchestration

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-01 | Initial documentation (Issue #52 Phase 4g) |

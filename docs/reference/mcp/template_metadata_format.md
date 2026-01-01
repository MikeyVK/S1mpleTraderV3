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
- Enforcement levels (FORMAT, ARCHITECTURAL, GUIDELINE)
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
| `enforcement` | String | Validation enforcement level (FORMAT/ARCHITECTURAL/GUIDELINE) |
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

### FORMAT (Strictest)

```yaml
enforcement: FORMAT
```

- **Purpose**: Enforce non-negotiable formatting/structure
- **Failure behavior**: Hard failure, score penalty
- **Use case**: Base document structure, markdown frontmatter
- **Example**: base_document.md.jinja2

**When to use FORMAT:**
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

Strict rules cause hard failures when enforcement is ARCHITECTURAL or FORMAT.

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

Guidelines provide warnings but never fail validation (even with FORMAT enforcement).

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

### DTO Template (ARCHITECTURAL)

```jinja
{# TEMPLATE_METADATA
enforcement: ARCHITECTURAL
level: content
extends: base/base_component.py.jinja2
version: "2.0"

validates:
  strict:
    - rule: base_class
      description: "Must inherit from Pydantic BaseModel"
      pattern: "class \\w+\\(BaseModel\\)"
      
    - rule: frozen_config
      description: "Must have frozen=True in model_config"
      pattern: '"frozen":\\s*True'
      
    - rule: field_validators
      description: "Must have field validators for id and timestamp"
      methods:
        - "validate_id_format"
        - "ensure_utc_timestamp"
      
  guidelines:
    - rule: docstring_format
      description: "Class docstring should describe purpose and immutability"
      severity: WARNING

purpose: |
  Generate immutable Pydantic DTOs following project conventions.
  Enforces causality tracking, ID generation, and timestamp handling.

variables:
  - name
  - description
  - has_causality
#}
```

### Worker Template (ARCHITECTURAL)

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
      
  guidelines:
    - rule: naming_convention
      description: "Worker class name should describe processing action"
      severity: WARNING

variables:
  - name
  - input_dto
  - output_dto
  - worker_type
#}
```

### Base Document Template (FORMAT)

```jinja
{# TEMPLATE_METADATA
enforcement: FORMAT
level: structure
version: "2.0"

validates:
  strict:
    - rule: frontmatter_block
      description: "Must have YAML frontmatter block at start"
      pattern: "^---\\n[\\s\\S]*?\\n---"
      
    - rule: required_headers
      description: "Must have ## Purpose and ## Scope sections"
      pattern: "## Purpose|## Scope"

purpose: |
  Enforce consistent structure for all markdown documentation.

variables:
  - title
  - doc_type
#}
```

## Best Practices

### 1. Choose Appropriate Enforcement Level

- **FORMAT**: Only for non-negotiable structure (markdown frontmatter)
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

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     FOOTER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Related Documentation

- **[MCP_TOOLS.md](MCP_TOOLS.md)** - MCP server tool documentation
- **[template_analyzer.py](../../../mcp_server/validation/template_analyzer.py)** - Implementation of metadata parsing
- **[layered_template_validator.py](../../../mcp_server/validation/layered_template_validator.py)** - Three-tier validation logic
- **[validation_service.py](../../../mcp_server/validation/validation_service.py)** - Validation orchestration

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-01 | Initial documentation (Issue #52 Phase 4g) |

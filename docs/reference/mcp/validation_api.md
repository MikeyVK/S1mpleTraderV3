# Template Validation API Reference - S1mpleTraderV3

<!--
GENERATED DOCUMENT
Template: generic.md.jinja2
Type: API Reference
-->

<!-- ═══════════════════════════════════════════════════════════════════════════
     HEADER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

**Status:** APPROVED
**Version:** 1.0
**Last Updated:** 2026-01-01

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTEXT SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Purpose

Complete API reference for the template-driven validation system. Documents the `TemplateAnalyzer` and `LayeredTemplateValidator` classes that implement the three-tier enforcement model.

## Scope

**In Scope:**
- TemplateAnalyzer class and methods
- LayeredTemplateValidator class and methods
- ValidationResult and ValidationIssue data structures
- Usage examples and common patterns

**Out of Scope:**
- Template metadata format specification (see [template_metadata_format.md](template_metadata_format.md))
- ValidationService orchestration
- Python/Markdown validator implementations

## Prerequisites

- Understanding of template-driven validation concept
- Familiarity with [template_metadata_format.md](template_metadata_format.md)
- Knowledge of async/await patterns in Python

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTENT SECTION (FLEXIBLE - VARIES BY DOC TYPE)
     ═══════════════════════════════════════════════════════════════════════════ -->

## TemplateAnalyzer

**Location:** `mcp_server/validation/template_analyzer.py`

Analyzes Jinja2 templates to extract TEMPLATE_METADATA from comment blocks and resolve template inheritance chains.

### Class Signature

```python
class TemplateAnalyzer:
    """Analyzes Jinja2 templates to extract validation metadata."""
    
    def __init__(self, template_root: Path):
        """
        Initialize analyzer with template directory root.
        
        Args:
            template_root: Root directory containing all templates.
        """
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `template_root` | `Path` | Root directory containing all template files |
| `env` | `jinja2.Environment` | Jinja2 environment for AST parsing |
| `_metadata_cache` | `dict[Path, dict[str, Any]]` | Internal cache of extracted metadata |

### Methods

#### `extract_metadata(template_path: Path) -> dict[str, Any]`

Extracts validation metadata from template YAML frontmatter within `{# TEMPLATE_METADATA ... #}` blocks.

**Parameters:**
- `template_path` (Path): Path to template file.

**Returns:**
- `dict[str, Any]`: Metadata dictionary with structure:
  ```python
  {
      "enforcement": "STRICT" | "ARCHITECTURAL" | "GUIDELINE",
      "level": "format" | "content",
      "extends": "path/to/base.jinja2" | None,
      "validates": {
          "strict": [...],
          "guidelines": [...]
      },
      "variables": ["name", "type", ...],
      "purpose": "...",
      "version": "2.0"
  }
  ```
- Empty dict if no metadata found.

**Raises:**
- `ValueError`: If YAML metadata is malformed or file cannot be read.

**Example:**
```python
analyzer = TemplateAnalyzer(Path("mcp_server/templates"))
metadata = analyzer.extract_metadata(
    Path("mcp_server/templates/components/dto.py.jinja2")
)
print(metadata["enforcement"])  # "ARCHITECTURAL"
print(metadata["validates"]["strict"])  # List of strict rules
```

#### `extract_jinja_variables(template_path: Path) -> list[str]`

Extracts undeclared variables from Jinja2 template using AST analysis.

**Parameters:**
- `template_path` (Path): Path to template file.

**Returns:**
- `list[str]`: Sorted list of variable names used in template (e.g., `["name", "description", "layer"]`).

**Example:**
```python
variables = analyzer.extract_jinja_variables(
    Path("mcp_server/templates/components/worker.py.jinja2")
)
print(variables)  # ["input_dto", "name", "output_dto", "worker_type"]
```

#### `get_base_template(template_path: Path) -> Path | None`

Gets the base template this template extends (if any).

**Parameters:**
- `template_path` (Path): Path to template file.

**Returns:**
- `Path | None`: Path to base template, or None if no inheritance.

**Example:**
```python
base = analyzer.get_base_template(
    Path("mcp_server/templates/components/worker.py.jinja2")
)
print(base)  # Path("mcp_server/templates/base/base_component.py.jinja2")
```

#### `get_inheritance_chain(template_path: Path) -> list[Path]`

Gets complete inheritance chain from specific to base.

**Parameters:**
- `template_path` (Path): Path to template file.

**Returns:**
- `list[Path]`: List of template paths from most specific to most general.
  Example: `[worker.py.jinja2, base_component.py.jinja2]`

**Handles:**
- Circular inheritance detection
- Missing base templates (breaks chain gracefully)

**Example:**
```python
chain = analyzer.get_inheritance_chain(
    Path("mcp_server/templates/components/worker.py.jinja2")
)
for tmpl in chain:
    print(tmpl.name)
# Output:
# worker.py.jinja2
# base_component.py.jinja2
```

#### `merge_metadata(child: dict[str, Any], parent: dict[str, Any]) -> dict[str, Any]`

Merges child and parent metadata, with child taking precedence.

**Merging Rules:**
- **strict rules**: Concatenate (child + parent, no duplicates)
- **guidelines**: Concatenate (child + parent, no duplicates)
- **enforcement**: Child overrides parent
- **variables**: Union of both
- **purpose/hints**: Child overrides parent

**Parameters:**
- `child` (dict): Child template metadata.
- `parent` (dict): Parent template metadata.

**Returns:**
- `dict[str, Any]`: Merged metadata dictionary.

**Example:**
```python
parent_meta = {
    "enforcement": "STRICT",
    "validates": {"strict": [{"rule": "imports"}]},
    "variables": ["base_var"]
}
child_meta = {
    "enforcement": "ARCHITECTURAL",
    "validates": {"strict": [{"rule": "base_class"}]},
    "variables": ["child_var"]
}
merged = analyzer.merge_metadata(child_meta, parent_meta)
print(merged["enforcement"])  # "ARCHITECTURAL" (child wins)
print(len(merged["validates"]["strict"]))  # 2 (concatenated)
print(merged["variables"])  # ["base_var", "child_var"] (union)
```

---

## LayeredTemplateValidator

**Location:** `mcp_server/validation/layered_template_validator.py`

Three-tier template validator enforcing format → architectural → guidelines with fail-fast behavior on errors.

### Class Signature

```python
class LayeredTemplateValidator(BaseValidator):
    """
    Three-tier template validator enforcing format → architectural → guidelines.
    
    Tier 1 (Base Template Format): STRICT
        - Import order, docstrings, type hints, file structure
        - Severity: ERROR (blocks save)
        - Source: Base templates (base_component.py, base_document.md)
    
    Tier 2 (Architectural Rules): STRICT
        - Base class inheritance, required methods, protocol compliance
        - Severity: ERROR (blocks save)
        - Source: Specific templates strict section
    
    Tier 3 (Guidelines): LOOSE
        - Naming conventions, field ordering, docstring format
        - Severity: WARNING (saves with notification)
        - Source: Specific templates guidelines section
    """
    
    def __init__(
        self,
        template_type: str,
        template_analyzer: TemplateAnalyzer
    ):
        """
        Initialize validator for specific template type.
        
        Args:
            template_type: Template identifier (dto, tool, base_document, etc.)
            template_analyzer: Analyzer for extracting template metadata.
        """
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `template_type` | `str` | Template identifier (dto, tool, worker, etc.) |
| `analyzer` | `TemplateAnalyzer` | Analyzer for metadata extraction |
| `metadata` | `dict[str, Any]` | Merged metadata for this template type |

### Methods

#### `async validate(path: str, content: str | None = None) -> ValidationResult`

Validates file against template rules using three-tier model with fail-fast behavior.

**Validation Flow:**
1. Validate format rules (base template) - **stop on ERROR**
2. Validate architectural rules (specific template) - **stop on ERROR**
3. Validate guidelines (all templates) - collect WARNINGs
4. Return combined result with agent hints

**Parameters:**
- `path` (str): File path to validate.
- `content` (str | None): Optional file content (reads from path if None).

**Returns:**
- `ValidationResult`: Result object with:
  - `passed` (bool): True if no errors
  - `score` (float): 10.0 (no issues), 8.0 (warnings only), 0.0 (errors)
  - `issues` (list[ValidationIssue]): List of validation issues
  - `agent_hint` (str | None): Optional agent guidance from template
  - `content_guidance` (dict | None): Optional content guidance

**Example:**
```python
analyzer = TemplateAnalyzer(Path("mcp_server/templates"))
validator = LayeredTemplateValidator("dto", analyzer)

result = await validator.validate("mcp_server/dtos/my_dto.py")
if result.passed:
    print(f"Validation passed with score {result.score}")
else:
    for issue in result.issues:
        print(f"{issue.severity.upper()}: {issue.message}")
```

#### `_validate_format(content: str) -> list[ValidationIssue]`

**Private method.** Validates Tier 1 format rules from base template.

**Checks:**
- Import order (stdlib → third-party → local)
- Docstring presence
- Type hints on functions
- File header/frontmatter

**Returns:**
- `list[ValidationIssue]`: Issues with severity ERROR.

#### `_validate_architectural(content: str) -> list[ValidationIssue]`

**Private method.** Validates Tier 2 architectural rules from specific template.

**Checks:**
- Base class inheritance
- Required methods with signatures
- Required imports
- Protocol compliance

**Returns:**
- `list[ValidationIssue]`: Issues with severity ERROR.

#### `_validate_guidelines(content: str) -> list[ValidationIssue]`

**Private method.** Validates Tier 3 guidelines from all templates.

**Checks:**
- Naming conventions
- Field/section ordering
- Docstring format
- Content type (for documents)

**Returns:**
- `list[ValidationIssue]`: Issues with severity WARNING.

---

## Data Structures

### ValidationResult

**Location:** `mcp_server/validation/base.py`

```python
@dataclass(frozen=True)
class ValidationResult:
    """Result of a validation check."""
    
    passed: bool
    score: float  # 0.0-10.0
    issues: list[ValidationIssue] = field(default_factory=list)
    agent_hint: str | None = None
    content_guidance: dict[str, Any] | None = None
```

**Fields:**
- `passed`: True if no ERROR issues (warnings are allowed)
- `score`: Quality score (10.0 = perfect, 8.0 = warnings only, 0.0 = errors)
- `issues`: List of validation issues found
- `agent_hint`: Optional guidance for AI agents (from template metadata)
- `content_guidance`: Optional content structure hints (from template metadata)

### ValidationIssue

**Location:** `mcp_server/validation/base.py`

```python
@dataclass(frozen=True)
class ValidationIssue:
    """A single validation issue."""
    
    message: str
    severity: str  # "error" or "warning"
    line: int | None = None
    column: int | None = None
    rule: str | None = None
```

**Fields:**
- `message`: Human-readable issue description
- `severity`: "error" (blocks save) or "warning" (allows save)
- `line`: Optional line number where issue occurs
- `column`: Optional column number where issue occurs
- `rule`: Optional rule identifier that was violated

---

## Usage Patterns

### Pattern 1: Basic Template Validation

```python
from pathlib import Path
from mcp_server.validation.template_analyzer import TemplateAnalyzer
from mcp_server.validation.layered_template_validator import LayeredTemplateValidator

# Initialize analyzer
template_root = Path("mcp_server/templates")
analyzer = TemplateAnalyzer(template_root)

# Create validator for DTO template
dto_validator = LayeredTemplateValidator("dto", analyzer)

# Validate a DTO file
result = await dto_validator.validate("mcp_server/dtos/trade_dto.py")

if not result.passed:
    print(f"Validation failed with score {result.score}")
    for issue in result.issues:
        if issue.severity == "error":
            print(f"ERROR: {issue.message}")
        else:
            print(f"WARNING: {issue.message}")
else:
    print(f"Validation passed (score: {result.score})")
```

### Pattern 2: Analyzing Template Metadata

```python
from pathlib import Path
from mcp_server.validation.template_analyzer import TemplateAnalyzer

analyzer = TemplateAnalyzer(Path("mcp_server/templates"))

# Get metadata for worker template
worker_template = Path("mcp_server/templates/components/worker.py.jinja2")
metadata = analyzer.extract_metadata(worker_template)

print(f"Enforcement: {metadata['enforcement']}")
print(f"Level: {metadata['level']}")
print(f"Variables: {metadata['variables']}")

# Check inheritance chain
chain = analyzer.get_inheritance_chain(worker_template)
print(f"Inheritance chain: {[t.name for t in chain]}")

# Get merged metadata with base templates
merged = metadata
for base_path in chain[1:]:  # Skip first (current template)
    base_meta = analyzer.extract_metadata(base_path)
    merged = analyzer.merge_metadata(merged, base_meta)

print(f"Total strict rules: {len(merged['validates']['strict'])}")
```

### Pattern 3: Integration with ValidationService

```python
from mcp_server.validation.validation_service import ValidationService
from mcp_server.validation.template_analyzer import TemplateAnalyzer

# ValidationService already integrates LayeredTemplateValidator
service = ValidationService()

# Service automatically:
# 1. Runs PythonValidator (pylint, mypy, pyright)
# 2. Runs LayeredTemplateValidator (template rules)
# 3. Combines results

result = await service.validate_file(
    "mcp_server/dtos/my_dto.py",
    file_type="dto"
)

if not result.passed:
    print("Validation failed:")
    for issue in result.issues:
        print(f"  {issue.severity}: {issue.message}")
```

### Pattern 4: Creating Custom Validators

```python
from pathlib import Path
from mcp_server.validation.template_analyzer import TemplateAnalyzer
from mcp_server.validation.layered_template_validator import LayeredTemplateValidator

# Subclass for custom validation logic
class CustomWorkerValidator(LayeredTemplateValidator):
    """Custom validator with additional checks for workers."""
    
    def __init__(self, analyzer: TemplateAnalyzer):
        super().__init__("worker", analyzer)
    
    async def validate(self, path: str, content: str | None = None) -> ValidationResult:
        # Run standard template validation
        result = await super().validate(path, content)
        
        # Add custom checks
        if content and "TODO" in content:
            result.issues.append(ValidationIssue(
                message="Worker contains TODO comments",
                severity="warning"
            ))
        
        return result
```

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     FOOTER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Related Documentation

- **[template_metadata_format.md](template_metadata_format.md)** - TEMPLATE_METADATA format specification
- **[MCP_TOOLS.md](MCP_TOOLS.md)** - MCP server tools documentation
- **[validation_service.py](../../../mcp_server/validation/validation_service.py)** - Validation orchestration
- **[base.py](../../../mcp_server/validation/base.py)** - Base validator interfaces

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-01 | Initial API documentation (Issue #52 Documentation Phase) |


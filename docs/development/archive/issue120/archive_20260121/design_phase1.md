# Phase 1: Self-Documenting Errors - Design - SimpleTraderV3

**Status:** 🔧 In Progress  
**Version:** 0.1  
**Last Updated:** 2026-01-21

---

## Purpose

Technical design and implementation specifications for template-based error introspection. Defines exact method signatures, data structures, error message formats, and implementation approach for Phase 1.

## Scope

**In Scope:**
- Complete method signatures with type hints
- Template introspection algorithm specifications
- Before/after error message examples
- Test scenario definitions
- Implementation sequence

**Out of Scope:**
- Phase 2: get_artifact_schema tool (separate issue)
- Performance optimization (cache design covered, tuning not)
- UI/formatting improvements beyond text hints

---

## Architecture Overview

### Component Interaction

```
User calls scaffold_artifact(type, **context)
         ↓
TemplateScaffolder.validate()
   ├─→ Missing fields? 
   │   └─→ _format_context_help() → TemplateAnalyzer → Template AST
   │       └─→ ValidationError(message, hints=[schema, example])
   │           └─→ @tool_error_handler → ToolResult.error()
   │
   └─→ _load_and_render_template()
       └─→ Jinja2 UndefinedError?
           └─→ Wrap with _format_context_help() → ValidationError
               └─→ @tool_error_handler → ToolResult.error()
```

### Data Flow

```
artifacts.yaml
  ├─→ ArtifactRegistryConfig.get_artifact() → ArtifactDefinition
  └─→ example_context (usage guidance)

templates/*.jinja2 (SSOT for schema)
  └─→ TemplateAnalyzer.extract_jinja_variables() → set[str]
      ├─→ _detect_conditional_variables() → set[str] (optional)
      └─→ _extract_template_schema() → {"required": [...], "optional": [...]}
          └─→ _format_context_help() → list[str] (hints)
```

---

## Detailed Design

### 1. Template Introspection System

#### 1.1 TemplateScaffolder Enhancements

**Dependencies to Inject:**

```python
class TemplateScaffolder(BaseScaffolder):
    def __init__(
        self,
        registry: ArtifactRegistryConfig | None = None,
        renderer: JinjaRenderer | None = None,
        analyzer: TemplateAnalyzer | None = None  # NEW DEPENDENCY
    ) -> None:
        """Initialize with dependency injection.
        
        Args:
            registry: Artifact registry configuration
            renderer: Jinja2 template renderer
            analyzer: Template introspection analyzer (NEW)
        """
        super().__init__()
        self.registry = registry or ArtifactRegistryConfig.from_file()
        
        # Initialize renderer
        if renderer is None:
            template_dir = Path(__file__).parent.parent / "templates"
            renderer = JinjaRenderer(template_dir=template_dir)
        self._renderer = renderer
        
        # Initialize analyzer (NEW)
        if analyzer is None:
            template_dir = Path(__file__).parent.parent / "templates"
            analyzer = TemplateAnalyzer(template_root=template_dir)
        self._analyzer = analyzer
```

#### 1.2 Template Schema Extraction

**Primary Method:**

```python
def _extract_template_schema(self, artifact_type: str) -> dict[str, Any]:
    """Extract required/optional variables from template AST.
    
    Uses TemplateAnalyzer to parse Jinja2 template and identify
    which variables are required vs optional (conditional).
    
    Args:
        artifact_type: Artifact type_id (e.g., 'dto', 'worker')
    
    Returns:
        Dict with structure:
        {
            "required": ["name", "description"],  # Unconditional usage
            "optional": ["fields", "frozen"],     # In {% if %} blocks
            "all": ["name", "description", "fields", "frozen"]
        }
    
    Raises:
        ConfigError: If artifact type unknown or template not found
    
    Example:
        >>> schema = scaffolder._extract_template_schema("dto")
        >>> schema["required"]
        ["name", "description"]
        >>> schema["optional"]
        ["fields", "frozen"]
    """
    # Get artifact definition
    artifact = self.registry.get_artifact(artifact_type)
    
    # Resolve template path
    template_path = self._resolve_template_path(
        artifact_type, artifact, {}
    )
    
    if not template_path:
        raise ConfigError(
            f"No template configured for artifact type: {artifact_type}"
        )
    
    # Get full path
    full_path = self._renderer._template_dir / template_path
    
    # Extract all undeclared variables via TemplateAnalyzer
    all_variables = self._analyzer.extract_jinja_variables(full_path)
    
    # Detect which are conditional (optional)
    optional_variables = self._detect_conditional_variables(full_path)
    
    # Required = all - optional
    required_variables = [v for v in all_variables if v not in optional_variables]
    
    return {
        "required": sorted(required_variables),
        "optional": sorted(list(optional_variables)),
        "all": sorted(all_variables)
    }
```

#### 1.3 Conditional Variable Detection

**Algorithm:**

```python
def _detect_conditional_variables(self, template_path: Path) -> set[str]:
    """Detect variables used only inside conditional blocks.
    
    Parses template to find variables referenced in {% if var %} tests
    or used exclusively within conditional blocks. These are optional.
    
    Algorithm:
    1. Parse template source with Jinja2 Environment
    2. Walk AST to find all If nodes
    3. Extract variable names from Test nodes ({% if var %})
    4. Track variables used exclusively in conditional body
    
    Args:
        template_path: Path to Jinja2 template
    
    Returns:
        Set of variable names that are optional (conditional usage)
    
    Example:
        Template: {% if fields %}{{ fields }}{% endif %}
        Returns: {"fields"}
        
        Template: {{ name }}  (unconditional)
        Returns: set()
    """
    from jinja2 import nodes
    
    try:
        source = template_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    
    # Parse template AST
    try:
        ast = self._analyzer.env.parse(source)
    except Exception:
        return set()  # Parse error - assume all required
    
    optional_vars = set()
    
    # Find all If nodes
    for node in ast.find_all(nodes.If):
        # Check if test is simple Name ({% if var %})
        if isinstance(node.test, nodes.Name):
            optional_vars.add(node.test.name)
    
    return optional_vars
```

**Edge Cases:**

| Template Pattern | Classification | Rationale |
|-----------------|----------------|-----------|
| `{{ name }}` | Required | Direct unconditional usage |
| `{% if fields %}{{ fields }}{% endif %}` | Optional | Used only in conditional |
| `{% if fields %}...{% else %}default{% endif %}` | Optional | Has fallback |
| `{{ fields \| default([]) }}` | Optional | Jinja2 default filter provides fallback |
| `{% for f in fields %}` | Required (safe) | Loop over undefined = error, assume required |

**Implementation Note:** Start conservative - assume required unless clearly optional. Better to have agent provide field and get better error.

### 2. Error Hint Formatting

#### 2.1 Context Help Generator

```python
def _format_context_help(
    self,
    artifact_type: str,
    missing_fields: list[str] | None = None,
    provided_fields: list[str] | None = None
) -> list[str]:
    """Format error hints with template-derived schema and example.
    
    Generates dynamic hints showing:
    1. Required variables from template (with ✗/✓ markers)
    2. Optional variables from template
    3. Example context from artifacts.yaml (if available)
    
    Args:
        artifact_type: Artifact type_id
        missing_fields: Fields required but not provided
        provided_fields: Fields that were provided
    
    Returns:
        List of hint strings for MCPError hints parameter
    
    Example Output:
        [
            "Template 'dto.py.jinja2' expects these variables:",
            "",
            "Required:",
            "  ✗ name",
            "  ✓ description",
            "",
            "Optional:",
            "    fields",
            "    frozen",
            "",
            "Example Context:",
            "{",
            '  "name": "TradeSignal",',
            '  "description": "Trading signal DTO",',
            '  "fields": [...]',
            "}"
        ]
    """
    # Extract schema from template
    schema = self._extract_template_schema(artifact_type)
    
    # Get artifact for template name and example
    artifact = self.registry.get_artifact(artifact_type)
    
    hints = []
    
    # Header with template name
    hints.append(f"Template '{artifact.template_path}' expects these variables:")
    hints.append("")
    
    # Required variables with status markers
    if schema["required"]:
        hints.append("Required:")
        for var in schema["required"]:
            if provided_fields is not None:
                marker = " ✓ " if var in provided_fields else " ✗ "
            elif missing_fields is not None:
                marker = " ✗ " if var in missing_fields else " ✓ "
            else:
                marker = "   "
            hints.append(f"{marker}{var}")
        hints.append("")
    
    # Optional variables
    if schema["optional"]:
        hints.append("Optional:")
        for var in schema["optional"]:
            hints.append(f"    {var}")
        hints.append("")
    
    # Example from artifacts.yaml
    if hasattr(artifact, 'example_context') and artifact.example_context:
        import json
        hints.append("Example Context:")
        example_json = json.dumps(artifact.example_context, indent=2)
        hints.extend(example_json.split('\n'))
    
    return hints
```

#### 2.2 Enhanced Validation Error

**Location:** `TemplateScaffolder.validate()` line ~80

**Before:**
```python
if missing:
    raise ValidationError(
        f"Missing required fields for {artifact_type}: "
        f"{', '.join(missing)}"
    )
```

**After:**
```python
if missing:
    hints = self._format_context_help(
        artifact_type,
        missing_fields=missing,
        provided_fields=list(kwargs.keys())
    )
    raise ValidationError(
        f"Missing required fields for {artifact_type}: "
        f"{', '.join(missing)}",
        hints=hints
    )
```

#### 2.3 Jinja2 Error Wrapping

**Location:** `TemplateScaffolder._load_and_render_template()` line ~162

**Before:**
```python
return self._renderer.render(template_name, **kwargs)
```

**After:**
```python
try:
    return self._renderer.render(template_name, **kwargs)
except jinja2.UndefinedError as e:
    # Extract variable name from error message
    # Pattern: "'varname' is undefined"
    field_match = re.search(r"'(\w+)' is undefined", str(e))
    field_name = field_match.group(1) if field_match else "unknown"
    
    # Get artifact_type from context (need to pass it through)
    # For now, extract from template_name
    artifact_type = self._infer_artifact_type(template_name)
    
    # Generate helpful hints
    hints = self._format_context_help(
        artifact_type,
        missing_fields=[field_name],
        provided_fields=list(kwargs.keys())
    )
    
    raise ValidationError(
        f"Template rendering failed - required variable '{field_name}' not provided",
        hints=hints
    ) from e
```

**Helper Method:**

```python
def _infer_artifact_type(self, template_name: str) -> str:
    """Infer artifact type from template name.
    
    Args:
        template_name: Template path (e.g., "components/dto.py.jinja2")
    
    Returns:
        Artifact type_id or "unknown"
    
    Note: This is a fallback - prefer passing artifact_type explicitly.
    """
    # Match template_name against registry
    for artifact in self.registry.artifact_types:
        if artifact.template_path == template_name:
            return artifact.type_id
    
    # Fallback: extract from filename
    # "components/dto.py.jinja2" -> "dto"
    base_name = Path(template_name).stem.replace('.py', '')
    if self.registry.has_artifact_type(base_name):
        return base_name
    
    return "unknown"
```

---

## Error Message Examples

### Example 1: Missing Required Field

**Trigger:**
```python
scaffold_artifact("dto", name="TradeSignal")  # Missing 'description'
```

**Error Message:**
```
ValidationError: Missing required fields for dto: description

Hints:
  Template 'components/dto.py.jinja2' expects these variables:
  
  Required:
    ✓ name
    ✗ description
  
  Optional:
      fields
      frozen
  
  Example Context:
  {
    "name": "TradeSignal",
    "description": "Signal for trade execution",
    "fields": [
      {"name": "symbol", "type": "str"},
      {"name": "price", "type": "Decimal"}
    ]
  }
```

### Example 2: Undefined Variable in Template

**Trigger:**
```python
scaffold_artifact("worker", input_dto="SignalDTO")  
# Missing 'output_dto', 'name'
```

**Error Message:**
```
ValidationError: Template rendering failed - required variable 'output_dto' not provided

Hints:
  Template 'components/worker.py.jinja2' expects these variables:
  
  Required:
    ✗ name
    ✓ input_dto
    ✗ output_dto
  
  Optional:
      dependencies
      docstring
      worker_type
  
  Example Context:
  {
    "name": "ProcessSignal",
    "input_dto": "SignalDTO",
    "output_dto": "ProcessedSignalDTO",
    "dependencies": ["strategy_cache: IStrategyCache"]
  }
```

### Example 3: Unknown Artifact Type

**Trigger:**
```python
scaffold_artifact("dto_invalid", name="Test")
```

**Error Message (existing - no changes):**
```
ConfigError: Artifact type 'dto_invalid' not found in registry.
Available types: {dynamically from artifacts.yaml}.
Fix: Check spelling or add new type to .st3/artifacts.yaml.

Hints:
  Check spelling: 'dto_invalid' not found
  Available types: dto, worker, adapter, tool, design, architecture, tracking, generic
  Add new type to .st3/artifacts.yaml if needed
```

---

## Implementation Sequence

### Task 1: Template Introspection Infrastructure (2-3h)

**Subtasks:**
1. Add `analyzer: TemplateAnalyzer` parameter to `TemplateScaffolder.__init__`
2. Implement `_extract_template_schema()` method
3. Implement `_detect_conditional_variables()` method
4. Implement `_infer_artifact_type()` helper
5. Add unit tests for schema extraction

**Test Cases:**
```python
def test_extract_template_schema_dto():
    """Test schema extraction from dto template."""
    schema = scaffolder._extract_template_schema("dto")
    assert "name" in schema["required"]
    assert "description" in schema["required"]
    assert "fields" in schema["optional"]

def test_detect_conditional_variables():
    """Test detection of conditional variables."""
    template = Path("test_template.jinja2")
    template.write_text("{% if optional_field %}{{ optional_field }}{% endif %}")
    optional = scaffolder._detect_conditional_variables(template)
    assert "optional_field" in optional
```

### Task 2: Context Help Formatting (1h)

**Subtasks:**
1. Implement `_format_context_help()` method
2. Add unit tests for hint formatting
3. Test with/without example_context

**Test Cases:**
```python
def test_format_context_help_with_missing():
    """Test hint formatting with missing fields."""
    hints = scaffolder._format_context_help(
        "dto",
        missing_fields=["description"],
        provided_fields=["name"]
    )
    assert "✗ description" in "\n".join(hints)
    assert "✓ name" in "\n".join(hints)
```

### Task 3: Add Example Contexts (1h)

**Subtasks:**
1. Add `example_context` to artifacts.yaml for:
   - dto
   - worker
   - adapter
   - design
   - architecture
2. Validate examples work (scaffold test)

**Example Additions:**

```yaml
# In .st3/artifacts.yaml

- type: code
  type_id: dto
  # ... existing fields ...
  example_context:
    name: TradeSignal
    description: Signal for trade execution
    fields:
      - name: symbol
        type: str
        description: Trading symbol
      - name: price
        type: Decimal
        description: Current price

- type: code
  type_id: worker
  # ... existing fields ...
  example_context:
    name: ProcessSignal
    input_dto: SignalDTO
    output_dto: ProcessedSignalDTO
    dependencies:
      - "strategy_cache: IStrategyCache"
```

### Task 4: Enhanced Validation Errors (1h)

**Subtasks:**
1. Update `TemplateScaffolder.validate()` to use `_format_context_help()`
2. Add integration test for missing field error
3. Manual test in VS Code chat

**Test Case:**
```python
def test_validation_error_includes_schema_hints():
    """Test ValidationError includes template schema in hints."""
    with pytest.raises(ValidationError) as exc_info:
        scaffolder.scaffold("dto", name="Test")  # Missing description
    
    error = exc_info.value
    assert error.hints is not None
    hints_text = "\n".join(error.hints)
    assert "Template" in hints_text
    assert "Required:" in hints_text
    assert "description" in hints_text
```

### Task 5: Jinja2 Error Wrapping (1-2h)

**Subtasks:**
1. Wrap `_load_and_render_template()` with try/except
2. Implement `_infer_artifact_type()` helper
3. Add integration test for UndefinedError
4. Manual test with missing template variable

**Test Case:**
```python
def test_jinja2_undefined_error_wrapped():
    """Test Jinja2 UndefinedError is wrapped with helpful hints."""
    with pytest.raises(ValidationError) as exc_info:
        # Create context missing required template variable
        scaffolder.scaffold("dto", name="Test", description="Test DTO")
        # If template uses {{ fields }}, this will trigger UndefinedError
    
    error = exc_info.value
    assert "Template rendering failed" in error.message
    assert error.hints is not None
```

---

## Testing Strategy

### Unit Tests (Tests TBD Count)

**Template Introspection:**
- [ ] `test_extract_template_schema_dto()` - Extract from DTO template
- [ ] `test_extract_template_schema_worker()` - Extract from Worker template
- [ ] `test_detect_conditional_variables()` - Identify optional fields
- [ ] `test_detect_conditional_with_default_filter()` - Handle `| default(...)`
- [ ] `test_infer_artifact_type()` - Map template to artifact type

**Hint Formatting:**
- [ ] `test_format_context_help_basic()` - Format with required/optional
- [ ] `test_format_context_help_with_markers()` - Show ✓/✗ for provided/missing
- [ ] `test_format_context_help_with_example()` - Include example_context
- [ ] `test_format_context_help_no_optional()` - Handle templates with no optional vars

**Error Wrapping:**
- [ ] `test_validation_error_includes_hints()` - Missing field → hints added
- [ ] `test_jinja2_undefined_wrapped()` - UndefinedError → ValidationError with hints
- [ ] `test_jinja2_other_errors_passthrough()` - SyntaxError not wrapped (template bug)

### Integration Tests (Tests TBD Count)

**End-to-End Scenarios:**
- [ ] `test_scaffold_dto_missing_field()` - Missing required field → helpful error
- [ ] `test_scaffold_worker_undefined_var()` - Template var missing → helpful error
- [ ] `test_scaffold_with_example_context()` - Use example from artifacts.yaml → success
- [ ] `test_template_change_updates_error()` - Modify template → error reflects change

### Manual Testing Checklist

- [ ] Trigger missing field error in VS Code chat, verify readability
- [ ] Trigger undefined template var, verify field identified correctly
- [ ] Modify template (add required var), verify error updates automatically
- [ ] Test with multiple artifact types (dto, worker, design)
- [ ] Verify hints format correctly in VS Code markdown rendering

---

## Acceptance Criteria

### Phase 1 Complete When:

- [ ] TemplateScaffolder has `_analyzer` dependency injected
- [ ] `_extract_template_schema()` correctly identifies required/optional variables
- [ ] `_detect_conditional_variables()` uses Jinja2 AST to find conditionals
- [ ] `_format_context_help()` generates readable hints with template info
- [ ] Missing field errors show template schema + example
- [ ] Jinja2 UndefinedError wrapped with field name + schema
- [ ] 3-5 artifact types have `example_context` in artifacts.yaml
- [ ] All unit tests passing (15+ tests)
- [ ] Integration tests verify end-to-end error flow
- [ ] Manual test confirms readability in VS Code chat
- [ ] Template changes automatically reflected in error messages (no cache staleness)

### Quality Gates:

- [ ] All tests passing
- [ ] No hardcoded values in hints (all dynamic from config/templates)
- [ ] No schema duplication (templates = SSOT)
- [ ] Pyright type checking passes
- [ ] Black formatting applied
- [ ] Documentation updated (README if needed)

---

## Related Documentation

- **[research_phase1.md](research_phase1.md)** - Problem analysis and design decisions
- **[mcp_server/validation/template_analyzer.py](../../mcp_server/validation/template_analyzer.py)** - Template introspection utility
- **[mcp_server/scaffolders/template_scaffolder.py](../../mcp_server/scaffolders/template_scaffolder.py)** - Implementation target

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-21 | AI | Initial design: method signatures, error examples, implementation sequence, test strategy |

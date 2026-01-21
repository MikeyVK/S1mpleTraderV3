# Phase 1: Self-Documenting Errors - Research - S1mpleTraderV3

<!--
GENERATED DOCUMENT
Template: generic.md.jinja2
Type: Generic
-->

<!-- ═══════════════════════════════════════════════════════════════════════════
     HEADER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

**Status:** 🔬 In Progress
**Version:** 0.1
**Last Updated:** 2026-01-21


---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTEXT SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Purpose

Research and design self-documenting error messages for scaffold_artifact tool. Transform cryptic Python errors into actionable, schema-rich error messages with examples and suggestions.

## Scope

**In Scope:**
- Analysis of current error messages and their problems
- Research into industry best practices (Rust, Pydantic)
- Design of schema enhancement strategy for artifacts.yaml
- Design of error formatting helpers
- Implementation planning for 6 tasks
- Testing strategy definition

**Out of Scope:**
- Phase 2: Schema introspection tool (`get_artifact_schema`)
- Phase 3: Early context validation (before template rendering)
- Automated schema generation from templates
- Migration of existing error messages outside scaffolding

## Prerequisites

- ✅ Phase 0 completed (scaffold metadata infrastructure)
- ✅ Understanding of current ArtifactManager/TemplateScaffolder architecture
- ✅ Access to artifacts.yaml and template structure
- Understanding of JSON Schema basics

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTENT SECTION
     ═══════════════════════════════════════════════════════════════════════════ -->

## Overview

Phase 1 focuses on **enhancing existing error messages** with better context, not building new infrastructure. The codebase already has:

✅ **Centralized error handling**: `@tool_error_handler` decorator catches all exceptions  
✅ **Structured error responses**: `ToolResult.error()` with `error_code`, `hints`, `file_path`  
✅ **MCPError hierarchy**: All domain exceptions support hints out of the box  
✅ **No server crashes**: Errors return as tool responses to VS Code chat  

**What's Missing (Issue #120 Goal):**
- Context schema information when scaffolding fails
- Example contexts showing correct structure
- Better hints for missing required fields
- Clearer guidance when workspace_root not configured

**Key Insight**: This is about improving **hint quality and context**, NOT adding new error infrastructure. The plumbing exists, we just need better content in the hints.

## Problem Analysis

### Current Error Messages

**What Already Works:**

1. **workspace_root errors** - Already have good hints:
```python
ConfigError: workspace_root not configured - cannot resolve artifact paths automatically

Hints:
  Option 1: Initialize ArtifactManager with workspace_root parameter: ArtifactManager(workspace_root='/path/to/workspace')
  Option 2: Provide explicit output_path in scaffold_artifact() call  
  Option 3: For MCP tools, workspace_root should be passed from server initialization
```
✅ Clear problem, ✅ Multiple solutions, ✅ Context-aware

2. **Unknown artifact type** - Already has good hints:
```python
ConfigError: Artifact type 'dto_invalid' not found in registry.
Available types: dto, worker, adapter, design, architecture, tracking, generic.
Fix: Check spelling or add new type to .st3/artifacts.yaml.

Hints:
  Check spelling: 'dto_invalid' not found
  Available types: dto, worker, adapter, design, architecture, tracking, generic
  Add new type to .st3/artifacts.yaml if needed
```
✅ Shows available options, ✅ Actionable fixes

**What Needs Improvement:**

3. **Missing required fields** - Minimal context:
```python
ValidationError: Missing required fields for dto: ['fields']
```
❌ No schema shown, ❌ No example, ❌ No type info

**Should be:**
```python
ValidationError: Missing required fields for dto: ['fields']

Expected Schema:
  name: string (required) - DTO class name in PascalCase
  fields: array (required) - List of field definitions
    - name: string - Field name
    - type: string - Python type hint
    - description: string - Field purpose
  frozen: boolean (optional, default=true) - Immutable DTO

Example Context:
  {
    "name": "TradeSignal",
    "fields": [
      {"name": "symbol", "type": "str", "description": "Trading symbol"},
      {"name": "price", "type": "Decimal", "description": "Current price"}
    ],
    "frozen": true
  }
```

4. **Template rendering errors** - Python traceback leaks through:
```python
jinja2.exceptions.UndefinedError: 'name' is undefined
```
❌ Implementation detail exposed, ❌ No guidance

**Should be:**
```python
ValidationError: Template rendering failed - required context field missing

Template expects field: 'name'
Artifact type: dto
Required fields: name, fields
Provided fields: fields

See schema above for complete requirements.
```

### What Good Error Messages Look Like

**Industry Examples:**

1. **Rust Compiler:**
```
error[E0308]: mismatched types
  --> src/main.rs:4:18
   |
4  |     let x: i32 = "hello";
   |            ---   ^^^^^^^ expected `i32`, found `&str`
   |            |
   |            expected due to this
   |
   = help: try using `.parse()` to convert string to number
```

2. **Pydantic V2:**
```python
ValidationError: 1 validation error for UserModel
age
  Input should be a valid integer, got string [type=int_type]
  For further information visit https://errors.pydantic.dev/2.0/v/int_type
```

**Key Principles:**
- Show what was expected vs what was received
- Provide concrete examples or suggestions
- Point to relevant documentation
- Use domain language (not implementation details)
- Surface errors early (fail fast)

### Requirements for Phase 1

**Must Have (Core Improvements):**
1. **Schema in hints** - Add context schema to missing field errors
2. **Example contexts** - Provide working example for each artifact type
3. **Template error wrapping** - Catch Jinja2 errors, show which field is undefined

**Should Have (Quality Improvements):**
4. **Better validation errors** - Show which fields were provided vs expected
5. **Type information** - Show expected types for each field in schema

**Nice to Have (Future):**
6. **Diff highlighting** - Visual comparison when context provided but incomplete
7. **Fuzzy matching** - "Did you mean?" for artifact type typos (may already work via hints)

**Out of Scope (Already Works or Not Needed):**
- ❌ New error infrastructure (already excellent with @tool_error_handler)
- ❌ workspace_root errors (already have comprehensive hints)
- ❌ Unknown artifact type (already lists all available types)
- ❌ Early validation (Jinja2 rendering is fine, just need better wrapping)



## Proposed Solution

### What We're Actually Doing

**NOT building new error infrastructure** - Just enhancing existing hints in 2 places:

1. **TemplateScaffolder.validate()** - When required fields missing
2. **TemplateScaffolder._load_and_render_template()** - When Jinja2 rendering fails

### Architecture Overview

**Current Flow (Already Good):**
```
TemplateScaffolder raises ValidationError
         ↓
@tool_error_handler catches it  
         ↓
ToolResult.error(message, hints=...)
         ↓
VS Code chat shows structured error
```

**What Changes:**
- ValidationError gets **better hints** (schema + example)
- Jinja2 errors get **wrapped** instead of leaking through

### Component Design

#### 1. Schema Generation from Templates (SSOT Compliance)

**NO manual schema in artifacts.yaml** - Extract directly from templates:

```python
# TemplateScaffolder gets TemplateAnalyzer helper
def _extract_template_schema(self, artifact_type: str) -> dict[str, Any]:
    """Extract required/optional variables from template.
    
    Uses TemplateAnalyzer.extract_jinja_variables() to parse template AST.
    Returns: {"required": [...], "optional": [...]}
    """
    artifact = self.registry.get_artifact(artifact_type)
    template_path = self.template_root / artifact.template_path
    
    # Extract ALL undeclared variables from template
    all_vars = self.analyzer.extract_jinja_variables(template_path)
    
    # Detect which are conditional (optional)
    optional_vars = self._detect_conditional_variables(template_path)
    
    return {
        "required": [v for v in all_vars if v not in optional_vars],
        "optional": list(optional_vars)
    }

def _detect_conditional_variables(self, template_path: Path) -> set[str]:
    """Detect variables used inside {% if %} blocks.
    
    Returns set of variable names that are conditional (optional).
    """
    source = template_path.read_text()
    # Parse for {% if varname %} patterns
    # Variables in conditionals are optional
    # Implementation uses regex or Jinja2 AST walker
```

**Why This Works:**
- Templates = SSOT (single source of truth)
- Template changes → automatic schema updates
- No duplication in artifacts.yaml
- Zero drift/sync issues

#### 2. Hint Formatting Helper (Generates Schema from Template)

Add to `TemplateScaffolder`:

```python
def _format_context_help(
    self,
    artifact_type: str,
    missing_fields: list[str] | None = None,
    provided_fields: list[str] | None = None
) -> list[str]:
    """Format hints with template-derived schema.
    
    Generates schema dynamically from template analysis (SSOT).
    Shows example from artifacts.yaml if available.
    """
    # Extract schema from template (SSOT)
    schema = self._extract_template_schema(artifact_type)
    
    hints = []
    
    # Show required variables from template
    hints.append("Template expects these variables:")
    hints.append("")
    hints.append("Required:")
    for var in schema["required"]:
        marker = " ✗ " if var in (missing_fields or []) else " ✓ "
        provided_marker = marker if var in (provided_fields or []) else " ✗ "
        hints.append(f"  {provided_marker}{var}")
    
    if schema["optional"]:
        hints.append("")
        hints.append("Optional:")
        for var in schema["optional"]:
            hints.append(f"    {var}")
    
    # Show example if available in artifacts.yaml
    artifact = self.registry.get_artifact(artifact_type)
    if hasattr(artifact, 'example_context') and artifact.example_context:
        hints.append("")
        hints.append("Example Context:")
        hints.append(json.dumps(artifact.example_context, indent=2))
    
    return hints
```

**Key Points:**
- Schema extracted from template AST (not manual config)
- Example in artifacts.yaml is OK (shows usage, doesn't define schema)
- Required vs Optional determined by template structure

#### 3. Enhanced Error Sites (2 Locations)

**Location 1: TemplateScaffolder.validate()** - Missing fields
```python
# BEFORE:
if missing:
    raise ValidationError(
        f"Missing required fields for {artifact_type}: {', '.join(missing)}"
    )

# AFTER:
if missing:
    hints = self._format_context_help(artifact_type, missing_fields=missing)
    raise ValidationError(
        f"Missing required fields for {artifact_type}: {', '.join(missing)}",
        hints=hints
    )
```

**Location 2: TemplateScaffolder._load_and_render_template()** - Jinja2 errors
```python
# NEW: Wrap around existing Jinja2 rendering
try:
    rendered = env.get_template(template_name).render(**render_context)
except jinja2.UndefinedError as e:
    # Extract field name from error message
    field_match = re.search(r"'(\w+)' is undefined", str(e))
    field_name = field_match.group(1) if field_match else "unknown"
    
    hints = self._format_context_help(artifact_type, missing_fields=[field_name])
    raise ValidationError(
        f"Template rendering failed - required field '{field_name}' not provided",
        hints=hints
    ) from e
```

### Implementation Plan (REVISED FOR SSOT)

**Task 1: Implement template introspection methods** (2-3 hours)
- Add `_extract_template_schema()` to TemplateScaffolder
- Add `_detect_conditional_variables()` helper
- Inject TemplateAnalyzer dependency into TemplateScaffolder
- Add tests verifying correct required/optional detection

**Task 2: Update _format_context_help() to use introspection** (1 hour)
- Generate schema from template analysis
- Show required vs optional variables
- Add example from artifacts.yaml if present
- Add tests

**Task 3: Add example_context to artifacts.yaml** (1 hour)
- Add example_context (NOT schema) to 3-5 artifact types
- Examples show **usage**, templates define **schema**
- Examples help agents understand structure

**Task 4: Enhance missing field errors** (1 hour)
- Update TemplateScaffolder.validate()
- Add template-derived hints
- Add tests

**Task 5: Wrap Jinja2 errors** (1-2 hours)
- Catch UndefinedError in _load_and_render_template()
- Extract field name, show template schema in hints
- Add tests

**Total Estimate:** 6-8 hours (adjusted for template introspection complexity)

### Testing Strategy

**Unit Tests (per task):**
- Test _extract_template_schema() with various templates (dto, worker, documents)
- Test _detect_conditional_variables() identifies optional fields correctly
- Test _format_context_help() generates readable hints from template analysis
- Test Jinja2 error wrapping and field extraction
- Verify hints are properly structured as list[str]

**Integration Tests:**
- Test scaffold_artifact with missing fields → get template-derived schema in hints
- Test scaffold_artifact with undefined template var → get helpful error
- Test template changes automatically update schema in errors
- Verify ToolResult.error() preserves hints correctly

**Manual Testing:**
- Trigger missing field error, verify schema extracted from template
- Trigger undefined template var, verify field identified correctly
- Modify template, verify error message reflects changes
- Check error readability in VS Code chat



## Design Decisions

### Decision 1: Schema Source - Template Introspection vs Manual Config

**Options:**
1. Manual schema in artifacts.yaml (violates DRY/SSOT)
2. Generate schema from template analysis (templates as SSOT)
3. Hybrid: Manual descriptions + template variable extraction

**Decision:** Option 2 - Template introspection as SSOT

**Rationale (Critical SRP/DRY/SSOT Compliance):**
- **Templates are already the SSOT** for what variables are needed
- `TemplateAnalyzer.extract_jinja_variables()` already extracts all template variables via Jinja2 AST
- Adding schema to artifacts.yaml would **duplicate** what templates define
- Violates DRY principle - schema would drift from template reality
- Template changes → automatic schema updates (no sync issues)

**Architecture:**
```python
# Template IS the schema:
{{ name }}  # → Required variable
{% if fields %}...{% endif %}  # → Optional variable (conditional)
```

**Trade-offs:**
- Cannot provide human-readable descriptions in hints (acceptable - field names should be descriptive)
- Cannot show type information unless parsed from template (acceptable - examples show types)
- Requires template parsing on error (minimal overhead - already cached)
- **BENEFIT:** Zero duplication, templates remain SSOT

### Decision 2: Where to Add Helper Method

**Options:**
1. ArtifactManager (where I originally thought)
2. TemplateScaffolder (where errors actually happen)
3. Separate formatter utility

**Decision:** Option 2 - TemplateScaffolder

**Rationale:**
- Errors happen in TemplateScaffolder.validate() and .render()
- Keep error formatting close to error raising
- No need to pass context between managers
- Simpler dependency chain

**Trade-offs:**
- TemplateScaffolder gets slightly larger
- Could be reused elsewhere later (acceptable - YAGNI for now)

### Decision 3: Jinja2 Error Handling

**Options:**
1. Catch and wrap all Jinja2 errors
2. Only wrap UndefinedError (undefined variables)
3. Let Jinja2 errors bubble up unchanged

**Decision:** Option 2 - Only UndefinedError

**Rationale:**
- UndefinedError is most common agent mistake
- Other Jinja2 errors (syntax) indicate template bugs, not user errors
- Template bugs should be visible in stack trace
- Focus on agent-fixable errors

**Trade-offs:**
- Some Jinja2 errors still leak through (acceptable - they're rare)
- Requires checking exception type (simple)

### Decision 4: Example Storage Location

**Options:**
1. No examples at all (rely on template schema only)
2. Examples in artifacts.yaml (usage guidance only)
3. Examples in separate file

**Decision:** Option 2 - Examples in artifacts.yaml (acceptable duplication)

**Rationale:**
- Examples show **usage**, templates define **schema** (different responsibilities)
- Examples are documentation, not schema definition
- Helps agents construct correct context structure
- Single file lookup (no extra file reads)
- Can validate examples in tests (scaffold with example_context)

**Trade-offs:**
- Small duplication (acceptable - examples demonstrate, don't define)
- Manual maintenance (acceptable - examples rarely change)
- **CRITICAL:** Schema NEVER in artifacts.yaml - only examples


## Open Questions

### Question 1: How to detect optional vs required template variables?

**Context:**
- `{{ name }}` is clearly required (direct usage)
- `{% if fields %}{{ fields }}{% endif %}` is optional (conditional)
- Need algorithm to distinguish these cases

**Options:**
1. Simple heuristic: variables in `{% if var %}` blocks are optional
2. Full AST analysis: trace variable usage in conditional contexts
3. Manual annotation in TEMPLATE_METADATA

**Recommendation:** Option 2 - AST analysis with fallback
- Jinja2 AST provides `If`, `Test`, and `Name` nodes
- Can detect if variable only used inside conditionals
- Fallback: assume required if unsure (safe - agent provides field, gets better error)

**Decision Point:** During implementation - test with dto/worker templates

### Question 2: Should TemplateAnalyzer cache introspection results?

**Context:**
- Template parsing happens on every error
- Templates rarely change during session
- TemplateAnalyzer already has `_metadata_cache`

**Recommendation:** Yes - extend existing cache
- Add `_schema_cache: dict[Path, dict]` to TemplateAnalyzer
- Cache result of `extract_jinja_variables()` + conditional analysis
- Minimal code change, significant performance gain

**Decision Point:** Implement caching during Task 1


## Next Steps

### Immediate Actions (This Research Phase)

1. **Commit updated research document** ✅ DONE
   - Corrected scope based on actual codebase analysis
   - Removed duplicate/unnecessary infrastructure
   - Focused on real pain points

2. **Transition to Design Phase**
   - Create design document with exact schema format examples
   - Define _format_context_help() signature and behavior
   - Document Jinja2 error wrapping approach

### Design Phase Tasks (Simplified)

1. **Schema Format Examples**
   - Show 2-3 complete artifact definitions with context_schema + example_context
   - Document plain text format conventions
   - Provide template for adding new artifact schemas

2. **Error Enhancement Patterns**
   - Document exact code changes for TemplateScaffolder.validate()
   - Document Jinja2 UndefinedError wrapping pattern
   - Show before/after error message examples

**TDD Phase Approach (Realistic):**

**RED Phase:** (1-2 hours)
- Write test: _extract_template_schema(dto) → expect {"required": ["name", "description"], "optional": ["fields"]}
- Write test: scaffold_artifact(dto, name="Test") → expect "missing fields" with template-derived hints
- Write test: scaffold with undefined var → expect wrapped error with field name
- Write test: _format_context_help() returns proper hint structure with template variables

**GREEN Phase:** (3-4 hours)
- Implement _extract_template_schema() using TemplateAnalyzer
- Implement _detect_conditional_variables() via AST analysis
- Update _format_context_help() to use template introspection
- Add example_context to 3 artifacts (dto, worker, design)
- Wrap ValidationError in TemplateScaffolder.validate()
- Wrap UndefinedError in _load_and_render_template()

**REFACTOR Phase:** (1-2 hours)
- Add caching to TemplateAnalyzer for schema results
- Improve hint readability
- Add docstrings and type hints
- Run quality gates

### Success Criteria (Updated)

**Phase 1 Complete When:**
- [ ] TemplateScaffolder extracts schema from template AST (templates = SSOT)
- [ ] 3-5 artifact types have example_context (NOT schema) in artifacts.yaml
- [ ] Missing field errors show template-derived required/optional variables
- [ ] Jinja2 UndefinedError wrapped with template schema context
- [ ] Tests verify schema extraction correctness
- [ ] Manual test confirms: template change → error message updates automatically

**Quality Gates:**
- All tests passing (including template introspection tests)
- No duplication: schema only in templates, examples only in artifacts.yaml
- No regressions in existing error handling
- Documentation updated with SSOT principle explanation




---

<!-- ═══════════════════════════════════════════════════════════════════════════
     FOOTER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Related Documentation

- **[README.md](../../README.md)** - Project overview

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-21 | AI | Initial research: problem analysis, solution design, implementation plan |
| 0.2 | 2026-01-21 | AI | **MAJOR REVISION**: Corrected scope after deep codebase analysis - removed duplicate infrastructure, focused on hint quality improvements only (5-8h vs 12-18h) |
| 0.3 | 2026-01-21 | AI | **ARCHITECTURAL CORRECTION**: Removed schema duplication in artifacts.yaml after SRP/DRY/SSOT feedback. Templates are now SSOT for schema, using TemplateAnalyzer introspection. Examples remain in artifacts.yaml (usage guidance only). Estimate: 6-8h |

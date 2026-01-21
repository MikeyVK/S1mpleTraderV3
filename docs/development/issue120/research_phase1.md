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

#### 1. Schema Storage in artifacts.yaml (Minimal Addition)

Add **two simple fields** to each artifact definition:

```yaml
artifacts:
  dto:
    # ... existing fields ...
    
    # NEW: Simple schema description (plain text, not JSON Schema)
    context_schema:
      name: "string (required) - DTO class name in PascalCase"
      fields: "array (required) - List of field definitions with name, type, description"
      frozen: "boolean (optional, default=true) - Whether DTO is immutable"
    
    # NEW: Working example
    example_context:
      name: TradeSignal
      fields:
        - name: symbol
          type: str
          description: Trading symbol
      frozen: true
```

**Why plain text schema vs JSON Schema?**
- Simpler to write and maintain
- Easier to read in error messages
- Sufficient for hints (not doing validation)

#### 2. Hint Formatting Helper (Simple Method)

Add to `TemplateScaffolder` (NOT ArtifactManager - keep it where errors happen):

```python
def _format_context_help(
    self,
    artifact_type: str,
    missing_fields: list[str] | None = None
) -> list[str]:
    """Format hints with schema and example.
    
    Returns list of hint strings (MCPError already supports this).
    """
    artifact = self.registry.get_artifact(artifact_type)
    
    hints = []
    
    # Show schema
    if hasattr(artifact, 'context_schema') and artifact.context_schema:
        hints.append("Expected Schema:")
        for field, desc in artifact.context_schema.items():
            marker = " * " if field in (missing_fields or []) else "   "
            hints.append(f"{marker}{field}: {desc}")
        hints.append("")
    
    # Show example
    if hasattr(artifact, 'example_context') and artifact.example_context:
        hints.append("Example Context:")
        hints.append(json.dumps(artifact.example_context, indent=2))
    
    return hints
```

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

### Implementation Plan (SIMPLIFIED)

**Task 1: Add schema + example to 5 artifact types** (2-3 hours)
- dto, worker, adapter (code artifacts)
- design, architecture (doc artifacts)  
- Add as plain text in artifacts.yaml

**Task 2: Implement _format_context_help()** (1-2 hours)
- Add method to TemplateScaffolder
- Format schema and example as hint list
- Add tests

**Task 3: Enhance missing field errors** (1 hour)
- Update TemplateScaffolder.validate()
- Add formatted hints
- Add tests

**Task 4: Wrap Jinja2 errors** (1-2 hours)
- Catch UndefinedError in _load_and_render_template()
- Extract field name, format hints
- Add tests

**Total Estimate:** 5-8 hours (NOT 12-18!)

### Testing Strategy

**Unit Tests (per task):**
- Test _format_context_help() with various artifact types
- Test missing field error formatting
- Test Jinja2 error wrapping and field extraction
- Verify hints are properly structured as list[str]

**Integration Tests:**
- Test scaffold_artifact with missing fields → get schema + example in hints
- Test scaffold_artifact with undefined template var → get helpful error  
- Verify ToolResult.error() preserves hints correctly

**Manual Testing:**
- Trigger missing field error, verify schema shows
- Trigger undefined template var, verify field identified
- Check error readability in VS Code chat



## Design Decisions

### Decision 1: Plain Text Schema vs JSON Schema

**Options:**
1. Full JSON Schema specification
2. Plain text descriptions (field: "type (required/optional) - description")
3. Custom schema format

**Decision:** Option 2 - Plain text descriptions

**Rationale:**
- Not doing validation, just showing hints
- Plain text is easier to read in error messages
- Simpler to write and maintain in artifacts.yaml
- Can always add JSON Schema later if needed

**Trade-offs:**
- No machine validation of schema structure
- Manual formatting required
- Sufficient for current use case (error hints)

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

### Decision 4: Schema Completeness

**Options:**
1. Minimal: Just required field names
2. Medium: Required + optional with types and descriptions
3. Detailed: Add validation rules, patterns, constraints

**Decision:** Option 2 - Medium detail

**Rationale:**
- Enough info to construct correct context
- Not duplicating template validation logic
- Easy to maintain manually

**Trade-offs:**
- Won't catch all validation errors (that's fine - template catches those)
- Manual updates when template changes (acceptable - infrequent)


## Open Questions

### Question 1: Should example_context be validated against templates?

**Context:**
- example_context in artifacts.yaml might get out of sync with templates
- No automated check if examples actually work

**Options:**
1. No validation (trust manual maintenance)
2. Add test that scaffolds with example_context
3. Generate examples from template analysis

**Recommendation:** Option 2 - Add test per artifact type
- Simple pytest that calls scaffold_artifact(type, **example_context)
- Catches schema/template mismatches during test runs
- Minimal maintenance overhead

**Decision Point:** After implementing 2-3 artifacts, assess if test needed

### Question 2: How to handle nested context structures?

**Context:**
- dto.fields is array of objects
- Plain text schema might be unclear for nesting

**Options:**
1. Flatten description (current approach)
2. Use indentation to show nesting
3. Show example first, schema second

**Recommendation:** Option 3 - Example-first
- Example is clearer than schema for nested structures
- Schema provides type/requirement info
- Most agents learn better from examples

**Decision Point:** After first manual test, evaluate clarity


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

### TDD Phase Approach (Realistic)

**RED Phase:** (1-2 hours)
- Write test: scaffold_artifact(dto, name="Test") → expect "missing fields" with schema hints
- Write test: scaffold with undefined var → expect wrapped error with field name
- Write test: _format_context_help() returns proper hint structure

**GREEN Phase:** (3-4 hours)
- Implement _format_context_help() method
- Add context_schema + example_context to 3 artifacts (dto, worker, design)
- Wrap ValidationError in TemplateScaffolder.validate()
- Wrap UndefinedError in _load_and_render_template()

**REFACTOR Phase:** (1-2 hours)
- Extract schema formatting logic if duplicated
- Improve hint readability
- Add docstrings and type hints
- Run quality gates

### Success Criteria (Achievable)

**Phase 1 Complete When:**
- [ ] 3-5 artifact types have context_schema and example_context
- [ ] Missing field errors show schema + example in hints
- [ ] Jinja2 UndefinedError wrapped with helpful context
- [ ] Tests verify hint structure and content
- [ ] Manual test confirms readability in VS Code chat

**Quality Gates:**
- All tests passing (including new error scenario tests)
- No regressions in existing error handling
- Documentation updated with error message examples




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

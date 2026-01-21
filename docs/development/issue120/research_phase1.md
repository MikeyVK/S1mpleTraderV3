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

Phase 1 focuses on transforming cryptic Python exceptions into self-documenting, actionable error messages. When scaffold_artifact fails, agents should receive:

1. **What went wrong** - Clear problem description in domain language
2. **What was expected** - Complete context schema with types and descriptions
3. **What was provided** - Diff showing expected vs actual context
4. **How to fix it** - Step-by-step solutions with examples
5. **Why it matters** - Context about the artifact type and its requirements

This research identifies current pain points, proposes enhancement strategies, and defines an implementation plan for 6 tasks estimated at 12-18 hours of work.

## Problem Analysis

### Current Error Messages

**Example 1: Missing workspace_root**
```python
TypeError: unsupported operand type(s) for /: 'NoneType' and 'str'
```

**Problems:**
- Generic Python exception, no domain context
- Stack trace points to internal code, not user error
- No hint about what's wrong or how to fix it
- Agent has to debug through stack trace

**Example 2: Missing context field**
```python
jinja2.exceptions.UndefinedError: 'name' is undefined
```

**Problems:**
- Error happens during template rendering (late failure)
- No info about required schema
- No example of correct context
- Trial-and-error required

**Example 3: Invalid artifact type**
```python
ConfigError: Unknown artifact type: 'dto_invalid'
```

**Better than above, but still lacks:**
- List of valid artifact types
- Did you mean? suggestions (fuzzy matching)
- Link to registry or documentation

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

**Must Have:**
1. **Schema-rich errors** - Show complete expected schema when context validation fails
2. **Example contexts** - Provide working examples for each artifact type
3. **Clear solutions** - Step-by-step fix instructions
4. **Workspace_root errors** - Special handling for common configuration issue
5. **Type information** - Show expected types for each field
6. **Required vs Optional** - Distinguish mandatory vs optional fields

**Nice to Have:**
7. **Diff highlighting** - Visual comparison of expected vs provided
8. **Fuzzy matching** - "Did you mean?" for typos
9. **Links to docs** - Direct links to relevant documentation
10. **Error codes** - Structured error codes for programmatic handling



## Proposed Solution

### Architecture Overview

**Error Enhancement Strategy:**
```
Original Exception (e.g., TypeError, UndefinedError)
         ↓
  Error Detection Layer (ArtifactManager/TemplateScaffolder)
         ↓
  Error Formatting Layer (_format_schema_for_error)
         ↓
  Enhanced Exception (ValidationError/ConfigError with rich context)
         ↓
  User sees actionable error message
```

### Component Design

#### 1. Schema Enhancement in artifacts.yaml

**Add to ArtifactDefinition:**
```yaml
artifacts:
  dto:
    type_id: dto
    type: code
    # ... existing fields ...
    
    # NEW: Context schema (JSON Schema subset)
    context_schema:
      type: object
      required:
        - name
        - fields
      properties:
        name:
          type: string
          description: DTO class name (PascalCase)
          example: TradeSignal
        fields:
          type: array
          description: List of DTO fields with name, type, and description
          example:
            - name: symbol
              type: str
              description: Trading symbol
        frozen:
          type: boolean
          description: Whether DTO should be immutable
          default: true
    
    # NEW: Example context (complete working example)
    example_context:
      name: TradeSignal
      fields:
        - name: symbol
          type: str
          description: Trading symbol (e.g., AAPL)
        - name: price
          type: Decimal
          description: Current price
      frozen: true
```

**Design Decisions:**
- Use JSON Schema subset (simpler than full JSON Schema)
- Include inline examples in schema
- Provide complete working example_context
- Keep schema simple (avoid advanced validation rules)

#### 2. Error Formatting Helper

**New method in ArtifactManager:**
```python
def _format_schema_for_error(
    self,
    artifact_type: str,
    missing_fields: list[str] | None = None,
    provided_context: dict[str, Any] | None = None
) -> str:
    """Format schema information for error messages.
    
    Args:
        artifact_type: Artifact type_id
        missing_fields: List of missing required fields (optional)
        provided_context: Context that was provided (optional)
    
    Returns:
        Formatted error message with schema, examples, and suggestions
    """
    artifact = self.registry.get_artifact(artifact_type)
    
    # Build error message parts
    parts = [
        f"Scaffolding error for artifact type: {artifact_type}",
        "",
        "Expected Context Schema:",
        self._format_schema(artifact.context_schema),
        "",
    ]
    
    # Show missing fields if provided
    if missing_fields:
        parts.extend([
            "Missing Required Fields:",
            *[f"  - {field}" for field in missing_fields],
            "",
        ])
    
    # Show example
    parts.extend([
        "Example Context:",
        self._format_example(artifact.example_context),
        "",
    ])
    
    # Show diff if context was provided
    if provided_context:
        parts.extend([
            "Provided Context:",
            self._format_example(provided_context),
            "",
            "Comparison:",
            self._format_diff(artifact.example_context, provided_context),
        ])
    
    return "\n".join(parts)
```

#### 3. Exception Wrapping Points

**Locations to enhance error messages:**

1. **TemplateScaffolder.validate()** - Missing required fields
2. **TemplateScaffolder._load_and_render_template()** - Template rendering errors
3. **ArtifactManager.scaffold_artifact()** - Generic artifacts without output_path
4. **ArtifactManager.__init__()** - Missing workspace_root
5. **ArtifactRegistryConfig.get_artifact()** - Unknown artifact type

**Example Enhancement:**
```python
# BEFORE:
if missing:
    raise ValidationError(
        f"Missing required fields for {artifact_type}: {', '.join(missing)}"
    )

# AFTER:
if missing:
    schema_info = self._format_schema_for_error(
        artifact_type,
        missing_fields=missing,
        provided_context=kwargs
    )
    raise ValidationError(
        f"Missing required fields for {artifact_type}\n\n{schema_info}"
    )
```

#### 4. Workspace Root Error Enhancement

**Special case for common configuration error:**
```python
# In ArtifactManager.get_artifact_path()
if self.workspace_root is None:
    raise ConfigError(
        "workspace_root not configured in ArtifactManager",
        hints=[
            "ArtifactManager requires workspace_root to resolve artifact paths",
            "",
            "Solution 1: Pass workspace_root when initializing:",
            "  manager = ArtifactManager(workspace_root=Path('/project/root'))",
            "",
            "Solution 2: Use FilesystemAdapter with root_path:",
            "  fs = FilesystemAdapter(root_path='/project/root')",
            "  manager = ArtifactManager(fs_adapter=fs)",
            "",
            "Current configuration:",
            f"  workspace_root: {self.workspace_root}",
            f"  fs_adapter.root_path: {getattr(self.fs_adapter, 'root_path', 'N/A')}",
        ]
    )
```

### Implementation Plan

**Task Breakdown:**

**Task 1.1: Enhance artifacts.yaml with schemas** (2-3 hours)
- Add context_schema to 3-5 common artifact types (dto, worker, design)
- Add example_context to same types
- Validate YAML syntax
- Document schema format in artifacts.yaml comments

**Task 1.2: Implement _format_schema_for_error helper** (3-4 hours)
- Create formatting methods in ArtifactManager
- Handle required vs optional fields
- Format nested structures (arrays, objects)
- Add tests for formatting output

**Task 1.3: Enhance TemplateScaffolder errors** (2-3 hours)
- Wrap missing field errors with schema info
- Wrap template rendering errors with context
- Add tests for error scenarios

**Task 1.4: Enhance ArtifactManager errors** (2-3 hours)
- Wrap workspace_root errors with solutions
- Wrap generic artifact errors with requirements
- Add tests for configuration errors

**Task 1.5: Enhance ConfigError in registry** (1-2 hours)
- Add fuzzy matching for unknown artifact types
- List available types in error message
- Add tests for typo detection

**Task 1.6: Add diff highlighting** (2-3 hours)
- Implement context comparison
- Highlight missing/extra/mismatched fields
- Format diff for readability
- Add tests for diff scenarios

**Total Estimate:** 12-18 hours (1.5-2.5 days)

### Testing Strategy

**Unit Tests (per task):**
- Test error formatting with various schemas
- Test missing field detection
- Test workspace_root error messages
- Test fuzzy matching for typos
- Test diff highlighting

**Integration Tests:**
- Test end-to-end scaffold with invalid context
- Test error messages in real scenarios
- Verify error messages are actionable

**Manual Testing:**
- Trigger each error scenario manually
- Verify error messages are clear
- Check that suggestions work
- Validate examples are correct



## Design Decisions

### Decision 1: JSON Schema Subset vs Full JSON Schema

**Options:**
1. Full JSON Schema specification
2. Simplified subset (type, required, properties, description, example)
3. Custom schema format

**Decision:** Option 2 - Simplified subset

**Rationale:**
- Full JSON Schema is overkill for our use case
- We only need basic validation info for error messages
- Simpler format is easier to maintain in artifacts.yaml
- Can extend later if needed

**Trade-offs:**
- Less expressive than full JSON Schema
- No validation of schemas themselves (YAGNI for now)
- Manual schema maintenance (acceptable for ~20 artifact types)

### Decision 2: Schema Location

**Options:**
1. Inline in artifacts.yaml (context_schema field)
2. Separate schema files (.st3/schemas/*.json)
3. Python dataclasses with type hints

**Decision:** Option 1 - Inline in artifacts.yaml

**Rationale:**
- Keeps schema close to artifact definition
- Single source of truth in artifacts.yaml
- Easy to view schema when editing artifact config
- No need for schema file synchronization

**Trade-offs:**
- artifacts.yaml becomes larger (acceptable - still readable)
- No schema validation tooling (can add later)
- Harder to share schemas between artifact types (rare need)

### Decision 3: Error Enhancement Strategy

**Options:**
1. Catch and wrap all exceptions with enhanced errors
2. Enhance only domain exceptions (ValidationError, ConfigError)
3. Let Python exceptions bubble up unchanged

**Decision:** Option 2 - Enhance domain exceptions only

**Rationale:**
- Domain exceptions are under our control
- Python exceptions (TypeError, etc.) indicate bugs, not user errors
- Wrapping Python exceptions can hide bugs
- Focus on errors agents can fix

**Trade-offs:**
- Some cryptic errors remain (e.g., Jinja2 syntax errors)
- Requires careful exception handling in code
- Bug vs user error boundary is sometimes unclear

### Decision 4: Example Context Format

**Options:**
1. Inline in artifacts.yaml (example_context field)
2. Separate example files (.st3/examples/*.yaml)
3. Generated from schema defaults

**Decision:** Option 1 - Inline in artifacts.yaml

**Rationale:**
- Examples are small (20-50 lines)
- Keeps examples visible when editing artifact config
- Easy to update when schema changes
- Single file to maintain

**Trade-offs:**
- artifacts.yaml becomes larger
- Examples can't be executed/tested directly (acceptable)
- Duplication if multiple artifacts share structure (rare)

### Decision 5: Diff Highlighting Implementation

**Options:**
1. Terminal color codes (ANSI escape sequences)
2. Plain text with markers (+ / - / ~)
3. No diff, just show expected vs provided separately

**Decision:** Option 2 - Plain text with markers

**Rationale:**
- Works in all environments (VS Code, terminal, logs)
- No dependency on terminal capabilities
- Simple to implement and test
- Still clearly shows differences

**Trade-offs:**
- Less visually appealing than colors
- Requires parsing both contexts to compare
- Manual alignment of output formatting


## Open Questions

### Question 1: How detailed should context_schema be?

**Context:**
- Simple schemas just list required fields
- Detailed schemas include types, validation rules, examples
- Very detailed schemas duplicate template logic

**Options:**
1. Minimal: Just required field names
2. Medium: Field names + types + descriptions
3. Detailed: Add validation rules, patterns, constraints

**Recommendation:** Start with Medium (Option 2)
- Provides enough info for good error messages
- Doesn't duplicate template validation logic
- Can extend to detailed later if needed

**Decision Point:** After implementing 2-3 artifact schemas, evaluate if more detail needed

### Question 2: Should we validate context_schema in artifacts.yaml?

**Context:**
- Schemas are currently unvalidated YAML
- Typos in schemas lead to broken error messages
- Validation adds complexity

**Options:**
1. No validation (trust developers)
2. Validate on load (fail fast if schema invalid)
3. Validate in tests only

**Recommendation:** Option 3 - Validate in tests only
- Catches schema errors during development
- Doesn't slow down runtime
- Can add runtime validation later if needed

**Decision Point:** After Phase 1 implementation, assess schema error rate

### Question 3: How to handle nested schema structures?

**Context:**
- Some artifacts have nested context (e.g., dto.fields is array of objects)
- Nested structures are harder to format in errors
- Examples need to show nested structure clearly

**Options:**
1. Flatten everything to top-level fields
2. Support one level of nesting (sufficient for current needs)
3. Support arbitrary nesting depth

**Recommendation:** Option 2 - One level of nesting
- Handles current artifact types (dto, worker, etc.)
- Simpler formatting logic
- Can extend later if deeper nesting needed

**Decision Point:** After implementing dto and worker schemas, evaluate nesting needs


## Next Steps

### Immediate Actions (This Research Phase)

1. **Review this research document**
   - Validate problem analysis
   - Confirm design decisions
   - Identify gaps or concerns

2. **Transition to Design Phase**
   - Create detailed design document
   - Define exact schema format
   - Specify error message templates
   - Document API changes

3. **Get Approval**
   - Review with stakeholders
   - Address feedback
   - Finalize approach

### Design Phase Tasks

1. **Schema Format Specification**
   - Define JSON Schema subset
   - Document field types and constraints
   - Provide schema examples

2. **Error Message Templates**
   - Define structure of enhanced errors
   - Create message templates
   - Specify formatting conventions

3. **API Design**
   - Define _format_schema_for_error signature
   - Specify helper methods
   - Document exception hierarchy changes

### TDD Phase Approach

**RED Phase:**
- Write tests for enhanced error messages
- Tests expect schema-rich errors with examples
- Tests verify workspace_root error handling
- Tests check diff highlighting

**GREEN Phase:**
- Implement _format_schema_for_error
- Add context_schema to artifacts.yaml
- Wrap exceptions with enhanced messages
- Implement diff highlighting

**REFACTOR Phase:**
- Extract common formatting logic
- Improve error message readability
- Add helper methods for schema formatting
- Clean up exception handling code

### Success Criteria

**Phase 1 Complete When:**
- [ ] 5+ artifact types have context_schema and example_context
- [ ] All scaffolding errors include schema information
- [ ] Workspace_root errors have clear solutions
- [ ] Missing field errors show expected schema
- [ ] Diff highlighting shows expected vs provided
- [ ] Tests verify error message quality
- [ ] Documentation updated with error examples

**Quality Gates:**
- Error messages tested with real scenarios
- Schema format validated across artifact types
- Error message readability reviewed
- Examples verified to work with templates




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

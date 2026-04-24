# Phase 1: Template-Driven Validation - Implementation Plan

<!-- SCAFFOLD: template=tracking version=1.0 created=2026-01-21T15:30:00Z path=docs/development/issue120/phase1-implementation-plan.md -->

**Status:** IN PLANNING  
**Last Updated:** 2026-01-21  
**Issue:** #120 - Scaffolder: Improve error messages and context validation  
**Phase:** Phase 1 (Template Introspection & Self-Documenting Errors)

---

## Executive Summary

**Objective:** Implement template introspection capability to generate schema dynamically from Jinja2 templates, enabling self-documenting error messages that eliminate DRY violations between artifacts.yaml and templates.

**Scope:** Issue #120 only (scaffolding validation). Issue #121 (content-aware editing) follows sequentially.

**Approach:** Conservative - start with simple required/optional detection, extend iteratively based on real-world template complexity.

**Success Criteria:**
- ✅ Template schema extracted automatically (no manual required_fields in artifacts.yaml)
- ✅ Error messages show template-derived schema with status indicators (✓/✗)
- ✅ Zero drift between templates and validation
- ✅ Existing templates work without modification

---

## Implementation Roadmap

### Phase 1.1: Template Introspection Foundation (Priority: HIGH)

**Deliverables:**
1. **New Module: `mcp_server/scaffolding/template_introspector.py`**
   - Purpose: Parse Jinja2 template AST to extract variable schema
   - Capability: Detect required vs optional variables
   - No code implementation in planning - detailed design follows in design phase

2. **Schema Format Definition**
   - Format: `{"required": [...], "optional": [...]}`
   - Flat structure (no nesting) for MCP/Claude compatibility
   - JSON serializable for tool responses

3. **Integration Point**
   - Hook into TemplateScaffolder validation flow
   - Call introspector before template rendering
   - Replace artifacts.yaml required_fields with dynamic schema

**Dependencies:**
- Jinja2 `meta.find_undeclared_variables()` API (stable, existing dependency)
- Existing TemplateScaffolder class (no structural changes needed)

**Testing Strategy:**
- Unit tests: Parse real templates (dto, worker, design) → verify schema
- Edge cases: Nested conditionals, complex filters, loops
- Performance tests: Schema generation < 100ms per template

**Validation Points:**
- Schema extraction matches actual template variables
- Required/optional classification conservative (safe defaults)
- All existing templates produce valid schema

**Risks & Mitigation:**
- Risk: Complex template patterns hard to classify → Mitigation: Start conservative, classify ambiguous as required
- Risk: Performance impact on every scaffold → Mitigation: Schema caching (covered in 1.2)

---

### Phase 1.2: Schema Caching Strategy (Priority: HIGH)

**Deliverables:**
1. **Cache Infrastructure**
   - Where: In-memory cache within TemplateScaffolder instance
   - Key: Template file path + modification timestamp
   - Invalidation: Automatic on template file change detection

2. **Cache Behavior**
   - First call: Parse template → cache schema
   - Subsequent calls: Return cached schema (if template unchanged)
   - Template change: Invalidate cache → re-parse

**Dependencies:**
- Phase 1.1 (introspection must work before caching)
- File system monitoring for template mtime

**Testing Strategy:**
- Performance tests: Cached vs uncached schema retrieval
- Cache invalidation tests: Template modification triggers re-parse
- Memory tests: Cache size reasonable for ~20-30 templates

**Validation Points:**
- First scaffold of template: < 100ms (includes parsing)
- Subsequent scaffolds: < 10ms (cache hit)
- Template change detected correctly (mtime-based)

**Risks & Mitigation:**
- Risk: Stale cache if template changes externally → Mitigation: mtime-based invalidation
- Risk: Memory bloat with many templates → Mitigation: LRU eviction (if needed)

---

### Phase 1.3: Enhanced Error Messages (Priority: HIGH)

**Deliverables:**
1. **Error Format Specification**
   - Schema display: Flat list of required/optional fields
   - Status indicators: ✓ provided, ✗ missing
   - No example_context (can drift from template truth)

2. **Error Message Structure**
   ```
   ValidationError: Missing required fields for artifact 'dto'
   
   Template Schema:
   Required: name, description, fields
   Optional: frozen, validators
   
   Provided Context:
   ✓ name
   ✗ description (MISSING)
   ✓ fields
   ```

3. **Integration Points**
   - TemplateScaffolder.validate() enhancement
   - Wrap Jinja2 UndefinedError with enriched message
   - Consistent format across all artifact types

**Dependencies:**
- Phase 1.1 (schema extraction)
- Existing exception handling in TemplateScaffolder

**Testing Strategy:**
- E2E tests: Trigger validation errors → verify message format
- Consistency tests: All artifact types use same error format
- Agent feedback tests: Error messages actionable (manual validation)

**Validation Points:**
- Error message contains template-derived schema
- Status indicators show exactly what's missing
- No hardcoded field names in error messages

**Risks & Mitigation:**
- Risk: Error messages too verbose for simple cases → Mitigation: Concise format, essential info only
- Risk: Inconsistent formatting across artifact types → Mitigation: Centralized error formatter

---

### Phase 1.4: Query Tool for Schema Discovery (Priority: MEDIUM)

**Deliverables:**
1. **New MCP Tool: `get_artifact_schema`**
   - Purpose: Agent pre-flight checks before scaffolding
   - Input: artifact_type (e.g., "dto")
   - Output: Template-derived schema (JSON)

2. **Tool Integration**
   - Tool registration in MCP server
   - Reuse introspector from Phase 1.1
   - Return cached schema (Phase 1.2)

**Dependencies:**
- Phase 1.1 (introspection)
- Phase 1.2 (caching for performance)
- MCP server tool registration (existing infrastructure)

**Testing Strategy:**
- Tool invocation tests: Call with various artifact types
- Performance tests: Response time < 50ms (cache hit)
- Error handling: Unknown artifact type → helpful error

**Validation Points:**
- Tool returns accurate schema for all artifact types
- Agent can use schema to prepare correct context
- Tool response format MCP-compatible

**Risks & Mitigation:**
- Risk: Tool adds complexity agents won't use → Mitigation: Optional feature, doesn't block core functionality
- Risk: Duplicate logic with validation flow → Mitigation: Shared introspector, single code path

---

### Phase 1.5: Deprecate Manual Fields in artifacts.yaml (Priority: LOW)

**Deliverables:**
1. **Migration Strategy**
   - Remove required_fields from artifacts.yaml (template = SSOT)
   - Keep optional_fields temporarily (deprecation warning)
   - Remove example_context (can drift, schema is truth)

2. **Backward Compatibility**
   - If required_fields present: Compare with template schema → warn on drift
   - Graceful degradation for legacy artifact definitions
   - Clear deprecation timeline in documentation

**Dependencies:**
- Phase 1.1, 1.2, 1.3 fully validated (introspection proven)
- Team consensus on deprecation approach

**Testing Strategy:**
- Migration tests: Remove fields from artifacts.yaml → still works
- Drift detection tests: Hardcoded fields mismatch → warning logged
- Rollback tests: Can revert if critical issues found

**Validation Points:**
- All templates work without manual field definitions
- Zero functional regressions after field removal
- Error messages quality unchanged (template-driven)

**Risks & Mitigation:**
- Risk: Breaking change impacts external tooling → Mitigation: Gradual deprecation, warnings first
- Risk: Edge cases not covered by introspection → Mitigation: Keep optional override mechanism

---

## Dependencies Map

```
Phase 1.1 (Introspection)
    ↓
Phase 1.2 (Caching) ← Depends on 1.1
    ↓
Phase 1.3 (Enhanced Errors) ← Depends on 1.1
    ↓
Phase 1.4 (Query Tool) ← Depends on 1.1, 1.2
    ↓
Phase 1.5 (Deprecation) ← Depends on 1.1, 1.2, 1.3 validated
```

**Critical Path:** 1.1 → 1.2 → 1.3 (core functionality)  
**Optional Path:** 1.4 (query tool - nice to have)  
**Future Path:** 1.5 (deprecation - after validation period)

---

## Testing Strategy

### Unit Testing
- **Introspection:** Parse 10+ real templates → verify schema accuracy
- **Caching:** Cache hit/miss, invalidation triggers
- **Error Formatting:** Consistent message structure

### Integration Testing
- **E2E Scaffolding:** Full scaffold flow with intentional errors → verify error messages
- **Cross-Artifact:** All artifact types use introspection consistently
- **Performance:** Schema generation within SLA (< 100ms uncached, < 10ms cached)

### Validation Testing
- **Template Coverage:** All templates in .st3/templates/ produce valid schema
- **Error Quality:** Manual review of error messages (actionable for agents)
- **Backward Compatibility:** Existing workflows unaffected

---

## Success Criteria

### Functional Requirements
- ✅ Template schema extracted automatically from Jinja2 AST
- ✅ Required/optional detection works for if-blocks and default filters
- ✅ Error messages show template-derived schema + status indicators
- ✅ Schema caching achieves < 10ms cache-hit performance
- ✅ Query tool (optional) provides schema on demand

### Non-Functional Requirements
- ✅ Zero hardcoded field names in validation logic
- ✅ Template changes auto-update schema (no manual sync)
- ✅ No performance regression (caching mitigates parsing cost)
- ✅ Backward compatible with existing templates

### Quality Gates
- ✅ All existing tests pass (no regressions)
- ✅ New introspection tests: 100% coverage on core logic
- ✅ Performance tests: Schema generation within SLA
- ✅ Manual validation: Error messages clear and actionable

---

## Out of Scope

**Explicitly NOT in Phase 1:**
- Issue #121 (Content-aware editing with Python AST) → Separate sequential phase
- Type validation beyond presence (e.g., "name must be string") → Future enhancement
- Nested schema support (e.g., fields list validation) → Future enhancement
- Template-driven Python code structure validation (Field() syntax) → Issue #121 scope
- Automatic template generation from schema → Not a requirement

---

## Open Questions for Design Phase

1. **Introspection Algorithm:** Exact AST node traversal strategy for if-blocks and default filters?
2. **Cache Implementation:** In-memory dict vs LRU cache? Eviction strategy needed?
3. **Error Format Details:** Exact text formatting, indentation, color coding (if terminal)?
4. **Tool Interface:** get_artifact_schema return format - match MCP JSON Schema pattern?
5. **Deprecation Timeline:** Immediate removal of required_fields or phased with warnings?

**Note:** These questions transition to design phase - no code decisions in planning.

---

## Next Steps

1. **Transition to Design Phase:** Create detailed technical design for Phase 1.1
2. **Prototype Introspection:** Small spike to validate Jinja2 meta API usage
3. **Review Real Templates:** Analyze dto, worker, design templates for complexity patterns
4. **Stakeholder Review:** Confirm scope and priorities with team

---

## Related Documents

- [unified_research.md](unified_research.md) - Research foundation for this plan
- [phase0-metadata-planning.md](phase0-metadata-planning.md) - Completed Phase 0 (SCAFFOLD metadata)
- [../../reference/mcp/mcp_vision_reference.md](../../reference/mcp/mcp_vision_reference.md) - Overall MCP architecture

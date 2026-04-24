# Issue #52 Planning: Template-Driven Validation Implementation

**Status:** DRAFT  
**Phase:** Planning  
**Date:** 2025-12-31  
**Issue:** #52 - Template-driven validation architecture

---

## Purpose

Define the implementation approach for migrating from hardcoded validation rules to template-driven SSOT architecture. This planning document translates research findings into actionable implementation goals with clear acceptance criteria and sequencing.

**Not Covered Here:**
- Technical class designs (see design phase documentation)
- Detailed code implementations (TDD phase)
- Problem analysis (completed in research phase)

---

## Scope

**In Scope (Epic #49: Config Infrastructure):**
- Template metadata schema design (YAML frontmatter format)
- TemplateAnalyzer infrastructure (extract metadata from templates)
- LayeredTemplateValidator infrastructure (three-tier enforcement logic)
- Add metadata to **3 core templates** (dto, tool, base_document - NO redesign)
- Integrate with SafeEditTool and ValidatorRegistry
- Remove hardcoded RULES dict (30 lines)
- Template version field support
- Infrastructure documentation

**Out of Scope (Moved to Other Epics):**
- Worker template redesign (IWorkerLifecycle) → **Epic #72: Template Library**
- Document templates (research, planning, unit_test) → **Epic #72: Template Library**
- Template governance (quarterly review, Rule of Three) → **Epic #73: Template Governance**
- AST-based validation improvements (future enhancement)
- Epic #18 enforcement policy tooling (separate concern)

---

## Implementation Goals

### Goal 1: Base Document Template Metadata

**Objective:** Add validation metadata to base_document.md.jinja2 for format enforcement.

**Success Criteria:**
- ✅ Template includes TEMPLATE_METADATA frontmatter
- ✅ Metadata enforces frontmatter presence and required fields
- ✅ Metadata enforces separator structure (---)
- ✅ Template metadata specifies STRICT enforcement level
- ✅ Template includes version field (e.g., version: "1.0")

**What Changes:**
- Update: `mcp_server/templates/base/base_document.md.jinja2`
- Add TEMPLATE_METADATA with enforcement level, format rules, validation specs

**Dependencies:** None (existing file update)

---

### Goal 2: Core Component Template Metadata

**Objective:** Add validation metadata to dto and tool templates.

**Success Criteria:**
- ✅ dto.py.jinja2 has TEMPLATE_METADATA with strict + guidelines
- ✅ tool.py.jinja2 has TEMPLATE_METADATA with strict + guidelines
- ✅ Metadata specifies enforcement levels (ARCHITECTURAL)
- ✅ Metadata includes version field
- ✅ Strict rules define architectural contracts
- ✅ Guidelines define best practices (warnings only)

**What Changes:**
- Update: `mcp_server/templates/components/dto.py.jinja2`
  - Add TEMPLATE_METADATA frontmatter
  - Strict: Pydantic BaseModel, frozen=True, Field validators
  - Guidelines: Field ordering (causality → id → timestamp → data)

- Update: `mcp_server/templates/components/tool.py.jinja2`
  - Add TEMPLATE_METADATA frontmatter
  - Strict: BaseTool inheritance, name/description/input_schema properties
  - Guidelines: Docstring format, execute() error handling

**Dependencies:** None (existing file updates)

---

### Goal 3: Template Analyzer Infrastructure

**Objective:** Build infrastructure to extract and parse template metadata.

**Success Criteria:**
- ✅ Extracts TEMPLATE_METADATA from Jinja2 comment blocks
- ✅ Parses YAML metadata into structured dict
- ✅ Extracts Jinja2 variables using meta.find_undeclared_variables()
- ✅ Resolves template inheritance chain (extends tracking)
- ✅ Returns complete metadata with inheritance merged
- ✅ Handles missing metadata gracefully (empty dict)
- ✅ 100% test coverage

**What Changes:**
- Create: `mcp_server/validators/template_analyzer.py`
  - Function: `extract_template_metadata(template_path: Path) -> dict`
  - Function: `get_base_template(template_path: Path) -> Path | None`
  - Function: `get_inheritance_chain(template_path: Path) -> list[Path]`
  - Function: `merge_metadata(child: dict, parent: dict) -> dict`

**Dependencies:** None (new module)

---

### Goal 6: Layered Template Validator

**Objective:** Build three-tier validation enforcing format → architectural → guidelines.

**Success Criteria:**
- ✅ Validates base template format rules (STRICT - blocks on error)
- ✅ Validates specific template architectural rules (STRICT - blocks on error)
- ✅ Validates guidelines (LOOSE - warnings only, never blocks)
- ✅ Returns ValidationResult with appropriate severity
- ✅ Stops validation on first ERROR (fail-fast)
- ✅ Continues through all warnings (reports all guidelines)
- ✅ Includes agent hints in response for document templates
- ✅ 100% test coverage

**What Changes:**
- Update: `mcp_server/validators/template_validator.py`
  - Class: `LayeredTemplateValidator` (replaces current TemplateValidator)
  - Method: `validate(file_path, template) -> ValidationResult`
  - Method: `_validate_format(file_path, base_template) -> ValidationResult`
  - Method: `_validate_architectural(file_path, template) -> ValidationResult`
  - Method: `_validate_guidelines(file_path, template) -> ValidationResult`
  - Method: `_get_base_template(template) -> Template`
  - Remove: `RULES` dict (30 lines deleted)

**Dependencies:** Goal 3 (TemplateAnalyzer must exist)

---

### Goal 5: SafeEditTool Integration

**Objective:** Integrate template-driven validation into SafeEditTool workflow.

**Success Criteria:**
- ✅ SafeEditTool uses LayeredTemplateValidator
- ✅ SafeEditTool loads templates from template directory
- ✅ SafeEditTool passes agent hints to tool response
- ✅ SafeEditTool blocks saves on ERROR severity
- ✅ SafeEditTool allows saves on WARNING severity (with notification)
- ✅ ValidatorRegistry loads template patterns from metadata
- ✅ All existing SafeEditTool tests pass

**What Changes:**
- Update: `mcp_server/tools/safe_edit_tool.py`
  - Update validator instantiation to use LayeredTemplateValidator
  - Load templates from mcp_server/templates/ directory
  - Pass validation metadata (hints, guidance) to ToolResult
  - Update error messages to include hints

- Update: `mcp_server/validators/validator_registry.py`
  - Load file patterns from template metadata (not hardcoded)
  - Register validators dynamically based on templates

**Dependencies:** Goal 4 (LayeredTemplateValidator must exist)

---

### Goal 6: Infrastructure Documentation

**Objective:** Document template metadata format for future template creation.

**Success Criteria:**
- ✅ Metadata format specification documented
- ✅ Enforcement levels explained (STRICT, ARCHITECTURAL, GUIDELINE)
- ✅ Three-tier model documented with examples
- ✅ Template versioning documented

**What Changes:**
- Create: `docs/reference/template_metadata_format.md`
  - Metadata structure specification
  - Enforcement level definitions
  - Validation rule examples
  - Version field usage

**Dependencies:** Goals 1-5 (implementation complete)

**Note:** Template governance documentation moved to Epic #73

---

## Testing Strategy

### Unit Tests (20 tests)

**TemplateAnalyzer Tests (8 tests):**
- `test_extract_metadata_with_frontmatter()` - Valid metadata extraction
- `test_extract_metadata_without_frontmatter()` - Returns empty dict
- `test_extract_metadata_invalid_yaml()` - Raises ValueError with hint
- `test_get_base_template_with_extends()` - Resolves base template path
- `test_get_base_template_without_extends()` - Returns None
- `test_get_inheritance_chain()` - Returns full chain (base → specific)
- `test_merge_metadata()` - Child overrides parent correctly
- `test_extract_jinja_variables()` - Extracts undeclared variables

**LayeredTemplateValidator Tests (12 tests):**
- `test_validate_format_pass()` - Base template format valid
- `test_validate_format_fail_imports()` - Wrong import order blocks
- `test_validate_format_fail_docstring()` - Missing docstring blocks
- `test_validate_architectural_pass()` - Architectural rules valid
- `test_validate_architectural_fail_base_class()` - Missing base class blocks
- `test_validate_architectural_fail_method()` - Missing required method blocks
- `test_validate_guidelines_pass()` - Guidelines followed
- `test_validate_guidelines_warnings()` - Guideline violations warn, don't block
- `test_validation_stops_on_format_error()` - Fail-fast on format error
- `test_validation_stops_on_architectural_error()` - Fail-fast on architectural error
- `test_validation_continues_through_guidelines()` - All warnings reported
- `test_agent_hints_included()` - Agent hints in response for documents

### Integration Tests (5 tests)

**SafeEditTool Integration (5 tests):**
- `test_safe_edit_blocks_on_format_error()` - Format error prevents save
- `test_safe_edit_blocks_on_architectural_error()` - Architectural error prevents save
- `test_safe_edit_allows_with_guideline_warnings()` - Warnings allow save
- `test_safe_edit_includes_agent_hints()` - Hints passed to response
- `test_validator_registry_loads_from_templates()` - Patterns loaded dynamically

### End-to-End Tests (3 tests)

**Scaffold → Validate Cycle (3 tests):**
- `test_scaffold_dto_passes_validation()` - Generated DTO validates
- `test_scaffold_tool_passes_validation()` - Generated tool validates
- `test_scaffold_document_passes_validation()` - Generated doc validates (base_document)

### Quality Gates

**All Tests:**
- [ ] 28 tests total (20 unit + 5 integration + 3 e2e)
- [ ] 100% coverage for template_analyzer.py
- [ ] 100% coverage for template_validator.py (new code)
- [ ] All existing tests pass (no regressions)

**Code Quality:**
- [ ] Pylint 10/10 for all new/modified files
- [ ] Mypy strict mode passing
- [ ] No TODO/FIXME comments in committed code

**Documentation:**
- [ ] All public functions have docstrings
- [ ] All metadata fields documented
- [ ] Examples provided for each enforcement level

---

## Rollout Plan

### Phase 1: Infrastructure Setup (Day 1)

**Add new infrastructure without breaking existing:**
1. Add metadata to base_document.md.jinja2
2. Add metadata to dto.py.jinja2
3. Add metadata to tool.py.jinja2
4. Create template_analyzer.py module
5. Write tests for TemplateAnalyzer

**Verification:**
- ✅ All existing tests still pass
- ✅ No breaking changes to existing code
- ✅ Templates can still be rendered

### Phase 2: Validator Implementation (Day 2)

**Build LayeredTemplateValidator:**
1. Implement LayeredTemplateValidator class
2. Implement three-tier validation methods
3. Write tests for LayeredTemplateValidator
4. **No parallel validation** - direct replacement of RULES dict

**Verification:**
- ✅ New validator passes all tests
- ✅ RULES dict removed (no compatibility check needed)
- ✅ Tests updated for new validation behavior

### Phase 3: Integration (Day 3)

**Integrate with SafeEditTool:**
1. Update SafeEditTool to use LayeredTemplateValidator
2. Update ValidatorRegistry to load from templates
3. Remove RULES dict
4. Update all affected tests

**Verification:**
- ✅ SafeEditTool tests pass
- ✅ ValidatorRegistry tests pass
- ✅ No references to RULES dict remain
- ✅ Integration tests pass

### Phase 4: Documentation (Day 4)

**Document infrastructure:**
1. Create template_metadata_format.md
2. Run final quality gates

**Verification:**
- ✅ Infrastructure documentation complete
- ✅ All tests passing
- ✅ Pylint 10/10
- ✅ Issue ready for review

**Note:** Template governance documentation moved to Epic #73

---

## File Changes Summary

### New Files (2)
1. `mcp_server/validators/template_analyzer.py` - Metadata extraction infrastructure
2. `docs/reference/template_metadata_format.md` - Metadata specification

### Modified Files (5)
1. `mcp_server/templates/base/base_document.md.jinja2` - Add metadata
2. `mcp_server/templates/components/dto.py.jinja2` - Add metadata
3. `mcp_server/templates/components/tool.py.jinja2` - Add metadata
4. `mcp_server/validators/template_validator.py` - LayeredTemplateValidator, remove RULES dict
5. `mcp_server/tools/safe_edit_tool.py` - Use new validator

### Test Files (3)
1. `tests/unit/mcp_server/validators/test_template_analyzer.py` - New tests (8 tests)
2. `tests/unit/mcp_server/validators/test_template_validator.py` - Update tests (12 tests)
3. `tests/integration/test_template_validation.py` - New integration tests (5 tests)

**Total Impact:**
- 2 new files
- 5 modified files
- 3 test files
- ~30 lines deleted (RULES dict)
- ~800 lines added (templates, analyzer, validator, tests)

---

## Success Metrics

### Completion Criteria
- [ ] All 8 implementation goals complete
- [ ] All 28 tests passing (100% pass rate)
- [ ] 100% coverage for new modules
- [ ] Pylint 10/10 (no exceptions)
- [ ] No RULES dict references remain
- [ ] Documentation complete and reviewed

### Quality Metrics
- [ ] Generated code from templates passes validation
- [ ] SafeEditTool blocks on ERROR, allows on WARNING
- [ ] Agent hints appear in validation responses
- [ ] Template inheritance chains resolve correctly
- [ ] No regressions in existing functionality

### Governance Setup
- [ ] Template growth limits documented
- [ ] Quarterly review process defined
- [ ] Escape hatch mechanism documented
- [ ] Template versioning strategy defined

---

## Risk Mitigation

### Risk 1: Template Metadata Parsing Errors
**Mitigation:**
- Comprehensive error handling in TemplateAnalyzer
- Clear error messages with hints for fixing YAML
- Test invalid YAML, missing metadata, malformed frontmatter
- Fallback to empty dict if parsing fails

### Risk 2: Breaking Existing Scaffolding
**Mitigation:**
- Test all templates after adding metadata
- Verify scaffold_component still works
- Run full test suite before/after changes
- Keep parallel validation temporarily (RULES + templates)

### Risk 3: Performance Impact
**Mitigation:**
- Cache template metadata after first load
- Only parse templates once per validator instance
- Profile validation performance (should be <100ms)
- Optimize if performance degrades

### Risk 4: Breaking Changes
**Mitigation:**
- **No backward compatibility** - clean break approach
- Worker template immediately uses IWorkerLifecycle (v2.0 only)
- Existing generated workers will fail validation (expected)
- Clear error messages: "Worker must implement IWorkerLifecycle - see migration guide"
- Migration guide documents: old pattern → new pattern transformation
- Breaking change is acceptable (platform still in development)

---

## Next Steps

**After Planning Approval:**
1. Transition to TDD phase
2. Start Phase 1: Create base_document.md.jinja2 (RED test first)
3. Follow TDD cycle: RED → GREEN → REFACTOR for each goal
4. Commit after each goal complete (atomic commits)
5. Run quality gates after each commit

**Design Phase (Parallel):**
- Create technical design document (separate phase)
- Specify class interfaces and contracts
- Design metadata schema structure
- Create Mermaid diagrams for validation flow

**TDD Phase Goals:**
- Goal 1 → 2 hours (template + tests)
- Goal 2 → 2 hours (template update + tests)
- Goal 3 → 2 hours (2 templates metadata)
- Goal 4 → 2 hours (2 doc templates)
- Goal 5 → 4 hours (analyzer + 8 tests)
- Goal 6 → 4 hours (validator + 12 tests)
- Goal 7 → 2 hours (integration + 5 tests)
- Goal 8 → 2 hours (documentation)
- Total: ~20 hours over 3 days (with buffer)

---

**Planning Complete.** Ready for design phase and TDD implementation.

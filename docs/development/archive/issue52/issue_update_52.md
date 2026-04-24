# Issue #52 Scope Update - Template-Driven Validation Infrastructure

## 🔄 Scope Shift: Config File → Template Metadata

After comprehensive research (see [docs/development/issue52/](docs/development/issue52/)), the implementation approach has evolved:

### ❌ Original Scope (DEPRECATED)
- ~~Create `config/validation.yaml` with validation rules~~
- ~~Pydantic model `ValidationConfig`~~
- ~~Config loader implementation~~

**Why deprecated:** This would create a **duplicate SSOT** (Single Source of Truth). Templates already define structure for scaffolding - adding separate config creates synchronization burden.

### ✅ Revised Scope (CURRENT)

**Core Principle:** Templates are the SSOT with embedded validation metadata in YAML frontmatter.

#### Epic #49 Deliverables (Infrastructure Only)

1. **TemplateAnalyzer Component**
   - Extracts validation metadata from Jinja2 template frontmatter
   - Resolves template inheritance chains
   - Merges metadata from base → specific templates

2. **LayeredTemplateValidator Component**
   - Three-tier enforcement model:
     - **Tier 1 (Format):** Base template rules → STRICT (ERROR blocks)
     - **Tier 2 (Architectural):** Specific template strict section → STRICT (ERROR blocks)
     - **Tier 3 (Guidelines):** Specific template guidelines section → LOOSE (WARNING only)
   - Fail-fast on ERROR, continues through WARNINGs

3. **Template Metadata Addition (6 Core Templates)**
   - Add metadata to existing templates - **NO REDESIGN**:
     - `components/dto.py.jinja2`
     - `components/tool.py.jinja2`
     - `base/base_document.md.jinja2`
   - Metadata includes: enforcement level, validation rules (strict + guidelines), version field

4. **Integration Updates**
   - SafeEditTool uses LayeredTemplateValidator
   - ValidatorRegistry auto-discovers validators from templates
   - Remove hardcoded RULES dict (30 lines)

5. **Infrastructure Documentation**
   - Template metadata format specification
   - Three-tier enforcement model documentation

#### Out of Scope (Moved to Other Epics)

- ❌ Worker template redesign (IWorkerLifecycle) → **Epic #72: Template Library**
- ❌ Document templates (research.md, planning.md, unit_test.py) → **Epic #72: Template Library**
- ❌ Template governance (quarterly review, Rule of Three) → **Epic #73: Template Governance**
- ❌ AST-based validation improvements → Future enhancement
- ❌ Epic #18 enforcement policy tooling → Depends on this foundation

---

## ✅ Updated Acceptance Criteria

### Infrastructure Components
- [ ] `TemplateAnalyzer` class created (`mcp_server/validators/template_analyzer.py`)
  - [ ] `extract_metadata(template_path)` - Parse YAML frontmatter from Jinja2 comments
  - [ ] `get_base_template(template)` - Resolve template inheritance
  - [ ] `get_inheritance_chain(template)` - Get full inheritance chain
  - [ ] `merge_metadata(child, parent)` - Merge parent + child metadata

- [ ] `LayeredTemplateValidator` class created (`mcp_server/validators/template_validator.py`)
  - [ ] Three-tier validation: `_validate_format()`, `_validate_architectural()`, `_validate_guidelines()`
  - [ ] Fail-fast on ERROR (stops at first error)
  - [ ] Continues through WARNINGs (collects all guidelines)
  - [ ] Includes agent hints in ValidationResult

### Template Updates (Metadata Only)
- [ ] `components/dto.py.jinja2` - Add TEMPLATE_METADATA frontmatter
  - [ ] Strict: Pydantic BaseModel, frozen=True, Field validators
  - [ ] Guidelines: Field ordering (causality → id → timestamp → data)

- [ ] `components/tool.py.jinja2` - Add TEMPLATE_METADATA frontmatter
  - [ ] Strict: BaseTool inheritance, name/description/input_schema properties
  - [ ] Guidelines: Docstring format, execute() error handling

- [ ] `base/base_document.md.jinja2` - Add TEMPLATE_METADATA frontmatter
  - [ ] Strict: Frontmatter presence/structure, separator format
  - [ ] Version field included

### Integration
- [ ] SafeEditTool updated to use LayeredTemplateValidator
- [ ] SafeEditTool blocks on ERROR, allows on WARNING
- [ ] SafeEditTool includes agent hints in response
- [ ] ValidatorRegistry auto-discovers validators from templates
- [ ] ValidatorRegistry loads file patterns from template metadata

### Cleanup
- [ ] RULES dict removed from `template_validator.py` (30 lines deleted)
- [ ] No hardcoded validation rules remain in code
- [ ] All validation rules sourced from template metadata

### Testing (39 tests)
- [ ] TemplateAnalyzer unit tests (10 tests)
  - [ ] Extract metadata with/without frontmatter
  - [ ] Resolve base templates and inheritance chains
  - [ ] Merge metadata correctly
- [ ] LayeredTemplateValidator unit tests (15 tests)
  - [ ] Three-tier enforcement works correctly
  - [ ] Fail-fast on ERROR
  - [ ] WARNINGs don't block
  - [ ] Agent hints included
- [ ] Integration tests (8 tests)
  - [ ] SafeEditTool validation workflow
  - [ ] ValidatorRegistry auto-discovery
- [ ] Acceptance tests (6 tests)
  - [ ] Generated code passes validation

### Documentation
- [ ] `docs/reference/template_metadata_format.md` created
  - [ ] Metadata schema specification
  - [ ] Enforcement level definitions
  - [ ] Validation rule examples
  - [ ] Template versioning guidelines

### Quality Gates
- [ ] All 39 tests passing
- [ ] 100% coverage for `template_analyzer.py`
- [ ] 100% coverage for new `LayeredTemplateValidator` code
- [ ] Pylint 10/10 for all new/modified files
- [ ] Mypy strict mode passing
- [ ] No TODO/FIXME in committed code

---

## 📊 Implementation Summary

**File Changes:**
- **New:** 2 files
  - `mcp_server/validators/template_analyzer.py` (~300 lines)
  - `docs/reference/template_metadata_format.md` (~150 lines)
- **Modified:** 5 files
  - 3 templates (add metadata frontmatter)
  - `mcp_server/validators/template_validator.py` (LayeredTemplateValidator)
  - `mcp_server/tools/safe_edit_tool.py` (integration)
- **Deleted:** RULES dict (30 lines)

**Test Files:**
- `tests/unit/mcp_server/validators/test_template_analyzer.py` (10 tests)
- `tests/unit/mcp_server/validators/test_template_validator.py` (15 tests)
- `tests/integration/test_template_validation.py` (8 tests)
- Acceptance tests (6 tests)

**Effort:** ~20 hours over 4 phases

**Impact:** Foundation for template-driven development, enables Epic #72 (Template Library) and Epic #73 (Template Governance)

---

## 🔗 Related Documentation

- **Research:** [docs/development/issue52/research.md](docs/development/issue52/research.md) - Problem analysis, three-tier model discovery
- **Planning:** [docs/development/issue52/planning.md](docs/development/issue52/planning.md) - Implementation goals, rollout strategy
- **Design:** [docs/development/issue52/design.md](docs/development/issue52/design.md) - Technical specification, class interfaces

---

## 🎯 Success Metrics

- ✅ Templates are single source of truth for scaffolding AND validation
- ✅ No duplicate maintenance (template change → validation follows automatically)
- ✅ Three-tier enforcement balances strictness with flexibility
- ✅ Adding new template requires only template file (no code changes)
- ✅ Foundation ready for Epic #72 (Template Library expansion)

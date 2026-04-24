# TDD Planning: Template Library Implementation

**Status:** Planning | **Phase:** Pre-TDD | **Issue:** #72

---

## Purpose

Plan TDD cycles voor refactoring van artifacts.yaml en implementatie van de 5-tier template hierarchy. Dit document definieert de volgorde van RED-GREEN-REFACTOR cycli om systematisch de template infrastructure te bouwen.

## Scope

**In Scope:**
- artifacts.yaml refactoring (type field toevoegen)
- tier0_base_artifact.jinja2 (universal SCAFFOLD)
- tier1_base_document.jinja2 (universal document structure)
- tier2_base_markdown.jinja2 (Markdown syntax)
- Update concrete/design.md.jinja2 (full DESIGN_TEMPLATE)
- Validation integration (STRICT enforcement tiers)

**Out of Scope:**
- Nieuwe artifact types (tracking templates = future work)
- MCP tool wijzigingen (scaffold_artifact is al unified)
- Andere document templates (alleen design als MVP)

## Prerequisites

- ✅ Issue #72 design complete
- ✅ Tier allocation gedocumenteerd
- ✅ SCAFFOLD format gestandaardiseerd (2-line format)
- ✅ File header standards gedocumenteerd
- ✅ Tracking type architecture besloten

## TDD Cycles Overview

### Cycle 1: artifacts.yaml Refactoring
**Doel:** Add `type` field to artifacts.yaml for type-based tier routing

**RED:**
- Test: `test_artifacts_yaml_has_type_field()`
  - Assert all artifacts have `type: code|doc|config`
  - Assert design artifact has `type: doc`
  - Assert dto/worker have `type: code`

**GREEN:**
- Update `.st3/artifacts.yaml`:
  - Add `type: doc` to design artifact
  - Add `type: code` to dto/worker/adapter/tool/resource artifacts
  - Add comments explaining type hierarchy

**REFACTOR:**
- Run quality gates (yaml syntax)
- Validate against JSON schema (if exists)

**Commit:** `git_add_or_commit(phase="refactor", message="add type field to artifacts.yaml")`

---

### Cycle 2: tier0_base_artifact.jinja2 (Universal SCAFFOLD)
**Doel:** Implement 2-line SCAFFOLD format for all artifact types

**RED:**
- Test: `test_tier0_scaffold_format()`
  - Scaffold test artifact
  - Assert line 1 = `# {filepath}` only
  - Assert line 2 = `# template={type} version={hash} created={iso8601} updated=`
  - Assert no "SCAFFOLD:" prefix

**GREEN:**
- Create `mcp_server/scaffolding/templates/tier0_base_artifact.jinja2`:
  ```jinja
  # {{ output_path }}
  # template={{ artifact_type }} version={{ version_hash }} created={{ timestamp }} updated=
  {%- block content %}{% endblock %}
  ```
- Update template_registry.yaml (tier0 entry)

**REFACTOR:**
- Test with multiple artifact types (dto, worker, design)
- Ensure language-aware comment syntax (# for Python, <!-- --> for Markdown)

**Commit:** `git_add_or_commit(phase="green", message="implement tier0 base artifact template")`

---

### Cycle 3: tier1_base_document.jinja2 (Universal Document Structure)
**Doel:** Implement STATUS/PURPOSE/SCOPE/VERSION HISTORY sections for all documents

**RED:**
- Test: `test_tier1_document_structure()`
  - Scaffold design document
  - Assert "**Status:**" field present
  - Assert "## Purpose" section present
  - Assert "## Scope" section with "**In Scope:**" / "**Out of Scope:**"
  - Assert "## Prerequisites" section present (optional)
  - Assert "## Related Documentation" section present
  - Assert "## Version History" table present

**GREEN:**
- Create `mcp_server/scaffolding/templates/tier1_base_document.jinja2`:
  ```jinja
  {%- extends "tier0_base_artifact.jinja2" -%}
  
  {%- block content %}
  # {{ title }}
  
  **Status:** {{ status | default("Draft") }} | **Phase:** {{ phase | default("Design") }}
  
  ---
  
  ## Purpose
  {{ purpose }}
  
  ## Scope
  
  **In Scope:**
  {{ scope_in }}
  
  **Out of Scope:**
  {{ scope_out }}
  
  {% if prerequisites -%}
  ## Prerequisites
  {{ prerequisites | join("\n- ") }}
  {%- endif %}
  
  {%- block document_content %}{% endblock %}
  
  ## Related Documentation
  {{ related_docs | default("None") }}
  
  ## Version History
  
  | Version | Date | Changes | Author |
  |---------|------|---------|--------|
  | 0.1 | {{ timestamp }} | Initial draft | Agent |
  {%- endblock %}
  ```
- Update template_registry.yaml

**REFACTOR:**
- Add TEMPLATE_METADATA (enforcement: STRICT, level: format)
- Test optional sections (prerequisites)
- Validate against Issue #52 format validation rules

**Commit:** `git_add_or_commit(phase="green", message="implement tier1 base document template")`

---

### Cycle 4: tier2_base_markdown.jinja2 (Markdown Syntax Layer)
**Doel:** Add Markdown-specific syntax (HTML comments, link definitions)

**RED:**
- Test: `test_tier2_markdown_syntax()`
  - Scaffold design document
  - Assert HTML comment present: `<!-- SCAFFOLD: ... -->`
  - Assert link definitions section present (before Version History)
  - Assert link format: `[id]: path/to/file.md "Title"`

**GREEN:**
- Create `mcp_server/scaffolding/templates/tier2_base_markdown.jinja2`:
  ```jinja
  {%- extends "tier1_base_document.jinja2" -%}
  
  {%- block content %}
  <!-- {{ output_path }} -->
  <!-- template={{ artifact_type }} version={{ version_hash }} created={{ timestamp }} -->
  
  {{ super() }}
  
  ---
  
  <!-- Link definitions -->
  {% if related_docs -%}
  {% for doc in related_docs %}
  [{{ doc | basename }}]: {{ doc }}
  {%- endfor %}
  {%- endif %}
  {%- endblock %}
  ```
- Update template_registry.yaml

**REFACTOR:**
- Add TEMPLATE_METADATA (enforcement: STRICT, level: format)
- Test with multiple link definitions
- Ensure link definitions invisible in Markdown preview

**Commit:** `git_add_or_commit(phase="green", message="implement tier2 markdown syntax template")`

---

### Cycle 5: concrete/design.md.jinja2 (Full DESIGN_TEMPLATE)
**Doel:** Update design template met complete structure (numbered sections, options, decisions)

**RED:**
- Test: `test_design_template_complete_structure()`
  - Scaffold design document
  - Assert "1. Context & Requirements" section present
  - Assert "2. Design Options" section with pros/cons subsections
  - Assert "3. Chosen Design" section with Decision/Rationale
  - Assert "Key Decisions" table present
  - Assert enforcement = GUIDELINE (not STRICT)

**GREEN:**
- Update `mcp_server/scaffolding/templates/concrete/design.md.jinja2`:
  ```jinja
  {%- extends "tier2_base_markdown.jinja2" -%}
  
  TEMPLATE_METADATA:
    enforcement: GUIDELINE
    level: content
  
  {%- block document_content %}
  
  ## 1. Context & Requirements
  
  ### Problem Statement
  {{ problem_statement }}
  
  ### Requirements
  {{ requirements }}
  
  ### Constraints
  {{ constraints | default("None") }}
  
  ## 2. Design Options
  
  {% for option in options %}
  ### Option {{ loop.index }}: {{ option.name }}
  
  {{ option.description }}
  
  **Pros:**
  {{ option.pros | join("\n- ") }}
  
  **Cons:**
  {{ option.cons | join("\n- ") }}
  {% endfor %}
  
  ## 3. Chosen Design
  
  ### Decision
  {{ decision }}
  
  ### Rationale
  {{ rationale }}
  
  ### Key Decisions
  
  | Decision | Rationale | Trade-offs |
  |----------|-----------|------------|
  {% for kd in key_decisions %}
  | {{ kd.decision }} | {{ kd.rationale }} | {{ kd.tradeoffs }} |
  {% endfor %}
  
  {% if open_questions -%}
  ## 4. Open Questions
  {{ open_questions | join("\n- ") }}
  {%- endif %}
  {%- endblock %}
  ```

**REFACTOR:**
- Test with real design context (Issue #72 design)
- Validate GUIDELINE enforcement (warnings only, no blocking)
- Ensure all BASE_TEMPLATE sections inherited

**Commit:** `git_add_or_commit(phase="refactor", message="complete design template with full structure")`

---

### Cycle 6: Validation Integration
**Doel:** Integreer template validation met Issue #52 enforcement model

**RED:**
- Test: `test_validation_enforcement_consistency()`
  - Assert tier0+tier1+tier2 templates have `enforcement: STRICT`
  - Assert design template has `enforcement: GUIDELINE`
  - Assert STRICT templates block save on missing sections
  - Assert GUIDELINE templates show warnings only

**GREEN:**
- Update validation logic in `mcp_server/validation/`:
  - Read TEMPLATE_METADATA from templates
  - Apply enforcement rules (STRICT = ERROR, GUIDELINE = WARNING)
  - Validate tier chain traceable

**REFACTOR:**
- Run quality gates on validation module
- Test with all artifact types
- Document validation flow in architecture docs

**Commit:** `git_add_or_commit(phase="refactor", message="integrate template validation with enforcement model")`

---

### Cycle 7: End-to-End Test
**Doel:** Validate complete template chain met real-world scenario

**RED:**
- Test: `test_scaffold_design_document_e2e()`
  - Scaffold design document with full context
  - Assert all tier0+tier1+tier2+concrete blocks present
  - Assert SCAFFOLD metadata correct (2-line format)
  - Assert link definitions generated
  - Assert Version History table generated
  - Run validate_doc() → should pass GUIDELINE level

**GREEN:**
- Fix any integration issues discovered during E2E test
- Update documentation if needed

**REFACTOR:**
- Test edge cases (missing optional fields)
- Test with multiple artifact types
- Performance test (large documents)

**Commit:** `git_add_or_commit(phase="refactor", message="validate e2e template scaffolding")`

---

## Dependencies Between Cycles

```
Cycle 1 (artifacts.yaml)
    ↓
Cycle 2 (tier0) ←─────────────┐
    ↓                          │
Cycle 3 (tier1)                │
    ↓                          │
Cycle 4 (tier2)                │
    ↓                          │
Cycle 5 (concrete design) ─────┤
    ↓                          │
Cycle 6 (validation) ──────────┤
    ↓                          │
Cycle 7 (E2E) ─────────────────┘
```

**Critical Path:** 1 → 2 → 3 → 4 → 5 → 7  
**Parallel Possible:** Cycle 6 kan parallel met Cycle 5 (validation is orthogonal)

## Test File Organization

```
tests/unit/scaffolding/
    test_artifacts_yaml.py           # Cycle 1
    test_tier0_base_artifact.py      # Cycle 2
    test_tier1_base_document.py      # Cycle 3
    test_tier2_base_markdown.py      # Cycle 4
    test_concrete_design.py          # Cycle 5

tests/unit/validation/
    test_template_enforcement.py     # Cycle 6

tests/integration/
    test_template_scaffolding_e2e.py # Cycle 7
```

## Acceptance Criteria

**Per Cycle:**
- [ ] RED test written and failing
- [ ] GREEN implementation passing test
- [ ] REFACTOR quality gates passing
- [ ] Commit with correct phase prefix

**Overall:**
- [ ] All 7 cycles completed
- [ ] E2E test passing
- [ ] Quality gates passing (ruff, mypy, pylint)
- [ ] Documentation updated (if needed)
- [ ] Ready for integration phase transition

## Risk Mitigation

**Risk 1: Template inheritance chain breaks**
- Mitigation: Test each tier independently before integration
- **BREAKING CHANGE:** Old templates replaced completely (no fallback)

**Risk 2: SCAFFOLD format breaks existing parsers**
- **BREAKING CHANGE:** 2-line format replaces old 1-line format completely
- Action: Update all existing scaffolded files to new format (separate cleanup task)
- Test: Verify new format parses correctly

**Risk 3: Validation too strict (blocks valid documents)**
- Mitigation: Start with GUIDELINE enforcement, tighten after data collection
- Test: Use real Issue #72 documents as test fixtures

## Notes for Implementation

1. **Jinja2 Syntax:** Watch for whitespace control (`{%-` vs `{%`)
2. **Context Variables:** Ensure all required variables documented in design.md
3. **Error Messages:** Provide clear errors for missing context variables
4. **Template Registry:** Update `.st3/template_registry.yaml` after each tier
5. **BREAKING CHANGES:** No backwards compatibility - clean slate approach
   - Old SCAFFOLD format (1-line) replaced by new format (2-line)
   - Existing scaffolded files need manual update (separate cleanup task)
   - Old templates fully replaced (no archive/fallback)

## Related Documentation

- [Issue #72 Design](docs/development/issue72/design.md)
- [Document Tier Allocation](docs/development/issue72/document-tier-allocation.md)
- [Tracking Type Architecture](docs/development/issue72/tracking-type-architecture.md)
- [DESIGN_TEMPLATE Reference](docs/reference/templates/DESIGN_TEMPLATE.md)

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-01-26 | Initial TDD planning | Agent |

# Phase 0: Scaffold Metadata Implementation - S1mpleTraderV3

<!--
GENERATED DOCUMENT
Template: generic.md.jinja2
Type: Generic
-->

<!-- ═══════════════════════════════════════════════════════════════════════════
     HEADER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

**Status:** Draft
**Version:** 0.1
**Last Updated:** 2026-01-20
**Issue:** #120
**Phase:** Planning
**Research:** [phase0-metadata-implementation.md](phase0-metadata-implementation.md)


---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTEXT SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Purpose

Translate research decisions into concrete, actionable implementation tasks for Phase 0: Scaffold Metadata Implementation. Define task breakdown, time estimates, dependencies, and acceptance criteria.

## Scope

**In Scope:**
- Task breakdown for 4 sub-phases (0.1-0.4)
- Time estimates per task
- Dependency mapping
- Acceptance criteria per sub-phase
- Risk assessment

**Out of Scope:**
- Template file updates (separate task)
- File migration strategy (future phase)
- Discovery tool implementation (Issue #121)

## Prerequisites

- ✅ Research document approved and committed
- ✅ Design decisions finalized (timestamps, optional path, TDD approach)
- ✅ Branch in planning phase
- Python environment configured
- Understanding of TDD workflow (RED → GREEN → REFACTOR)

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTENT SECTION
     ═══════════════════════════════════════════════════════════════════════════ -->

## Overview

Phase 0 implements a config-driven metadata system for scaffolded artifacts. We break this into 4 sub-phases following strict TDD (tests first), with E2E validation at the end.

**Approach:** Sequential implementation with quality gates between sub-phases.

---

## Implementation Plan

### Phase 0.0: artifacts.yaml Schema Update ⏱️ 30 minutes

**Objective:** Add required metadata fields to artifacts.yaml for Phase 0.1-0.4

**Blocker Resolution:** Current artifacts.yaml lacks `version` and `output_type` per artifact, which Phase 0.3 needs.

**Tasks:**
1. **Add fields to each artifact** - 15 min
   - Add `version: "1.0"` to each artifact (template version)
   - Add `output_type: "file"` to all code/document artifacts
   - Add `output_type: "ephemeral"` to git commit artifacts (if any)
   
2. **Update ArtifactDefinition model** - 10 min
   - Verify `mcp_server/config/artifact_registry_config.py` supports these fields
   - Add fields to Pydantic model if missing
   - Update type hints
   
3. **Validate** - 5 min
   - Test artifacts.yaml loads without errors
   - Verify `artifact_def.version` and `artifact_def.output_type` accessible

**Dependencies:** Phase 0.0 complete (prerequisite for all other phases)

**Acceptance Criteria:**
- ✅ All artifacts have `version` field
- ✅ All artifacts have `output_type` field (`"file"` or `"ephemeral"`)
- ✅ artifacts.yaml loads successfully
- ✅ ArtifactDefinition model includes version and output_type fields

**Risks:**
- ⚠️ Breaking existing code → Mitigate: Make fields optional in Pydantic model initially

---

### Phase 0.1: Config Infrastructure ⏱️ 2-3 hours

**Objective:** Create config file + Pydantic models with validation

**Tasks:**
1. **Write tests FIRST (RED)** - 30 min
   - `tests/unit/config/test_scaffold_metadata_config.py`
   - Test: Load config from YAML
   - Test: Validate field formats (regex patterns)
   - Test: Invalid config rejection
   
2. **Create config file** - 30 min
   - `.st3/scaffold_metadata.yaml`
   - 4 comment patterns (hash, double-slash, html-comment, jinja-comment)
   - 5 metadata fields (template, version, created, updated, path)
   - Format regex for each field
   
3. **Implement Pydantic models (GREEN)** - 45 min
   - `mcp_server/config/scaffold_metadata_config.py`
   - `CommentPattern` model
   - `MetadataField` model with `.validate()` method
   - `ScaffoldMetadataConfig` model with `.from_file()` classmethod
   
4. **Refactor** - 30 min
   - Extract validation helpers
   - Optimize YAML loading
   - Add error messages

**Dependencies:** Phase 0.0 complete

**Acceptance Criteria:**
- ✅ Config loads without errors
- ✅ All tests pass (GREEN)
- ✅ Field validation works for all 5 fields
- ✅ Invalid configs raise ValidationError

**Risks:**
- ⚠️ YAML syntax errors → Mitigate: Use IDE validation

---

### Phase 0.2: Metadata Parser ⏱️ 3-4 hours

**Objective:** Parse metadata from first line of scaffolded files

**Tasks:**
1. **Write tests FIRST (RED)** - 45 min
   - `tests/unit/scaffolding/test_metadata_parser.py`
   - Test: Parse Python metadata (hash comment)
   - Test: Parse Markdown metadata (HTML comment)
   - Test: Parse TypeScript metadata (double-slash)
   - Test: Parse Jinja2 metadata (jinja comment)
   - Test: Non-scaffolded file returns None
   - Test: Invalid timestamp format raises ValueError
   - Test: Ephemeral artifact (no path) is valid
   
2. **Implement parser (GREEN)** - 90 min
   - `mcp_server/scaffolding/metadata.py`
   - `ScaffoldMetadataParser` class
   - `.parse()` method with pattern matching
   - `._parse_key_value_pairs()` with validation
   - `._filter_patterns()` by extension
   
3. **Refactor** - 45 min
   - Extract validation to separate method
   - Optimize pattern matching (exit early)
   - Add comprehensive error messages

**Dependencies:** Phase 0.1 complete

**Acceptance Criteria:**
- ✅ All 4 comment syntaxes parsed correctly
- ✅ Non-scaffolded files return None (graceful)
- ✅ Runtime validation rejects invalid formats
- ✅ Ephemeral artifacts work (no path field)
- ✅ All tests pass (GREEN)

**Risks:**
- ⚠️ Regex patterns too strict → Mitigate: Test with real templates

---

### Phase 0.3: ArtifactManager Integration ⏱️ 2-3 hours

**Objective:** Enrich context with metadata fields during scaffolding

**Tasks:**
1. **Write tests FIRST (RED)** - 30 min
   - `tests/unit/managers/test_artifact_manager_metadata.py`
   - Test: Context enrichment adds 5 fields
   - Test: Timestamp format is ISO 8601 UTC
   - Test: Ephemeral artifact has no output_path
   - Test: File artifact has output_path
   
2. **Implement context enrichment (GREEN)** - 60 min
   - Modify `mcp_server/managers/artifact_manager.py`
   - Update `scaffold_artifact()` method
   - Add timestamp generation (UTC)
   - Conditional path field (based on artifacts.yaml output_type)
   - **Data source:** Read `artifact_def.version` and `artifact_def.output_type` from artifacts.yaml
   - **No duplication:** Templates receive enriched context, don't define metadata
   
3. **Refactor** - 45 min
   - Extract enrichment to `._enrich_context()` method
   - Add type hints
   - Document context variables

**Dependencies:** Phase 0.2 complete

**Acceptance Criteria:**
- ✅ Context includes: template_id, template_version, scaffold_created
- ✅ output_path only for file artifacts
- ✅ Timestamps are ISO 8601 UTC format
- ✅ All tests pass (GREEN)

**Risks:**
- ⚠️ artifacts.yaml doesn't have output_type → Mitigate: Add field or default to "file"

---

### Phase 0.4: End-to-End Tests ⏱️ 2-3 hours

**Objective:** Validate full scaffold → parse → validate flow

**Tasks:**
1. **Write E2E tests (RED)** - 60 min
   - `tests/integration/test_metadata_e2e.py`
   - Test: Scaffold DTO → read → parse → validate metadata
   - Test: Scaffold git commit (ephemeral) → parse → no path
   - Test: Invalid metadata format fails gracefully
   - Test: Manual file (no metadata) returns None
   
2. **Fix integration issues (GREEN)** - 45 min
   - Run E2E tests
   - Fix discovered bugs
   - Adjust parsers/validators
   
3. **Refactor + Coverage** - 45 min
   - Verify 100% coverage for new code
   - Add missing edge case tests
   - Clean up test helpers

**Dependencies:** Phase 0.3 complete

**Acceptance Criteria:**
- ✅ E2E test: scaffold DTO has metadata
- ✅ E2E test: scaffold git commit has no path
- ✅ 100% test coverage for new code
- ✅ All tests pass (unit + integration)

**Risks:**
- ⚠️ Template updates needed → Mitigate: Out of scope, separate task

---

## Time Estimate

| Sub-Phase | Estimate | Cumulative |
|-----------|----------|------------|
| 0.0: artifacts.yaml Update | 30min | 30min |
| 0.1: Config Infrastructure | 2-3h | 2.5-3.5h |
| 0.2: Metadata Parser | 3-4h | 5.5-7.5h |
| 0.3: ArtifactManager Integration | 2-3h | 7.5-10.5h |
| 0.4: End-to-End Tests | 2-3h | 9.5-13.5h |

**Total: 9.5-13.5 hours** (~2 work days)

---

## Dependencies

```
Phase 0.0 (artifacts.yaml Update)
    ↓
Phase 0.1 (Config)
    ↓
Phase 0.2 (Parser)
    ↓
Phase 0.3 (Integration)
    ↓
Phase 0.4 (E2E Tests)
```

**Dependencies:**
- artifacts.yaml must have `output_type` field (or default to "file")
- Templates must use new context vars: `{{ scaffold_created }}`, `{{ output_path }}`
- Python environment with pytest installed

**SSOT Architecture:**

| Aspect | Owner | Role | Reason |
|--------|-------|------|--------|
| Template version | artifacts.yaml | Defines `version: "2.0"` | SSOT for compatibility tracking |
| Output type | artifacts.yaml | Defines `output_type: "file"` | SSOT for path logic |
| Template path | artifacts.yaml | Defines `template_path: "..."` | SSOT for discovery |
| Comment syntax | Template (.jinja2) | Injects own syntax | Templates know target language |
| Metadata injection | Template | Uses `{{ template_version }}` | Templates USE artifacts.yaml data |

**Data Flow:**
```
1. ArtifactManager reads artifacts.yaml
   ↓
2. Context enrichment (template_id, template_version, scaffold_created)
   ↓
3. Conditional path (if output_type == "file")
   ↓
4. Template renders using enriched context
   ↓
5. Metadata line: template=dto version=2.0 created=... path=...
```

**No Duplication:** Templates never define version/output_type, they only USE enriched context vars.

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| YAML syntax errors | Low | Medium | Use IDE validation, test early |
| Regex patterns too strict | Medium | High | Test with real templates, make patterns flexible |
| artifacts.yaml missing output_type | Medium | Medium | Add field or default to "file" |
| Template updates needed | High | Low | Out of scope, separate task after Phase 0 |
| Test coverage <100% | Low | Medium | Strict TDD, coverage checks in CI |

---

## Success Criteria

**Phase 0 is complete when:**
- ✅ All 4 sub-phases complete with passing tests
- ✅ 100% test coverage for new code
- ✅ E2E tests validate full flow
- ✅ Config loads and validates correctly
- ✅ Parser handles all 4 syntaxes + edge cases
- ✅ Context enrichment adds correct fields
- ✅ Documentation updated (docstrings, README)

**Ready for next phase (Design) when:**
- ✅ All acceptance criteria met
- ✅ Code review approved
- ✅ No blocking issues


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
| 0.1 | YYYY-MM-DD | GitHub Copilot | Initial creation |

<!-- docs\development\issue349\planning.md -->
<!-- template=planning version=130ac5ea created=2026-07-15T18:16Z updated= -->
# Implementation Plan: Dynamic YAML Schema Validation

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-07-15

---

## Purpose

Define safe sequential slices (TDD cycles) to replace legacy context classes and absorb Issue #326 scope (V1 pipeline removal).

## Scope

**In Scope:**
mcp_server/config/schemas/artifact_registry_config.py, mcp_server/managers/artifact_manager.py, artifacts.yaml, scaffold_artifact tool, mcp_server/schemas/ (legacy contexts), test paths.

**Out of Scope:**
Versioning, remote schema fetching.

## Prerequisites

Read these first:
1. Approved strategy and design from previous phases.
---

## Summary

Execute a Clean Break migration to replace internal Python-coupled template loading with a declarative YAML-driven `ArtifactManager` that builds frozen Pydantic validation models at runtime. Also eliminates V1/V2 dual pipelines.

---

## Dependencies

- Cycles must be executed in sequential order.

---

## TDD Cycles


### Cycle 1: C_CONFIG.1

**Goal:** Update ArtifactRegistryConfig and artifacts.yaml to use declarative SchemaFieldDef instead of context_class string.

**Tests:**
- tests/mcp_server/config/test_component_registry.py (Verified existing file)
- tests/mcp_server/unit/config/test_artifact_registry_config.py
**Success Criteria:**
- ArtifactRegistryConfig parses schema definition correctly
- tests/mcp_server/config/test_component_registry.py passes



### Cycle 2: C_ENGINE.2

**Goal:** Refactor ArtifactManager to build frozen Pydantic models at runtime via pydantic.create_model (inheriting/injecting BaseRenderContext lifecycle fields) and use them for schema generation and validation. Remove the V1 dict-based fallback logic and the `PYDANTIC_SCAFFOLDING_ENABLED` feature flag (Issue #326).

**Tests:**
- tests/mcp_server/unit/managers/test_artifact_manager.py

**Success Criteria:**
- get_schema() outputs valid JSON Schema
- scaffold_artifact properly fails fast on invalid input using the dynamic model
- All typing/mypy obligations from TYPE_CHECKING_PLAYBOOK.md are respected when instantiating dynamic types.
- Feature flag and V1 fallback logic are completely deleted.



### Cycle 3: C_CLEANUP.3

**Goal:** Delete legacy python contexts, test fixtures, and 17 parity tests from Issue #326. Explicitly migrate all artifacts.yaml entries.

**Tests:**
- tests/mcp_server/acceptance/test_issue56_acceptance.py
- tests/mcp_server/unit/tools/test_scaffold_artifact.py

**Success Criteria:**
- No Python module lookups remain in ArtifactManager
- Test helpers are DRY and resolve paths centrally (SSOT)
- ~23 legacy Context files (`schemas/contexts/`) and ~21 legacy RenderContext files (`schemas/render_contexts/`) are fully deleted
- ~17 V1/V2 parity tests deleted or rewritten
- 21 entries in `artifacts.yaml` successfully migrated from `context_class` to `context_schema`



### Cycle 4: C_MODULAR_LOADER.4

**Goal:** Refactor `loader.py`'s `load_artifact_registry_config` method to scan and load modular configurations from the resolved config folder root (`artifacts/` subdirectory), merging them dynamically.

**Tests:**
- `tests/mcp_server/unit/config/test_modular_loader.py` (New test file)

**Success Criteria:**
- `loader.load_artifact_registry_config()` resolves directory-based configuration files and successfully merges them.
- Fails fast on invalid syntax or schema mismatches in sub-files.



### Cycle 5: C_MIGRATE_MODULAR.5

**Goal:** Migrate the monolithic `artifacts.yaml` by splitting it into modular `.yaml` files under the resolved config directory's `artifacts/` subdirectory. Add the new `typescript_dto` template and register it in the modular configuration folder.

**Tests:**
- `tests/mcp_server/acceptance/test_issue56_acceptance.py`
- Full test suite passes successfully.

**Success Criteria:**
- Monolithic `artifacts.yaml` cleaned up and split.
- `typescript_dto` fully registered and scaffolded successfully.
---

## Risks & Mitigation

- **Risk:** Dynamic Pydantic models bypass strict Mypy checks and trigger linter warnings.
  - **Mitigation:** Use targeted casting or `assert` narrowing where required, strictly documenting deviations per TYPE_CHECKING_PLAYBOOK.md. Explicit Quality Gate Expectation: No global or file-level suppressions (e.g., `# ruff: noqa:`) are permitted for dynamic model logic. Strict 10.00/10 pylint adherence must be maintained.
- **Risk:** Regression tests may fail purely because they explicitly assert legacy Python schemas.
  - **Mitigation:** Delete test baggage that proves a negative. Refactor to test observable tool behavior instead of internal mock signatures.

---

## Milestones

- Configuration logic adapted
- ArtifactManager Engine running on pure YAML (V3), V1 pipeline eliminated
- Massive legacy cleanup completed

## Documentation Deliverables

During the documentation phase, the following mandatory guides must be created:
1. **Scaffolding Architecture Guide**: A complete description of the new decoupled, tiered Jinja2 template and YAML-driven schema architecture.
2. **Developer & Agent Guide**: A tutorial for new developers and LLM agents on how to create and contribute new templates and artifacts.
3. **Migration Guide**: Step-by-step instructions on splitting the legacy monolithic `artifacts.yaml` configuration into the new modular folder-based `artifacts/` folder structure.
## Related Documentation
- **[docs/development/issue349/design.md][related-1]**
- **[docs/development/issue349/research.md][related-2]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-3]**

<!-- Link definitions -->

[related-1]: docs/development/issue349/design.md
[related-2]: docs/development/issue349/research.md
[related-3]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Version History

| 1.0 | 2026-07-15 | Agent | Initial draft |
| 1.1 | 2026-07-15 | Agent | Fix test paths, incorporate QA review (Issue 326 deletion blast radius) |
| 1.2 | 2026-07-15 | Agent | Added C_MODULAR_LOADER.4 and C_MIGRATE_MODULAR.5 cycles for folder-based config modularity |
| 1.3 | 2026-07-15 | Agent | Updated planning to reflect Option B Clean Break and documented extra documentation obligations |

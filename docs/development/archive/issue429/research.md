<!-- docs\development\issue429\research.md -->
<!-- template=research version=8b7bb3ab created=2026-07-17T07:43Z updated= -->
# Issue 429: Template Package Bundling

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-07-17

---

## Problem Statement

The configuration YAMLs for artifacts currently live in `.pgmcp/config/artifacts/` while their corresponding Jinja2 templates live in `.pgmcp/templates/`. This artificial separation breaks cohesion, as they form a tight 1-to-1 pair. Issue #429 aims to bundle them together into cohesive Template Packages, but this requires refactoring the `ConfigLoader` and handling backward compatibility.

## Research Goals

- Identify blast radius of migrating artifacts configs to templates/
- Resolve architectural tension in ConfigLoader scanning presentation paths
- Determine a migration policy for legacy workspaces
- Establish version-pairing logic between templates and yaml configs

---

## Findings

### Current State
- `ConfigLoader` loads `artifacts.yaml` as an index, then scans `config_root / "artifacts"` to merge modular configurations into `ArtifactRegistryConfig`.
- `ArtifactManager` uses this registry to resolve scaffolding requests, locating the Jinja2 templates via its own `_get_template_root()` logic.

### Resolving Architectural Tension
- **New Principle:** "Things that belong together, should live together." Co-locating the artifact config with its template resolves the fundamental cohesion violation.
- **Config Sub-directory:** By introducing a `config/` sub-directory within the templates root (e.g., `templates/config/`), we further soften the architectural tension. This provides a clean separation of configuration from presentation within the unified Template Package, explicitly choosing `config/` rather than `artifacts/` as the subfolder.

### Blast Radius & Path Resolution
- **Scattered Hard-Codings Verified:** A codebase search confirms that test code currently has scattered hard-codings of `config/artifacts.yaml` and `artifacts/` directories (e.g., in `test_smoke_all_types.py`, `artifact_test_harness.py`, `test_template_missing_e2e.py`). 
- **In Scope for Test Suite:**
  - Refactoring the `artifact_test_harness.py` helper to centrally intercept and resolve the new paths.
  - Fixing tests that *actively fail* (turn red) purely as a result of the YAML relocation.
- **Out of Scope (Explicit Exclusion):**
  - We will **not** proactively rewrite or refactor the entire test suite purely to clean up historical hard-coded paths. Sweeping cleanups are excluded to maintain scope discipline. Focus is strictly on tests that break.
- **Assets Folder Role:** The `assets/` directory acts strictly as a package container for the wheel distribution and its content is completely irrelevant during dev-time. To prevent confusion and eliminate unnecessary baggage, the assets directory should be emptied entirely when beginning this refactoring against the stable release.

### Architecture Preservation
- The internal representation and Pydantic validation of `ArtifactRegistryConfig` must remain unchanged.
- The `ConfigLoader` must receive `template_root` via its constructor (Dependency Injection) from `bootstrap.py` to preserve the Domain vs Presentation separation defined in `ARCHITECTURE_PRINCIPLES.md`.

### Seams
The refactor can be split into safely testable steps:
1. Update `ArtifactDefinition` to support strict version-pairing.
2. Unify path resolution for `template_root` across production and test suites, eliminating hard-coded paths.
3. Update `ConfigLoader` to scan the new `templates/config/` location and remove legacy loading.
4. Empty the dev-time `assets/` directory and migrate physical assets accordingly for the package container.

---

## Approved Strategy

### Template Package Migration Strategy
**Policy:** Clean Break (No backward compatibility for legacy `config/artifacts/`)
**Rationale:** The v2.0.0 release is already breaking compared to v1.0.0. Maintaining a dual-loader fallback for the old `config/artifacts/` directory adds technical debt and architectural contamination (mixing domain loaders with presentation fallbacks). Instead, we enforce a clean break where old workspaces must use the `pgmcp --upgrade` command to align their structures.

### Version-Pairing Strategy
**Policy:** Strict Centralized Semantic Versioning (SemVer)
**Rationale:** To prevent templates and their YAML configurations from drifting out of sync, `ArtifactDefinition` will receive a `template_version` field. The system will enforce alignment between the YAML configuration and the corresponding Jinja2 template.
**Centralization:** All version validation (both template-vs-yaml and wheel-vs-workspace) must occur centrally (e.g., via a `mcp_server/utils/versioning.py` utility) to adhere to DRY and SRP.
**SemVer Rules:**
- **MAJOR:** Mismatches crash the application (Breaking API/Schema changes).
- **MINOR:** Newer asset versions yield a Warning (forward-incompatible features missing in engine); older asset versions are silently accepted (backward compatible).
- **PATCH:** Silently accepted (safe bugfixes).

---

## Expected Results

1. `ArtifactRegistryConfig` successfully loads its modular configs directly from the `templates/config/` directory (e.g., `templates/concrete/config/` or `templates/config/`).
2. `ConfigLoader` remains architecturally clean by accepting `template_root` via dependency injection from the composition root, rather than hardcoding presentation paths.
3. Legacy loading from `config/artifacts/` is strictly removed.
4. `ArtifactDefinition` includes explicit version-pairing logic to ensure the Jinja2 template and its YAML schema are structurally aligned.
5. All test suites (e.g., `test_modular_loader.py`, `artifact_test_harness.py`, `test_concrete_templates.py`) are refactored to use the new `templates/config/` structure and enforce uniform centralized path resolution.

## Related Documentation
None
---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-17 | Agent | Initial draft |
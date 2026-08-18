<!-- docs\development\issue349\research.md -->
<!-- template=research version=8b7bb3ab created=2026-07-14T20:52Z updated= -->
# Template Workspace Initiative: workspace-owned templates, schema packs

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-07-15

---

## Problem Statement

The three-part scaffolding trinity (schemas, Jinja2 templates, artifacts.yaml) is currently bundled inside the wheel. Users have no supported path to adapt scaffolding to their projects or to reuse template schema packs across arbitrary projects without modifying the core server. Furthermore, requiring Python-based `context_class` schemas introduces security risks (arbitrary code execution), caching/reloading issues requiring server restarts, and friction for users wanting simple declarative templates.

**Broadened Scope (Issue #326):** The legacy V1 pipeline (dict-based fallbacks) and the `PYDANTIC_SCAFFOLDING_ENABLED` feature flag in `ArtifactManager` are dead weight. Because this initiative replaces Python-based V2 contexts with pure declarative YAML models (effectively "V3"), retaining the V1 fallback and feature flag would create unacceptable maintenance overhead. Issue #326 is formally absorbed into this initiative's Clean Break strategy.

## Research Goals

- **Decoupled Template Architecture**: Templates are no longer bundled. The server operates as an engine that resolves scaffolding from a single configured template root.
- **Folder-Contained Scaffolding**: The "scaffolding trinity" (Jinja2 templates, `artifacts.yaml` metadata, and schema logic) is fully resolved from the workspace configuration paths.
- **Single Source of Truth**: There is exactly one `artifacts.yaml` (no merging needed) and one template directory.
- **Pure Declarative Schemas**: Eliminate the need for Python-based `context` and `render_context` schemas for custom templates. Replace with dynamic models built entirely from YAML configuration.
- **V1/V2 Cleanup**: Completely remove the `PYDANTIC_SCAFFOLDING_ENABLED` feature flag and the legacy V1 dict-based fallback pipeline.

## Background

*   **Current State of Templating**: The Jinja2 templates are bundled in the MCP server wheel, loaded directly via `FileSystemLoader` pointing to a single bundled directory. Schema validation uses Python imports dynamically loaded from the internal `mcp_server.schemas` package. `artifacts.yaml` configuration is loaded strictly from the `server_root/config/artifacts.yaml` path.
*   **Schema Coupling**: The V2 pipeline hardcodes dynamic `import mcp_server.schemas.<context_class>` logic and uses naming conventions (`<ContextClass>RenderContext`) to validate and enrich context payloads.
*   **Validator Usage**: A comprehensive scan of all 24 existing `@field_validator` functions in the `pgmcp` codebase reveals they exclusively perform standard constraints (not-empty checks via `min_length`, list type checks, and regex formatting). No advanced cross-field business logic exists in template contexts.

## Findings

*   **Blast Radius**: Implementing these changes impacts `JinjaRenderer` and `TemplateEngine` initialization. `ArtifactManager` must completely drop the Python `sys.modules` lookup for `context_class` and `RenderContext`. `ArtifactRegistryConfig` must be updated to replace `required_fields`/`optional_fields` (or augment them) with JSON Schema-like constraints.
    *   **Massive Deletion Scope**: The cleanup explicitly encompasses ~23 Context classes (`schemas/contexts/`), ~21 RenderContext classes (`schemas/render_contexts/`), the `PYDANTIC_SCAFFOLDING_ENABLED` feature flag, and the V1 fallback code in `scaffold_artifact()`. 
    *   **Test Suite Impact**: Approximately 17 tests tied to the V1/V2 feature flag parity (from Issue #326) must be deleted or refactored.
*   **Architectural Constraints**:
    *   **SSOT (Single Source of Truth)**: The single `artifacts.yaml` at the configured `resolved_config_root` is the definitive SSOT. No fallback merging logic.
    *   **No Import-Time Side Effects**: Removing Python schema loading eliminates the security and reloading issues.
*   **Dynamic Validation**: By utilizing `pydantic.create_model` or `jsonschema.validate`, `ArtifactManager` can dynamically generate memory-based validation schemas directly from the `artifacts.yaml` definitions.
*   **Lifecycle Enrichment**: Generic base classes (`DocRenderContext`, `CodeRenderContext`) can handle all lifecycle metadata injection without needing a 1-to-1 concrete python `RenderContext` for every template.
*   **Modular Configuration**: A monolithic `artifacts.yaml` of 1400+ lines introduces maintenance bottlenecks and DRY violations. By implementing a modular folder-based loader (scanning `config/artifacts/*.yaml`), we can split definitions into separate, small files.
*   **Extensibility Case Study (TypeScript DTO)**: To prove the language-agnostic extensibility of the V3 tiered template pipeline, we will design and implement TypeScript support. This serves as a blueprint showing how a non-Python template fits into Tier 0, Tier 1, Tier 2 (language syntax), Tier 3 (domain patterns), and Tier 4 (concrete definitions).
---

## Approved Strategy

**Clean Break (Breaking)**

- **Internal Template Behavior Removed**: The current internally-bundled, Python-dependent template behavior is completely deprecated.
- **Single Root**: All template logic moves exclusively to the configured `template_root`. 
- **YAML-Driven Validation**: `artifacts.yaml` becomes the sole source of truth for validation. 
- **No Python Schemas**: `context` and `render_context` Python schemas for individual templates are completely eliminated. The server will dynamically build validation boundaries (via Pydantic `create_model` or JSON Schema) based on the YAML constraints (e.g., `min_length`, `pattern`, `type: array`).
- **Generic Render Context**: Lifecycle fields (e.g., `output_path`, `version_hash`) will be injected generically via base render contexts rather than template-specific classes.
- **Issue #326 Absorption**: The V1 dict-based fallback pipeline and the `PYDANTIC_SCAFFOLDING_ENABLED` feature flag are permanently removed.
- **Modular Configuration (Breaking)**: The config loader is permanently rewritten to load all files under the `artifacts/` folder of the resolved `config_root`. Monolithic `artifacts.yaml` support is removed (Clean Break). This change is breaking and requires monolithic files to be split. A formal developer and migration guide must be provided during the documentation phase to instruct developers on splitting files and implementing new templates.
---

## Expected Results

Users can define a new template entirely via a `.jinja2` file and a modular block in the resolved config folder. Scaffolding validation occurs dynamically without requiring server restarts, custom Python classes, or complex plugin registry management. True folder-contained simplicity is achieved, and the bloated legacy pipelines (V1/V2) are eliminated.

## Related Documentation
- Issue #326
- Issue #349 - Modular Configuration Initiative (Proposed in v1.3)

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-14 | Agent | Initial draft |
| 1.1 | 2026-07-15 | Agent | Updated with Approved Strategy: Clean Break, YAML-driven validation |
| 1.2 | 2026-07-15 | Agent | Broadened scope to absorb Issue #326 (Remove V1 pipeline and feature flag) |
| 1.3 | 2026-07-15 | Agent | Added Modular Configuration Initiative (split artifacts.yaml into artifacts/*.yaml) |
| 1.4 | 2026-07-15 | Agent | Updated Strategy: Clean Break (breaking monolithic config) and TypeScript Case Study scope |

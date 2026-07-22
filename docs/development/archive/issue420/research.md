<!-- docs\development\issue420\research.md -->
<!-- template=research version=8b7bb3ab created=2026-07-06T05:52Z updated=2026-07-07T09:38Z -->
# Research: Deferred Release Assets and Template Bootstrap

**Status:** APPROVED  
- **Version:** 1.6  
**Last Updated:** 2026-07-07

## Prerequisites

Read these first:
1. Issue #420
2. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
3. docs/coding_standards/DOCUMENTATION_STANDARD.md
4. docs/reference/mcp/release-assets-procedure.md
---

## Problem Statement

1. **Workspace templates initialization blocker:** Clean repository checkouts of the development repository contain the tracked `.pgmcp/config` folder but miss the untracked `.pgmcp/templates` directory. The current `pgmcp --init` command checks if `.pgmcp` exists and aborts immediately. This prevents developers from bootstrapping templates in the development workspace.
2. **CLI `--init` incomplete copy behavior:** The current implementation of `pgmcp --init` in `mcp_server/cli.py` is hardcoded to only copy the `config` and `templates` subdirectories from package assets via `shutil.copytree`. It does not perform a recursive flat copy of the entire `mcp_server/assets/` directory, causing other packaged assets (excluding `template_registry.json`) to be completely missed.
3. **Deferred packaging build automation:** The release packaging automation and manifest synchronization specified in `release-assets-procedure.md` (distributing files from the `docs/agents/` Single Source of Truth to `mcp_server/assets/` using a manifest file mapping) are deferred.
4. **Lack of Configuration Version Verification:** The server lacks a fail-fast mechanism to detect when a target workspace's local configurations (`.pgmcp/config/`) are incompatible with the running server. Upgrades currently rely on cryptic Pydantic validation errors instead of a clean break with a human-readable error message.

## Research Goals

- Support clean workspace initialization in target environments without changing product runtime CLI checks.
- Update `pgmcp --init` to perform a flat recursive copy of the entire `mcp_server/assets/` directory (excluding `template_registry.json`) instead of only copying hardcoded subdirectories.
- Eliminate templates directory triplication by removing `mcp_server/scaffolding/templates` and updating the test suite to use resolved settings.
- Research a simplified config-only versioning strategy to fail fast with clear error messages on incompatibility, avoiding complex upgrade or compatibility matrices.
- Research path resolution in the test suite to establish a DRY template path resolution strategy using environment variables.
- Implement automated build-time copy/sync of release-bound assets to `mcp_server/assets/` on release builds using `.pgmcp/config/release_manifest.yaml` and a pre-build script.
- Establish a secure development isolation setup where the active running server instance operates from a packaged wheel in a stable virtual environment, fully separated from the active development codebase.

---

## Detailed Findings & Analysis

### 1. The Configuration Versioning Scope
* **Templates:** Frozen. Out of scope for versioning. Templates will eventually be decoupled from the server entirely under the Template Workspace Initiative (#349). No template version checks or upgrades are required.
* **Template Registry (`template_registry.json`):** Classified as a log file (provenance logging), not an active production enforcement component. It does not block startup or enforce active versioning.
* **Configurations (`.pgmcp/config/`):** The only asset subject to version verification.
* **Standardized Version:** All configuration files (including `git.yaml`, `contracts.yaml`, `policies.yaml`, `project_structure.yaml`, and `enforcement.yaml`) must standardize on version `"1.0.0"`.
* **Clean-Break Validation:** To keep the codebase clean, we avoid complex migrations. The `ConfigLoader` will validate this version field at startup. If a configuration schema or version mismatch is found, it will fail fast and raise a friendly `ConfigError` with the file path.

### 2. Template Path Resolution in the Test Suite
* **Current Fragmentation:** 7 test suites reference the duplicate path `"mcp_server/scaffolding/templates"` directly. If this folder is deleted, they will fail:
  1. `tests/mcp_server/integration/test_document_templates.py`
  2. `tests/mcp_server/integration/test_smoke_all_types.py`
  3. `tests/mcp_server/scaffolding/test_tier3_pattern_python_pytest.py`
  4. `tests/mcp_server/test_design_e2e.py`
  5. `tests/mcp_server/test_design_template.py`
  6. `tests/mcp_server/test_validation_enforcement.py`
  7. `tests/mcp_server/unit/services/test_template_engine.py`
* **Single Point of Fallback:** Production code resolves templates using `Settings.from_env().server.resolved_template_root` (which looks at the `MCP_TEMPLATE_ROOT` environment variable and falls back to `.pgmcp/templates`).
* **Richting 1 (Dynamic Environment Override):** To keep the test suite DRY and avoid file-copying overhead:
  1. `tests/conftest.py` will resolve the project root and dynamically set `os.environ["MCP_TEMPLATE_ROOT"]` to `project_root / Settings().server.server_root_dir / "templates"`.
  2. `get_template_root()` in `tests/mcp_server/test_support.py` will be refactored to dynamically return `Settings.from_env().server.resolved_template_root`.
  3. The 7 fragmented test files will be refactored to call `get_template_root()`.
  4. This eliminates hardcoded paths and uses a single point of fallback.

---

## Approved Strategy

### Boundary: Default Configuration Root & Workspace Initialization (`pgmcp --init`) & Dev Setup
- **Policy:** Keep the production CLI's `pgmcp --init` implementation clean and strict: it must abort if the `.pgmcp/` directory already exists (idempotency guard). Do not add dev-specific runtime bypasses in the CLI code.
- **Policy:** To resolve the chicken-and-egg problem in the development workspace, fully track `.pgmcp/templates/` under version control in Git. This ensures a clean clone of the development repository immediately contains all templates.
- **Policy:** Update `pgmcp --init` in `mcp_server/cli.py` to copy the entire contents of the packaged `assets/` folder recursively (using `shutil.copytree(assets_dir, resolved_server_root, dirs_exist_ok=True)`) rather than hardcoding individual subfolders. This ensures assets (excluding `template_registry.json`) are correctly bootstrapped.

### Boundary: Templates Source of Truth
- **Policy:** Remove the duplicate `mcp_server/scaffolding/templates` directory.
- **Policy:** The test suite must resolve templates dynamically through `get_template_root()` pointing to the settings-resolved root. `tests/conftest.py` will set `os.environ["MCP_TEMPLATE_ROOT"]` dynamically based on `Settings().server.server_root_dir`, ensuring a single point of fallback and avoiding copying templates.

### Boundary: Configuration Versioning & Upgrades
- **Policy:** Limit version checking strictly to configuration files in `.pgmcp/config/`.
- **Policy:** Implement a "clean break" upgrade strategy. If a configuration schema mismatch or version mismatch (expected: `"1.0.0"`) is detected at startup, the server must fail fast with an explicit, human-friendly `ConfigError` explaining the incompatibility, rather than executing complex migration logic.

### Boundary: Release Packaging & Automation (Build Pipeline)
- **Policy:** Add `mcp_server/assets/` to `.gitignore` so that packaged assets are not checked into Git. The only checked-in config and template files will be in `.pgmcp/`.
- **Policy:** Place the build manifest file at `.pgmcp/config/release_manifest.yaml` to ensure all configurations are co-located in the config folder.
- **Policy:** Implement a build-time pre-build sync script (e.g. `scripts/build_package.py`) that parses `.pgmcp/config/release_manifest.yaml`, clears `mcp_server/assets/`, copies the designated source files, and then triggers the package build backend (`python -m build`). This pipeline is built as part of this issue (#420).
- **Policy:** Active development of agent instructions/workflows modifies files in their active IDE/system locations (`.agents/`, `.github/agents/`). They are copied to `docs/agents/` to serve as the stable inventory for packaging. Bypasses brittle automated sync scripts.

### Boundary: Development Isolation
- **Policy:** Document the development isolation setup (running a stable built wheel in `pgmcp_stable_venv` pointing its working directory to the development repository root) as the **standard best practice** for developers working on the `pgmcp` repository itself. This keeps the running chat engine stable during refactoring.

---

## Expected Results

1. Clean checkouts of target repositories can be initialized via `pgmcp --init` to recursively copy all packaged assets (excluding `template_registry.json`) under `.pgmcp/`.
2. `mcp_server/scaffolding/templates` is deleted and all tests pass using the settings-based template paths.
3. The server validates configuration compatibility at startup, failing fast with clear, human-readable error messages on schema/version mismatch (expected: `"1.0.0"`).
4. Bundled package assets (`mcp_server/assets/`) are ignored in Git and populated automatically during package packaging by a build-time pre-build sync script using the rules defined in `.pgmcp/config/release_manifest.yaml`.
5. The running instance of the MCP server can be installed and run from a packaged wheel in a stable venv, operating independently of the active development repository's python source files.

## Related Documentation
- **[docs/reference/mcp/release-assets-procedure.md](docs/reference/mcp/release-assets-procedure.md)**
- **[docs/reference/mcp/server-configuration.md](docs/reference/mcp/server-configuration.md)**
- **[docs/development/issue385/documentation.md](docs/development/issue385/documentation.md)**
---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-06 | Agent | Initial draft |
| 1.1 | 2026-07-06 | Agent | Refine strategy to preserve strict CLI initialization check, track templates in dev git, ignore assets folder, and implement flat copy |
| 1.2 | 2026-07-06 | Agent | Move release manifest to `.pgmcp/config/release_manifest.yaml`, define dev-isolation as a developer best practice, and untrack `.agents/mcp_config.json`. |
| 1.3 | 2026-07-07 | Agent | Deepen versioning analysis: identify versioning problem space, boundaries, gaps, options, and non-destructive upgrade policy. |
| 1.4 | 2026-07-07 | Agent | Simplify versioning: exclude templates, classify registry as log, restrict to config versioning with clean-break error reporting. |
| 1.5 | 2026-07-07 | Agent | Document test template path resolution strategy (Richtung 1) and configuration version standardization to `"1.0.0"`. |
| 1.6 | 2026-07-07 | Agent | Align with design v1.1 decisions: exclude template_registry.json, reject sync script, and clarify copying of agent instructions. |

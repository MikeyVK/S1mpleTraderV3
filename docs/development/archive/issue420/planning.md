<!-- c:\temp\pgmcp\docs\development\issue420\planning.md -->
<!-- template=planning version=130ac5ea created=2026-07-07T10:47Z updated= -->
# Release Assets Sync and Config Validation Planning

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-07-07

---

## Purpose

Define sequential cycle decomposition, test-suite impact, and validation criteria for deferred release assets, template initialization, and config version validation.

## Scope

**In Scope:**
Adding version: Literal['1.0.0'] to schemas, intercepting version validation errors in loader.py, CLI --init flat recursive copy, removing mcp_server/scaffolding/templates, build sync script scripts/build_package.py, release_manifest.yaml, docs/agents/ IDE partitioning, test conftest/test_support refactoring, and fail-fast check in conftest.py.

**Out of Scope:**
Automatic rule synchronization script, template registry versioning, automatic config upgrade tool, and changes to release flow outside scripts/build_package.py.

## Prerequisites

Read these first:
1. Read the approved research.md and design.md for issue 420.
2. Read docs/coding_standards/ARCHITECTURE_PRINCIPLES.md, DOCUMENTATION_STANDARD.md, and TYPE_CHECKING_PLAYBOOK.md.
---

## Summary

Plan the sequential execution cycles, verification strategies, and deliverables to integrate release packaging and config version validation cleanly.

---

## Dependencies

- None

---

## TDD Cycles


### Cycle 1: C_VERSION.1: Config Version Validation

**Goal:** Implement clean-break version validation check in ConfigLoader and standardize all config files in `.pgmcp/config/` to version `"1.0.0"`.

**Tests:**
- `tests/mcp_server/unit/config/test_config_version.py` (new unittests verifying success and error cases)

**Success Criteria:**
- `ConfigLoader` public load methods (such as `load_git_config`) reject config versions other than `"1.0.0"` (including missing version fields) with `ConfigError`
- All 16 config files under `.pgmcp/config/` load successfully with version `"1.0.0"`
- Type checking (MyPy and Pyright) passes flawlessly for all modified files
- Quality gates (`run_quality_gates` / Ruff / Pylint 10.0/10) pass for all modified files
- The entire test suite passes


### Cycle 2: C_TEST_RESOLVE.1: Test Suite Path Resolution

**Goal:** Refactor `tests/conftest.py` and `tests/mcp_server/test_support.py` to dynamically resolve template path from Settings, removing hardcoded paths.

**Tests:**
- All 7 affected test suites pass when pointing to resolved template paths:
  1. `tests/mcp_server/integration/test_document_templates.py`
  2. `tests/mcp_server/integration/test_smoke_all_types.py`
  3. `tests/mcp_server/scaffolding/test_tier3_pattern_python_pytest.py`
  4. `tests/mcp_server/test_design_e2e.py`
  5. `tests/mcp_server/test_design_template.py`
  6. `tests/mcp_server/test_validation_enforcement.py`
  7. `tests/mcp_server/unit/services/test_template_engine.py`

**Success Criteria:**
- `conftest.py` sets `MCP_TEMPLATE_ROOT` dynamically from `Settings().server.server_root_dir`
- `get_template_root()` returns `Settings.from_env().server.resolved_template_root`
- The 7 test files use `get_template_root()` instead of hardcoded paths
- No template copying logic exists in `conftest.py` or `test_support.py`
- Type checking (MyPy and Pyright) passes for all modified files
- Quality gates (`run_quality_gates`) pass for all modified files

**Dependencies:** C_VERSION.1: Config Version Validation


### Cycle 3: C_SCAFFOLD_CLEAN.1: Scaffolding Duplicates Deletion & Git Tracking

**Goal:** Delete the duplicate scaffolding templates directory from Git, verify the Git tracking of `.pgmcp/templates/`, and verify the test suite passes.

**Tests:**
- All test suites pass after `mcp_server/scaffolding/templates` is deleted

**Success Criteria:**
- `mcp_server/scaffolding/templates/` directory is removed from Git and filesystem
- `.pgmcp/templates/` directory is confirmed as tracked under Git version control
- No test failures occur due to missing templates
- Type checking (MyPy and Pyright) passes for all modified files
- Quality gates (`run_quality_gates`) pass for all modified files

**Dependencies:** C_TEST_RESOLVE.1: Test Suite Path Resolution


### Cycle 4: C_CLI_INIT.1: CLI Flat Copy Initialization

**Goal:** Refactor `pgmcp --init` to recursively copy all assets to `.pgmcp/` in the workspace.

**Tests:**
- `tests/mcp_server/unit/test_cli.py` (success and fail-fast scenarios)

**Success Criteria:**
- `pgmcp --init` performs a flat recursive copy of `mcp_server/assets/` to `.pgmcp/`
- Idempotency check remains active (fails if `.pgmcp/` already exists)
- Type checking (MyPy and Pyright) passes for all modified files
- Quality gates (`run_quality_gates`) pass for all modified files

**Dependencies:** C_SCAFFOLD_CLEAN.1: Scaffolding Duplicates Deletion & Git Tracking


### Cycle 5: C_IDE_PARTITION.1: IDE Agent Instructions Partitioning

**Goal:** Copy and organize agent instructions under `docs/agents/` partitioned by target environment (VS Code and Antigravity 2.0) to serve as a stable inventory for packaging, while keeping active configuration directories (`.agents/`, `.github/agents/`) fully intact.

**Tests:**
- Verify correct layout of `docs/agents/` in workspace.

**Success Criteria:**
- `docs/agents/vscode/` and `docs/agents/antigravity/` directories are created and populated
- Active rule/agent instruction files in `.agents/` and `.github/agents/` are fully retained in place to ensure ongoing IDE functionality
- Quality gates (`run_quality_gates` for documentation files) pass

**Dependencies:** C_CLI_INIT.1: CLI Flat Copy Initialization


### Cycle 6: C_BUILD.1: Build-Time Packaging Automation

**Goal:** Create `release_manifest.yaml`, implement `scripts/build_package.py` pre-build sync script, and fail-fast check in `conftest.py` for empty assets.

**Tests:**
- `tests/mcp_server/unit/config/test_settings.py:test_assets_directories_exist` (verify it handles clean checkouts cleanly)

**Success Criteria:**
- `release_manifest.yaml` maps sources to `mcp_server/assets/`, excluding `template_registry.json`
- `scripts/build_package.py` cleans assets, reads `release_manifest.yaml`, copies files, and invokes python package build
- `build_package.py` fails fast if manifest or any mapped source file is missing
- `conftest.py` checks if `mcp_server/assets/` is empty/missing and fails fast with instructions to run `build_package.py`
- Type checking (MyPy and Pyright) passes for all modified files
- Quality gates (`run_quality_gates`) pass for all modified files

**Dependencies:** C_IDE_PARTITION.1: IDE Agent Instructions Partitioning


### Cycle 7: C_DOC.1: Developer Isolation Documentation

**Goal:** Document development isolation best practices under `docs/setup/dev-isolation.md`.

**Tests:**
- Verify documentation is readable and follows markdown standards.

**Success Criteria:**
- `docs/setup/dev-isolation.md` created with clear setup guide
- Quality gates (`run_quality_gates`) pass for documentation

**Dependencies:** C_BUILD.1: Build-Time Packaging Automation

---

## Risks & Mitigation

- **Risk:** Missing `mcp_server/assets` directory on fresh checkout causing tests to fail.
  - **Mitigation:** Update `tests/conftest.py` to check if `mcp_server/assets/` is empty/missing, and fail fast with a clear message instructing the developer to run `scripts/build_package.py`. This avoids duplicating copying code in `conftest.py`.
- **Risk:** Version validation checks breaking tests immediately upon activation.
  - **Mitigation:** Add `version: Literal["1.0.0"]` to Pydantic schemas and update all 16 configuration files in `.pgmcp/config/` to version `"1.0.0"` in the same commit.
- **Risk:** Modifying or deleting active agent directories (`.agents/`, `.github/agents/`) causing active agent sessions to fail or lose configuration.
  - **Mitigation:** Copy the instructions to `docs/agents/` to serve as the stable inventory for packaging. Do not move or delete any active configuration files from `.agents/` or `.github/agents/` in the workspace; they must remain fully intact.

---

## Milestones

- Cycle C_VERSION.1: Loader version check active and all configs updated to `"1.0.0"`
- Cycle C_TEST_RESOLVE.1: Test suite decoupled from scaffolding templates
- Cycle C_SCAFFOLD_CLEAN.1: Redundant scaffolding templates directory deleted and Git-tracked templates verified
- Cycle C_CLI_INIT.1: CLI `--init` flat-copy active
- Cycle C_IDE_PARTITION.1: IDE agent instructions partitioned under `docs/agents/`
- Cycle C_BUILD.1: Build Sync Script active, `mcp_server/assets` ignored, and fail-fast check in `conftest.py`
- Cycle C_DOC.1: Developer isolation guide documented

## Related Documentation
- **[docs/reference/mcp/release-assets-procedure.md][related-1]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-2]**

<!-- Link definitions -->

[related-1]: docs/reference/mcp/release-assets-procedure.md
[related-2]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-07 | Agent | Initial draft |
| 1.1 | 2026-07-07 | Agent | Add typing/quality gates to cycles, split Cycle 5, list test files explicitly, add dev-isolation doc cycle, and verify Git template tracking. |
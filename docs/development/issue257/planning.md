<!-- docs\development\issue257\planning.md -->
<!-- template=planning version=130ac5ea created=2026-03-14T00:00Z updated=2026-03-14 -->
# Config Layer SRP Refactoring — Implementation Planning

**Status:** READY
**Version:** 2.0
**Last Updated:** 2026-03-14
**Research reference:** [research_config_layer_srp.md](research_config_layer_srp.md) v1.9
**Archived predecessor:** [planning_pse_v1.0_archived.md](planning_pse_v1.0_archived.md) (Config-First PSE Architecture — different scope, superseded)

---

## Purpose

Executable implementation specification for the config-layer SRP refactoring (issue #257).
Six ordered cycles, each with explicit blast-radius closure, structural anti-regression tests,
test-zone assignments, and hard Stop/Go gates with verifiable output.

This document is the single authoritative scope description for this refactor run.
The archived PSE planning and any earlier planning.md versions are not applicable.

---

## Prerequisites

Before cycle 1 starts, all of the following must be true:

- ☐ `research_config_layer_srp.md` v1.9 committed on active branch
- ☐ `ARCHITECTURE_PRINCIPLES.md` §12 updated (committed in research v1.8)
- ☐ Branch `feature/257-reorder-workflow-phases` active, `planning` phase
- ☐ `pytest tests/mcp_server/ --override-ini="addopts=" --tb=no -q` → all pass, 0 errors

---

## Global Planning Rules

These rules apply to every cycle. A cycle whose implementation violates any rule is a NO-GO
regardless of whether its own Stop/Go gate passes.

### Rule P-1: No Partial Migration
If a cycle is flag-day (C_SETTINGS, C_LOADER), the old pattern must be completely gone before
the cycle is marked done. Remnants are cycle-blockers, not technical debt to defer.
A cycle completion with residual old-pattern calls is a false GO.

### Rule P-2: Forbidden Legacy Patterns After C_LOADER
After C_LOADER is complete, the following patterns are prohibited everywhere outside
`mcp_server/config/`:

| Pattern | Prohibited in |
|---|---|
| `Config.from_file(...)` | `tools/`, `managers/`, `core/`, `scaffolding/`, `scaffolders/`, tests |
| `Config.load()` | same |
| `Config.reset_instance()` / `Config.reset()` | same |
| `ClassVar _instance` on schema classes | `config/schemas/` |
| Fallback construction `x or Config.from_file()` | `managers/`, `core/` |
| Module-level singleton export (`settings = Settings.load()`) | `config/` |

A structural test in C_LOADER RED phase enforces P-2 permanently.

### Rule P-3: Generic Config Only
Workflow-level config (`workflows.yaml`, `workphases.yaml`) must not contain issue-specific
values, paths, or literals. If issue context is needed at runtime, it is passed as a parameter
to a translator/builder; it is never baked into YAML. Violation = cycle-blocker.

### Rule P-4: Built and Wired
Every new component (ConfigLoader, ConfigValidator, GatePlanBuilder, etc.) must satisfy ALL
of these before the cycle DoD is met:

1. Component exists in production code
2. At least one real consumer uses it in production wiring (`server.py`)
3. The old code path that it replaces is deleted
4. A grep confirms zero residual old-path calls
5. At least one integration test exercises the new path end-to-end

### Rule P-5: Test Zones Enforced Per Cycle
Zone 1 (config layer, YAML access permitted), Zone 2 (spec/builder — no YAML, pre-built objects),
Zone 3 (managers/tools/core — no YAML, no config loading).
Each cycle's implementation must explicitly assign its new tests to a zone. No Zone 3 test
may construct a `.st3/` subtree or call `Config.from_file()`.

### Rule P-6: Env-Var Renames Are Blast-Radius Items
Any env-var rename (e.g., `MCP_LOG_LEVEL` → `LOG_LEVEL`) must be tracked in the cycle's
blast radius section alongside production and test callers. Verification = grep showing 0
matches for the old name.

### Rule P-7: Single Source of Truth
This document is the single planning reference. Contradictory scope descriptions in older
artefacts are superseded. All cross-references in tests and commits must point to this
document's cycle labels (`C_SETTINGS`, `C_LOADER`, etc.).

---

## Cycle Summary & Order

```
C_SETTINGS (P0) → C_LOADER (P0) → C_VALIDATOR (P1) → C_GITCONFIG (P2)
                                                     → C_CLEANUP   (P2)
                                                     → C_SPECBUILDERS (P4, optional)
```

No cycle may start until the previous cycle's Stop/Go gate is fully ticked with verification
output shown and committed.

---

## Cycle 1 — C_SETTINGS

**Priority:** P0
**Depends on:** nothing
**Flag-day:** yes — module-level singletons deleted

### Goal

Delete `settings = Settings.load()` and `workflow_config = WorkflowConfig.load()` as module-level
exports. `Settings.from_env()` is called once at the composition root (`server.py`).
All 14 consumers receive `settings: Settings` as a constructor parameter.
`MCP_LOG_LEVEL` is renamed to `LOG_LEVEL` everywhere simultaneously.

### Integration Surface (all files that MUST change in this cycle)

The cycle is not done until every entry below is ticked.

**Production changes — singleton deletes & DI wiring:**

| ☐ | File | Required change |
|---|---|---|
| ☐ | `mcp_server/config/settings.py` | Delete `settings = Settings.load()`; rename `Settings.load` → `Settings.from_env`; rename `MCP_LOG_LEVEL` → `LOG_LEVEL` |
| ☐ | `mcp_server/config/workflows.py` | Delete `workflow_config = WorkflowConfig.load()` |
| ☐ | `mcp_server/server.py` | Add `settings = Settings.from_env()` at composition root; pass `settings` to all consumers |
| ☐ | `mcp_server/managers/artifact_manager.py` | Remove singleton import; accept `workspace_root: Path` param |
| ☐ | `mcp_server/core/logging.py` | Remove singleton import; accept `log_level: str` param |
| ☐ | `mcp_server/cli.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/tools/test_tools.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/adapters/filesystem.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/adapters/git_adapter.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/adapters/github_adapter.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/tools/discovery_tools.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/tools/code_tools.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/scaffolding/utils.py` | Remove singleton import; accept `settings: Settings` param |

**Env-var rename blast radius (Rule P-6):**

| ☐ | Location | Change |
|---|---|---|
| ☐ | `mcp_server/config/settings.py` line 62 | `os.environ.get("MCP_LOG_LEVEL")` → `os.environ.get("LOG_LEVEL")` |
| ☐ | `tests/mcp_server/unit/conftest.py` line 10 | `monkeypatch.setenv("MCP_LOG_LEVEL", ...)` → `setenv("LOG_LEVEL", ...)` |
| ☐ | `.vscode/mcp.json` (new file) | Add env block: `LOG_LEVEL`, `MCP_SERVER_NAME`, `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_PROJECT_NUMBER` |

**Test changes:**

| ☐ | File | Required change |
|---|---|---|
| ☐ | `tests/mcp_server/unit/config/test_settings.py` | `Settings.load()` → `Settings.from_env()` with mocked env |
| ☐ | `tests/unit/tools/test_discovery_tools.py` | Construct `Settings(...)` directly (no singleton import) |
| ☐ | `tests/integration/*/test_search_documentation_e2e.py` | Construct `Settings(...)` directly |
| ☐ | `tests/unit/config/test_c_settings_structural.py` | **New file — structural tests (see RED phase below)** |

### RED Phase (write first, must fail before production change)

```python
# tests/unit/config/test_c_settings_structural.py
def test_settings_module_does_not_export_singleton():
    import mcp_server.config.settings as m
    assert not hasattr(m, "settings"), \
        "mcp_server.config.settings must not export a module-level 'settings' object"

def test_settings_exposes_from_env_not_load():
    from mcp_server.config.settings import Settings
    assert hasattr(Settings, "from_env"), "Settings.from_env() must exist"
    assert not hasattr(Settings, "load"), "Settings.load() must not exist after C_SETTINGS"

def test_workflows_module_does_not_export_singleton():
    import mcp_server.config.workflows as m
    assert not hasattr(m, "workflow_config"), \
        "mcp_server.config.workflows must not export a module-level 'workflow_config' object"

def test_log_level_env_var_is_log_level_not_mcp_log_level():
    import inspect, mcp_server.config.settings as m
    source = inspect.getsource(m)
    assert "MCP_LOG_LEVEL" not in source, \
        "settings.py must not reference MCP_LOG_LEVEL after C_SETTINGS"
```

### Test Zone Assignment

| Test | Zone | Rationale |
|---|---|---|
| `test_c_settings_structural.py` | Zone 1 | Imports Settings class; no YAML, but allowed to inspect module attributes |
| `test_settings.py` | Zone 1 | Tests `Settings.from_env()` with mocked env vars |
| Manager/tool tests that previously imported `settings` singleton | Zone 3 | Must now inject `Settings(...)` directly; no `from_module import singleton` |

### Built-and-Wired Proof (Rule P-4)

Before Stop/Go:
1. ☐ `Settings.from_env()` exists in production code
2. ☐ `server.py` calls `Settings.from_env()` at startup and passes result to all listed consumers
3. ☐ `settings = Settings.load()` line deleted from `settings.py`
4. ☐ `workflow_config = WorkflowConfig.load()` line deleted from `workflows.py`
5. ☐ grep confirms 0 residual `import settings` calls outside `server.py`
6. ☐ `test_c_settings_structural.py` is green

### Anti-Regression Check (P0 cycle — Rule P-10)

At the end of C_SETTINGS, verify these root causes from GAP_ANALYSE_ISSUE257.md are closed:

| Root cause | Verification |
|---|---|
| RC-4: Highest-risk item deferred | C_SETTINGS is done first; singleton is gone |
| RC-5: Incomplete migration | All 14 consumers updated; grep total = 0 |
| RC-2: Component built but not wired | `server.py` passes `Settings` to every consumer |

### Stop/Go — C_SETTINGS

All of the following must produce the shown output before C_LOADER may begin.

```powershell
# 1. No module-level singleton export
Select-String "settings = Settings.load\(\)" mcp_server/ -Recurse
# Expected: 0 matches

# 2. No module-level workflow export
Select-String "workflow_config = WorkflowConfig.load\(\)" mcp_server/ -Recurse
# Expected: 0 matches

# 3. No MCP_LOG_LEVEL anywhere
Select-String "MCP_LOG_LEVEL" mcp_server/, tests/ -Recurse
# Expected: 0 matches

# 4. No singleton import remaining
Select-String "from mcp_server.config.settings import settings" (Get-ChildItem -Recurse -Filter *.py).FullName
# Expected: 0 matches

# 5. Tests
pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q
# Expected: all pass, 0 errors

# 6. Quality gates
run_quality_gates(scope="branch")
# Expected: all green
```

---

## Cycle 2 — C_LOADER

**Priority:** P0
**Depends on:** C_SETTINGS
**Flag-day:** yes — `from_file()`, `load()`, `ClassVar _instance`, `reset_instance()` deleted from all 15 schema classes

### Goal

Introduce `ConfigLoader(config_root: Path)` as the sole loader for all 15 schema classes.
Move all 15 schema classes to `config/schemas/`. Hard delete of all self-loading methods.
Update all 17 production files and 15 non-Zone-1 test/fixture files. Wire 15 configs into
composition root. Establish permanent structural guard (Rule P-2).

### Integration Surface

#### New components

| ☐ | Component | Module | Purpose |
|---|---|---|---|
| ☐ | `ConfigLoader` | `mcp_server/config/loader.py` | Single loader: `load_git_config()`, `load_workflow_config()`, etc. for all 15 schemas |
| ☐ | `config/schemas/` directory | new | Home for all 15 YAML-backed schema classes + Settings |

#### Schema moves (15 classes) — must happen in this cycle

| ☐ | Class | Current location | New location |
|---|---|---|---|
| ☐ | `ArtifactRegistryConfig` | `config/artifact_registry_config.py` | `config/schemas/artifact_registry_config.py` |
| ☐ | `ContributorConfig` | `config/contributor_config.py` | `config/schemas/contributor_config.py` |
| ☐ | `GitConfig` | `config/git_config.py` | `config/schemas/git_config.py` |
| ☐ | `IssueConfig` | `config/issue_config.py` | `config/schemas/issue_config.py` |
| ☐ | `LabelConfig` | `config/label_config.py` | `config/schemas/label_config.py` |
| ☐ | `MilestoneConfig` | `config/milestone_config.py` | `config/schemas/milestone_config.py` |
| ☐ | `OperationPoliciesConfig` | `config/operation_policies.py` | `config/schemas/operation_policies.py` |
| ☐ | `ProjectStructureConfig` | `config/project_structure.py` | `config/schemas/project_structure.py` |
| ☐ | `QualityConfig` | `config/quality_config.py` | `config/schemas/quality_config.py` |
| ☐ | `ScaffoldMetadataConfig` | `config/scaffold_metadata_config.py` | `config/schemas/scaffold_metadata_config.py` |
| ☐ | `ScopeConfig` | `config/scope_config.py` | `config/schemas/scope_config.py` |
| ☐ | `WorkflowConfig` | `config/workflows.py` | `config/schemas/workflows.py` |
| ☐ | `WorkphasesConfig` | `config/workphases.py` | `config/schemas/workphases.py` |
| ☐ | `EnforcementConfig` | `managers/enforcement_runner.py` | `config/schemas/enforcement_config.py` |
| ☐ | `PhaseContractsConfig` | `managers/phase_contract_resolver.py` | `config/schemas/phase_contracts_config.py` |

#### Self-loading method deletions (all 15 classes)

| ☐ | Class | Delete |
|---|---|---|
| ☐ | `ArtifactRegistryConfig` | `from_file()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `ContributorConfig` | `from_file()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `GitConfig` | `from_file()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `IssueConfig` | `from_file()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `LabelConfig` | `load()`, `reset()`, `ClassVar _instance` |
| ☐ | `MilestoneConfig` | `from_file()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `OperationPoliciesConfig` | `from_file()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `ProjectStructureConfig` | `from_file()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `QualityConfig` | `load()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `ScaffoldMetadataConfig` | `from_file()`, local `ConfigError` class (use `core.exceptions.ConfigError`) |
| ☐ | `ScopeConfig` | `from_file()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `WorkflowConfig` | `from_file()`, `load()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `WorkphasesConfig` | `from_file()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `EnforcementConfig` | `from_file()` |
| ☐ | `PhaseContractsConfig` | `from_file()` |

#### Production consumer updates (17 files — F16)

| ☐ | File | Anti-pattern | Required fix |
|---|---|---|---|
| ☐ | `tools/pr_tools.py` | Direct tool-layer load | Remove `GitConfig.from_file()`; use `git_manager.git_config` |
| ☐ | `tools/cycle_tools.py` (×2) | Direct tool-layer load | Remove `GitConfig.from_file()`; use `git_manager.git_config` |
| ☐ | `tools/git_tools.py` (×2) | Direct tool-layer load | Remove `GitConfig.from_file()`; use `git_manager.git_config` |
| ☐ | `tools/project_tools.py` | Direct tool-layer load | Remove `WorkflowConfig.load()`; use `project_manager` |
| ☐ | `tools/label_tools.py` (×3) | Direct tool-layer load | Remove `LabelConfig.load()`; use `label_manager.label_config` |
| ☐ | `tools/issue_tools.py` (×9) | `@field_validator` load | Move all to `GitHubManager.validate_issue_params()` (→ D15) |
| ☐ | `managers/git_manager.py` | Constructor load | Remove; receive `GitConfig` via DI |
| ☐ | `managers/phase_state_engine.py` | Fallback construction | Make `git_config` param mandatory (no default) |
| ☐ | `managers/artifact_manager.py` | Fallback construction | Make `registry` param mandatory (no default) |
| ☐ | `managers/qa_manager.py` (×2) | Direct load | Remove; receive `QualityConfig` via DI |
| ☐ | `managers/phase_contract_resolver.py` | Direct load | Remove; receive `PhaseContractsConfig` via DI |
| ☐ | `managers/enforcement_runner.py` | Direct load | Remove; receive `EnforcementConfig` via DI |
| ☐ | `core/policy_engine.py` (constructor ×2) | Direct load | Remove; receive `OperationPoliciesConfig`, `GitConfig` via DI |
| ☐ | `core/policy_engine.py` (`reload()` ×4) | `reset_instance()` + `from_file()` | Replace with `ConfigLoader(self._config_root).load_*()` |
| ☐ | `core/directory_policy_resolver.py` | Fallback construction | Make `config` param mandatory (no default) |
| ☐ | `scaffolding/metadata.py` | Direct load | Remove; receive `ScaffoldMetadataConfig` via DI |
| ☐ | `scaffolders/template_scaffolder.py` | Fallback construction | Make `registry` param mandatory (no default) |

#### GitHubManager extension (D15)

| ☐ | File | Change |
|---|---|---|
| ☐ | `managers/github_manager.py` | Constructor receives: `issue_config`, `milestone_config`, `contributor_config`, `label_config`, `scope_config`, `git_config`, `adapter` |
| ☐ | `managers/github_manager.py` | Add `validate_issue_params()` — receives all 6 validator bodies moved from `issue_tools.py @field_validator` methods |
| ☐ | `tools/issue_tools.py` | `@field_validator` methods that call `Config.from_file()` removed; delegate to `github_manager.validate_issue_params()` |

#### Composition root wiring (server.py — Rule P-4)

| ☐ | Step | Change |
|---|---|---|
| ☐ | Step 1 | `loader = ConfigLoader(config_root)` instantiated; all 15 `loader.load_*()` called |
| ☐ | Step 2 | `ConfigValidator().validate_startup(...)` stub called (real impl in C_VALIDATOR) |
| ☐ | Step 3 | All managers instantiated with config objects injected |
| ☐ | Step 4 | `GitHubManager(issue_config, milestone_config, contributor_config, label_config, scope_config, git_config, adapter)` |
| ☐ | Step 5 | `PolicyEngine(policies_config, git_config)` — `config_root` stored for `reload()` |

#### Test blast-radius closure — non-Zone-1 (15 files)

| ☐ | File | Zone | Current anti-pattern | Fix |
|---|---|---|---|---|
| ☐ | `tests/mcp_server/core/test_policy_engine_config.py` | 3 | `GitConfig.reset_instance()` ×2 | Delete; singleton gone |
| ☐ | `tests/mcp_server/core/test_policy_engine.py` | 3 | `ArtifactRegistryConfig/OperationPoliciesConfig/ProjectStructureConfig.reset_instance()` ×3 | Delete; inject mocks |
| ☐ | `tests/mcp_server/core/test_directory_policy_resolver.py` | 3 | `ArtifactRegistryConfig/ProjectStructureConfig.reset_instance()` ×4 | Delete; inject mocks |
| ☐ | `tests/mcp_server/managers/test_git_manager_config.py` | 3 | `GitConfig.reset_instance()` ×2 | Delete; receive `GitConfig` directly |
| ☐ | `tests/mcp_server/integration/test_validation_policy_e2e.py` | Integration | `reset_instance()` + `from_file()` ×3 | Replace with `ConfigLoader(tmp_path)` |
| ☐ | `tests/mcp_server/integration/test_v2_smoke_all_types.py` | Integration | `reset_instance()` ×2 | Replace with `ConfigLoader(tmp_path)` |
| ☐ | `tests/mcp_server/integration/test_template_missing_e2e.py` | Integration | `reset_instance()` + `from_file()` ×1 | Replace with `ConfigLoader(tmp_path)` |
| ☐ | `tests/mcp_server/integration/test_config_error_e2e.py` | Integration | `reset_instance()` + `from_file()` ×3 | Pass bad YAML via `tmp_path`; use `ConfigLoader` |
| ☐ | `tests/mcp_server/integration/test_concrete_templates.py` | Integration | `ArtifactRegistryConfig.from_file()` ×9 | Replace with `ConfigLoader(tmp_path)` |
| ☐ | `tests/mcp_server/tools/test_pr_tools_config.py` | 3 | `GitConfig.reset_instance()` ×2, `from_file()` ×1 | Delete singleton calls; inject via `GitManager` |
| ☐ | `tests/mcp_server/tools/test_git_tools_config.py` | 3 | `GitConfig.reset_instance()` ×2, `from_file()` ×1 | Delete singleton calls; inject via `GitManager` |
| ☐ | `tests/mcp_server/unit/tools/test_github_extras.py` | 3 | `LabelConfig.reset()` ×1, `LabelConfig.load()` ×1 | Delete; inject `LabelConfig` via manager |
| ☐ | `tests/mcp_server/unit/tools/test_label_tools_integration.py` | 3 | `LabelConfig.reset()` ×15, `LabelConfig.load()` ×15 | Delete; inject via `LabelManager` |
| ☐ | `tests/mcp_server/fixtures/artifact_test_harness.py` | Fixture | `reset_instance()` ×2, `from_file()` ×1 | Rewrite to accept `ConfigLoader`-produced config |
| ☐ | `tests/mcp_server/fixtures/workflow_fixtures.py` | Fixture | `WorkflowConfig.load()` ×1 | Replace with `ConfigLoader(tmp_path).load_workflow_config()` |

#### Zone 1 test rewrites (5 files — pattern change, not break)

| ☐ | File | Change |
|---|---|---|
| ☐ | `tests/mcp_server/unit/config/test_artifact_registry_config.py` | `from_file()` + `reset_instance()` → `ConfigLoader(tmp_path).load_artifact_registry_config()` |
| ☐ | `tests/mcp_server/unit/config/test_contributor_config.py` | Same |
| ☐ | `tests/mcp_server/unit/config/test_issue_config.py` | Same |
| ☐ | `tests/mcp_server/unit/config/test_workflow_config.py` | `WorkflowConfig.load()` → `ConfigLoader(tmp_path).load_workflow_config()` |
| ☐ | `tests/mcp_server/unit/config/test_settings.py` | `Settings.load()` → `Settings.from_env()` with mocked env |

### RED Phase (write first, must fail before production change)

```python
# tests/unit/config/test_c_loader_structural.py

def test_no_from_file_on_any_config_schema():
    """Every schema class must be a pure Pydantic model — no loader methods."""
    import inspect
    import mcp_server.config.schemas as schemas_module
    for name, cls in inspect.getmembers(schemas_module, inspect.isclass):
        for forbidden in ("from_file", "load", "reset_instance", "reset"):
            assert not hasattr(cls, forbidden), (
                f"{name}.{forbidden}() must not exist — ConfigLoader is the sole loader."
            )

def test_no_manager_imports_config_schema_directly():
    """Managers must not import config schema classes."""
    import pathlib
    managers_dir = pathlib.Path("mcp_server/managers")
    for py_file in managers_dir.glob("*.py"):
        source = py_file.read_text()
        assert "from mcp_server.config" not in source, (
            f"{py_file.name} imports a config class directly — must use constructor injection."
        )

def test_no_tool_calls_config_loader_methods():
    """Tools must not call Config.from_file() or Config.load() directly."""
    import pathlib
    tools_dir = pathlib.Path("mcp_server/tools")
    for py_file in tools_dir.glob("*.py"):
        source = py_file.read_text()
        assert ".from_file(" not in source and ".reset_instance(" not in source, (
            f"{py_file.name} calls from_file()/reset_instance() — must use manager."
        )

def test_config_loader_exists():
    from mcp_server.config.loader import ConfigLoader
    assert callable(ConfigLoader)
```

### Test Zone Assignment

| Test file | Zone | Permitted accesses |
|---|---|---|
| `test_c_loader_structural.py` | Zone 1 | Introspects class attributes — no YAML |
| `tests/unit/config/test_*.py` (config schema tests) | Zone 1 | Write YAML to `tmp_path`; call `ConfigLoader(tmp_path).load_*()` |
| `test_validation_policy_e2e.py`, `test_concrete_templates.py` | Integration | `ConfigLoader(tmp_path)` with constructed YAML; no real `.st3/` |
| `test_policy_engine.py`, `test_directory_policy_resolver.py` | Zone 3 | Receive pre-built config objects; no YAML, no `from_file()` |
| `test_github_extras.py`, `test_label_tools_integration.py` | Zone 3 | Receive pre-built `LabelConfig`; no `LabelConfig.load()` |

### Built-and-Wired Proof (Rule P-4)

Before Stop/Go:
1. ☐ `ConfigLoader` exists in `config/loader.py` with methods for all 15 schemas
2. ☐ `server.py` instantiates `ConfigLoader(config_root)` and calls all 15 `load_*()` methods
3. ☐ All 17 production files have no `from_file()` / `load()` / `reset_instance()` calls
4. ☐ All 15 test/fixture files in Zone 3 have no `reset_instance()` / `from_file()` calls
5. ☐ `test_c_loader_structural.py` — all 4 tests pass
6. ☐ At least one integration test exercises `ConfigLoader → manager → tool` end-to-end

### Anti-Regression Check (P0 cycle — Rule P-10)

| Root cause | Verification |
|---|---|
| RC-5: Halve migraties | All 17 + 15 checklist items ticked; grep confirms 0 |
| RC-2: Component built but not wired | `server.py` wires all 15 configs; grep confirms |
| RC-4: Highest-risk last | C_LOADER is P0, done before any P1+ cycles |

### Stop/Go — C_LOADER

All of the following must produce the shown output before C_VALIDATOR may begin.

```powershell
# 1. No from_file / load / reset_instance in production code outside config/
Select-String "\.from_file\(|reset_instance\(|\.reset\(" `
    (Get-ChildItem mcp_server/tools, mcp_server/managers, mcp_server/core, mcp_server/scaffolding, mcp_server/scaffolders -Recurse -Filter *.py).FullName
# Expected: 0 matches

# 2. No config schema imports in managers
Select-String "from mcp_server\.config" `
    (Get-ChildItem mcp_server/managers -Recurse -Filter *.py).FullName
# Expected: 0 matches (only loader.py and validator.py may be imported by server.py)

# 3. No from_file / reset_instance in tests
Select-String "\.from_file\(|reset_instance\(|LabelConfig\.reset\(|LabelConfig\.load\(" `
    (Get-ChildItem tests/mcp_server -Recurse -Filter *.py).FullName
# Expected: 0 matches

# 4. Structural tests
pytest tests/unit/config/test_c_loader_structural.py -v
# Expected: 4 passed

# 5. Full test suite
pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q
# Expected: all pass, 0 errors

# 6. Quality gates
run_quality_gates(scope="branch")
# Expected: all green
```

---

## Cycle 3 — C_VALIDATOR

**Priority:** P1
**Depends on:** C_LOADER
**Flag-day:** no — additive + one deletion (`label_startup.py`)

### Goal

Introduce `ConfigValidator.validate_startup()` as the single cross-config validation entrypoint.
Delete `label_startup.py` (label-sync-against-GitHub does not belong here; moves to `LabelManager`).

### Integration Surface

| ☐ | File | Required change |
|---|---|---|
| ☐ | `mcp_server/config/validator.py` (new) | `ConfigValidator` with `validate_startup(policies, workflow, structure, artifact, phase_contracts, workphases)` |
| ☐ | `mcp_server/server.py` | Replace stub with real `ConfigValidator().validate_startup(...)` call |
| ☐ | `mcp_server/config/label_startup.py` | Delete file |
| ☐ | All files importing `label_startup` | Remove import |

### RED Phase

```python
# tests/unit/config/test_c_validator_structural.py
def test_label_startup_deleted():
    import importlib.util
    assert importlib.util.find_spec("mcp_server.config.label_startup") is None

def test_config_validator_exists():
    from mcp_server.config.validator import ConfigValidator
    assert callable(getattr(ConfigValidator, "validate_startup", None))
```

### Test Zone Assignment

| Test | Zone | Notes |
|---|---|---|
| `test_c_validator_structural.py` | Zone 1 | Imports validator class; no YAML |
| `test_config_validator.py` (Zone 1 unit tests) | Zone 1 | Pass pre-built config objects to `validate_startup()` |
| Integration tests for startup failure | Integration | `ConfigLoader(tmp_path)` → `validate_startup()` with bad YAML |

### Built-and-Wired Proof (Rule P-4)

1. ☐ `ConfigValidator` exists in `config/validator.py`
2. ☐ `server.py` calls `validate_startup()` at startup; raises `ConfigError` on invalid config
3. ☐ `label_startup.py` deleted; grep confirms 0 imports
4. ☐ At least one test exercises `validate_startup()` with a cross-config violation

### Stop/Go — C_VALIDATOR

```powershell
# 1. label_startup deleted
Test-Path mcp_server/config/label_startup.py
# Expected: False

# 2. No imports of label_startup
Select-String "label_startup" (Get-ChildItem mcp_server -Recurse -Filter *.py).FullName
# Expected: 0 matches

# 3. Tests
pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q
# Expected: all pass

# 4. Quality gates
run_quality_gates(scope="branch")
# Expected: all green
```

---

## Cycle 4 — C_GITCONFIG

**Priority:** P2
**Depends on:** C_LOADER
**Flag-day:** no — field defaults removed; YAML must be complete

### Goal

Remove Python defaults from `GitConfig` domain-convention fields (makes missing `git.yaml`
a hard error, not silent fallback). Remove `output_dir` default from `ArtifactLoggingConfig`.

### Integration Surface

| ☐ | File | Required change |
|---|---|---|
| ☐ | `mcp_server/config/schemas/git_config.py` | All domain-convention fields: `Field(default=...)` → `Field(...)` |
| ☐ | `mcp_server/config/schemas/quality_config.py` | `ArtifactLoggingConfig.output_dir`: remove `default="temp/qa_logs"` |

### RED Phase

```python
def test_git_config_domain_fields_have_no_defaults():
    from mcp_server.config.schemas.git_config import GitConfig
    fields_with_defaults = [
        name for name, field in GitConfig.model_fields.items()
        if field.default is not None or field.default_factory is not None
    ]
    assert fields_with_defaults == [], \
        f"GitConfig domain-convention fields must not have Python defaults: {fields_with_defaults}"
```

### Test Zone Assignment

| Test | Zone | Notes |
|---|---|---|
| `test_git_config_domain_fields_have_no_defaults` | Zone 1 | Inspects model fields; no YAML |
| `test_loader_raises_on_missing_git_yaml` | Zone 1 | `ConfigLoader(empty_tmp_path)` → `ConfigError` |

### Stop/Go — C_GITCONFIG

```powershell
pytest tests/unit/config/test_git_config.py -v
# Expected: all pass (including missing-yaml error test)

pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q
# Expected: all pass

run_quality_gates(scope="branch")
# Expected: all green
```

---

## Cycle 5 — C_CLEANUP

**Priority:** P2
**Depends on:** C_SETTINGS, C_LOADER
**Flag-day:** no — one file move, one constants update

### Goal

Move `template_config.py` to `utils/` (path-resolution utility, not config schema).
Replace `server.version` hardcoded string with `importlib.metadata.version("mcp_server")`.

### Integration Surface

| ☐ | File | Required change |
|---|---|---|
| ☐ | `mcp_server/utils/template_config.py` (new) | Move `get_template_root()` here from `config/template_config.py` |
| ☐ | `mcp_server/config/template_config.py` | Delete original file |
| ☐ | All importers of `config.template_config` | Update import → `utils.template_config` |
| ☐ | `mcp_server/config/schemas/settings.py` | `version = "1.0.0"` → `importlib.metadata.version("mcp_server")` |

### Test Zone Assignment

| Test | Zone | Notes |
|---|---|---|
| Import tests for `utils.template_config` | Zone 3 | No YAML; pure import test |

### Stop/Go — C_CLEANUP

```powershell
# 1. Old file gone
Test-Path mcp_server/config/template_config.py
# Expected: False

# 2. No old import remaining
Select-String "from mcp_server.config.template_config" (Get-ChildItem -Recurse -Filter *.py).FullName
# Expected: 0 matches

pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q
# Expected: all pass

run_quality_gates(scope="branch")
# Expected: all green
```

---

## Cycle 6 — C_SPECBUILDERS

**Priority:** P4
**Depends on:** C_LOADER, C_VALIDATOR
**Flag-day:** no — additive; existing paths are replaced cycle-internally
**Note:** May be moved to a separate issue if P0+P1 cycles reveal unexpected scope.

### Goal

Introduce `GatePlanBuilder`, `ScaffoldSpecBuilder`, `WorkflowSpecBuilder` in
`config/translators/`. Create `mcp_server/dtos/specs/` with typed spec output DTOs.
Update `QAManager`, `ArtifactManager`, `ProjectManager` to consume specs (Rule P-4).

### Integration Surface

**New components:**

| ☐ | Component | Module |
|---|---|---|
| ☐ | `GatePlanBuilder` | `config/translators/gate_plan_builder.py` |
| ☐ | `ScaffoldSpecBuilder` | `config/translators/scaffold_spec_builder.py` |
| ☐ | `WorkflowSpecBuilder` | `config/translators/workflow_spec_builder.py` |
| ☐ | `GateExecutionPlan` | `dtos/specs/gate_execution_plan.py` |
| ☐ | `ScaffoldSpec` | `dtos/specs/scaffold_spec.py` |
| ☐ | `WorkflowInitSpec` | `dtos/specs/workflow_init_spec.py` |
| ☐ | `FileScope` | `dtos/specs/file_scope.py` |
| ☐ | `ProjectInitOptions` | `dtos/specs/project_init_options.py` |

**Consumer updates:**

| ☐ | File | Required change |
|---|---|---|
| ☐ | `managers/qa_manager.py` | Accept `gate_plan_builder: GatePlanBuilder` via DI; build plan in `run_quality_gates()` |
| ☐ | `managers/artifact_manager.py` | Accept `scaffold_spec_builder: ScaffoldSpecBuilder` via DI |
| ☐ | `managers/project_manager.py` | Accept `workflow_spec_builder: WorkflowSpecBuilder` via DI |
| ☐ | `managers/phase_state_engine.py` | Accept `WorkflowInitSpec` as runtime param (D14 P4) |
| ☐ | `mcp_server/server.py` | Wire all three builders at composition root |

### RED Phase

```python
def test_spec_builder_classes_exist():
    from mcp_server.config.translators.gate_plan_builder import GatePlanBuilder
    from mcp_server.config.translators.scaffold_spec_builder import ScaffoldSpecBuilder
    from mcp_server.config.translators.workflow_spec_builder import WorkflowSpecBuilder

def test_spec_dto_classes_exist():
    from mcp_server.dtos.specs.gate_execution_plan import GateExecutionPlan
    from mcp_server.dtos.specs.scaffold_spec import ScaffoldSpec
    from mcp_server.dtos.specs.workflow_init_spec import WorkflowInitSpec
    from mcp_server.dtos.specs.file_scope import FileScope
    from mcp_server.dtos.specs.project_init_options import ProjectInitOptions

def test_qa_manager_accepts_gate_plan_not_quality_config():
    """QAManager must not import QualityConfig directly after C_SPECBUILDERS."""
    import inspect, pathlib
    source = pathlib.Path("mcp_server/managers/qa_manager.py").read_text()
    assert "QualityConfig" not in source, \
        "QAManager must use GateExecutionPlan, not raw QualityConfig"
```

### Test Zone Assignment

| Test | Zone | Notes |
|---|---|---|
| `test_gate_plan_builder.py` | Zone 2 | Receives `QualityConfig` object (no YAML); produces `GateExecutionPlan` |
| `test_scaffold_spec_builder.py` | Zone 2 | Receives `ArtifactRegistryConfig` object; produces `ScaffoldSpec` |
| `test_qa_manager_with_plan.py` | Zone 3 | Receives pre-built `GateExecutionPlan`; no YAML |

### Built-and-Wired Proof (Rule P-4)

1. ☐ All 3 builders exist
2. ☐ `server.py` instantiates all 3 builders and injects them into respective managers
3. ☐ `QAManager`, `ArtifactManager`, `ProjectManager` no longer hold `QualityConfig`, `ArtifactRegistryConfig`, `WorkflowConfig` directly
4. ☐ Zone 3 test for `QAManager` uses injected `GateExecutionPlan` — no YAML

### Stop/Go — C_SPECBUILDERS

```powershell
# 1. Zone 2 builder tests pass with no filesystem access
pytest tests/unit/config/translators/ -v
# Expected: all pass

# 2. Zone 3 manager test uses injected plan
pytest tests/mcp_server/managers/test_qa_manager.py -v
# Expected: all pass, no .st3/ fixture construction

# 3. Full suite
pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q
# Expected: all pass

run_quality_gates(scope="branch")
# Expected: all green
```

---

## Forbidden Pattern Reference Card

After C_LOADER completes, use this as a quick anti-regression check. Any of the below found
in a PR is a blocker, not a comment.

```python
# ❌ FORBIDDEN everywhere outside mcp_server/config/ after C_LOADER
Config.from_file(...)            # schema self-loading
Config.load()                    # schema self-loading
Config.reset_instance()          # singleton cleanup hack
Config.reset()                   # LabelConfig variant
x = x or Config.from_file()     # fallback constructor
settings = Settings.load()       # module-level singleton export
from mcp_server.config.x import some_config_singleton  # module-level import
```

---

## Anti-Regression Checklist (End of P0+P1 Cycles)

Run after C_SETTINGS and C_LOADER complete. Maps directly to root causes in GAP_ANALYSE_ISSUE257.md.

| Root cause | Check | Expected |
|---|---|---|
| RC-1: Stop/Go not enforced | Each cycle gate was gated; output was shown | All Stop/Go ticked with output |
| RC-2: Component built not wired | `server.py` wires ConfigLoader + all 15 configs + all managers | grep confirms |
| RC-3: No structural tests | `test_c_settings_structural.py`, `test_c_loader_structural.py` green | pytest pass |
| RC-4: High-risk deferred | C_SETTINGS + C_LOADER done as P0, before any P1+ | commit order confirms |
| RC-5: Half migration | All 17 prod + 15 test files updated; grep = 0 | Select-String = 0 |
| RC-6: Private/prohibited internals called | No `from_file()` in managers/tools; structural test enforces | pytest pass |
| RC-7: Component-boundary violations | No config schema imports in managers | structural test enforces |
| RC-8: Planning not executable | Every cycle has grep-verifiable DoD criteria | this document |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-03-14 | Agent | Complete rewrite incorporating 12 mandatory planning conditions from QA agent review: Global Planning Rules P-1 through P-7; Integration Surface per cycle; RED phase per cycle; Test Zone Assignment per cycle; Built-and-Wired Proof per cycle; Anti-Regression Check for P0 cycles; Forbidden Pattern Reference Card; all env-var renames treated as blast-radius items; 12-condition compliance table (RC-1 through RC-8) |
| 1.0 | 2026-03-14 | Agent | Initial config SRP planning (superseded — lacked Integration Surface, test zone assignments, built-and-wired proof per cycle, and anti-regression checks) |

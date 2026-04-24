<!-- docs\development\issue257\planning.md -->
<!-- template=planning version=130ac5ea created=2026-03-14T00:00Z updated=2026-03-14 -->
# Config Layer SRP Refactoring — Implementation Planning

**Status:** READY
**Version:** 3.0
**Last Updated:** 2026-03-14
**Research reference:** [research_config_layer_srp.md](research_config_layer_srp.md) v1.9
**Archived predecessor:** [planning_pse_v1.0_archived.md](planning_pse_v1.0_archived.md) (Config-First PSE Architecture — different scope, superseded)

---

## Purpose

Executable implementation specification and deliverables manifest for the config-layer SRP refactoring (issue #257).

**Dual purpose:** This document serves both as an implementation guide (integration surfaces, RED-phase tests, Stop/Go gates) and as a `save_planning_deliverables` input (stable deliverable ids, artifacts, validates). The two layers are kept separate per cycle: the **Deliverables** section at the top of each cycle feeds `projects.json`; the **Integration Surface** section below it feeds implementation.

---

## Prerequisites

- ☐ `research_config_layer_srp.md` v1.9 committed on active branch
- ☐ `ARCHITECTURE_PRINCIPLES.md` §12 updated (committed in research v1.8)
- ☐ Branch `feature/257-reorder-workflow-phases` active, `planning` phase
- ☐ `pytest tests/mcp_server/ --override-ini="addopts=" --tb=no -q` → all pass, 0 errors

---

## Global Planning Rules

### Rule P-1: No Partial Migration
Flag-day cycles (C_SETTINGS, C_LOADER) must be fully complete before the next cycle starts.
Remnants are cycle-blockers, not technical debt. A cycle with residual old-pattern calls is a false GO.

### Rule P-2: Forbidden Legacy Patterns After C_LOADER
After C_LOADER.5 completes, these patterns are prohibited everywhere outside `mcp_server/config/`:

```python
Config.from_file(...)          # schema self-loading
Config.load()                  # schema self-loading
Config.reset_instance()        # singleton cleanup hack
Config.reset()                 # LabelConfig variant
x = x or Config.from_file()   # fallback constructor
settings = Settings.load()     # module-level singleton export
ClassVar _instance             # on any schema class
```

A structural test in C_LOADER.1 RED phase enforces P-2 permanently.

### Rule P-3: Generic Config Only
Workflow-level config must not contain issue-specific values or paths. If issue context is needed at runtime it is passed as a parameter; never baked into YAML.

### Rule P-4: Built and Wired
Every new component must satisfy all of: (1) exists in production, (2) at least one real consumer uses it through `server.py`, (3) old code path deleted, (4) grep confirms zero residual old-path calls, (5) at least one integration test exercises the new path.

### Rule P-5: Test Zones Enforced Per Cycle
Zone 1 = config layer (YAML access permitted). Zone 2 = spec/builder (no YAML, pre-built objects). Zone 3 = managers/tools/core (no YAML, no config loading). Each cycle's new tests must be explicitly zone-assigned.

### Rule P-6: Env-Var Renames Are Blast-Radius Items
Env-var renames tracked alongside production and test callers in the blast-radius section. Verified by grep showing 0 matches for old name.

### Rule P-7: Single Source of Truth
This document is the single planning reference. The archived PSE planning and v1.0/v2.0 of this document are superseded.

---

## Cycle Summary

```
C_SETTINGS.1 → C_SETTINGS.2
                             → C_LOADER.1 → C_LOADER.2 → C_LOADER.3 → C_LOADER.4 → C_LOADER.5
                                                                                              → C_VALIDATOR
                                                                                              → C_GITCONFIG
                                                                                              → C_CLEANUP
                                            (C_SPECBUILDERS deferred — separate issue)
```

| Cycle | Priority | Size | Depends On |
|---|---|---|---|
| C_SETTINGS.1 | P0 | S | — |
| C_SETTINGS.2 | P0 | S | C_SETTINGS.1 |
| C_LOADER.1 | P0 | S | C_SETTINGS.2 |
| C_LOADER.2 | P0 | M | C_LOADER.1 |
| C_LOADER.3 | P0 | M | C_LOADER.2 |
| C_LOADER.4 | P0 | M | C_LOADER.3 |
| C_LOADER.5 | P0 | S | C_LOADER.4 |
| C_VALIDATOR | P1 | S | C_LOADER.5 |
| C_GITCONFIG | P2 | S | C_LOADER.5 |
| C_CLEANUP | P2 | S | C_SETTINGS.2, C_LOADER.5 |
| C_SPECBUILDERS | P4 | L | deferred — separate issue |

---

## Cycle 1a — C_SETTINGS.1

**Goal:** Delete `settings = Settings.load()` singleton; rename `Settings.load` → `Settings.from_env`; rename `MCP_LOG_LEVEL` → `LOG_LEVEL`; wire `Settings` into `server.py` and two initial consumers (`core/logging.py`, `cli.py`) as proof of the new DI pattern.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_settings_1.from_env` | Settings.from_env() introduced | component | `Settings.from_env()` exists; `Settings.load()` deleted | `test_settings_exposes_from_env_not_load` passes | RC-4 highest risk first; P-2 no singleton |
| `c_settings_1.singleton_deleted` | Module-level singleton removed | deletion | `settings = Settings.load()` line gone from `settings.py` | `test_settings_module_does_not_export_singleton` passes | P-1 no partial migration |
| `c_settings_1.log_level_rename` | MCP_LOG_LEVEL → LOG_LEVEL | migration | `settings.py` + `conftest.py` use `LOG_LEVEL` | `Select-String "MCP_LOG_LEVEL" → 0 matches` | P-6 env-var rename |
| `c_settings_1.server_wiring_stub` | server.py DI stub wired | wiring | `server.py` calls `Settings.from_env()`; injects into `core/logging.py` + `cli.py` | `test_c_settings_structural.py` all 3 pass | P-4 built-and-wired |

### Integration Surface

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/config/settings.py` | Delete `settings = Settings.load()`; rename method to `from_env()`; `MCP_LOG_LEVEL` → `LOG_LEVEL` |
| ☐ | `mcp_server/server.py` | Add `settings = Settings.from_env()` at composition root; pass to `core/logging.py` and `cli.py` |
| ☐ | `mcp_server/core/logging.py` | Remove singleton import; accept `log_level: str` param |
| ☐ | `mcp_server/cli.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `tests/mcp_server/unit/conftest.py` line 10 | `MCP_LOG_LEVEL` → `LOG_LEVEL` |
| ☐ | `tests/unit/config/test_c_settings_structural.py` | **New file — RED phase structural tests (see below)** |

### RED Phase

```python
# tests/unit/config/test_c_settings_structural.py
def test_settings_module_does_not_export_singleton():
    import mcp_server.config.settings as m
    assert not hasattr(m, "settings")

def test_settings_exposes_from_env_not_load():
    from mcp_server.config.settings import Settings
    assert hasattr(Settings, "from_env")
    assert not hasattr(Settings, "load")

def test_log_level_env_var_renamed():
    import inspect, mcp_server.config.settings as m
    assert "MCP_LOG_LEVEL" not in inspect.getsource(m)
# Note: test_workflows_module_does_not_export_singleton belongs to C_SETTINGS.2 (workflow singleton scope)
```

### Test Zone Assignment

| Test | Zone |
|---|---|
| `test_c_settings_structural.py` | Zone 1 (class introspection, no YAML) |
| `test_settings.py` | Zone 1 (`Settings.from_env()` with mocked env) |

### Stop/Go — C_SETTINGS.1

```powershell
Select-String "settings = Settings.load\(\)" mcp_server/ -Recurse            # 0 matches
Select-String "MCP_LOG_LEVEL" mcp_server/, tests/ -Recurse                    # 0 matches
pytest tests/unit/config/test_c_settings_structural.py -v                     # 3 passed
pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q              # all pass
```

---

## Cycle 1b — C_SETTINGS.2

**Goal:** Rewire remaining 11 `Settings` consumers; delete `workflow_config` singleton; rewire all direct `workflow_config` importers; create `.vscode/mcp.json`; achieve full grep closure on singleton imports.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_settings_2.workflow_singleton_deleted` | workflow_config singleton removed | deletion | `workflow_config = WorkflowConfig.load()` gone from `workflows.py`; direct `workflow_config` importers rewired | `test_workflows_module_does_not_export_singleton` passes; `Select-String "from mcp_server.config.workflows import workflow_config" → 0 matches` | P-1 no partial migration |
| `c_settings_2.consumers_rewired` | All 11 remaining Settings consumers rewired | migration | 11 files accept `settings: Settings` param; no singleton import | `Select-String "import settings" → 0 matches` | RC-2 built and wired; RC-5 complete migration |
| `c_settings_2.mcp_json` | .vscode/mcp.json created | component | File with `LOG_LEVEL`, `MCP_SERVER_NAME`, `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_PROJECT_NUMBER` env entries | `Test-Path .vscode/mcp.json → True` | P-6 env-var single source |
| `c_settings_2.grep_closure` | Singleton import grep = 0 | verification | Zero residual singleton imports for `settings` and `workflow_config` | `Select-String → 0 matches` | RC-1 stop/go enforced; RC-5 full migration |

### Integration Surface

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/config/workflows.py` | Delete `workflow_config = WorkflowConfig.load()` |
| ☐ | `mcp_server/managers/project_manager.py` | Remove `workflow_config` import; inject workflow config dependency |
| ☐ | `mcp_server/managers/phase_state_engine.py` | Remove `workflow_config` import; inject workflow config dependency |
| ☐ | `mcp_server/config/operation_policies.py` | Remove `workflow_config` import; inject workflow config dependency |
| ☐ | `tests/mcp_server/unit/tools/test_initialize_project_tool.py` | Rewire test away from `workflow_config` singleton import |
| ☐ | `tests/mcp_server/unit/managers/test_project_manager.py` | Rewire test away from `workflow_config` singleton import |
| ☐ | `tests/mcp_server/unit/managers/test_phase_state_engine_recovery.py` | Rewire test away from `workflow_config` singleton import |
| ☐ | `mcp_server/managers/artifact_manager.py` | Remove singleton import; accept `workspace_root: Path` param |
| ☐ | `mcp_server/tools/test_tools.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/adapters/filesystem.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/adapters/git_adapter.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/adapters/github_adapter.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/tools/discovery_tools.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/tools/code_tools.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/scaffolding/utils.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `tests/unit/tools/test_discovery_tools.py` | Inject `Settings(...)` directly |
| ☐ | `tests/integration/*/test_search_documentation_e2e.py` | Inject `Settings(...)` directly |
| ☐ | `tests/mcp_server/unit/config/test_settings.py` | `Settings.load()` → `Settings.from_env()` with mocked env |
| ☐ | `.vscode/mcp.json` (new) | Env block: `LOG_LEVEL`, `MCP_SERVER_NAME`, `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_PROJECT_NUMBER` |

### Test Zone Assignment

| Test | Zone |
|---|---|
| `test_settings.py` | Zone 1 |
| `test_discovery_tools.py` | Zone 3 (inject `Settings` directly) |

### Stop/Go — C_SETTINGS.2 (= C_SETTINGS full closure)

```powershell
Select-String "workflow_config = WorkflowConfig.load\(\)" mcp_server/ -Recurse                    # 0 matches
Select-String "from mcp_server.config.settings import settings" (Get-ChildItem -Recurse -Filter *.py).FullName  # 0 matches
Select-String "from mcp_server.config.workflows import workflow_config" (Get-ChildItem -Recurse -Filter *.py).FullName  # 0 matches
Test-Path .vscode/mcp.json                                                                          # True
pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q                                   # all pass
run_quality_gates(scope="branch")                                                                   # all green
```

---

## Cycle 2a — C_LOADER.1

**Goal:** Introduce `ConfigLoader(config_root: Path)`; create `config/schemas/` directory; migrate first 5 low-coupling schemas (GitConfig, LabelConfig, ScopeConfig, WorkflowConfig, WorkphasesConfig) to `config/schemas/`; keep their legacy public loader API temporarily for compatibility until production and test consumers are rewired in later C_LOADER cycles. Establish initial structural guard and fail-fast loader tests.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_loader_1.config_loader_class` | ConfigLoader class introduced | component | `ConfigLoader(config_root)` with `load_git_config()`, `load_label_config()`, `load_scope_config()`, `load_workflow_config()`, `load_workphases_config()` | `test_config_loader_exists` passes; `ConfigLoader(tmp_path).load_git_config()` raises `ConfigError` on missing yaml | P-4 built (partial) |
| `c_loader_1.schemas_dir` | config/schemas/ directory created | component | `mcp_server/config/schemas/__init__.py` exists | `Test-Path mcp_server/config/schemas` | RC-2 structural foundation |
| `c_loader_1.first_5_schemas_moved` | 5 schemas migrated to schemas/ | migration | GitConfig, LabelConfig, ScopeConfig, WorkflowConfig, WorkphasesConfig live under `config/schemas/`; `ConfigLoader.load_*()` resolves them there | `Test-Path` on all 5 files is `True` | P-2 staged migration |
| `c_loader_1.structural_guard` | Initial structural guard test written | test | `test_c_loader_structural.py` contains `test_config_loader_exists` plus initial loader/fail-fast guards; deletion-focused guards deferred to later C_LOADER cycles | Test file exists and C_LOADER.1 guards pass | RC-3 structural test |

### Integration Surface

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/config/loader.py` (new) | `ConfigLoader(config_root: Path)` with load methods for all 15 schemas (stubs OK for schemas not yet migrated) |
| ☐ | `mcp_server/config/schemas/` (new dir) | Create `__init__.py` |
| ☐ | `mcp_server/config/schemas/git_config.py` | Move `GitConfig`; keep existing public loader API temporarily until C_LOADER.4 |
| ☐ | `mcp_server/config/schemas/label_config.py` | Move `LabelConfig`; keep existing public loader API temporarily until C_LOADER.4 |
| ☐ | `mcp_server/config/schemas/scope_config.py` | Move `ScopeConfig`; keep existing public loader API temporarily until C_LOADER.4 |
| ☐ | `mcp_server/config/schemas/workflows.py` | Move `WorkflowConfig`; keep existing public loader API temporarily until C_LOADER.4 |
| ☐ | `mcp_server/config/schemas/workphases.py` | Move `WorkphasesConfig`; keep existing public loader API temporarily until C_LOADER.4 |
| ☐ | `tests/unit/config/test_c_loader_structural.py` | **New file — C_LOADER.1 structural tests** |

### RED Phase

```python
# tests/unit/config/test_c_loader_structural.py
def test_config_loader_exists():
    from mcp_server.config.loader import ConfigLoader
    assert callable(ConfigLoader)

def test_loader_raises_on_missing_yaml(tmp_path):
    from mcp_server.config.loader import ConfigLoader
    with pytest.raises(ConfigError):
        ConfigLoader(tmp_path / ".st3").load_git_config()

# Note: deletion-focused guards for no from_file/load/reset_instance/reset and
# no direct manager/tool schema usage are deferred to later C_LOADER cycles.
# They become executable only after production consumers (C_LOADER.3) and
# test/fixture consumers (C_LOADER.4) are rewired.
```

### Test Zone Assignment

| Test | Zone |
|---|---|
| `test_c_loader_structural.py` | Zone 1 (class introspection; no YAML) |
| `test_loader_raises_on_missing_yaml` | Zone 1 (`ConfigLoader(empty_tmp_path)` → `ConfigError`) |

### Stop/Go — C_LOADER.1

```powershell
# ConfigLoader exists
python -c "from mcp_server.config.loader import ConfigLoader; print('ok')"    # ok

# Schemas dir created
Test-Path mcp_server/config/schemas/__init__.py                                # True

# 5 schema files present in config/schemas/
Test-Path mcp_server/config/schemas/git_config.py                              # True
Test-Path mcp_server/config/schemas/label_config.py                            # True
Test-Path mcp_server/config/schemas/scope_config.py                            # True
Test-Path mcp_server/config/schemas/workflows.py                               # True
Test-Path mcp_server/config/schemas/workphases.py                              # True

# Initial C_LOADER.1 structural tests pass
pytest tests/unit/config/test_c_loader_structural.py -v                        # pass

pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q              # all pass
```

---

## Cycle 2b — C_LOADER.2

**Goal:** Migrate remaining 10 schema classes (including `EnforcementConfig` and `PhaseContractsConfig` from `managers/`) to `config/schemas/`. Delete all `from_file()`/`load()`/`ClassVar _instance`/`reset_instance()` from all 15 schemas. `test_no_from_file_on_any_config_schema` must go GREEN in this cycle.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_loader_2.remaining_schemas_moved` | 10 remaining schemas migrated | migration | ArtifactRegistryConfig, ContributorConfig, IssueConfig, MilestoneConfig, OperationPoliciesConfig, ProjectStructureConfig, QualityConfig, ScaffoldMetadataConfig, EnforcementConfig, PhaseContractsConfig in `config/schemas/` | Each file exists at new path | RC-5 complete migration |
| `c_loader_2.misplaced_schemas_extracted` | EnforcementConfig + PhaseContractsConfig extracted from managers/ | deletion | Both classes gone from `managers/`; in `config/schemas/` | `Select-String "class EnforcementConfig\|class PhaseContractsConfig" mcp_server/managers/ → 0 matches` | RC-5 SRP enforced |
| `c_loader_2.loader_methods_complete` | ConfigLoader covers all 15 schemas | component | `ConfigLoader.load_*()` methods implemented for all migrated schemas, including enforcement and phase contracts | `Select-String "def load_enforcement_config\|def load_phase_contracts_config" mcp_server/config/loader.py → matches` | P-4 built (expanded) |
| `c_loader_2.local_config_error_deleted` | Local ConfigError in scaffold_metadata_config.py deleted | deletion | `scaffold_metadata_config.py` imports `ConfigError` from `core.exceptions` | `Select-String "class ConfigError" mcp_server/config/schemas/ → 0 matches` | F13 DRY/SSOT |

### Integration Surface

| ☐ | Schema | Old location | New location | Delete |
|---|---|---|---|---|
| ☐ | `ArtifactRegistryConfig` | `config/artifact_registry_config.py` | `config/schemas/artifact_registry_config.py` | `from_file`, `ClassVar`, `reset_instance` |
| ☐ | `ContributorConfig` | `config/contributor_config.py` | `config/schemas/contributor_config.py` | `from_file`, `ClassVar`, `reset_instance` |
| ☐ | `IssueConfig` | `config/issue_config.py` | `config/schemas/issue_config.py` | `from_file`, `ClassVar`, `reset_instance` |
| ☐ | `MilestoneConfig` | `config/milestone_config.py` | `config/schemas/milestone_config.py` | `from_file`, `ClassVar`, `reset_instance` |
| ☐ | `OperationPoliciesConfig` | `config/operation_policies.py` | `config/schemas/operation_policies.py` | `from_file`, `ClassVar`, `reset_instance` |
| ☐ | `ProjectStructureConfig` | `config/project_structure.py` | `config/schemas/project_structure.py` | `from_file`, `ClassVar`, `reset_instance` |
| ☐ | `QualityConfig` | `config/quality_config.py` | `config/schemas/quality_config.py` | `load`, `ClassVar`, `reset_instance` |
| ☐ | `ScaffoldMetadataConfig` | `config/scaffold_metadata_config.py` | `config/schemas/scaffold_metadata_config.py` | `from_file`; replace local `ConfigError` → `core.exceptions.ConfigError` |
| ☐ | `EnforcementConfig` | `managers/enforcement_runner.py` | `config/schemas/enforcement_config.py` | `from_file` |
| ☐ | `PhaseContractsConfig` | `managers/phase_contract_resolver.py` | `config/schemas/phase_contracts_config.py` | `from_file` |

Complete `ConfigLoader.load_*()` stubs for all 15 schemas.

### Stop/Go — C_LOADER.2

```powershell
# All 15 schemas now exist under config/schemas/
Test-Path mcp_server/config/schemas/enforcement_config.py                       # True
Test-Path mcp_server/config/schemas/phase_contracts_config.py                  # True

# ConfigLoader covers the extracted schemas
Select-String "def load_enforcement_config|def load_phase_contracts_config" `
    mcp_server/config/loader.py                                                # matches

# EnforcementConfig + PhaseContractsConfig gone from managers/
Select-String "class EnforcementConfig|class PhaseContractsConfig" `
    (Get-ChildItem mcp_server/managers -Recurse -Filter *.py).FullName         # 0 matches

# No local ConfigError in schemas/
Select-String "class ConfigError" `
    (Get-ChildItem mcp_server/config/schemas -Recurse -Filter *.py).FullName   # 0 matches

pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q              # all pass
```

---

## Cycle 2c — C_LOADER.3

**Goal:** Rewire all 26 production consumer and composition-root files (tools/, managers/, core/, scaffolding/, scaffolders/, validation/, and `server.py`) to receive configs via constructor injection. No `from_file()` / `load()` / fallback construction remaining outside `config/`.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_loader_3.tools_rewired` | 14 tool and validator entry-point files rewired | migration | pr_tools, cycle_tools, git_tools, project_tools, label_tools, issue_tools, phase_tools, discovery_tools, git_pull_tool, git_fetch_tool, git_analysis_tools, quality_tools, validation_tools, scaffold_artifact remove direct config loads and mandatory-DI call-sites are updated | `test_no_tool_calls_from_file` passes | P-2 tools clean |
| `c_loader_3.managers_rewired` | 7 manager files rewired | migration | git_manager, phase_state_engine, artifact_manager, qa_manager, phase_contract_resolver, enforcement_runner, project_manager receive config via DI; no direct config imports remain in managers/ | `test_no_manager_imports_config_schema_directly` passes | P-2 managers clean |
| `c_loader_3.core_rewired` | policy_engine + directory_policy_resolver rewired | migration | `PolicyEngine` constructor receives configs via DI; `reload()` uses `ConfigLoader(self._config_root).load_()`; `directory_policy_resolver` mandatory param | `Select-String "\.from_file\(|reset_instance\(|\.reset\(" mcp_server/core/ → 0 matches` | RC-6 no prohibited internals |
| `c_loader_3.scaffolding_rewired` | scaffolding and scaffolder entry points rewired | migration | `scaffolding/metadata.py` receives `ScaffoldMetadataConfig` via DI; `TemplateScaffolder` registry is mandatory; production call-sites are updated in the same cycle | `Select-String "\.from_file\(" mcp_server/scaffolding/, mcp_server/scaffolders/ → 0 matches` | P-2 scaffolding clean |

### Integration Surface

**Tools and validator entry points (14 files):**

| ☐ | File | Anti-pattern | Fix |
|---|---|---|---|
| ☐ | `tools/pr_tools.py` | `GitConfig.from_file()` | Remove; use `git_manager.git_config` |
| ☐ | `tools/cycle_tools.py` ×2 | `GitConfig.from_file()` | Remove; use `git_manager.git_config` |
| ☐ | `tools/git_tools.py` ×2 | `GitConfig.from_file()` | Remove; use `git_manager.git_config` |
| ☐ | `tools/project_tools.py` | `WorkflowConfig.load()` and fallback manager construction | Remove; use injected `project_manager`, `git_manager`, and `state_engine` |
| ☐ | `tools/label_tools.py` ×3 | `LabelConfig.load()` | Remove; use `label_manager.label_config` |
| ☐ | `tools/issue_tools.py` ×9 | `@field_validator` w/ `Config.from_file()` | Remove config calls from validators (validation logic moves to C_LOADER.5 → GitHubManager) |
| ☐ | `tools/phase_tools.py` | `PhaseStateEngine(...)` built with fallback-loading dependencies | Pass injected config-backed dependencies through `ProjectManager` / composition root |
| ☐ | `tools/discovery_tools.py` | `GitManager()` and `PhaseStateEngine(...)` rely on self-loading config | Rewire to injected manager/config path |
| ☐ | `tools/git_pull_tool.py` | `GitManager()` / `PhaseStateEngine(...)` fallback construction | Rewire to DI-only manager/state-engine construction |
| ☐ | `tools/git_fetch_tool.py` | `GitManager()` fallback construction | Rewire to DI-only manager construction |
| ☐ | `tools/git_analysis_tools.py` | `GitManager()` fallback construction | Rewire to DI-only manager construction |
| ☐ | `tools/quality_tools.py` | `QAManager()` fallback construction | Inject `QAManager` backed by explicit `QualityConfig` |
| ☐ | `tools/validation_tools.py` | `QAManager()` fallback construction | Inject `QAManager` backed by explicit `QualityConfig` |
| ☐ | `tools/scaffold_artifact.py` | `ArtifactManager()` fallback construction | Inject `ArtifactManager` with explicit registry-backed dependencies |

**Managers (7 files):**

| ☐ | File | Fix |
|---|---|---|
| ☐ | `managers/git_manager.py` | Remove constructor load; receive `GitConfig` via DI |
| ☐ | `managers/phase_state_engine.py` | Make `git_config` mandatory (no fallback) |
| ☐ | `managers/artifact_manager.py` | Make `registry` mandatory (no fallback); remove direct config import path used only for fallback loading |
| ☐ | `managers/qa_manager.py` ×2 | Remove self-loading path; receive `QualityConfig` via DI |
| ☐ | `managers/phase_contract_resolver.py` | Remove config-loader path; receive `PhaseContractsConfig` and related config context via DI |
| ☐ | `managers/enforcement_runner.py` | Remove config-loader path; receive `EnforcementConfig` via DI |
| ☐ | `managers/project_manager.py` | Remove `WorkflowConfig.load()` fallback; receive `WorkflowConfig` via DI |

**Core (2 files):**

| ☐ | File | Fix |
|---|---|---|
| ☐ | `core/policy_engine.py` (constructor) | Receive `OperationPoliciesConfig`, `GitConfig` via DI; store `config_root: Path` |
| ☐ | `core/policy_engine.py` (`reload()` ×4) | Replace `reset_instance()` + `from_file()` with `ConfigLoader(self._config_root).load_*()` |
| ☐ | `core/directory_policy_resolver.py` | Make `config` mandatory (no fallback) |

**Scaffolding and scaffolders (2 files):**

| ☐ | File | Fix |
|---|---|---|
| ☐ | `scaffolding/metadata.py` | Receive `ScaffoldMetadataConfig` via DI |
| ☐ | `scaffolders/template_scaffolder.py` | Make `registry` mandatory (no fallback) |

**Composition Root (1 file):**

| ☐ | File | Fix |
|---|---|---|
| ☐ | `server.py` | Pass required configs into `QAManager` and `ArtifactManager` so production startup does not rely on fallback self-loading |

### Test Zone Assignment

All modified tests in this cycle are Zone 3 — they receive pre-built config objects or injected managers.
Tests updated in this cycle exist only because mandatory-DI rewiring changes constructor surfaces or production composition roots.
No test in this cycle may write YAML to disk or call `Config.from_file()`.

### Stop/Go — C_LOADER.3

```powershell
Select-String "\.from_file\(|reset_instance\(|\.reset\(" `
    (Get-ChildItem mcp_server/tools, mcp_server/managers, mcp_server/core, mcp_server/scaffolding, mcp_server/scaffolders, mcp_server/validation -Recurse -Filter *.py).FullName
# Expected: 0 matches

Select-String "\.from_file\(|reset_instance\(|\.reset\(" mcp_server/server.py
# Expected: 0 matches

Select-String "from mcp_server\.config" `
    (Get-ChildItem mcp_server/managers -Recurse -Filter *.py).FullName
# Expected: 0 matches

pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q              # all pass
```

---

## Cycle 2d — C_LOADER.4

**Goal:** Update all 15 non-Zone-1 test/fixture files to remove singleton calls. Rewrite 5 Zone-1 config tests to use `ConfigLoader(tmp_path)` pattern.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_loader_4.zone3_tests_clean` | 9 Zone-3 tests + 4 integration tests cleaned | migration | No `reset_instance()` / `from_file()` in these 13 files | `Select-String "reset_instance\|from_file\|LabelConfig\.reset\|LabelConfig\.load" tests/ → 0` | RC-5: no partial migration |
| `c_loader_4.fixtures_rewritten` | artifact_test_harness + workflow_fixtures rewritten | migration | Fixtures accept `ConfigLoader`-produced config objects | `Select-String "reset_instance\|from_file" tests/mcp_server/fixtures/ → 0` | RC-5: test isolation |
| `c_loader_4.zone1_rewrites` | 5 Zone-1 config tests updated | migration | `from_file()` + `reset_instance()` → `ConfigLoader(tmp_path).load_*()` | `pytest tests/mcp_server/unit/config/ -v → all pass` | P-5 zone discipline |
| `c_loader_4.self_loading_deleted_green` | Legacy public loader API deleted after final consumer rewrites | deletion | All 15 schema classes have no `from_file`, `load`, `reset_instance`, `reset`, `ClassVar _instance`; `test_no_from_file_on_any_config_schema` GREEN | `pytest tests/unit/config/test_c_loader_structural.py::test_no_from_file_on_any_config_schema -v` passes | P-2 permanent guard |

### Non-Zone-1 blast-radius files (13 test + 2 fixture = 15 total)

| ☐ | File | Zone | Fix |
|---|---|---|---|
| ☐ | `tests/mcp_server/core/test_policy_engine_config.py` | 3 | Delete `GitConfig.reset_instance()` ×2 |
| ☐ | `tests/mcp_server/core/test_policy_engine.py` | 3 | Delete `reset_instance()` ×3; inject mocks |
| ☐ | `tests/mcp_server/core/test_directory_policy_resolver.py` | 3 | Delete `reset_instance()` ×4; inject mocks |
| ☐ | `tests/mcp_server/managers/test_git_manager_config.py` | 3 | Delete `GitConfig.reset_instance()` ×2 |
| ☐ | `tests/mcp_server/integration/test_validation_policy_e2e.py` | Integration | `ConfigLoader(tmp_path)` |
| ☐ | `tests/mcp_server/integration/test_v2_smoke_all_types.py` | Integration | `ConfigLoader(tmp_path)` |
| ☐ | `tests/mcp_server/integration/test_template_missing_e2e.py` | Integration | `ConfigLoader(tmp_path)` |
| ☐ | `tests/mcp_server/integration/test_config_error_e2e.py` | Integration | `ConfigLoader(tmp_path)` bad-YAML |
| ☐ | `tests/mcp_server/integration/test_concrete_templates.py` | Integration | `ConfigLoader(tmp_path)` ×9 |
| ☐ | `tests/mcp_server/tools/test_pr_tools_config.py` | 3 | Inject `GitConfig` via `GitManager` |
| ☐ | `tests/mcp_server/tools/test_git_tools_config.py` | 3 | Inject `GitConfig` via `GitManager` |
| ☐ | `tests/mcp_server/unit/tools/test_github_extras.py` | 3 | Inject `LabelConfig` via manager |
| ☐ | `tests/mcp_server/unit/tools/test_label_tools_integration.py` | 3 | Inject via `LabelManager` |
| ☐ | `tests/mcp_server/fixtures/artifact_test_harness.py` | Fixture | Accept `ConfigLoader`-produced config |
| ☐ | `tests/mcp_server/fixtures/workflow_fixtures.py` | Fixture | `ConfigLoader(tmp_path).load_workflow_config()` |

**Zone-1 rewrites (5 files):**

| ☐ | File | Fix |
|---|---|---|
| ☐ | `tests/mcp_server/unit/config/test_artifact_registry_config.py` | `from_file()` → `ConfigLoader(tmp_path).load_artifact_registry_config()` |
| ☐ | `tests/mcp_server/unit/config/test_contributor_config.py` | Same |
| ☐ | `tests/mcp_server/unit/config/test_issue_config.py` | Same |
| ☐ | `tests/mcp_server/unit/config/test_workflow_config.py` | `WorkflowConfig.load()` → `ConfigLoader(tmp_path).load_workflow_config()` |
| ☐ | `tests/mcp_server/unit/config/test_settings.py` | `Settings.load()` → `Settings.from_env()` with mocked env |

### Stop/Go — C_LOADER.4

```powershell
Select-String "\.from_file\(|reset_instance\(|LabelConfig\.reset\(|LabelConfig\.load\(" `
    (Get-ChildItem tests/mcp_server -Recurse -Filter *.py).FullName
# Expected: 0 matches

# Structural delete guard is now fully GREEN
pytest tests/unit/config/test_c_loader_structural.py::test_no_from_file_on_any_config_schema -v  # PASSED

pytest tests/mcp_server/unit/config/ -v                                        # all pass
pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q              # all pass
```

---

## Cycle 2e — C_LOADER.5

**Goal:** Implement `GitHubManager.validate_issue_params()` (D15); wire full composition root in `server.py` (all 15 configs + all managers + PolicyEngine); achieve complete grep closure; all 4 structural tests must be GREEN.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_loader_5.github_manager_validator` | GitHubManager.validate_issue_params() implemented | component | `GitHubManager` constructor extended + `validate_issue_params()` method; 9 `@field_validator` call-sites in `issue_tools.py` removed | `Select-String "from_file\|Config\.load" mcp_server/tools/issue_tools.py → 0 matches` | D15; RC-6 |
| `c_loader_5.server_full_wiring` | Composition root complete | wiring | `server.py` calls `ConfigLoader(config_root)`, all 15 `load_*()`, all managers, `PolicyEngine`, `GitHubManager` instantiated with DI | `pytest` integration test exercises full path | P-4 fully wired; RC-2 |
| `c_loader_5.structural_tests_green` | All 4 structural tests pass | test | `test_c_loader_structural.py` — all 4 tests GREEN | `pytest tests/unit/config/test_c_loader_structural.py -v → 4 passed` | RC-3 structural guards |
| `c_loader_5.grep_closure` | Full grep closure on C_LOADER patterns | verification | Zero residual `from_file`/`load`/`reset_instance` in entire codebase outside `config/` | `Select-String → 0 matches` (3 queries) | P-1 no partial migration; RC-5 |

### Integration Surface

**GitHubManager extension:**

| ☐ | File | Change |
|---|---|---|
| ☐ | `managers/github_manager.py` | Constructor: `issue_config`, `milestone_config`, `contributor_config`, `label_config`, `scope_config`, `git_config`, `adapter` |
| ☐ | `managers/github_manager.py` | Add `validate_issue_params()` — all 6 validator bodies from `issue_tools.py @field_validator` |
| ☐ | `tools/issue_tools.py` | Remove `@field_validator` methods that called `Config.from_file()`; delegate to `github_manager.validate_issue_params()` |

**Composition root (server.py — step by step):**

| ☐ | Step | Change |
|---|---|---|
| ☐ | Step 1 | `loader = ConfigLoader(config_root)` — all 15 `load_*()` called |
| ☐ | Step 2 | `ConfigValidator().validate_startup(...)` stub (real impl in C_VALIDATOR) |
| ☐ | Step 3 | All managers instantiated with injected config |
| ☐ | Step 4 | `GitHubManager(issue_config, milestone_config, contributor_config, label_config, scope_config, git_config, adapter)` |
| ☐ | Step 5 | `PolicyEngine(policies_config, git_config, config_root=config_root)` |

### Anti-Regression Check (P0 completion — Rule P-10)

| Root cause | Verification | Expected |
|---|---|---|
| RC-2: Component built not wired | `server.py` wires ConfigLoader + all 15 configs + all managers | grep/read confirms |
| RC-3: No structural tests | `test_c_loader_structural.py` — 4 tests | 4 passed |
| RC-4: High-risk deferred | C_SETTINGS + C_LOADER done as P0 | commit order confirms |
| RC-5: Half migration | All 17 prod + 15 test files updated; grep = 0 | 3× Select-String = 0 |
| RC-6: Prohibited internals | No `from_file()` in tools/managers | structural test passes |
| RC-7: Component-boundary violations | No config schema imports in managers | structural test passes |

### Stop/Go — C_LOADER.5 (= C_LOADER full closure)

```powershell
# 1. No from_file/load/reset_instance in production code outside config/
Select-String "\.from_file\(|reset_instance\(|\.reset\(" `
    (Get-ChildItem mcp_server/tools, mcp_server/managers, mcp_server/core, mcp_server/scaffolding, mcp_server/scaffolders -Recurse -Filter *.py).FullName
# Expected: 0 matches

# 2. No config schema imports in managers
Select-String "from mcp_server\.config" `
    (Get-ChildItem mcp_server/managers -Recurse -Filter *.py).FullName
# Expected: 0 matches

# 3. No from_file/reset_instance in tests
Select-String "\.from_file\(|reset_instance\(|LabelConfig\.reset\(|LabelConfig\.load\(" `
    (Get-ChildItem tests/mcp_server -Recurse -Filter *.py).FullName
# Expected: 0 matches

# 4. All structural tests pass
pytest tests/unit/config/test_c_loader_structural.py -v
# Expected: 4 passed

# 5. Full suite
pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q
# Expected: all pass, 0 errors

run_quality_gates(scope="branch")
# Expected: all green
```

---

## Cycle 3 — C_VALIDATOR

**Priority:** P1 | **Depends on:** C_LOADER.5 | **Size:** S

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_validator.class_exists` | ConfigValidator introduced | component | `ConfigValidator.validate_startup()` in `config/validator.py` | `test_config_validator_exists` passes | D4; P-4 |
| `c_validator.label_startup_deleted` | label_startup.py deleted | deletion | File does not exist; 0 import references | `Test-Path label_startup.py → False`; `Select-String "label_startup" → 0` | D4 SRP |
| `c_validator.server_wiring` | validate_startup() wired in server.py | wiring | `server.py` calls real `validate_startup()` (not stub) | Integration test: bad cross-config raises `ConfigError` at startup | P-4 built-and-wired |

### RED Phase

```python
def test_label_startup_deleted():
    import importlib.util
    assert importlib.util.find_spec("mcp_server.config.label_startup") is None

def test_config_validator_exists():
    from mcp_server.config.validator import ConfigValidator
    assert callable(getattr(ConfigValidator, "validate_startup", None))
```

### Integration Surface

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/config/validator.py` (new) | `ConfigValidator.validate_startup(policies, workflow, structure, artifact, phase_contracts, workphases)` |
| ☐ | `mcp_server/server.py` | Replace stub with real `ConfigValidator().validate_startup(...)` call |
| ☐ | `mcp_server/config/label_startup.py` | Delete |
| ☐ | All callers of `label_startup` | Remove import |

### Stop/Go — C_VALIDATOR

```powershell
Test-Path mcp_server/config/label_startup.py                                   # False
Select-String "label_startup" (Get-ChildItem mcp_server -Recurse -Filter *.py).FullName  # 0 matches
pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q              # all pass
run_quality_gates(scope="branch")                                               # all green
```

---

## Cycle 4 — C_GITCONFIG

**Priority:** P2 | **Depends on:** C_LOADER.5 | **Size:** S

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_gitconfig.no_python_defaults` | GitConfig domain fields have no defaults | deletion | All domain-convention fields in `GitConfig`: `Field(...)` no default | `test_git_config_domain_fields_have_no_defaults` passes | D3; F4 |
| `c_gitconfig.output_dir_no_default` | ArtifactLoggingConfig.output_dir no default | deletion | `output_dir` field: `Field(...)` no default | Missing `output_dir` in YAML → `ConfigError` | F5 |

### RED Phase

```python
def test_git_config_domain_fields_have_no_defaults():
    from mcp_server.config.schemas.git_config import GitConfig
    fields_with_defaults = [
        name for name, f in GitConfig.model_fields.items()
        if f.default is not None or f.default_factory is not None
    ]
    assert fields_with_defaults == []
```

### Integration Surface

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/config/schemas/git_config.py` | All domain fields: `Field(default=...)` → `Field(...)` |
| ☐ | `mcp_server/config/schemas/quality_config.py` | `ArtifactLoggingConfig.output_dir`: remove default |

### Stop/Go — C_GITCONFIG

```powershell
pytest tests/unit/config/test_git_config.py -v                                 # all pass
pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q              # all pass
run_quality_gates(scope="branch")                                               # all green
```

---

## Cycle 5 — C_CLEANUP

**Priority:** P2 | **Depends on:** C_SETTINGS.2, C_LOADER.5 | **Size:** S

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_cleanup.template_config_moved` | template_config.py moved to utils/ | migration | `mcp_server/utils/template_config.py` exists; `config/template_config.py` gone | `Test-Path mcp_server/config/template_config.py → False` | D6; SRP |
| `c_cleanup.server_version_metadata` | server.version from importlib.metadata | migration | `Settings.version` reads `importlib.metadata.version("mcp_server")` | No hardcoded `"1.0.0"` in `settings.py` | D12 |

### Integration Surface

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/utils/template_config.py` (new) | Move `get_template_root()` from `config/template_config.py` |
| ☐ | `mcp_server/config/template_config.py` | Delete |
| ☐ | All importers | Update `config.template_config` → `utils.template_config` |
| ☐ | `mcp_server/config/schemas/settings.py` | `version = "1.0.0"` → `importlib.metadata.version("mcp_server")` |

### Stop/Go — C_CLEANUP

```powershell
Test-Path mcp_server/config/template_config.py                                 # False
Select-String "from mcp_server.config.template_config" (Get-ChildItem -Recurse -Filter *.py).FullName  # 0 matches
pytest tests/mcp_server/ --override-ini="addopts=" --tb=short -q              # all pass
run_quality_gates(scope="branch")                                               # all green
```

---

## Cycle 6 — C_SPECBUILDERS (deferred — separate issue)

**Status:** DEFERRED
**Reason:** Scope is too large for the remaining context budget on this branch. Also, the
spec-builder layer (GatePlanBuilder, ScaffoldSpecBuilder, WorkflowSpecBuilder) adds value only
after C_LOADER.5 proves the composition root is stable. Attempting it in the same issue run
risks half-integration in the most complex zone.

**What moves to follow-up issue:**
- `ConfigLoader` translators package (`config/translators/`)
- Spec output DTOs (`dtos/specs/GateExecutionPlan`, `ScaffoldSpec`, `WorkflowInitSpec`, `FileScope`, `ProjectInitOptions`)
- `QAManager`, `ArtifactManager`, `ProjectManager` receiving specs via DI
- `PhaseStateEngine` accepting `WorkflowInitSpec` (D14 P4)

**Pre-condition for follow-up:** C_LOADER.5 Stop/Go gate must be fully ticked and committed.

---

## Forbidden Pattern Reference Card

Use as anti-regression quick-check. Any of the following found in a PR after C_LOADER.5 is a blocker.

```python
Config.from_file(...)          # ❌ schema self-loading
Config.load()                  # ❌ schema self-loading
Config.reset_instance()        # ❌ singleton cleanup hack
Config.reset()                 # ❌ LabelConfig variant
x = x or Config.from_file()   # ❌ fallback constructor
settings = Settings.load()     # ❌ module-level singleton export
# ❌ in managers/ or tools/:
from mcp_server.config.schemas import SomeConfig
```

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 3.0 | 2026-03-14 | Agent | Restructure based on QA agent review: (1) C_SETTINGS split into C_SETTINGS.1 + C_SETTINGS.2; (2) C_LOADER split into C_LOADER.1–C_LOADER.5; (3) Deliverables manifest table added per cycle with stable ids, artifact, done_when, validates; (4) C_SPECBUILDERS explicitly deferred; (5) Cycle Summary updated |
| 2.0 | 2026-03-14 | Agent | Added 12 QA conditions: global planning rules, integration surfaces, structural RED tests, test zone assignments, built-and-wired proof, anti-regression checks (superseded by v3.0) |
| 1.0 | 2026-03-14 | Agent | Initial config SRP planning (superseded) |

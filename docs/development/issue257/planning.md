<!-- docs\development\issue257\planning.md -->
<!-- template=planning version=130ac5ea created=2026-03-14T00:00Z updated=2026-03-14 -->
# Config Layer SRP Refactoring — Implementation Planning

**Status:** READY  
**Version:** 1.0  
**Last Updated:** 2026-03-14

---

## Purpose

Break down the research decisions from `research_config_layer_srp.md` v1.8 into six ordered,
independently-testable implementation cycles. Each cycle has explicit stop/go criteria that must
be satisfied before the next cycle begins. Ordered for risk reduction: highest-risk, most-
entangled work first (C_SETTINGS, C_LOADER), then validation layer, cleanup, and finally the
spec-builder optimisation layer.

This planning supersedes the earlier `planning.md` (Config-First PSE Architecture, v1.0, 2026-03-12)
which covered a different refactoring scope.

## Scope

**In Scope:**
All cycles defined in the Priority Matrix of `research_config_layer_srp.md`:
`C_SETTINGS`, `C_LOADER`, `C_VALIDATOR`, `C_GITCONFIG`, `C_CLEANUP`, `C_SPECBUILDERS`.

`ARCHITECTURE_PRINCIPLES.md` §12 update (done in research v1.8).

**Out of Scope:**
Spec-builder DTO layer (`C_SPECBUILDERS`) — may be moved to a follow-up issue if scope is too
large. `.st3/` directory rename / path centralization (separate issues). `LabelManager` sync-
against-GitHub (separate cycle `C_LABELMGR`, out of scope here).

## Prerequisites

Before Cycle 1 starts:
1. `research_config_layer_srp.md` v1.8 complete — all OQ resolved
2. Branch `feature/257-reorder-workflow-phases` active, research phase → planning phase transition
3. Full test suite green: `pytest tests/mcp_server/ --override-ini="addopts=" -q` → all pass
4. `ARCHITECTURE_PRINCIPLES.md` §12 updated (done — commit `2d72deb`)

---

## Executable DoD Convention (RC-8)

Every checklist item below follows this format:
> **Criterion** — *verification command* → `expected output`

Items marked ☐ are not yet done. Items marked ☑ are complete.
A cycle DoD is not satisfied until every ☐ is ticked and the verification output is shown.

---

## Cycle 1 — C_SETTINGS

**Goal:** Delete module-level singleton exports; `Settings` becomes a pure env-var reader
called once at the composition root.

**Why first:** F12 + F3. `settings = Settings.load()` fires on every import of 14 files.
Until this is removed, every test that imports those 14 files boots on silent-default settings.
C_LOADER cannot be clean until C_SETTINGS is clean.

### RED phase

Structural tests that must fail before any production code is changed:

```python
# tests/unit/config/test_c_settings_structural.py

def test_settings_module_does_not_export_singleton():
    """module-level `settings` export must not exist after C_SETTINGS."""
    import mcp_server.config.settings as m
    assert not hasattr(m, "settings"), \
        "mcp_server.config.settings must not export a module-level 'settings' object"

def test_settings_has_from_env_not_load():
    """Settings must expose from_env(), not load()."""
    from mcp_server.config.settings import Settings
    assert hasattr(Settings, "from_env"), "Settings.from_env() must exist"
    assert not hasattr(Settings, "load"), "Settings.load() must not exist after C_SETTINGS"

def test_workflow_module_does_not_export_singleton():
    """module-level `workflow_config` export must not exist after C_SETTINGS."""
    import mcp_server.config.workflows as m
    assert not hasattr(m, "workflow_config"), \
        "mcp_server.config.workflows must not export a module-level 'workflow_config' object"

def test_log_level_env_var_renamed():
    """Settings must read LOG_LEVEL, not MCP_LOG_LEVEL."""
    import inspect, mcp_server.config.settings as m
    source = inspect.getsource(m)
    assert "MCP_LOG_LEVEL" not in source, \
        "settings.py must not reference MCP_LOG_LEVEL — rename to LOG_LEVEL complete"
```

### GREEN phase — production changes

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/config/settings.py` | Delete `settings = Settings.load()` line; replace `Settings.load()` with `Settings.from_env()`; rename `MCP_LOG_LEVEL` → `LOG_LEVEL` in `os.environ.get()` |
| ☐ | `mcp_server/config/workflows.py` | Delete `workflow_config = WorkflowConfig.load()` line |
| ☐ | `mcp_server/server.py` | Add `settings = Settings.from_env()` at composition root; pass `settings` as param to all consumers |
| ☐ | `mcp_server/managers/artifact_manager.py` | Remove `from mcp_server.config.settings import settings`; accept `workspace_root: Path` param |
| ☐ | `mcp_server/core/logging.py` | Remove singleton import; accept `log_level: str` param |
| ☐ | `mcp_server/cli.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/tools/test_tools.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/adapters/filesystem.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/adapters/git_adapter.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/adapters/github_adapter.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/tools/discovery_tools.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/tools/code_tools.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `mcp_server/scaffolding/utils.py` | Remove singleton import; accept `settings: Settings` param |
| ☐ | `.vscode/mcp.json` | Add env entries: `MCP_SERVER_NAME`, `LOG_LEVEL`, `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_PROJECT_NUMBER` |

### GREEN phase — test changes

| ☐ | File | Change |
|---|---|---|
| ☐ | `tests/mcp_server/unit/conftest.py` | Rename `setenv("MCP_LOG_LEVEL", ...)` → `setenv("LOG_LEVEL", ...)` |
| ☐ | `tests/mcp_server/unit/config/test_settings.py` | Update: `Settings.load()` → `Settings.from_env()` with mocked env |
| ☐ | `tests/unit/config/test_c_settings_structural.py` | New file — structural tests from RED phase above |
| ☐ | All 3 test files that import `settings` singleton | Update to inject `Settings(...)` directly |

### REFACTOR phase

- ☐ Run quality gates: `run_quality_gates(scope="files", files=[all changed files])`
- ☐ Verify no orphaned `import settings` remains

### Stop/Go — C_SETTINGS

- ☐ `Select-String "settings = Settings.load\(\)" mcp_server/` → **0 matches**
- ☐ `Select-String "workflow_config = WorkflowConfig.load\(\)" mcp_server/` → **0 matches**
- ☐ `Select-String "MCP_LOG_LEVEL" mcp_server/ tests/` → **0 matches**
- ☐ `Select-String "from mcp_server.config.settings import settings" (Get-ChildItem -Recurse -Filter *.py).FullName` → **0 matches**
- ☐ `pytest tests/mcp_server/ --override-ini="addopts=" -q` → **all pass, 0 errors**
- ☐ `run_quality_gates(scope="branch")` → **all gates green**

**Integration gate (RC-2):** All 14 files in DQ3 migration table have been updated. Tick each:
`artifact_manager`, `core/logging`, `cli`, `test_tools`, `adapters/filesystem`, `adapters/git_adapter`,
`adapters/github_adapter`, `tools/discovery_tools`, `tools/code_tools`, `server.py`,
`scaffolding/utils`, 3 test files.

---

## Cycle 2 — C_LOADER

**Goal:** Introduce `ConfigLoader`; move all 15 schemas to `config/schemas/`; delete `from_file()`,
`load()`, `ClassVar _instance`, `reset_instance()` from every schema class. Update all 17 production
consumer files and 15 non-Zone-1 test/fixture files.

**Why second:** Hard break. Until C_LOADER is complete, every manager that calls `Config.from_file()`
is a latent RC-2 gap. This cycle is the largest and riskiest — doing it fully in one cycle (D10: no
deprecated delegates) makes incomplete work visible as broken imports.

### RED phase

Structural tests (written first, all RED):

```python
# tests/unit/config/test_c_loader_structural.py

def test_no_from_file_on_any_config_schema():
    """Every schema class must be a pure Pydantic model — no loader methods."""
    import inspect
    import mcp_server.config.schemas as schemas_module
    for name, cls in inspect.getmembers(schemas_module, inspect.isclass):
        for forbidden in ("from_file", "load", "reset_instance"):
            assert not hasattr(cls, forbidden), (
                f"{name}.{forbidden}() must not exist — ConfigLoader is the sole loader."
            )

def test_no_manager_imports_config_class():
    """Managers must not import config classes directly."""
    import inspect, pathlib
    managers_dir = pathlib.Path("mcp_server/managers")
    for py_file in managers_dir.glob("*.py"):
        source = py_file.read_text()
        assert "from mcp_server.config" not in source, (
            f"{py_file.name} imports a config class — must receive via constructor injection."
        )

def test_no_tool_calls_from_file():
    """Tools must not call Config.from_file() directly."""
    import inspect, pathlib
    tools_dir = pathlib.Path("mcp_server/tools")
    for py_file in tools_dir.glob("*.py"):
        source = py_file.read_text()
        assert ".from_file(" not in source and ".load()" not in source, (
            f"{py_file.name} calls from_file() or load() — must use manager."
        )
```

### GREEN phase — new components

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/config/loader.py` (new) | `ConfigLoader(config_root: Path)` with `load_*()` methods for all 15 schemas |
| ☐ | `mcp_server/config/schemas/` (new dir) | Move all 13 YAML-backed schema classes + `Settings` + `EnforcementConfig` (from `enforcement_runner.py`) + `PhaseContractsConfig` (from `phase_contract_resolver.py`) |

### GREEN phase — schema deletions (15 schemas)

| ☐ | Schema class | Delete |
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
| ☐ | `ScaffoldMetadataConfig` | `from_file()`, `ClassVar _instance`, local `ConfigError` class |
| ☐ | `ScopeConfig` | `from_file()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `WorkflowConfig` | `from_file()`, `load()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `WorkphasesConfig` | `from_file()`, `ClassVar _instance`, `reset_instance()` |
| ☐ | `EnforcementConfig` | `from_file()` — move class to `config/schemas/` |
| ☐ | `PhaseContractsConfig` | `from_file()` — move class to `config/schemas/` |

### GREEN phase — production consumer updates (17 files, F16)

| ☐ | File | Anti-pattern | Fix |
|---|---|---|---|
| ☐ | `tools/pr_tools.py` | Direct load | Remove `from_file()`; use `git_manager` |
| ☐ | `tools/cycle_tools.py` | Direct load ×2 | Remove `from_file()`; use `git_manager` |
| ☐ | `tools/git_tools.py` | Direct load ×2 | Remove `from_file()`; use `git_manager` |
| ☐ | `tools/project_tools.py` | Direct load | Remove `from_file()`; use `project_manager` |
| ☐ | `tools/label_tools.py` | Direct load ×3 | Remove `load()`; use `label_manager` |
| ☐ | `tools/issue_tools.py` | `@field_validator` ×9 | Move to `GitHubManager.validate_issue_params()` (D15) |
| ☐ | `managers/git_manager.py` | Constructor load | Receive `GitConfig` via DI |
| ☐ | `managers/phase_state_engine.py` | Fallback `from_file()` | Make `git_config` mandatory param |
| ☐ | `managers/artifact_manager.py` | Fallback `from_file()` | Make `registry` mandatory param |
| ☐ | `managers/qa_manager.py` | Direct load ×2 | Receive `QualityConfig` via DI |
| ☐ | `managers/phase_contract_resolver.py` | Direct load | Receive `PhaseContractsConfig` via DI |
| ☐ | `managers/enforcement_runner.py` | Direct load | Receive `EnforcementConfig` via DI |
| ☐ | `core/policy_engine.py` (constructor) | Direct load ×2 | Receive configs via DI |
| ☐ | `core/policy_engine.py` (`reload()`) | `reset_instance()` + `from_file()` ×4 | Replace with `ConfigLoader(config_root).load_*()` |
| ☐ | `core/directory_policy_resolver.py` | Fallback `from_file()` | Make `config` mandatory param |
| ☐ | `scaffolding/metadata.py` | Direct load | Receive `ScaffoldMetadataConfig` via DI |
| ☐ | `scaffolders/template_scaffolder.py` | Fallback `from_file()` | Make `registry` mandatory param |

### GREEN phase — GitHubManager extension (D15)

| ☐ | File | Change |
|---|---|---|
| ☐ | `managers/github_manager.py` | Add constructor params: `issue_config`, `milestone_config`, `contributor_config`, `label_config`, `scope_config`, `git_config`, `adapter` |
| ☐ | `managers/github_manager.py` | Add `validate_issue_params()` method — move all 6 `@field_validator` bodies from `issue_tools.py` |
| ☐ | `tools/issue_tools.py` | `@field_validator` methods that call `Config.from_file()` → removed; Pydantic DTO retains structural checks only |

### GREEN phase — composition root wiring (server.py)

| ☐ | Step | Change |
|---|---|---|
| ☐ | Step 1 | `ConfigLoader(config_root)` instantiated; all 15 `loader.load_*()` called |
| ☐ | Step 2 | `ConfigValidator().validate_startup(...)` called (stub OK until C_VALIDATOR) |
| ☐ | Step 3 | `Settings.from_env()` called |
| ☐ | Step 4 | All managers instantiated with config objects via DI (see DQ1 sequence) |
| ☐ | Step 5 | `GitHubManager(issue_config, milestone_config, contributor_config, label_config, scope_config, git_config, adapter)` |
| ☐ | Step 6 | `PolicyEngine(policies_config, git_config)` |

### GREEN phase — test/fixture updates (F16 non-Zone-1 + Zone 1 rewrites)

**Non-Zone-1 test files (delete singleton calls):**

| ☐ | File | Fix |
|---|---|---|
| ☐ | `tests/mcp_server/core/test_policy_engine_config.py` | Delete `GitConfig.reset_instance()` ×2 |
| ☐ | `tests/mcp_server/core/test_policy_engine.py` | Delete `ArtifactRegistryConfig/OperationPoliciesConfig/ProjectStructureConfig.reset_instance()` ×3 |
| ☐ | `tests/mcp_server/core/test_directory_policy_resolver.py` | Delete `ArtifactRegistryConfig/ProjectStructureConfig.reset_instance()` ×4 |
| ☐ | `tests/mcp_server/managers/test_git_manager_config.py` | Delete `GitConfig.reset_instance()` ×2 |
| ☐ | `tests/mcp_server/integration/test_validation_policy_e2e.py` | Replace `reset_instance()` + `from_file()` with `ConfigLoader(tmp_path)` |
| ☐ | `tests/mcp_server/integration/test_v2_smoke_all_types.py` | Replace `reset_instance()` with `ConfigLoader(tmp_path)` |
| ☐ | `tests/mcp_server/integration/test_template_missing_e2e.py` | Replace `reset_instance()` + `from_file()` with `ConfigLoader(tmp_path)` |
| ☐ | `tests/mcp_server/integration/test_config_error_e2e.py` | Replace `reset_instance()` + `from_file()` with `ConfigLoader(tmp_path)` bad-YAML path |
| ☐ | `tests/mcp_server/integration/test_concrete_templates.py` | Replace `ArtifactRegistryConfig.from_file()` ×9 with `ConfigLoader(tmp_path)` |
| ☐ | `tests/mcp_server/tools/test_pr_tools_config.py` | Delete `GitConfig.reset_instance()` ×2; inject via manager |
| ☐ | `tests/mcp_server/tools/test_git_tools_config.py` | Delete `GitConfig.reset_instance()` ×2; inject via manager |
| ☐ | `tests/mcp_server/unit/tools/test_github_extras.py` | Delete `LabelConfig.reset()` ×1; inject `LabelConfig` via manager |
| ☐ | `tests/mcp_server/unit/tools/test_label_tools_integration.py` | Delete `LabelConfig.reset()` ×15; inject via `LabelManager` |
| ☐ | `tests/mcp_server/fixtures/artifact_test_harness.py` | Rewrite to accept `ConfigLoader`-produced config |
| ☐ | `tests/mcp_server/fixtures/workflow_fixtures.py` | Replace `WorkflowConfig.load()` with `ConfigLoader(tmp_path).load_workflow_config()` |

**Zone 1 tests (rewrite from `from_file()` pattern to `ConfigLoader` pattern):**

| ☐ | File | Fix |
|---|---|---|
| ☐ | `tests/mcp_server/config/test_project_structure.py` | Rewrite all `from_file()` / `reset_instance()` as `ConfigLoader(tmp_path).load_*()` |
| ☐ | `tests/mcp_server/config/test_operation_policies.py` | Same |
| ☐ | `tests/mcp_server/config/test_git_config.py` | Same |
| ☐ | `tests/mcp_server/config/test_component_registry.py` | Same |
| ☐ | `tests/mcp_server/unit/config/test_artifact_registry_config.py` | Same |
| ☐ | `tests/mcp_server/unit/config/test_contributor_config.py` | Same |
| ☐ | `tests/mcp_server/unit/config/test_issue_config.py` | Same |
| ☐ | `tests/mcp_server/unit/config/test_workflow_config.py` | Same |

### REFACTOR phase

- ☐ Run `run_quality_gates(scope="branch")` → all green
- ☐ F13: verify local `ConfigError` in `scaffold_metadata_config.py` is deleted

### Stop/Go — C_LOADER

- ☐ `Select-String "\.from_file\(|\.load\(\)|reset_instance\(" (Get-ChildItem mcp_server -Recurse -Filter *.py).FullName` → **0 matches** (excluding docstring text)
- ☐ `Select-String "from mcp_server\.config\." (Get-ChildItem mcp_server/managers -Recurse -Filter *.py).FullName` → **0 matches**
- ☐ `Select-String "from mcp_server\.config\." (Get-ChildItem mcp_server/tools -Recurse -Filter *.py).FullName` → **0 schema class imports** (only `loader.py`, `validator.py`, `settings.py` imports permitted in tools if needed)
- ☐ Structural test `test_no_from_file_on_any_config_schema()` → **PASS**
- ☐ Structural test `test_no_manager_imports_config_class()` → **PASS**
- ☐ Structural test `test_no_tool_calls_from_file()` → **PASS**
- ☐ `pytest tests/mcp_server/ --override-ini="addopts=" -q` → **all pass, 0 errors**
- ☐ `run_quality_gates(scope="branch")` → **all gates green**

**Integration gate (RC-2):** Every file in the F16 production checklist (17 files) and F16 test
checklist (15 files) above has been ticked. An entry is not done until it appears in `Select-String`
output as 0 matches.

---

## Cycle 3 — C_VALIDATOR

**Goal:** Introduce `ConfigValidator.validate_startup()`; delete `label_startup.py`.

**Depends on:** C_LOADER.

### RED phase

```python
# tests/unit/config/test_c_validator_structural.py

def test_label_startup_deleted():
    import importlib.util
    spec = importlib.util.find_spec("mcp_server.config.label_startup")
    assert spec is None, "label_startup.py must not exist after C_VALIDATOR"

def test_config_validator_exists_with_validate_startup():
    from mcp_server.config.validator import ConfigValidator
    assert callable(getattr(ConfigValidator, "validate_startup", None))
```

### GREEN phase

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/config/validator.py` (new) | `ConfigValidator` with `validate_startup(policies, workflow, structure, artifact, phase_contracts, workphases)` |
| ☐ | `mcp_server/server.py` | Replace stub with real `ConfigValidator().validate_startup(...)` call |
| ☐ | `mcp_server/config/label_startup.py` | Delete file |
| ☐ | All callers of `label_startup` | Remove import and call |

### Stop/Go — C_VALIDATOR

- ☐ `Test-Path mcp_server/config/label_startup.py` → **False**
- ☐ `Select-String "label_startup" (Get-ChildItem mcp_server -Recurse -Filter *.py).FullName` → **0 matches**
- ☐ `pytest tests/mcp_server/ --override-ini="addopts=" -q` → **all pass**
- ☐ `run_quality_gates(scope="branch")` → **all green**

---

## Cycle 4 — C_GITCONFIG

**Goal:** Remove Python defaults from `GitConfig` (domain convention fields become required);
remove `output_dir` default from `ArtifactLoggingConfig`.

**Depends on:** C_LOADER.

### RED phase

```python
def test_git_config_has_no_field_defaults():
    from mcp_server.config.schemas.git_config import GitConfig
    fields_with_defaults = [
        name for name, field in GitConfig.model_fields.items()
        if field.default is not None or field.default_factory is not None
    ]
    # Only allowed defaults: none for domain convention fields
    assert fields_with_defaults == [], (
        f"GitConfig fields must not have defaults: {fields_with_defaults}"
    )
```

### GREEN phase

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/config/schemas/git_config.py` | All domain convention fields: `Field(default=...)` → `Field(...)` (no default) |
| ☐ | `mcp_server/config/schemas/quality_config.py` | `ArtifactLoggingConfig.output_dir`: remove `default="temp/qa_logs"` |

### Stop/Go — C_GITCONFIG

- ☐ `GitConfig` unit test with missing `git.yaml` → raises `ConfigError`
- ☐ `pytest tests/mcp_server/ --override-ini="addopts=" -q` → **all pass**
- ☐ `run_quality_gates(scope="branch")` → **all green**

---

## Cycle 5 — C_CLEANUP

**Goal:** Move `template_config.py` to `utils/`; move `server.version` to
`importlib.metadata`.

**Depends on:** C_LOADER (for import-break coverage), C_SETTINGS (for `server.name` removal).

### GREEN phase

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/utils/template_config.py` (new location) | Move `get_template_root()` from `config/template_config.py` |
| ☐ | `mcp_server/config/template_config.py` | Delete |
| ☐ | All importers of `config.template_config` | Update import path to `utils.template_config` |
| ☐ | `mcp_server/config/schemas/settings.py` | Replace `version = "1.0.0"` with `importlib.metadata.version("mcp_server")` |

### Stop/Go — C_CLEANUP

- ☐ `Test-Path mcp_server/config/template_config.py` → **False**
- ☐ `Select-String "from mcp_server.config.template_config" (Get-ChildItem mcp_server -Recurse -Filter *.py).FullName` → **0 matches**
- ☐ `pytest tests/mcp_server/ --override-ini="addopts=" -q` → **all pass**
- ☐ `run_quality_gates(scope="branch")` → **all green**

---

## Cycle 6 — C_SPECBUILDERS

**Goal:** Introduce `GatePlanBuilder`, `ScaffoldSpecBuilder`, `WorkflowSpecBuilder` in
`config/translators/`; create `mcp_server/dtos/specs/`; update `PhaseStateEngine` to accept
`WorkflowInitSpec` (D14 P4 step).

**Depends on:** C_LOADER, C_VALIDATOR.

**Note:** This cycle may be moved to a follow-up issue if scope or test-suite complexity
(Zone 3 isolation — F11) is better handled separately.

### RED phase

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
```

### GREEN phase

| ☐ | File | Change |
|---|---|---|
| ☐ | `mcp_server/config/translators/gate_plan_builder.py` | `GatePlanBuilder.build(config: QualityConfig, scope: FileScope) → GateExecutionPlan` |
| ☐ | `mcp_server/config/translators/scaffold_spec_builder.py` | `ScaffoldSpecBuilder.build(registry: ArtifactRegistryConfig, context: dict) → ScaffoldSpec` |
| ☐ | `mcp_server/config/translators/workflow_spec_builder.py` | `WorkflowSpecBuilder.build(config: WorkflowConfig, params: ProjectInitOptions) → WorkflowInitSpec` |
| ☐ | `mcp_server/dtos/specs/` | Create `GateExecutionPlan`, `ScaffoldSpec`, `WorkflowInitSpec`, `FileScope`, `ProjectInitOptions` |
| ☐ | `managers/qa_manager.py` | Accept `gate_plan_builder: GatePlanBuilder` via DI; internal `.run_quality_gates()` builds plan |
| ☐ | `managers/artifact_manager.py` | Accept `scaffold_spec_builder: ScaffoldSpecBuilder` via DI |
| ☐ | `managers/project_manager.py` | Accept `workflow_spec_builder: WorkflowSpecBuilder` via DI |
| ☐ | `managers/phase_state_engine.py` | Update to accept `WorkflowInitSpec` (D14 P4) |

### Stop/Go — C_SPECBUILDERS

- ☐ Zone 2 spec-builder tests all pass with no YAML or filesystem access
- ☐ Zone 3 test for `QAManager` uses injected `GateExecutionPlan`, no `QualityConfig.load` patch
- ☐ `pytest tests/mcp_server/ --override-ini="addopts=" -q` → **all pass**
- ☐ `run_quality_gates(scope="branch")` → **all green**

---

## Summary: DoD Gate Order

```
C_SETTINGS → C_LOADER → C_VALIDATOR → C_GITCONFIG → C_CLEANUP → C_SPECBUILDERS
    P0            P0          P1            P2            P3            P4
```

No cycle may start until the previous cycle's Stop/Go gate is fully ticked with
verification output shown.

---

## Related Documentation

- **[research_config_layer_srp.md](research_config_layer_srp.md)** — v1.8, all findings and decisions
- **[ARCHITECTURE_PRINCIPLES.md](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)** — §12 updated
- **[GAP_ANALYSE_ISSUE257.md](GAP_ANALYSE_ISSUE257.md)** — RC-1 through RC-8 root causes


**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-12

---

## Purpose

Break down the design decisions from design.md (A–J) into six ordered, independently-testable implementation cycles. Each cycle has explicit stop/go criteria before the next cycle begins. Ordered for risk reduction: foundations and renames first, core abstractions second, then config layer, tool layer integration, enforcement, and deliverables tooling last.

## Scope

**In Scope:**
All components from design.md: phase_contracts.yaml, enforcement.yaml, deliverables.json, AtomicJsonWriter, PhaseContractResolver, StateRepository, EnforcementRunner, IStateReader/IStateRepository, PSE refactor, GitConfig.extract_issue_number(), tdd→implementation rename, projects.json abolishment

**Out of Scope:**
SHA-256 tamper detection for deliverables.json (issue #261); performance optimizations; multi-project support; backward-compatible migration layer

## Prerequisites

Read these first:
1. design.md APPROVED — all A–J decisions finalized
2. Branch feature/257-reorder-workflow-phases active, planning phase
3. Existing test suite green before cycle 1 starts
---

## Summary

Six implementation cycles that incrementally refactor the Phase State Engine to a Config-First architecture. Ordered by risk reduction: foundations and renames first, core abstractions second, then config layer, tool layer integration, enforcement, and finally deliverables tooling. Each cycle is independently testable and leaves the system in a deployable state.

---

## Dependencies

- Cycle 2 depends on Cycle 1: BranchState model references 'implementation' phase name
- Cycle 3 depends on Cycle 2: PhaseContractResolver receives IStateReader via constructor injection
- Cycle 4 depends on Cycles 2+3: PSE.get_state() returns BranchState; tool layer calls PCR.resolve()
- Cycle 5 depends on Cycle 4: EnforcementRunner injected at dispatch level alongside PSE
- Cycle 6 depends on Cycle 5: post-merge cleanup is an enforcement.yaml action; delete_file handler must exist

---

## TDD Cycles

### Cycle 1: Foundations & Renames (H + G + I3 + C)

**Design decisions:** H1–H4, G1–G2, I3, C2–C4

**Goal:** Eliminate dead code and rename all moving parts before new abstractions are introduced. Flag-day: `tdd` → `implementation`, `workflow_config.py` deleted, `GitConfig.extract_issue_number()` added, `projects.json` abolished.

**Tests:**
- All existing workflow tests pass with `implementation` replacing `tdd` in config and code
- `WorkflowConfig` methods (`get_workflow`, `validate_transition`, `get_first_phase`, `has_workflow`) available from `workflows.py` import path
- `GitConfig.extract_issue_number('feature/42-name')` returns `42`; returns `None` for branch without number
- PSE no longer contains `_extract_issue_from_branch()`; `GitConfig` injected instead
- `projects.json` does not exist; all references in PSE and ProjectManager removed
- No `import` from `workflow_config.py` anywhere in the codebase

**Success Criteria:**
- Full test suite green (no regressions)
- `grep` finds zero occurrences of `phase_deliverables`, `PhaseDeliverableResolver`, `HookRunner`, `workflow_config` in source
- `grep` finds zero occurrences of `projects.json` in source code (docs excluded)

**Stop/Go:** ✅ Go to Cycle 2 only if all three success criteria pass.

---

### Cycle 2: StateRepository + BranchState + AtomicJsonWriter (E + B3)

**Design decisions:** E1–E4, B3

**Goal:** Extract state I/O from PSE into a dedicated SRP component. Introduce `BranchState` (frozen Pydantic), `IStateReader`/`IStateRepository` Protocols, `FileStateRepository`, `InMemoryStateRepository`, and `AtomicJsonWriter`.

**Tests:**
- `BranchState` is a frozen Pydantic model; mutating any field raises `ValidationError`
- `FileStateRepository.load()` returns correct `BranchState` from `state.json` fixture
- `FileStateRepository.save()` writes `state.json` atomically (temp-file + rename; no partial writes)
- `InMemoryStateRepository` load/save round-trip without touching filesystem
- `AtomicJsonWriter` crash-test: simulate crash between write and rename; original file intact
- PSE receives `IStateRepository` via constructor injection; no direct file I/O in PSE
- `IStateReader`-typed consumers (`ScopeDecoder`, `PhaseContractResolver` stub) accept `IStateReader` and are rejected by Pyright when passed `IStateRepository`-only subtype

**Success Criteria:**
- PSE unit tests use `InMemoryStateRepository` (zero filesystem dependency in unit tests)
- Pyright `--strict` passes on `core/interfaces/`, state module, and PSE module
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 3 only if Pyright strict passes and InMemoryStateRepository is the default in all PSE unit tests.

---

### Cycle 3: phase_contracts.yaml loader + PhaseContractResolver (A + D + G3)

**Design decisions:** A1, A3, A5, A6, D1–D5, G3

**Goal:** Introduce the config layer: `phase_contracts.yaml` schema with Fail-Fast loader, `CheckSpec` Pydantic model, `PhaseContractResolver.resolve()`, and `PhaseConfigContext` facade.

**Tests:**
- Loader raises `ConfigError` at startup if `cycle_based: true` and `commit_type_map: {}` (decision A1)
- Loader fills missing fields with defaults: `subphases: []`, `commit_type_map: {}`, `cycle_based: false`
- `PhaseContractResolver.resolve('feature', 'implementation', cycle_number=1)` returns correct `list[CheckSpec]` from fixture YAML
- `PhaseContractResolver.resolve('docs', 'implementation', None)` returns `[]` without error (D3)
- `required=True` gates cannot be overridden by `deliverables.json` entries (resolver merge logic)
- `PhaseContractResolver` has no `import` of `StateRepository` or `pathlib.glob`
- `PhaseConfigContext` facade: tests inject one mock; resolver and workphases config both accessible
- `ConfigError` carries `file_path='.st3/config/phase_contracts.yaml'`

**Success Criteria:**
- Fail-Fast test passes: invalid `phase_contracts.yaml` raises `ConfigError` before first tool call
- Resolver returns `[]` for unknown phase (no exception)
- Pyright `--strict` passes on `PhaseContractResolver`, `CheckSpec`, `PhaseConfigContext`
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 4 only if Fail-Fast test and Pyright strict both pass.

---

### Cycle 4: Tool layer integration + PSE.get_state() + legacy param drop (J)

**Design decisions:** J1–J4

**Goal:** Wire the tool layer as composition root: `PSE.get_state(branch)` returns frozen `BranchState`, `GitManager.commit_with_scope()` receives `commit_type` as explicit parameter, legacy `phase=` parameter fully removed from `git_add_or_commit`.

**Tests:**
- `PSE.get_state('feature/42-name')` returns `BranchState` with correct fields
- `PSE.get_current_phase()` is a convenience wrapper over `get_state().current_phase`
- `GitManager.commit_with_scope(message, commit_type)` generates scoped commit message; no `PhaseContractResolver` dependency in `GitManager`
- `git_add_or_commit` tool raises `ValidationError` when called with legacy `phase=` kwarg
- Zero `phase=` kwargs remaining in `mcp_server/tools/`
- `TransitionPhaseTool` integration test: reads `cycle_number` from `PSE.get_state()`, passes it to `PCR.resolve()`, passes `commit_type` to `GitManager`

**Success Criteria:**
- `grep` finds zero `phase=` kwargs in `mcp_server/tools/` and `tests/`
- Backward-compat tests deleted (no dead test code)
- Pyright `--strict` passes on all tool files and PSE public API
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 5 only if grep check and Pyright strict both pass.

---

### Cycle 5: enforcement.yaml + EnforcementRunner (F + F3 + F5)

**Design decisions:** F1–F5

**Goal:** Introduce the enforcement layer: `enforcement.yaml` schema with plugin registration at startup, `EnforcementRunner` as separate service, `BaseTool.enforcement_event` class variable, dispatcher injection. `force_transition` catches hook exceptions as `ToolResult` warnings.

**Tests:**
- Loader raises `ConfigError` at startup if an action type has no registered handler (F2)
- `EnforcementRunner.run(event, timing, context)` calls the correct action-handler from registry
- `EnforcementRunner` unit tests: constructor-inject fake `EnforcementRegistry` with no-op handlers; zero dependency on `FileStateRepository` or PSE
- `BaseTool` subclass with `enforcement_event='transition_phase'` triggers pre/post hooks at dispatch level
- `BaseTool` subclass with `enforcement_event=None` incurs no registry lookup
- `force_transition`: `DeliverableCheckError` from hook returned as `ToolResult` warning, not raised (F5)
- `check_branch_policy` pre-hook on `create_branch` blocks creation if base restriction violated
- `commit_state_files` post-hook on `transition_phase` writes and commits `state.json`

**Success Criteria:**
- End-to-end test: `transition_phase` triggers post-hook → `state.json` committed automatically
- End-to-end test: `create_branch` with invalid base raises `ToolResult` error (not unhandled exception)
- `EnforcementRunner` unit tests have zero dependency on `FileStateRepository` or PSE
- Pyright `--strict` passes on `EnforcementRunner`, `EnforcementRegistry`, `BaseTool`
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 6 only if both end-to-end tests pass.

---

### Cycle 5.1: transition_tools refactor — shared base + enforcement hooks + DIP/DRY fixes (F6)

**Design decisions:** F6.1–F6.5

**Goal:** Bring `TransitionCycleTool` and `ForceCycleTransitionTool` in line with the C1–C5 refactoring. Three violations introduced before the refactoring are corrected in a single focused cycle: DIP (direct settings access in execute), DRY (private `_extract_issue_number()` instead of `GitConfig`), and F3 gap (`enforcement_event` missing → cycle state never auto-committed).

**Tests:**
- `TransitionCycleTool` and `ForceCycleTransitionTool` accept `workspace_root` as constructor parameter; no `settings` access inside `execute()` (DIP F6.2)
- `GitConfig.extract_issue_number()` is called for branch parsing; `_extract_issue_number()` method is absent from `transition_tools.py` (I3/DRY F6.3)
- Both tools inherit from `_BaseTransitionTool` (or equivalent shared base); `_create_engine()` is not duplicated (F6.1)
- `TransitionCycleTool.enforcement_event == "transition_cycle"` (F6.4)
- `ForceCycleTransitionTool.enforcement_event == "transition_cycle"` (F6.4)
- Dispatch E2E test: `transition_cycle` triggers post-hook → `state.json` committed automatically (F6.4, analogous to `transition_phase` test in `test_server.py`)
- `ForceCycleTransitionTool`: `DeliverableCheckError` / `ConfigError` from enforcement hook returned as `ToolResult` warning, not raised (F5/F6.5)
- `enforcement.yaml` contains `transition_cycle` post-hook with `commit_state_files` action on `.st3/state.json`
- `server.py` instantiates `TransitionCycleTool(workspace_root=...)` and `ForceCycleTransitionTool(workspace_root=...)` at composition root
- `cycle_tools.py` exists; `transition_tools.py` does not exist (F6.6 — file rename)
- All imports of `TransitionCycleTool` / `ForceCycleTransitionTool` in `server.py` and test files reference `mcp_server.tools.cycle_tools` (F6.6)

**Success Criteria:**
- `grep` finds zero occurrences of `_extract_issue_number` in `cycle_tools.py`
- `grep` finds zero occurrences of `settings.server.workspace_root` inside `execute()` in `cycle_tools.py`
- `grep` finds `enforcement_event = "transition_cycle"` in both tool classes
- `transition_tools.py` does not exist; `cycle_tools.py` exists (F6.6)
- E2E dispatch test for `transition_cycle` post-hook passes
- Pyright `--strict` passes on `cycle_tools.py`
- Full test suite green

**Stop/Go:** ✅ Go to Cycle 6 only if grep checks, E2E dispatch test, Pyright strict, and file rename all pass.

---

### Cycle 6: deliverables.json tools + state.json git-tracked (B1 + B2 + B4 + B5)

**Design decisions:** B1–B5

**Goal:** Implement `deliverables.json` tooling (`save`/`update` with completed-cycle guard), remove `state.json` from `.gitignore`, add post-merge cleanup action to `enforcement.yaml`, and add PSE startup guard for uncommitted state changes.

**Tests:**
- `save_planning_deliverables` creates `deliverables.json` with correct nested structure under issue number
- `update_planning_deliverables` raises `ValidationError` when attempting to modify a completed cycle in `cycle_history`
- `update_planning_deliverables` succeeds for open cycles
- All `deliverables.json` writes go through `AtomicJsonWriter` (no direct `open()` calls in tools)
- `state.json` not present in `.gitignore`; `git status` shows `state.json` as tracked after initialization
- Post-merge enforcement rule `delete_file` removes `deliverables.json` and `state.json` after merge
- `PSE.initialize_branch()` emits explicit warning (not exception) when `state.json` has uncommitted local changes
- After the final cycle, `.st3/state.json` is restored from temporary `tdd` compatibility back to the new `implementation` phase state before PR/merge work begins

**Success Criteria:**
- Completed-cycle guard raises `ValidationError` with message identifying the cycle id
- `AtomicJsonWriter` used for all `deliverables.json` writes (grep verification)
- Integration test: full `transition_phase` flow commits `state.json` automatically (from Cycle 5 hook)
- Pyright `--strict` passes on `save_planning_deliverables` and `update_planning_deliverables` tools
- Full test suite green
- `.st3/state.json` is back on the new `implementation` phase state before PR/merge work starts
- KPIs 1–20 in `research_config_first_pse.md` all verifiable

**Stop/Go:** ✅ KPIs 1–20 all verifiable → open PR.

---

## Risks & Mitigation

- **Risk:** Cycle 1 — `tdd` → `implementation` rename breaks active `state.json` files on other branches
  - **Mitigation:** Manual fix per decision H1. No migration code. Any active branch with `tdd` in `state.json` fixed by hand before Cycle 1 merges.
- **Risk:** Cycle 2 — PSE state refactor introduces regression in read/write path
  - **Mitigation:** `InMemoryStateRepository` used in all PSE unit tests. `FileStateRepository` tested in isolation with fixture files. `AtomicJsonWriter` crash-test validates no partial writes.
- **Risk:** Cycle 3 — `phase_contracts.yaml` schema mismatch with existing `.st3/config/` YAML files
  - **Mitigation:** Loader fills missing fields with defaults (decision A1). All existing YAML fixtures updated in Cycle 3. Fail-Fast catches schema errors at startup before any tool executes.
- **Risk:** Cycle 4 — legacy `phase=` param removal breaks undiscovered callers outside `mcp_server/tools/`
  - **Mitigation:** Full codebase `grep` pass (including tests and scripts) before removal. Pyright `--strict` catches remaining type errors at CI level.
- **Risk:** Cycle 5 — dispatch-level `EnforcementRunner` injection increases server startup complexity
  - **Mitigation:** `EnforcementRunner` independently testable via constructor injection of fake registry (zero PSE/filesystem dependency). Startup `ConfigError` for unknown action types catches config drift early.
- **Risk:** Cycle 6 — `.gitignore` removal of `state.json` affects all branches simultaneously
  - **Mitigation:** Single-line `.gitignore` removal. Active branches need `git add .st3/state.json` once. No data loss possible (file already present locally).

---

## Milestones

- After Cycle 1: codebase free of tdd, projects.json, workflow_config.py, old class names — green test suite
- After Cycle 2: PSE decoupled from filesystem; state I/O behind IStateRepository — Pyright strict passes
- After Cycle 3: phase gates config-driven; PhaseContractResolver independently testable — Fail-Fast validated
- After Cycle 4: tool layer is composition root; legacy param gone; commit scoping driven by phase_contracts.yaml
- After Cycle 5: enforcement layer live; state.json auto-committed on phase transition; branch policy enforced
- After Cycle 6: deliverables.json tooling complete; KPIs 1–20 in research_config_first_pse.md all verifiable — ready for PR

## Appendix — `save_planning_deliverables` Payload

> **Doel:** Één-op-één persisteerbare payload. Geen interpretatiestap vereist.
> Kopieer de JSON-block hieronder direct naar de `save_planning_deliverables` tool-aanroep.
>
> **Expliciete keuze over fase-entries:**
> - `design` → **inbegrepen**: design.md is APPROVED; twee structurele checks.
> - `validation` → **inbegrepen**: één check op aanwezigheid KPI-sectie na Cycle 6.
> - `documentation` → **inbegrepen**: één check op SCAFFOLD-header planning.md.
>
> **`validates`-types gebruikt:** `file_exists`, `contains_text`, `absent_text` — allemaal met verplicht `file`-veld, gevalideerd door `validate_spec` en `DeliverableChecker`.

```json
{
  "issue_number": 257,
  "planning_deliverables": {
    "tdd_cycles": {
      "total": 6,
      "cycles": [
        {
          "cycle_number": 1,
          "deliverables": [
            {
              "id": "D1.1",
              "description": "tdd → implementation: present in .st3/workflows.yaml (H rename)",
              "validates": {
                "type": "contains_text",
                "file": ".st3/workflows.yaml",
                "text": "- implementation"
              }
            },
            {
              "id": "D1.2",
              "description": "- tdd absent from .st3/workflows.yaml (H flag-day, no alias)",
              "validates": {
                "type": "absent_text",
                "file": ".st3/workflows.yaml",
                "text": "- tdd"
              }
            },
            {
              "id": "D1.3",
              "description": "GitConfig.extract_issue_number() implemented (I3 — cohesion in GitConfig)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/config/git_config.py",
                "text": "extract_issue_number"
              }
            },
            {
              "id": "D1.4",
              "description": "_extract_issue_from_branch removed from PSE (replaced by D1.3)",
              "validates": {
                "type": "absent_text",
                "file": "mcp_server/managers/phase_state_engine.py",
                "text": "_extract_issue_from_branch"
              }
            },
            {
              "id": "D1.5",
              "description": "projects.json references removed from PSE source (C abolishment)",
              "validates": {
                "type": "absent_text",
                "file": "mcp_server/managers/phase_state_engine.py",
                "text": "projects.json"
              }
            }
          ],
          "exit_criteria": "Full test suite green; absent: '- tdd' in .st3/workflows.yaml; absent: '_extract_issue_from_branch' in PSE; absent: 'projects.json' in PSE; present: 'extract_issue_number' in git_config.py"
        },
        {
          "cycle_number": 2,
          "deliverables": [
            {
              "id": "D2.1",
              "description": "state_repository.py created with BranchState + FileStateRepository + InMemoryStateRepository (E)",
              "validates": {
                "type": "file_exists",
                "file": "mcp_server/managers/state_repository.py"
              }
            },
            {
              "id": "D2.2",
              "description": "BranchState frozen=True — CQS enforced at type-system level (E)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/state_repository.py",
                "text": "frozen=True"
              }
            },
            {
              "id": "D2.3",
              "description": "InMemoryStateRepository present for test isolation (E4)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/state_repository.py",
                "text": "InMemoryStateRepository"
              }
            },
            {
              "id": "D2.4",
              "description": "AtomicJsonWriter implemented for crash-safe writes (B3)",
              "validates": {
                "type": "file_exists",
                "file": "mcp_server/utils/atomic_json_writer.py"
              }
            },
            {
              "id": "D2.5",
              "description": "IStateReader / IStateRepository Protocols created in core/interfaces/ (ISP split, E)",
              "validates": {
                "type": "file_exists",
                "file": "mcp_server/core/interfaces/__init__.py"
              }
            },
            {
              "id": "D2.6",
              "description": "PSE constructor receives IStateRepository — no direct file I/O in PSE (DIP, E)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_state_engine.py",
                "text": "IStateRepository"
              }
            }
          ],
          "exit_criteria": "PSE unit tests use InMemoryStateRepository (zero filesystem dependency in unit tests); Pyright --strict passes on core/interfaces/, state_repository.py, phase_state_engine.py; full test suite green"
        },
        {
          "cycle_number": 3,
          "deliverables": [
            {
              "id": "D3.1",
              "description": "phase_contracts.yaml config file created in .st3/config/ (A — Config-First split)",
              "validates": {
                "type": "file_exists",
                "file": ".st3/config/phase_contracts.yaml"
              }
            },
            {
              "id": "D3.2",
              "description": "PhaseContractResolver implemented — SRP, no StateRepository dependency (D)",
              "validates": {
                "type": "file_exists",
                "file": "mcp_server/managers/phase_contract_resolver.py"
              }
            },
            {
              "id": "D3.3",
              "description": "CheckSpec Pydantic model defined in phase_contract_resolver.py (D2)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_contract_resolver.py",
                "text": "class CheckSpec"
              }
            },
            {
              "id": "D3.4",
              "description": "Fail-Fast ConfigError raised for invalid phase_contracts.yaml (A1)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_contract_resolver.py",
                "text": "ConfigError"
              }
            },
            {
              "id": "D3.5",
              "description": "PhaseConfigContext facade — single injection point for tool layer (D5, G)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_contract_resolver.py",
                "text": "PhaseConfigContext"
              }
            }
          ],
          "exit_criteria": "Fail-Fast test passes: invalid phase_contracts.yaml raises ConfigError before first tool call; PhaseContractResolver.resolve() returns [] for unknown phase without exception; Pyright --strict passes on PhaseContractResolver, CheckSpec, PhaseConfigContext; full test suite green"
        },
        {
          "cycle_number": 4,
          "deliverables": [
            {
              "id": "D4.1",
              "description": "PSE.get_state(branch) → BranchState added — composition root (J1)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_state_engine.py",
                "text": "def get_state"
              }
            },
            {
              "id": "D4.2",
              "description": "GitManager.commit_with_scope() with explicit commit_type param (J3)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/git_manager.py",
                "text": "commit_with_scope"
              }
            },
            {
              "id": "D4.3",
              "description": "Legacy phase= backward-compat path removed from git_tools.py (J4 flag-day)",
              "validates": {
                "type": "absent_text",
                "file": "mcp_server/tools/git_tools.py",
                "text": "LEGACY backward-compatible path"
              }
            },
            {
              "id": "D4.4",
              "description": "tdd literal guard removed from git_tools.py (workflow_phase == 'tdd' check gone after H)",
              "validates": {
                "type": "absent_text",
                "file": "mcp_server/tools/git_tools.py",
                "text": "workflow_phase == \"tdd\""
              }
            }
          ],
          "exit_criteria": "grep finds zero 'phase=' kwargs in mcp_server/tools/; backward-compat tests deleted; Pyright --strict passes on all tool files and PSE public API; full test suite green"
        },
        {
          "cycle_number": 5,
          "deliverables": [
            {
              "id": "D5.1",
              "description": "enforcement.yaml config file created in .st3/config/ (F — enforcement rules)",
              "validates": {
                "type": "file_exists",
                "file": ".st3/config/enforcement.yaml"
              }
            },
            {
              "id": "D5.2",
              "description": "EnforcementRunner service implemented — SRP, no PSE dependency (F)",
              "validates": {
                "type": "file_exists",
                "file": "mcp_server/managers/enforcement_runner.py"
              }
            },
            {
              "id": "D5.3",
              "description": "BaseTool.enforcement_event class variable added — declarative hook registration (F, Option C)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/tools/base.py",
                "text": "enforcement_event"
              }
            },
            {
              "id": "D5.4",
              "description": "EnforcementRegistry referenced in enforcement_runner.py — plugin fail-fast at startup (F2)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/enforcement_runner.py",
                "text": "EnforcementRegistry"
              }
            }
          ],
          "exit_criteria": "End-to-end test: transition_phase triggers post-hook → state.json committed automatically; end-to-end test: create_branch with invalid base raises ToolResult error (not unhandled exception); EnforcementRunner unit tests have zero dependency on FileStateRepository or PSE; Pyright --strict passes on EnforcementRunner, EnforcementRegistry, BaseTool; full test suite green"
        },
        {
          "cycle_number": 6,
          "deliverables": [
            {
              "id": "D6.1",
              "description": "project_manager.py writes to deliverables.json — projects.json abolished (B, C)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/project_manager.py",
                "text": "deliverables.json"
              }
            },
            {
              "id": "D6.2",
              "description": "projects_file attribute removed from ProjectManager (replaced by deliverables_file)",
              "validates": {
                "type": "absent_text",
                "file": "mcp_server/managers/project_manager.py",
                "text": "projects_file"
              }
            },
            {
              "id": "D6.3",
              "description": "AtomicJsonWriter used in project_manager.py for deliverables.json writes (B3)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/project_manager.py",
                "text": "AtomicJsonWriter"
              }
            },
            {
              "id": "D6.4",
              "description": "state.json removed from .gitignore — git-tracked per branch (B5)",
              "validates": {
                "type": "absent_text",
                "file": ".gitignore",
                "text": ".st3/state.json"
              }
            },
            {
              "id": "D6.5",
              "description": "PSE.initialize_branch() emits explicit warning for uncommitted state changes (B5, Explicit-over-Implicit)",
              "validates": {
                "type": "contains_text",
                "file": "mcp_server/managers/phase_state_engine.py",
                "text": "initialize_branch"
              }
            },
            {
              "id": "D6.6",
              "description": "state.json restored from temporary tdd compatibility back to implementation phase state before PR/merge work",
              "validates": {
                "type": "contains_text",
                "file": ".st3/state.json",
                "text": "\"current_phase\": \"implementation\""
              }
            }
          ],
          "exit_criteria": "Completed-cycle guard raises ValidationError with cycle id; AtomicJsonWriter used for all deliverables.json writes (grep: no direct open() calls in project_manager.py for deliverables); integration test: full transition_phase flow commits state.json automatically; Pyright --strict passes on save/update tools and project_manager.py; full test suite green; .st3/state.json restored to implementation phase state before PR/merge work; KPIs 1–20 in research_config_first_pse.md all verifiable"
        }
      ]
    },
    "design": {
      "deliverables": [
        {
          "id": "DD.1",
          "description": "design.md status is APPROVED (scaffold workflow gate)",
          "validates": {
            "type": "contains_text",
            "file": "docs/development/issue257/design.md",
            "text": "Status:** APPROVED"
          }
        },
        {
          "id": "DD.2",
          "description": "design.md contains Key Design Decisions table for A–J",
          "validates": {
            "type": "contains_text",
            "file": "docs/development/issue257/design.md",
            "text": "### 3.1. Key Design Decisions"
          }
        }
      ]
    },
    "validation": {
      "deliverables": [
        {
          "id": "DV.1",
          "description": "KPI section present in research_config_first_pse.md — 20 KPIs verifiable after Cycle 6",
          "validates": {
            "type": "contains_text",
            "file": "docs/development/issue257/research_config_first_pse.md",
            "text": "## KPI"
          }
        }
      ]
    },
    "documentation": {
      "deliverables": [
        {
          "id": "DDOC.1",
          "description": "planning.md SCAFFOLD header present — template-tracked artifact",
          "validates": {
            "type": "contains_text",
            "file": "docs/development/issue257/planning.md",
            "text": "<!-- template=planning"
          }
        }
      ]
    }
  }
}
```

## Related Documentation
- **[design.md — Config-First PSE Architecture (decisions A–J, interfaces, component diagram)][related-1]**
- **[research_config_first_pse.md — Research source + KPIs 1–20 (frozen)][related-2]**
- **[../../coding_standards/ARCHITECTURE_PRINCIPLES.md — Binding architecture contract][related-3]**
- **[../../coding_standards/QUALITY_GATES.md — Gate 7: architectural review checklist][related-4]**

<!-- Link definitions -->

[related-1]: design.md — Config-First PSE Architecture (decisions A–J, interfaces, component diagram)
[related-2]: research_config_first_pse.md — Research source + KPIs 1–20 (frozen)
[related-3]: ../../coding_standards/ARCHITECTURE_PRINCIPLES.md — Binding architecture contract
[related-4]: ../../coding_standards/QUALITY_GATES.md — Gate 7: architectural review checklist

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |
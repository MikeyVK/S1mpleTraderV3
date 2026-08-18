<!-- docs\reference\mcp\config-loading-architecture.md -->
<!-- template=reference version=064954ea created=2026-05-07T07:49Z updated= -->
# MCP Server — Configuration Loading Architecture

**Status:** DEFINITIVE
**Version:** 1.0
**Last Updated:** 2026-05-07

**Source:** [mcp_server/config/loader.py](../../../mcp_server/config/loader.py)
**Tests:** [tests/unit/config/test_c_loader_structural.py](../../../tests/unit/config/test_c_loader_structural.py) (20 tests)

---

## Overview

The MCP server uses a layered, immutable configuration architecture. All YAML files under
the resolved `config_root` are loaded **once at startup** into typed Pydantic value objects. Those
objects are passed as constructor arguments (dependency injection) into managers and tools —
no component re-reads YAML at runtime.

```mermaid
flowchart TD
    ENV["Environment Variables<br/>Settings.from_env"] --> S[Settings]
    S --> SR["server_root = workspace_root / server_root_dir<br/>(e.g. .pgmcp/)"] 
    SR --> CR["config_root = server_root / 'config'"]
    CR --> CL[ConfigLoader]
    CL --> |"load_*_config() × 14"| VO["Typed Value Objects<br/>Pydantic BaseModel"]
    VO --> CV["ConfigValidator<br/>validate_startup()"]
    CV --> |validated| DI["Dependency Injection<br/>ServerBootstrapper._build_config_layer()"]
    DI --> MGR[Managers]
    DI --> TOOLS[Tools]
    DI --> RES[Resources]
```

---

## API Reference

### `normalize_config_root(path)`

**Module:** `mcp_server/config/loader.py`

After C3 (chain inversion), this function is a **pure `Path.resolve()` wrapper**.
Callers always supply the already-derived `server_root / "config"` path;
no heuristic detection or directory-name probing is performed.

```python
def normalize_config_root(config_root: Path | str) -> Path:
    return Path(config_root).resolve()
```

It is called by `ConfigLoader.__init__` to normalise whatever path the caller
provides, and remains available as a utility for tests and manual invocations.

---

### `resolve_config_root(preferred_root, explicit_root, required_files)`

**Module:** `mcp_server/config/loader.py`

Resolves the config root directory without
legacy fallbacks. Raises `FileNotFoundError` when no candidate satisfies `required_files`.

```mermaid
flowchart TD
    A{explicit_root set?} -- Yes --> B{"Exists + has<br/>required files?"}
    B -- Yes --> RETURN[Return explicit_root]
    B -- No --> ERR1[FileNotFoundError]
    A -- No --> C[Build candidate list]
    C --> C1[normalize preferred_root]
    C1 --> C2[normalize cwd]
    C2 --> C3["normalize loader.py/../../.."]
    C3 --> DEDUP[Deduplicate]
    DEDUP --> SCAN{"Each candidate exists<br/>and has required files?"}
    SCAN -- First match --> RETURN
    SCAN -- None --> ERR2[FileNotFoundError]
```
> **Not called in production.** `server.py` (C3 chain inversion) derives `config_root` directly:
> `server_root = workspace_root / settings.server.server_root_dir` → `config_root = server_root / "config"`.
> Available as a test/manual-invocation utility.

---

### `ConfigLoader`

**Module:** `mcp_server/config/loader.py`

Takes a `config_root: Path` in its constructor. Each `load_*` method:
1. Calls `_load_yaml(filename)` → reads YAML, returns `(dict, resolved_path)`
2. Passes the dict to `_validate_schema(SchemaClass, data, path)` → Pydantic `model_validate`

**Config File → Schema Map:**

| YAML file | `load_*` method | Schema class | Special processing |
|-----------|----------------|--------------|-------------------|
| `git.yaml` | `load_git_config` | `GitConfig` | — |
| `labels.yaml` | `load_label_config` | `LabelConfig` | — |
| `scopes.yaml` | `load_scope_config` | `ScopeConfig` | — |
| `workflows.yaml` | `load_workflow_config` | `WorkflowConfig` | — |
| `workphases.yaml` | `load_workphases_config` | `WorkphasesConfig` | — |
| `artifacts.yaml` | `load_artifact_registry_config` | `ArtifactRegistryConfig` | Custom YAML open + scans and merges files under `artifacts/` folder |
| `contributors.yaml` | `load_contributor_config` | `ContributorConfig` | — |
| `issues.yaml` | `load_issue_config` | `IssueConfig` | — |
| `milestones.yaml` | `load_milestone_config` | `MilestoneConfig` | — |
| `policies.yaml` | `load_operation_policies_config` | `OperationPoliciesConfig` | Pre-injects `operation_id` key per operation entry |
| `project_structure.yaml` | `load_project_structure_config` | `ProjectStructureConfig` | Optional `artifact_registry` param for path resolution |
| `quality.yaml` | `load_quality_config` | `QualityConfig` | — |
| `contracts.yaml` | `load_contracts_config` | `ContractsConfig` | — |
| `enforcement.yaml` | `load_enforcement_config` | `EnforcementConfig` | — |
| `scaffold_metadata.yaml` | `load_scaffold_metadata_config` | `ScaffoldMetadataConfig` | — |

**Schema module locations** (`mcp_server/config/schemas/`):

```
mcp_server/config/schemas/
├── __init__.py                      ← re-exports all schema classes
├── artifact_registry_config.py      ← ArtifactRegistryConfig
├── contracts_config.py              ← ContractsConfig
├── contributor_config.py            ← ContributorConfig
├── enforcement_config.py            ← EnforcementConfig
├── git_config.py                    ← GitConfig
├── issue_config.py                  ← IssueConfig
├── label_config.py                  ← LabelConfig, Label, LabelPattern
├── milestone_config.py              ← MilestoneConfig
├── operation_policies_config.py     ← OperationPoliciesConfig
├── project_structure_config.py      ← ProjectStructureConfig
├── quality_config.py                ← QualityConfig
├── scaffold_metadata_config.py      ← ScaffoldMetadataConfig
├── scope_config.py                  ← ScopeConfig
├── workflows.py                     ← WorkflowConfig
└── workphases.py                    ← WorkphasesConfig
```

---

### `ConfigValidator.validate_startup()`

**Module:** `mcp_server/config/validator.py`

Called after all configs are loaded, before any manager is constructed. Raises `ConfigError` on any violation.

**Degraded Startup Fallback:**
If `ConfigValidator.validate_startup()` raises a `ConfigError` (or if a `FileNotFoundError` occurs during loading), the CLI catches the exception and boots the server in a **degraded mode** (`DegradedMCPServer`) exposing only the `health_check` tool. True infrastructure errors still crash the process.

**Decoupled Template Validation:**
Template version validation is decoupled from global bootstrap and deferred to `TemplateScaffolder` execution (e.g. during `scaffold_artifact` or `validate_template` tool calls) to prevent individual template errors from blocking server startup.

```mermaid
flowchart LR
    subgraph IN["validate_startup() inputs"]
        WP[WorkphasesConfig]
        WF[WorkflowConfig]
        AR[ArtifactRegistryConfig]
        CO[ContractsConfig]
        PO[OperationPoliciesConfig]
        PS[ProjectStructureConfig]
    end
    subgraph CHECKS["Cross-config checks"]
        C1["_validate_phase_contracts()<br/>contracts.workflows phases<br/>⊆ known_phases ∩ known_workflows"]
        C2["_validate_operation_policies()<br/>policies.allowed_phases<br/>⊆ known_phases"]
        C3["_validate_project_structure()<br/>structure.allowed_artifact_types<br/>⊆ known_artifact_types"]
        C4["_validate_merge_policy_phase()<br/>merge_policy.pr_allowed_phase<br/>∈ known_phases"]
    end
    WP --> C1 & C2 & C4
    WF --> C1
    AR --> C3
    CO --> C1 & C4
    PO --> C2
    PS --> C3
```

---

### `Settings.from_env()`

**Module:** `mcp_server/config/settings.py`

Loads runtime settings from environment variables. Separate from domain configs — controls
server behaviour, not domain data.

```mermaid
classDiagram
    class Settings {
        +server: ServerSettings
        +logging: LogSettings
        +github: GitHubSettings
        +from_env() Settings
    }
    class ServerSettings {
        +name: str
        +workspace_root: str
        +server_root_dir: str
        +logs_dir: str
        +config_root: str | None
    }
    class LogSettings {
        +level: str
        +audit_log: str | None
    }
    class GitHubSettings {
        +owner: str
        +repo: str
        +token: str | None
    }
    Settings --> ServerSettings
    Settings --> LogSettings
    Settings --> GitHubSettings
```

| Environment variable | Maps to | Default |
|----------------------|---------|---------|
| `GITHUB_TOKEN` | `settings.github.token` | `None` — GitHub tools disabled |
| `PGMCP_WORKSPACE_ROOT` | `settings.server.workspace_root` | `os.getcwd()` |
| `PGMCP_SERVER_PROJECT_DIR` | `settings.server.server_root_dir` | `\".pgmcp\"` |
| `PGMCP_LOGS_DIR` | `settings.server.logs_dir` | `"logs"` |
| `PGMCP_CONFIG_ROOT` | `settings.server.config_root` | `None` — auto-resolved |
| `PGMCP_SERVER_NAME` | `settings.server.name` | `"phase-gate-mcp"` |
| `LOG_LEVEL` | `settings.logging.level` | `"INFO"` |

---

### `validate_phase_label(name, workphases)`

**Module:** `mcp_server/config/schemas/label_config.py` (added in issue #302)

Module-level free function. Validates that a `phase:*` label's suffix is a known top-level
phase from `WorkphasesConfig`. Only top-level phase keys are valid issue labels — subphases
(`red`, `green`, `contracts`, `e2e`) are commit-level granularity and rejected.

```python
def validate_phase_label(name: str, workphases: WorkphasesConfig) -> tuple[bool, str]:
    if not name.startswith("phase:"):
        return (True, "")       # non-phase labels pass through
    suffix = name.removeprefix("phase:")
    valid_phases = set(workphases.phases.keys())
    if suffix not in valid_phases:
        return (False, f"Label '{name}' references unknown workphase '{suffix}'. ...")
    return (True, "")
```

Called as **second step** after `LabelConfig.validate_label_name()` (format check) in
`AddLabelsTool` and `CreateLabelTool`.

---

## Usage Examples

### Startup sequence in `ServerBootstrapper._build_config_layer()` (Issue #285)

> **Note:** Since Issue #285 (refactor/285-separate-mcpserver-composition-root), config loading
> is the responsibility of `ServerBootstrapper` in `mcp_server/bootstrap.py`, not `MCPServer.__init__`.
> `MCPServer` now receives a fully constructed `ConfigLayer` via constructor injection.

```python
# ServerBootstrapper._build_config_layer() — mcp_server/bootstrap.py

# 1. Derive server_root and config_root
server_root = workspace_root / settings.server.server_root_dir  # e.g. .pgmcp/
config_root = server_root / "config"  # always derived; resolve_config_root() NOT called

# 2. Load all configs (immutable from this point) — returns ConfigLayer dataclass
config_loader = ConfigLoader(config_root=config_root)
workphases_config = config_loader.load_workphases_config()
label_config = config_loader.load_label_config()
# ... (14+ load_* calls total)

# 3. Cross-config validation (raises ConfigError on violation)
ConfigValidator().validate_startup(
    policies=operation_policies_config,
    workflow=workflow_config,
    structure=project_structure_config,
    artifact=artifact_registry,
    contracts=contracts_config,
    workphases=workphases_config,
)

# 4. Returns ConfigLayer @dataclass(frozen=True) — injected into MCPServer via constructor
return ConfigLayer(
    workphases=workphases_config,
    labels=label_config,
    # ... all 14 config VOs
)
```

Tools receive config VOs through the ManagerGraph and the tool-builder step:
```python
# ServerBootstrapper._build_tools() — mcp_server/bootstrap.py
AddLabelsTool(
    manager=graph.github_manager,
    label_config=configs.labels,
    workphases_config=configs.workphases,   # added in issue #302
)
```

### Test Pattern 1 — Real config (integration tests)

```python
from mcp_server.config.loader import ConfigLoader
from pathlib import Path

workphases_config = ConfigLoader(resolve_config_root(Path.cwd())).load_workphases_config()
```

### Test Pattern 2 — Inline YAML via `tmp_path` (unit tests)

```python
def _load_label_config(tmp_path: Path, yaml_content: str) -> LabelConfig:
    yaml_file = tmp_path / "labels.yaml"
    yaml_file.write_text(yaml_content)
    return ConfigLoader(tmp_path).load_label_config(config_path=yaml_file)
```

The `config_path` override bypasses the default `config_root / filename` lookup —
the primary isolation mechanism for unit tests with custom minimal configs.

### Test Pattern 3 — Shared fixtures (`tests/mcp_server/fixtures/workflow_fixtures.py`)

```python
# Registered globally via tests/conftest.py
@pytest.fixture
def contracts_config() -> ContractsConfig:
    return ConfigLoader(resolve_config_root(Path.cwd())).load_contracts_config()
```

Available fixtures: `workflow_config`, `contracts_config`, `workflow_phases`,
`feature_phases`, `bug_phases`, `hotfix_phases`.

---

## Dependency Injection Map

Full config VO → consumer map (managers and tools):

| Config VO | Direct consumers |
|-----------|-----------------|
| `GitConfig` | `GitManager`, `GitHubManager`, `ListPRsTool`, `MergePRTool`, `EnforcementRunner` |
| `WorkphasesConfig` | `GitManager`, `ProjectManager`, `PhaseStateEngine`, `ScopeDecoder`, `CommitPhaseDetector`, `GetWorkContextTool`, `AddLabelsTool`*, `CreateLabelTool`* |
| `WorkflowConfig` | `ConfigValidator` (startup only) |
| `LabelConfig` | `GitHubManager`, `AddLabelsTool`, `CreateLabelTool`, `DeleteLabelTool`, `ListLabelsTool`, `RemoveLabelsTool` |
| `IssueConfig` | `GitHubManager`, `CreateIssueTool` |
| `ScopeConfig` | `GitHubManager` |
| `MilestoneConfig` | `GitHubManager` |
| `ContributorConfig` | `GitHubManager` |
| `ContractsConfig` | `ProjectManager`, `PhaseContractResolver`, `PhaseStateEngine`, `ConfigValidator`, `MergeReadinessContext`, `CreateIssueTool` |
| `ArtifactRegistryConfig` | `ArtifactManager`, `ConfigValidator` |
| `ProjectStructureConfig` | `ArtifactManager`, `ConfigValidator` |
| `OperationPoliciesConfig` | `ConfigValidator` (startup only) |
| `EnforcementConfig` | `EnforcementRunner` |
| `QualityConfig` | `QAManager` |

\* Added in issue #302

---

## End-to-End Flow

```mermaid
flowchart TD
    subgraph DISK["config_root — YAML files"]
        Y1[git.yaml]
        Y2[labels.yaml]
        Y3[workphases.yaml]
        Y4[workflows.yaml]
        Y5[contracts.yaml]
        Y6[policies.yaml]
        Y7["artifacts.yaml + artifacts/*.yaml"]
        Y8["issues / milestones<br/>scopes / contributors"]
        Y9["enforcement / quality<br/>project_structure"]
    end
    subgraph LOAD["ConfigLoader — loaded once at startup"]
        L1[GitConfig]
        L2[LabelConfig]
        L3[WorkphasesConfig]
        L4[WorkflowConfig]
        L5[ContractsConfig]
        L6[OperationPoliciesConfig]
        L7["ArtifactRegistryConfig (merged)"]
        L8["IssueConfig / MilestoneConfig<br/>ScopeConfig / ContributorConfig"]
        L9["EnforcementConfig / QualityConfig<br/>ProjectStructureConfig"]
    end
    subgraph VALIDATE["ConfigValidator.validate_startup()"]
        V1[contracts ↔ workphases]
        V2[policies ↔ workphases]
        V3[structure ↔ artifacts]
        V4[merge_policy ↔ workphases]
    end
    subgraph MANAGERS["Managers — DI"]
        M1[GitManager]
        M2[GitHubManager]
        M3["ProjectManager<br/>PhaseStateEngine<br/>PhaseContractResolver"]
        M4[ArtifactManager]
        M5["QAManager<br/>EnforcementRunner"]
    end
    subgraph TOOLS["Tools — DI"]
        T1["Git tools"]
        T2["Label tools<br/>(+workphases_config #302)"]
        T3[Issue tools]
        T4[Phase tools]
        T5[Scaffold tools]
    end
    Y1 --> L1
    Y2 --> L2
    Y3 --> L3
    Y4 --> L4
    Y5 --> L5
    Y6 --> L6
    Y7 --> L7
    Y8 --> L8
    Y9 --> L9
    L3 & L4 & L5 & L6 & L7 & L9 --> VALIDATE
    L1 & L3 --> M1
    L1 & L2 & L8 --> M2
    L3 & L5 --> M3
    L7 & L9 --> M4
    L9 --> M5
    M1 --> T1 & T4
    M2 & L2 & L3 --> T2
    M2 & L8 --> T3
    M3 --> T4
    M4 --> T5
```

---

## Design Invariants

1. **Immutable after load:** All config value objects use `frozen=True` or `ConfigDict(frozen=True)`. No mutation at runtime.
2. **Single load point:** `ConfigLoader` is constructed once in `ServerBootstrapper._build_config_layer()` (issue #285). No lazy loading, no singleton registry.
3. **No config re-reads at runtime:** Tools and managers hold references to config VOs. Exception: `CommitPhaseDetector` constructs its own `ConfigLoader` lazily when called outside server context.
4. **`config_path` override for tests:** Every `load_*` method accepts `config_path: Path | None` to bypass the default `config_root / filename` lookup. Primary isolation mechanism for unit tests.
5. **Cross-config validation at startup only:** `ConfigValidator.validate_startup()` enforces referential integrity once. No runtime re-validation.
6. **Use-time semantic validation for `phase:*`:** `validate_phase_label()` enforces workphase-backed semantics at the point of label assignment/creation (not at startup). Injected via `workphases_config` constructor parameter in label tools.

---

## Adding a Configured Workflow

A new workflow normally extends the existing issue, workflow, contract, Git, and
enforcement configuration files; it does not add a new config loader or schema.
Follow [Adding a First-Class Workflow](workflow-extension-guide.md) for the
complete dependency and verification procedure.

---

## Adding a New Config File

1. Create schema in `mcp_server/config/schemas/new_thing.py` (Pydantic `BaseModel`)
2. Export from `mcp_server/config/schemas/__init__.py`
3. Add `load_new_thing_config()` to `ConfigLoader`
4. Load in `ServerBootstrapper._build_config_layer()` (in `mcp_server/bootstrap.py`) before `ConfigValidator.validate_startup()`; add the field to the `ConfigLayer` dataclass
5. If the new config references workphases or artifact types, add a cross-validation check to `ConfigValidator`
7. Add shared fixture in `tests/mcp_server/fixtures/` if widely used across tests

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-07-16 | Agent | Updated for modular YAML configuration loading (split configurations under artifacts/ directory). |
| 1.0 | 2026-05-07 | Agent | Initial draft |

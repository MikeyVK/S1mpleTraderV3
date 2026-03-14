<!-- docs\development\issue257\research_config_layer_srp.md -->
<!-- template=research version=8b7bb3ab created=2026-03-14T06:31Z updated=2026-03-14 -->
# Config Layer SRP Violations: Missing Loader, Validator and Schema Separation

**Status:** DRAFT
**Version:** 1.1
**Last Updated:** 2026-03-14

---

## Purpose

Document the architectural defects in `mcp_server/config/` discovered during issue #257 research.
Establishes the prioritized list of cycles for the next implementation run: missing `ConfigLoader`,
missing `ConfigValidator`, the `mcp_config.yaml` / `mcp.json` layering problem, DRY violations
between Python defaults and YAML, misplaced non-schema files, and the config-vs-constants boundary.

## Scope

**In Scope:**
`mcp_server/config/*.py` analysis; `.st3/*.yaml` completeness check; comparison against
`backend/config/` reference pattern; identification of the `mcp.json` / `mcp_config.yaml` layering
conflict; config vs constants boundary analysis; fail-fast vs graceful degradation boundary;
`label_startup.py` SRP analysis; priority ordering for next implementation cycles.

**Out of Scope:**
Implementation of the fixes; template engine config (issue #72); `sections.yaml` architecture
(issue #258); `.st3/` directory rename / path centralization (separate C8/C9 cycles).

## Prerequisites

Read these first:
1. `docs/development/issue257/GAP_ANALYSE_ISSUE257.md` — 10/20 KPIs red, RC-1 through RC-8
2. `backend/config/__init__.py` — reference architecture: ConfigLoader / ConfigValidator / ConfigTranslator
3. `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` — sections 2 (DRY+SSOT), 3 (Config-First), 4 (Fail-Fast)
4. `docs/system/addendums/Addendum_ 3.8 Configuratie en Vertaal Filosofie.md` — three-layer config philosophy
5. `.vscode/mcp.json` — the authoritative MCP server configuration file

---

## Problem Statement

`mcp_server/config/` contains 15 config classes that each implement their own YAML loader, their
own error handling, and their own hardcoded `.st3/` path. There is no central `ConfigLoader`, no
`ConfigValidator`, and the `Settings` class references a `mcp_config.yaml` that does not exist —
and should not exist. Every class is simultaneously a Pydantic schema and a loader, a direct SRP
violation. Python defaults silently mirror YAML values (DRY violation). There is an undetected
value conflict in `quality_config.py`. Two non-schema files are misplaced in `config/`. Two
YAML-backed Pydantic schemas live outside `config/` entirely. The current state is the inverse of
the `ARCHITECTURE_PRINCIPLES` the project enforces on itself.

## Research Goals

- Document the full deviation from the `backend/config/` ConfigLoader/ConfigValidator reference pattern
- Establish that `mcp_config.yaml` must not be created — `mcp.json` is the MCP-standard config source
- Define the loader's responsibility for fail-fast vs graceful degradation (neither may be silent)
- Identify all Python defaults that silently duplicate YAML values (DRY violations)
- Establish the config vs constants boundary for `GitConfig` and `Settings`
- Identify misplaced files in `config/` and schemas that live outside `config/`
- Resolve the `label_startup.py` SRP question
- Produce a prioritized cycle list for the next implementation run

---

## Background

The MCP server grew inside the S1mpleTrader V3 workspace, which already had a clean three-layer
config system in `backend/config/` (`ConfigLoader` → `ConfigValidator` → `ConfigTranslator`). During
MCP server development, config classes were added incrementally (Issue #55, #138, etc.) without
adopting the central loader layer. Each class implemented its own `from_file()` or `load()` method.
`settings.py` was added referencing a `mcp_config.yaml` as config source — but that YAML file was
never created. The server has always booted on hardcoded Python defaults, silently, without any
startup error or warning.

---

## Findings

### F1 — No Central ConfigLoader (SRP Violation)

Each of the 15 config classes implements its own YAML loading logic via `from_file()` or `load()`.
Each class hardcodes its own `.st3/xxx.yaml` path. Error handling is inconsistent across classes
(`FileNotFoundError` vs `ConfigError` vs `ValueError`). There is no composition root where all
configs are loaded and cross-validated at startup.

This is the inverse of the backend reference pattern:

```
# Backend (reference):              # mcp_server/config/ (current):
ConfigLoader                        GitConfig.from_file()
  .load_git_config()       vs       LabelConfig.load()
  .load_label_config()              WorkflowConfig.from_file()
  .load_workflow_config()           QualityConfig.from_file()
  # config_root injected once       # .st3/ hardcoded 15x
```

**Impact:** Adding a new YAML file requires: (a) new Pydantic schema, (b) new loader method baked
into the schema class itself, (c) hardcoded path in that class, (d) inconsistent error type choice.
There is no single place to audit which YAML files are loaded at startup.

**Complete mapping — Python schema class to YAML file:**

| Python file | YAML file | Status |
|---|---|---|
| `artifact_registry_config.py` | `.st3/artifacts.yaml` | OK — YAML-backed |
| `contributor_config.py` | `.st3/contributors.yaml` | OK — YAML-backed |
| `git_config.py` | `.st3/git.yaml` | WARN — DRY violation (see F4) |
| `issue_config.py` | `.st3/issues.yaml` | OK — YAML-backed |
| `label_config.py` | `.st3/labels.yaml` | OK — YAML-backed |
| `milestone_config.py` | `.st3/milestones.yaml` | OK — YAML-backed |
| `operation_policies.py` | `.st3/policies.yaml` | OK — YAML-backed |
| `project_structure.py` | `.st3/project_structure.yaml` | OK — YAML-backed |
| `quality_config.py` | `.st3/quality.yaml` | WARN — value conflict (see F5) |
| `scaffold_metadata_config.py` | `.st3/scaffold_metadata.yaml` | OK — YAML-backed |
| `scope_config.py` | `.st3/scopes.yaml` | OK — YAML-backed |
| `workflows.py` | `.st3/workflows.yaml` | OK — YAML-backed |
| `workphases_config.py` | `.st3/workphases.yaml` | OK — YAML-backed |
| `settings.py` | `mcp_config.yaml` | ERROR — YAML must not exist; source is `mcp.json` (see F3) |
| `template_config.py` | — | ERROR — not a config schema (see F6) |
| `label_startup.py` | — | ERROR — not a config schema (see F8) |

Schemas that live outside `config/` and must be relocated:

| Python file | YAML file |
|---|---|
| `managers/enforcement_runner.py` | `.st3/config/enforcement.yaml` |
| `managers/phase_contract_resolver.py` | `.st3/config/phase_contracts.yaml` |

---

### F2 — No ConfigValidator (Cross-Config Validation Missing at Startup)

`ARCHITECTURE_PRINCIPLES.md` section 4 requires:

> *"Config loaders raise ConfigError for logically inconsistent combinations — detected at startup,
> not at runtime."*

There is no central validator. Cross-config consistency checks exist but are scattered inside
individual loader methods:

- `operation_policies.py` validates `allowed_phases` against `workflows.yaml` internally
- `project_structure.py` validates `allowed_artifact_types` against `artifacts.yaml` internally

These checks are invisible as startup validation, produce no structured error report, and cannot be
tested as a unified startup contract.

#### Four validation layers

Not all consistency checks belong in a single `ConfigValidator`. The correct allocation:

| Layer | Owner | Responsibility |
|---|---|---|
| 1 — Structural | Pydantic at `ConfigLoader.load_*()` | "Can this YAML fit this schema?" — type errors, required fields |
| 2 — Intra-config semantic | Pydantic `model_validator` on schema class | "Are values within ONE file consistent?" |
| 3 — Inter-config referential | `ConfigValidator` | "Do references from config A exist in config B?" |
| 4 — Environment | Manager / `EnvironmentChecker` | "Does config match actual system state?" |

Layer 1 and 2 fire synchronously on schema construction inside `ConfigLoader.load_*()`. Layer 3
fires once at startup via `ConfigValidator.validate_startup()`. Layer 4 fires when a manager
begins an operation that requires the environment to be ready (e.g. branch must exist in remote).

**Layer 3 — `ConfigValidator` scope (inter-config referential integrity only):**

| Constraint | Source file | Target file |
|---|---|---|
| `allowed_phases` must be subset of defined workflow phases | `policies.yaml` | `workflows.yaml` |
| `allowed_artifact_types` must be subset of defined types | `project_structure.yaml` | `artifacts.yaml` |
| `phase_contracts` phase names must exist in workflow phases | `phase_contracts.yaml` | `workphases.yaml` |

**Placed in Layer 2 (`model_validator` on schema), NOT in `ConfigValidator`):**

| Constraint | Reason |
|---|---|
| `active_gates` keys must exist in `gates` map | Both live in `quality.yaml` — single-file check |

**Placed in Layer 4 (manager / `EnvironmentChecker`), NOT in `ConfigValidator`:**

| Constraint | Reason |
|---|---|
| enforcement rule `paths` must exist on filesystem | Requires filesystem access; not a config-to-config reference |

---

### F3 — mcp_config.yaml Must Not Exist: mcp.json is the MCP-Standard Config Source

`settings.py` references `mcp_config.yaml` as an optional config file. This file does not exist.
The server silently falls back to hardcoded Python defaults on every boot:

```python
if path.exists():                              # False — file never exists
    config_data = yaml.safe_load(f) or {}
# No error. No warning. Continues with Python defaults.
```

`test_default_settings()` constructs `Settings()` without any YAML and asserts the hardcoded
values — a test that proves the silent fallback "works", which is the wrong guarantee.

**The correct solution is not to create `mcp_config.yaml`.** It is to recognize that
`.vscode/mcp.json` already is the authoritative MCP server configuration, per the MCP
specification. All MCP-compatible tools (VS Code, Cursor, Claude Desktop, etc.) use this file as
the single installation and configuration mechanism. Its current content:

```json
{
  "servers": {
    "st3-workflow": {
      "type": "stdio",
      "command": "python",
      "args": ["-m", "mcp_server.core.proxy"],
      "env": {
        "GITHUB_TOKEN": "${env:GITHUB_TOKEN}"
      }
    }
  }
}
```

Adding `mcp_config.yaml` introduces a three-layer architecture where exactly one layer must exist:

| Layer | Source | Verdict |
|---|---|---|
| Layer 1 — authoritative | `.vscode/mcp.json` — MCP standard, IDE-managed | Must remain |
| Layer 2 — redundant | `mcp_config.yaml` — custom YAML, no schema contract | Must not be created |
| Layer 3 — dangerous | Python defaults in `settings.py` | Must be removed |

**Decision:** `Settings` reads exclusively from environment variables injected via `mcp.json`.
The values currently hardcoded in `settings.py` (`owner`, `repo`, `project_number`, `log_level`)
are moved to explicit `env` entries in `mcp.json`. `settings.py` becomes a pure env-var reader.
Missing required env vars raise `ConfigError` at startup — no silent fallback.

---

### F4 — Python Defaults Mirror YAML Exactly (DRY Violation, Dead Code)

`GitConfig` carries `Field(default=["feature", "bug", "fix", "refactor", "docs", "hotfix", "epic"])`.
`.st3/git.yaml` defines the identical list under `branch_types`. All 5 consumers in the codebase
call `GitConfig.from_file()` — `GitConfig()` is never constructed directly. The Python defaults
are dead code that creates a false appearance of graceful degradation: if `.st3/git.yaml` is
absent the `GitConfig` object can be constructed from defaults, but the rest of the system will
fail immediately because branch validation, commit validation, and PR creation all depend on the
loaded config behaving as the YAML specifies.

The same pattern repeats across all `Field(default=...)` entries in `GitConfig`:
`commit_types`, `protected_branches`, `tdd_phases`, `commit_prefix_map`,
`branch_name_pattern`, `default_base_branch`, `issue_title_max_length`.

**Correct approach:** Domain conventions use `Field(...)` with no default. The `ConfigLoader`
raises `ConfigError` with the file path if the YAML is absent. Defaults are explicitly deleted
from the schema. See F9 for the full fail-fast vs graceful degradation boundary.

---

### F5 — Value Conflict Between quality_config.py and quality.yaml

`ArtifactLoggingConfig` in `quality_config.py` hardcodes:

```python
output_dir: str = Field(default="temp/qa_logs")
```

`.st3/quality.yaml` defines:

```yaml
artifact_logging:
  output_dir: "mcp_server/logs/qa_logs"
```

Two different paths. The YAML wins at runtime because the file exists. But if `artifact_logging`
is ever omitted from `quality.yaml`, the server silently switches to the wrong directory for QA
log output. No error. No warning. This is the kind of silent configuration drift that a
`ConfigValidator` must catch at startup: a required section absent from an existing YAML file
is not a valid "use the default" situation.

---

### F6 — Non-Schema Files Misplaced in config/

`config/` is the home of Pydantic schemas and their loaders. Two files in this directory do not
fulfill that role:

**`template_config.py`** contains one function, `get_template_root()`. It checks an env var, probes
two filesystem locations, and raises `FileNotFoundError` if neither exists. This is a path-resolution
utility, not a config schema. No Pydantic, no YAML, no loader pattern. Belongs in `utils/`.

**`label_startup.py`** is a startup validation function. See F8 for why it is not a config schema
and where its responsibilities belong.

---

### F7 — Config vs Constants: The Boundary

Several values carry the structural form of configuration (Pydantic fields, YAML-backed) but behave
as compile-time conventions: they are never intended to be changed by a user or operator without
developer knowledge of the codebase.

**Rule:** A value is a *constant* if changing it requires knowledge of the codebase internals.
A value is *configuration* if a user or operator can safely change it without understanding the
codebase. A value is *deployment config* if it identifies the specific running instance.

| Value | Current form | Verdict | Correct form |
|---|---|---|---|
| `branch_types` | `GitConfig` field with Python default | Domain convention — fail-fast from YAML | Required field, no default |
| `commit_types` | `GitConfig` field with Python default | Domain convention — fail-fast from YAML | Required field, no default |
| `protected_branches` | `GitConfig` field with Python default | Domain convention — fail-fast from YAML | Required field, no default |
| `branch_name_pattern` | `GitConfig` field with Python default | Domain convention — fail-fast from YAML | Required field, no default |
| `server.name` (`"st3-workflow"`) | `ServerSettings` Python default | Deployment identity — comes from `mcp.json`key | env var `MCP_SERVER_NAME` |
| `server.version` (`"1.0.0"`) | `ServerSettings` Python default | Build artifact — belongs in `pyproject.toml` | `importlib.metadata.version()` |
| `github.owner` (`"MikeyVK"`) | `GitHubSettings` Python default | Deployment config — comes from `mcp.json` | env var `GITHUB_OWNER` |
| `github.repo` (`"S1mpleTraderV3"`) | `GitHubSettings` Python default | Deployment config — comes from `mcp.json` | env var `GITHUB_REPO` |
| `github.project_number` (`1`) | `GitHubSettings` Python default | Deployment config — comes from `mcp.json` | env var `GITHUB_PROJECT_NUMBER` |
| `logging.level` (`"INFO"`) | `LogSettings` Python default | Operational parameter — graceful default `INFO` acceptable, but must log warning if absent | `mcp.json` env var, default `INFO` with warning |

---

### F8 — label_startup.py Conflates Two Distinct Responsibilities (SRP Violation)

`label_startup.py` performs two tasks that each have a distinct correct owner:

**Responsibility A — Validate that `labels.yaml` is structurally sound at startup.**
This is a config validation task. Its correct owner is `ConfigValidator.validate_startup()`. When
that class exists, it loads all YAML configs and raises a structured `ConfigError` on the first
inconsistency. `label_startup.py`'s load-and-catch logic becomes fully redundant.

**Responsibility B — Validate that `labels.yaml` matches the live GitHub label state.**
This is a runtime integration check against the GitHub API. It answers the question "is this
workspace in sync with GitHub?" — not "is the config file structurally valid?". This responsibility
belongs to `LabelManager` or a dedicated `LabelSyncService`. It must not be folded into
`ConfigValidator` — that would couple startup config validation to a network call.

`label_startup.py` exists because both owners are absent. It is a structural gap-filler, not a
component. When `ConfigValidator` and `LabelManager` both exist, `label_startup.py` is deleted.

Additionally: the current soft-fail behavior (warning on missing file, error log on invalid config,
no startup block) violates Fail-Fast. A missing `labels.yaml` is a `ConfigError`, not a warning.

---

### F9 — Loader Responsibilities: Fail-Fast vs Graceful Degradation

Neither outcome is acceptable when it is silent. The `ConfigLoader` owns both outcomes and must
make them explicit at startup. The boundary:

| Situation | Required behavior | Example |
|---|---|---|
| YAML file missing, field has no safe default | `ConfigError` at startup with file path | `git.yaml` absent → cannot validate branch types |
| YAML file missing, field has a safe operational default | Log `WARNING` with value used, continue | `logging.level` → default `INFO`, warn |
| YAML file present, required field absent | `ConfigError` with field name and file path | Pydantic `Field(...)` enforces this |
| YAML file present, optional field absent | Use schema default, log `DEBUG` | Documented optional fields only |
| Cross-config constraint violated | `ConfigError` in `ConfigValidator` | `allowed_phases` not in `workflows.yaml` |
| Required env var missing | `ConfigError` at startup | `GITHUB_TOKEN` absent |
| Required env var present but empty | `ConfigError` at startup | `GITHUB_TOKEN=""` |

The `ConfigLoader` is the single place where "file not found" becomes either a `ConfigError` or
a logged warning with a stated default. Individual schema classes never make this decision.

---

### F11 — ConfigTranslator Role: Three Domain-Specific Spec-Builders

`ConfigTranslator` is a concept in the backend reference pattern (see `docs/architecture/`) but it
does not exist as a single class in the MCP server. The correct implementation is not a single
god-class translator but three domain-specific spec-builders in `config/translators/`.

#### Current SRP violations that motivate this

`QAManager` currently loads `QualityConfig` internally AND determines which gates to execute based
on that config — two distinct responsibilities. The same pattern appears in `ArtifactManager`
(loads `ArtifactRegistryConfig` AND resolves template paths) and `ProjectManager` (imports
`workflow_config` as a singleton AND translates it to a `ProjectPlan`).

Each manager is a config reader and a config interpreter rolled into one. The spec-builder layer
severs this coupling: managers receive a typed spec; they do not know how configs are structured.

#### The three spec-builders

```python
# config/translators/gate_plan_builder.py
class GatePlanBuilder:
    """Translates QualityConfig + FileScope → GateExecutionPlan.

    Knows: which gates are active, how scope maps to file sets, gate command assembly.
    Does not know: how config was loaded, what workspace_root is.
    """
    def build(self, config: QualityConfig, scope: FileScope) -> GateExecutionPlan: ...


# config/translators/scaffold_spec_builder.py
class ScaffoldSpecBuilder:
    """Translates ArtifactRegistryConfig + context dict → ScaffoldSpec.

    Knows: template path resolution, context validation, output path determination.
    Does not know: how config was loaded, Jinja2 rendering.
    """
    def build(self, registry: ArtifactRegistryConfig, context: dict) -> ScaffoldSpec: ...


# config/translators/workflow_spec_builder.py
class WorkflowSpecBuilder:
    """Translates WorkflowConfig + ProjectInitOptions → WorkflowInitSpec.

    Knows: phase ordering, required deliverables per phase, cycle mapping.
    Does not know: how config was loaded, git operations, filesystem state.
    """
    def build(self, config: WorkflowConfig, params: ProjectInitOptions) -> WorkflowInitSpec: ...
```

#### Responsibility allocation

| Component | Input type | Output type | Does NOT touch |
|---|---|---|---|
| `ConfigLoader` | `Path` (YAML file) | Pydantic config object | managers, specs |
| `ConfigValidator` | Multiple config objects | `ValidationReport` | filesystem, managers |
| `GatePlanBuilder` | `QualityConfig`, `FileScope` | `GateExecutionPlan` | filesystem, git |
| `ScaffoldSpecBuilder` | `ArtifactRegistryConfig`, `dict` | `ScaffoldSpec` | Jinja2, filesystem |
| `WorkflowSpecBuilder` | `WorkflowConfig`, `ProjectInitOptions` | `WorkflowInitSpec` | git, filesystem |
| `QAManager` | `GateExecutionPlan` | `QualityResult` | config classes, YAML |
| `ArtifactManager` | `ScaffoldSpec` | rendered file | config classes, YAML |
| `ProjectManager` | `WorkflowInitSpec` | `ProjectState` | config classes, YAML |

The chain `ConfigLoader → spec-builder → manager` means each layer has exactly one input type.
No manager imports a config class. No config class knows a manager exists.

---

### F10 — Test Isolation: Current State and Future Gain

#### Current test problems

Without a `ConfigLoader` and without typed spec objects, tests throughout the suite are forced to
own config knowledge they should not have. Three anti-patterns emerge:

**Anti-pattern A — Tests construct `.st3/` on disk in manager tests**

`test_phase_state_engine_c2.py` builds a full `.st3/workphases.yaml` in `tmp_path` for every
test that exercises `PhaseStateEngine`. The YAML content — phase names, keys, descriptions —
is repeated inline in the fixture. The test is not testing the schema; it is paying a YAML tax
to reach the manager behavior it actually wants to verify.

```python
# Current: manager test pays YAML tax
@pytest.fixture
def workspace_root(tmp_path):
    st3 = tmp_path / ".st3"
    st3.mkdir()
    (st3 / "workphases.yaml").write_text("""
phases:
  planning:
    exit_requires:
      - key: planning_deliverables
  implementation:
    entry_expects: ...
""")
    return tmp_path
```

This pattern appears in at least 8 test files:
`test_phase_state_engine_c2.py`, `test_phase_state_engine_c3.py`, `test_deliverable_checker.py`,
`test_git_manager.py`, `test_enforcement_runner.py`, `test_phase_contract_resolver.py`,
`test_baseline_advance.py`, `test_scope_encoder.py` — each constructing their own `.st3/` subtree.

**Anti-pattern B — Tests patch config class methods at the wrong seam**

`test_baseline_advance.py` patches `QualityConfig.load` to inject a mock config into `QAManager`.
The patch address (`mcp_server.managers.qa_manager.QualityConfig.load`) is an implementation
detail of how `QAManager` internally acquires config — not a stable contract. If `QAManager` is
refactored to accept config via constructor injection, every patch breaks.

```python
# Current: patching at the wrong abstraction level
with patch("mcp_server.managers.qa_manager.QualityConfig.load") as mock_cfg:
    mock_cfg.return_value = QualityConfig(...)
    manager.run_quality_gates(["file.py"])
```

This pattern appears 6 times in `test_baseline_advance.py` alone.

**Anti-pattern C — Config tests use the live `.st3/` directory**

`test_component_registry.py` and `test_project_structure.py` call `ArtifactRegistryConfig.from_file()`
and `ProjectStructureConfig.from_file()` against the real `.st3/artifacts.yaml` and
`.st3/project_structure.yaml`. These are integration tests masquerading as unit tests. They pass
only when the workspace has the correct `.st3/` directory at the CWD — they cannot run in CI
isolation, are CWD-sensitive, and are order-sensitive.

**Root symptom: `reset_instance()` hacks**

`ArtifactRegistryConfig.reset_instance()` appears in `test_component_registry.py` and
`artifact_test_harness.py`. This pattern exists exclusively because the singleton inside the
schema class can leak state between tests. It is a symptom of the missing composition root.

---

#### Future test architecture: three zones

The `ConfigLoader` / `ConfigValidator` / spec-builder layer creates a clean separation into three
test zones. Only Zone 1 is permitted to touch YAML or the filesystem for config purposes.

**Zone 1 — Config layer tests (only zone that touches YAML)**

Tests for `ConfigLoader`, `ConfigValidator`, and each schema class in isolation. These are the
only tests that construct YAML on disk or parse YAML strings. All other zones are forbidden.

```python
# Zone 1: ConfigLoader — only place that writes YAML in a test
def test_loader_raises_on_missing_git_yaml(tmp_path):
    loader = ConfigLoader(config_root=tmp_path / ".st3")
    with pytest.raises(ConfigError, match="git.yaml"):
        loader.load_git_config()

def test_loader_loads_git_config(tmp_path):
    (tmp_path / ".st3" / "git.yaml").write_text("branch_types: [feature, bug]")
    loader = ConfigLoader(config_root=tmp_path / ".st3")
    config = loader.load_git_config()
    assert config.branch_types == ["feature", "bug"]
```

**Zone 2 — Spec-builder tests (no files, only Pydantic objects)**

Tests for `GatePlanBuilder`, `ScaffoldSpecBuilder`, `WorkflowSpecBuilder`. Input is a Pydantic
config object constructed directly in Python (no YAML, no `from_file()`). Output is a typed spec.
Tests verify translation logic: which gates are active, how scope maps to files, how a workflow
maps to ordered phases.

```python
# Zone 2: spec-builder — no YAML, no filesystem
def test_gate_plan_builder_filters_inactive_gates():
    config = QualityConfig(
        version="1.0",
        active_gates=["gate1"],
        gates={"gate1": make_gate(), "gate2": make_gate()}
    )
    plan = GatePlanBuilder().build(config, scope=FileScope(files=["foo.py"]))
    assert len(plan.gates) == 1
    assert plan.gates[0].id == "gate1"
```

**Zone 3 — Manager tests (specs injected, no config knowledge)**

Tests for `QAManager`, `ArtifactManager`, `PhaseStateEngine`, `ProjectManager`. Managers receive
a typed spec via constructor injection. No YAML, no `from_file()`, no config class patches, no
`.st3/` directory construction (except where the manager genuinely reads/writes runtime state
such as `state.json`).

```python
# Zone 3: QAManager — spec injected, zero config knowledge in this test
def test_qa_manager_executes_plan(tmp_path, mock_subprocess):
    plan = GateExecutionPlan(
        gates=[GateInstruction(id="gate1", command=["ruff", "check", "foo.py"])]
    )
    manager = QAManager(workspace_root=tmp_path)
    result = manager.execute(plan)
    assert result.overall_pass is True

# Zone 3: PhaseStateEngine — WorkflowInitSpec replaces workphases.yaml fixture
def test_phase_transition_requires_deliverable(tmp_path):
    spec = WorkflowInitSpec(
        workflow_name="feature",
        phases=[PhaseSpec(name="planning", exit_requires=["planning_deliverables"])]
    )
    engine = PhaseStateEngine(workspace_root=tmp_path, plan=spec)
    with pytest.raises(TransitionError):
        engine.transition_to("implementation")
```

---

#### Concrete gains

| Current | Future |
|---|---|
| 8+ fixtures constructing `.st3/` subtrees in manager tests | 0 — managers receive specs |
| 6 `patch("...QualityConfig.load")` calls in `test_baseline_advance.py` | 0 — `GateExecutionPlan` injected directly |
| `test_component_registry.py` requires live `.st3/` at CWD | `ConfigLoader` test uses `tmp_path` |
| `test_project_structure.py` calls `from_file()` against real workspace | Isolated Zone 1 test |
| New YAML field breaks tests across 3 zones | New YAML field only touches Zone 1 |
| `reset_instance()` hacks to prevent cross-test singleton pollution | Not needed — `ConfigLoader` instantiated per test |

---

## Decisions

**D1 — `mcp_config.yaml` is abolished.** `Settings` reads exclusively from env vars injected via
`mcp.json`. Owner, repo, project_number, log_level are added to `mcp.json` as `env` entries.

**D2 — `ConfigLoader` receives `config_root: Path` as constructor parameter.** The `.st3/`
hardcoded path is removed from all schema classes. This simultaneously resolves the C8/C9
path-centralization requirement for config files.

**D3 — Domain conventions in `GitConfig` become required fields (`Field(...)`, no default).** The
`ConfigLoader` raises `ConfigError` if `git.yaml` is absent. Python defaults are deleted.

**D4 — `ConfigValidator.validate_startup()` is the single startup validation entrypoint.** All
cross-config constraints are checked here. `label_startup.py` is deleted when this exists.

**D5 — Label-sync-against-GitHub moves to `LabelManager`.** It is a runtime integration check,
not a config validation. Must not be folded into `ConfigValidator`.

**D6 — `template_config.py` moves to `utils/`.** It is a path-resolution utility.

**D7 — `EnforcementConfig` and the `phase_contracts` root schema move to `config/schemas/`.**

**D8 — There is no single `ConfigTranslator` class.** The translation layer consists of three
domain-specific spec-builders in `config/translators/`: `GatePlanBuilder`, `ScaffoldSpecBuilder`,
`WorkflowSpecBuilder`. Each accepts Pydantic config objects and returns a typed spec. Managers
receive specs via constructor injection and are prohibited from importing config classes.

---

## Priority Matrix for Next Cycles

| Priority | Finding | Cycle label | Depends on |
|---|---|---|---|
| P0 | F3 — abolish `mcp_config.yaml`; extend `mcp.json`; `Settings` becomes pure env-var reader | C_SETTINGS | — |
| P0 | F1 — introduce `ConfigLoader(config_root)`, one method per YAML | C_LOADER | C_SETTINGS |
| P1 | F2, F8 — introduce `ConfigValidator.validate_startup()`; delete `label_startup.py` | C_VALIDATOR | C_LOADER |
| P2 | F4 — remove Python defaults from `GitConfig`; make domain convention fields required | C_GITCONFIG | C_LOADER |
| P2 | F5 — remove `output_dir` default from `ArtifactLoggingConfig` | C_GITCONFIG | C_LOADER |
| P3 | F7 — move `server.version` to `importlib.metadata`; add remaining deployment vars to `mcp.json` | C_SETTINGS | C_SETTINGS |
| P3 | F6 — move `template_config.py` to `utils/` | C_CLEANUP | C_LOADER |
| P4 | F8 part B — label sync against GitHub to `LabelManager` | C_LABELMGR | C_VALIDATOR |
| P4 | F11 — introduce `GatePlanBuilder`, `ScaffoldSpecBuilder`, `WorkflowSpecBuilder` in `config/translators/` | C_SPECBUILDERS | C_LOADER, C_VALIDATOR |
| P4 | — move `EnforcementConfig` and phase_contracts schema to `config/schemas/` | C_CLEANUP | C_LOADER |

---

## Open Questions

- ❓ Should `config/schemas/` subdirectory be adopted now (matching backend reference) or deferred?
  Moving all schema classes into a subdirectory touches test imports across the entire test suite.
- ❓ When `ConfigLoader` is introduced, should existing `from_file()` class methods be kept as
  deprecated delegates or removed immediately? Keeping them allows phased migration; removing
  them forces all consumers to update in the same cycle.

---

## Related Documentation

- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[docs/system/addendums/Addendum_ 3.8 Configuratie en Vertaal Filosofie.md][related-2]**
- **[backend/config/__init__.py][related-3]**
- **[docs/development/issue257/planning.md][related-4]**
- **[docs/development/issue257/GAP_ANALYSE_ISSUE257.md][related-5]**
- **[docs/development/issue257/research.md][related-6]**
- **[.vscode/mcp.json][related-7]**

<!-- Link definitions -->
[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: docs/system/addendums/Addendum_%203.8%20Configuratie%20en%20Vertaal%20Filosofie.md
[related-3]: backend/config/__init__.py
[related-4]: docs/development/issue257/planning.md
[related-5]: docs/development/issue257/GAP_ANALYSE_ISSUE257.md
[related-6]: docs/development/issue257/research.md
[related-7]: .vscode/mcp.json

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-03-14 | Agent | Full rewrite in English; added F9 (loader responsibilities); resolved all open questions as decisions D1–D7; added mcp.json analysis (F3); label_startup.py SRP analysis (F8); complete priority matrix |
| 1.0 | 2026-03-14 | Agent | Initial draft |

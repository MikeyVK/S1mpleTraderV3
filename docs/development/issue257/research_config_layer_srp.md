<!-- docs\development\issue257\research_config_layer_srp.md -->
<!-- template=research version=8b7bb3ab created=2026-03-14T06:31Z updated=2026-03-14 -->
# Config Layer SRP Violations: Missing Loader, Validator and Schema Separation

**Status:** COMPLETE
**Version:** 1.5
**Last Updated:** 2026-03-14

---

## Table of Contents

- [Purpose](#purpose)
- [Scope](#scope)
- [Prerequisites](#prerequisites)
- [Problem Statement](#problem-statement)
- [Research Goals](#research-goals)
- [Background](#background)
- [Findings](#findings)
  - [F1 — No Central ConfigLoader](#f1--no-central-configloader-srp-violation)
  - [F2 — No ConfigValidator](#f2--no-configvalidator-cross-config-validation-missing-at-startup)
  - [F3 — mcp\_config.yaml Must Not Exist](#f3--mcp_configyaml-must-not-exist-mcpjson-is-the-mcp-standard-config-source)
  - [F4 — Python Defaults Mirror YAML](#f4--python-defaults-mirror-yaml-exactly-dry-violation-dead-code)
  - [F5 — Value Conflict in quality\_config.py](#f5--value-conflict-between-quality_configpy-and-qualityyaml)
  - [F6 — Non-Schema Files in config/](#f6--non-schema-files-misplaced-in-config)
  - [F7 — Config vs Constants Boundary](#f7--config-vs-constants-the-boundary)
  - [F8 — label\_startup.py SRP Violation](#f8--label_startuppy-conflates-two-distinct-responsibilities-srp-violation)
  - [F9 — Loader Responsibilities: Fail-Fast vs Graceful Degradation](#f9--loader-responsibilities-fail-fast-vs-graceful-degradation)
  - [F10 — Spec-Builders (ConfigTranslator Role)](#f10--configtranslator-role-three-domain-specific-spec-builders)
  - [F11 — Test Isolation: Three Zones](#f11--test-isolation-current-state-and-future-gain)
  - [F12 — Module-Level Singletons](#f12--module-level-singletons-import-time-side-effect-architecture_principlesmd-12)
  - [F13 — Two ConfigError Classes](#f13--two-configerror-classes-ssot-violation-architecture_principlesmd-2)
  - [F14 — Config Coverage: Full Flow Mapping](#f14--config-coverage-full-flow-mapping)
  - [F15 — Naming Conventions Audit](#f15--naming-conventions-audit-of-all-new-code-proposed-in-this-document)
- [Decisions](#decisions)
  - D1 mcp\_config.yaml abolished · D2 ConfigLoader path injection · D3 GitConfig fail-fast
  - D4 ConfigValidator entrypoint · D5 label-sync to LabelManager · D6 template\_config to utils/
  - D7 config/schemas/ in C\_LOADER · D8 three spec-builders · D9 ClassVar removal · D10 hard break
  - D11 config/schemas/ formalised · D12 MCP\_SERVER\_NAME · D13 LOG\_LEVEL · D14 PSE two-step migration
- [Priority Matrix for Next Cycles](#priority-matrix-for-next-cycles)
- [Design Questions Resolved](#design-questions-resolved-in-research)
  - [DQ1 — Composition Root](#dq1--composition-root-who-instantiates-what)
  - [DQ2 — from\_file() Strategy](#dq2--from_file-strategy-hard-break--d10)
  - [DQ3 — Module-Level Singletons](#dq3--module-level-singletons-what-replaces-them)
  - [DQ4 — config/schemas/ Subdirectory](#dq4--configschemas-subdirectory-included-in-c_loader-answer-revised)
  - [DQ5 — ClassVar Singleton Removal](#dq5--classvar-singleton-removal-c_loader--d9)
- [Gap Prevention Protocol](#gap-prevention-protocol)
  - [RC-1 Stop/Go as Hard Gate](#rc-1--stopgo-as-hard-gate-not-a-suggestion)
  - [RC-2 Explicit Integration Points](#rc-2--explicit-integration-points-in-every-cycle-dod)
  - [RC-3 Structural Test per RED Phase](#rc-3--minimum-one-structural-test-per-red-phase)
  - [RC-4 Highest-Risk Work First](#rc-4--highest-risk-work-in-first-cycles)
  - [RC-5 Migration Checklists](#rc-5--migration-checklists-as-tracked-artifacts)
  - [RC-6/RC-7 — addressed via F11 + RC-3](#rc-5--migration-checklists-as-tracked-artifacts)
  - [RC-8 Planning as Executable Specification](#rc-8--planning-as-executable-specification)
- [Open Questions](#open-questions) (OQ1–OQ5)
- [Related Documentation](#related-documentation)
- [Version History](#version-history)

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

`mcp_server/config/` contains 13 YAML-backed schema classes, one `Settings` class referencing a
non-existent `mcp_config.yaml`, and 2 misplaced non-schema files (`template_config.py`,
`label_startup.py`) — 16 files in total. There is no central `ConfigLoader`, no
`ConfigValidator`, and the `Settings` class references a `mcp_config.yaml` that does not exist —
and should not exist. Every schema class is simultaneously a Pydantic schema and a loader, a
direct SRP violation. Python defaults silently mirror YAML values (DRY violation). There is an
undetected value conflict in `quality_config.py`. Two non-schema files are misplaced in
`config/`. Two YAML-backed Pydantic schemas live outside `config/` entirely. The current state
is the inverse of the `ARCHITECTURE_PRINCIPLES` the project enforces on itself.

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
| `server.name` (`"st3-workflow"`) | `ServerSettings` Python default | Deployment identity — persistent source of confusion, must be explicit | env var `MCP_SERVER_NAME`; set `"MCP_SERVER_NAME": "st3-workflow"` in `mcp.json` |
| `server.version` (`"1.0.0"`) | `ServerSettings` Python default | Build artifact — belongs in `pyproject.toml` | `importlib.metadata.version()` |
| `github.owner` (`"MikeyVK"`) | `GitHubSettings` Python default | Deployment config — comes from `mcp.json` | env var `GITHUB_OWNER` |
| `github.repo` (`"S1mpleTraderV3"`) | `GitHubSettings` Python default | Deployment config — comes from `mcp.json` | env var `GITHUB_REPO` |
| `github.project_number` (`1`) | `GitHubSettings` Python default | Deployment config — comes from `mcp.json` | env var `GITHUB_PROJECT_NUMBER` |
| `logging.level` (`"INFO"`) | `LogSettings` Python default | Operational parameter that affects config loading itself — must be known before startup; configured in `mcp.json` so always present in production; graceful fallback to `INFO` acceptable when run outside `mcp.json` | `mcp.json` env var `LOG_LEVEL`; set `"LOG_LEVEL": "INFO"` in `mcp.json`; no `ConfigError` if absent (operational default) |

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
| YAML file missing, field has a safe operational default | Log `WARNING` with value used, continue | `logging.level` → default `INFO`, warn (see D13 for `LOG_LEVEL` specifically — env var, not YAML) |
| YAML file present, required field absent | `ConfigError` with field name and file path | Pydantic `Field(...)` enforces this |
| YAML file present, optional field absent | Use schema default, log `DEBUG` | Documented optional fields only |
| Cross-config constraint violated | `ConfigError` in `ConfigValidator` | `allowed_phases` not in `workflows.yaml` |
| Required env var missing | `ConfigError` at startup | `GITHUB_TOKEN` absent |
| Required env var present but empty | `ConfigError` at startup | `GITHUB_TOKEN=""` |

The `ConfigLoader` is the single place where "file not found" becomes either a `ConfigError` or
a logged warning with a stated default. Individual schema classes never make this decision.

---

### F10 — ConfigTranslator Role: Three Domain-Specific Spec-Builders

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

### F11 — Test Isolation: Current State and Future Gain

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

### F12 — Module-Level Singletons: Import-Time Side Effect (ARCHITECTURE_PRINCIPLES.md §12)

`ARCHITECTURE_PRINCIPLES.md` section 12 forbids module-level code that reads files or initializes
singletons:

> *"A `config = AppConfig.load()` as a module-level statement causes `FileNotFoundError` on import
> in tests. Use `ClassVar` with lazy init."*

Two config singletons are instantiated at module level:

```python
# mcp_server/config/settings.py — line 71
settings = Settings.load()           # fires on every import

# mcp_server/config/workflows.py — line 198
workflow_config = WorkflowConfig.load()  # fires on every import
```

`from mcp_server.config.settings import settings` appears in **14 production files and tests**:
`artifact_manager.py`, `core/logging.py`, `cli.py`, `test_tools.py`, `adapters/filesystem.py`,
`adapters/git_adapter.py`, `adapters/github_adapter.py`, `tools/discovery_tools.py`,
`tools/code_tools.py`, `server.py`, `scaffolding/utils.py`, and 3 test files.

Every import of any of these 14 modules triggers `Settings.load()` — which reads `mcp_config.yaml`
(does not exist) and falls back to hardcoded Python defaults, silently. This is the root cause of
CWD-sensitive tests and `reset_instance()` hacks — not just the absence of `ConfigLoader`. Tests
that import any of these 14 modules are always booting on silent-default `Settings`, regardless
of what environment variables or mocks the test sets up.

**Highest-risk item in this entire refactoring.** `Settings` is consumed at module-level by
14 files. Removing the module-level export breaks all 14 immediately. This must be the first
action in C_SETTINGS — not an afterthought to be cleaned up later.

**Replacement:** `settings` and `workflow_config` as module-level exports are eliminated.
`Settings.from_env()` is called once at the composition root (`server.py`). All 14 consumers
receive `settings: Settings` as a constructor parameter, injected from the composition root.
There is no module-level `settings` export after C_SETTINGS.

---

### F13 — Two `ConfigError` Classes: SSOT Violation (ARCHITECTURE_PRINCIPLES.md §2)

Two independent `ConfigError` classes exist in the codebase:

| File | Class | Base class | Structured fields |
|---|---|---|---|
| `mcp_server/core/exceptions.py` | `class ConfigError(MCPError)` | `MCPError` | `file_path`, `hints` |
| `mcp_server/config/scaffold_metadata_config.py` | `class ConfigError(Exception)` | `Exception` | none |

`ARCHITECTURE_PRINCIPLES.md` section 2 (DRY + SSOT): every fact has exactly one authoritative
location. `core.exceptions.ConfigError` is the authoritative class. It inherits from `MCPError`,
carries structured context (`file_path`, `hints`), and is already used by
`operation_policies.py`, `project_structure.py`, and `artifact_registry_config.py`.

The local copy in `scaffold_metadata_config.py` is a DRY violation established when that module
was written in isolation. `ConfigLoader` must import exclusively from `core.exceptions`. The
local copy is deleted in C_LOADER.

---

### F14 — Config Coverage: Full Flow Mapping

**Finding (raised during research review — question E):** It was unclear whether ALL 13 YAML-backed
configs plus Settings + 2 misplaced classes flow completely through
`ConfigLoader → validation → (optional spec-builder) → manager`, or whether some configs take a
shortcut (e.g., direct `from_file()` call inside a manager).

**Two valid routes after C_LOADER (both eliminate `from_file()` in managers):**

| Route | Path | When to use |
|---|---|---|
| **Route 1 — via spec-builder** | `ConfigLoader → PydanticConfig → SpecBuilder → TypedSpec → Manager` | Config needs non-trivial translation into an executable spec with domain-specific fields |
| **Route 2 — direct DI** | `ConfigLoader → PydanticConfig → Manager` | Config maps 1-to-1 to manager needs; no translation logic required |

**Complete flow table (13 YAML-backed configs + Settings):**

| Config class | YAML file | Route | Consumer | Notes |
|---|---|---|---|---|
| `QualityConfig` | `quality.yaml` | Route 1 | `GatePlanBuilder` → `GateExecutionPlan` → `QAManager` | Spec encodes gate ordering + thresholds |
| `ArtifactRegistryConfig` | `artifacts.yaml` | Route 1 | `ScaffoldSpecBuilder` → `ScaffoldSpec` → `ArtifactManager` | Spec resolves template path + context schema |
| `WorkflowConfig` | `workflows.yaml` | Route 1 (P4) | `WorkflowSpecBuilder` → `WorkflowInitSpec` → `ProjectManager` (+PSE) | P0: direct DI to `ProjectManager`; `WorkflowInitSpec` produced in C_SPECBUILDERS |
| `WorkphasesConfig` | `workphases.yaml` | Route 2 (P0) → Route 1 (P4) | `PhaseStateEngine` directly (P0); `WorkflowSpecBuilder` input (P4) | P0 interim: PSE receives raw `WorkphasesConfig`. P4: folded into `WorkflowInitSpec` |
| `GitConfig` | `git.yaml` | Route 2 | `GitManager`, `GitAdapter` | No translation needed |
| `LabelConfig` | `labels.yaml` | Route 2 | `LabelManager` | No translation needed |
| `MilestoneConfig` | `milestones.yaml` | Route 2 | `MilestoneManager` | TBD — verify manager existence in planning |
| `IssueConfig` | `issues.yaml` | Route 2 | `IssueManager` | TBD — verify manager existence in planning |
| `ContributorConfig` | `contributors.yaml` | Route 2 | **Unknown** — no clear manager owner identified in research | ⚠️ Must resolve in planning: who consumes this? |
| `ScopeConfig` | `scopes.yaml` | Route 2 | `ScopeEncoder` | No translation needed |
| `OperationPoliciesConfig` | `policies.yaml` | Route 2 | `PolicyChecker` / `PhaseStateEngine` | Depends on enforcement wiring |
| `ProjectStructureConfig` | `project_structure.yaml` | Route 2 | `ProjectManager` | No translation needed |
| `ScaffoldMetadataConfig` | `scaffold_metadata.yaml` | Route 2 | `ArtifactManager` | Moves to `config/schemas/` in C_LOADER (D7); local `ConfigError` deleted (F13) |
| `EnforcementConfig` | `enforcement.yaml` | Route 2 | `EnforcementRunner` | No translation needed |
| `PhaseContractConfig` | `phase_contracts.yaml` | Route 2 | `PhaseContractResolver` | No translation needed |
| `Settings` | env vars via `mcp.json` | N/A | All managers via `server.py` composition root | `Settings.from_env()` called once; not via `ConfigLoader` |

**Key invariant (enforced by structural test in C_LOADER RED phase):**

```python
# tests/unit/test_config_schemas.py — structural test (C_LOADER RED)
def test_no_from_file_on_any_config_schema():
    """Every schema class must be a pure Pydantic model without file-loading methods."""
    import inspect
    import mcp_server.config.schemas as schemas_module
    for name, cls in inspect.getmembers(schemas_module, inspect.isclass):
        for forbidden in ("from_file", "load", "reset_instance"):
            assert not hasattr(cls, forbidden), (
                f"{name}.{forbidden}() must not exist — ConfigLoader is the sole loader."
            )
```

This test prevents future drift: any new schema class that adds `from_file()` will fail immediately.

**Unresolved items for planning:**
- `ContributorConfig`: no manager owner identified — must assign in C_LOADER planning.
- `WorkflowConfig` + `WorkphasesConfig` (P4): confirm `WorkflowSpecBuilder` takes both as input
  so `WorkflowInitSpec` carries all phase-exit requirements.
- `OperationPoliciesConfig`: clarify whether it feeds `PolicyChecker` (new class?) or directly
  into `PhaseStateEngine`'s enforcement logic — affects C_LOADER composition root.

---

### F15 — Naming Conventions: Audit of All New Code Proposed in This Document

**Finding (raised during research review — question F):** New class names, folder names, and type
aliases proposed across this document have not been compiled in one place. Before planning begins,
every name needs an explicit decision so that PRs do not introduce accidental inconsistency.

**New folder structure (proposed by this document):**

| Folder | Status | Contains | Notes |
|---|---|---|---|
| `mcp_server/config/` | Exists (partial) | `loader.py`, `validator.py`, `schemas/`, `translators/` | `schemas/` + `translators/` are new subdirectories |
| `mcp_server/config/schemas/` | New (C_LOADER) | 13 schema classes (`*_config.py`) + `Settings` | All moved from `config/` and two from `managers/`; D7 |
| `mcp_server/config/translators/` | New (C_SPECBUILDERS) | `gate_plan_builder.py`, `scaffold_spec_builder.py`, `workflow_spec_builder.py` | Name "translators" mirrors backend reference; the classes inside are "builders" |
| `mcp_server/dtos/` | New (C_SPECBUILDERS) | `specs/gate_execution_plan.py`, `specs/scaffold_spec.py`, `specs/workflow_init_spec.py` | Spec output types are Pydantic DTOs; mirrors `backend/dtos/` pattern |

**New class names (decided):**

| Class | Module | Pattern | Rationale |
|---|---|---|---|
| `ConfigLoader` | `config/loader.py` | Service | Loads all YAML-backed configs; single responsibility |
| `ConfigValidator` | `config/validator.py` | Service | Cross-config validation at startup; single responsibility |
| `GatePlanBuilder` | `config/translators/gate_plan_builder.py` | Builder | Stateless; translates `QualityConfig` → `GateExecutionPlan` |
| `ScaffoldSpecBuilder` | `config/translators/scaffold_spec_builder.py` | Builder | Stateless; translates `ArtifactRegistryConfig` → `ScaffoldSpec` |
| `WorkflowSpecBuilder` | `config/translators/workflow_spec_builder.py` | Builder | Stateless; translates `WorkflowConfig` + `WorkphasesConfig` → `WorkflowInitSpec` |
| `GateExecutionPlan` | `dtos/specs/gate_execution_plan.py` | Pydantic model / DTO | Spec consumed by `QAManager` |
| `ScaffoldSpec` | `dtos/specs/scaffold_spec.py` | Pydantic model / DTO | Spec consumed by `ArtifactManager` |
| `WorkflowInitSpec` | `dtos/specs/workflow_init_spec.py` | Pydantic model / DTO | Spec consumed by `ProjectManager` and (P4) `PhaseStateEngine` |

**Classmethod naming:**

| Classmethod | Class | Rationale |
|---|---|---|
| `Settings.from_env()` | `Settings` | Follows Python convention (`from_dict`, `from_env`, `from_file`); consistent with upcoming deletion of `from_file()` on schema classes |

**Environment variable naming:**

| Env var | mcp.json key | `Settings` field | Notes |
|---|---|---|---|
| `MCP_SERVER_NAME` | `"MCP_SERVER_NAME": "st3-workflow"` | `settings.server_name` | Replaces hardcoded `server.name = "st3-workflow"` in Python; D12 |
| `LOG_LEVEL` | `"LOG_LEVEL": "INFO"` | `settings.log_level` | Always present in mcp.json; D13 |

**Existing code — no rename (too much blast radius):**

| Current name | Lives in | Issue | Decision |
|---|---|---|---|
| `PhaseStateEngine` | `managers/` | Is an Engine, not a Manager | Keep in `managers/`; separate cleanup issue if folder is renamed |
| `EnforcementRunner` | `managers/` | Is a Runner, not a Manager | Keep in `managers/`; same cleanup issue |
| `PhaseContractResolver` | `managers/` | Is a Resolver, not a Manager | Keep in `managers/`; same cleanup issue |

**Naming decision (resolved):** Spec output DTOs (`GateExecutionPlan`, `ScaffoldSpec`,
`WorkflowInitSpec`) are placed in `mcp_server/dtos/specs/`. Rationale: these types are
consumed by managers, not owned by the config layer. Placing them in `config/` would create
an import dependency `managers/ → config/dtos` which inverts the intended direction. The
`mcp_server/dtos/` folder mirrors the `backend/dtos/` pattern already established in the
codebase.

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

**D7 — `EnforcementConfig` and the `phase_contracts` root schema move to `config/schemas/`.** All
13 YAML-backed schema classes also move to a `config/schemas/` subdirectory in C_LOADER
(previously deferred in DQ4 — overruled: hard break is the right time to move them since all
consumer imports break anyway; doing it later creates a second round of blast radius for no
functional gain).

**D8 — There is no single `ConfigTranslator` class.** The translation layer consists of three
domain-specific spec-builders in `config/translators/`: `GatePlanBuilder`, `ScaffoldSpecBuilder`,
`WorkflowSpecBuilder`. Each accepts Pydantic config objects and returns a typed spec. Managers
receive specs via constructor injection and are prohibited from importing config classes.

**D9 — `ClassVar` singleton pattern is removed from all schema classes.** Schema classes become
pure Pydantic value objects. `ConfigLoader` owns instance lifecycle. `ClassVar _instance`,
`from_file()`, `load()`, and `reset_instance()` are deleted from all schema classes in C_LOADER.
There is no per-class lazy init, no singleton guard, no `_instance`. Instance lifecycle is the
caller's responsibility — in production that is `ConfigLoader`, in tests that is `tmp_path`.

**D10 — Hard Break: no deprecated delegates, no parallel migration paths.** The migration from
`from_file()` / module-level singletons to `ConfigLoader` is executed as a single atomic hard
break in C_SETTINGS + C_LOADER:

1. Delete `settings = Settings.load()` and `workflow_config = WorkflowConfig.load()` module-level exports.
2. Delete `from_file()`, `load()`, `ClassVar _instance`, `reset_instance()` from all 15 schema classes.
   *(15 = 13 YAML-backed schemas + `EnforcementConfig` from `managers/enforcement_runner.py` +
   `PhaseContractConfig` from `managers/phase_state_engine.py`. `Settings` is handled separately
   in C_SETTINGS: `load()` is replaced by `from_env()`, not simply deleted.)*
3. This breaks all 14+ importers immediately — that is intentional and desired.
4. Add `ConfigLoader` with all methods. Add `Settings.from_env()`.
5. Update every consumer in the same cycle. Every broken import is a tracked checklist item.

**Rationale:** Flag-day (gradual / soft) was evaluated and rejected based on the issue #257 cycle
run. RC-2 proves that when the old wiring path remains available, agent implementations
systematically build the new component correctly but skip the integration step — because the
silent fallback hides the incompleteness. A hard break makes partial completion visible as
broken tests. There is no silent path to cover incomplete work. RC-2 cannot occur when the old
wiring no longer compiles.

**D11 — `config/schemas/` subdirectory in C_LOADER (formalizes DQ4 + D7).** All 13 YAML-backed
schema classes and `Settings` move to `mcp_server/config/schemas/`. Two misplaced classes in
`managers/` (`EnforcementConfig` from `enforcement_manager.py`, `PhaseContractConfig` from
`phase_state_engine.py`) also move to `config/schemas/` in C_LOADER. This costs nothing extra:
D10 hard break already forces all import updates.

**D12 — `server.name` hardcoding replaced by env var `MCP_SERVER_NAME`.** `Settings.server.name`
(currently hardcoded as `"st3-workflow"` in Python) is removed. `mcp.json` gains a new env entry:
`"MCP_SERVER_NAME": "st3-workflow"`. The `Settings` object reads this field via `os.environ`.
Rationale: naming is deployment identity — it belongs in `mcp.json` alongside `GITHUB_OWNER`,
`GITHUB_REPO`, etc., not as a Python compile-time constant.

**D13 — `LOG_LEVEL` managed in `mcp.json`.** `LOG_LEVEL` affects logging initialisation, which
runs before `ConfigLoader` starts. It must be a known value before startup begins. `mcp.json`
gains `"LOG_LEVEL": "INFO"` as an explicit env entry. `Settings.log_level` reads it at startup.
When running outside `mcp.json` (e.g., bare CLI), a documented fallback of `"INFO"` is acceptable
and should emit a startup notice — `LOG_LEVEL` is operational configuration, not security-critical.
No `ConfigError` raised on absence; the fallback is intentional and documented.

**D14 — `PhaseStateEngine` constructor injection (two-step migration).** In P0 (C_LOADER):
`PhaseStateEngine(workspace_root, workphases_config, state_repository)` — receives raw
`WorkphasesConfig` via DI. In P4 (C_SPECBUILDERS): `WorkflowSpecBuilder` produces
`WorkflowInitSpec` from `WorkflowConfig + WorkphasesConfig`; PSE is then updated to accept
`WorkflowInitSpec` instead. The Zone 3 test-isolation goal (F11) depends on P4. P0 is the
minimum viable hard break; P4 is the quality-of-test improvement on top.

---

## Priority Matrix for Next Cycles

| Priority | Finding | Cycle label | Depends on |
|---|---|---|---|
| **P0** | F12 — delete `settings = Settings.load()` module-level; `Settings.from_env()` at composition root; update 14 consumers (D10 hard break step 1) | C_SETTINGS | — |
| **P0** | F3 + D12 + D13 — `Settings` becomes pure env-var reader; add `MCP_SERVER_NAME`, `LOG_LEVEL`, `owner`, `repo`, `project_number` to `mcp.json`; delete `mcp_config.yaml` fallback code | C_SETTINGS | — |
| **P0** | F1 + D9 + D10 + D11 — introduce `ConfigLoader(config_root)`; move all 15 schema classes to `config/schemas/`; delete `from_file()`, `load()`, `ClassVar _instance`, `reset_instance()` from all 15 schemas (hard break); update all consumers | C_LOADER | C_SETTINGS |
| P0 | F13 — delete local `ConfigError` in `scaffold_metadata_config.py`; all config raise `core.exceptions.ConfigError` | C_LOADER | C_LOADER |
| P0 | F14 — structural test `test_no_from_file_on_any_config_schema()` in `tests/unit/config/` | C_LOADER | C_LOADER |
| P1 | F2, F8 — introduce `ConfigValidator.validate_startup()`; delete `label_startup.py` | C_VALIDATOR | C_LOADER |
| P2 | F4 — remove Python defaults from `GitConfig`; make domain convention fields required | C_GITCONFIG | C_LOADER |
| P2 | F5 — remove `output_dir` default from `ArtifactLoggingConfig` | C_GITCONFIG | C_LOADER |
| P3 | F7 — move `server.version` to `importlib.metadata`; `MCP_SERVER_NAME` + `LOG_LEVEL` already in `mcp.json` (done in C_SETTINGS / D12 / D13) | C_CLEANUP | C_SETTINGS |
| P3 | F6 — move `template_config.py` to `utils/`; delete from `config/` | C_CLEANUP | C_LOADER |
| P4 | F8 part B — label sync against GitHub to `LabelManager` | C_LABELMGR | C_VALIDATOR |
| P4 | F10 + D14 — introduce `GatePlanBuilder`, `ScaffoldSpecBuilder`, `WorkflowSpecBuilder` in `config/translators/`; create `mcp_server/dtos/specs/`; update PSE to accept `WorkflowInitSpec` (D14) | C_SPECBUILDERS | C_LOADER, C_VALIDATOR |
| P4 | F11 — Zone 3 test isolation complete (PSE receives `WorkflowInitSpec` — depends on C_SPECBUILDERS) | C_SPECBUILDERS | C_SPECBUILDERS |
| P4 | F15 — Naming review: confirm all new class/folder names match decisions before any C_* cycle starts planning | Pre-planning | — |

---

## Design Questions Resolved in Research

The following architectural questions were answered during research to prevent agents from making
ad-hoc decisions during implementation. Unanswered design questions are the primary source of
RC-2 gaps ("component built, not wired") — an agent that must invent the answer to "how does
`ConfigLoader` reach `QAManager`?" will either guess wrong or silently leave the old path active.

### DQ1 — Composition Root: Who Instantiates What?

The composition root is `server.py`. It is the only location that instantiates concrete
implementations. The startup sequence:

```python
# server.py — composition root (illustrative, not final API)
config_root = Path(workspace_root) / ".st3"
loader = ConfigLoader(config_root=config_root)

# Step 1 — Load all configs (ConfigLoader raises ConfigError on any missing required file)
git_config        = loader.load_git_config()
workflow_config   = loader.load_workflow_config()
workphases_config = loader.load_workphases_config()
quality_config    = loader.load_quality_config()
artifact_config   = loader.load_artifact_registry_config()
label_config      = loader.load_label_config()
issue_config      = loader.load_issue_config()
milestone_config  = loader.load_milestone_config()
contributor_config = loader.load_contributor_config()
scope_config      = loader.load_scope_config()
policies_config   = loader.load_operation_policies()
structure_config  = loader.load_project_structure()
scaffold_meta     = loader.load_scaffold_metadata_config()
enforcement_config = loader.load_enforcement_config()
phase_contracts   = loader.load_phase_contracts_config()

# Step 2 — Cross-config validation (Layer 3, fires once at startup)
ConfigValidator().validate_startup(
    policies=policies_config,
    workflow=workflow_config,
    structure=structure_config,
    artifact=artifact_config,
    phase_contracts=phase_contracts,
    workphases=workphases_config,
)

# Step 3 — Settings from env vars (raises ConfigError on missing required vars)
settings = Settings.from_env()

# Step 4 — Spec-builders (stateless, constructed once, no init args)
gate_plan_builder     = GatePlanBuilder()
scaffold_spec_builder = ScaffoldSpecBuilder()
workflow_spec_builder = WorkflowSpecBuilder()

# Step 5 — Managers receive config objects + spec-builders (or raw config) via constructor
qa_manager            = QAManager(workspace_root, quality_config, gate_plan_builder)
artifact_manager      = ArtifactManager(workspace_root, artifact_config, scaffold_spec_builder)
project_manager       = ProjectManager(workspace_root, workflow_config, workflow_spec_builder)
git_manager           = GitManager(workspace_root, git_config, settings)
label_manager         = LabelManager(workspace_root, label_config, settings)
phase_state_engine    = PhaseStateEngine(workspace_root, workphases_config, state_repository)  # state_repository: adapter for .st3/state.json (e.g. JsonStateRepository)
enforcement_runner    = EnforcementRunner(workspace_root, enforcement_config)
phase_contract_resolver = PhaseContractResolver(phase_contracts, workphases_config)
# ... remaining managers

# Step 6 — Tools receive managers (already current pattern — no change here)
```

**Invariants:**
- Only `server.py` instantiates concrete implementations.
- No manager imports any config class (`from mcp_server.config.*` is forbidden in `managers/`).
- No config class imports any manager class.
- Spec-builders are stateless: they hold no shared mutable state, constructed once, safe to inject.
- The depth of the dependency chain from a tool is at most 2: `tool → manager`, `manager → spec-builder + config`. (Law of Demeter, ARCHITECTURE_PRINCIPLES.md §7.)
- `PhaseStateEngine` receives `workphases_config: WorkphasesConfig` directly (P0). In P4
  (C_SPECBUILDERS), `WorkflowSpecBuilder` will produce `WorkflowInitSpec` from `WorkflowConfig` +
  `WorkphasesConfig`, and PSE will be updated to accept `WorkflowInitSpec`. This is a two-step
  migration — direct DI is the valid P0 state.

### DQ2 — `from_file()` Strategy: Hard Break (→ D10)

See D10. No deprecated delegates. All deletions and all consumer updates in the same two cycles
(C_SETTINGS + C_LOADER). Partial completion is visible as broken tests. This is acceptable and
intentional.

### DQ3 — Module-Level Singletons: What Replaces Them?

After C_SETTINGS, there is no `settings` module-level export. Consumers that currently
`from mcp_server.config.settings import settings` receive `settings: Settings` as a constructor
parameter, injected from `server.py`.

Migration checklist for planning (all 14 consumers must be ticked before C_SETTINGS DoD):

| Consumer file | Current usage | After C_SETTINGS |
|---|---|---|
| `managers/artifact_manager.py` | `settings.server.workspace_root` | `workspace_root: Path` param |
| `core/logging.py` | `settings.logging.level` | `log_level: str` param |
| `cli.py` | `settings.server.*` | `settings: Settings` param |
| `tools/test_tools.py` | `settings.server.*` | `settings: Settings` param |
| `adapters/filesystem.py` | `settings.server.*` | `settings: Settings` param |
| `adapters/git_adapter.py` | `settings.github.*` | `settings: Settings` param |
| `adapters/github_adapter.py` | `settings.github.*` | `settings: Settings` param |
| `tools/discovery_tools.py` | `settings.*` | `settings: Settings` param |
| `tools/code_tools.py` | `settings.*` | `settings: Settings` param |
| `server.py` | `settings.*` | reads directly from `Settings.from_env()` |
| `scaffolding/utils.py` | `settings.*` | `settings: Settings` param |
| `tests/unit/tools/test_discovery_tools.py` | import | construct `Settings(...)` directly |
| `tests/integration/.../test_search_documentation_e2e.py` | import | construct `Settings(...)` directly |
| `tests/unit/config/test_settings.py` | `Settings` class | already imports class, not singleton |

`workflow_config = WorkflowConfig.load()` in `workflows.py` is eliminated in C_LOADER as part
of the `WorkflowConfig` hard break. Its only consumer in the current codebase is `server.py`
(which will receive the loaded config from `ConfigLoader` after C_LOADER).

### DQ4 — `config/schemas/` Subdirectory: Included in C_LOADER (Answer revised)

~~Moving all schema classes to a `config/schemas/` subdirectory deferred to C_REORGANIZE.~~

**Revised decision (D7):** `config/schemas/` is created in C_LOADER as part of the hard break.
Since C_LOADER already breaks every import of every schema class (D10 hard break: deleting
`from_file()`, `load()`, `ClassVar _instance`), consumer imports must be updated regardless.
Moving schemas to `config/schemas/` at the same time adds zero additional blast radius — the
imports are already broken and being updated. Doing it later would mean a second round of import
updates for no functional gain. This is directly analogous to RC-5 (half-done migration looks
done). Applies to all 13 YAML-backed schemas and the 2 schemas from `managers/`.

### DQ5 — `ClassVar` Singleton Removal: C_LOADER (→ D9)

`ClassVar _instance`, `from_file()`, `load()`, and `reset_instance()` are deleted from all
15 schema classes in C_LOADER — the same cycle as the hard break. They are companion structures
to the patterns being deleted. Leaving any of them in place after C_LOADER constitutes incomplete
work and will be caught by a structural test:

```python
# Structural test — required in C_LOADER RED phase
# NOTE: This per-class variant is illustrative. The canonical implementation is
# the inspect-based test defined in F14 (test_no_from_file_on_any_config_schema),
# which covers all schema classes automatically via the schemas module namespace.
def test_no_from_file_on_any_config_class() -> None:
    from mcp_server.config import quality_config, git_config, workflows  # etc.
    for cls in [quality_config.QualityConfig, git_config.GitConfig, ...]:
        assert not hasattr(cls, "from_file"), f"{cls.__name__} still has from_file()"
        assert not hasattr(cls, "load"), f"{cls.__name__} still has load()"
        assert not hasattr(cls, "reset_instance"), f"{cls.__name__} still has reset_instance()"
```

---

## Gap Prevention Protocol

Root causes RC-1 through RC-8 from `GAP_ANALYSE_ISSUE257.md` are addressed by measures encoded
as non-negotiable requirements in `planning.md`. This section is the reference for why those
planning constraints exist.

### RC-1 — Stop/Go as Hard Gate (not a suggestion)

Every cycle in `planning.md` has a "Verification" block with exact commands and expected output.
An agent may not start the next cycle until it has produced the output of every verification
command as evidence. Format:

```
### Stop/Go — Cycle X
- [ ] `Select-String "from_file" mcp_server/config/quality_config.py` → 0 matches
- [ ] `python -m pytest tests/mcp_server/unit/config/ -q` → all pass
Show output before starting Cycle X+1.
```

### RC-2 — Explicit Integration Points in Every Cycle DoD

Every cycle DoD contains a mandatory "Integration" item:

> *List every existing file that currently calls, imports, or depends on the component modified
> in this cycle. Verify each one has been updated. An entry is not done until it has been
> updated — not until the new component's own tests are green.*

This targets the pattern where `PhaseContractResolver` was built and tested in isolation but
never wired into `PhaseStateEngine`.

For this implementation run, the equivalent risk is: `ConfigLoader` built and tested, but managers
patching `QualityConfig.load` or constructing YAML on disk in tests remain untouched.

### RC-3 — Minimum One Structural Test per RED Phase

Every RED phase includes at least one structural test that verifies the absence of the old
anti-pattern. Behavioral tests alone do not catch structural gaps.

```python
# Structural test: no manager imports a config class
def test_qa_manager_does_not_import_config() -> None:
    import inspect
    import mcp_server.managers.qa_manager as m
    source = inspect.getsource(m)
    assert "from mcp_server.config" not in source

# Structural test: no from_file() on schema class
def test_quality_config_has_no_loader_methods() -> None:
    from mcp_server.config.quality_config import QualityConfig
    assert not hasattr(QualityConfig, "from_file")
    assert not hasattr(QualityConfig, "load")
    assert not hasattr(QualityConfig, "reset_instance")
```

### RC-4 — Highest-Risk Work in First Cycles

C_SETTINGS (module-level singletons, 14 consumers) and C_LOADER (hard break, 15 schema classes)
are **P0** — done first. The hardest, most-entangled work happens before any new components are
built on top of it. This inverts the issue #257 pattern where `PhaseStateEngine` (highest risk,
869 lines, most-tested class) was systematically deferred while smaller components were built
and tested in isolation.

### RC-5 — Migration Checklists as Tracked Artifacts

`planning.md` contains explicit checklists of every consumer of `from_file()`, every module-level
singleton, and every schema class that carries a `ClassVar`. Each item is a checkbox. A cycle is
not done until every checkbox is ticked and a verification command confirms it.

*Note: RC-6 (test coverage gaps at boundary layers) and RC-7 (spec-builder tests not separated
from manager tests) from `GAP_ANALYSE_ISSUE257.md` are addressed structurally by the three-zone
test architecture (F11) and the structural test requirement (RC-3 + F14) rather than as separate
protocol items. They do not require standalone protocol entries here.*

### RC-8 — Planning as Executable Specification

Every DoD item in `planning.md` follows the format:

`Criterion | Verification command | Expected output`

Reading `planning.md` feels like reading a test specification, not a design document. The
planning document is consulted before every commit in a cycle — not once at the start.

---

## Open Questions

**Resolved (previous versions):**
- `from_file()` deprecated delegates vs immediate removal → D10 + DQ2: hard break, no deprecated delegates.
- `config/schemas/` subdirectory timing → DQ4 revised: included in C_LOADER (not deferred to C_REORGANIZE).

**Open — must resolve before C_LOADER planning:**

| # | Question | Where raised | Impact if unresolved |
|---|---|---|---|
| OQ1 | **`ContributorConfig` consumer** — No manager owner identified in research. Who consumes `contributors.yaml` at runtime? | F14 | Cannot wire `ContributorConfig` into DQ1 composition root (Step 5) |
| OQ2 | **`OperationPoliciesConfig` wiring** — Does it feed a new `PolicyChecker` class, or does it go directly into `PhaseStateEngine`'s enforcement logic? | F14 | Affects DQ1 composition root and C_LOADER scope |
| OQ3 | **`MilestoneConfig` / `IssueConfig`** — Do `MilestoneManager` and `IssueManager` exist in `managers/` or are they planned? If planned, are they in scope for C_LOADER? | F14 | Affects Step 5 of DQ1; if absent, direct DI has no target |
| OQ4 | **`FileScope` type** — Used in `GatePlanBuilder.build(config, scope: FileScope)` (F10). Is this a new DTO created in C_SPECBUILDERS, or an existing type? | F10 | Affects C_SPECBUILDERS scope; name and location not yet in F15 naming table |
| OQ5 | **`ProjectInitOptions` type** — Used in `WorkflowSpecBuilder.build(config, params: ProjectInitOptions)` (F10). Same question as OQ4. | F10 | Affects C_SPECBUILDERS scope; name and location not yet in F15 naming table |

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
| 1.5 | 2026-03-14 | Agent | Added TOC; fixed Open Questions (removed wrong DQ4 "deferred" reference, added OQ1-OQ5 from F14/F10); clarified "15 schema classes" in D10; added state_repository note in DQ1; DQ5 structural test points to canonical F14 version; F15 spec DTO location marked as decided; RC-6/RC-7 note added; F9 LOG_LEVEL cross-reference to D13 |
| 1.4 | 2026-03-14 | Agent | Added F14 (Config Coverage — full flow mapping, two routes, unresolved ContributorConfig owner); added F15 (Naming conventions — new folders, classes, env vars, spec DTO location); added D11-D14 (config/schemas/ formalised, MCP_SERVER_NAME, LOG_LEVEL, PSE two-step migration); expanded DQ1 startup sequence to include all 15 configs + PSE/EnforcementRunner/PhaseContractResolver; answers A-F from user review incorporated; Priority Matrix updated |
| 1.3 | 2026-03-14 | Agent | Added DQ1–DQ5 (design questions resolved); D7 amended (all 13 schemas + 2 misplaced to config/schemas/ in C_LOADER, not deferred); DQ4 revised (no longer deferred); F7 table: server.name → MCP_SERVER_NAME, LOG_LEVEL row added; Problem Statement count corrected (16 total) |
| 1.2 | 2026-03-14 | Agent | Added F10 (spec-builders: GatePlanBuilder, ScaffoldSpecBuilder, WorkflowSpecBuilder); F11 (test isolation 3-zone architecture); F12 (module-level singletons); F13 (two ConfigError classes); D8-D10 (no single ConfigTranslator, ClassVar singleton removal, hard-break strategy); Gap Prevention Protocol (RC-1 through RC-8) |
| 1.1 | 2026-03-14 | Agent | Full rewrite in English; added F9 (loader responsibilities); resolved all open questions as decisions D1–D7; added mcp.json analysis (F3); label_startup.py SRP analysis (F8); complete priority matrix |
| 1.0 | 2026-03-14 | Agent | Initial draft |

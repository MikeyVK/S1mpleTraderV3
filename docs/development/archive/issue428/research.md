<!-- docs/development/issue428/research.md -->
<!-- template=research version=8b7bb3ab created=2026-07-21T21:11Z updated=2026-07-22 -->
# Research Document - Implement `--upgrade` CLI command and release v2.0.0

**Status:** DEFINITIVE  
**Version:** 1.2.0  
**Last Updated:** 2026-07-22  

---

## Problem Statement

Currently, there is no standardized way to upgrade an existing user workspace `.pgmcp/` directory when a newer version of the wheel package is installed. Upgrades to schemas, default templates, rules, and configurations require manual intervention, leading to startup crashes, version mismatches, or outdated workspace assets.

---

## Research Goals

- Analyze current CLI entry points and argument parsing in `mcp_server/cli.py`.
- Examine package asset distribution (`mcp_server/assets/`) and build pipelines.
- Clarify package versioning mechanisms (`pyproject.toml`, `release_manifest.yaml`) and release history tracking (`CHANGELOG.md`).
- Evaluate workspace upgrade strategies (Full Asset Overwrite vs. Version-Aware Preservation).
- Formulate the binding Approved Strategy for Issue #428 (fail-safe backups, asset renewal, state preservation, upgrade logging).
- Map the blast radius across CLI, bootstrapper, services, test suites, and documentation.

---

## Codebase Findings & Evidence

### 1. CLI Entry Points & Argument Parsing
- **Script Entry Point**: Configured in `pyproject.toml` (lines 18–20): `pgmcp = "mcp_server.cli:main"`.
- **Module Entrypoint**: `mcp_server/__main__.py` (lines 1–3) invokes `main()`.
- **CLI Implementation**: `mcp_server/cli.py` (lines 13–84) uses stdlib `argparse.ArgumentParser`.
- **Existing Flags**:
  - `--version` (lines 18, 26–29): Prints `Phase-Gate MCP Server v{version}` and exits `0`.
  - `--init` (lines 20–23, 31–63): Checks if `.pgmcp/` exists. If missing, copies `mcp_server/assets/` into `.pgmcp/` and writes `.pgmcp/.version`. If present, exits `1` with error.

### 2. Package Versioning & Build Mechanism
- **Version SSOT**: Package version is explicitly declared in `pyproject.toml` (`version = "1.0.0"`) and `.pgmcp/config/release_manifest.yaml` (`version: "1.0.0"`).
- **Build Pipeline**: `scripts/build_package.py` reads `release_manifest.yaml`, copies source assets into `mcp_server/assets/`, and invokes `python -m build`. The build tool inspects `pyproject.toml` to name the wheel artifact (e.g. `phase_gate_mcp-2.0.0-py3-none-any.whl`).
- **Bumping to v2.0.0**: Updating `version = "2.0.0"` in `pyproject.toml`, `release_manifest.yaml`, and `settings.py` signals the build system to compile release `v2.0.0`.

### 3. Version History (Package Changelog) vs. Workspace Migration Log
- **Package Version History (`CHANGELOG.md`)**:
  - Permanent repository document tracking changes across server releases (`1.0.0` $\rightarrow$ `2.0.0`).
  - Leans on Git history (commit logs, closed PRs #428, #433, #438, etc.) to list added features, breaking changes, and bug fixes between releases.
  - Can be partially automated via release scripts parsing Git logs/tags into a clean Markdown `CHANGELOG.md`.
- **Workspace Migration Log (`.pgmcp/logs/upgrade_YYYYMMDD_HHMMSS.json`)**:
  - Dynamic runtime artifact generated on the user's machine during `pgmcp --upgrade`.
  - Records disk-level actions (timestamped backup path, preserved custom files, updated templates).

### 4. Bootstrapping & Version Validation Decoupling
- **Current State**: `ServerBootstrapper._validate_version()` in `mcp_server/bootstrap.py` checks `.pgmcp/.version` against `settings.server.version`. If missing or mismatched, raises `ConfigError`.
- **Decoupling (SRP)**: Decouple workspace version validation into `WorkspaceVersionValidator` so `ServerBootstrapper` remains pure in its startup orchestration.

---

## Blast Radius & Affected Boundaries

| Component / Boundary | Location | Impact Description |
|---|---|---|
| **CLI Argument Parsing** | `mcp_server/cli.py` | Add `--upgrade` flag and delegate execution to upgrader service. |
| **Workspace Upgrader Service** | `mcp_server/services/workspace_upgrader.py` | Dedicated service for fail-safe backup, asset renewal, state preservation, and upgrade logging. |
| **Version Validation (SRP)** | `mcp_server/managers/workspace_version_validator.py` | Decoupled workspace version validation service. |
| **Server Bootstrapper** | `mcp_server/bootstrap.py` | Delegate version check to `WorkspaceVersionValidator`; update error message to direct user to `pgmcp --upgrade`. |
| **Package Changelog** | `CHANGELOG.md` | Formal release notes tracking features/changes from v1.0.0 to v2.0.0. |
| **Unit & Integration Tests** | `tests/mcp_server/unit/test_cli.py` | Unit tests for `pgmcp --upgrade`, backup creation, asset renewal, and state preservation. |
| **Documentation & Help** | `docs/reference/mcp/` & `AGENTS.md` | Update CLI usage reference pages and help menus. |

---

## Approved Strategy

**Selected Strategy:** `Smart Version-Aware Preservation with Backup & Upgrade Logging`

### Strategy Principles & Rules:

1. **Fail-Safe Timestamped Backup**:
   - Before modifying workspace assets, generate a complete copy of `.pgmcp/` to `.pgmcp_backup_YYYYMMDD_HHMMSS/`.
   - Backup pruning is left to the user.

2. **Smart Version-Aware Preservation via `ConfigLoader`**:
   - Leverage `ConfigLoader` / `ValidationService` infrastructure: valid user YAML configs matching schemas remain intact.
   - Outdated, corrupt, or missing core assets (`config/`, `templates/`, `docs/`) are renewed from `mcp_server/assets/`.
   - `.pgmcp/.version` is updated to the target server version.

3. **Strict Dynamic State Preservation**:
   - Dynamic runtime state files (`state.json`, `deliverables.json`, `template_registry.json`, `logs/`) are **strictly preserved**.

4. **Single Structured Upgrade Log**:
   - Write a single structured JSON log file to `.pgmcp/logs/upgrade_YYYYMMDD_HHMMSS.json`.

5. **Package Version History (`CHANGELOG.md`)**:
   - Maintain a clear, human-readable `CHANGELOG.md` in the repository documenting all changes between `1.0.0` and `2.0.0` based on Git commit and PR history.

6. **Simple CLI Interface (No `--force` Flag)**:
   - Clean CLI interface (`pgmcp --upgrade`). Standard recovery for severely broken workspaces remains deleting `.pgmcp/` and running `pgmcp --init`.

---

## Architectural Constraints & Principles

- **CQS**: Separate query methods from command methods in `WorkspaceUpgrader`.
- **DIP**: Inject workspace paths, settings, and file writers.
- **SRP**: Keep `cli.py` concise and decouple version checking from `ServerBootstrapper`.

---

## Expected Results for Design & Planning

- High-level design for `WorkspaceUpgrader` service in `mcp_server/services/workspace_upgrader.py`.
- Decoupled `WorkspaceVersionValidator` design.
- Interface for `pgmcp --upgrade` CLI command in `mcp_server/cli.py`.
- Structured Upgrade Log format (`.pgmcp/logs/upgrade_YYYYMMDD_HHMMSS.json`).
- Package `CHANGELOG.md` template/structure for v2.0.0 release.
- Comprehensive unit test plan in `test_cli.py`.

---

## Related Documentation

- [docs/reference/tools/README.md](../../reference/tools/README.md)
- [docs/coding_standards/ARCHITECTURE_PRINCIPLES.md](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-07-21 | Agent | Initial draft with Approved Strategy for Issue #428 |
| 1.1.0 | 2026-07-22 | Agent | Refined with feedback: bootstrapper SRP version check decoupling, ConfigLoader schema validation reuse, single log file, no --force flag, no backup pruning |
| 1.2.0 | 2026-07-22 | Agent | Added build version bump mechanism (pyproject.toml SSOT) and package CHANGELOG.md distinction |

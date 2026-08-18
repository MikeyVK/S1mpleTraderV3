<!-- docs/development/issue428/planning.md -->
<!-- template=planning version=130ac5ea created=2026-07-22T16:21Z updated=2026-07-22 -->
# Planning Document - Implement `--upgrade` CLI command and release v2.0.0

**Status:** DEFINITIVE  
**Version:** 1.0.0  
**Last Updated:** 2026-07-22  

---

## Executive Summary

Implementation plan for Issue #428: *Implement `--upgrade` CLI command and release v2.0.0* divided into 3 sequential, independent, test-driven cycles:
1. **Cycle 1 (`C_VALIDATOR.1`)**: Decoupled version validation manager & upgrade log DTO.
2. **Cycle 2 (`C_UPGRADER.2`)**: Workspace upgrader service with fail-safe backups, asset renewal, state preservation, and upgrade log generation.
3. **Cycle 3 (`C_CLI_RELEASE.3`)**: CLI `--upgrade` command wiring, SSOT version bump to `2.0.0`, release `CHANGELOG.md`, and version consistency test alignment.

---

## Quality Gate & Test Architecture Obligations

1. **Test Code Architecture Principles**:
   - All test code must strictly comply with `ARCHITECTURE_PRINCIPLES.md`.
   - Injected dependency mocks in fixtures must strictly implement protocol interfaces (`IAtomicFileWriter`, etc.).
   - No uncleaned global state or environment variable mutations (must use `monkeypatch` or `try...finally`).
   - 100% Pyright/Mypy strict typing in test files.

2. **"No Test Ballast" Policy**:
   - Any exploratory, temporary, or duplicate test cases written during TDD cycles must be hard-removed before cycle completion.
   - Only durable, high-value unit and integration tests remain in `tests/`.

---

## TDD Cycles & Deliverables

### Cycle 1: `C_VALIDATOR.1` — Decoupled Version Validation & Upgrade Log DTO

**Goal:** Decouple workspace version validation from `ServerBootstrapper` into `WorkspaceVersionValidator` manager (SRP compliance) and define the immutable `UpgradeLogDTO` value object.

**Deliverables:**
- `D1.1`: `WorkspaceVersionValidator` manager (`mcp_server/managers/workspace_version_validator.py`) implementing `.version` file checks with descriptive `ConfigError` messages.
- `D1.2`: `UpgradeLogDTO` value object (`mcp_server/dtos/upgrade_log.py`) with `ConfigDict(frozen=True, extra="forbid")`.
- `D1.3`: Refactored `ServerBootstrapper._validate_version()` in `mcp_server/bootstrap.py` delegating to `WorkspaceVersionValidator`.
- `D1.4`: Unit test coverage (`tests/mcp_server/unit/managers/test_workspace_version_validator.py` & `test_upgrade_log.py`).

**Tests:**
- `tests/mcp_server/unit/managers/test_workspace_version_validator.py`
- `tests/mcp_server/unit/dtos/test_upgrade_log.py`

**Exit Criteria:**
- `WorkspaceVersionValidator` handles missing `.version`, read failures, and version mismatches cleanly with `--upgrade` guidance.
- `UpgradeLogDTO` is frozen and extra="forbid".
- `ServerBootstrapper._validate_version` delegates to validator without breaking existing tests.
- Pyright / Ruff quality gates 100% PASS.

---

### Cycle 2: `C_UPGRADER.2` — Workspace Upgrader Service

**Goal:** Implement `WorkspaceUpgrader` service in `mcp_server/services/workspace_upgrader.py` managing fail-safe backups, Smart Asset Preservation via `ConfigLoader`, dynamic state preservation, and upgrade log artifact generation.

**Deliverables:**
- `D2.1`: `WorkspaceUpgrader` service (`mcp_server/services/workspace_upgrader.py`) with command and query methods.
- `D2.2`: Fail-safe timestamped backup engine (`.pgmcp_backup_YYYYMMDD_HHMMSS/`) executed prior to asset mutation.
- `D2.3`: Smart Asset Preservation via `ConfigLoader` (valid user custom YAML configs in `.pgmcp/config/` are preserved; outdated/corrupt core assets updated from `mcp_server/assets/`).
- `D2.4`: Strict Dynamic State Preservation (preserving `state.json`, `deliverables.json`, `template_registry.json`, and `logs/`).
- `D2.5`: Structured log writing to `.pgmcp/logs/upgrade_YYYYMMDD_HHMMSS.json`.
- `D2.6`: Unit tests for `WorkspaceUpgrader` simulating backup creation, asset renewal, state preservation, and log writing on `tmp_path`.

**Tests:**
- `tests/mcp_server/unit/services/test_workspace_upgrader.py`

**Exit Criteria:**
- Backup directory `.pgmcp_backup_YYYYMMDD_HHMMSS/` created before any asset mutation.
- Dynamic runtime state files strictly preserved.
- Valid user custom YAML configs preserved via `ConfigLoader`.
- Single upgrade log JSON file written to `.pgmcp/logs/`.
- Zero test ballast; 100% quality gate pass.

**Dependencies:** Cycle 1 (`C_VALIDATOR.1`)

---

### Cycle 3: `C_CLI_RELEASE.3` — CLI Integration, Version Bump & Release v2.0.0

**Goal:** Wire `--upgrade` flag into `mcp_server/cli.py`, synchronize SSOT version files to `"2.0.0"`, add release `CHANGELOG.md`, and verify version consistency via automated unit tests.

**Deliverables:**
- `D3.1`: `cli.py` `--upgrade` CLI flag integration in `argparse`, checking `.pgmcp/` existence and calling `WorkspaceUpgrader`.
- `D3.2`: Version SSOT synchronization to `"2.0.0"` in `pyproject.toml`, `release_manifest.yaml`, and `settings.py`.
- `D3.3`: Repository release `CHANGELOG.md` documenting functional deltas between v1.0.0 and v2.0.0.
- `D3.4`: Test alignment in `test_cli.py` including `test_version_consistency` to verify version parity across SSOT files (`pyproject.toml`, `release_manifest.yaml`, `settings.py`, `.version`).

**Tests:**
- `tests/mcp_server/unit/test_cli.py`

**Exit Criteria:**
- `pgmcp --upgrade` triggers upgrader service and exits `0` on success or `1` on error.
- Version SSOT bump to `"2.0.0"` synchronized across `pyproject.toml`, `release_manifest.yaml`, `settings.py`.
- Repository `CHANGELOG.md` added for v2.0.0.
- `test_version_consistency` passes cleanly.
- Quality gates score 10.00/10 with zero Pyright warnings and zero test ballast.

**Dependencies:** Cycle 2 (`C_UPGRADER.2`)

---

## Related Documentation

- [design.md](design.md)
- [research.md](research.md)
- [docs/coding_standards/ARCHITECTURE_PRINCIPLES.md](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-07-22 | Agent | Initial planning document for Issue #428 |

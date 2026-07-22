# Planning - Issue #435: Workspace Version Tracking

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-07-19

---

## Summary

This planning document outlines the test-driven implementation plan for Issue #435. The feature will be delivered in three logical cycles, ensuring backward compatibility, fail-fast but graceful validation in a degraded server mode, and a zero-regression impact on the existing test suite.

---

## Scope & Prerequisites

- **Scope In:**
  - Support for `bypass_version_check` in `ServerSettings` and `Settings.from_env()`.
  - Writing `.pgmcp/.version` during workspace initialization via `pgmcp --init`.
  - Validating workspace version during `ServerBootstrapper.bootstrap()`.
  - Transitioning to `DegradedMCPServer` on validation failure.
- **Scope Out (Deferred):**
  - Schema versioning of dynamic data files (`state.json`, `deliverables.json`). This is deferred as explicitly identified follow-up work.
  - Implement `--upgrade` CLI command (issue #428).

---

## TDD Cycles

### Cycle 1: C_SETTINGS.1
- **Goal:** Update `ServerSettings` and `Settings.from_env` to support version check bypass (incorporating QA review for explicit environment variable configuration).
- **Production Files:**
  - `mcp_server/config/settings.py`
- **Tests:**
  - `tests/mcp_server/unit/config/test_settings.py:test_bypass_version_check_default`
  - `tests/mcp_server/unit/config/test_settings.py:test_bypass_version_check_from_env_var`
- **Deliverables:**
  - `[D1.1]` Add `bypass_version_check` setting field to `ServerSettings` in `settings.py`.
  - `[D1.2]` Add `PGMCP_BYPASS_VERSION_CHECK` env var parsing to `Settings.from_env()` in `settings.py`.
  - `[D1.3]` Add unit tests in `test_settings.py` verifying default values, custom env var values, and precedence.
- **Success Criteria / Exit Criteria:**
  - `ServerSettings` exposes `bypass_version_check` correctly defaulted.
  - `Settings.from_env()` supports explicit `PGMCP_BYPASS_VERSION_CHECK` environment variable parsing.
  - Zero file I/O operations occur inside Settings initialization.
- **Dependencies:** None.

---

### Cycle 2: C_CLI_INIT.2
- **Goal:** Update `pgmcp --init` to write the server version to `.pgmcp/.version` after copying static assets.
- **Production Files:**
  - `mcp_server/cli.py`
- **Tests:**
  - `tests/mcp_server/unit/test_cli.py:test_cli_init_success` (extended to assert `.version` file creation and value)
- **Deliverables:**
  - `[D2.1]` Update `args.init` block in `cli.py` to write version to `resolved_server_root / ".version"`.
  - `[D2.2]` Extend `test_cli_init_success` in `test_cli.py` to assert `.version` file creation and contents.
- **Success Criteria / Exit Criteria:**
  - `pgmcp --init` creates `.version` file with correct version string.
  - CLI init unit test passes cleanly.
- **Dependencies:** C_SETTINGS.1

---

### Cycle 3: C_BOOTSTRAP.3
- **Goal:** Implement startup version validation in `ServerBootstrapper` and verify graceful transition into `DegradedMCPServer`.
- **Production Files:**
  - `mcp_server/bootstrap.py`
- **Tests:**
  - `tests/mcp_server/unit/server/test_bootstrap.py:test_bootstrap_missing_version_raises_config_error`
  - `tests/mcp_server/unit/server/test_bootstrap.py:test_bootstrap_version_mismatch_raises_config_error`
  - `tests/mcp_server/unit/test_cli.py` (extended/added to check transition to `DegradedMCPServer` on `bootstrap()` validation failure)
- **Deliverables:**
  - `[D3.1]` Add startup version verification in `ServerBootstrapper.bootstrap()` in `bootstrap.py`.
  - `[D3.2]` Add bootstrap unit tests for missing version, version mismatch, and successful match.
  - `[D3.3]` Add integration test checking transition to `DegradedMCPServer` on validation failure.
- **Success Criteria / Exit Criteria:**
  - Validation checks version file and throws `ConfigError` on mismatch or missing file when not bypassed.
  - `DegradedMCPServer` successfully instantiates and reports `UNHEALTHY` status on startup validation failures.
  - All existing workspace tests pass cleanly via the pytest check bypass.
- **Dependencies:** C_CLI_INIT.2

---

## Risks & Mitigations

- **Test Suite Blast Radius:** 50+ mock tests instantiate `.pgmcp` dynamically without version files.
  - *Mitigation:* Bypassing validation in pytest via `bypass_version_check` default factory using `PYTEST_CURRENT_TEST` env var check.
- **Strict Sequencing Constraint:** Cycle 1 must be implemented first. Implementing validation (Cycle 3) before settings/bypass are in place would break all test suites instantly.
  - *Mitigation:* Sequential cycle execution and green verification before moving to the next cycle.

---

## Typing Obligations

All new parameters, functions, and classes (including `bypass_version_check` in `ServerSettings` and bootstrapper validation logic) must be fully type-annotated in compliance with PEP 561. Type annotations must compile without errors under `pyright` / `mypy` following the guidelines in `docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md`. No broad `# type: ignore` or `Any` should be used unless explicitly scoped and justified.

---

## Quality-Gate Expectations

Before transitioning from the `implementation` phase to the `validation` phase, and prior to opening a PR, the implementer must execute quality gates using `run_quality_gates(files=[...])` on all modified files (`settings.py`, `cli.py`, `bootstrap.py`, and test files). A pylint score of **10.00/10** and a successful type-checking pass are strictly required.

---

## Cleanup Expectations

All tests that write `.version` files or mock workspace components must run inside isolated temporary directories (e.g., using pytest's `tmp_path` fixture or mocking file system operations) to ensure no artifacts are left behind in the workspace or repository root after test runs.

---

## Related Documentation

- [research.md](research.md)
- [design.md](design.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-19 | Agent | Initial Definitive Planning Document |

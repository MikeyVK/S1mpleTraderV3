<!-- docs\development\issue386\planning.md -->
<!-- template=planning version=130ac5ea created=2026-07-08T19:39Z updated=2026-07-08T22:02Z -->
# Planning for renaming env var prefix MCP to PGMCP

**Status:** APPROVED  
**Version:** 1.2  
**Last Updated:** 2026-07-08

---

## Summary

Sequential implementation plan for renaming all `MCP_*` environment variables to `PGMCP_*` across production code, tests, and documentation, under a clean break strategy.

---

## Scope Boundaries

### In Scope:
*   Direct rename of the 7 identified environment variables in `mcp_server/config/settings.py`.
*   Direct rename of workspace-related environment variable lookups in `mcp_server/core/proxy.py`.
*   Direct rename of restart marker directory resolution in `mcp_server/tools/admin_tools.py`.
*   Direct rename of environment variable setups in `tests/conftest.py` and mocks in `tests/mcp_server/unit/config/test_settings.py`, `tests/mcp_server/unit/conftest.py`, `tests/mcp_server/unit/test_server.py`, `tests/mcp_server/unit/tools/test_cycle_tools.py`, and `tests/mcp_server/unit/test_c260_c2_state_root_injection.py`.
*   Addition of structural unit test checks in `tests/mcp_server/unit/config/test_c_settings_structural.py`.
*   All active documentation files (`README.md` and manuals).
*   User-facing and editor configuration templates (`mcp_config.json`, `mcp.json`, and `docs/setup/mcp.json`).

### Out of Scope:
*   Renaming of non-environment variables starting with `MCP_` (e.g. `__MCP_RESTART_REQUEST__` output marker is kept as-is as it is not an env var).
*   Adding backward-compatibility layer (e.g., fallback reading of legacy `MCP_*` env vars).

---

## Prerequisites
1.  Approved Strategy from Research (Clean Break).
2.  All quality gates passing on the base branch.

---

## TDD Cycles

### Cycle 1: Core Refactoring (Production Code & Tests)

**Goal:** Rename all `MCP_*` variables to `PGMCP_*` in production settings, proxy, tools, and mock test environments.

**Production Files affected:**
*   [mcp_server/config/settings.py](file:///c:/temp/pgmcp/mcp_server/config/settings.py)
*   [mcp_server/core/proxy.py](file:///c:/temp/pgmcp/mcp_server/core/proxy.py)
*   [mcp_server/tools/admin_tools.py](file:///c:/temp/pgmcp/mcp_server/tools/admin_tools.py)

**Test Files affected:**
*   [tests/conftest.py](file:///c:/temp/pgmcp/tests/conftest.py)
*   [tests/mcp_server/unit/conftest.py](file:///c:/temp/pgmcp/tests/mcp_server/unit/conftest.py)
*   [tests/mcp_server/unit/config/test_settings.py](file:///c:/temp/pgmcp/tests/mcp_server/unit/config/test_settings.py)
*   [tests/mcp_server/unit/test_server.py](file:///c:/temp/pgmcp/tests/mcp_server/unit/test_server.py)
*   [tests/mcp_server/unit/tools/test_cycle_tools.py](file:///c:/temp/pgmcp/tests/mcp_server/unit/tools/test_cycle_tools.py)
*   [tests/mcp_server/unit/test_c260_c2_state_root_injection.py](file:///c:/temp/pgmcp/tests/mcp_server/unit/test_c260_c2_state_root_injection.py)
*   [tests/mcp_server/integration/mcp_server/conftest.py](file:///c:/temp/pgmcp/tests/mcp_server/integration/mcp_server/conftest.py)
*   [tests/mcp_server/unit/config/test_c_settings_structural.py](file:///c:/temp/pgmcp/tests/mcp_server/unit/config/test_c_settings_structural.py)

**Tests:**
*   `pytest tests/mcp_server/unit/config/test_settings.py`
*   `pytest tests/mcp_server/unit/test_c260_c2_state_root_injection.py`
*   `pytest tests/mcp_server/unit/test_server.py tests/mcp_server/unit/tools/test_cycle_tools.py`
*   `pytest tests/mcp_server/unit/config/test_c_settings_structural.py`

**Success Criteria:**
*   All unit tests pass and a structural test confirms that no `MCP_*` variables remain in `settings.py` source code.

**Deliverables:**
*   `D1.1`: Renaming in `settings.py` (`from_env` method).
*   `D1.2`: Renaming in `proxy.py` (audit logs directory derivation).
*   `D1.3`: Renaming in `admin_tools.py` (`verify_server_restarted`).
*   `D1.4`: Update of pytest-monkeypatches in `test_settings.py`, `tests/conftest.py`, `tests/mcp_server/unit/conftest.py`, `test_c260_c2_state_root_injection.py`, `test_server.py`, and `test_cycle_tools.py`.
*   `D1.5`: Add a structural unit test to verify that no `MCP_*` prefixes remain in `settings.py` source code.

---

### Cycle 2: Sync Documentation & Configs

**Goal:** Update all active documentation and agent configurations to use the `PGMCP_*` prefix.

**Files affected:**
*   [README.md](file:///c:/temp/pgmcp/README.md)
*   [docs/reference/server-configuration.md](file:///c:/temp/pgmcp/docs/reference/server-configuration.md)
*   [docs/reference/config-loading-architecture.md](file:///c:/temp/pgmcp/docs/reference/config-loading-architecture.md)
*   [docs/reference/tools/README.md](file:///c:/temp/pgmcp/docs/reference/tools/README.md)
*   [docs/manuals/architecture.md](file:///c:/temp/pgmcp/docs/manuals/architecture.md)
*   [docs/setup/dev-isolation.md](file:///c:/temp/pgmcp/docs/setup/dev-isolation.md)
*   [docs/setup/README.md](file:///c:/temp/pgmcp/docs/setup/README.md)
*   [docs/setup/mcp.json](file:///c:/temp/pgmcp/docs/setup/mcp.json)
*   [docs/agents/antigravity/mcp_config.json](file:///c:/temp/pgmcp/docs/agents/antigravity/mcp_config.json)
*   [docs/agents/vscode/copilot/mcp.json](file:///c:/temp/pgmcp/docs/agents/vscode/copilot/mcp.json)

**Tests:**
*   Quality gates check: `run_quality_gates(scope='branch')`

**Success Criteria:**
*   All modified documentation and JSON configs are validated, and quality gates pass.

**Deliverables:**
*   `D2.1`: Updates in `README.md` and manuals.
*   `D2.2`: Updates in agent configurations (`mcp_config.json`, `mcp.json`, and `docs/setup/mcp.json`).

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Test suite fails to catch a missed `MCP_*` lookup | We implement a structural unit test in `test_c_settings_structural.py` that inspects the source code of `settings.py` for any remaining references to `MCP_*`. |
| Standalone proxy logs directory breaks due to mismatch | We verify that `test_proxy.py` and proxy startup tests are executed and pass. |

---

## Related Documentation
*   [docs/development/issue386/research.md](file:///c:/temp/pgmcp/docs/development/issue386/research.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-08 | Agent | Initial sequential implementation plan |
| 1.1 | 2026-07-08 | Agent | Expanded scope to include test files and setup/mcp.json based on QA feedback |
| 1.2 | 2026-07-08 | Agent | Added test_server.py and test_cycle_tools.py to Cycle 1 scope and deliverables |

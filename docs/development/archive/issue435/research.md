<!-- docs\development\issue435\research.md -->
<!-- template=research version=8b7bb3ab created=2026-07-19T19:58Z updated= -->
# Research - Issue #435: Workspace Version Tracking

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-07-19

---

## Problem Statement

Currently, when a workspace is initialized via 'pgmcp --init', there is no version file written to record the package/wheel version. If a new package version is installed, the running server cannot identify when the workspace configurations or templates are out of date compared to the code, leading to schema validation failures or outdated scaffolding.

## Research Goals

- Define version file format and location under '.pgmcp/'
- Establish validation mechanism in ServerBootstrapper to trigger degraded mode on version mismatch
- Identify test environment bypass options to prevent regression in mock workspaces
- Formulate a strategy for state file versioning as deferred follow-up work

---

## Findings

### 1. Workspace Initialization and Tool Logic
- **CLI Initialization (`pgmcp --init`):** Defined in [cli.py](file:///c:/temp/pgmcp/mcp_server/cli.py#L31-L59). When `--init` is called, it copies release assets from the package's internal assets directory to `.pgmcp/`.
- **Project/Issue Initialization (`initialize_project`):** Defined in [project_manager.py](file:///c:/temp/pgmcp/mcp_server/managers/project_manager.py#L117-L193). Sets up issue-level state files (e.g. `state.json` and `deliverables.json`).
- **Package Version Resolution:** Defined in [settings.py](file:///c:/temp/pgmcp/mcp_server/config/settings.py#L27-L40) via `importlib.metadata`. The running version is accessible as `Settings().server.version`.

### 2. Static Assets vs. State File Versioning
- **Category A (Configs) & Category B (Templates):** These are copied statically during initialization. Outdated versions compared to running code can cause bootstrapper failures or template rendering errors.
- **Category C (Docs, Guidelines, Rules):** These are also copied during initialization. They have no code dependencies but need version alignment to ensure the AI agent is always following the correct active directives (e.g. in `AGENTS.md` and `.agents/rules/`).
- **Dynamic State Files:** Best practices dictate these should eventually have their own schema versions and a migration registry in Python, separating data lifecycle from CLI installation lifecycle.

### 3. Blast Radius and Test Impact
- **Mock Workspaces:** More than 50 test files (e.g. [artifact_test_harness.py](file:///c:/temp/pgmcp/tests/mcp_server/fixtures/artifact_test_harness.py#L208-L235)) instantiate a bare `.pgmcp/` directory dynamically without calling `pgmcp --init`.
- **Enforcement Bypass:** Strict version checking would break these tests unless we bypass checks when running under pytest (by detecting the `PYTEST_CURRENT_TEST` environment variable).

---

## Approved Strategy

- **Workspace Version Marker:** We will write a plain-text version string to `.pgmcp/.version` during `pgmcp --init`.
- **Bootstrapper Validation:** On server startup in `ServerBootstrapper.bootstrap()`, the server will check if `.pgmcp/.version` exists and matches the running package version.
- **Degraded Server Mode:** If `.version` is missing or mismatched, `bootstrap()` will raise a `ConfigError`. This will be caught by `cli.py` to instantiate `DegradedMCPServer` (exposing only `HealthCheckTool` marked as `UNHEALTHY` with the specific mismatch reason).
- **Test Environment Bypass:** The startup version validation will be bypassed if `os.environ.get("PYTEST_CURRENT_TEST")` is detected.

---

## Deferred Work

We have identified the following items to be deferred to separate follow-up issues:
1. **Dynamic State File Versioning:** Add an explicit `"schema_version"` integer to `state.json` and `deliverables.json`, along with a lightweight in-memory migration registry in the python state repositories. This prevents domain/manager logic from becoming cluttered with legacy Pydantic resolver fallbacks.
2. **Upgrade CLI Command:** Implementation of the `--upgrade` command (issue #428) which will parse the baseline `.version` and perform asset upgrades.

---

## Expected Results

- Running `pgmcp --init` successfully writes the running package version to `.pgmcp/.version`.
- Modifying `.pgmcp/.version` to a mismatching version (or deleting it) causes the server to start in degraded mode, exposing an unhealthy health check.
- All workspace tests continue to pass without needing manual `.version` mocking due to the pytest environment bypass.

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-19 | Agent | Initial Definitive Research Document |

<!-- docs\development\issue429\deferred_work_notice.md -->
<!-- template=generic_doc version=43c84181 created=2026-07-17T22:10Z updated= -->
# Deferred Work Notice: Graceful Server Initialization & Config Validation

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-07-17

---

## Purpose

Record findings about initialization crashes for a future feature issue.

---

## Summary

Deferred work notice capturing initialization crash findings (chicken-and-egg startup crash, package version crash, template validation crash) for a new feature issue.

## Context
During the analysis of the template workspace implementation, critical vulnerabilities were discovered in the MCP Server's startup sequence. These currently cause "hard" server crashes (exit code 1), which means the AI agent is confronted with an unreachable server (Tools not available) rather than clear error messages.

Because these stability improvements fall outside the initial scope of the current implementation cycle and we strictly adhere to workflow governance, these findings are recorded here as deferred work. This document will serve as the foundation for a new Feature Issue.

## Findings

### 1. Hard Crash on Package Version Mismatch (Wheel)
- **Location:** `mcp_server/config/settings.py` -> `_default_server_version()`
- **Triggers:** The `ServerSettings.version` property attempts to retrieve the installed Python package version (`mcp_server`) via `importlib.metadata.version()`.
- **Impact:** If the package is not explicitly installed as a distribution (for instance, when running locally via scripts without `pip install -e .`), `importlib.metadata` raises a `PackageNotFoundError`. Because this happens during the initialization of the global `Settings` object (well before `ServerBootstrapper`), it results in an immediate fatal crash of the entire process.
- **Current Usage:** This field is currently used purely for informational purposes for the `--version` CLI flag and the output of the `HealthCheckTool`.

### 2. Hard Crash on Config Version Mismatch (`artifacts.yaml`)
- **Location:** `mcp_server/config/schemas/artifact_registry_config.py`
- **Triggers:** The schema enforces `version: Literal["1.0.0"]` via Pydantic.
- **Impact:** If the loaded `artifacts.yaml` contains a version string that deviates (or is missing), it results in a `ValidationError` in the `ConfigLoader`. Since this occurs within `ServerBootstrapper._build_config_layer()`, the server bootstrapping process crashes. A chicken-and-egg problem arises: without a loaded configuration, there is no MCP interface available to report the error to the agent.

### 3. Hard Crash on Template Version Mismatch
- **Location:** `mcp_server/managers/artifact_manager.py` -> `_validate_template_versions()`
- **Triggers:** During `__init__`, the manager proactively validates the templates. If `extract_template_version` or `validate_compatibility` fails, a `ConfigError` is raised.
- **Impact:** An error in a single template prevents the `ArtifactManager` (and consequently the `ServerBootstrapper`) from starting up. This blocks all tools and interactions with the MCP Server.

## Scope for the new Feature Issue
- Prevent the startup-crash (chicken-and-egg) problem for faulty configurations.
- Decouple error reporting so independent error situations can be caught and communicated locally.
- Investigate the possibility of executing "fail-fast" directly at the tool invocation level (e.g., in `scaffold_artifact`).
- Investigate a "Degraded Mode" (Safe Mode) or similar pattern for the MCP server when critical configuration errors occur.

*(This document serves as input for the issue-author role when creating the follow-up issue)*
## Related Documentation
None
---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-17 | Agent | Initial draft |
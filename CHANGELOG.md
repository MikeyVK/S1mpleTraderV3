<!-- CHANGELOG.md -->
<!-- template=generic_doc version=43c84181 created=2026-07-22T17:47Z updated=2026-07-22T20:12Z -->
# Changelog

All notable changes to Phase-Gate MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed
- **Breaking — Generic documentation search**: Removed the `search_documentation` MCP tool, its dedicated indexing/search services, contracts, tests, and agent allowlist entries. Agents now use host-native repository search; upgraded MCP clients must refresh or reconnect before requesting the new tool inventory (#443).

## [2.0.0] - 2026-07-22

### Added
- **Workspace Upgrade Command (`pgmcp --upgrade`)**: Automated workspace upgrade mechanism orchestrating fail-safe timestamped backups (`.pgmcp_backup_YYYYMMDD_HHMMSS/`), smart asset renewal, and structured audit logs (`.pgmcp/logs/upgrade_YYYYMMDD_HHMMSS.json`) (#428).
- **Workspace Version Validation Manager (`WorkspaceVersionValidator`)**: Decoupled manager enforcing `.version` file existence and runtime version parity with actionable CLI advice (`pgmcp --upgrade` / `pgmcp --init`) (#428, #435, #437).
- **Upgrade Log Telemetry (`UpgradeLogDTO`)**: Immutable frozen Pydantic model (`extra="forbid"`) capturing structured telemetry for workspace upgrades (#428).
- **Frictionless File Editing (`safe_edit_file`)**: Clean Break refactor introducing a 4-operation schema (`replace`, `append`, `rewrite`, `pattern_replace`) with `must_exist=True` governance and fuzzy-match `difflib` error suggestions (#433, #440).
- **Atomic File Writing (`IAtomicFileWriter` & `AtomicFileWriter`)**: Safe atomic temp-swap file writer utility guaranteeing zero corrupted partial writes (#433).
- **Graceful Server Initialization (`DegradedMCPServer`)**: Fallback server mode serving `health_check` and reporting diagnostic remediation advice on `ConfigError` or missing directories without dropping stdio connection (#432, #434).
- **Dynamic State File Versioning**: Version tracking and preservation for runtime state files (`state.json`, `deliverables.json`, `template_registry.json`) (#438, #439).
- **Standalone Wheel Packaging & CLI Bootstrap**: `pgmcp` CLI entry points (`--init`, `--upgrade`, `--version`), deferred release asset bundling via `release_manifest.yaml`, and `scripts/build_package.py` pre-build pipeline (#416, #420, #421, #426).

### Changed
- **Version SSOT Parity**: Package release version synchronized to `2.0.0` across `pyproject.toml`, `.pgmcp/config/release_manifest.yaml`, and `mcp_server/config/settings.py` (#428).
- **Environment Variable Standardization**: Renamed environment variable prefix from `MCP_*` to `PGMCP_*` (`PGMCP_WORKSPACE_ROOT`, `PGMCP_SERVER_PROJECT_DIR`, `PGMCP_BYPASS_VERSION_CHECK`) (#386, #425).
- **Template Workspace Initiative**: Consolidated template configuration and Jinja2 artifact templates under `.pgmcp/templates/` with workspace-owned schema packs (#349, #427, #429, #431).
- **Bootstrapper Decoupling**: Refactored `ServerBootstrapper._validate_version` to delegate version validation responsibilities to `WorkspaceVersionValidator` (#428).
- **Force Transition Tool Interface**: Renamed parameter `human_approval` to `human_approval_message` across force phase/cycle transition tools for explicit audit logging (#430, #436).

### Fixed
- **Dynamic State Preservation**: Guaranteed preservation of dynamic runtime state files (`state.json`, `deliverables.json`, `template_registry.json`, `logs/`) during workspace initialization and upgrades (#428, #438).
- **Dirty Worktree Commit Defect**: Fixed worktree handling in `git_add_or_commit` (#422, #424).

## [1.0.0] - 2026-07-06

### Added
- **Phase-Gate MCP Framework**: Core architecture supporting phase-gated software engineering workflows (`feature`, `bug`, `docs`, `refactor`, `hotfix`, `epic`, `custom`).
- **MCP Server Tools Registry**: 47 specialized tools covering Git operations, GitHub issues/PR management, template scaffolding, test execution, quality gate validation, and work context discovery.
- **Three-Agent Model Protocol**: Built-in instructions and boundary controls for Coordination (`@co`), Implementation (`@imp`), and QA (`@qa`) agents.
- **Quality Gates Engine**: Automated linting (Ruff), type checking (Pyright/Mypy), line length enforcement, and import checking.
- **Template Scaffolding Engine**: Jinja2-powered artifact scaffolding with strict metadata headers and schema validation (`scaffold_artifact`, `scaffold_schema`).

[2.0.0]: https://github.com/MikeyVK/phase-gate-mcp/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/MikeyVK/phase-gate-mcp/releases/tag/v1.0.0

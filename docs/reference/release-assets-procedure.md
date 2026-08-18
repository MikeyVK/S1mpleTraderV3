<!-- docs\reference\mcp\release-assets-procedure.md -->
<!-- template=generic_doc version=43c84181 created=2026-07-05T20:37Z updated= -->
# Reference Guide: Release Assets Procedure and Manifest Specification

**Status:** ACTIVE  
**Version:** 1.0.0  
**Last Updated:** 2026-07-08

---

## Purpose

Specify the folder structure, manifest format, and build-time synchronization procedure for packaging default configuration assets, templates, agent instructions, and workflows into the installable pip wheel.

## Prerequisites

Read these first:
1. docs/setup/README.md
---

## Summary

Defines a strict build-time copy regime from the workspace sources (including docs/agents/ and slash commands) to mcp_server/assets/ driven by a release_manifest.yaml, ensuring a clean and IDE-agnostic bootstrapping process.

---

- Define docs/agents/ as the SSOT for rules and slash commands
- Introduce release_manifest.yaml to declare release-bound files
- Automate assets folder compilation in the package build pipeline

---

## 1. Specification: Agent Instruction Sources (SSOT)

To avoid duplication debt across host-specific layouts, the repository designates
`docs/agents/` as the single source of truth for distributable agent instructions,
workflows, and Codex skills:

```text
docs/agents/
├── antigravity/                   # Google Antigravity instructions and workflows
├── vscode/
│   └── copilot/                   # VS Code/Copilot agents and prompts
└── codex/                         # Codex rules, workflows, and discoverable skills
```

Each host directory preserves the structure needed to deploy that host's active files.
Local MCP connection configuration, absolute workspace paths, credentials, runtime
state, and other machine-specific settings are not part of this SSOT.

### 1.1. Local Development Synchronization (Dev Sync)

Authoritative changes are made under the appropriate `docs/agents/<host>/` directory
and are then deployed to the host's active runtime locations:

- `docs/agents/antigravity/` → the active Antigravity rules and workflows.
- `docs/agents/vscode/copilot/` → `AGENTS.md`, `.github/agents/`, and
  `.github/prompts/`.
- `docs/agents/codex/` → `.agents/`, excluding local files such as
  `mcp_config.json`.

Active runtime copies may remain version-controlled when the host requires them in a
repository checkout, but they are derived copies and must remain byte-equivalent to
their authoritative source. The build manifest packages `docs/agents/` directly; it
does not package active runtime locations.

---

## 2. Release Manifest Specification (`release_manifest.yaml`)

A structured configuration file `release_manifest.yaml` located under `.pgmcp/config/release_manifest.yaml` defines which files are release-bound and packaged into the wheel assets:

```yaml
version: "1.0.0"
assets:
  - source: ".pgmcp/config"
    target: "config"
  - source: ".pgmcp/templates"
    target: "templates"
  - source: "docs/agents"
    target: "agents"
  - source: "docs/coding_standards"
    target: "docs/coding_standards"
  - source: "docs/manuals"
    target: "docs/manuals"
  - source: "docs/reference"
    target: "docs/reference"
  - source: "docs/setup"
    target: "docs/setup"
```

---

## 3. Build-Time Assembly Procedure

During the Python wheel compilation step:
1. The packaging utility clears `mcp_server/assets/` completely.
2. It parses `release_manifest.yaml`.
3. It copies specified paths from the repository sources to the subdirectories under `mcp_server/assets/`.
4. The `pyproject.toml` file bundles `mcp_server/assets/` via `package-data`, resulting in a clean standalone wheel.

---

## 4. Bootstrapping Execution (`pgmcp --init`)

The CLI `pgmcp --init` performs a strict flat copy of `mcp_server/assets/` to `.pgmcp/` in the user's workspace:
- It checks if `.pgmcp/` already exists. If yes, it aborts (idempotency guard).
- If no, it copies `mcp_server/assets/` directly to `.pgmcp/`.
- No files are written outside `.pgmcp/` to keep the user's project workspace clean.

---

## Related Documentation
- **[docs/manuals/user-guide.md][related-1]**

<!-- Link definitions -->

[related-1]: docs/manuals/user-guide.md

---

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-07-05 | Agent | Initial draft |
| 1.0.0 | 2026-07-08 | Agent | Document build automation, manifest paths, and schema matching implementation #420 |

<!-- docs\development\issue432\research.md -->
<!-- template=research version=8b7bb3ab created=2026-07-18T17:49Z updated= -->
# Bug #432 Research: Graceful Server Initialization

**Status:** APPROVED  
**Version:** 1.1  
**Last Updated:** 2026-07-18

---

## Problem Statement

Vulnerabilities in the MCP Server's startup sequence cause hard crashes on config validation errors. Crucially, the current sequence conflates actual server-related initialization issues with template vs. artifact (config) version mismatches. Template and artifact version mismatches have nothing to do with the server itself and only affect the template/artifact/scaffolding tools, yet they currently bring down the entire server and break the agent connection. 

Furthermore, the `ConfigError` that triggers this crash is directly caused by hardcoded `version: Literal["1.0.0"]` fields inside the Pydantic schemas when they mismatch with disk configs. While initially considered an architectural violation, deeper analysis reveals these Literals act as structural type tags tightly coupled to the Python fields. Removing them would violate SRP and Schema Cohesion, meaning the fix must occur in the error handling layers (CLI and ArtifactManager) rather than by altering the schemas.

## Research Goals

1. Analyze the current startup sequence in `cli.py` and `server.py` to trace where `ConfigLoader` crashes bubble up.
2. Verify if the `mcp_server` (wheel) version plays any actual role in the domain data structures or if it's purely informational.
3. Assess the Pydantic schemas (e.g., `ArtifactRegistryConfig`) to verify the hardcoded `Literal["1.0.0"]` versions and their architectural implications.
4. Separate the concerns between system-level OS errors and domain-level configuration errors.

## Root Cause Candidates

This issue was originally discovered during the implementation of #429 and deferred for separate handling. The server uses `ConfigLoader` which raises `ConfigError` or `FileNotFoundError` on startup for invalid configurations or template mismatches. This correctly enforces the architectural 'Fail-Fast' principle at the domain layer. However, in `cli.py`, this exception is unhandled and causes a non-zero exit code process crash, terminating the `stdio` connection used by the MCP protocol. Because MCP relies on JSON-RPC over `stdio`, the agent experiences an unexpected EOF, perceives the tools as 'dead', and presents an unrecoverable initialization failure to the user.

---

## Findings

1. **Separation of Concerns (Server vs. Tools)**: Template and artifact version mismatches are strictly related to scaffolding tools. They should not block server bootstrap. The server must initialize successfully regardless of template mismatches, isolating the failure to the specific scaffolding tools that rely on those templates.
2. **Protocol Support for Server Errors**: For actual server configuration errors, the MCP specification (using JSON-RPC 2.0) allows returning a JSON-RPC error object during the `initialize` handshake, rather than returning a successful capability negotiation.
3. **Differentiation**: True server-binding or OS-level infrastructure issues should still fail-fast and crash the process. Domain-specific server configuration errors must be translated to MCP protocol errors. Template/artifact mismatches should simply be isolated to tool-level validation.
4. **Consumer Impact**: As confirmed, there are no CLI/CI consumers relying on the `exit code > 0` behavior, clearing the path to catch actual server config errors in the CLI and handle them gracefully for MCP clients.

---

## Blast Radius & Boundaries

1. **Pydantic Schema Files (16 files)**: Initially considered a risk, it is now decided that the `Literal["1.0.0"]` tags will **not** be removed. The blast radius for schema files is therefore zero.
2. **ConfigLoader (Tests & Logic)**: Since schema versions remain untouched, `ConfigLoader` and its unit tests will remain unchanged. Validation continues to work as intended.
3. **CLI Boundary (`cli.py`)**: Modifying the server initialization entrypoint to catch `ConfigError` and boot a Degraded Server affects the integration tests that might currently assert non-zero exit codes. The boundary behavior changes from "crash and burn" to "connect and explain".
4. **Agent Client Compatibility**: The MCP agent (consumer of `pgmcp`) strongly benefits from a stable `stdio` connection. Falling back to a degraded server rather than crashing explicitly supports the agent's need to report status to the user.

## Approved Strategy

Clean break strategy with distinct handling paths:
1. **Architectural Purity & Version Validation**: Retain the `version: Literal["1.0.0"]` constraints in the Pydantic schemas. These act as necessary structural type tags. Removing them would push business logic into the loader, violating SRP and Cohesion.
2. **Template/Artifact Version Mismatches**: Decouple these from the global server bootstrap validation. The server must initialize normally even if templates mismatch. The mismatch must be handled locally by the scaffolding tools (e.g., returning a validation error when the specific tool is invoked).
3. **True Server-Related Config Errors (Degraded Server Pattern)**: Modify the CLI entrypoint to catch domain-level server `ConfigError`s. Instead of exiting the process, the CLI will instantiate a **Degraded Server**. This minimal MCP server successfully accepts the agent's `initialize` handshake but registers only a single tool (e.g. `get_startup_error`). This allows the agent to gracefully read the error and explain it to the user without losing its connection.
4. **Infrastructure Errors**: True server infrastructure errors (e.g., failing to bind, OS faults) will continue to fail fast.
No separate `--stdio` flag is needed because no CLI/CI consumers rely on the non-zero exit code.

---

## Expected Results

1. Template/artifact version mismatches have zero impact on global server initialization; they only affect the specific scaffolding tools.
2. Actual server configuration errors do not cause a process crash, but instead return a diagnostic error message via the MCP protocol.
3. True infrastructure faults continue to fail-fast.

## Related Documentation

- **[docs/development/issue429/deferred_work_notice.md][related-1]**
- **Issue #429**

<!-- Link definitions -->
[related-1]: ../issue429/deferred_work_notice.md
## Deferred Work

To prevent scope creep, the following items are explicitly deferred and must be picked up by the `@co` agent during the Documentation/Ready phase for assignment to a new feature/tech-debt issue:

1. **Workspace Version Tracking**: Implement a mechanism during `pgmcp --init` to record the initialized wheel version in the workspace (e.g., in a dedicated configuration file, **not** in `.pgmcp/state.json` which is strictly for branch state). This will enable the CLI to detect mismatches gracefully and provide targeted upgrade instructions.
2. **Upgrade Tooling**: The actual implementation of a `pgmcp --upgrade` command and associated migration scripts is deferred.

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-18 | Agent | Initial draft |
| 1.1 | 2026-07-18 | Agent | Updated strategy: Retain Pydantic Literals |

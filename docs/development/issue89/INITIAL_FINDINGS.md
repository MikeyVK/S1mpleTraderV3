# Issue 89 — Initial Research Findings (Tools Disabled / Session Poisoning)

**Status:** DRAFT
**Author:** GitHub Copilot
**Created:** 2026-01-06

## Context & Scope

Issue #89 tracks an intermittent failure in VS Code Copilot Chat / MCP where tools become uncallable within a chat session and the UI reports a misleading message like “Tool … is currently disabled by the user”. The goal of this note is to capture what we know *before* attempting to reproduce, and to define evidence we should capture when we do.

Scope constraints for this document:
- No reproduction attempts in this session.
- Focus on hypotheses that can explain "works in new chat" and "sometimes only some tools".
- Prefer mitigations that are low-risk and server-side where possible.

## Observed Symptoms (Issue #89)

From the issue body and session handover:
- Within a single Copilot Chat session, at least one MCP tool (e.g. `mcp_st3-workflow_get_issue`) can start failing with:
  - “Tool … is currently disabled by the user”
- The message is misleading: starting a new chat frequently restores the tool.
- The failure can affect read tools and sometimes write tools, suggesting it is not a policy/high-risk block.
- There is a known, separate UI/rendering error sometimes seen:
  - “Failed to render content: ModelService: Cannot add model because it already exists!”
  This is treated as an extension/UI rendering bug and not necessarily the underlying tool failure.

## What We Already Have (Issue #77 Error Handling)

Internal docs for issue #77 established an important baseline:
- VS Code can mark tools "disabled" for the remainder of a session if a tool execution results in an unhandled exception or protocol-level failure.
- The repo contains global tool error handling infrastructure intended to prevent this by converting exceptions into structured error results:
  - `mcp_server/core/ERROR_HANDLING.md`
  - `mcp_server/core/error_handling.py`

Implication for issue #89:
- If issue #77 mitigation is present but issue #89 still occurs, then the trigger may not be a plain uncaught exception. Likely candidates include protocol framing/corruption, tool list refresh/reregister behavior, or client-side tool caching/toolset state.

## Server Code Audit (mcp_server)

This section summarizes a targeted audit of the server codebase for the most common stdio JSON-RPC “session poisoning” causes: writing anything non-protocol to stdout, emitting multi-line JSON-RPC frames, or letting subprocess output leak into stdout.

### Stdout Pollution (Print/Logging)
- `mcp_server/core/logging.py` configures structured logging to `sys.stderr` via `logging.StreamHandler(sys.stderr)`. This is correct for stdio transport.
- Direct `print(...)` usage appears only in:
  - `mcp_server/cli.py` for `--version` output (safe as long as the MCP server isn’t launched with `--version` in the VS Code MCP config).
  - `mcp_server/tools/safe_edit_tool.py` contains `print(` only inside an example string, not executed.

### Newline-Delimited JSON-RPC (CRLF / Framing)
- `mcp_server/server.py` explicitly forces LF-only writes on Windows:
  - It wraps `sys.stdout.buffer` in `TextIOWrapper(..., newline="\n")` before passing it to `stdio_server`.
  - The comment references preventing “invalid trailing data” and CRLF issues in the JSON-RPC stream.

Interpretation:
- This is a strong indicator that CRLF translation / message framing was a known risk. With this wrapper, the server’s protocol writer should not emit `\r\n` line endings that can confuse newline-delimited framing.

### Subprocess Output Leakage (High-Risk Pattern)
A major stdio-corruption risk is running subprocesses with inherited stdout (default), which would write directly into the protocol stream.

Audit result:
- All direct `subprocess.run` / `subprocess.Popen` call sites in `mcp_server` either:
  - use `capture_output=True`, or
  - set `stdout=PIPE` / `stderr=PIPE`, or
  - redirect both `stdout` and `stderr` to `DEVNULL`.
- Some git calls also close stdin (`stdin=DEVNULL`) and disable pagers/prompts (e.g. setting `GIT_PAGER=cat`, `GIT_TERMINAL_PROMPT=0`) to avoid hangs.

Implication:
- The server code looks intentionally hardened against the most common *server-side* stdio transport corruption mechanism.

### Dynamic Tool List / tools/list_changed
- No occurrences of `tools/list_changed` / `list_changed` notifications were found in `mcp_server`.
- The tool list appears static at server startup.

Implication:
- Client-side tool registry race conditions around `tools/list_changed` are less likely to be triggered by this server (though the client can still have its own internal tool refresh logic).

### Residual Server-Side Risks (Not Yet Proven)
Even with the mitigations above, remaining server-side candidates would be:
- A third-party dependency writing to stdout directly (rare but possible).
- A protocol-level bug inside the MCP library/version (less likely, but fits “new chat fixes it”).

## External Signals (VS Code / Copilot)

The external issues referenced in #89 point to multiple client-side failure modes that can surface as "tools disabled":

1) MCP stdio transport constraints (MCP spec)
- In stdio transport, stdout must be protocol-only and messages must be newline-delimited JSON-RPC with no embedded newlines.
- Any non-protocol output to stdout can corrupt the stream and lead to downstream client errors.

2) Tool registration / refresh races
- VS Code issue #256521 documents failures when reacting to `tools/list_changed`, including tool re-registration errors and a temporary “disabled by the user” state right after enabling tools.
- This suggests tool availability can flap due to client-side tool registry state, not only server exceptions.

3) Tool schema caching
- VS Code issue #284221 reports that `MCP: Reset Cached Tools` does not always refresh schemas for URL-configured servers, and only a full VS Code restart reliably updates.
- This suggests the client can hold stale tool metadata even after reset, potentially leading to errors that persist per session.

4) Copilot tool availability across sessions/modes
- Copilot release issue #13622 describes tool availability changing depending on how the session was started (custom agent modes losing access to tools unless restarted / using Insiders).
- This indicates that session state, mode switching, or initialization order can affect tool plumbing.

## Working Hypotheses (Ranked)

H1 — Protocol/transport corruption (stdio stdout pollution or framing)
- If the MCP server (or any dependency) writes non-protocol output to stdout, or emits malformed JSON-RPC framing, the client may treat subsequent tool calls as unsafe/unavailable.
- This is consistent with "session poisoning" and "new chat fixes it" if a new process/session resets the stream.

H2 — Client-side tool registry/toolset state bug
- VS Code/Copilot may internally disable a single tool after a failure to register/reregister tools, especially around `tools/list_changed` or toolset changes.
- This can explain cases where one tool is disabled while others still work.

H3 — Tool schema caching mismatch
- The client may invoke tools against stale schema, causing argument validation or invocation failures that then cascade into “disabled” for that tool/session.
- Restarting VS Code (or starting a new chat) can refresh the toolset and resolve.

H4 — Server-side unhandled exception escaping the global handler
- Despite the error-handling infrastructure, there may still be code paths that raise before the decorator/base wrapper runs (e.g., during tool instantiation/registration, schema generation, or import-time initialization).
- This would align with issue #77 findings and would be visible in server stderr logs.

## Evidence To Capture Next (No Repro Yet)

When we do attempt reproduction, the key is to capture the *first* real error before the session becomes poisoned:

VS Code-side:
- Output panel logs for Copilot Chat and MCP-related channels.
- Any tool registry errors such as "already registered".
- VS Code version + Copilot extension version + selected mode/model.

Server-side:
- MCP server stderr logs around the first failing tool call.
- Confirmation that stdout is protocol-only (no logging, no stray prints).

For each failure:
- Tool name + exact args.
- Exact UI error string.
- Whether other tools remain callable or multiple tools disable.

## Immediate Low-Risk Next Steps

Without reproducing yet, low-risk steps we can take:
1) Audit that the MCP server never writes to stdout outside protocol messages.
2) Identify whether any tool can throw during schema/registration time (import-time side effects).
3) Confirm whether the server emits `tools/list_changed` notifications and under what circumstances.
4) Document a recovery checklist (new chat vs restart vs reset cached tools) with expected effectiveness.

# Session Handover — Issue #89 — 2026-01-06

## Context
Issue #89 tracks an intermittent VS Code Copilot Chat / MCP integration failure where tools suddenly become unusable with a misleading message like “tool disabled by the user”. We want to continue research in a fresh chat with **all MCP server tools available** from the start.

Repo/branch state:
- Repo: `SimpleTraderV3`
- Branch: `fix/89-copilot-chat-tools-disabled`
- `.st3/projects.json`: contains issue `89` project entry (bug workflow)
- `.st3/state.json`: initialized to issue `89`, phase `research` (note: state.json is gitignored by design)

## Goal for Next Chat
- Start a new Copilot Chat session that can successfully call MCP tools repeatedly.
- Reproduce the failure in a controlled way and capture the first triggering error (server-side) that causes “session poisoning”.

## Pre-Flight (Do This Before Calling Any Tools)
1. Save work and **Reload Window** (VS Code: Command Palette → “Developer: Reload Window”).
2. Ensure the MCP server is running/healthy.
3. Open the repo root folder (`D:\dev\SimpleTraderV3`).
4. Verify you are on branch `fix/89-copilot-chat-tools-disabled`.

If you see UI errors like:
- “Failed to render content: ModelService: Cannot add model because it already exists!”

Treat that as an **extension/UI rendering bug**, not necessarily a tool failure. Reload Window usually clears it.

## Tool Availability Checklist (Quick Sanity)
In the new chat, run these in order:
1. `health_check`
2. `get_work_context`
3. `search_documentation` with a tiny query (e.g. “issue77”) — optional, this may trigger the UI render error
4. A “safe” tool that does no network calls and minimal IO

Expected:
- All should return results without “disabled by the user”.
- If any tool fails, immediately capture server stderr/log output (see below).

## Minimal Repro Script (Research Procedure)
Run steps until the first failure occurs:
1. Call a read-only tool repeatedly (same tool, same args) 10–20 times.
2. Then alternate between 2–3 different tools.
3. Introduce one tool call that is known to be flaky (e.g., issue retrieval) only after the basics are stable.

Record for each failure:
- Tool name + args
- Exact error message shown in chat
- Whether subsequent tool calls are now blocked/disabled

## Logging / Evidence Capture
We need the *first* real error before the session becomes poisoned.

Capture sources:
- VS Code Output panel relevant channels (Copilot Chat / MCP / related extension output)
- MCP server stderr (the server must keep stdout protocol-only)

If tools become disabled:
- Immediately stop calling tools.
- Reload Window.
- Start a new chat and re-run the checklist.

## Known Constraints / Notes
- `.st3/state.json` is ignored by git; this is expected.
- Session poisoning can happen after a tool exception, protocol violation, or malformed response; issue #89 is SSOT for hypotheses and acceptance criteria.

## Next Concrete Actions
- Commit `.st3/projects.json` (issue 89 initialized).
- Add a small “probe” path in the server (or a dedicated debug tool) that returns a deterministic response to validate tool plumbing, without touching git/network.

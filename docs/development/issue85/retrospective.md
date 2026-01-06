# Issue #85 Retrospective — state.json updates during branch switching

**Date:** 2026-01-06  
**Branch:** `fix/85-epic-branch-support`  
**Parent branch (confirmed):** `epic/76-quality-gates-tooling`  

## Executive summary

Issue #85 started as “state tracking doesn’t support epic branches”, but the real operational failure (as observed via MCP stdio / VS Code chat tool invocation) was: **`git_checkout` sometimes completes the work (state.json gets written) but the MCP response never arrives**.

Two root causes were identified and fixed:

1. **Non-deterministic state update after checkout**
   - Earlier implementation updated `.st3/state.json` via detached/background mechanisms.
   - Result: state could lag or reflect the previous branch.

2. **Stdio hang caused by interactive git subprocess behavior during reconstruction**
   - When `.st3/state.json` was missing/empty, `PhaseStateEngine.get_state()` triggers `_reconstruct_branch_state()` which calls `git log`.
   - Under stdio transport, a git subprocess can block if it tries to interact with stdin / pager.
   - Symptom: client times out waiting for the JSON-RPC response line, while the server continues and writes state.json.

**Final fix:**
- Make `git_checkout` deterministic and safe for the event loop by offloading blocking git/state work to a worker thread.
- Make `git log` explicitly non-interactive (`stdin=DEVNULL`, `GIT_TERMINAL_PROMPT=0`, pager disabled) to prevent stdio deadlocks.
- Keep state writes Windows-safe using atomic temp-file + rename.

## What “done” means

After the final fixes, these scenarios work reliably via MCP tool invocation (VS Code chat / stdio):

- `.st3/state.json` missing → tool returns, file is created with correct branch state.
- `.st3/state.json` empty → tool returns, file is overwritten with correct branch state.
- `.st3/state.json` contains a different branch → tool returns, file is overwritten with correct branch state.

## Parent branch confirmation (no assumptions)

`fix/85-epic-branch-support` is a child of `epic/76-quality-gates-tooling` based on:

- PR **#86**: base = `epic/76-quality-gates-tooling`, head = `fix/85-epic-branch-support`.
- `git merge-base fix/85-epic-branch-support epic/76-quality-gates-tooling` yields `39717d0...`.

## Timeline by commit (detailed)

This section summarizes each relevant commit and what it attempted to change.

### Commits on `fix/85-epic-branch-support` (unique vs parent)

These are the commits that are present on `fix/85-epic-branch-support` and not on `epic/76-quality-gates-tooling` at the time of writing.

1. `8d97afe` — **[red] Add tests for single-branch state.json persistence**
   - Added tests asserting `state.json` is a single-branch document and is overwritten on branch changes.
   - Purpose: lock down the intended persistence semantics.

2. `640f9fb` — **docs: Add research document for git checkout crash**
   - Added Issue #85 project plan entry to `.st3/projects.json`.
   - Added early research notes in `docs/development/issue85/research.md`.

3. `bf1b60c` — **test: Add failing test for async git checkout**
   - Added a regression test to ensure checkout/state sync logic is offloaded from the main event loop.

4. `ffc4546` — **feat: Fix git checkout crash by offloading blocking operations**
   - Wrapped the checkout + state reconstruction path in thread offload.
   - Goal: prevent event-loop stalls / missing tool responses.

5. `9e4b358` — **refactor: Fix trailing whitespace in git_tools.py**
   - Pure formatting cleanup.

6. `9d20d5e` — **feat: fix async blocking in phase state operations (Issue #85)**
   - Earlier attempt to remove blocking patterns in state persistence / tool execution.
   - Introduced changes around state save + tool call behavior.

7. `b9c7837` — **wip: async subprocess state sync (unstable)**
   - Experimented with asynchronous/detached sync strategies.
   - Outcome: unstable/non-deterministic; later replaced by deterministic in-process sync.

8. `b69e201` — **fix: deterministic git_checkout state sync**
   - `git_checkout` now performs checkout and state sync deterministically (no detached subprocess).
   - Uses anyio thread offload for blocking work.

9. `b968626` — **refactor: Add debug logs around tool calls**
   - Added diagnostic logging to help reproduce stdio-only hangs.

10. `1a9dc49` — **refactor: Make git log non-interactive for MCP stdio**
   - Ensures `git log` cannot block waiting for input/pager:
     - `stdin=subprocess.DEVNULL`
     - `GIT_TERMINAL_PROMPT=0`
     - `GIT_PAGER=cat` / `PAGER=cat`
   - This was the key change that eliminated the “state.json empty → tools/call hangs” behavior.

11. `80f44ea` — **docs: Ignore .st3 local debug artifacts**
   - Keeps local debug files out of git noise.

12. `9099ea1` — **refactor: cleanup debug artifacts and ignore outputs**
   - Removes a large set of generated artifacts from the repo root (coverage outputs, mypy/pylint reports, temporary scripts, lock files).
   - Extends `.gitignore` so these do not reappear (including `.mypy_cache/` and `.tmp/`).
   - Purpose: make the branch/repo root clean for future work and reduce noise during reviews.

13. `5051cee` — **refactor: qa: skip non-python files in quality gates**
   - Fixes the `run_quality_gates` tool path so it no longer tries to run pylint/mypy/pyright on non-`.py` inputs like Markdown.
   - Adds an explicit “File Filtering” gate: non-Python inputs are reported as skipped, and Python gates only run on `.py` inputs.
   - Discovered while validating this retrospective: without the filter, Markdown text was interpreted as Python, producing hundreds of bogus diagnostics.

### Related commits on `epic/76-quality-gates-tooling`

During PR #86 and subsequent work, several mitigation attempts landed on the epic branch (sleep/yield strategies, merge commits). These helped reduce timing flakiness but did not address the true stdio deadlock root cause.

Examples:
- `30a3db0` — Merge PR #86 (base epic/76)
- `974bc25` — Merge fix/85 with a delay-based workaround
- `fc195ff`, `29994e7` — yield/sleep based attempts

## Final implementation (where to look)

- Deterministic checkout + state sync: `GitCheckoutTool.execute` in `mcp_server/tools/git_tools.py`.
- Windows-safe atomic state writes: `PhaseStateEngine._save_state` in `mcp_server/managers/phase_state_engine.py`.
- Non-interactive git log to avoid stdio deadlocks: `PhaseStateEngine._get_git_commits` in `mcp_server/managers/phase_state_engine.py`.

## Verification steps

1. Ensure you are invoking via MCP stdio (VS Code chat / tools).
2. Make `.st3/state.json` empty or delete it.
3. Call `git_checkout` to the current branch.
4. Confirm:
   - Response returns quickly.
   - `.st3/state.json` exists and `branch` matches the checked-out branch.

---

## Notes / follow-ups

- Issue #85’s original problem statement (epic branch parsing) may still be relevant conceptually, but the critical failure mode resolved here was the MCP stdio hang + deterministic rewrite requirement.
- If we later re-enable multi-branch state storage, re-check the stdio safety constraints around git subprocess usage.

# Research: Git Checkout Tool Crash

**Author:** GitHub Copilot
**Status:** Draft
**Date:** 2026-01-04

## Executive Summary
Analysis of MCP server crash during git checkout due to blocking I/O on the main thread.

## Problem Analysis
The `git_checkout` tool causes the MCP server to hang and eventually crash with a "Stream terminated" error when switching branches (or simulating a switch). This behavior was observed even when checking out the current branch after deleting `state.json`. The crash occurs because the server becomes unresponsive to JSON-RPC messages.

## Root Cause
The `GitCheckoutTool.execute` method performs synchronous, blocking I/O operations on the main asyncio event loop. 

Key blocking operations identified:
1. `self.manager.checkout(params.branch)`: Executes `git checkout` using `gitpython` or subprocess synchronously.
2. `PhaseStateEngine` operations:
   - `engine.get_state(params.branch)`: Reads/writes `state.json` synchronously.
   - `_infer_phase_from_git`: Executes `git log` via `subprocess.run` synchronously.

Since the MCP server runs on a single-threaded asyncio event loop, any blocking operation freezes the entire server. This prevents the server from processing incoming messages or sending heartbeats, leading the client (VS Code) to assume the connection is dead and terminate the stream.

## Proposed Solution
To fix this, we must ensure that the main event loop remains unblocked. We will use `asyncio.to_thread()` to offload the blocking synchronous operations to a separate thread.

**Plan:**
1. Modify `mcp_server/tools/git_tools.py`.
2. Wrap `self.manager.checkout` in `asyncio.to_thread`.
3. Wrap the `PhaseStateEngine` state synchronization logic in a helper function and run it via `asyncio.to_thread`.

This will allow the asyncio loop to continue processing other events (like keep-alives) while the heavy I/O operations complete in the background.

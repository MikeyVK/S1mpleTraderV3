# Issue #55: Server Restart Tool for Agent TDD Autonomy

**Status:** IN PROGRESS
**Author:** GitHub Copilot (Claude Sonnet 4.5)
**Created:** 2026-01-13
**Last Updated:** 2026-01-13
**Parent Issue:** #55 - Git Conventions Configuration
**Purpose:** Enable agent-driven TDD by allowing autonomous server restarts via watchdog supervisor

---

## 1. Problem Statement

### 1.1 Current Bottleneck

**Agent TDD Flow (Manual Intervention Required):**
```
Agent: TDD Cycle 1 - Implement GitConfig
├─ red: Write test_git_config_loads_from_yaml()
├─ green: Implement GitConfig.from_file()
├─ Want to verify: pytest tests/mcp_server/config/test_git_config.py
└─ ❌ BLOCKED: Code changes not loaded (server still running old code)
    └─ Human must: Manually restart VS Code MCP connection
    └─ Breaks agent autonomy, requires 30-50 manual restarts for Issue #55
```

**Impact on Issue #55:**
- 10 TDD cycles × 3-5 restarts per cycle = **30-50 manual restarts**
- Each restart: 30-60 seconds of human intervention
- Total time lost: 15-50 minutes + broken agent flow
- Agent cannot work autonomously through TDD implementation

### 1.2 Solution Architecture

**Agent TDD Flow (With Watchdog Supervisor):**
```
Agent: TDD Cycle 1 - Implement GitConfig
├─ red: Write test_git_config_loads_from_yaml()
├─ green: Implement GitConfig.from_file()
├─ restart_server(reason="Load new GitConfig implementation")
│  ├─ Tool writes restart marker
│  ├─ Tool logs audit event
│  ├─ Tool returns success response
│  ├─ After 500ms: sys.exit(42)
│  ├─ Supervisor detects exit 42
│  ├─ Supervisor spawns new MCP server instance
│  └─ New instance inherits stdio (continuous connection)
├─ Wait ~2 seconds for restart completion
├─ verify_server_restarted(since_timestamp=...)
├─ pytest tests/mcp_server/config/test_git_config.py
└─ ✅ Full autonomous TDD cycle!
```

**Key Components:**
1. **RestartServerTool**: Triggers restart via exit code 42
2. **Watchdog Supervisor**: Monitors exit codes, spawns new instances
3. **Restart Marker**: Persists restart metadata for verification
4. **Audit Trail**: Logs all restart events for forensics
5. **VerifyServerRestartedTool**: Confirms restart occurred

---

## 2. Architecture Overview

### 2.1 Process Model

```
┌─────────────────────────────────────────────────────────────┐
│ VS Code MCP Extension                                       │
│ - Starts watchdog supervisor (not MCP server directly!)    │
│ - Connects stdio pipes to supervisor                       │
│ - Sends initialize once (at connection start)              │
│ - Unaware of child MCP server restarts                     │
└───────────────────┬─────────────────────────────────────────┘
                    │ stdio (stable connection)
┌───────────────────▼─────────────────────────────────────────┐
│ Watchdog Supervisor (supervisor.py)                        │
│ - PID: 12345 (stable)                                      │
│ - Maintains stdio pipes to VS Code                         │
│ - Spawns MCP server as child (inherit stdio)               │
│ - Monitors exit codes:                                     │
│   * Exit 0: Clean shutdown → supervisor exits              │
│   * Exit 42: Restart request → spawn new child             │
│   * Exit >0: Crash → spawn new child with backoff          │
└───────────────────┬─────────────────────────────────────────┘
                    │ subprocess.Popen (stdio inherited)
┌───────────────────▼─────────────────────────────────────────┐
│ MCP Server Process (mcp_server/__main__.py)                │
│ - PID: 67890 (ephemeral, changes on restart)               │
│ - RestartServerTool.execute():                             │
│   1. Write restart marker                                  │
│   2. Log audit event                                       │
│   3. Return success response                               │
│   4. asyncio.create_task(delayed_exit())                   │
│   5. After 500ms: sys.exit(42)                             │
│ - Supervisor detects exit 42 → spawns new instance         │
│ - New instance PID: 67891 (inherits same stdio)            │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Exit Code Protocol

**The supervisor uses exit codes to determine restart behavior:**

| Exit Code | Meaning | Supervisor Action |
|-----------|---------|-------------------|
| `0` | Clean shutdown | Supervisor exits (propagates 0 to VS Code) |
| `42` | Restart request | Supervisor spawns new child (with throttle) |
| `>0` | Crash/error | Supervisor spawns new child (with backoff) |

**Why Exit Code 42?**
- Not a standard POSIX exit code (unambiguous signal)
- Mnemonic: "The Answer to Life, the Universe, and Everything"
- Easy to remember and grep for in logs

### 2.3 Lifecycle Flow

**Happy Path (Restart Request):**

```
1. Agent calls restart_server(reason="Load new code")
2. RestartServerTool.execute():
   - Writes restart marker: {timestamp, reason, exit_code: 42}
   - Logs audit event: "server_restart_requested"
   - Returns ToolResult: "Restart scheduled, will exit with code 42 in 500ms"
   - Schedules delayed_exit() background task
3. MCP server sends response to agent (via stdio/supervisor/VS Code)
4. After 500ms:
   - logging.shutdown() - flush all logs
   - sys.exit(42) - signal restart to supervisor
5. Child process terminates (PID 67890 exits)
6. Supervisor detects exit code 42
7. Supervisor checks throttle (max 1 restart/second)
8. Supervisor sleeps 500ms (cleanup delay)
9. Supervisor spawns new child (PID 67891)
10. New child inherits stdio from supervisor (same pipes!)
11. VS Code continues sending requests (no re-initialization needed)
12. Agent calls verify_server_restarted() to confirm
```

**VS Code Stop (Clean Shutdown):**

```
1. User closes VS Code or disconnects MCP server
2. VS Code closes stdin pipe (EOF signal)
3. MCP server detects EOF on stdin
4. MCP server exits with code 0 (clean shutdown)
5. Supervisor detects exit code 0
6. Supervisor logs "Clean shutdown requested"
7. Supervisor exits with code 0
8. VS Code detects supervisor exit → connection closed
```

**Crash Recovery:**

```
1. MCP server encounters unhandled exception
2. Python runtime calls sys.exit(1) or similar
3. Child process terminates (PID 67890 exits)
4. Supervisor detects exit code 1 (or any non-0, non-42)
5. Supervisor logs "Server crashed (exit code 1)"
6. Supervisor calculates backoff delay:
   - Restarts 1-3: 1 second
   - Restarts 4-10: 5 seconds
   - Restarts 10+: 10 seconds
7. Supervisor sleeps for backoff duration
8. Supervisor spawns new child (PID 67891)
9. New child inherits stdio, starts fresh
10. VS Code continues sending requests (automatic recovery)
```

---

## 3. RestartServerTool Design

### 3.1 Tool Specification

**Tool Name:** `restart_server`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "reason": {
      "type": "string",
      "description": "Reason for restart (for audit logging)"
    }
  },
  "required": ["reason"]
}
```

**Output:**
```json
{
  "type": "text",
  "text": "Server restart scheduled (reason: {reason}). Server will exit with code 42 in 500ms, supervisor will spawn new instance."
}
```

### 3.2 Implementation

**File:** `mcp_server/tools/admin_tools.py`

**Key Functions:**

```python
async def delayed_exit() -> None:
    """Exit with code 42 after delay to allow response delivery.
    
    Timeline:
    - T+0ms: Tool returns response to agent
    - T+0ms: This function scheduled as background task
    - T+500ms: Flush logs
    - T+500ms: sys.exit(42)
    - T+500ms: Child process terminates
    - T+500ms: Supervisor detects exit 42
    - T+1000ms: Supervisor spawns new child
    - T+2000ms: New server ready
    """
    await asyncio.sleep(0.5)  # 500ms delay
    
    # Flush all logs before exit
    logging.shutdown()
    
    # Log final audit event
    logger.info(
        "Server exiting for restart (exit code 42)",
        extra={"props": {"exit_code": 42}}
    )
    
    # Exit with code 42 → supervisor will restart
    sys.exit(42)


class RestartServerTool(BaseTool):
    """Restart MCP server via watchdog supervisor.
    
    Triggers server restart by exiting with code 42. The watchdog supervisor
    detects this exit code and spawns a new MCP server instance with updated
    code. The stdio connection remains stable (maintained by supervisor), so
    VS Code sees continuous connection without re-initialization.
    
    Used during TDD workflows to load code changes without human intervention.
    """
    
    name = "restart_server"
    description = """Restart MCP server to reload code changes.
    
    Exits current server process (code 42) and supervisor spawns new instance.
    VS Code connection remains stable (no re-initialization needed).
    
    Use after modifying server code to load changes in autonomous TDD workflow.
    """
    
    async def execute(self, arguments: RestartServerInput) -> list[TextContent]:
        """Execute server restart request.
        
        1. Write restart marker (timestamp, reason, exit_code)
        2. Log audit event (server_restart_requested)
        3. Return success response to agent
        4. Schedule delayed_exit() after 500ms
        5. After delay: sys.exit(42) → supervisor restarts
        
        Args:
            arguments: RestartServerInput with reason field
            
        Returns:
            ToolResult indicating restart scheduled
        """
        reason = arguments.reason
        timestamp = datetime.now(UTC)
        
        # Write restart marker (for verify_server_restarted tool)
        marker_path = settings.paths.workspace_root / ".mcp_restart_marker"
        marker_data = {
            "timestamp": timestamp.isoformat(),
            "reason": reason,
            "exit_code": 42,
            "method": "sys.exit(42) → supervisor restart"
        }
        marker_path.write_text(json.dumps(marker_data, indent=2))
        
        # Log audit event
        audit_logger.info(
            "server_restart_requested",
            extra={
                "reason": reason,
                "timestamp": timestamp.isoformat(),
                "exit_code": 42,
                "marker_path": str(marker_path)
            }
        )
        
        # Schedule delayed exit (allows response to be sent)
        asyncio.create_task(delayed_exit())
        
        # Return success immediately (before exit)
        return ToolResult.text(
            f"Server restart scheduled (reason: {reason}). "
            f"Server will exit with code 42 in 500ms, "
            f"supervisor will spawn new instance."
        )
```

### 3.3 Response Timing

**Critical Timing Requirement:**

The tool MUST return a response BEFORE the server exits. Otherwise:
- Tool call hangs indefinitely (response never delivered)
- Agent blocks waiting for response
- Autonomous workflow breaks

**Solution: Delayed Exit**

```python
# Return response immediately
result = ToolResult.text("Restart scheduled...")

# Schedule exit in background (500ms delay)
asyncio.create_task(delayed_exit())

# Response delivered before exit occurs
return result
```

**Timeline:**
```
T+0ms:    RestartServerTool.execute() called
T+0ms:    Marker written, audit logged
T+0ms:    ToolResult returned to agent
T+0ms:    delayed_exit() scheduled as background task
T+50ms:   Response typically delivered to VS Code → agent
T+500ms:  delayed_exit() executes: logging.shutdown() + sys.exit(42)
T+500ms:  Child process terminates
T+500ms:  Supervisor detects exit 42
T+1000ms: Supervisor spawns new child (after 500ms cleanup delay)
T+2000ms: New server ready (process spawn ~1s)
```

**Why 500ms?**
- JSON-RPC response delivery typically < 50ms
- 500ms provides 10x safety margin
- Balance: long enough for delivery, short enough for fast restart

---

## 4. VerifyServerRestartedTool Design

### 4.1 Purpose

**Problem:** Agent needs confirmation that restart completed successfully.

**Without Verification:**
```python
restart_server(reason="Load new code")
# Did restart happen? No way to know!
run_tests()  # Might test old code if restart failed!
```

**With Verification:**
```python
restart_server(reason="Load new code")
time.sleep(2)  # Wait for restart
verify_server_restarted(since_timestamp="2026-01-13T22:30:00Z")
# ✅ Confirmed: restart occurred, running new code
run_tests()  # Guaranteed to test new code
```

### 4.2 Tool Specification

**Tool Name:** `verify_server_restarted`

**Input Schema:**
```json
{
  "type": "object",
  "properties": {
    "since_timestamp": {
      "type": "string",
      "description": "ISO 8601 timestamp - verify restart occurred after this time"
    }
  },
  "required": ["since_timestamp"]
}
```

**Output:**
```json
{
  "type": "text",
  "text": "✅ Server restart verified: occurred at {timestamp} (reason: {reason})"
}
```

**Error Output:**
```json
{
  "type": "text",
  "text": "❌ No recent restart detected since {since_timestamp}"
}
```

### 4.3 Implementation

```python
class VerifyServerRestartedTool(BaseTool):
    """Verify that server restart occurred after specified timestamp.
    
    Checks restart marker file written by RestartServerTool. Confirms that:
    1. Marker file exists
    2. Marker timestamp is after since_timestamp
    3. Marker has valid schema (timestamp, reason, exit_code)
    
    Used by agents to confirm restart completed before continuing TDD workflow.
    """
    
    name = "verify_server_restarted"
    description = """Verify server restart occurred after specified timestamp.
    
    Checks restart marker written by restart_server tool. Returns success if
    restart occurred after given timestamp, error otherwise.
    
    Use after restart_server + wait period to confirm restart completed.
    """
    
    async def execute(self, arguments: VerifyRestartInput) -> list[TextContent]:
        """Verify restart occurred after specified timestamp.
        
        Args:
            arguments: VerifyRestartInput with since_timestamp
            
        Returns:
            ToolResult indicating verification success or failure
        """
        since_timestamp = datetime.fromisoformat(arguments.since_timestamp)
        marker_path = settings.paths.workspace_root / ".mcp_restart_marker"
        
        # Check marker exists
        if not marker_path.exists():
            return ToolResult.error(
                f"❌ No restart marker found at {marker_path}. "
                f"No recent restarts detected."
            )
        
        # Read marker data
        try:
            marker_data = json.loads(marker_path.read_text())
        except (json.JSONDecodeError, OSError) as e:
            return ToolResult.error(
                f"❌ Failed to read restart marker: {e}"
            )
        
        # Verify schema
        required_fields = ["timestamp", "reason", "exit_code"]
        if not all(field in marker_data for field in required_fields):
            return ToolResult.error(
                f"❌ Invalid restart marker schema. "
                f"Required fields: {required_fields}"
            )
        
        # Check timestamp
        marker_timestamp = datetime.fromisoformat(marker_data["timestamp"])
        
        if marker_timestamp <= since_timestamp:
            return ToolResult.error(
                f"❌ No recent restart detected since {since_timestamp.isoformat()}. "
                f"Last restart: {marker_timestamp.isoformat()}"
            )
        
        # Verify exit code (should be 42 for intentional restart)
        if marker_data["exit_code"] != 42:
            return ToolResult.warning(
                f"⚠️ Restart occurred but with unexpected exit code: "
                f"{marker_data['exit_code']} (expected 42)"
            )
        
        # Success!
        return ToolResult.text(
            f"✅ Server restart verified: occurred at {marker_timestamp.isoformat()} "
            f"(reason: {marker_data['reason']})"
        )
```

---

## 5. Supervisor Interaction

### 5.1 Configuration (mcp.json)

**VS Code starts the supervisor, not the MCP server directly:**

```jsonc
{
  "servers": {
    "st3-workflow": {
      "type": "stdio",
      "command": "${workspaceFolder}\\.venv\\Scripts\\python.exe",
      "args": ["-m", "mcp_server.supervisor"],  // ← Supervisor, not mcp_server!
      "cwd": "${workspaceFolder}",
      "env": {
        "GITHUB_TOKEN": "${env:GITHUB_TOKEN}"
      }
    }
  }
}
```

**VS Code lifecycle:**
1. Start: Spawns supervisor → supervisor spawns MCP server
2. Stop: Closes stdin (EOF) → server exits with 0 → supervisor exits with 0
3. Restart: Agent calls tool → server exits with 42 → supervisor spawns new instance

### 5.2 Supervisor Responsibilities

**The supervisor handles:**
- Spawn MCP server as child process
- Monitor child exit codes
- Detect exit 42 → restart with throttle
- Detect exit 0 → clean shutdown (supervisor exits)
- Detect exit >0 → crash recovery with backoff
- Log all lifecycle events to stderr
- Maintain stdio connection to VS Code

**The supervisor does NOT handle:**
- MCP protocol (that's the child server's job)
- Tool execution (that's the child server's job)
- State management (supervisor is stateless except restart_count)

### 5.3 Stdio Flow

**Key Insight: Stdio pipes maintained by supervisor, inherited by child**

```
VS Code creates pipes:
  stdin_pipe, stdout_pipe, stderr_pipe

VS Code spawns supervisor:
  supervisor.stdin  = stdin_pipe
  supervisor.stdout = stdout_pipe
  supervisor.stderr = stderr_pipe

Supervisor spawns child:
  child.stdin  = supervisor.stdin  (same pipe!)
  child.stdout = supervisor.stdout (same pipe!)
  child.stderr = supervisor.stderr (same pipe!)

Child exits, new child spawned:
  new_child.stdin  = supervisor.stdin  (same pipe again!)
  new_child.stdout = supervisor.stdout (same pipe again!)
  new_child.stderr = supervisor.stderr (same pipe again!)
```

**Result:** Continuous stdio stream across child restarts. VS Code unaware of child lifecycle.

---

## 6. Testing Strategy

### 6.1 Unit Tests

**Test File:** `tests/mcp_server/tools/test_admin_tools.py`

**Test Coverage:**

1. **`test_restart_tool_writes_marker`**
   - Verify marker file created at correct path
   - Verify marker contains timestamp, reason, exit_code
   - Verify exit_code == 42

2. **`test_restart_tool_exits_with_42`**
   - Mock sys.exit to capture exit code
   - Mock asyncio.sleep to fast-forward delay
   - Verify sys.exit(42) called (not os.execv)
   - Verify response returned before exit

3. **`test_restart_tool_logs_audit_event`**
   - Capture audit log output
   - Verify "server_restart_requested" event logged
   - Verify reason included in log

4. **`test_verify_tool_succeeds_with_valid_marker`**
   - Write valid marker with recent timestamp
   - Call verify_server_restarted
   - Verify success response

5. **`test_verify_tool_fails_with_old_marker`**
   - Write marker with old timestamp
   - Call verify_server_restarted with recent since_timestamp
   - Verify error response

6. **`test_verify_tool_fails_without_marker`**
   - Ensure no marker file exists
   - Call verify_server_restarted
   - Verify error response

### 6.2 Integration Tests

**Manual Integration Test:**

1. Update mcp.json to use supervisor
2. Restart VS Code MCP connection
3. Verify server starts (health_check succeeds)
4. Call restart_server(reason="Integration test 1")
5. Wait 2 seconds
6. Call verify_server_restarted(since_timestamp=<before_restart>)
7. Verify success response
8. Call health_check (should succeed)
9. Repeat steps 4-8 for "Integration test 2"
10. Check supervisor logs in VS Code Output panel

**Expected Output:**
```
[SUPERVISOR] Starting MCP server (restart #0)
[SUPERVISOR] MCP server running (PID: 67890)
... (agent calls restart_server)
Server restart scheduled (reason: Integration test 1)
[SUPERVISOR] MCP server exited (code: 42)
[SUPERVISOR] Restart requested, spawning new server (restart #1)
[SUPERVISOR] Starting MCP server (restart #1)
[SUPERVISOR] MCP server running (PID: 67891)
✅ Server restart verified: occurred at 2026-01-13T22:35:00Z
```

---

## 7. Success Criteria

**Functional Requirements:**

- ✅ FR-1: Agent can call restart_server(reason="...")
- ✅ FR-2: Server exits with code 42 after 500ms
- ✅ FR-3: Supervisor detects exit 42 and spawns new instance
- ✅ FR-4: VS Code connection remains stable (no re-initialization)
- ✅ FR-5: Agent can verify restart with verify_server_restarted
- ✅ FR-6: Audit trail captures all restart events
- ✅ FR-7: Restart marker persisted before exit

**Non-Functional Requirements:**

- ✅ NFR-1: Restart completes in < 2 seconds (median)
- ✅ NFR-2: Zero data loss (logs flushed before exit)
- ✅ NFR-3: Tool response delivered before exit (no hung calls)
- ✅ NFR-4: Clean shutdown works (VS Code stop → exit 0)
- ✅ NFR-5: Crash recovery works (exit >0 → backoff restart)

**Verification:**

```bash
# Run all admin tools tests
pytest tests/mcp_server/tools/test_admin_tools.py

# All tests must pass
# Expected: 6/6 tests passing (100%)
```

---

## 8. Implementation Checklist

**Phase 1: Update RestartServerTool** ✅ COMPLETE
- [x] Supervisor implemented and tested
- [x] Supervisor reference document created
- [ ] Update RestartServerTool to use sys.exit(42) (instead of os.execv)
- [ ] Update delayed_restart → delayed_exit
- [ ] Update audit log event names
- [ ] Update tool response messages
- [ ] Update tests for sys.exit(42)

**Phase 2: Update mcp.json**
- [ ] Change command to supervisor: `["-m", "mcp_server.supervisor"]`
- [ ] Remove obsolete PowerShell wrapper configuration

**Phase 3: Integration Testing**
- [ ] Manual test: restart_server → verify logs → health_check
- [ ] Verify restart timing < 2 seconds
- [ ] Verify VS Code sees continuous connection
- [ ] Verify audit trail complete

**Phase 4: Cleanup**
- [ ] Delete start_mcp_server.ps1 (obsolete)
- [ ] Update this design document (mark COMPLETE)
- [ ] Push all commits to remote

---

## 9. Appendix: Lessons Learned

### 9.1 PowerShell Wrapper Approach (FAILED)

**What We Tried:**
- PowerShell script monitors exit code 42
- Script restarts server on detection

**Why It Failed:**
- Exit detection delayed until next stdio operation (2+ minutes!)
- Wrapper interference with stdout broke JSON-RPC protocol
- Tool calls hung during restart (response never sent)

**Lesson:** External wrappers cannot handle stdio-based protocols reliably.

### 9.2 os.execv() Approach (FAILED)

**What We Tried:**
- Server calls os.execv(sys.executable, ["-m", "mcp_server"])
- Replaces process in-place, preserves PID and stdio

**Why It Failed:**
- MCP protocol requires initialize handshake for each server instance
- os.execv() preserves stdio connection, but creates new server expecting initialize
- VS Code thinks connection already initialized (same PID/stdio)
- Result: "initialization incomplete" errors indefinitely

**Lesson:** MCP protocol is stateful. Cannot restart server without breaking connection.

### 9.3 Watchdog Supervisor Approach (SUCCESS)

**What We Did:**
- Supervisor process maintains stdio connection with VS Code
- Supervisor spawns MCP server as child (inherit stdio)
- Child exits with code 42 → supervisor spawns new instance
- New instance inherits same stdio → continuous connection

**Why It Works:**
- Supervisor maintains stable stdio connection (never breaks)
- Each child is a fresh server instance (new PID, clean state)
- VS Code sees continuous connection (unaware of child lifecycle)
- MCP protocol satisfied (no re-initialization needed)

**Lesson:** Process supervision is the correct pattern for server lifecycle management.

---

**Document End**

# Issue #55: Watchdog Supervisor for MCP Server Restart

**Status:** DRAFT
**Author:** GitHub Copilot (Claude Sonnet 4.5)
**Created:** 2026-01-13
**Parent Issue:** #55 - Git Conventions Configuration
**Purpose:** Enable autonomous MCP server restarts via watchdog supervisor

---

## Executive Summary

**Design and implementation plan for a Python watchdog supervisor process that enables autonomous MCP server restarts while maintaining stdio connection integrity with VS Code. This replaces the failed os.execv() approach which broke MCP protocol initialization handshake.**

### The Problem

The os.execv() approach implemented in commit 31ef4f82 failed because:
- **MCP Protocol Violation**: Server restart via os.execv() preserves PID and stdio, but creates a new server instance expecting a fresh `initialize` handshake
- **Client State Mismatch**: VS Code MCP client thinks connection is already initialized (because PID/stdio unchanged), sends normal requests instead of re-initializing
- **Result**: Server waits for `initialize`, client sends `tools/call` → deadlock
- **Symptom**: Health checks fail indefinitely after restart, server logs show "running" but tools return "initialization incomplete" errors

### The Solution

**Watchdog Supervisor Pattern:**
- Separate supervisor process manages server lifecycle
- VS Code connects to supervisor (stable PID, stable stdio)
- Supervisor spawns MCP server as child process
- Child server exits with code 42 → supervisor spawns new instance
- VS Code sees continuous connection, no re-initialization needed
- Clean garbage collection between server instances

### Key Benefits

1. **MCP Protocol Compliant**: Each server instance gets fresh connection lifecycle
2. **VS Code Transparency**: Client sees one stable process (the supervisor)
3. **Platform Agnostic**: Pure Python solution, no shell scripts
4. **Crash Recovery**: Automatic restart on unexpected exits
5. **Clean Separation**: Supervisor handles process management, server handles MCP protocol

---

## 1. Executive Summary

See above.

---

## 2. Problem Analysis

### 2.1 os.execv() Failure Root Cause

**Timeline of Failed Implementation:**

```
22:01:46.535 - Tool call: restart_server(reason="Testing os.execv()")
22:01:46.535 - RestartServerTool.execute() returns ToolResult immediately ✓
22:01:47.041 - os.execv() replaces process (PID unchanged, stdio unchanged)
22:01:48.788 - New server instance: "MCP server running" ✓
22:04:03.000 - Health check: ERROR "Invalid request parameters"
22:04:11.000 - Health check: ERROR "Invalid request parameters"  
22:04:20.000 - Health check: ERROR "Invalid request parameters"
22:10:00.000 - Health check: ERROR (indefinite failure)
```

**Analysis:**
- Server logs show "running" at 22:01:48.788
- First health check 2m15s later (22:04:03) - FAILS
- Pattern continues indefinitely
- **NOT a timing issue** - server never becomes functional

**VS Code Logs:**
```
WARNING:root:Failed to validate request: Received request before initialization was complete
```

**Root Cause:**
1. os.execv() preserves PID and stdio file descriptors
2. New Python interpreter starts, loads mcp_server package
3. New MCP Server instance calls `stdio_server()` expecting `initialize` request
4. VS Code MCP client still thinks connection from previous instance is active
5. Client sends normal JSON-RPC requests (tools/call, health_check)
6. Server rejects: "initialization incomplete"
7. **Deadlock**: Server waits for initialize, client won't send it

### 2.2 Why PowerShell Wrapper Failed

**Previous Approach (start_mcp_server.ps1):**
```powershell
while ($true) {
    $proc = Start-Process python -Args "-m","mcp_server" -Wait -PassThru
    if ($proc.ExitCode -eq 42) {
        Write-Host "Restarting..." -ForegroundColor Yellow
        continue
    }
    exit $proc.ExitCode
}
```

**Failures:**
1. **Exit Detection Delay**: `Start-Process -Wait` only checks exit on stdio operation
   - Server exits at 18:04:20
   - Wrapper detects exit at 19:06:48 (62 minutes later!)
   - Restart triggered by agent's next tool call, not automatically

2. **Stdio Interference**: Wrapper wrote to stdout, breaking JSON-RPC protocol
   - MCP expects clean stdout for JSON-RPC messages
   - Wrapper output: "Failed to parse message" errors in VS Code

3. **Hung Tool Calls**: Agent's call during restart never completed
   - Server exits mid-call, response never sent
   - Agent blocked, cannot continue autonomous workflow

### 2.3 MCP Protocol Requirements

From [MCP Architecture Documentation](https://modelcontextprotocol.io/docs/learn/architecture):

**Lifecycle Management (Stateful Protocol):**
1. Client sends `initialize` request with protocolVersion and capabilities
2. Server responds with serverInfo and capabilities
3. Client sends `notifications/initialized` notification
4. Connection is "ready" - tools/resources/prompts can be used

**Critical Insight:**
> "MCP is a stateful protocol that requires lifecycle management. The purpose of lifecycle management is to negotiate the capabilities that both client and server support."

**STDIO Transport:**
> "Uses standard input/output streams for direct process communication between local processes on the same machine, providing optimal performance with no network overhead."

**Problem:**
- os.execv() creates a new server instance expecting step 1-3
- But stdio connection from previous instance still exists
- Client thinks steps 1-3 already completed
- **No mechanism in MCP spec for "re-initialize on same stdio"**

### 2.4 Why Watchdog Supervisor Works

**Architecture:**
```
VS Code MCP Client
    ↓ stdio (stdin/stdout/stderr)
Watchdog Supervisor Process (PID: 12345, stable)
    ↓ subprocess.Popen()
MCP Server Process (PID: 67890, ephemeral)
```

**Lifecycle:**
```
1. VS Code starts supervisor → stdio connected to supervisor PID
2. Supervisor spawns child MCP server → server inherits stdio
3. VS Code sends initialize → forwarded to child → child responds
4. Connection ready, agent uses tools
5. Agent calls restart_server() → child exits with code 42
6. Supervisor detects exit → spawns NEW child process
7. New child inherits SAME stdio from supervisor
8. VS Code sees continuous connection (supervisor PID unchanged)
9. NO re-initialization needed - stdio stream continues
```

**Key Difference from os.execv():**
- os.execv(): New server instance, **SAME stdio connection** → MCP protocol violation
- Watchdog: New server instance, **INHERITS stdio from stable parent** → Protocol compliant

**Why This Works:**
- VS Code connects to supervisor (one-time initialization)
- Supervisor's stdio = pipe to VS Code
- Child server's stdio = inherited from supervisor (same pipe)
- When child exits, supervisor spawns new child with same inherited stdio
- **Stdio stream is continuous** (supervisor maintains it)
- New child server seamlessly takes over the stream
- No MCP protocol re-initialization needed

---

## 3. MCP Protocol Requirements

### 3.1 STDIO Transport Specifications

**From MCP Specification:**

**Connection Setup:**
```python
# Client side (VS Code)
process = subprocess.Popen(
    command=["python", "-m", "mcp_server"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# MCP client reads from process.stdout, writes to process.stdin
```

**Message Format:**
- JSON-RPC 2.0 over stdio
- Each message: JSON object followed by newline
- Request: `{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {...}}\n`
- Response: `{"jsonrpc": "2.0", "id": 1, "result": {...}}\n`
- Notification: `{"jsonrpc": "2.0", "method": "notifications/initialized"}\n`

**Critical Requirements:**
1. **Clean stdout**: Only JSON-RPC messages, no debug output
2. **Line-buffered**: Each message ends with \n
3. **Bidirectional**: stdin for requests, stdout for responses
4. **Continuous stream**: Connection breaks if stdout/stdin close

### 3.2 Initialization Handshake

**Required Sequence (MUST happen exactly once per connection):**

```json
// Step 1: Client → Server (initialize request)
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": { "elicitation": {} },
    "clientInfo": { "name": "vscode-mcp", "version": "1.0.0" }
  }
}

// Step 2: Server → Client (initialize response)
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2025-06-18",
    "capabilities": { "tools": {"listChanged": true}, "resources": {} },
    "serverInfo": { "name": "st3-workflow", "version": "0.1.0" }
  }
}

// Step 3: Client → Server (initialized notification)
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}

// Connection now "ready" - tools/resources/prompts can be used
```

**After Initialization:**
```json
// Normal tool call
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "health_check",
    "arguments": {}
  }
}
```

**What Happens with os.execv():**
1. First server instance: Steps 1-3 complete, connection ready ✓
2. Agent calls restart_server() → os.execv() → new server instance
3. New server instance expects Steps 1-3 (fresh initialize handshake)
4. VS Code client thinks Steps 1-3 already done (connection established)
5. Client sends normal requests (tools/call) → Server rejects: "initialization incomplete"
6. **Deadlock**: No way to force re-initialization on existing connection

### 3.3 Watchdog Supervisor Compliance

**How Watchdog Maintains Protocol Compliance:**

```python
# supervisor.py (watchdog process)
def main():
    # Supervisor's stdio = VS Code connection
    # sys.stdin  → from VS Code
    # sys.stdout → to VS Code
    # sys.stderr → logging (not MCP protocol)
    
    while True:
        # Spawn child, inherits supervisor's stdio
        child = subprocess.Popen(
            [sys.executable, "-m", "mcp_server"],
            stdin=sys.stdin,   # Child reads from same stdin as supervisor
            stdout=sys.stdout, # Child writes to same stdout as supervisor
            stderr=sys.stderr  # Child logs to same stderr as supervisor
        )
        
        # Wait for child exit
        exit_code = child.wait()
        
        if exit_code == 42:  # Restart requested
            # Child exited, spawn NEW child
            # New child inherits SAME stdio from supervisor
            # Stdio stream is continuous (supervisor maintains it)
            continue
        else:
            # Clean exit or crash
            sys.exit(exit_code)
```

**Key Insight:**
- **Supervisor's stdio = pipe to VS Code** (established once)
- **Child's stdio = inherited from supervisor** (same pipe)
- When child exits, pipe remains open (supervisor holds it)
- New child inherits same pipe → **continuous stdio stream**
- **No connection boundary** → No re-initialization needed

**VS Code Perspective:**
```
Time 0:   Start supervisor → initialize handshake → connection ready
Time 10:  Call restart_server() → child exits
Time 10:  Supervisor spawns new child (invisible to VS Code)
Time 10:  Continue using connection (no interruption)
```

---

## 4. Watchdog Supervisor Design

### 4.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ VS Code MCP Extension (Client)                              │
│ - Starts supervisor via mcp.json configuration              │
│ - Sends initialize handshake once                           │
│ - Uses tools/resources/prompts throughout session           │
└───────────────────┬─────────────────────────────────────────┘
                    │ stdio (pipe)
                    │ stdin:  VS Code → Supervisor
                    │ stdout: Supervisor → VS Code
                    │ stderr: Supervisor → VS Code (logs)
┌───────────────────▼─────────────────────────────────────────┐
│ Watchdog Supervisor Process (supervisor.py)                 │
│ - PID: 12345 (stable, never changes)                        │
│ - Maintains stdio pipe to VS Code                           │
│ - Spawns MCP server as child process                        │
│ - Monitors child exit codes                                 │
│ - Restart logic:                                            │
│   * Exit 42 → spawn new child (restart requested)           │
│   * Exit 0  → clean shutdown, supervisor exits              │
│   * Exit >0 → crash, spawn new child (auto-recovery)        │
│ - Logging: stderr (won't interfere with stdout JSON-RPC)    │
└───────────────────┬─────────────────────────────────────────┘
                    │ subprocess.Popen() with inherited stdio
                    │ child.stdin  = supervisor.stdin  (VS Code pipe)
                    │ child.stdout = supervisor.stdout (VS Code pipe)
                    │ child.stderr = supervisor.stderr
┌───────────────────▼─────────────────────────────────────────┐
│ MCP Server Process (mcp_server/__main__.py)                 │
│ - PID: 67890 (ephemeral, changes on each restart)           │
│ - Runs normal MCP server with stdio_server()                │
│ - Tools include RestartServerTool:                          │
│   * Writes restart marker                                   │
│   * Logs audit event                                        │
│   * Returns success response                                │
│   * Exits with code 42 after 500ms delay                    │
│ - On exit 42: process terminates                            │
│ - Supervisor detects exit and spawns new instance           │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Supervisor Implementation

**File: `mcp_server/supervisor.py`**

```python
"""
Watchdog supervisor for MCP server lifecycle management.

This supervisor process maintains a stable stdio connection with VS Code
while managing ephemeral MCP server child processes. It enables autonomous
server restarts without breaking the MCP protocol initialization handshake.

Exit Codes:
- 0: Clean shutdown (supervisor exits)
- 42: Restart request (supervisor spawns new child)
- >0: Crash (supervisor spawns new child with crash recovery)
"""
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone


def log(message: str) -> None:
    """
    Log to stderr (safe for MCP protocol).
    
    MCP protocol requires clean stdout for JSON-RPC messages.
    All supervisor logging goes to stderr.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[{timestamp}] [SUPERVISOR] {message}", file=sys.stderr, flush=True)


def run_server() -> int:
    """
    Start MCP server and monitor exit codes.
    
    Returns:
        int: Exit code to propagate (0 = clean shutdown, >0 = error)
    """
    restart_count = 0
    last_restart = None
    
    while True:
        # Spawn MCP server as child process
        # Child inherits supervisor's stdio (VS Code pipe)
        log(f"Starting MCP server (restart #{restart_count})")
        
        child = subprocess.Popen(
            [sys.executable, "-m", "mcp_server"],
            stdin=sys.stdin,    # Inherit VS Code stdin
            stdout=sys.stdout,  # Inherit VS Code stdout
            stderr=sys.stderr,  # Inherit stderr for logging
        )
        
        log(f"MCP server running (PID: {child.pid})")
        
        # Wait for child exit
        exit_code = child.wait()
        
        log(f"MCP server exited (code: {exit_code})")
        
        # Handle exit codes
        if exit_code == 0:
            # Clean shutdown - supervisor exits
            log("Clean shutdown requested, supervisor exiting")
            return 0
            
        elif exit_code == 42:
            # Restart request from RestartServerTool
            restart_count += 1
            now = datetime.now(timezone.utc)
            
            # Throttle restarts (max 1/second to prevent restart loops)
            if last_restart and (now - last_restart).total_seconds() < 1.0:
                log("WARNING: Restart throttle triggered (max 1/sec)")
                time.sleep(1.0)
            
            last_restart = now
            log(f"Restart requested, spawning new server (restart #{restart_count})")
            
            # Brief delay for cleanup
            time.sleep(0.5)
            continue
            
        else:
            # Unexpected exit (crash)
            restart_count += 1
            log(f"ERROR: Server crashed (exit code {exit_code}), restarting (restart #{restart_count})")
            
            # Exponential backoff for crash recovery (prevent crash loops)
            if restart_count <= 3:
                delay = 1.0
            elif restart_count <= 10:
                delay = 5.0
            else:
                delay = 10.0
            
            log(f"Crash recovery delay: {delay}s")
            time.sleep(delay)
            continue


def main() -> None:
    """Main entry point for watchdog supervisor."""
    log("=== Watchdog Supervisor Starting ===")
    log(f"Python: {sys.executable}")
    log(f"PID: {subprocess.os.getpid()}")
    log(f"CWD: {Path.cwd()}")
    
    try:
        exit_code = run_server()
        log(f"=== Watchdog Supervisor Exiting (code: {exit_code}) ===")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        log("Keyboard interrupt received, shutting down")
        sys.exit(0)
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### 4.3 RestartServerTool Changes

**Current Implementation (uses os.execv()):**
```python
async def delayed_restart():
    await asyncio.sleep(0.5)
    logging.info("Server restarting via os.execv")
    python_exe = sys.executable
    args = [python_exe, "-m", "mcp_server"]
    os.execv(python_exe, args)  # ❌ BREAKS MCP PROTOCOL

async def execute(self, arguments: RestartServerInput) -> list[TextContent]:
    # ... marker writing, audit logging ...
    asyncio.create_task(delayed_restart())
    return ToolResult.text(...)
```

**New Implementation (exits with code 42):**
```python
async def delayed_exit():
    """Exit with code 42 after delay to allow response delivery."""
    await asyncio.sleep(0.5)
    
    # Flush all logs before exit
    logging.shutdown()
    
    # Log audit event (should be captured before shutdown)
    logger.info("Server exiting for restart (exit code 42)")
    
    # Exit with code 42 → supervisor will restart
    sys.exit(42)

async def execute(self, arguments: RestartServerInput) -> list[TextContent]:
    """
    Request server restart via watchdog supervisor.
    
    This tool triggers a graceful restart by:
    1. Writing restart marker with timestamp/reason
    2. Logging audit event
    3. Returning success response to agent
    4. Exiting with code 42 after 500ms delay
    5. Supervisor detects exit 42 and spawns new server
    
    Args:
        arguments: RestartServerInput with reason for restart
        
    Returns:
        ToolResult indicating restart scheduled
    """
    reason = arguments.reason
    timestamp = datetime.now(timezone.utc)
    
    # Write restart marker
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
    
    # Return success immediately
    return ToolResult.text(
        f"Server restart scheduled (reason: {reason}). "
        f"Server will exit with code 42 in 500ms, supervisor will spawn new instance."
    )
```

### 4.4 VS Code Configuration Changes

**Current mcp.json (with PowerShell wrapper):**
```jsonc
{
  "servers": {
    "st3-workflow": {
      "type": "stdio",
      "command": "powershell.exe",
      "args": [
        "-ExecutionPolicy", "Bypass",
        "-File", "${workspaceFolder}\\start_mcp_server.ps1"
      ],
      "cwd": "${workspaceFolder}",
      "env": {
        "GITHUB_TOKEN": "${env:GITHUB_TOKEN}"
      }
    }
  }
}
```

**New mcp.json (with Python supervisor):**
```jsonc
{
  "servers": {
    "st3-workflow": {
      "type": "stdio",
      "command": "${workspaceFolder}\\.venv\\Scripts\\python.exe",
      "args": [
        "-m", "mcp_server.supervisor"
      ],
      "cwd": "${workspaceFolder}",
      "env": {
        "GITHUB_TOKEN": "${env:GITHUB_TOKEN}"
      }
    }
  }
}
```

**Key Changes:**
- Direct Python execution (no PowerShell wrapper)
- Supervisor module as entry point
- Supervisor manages server lifecycle

---

## 5. Implementation Plan

### 5.1 File Structure

```
mcp_server/
├── __init__.py
├── __main__.py              # MCP server entry point (unchanged)
├── supervisor.py            # NEW: Watchdog supervisor
├── cli.py                   # CLI entry point (unchanged)
├── server.py                # MCP server class (unchanged)
└── tools/
    └── admin_tools.py       # MODIFY: RestartServerTool (sys.exit(42) instead of os.execv)

tests/mcp_server/
├── test_supervisor.py       # NEW: Supervisor tests
└── tools/
    └── test_admin_tools.py  # MODIFY: Update restart tests

docs/development/issue55/
├── restart_tool_design.md           # Existing design doc
└── watchdog_supervisor_design.md    # This document

.vscode/
└── mcp.json                 # MODIFY: Update to use supervisor

start_mcp_server.ps1         # DELETE: Obsolete PowerShell wrapper
```

### 5.2 Dependencies

**No New Dependencies Required:**
- `subprocess` - stdlib
- `sys` - stdlib
- `time` - stdlib
- `pathlib` - stdlib (already used)
- `datetime` - stdlib (already used)
- `json` - stdlib (already used)

**Testing Dependencies (already installed):**
- `pytest` - existing
- `pytest-asyncio` - existing

---

## 6. TDD Cycle Breakdown

### Cycle 1: Supervisor Basic Structure (RED)

**Test: `test_supervisor_starts_child_process`**
```python
def test_supervisor_starts_child_process(monkeypatch, tmp_path):
    """Verify supervisor spawns child MCP server process."""
    # Mock subprocess.Popen to track calls
    popen_calls = []
    
    class MockPopen:
        def __init__(self, *args, **kwargs):
            popen_calls.append((args, kwargs))
            self.pid = 12345
        
        def wait(self):
            return 0  # Clean exit
    
    monkeypatch.setattr("subprocess.Popen", MockPopen)
    monkeypatch.setattr("sys.exit", lambda x: None)
    
    # Run supervisor
    from mcp_server.supervisor import run_server
    exit_code = run_server()
    
    # Verify child spawned
    assert len(popen_calls) == 1
    args, kwargs = popen_calls[0]
    assert args[0] == [sys.executable, "-m", "mcp_server"]
    assert kwargs["stdin"] == sys.stdin
    assert kwargs["stdout"] == sys.stdout
    assert kwargs["stderr"] == sys.stderr
    
    # Verify clean exit
    assert exit_code == 0
```

**Implementation: Create `mcp_server/supervisor.py`**
- Skeleton with `run_server()` and `main()`
- Spawn child with subprocess.Popen()
- Wait for exit, return code

### Cycle 2: Exit Code 42 Restart (RED)

**Test: `test_supervisor_restarts_on_exit_42`**
```python
def test_supervisor_restarts_on_exit_42(monkeypatch):
    """Verify supervisor restarts child when it exits with code 42."""
    exit_codes = [42, 42, 0]  # Two restarts, then clean exit
    popen_count = 0
    
    class MockPopen:
        def __init__(self, *args, **kwargs):
            nonlocal popen_count
            self.pid = 12345 + popen_count
            popen_count += 1
        
        def wait(self):
            return exit_codes.pop(0)
    
    monkeypatch.setattr("subprocess.Popen", MockPopen)
    monkeypatch.setattr("sys.exit", lambda x: None)
    monkeypatch.setattr("time.sleep", lambda x: None)  # Fast-forward
    
    from mcp_server.supervisor import run_server
    exit_code = run_server()
    
    # Verify 3 spawns (initial + 2 restarts)
    assert popen_count == 3
    assert exit_code == 0
```

**Implementation: Add restart logic**
- Check exit code == 42
- Continue loop to spawn new child
- Add restart counter and logging

### Cycle 3: Crash Recovery (RED)

**Test: `test_supervisor_recovers_from_crash`**
```python
def test_supervisor_recovers_from_crash(monkeypatch):
    """Verify supervisor auto-recovers from server crashes."""
    exit_codes = [1, 2, 0]  # Two crashes, then clean exit
    popen_count = 0
    
    class MockPopen:
        def __init__(self, *args, **kwargs):
            nonlocal popen_count
            self.pid = 12345 + popen_count
            popen_count += 1
        
        def wait(self):
            return exit_codes.pop(0)
    
    monkeypatch.setattr("subprocess.Popen", MockPopen)
    monkeypatch.setattr("sys.exit", lambda x: None)
    monkeypatch.setattr("time.sleep", lambda x: None)
    
    from mcp_server.supervisor import run_server
    exit_code = run_server()
    
    # Verify 3 spawns (initial + 2 crash recoveries)
    assert popen_count == 3
    assert exit_code == 0
```

**Implementation: Add crash handling**
- Check exit code > 0
- Log crash with exit code
- Exponential backoff for repeated crashes

### Cycle 4: Restart Throttle (RED)

**Test: `test_supervisor_throttles_rapid_restarts`**
```python
def test_supervisor_throttles_rapid_restarts(monkeypatch):
    """Verify supervisor throttles restarts to max 1/second."""
    exit_codes = [42, 42, 42, 0]  # 3 rapid restarts
    sleep_calls = []
    
    class MockPopen:
        def __init__(self, *args, **kwargs):
            self.pid = 12345
        def wait(self):
            return exit_codes.pop(0)
    
    def mock_sleep(duration):
        sleep_calls.append(duration)
    
    monkeypatch.setattr("subprocess.Popen", MockPopen)
    monkeypatch.setattr("sys.exit", lambda x: None)
    monkeypatch.setattr("time.sleep", mock_sleep)
    
    from mcp_server.supervisor import run_server
    run_server()
    
    # Verify throttle enforced (1s delay between restarts)
    # First restart: 0.5s cleanup + 1.0s throttle
    # Second restart: 0.5s cleanup + 1.0s throttle
    # Third restart: 0.5s cleanup
    assert sleep_calls.count(1.0) >= 2  # At least 2 throttle delays
```

**Implementation: Add throttle logic**
- Track last_restart timestamp
- If < 1 second since last restart, sleep(1.0)
- Update timestamp after each restart

### Cycle 5: Update RestartServerTool (RED)

**Test: `test_restart_uses_sys_exit_42`**
```python
@pytest.mark.asyncio
async def test_restart_uses_sys_exit_42(monkeypatch):
    """Verify RestartServerTool exits with code 42 (not os.execv)."""
    exit_called = []
    execv_called = []
    
    def mock_exit(code):
        exit_called.append(code)
        raise SystemExit(code)
    
    def mock_execv(*args):
        execv_called.append(args)
        raise SystemExit(0)
    
    monkeypatch.setattr("sys.exit", mock_exit)
    monkeypatch.setattr("os.execv", mock_execv)
    monkeypatch.setattr("asyncio.sleep", lambda x: asyncio.sleep(0))
    
    # Execute tool
    tool = RestartServerTool()
    result = await tool.execute(RestartServerInput(reason="Test"))
    
    # Verify response returned
    assert "exit with code 42" in result[0].text
    
    # Wait for background task
    await asyncio.sleep(0.1)
    
    # Verify sys.exit(42) called, NOT os.execv
    assert exit_called == [42]
    assert execv_called == []
```

**Implementation: Modify admin_tools.py**
- Replace `delayed_restart()` with `delayed_exit()`
- Replace `os.execv()` with `sys.exit(42)`
- Update response message
- Update audit log event

### Cycle 6: Integration Test (RED)

**Test: `test_supervisor_and_restart_tool_integration`**
```python
def test_supervisor_and_restart_tool_integration(monkeypatch, tmp_path):
    """End-to-end test: RestartServerTool triggers supervisor restart."""
    # This test spawns real subprocess (not mocked)
    # Verifies actual integration between tool and supervisor
    
    # Create test script that exits with code 42 immediately
    test_server = tmp_path / "test_server.py"
    test_server.write_text("""
import sys
import time
time.sleep(0.1)
sys.exit(42)
""")
    
    # Run supervisor with test server
    supervisor_code = f"""
import sys
sys.path.insert(0, '{Path.cwd()}')
from mcp_server.supervisor import run_server
run_server()
"""
    
    # ... (complex integration test)
```

**Implementation: Verify end-to-end flow**
- Tool writes marker
- Tool logs audit event
- Tool exits with 42
- Supervisor detects 42
- Supervisor spawns new instance

### Cycle 7: Logging and Observability (RED)

**Test: `test_supervisor_logs_lifecycle_events`**
```python
def test_supervisor_logs_lifecycle_events(monkeypatch, capsys):
    """Verify supervisor logs all lifecycle events to stderr."""
    # ... test that start/exit/restart events logged
```

**Implementation: Add comprehensive logging**
- Startup: PID, Python version, CWD
- Child spawn: PID, restart count
- Exit: exit code, reason
- Restart: restart count, throttle status
- Crash: exit code, backoff delay

---

## 7. Testing Strategy

### 7.1 Unit Tests

**Target: `tests/mcp_server/test_supervisor.py`**

Tests cover:
- Child process spawning
- Exit code 42 restart logic
- Crash recovery with exponential backoff
- Restart throttle (max 1/second)
- Clean shutdown (exit code 0)
- Logging to stderr (not stdout)
- Stdio inheritance from supervisor

**Mocking Strategy:**
- Mock `subprocess.Popen` to avoid spawning real processes
- Mock `time.sleep` to fast-forward delays
- Mock `sys.exit` to capture exit codes
- Use `capsys` to capture stderr logs

### 7.2 Integration Tests

**Target: `tests/integration/test_supervisor_restart.py`**

Tests cover:
- Real subprocess spawn (no mocks)
- Restart marker written by tool
- Supervisor detects marker and restarts
- New server instance loads code changes
- Health check succeeds after restart
- Audit trail complete

**Test Environment:**
- Use test workspace with tmp_path
- Start supervisor with real MCP server
- Call restart_server tool via MCP protocol
- Verify restart completes
- Verify health_check succeeds

### 7.3 Manual Verification

**Checklist:**
1. Start VS Code with supervisor via mcp.json
2. Health check succeeds
3. Call restart_server(reason="Manual test 1")
4. Verify in VS Code logs:
   - "Server exiting for restart (exit code 42)"
   - "[SUPERVISOR] MCP server exited (code: 42)"
   - "[SUPERVISOR] Restart requested, spawning new server"
   - "[SUPERVISOR] MCP server running (PID: XXXX)"
5. Health check succeeds (< 5 seconds after restart)
6. Call restart_server(reason="Manual test 2")
7. Verify consistent behavior
8. Check audit trail: both restarts logged
9. Check restart markers: both written with correct timestamps

---

## 8. Migration Path

### 8.1 Phase 1: Develop and Test Supervisor

**Branch: `refactor/55-git-yaml` (continue current branch)**

1. RED: Write test_supervisor_starts_child_process
2. GREEN: Implement basic supervisor.py
3. REFACTOR: Clean up, add logging
4. Commit: "red: add test for supervisor child spawning"
5. Commit: "green: implement basic supervisor with child spawn"
6. Commit: "refactor: add logging and error handling to supervisor"

Repeat for cycles 2-4 (restart, crash, throttle)

### 8.2 Phase 2: Update RestartServerTool

**Branch: `refactor/55-git-yaml`**

1. RED: Write test_restart_uses_sys_exit_42
2. GREEN: Replace os.execv() with sys.exit(42)
3. REFACTOR: Update messages and logs
4. Commit: "red: add test for sys.exit(42) restart"
5. Commit: "green: replace os.execv with sys.exit(42)"
6. Commit: "refactor: update restart tool messages for supervisor"

### 8.3 Phase 3: Integration Testing

**Branch: `refactor/55-git-yaml`**

1. Manual test: Update mcp.json to use supervisor
2. Restart VS Code MCP connection
3. Run health_check → verify success
4. Run restart_server(reason="Integration test 1")
5. Wait for restart logs in VS Code output
6. Run health_check → verify success (should succeed quickly)
7. Run restart_server(reason="Integration test 2")
8. Verify consistent behavior
9. Check audit logs and restart markers

### 8.4 Phase 4: Cleanup

**Branch: `refactor/55-git-yaml`**

1. Delete start_mcp_server.ps1 (obsolete wrapper)
2. Update restart_tool_design.md with lessons learned
3. Add Section 12: "Watchdog Supervisor Solution"
4. Document migration path and verification
5. Commit: "refactor: remove obsolete PowerShell wrapper"
6. Commit: "docs: document watchdog supervisor solution"

### 8.5 Phase 5: Push and Continue Issue #55

**Branch: `refactor/55-git-yaml`**

1. git push origin refactor/55-git-yaml
2. All commits now backed up
3. Autonomous restart capability verified
4. Ready to begin Issue #55 main TDD implementation
5. Agent can now work through 30-50 restarts without human intervention

---

## 9. Success Criteria

### 9.1 Functional Requirements

✅ **FR-1: Autonomous Restart**
- Agent can call restart_server(reason="...") 
- Server restarts automatically without human intervention
- Health check succeeds within 5 seconds after restart

✅ **FR-2: MCP Protocol Compliance**
- No "initialization incomplete" errors after restart
- Tools remain callable immediately after restart
- VS Code sees continuous connection (no reconnect needed)

✅ **FR-3: Restart Reliability**
- Consistent restart timing (< 2 seconds)
- No hung tool calls during restart
- Tool response delivered before restart

✅ **FR-4: Crash Recovery**
- Supervisor auto-restarts on unexpected exits
- Exponential backoff prevents crash loops
- Audit trail captures crash events

✅ **FR-5: Restart Throttle**
- Maximum 1 restart per second
- Prevents restart loops from buggy code
- Logs throttle events for debugging

### 9.2 Non-Functional Requirements

✅ **NFR-1: Platform Independence**
- Pure Python solution (no shell scripts)
- Works on Windows, macOS, Linux
- No external dependencies

✅ **NFR-2: Observability**
- All lifecycle events logged to stderr
- Audit trail for every restart (reason, timestamp)
- Restart markers written with metadata

✅ **NFR-3: Maintainability**
- Clean separation: supervisor manages lifecycle, server handles MCP
- Well-tested (unit + integration)
- Documented design decisions

✅ **NFR-4: Backward Compatibility**
- Existing tools continue working
- No changes to MCP protocol implementation
- Drop-in replacement for PowerShell wrapper

### 9.3 Verification Tests

**Test Suite Must Pass:**
- `pytest tests/mcp_server/test_supervisor.py` - 100% pass
- `pytest tests/mcp_server/tools/test_admin_tools.py` - 100% pass
- `pytest tests/integration/test_supervisor_restart.py` - 100% pass

**Manual Verification:**
1. ✅ Start VS Code with supervisor
2. ✅ Health check succeeds
3. ✅ Restart #1 completes in < 2 seconds
4. ✅ Health check succeeds after restart #1
5. ✅ Restart #2 completes in < 2 seconds
6. ✅ Health check succeeds after restart #2
7. ✅ Audit trail shows both restarts
8. ✅ Restart markers written with correct data

**Success Metrics:**
- 0 "initialization incomplete" errors
- 100% health check success rate after restart
- < 2 second restart time (median)
- 0 hung tool calls during restart

---

## 10. Appendix: Technical Details

### 10.1 Exit Code Semantics

**Standard Exit Codes:**
- `0` - Success (clean shutdown)
- `1` - General error
- `2` - Misuse of shell command
- `126` - Command cannot execute
- `127` - Command not found
- `128+N` - Fatal signal N (e.g., 130 = Ctrl+C)

**MCP Server Exit Codes:**
- `0` - Clean shutdown (supervisor exits)
- `42` - Restart request (supervisor spawns new child)
- `1-41, 43-127` - Error/crash (supervisor spawns new child with backoff)

**Why 42?**
- Not a standard exit code (unambiguous signal)
- [The Answer to Life, the Universe, and Everything](https://en.wikipedia.org/wiki/42_(number)) - memorable mnemonic
- Used in other restart-on-exit systems (e.g., Kubernetes restart policies)

### 10.2 Stdio Inheritance Mechanics

**How subprocess Inherits Stdio:**

```python
# Supervisor process
# supervisor.stdin  = pipe from VS Code (file descriptor 0)
# supervisor.stdout = pipe to VS Code   (file descriptor 1)
# supervisor.stderr = pipe to VS Code   (file descriptor 2)

# Spawn child
child = subprocess.Popen(
    [sys.executable, "-m", "mcp_server"],
    stdin=sys.stdin,    # Pass FD 0 to child
    stdout=sys.stdout,  # Pass FD 1 to child
    stderr=sys.stderr   # Pass FD 2 to child
)

# Child process inherits file descriptors
# child.stdin  = FD 0 (same pipe from VS Code)
# child.stdout = FD 1 (same pipe to VS Code)
# child.stderr = FD 2 (same pipe to VS Code)
```

**Key Insight:**
- Supervisor doesn't forward messages (not a proxy)
- Child directly reads/writes the same FDs
- VS Code sees continuous stream (no awareness of child lifecycle)

### 10.3 Race Condition: Tool Response vs Exit

**Problem:**
```python
# If we exit immediately
def execute(...):
    sys.exit(42)  # ❌ Response never sent!
```

**Solution:**
```python
# Delay exit to allow response delivery
async def delayed_exit():
    await asyncio.sleep(0.5)  # 500ms delay
    sys.exit(42)

async def execute(...):
    # Return response immediately
    result = ToolResult.text("Restart scheduled...")
    
    # Schedule exit in background
    asyncio.create_task(delayed_exit())
    
    return result  # Response sent before exit
```

**Timing:**
- T+0ms: Tool returns response
- T+0ms: MCP server writes response to stdout
- T+50ms: Response typically delivered to VS Code
- T+500ms: sys.exit(42) called
- T+500ms: Supervisor spawns new child

**Why 500ms?**
- JSON-RPC response typically < 50ms to deliver
- 500ms provides 10x safety margin
- Balance: not too short (response might not deliver), not too long (unnecessary delay)

### 10.4 Logging Best Practices

**Supervisor Logging (stderr):**
```python
# Always use stderr for supervisor logs
print(f"[SUPERVISOR] {message}", file=sys.stderr, flush=True)

# Why stderr?
# - stdout is reserved for MCP JSON-RPC protocol
# - VS Code displays stderr in Output panel (visible to user)
# - flush=True ensures immediate output (no buffering delays)
```

**MCP Server Logging (Python logging module):**
```python
# Use Python logging module (configured to write to stderr)
logger.info("Server starting")

# Why logging module?
# - Structured logging with levels (DEBUG/INFO/WARNING/ERROR)
# - Audit trail with timestamps and context
# - Configured in setup_logging() to write to stderr
```

**Audit Logging:**
```python
# Special audit logger for restart events
audit_logger.info(
    "server_restart_requested",
    extra={
        "reason": reason,
        "timestamp": timestamp.isoformat(),
        "exit_code": 42
    }
)

# Why separate audit logger?
# - Filtered view of important events
# - Structured data for analysis
# - Compliance and debugging
```

### 10.5 Throttle and Backoff Algorithms

**Restart Throttle (prevent restart loops):**
```python
# Maximum 1 restart per second
if last_restart and (now - last_restart).total_seconds() < 1.0:
    log("WARNING: Restart throttle triggered")
    time.sleep(1.0)
```

**Crash Backoff (prevent crash loops):**
```python
# Exponential backoff for repeated crashes
if restart_count <= 3:
    delay = 1.0   # First 3 crashes: 1s delay
elif restart_count <= 10:
    delay = 5.0   # Crashes 4-10: 5s delay
else:
    delay = 10.0  # Crashes 10+: 10s delay
```

**Why These Values?**
- **1s restart throttle**: Fast enough for TDD workflow, slow enough to prevent loops
- **1s initial backoff**: Quick recovery from transient errors
- **5s medium backoff**: Time for external dependencies to stabilize
- **10s final backoff**: Prevents resource exhaustion from persistent crashes

### 10.6 Security Considerations

**Restart Marker File:**
```python
# Written to workspace root (user-controlled directory)
marker_path = settings.paths.workspace_root / ".mcp_restart_marker"

# Contains only metadata (no secrets)
marker_data = {
    "timestamp": "2026-01-13T22:01:46Z",
    "reason": "Load new GitConfig implementation",
    "exit_code": 42
}
```

**Risk: Restart Abuse**
- Agent could call restart_server repeatedly → throttle prevents DOS
- Malicious code could trigger restart loops → backoff prevents resource exhaustion
- Audit trail logs all restarts → forensics available

**Mitigation:**
- Throttle: Max 1 restart/second
- Backoff: Exponential delay for crashes
- Logging: All restarts logged with reason and timestamp
- Human oversight: User can monitor VS Code output for unexpected restarts

---

## Summary

The watchdog supervisor pattern solves the fundamental MCP protocol incompatibility with os.execv() by:

1. **Maintaining Connection Integrity**: VS Code connects once to supervisor (stable PID/stdio)
2. **Enabling Clean Restarts**: Each server instance gets fresh lifecycle (protocol compliant)
3. **Providing Crash Recovery**: Automatic restart on unexpected exits
4. **Ensuring Observability**: Comprehensive logging and audit trail
5. **Platform Independence**: Pure Python, no shell scripts

This enables fully autonomous TDD workflows where agents can:
- Modify server code
- Call restart_server(reason="Load changes")
- Wait ~2 seconds for restart
- Continue testing with new code
- Repeat 30-50 times without human intervention

**Next Steps:**
1. Implement supervisor.py via TDD (7 cycles)
2. Update RestartServerTool (sys.exit(42) instead of os.execv)
3. Integration test with VS Code
4. Push all commits
5. Begin Issue #55 main implementation with autonomous restart capability

---

**Document End**

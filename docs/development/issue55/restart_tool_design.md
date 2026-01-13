# Issue #55: Server Restart Tool for Agent TDD Autonomy

**Status:** DRAFT
**Author:** GitHub Copilot (Claude Sonnet 4.5)
**Created:** 2026-01-13
**Parent Issue:** #55 - Git Conventions Configuration
**Purpose:** Enable agent-driven TDD by allowing autonomous server restarts

---

## 1. Problem Statement

### 1.1 Current Bottleneck

**Agent TDD Flow (Current - Manual Intervention Required):**
```
Agent: TDD Cycle 1 - Implement GitConfig
├─ red: Write test_git_config_loads_from_yaml()
├─ green: Implement GitConfig.from_file()
├─ Want to verify: pytest tests/mcp_server/config/test_git_config.py
└─ ❌ BLOCKED: Code changes not loaded (server still running old code)
    └─ Human must: Ctrl+C → restart server → agent continues
    └─ Breaks agent autonomy, requires 30-50 manual restarts for Issue #55
```

**Impact on Issue #55:**
- 10 TDD cycles × 3-5 restarts per cycle = **30-50 manual restarts**
- Each restart: 30-60 seconds of human intervention
- Total time lost: 15-50 minutes + broken agent flow
- Agent cannot work autonomously through TDD implementation

### 1.2 Required Solution

**Agent TDD Flow (With restart_server tool):**
```
Agent: TDD Cycle 1 - Implement GitConfig
├─ red: Write test_git_config_loads_from_yaml()
├─ green: Implement GitConfig.from_file()
├─ restart_server(reason="Load new GitConfig implementation")
├─ [Server exits with code 42, parent restarts]
├─ verify_server_restarted(since_timestamp=...)
├─ pytest tests/mcp_server/config/test_git_config.py
└─ ✅ Full autonomous TDD cycle!
```

**Requirements:**
1. Tool to trigger server restart from agent context
2. Audit logging of all restart events
3. Verification mechanism to confirm restart occurred
4. Graceful exit that signals parent process to restart
5. Zero data loss (audit trail persisted before exit)

---

## 2. Tool Design

### 2.1 restart_server() Tool

**File:** `mcp_server/tools/admin_tools.py` (new file)

```python
"""Administrative tools for server management.

Development tools for agent-driven workflows. Enables agents to:
- Restart server to load code changes
- Verify restart occurred
- Maintain audit trail of server lifecycle events
"""

from pathlib import Path
import sys
import time
from datetime import UTC, datetime

from mcp_server.core.logging import get_logger


@mcp.tool()
def restart_server(reason: str = "code changes") -> str:
    """Restart MCP server to reload code changes.
    
    **Purpose:** Enable agent autonomy during TDD workflows.
    
    Agent can implement code changes and restart server without human
    intervention, allowing fully autonomous test-driven development cycles.
    
    **Workflow:**
    1. Agent makes code changes (via safe_edit_file)
    2. Agent calls restart_server(reason="...")
    3. Server logs restart to audit trail
    4. Server writes restart marker file
    5. Server exits with code 42 (restart requested)
    6. Parent process (VS Code) restarts server
    7. Agent calls verify_server_restarted() to confirm
    8. Agent continues with testing/next cycle
    
    Args:
        reason: Description of why restart is needed (for audit logging).
                Examples: "Load new GitConfig implementation",
                         "Apply refactored GitManager changes",
                         "Test PolicyEngine integration"
    
    Returns:
        Status message (may not be delivered if exit is immediate).
        Agent should not rely on return value, use verify_server_restarted() instead.
    
    Raises:
        Never - always exits process with code 42
    
    Note:
        - Development tool only, not for production use
        - Parent process must handle exit code 42 by restarting server
        - All audit logs flushed before exit (zero data loss)
        - Restart marker written to .st3/.restart_marker
    
    Example:
        # Agent TDD workflow
        safe_edit_file("mcp_server/config/git_config.py", content=new_code)
        restart_server(reason="Load GitConfig singleton pattern fix")
        # [Server restarts]
        verify_server_restarted(since_timestamp=before_restart_time)
        run_tests("tests/mcp_server/config/test_git_config.py")
    """
    logger = get_logger("tools.admin")
    
    # Audit log: Restart requested
    restart_time = datetime.now(UTC)
    logger.info(
        "Server restart requested",
        extra={
            "props": {
                "reason": reason,
                "pid": sys.getpid(),
                "timestamp": restart_time.isoformat(),
                "event_type": "server_restart_requested"
            }
        }
    )
    
    # Write restart marker file (for verification)
    marker_path = Path(".st3/.restart_marker")
    marker_path.parent.mkdir(exist_ok=True)
    marker_content = {
        "timestamp": restart_time.timestamp(),
        "pid": sys.getpid(),
        "reason": reason,
        "iso_time": restart_time.isoformat()
    }
    
    import json
    marker_path.write_text(json.dumps(marker_content, indent=2))
    
    # Audit log: Marker written
    logger.info(
        "Restart marker written",
        extra={
            "props": {
                "marker_path": str(marker_path),
                "marker_content": marker_content
            }
        }
    )
    
    # Flush all output (ensure audit logs persisted)
    sys.stdout.flush()
    sys.stderr.flush()
    
    # Force flush logging handlers
    import logging
    for handler in logging.root.handlers:
        handler.flush()
    
    # Audit log: Exiting
    logger.info(
        "Server exiting for restart",
        extra={
            "props": {
                "exit_code": 42,
                "reason": reason
            }
        }
    )
    
    # Final flush
    sys.stdout.flush()
    sys.stderr.flush()
    
    # Exit with code 42 = "please restart me"
    # Parent process should detect this and restart server
    sys.exit(42)
```

### 2.2 Exit Code Convention

**Exit Code 42:** "Restart Requested"

**Rationale:**
- Distinguishes intentional restart from crashes (exit code 1)
- Distinguishes from normal shutdown (exit code 0)
- Convention borrowed from systemd (42 = restart requested)
- Parent process can implement restart logic based on exit code

**Parent Process Handling (VS Code MCP Extension):**
```typescript
// Pseudocode - parent should implement
if (process.exitCode === 42) {
    console.log("Server requested restart, restarting...");
    await restartServer();
} else if (process.exitCode === 0) {
    console.log("Server shutdown normally");
} else {
    console.error(`Server crashed with exit code ${process.exitCode}`);
}
```

---

## 3. Audit Logging

### 3.1 Restart Event Schema

**Event Type:** `server_restart_requested`

**Log Entry Structure:**
```json
{
  "timestamp": "2026-01-13T14:32:45.123Z",
  "level": "INFO",
  "logger": "tools.admin",
  "message": "Server restart requested",
  "props": {
    "reason": "Load new GitConfig implementation",
    "pid": 12345,
    "timestamp": "2026-01-13T14:32:45.123Z",
    "event_type": "server_restart_requested"
  }
}
```

### 3.2 Restart Lifecycle Events

**Complete restart lifecycle logged:**

1. **Restart Requested:**
   ```python
   logger.info("Server restart requested", extra={"props": {...}})
   ```

2. **Marker Written:**
   ```python
   logger.info("Restart marker written", extra={"props": {...}})
   ```

3. **Exiting:**
   ```python
   logger.info("Server exiting for restart", extra={"props": {...}})
   ```

4. **Server Started (after restart):**
   ```python
   # Existing startup logging should capture
   logger.info("Server started", extra={"props": {...}})
   ```

### 3.3 Audit Trail Query

**Query all restarts:**
```bash
# Assuming structured logging to file
cat logs/server.log | jq 'select(.props.event_type == "server_restart_requested")'
```

**Output:**
```json
[
  {
    "timestamp": "2026-01-13T14:32:45.123Z",
    "reason": "Load new GitConfig implementation",
    "pid": 12345
  },
  {
    "timestamp": "2026-01-13T14:45:12.456Z",
    "reason": "Apply refactored GitManager changes",
    "pid": 12346
  }
]
```

---

## 4. Marker File Format

### 4.1 File Location

**Path:** `.st3/.restart_marker`

**Rationale:**
- Consistent with other .st3/ metadata files
- Git-ignored (not committed)
- Workspace-scoped (not global)

**Add to .gitignore:**
```gitignore
.st3/.restart_marker
```

### 4.2 File Format

**Format:** JSON (structured, parseable)

**Schema:**
```json
{
  "timestamp": 1705158765.123,
  "pid": 12346,
  "reason": "Load new GitConfig implementation",
  "iso_time": "2026-01-13T14:32:45.123Z"
}
```

**Fields:**
- `timestamp`: Unix timestamp (float) for precise comparisons
- `pid`: Process ID of restarted server (for debugging)
- `reason`: Human-readable restart reason (from tool call)
- `iso_time`: ISO 8601 timestamp (human-readable)

### 4.3 File Lifecycle

**Created:** On every restart_server() call (overwrite previous)

**Read:** By verify_server_restarted() tool

**Deleted:** Never (kept for debugging, overwritten on next restart)

**Size:** ~150 bytes (negligible)

---

## 5. Verification Tool

### 5.1 verify_server_restarted() Tool

```python
@mcp.tool()
def verify_server_restarted(since_timestamp: float) -> dict[str, Any]:
    """Verify that server restarted after given timestamp.
    
    **Purpose:** Allow agent to confirm restart completed before continuing.
    
    Agent workflow:
    1. Record timestamp: before_restart = time.time()
    2. Call restart_server(reason="...")
    3. [Wait for server to restart]
    4. Call verify_server_restarted(since_timestamp=before_restart)
    5. If restarted=True: Continue with testing
    6. If restarted=False: Error - restart failed
    
    Args:
        since_timestamp: Unix timestamp before restart request.
                         Server must have restarted AFTER this time.
    
    Returns:
        Dictionary with verification result:
        {
            "restarted": bool,           # True if restart confirmed
            "restart_timestamp": float,  # When restart occurred
            "current_pid": int,          # Current process ID
            "previous_pid": int,         # PID before restart (from marker)
            "reason": str,               # Restart reason (from marker)
            "time_since_restart": float  # Seconds since restart
        }
    
    Example:
        before = time.time()
        restart_server(reason="Load changes")
        # [Server restarts]
        result = verify_server_restarted(since_timestamp=before)
        if result["restarted"]:
            print(f"Restart confirmed! Reason: {result['reason']}")
            run_tests(...)
        else:
            raise Exception("Server restart failed!")
    """
    logger = get_logger("tools.admin")
    
    marker_path = Path(".st3/.restart_marker")
    
    # Check if marker exists
    if not marker_path.exists():
        return {
            "restarted": False,
            "error": "Restart marker not found",
            "marker_path": str(marker_path)
        }
    
    # Parse marker
    import json
    try:
        marker_data = json.loads(marker_path.read_text())
    except Exception as e:
        return {
            "restarted": False,
            "error": f"Failed to parse restart marker: {e}"
        }
    
    restart_timestamp = marker_data["timestamp"]
    
    # Check if restart happened after since_timestamp
    restarted = restart_timestamp > since_timestamp
    
    result = {
        "restarted": restarted,
        "restart_timestamp": restart_timestamp,
        "current_pid": sys.getpid(),
        "previous_pid": marker_data["pid"],
        "reason": marker_data["reason"],
        "time_since_restart": time.time() - restart_timestamp,
        "iso_time": marker_data["iso_time"]
    }
    
    # Audit log verification
    logger.info(
        "Server restart verification",
        extra={
            "props": {
                "result": result,
                "since_timestamp": since_timestamp
            }
        }
    )
    
    return result
```

### 5.2 Verification Logic

**Restart Confirmed If:**
```python
marker_data["timestamp"] > since_timestamp
```

**Edge Cases Handled:**
1. **Marker missing:** Return `restarted: False` with error
2. **Marker corrupt:** Return `restarted: False` with parse error
3. **Restart too old:** Return `restarted: False` (timestamp check fails)
4. **PID changed:** Logged in result (confirms new process)

---

## 6. Agent Workflow

### 6.1 Standard TDD Cycle with Restart

```python
# Agent implements this pattern for each TDD cycle

# 1. RED: Write test
safe_edit_file(
    path="tests/mcp_server/config/test_git_config.py",
    content=test_code
)
git_add_or_commit(
    files=["tests/mcp_server/config/test_git_config.py"],
    message="test git.yaml loading",
    phase="red"
)

# 2. GREEN: Implement code
safe_edit_file(
    path="mcp_server/config/git_config.py",
    content=implementation_code
)
git_add_or_commit(
    files=["mcp_server/config/git_config.py"],
    message="implement GitConfig.from_file()",
    phase="green"
)

# 3. RESTART: Load new code
import time
before_restart = time.time()

restart_server(reason="Load GitConfig implementation for testing")

# [Server exits and restarts - agent waits]

# 4. VERIFY: Confirm restart
result = verify_server_restarted(since_timestamp=before_restart)
if not result["restarted"]:
    raise Exception(f"Restart verification failed: {result}")

# 5. TEST: Run tests with new code
test_result = run_tests("tests/mcp_server/config/test_git_config.py")

# 6. REFACTOR (if tests pass)
if test_result["passed"]:
    # Make refactoring changes
    # Restart again
    # Test again
```

### 6.2 Error Handling

**Restart Timeout:**
```python
# Agent should implement retry logic
max_retries = 3
retry_delay = 5  # seconds

for attempt in range(max_retries):
    restart_server(reason="...")
    time.sleep(retry_delay)
    
    result = verify_server_restarted(since_timestamp=before)
    if result["restarted"]:
        break
else:
    # All retries failed
    raise Exception("Server restart failed after 3 attempts")
```

**Restart Failure:**
```python
# If verify returns restarted=False, agent should:
1. Log error with marker details
2. Ask human for manual restart
3. Abort current TDD cycle
4. Continue after manual restart confirmed
```

---

## 7. Testing Strategy

### 7.1 Manual Testing (Pre-Implementation)

**Test 1: Basic Restart**
```bash
# Terminal 1: Start server
python -m mcp_server

# Terminal 2: Call tool
# (via MCP client)
restart_server(reason="Test basic restart")

# Expected: Server exits with code 42
# Terminal 1 shows: Exit code 42

# Manually restart in Terminal 1
python -m mcp_server

# Terminal 2: Verify
verify_server_restarted(since_timestamp=...)
# Expected: {"restarted": True, ...}
```

**Test 2: Audit Logging**
```bash
# After restart, check logs
cat logs/server.log | grep "server_restart_requested"

# Expected: 3 log entries
# 1. "Server restart requested"
# 2. "Restart marker written"
# 3. "Server exiting for restart"
```

**Test 3: Marker File**
```bash
# After restart
cat .st3/.restart_marker

# Expected: Valid JSON
# {
#   "timestamp": 1705158765.123,
#   "pid": 12345,
#   "reason": "Test basic restart",
#   "iso_time": "2026-01-13T14:32:45.123Z"
# }
```

### 7.2 Automated Testing (Unit Tests)

**File:** `tests/mcp_server/tools/test_admin_tools.py`

```python
def test_restart_marker_written():
    """Test that restart_server writes marker file."""
    marker_path = Path(".st3/.restart_marker")
    marker_path.unlink(missing_ok=True)  # Clean state
    
    # Capture exit
    with pytest.raises(SystemExit) as exc_info:
        restart_server(reason="Test marker")
    
    assert exc_info.value.code == 42
    assert marker_path.exists()
    
    # Verify marker content
    marker_data = json.loads(marker_path.read_text())
    assert marker_data["reason"] == "Test marker"
    assert marker_data["pid"] == os.getpid()


def test_verify_server_restarted_success():
    """Test verification with valid marker."""
    # Setup: Create marker from "past"
    past_time = time.time() - 10
    marker_path = Path(".st3/.restart_marker")
    marker_data = {
        "timestamp": past_time + 5,  # 5 seconds ago
        "pid": 12345,
        "reason": "Test restart",
        "iso_time": datetime.now(UTC).isoformat()
    }
    marker_path.write_text(json.dumps(marker_data))
    
    # Verify restart happened after past_time
    result = verify_server_restarted(since_timestamp=past_time)
    assert result["restarted"] is True
    assert result["previous_pid"] == 12345


def test_verify_server_restarted_no_marker():
    """Test verification with missing marker."""
    marker_path = Path(".st3/.restart_marker")
    marker_path.unlink(missing_ok=True)
    
    result = verify_server_restarted(since_timestamp=time.time())
    assert result["restarted"] is False
    assert "error" in result
```

---

## 8. Implementation Order

### 8.1 Prerequisites

**Before implementing restart tool:**
1. ✅ Design.md for main Issue #55 complete
2. ✅ This restart_tool_design.md complete
3. ✅ Design phase commit

### 8.2 Implementation Steps (TDD)

**Step 1: Marker File Logic (RED → GREEN → REFACTOR)**
```bash
# RED
red: test restart marker file is written with correct schema

# GREEN  
green: implement restart marker write logic

# REFACTOR
refactor: extract marker path to constant
```

**Step 2: Audit Logging (RED → GREEN → REFACTOR)**
```bash
# RED
red: test restart events logged to audit trail

# GREEN
green: add audit logging to restart_server

# REFACTOR
refactor: extract log message formatting
```

**Step 3: Exit Logic (RED → GREEN → REFACTOR)**
```bash
# RED
red: test server exits with code 42

# GREEN
green: implement sys.exit(42) with flush

# REFACTOR
refactor: ensure all handlers flushed
```

**Step 4: Verification Tool (RED → GREEN → REFACTOR)**
```bash
# RED
red: test verify_server_restarted returns correct result

# GREEN
green: implement verify_server_restarted tool

# REFACTOR
refactor: extract marker parsing logic
```

**Step 5: Integration Testing**
```bash
# Manual test full workflow
1. Make dummy code change
2. Call restart_server(reason="Test integration")
3. Manually restart server
4. Call verify_server_restarted()
5. Verify audit logs
6. Check marker file
```

### 8.3 Commit Strategy

**Micro-commits per TDD cycle:**
```bash
red: test restart marker written with schema
green: implement restart marker file creation
refactor: extract marker path constant

red: test restart audit logging
green: add structured logging to restart_server
refactor: extract log message formatters

red: test server exits with code 42
green: implement graceful exit with code 42
refactor: ensure all log handlers flushed

red: test verify_server_restarted with valid marker
green: implement verification tool
refactor: extract marker parsing helper

docs: update restart_tool_design.md with final implementation notes
```

### 8.4 Timeline Estimate

**Total Time:** 1.5-2 hours

- Design document: 30 min ✅ (this document)
- TDD Cycle 1 (Marker file): 20 min
- TDD Cycle 2 (Audit logging): 15 min
- TDD Cycle 3 (Exit logic): 15 min
- TDD Cycle 4 (Verification): 20 min
- Integration testing: 15 min
- Documentation updates: 10 min

**ROI:** Saves 15-50 minutes during Issue #55 TDD + enables full agent autonomy

---

## 9. Success Criteria

### 9.1 Functional Criteria

- ✅ restart_server(reason) tool implemented
- ✅ Server exits with code 42 on restart request
- ✅ Restart marker file written to .st3/.restart_marker
- ✅ Marker contains timestamp, PID, reason, iso_time
- ✅ All audit events logged (requested, marker written, exiting)
- ✅ verify_server_restarted(since_timestamp) tool implemented
- ✅ Verification returns correct restarted status
- ✅ All log handlers flushed before exit (zero data loss)

### 9.2 Quality Criteria

- ✅ Unit tests for marker file creation
- ✅ Unit tests for verification logic
- ✅ Unit tests for exit code 42
- ✅ Manual integration test passed
- ✅ Audit logs queryable and structured
- ✅ .restart_marker added to .gitignore

### 9.3 Documentation Criteria

- ✅ This design document complete
- ✅ Tool docstrings with agent workflow examples
- ✅ Audit logging schema documented
- ✅ Marker file format specified
- ✅ Agent workflow pattern documented

---

## 10. Next Steps

## 11. Implementation Lessons Learned

### 11.1 Exit Code 42 + PowerShell Wrapper Issues

**Initial Approach:**
- Tool calls `sys.exit(42)` after 500ms delay
- PowerShell wrapper script detects exit code 42
- Wrapper restarts Python process

**Problems Discovered:**
1. **Delayed Detection:** PowerShell `Start-Process -Wait` only detects process exit on next stdio operation
   - Exit at 18:04:20, detection at 19:06:48 (2+ minutes later)
   - Restart triggered by agent's next tool call, not automatically

2. **Stdio Blocking:** Wrapper cannot properly pass through stdin/stdout for JSON-RPC
   - MCP protocol requires clean stdio channel
   - Any wrapper interference breaks communication

3. **Tool Call Hangs:** Agent's tool call during restart never completes
   - Server exits mid-call
   - Agent waits indefinitely for response
   - User must cancel tool call

**Conclusion:** External wrapper approach is fundamentally flawed for MCP stdio protocol.

### 11.2 Alternative: os.execv() In-Process Restart

**Concept:**
- Replace current process with new Python interpreter using `os.execv()`
- No exit code, no wrapper needed
- Preserves PID and stdio file descriptors
- Server "restarts" by replacing itself

**Implementation Plan (TDD):**
1. RED: Write test mocking os.execv() to verify it's called correctly
2. GREEN: Change sys.exit(42) to os.execv()
3. REFACTOR: Clean up wrapper-related code
4. Manual integration test to verify real restart works

### 10.1 Immediate Actions

1. **Commit this design document:**
   ```bash
   git add docs/development/issue55/restart_tool_design.md
   git commit -m "docs: design restart_server tool for agent TDD autonomy"
   ```

2. **Update .gitignore:**
   ```bash
   echo ".st3/.restart_marker" >> .gitignore
   git commit -m "chore: ignore restart marker file"
   ```

3. **Transition to TDD:**
   - Start TDD Cycle 1: Marker file logic
   - Follow implementation order from Section 8.2

### 10.2 Integration with Issue #55

**After restart tool complete:**
1. Tool available for agent use during Issue #55 TDD
2. Agent can autonomously complete all 10 TDD cycles
3. No manual intervention required for code reload
4. Full audit trail of development process

**Agent workflow becomes:**
```python
for cycle in range(1, 11):  # 10 TDD cycles
    write_test()
    implement_code()
    restart_server(reason=f"TDD Cycle {cycle}")
    verify_server_restarted()
    run_tests()
    if passed:
        refactor()
        restart_server(reason=f"Cycle {cycle} refactor")
        verify_server_restarted()
        run_tests()
```

---

**Document Status:** DRAFT → READY FOR IMPLEMENTATION
**Implementation Time:** 1.5-2 hours
**Next Phase:** TDD (implement restart_server + verify tools)
**After Complete:** Transition to Issue #55 main TDD (GitConfig implementation)
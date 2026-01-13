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
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path


def log(message: str) -> None:
    """
    Log to stderr (safe for MCP protocol).

    MCP protocol requires clean stdout for JSON-RPC messages.
    All supervisor logging goes to stderr.
    """
    timestamp = datetime.now(UTC).isoformat()
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

        if exit_code == 42:
            # Restart request from RestartServerTool
            restart_count += 1
            now = datetime.now(UTC)

            # Throttle restarts (max 1/second to prevent restart loops)
            if last_restart and (now - last_restart).total_seconds() < 1.0:
                log("WARNING: Restart throttle triggered (max 1/sec)")
                time.sleep(1.0)

            last_restart = now
            log(f"Restart requested, spawning new server (restart #{restart_count})")

            # Brief delay for cleanup
            time.sleep(0.5)
            continue

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
    log(f"PID: {os.getpid()}")
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

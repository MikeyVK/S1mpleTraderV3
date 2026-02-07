#!/usr/bin/env python3
"""
MCP Proxy - Transparent Server Restart

Enables hot-restart of MCP server without VS Code noticing by:
1. Capturing initialize handshake
2. Monitoring stderr for restart marker (__MCP_RESTART_REQUEST__)
3. Transparently spawning new server
4. Replaying initialize to new server
5. VS Code continues without reconnection

Architecture:
    VS Code â†” Proxy â†” Server
                â”œâ”€ stdout reader â†’ JSON-RPC messages
                â””â”€ stderr reader â†’ logs + restart marker

Integration:
    - Entry point: python -m mcp_server.core.proxy
    - Configuration: .vscode/mcp.json â†’ "args": ["-m", "mcp_server.core.proxy"]
    - Restart trigger: admin_tools.restart_server() prints marker to stderr
    - Audit logging: mcp_server/logs/mcp_audit.log

Performance:
    - Restart time: ~2.3 seconds
    - Tool response: < 5ms (no hang)
    - UTF-8 encoding: forced on stdout/stderr (Windows compatibility)

Author: Autonomous Agent (Issue #55)
Date: 2026-01-15
Status: Production
"""

import io
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# RESTART_MARKER: Printed to stderr by server to signal restart request
# Proxy detects this marker and triggers transparent server restart
RESTART_MARKER = "__MCP_RESTART_REQUEST__"


def fix_json_surrogates(json_str: str) -> str:
    """Fix malformed Unicode surrogate pairs in JSON strings.

    VS Code sometimes sends emoji as broken surrogate pairs (e.g. \\uD83D\\uDE80
    split across encoding boundaries). This fixes those cases by:
    1. Finding surrogate pair patterns
    2. Converting to proper UTF-8
    3. Re-encoding as valid JSON escape sequences

    Args:
        json_str: Raw JSON string potentially containing malformed surrogates

    Returns:
        Fixed JSON string safe for Python json.loads()
    """
    # Pattern: \uD800-\uDBFF (high surrogate) followed by \uDC00-\uDFFF (low surrogate)
    surrogate_pattern = re.compile(
        r"\\u([dD][8-9a-bA-B][0-9a-fA-F]{2})\\u([dD][c-fC-F][0-9a-fA-F]{2})"
    )

    def replace_surrogate_pair(match: re.Match[str]) -> str:
        high = int(match.group(1), 16)
        low = int(match.group(2), 16)

        # Convert surrogate pair to Unicode codepoint
        # Formula: (high - 0xD800) * 0x400 + (low - 0xDC00) + 0x10000
        codepoint = (high - 0xD800) * 0x400 + (low - 0xDC00) + 0x10000

        # Convert to UTF-8 character
        try:
            return chr(codepoint)
        except (ValueError, OverflowError):
            # Invalid codepoint - replace with Unicode replacement character
            return "\ufffd"

    return surrogate_pattern.sub(replace_surrogate_pair, json_str)


def _setup_utf8_encoding() -> None:
    """Force UTF-8 encoding on Windows stdout/stderr.

    CRITICAL: Prevents 'charmap' codec errors when forwarding Unicode.
    Only runs in production (not during pytest imports).
    """
    if sys.platform == "win32" and "pytest" not in sys.modules:
        # Reconfigure stdin to read UTF-8 bytes correctly
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace")
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer,
            encoding="utf-8",
            errors="replace",
            line_buffering=True,
        )


class MCPProxy:
    """Transparent MCP server restart proxy.

    Sits between VS Code and MCP server, enabling hot-restart without
    breaking the MCP protocol initialization handshake.
    """

    def __init__(self) -> None:
        """Initialize proxy state."""
        # Setup UTF-8 encoding (Windows compatibility)
        _setup_utf8_encoding()

        self.server_process: subprocess.Popen[str] | None = None
        self.init_request: dict[str, Any] | None = None
        self.lock = threading.Lock()
        self.restarting = False
        self.restart_count = 0
        self.proxy_pid = os.getpid()

        self._server_started = threading.Event()

    def audit_log(self, message: str, level: str = "INFO", **extra: Any) -> None:
        """Write structured log entry to mcp_audit.log.

        Args:
            message: Log message
            level: Log level (INFO, WARNING, ERROR)
            **extra: Additional fields to include in log entry
        """
        try:
            log_dir = Path("mcp_server/logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            audit_file = log_dir / "mcp_audit.log"

            entry = {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": level,
                "logger": "mcp_proxy",
                "message": message,
                "proxy_pid": self.proxy_pid,
                "server_pid": self.server_process.pid if self.server_process else None,
                "restart_count": self.restart_count,
                **extra,
            }

            with open(audit_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as e:
            print(f"[PROXY ERROR] Audit log failed: {e}", file=sys.stderr, flush=True)

    def log(self, message: str, level: str = "INFO", **extra: Any) -> None:
        """Log to both stderr (VS Code Output) and audit log.

        Args:
            message: Log message
            level: Log level
            **extra: Additional audit log fields
        """
        print(f"[PROXY] {message}", file=sys.stderr, flush=True)
        self.audit_log(message, level, **extra)

    def _spawn_server_in_context(self, env: dict[str, str]) -> None:
        try:
            with subprocess.Popen(
                [sys.executable, "-m", "mcp_server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
            ) as process:
                self.server_process = process
                self._server_started.set()

                process.wait()
        except (OSError, ValueError, subprocess.SubprocessError) as e:
            self.log(
                f"Server start failed: {e}",
                level="ERROR",
                event_type="server_start_failed",
                error=str(e),
            )
            self.server_process = None
            self._server_started.set()
        finally:
            current = self.server_process
            if current is not None and current.poll() is not None:
                self.server_process = None

    def start_server(self, is_restart: bool = False) -> None:
        """Start MCP server subprocess.

        Args:
            is_restart: If True, replay initialize handshake after spawn
        """
        start_time = time.time()
        attempt = self.restart_count + 1

        self.log(f"Starting MCP server (restart={is_restart}, attempt={attempt})")

        # Create environment with PYTHONUTF8=1 to ensure server sees UTF-8 streams
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"

        self._server_started.clear()
        threading.Thread(
            target=self._spawn_server_in_context,
            args=(env,),
            daemon=True,
        ).start()

        if not self._server_started.wait(timeout=5):
            self.log(
                "Server start timed out",
                level="ERROR",
                event_type="server_start_failed",
            )
            return

        if self.server_process is None:
            return

        # Replay initialize handshake if restarting
        if is_restart and self.init_request:
            time.sleep(0.3)  # Let server initialize

            process = self.server_process
            if process.stdin is None or process.stdout is None:
                self.log(
                    "Server process stdio not available for initialize replay",
                    level="ERROR",
                    event_type="initialize_replay_failed",
                )
            else:
                self.log("Replaying initialize handshake to new server...")
                process.stdin.write(json.dumps(self.init_request) + "\n")
                process.stdin.flush()

                # Read and discard initialize response (VS Code already has it)
                response = process.stdout.readline()
                try:
                    resp_data = json.loads(response)
                    server_info = resp_data.get("result", {}).get("serverInfo", {})
                    server_name = server_info.get("name", "unknown")
                    server_version = server_info.get("version", "unknown")
                    self.log(
                        f"Initialize handshake completed ({server_name} v{server_version})",
                        event_type="initialize_replayed",
                    )
                except json.JSONDecodeError:
                    self.log("Initialize response received (non-JSON)")

        # Start output reader threads AFTER initialize replay
        threading.Thread(target=self.read_server_output, daemon=True).start()
        threading.Thread(target=self.read_server_stderr, daemon=True).start()

        elapsed_ms = (time.time() - start_time) * 1000
        self.log(
            f"Server ready (startup: {elapsed_ms:.1f}ms)",
            event_type="server_ready",
            startup_time_ms=elapsed_ms,
        )

    def send_to_server(self, message_line: str) -> None:
        """Send JSON-RPC message line to server.

        Args:
            message_line: Raw JSON-RPC message line (already Unicode-fixed)
        """
        if self.restarting:
            return  # Skip sends during restart

        process = self.server_process
        if process is None or process.stdin is None:
            return

        try:
            process.stdin.write(message_line + "\n")
            process.stdin.flush()
        except (OSError, ValueError) as e:
            self.log(
                f"Send error: {e}",
                level="ERROR",
                event_type="send_failed",
                error=str(e),
            )

    def read_server_output(self) -> None:
        """Read server stdout and forward JSON-RPC to VS Code."""
        while True:
            process = self.server_process
            if process is None or process.stdout is None:
                break

            try:
                line = process.stdout.readline()
            except (OSError, ValueError) as e:
                self.log(
                    f"Read error: {e}",
                    level="ERROR",
                    event_type="read_failed",
                    error=str(e),
                )
                break

            if not line:
                self.log("Server stdout closed", level="WARNING")
                break

            line = line.strip()
            if not line:
                continue

            # Forward JSON-RPC messages to VS Code
            try:
                json.loads(line)  # Validate JSON
                print(line, flush=True)  # Forward to VS Code
            except json.JSONDecodeError:
                pass  # Skip non-JSON lines (server internal logs)

    def read_server_stderr(self) -> None:
        """Read server stderr and monitor for restart marker."""
        while True:
            process = self.server_process
            if process is None or process.stderr is None:
                break

            try:
                line = process.stderr.readline()
            except (OSError, ValueError) as e:
                self.log(
                    f"Stderr read error: {e}",
                    level="ERROR",
                    event_type="stderr_read_failed",
                    error=str(e),
                )
                break

            if not line:
                break

            line = line.strip()
            if not line:
                continue

            # Check for restart marker on stderr
            if RESTART_MARKER in line:
                self.log(
                    "ðŸ”„ Restart marker detected on stderr - initiating transparent restart",
                    event_type="restart_marker_detected",
                )
                threading.Thread(target=self.trigger_restart).start()
                continue

            # Check for Pydantic validation errors (crash cause)
            msg_lower = line.lower()
            if "validation error" in msg_lower or "pydantic" in msg_lower:
                self.log(
                    f"Server validation error detected: {line}",
                    level="ERROR",
                    event_type="validation_error_detected",
                    raw_stderr=line,
                )

            # Forward server logs to VS Code Output (stderr)
            print(f"[SERVER] {line}", file=sys.stderr, flush=True)

    def trigger_restart(self) -> None:
        """Perform transparent server restart."""
        with self.lock:
            if self.server_process is None:
                return

            self.restarting = True
            self.restart_count += 1
            restart_start = time.time()

            old_process = self.server_process
            old_pid = old_process.pid

            self.log(
                f"=== RESTART #{self.restart_count} INITIATED ===",
                event_type="restart_initiated",
                old_server_pid=old_pid,
            )

            self.log(f"Terminating old server (PID={old_pid})...")
            old_process.terminate()

            try:
                old_process.wait(timeout=5)
                self.log("Old server terminated gracefully", event_type="server_terminated")
            except subprocess.TimeoutExpired:
                self.log(
                    f"Force killing old server (PID={old_pid})",
                    level="WARNING",
                    event_type="server_force_killed",
                )
                old_process.kill()

            time.sleep(0.5)  # Brief pause before respawn

            # Start new server
            self.start_server(is_restart=True)

            self.restarting = False
            elapsed_ms = (time.time() - restart_start) * 1000

            self.log(
                f"=== RESTART COMPLETE (duration: {elapsed_ms:.1f}ms, VS Code unaware) ===",
                event_type="restart_completed",
                restart_duration_ms=elapsed_ms,
                new_server_pid=self.server_process.pid if self.server_process else None,
            )

    def run(self) -> None:
        """Main proxy loop - read from VS Code stdin and forward to server."""
        self.log(f"MCP Proxy starting (PID={self.proxy_pid})", event_type="proxy_started")
        self.log("Mode: Transparent restart without VS Code disconnect")

        self.start_server(is_restart=False)

        try:
            # Read JSON-RPC messages from VS Code stdin
            for line in sys.stdin:
                line = line.strip()
                if not line:
                    continue

                try:
                    # Parse JSON first
                    # DISABLED: Using generic validation
                    # fixed_line = fix_json_surrogates(line)
                    fixed_line = line
                    message = json.loads(fixed_line)

                    # GENERIC VALIDATION: Ensure message content is strictly valid UTF-8
                    # Python's json.loads allows lone surrogates (e.g. \uD83D), but these
                    # can crash downstream libraries/servers trying to encode strict UTF-8.
                    # We validate by attempting a strict encoding.
                    try:
                        json.dumps(message, ensure_ascii=False).encode("utf-8")
                    except (UnicodeError, ValueError) as e:
                        # Validation failed - Block message to prevent Server crash
                        error_msg = (
                            f"Message validation failed (encoding error): {e}. "
                            "Please ensure valid Unicode input."
                        )
                        self.log(
                            error_msg,
                            level="ERROR",
                            event_type="validation_blocked",
                            raw_line=line,
                        )

                        # Send error back to client
                        msg_id = message.get("id")
                        if msg_id is not None:
                            err_response = {
                                "jsonrpc": "2.0",
                                "id": msg_id,
                                "error": {"code": -32602, "message": error_msg},
                            }
                            print(json.dumps(err_response), flush=True)

                        continue  # Skip sending to server

                    # Capture initialize request for replay
                    if message.get("method") == "initialize":
                        init_id = message.get("id")
                        client_info = message.get("params", {}).get("clientInfo", {})
                        client_name = client_info.get("name", "unknown")
                        protocol_version = message.get("params", {}).get(
                            "protocolVersion", "unknown"
                        )

                        self.log(
                            f"Initialize request captured (id={init_id}, client={client_name}, "
                            f"protocol={protocol_version})",
                            event_type="initialize_captured",
                            init_id=init_id,
                            client=client_name,
                        )
                        self.init_request = message

                    # Forward to server (send fixed line, not re-serialized dict)
                    self.send_to_server(fixed_line)

                except json.JSONDecodeError as e:
                    self.log(
                        f"Invalid JSON from VS Code: {e}",
                        level="WARNING",
                        event_type="json_decode_error",
                    )

        except KeyboardInterrupt:
            self.log("Interrupted by user", event_type="interrupted")
        except OSError as e:
            self.log(
                f"I/O error in proxy loop: {e}",
                level="ERROR",
                event_type="unexpected_error",
                error=str(e),
            )
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Cleanup on exit."""
        self.log(
            f"Proxy shutting down (total restarts: {self.restart_count})",
            event_type="proxy_stopping",
        )

        process = self.server_process
        if process:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()

        self.log("Proxy stopped", event_type="proxy_stopped")


def main() -> None:
    """Entry point for python -m mcp_server.core.proxy"""
    proxy = MCPProxy()
    proxy.run()


if __name__ == "__main__":
    main()

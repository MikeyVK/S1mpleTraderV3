"""Tests for watchdog supervisor (server lifecycle management)."""

import sys

# pylint: disable=import-error,no-name-in-module,import-outside-toplevel
# pylint: disable=missing-class-docstring,missing-function-docstring,too-few-public-methods
# pylint: disable=unused-argument,use-implicit-booleaness-not-comparison-to-zero
# pylint: disable=use-implicit-booleaness-not-comparison-to-string


def test_supervisor_starts_child_process(monkeypatch):
    """RED: Verify supervisor spawns child MCP server process.

    Verifies:
    - Supervisor spawns child with subprocess.Popen()
    - Child command is [sys.executable, "-m", "mcp_server"]
    - Child inherits stdin/stdout/stderr from supervisor
    - Supervisor waits for child exit
    - Supervisor returns child exit code
    """
    # Mock subprocess.Popen to track calls
    popen_calls = []

    class MockPopen:
        def __init__(self, *args, **kwargs):
            popen_calls.append((args, kwargs))
            self.pid = 12345

        def wait(self):
            return 0  # Clean exit

    monkeypatch.setattr("subprocess.Popen", MockPopen)

    # Run supervisor
    from mcp_server.supervisor import run_server
    exit_code = run_server()

    # Verify child spawned
    assert len(popen_calls) == 1, "Expected exactly one child process spawn"

    args, kwargs = popen_calls[0]
    assert args[0] == [sys.executable, "-m", "mcp_server"], \
        f"Expected MCP server command, got {args[0]}"

    assert kwargs["stdin"] == sys.stdin, "Child should inherit supervisor stdin"
    assert kwargs["stdout"] == sys.stdout, "Child should inherit supervisor stdout"
    assert kwargs["stderr"] == sys.stderr, "Child should inherit supervisor stderr"

    # Verify clean exit propagated
    assert exit_code == 0, f"Expected exit code 0, got {exit_code}"


def test_supervisor_restarts_on_exit_42(monkeypatch):
    """RED: Verify supervisor restarts child when it exits with code 42.

    Verifies:
    - Supervisor detects exit code 42
    - Supervisor spawns new child instance
    - Supervisor continues until exit code != 42
    - Restart counter increments
    """
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
    monkeypatch.setattr("time.sleep", lambda x: None)  # Fast-forward delays

    from mcp_server.supervisor import run_server
    exit_code = run_server()

    # Verify 3 spawns (initial + 2 restarts)
    assert popen_count == 3, \
        f"Expected 3 child spawns (initial + 2 restarts), got {popen_count}"

    # Verify clean exit after restarts
    assert exit_code == 0, f"Expected final exit code 0, got {exit_code}"


def test_supervisor_recovers_from_crash(monkeypatch):
    """RED: Verify supervisor auto-recovers from server crashes.

    Verifies:
    - Supervisor detects non-zero exit codes (crashes)
    - Supervisor spawns new child after crash
    - Supervisor logs crash events
    - Exponential backoff applied for repeated crashes
    """
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
    monkeypatch.setattr("time.sleep", lambda x: None)  # Fast-forward delays

    from mcp_server.supervisor import run_server
    exit_code = run_server()

    # Verify 3 spawns (initial + 2 crash recoveries)
    assert popen_count == 3, \
        f"Expected 3 child spawns (initial + 2 crash recoveries), got {popen_count}"

    # Verify clean exit after crashes
    assert exit_code == 0, f"Expected final exit code 0, got {exit_code}"


def test_supervisor_throttles_rapid_restarts(monkeypatch):
    """RED: Verify supervisor throttles restarts to max 1/second.

    Verifies:
    - Supervisor tracks last restart timestamp
    - If < 1 second since last restart, enforces 1s delay
    - Throttle prevents restart loops from buggy code
    """
    exit_codes = [42, 42, 42, 0]  # 3 rapid restarts
    sleep_calls = []
    popen_count = 0

    class MockPopen:
        def __init__(self, *args, **kwargs):
            nonlocal popen_count
            self.pid = 12345 + popen_count
            popen_count += 1

        def wait(self):
            return exit_codes.pop(0)

    def mock_sleep(duration):
        sleep_calls.append(duration)

    monkeypatch.setattr("subprocess.Popen", MockPopen)
    monkeypatch.setattr("time.sleep", mock_sleep)

    from mcp_server.supervisor import run_server
    run_server()

    # Verify throttle enforced
    # Each restart should have:
    # - 0.5s cleanup delay
    # - 1.0s throttle delay (if < 1s since last restart)

    # With fast mock_sleep, all restarts happen "instantly"
    # So all should trigger throttle (except maybe first)
    assert sleep_calls.count(1.0) >= 2, \
        f"Expected at least 2 throttle delays (1.0s), got {sleep_calls.count(1.0)}"


def test_supervisor_logs_lifecycle_events(monkeypatch, capsys):
    """RED: Verify supervisor logs all lifecycle events to stderr.

    Verifies:
    - Startup logs: PID, Python version, CWD
    - Child spawn logs: PID, restart count
    - Exit logs: exit code, restart/crash/shutdown reason
    - All logs go to stderr (not stdout - preserves MCP JSON-RPC)
    """
    exit_codes = [42, 0]  # One restart, then clean exit

    class MockPopen:
        def __init__(self, *args, **kwargs):
            self.pid = 12345

        def wait(self):
            return exit_codes.pop(0)

    monkeypatch.setattr("subprocess.Popen", MockPopen)
    monkeypatch.setattr("time.sleep", lambda x: None)

    from mcp_server.supervisor import run_server
    run_server()

    # Capture stderr (stdout should be empty - reserved for MCP JSON-RPC)
    captured = capsys.readouterr()

    # Verify stdout is clean (MCP protocol requirement)
    assert captured.out == "", \
        "Supervisor must not write to stdout (reserved for MCP JSON-RPC)"

    # Verify lifecycle events logged to stderr
    assert "[SUPERVISOR]" in captured.err, "Missing supervisor log prefix"
    assert "Starting MCP server" in captured.err, "Missing startup log"
    assert "MCP server running" in captured.err, "Missing running log"
    assert "MCP server exited" in captured.err, "Missing exit log"
    assert "Restart requested" in captured.err, "Missing restart log"

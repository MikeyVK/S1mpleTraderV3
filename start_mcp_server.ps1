# MCP Server Wrapper with Auto-Restart on Exit Code 42
# This wrapper monitors the MCP server and automatically restarts it when
# it exits with code 42 (restart requested by restart_server tool)

param(
    [string]$VenvPath = ".venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

# Write status messages to stderr (VS Code expects only JSON-RPC on stdout)
[Console]::Error.WriteLine("=== MCP Server Wrapper ===")
[Console]::Error.WriteLine("Monitoring for exit code 42 (auto-restart)")
[Console]::Error.WriteLine("")

$restartCount = 0

while ($true) {
    if ($restartCount -gt 0) {
        $timestamp = Get-Date -Format 'HH:mm:ss'
        [Console]::Error.WriteLine("[$timestamp] Restart #$restartCount")
    }
    
    # Start server process
    $process = Start-Process -FilePath $VenvPath `
                              -ArgumentList "-m", "mcp_server" `
                              -WorkingDirectory $PSScriptRoot `
                              -PassThru `
                              -NoNewWindow `
                              -Wait
    
    $exitCode = $process.ExitCode
    
    if ($exitCode -eq 42) {
        # Restart requested
        $restartCount++
        $timestamp = Get-Date -Format 'HH:mm:ss'
        [Console]::Error.WriteLine("[$timestamp] Exit code 42 detected - Restarting server...")
        Start-Sleep -Milliseconds 100
        continue
    } elseif ($exitCode -eq 0) {
        # Normal exit
        $timestamp = Get-Date -Format 'HH:mm:ss'
        [Console]::Error.WriteLine("[$timestamp] Server exited normally (code 0)")
        break
    } else {
        # Error exit
        $timestamp = Get-Date -Format 'HH:mm:ss'
        [Console]::Error.WriteLine("[$timestamp] Server exited with error code $exitCode")
        break
    }
}

[Console]::Error.WriteLine("")
[Console]::Error.WriteLine("=== MCP Server Stopped ===")

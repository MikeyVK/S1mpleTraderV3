# MCP Server Wrapper with Auto-Restart on Exit Code 42
# This wrapper monitors the MCP server and automatically restarts it when
# it exits with code 42 (restart requested by restart_server tool)

param(
    [string]$VenvPath = ".venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

Write-Host "=== MCP Server Wrapper ===" -ForegroundColor Cyan
Write-Host "Monitoring for exit code 42 (auto-restart)" -ForegroundColor Gray
Write-Host ""

$restartCount = 0

while ($true) {
    if ($restartCount -gt 0) {
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Restart #$restartCount" -ForegroundColor Yellow
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
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Exit code 42 detected - Restarting server..." -ForegroundColor Green
        Start-Sleep -Milliseconds 100
        continue
    } elseif ($exitCode -eq 0) {
        # Normal exit
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Server exited normally (code 0)" -ForegroundColor Gray
        break
    } else {
        # Error exit
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Server exited with error code $exitCode" -ForegroundColor Red
        break
    }
}

Write-Host ""
Write-Host "=== MCP Server Stopped ===" -ForegroundColor Cyan

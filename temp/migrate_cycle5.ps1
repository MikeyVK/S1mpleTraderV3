# Cycle 5: Migratie MCP test files naar tests/mcp_server/

# Stap 1: Verplaats hele directories
$dirMoves = @(
    "tests\integration|tests\mcp_server\integration",
    "tests\acceptance|tests\mcp_server\acceptance",
    "tests\regression|tests\mcp_server\regression",
    "tests\parity|tests\mcp_server\parity",
    "tests\fixtures|tests\mcp_server\fixtures"
)

foreach ($entry in $dirMoves) {
    $parts = $entry -split '\|'
    $src = $parts[0]; $dst = $parts[1]
    if (Test-Path $src) {
        Move-Item -Path $src -Destination $dst -Force
        Write-Host "DIR OK: $src -> $dst"
    } else {
        Write-Host "DIR MISSING: $src"
    }
}

# Stap 2: Verplaats tests/unit/ subdirs (niet-backend) naar tests/mcp_server/unit/
New-Item -ItemType Directory -Path "tests\mcp_server\unit" -Force | Out-Null
Copy-Item "tests\unit\__init__.py" "tests\mcp_server\unit\__init__.py" -Force

$unitSubdirs = @("assembly", "config", "managers", "mcp_server", "scaffolders", "scaffolding", "templates", "tools", "validation")
foreach ($sub in $unitSubdirs) {
    $src = "tests\unit\$sub"
    $dst = "tests\mcp_server\unit\$sub"
    if (Test-Path $src) {
        Move-Item -Path $src -Destination $dst -Force
        Write-Host "UNIT OK: $sub"
    } else {
        Write-Host "UNIT MISSING: $sub"
    }
}

# Verplaats test_pytest_config.py
if (Test-Path "tests\unit\test_pytest_config.py") {
    Move-Item "tests\unit\test_pytest_config.py" "tests\mcp_server\unit\test_pytest_config.py" -Force
    Write-Host "FILE OK: test_pytest_config.py"
}

# Stap 3: Verplaats root test_*.py naar tests/mcp_server/
$rootFiles = Get-ChildItem "tests\" -Filter "test_*.py" -File
foreach ($f in $rootFiles) {
    Move-Item -Path $f.FullName -Destination "tests\mcp_server\$($f.Name)" -Force
    Write-Host "ROOT OK: $($f.Name)"
}

Write-Host "=== Klaar ==="

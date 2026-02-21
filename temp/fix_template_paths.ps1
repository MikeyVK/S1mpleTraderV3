$files = @(
    "tests\mcp_server\test_validation_metadata.py",
    "tests\mcp_server\test_tier2_templates.py",
    "tests\mcp_server\test_tier2_markdown_cycle4.py",
    "tests\mcp_server\test_tier1_templates.py",
    "tests\mcp_server\test_tier1_document_cycle3.py",
    "tests\mcp_server\test_tier0_two_line_format.py",
    "tests\mcp_server\test_tier0_template.py",
    "tests\mcp_server\test_tier0_conditional_header.py"
)
$count = 0
foreach ($f in $files) {
    $content = Get-Content $f -Raw -Encoding UTF8
    $new = $content -replace 'parent\.parent / "mcp_server"', 'parent.parent.parent / "mcp_server"'
    if ($content -ne $new) {
        [System.IO.File]::WriteAllText((Resolve-Path $f), $new, [System.Text.Encoding]::UTF8)
        $count++
        Write-Host "Fixed: $f"
    } else {
        Write-Host "No change: $f"
    }
}
Write-Host "Total fixed: $count files"

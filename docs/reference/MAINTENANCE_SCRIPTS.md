# docs/reference/MAINTENANCE_SCRIPTS.md

**Status:** APPROVED  
**Last Updated:** November 2025

---

## Purpose

Ready-to-use PowerShell scripts for documentation maintenance tasks. Run these during weekly, monthly, or emergency maintenance cycles.

## Scope

**In scope:** PowerShell scripts for doc auditing, duplicate detection, orphan finding  
**Out of scope:** Content writing → see [AI_DOC_PROMPTS.md](templates/AI_DOC_PROMPTS.md)

---

## File Size Audit

Find documents exceeding their size limits:

```powershell
# List all docs by size (descending)
Get-ChildItem docs -Recurse -Filter "*.md" | 
    Select-Object FullName, @{
        Name="Lines"
        Expression={(Get-Content $_.FullName | Measure-Object -Line).Lines}
    } |
    Sort-Object Lines -Descending

# Find oversized docs (respects architecture/ 1000-line limit)
Get-ChildItem docs -Recurse -Filter "*.md" | 
    Where-Object {
        $lines = (Get-Content $_.FullName | Measure-Object -Line).Lines
        $limit = if ($_.FullName -match "\\architecture\\") { 1000 } else { 300 }
        $lines -gt $limit
    } | 
    Select-Object @{
        Name="File"; Expression={$_.Name}
    }, @{
        Name="Lines"; Expression={(Get-Content $_.FullName | Measure-Object -Line).Lines}
    }, @{
        Name="Limit"; Expression={if ($_.FullName -match "\\architecture\\") { 1000 } else { 300 }}
    }
```

---

## Duplication Check

Search for repeated patterns that should be consolidated:

```powershell
# Search for pattern in all docs (adjust keywords as needed)
Get-ChildItem docs -Recurse -Filter "*.md" | 
    Select-String -Pattern "TDD workflow" | 
    Group-Object Path | 
    Select-Object Count, Name

# Other common patterns to check:
# "quality gates", "Point-in-Time", "frozen=True"

# If count > 3, consolidate to single source with links
```

---

## Orphan Detection

Find .md files not linked from any README.md:

```powershell
# Step 1: Get all .md files (excluding READMEs)
$allDocs = Get-ChildItem docs -Recurse -Filter "*.md" | 
    Where-Object { $_.Name -ne "README.md" } | 
    Select-Object -ExpandProperty Name

# Step 2: Get all links from README files
$linkedDocs = Get-ChildItem docs -Recurse -Filter "README.md" | 
    ForEach-Object { Get-Content $_.FullName } | 
    Select-String -Pattern "\[.*\]\((.*\.md)" -AllMatches | 
    ForEach-Object { $_.Matches.Groups[1].Value } | 
    ForEach-Object { Split-Path $_ -Leaf } | 
    Sort-Object -Unique

# Step 3: Find orphans
$allDocs | Where-Object { $_ -notin $linkedDocs }
```

---

## Broken Link Check

Find markdown links pointing to non-existent files:

```powershell
# Check all markdown links in docs/
$broken = @()
Get-ChildItem docs -Recurse -Filter "*.md" | ForEach-Object {
    $file = $_
    $dir = $file.DirectoryName
    $content = Get-Content $file.FullName -Raw
    
    # Find all markdown links: [text](path.md) or [text](path.md#anchor)
    $links = [regex]::Matches($content, '\[([^\]]+)\]\(([^)]+\.md)(#[^)]*)?\)')
    
    foreach ($link in $links) {
        $linkPath = $link.Groups[2].Value
        # Skip URLs
        if ($linkPath -match '^https?://') { continue }
        
        # Resolve relative path
        $targetPath = Join-Path $dir $linkPath | Resolve-Path -ErrorAction SilentlyContinue
        
        if (-not $targetPath -or -not (Test-Path $targetPath)) {
            $broken += [PSCustomObject]@{
                Source = $file.FullName -replace [regex]::Escape((Get-Location).Path + "\"), ""
                BrokenLink = $linkPath
                Line = ($content.Substring(0, $link.Index) -split "`n").Count
            }
        }
    }
}

if ($broken.Count -eq 0) {
    Write-Host "No broken links found!" -ForegroundColor Green
} else {
    Write-Host "Found $($broken.Count) broken links:" -ForegroundColor Red
    $broken | Format-Table -AutoSize
}
```

---

## Emergency Cleanup Procedure

When documentation becomes chaotic (multiple files >400 lines, conflicting info, outdated indices):

```powershell
# 1. Create emergency branch
git checkout -b docs/emergency-cleanup

# 2. Triage - list all docs by size
Get-ChildItem docs -Recurse -Filter "*.md" | 
    Select-Object FullName, @{
        Name="Lines"
        Expression={(Get-Content $_.FullName | Measure-Object -Line).Lines}
    } |
    Sort-Object Lines -Descending |
    Format-Table -AutoSize

# 3. Find repeated content
Get-ChildItem docs -Recurse -Filter "*.md" | 
    Select-String -Pattern "specific phrase from duplicated content" |
    Format-Table Path, LineNumber, Line -AutoSize

# 4. After fixes, commit with clear message
git add docs/
git commit -m "docs: emergency cleanup - restore modular structure

Problem: Documentation grew to unmanageable state
- X files exceeded 400 lines (split into focused docs)
- Found Y concept duplicated in Z places (consolidated)
- Updated all README indices with current structure

Result: Back to <300 lines per doc, single source of truth"

# 5. Merge
git checkout main
git merge --no-ff docs/emergency-cleanup
```

---

## Related Documentation

- [DOCUMENTATION_MAINTENANCE.md](../DOCUMENTATION_MAINTENANCE.md) - Meta-rules + maintenance schedule
- [GIT_WORKFLOW.md](../coding_standards/GIT_WORKFLOW.md) - Branch/commit patterns

---

## Version History

| Version | Date | Changes |
|---------|------|---------|  
| 1.0 | 2025-11-27 | Initial creation, extracted from DOCUMENTATION_MAINTENANCE.md |

<!-- ═══════════════════════════════════════════════════════════════════════════
     LINK DEFINITIONS
     ═══════════════════════════════════════════════════════════════════════════ -->
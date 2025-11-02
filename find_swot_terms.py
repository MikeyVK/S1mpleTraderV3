#!/usr/bin/env python3
"""
Find all SWOT terminology references in the codebase.
Case-insensitive search for: opportunity, threat, SWOT
Excludes: docs/system/, docs/development/#Archief/
"""

import re
from pathlib import Path
from typing import List, Tuple

# Directories to exclude
EXCLUDE_DIRS = {
    'docs/system',
    'docs/development/#Archief',
    '__pycache__',
    '.git',
    'simpletraderv3.egg-info',
    '.pytest_cache',
    'node_modules'
}

# Search patterns (case-insensitive)
PATTERNS = [
    r'\bopportunity\b',
    r'\bthreat\b',
    r'\bSWOT\b'
]

def should_exclude(path: Path) -> bool:
    """Check if path should be excluded."""
    path_str = str(path).replace('\\', '/')
    return any(excl in path_str for excl in EXCLUDE_DIRS)

def search_file(file_path: Path) -> List[Tuple[int, str]]:
    """Search file for patterns. Returns list of (line_number, line_content)."""
    matches = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                for pattern in PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        matches.append((line_num, line.rstrip()))
                        break  # Don't count same line multiple times
    except (UnicodeDecodeError, PermissionError):
        pass  # Skip binary/locked files
    
    return matches

def main():
    root = Path('.')
    
    # Find all .py and .md files
    py_files = list(root.rglob('*.py'))
    md_files = list(root.rglob('*.md'))
    
    all_files = py_files + md_files
    
    # Filter excluded paths
    files_to_search = [f for f in all_files if not should_exclude(f)]
    
    print(f"Searching {len(files_to_search)} files...\n", flush=True)
    
    total_matches = 0
    files_with_matches = []
    
    for file_path in sorted(files_to_search):
        matches = search_file(file_path)
        if matches:
            files_with_matches.append((file_path, matches))
            total_matches += len(matches)
    
    # Print results (ASCII-safe for Windows console)
    if files_with_matches:
        print(f"Found {total_matches} matches in {len(files_with_matches)} files:\n", flush=True)
        print("=" * 80, flush=True)
        
        for file_path, matches in files_with_matches:
            print(f"\n{file_path}:", flush=True)
            for line_num, line_content in matches:
                # Replace problematic Unicode characters for Windows console
                safe_line = line_content.replace('❌', 'X').replace('✅', 'OK')
                print(f"  {line_num:4d}: {safe_line[:100]}", flush=True)
        
        print("\n" + "=" * 80, flush=True)
        print(f"\nTotal: {total_matches} matches in {len(files_with_matches)} files", flush=True)
    else:
        print("OK No matches found!", flush=True)
    
    return len(files_with_matches)

if __name__ == '__main__':
    exit(main())

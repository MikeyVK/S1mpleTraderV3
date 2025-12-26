import re
from pathlib import Path

# Read the test file
test_file = Path("tests/unit/mcp_server/tools/test_safe_edit_tool.py")
content = test_file.read_text(encoding="utf-8")

# Step 1: Remove SearchReplace from imports
content = re.sub(
    r"from mcp_server\.tools\.safe_edit_tool import \((.*?)SearchReplace,(.*?)\)",
    r"from mcp_server.tools.safe_edit_tool import (\1\2)",
    content,
    flags=re.DOTALL
)

# Step 2: Replace SearchReplace usages with flattened parameters
# Pattern 1: search_replace=SearchReplace(search="...", replace="...", regex=False)
content = re.sub(
    r'search_replace=SearchReplace\(search="([^"]+)",\s*replace="([^"]+)",\s*regex=False\)',
    r'search="\1", replace="\2"',
    content
)

# Pattern 2: search_replace=SearchReplace(search="...", replace="...", regex=False, count=N)
content = re.sub(
    r'search_replace=SearchReplace\(search="([^"]+)",\s*replace="([^"]+)",\s*regex=False,\s*count=(\d+)\)',
    r'search="\1", replace="\2", search_count=\3',
    content
)

# Pattern 3: search_replace=SearchReplace(search=r"...", replace=r"...", regex=True)
content = re.sub(
    r'search_replace=SearchReplace\(\s*search=r"([^"]+)",\s*replace=r"([^"]+)",\s*regex=True\s*\)',
    r'search=r"\1", replace=r"\2", regex=True',
    content
)

# Pattern 4: search_replace=SearchReplace(search="...", replace="...")
content = re.sub(
    r'search_replace=SearchReplace\(search="([^"]+)",\s*replace="([^"]+)"\)',
    r'search="\1", replace="\2"',
    content
)

# Write updated content
test_file.write_text(content, encoding="utf-8")

print("Successfully updated test file")
print("SearchReplace remaining:", content.count("SearchReplace"))

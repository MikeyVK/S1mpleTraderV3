import re

path = r'tests\unit\scaffolding\test_metadata_parser.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Add assert metadata is not None before all dictionary access
content = re.sub(
    r'(parser\.parse\(content, "[^"]+"\))\n\n        (assert metadata\[)',
    r'\1\n\n        assert metadata is not None\n        \2',
    content
)

# Fix line 23 - split long string
content = content.replace(
    '# SCAFFOLD: template=dto version=1.0 created=2026-01-20T14:00:00Z path=mcp_server/dto/user.py',
    '# SCAFFOLD: template=dto version=1.0 '
    'created=2026-01-20T14:00:00Z path=mcp_server/dto/user.py'
)

# Write back
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed test file - added assert metadata is not None')

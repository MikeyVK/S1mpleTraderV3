"""Test current state with my edits."""
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.config.template_config import get_template_root
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer

reg = ArtifactRegistryConfig.from_file()
renderer = JinjaRenderer(template_dir=get_template_root())
s = TemplateScaffolder(registry=reg, renderer=renderer)

res = s.scaffold(
    artifact_type='dto',
    name='UserDTO',
    description='Test DTO',
    fields=[{'name':'id','type':'int'}]
)

print('=== CURRENT STATE (WITH MY EDITS) ===')
lines = res.content.splitlines()
print(f'Total lines: {len(lines)}')
print('\nFirst 15 lines:')
for i, line in enumerate(lines[:15], 1):
    print(f"{i:2d}: {repr(line)}")

try:
    compile(res.content, '<dto>', 'exec')
    print('\n✓ COMPILE: OK')
except SyntaxError as e:
    print(f'\n✗ COMPILE ERROR: {e}')
    print(f'   Line {e.lineno}: {e.text}')

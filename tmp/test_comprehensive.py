"""Test ALL Python artifact types CORRECTLY."""
import sys
sys.path.insert(0, r'd:\dev\SimpleTraderV3')

from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.config.template_config import get_template_root
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer

reg = ArtifactRegistryConfig.from_file()
renderer = JinjaRenderer(template_dir=get_template_root())
s = TemplateScaffolder(registry=reg, renderer=renderer)

print('='*60)
print('COMPREHENSIVE PYTHON ARTIFACT TEST')
print('='*60 + '\n')

tests = [
    ('DTO', {
        'artifact_type': 'dto',
        'name': 'TestDTO',
        'description': 'Test DTO',
        'fields': [{'name': 'id', 'type': 'int'}],
        'layer': 'Backend',
        'dependencies': ['pydantic'],
        'responsibilities': ['Data transfer']
    }),
    ('Worker (no deps)', {
        'artifact_type': 'worker',
        'name': 'TestWorker',
        'description': 'Test Worker',
        'class_name': 'TestWorker',
        'layer': 'Backend'
    }),
    ('Worker (with deps)', {
        'artifact_type': 'worker',
        'name': 'TestWorkerDeps',
        'description': 'Test Worker with Dependencies',
        'class_name': 'TestWorkerDeps',
        'layer': 'Backend',
        'dependencies': [
            {'name': 'db', 'type': 'Database'},
            {'name': 'logger', 'type': 'Logger'}
        ]
    }),
    ('Service', {
        'artifact_type': 'service_command',
        'name': 'TestService',
        'description': 'Test Service',
        'class_name': 'TestService',
        'layer': 'Backend'
    }),
    ('Generic', {
        'artifact_type': 'generic',
        'name': 'TestGeneric',
        'description': 'Test Generic',
        'class_name': 'TestGeneric'
    })
]

for test_name, context in tests:
    print(f'{test_name}:')
    print('-'*60)
    try:
        res = s.scaffold(**context)
        lines = res.content.splitlines()
        
        # Show first 15 lines
        for i, line in enumerate(lines[:15], 1):
            print(f'{i:3d}: {repr(line)}')
        if len(lines) > 15:
            print(f'... ({len(lines)-15} more lines)')
        
        # Compile
        compile(res.content, f'<{test_name}>', 'exec')
        print(' COMPILE: OK\n')
    except SyntaxError as e:
        print(f' COMPILE ERROR line {e.lineno}: {e.msg}')
        print(f'Line {e.lineno}: {repr(lines[e.lineno-1])}\n')
    except Exception as e:
        print(f' SCAFFOLD ERROR: {e}\n')

print('='*60)
print('All tests complete!')

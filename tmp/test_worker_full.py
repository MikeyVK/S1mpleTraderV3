"""Test Worker full output."""
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.config.template_config import get_template_root
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer

reg = ArtifactRegistryConfig.from_file()
renderer = JinjaRenderer(template_dir=get_template_root())
s = TemplateScaffolder(registry=reg, renderer=renderer)

res = s.scaffold(
    artifact_type="worker",
    name="TestWorker",
    description="Test Worker",
    class_name="TestWorker",
    layer="Backend",
    dependencies=["asyncio"],
    responsibilities=["Background task"]
)

print("FULL WORKER OUTPUT (all lines with repr):")
print("="*60)
lines = res.content.splitlines()
for i, line in enumerate(lines, 1):
    print(f"{i:3}: {repr(line)}")

print("\n" + "="*60)
try:
    compile(res.content, '<worker>', 'exec')
    print(" COMPILE: OK")
except SyntaxError as e:
    print(f" COMPILE ERROR: {e}")
    print(f"  Line {e.lineno}: {repr(e.text)}")
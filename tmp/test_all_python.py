"""Test ALL Python artifact types for consistent whitespace."""
from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
from mcp_server.config.template_config import get_template_root
from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
from mcp_server.scaffolding.renderer import JinjaRenderer

reg = ArtifactRegistryConfig.from_file()
renderer = JinjaRenderer(template_dir=get_template_root())
s = TemplateScaffolder(registry=reg, renderer=renderer)

print("="*60)
print("TESTING ALL PYTHON ARTIFACT TYPES")
print("="*60 + "\n")

# Test DTO
print("1. DTO:")
print("-"*60)
res = s.scaffold(
    artifact_type="dto",
    name="TestDTO",
    description="Test DTO",
    fields=[{"name":"id","type":"int"}],
    layer="Backend",
    dependencies=["pydantic"],
    responsibilities=["Data transfer"]
)
lines = res.content.splitlines()
print(f"Total lines: {len(lines)}")
print("First 8 lines:")
for i, line in enumerate(lines[:8], 1):
    print(f" {i}: {repr(line)}")
try:
    compile(res.content, '<dto>', 'exec')
    print(" COMPILE: OK\n")
except SyntaxError as e:
    print(f" COMPILE ERROR: {e}\n")

# Test Worker
print("2. WORKER:")
print("-"*60)
res = s.scaffold(
    artifact_type="worker",
    name="TestWorker",
    description="Test Worker",
    class_name="TestWorker",
    layer="Backend",
    dependencies=["asyncio"],
    responsibilities=["Background task"]
)
lines = res.content.splitlines()
print(f"Total lines: {len(lines)}")
print("First 8 lines:")
for i, line in enumerate(lines[:8], 1):
    print(f" {i}: {repr(line)}")
try:
    compile(res.content, '<worker>', 'exec')
    print(" COMPILE: OK\n")
except SyntaxError as e:
    print(f" COMPILE ERROR: {e}\n")

# Test Service
print("3. SERVICE:")
print("-"*60)
res = s.scaffold(
    artifact_type="service",
    name="TestService",
    description="Test Service",
    class_name="TestService",
    layer="Backend",
    dependencies=[],
    responsibilities=["Business logic"]
)
lines = res.content.splitlines()
print(f"Total lines: {len(lines)}")
print("First 8 lines:")
for i, line in enumerate(lines[:8], 1):
    print(f" {i}: {repr(line)}")
try:
    compile(res.content, '<service>', 'exec')
    print(" COMPILE: OK\n")
except SyntaxError as e:
    print(f" COMPILE ERROR: {e}\n")
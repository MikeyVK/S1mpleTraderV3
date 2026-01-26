"""Debug whitespace in template rendering."""
import asyncio
from pathlib import Path


async def main():
    """Debug exact whitespace behavior."""
    from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
    from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
    from mcp_server.scaffolding.renderer import JinjaRenderer
    from mcp_server.config.template_config import get_template_root
    
    registry = ArtifactRegistryConfig.from_file()
    renderer = JinjaRenderer(template_dir=get_template_root())
    scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)
    
    # Direct scaffold
    result_obj = scaffolder.scaffold(
        artifact_type="dto",
        name="DebugDTO",
        description="Debug whitespace",
        fields=[{"name": "id", "type": "int"}]
    )
    
    content = result_obj.content
    lines = content.splitlines(keepends=True)
    
    print("=" * 80)
    print("LINE-BY-LINE WITH REPR:")
    print("=" * 80)
    for i, line in enumerate(lines[:15], 1):
        print(f"{i:2d}: {repr(line)}")
    
    print("\n" + "=" * 80)
    print("FIRST 500 CHARS:")
    print("=" * 80)
    print(repr(content[:500]))


if __name__ == "__main__":
    asyncio.run(main())

"""Quick test for whitespace issue - bypass validation."""
import asyncio
from pathlib import Path


async def main():
    """Test scaffolding and check for whitespace issues."""
    # Bypass validation to see raw output
    from mcp_server.config.artifact_registry_config import ArtifactRegistryConfig
    from mcp_server.scaffolders.template_scaffolder import TemplateScaffolder
    from mcp_server.scaffolding.renderer import JinjaRenderer
    from mcp_server.config.template_config import get_template_root
    
    registry = ArtifactRegistryConfig.from_file()
    renderer = JinjaRenderer(template_dir=get_template_root())
    scaffolder = TemplateScaffolder(registry=registry, renderer=renderer)
    
    # Direct scaffold - no validation
    result_obj = scaffolder.scaffold(
        artifact_type="dto",
        name="TestWhitespaceDTO",
        description="Test DTO for whitespace",
        fields=[{"name": "id", "type": "int"}, {"name": "name", "type": "str"}]
    )
    
    result = "tmp/output_dto.py"
    Path(result).write_text(result_obj.content)
    
    print(f"Generated file: {result}")
    print("=" * 80)
    
    content = result_obj.content
    
    # Print first 1500 chars to see the issue
    print("FIRST 1500 CHARACTERS:")
    print(repr(content[:1500]))
    print("=" * 80)
    
    # Try to compile it
    try:
        compile(content, result, "exec")
        print("✓ COMPILE SUCCESS")
    except SyntaxError as e:
        print(f"✗ COMPILE ERROR: {e}")
        print(f"  Line {e.lineno}: {e.text}")
        if e.offset:
            print(f"  {' ' * (e.offset - 1)}^")
        
        # Show lines around the error
        lines = content.splitlines()
        start = max(0, e.lineno - 5)
        end = min(len(lines), e.lineno + 3)
        print("\nContext:")
        for i in range(start, end):
            marker = ">>>" if i == e.lineno - 1 else "   "
            print(f"{marker} {i+1:3d}: {repr(lines[i])}")


if __name__ == "__main__":
    asyncio.run(main())

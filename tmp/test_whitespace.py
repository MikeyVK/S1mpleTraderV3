"""Quick test for whitespace issue in tier templates."""
import asyncio
from pathlib import Path
from mcp_server.managers.artifact_manager import ArtifactManager


async def main():
    """Test scaffolding and check for whitespace issues."""
    m = ArtifactManager(workspace_root=".")
    result = await m.scaffold_artifact(
        "dto",
        name="TestWhitespaceDTO",
        description="Test DTO for whitespace",
        fields=[{"name": "id", "type": "int"}, {"name": "name", "type": "str"}]
    )
    
    print(f"Generated file: {result}")
    print("=" * 80)
    
    content = Path(result).read_text()
    
    # Print first 1000 chars to see the issue
    print("FIRST 1000 CHARACTERS:")
    print(repr(content[:1000]))
    print("=" * 80)
    
    # Try to compile it
    try:
        compile(content, result, "exec")
        print("✓ COMPILE SUCCESS")
    except SyntaxError as e:
        print(f"✗ COMPILE ERROR: {e}")
        print(f"  Line {e.lineno}: {e.text}")
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

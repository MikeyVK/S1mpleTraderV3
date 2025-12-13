import asyncio
import sys
from pathlib import Path

# Add root to path
sys.path.append(str(Path.cwd()))

from mcp_server.tools.safe_edit_tool import SafeEditTool
from mcp_server.validation.registry import ValidatorRegistry

async def main():
    root = Path("mcp_server")
    # Initialize tool to register validators
    tool = SafeEditTool()
    
    print("File|Template|Status")
    
    # Walk all python files
    for path in root.rglob("*.py"):
        # Skip __init__.py and logicless files if needed, but strict compliance means ALL
        if path.name == "__init__.py":
            continue
            
        try:
            content = path.read_text(encoding="utf-8")
            abs_path = str(path.resolve())
            
            # Use _validate from SafeEditTool
            passed, issues = await tool._validate(abs_path, content)
            
            # Determine template type
            validators = ValidatorRegistry.get_validators(abs_path)
            template_type = "Standard"
            for v in validators:
                if hasattr(v, "template_type"):
                    template_type = v.template_type.capitalize()
                    
            status = "✅" if passed else "❌"
            print(f"{path}|{template_type}|{status}")
            
        except Exception as e:
            print(f"{path}|Error|❌ {e}")

if __name__ == "__main__":
    asyncio.run(main())

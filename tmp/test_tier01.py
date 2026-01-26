"""Test tier0 + tier1 CODE without tier2."""
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import datetime, timezone

# Setup
template_root = Path("mcp_server/scaffolding/templates")
env = Environment(loader=FileSystemLoader(str(template_root)))

try:
    template = env.get_template("test_minimal_code.jinja2")
    output = template.render(
        artifact_type="test",
        timestamp=datetime.now(timezone.utc).isoformat(),
        output_path="test.py",
        format="python",
        class_name="TestClass",
        class_docstring="Test class docstring.",
        module_title="Test Module"
    )
    
    lines = output.splitlines(keepends=True)
    
    print("=" * 80)
    print("TIER 0 + TIER 1 CODE OUTPUT:")
    print("=" * 80)
    for i, line in enumerate(lines, 1):
        print(f"{i:2d}: {repr(line)}")
    
    print("\n" + "=" * 80)
    print("VALIDATION:")
    print("=" * 80)
    
    assert lines[0].startswith("# SCAFFOLD:"), f"Line 1 should be SCAFFOLD, got {repr(lines[0])}"
    
    # Try to compile
    try:
        compile(output, "test.py", "exec")
        print("✓ Python syntax valid")
    except SyntaxError as e:
        print(f"✗ Syntax error at line {e.lineno}: {e}")
        raise
    
    print("✓ Tier 0 + Tier 1 CODE chain works correctly")
    
finally:
    # Cleanup
    Path("mcp_server/scaffolding/templates/test_minimal_code.jinja2").unlink(missing_ok=True)

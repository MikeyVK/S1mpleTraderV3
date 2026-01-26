"""Test tier0 + tier1 CODE without tier2."""
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import datetime, timezone

# Setup
template_root = Path("mcp_server/scaffolding/templates")
env = Environment(loader=FileSystemLoader(str(template_root)))

# Minimal concrete that extends tier1 directly (no tier2)
minimal_code_source = """{%- extends "tier1_base_code.jinja2" -%}"""

minimal_path = template_root / "test_minimal_code.jinja2"
minimal_path.write_text(minimal_code_source)

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
    
    # Expected structure:
    # 1: # SCAFFOLD: ...
    # 2: """Test Module."""
    # 3: 
    # 4: class TestClass:
    # 5:     """Test class docstring."""
    # 6:     pass
    
    assert lines[0].startswith("# SCAFFOLD:"), f"Line 1 should be SCAFFOLD"
    assert lines[1].strip().startswith('"""'), f"Line 2 should be docstring start"
    assert lines[2] == "\n", f"Line 3 should be empty, got {repr(lines[2])}"
    assert "class TestClass:" in lines[3], f"Line 4 should be class definition"
    
    # Check no double newlines anywhere
    assert "\n\n\n" not in output, "Found triple newline!"
    
    # Try to compile
    try:
        compile(output, "test.py", "exec")
        print("✓ Python syntax valid")
    except SyntaxError as e:
        print(f"✗ Syntax error: {e}")
        raise
    
    print("✓ SCAFFOLD on line 1")
    print("✓ Docstring on line 2")
    print("✓ Exactly 1 blank line before class")
    print("✓ No triple newlines")
    
finally:
    if minimal_path.exists():
        minimal_path.unlink()

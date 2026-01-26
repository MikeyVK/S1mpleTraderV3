"""Test tier0 whitespace in isolation."""
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import datetime, timezone

# Setup Jinja2 environment
template_root = Path("mcp_server/scaffolding/templates")
env = Environment(loader=FileSystemLoader(str(template_root)))

# Create minimal concrete template that ONLY extends tier0
minimal_template_source = """
{%- extends "tier0_base_artifact.jinja2" -%}
"""

# Write minimal template temporarily
minimal_path = template_root / "test_minimal.jinja2"
minimal_path.write_text(minimal_template_source)

try:
    # Render
    template = env.get_template("test_minimal.jinja2")
    output = template.render(
        artifact_type="test",
        timestamp=datetime.now(timezone.utc).isoformat(),
        output_path="test.py",
        format="python"
    )
    
    # Analyze
    lines = output.splitlines(keepends=True)
    
    print("=" * 80)
    print("TIER 0 ONLY OUTPUT:")
    print("=" * 80)
    for i, line in enumerate(lines, 1):
        print(f"{i}: {repr(line)}")
    
    print("\n" + "=" * 80)
    print("VALIDATION:")
    print("=" * 80)
    
    # Should be exactly 1 line with 1 newline
    assert len(lines) == 1, f"Expected 1 line, got {len(lines)}"
    assert lines[0].startswith("# SCAFFOLD:"), f"Line doesn't start with SCAFFOLD: {repr(lines[0])}"
    assert lines[0].endswith("\n"), f"Line doesn't end with newline: {repr(lines[0])}"
    
    # Check for NO double newlines
    assert "\n\n" not in output, "Found double newline in output!"
    
    print("✓ Tier0 produces exactly ONE line with ONE trailing newline")
    print("✓ No double newlines")
    print("✓ SCAFFOLD header format correct")
    
finally:
    # Cleanup
    if minimal_path.exists():
        minimal_path.unlink()

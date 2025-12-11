"""Verify QA Reporting."""
import asyncio
import os
from mcp_server.tools.quality_tools import RunQualityGatesTool

# Create a bad file for testing
BAD_FILE = "verify_strict.py"
CONTENT = """
def foo(x):
    return x + 1
"""
# Issues expected:
# - Missing module docstring (C0114)
# - Missing function docstring (C0116)
# - Argument name "x" doesn't conform to snake_case?
#   (C0103 - single letter might be fine but strictly maybe not)
# - Missing type annotation for x (mypy)
# - Missing return type annotation (mypy)

with open(BAD_FILE, "w", encoding="utf-8") as f:
    f.write(CONTENT)

async def test_reporting() -> None:
    """Run the reporting test."""
    print("Running QA Gates on bad file...")

    tool = RunQualityGatesTool()
    res = await tool.execute(files=[BAD_FILE])

    # Check if content exists and is a list as expected from tool result
    if res.content and isinstance(res.content, list):
        print("\n--- TOOL OUTPUT START ---")
        print(res.content[0].get("text", ""))
        print("--- TOOL OUTPUT END ---\n")

    # Clean up
    if os.path.exists(BAD_FILE):
        os.remove(BAD_FILE)

if __name__ == "__main__":
    asyncio.run(test_reporting())

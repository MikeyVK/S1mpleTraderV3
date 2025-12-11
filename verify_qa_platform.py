"""Verification script for Unified QA Platform."""
import asyncio
from typing import Any
from mcp_server.tools.safe_edit_tool import SafeEditTool
from mcp_server.tools.template_validation_tool import TemplateValidationTool

async def verify() -> None:
    print("Verifying Unified QA Platform...")
    
    # 1. Test SafeEditTool (Python - Good)
    print("\n[Test 1] SafeEditTool (Python - Good)")
    safe_tool = SafeEditTool()
    code_good = "def hello():\n    print('Hello')\n"
    res1 = await safe_tool.execute(
        path=r"d:\dev\SimpleTraderV3\verification_test_good.py",
        content=code_good,
        mode="strict"
    )
    print(res1)

    # 2. Test SafeEditTool (Python - Bad)
    print("\n[Test 2] SafeEditTool (Python - Bad: Pylint error)")
    code_bad = "import non_existent_module\n" # Should fail import check or basic syntax
    res2 = await safe_tool.execute(
        path=r"d:\dev\SimpleTraderV3\verification_test_bad.py",
        content=code_bad,
        mode="strict"
    )
    print(res2)

    # 3. Test TemplateValidationTool (Worker - Good)
    print("\n[Test 3] TemplateValidationTool (Worker - Good)")
    template_tool = TemplateValidationTool()
    worker_code_good = """
from mcp_server.workers.base_worker import BaseWorker, TaskResult

class TestWorker(BaseWorker):
    def execute(self, task):
        pass
"""
    # Write temp file for test
    good_worker_path = r"d:\dev\SimpleTraderV3\verification_test_worker.py"
    with open(good_worker_path, "w", encoding="utf-8") as f:
        f.write(worker_code_good)
        
    res3 = await template_tool.execute(path=good_worker_path, template_type="worker")
    print(res3)

    # 4. Test TemplateValidationTool (Worker - Bad)
    print("\n[Test 4] TemplateValidationTool (Worker - Bad: Missing Suffix)")
    worker_code_bad = """
class Test(BaseWorker):
    def execute(self, task):
        pass
"""
    bad_worker_path = r"d:\dev\SimpleTraderV3\verification_bad_worker.py"
    with open(bad_worker_path, "w", encoding="utf-8") as f:
        f.write(worker_code_bad)

    res4 = await template_tool.execute(path=bad_worker_path, template_type="worker")
    print(res4)
    
    # 5. Test SafeEditTool with Automatic Template Detection
    print("\n[Test 5] SafeEditTool with Automatic Template Detection (Bad Worker)")
    # Since we registered patterns in SafeEditTool, writing to *_worker.py should trigger Worker Template Check
    res5 = await safe_tool.execute(
        path=r"d:\dev\SimpleTraderV3\auto_test_worker.py",
        content=worker_code_bad, # Missing suffix
        mode="strict"
    )
    print(res5)

if __name__ == "__main__":
    asyncio.run(verify())

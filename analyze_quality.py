"""Analyze code quality and generate report."""
import json
import subprocess
import sys
from pathlib import Path

def run_command(cmd):
    """Run command and return output."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=False, encoding="utf-8"
        )
        return result.stdout + result.stderr, result.returncode
    except Exception as e:
        return str(e), 1

def parse_pylint_score(output):
    """Parse pylint score from output."""
    for line in output.splitlines():
        if "Your code has been rated at" in line:
            return line.strip()
    return "N/A"

def parse_coverage(output):
    """Parse coverage percentage."""
    for line in output.splitlines():
        if "TOTAL" in line:
            parts = line.split()
            return parts[-1]
    return "N/A"

def main():
    print("Running Pylint...")
    pylint_out, _ = run_command([sys.executable, "-m", "pylint", "mcp_server"])
    score = parse_pylint_score(pylint_out)
    
    print("Running Pytest & Coverage...")
    pytest_out, _ = run_command([
        sys.executable, "-m", "pytest", 
        "--cov=mcp_server", 
        "--cov-report=term-missing"
    ])
    coverage = parse_coverage(pytest_out)
    
    report = {
        "pylint_score": score,
        "coverage": coverage,
        "pylint_output": pylint_out,
        "pytest_output": pytest_out
    }
    
    with open("quality_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        
    print(f"Report generated: quality_report.json")
    print(f"Pylint: {score}")
    print(f"Coverage: {coverage}")

if __name__ == "__main__":
    main()

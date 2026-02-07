import json
import subprocess
import sys
from pathlib import Path


def run_command(cmd):
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            encoding='utf-8', # Force UTF-8
            errors='replace' # Handle decode errors
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def main() -> None:
    root = Path("mcp_server")
    files = [str(f) for f in root.rglob("*.py")]

    print(f"Analyzing {len(files)} files...")

    # 1. Run Coverage
    print("Running coverage...")
    run_command([sys.executable, "-m", "pytest", "--cov=mcp_server", "--cov-report=json"])

    coverage_data = {}
    if Path("coverage.json").exists():
        with open("coverage.json") as f:
            cov_json = json.load(f)
            # Map absolute paths to relative for easier matching
            for abs_path, data in cov_json.get("files", {}).items():
                # Try to make path relative to cwd
                try:
                    rel_path = Path(abs_path).relative_to(Path.cwd())
                    coverage_data[str(rel_path)] = data
                except ValueError:
                    continue

    # 2. Run Pylint
    print("Running pylint...")
    # We run on the whole directory to catch cross-file issues, but output JSON
    pylint_out, pylint_err, _ = run_command([
        sys.executable, "-m", "pylint",
        "mcp_server",
        "--output-format=json",
        "--rcfile=pyproject.toml"  # Ensure we use project config
    ])

    try:
        pylint_issues = json.loads(pylint_out)
    except json.JSONDecodeError:
        print("Failed to parse pylint JSON output", file=sys.stderr)
        pylint_issues = []

    # Map issues to files
    file_warnings = {}
    all_warnings = []

    for issue in pylint_issues:
        path = issue.get("path", "")
        # Normalize path separators
        path = path.replace("\\\\", "/")

        if path not in file_warnings:
            file_warnings[path] = []

        file_warnings[path].append(issue)
        all_warnings.append(issue)

    # 3. Aggregate Results
    results = []

    for file_path in files:
        # Normalize for matching
        try:
            rel_path = Path(file_path).resolve().relative_to(root.resolve().parent)
            path_str = str(rel_path).replace("\\\\", "/")
        except ValueError:
             # Fallback if somehow outside
            path_str = str(Path(file_path).name)
            rel_path = Path(file_path)


        # Get Coverage
        cov_info = coverage_data.get(str(rel_path), {})
        summary = cov_info.get("summary", {})
        percent = summary.get("percent_covered", 0.0)
        missing_lines = cov_info.get("missing_lines", [])

        # Get Warnings
        warnings = file_warnings.get(path_str, [])
        warning_count = len(warnings)

        results.append({
            "path": path_str,
            "coverage_percent": round(percent, 2),
            "missing_lines": missing_lines,
            "warning_count": warning_count,
            "warnings": warnings
        })

    # Sort by coverage (ascending) then warnings (descending)
    results.sort(key=lambda x: (x["coverage_percent"], -x["warning_count"]))

    # Output Report Structure
    report = {
        "files": results,
        "all_warnings": all_warnings
    }

    with open("quality_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("Analysis complete. Saved to quality_report.json")

if __name__ == "__main__":
    main()

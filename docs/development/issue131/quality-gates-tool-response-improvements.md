<!-- docs/development/issue131/quality-gates-tool-response-improvements.md -->
<!-- template=research version=8b7bb3ab created=2026-02-12 updated= -->
# Quality Gates Tool Response Improvements - Research

**Status:** READY FOR REVIEW  
**Version:** 2.0  
**Last Updated:** 2026-02-12

---

## Purpose

Document comprehensive improvements to run_quality_gates tool response format based on real-world usage during Issue #131 validation. Transform tool output from basic exit codes to production-grade structured responses with machine-readable schemas, reproducibility metadata, and intelligent error handling.

## Scope

**In Scope:**
Schema-first response design (JSON source of truth, text as derived view), Tool output capture with truncation policies, Command/environment reproducibility metadata, JSON parsing for ruff/mypy/pytest output, Mode visibility and consistent skip reasons, Progress indication feasibility analysis, quality.yaml extensions for response format configuration

**Out of Scope:**
Backward compatibility with v1 response format (beta breaking changes acceptable), Gate implementation algorithms, Python/Ruff version compatibility issues

## Prerequisites
Read these first:
1. Issue #131 implementation complete
2. Real-world validation executed with 7 files across 6 gates
3. Multiple gate failures encountered and resolved
4. Dual execution mode system validated (project-level vs file-specific)
---

## Problem Statement

The run_quality_gates tool successfully executes quality gates but lacks: (1) Structured output - text-only format requires parsing heuristics, (2) Error context - exit code failures provide no diagnostic information, (3) Reproducibility - missing command/environment metadata, (4) Output management - no truncation policy for large stderr/stdout, (5) Mode visibility - users cannot determine execution context programmatically. This makes debugging less efficient than direct terminal execution and limits CI/CD integration.

## Research Goals

- Production-grade output: Machine-readable JSON + human-friendly text
- Debugging efficiency: Inline error context without re-running commands
- Reproducibility: Full command/environment capture per gate
- Scalability: Handle large tool outputs without response explosion
- CI/CD ready: Enable automated parsing and decision-making

## Related Documentation
- **[docs/development/issue131/design.md][related-1]**
- **[docs/coding_standards/QUALITY_GATES.md][related-2]**

<!-- Link definitions -->

[related-1]: docs/development/issue131/design.md
[related-2]: docs/coding_standards/QUALITY_GATES.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-02-12 | Agent | Initial draft |

---

## Key Findings

### Finding 1: Exit Code Failures Lack Error Details

**Observation:**
When a gate fails with exit code 1, tool response shows:
```
❌ Gate 1: Ruff Strict Lint: Fail (exit=1)
  Issues:
  - unknown:?:? Gate failed with exit code 1
```

**Impact:**
- Agent must re-run command manually to see actual errors
- Adds 1-2 minutes debugging overhead per failed gate
- User cannot assess severity without additional steps
- No inline context for "why did this fail?"

**Root Cause:**
QAManager captures exit code but not stdout/stderr for exit_code strategy gates

**Solution:**
Capture stdout/stderr with truncation policy (see Advanced Improvement #3):
```
❌ Gate 1: Ruff Strict Lint: Fail (exit=1)
  Issues (showing first 5 of 7):
  - test_qa_manager.py:260:41: ANN401 Dynamically typed expressions (typing.Any) are disallowed
  - test_qa_manager.py:262:9: RET501 Do not explicitly return None if it's the only return
  - qa_manager.py:271:8: SIM103 Return the condition directly
  ... (2 more violations, see full log)
  Full output: /tmp/qa_gate_1_20260212_143022.log
```

---

### Finding 2: Fixable Issues Not Prominent

**Observation:**
Re-run hints mention `--fix` option but buried in hint text:
```
Hints:
  - Re-run: python -m ruff check ... <files>
  - If safe, try Ruff autofix by adding `--fix` to the re-run command.
```

**Impact:**
- Agent doesn't immediately recognize auto-fixable errors
- Wastes time on manual fixes that could be automated
- No quantification of how many issues are auto-fixable

**Root Cause:**
Fixability detection relies on text parsing heuristics instead of tool-native JSON output

**Solution:**
Use JSON parsing (see Advanced Improvement #4) to get accurate fixable count:
```
❌ Gate 1: Ruff Strict Lint: Fail (7 violations, 5 auto-fixable)
  Run with --fix to auto-resolve: ANN401, RET501, SIM103, SIM108, UP032
```

---

### Finding 3: No Progress Indication During Execution

**Observation:**
Tool is silent during execution (~30s for 7 files across 6 gates)

**Impact:**
- Uncertainty whether tool is working or hanging
- Critical for pytest gate which can take 5+ minutes
- No way to identify slow gates for optimization

**Root Cause:**
MCP protocol doesn't support streaming tool responses

**Solution:**
Post-execution timing breakdown (see Advanced Improvement #5):
```
Quality Gates Results:
Gate execution timings:
  Gate 0 (Ruff Format):     0.2s ✅
  Gate 1 (Ruff Lint):       1.3s ❌
  Gate 5 (Tests):          12.4s ✅ ← slowest
  Total:                   14.6s
```

Real-time progress limited to server logs: `logger.info(f"Running gate {i+1}/{total}: {gate.name}")`

---

### Finding 4: Multi-File Issues Not Grouped

**Observation:**
When 7 files checked, violations listed without file context:
```
Issues:
  - unknown:?:? Gate failed with exit code 1
```

**Impact:**
- Cannot prioritize which files have most issues
- Hard to track progress when fixing multiple files
- No high-level view of issue distribution

**Root Cause:**
Text parsing instead of structured JSON output from tools

**Solution:**
Use JSON parsing for file-level grouping:
```
Issues by file (3 files with violations):
  mcp_server/managers/qa_manager.py: 4 violations (2 fixable)
    - Line 260: ANN401 typing.Any disallowed [auto-fix]
    - Line 262: RET501 Remove explicit return None [auto-fix]
    - Line 271: SIM103 Return condition directly [auto-fix]
    - Line 280: E501 Line too long (123 > 100)
  tests/unit/mcp_server/managers/test_qa_manager.py: 3 violations (1 fixable)
    ...
```

---

### Finding 5: Overall Summary Lacks Context

**Observation:**
```
Overall Pass: False
```

**Impact:**
- Must scan entire gate list to count failures/skips
- No quick assessment of issue severity
- Missing aggregation for decision-making

**Root Cause:**
Summary field not designed for at-a-glance status

**Solution:**
Enhanced summary with gate breakdown:
```
Overall Pass: False (2 failed, 2 skipped, 2 passed)
  Failed gates: Gate 1 (Ruff Lint), Gate 3 (Imports)
  Total violations: 14 (9 auto-fixable)
```

---

### Finding 6: Execution Mode Not Visible in Response

**Observation:**
Tool response doesn't indicate which execution mode is active:
```
Quality Gates Results:
Overall Pass: True
✅ Gate 0: Ruff Format: Skipped (no matching files)
✅ Gate 5: Tests: Pass
```

**Impact:**
- User must infer mode from skip patterns
- Ambiguous whether skips are intentional (mode-based) or errors (missing files)
- No clear feedback that `files=[]` triggered project-level test validation mode
- Agent cannot programmatically determine execution context

**Root Cause:**
Response format doesn't include mode metadata

**Solution:**
Add execution mode header (schema-first approach provides this naturally):
```
Quality Gates Results:
Mode: project-level test validation (pytest gates only)
Files: [] (no file-specific validation)
Overall Pass: True (4 static gates skipped, 2 pytest gates passed)

✅ Gate 0: Ruff Format: Skipped (project-level mode)
✅ Gate 5: Tests: Pass ✓
✅ Gate 6: Coverage ≥90%: Pass ✓
```

---

### Finding 7: Skip Reason Inconsistency Across Modes

**Merged from original Finding 5 + 8 - same root cause**

**Observation:**
Skip messages differ in clarity between execution modes causing confusion:

**File-specific mode (files=["file.py"]):**
```
✅ Gate 5: Tests: Skipped (file-specific mode) ← Clear and intentional
```

**Project-level mode (files=[]):**
```
✅ Gate 0: Ruff Format: Skipped (no matching files) ← Looks like an error!
```

**Impact:**
- "no matching files" resembles error message (file discovery failed?)
- Not obvious this is **intentional behavior** in project-level mode
- Inconsistent UX: file-specific skips are explicit, project-level skips are generic
- Users waste time debugging non-existent problems
- Agent uncertainty: "should I provide files differently?"

**Root Cause:**
Skip reason logic uses different strategies:
- File-specific pytest skip: Explicit mode mention ("file-specific mode")
- Project-level static gate skip: Generic fallback message ("no matching files")

**Solution:**
Use consistent mode-based skip reasons across both modes:

```
Project-level mode (files=[]):
✅ Gate 0: Ruff Format: Skipped (project-level mode - static analysis unavailable)
✅ Gate 1: Ruff Lint: Skipped (project-level mode - static analysis unavailable)
   Tip: Use files=["path/file.py"] for file-specific static analysis

File-specific mode (files=[...]):
✅ Gate 5: Tests: Skipped (file-specific mode - tests run project-wide)
✅ Gate 6: Coverage: Skipped (file-specific mode - coverage is project-wide)
   Tip: Use files=[] for project-level test validation
```
**Implementation:**
Standardize skip reason generation in qa_manager.py:
```python
def _get_skip_reason(self, gate: Gate, mode: str) -> str:
    if mode == "file-specific" and self._is_pytest_gate(gate):
        return "file-specific mode - tests run project-wide"
    elif mode == "project-level" and not self._is_pytest_gate(gate):
        return "project-level mode - static analysis unavailable"
    else:
        return "gate not applicable"
```

**Benefits:**
- **Single source of truth** for skip logic
- **Testable:** Unit tests verify consistency
- **Maintainable:** One place to update messaging
- **User-friendly:** Always shows WHY skip happened

**Implementation Priority:** P1 (fixes Finding 7 comprehensively)

---

## Advanced Improvements
### Improvement A: Schema-First JSON Output

**Rationale:**
Text-only output requires fragile parsing heuristics. Machines need structured data, humans need formatted text. Solution: **JSON as source of truth**, text output is **derived rendering** (not primary contract).

**Design Decision (Beta):**
- `text_output` field exists for **convenience only** (human-readable view)
- Tool consumers **must parse JSON** structure (gates[], summary, etc.)
- Alternative: Render text only in logs/CLI (not in response) - deferred for now

**Benefits:**
- **Zero ambiguity:** No "did gate skip because of error or mode?"
- **CI/CD ready:** Automated decision-making without regex parsing
- **Single source of truth:** JSON is primary contract, text is convenience view
- **Schema versioning:** Breaking changes explicit via version field (consumers must update)
- **Config-driven:** All policies in quality.yaml, not hidden in code

**Schema Design:**
```json
{
  "version": "2.0",
  "mode": "project-level" | "file-specific",
  "files": [],
  "summary": {
    "passed": 2,
    "failed": 1,
    "skipped": 3,
    "total_violations": 14,
    "auto_fixable": 9
  },
  "gates": [
    {
      "id": 0,
      "name": "Ruff Format",
      "status": "skipped" | "passed" | "failed",
      "skip_reason": "project-level mode - static analysis unavailable",
      "duration_ms": 0,
      "command": {
        "executable": "ruff",
        "args": ["format", "--check"],
        "cwd": "/workspace",
        "environment": {
          "python": "3.12.1",
          "ruff": "0.1.9"
        }
      },
      "output": {
        "stdout": "All checks passed!",
        "stderr": "",
        "truncated": false,
        "full_log_path": null
      },
      "issues": []
    }
  ],
  "text_output": "Quality Gates Results:\n..."
}
```

**Implementation Priority:** P0 (must-have for v1)

---

### Improvement B: Command + Environment Reproducibility

**Rationale:**
"It works on my machine" debugging requires exact command, cwd, and tool versions. Often failures are version/path differences.

**Metadata per Gate:**
```json
"command": {
  "executable": "python",
  "args": ["-m", "ruff", "check", "--config=.st3/ruff.toml"],
  "cwd": "/workspace",
  "duration_ms": 1234,
  "exit_code": 1,
  "environment": {
    "python_version": "3.12.1",
    "tool_version": "0.1.9",
    "tool_path": "/workspace/.venv/bin/ruff",
    "platform": "Windows-11-10.0.22621"
  }
}
```

**Use Cases:**
1. **Local reproduction:** Copy exact command from failure
2. **Version debugging:** "Oh, CI uses ruff 0.1.9, I have 0.2.1"
3. **Performance analysis:** Identify slow gates via duration_ms
4. **Audit trail:** Full context for compliance requirements

**Implementation Priority:** P1 (high value for v1)

---

### Improvement C: Stdout/Stderr Capture with Truncation Policy

**Rationale:**
Large tool outputs (pytest: 500 lines, mypy: 200 errors) explode response size. Need intelligent truncation with escape hatch to full logs.

**Truncation Policy:**
```python
MAX_LINES = 50
MAX_BYTES = 5120  # 5KB

def truncate_output(output: str) -> dict:
    lines = output.splitlines()
    if len(lines) <= MAX_LINES and len(output) <= MAX_BYTES:
        return {"content": output, "truncated": false}
    
    truncated = "\n".join(lines[:MAX_LINES])
    remaining = len(lines) - MAX_LINES
    
    return {
        "content": truncated + f"\n\n... (truncated {remaining} more lines)",
        "truncated": true,
        "full_log_path": save_to_artifact(output)
    }
```

**Example Output:**
```json
"output": {
  "stdout": "test_qa_manager.py::test_something PASSED\n...(48 more lines)...\n\n... (truncated 452 more lines)",
  "stderr": "",
  "truncated": true,
  "full_log_path": "/tmp/qa_gate_5_20260212_143022.log"
}
```

**Implementation Priority:** P0 (critical for Finding 1)

---

### Improvement D: JSON-Native Tool Parser

**Rationale:**
Ruff, mypy, pytest all support structured JSON output. Text parsing is fragile (regex brittle, fixability detection unreliable). Use native formats.

**Tool-Specific Parsers:**
```python
# .st3/quality.yaml
gates:
  - id: 1
    name: "Ruff Strict Lint"
    command: "ruff check --output-format=json"
    parse_strategy: "json"
    parser: "ruff_json"  # Uses ruff's native JSON schema
    
  - id: 3
    name: "Mypy Type Check"
    command: "mypy --output=json"
    parse_strategy: "json"
    parser: "mypy_json"
    
  - id: 5
    name: "Tests"
    command: "pytest --json-report --json-report-file=-"
    parse_strategy: "json"
    parser: "pytest_json"
```

**Benefits:**
- **Accurate fixable detection:** Ruff JSON has `fix.applicability` field
- **File grouping:** Native `filename` field in each violation
- **Rule metadata:** Description, URL to docs, severity level
- **Zero regex:** Direct object access, no pattern matching

**Example Ruff JSON Output:**
```json
[
  {
    "code": "ANN401",
    "message": "Dynamically typed expressions (typing.Any) are disallowed",
    "location": {
      "file": "qa_manager.py",
      "row": 260,
      "column": 41
    },
    "fix": {
      "applicability": "safe",
      "edits": [...]
    }
  }
]
```

**Implementation Priority:** P0 (enables Finding 2 + 4 solutions)

---

### Improvement E: Realistic Progress Indication

**Rationale:**
MCP protocol doesn't support streaming tool responses. Live progress during execution is **technically infeasible** without protocol changes.

**What's Possible:**
1. **Post-execution timing breakdown** (user-facing):
   ```
   Gate execution timings:
     Gate 0 (Ruff Format):     0.2s ✅
     Gate 1 (Ruff Lint):       1.3s ❌
     Gate 5 (Tests):          12.4s ✅ ← slowest
     Total:                   14.6s
   ```

2. **Server-side logging** (developer/CI logs):
   ```python
   logger.info(f"[{timestamp}] Running gate {i+1}/{total}: {gate.name}")
   logger.info(f"[{timestamp}] Gate {gate.id} completed in {duration_ms}ms: {status}")
   ```

**What's NOT Possible:**
- Real-time progress bars in tool response
- Live streaming of gate execution
- Cancellable/interruptible gates via UI

**Implementation Priority:** P2 (post-v1, manage expectations)

---

### Improvement F: Consolidated Skip Reason Logic

**Rationale:**
Finding 7 identified two symptoms of same problem: skip reasons inconsistent and ambiguous across modes.

**Root Cause Analysis:**
```python
# Current: Different code paths for skip reasons
if not python_files:
    skip_reason = "no matching files"  # Generic, ambiguous
elif is_file_specific_mode and is_pytest_gate:
    skip_reason = "file-specific mode"  # Explicit, clear
```

**Solution - Unified Skip Reason Generator:**
```python
def _get_skip_reason(self, gate: Gate, mode: str) -> str:
    """Generate consistent, mode-aware skip reasons."""
    is_pytest = self._is_pytest_gate(gate)
    
    if mode == "file-specific":
        if is_pytest:
            return "file-specific mode - tests run project-wide"
        else:
            return "gate passed/executed"  # Not skipped
    else:  # project-level
        if not is_pytest:
            return "project-level mode - static analysis unavailable"
        else:
            return "gate passed/executed"  # Not skipped
```

**Benefits:**
- **Single source of truth** for skip logic
- **Testable:** Unit tests verify consistency
- **Maintainable:** One place to update messaging
- **User-friendly:** Always shows WHY skip happened

**Implementation Priority:** P1 (fixes Finding 7 comprehensively)

---
---

## Config-First Design Philosophy

**Principle:** quality.yaml is the **single source of truth** for ALL quality gate policies. Code contains only defaults + execution logic, no "hidden policies".

**What Belongs in Config:**

```yaml
gates:
  - id: 1
    name: "Ruff Strict Lint"
    
    # Execution
    command_template: "ruff check --output-format=json {files}"
    timeout: 120
    
    # Parsing
    output_format: "json"  # json | text
    parser: "ruff_json"    # ruff_json | mypy_json | pytest_json | none
    
    # Output Capture
    capture: "on_fail"     # none | on_fail | always
    truncate:
      max_lines: 50
      max_bytes: 5120      # 5KB
      
    # Artifact Management
    artifact_log: true     # Save full output to /tmp/qa_gate_*.log
    
    # Mode Applicability (optional)
    modes:
      file_specific: true  # Run in file-specific mode?
      project_level: false # Run in project-level mode?
```

**What Stays in Code:**

```python
# ONLY defaults + execution orchestration
class QAManager:
    DEFAULT_TIMEOUT = 300
    DEFAULT_CAPTURE = "on_fail"
    DEFAULT_TRUNCATE_LINES = 50
    
    def run_quality_gates(self, files: list[str]) -> dict:
        # Load config (SSOT)
        gates = self.config_loader.load_gates()
        
        # Execute with config-driven policies
        for gate in gates:
            result = self._execute_gate(
                gate,
                timeout=gate.timeout or self.DEFAULT_TIMEOUT,
                capture=gate.capture or self.DEFAULT_CAPTURE
            )
```

**Benefits:**
1. **Visibility:** All policies visible in one file
2. **Testability:** Change policies without code changes
3. **Auditability:** Git tracks policy evolution
4. **Flexibility:** Per-gate configuration granularity

**Anti-Pattern (Avoid):**
```python
# ❌ Hidden policy in code
if gate.id == 1:  # Special case for Ruff
    max_lines = 100
else:
    max_lines = 50
```

**Correct Pattern:**
```yaml
# ✅ Policy in config
gates:
  - id: 1
    truncate:
      max_lines: 100  # Ruff verbose, needs more context
  - id: 3
    truncate:
      max_lines: 50   # Mypy concise
```

---
## Improvement Recommendations

### Priority 0 (Must-Have for v1 - Architecture Foundations):
1. **Schema-first JSON output** (Improvement A) - Foundation for all parsing
2. **JSON-native tool parsers** (Improvement D) - Ruff/mypy/pytest structured output
3. **Stdout/stderr truncation** (Improvement C) - Handle large outputs safely
4. **Consolidated skip logic** (Improvement F) - Fix Finding 7 completely

**Rationale:** These enable all other improvements and fix critical usability gaps.

---

### Priority 1 (High Value for v1 - User Experience):
5. **Command + environment metadata** (Improvement B) - Reproducibility
6. **Execution mode header** (Finding 6) - Clear mode visibility
7. **Enhanced summary** (Finding 5) - At-a-glance gate breakdown
8. **File grouping** (Finding 4) - Requires JSON parsing from P0

**Rationale:** Major UX improvements, all buildable on P0 foundation.

---

### Priority 2 (Post-v1 - Nice-to-Have):
9. **Timing breakdown** (Improvement E) - Post-execution only, no streaming
10. **Auto-fix prominence** (Finding 2) - Depends on JSON parsing maturity
11. **Extended skip tips** - Inline guidance for mode switching

**Rationale:** Lower impact or higher complexity, defer to v2.

---

## Implementation Notes

### Phase 1: Schema-First Response Format (P0 Items)

**File:** `mcp_server/managers/qa_manager.py`

**Changes Required:**
1. **Return structured dict instead of formatted string:**
   ```python
   def run_quality_gates(self, files: list[str]) -> dict:
       mode = "file-specific" if files else "project-level"
       results = {
           "version": "2.0",
           "mode": mode,
           "files": files,
           "summary": {"passed": 0, "failed": 0, "skipped": 0},
           "gates": [],
           "timings": {}
       }
       # ... execute gates, populate results dict
       results["text_output"] = self._render_text_output(results)
       return results
   ```

2. **Implement JSON parsers for each tool:**
   ```python
   def _parse_ruff_json(self, output: str) -> list[Issue]:
       violations = json.loads(output)
       return [
           Issue(
               file=v["location"]["file"],
               line=v["location"]["row"],
               column=v["location"]["column"],
               code=v["code"],
               message=v["message"],
               fixable=v.get("fix", {}).get("applicability") == "safe"
           )
           for v in violations
       ]
   ```

3. **Output capture with truncation:**
   ```python
   def _execute_gate(self, gate: Gate) -> GateResult:
       result = subprocess.run(
           gate.command,
           capture_output=True,
           text=True,
           timeout=gate.timeout
       )
       
       output = self._truncate_output(
           result.stdout + result.stderr,
           max_lines=50,
           max_bytes=5120
       )
       
       return GateResult(
           status=self._determine_status(result.returncode),
           exit_code=result.returncode,
           output=output,
           issues=self._parse_output(gate, output["content"])
       )
   ```

4. **Unified skip reason logic:**
   ```python
   def _get_skip_reason(self, gate: Gate, mode: str, has_files: bool) -> str:
       """Single source of truth for skip reasons."""
       is_pytest = self._is_pytest_gate(gate)
       
       if mode == "file-specific" and is_pytest:
           return "file-specific mode - tests run project-wide"
       elif mode == "project-level" and not is_pytest and not has_files:
           return "project-level mode - static analysis unavailable"
       else:
           return None  # Gate executable in this mode
   ```

---

### Phase 2: Tool Configuration Updates (P0 Items)

**File:** `.st3/quality.yaml`

**Add parser specifications:**
```yaml
gates:
  - id: 1
    name: "Ruff Strict Lint"
    command_template: "ruff check --output-format=json {files}"
    parse_strategy: "json"
    parser: "ruff_json"
    timeout: 120
    
  - id: 3
    name: "Mypy Type Check"
    command_template: "mypy --output=json {files}"
    parse_strategy: "json"
    parser: "mypy_json"
    timeout: 180
```

---

### Phase 3: Enhanced Metadata (P1 Items)

**Add command context capture:**
```python
def _capture_command_context(self, gate: Gate) -> dict:
    return {
        "command": {
            "executable": gate.tool_name,
            "args": gate.command_args,
            "cwd": str(Path.cwd()),
            "duration_ms": elapsed_time_ms,
            "environment": {
                "python_version": platform.python_version(),
                "tool_version": self._get_tool_version(gate.tool_name),
                "tool_path": shutil.which(gate.tool_name),
                "platform": platform.platform()
            }
        }
    }
```

---

### Phase 4: Text Output Rendering (All Phases)

**Generate human-friendly text from JSON:**
```python
def _render_text_output(self, results: dict) -> str:
    lines = ["Quality Gates Results:"]
    lines.append(f"Mode: {results['mode']} validation")
    lines.append(f"Files: {len(results['files'])} files" if results['files'] else "Files: [] (project-level)")
    
    summary = results['summary']
    lines.append(f"\nOverall Pass: {summary['failed'] == 0} "
                f"({summary['passed']} passed, {summary['failed']} failed, {summary['skipped']} skipped)")
    
    if summary['auto_fixable'] > 0:
        lines.append(f"  💡 {summary['auto_fixable']} issues are auto-fixable")
    
    lines.append("\nGate Results:")
    for gate in results['gates']:
        icon = "✅" if gate['status'] == "passed" else "❌" if gate['status'] == "failed" else "⏭️"
        line = f"{icon} Gate {gate['id']}: {gate['name']}: {gate['status'].title()}"
        
        if gate['status'] == "skipped":
            line += f" ({gate['skip_reason']})"
        elif gate['status'] == "failed":
            fixable = sum(1 for i in gate['issues'] if i.get('fixable'))
            line += f" ({len(gate['issues'])} violations"
            if fixable:
                line += f", {fixable} auto-fixable"
            line += ")"
        
        lines.append(line)
    
    # Add timing breakdown
    if 'timings' in results:
        lines.append("\nGate Execution Timings:")
        for gate_id, duration_ms in results['timings'].items():
            gate_name = next(g['name'] for g in results['gates'] if g['id'] == gate_id)
            lines.append(f"  Gate {gate_id} ({gate_name}): {duration_ms}ms")
        lines.append(f"  Total: {sum(results['timings'].values())}ms")
    
    return "\n".join(lines)
```

---

### Stability Invariants (Beta)

**Principle:** Breaking changes are **intentional and acceptable**. We maintain minimal invariants for smooth internal iteration only.

**Required Fields (Contract):**

1. **version field** (semver format, always present)
   ```json
   {"version": "2.0"}
   ```

2. **gates[] structure** (always present with core fields)
   ```json
   {"gates": [{"id": 0, "name": "...", "status": "..."}]}
   ```

**What Can Break (No Guarantees):**
- Field names (except version, gates[])
- Enum values (status, mode, etc.)
- text_output format (convenience field, not contract)
- Nested structures (command, output, issues)

**Schema Versioning:**
- Major bump (2.0 → 3.0): Breaking structural changes
- Minor bump (2.0 → 2.1): Additive fields, enum extensions
- Consumers **must handle version check** and reject unknown majors

**No Fallback Parsers:**
If schema changes, consumers update or fail fast. No silent degradation.

---

## Example Response Format

### Full JSON Response (Project-Level Mode):
```json
{
  "version": "2.0",
  "mode": "project-level",
  "files": [],
  "summary": {
    "passed": 2,
    "failed": 0,
    "skipped": 4,
    "total_violations": 0,
    "auto_fixable": 0
  },
  "gates": [
    {
      "id": 0,
      "name": "Ruff Format",
      "status": "skipped",
      "skip_reason": "project-level mode - static analysis unavailable",
      "duration_ms": 0,
      "command": null,
      "output": null,
      "issues": []
    },
    {
      "id": 5,
      "name": "Tests",
      "status": "passed",
      "skip_reason": null,
      "duration_ms": 12456,
      "command": {
        "executable": "pytest",
        "args": ["tests/", "-v", "--cov=backend", "--cov-report=term"],
        "cwd": "/workspace",
        "exit_code": 0,
        "environment": {
          "python_version": "3.12.1",
          "tool_version": "7.4.3",
          "tool_path": "/workspace/.venv/Scripts/pytest.exe",
          "platform": "Windows-11-10.0.22621"
        }
      },
      "output": {
        "stdout": "===== test session starts =====\n... (48 lines) ...",
        "stderr": "",
        "truncated": false,
        "full_log_path": null
      },
      "issues": []
    }
  ],
  "timings": {
    "0": 0,
    "1": 0,
    "2": 0,
    "3": 0,
    "5": 12456,
    "6": 2341
  },
  "text_output": "Quality Gates Results:\nMode: project-level validation\n..."
}
```

### Full JSON Response (File-Specific Mode with Failures):
```json
{
  "version": "2.0",
  "mode": "file-specific",
  "files": ["mcp_server/managers/qa_manager.py", "mcp_server/tools/quality_tools.py"],
  "summary": {
    "passed": 3,
    "failed": 2,
    "skipped": 1,
    "total_violations": 14,
    "auto_fixable": 9
  },
  "gates": [
    {
      "id": 1,
      "name": "Ruff Strict Lint",
      "status": "failed",
      "skip_reason": null,
      "duration_ms": 1342,
      "command": {
        "executable": "ruff",
        "args": ["check", "--output-format=json", "mcp_server/managers/qa_manager.py", "mcp_server/tools/quality_tools.py"],
        "cwd": "/workspace",
        "exit_code": 1,
        "environment": {
          "python_version": "3.12.1",
          "tool_version": "0.1.9",
          "tool_path": "/workspace/.venv/Scripts/ruff.exe"
        }
      },
      "output": {
        "stdout": "[{\"code\": \"ANN401\", \"message\": \"Dynamically typed expressions...\"}]",
        "stderr": "",
        "truncated": false,
        "full_log_path": null
      },
      "issues": [
        {
          "file": "mcp_server/managers/qa_manager.py",
          "line": 260,
          "column": 41,
          "code": "ANN401",
          "message": "Dynamically typed expressions (typing.Any) are disallowed",
          "fixable": false,
          "severity": "error"
        },
        {
          "file": "mcp_server/managers/qa_manager.py",
          "line": 262,
          "column": 9,
          "code": "RET501",
          "message": "Do not explicitly return None if it's the only return",
          "fixable": true,
          "severity": "warning"
        }
      ],
      "issues_by_file": {
        "mcp_server/managers/qa_manager.py": [
          {"line": 260, "code": "ANN401", "fixable": false},
          {"line": 262, "code": "RET501", "fixable": true}
        ]
      }
    },
    {
      "id": 5,
      "name": "Tests",
      "status": "skipped",
      "skip_reason": "file-specific mode - tests run project-wide",
      "duration_ms": 0,
      "command": null,
      "output": null,
      "issues": []
    }
  ],
  "timings": {
    "0": 234,
    "1": 1342,
    "2": 567,
    "3": 1891,
    "4": 445,
    "5": 0
  },
  "text_output": "Quality Gates Results:\nMode: file-specific validation (2 files)\n..."
}
```
```

---

## Breaking Change Policy (Beta)

**Design Philosophy:** This is a **beta/single-user system**. We prioritize rapid iteration over API stability.

**Breaking Changes Are Intentional:**
1. **No backward compatibility layer** - Old response shapes not supported
2. **version field required** - Semver-style versioning (2.0, 2.1, 3.0)
3. **Config-driven evolution** - quality.yaml is source of truth for policies
4. **Single consumer** - No external integration dependencies to maintain

**Stability Invariants (Minimal Contract):**

See [Stability Invariants (Beta)](#stability-invariants-beta) section for technical details on guaranteed fields (`version`, `gates[]`).

**Migration Strategy:**

When external consumers exist (future state):
- Re-evaluate whether backward compatibility is needed
- If yes: Consider stabilizing schema or versioning API endpoints
- If no: Continue breaking changes as needed

**Until then:** Breaking changes are features, not bugs. Iterate freely.

**Trade-off:**
- ✅ **Fast iteration** - Refactor freely without migration burden
- ❌ **API instability** - Tool consumers must update with schema changes

For single-user beta: clear win for velocity over stability.

---

## Success Metrics

**Pre-Implementation (Baseline):**
- Average debug cycles per gate failure: 2-3 (manual re-run + analysis)
- Time to identify fixable issues: 2-5 minutes (read hints, test --fix)
- CI/CD integration: Manual parsing required
- Mode ambiguity incidents: ~30% of usage (Finding 7)

**Post-Implementation (Target):**
- Debug cycles: 1 (inline error context eliminates re-run)
- Fixable issue identification: Immediate (header shows count)
- CI/CD integration: Zero parsing (native JSON consumption)
- Mode ambiguity: 0% (explicit mode header + consistent skip reasons)

**Measurement:**
- Track MCP tool call patterns (re-run frequency)
- Survey user feedback on clarity improvements
- Monitor CI/CD adoption rate for JSON parsing
- Count support questions about skip reasons

---
---

## Implementation Decisions

### 1. Config Contract (quality.yaml Extensions)

**New Fields per Gate:**
```yaml
gates:
  - id: 1
    # Existing fields: name, command_template, timeout
    
    # NEW: Output parsing
    output_format: "json" | "text"  # Default: "text"
    parser: "ruff_json" | "mypy_json" | "pytest_json" | "coverage_json" | "none"  # Default: "none"
    
    # NEW: Capture policy
    capture: "none" | "on_fail" | "always"  # Default: "on_fail"
    
    # NEW: Truncation
    truncate:
      max_lines: 50     # Default: 50
      max_bytes: 5120   # Default: 5KB
    
    # NEW: Artifact logging
    artifact_log: true | false  # Default: false
    artifact_path: "temp/qa_logs"  # Default: "temp/qa_logs" (repo-relative)
```

**Defaults in Code:**
```python
class GateConfig:
    output_format: str = "text"
    parser: str = "none"
    capture: str = "on_fail"
    truncate_max_lines: int = 50
    truncate_max_bytes: int = 5120
    artifact_log: bool = False
    artifact_path: str = "temp/qa_logs"
```

---

### 2. Tooling Reality Check (JSON Output Availability)

**Gate-by-Gate Analysis:**

| Gate | Tool | JSON Support | Decision | Config |
|------|------|-------------|----------|--------|
| 0 | Ruff Format | ❌ Formatter only (exit code + stdout) | **Exit code only** | `output_format: text, parser: none` |
| 1 | Ruff Check (Strict Lint) | ✅ `--output-format=json` | Use JSON | `output_format: json, parser: ruff_json` |
| 2 | Ruff Check (Imports) | ✅ `--output-format=json` | Use JSON | `output_format: json, parser: ruff_json` |
| 3 | Ruff Check (Line Length) | ✅ `--output-format=json` | Use JSON | `output_format: json, parser: ruff_json` |
| 4 | Mypy (Types) | ⚠️ `--output=json` (built-in but verbose) | Use JSON (P1) | `output_format: json, parser: mypy_json` |
| 5 | Pytest (Tests) | ⚠️ Requires `pytest-json-report` plugin | **Conditional:** Check if installed | `output_format: json, parser: pytest_json` IF plugin present |
| 6 | Coverage | ✅ `coverage json` built-in | Use JSON (P1) | `output_format: json, parser: coverage_json` |

**P0 Implementation:**
- **Ruff gates (1-3):** JSON parsing REQUIRED (high value, low risk)
- **Ruff format (0):** Exit code only (formatters don't produce diagnostics)
- **Mypy/Pytest/Coverage (4-6):** Text parser fallback if JSON fails (graceful degradation)

**Feature Detection:**
```python
def _supports_json_output(self, gate: Gate) -> bool:
    """Check if gate supports JSON output via feature detection."""
    if gate.tool == "pytest":
        # Use importlib for cross-platform Python import detection
        import importlib.util
        return importlib.util.find_spec('pytest_jsonreport') is not None
    return gate.output_format == "json"
```

---

### 3. Artifacts & Logging (Windows-Safe Paths)

**Artifact Storage:**
```python
# Location: repo-relative for versioning, temp for CI cleanup
ARTIFACT_BASE = Path("temp/qa_logs")  # Relative to repo root

# Naming convention:
# temp/qa_logs/qa_gate_{id}_{timestamp}.log
# Example: temp/qa_logs/qa_gate_1_20260212_143052.log

def _get_artifact_path(self, gate_id: int) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return ARTIFACT_BASE / f"qa_gate_{gate_id}_{timestamp}.log"
```

**Windows Path Safety:**
```python
# ALWAYS use pathlib.Path for cross-platform
from pathlib import Path

# Convert to forward slashes in JSON output
artifact_path = str(path).replace("\\", "/")  # Windows -> POSIX
```

**Cleanup Policy:**
```yaml
# .st3/quality.yaml (optional global config)
artifact_retention:
  max_age_hours: 168  # 7 days
  max_files: 100      # Per gate
  cleanup_on_pass: true  # Delete logs for passed gates (keep failures only)
```

**Implementation:**
```python
# Separate cleanup strategies
def _cleanup_old_artifacts(self):
    """Time-based cleanup (7 days retention)."""
    cutoff = datetime.now() - timedelta(hours=config.artifact_retention.max_age_hours)
    for log_file in ARTIFACT_BASE.glob("qa_gate_*.log"):
        if log_file.stat().st_mtime < cutoff.timestamp():
            log_file.unlink()

def _cleanup_passed_gate_artifacts(self, gate_id: int):
    """Delete artifact logs for passed gates (if cleanup_on_pass enabled)."""
    if config.artifact_retention.cleanup_on_pass:
        for log_file in ARTIFACT_BASE.glob(f"qa_gate_{gate_id}_*.log"):
            log_file.unlink()
```

**Git Ignore:**
```gitignore
# .gitignore (add if not present)
temp/qa_logs/
```

---

### Implementation Plan (P0 - 5-10 Tasks)

**Based on Priority 0 from Improvement Recommendations:**

1. ☐ **Extend quality.yaml schema** - Add new fields with validation
2. ☐ **Implement Ruff JSON parser** - Gates 1-3 (high value, low risk)
3. ☐ **Add stdout/stderr capture** - With truncation policy
4. ☐ **Implement artifact logging** - temp/qa_logs with cleanup
5. ☐ **Update response schema to JSON** - version field + gates[]
6. ☐ **Add consolidated skip logic** - Unified _get_skip_reason()
7. ☐ **Feature detection** - Check pytest-json-report via importlib
8. ☐ **Schema contract tests** - Validate version + gates[] present
9. ☐ **Update MCP tool response** - Return dict instead of string
10. ☐ **Documentation update** - Tool reference with JSON schema

**Success Criteria:**
- Ruff gates (1-3) return structured JSON with file grouping
- Full output captured in temp/qa_logs/*.log (when enabled)
- Response includes version field + gates[] structure
- All tests pass with new response format

**Out of Scope for P0:**
- Mypy/Pytest JSON parsers (P1 - fallback to text if not available)
- Enhanced summary with auto-fixable counts (P1)
- Command/environment metadata (P1)

## Next Steps

1. **Review:** Stakeholder sign-off on schema design and priorities
2. **Prototype:** Implement P0 items in feature branch
3. **Validation:** Run against Issue #131 test suite
4. **Integration:** Merge to main with schema contract tests (version field, gates[] structure)
5. **Documentation:** Update tool reference docs with JSON schema
6. **Iteration:** Gather feedback, prioritize P1/P2 items for v2.1

---

## Appendix: Related Issues

- **Issue #131:** Parent issue for quality gates config-driven execution
- **Issue #133:** Gate 5 & 6 always skipped (RESOLVED - led to dual execution mode design)
- **Issue #121:** Content-aware edit tool improvements (separate safe_edit_file concerns)

---

## References

- **[docs/development/issue131/design.md](../../development/issue131/design.md)** - Issue #131 design specification
- **[docs/coding_standards/QUALITY_GATES.md](../../coding_standards/QUALITY_GATES.md)** - Quality gates enforcement standards

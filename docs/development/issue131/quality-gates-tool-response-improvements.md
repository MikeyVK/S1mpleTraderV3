# Quality Gates Tool Response Improvements - Research

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-12  
**Timestamp:** 2026-02-12

---

## Purpose

Document findings and improvement proposals for run_quality_gates tool response format based on real-world usage during Issue #131 validation. The tool successfully executes quality gates but lacks detailed error context, progress indicators, and structured issue reporting.

## Problem Statement

The run_quality_gates tool successfully executes quality gates but lacks detailed error context, progress indicators, and structured issue reporting, making debugging less efficient than direct terminal execution

## Scope

**In Scope:**
Tool response format, error reporting detail level, progress indicators, issue grouping strategies, skip reason visibility

**Out of Scope:**
Core gate execution logic, quality.yaml configuration format, gate implementation details, Python/Ruff version compatibility

## Prerequisites

- Issue #131 implementation complete
- Real-world validation executed with 7 files across 6 gates
- Multiple gate failures encountered and resolved

## Goals

- Identify specific improvements to tool response format
- Propose actionable changes to enhance debugging workflow
- Evaluate information density vs clarity tradeoffs

## Related Documentation

- docs/development/issue131/
- .st3/quality.yaml
- mcp_server/managers/qa_manager.py
- mcp_server/tools/quality_tools.py

## References

- docs/development/issue131/design.md
- docs/coding_standards/QUALITY_GATES.md

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
- Agent must run re-run command manually to see actual errors
- Adds 1-2 minutes debugging overhead per failed gate
- User cannot assess severity without additional steps

**Root Cause:**
QAManager captures exit code but not stdout/stderr for exit_code strategy gates

**Proposal:**
Include first 5-10 lines of tool output in issues list:
```
❌ Gate 1: Ruff Strict Lint: Fail (exit=1)
  Issues (showing first 5):
  - test_qa_manager.py:260:41: ANN401 Dynamically typed expressions (typing.Any) are disallowed
  - test_qa_manager.py:262:9: RET501 Do not explicitly return None if it's the only return
  - qa_manager.py:271:8: SIM103 Return the condition directly
  ...and 2 more violations
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

**Proposal:**
Add fixable count to gate result header:
```
❌ Gate 1: Ruff Strict Lint: Fail (exit=1) [* 2 auto-fixable]
```

---

### Finding 3: No Progress Indication During Execution

**Observation:**
Tool is silent during execution (~30s for 7 files across 6 gates)

**Impact:**
- Uncertainty whether tool is working or hanging
- Critical for pytest gate which can take 5+ minutes

**Proposal:**
Return progress updates during execution:
```
Running Gate 1 of 6: Ruff Format...
Running Gate 2 of 6: Ruff Strict Lint...
✅ Gate 1: Ruff Format: Pass
Running Gate 3 of 6: Imports...
```

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

**Proposal:**
Group issues by file:
```
Issues by file (3 files with violations):
  mcp_server/managers/qa_manager.py: 4 violations
    - Line 260: ANN401 typing.Any disallowed
    - Line 262: RET501 Remove explicit return None
    ...
  tests/unit/mcp_server/managers/test_qa_manager.py: 9 violations
    - Line 62: E501 Line too long (123 > 100)
    ...
```

---

### Finding 5: Skip Reasons Could Be More Informative

**Observation:**
Current skip reasons:
```
✅ Gate 4: Types: Skipped (no matching files)
✅ Gate 5: Tests: Skipped (repo-scoped)
```

**Impact:**
- "no matching files" doesn't explain WHY (scope filtering)
- "repo-scoped" requires understanding of pytest gate design

**Proposal:**
Expand skip reasons with context:
```
✅ Gate 4: Types: Skipped
   Reason: No files match scope 'backend/dtos/**/*.py'
   Files checked: 7 (all outside scope)

✅ Gate 5: Tests: Skipped
   Reason: Pytest is repo-scoped (tests/ hardcoded in command)
   Use case: File-specific quality checks do not run pytest
```

---

### Finding 6: Overall Summary Lacks Context

**Observation:**
```
Overall Pass: False
```

**Impact:**
- Must scan entire gate list to count failures/skips
- No quick assessment of issue severity

**Proposal:**
```
Overall Pass: False (2 gates failed, 2 skipped, 2 passed)
```

---

## Improvement Recommendations

### Priority 1 (High Impact, Low Effort):
1. **Add fixable count to gate headers** - `[* 2 auto-fixable]`
2. **Enhance overall summary** - `(2 failed, 2 skipped, 2 passed)`
3. **Show first 5 error lines** - Capture stdout for context

### Priority 2 (High Impact, Medium Effort):
4. **Group issues by file** - File-level summary before details
5. **Expand skip reasons** - Add scope/reason context

### Priority 3 (Medium Impact, High Effort):
6. **Progress indicators** - Streaming updates during execution

---

## Implementation Notes

**QAManager Changes Required:**
- Capture stdout/stderr for failed gates (not just exit code)
- Parse output for file/line/rule structure
- Count auto-fixable issues per gate
- Emit progress events during execution

**Response Format Changes:**
- Add `auto_fixable_count` to gate result
- Add `files_with_issues` dict to gate result
- Enhance `skip_reason` field with structured data

**Backward Compatibility:**
- All additions, no breaking changes
- Existing consumers ignore new fields
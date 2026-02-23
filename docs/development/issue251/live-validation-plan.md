<!-- docs/development/issue251/live-validation-plan.md -->
<!-- template=generic_doc version=43c84181 created=2026-02-23 updated= -->
# Live Validation Plan — Issue #251 run_quality_gates refactor

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-23

---

## Purpose

Validate the refactored run_quality_gates tool in practice by calling it with real files. Confirms that structured violation output, scope resolution, and uniform parsing_strategy coverage work end-to-end across all 6 active gates.

## Scope

**In Scope:**
Live MCP tool calls to run_quality_gates on real workspace files. Scope variants: scope=files (specific file list), scope=project, scope=branch. Visual inspection of structured violations in tool response.

**Out of Scope:**
Unit test coverage (covered in TDD cycles C0–C31). Performance benchmarks. Gates outside active_gates (gate5/gate6).

## Prerequisites

Read these first:
1. Branch refactor/251-refactor-run-quality-gates, commit 89e53559 or later
2. MCP server running (start_mcp_server.ps1)
3. quality.yaml: all 6 active gates have parsing_strategy declared
4. Baseline 2037 tests passing
---

## Summary

The refactor replaced exit-code-only gate execution with a config-driven parsing pipeline. Two parsing strategy types cover all real gate outputs: json_violations (ruff/pyright JSON) and text_violations (ruff format diff, mypy text). This plan verifies that all 6 active gates produce structured, actionable ViolationDTO output — not truncated blobs.

---

## Key Changes

- ExitCodeParsing / ParsingConfig removed — replaced by capabilities.parsing_strategy in quality.yaml
- gate2_imports and gate3_line_length: json_violations (ruff --output-format=json)
- gate4_types (mypy): text_violations with named-group regex
- gate4_pyright: json_violations via generalDiagnostics path
- scope=files arm in _resolve_scope — no more ValueError
- _get_skip_reason inlined and removed


---

## Validation Checklist

- [ ] [ ] V1: scope=files with a clean file → overall_pass=true, gate passes, issues=[]
- [ ] [ ] V2: scope=files with a file containing ruff format violations → gate0 issues list non-empty, file/rule/message populated
- [ ] [ ] V3: scope=files with a file containing ruff lint violations → gate1 issues list non-empty, structured ViolationDTO
- [ ] [ ] V4: scope=files with a file having a long line → gate3 issues show file+line+col+rule=E501
- [ ] [ ] V5: scope=files, mypy-failing DTO file → gate4_types issues show file+line+severity+message+rule
- [ ] [ ] V6: scope=project → all 6 gates execute, response contains 6 gate entries
- [ ] [ ] V7: scope=files with empty list → all gates skipped, skip_reason populated
- [ ] [ ] V8: scope=branch → gates run against changed .py files
- [ ] [ ] F12 guard: run_quality_gates response contains no _get_skip_reason reference in issues
- [ ] [ ] Response shape: content[0] type=text (summary_line), content[1] type=json (full payload)


---

## Test Scenarios

Each scenario below is a live MCP call. Record the actual tool response in the Results column.

| # | Scenario | Call | Expected | Result |
|---|----------|------|----------|--------|
| V1 | Clean file, scope=files | `run_quality_gates(scope="files", files=["script.py"])` | overall_pass=true | |
| V2 | Unformatted file | `run_quality_gates(scope="files", files=["<unformatted_file>"])` | gate0 issues with file/rule=FORMAT | |
| V3 | Lint violations | `run_quality_gates(scope="files", files=["<lint_file>"])` | gate1 structured violations | |
| V4 | Long line (E501) | `run_quality_gates(scope="files", files=["<long_line_file>"])` | gate3 issue rule=E501, line+col | |
| V5 | Mypy-failing DTO | `run_quality_gates(scope="files", files=["<dto_file>"])` | gate4_types text violations | |
| V6 | Project scope | `run_quality_gates(scope="project")` | 6 gate entries, all have status | |
| V7 | Empty file list | `run_quality_gates(scope="files", files=[])` | all skip_reason="Skipped (no matching files)" | |
| V8 | Branch scope | `run_quality_gates(scope="branch")` | runs on changed files since baseline | |

## Validation Results

_To be filled in during live validation session._

**Date:**  
**Tester:**  
**Commit:**  

| # | Status | Notes |
|---|--------|-------|
| V1 | | |
| V2 | | |
| V3 | | |
| V4 | | |
| V5 | | |
| V6 | | |
| V7 | | |
| V8 | | |

## Go / No-Go Criteria

**GO** (ready for PR) when:
- All V1–V8 checkmarks green
- No truncated blob issues in any gate response
- summary_line present as first content item
- F12 guard confirmed: no _get_skip_reason in prod code

**NO-GO** if:
- Any active gate returns unstructured `Gate failed exit=1` blob
- scope resolution raises ValueError or returns wrong files
- Pyright/mypy violations show as single-issue blob instead of per-violation list

## Related Documentation
- **[docs/development/issue251/design.md][related-1]**
- **[docs/development/issue251/research.md][related-2]**
- **[.st3/quality.yaml][related-3]**

<!-- Link definitions -->

[related-1]: docs/development/issue251/design.md
[related-2]: docs/development/issue251/research.md
[related-3]: .st3/quality.yaml

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-23 | Agent | Initial draft |
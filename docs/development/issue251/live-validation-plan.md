<!-- docs/development/issue251/live-validation-plan.md -->
<!-- template=generic_doc version=43c84181 created=2026-02-23 updated=2026-02-23 -->
# Live Validation Plan — Issue #251 run_quality_gates refactor

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-02-23

---

## Purpose

Validate the refactored `run_quality_gates` tool in practice by calling it with real files.  
Confirms that structured violation output, scope resolution, and uniform `parsing_strategy`
coverage work end-to-end across all 6 active gates and all 4 scope modes.

## Scope

**In Scope:**  
Live MCP tool calls across all scope variants: `auto` (default), `files`, `branch`, `project`.  
Each scope includes at least one PASS and one FAIL scenario.  
`files` scope covers single-file, multi-file, single-dir, and multi-dir combinations.

**Out of Scope:**  
Unit test coverage (TDD cycles C0–C31). Performance benchmarks. Inactive gates (gate5/gate6).

## Prerequisites

1. Branch `refactor/251-refactor-run-quality-gates`, commit `89e53559` or later
2. MCP server running (`start_mcp_server.ps1`)
3. `quality.yaml`: all 6 active gates have `parsing_strategy` declared
4. Baseline: 2037 tests passing

---

## Summary

The refactor replaced exit-code-only gate execution with a config-driven parsing pipeline.
All 4 scope modes now resolve deterministically to a `list[str]` of `.py` paths passed to each gate.
This plan verifies every scope mode resolves correctly **and** that gates produce structured
`ViolationDTO` output — not truncated blobs.

---

## Key Changes

- `ExitCodeParsing` / `ParsingConfig` removed — replaced by `capabilities.parsing_strategy` in `quality.yaml`
- `gate2_imports` and `gate3_line_length`: `json_violations` (ruff `--output-format=json`)
- `gate4_types` (mypy): `text_violations` with named-group regex
- `gate4_pyright`: `json_violations` via `generalDiagnostics` path
- `scope=files` arm in `_resolve_scope` — no more `ValueError`
- `_get_skip_reason` inlined and removed

---

## Scope Behavior Reference

| Scope | What the tool actually does | Files passed to gates |
|-------|-----------------------------|-----------------------|
| `auto` *(default)* | Reads `quality_gates.baseline_sha` from `.st3/state.json`. Runs `git diff <baseline_sha>..HEAD --name-only`, keeps `.py` files. Takes union with `quality_gates.failed_files` from state. **Fallback:** if no `baseline_sha` in state, falls back to `project` scope. | `diff_files ∪ failed_files` (or full project glob) |
| `branch` | Reads `workflow.parent_branch` from `.st3/state.json` (fallback: `"main"`). Runs `git diff <parent_branch>..HEAD --name-only`, keeps `.py` files. | `.py` files changed since parent branch |
| `project` | Expands `project_scope.include_globs` from `quality.yaml` against workspace root using `Path.glob`. Sorted, deduplicated. | All matched `.py` files in workspace |
| `files` | Returns the caller-supplied list **verbatim** — no git, no glob expansion. Empty list or missing `files` raises `ValidationError` at input level. | Exactly the paths supplied (no expansion) |

---

## Validation Checklist

### scope=auto

- [ ] A1-pass: `baseline_sha` present, only clean files in diff → `overall_pass=true`
- [ ] A1-fail: `baseline_sha` present, diff includes a file with ruff violations → gate1 issues populated
- [ ] A2: no `baseline_sha` in state → falls back to project scope, all project files checked

### scope=branch

- [ ] B1-pass: diff against parent branch contains only clean `.py` files → `overall_pass=true`
- [ ] B2-fail: diff includes a file with type errors → gate4_types issues populated
- [ ] B3: no `parent_branch` in state → defaults to `"main"`, tool runs without error

### scope=project

- [ ] P1-pass: all matched project files are clean → `overall_pass=true`, 6 gate entries
- [ ] P2-fail: project contains a file with line-length violations → gate3 issues show `rule=E501`

### scope=files

- [ ] F1: single clean file → `overall_pass=true`, issues=[]
- [ ] F2: single failing file (ruff format) → gate0 issues non-empty, `file/rule/message` populated
- [ ] F3: multiple files, all clean → `overall_pass=true`
- [ ] F4: multiple files, one failing (lint) → only the failing file appears in gate1 issues
- [ ] F5: single directory path → tool accepts it, gates receive the dir path verbatim; observe behavior
- [ ] F6: multiple directory paths → same as F5, both dirs forwarded to all gates
- [ ] F7: `files` not provided with `scope="files"` → `ValidationError` at input level (never reaches gates)

### Response shape (all scopes)

- [ ] `content[0]` type=`text` (summary line)
- [ ] `content[1]` type=`json` (full payload with `gates` list)
- [ ] F12 guard: no `_get_skip_reason` reference anywhere in response

---

## Test Scenarios

### scope=auto (default)

| # | Scenario | Call | Behavior | Expected | Result |
|---|----------|------|----------|----------|--------|
| A1-pass | Baseline present, diff is clean | `run_quality_gates()` | diffs `<baseline_sha>..HEAD`, finds only clean files | `overall_pass=true`, all gates pass or skip | |
| A1-fail | Baseline present, diff has violation | `run_quality_gates()` *(with a dirty .py in diff)* | same diff, dirty file included | gate for that violation type shows issues | |
| A2 | No baseline_sha in state | `run_quality_gates()` *(state has no baseline_sha)* | falls back to project scope; expands include_globs | behaves identically to `scope="project"` | |

### scope=branch

| # | Scenario | Call | Behavior | Expected | Result |
|---|----------|------|----------|----------|--------|
| B1-pass | Parent branch in state, diff is clean | `run_quality_gates(scope="branch")` | `git diff <parent>..HEAD`, clean `.py` files only | `overall_pass=true` | |
| B2-fail | Diff contains type-error file | `run_quality_gates(scope="branch")` *(with mypy-failing file in diff)* | same diff, includes bad file | gate4_types issues: `file/line/severity/rule` populated | |
| B3 | No parent_branch in state | `run_quality_gates(scope="branch")` *(state has no parent_branch)* | defaults to `"main"`, `git diff main..HEAD` | runs without error, result depends on diff vs main | |

### scope=project

| # | Scenario | Call | Behavior | Expected | Result |
|---|----------|------|----------|----------|--------|
| P1-pass | Workspace files all clean | `run_quality_gates(scope="project")` | expands `include_globs` from `quality.yaml`, runs all 6 gates | `overall_pass=true`, 6 gate entries | |
| P2-fail | Workspace has E501 file | `run_quality_gates(scope="project")` *(with long-line file present)* | same expansion, gate3 hits the file | gate3 issues: `rule=E501`, `line`, `col` populated | |

### scope=files — single/multiple files

| # | Scenario | Call | Behavior | Expected | Result |
|---|----------|------|----------|----------|--------|
| F1 | Single clean file | `run_quality_gates(scope="files", files=["script.py"])` | passes `["script.py"]` verbatim to all gates | `overall_pass=true`, issues=[] for all gates | |
| F2 | Single file with format violation | `run_quality_gates(scope="files", files=["<dirty_fmt.py>"])` | verbatim path, ruff format runs on it | gate0 issues non-empty, `file/rule=FORMAT/message` | |
| F3 | Multiple files, all clean | `run_quality_gates(scope="files", files=["script.py", "backend/__init__.py"])` | both paths forwarded to all gates | `overall_pass=true` | |
| F4 | Multiple files, one fails lint | `run_quality_gates(scope="files", files=["script.py", "<lint_fail.py>"])` | both paths forwarded; only failing file triggers violation | gate1 issues reference only `<lint_fail.py>`, not `script.py` | |

### scope=files — directories

| # | Scenario | Call | Behavior | Expected | Result |
|---|----------|------|----------|----------|--------|
| F5 | Single directory | `run_quality_gates(scope="files", files=["backend/"])` | `"backend/"` passed verbatim to gates (no Python glob expansion in `_resolve_scope`) | observe: do gates accept dir path? does ruff recurse into it? | |
| F6 | Multiple directories | `run_quality_gates(scope="files", files=["backend/", "mcp_server/"])` | both dir paths forwarded verbatim | same as F5, two dirs; note any skip_reason or error per gate | |

### scope=files — validation errors

| # | Scenario | Call | Behavior | Expected | Result |
|---|----------|------|----------|----------|--------|
| F7 | `scope="files"` with no `files` | `run_quality_gates(scope="files")` | pydantic validator rejects before reaching gates | `ValidationError`: files required when scope=files | |

---

## Validation Results

_To be filled in during live validation session._

**Date:**  
**Tester:**  
**Commit:**  

| # | Status | Notes |
|---|--------|-------|
| A1-pass | | |
| A1-fail | | |
| A2 | | |
| B1-pass | | |
| B2-fail | | |
| B3 | | |
| P1-pass | | |
| P2-fail | | |
| F1 | | |
| F2 | | |
| F3 | | |
| F4 | | |
| F5 | | |
| F6 | | |
| F7 | | |

---

## Go / No-Go Criteria

**GO** (ready for PR) when:
- All pass/fail scenarios match expected outcomes
- `scope=files` with directories (F5/F6): behavior is documented even if gates skip or recurse
- No gate returns unstructured `Gate failed exit=1` blob
- `summary_line` present as first content item across all scopes
- F12 guard confirmed: no `_get_skip_reason` in response

**NO-GO** if:
- Any active gate returns unstructured blob for violations
- `scope=auto` fallback to project silently broken (A2 fails)
- `scope=files` verbatim pass-through raises `ValueError` instead of working
- Pyright/mypy violations show as single-issue blob instead of per-violation list

---

## Related Documentation

- **[docs/development/issue251/design.md](docs/development/issue251/design.md)**
- **[docs/development/issue251/research.md](docs/development/issue251/research.md)**
- **[.st3/quality.yaml](.st3/quality.yaml)**

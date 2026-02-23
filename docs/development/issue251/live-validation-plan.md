<!-- docs/development/issue251/live-validation-plan.md -->
<!-- template=generic_doc version=43c84181 created=2026-02-23 updated=2026-02-23 -->
# Live Validation Plan — Issue #251 run_quality_gates refactor

**Status:** READY FOR EXECUTION  
**Version:** 1.2  
**Last Updated:** 2026-02-23

---

## Purpose

Validate the refactored `run_quality_gates` tool end-to-end through real MCP calls.
This plan verifies, in one runbook, that:
1. scope resolution is deterministic for all 4 scope modes;
2. active gates return structured violations (not fallback blobs);
3. response contract (`content[0]=text`, `content[1]=json`) is stable.

## Scope

**In Scope:**
- Live MCP tool calls for `auto` (default), `branch`, `project`, `files`
- At least one PASS and one FAIL case per scope
- `files` scope variants: single file, multiple files, single dir, multiple dirs
- Response schema and violation-shape validation for all active gates (0,1,2,3,4,4b)

**Out of Scope:**
- Unit/integration suite quality (already covered in TDD C0–C31)
- Performance/benchmarking
- Inactive gates (gate5/gate6)

## Prerequisites

1. Branch: `refactor/251-refactor-run-quality-gates`
2. Commit: `89e53559` or later
3. MCP server started with `start_mcp_server.ps1`
4. `.st3/quality.yaml`: all active gates define `capabilities.parsing_strategy`
5. Workspace is clean enough to isolate scenario outcomes (prefer one scenario at a time)
6. Baseline context known:
   - `.st3/state.json` has/has-not `quality_gates.baseline_sha` depending on scenario
   - `.st3/state.json` has/has-not `workflow.parent_branch` depending on scenario

---

## Summary of Refactor Behavior (what must hold true)

- Gate parsing is config-driven via `capabilities.parsing_strategy`.
- `scope` always resolves to `list[str]` before gate execution.
- `scope="files"` is explicit, validated input: no implicit fallback.
- Violations are surfaced as structured entries in `gates[].issues[]`.
- Exit-code fallback blobs (`"Gate failed with exit code ..."`) are not expected for active gates.

---

## Scope Behavior Reference

| Scope | Resolution behavior | Files passed to gates |
|-------|---------------------|-----------------------|
| `auto` *(default)* | Uses `quality_gates.baseline_sha` from `.st3/state.json`; resolves `git diff <baseline_sha>..HEAD` `.py` + union with `quality_gates.failed_files`; if no baseline -> fallback to `project` | `diff_files ∪ failed_files` or project glob result |
| `branch` | Uses `workflow.parent_branch` from state; fallback `"main"`; resolves `.py` changes from `git diff <parent>..HEAD` | changed `.py` files |
| `project` | Expands `project_scope.include_globs` from `.st3/quality.yaml`; dedupe + sort | matched project files |
| `files` | Uses caller-supplied list verbatim; no git/glob expansion; missing/empty `files` rejected by validation | exactly provided paths |

---

## Execution Protocol (strict order)

1. Capture test metadata (`date`, `tester`, `commit`, server session info).
2. Run response-shape smoke check (`run_quality_gates()` default) and confirm content ordering.
3. Execute scenarios in this order: `A*` -> `B*` -> `P*` -> `F*`.
4. After each scenario, store one evidence block (request, response summary, gate evidence, verdict).
5. If scenario outcome is ambiguous, rerun once; if still ambiguous, mark **BLOCKED** with reason.

---

## Evidence Format (required per scenario)

For every scenario row, capture:
- **Request:** exact MCP call payload
- **Summary:** `overall_pass`, summary line text, passed/failed/skipped counts
- **Gate proof:** affected gate id + minimal issue sample (`file`, `line`, `rule`, `message`, `fixable` if available)
- **Fallback check:** confirm no active gate returns `Gate failed with exit code`
- **Verdict:** PASS / FAIL / BLOCKED with 1-line rationale

---

## Validation Checklist

### scope=auto

- [ ] A1-pass: `baseline_sha` present, diff clean -> `overall_pass=true`
- [ ] A1-fail: `baseline_sha` present, diff has violation -> relevant gate `issues[]` populated
- [ ] A2: no `baseline_sha` -> fallback to `project` behavior

### scope=branch

- [ ] B1-pass: parent diff clean -> `overall_pass=true`
- [ ] B2-fail: parent diff has type error -> `gate4_types` structured issues
- [ ] B3: no `parent_branch` -> fallback to `main`, run succeeds

### scope=project

- [ ] P1-pass: project clean -> `overall_pass=true`, 6 gate entries
- [ ] P2-fail: E501 present -> `gate3` issues include `rule=E501`

### scope=files

- [ ] F1: single clean file -> `overall_pass=true`
- [ ] F2: single format-failing file -> `gate0` issues non-empty (`rule=FORMAT`)
- [ ] F3: multiple clean files -> `overall_pass=true`
- [ ] F4: multiple files one lint-fail -> failing file only in gate1 issues
- [ ] F5: single directory path -> accepted and forwarded verbatim
- [ ] F6: multiple directory paths -> both forwarded verbatim
- [ ] F7: missing `files` with `scope="files"` -> validation error pre-execution

### response shape & contract (all scopes)

- [ ] `content[0]` is `type="text"` summary
- [ ] `content[1]` is `type="json"` payload with `gates`
- [ ] each gate entry has stable minimal shape: `id`, `passed`, `skipped`, `violations`
- [ ] no `_get_skip_reason` reference in user-visible response artifacts

---

## Test Scenarios

### scope=auto (default)

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| A1-pass | Baseline present, diff clean | `run_quality_gates()` | pass or skip-only outcomes; no structured failures |
| A1-fail | Baseline present, diff dirty | `run_quality_gates()` | failing gate has structured issue entries |
| A2 | No baseline in state | `run_quality_gates()` | behavior equivalent to `scope="project"` |

### scope=branch

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| B1-pass | Parent diff clean | `run_quality_gates(scope="branch")` | `overall_pass=true` |
| B2-fail | Parent diff has type errors | `run_quality_gates(scope="branch")` | `gate4_types` issues include `file/line/severity/rule` |
| B3 | No parent in state | `run_quality_gates(scope="branch")` | defaults to `main`, executes without crash |

### scope=project

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| P1-pass | Project clean | `run_quality_gates(scope="project")` | 6 gate results; pass/skip only |
| P2-fail | Long line present | `run_quality_gates(scope="project")` | `gate3` includes `E501` violation entries |

### scope=files — single/multiple files

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| F1 | One clean file | `run_quality_gates(scope="files", files=["script.py"])` | pass/skip only |
| F2 | One format-fail file | `run_quality_gates(scope="files", files=["<dirty_fmt.py>"])` | `gate0` structured violations, not blob |
| F3 | Multiple clean files | `run_quality_gates(scope="files", files=["script.py", "backend/__init__.py"])` | pass/skip only |
| F4 | Mixed files (one lint fail) | `run_quality_gates(scope="files", files=["script.py", "<lint_fail.py>"])` | lint issue references failing file only |

### scope=files — directories

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| F5 | Single dir | `run_quality_gates(scope="files", files=["backend/"])` | accepted; path forwarded verbatim |
| F6 | Multiple dirs | `run_quality_gates(scope="files", files=["backend/", "mcp_server/"])` | both forwarded; behavior documented |

### scope=files — validation errors

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| F7 | Missing files field | `run_quality_gates(scope="files")` | input validation error (no gate run) |

---

## Validation Results (to fill live)

**Date:**  
**Tester:**  
**Commit:**  
**Server Session:**  

| Scenario | Status (PASS/FAIL/BLOCKED) | Evidence Ref | Notes |
|----------|-----------------------------|--------------|-------|
| A1-pass | | | |
| A1-fail | | | |
| A2 | | | |
| B1-pass | | | |
| B2-fail | | | |
| B3 | | | |
| P1-pass | | | |
| P2-fail | | | |
| F1 | | | |
| F2 | | | |
| F3 | | | |
| F4 | | | |
| F5 | | | |
| F6 | | | |
| F7 | | | |

---

## Go / No-Go Criteria

**GO** when all below are true:
- All scenarios complete with expected behavior or justified skips
- No active gate emits unstructured `Gate failed with exit code` as primary failure signal
- `scope=auto` fallback to project proven in A2
- `scope=files` validation contract proven in F7
- Response ordering and compact gate shape stable in all sampled scopes

**NO-GO** if any of the following occurs:
- Active gate failure is only blob-based/unstructured
- `scope=auto` fallback path is broken or inconsistent
- `scope=files` yields runtime `ValueError` instead of input validation
- Mypy/Pyright failures collapse to one generic issue without per-violation fields

---

## Risk Notes / Common False Positives

- Empty-file-set scenarios can produce skips; this is not automatically a failure.
- `files` with directory paths depends on tool recursion behavior (ruff/mypy/pyright); document observed behavior explicitly.
- Local env drift (tool version mismatch) can change violation counts; compare structure first, counts second.

---

## Related Documentation

- **[docs/development/issue251/design.md](docs/development/issue251/design.md)**
- **[docs/development/issue251/research.md](docs/development/issue251/research.md)**
- **[.st3/quality.yaml](.st3/quality.yaml)**

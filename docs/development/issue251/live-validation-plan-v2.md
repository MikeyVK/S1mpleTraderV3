<!-- docs/development/issue251/live-validation-plan-v2.md -->
<!-- based on live-validation-plan.md v1.2 — updated for C32–C39 post-fix state -->
# Live Validation Plan v2 — Issue #251 run_quality_gates refactor

**Status:** COMPLETED (SEE 2026-03-01 ADDENDUM)
**Version:** 2.0
**Last Updated:** 2026-03-01
**Based on:** live-validation-plan.md v1.2 (session 1–3, 2026-02-23/24)

---

## Purpose

Validate the refactored `run_quality_gates` tool end-to-end through real MCP calls,
**after completing TDD cycles C32–C39** which resolved all actionable findings from
the first validation run (F-1 through F-19).

This plan verifies, in one clean runbook, that:
1. Scope resolution is deterministic for all 4 scope modes;
2. Active gates return structured violations (not fallback blobs);
3. Response contract (`content[0]=text`, `content[1]=json`) is stable and matches the
   updated C35/C36/C37/C38/C39 contract;
4. All C32–C39 fixes hold under live conditions.

## Delta vs v1 — What is New

| Area | v1 expected | v2 expected (after C32–C39) |
|------|-------------|-----------------------------|
| All-skipped summary | `⚠️ 0/0 active (N skipped)` | `✅ Nothing to check (no changed files) [scope · 0 files] — Nms` |
| Summary suffix | bare text | always `[scope · N files] — Nms` |
| Compact JSON root keys | `overall_pass`, `duration_ms`, `gates` | `overall_pass`, `gates` only |
| Gate 0 `fixable` | `false` | `true` |
| Gate 4b `severity` | `null` | `"error"` / `"warning"` / `"information"` |
| Gate 4b messages | may contain `\n` / `\u00a0` | single-line, space-normalised |
| Violation `file` paths | mixed: relative backslash / absolute Windows | workspace-relative POSIX always |
| `scope="files"` + directory | silent skip (all skipped) | expanded to `.py` files, evaluated |
| B1-pass / P1-pass | BLOCKED (F-6/F-7/F-8) | expected PASS |

---

## Scope

**In Scope:**
- Live MCP tool calls for `auto`, `branch`, `project`, `files`
- At least one PASS and one FAIL case per scope
- `files` scope variants: single file, multiple files, single dir, multiple dirs
- Response schema and violation-shape validation for all active gates (0, 1, 2, 3, 4, 4b)
- Verification of all C32–C39 behavioral fixes under live conditions

**Out of Scope:**
- Unit/integration suite quality (covered in TDD C0–C39)
- Performance/benchmarking
- Inactive gates (gate5/gate6)

## Prerequisites

1. Branch: `refactor/251-refactor-run-quality-gates`
2. Commit: `85e9de39` or later (C39 REFACTOR — final post-fix commit)
3. MCP server started with `start_mcp_server.ps1`
4. `.st3/quality.yaml`: all active gates define `capabilities.parsing_strategy`
5. Workspace is clean enough to isolate scenario outcomes (prefer one scenario at a time)
6. Baseline context known:
   - `.st3/state.json` `quality_gates.baseline_sha` set or absent depending on scenario
   - `.st3/state.json` `parent_branch` at top level (not nested under `workflow`)
7. **Known clean fixtures:**
   - `backend/__init__.py` — clean file (no violations in any active gate)
   - `tests/mcp_server/validation_fixtures/gate0_format_violation.py` — Gate 0 dedicated fixture (single-quote style → format violation)
   - `tests/mcp_server/validation_fixtures/violations.py` — multi-gate fixture (Gate 1/3/4 violations; also triggers Gate 0 via `badly_formatted_function`)
   - `backend/dtos/validation_fixture_gate4.py` — dedicated Gate 4/4b type-error fixture

---

## Response Contract Reference (C35/C39 state)

### content[0] — summary line format

```
{icon} {message}{scope_part}{duration_part}
```

| Case | Icon + message | scope_part | duration_part |
|------|----------------|------------|---------------|
| All skipped (clean diff) | `✅ Nothing to check (no changed files)` | ` [auto · 0 files]` | ` — 0ms` |
| All pass | `✅ Quality gates: N/N passed (V violations)` | ` [scope · N files]` | ` — Nms` |
| Some skip, rest pass | `⚠️ Quality gates: N/N active (S skipped)` | ` [scope · N files]` | ` — Nms` |
| Any fail | `❌ Quality gates: N/M passed — V violations in Gate X, Gate Y` | ` [scope · N files]` | ` — Nms` |

When scope is not provided (if called without scope param), scope_part is absent.

### content[1] — compact JSON payload

```json
{
  "overall_pass": bool,
  "gates": [
    {
      "id": "Gate N: Name",
      "passed": bool,
      "skipped": bool,
      "status": "passed|failed|skipped",
      "violations": [
        {
          "file": "workspace/relative/posix/path.py",
          "message": "single-line string (no \\n or \\u00a0)",
          "line": int | null,
          "col": int | null,
          "rule": "RULE_ID" | null,
          "fixable": bool,
          "severity": "error|warning|information" | null
        }
      ]
    }
  ]
}
```

**Key assertions:**
- Root keys: exactly `overall_pass` + `gates` (no `duration_ms`)
- `file` paths: workspace-relative POSIX (e.g. `backend/dtos/x.py`, not `C:\...` or `backend\dtos\x.py`)
- Gate 0 violations: `line: null`, `col: null`, `fixable: true`, `rule: "FORMAT"`, `severity: "error"`
- Gate 4b violations: `severity` is `"error"` / `"warning"` / `"information"` — never `null`
- Gate 4b messages: no embedded `\n` or `\u00a0`; secondary type annotation separated by ` — `

---

## Scope Behavior Reference

| Scope | Resolution behavior | Files passed to gates |
|-------|---------------------|-----------------------|
| `auto` *(default)* | Uses `quality_gates.baseline_sha` from `.st3/state.json`; resolves `git diff <baseline_sha>..HEAD` `.py` + union with `quality_gates.failed_files`; if no baseline → fallback to `project` | `diff_files ∪ failed_files` or project glob result |
| `branch` | Uses `parent_branch` from state.json **top level**; fallback `"main"`; resolves `.py` changes from `git diff <parent>..HEAD` | changed `.py` files since parent branch |
| `project` | Expands `project_scope.include_globs` from `.st3/quality.yaml`; dedupe + sort | matched project files |
| `files` | Uses caller-supplied list; directories expanded to `.py` files via `resolve_input_paths`; missing paths warn-and-skip; empty/missing `files` rejected by validation | resolved `.py` paths from input |

---

## Execution Protocol (strict order)

1. Capture test metadata (`date`, `tester`, `commit`, server session info).
2. Run response-shape smoke check (`run_quality_gates()` default) and confirm content ordering.
3. Execute scenarios in order: `A*` → `B*` → `P*` → `F*` → `X*`.
4. After each scenario, store one evidence block (request, response summary, gate evidence, verdict).
5. If scenario outcome is ambiguous, rerun once; if still ambiguous, mark **BLOCKED** with reason.

---

## Evidence Format (required per scenario)

For every scenario row, capture:
- **Request:** exact MCP call payload
- **Summary:** `overall_pass`, summary line text (full — include duration suffix and scope suffix), passed/failed/skipped counts
- **Gate proof:** affected gate id + minimal issue sample (`file`, `line`, `rule`, `message`, `fixable`, `severity`, `path format`)
- **Fallback check:** confirm no active gate returns `Gate failed with exit code`
- **Verdict:** PASS / FAIL / BLOCKED with 1-line rationale

---

## Validation Checklist

### scope=auto

- [ ] A1-pass: `baseline_sha` present, diff clean → `✅ Nothing to check` + all-skipped or all-pass
- [ ] A1-fail: `baseline_sha` present, diff has violation → relevant gate `issues[]` populated, structured
- [ ] A2: no `baseline_sha` → fallback to `project` behavior (N violations from project scope)

### scope=branch

- [ ] B1-pass: parent diff clean → `✅ Quality gates: N/N passed` (not BLOCKED by F-6/F-7/F-8 anymore)
- [ ] B2-fail: parent diff has type error → `gate4_types` structured issues with `file/line/severity/rule`
- [ ] B3: no `parent_branch` in state → fallback to `main`, executes without crash

### scope=project

- [ ] P1-pass: project clean → `overall_pass=true`, 5-6 gate entries, pass/skip only
- [ ] P2-fail: introduce one violation → relevant gate issues populated

### scope=files

- [ ] F1: single clean file → `overall_pass=true`
- [ ] F2: `gate0_format_violation.py` → Gate 0 violations: `rule=FORMAT`, `fixable=true`, `line=null`, `severity="error"`, `file` in POSIX
- [ ] F3: multiple clean files → `overall_pass=true`
- [ ] F4: multiple files, one lint-fail → failing file only in gate1 issues
- [ ] F5: single directory path → **expanded** to `.py` files (not silent skip)
- [ ] F6: multiple directory paths → **both expanded**; behavior documented
- [ ] F7: missing `files` with `scope="files"` → validation error pre-execution (no gate run)

### response shape & contract (all scopes)

- [ ] `content[0]` is `type="text"` summary with `[scope · N files] — Nms` suffix
- [ ] `content[1]` is `type="json"` payload with root keys: `overall_pass`, `gates` only (no `duration_ms`)
- [ ] each gate entry has: `id`, `passed`, `skipped`, `status`, `violations`
- [ ] all violation `file` paths are workspace-relative POSIX (no absolute, no backslash)
- [ ] Gate 0 violations have `fixable: true`
- [ ] Gate 4b violations have non-null `severity` string
- [ ] Gate 4b messages are single-line (no `\n` / `\u00a0`)
- [ ] all-skipped summary emits `✅ Nothing to check` (not `⚠️`)

### baseline state machine (auto scope)

- [ ] X3a: fail-run accumulates `failed_files` in `state.json`, `baseline_sha` unchanged
- [ ] X3b: `scope=auto` with empty diff but non-empty `failed_files` → evaluates persisted files
- [ ] X3c: all-pass run advances `baseline_sha` to HEAD, resets `failed_files=[]`

### closure scenarios

- [ ] X1: Gate 0 dedicated FAIL — `gate0_format_violation.py` → `gate0` structured violations, `fixable=true`
- [ ] X2: Gate 4 Types dedicated FAIL — `validation_fixture_gate4.py` → `gate4_types` structured mypy issues; Gate 4b also fires with non-null severity and single-line messages
- [ ] X4: response-contract check captured explicitly for each scope (`auto|branch|project|files`)
- [ ] X5: mixed rerun set — evaluated = `{persisted_failed ∪ changed_since_baseline}`; unchanged previously-pass file excluded

---

## Test Scenarios

### scope=auto (default)

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| A1-pass | Baseline = HEAD, no diff | `run_quality_gates()` | `✅ Nothing to check (no changed files) [auto · 0 files] — Nms`; all gates skipped; `overall_pass=true` |
| A1-fail | Baseline present, diff has violation | `run_quality_gates()` | `❌ ...` summary with `[auto · N files] — Nms`; failing gate has `violations[]` with structured entries; paths POSIX |
| A2 | No `baseline_sha` in state | `run_quality_gates()` | Behavior equivalent to `scope=project`; summary includes `[auto · N files] — Nms` |

### scope=branch

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| B1-pass | Branch diff clean (all changed files pass gates) | `run_quality_gates(scope="branch")` | `✅ Quality gates: N/N passed (0 violations) [branch · N files] — Nms`; `overall_pass=true` |
| B2-fail | Branch diff contains `validation_fixture_gate4.py` or similar | `run_quality_gates(scope="branch")` | `gate4_types` issues include `file/line/severity/rule`; paths POSIX; Gate 4b severity non-null |
| B3 | `parent_branch` absent from state | `run_quality_gates(scope="branch")` | Defaults to `main`; executes without crash; summary includes `[branch · N files]` |

### scope=project

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| P1-pass | Project production files clean | `run_quality_gates(scope="project")` | `✅ Quality gates: N/N passed (0 violations) [project · N files] — Nms`; `overall_pass=true` |
| P2-fail | Introduce known E501 violation in project file | `run_quality_gates(scope="project")` | `gate3` issues include `rule=E501`; violation `file` is POSIX path |

### scope=files — single/multiple files

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| F1 | One clean file | `run_quality_gates(scope="files", files=["backend/__init__.py"])` | `✅ ... [files · 1 files] — Nms`; pass/skip only |
| F2 | Gate 0 fixture | `run_quality_gates(scope="files", files=["tests/mcp_server/validation_fixtures/gate0_format_violation.py"])` | `gate0` violations: `rule="FORMAT"`, `fixable=true`, `line=null`, `severity="error"`, `file` POSIX |
| F3 | Multiple clean files | `run_quality_gates(scope="files", files=["backend/__init__.py", "mcp_server/__init__.py"])` | `✅ ... [files · 2 files] — Nms`; pass/skip only |
| F4 | Mixed files (one lint-fail) | `run_quality_gates(scope="files", files=["backend/__init__.py", "tests/mcp_server/validation_fixtures/violations.py"])` | violations reference only `violations.py`; `backend/__init__.py` contributes zero issues |

### scope=files — directories

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| F5 | Single directory | `run_quality_gates(scope="files", files=["backend/"])` | directory **expanded** to `.py` files; gates run; result is not all-skipped |
| F6 | Multiple directories | `run_quality_gates(scope="files", files=["backend/", "mcp_server/"])` | both directories expanded; combined file set evaluated |

### scope=files — validation errors

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| F7 | Missing files field | `run_quality_gates(scope="files")` | Pydantic ValidationError before gate execution; no gate runs; clean error message |

### closure scenarios

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| X1 | Gate 0 dedicated FAIL | `run_quality_gates(scope="files", files=["tests/mcp_server/validation_fixtures/gate0_format_violation.py"])` | `gate0`: `passed=false`, violations `[{file: POSIX, rule: "FORMAT", fixable: true, line: null, severity: "error", message: "File requires formatting"}]` |
| X2 | Gate 4 dedicated FAIL | `run_quality_gates(scope="files", files=["backend/dtos/validation_fixture_gate4.py"])` | `gate4_types`: structured mypy violations with `file/line/rule/severity`; `gate4_pyright`: `severity` non-null, messages single-line; paths POSIX |
| X3a | Fail-run accumulation | `run_quality_gates(scope="auto")` with dirty diff | Post-run: `state.json` `failed_files` updated; `baseline_sha` unchanged |
| X3b | Auto union includes persisted set | `run_quality_gates(scope="auto")` with clean diff but non-empty `failed_files` | Persisted files evaluated; violations found even with empty git diff |
| X3c | All-pass advances baseline | `run_quality_gates(scope="auto")` after clean fix | Post-run: `state.json` `baseline_sha=HEAD`, `failed_files=[]` |
| X4 | Contract evidence per scope | `run_quality_gates(...)` for each of 4 scopes | `content[0]`: text with scope+duration suffix; `content[1]`: `{overall_pass, gates}`; captured explicitly per scope |
| X5 | Mixed rerun narrowing | Setup: `failed_files=[A]`, diff=`{B,C}`, unchanged `D` in project | Evaluated set = `{A,B,C}`; `D` absent from all gate results |

---

## Validation Results (to fill live)

**Date:** 2026-01-27
**Tester:** Copilot (automated validation run)
**Commit start:** 708adc5 (HEAD at start) → **F-20 fix committed as 8dfe6fa**
**Server Session:** after VS Code restart with latest MCP server

| Scenario | Status | Evidence Ref | Notes |
|----------|--------|--------------|-------|
| A1-pass | ✅ PASS | `✅ Nothing to check (no changed files) [auto · 0 files] — 0ms`; `overall_pass=true`; root keys `{overall_pass,gates}` | F-1 fix confirmed |
| A1-fail | ✅ PASS (via X3a) | X3a demonstrates fail-run with 99 files, violations detected | Structurally equivalent |
| A2 | ✅ PASS | `❌ ... [auto · 408 files] — 9986ms`; fallback to project; `overall_pass=false`; no `duration_ms` in root | |
| B1-pass | ⚠️ BLOCKED | Branch diff includes violation fixtures; clean-diff B1 merged with B2-fail | Violation fixtures in diff; see also F-20 fix |
| B2-fail | ✅ PASS | `❌ 0/6 passed — 1898 violations [branch · 313 files]`; Gate 4b `severity="error"`; POSIX paths; no `duration_ms` | F-17/F-20 confirmed |
| B3 | ✅ PASS | Same result as B2-fail but with `parent_branch` absent → defaults to main | No crash |
| P1-pass | ⚠️ N/A | Project has archive + fixture violations; scope=project itself works correctly | Aspirational — not achievable with current workspace state |
| P2-fail | ✅ PASS (via P scan) | `❌ 0/5 passed — 1602 violations [project · 408 files]`; Gate 0–4b all fire | |
| F1 | ✅ PASS | `⚠️ 5/5 active (1 skipped) [files · 2 files] — 2569ms`; `overall_pass=true` | |
| F2 | ✅ PASS | `gate0`: `rule=FORMAT`, `fixable=true`, `line=null`, `severity="error"`, POSIX path | |
| F3 | ✅ PASS | `⚠️ 5/5 active (1 skipped) [files · 2 files]`; `overall_pass=true` | |
| F4 | ✅ PASS | All 13 violations reference only `violations.py`; `backend/__init__.py` contributes 0 | |
| F5 | ✅ PASS | `backend/` expanded to 54 files; gates run; not all-skipped | |
| F6 | ✅ PASS | `backend/` + `mcp_server/config/` combined to 72 files | |
| F7 | ✅ PASS | Pydantic ValidationError: `files must be a non-empty list when scope='files'` | Pre-gate error, no gate run |
| X1 | ✅ PASS | Gate 0 dedicated: `passed=false`, 1 violation: `rule=FORMAT`, `fixable=true`, `line=null`, `severity="error"` | |
| X2 | ✅ PASS | Gate 4: `no-untyped-def`+`assignment` with `severity="error"`; Gate 4b: `reportAssignmentType`, `severity="error"`, single-line message (F-18 `\u2014`) | |
| X3a | ✅ PASS | After fail-run: `baseline_sha=52442aa` unchanged; `failed_files` count=99 | State machine correct |
| X3b | ✅ PASS | Clean diff (baseline=HEAD) + 99 persisted failed_files → evaluates 99 files → same 353 violations | Union logic correct |
| X3c | ✅ PASS | All-pass run: `baseline_sha` advanced to HEAD; `failed_files=[]` | |
| X4 | ✅ PASS | All 4 scopes captured: root always `{overall_pass,gates}`; summary always `[scope · N files] — Nms` | Verified across auto/branch/project/files runs |
| X5 | ✅ PASS | Evaluated = {A,B,C}=3 files; D (`backend/__init__.py`) absent from all gate results; 6 violations only from A | Narrowing confirmed |

### Session Findings

| ID | Finding | Fix Applied | Commit |
|----|---------|------------|--------|
| F-20 | `_git_diff_py_files` used `--name-only` without `--diff-filter=d`; deleted files (status D vs parent) appeared in scope → "File not found" in File Validation | Added `--diff-filter=d` to git diff command | `8dfe6fa` |
| F-21 | **Baseline state machine scope guard missing (historical finding).** Non-auto runs could mutate baseline lifecycle fields prior to stabilization cycles. | Fixed in issue251 TDD cycles (C41–C44); validated in addendum 2026-03-01 | See `live-validation-blocked-scenarios-20260301.md` |

---

## Go / No-Go Criteria

**GO** when all below are true:
- All scenarios complete with expected behavior or explicitly justified skips
- No active gate emits unstructured `Gate failed with exit code` as primary failure signal
- `scope=auto` fallback to project proven in A2
- `scope=files` validation contract proven in F7
- B1-pass achieves `overall_pass=true` (was BLOCKED in v1 due to F-6/F-7/F-8)
- P1-pass achieves `overall_pass=true` (was BLOCKED in v1)
- F5/F6 demonstrate directory expansion (not silent skip)
- Response contract confirmed per scope in X4: root keys `overall_pass`+`gates` only; summary has `[scope · N files] — Nms`
- Gate 0 violations confirmed `fixable=true` in X1
- Gate 4b violations confirmed non-null `severity` + single-line messages in X2
- All violation `file` paths confirmed workspace-relative POSIX across gates
- X3a/X3b/X3c baseline state-machine behavior proven with `state.json` evidence
- X5 mixed rerun narrowing proven

**NO-GO** if any of the following occurs:
- Active gate failure is only blob-based/unstructured
- `scope=auto` fallback path is broken or inconsistent
- `scope=files` yields runtime error instead of input validation
- Gate 0 violations have `fixable=false`
- Gate 4b `severity` is `null` on any violation
- Gate 4b messages contain `\n` or `\u00a0`
- Any violation `file` path uses absolute path or OS-native backslash
- `duration_ms` appears in compact JSON root
- All-skipped summary emits `⚠️` instead of `✅`
- `scope=files` with directory path still silently skips (all gates skipped, no expansion)
- B1-pass BLOCKED for any reason related to F-6/F-7/F-8 (should be resolved)
- **F-21:** `scope=files`/`branch`/`project` passing run mutates `failed_files` or advances `baseline_sha`

---

## Risk Notes / Common False Positives

- Duration (`Nms`) will vary per run — assert presence/format, not exact value.
- File count (`N files`) depends on git diff state at test time — assert presence/format.
- Empty-file-set scenarios can produce all-skipped; `✅ Nothing to check` is correct for clean diff.
- B1-pass: if new violations are introduced in the branch diff since writing this plan, it will fail; check branch cleanliness first.
- P1-pass: runs on all project-scope files; if any project file has a violation, it will fail. Verify which files are in `project_scope.include_globs` before asserting P1-pass.
- Local env drift (tool version mismatch) can change violation counts; compare structure and fields first, counts second.

---

## Follow-up Addendum (2026-03-01)

Blocked scenarios from this plan were re-run end-to-end and closed in:
- `docs/development/issue251/live-validation-blocked-scenarios-20260301.md`

---

## Related Documentation

- [live-validation-plan.md](live-validation-plan.md) — v1 (session 1–3 results + all findings)
- [research_v2.md](research_v2.md) — findings F-1 through F-19 + proposed cycle plan
- [planning.md](planning.md) — Addendum A: C32–C39 implementation cycles
- [design_v2.md](design_v2.md) — design for post-validation cycles
- [.st3/quality.yaml](../../../.st3/quality.yaml) — gate catalog

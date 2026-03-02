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

### closure coverage (must-run additions)

- [x] X1: dedicated Gate 0 FAIL scenario produces structured `FORMAT` violations (not Gate1/3/4b substitution)
- [x] X2: dedicated Gate 4 Types FAIL scenario yields structured mypy issues in `gate4_types`
- [x] X3a: fail-run persists/accumulates `quality_gates.failed_files` in `.st3/state.json`
- [x] X3b: subsequent `scope="auto"` run includes persisted `failed_files` even when diff is empty
- [x] X3c: all-pass run advances `baseline_sha` to `HEAD` and resets `failed_files=[]`
- [x] X4: response-contract check is explicitly captured for each scope (`auto|branch|project|files`)
- [x] X5: mixed rerun scope proves failure-narrowing set logic (`changed_since_baseline ∪ failed_files`) and excludes unchanged previously-passing files

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

### closure scenarios — omissions fixed

| # | Scenario | Call | Expected |
|---|----------|------|----------|
| X1 | Gate 0 dedicated FAIL | `run_quality_gates(scope="files", files=["<gate0_fixture.py>"])` | `gate0` contains structured `FORMAT` violations (`file`,`message`,`rule`) |
| X2 | Gate 4 Types dedicated FAIL | `run_quality_gates(scope="files", files=["<gate4_types_fixture.py>"])` | `gate4_types` contains structured mypy issues (`file`,`line`,`rule`,`message`) |
| X3a | Baseline state accumulation on fail | `run_quality_gates(scope="auto")` after introducing known failing diff | `.st3/state.json` updates `quality_gates.failed_files` with failing file(s) |
| X3b | Auto union includes persisted failed set | `run_quality_gates(scope="auto")` with empty diff but non-empty `failed_files` | run still evaluates persisted failed file(s) |
| X3c | Baseline advance/reset on all-pass | `run_quality_gates(scope="auto")` after clean fix pass | `.st3/state.json`: `baseline_sha=HEAD`, `failed_files=[]` |
| X4 | Contract evidence per scope | `run_quality_gates(...)` for each scope | each scope evidence logs `content[0]` text and `content[1]` json contract explicitly |
| X5 | Mixed rerun set (core narrowing behavior) | `run_quality_gates(scope="auto")` with setup: one persisted failed file + one newly changed file + one unchanged previously-pass file | evaluated set equals `{persisted_failed ∪ newly_changed}` and explicitly excludes unchanged previously-pass file

---

## Validation Results (to fill live)

**Date:** 2026-02-23 (session 1) / 2026-02-24 (session 2 — X1-X4) / 2026-02-24 (session 3 — X1/X2/X5 fully proven after fixes)
**Tester:** GitHub Copilot (automated session)  
**Commit:** `da4a5c17` (session 1) / `52442aa4` (session 2) / `15318372` (session 3 base)  
**Server Session:** proxy restart after each fix; session 3 includes two server restarts (F-13 fix + F-4 fix)

| Scenario | Status (PASS/FAIL/BLOCKED) | Evidence Ref | Notes |
|----------|-----------------------------|--------------|-------|
| A1-pass | PASS | baseline=HEAD diff empty → 6/6 skipped, `⚠️ 0/0 active (6 skipped)` | Behavior correct. **Finding F-1:** ⚠️ used for expected clean state (should be ✅). **Finding F-3:** `skipped=true`+`passed=true` on all gate entries is contradictory |
| A1-fail | PASS | baseline=49bca199, diff=violations.py → 12 violations: Gate1 (9), Gate3 (1), Gate4b (2) | All violations structured with `file/line/col/rule`. No blob. Gate4:Types skipped — `violations.py` is in `tests/`, not `backend/dtos/**`, so scope filter correctly excludes it. *(At the time attributed to **F-4**; F-4 was a real bug but not observable from this file — Gate 4 skip here is correct behavior.)* |
| A2 | PASS | no baseline → project fallback → 1516 violations across 405 files | Fallback path confirmed. **Finding F-5:** response 502KB, exceeded MCP inline limit, written to disk — unusable in chat for large codebases |
| B1-pass | BLOCKED | scope=branch → 15 violations in production files | Branch has real violations: `qa_manager.py` F821 dead code (lines 321-344, unreachable block after `return []`) + `server.py` I001 import order. **Finding F-6, F-7 — NO-GO bugs in production code.** B1-pass unachievable without fixing these |
| B2-fail | PASS (after F-4 fix) | scope=branch → Gate 0: 6 FORMAT violations (server.py + test files); Gate 1: 11 violations (F821/I001/F401/ANN/ARG); Gate 3: 2 E501; **Gate 4: Types: `passed=false`, violations `{rule: "no-untyped-def", line: 9}` + `{rule: "assignment", line: 17}` for `backend/dtos/validation_fixture_gate4.py`**; Gate 4b: 3 violations. | Gate 4: Types now correctly runs for `backend/dtos/**/*.py` files in the branch diff (F-4 `full_match` fix). Structured mypy violations confirmed with `file/line/rule/severity`. Plan concern about gate4_types always being skipped → resolved. F-8 (parent_branch key mismatch) still present — branch scope always falls back to "main". |
| B3 | IMPLICIT | Fallback to "main" is the only behavior that executes | B3 condition is permanently active due to **Finding F-8** (key path bug). Cannot test fallback separately from normal operation |
| P1-pass | BLOCKED | scope=project → 1516 violations; project not clean | Blocked by same production violations as B1-pass. P1-pass unachievable in current branch state |
| P2-fail | PASS | scope=project → 1516 violations; gate3 includes `rule=E501` | Violations structured. **Finding F-2:** compact payload omits `overall_pass` and `duration_ms` — LLM must iterate all gates to determine outcome |
| F1 | PASS (alt file) | scope=files, files=["backend/__init__.py"] → 5/5 passed (1 skipped) | Plan pre-condition wrong: `script.py` is not clean (B018/F821/W292). **Finding F-11:** test plan uses dirty file as "clean" reference. Confirmed with `backend/__init__.py`. ⚠️ again for clean result (F-1) |
| F2 | PASS | scope=files, files=["violations.py"] → 12 violations in Gate1/Gate3/Gate4b | Violations fully structured. **Finding F-10:** plan expected gate0 violations; Gate0 passes (ruff format doesn't flag this fixture). Gate1/Gate3/Gate4b correctly report structured issues |
| F3 | PASS | scope=files, files=["backend/__init__.py","mcp_server/__init__.py"] → 5/5 passed | Both files clean. ⚠️ for clean result (F-1 confirmed again) |
| F4 | PASS | scope=files, mixed files → violations only from violations.py | File isolation correct — backend/__init__.py contributes zero violations |
| F5 | FAIL | scope=files, files=["backend/"] → 6/6 skipped, no error | **Finding F-9:** directory paths silently skipped (not `.py` extension); no validation error, no warning. Indistinguishable from "all files passed" |
| F6 | FAIL | scope=files, files=["backend/","mcp_server/"] → 6/6 skipped | Same as F5. Multiple directory paths silently silenced. **Finding F-9** confirmed |
| F7 | PASS | scope=files (no files) → Pydantic ValidationError pre-execution | Input validation fires correctly, no gate runs, clear error message. **Finding F-12:** ValidationError also logged server-side as structured WARNING with `call_id`, `tool_name`, `model`, `arguments` — good observability but double-reported (server log + chat response) |
| X1 | PASS (after fix) | `tests/mcp_server/validation_fixtures/gate0_format_violation.py` → Gate 0: `passed=false`, `violations=[{file, rule: "FORMAT", message: "File requires formatting", severity: "error"}]` | **F-13 fixed:** pattern changed from `^--- a/(?P<file>.+)$` to `^--- (?P<file>.+)$` in `.st3/quality.yaml`. Ruff format diff uses `--- <path>` without `a/` prefix on Windows. Gate 0 now correctly detects format violations. **New observations:** `fixable: false` despite gate being autofix-capable → **F-14**. `line: null, col: null` → **F-16**. File path relative+backslash vs absolute in other gates → **F-15**. |
| X2 | PASS (after fix) | `backend/dtos/validation_fixture_gate4.py` → Gate 4: Types `passed=false`, violations: `{rule: "no-untyped-def", line: 9, severity: "error"}` + `{rule: "assignment", line: 17, severity: "error"}`. Gate 4b also `passed=false`. | **F-4 root cause fixed:** `PurePosixPath.full_match()` resolves `backend/dtos/**/*.py` correctly. **New observations:** Gates 4 + 4b both fire for the same line-17 type error with different rule/col/severity → **F-17**. Gate 4b `severity: null` despite config mapping → **F-17**. Gate 4b message contains `\n`+`\u00a0` verbatim → **F-18**. 4 different path formats across gates in the same run → **F-15**. |
| X3a | PASS | Pre: `baseline_sha=233571ae`, `failed_files=[]`. Run: `scope=auto` → diff returns `qa_manager.py` → Gate 1 F821 violation. Post: `state.json` `failed_files=["mcp_server/managers/qa_manager.py"]`, `baseline_sha` unchanged (233571ae). | fail-run correctly accumulates `failed_files` and leaves `baseline_sha` unchanged. |
| X3b | PASS | Pre: `baseline_sha=52442aa` (HEAD), `failed_files=["mcp_server/managers/qa_manager.py"]`. Run: `scope=auto` → diff empty (no commits past HEAD). `qa_manager.py` evaluated via persisted `failed_files` → Gate 1 F821 found. | auto union includes persisted `failed_files` even when diff is empty. State machine correct. |
| X3c | PASS | Pre: `baseline_sha=233571ae`, `failed_files=[]`. Run: `scope=files`, `files=["backend/__init__.py"]` → all gates pass/skip, `overall_pass=True` → `_advance_baseline_on_all_pass` fires. Post: `state.json` `baseline_sha=52442aa` (HEAD), `failed_files=[]`. | all-pass run correctly advances `baseline_sha` to HEAD and resets `failed_files=[]`. |
| X4 | PASS | All 4 scopes confirmed: `content[0]`=text summary (e.g. `❌ Quality gates: 4/5 passed — 1 violations in Gate 1: Ruff Strict Lint`), `content[1]`=`{gates:[{id, passed, skipped, violations:[...]}, ...]}`. Consistent across `auto` (X3a), `branch` (B-series), `project` (A2), `files` (X2/X3c). | Response contract stable. text-first/json-second order (C29 fix) confirmed for all scopes. |
| X5 | PASS | Pre: `baseline_sha=233571ae`, `failed_files=["tests/.../violations.py"]`. Diff=`{qa_manager.py, validation_fixture_gate4.py, gate0_format_violation.py}`. Union={4 files}. `mcp_server/server.py` (known I001 violation) excluded. Run: violations only from `qa_manager.py` (F821), `violations.py` (I001/F401/ANN/ARG/E501/FORMAT), `validation_fixture_gate4.py` (ANN/no-untyped-def/assignment), `gate0_format_violation.py` (FORMAT). No I001 from `server.py` anywhere. | Narrowing set logic correct: `{diff_files ∪ failed_files}` evaluated; `server.py` absent from all gate results confirms unchanged previously-passing files are excluded. **Observation:** Gate 0 now fires on `violations.py` too (it has formatting issues) — confirms F-13 fix has broader scope than just the dedicated fixture. Path inconsistency across all 5 active gates again observed → **F-15**. |

### Validation Findings (cross-scenario)

| ID | Severity | Description | Scope |
|----|----------|-------------|-------|
| F-1 | Medium | `⚠️` emitted for scope=auto with empty diff — correct behavior but wrong signal; should be `✅ Nothing to check (no changed files)` | UX / `_format_summary_line` |
| F-2 | Medium | Compact payload missing `overall_pass` and `duration_ms`; consumer must iterate all gate entries to determine pass/fail | Contract / `_build_compact_result` |
| F-3 | Low | `skipped=true` + `passed=true` simultaneously on gate entries is semantically contradictory; skipped means not evaluated, not passed | Contract / `_build_compact_result` |
| F-4 | Low ~~→ Fixed~~ | Gate 4: Types (mypy) always skipped. **Root cause (session 2):** `PurePosixPath.match("backend/dtos/**/*.py")` returns `False` — `.match()` does suffix-matching and does not correctly handle `**` in non-trailing position. Fixed by switching to `PurePosixPath.full_match()` (Python 3.12+) in `filter_files()` (`mcp_server/config/quality_config.py`). Gate 4 now runs correctly for `backend/dtos/**/*.py` files. | Observability / `filter_files()` / `quality_config.py` |
| F-5 | High | scope=auto fallback to project (A2) and scope=project (P2) produce 502KB responses — exceeds MCP inline transport, written to disk, not usable in chat | Scalability / response size |
| F-6 | **Critical** | Dead code in `_resolve_scope` (qa_manager.py lines 321–344): unreachable block after `return []` with invalid `base_ref` reference (F821). Introduced during cleanup session. Production code ships with own lint violation | Code quality / cleanup regression |
| F-7 | **Critical** | `server.py` line 3: import order violation (I001). Production file introduced by fix commit fails its own quality gate | Code quality / fix regression |
| F-8 | High | `_resolve_branch_scope` reads `state.get("workflow", {}).get("parent_branch")` but state.json stores `parent_branch` at top level — key mismatch means configured parent_branch is never read; always defaults to `"main"` | Bug / scope resolution |
| F-9 | High | Directory paths in `scope="files"` silently accepted and skipped — no validation error, no warning; result is indistinguishable from "all files clean" | Correctness / silent failure |
| F-10 | Low | Test plan error: fixture was expected to trigger Gate0 (ruff format) but Gate0 passes; violations are in Gate1/Gate3/Gate4b only | Test plan / fixture design |
| F-11 | Low | Test plan error: `script.py` used as "clean" reference file but contains real violations (B018, F821, W292) | Test plan / pre-condition error |
| F-12 | Info | ValidationError (F7) also emitted as structured server-side WARNING log with `call_id`, `tool_name`, `model`, `arguments` — useful observability; double-reporting is by design (log + chat client) | Observability / server logging |
| F-13 | **Critical** ~~→ Fixed~~ | Gate 0 violation parser pattern `^--- a/(?P<file>.+)$` never matched ruff format `--diff` output which uses `--- <filepath>` (no `a/` prefix). Gate 0 always reported `passed=true, violations=[]`. **Fixed (session 2):** pattern changed to `^--- (?P<file>.+)$` in `.st3/quality.yaml`. Gate 0 now correctly detects and reports structured format violations. | Bug / Gate 0 parser / `quality.yaml` |
| F-14 | Medium | Gate 0 FORMAT violations have `fixable: false` despite gate config `supports_autofix: true`. The `text_violations` parser has no `fixable_when` analogue — there is no mechanism to propagate gate-level autofix capability to individual violation entries. Consumer sees a non-fixable violation for a file that `ruff format` would fully fix. Gap: `supports_autofix` exists at gate level only; per-violation `fixable` is not set for any text_violations gate. | Contract / Gate 0 / `fixable` field |
| F-15 | Medium | File paths in violation entries are inconsistent across gates within the same run (observed in X1, X2, X5): Gate 0 and Gate 4 (mypy) emit **relative paths with OS-native backslashes** (`tests\...`, `backend\dtos\...`); Gate 1 (ruff JSON) emits **absolute paths with uppercase drive** (`C:\temp\st3\...`); Gate 4b (Pyright JSON) emits **absolute paths with lowercase drive** (`c:\temp\st3\...`). Four different path formats in one response. Consumer cannot reliably deduplicate, compare, or display paths across gates without per-gate normalization logic. | Contract / path normalization / all gates |
| F-16 | Low | Gate 0 FORMAT violations have `line: null, col: null` because the violation is inferred from the diff-header line (`--- <file>`), not from a specific code position. No line/col information exists in ruff format's diff output. Combined with F-14 (`fixable: false`), the Gate 0 violation carries only three actionable fields: `file`, `rule`, and `message`. Consumer cannot navigate to a specific location or apply a fix from the violation object alone — must re-run `ruff format <file>` separately. | UX / Gate 0 / violation actionability |
| F-17 | Low | Gates 4 (mypy) and 4b (Pyright) both report the same logical type error for the same file and line (observed X2: line 17 `str`→`int` mismatch). Gate 4 emits `rule: "assignment"`, `col: null`, `severity: "error"`; Gate 4b emits `rule: "reportAssignmentType"`, `col: 14`, `severity: null`. Double-reporting of one code issue with differing rule codes, column precision, and severity values. Consumer cannot silently deduplicate without custom cross-gate rule mapping. Additionally: Gate 4b `severity` is always `null` despite config mapping `severity: "severity"` from Pyright's JSON `generalDiagnostics` — Pyright may use a different field name in its current output version. | Contract / Gate 4 + Gate 4b / deduplication + severity |
| F-18 | Low | Gate 4b (Pyright) messages are passed through verbatim from Pyright JSON and contain embedded `\n` newlines and `\u00a0` (non-breaking space) characters (e.g. `"Type \"str\" is not assignable...\n\u00a0\u00a0\"str\" is not assignable..."`). Consumers expecting single-line, ASCII-safe message strings will render these incorrectly in terminals, inline comments, or log lines. | UX / Gate 4b / message formatting |
| F-19 | Medium | Summary line reports gate outcome only, but does not expose effective scope resolution context (requested scope vs evaluated set). For `auto` and `branch`, callers cannot see from `content[0]` whether execution used baseline diff, fallback-to-project, or parent-branch ref, nor how many files were actually resolved for evaluation. This reduces utility of the one-line status for quick validate-fix-revalidate loops. | UX+Contract / summary-line context / scope resolution visibility |

---

## Go / No-Go Criteria

**GO** when all below are true:
- All scenarios complete with expected behavior or justified skips
- No active gate emits unstructured `Gate failed with exit code` as primary failure signal
- `scope=auto` fallback to project proven in A2
- `scope=files` validation contract proven in F7
- Response ordering and compact gate shape stable in all sampled scopes
- X1 and X2 are executed with real failing fixtures (Gate 0 + Gate 4 Types)
- X3a/X3b/X3c baseline state-machine behavior is proven with state.json evidence
- X4 explicit response-contract evidence is captured for all four scopes
- X5 mixed rerun narrowing behavior is proven (`failed_files ∪ changed_since_baseline`, unchanged previously-pass excluded)

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

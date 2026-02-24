<!-- c:\temp\st3\docs\development\issue251\research_v2.md -->
<!-- template=research version=8b7bb3ab created=2026-02-24T17:07Z updated= -->
# Post-Validation Rerun Research — Findings F-1..F-18

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-24

---

## Purpose

Provide a structured basis for the planning phase to define new TDD cycles that address all validation blockers and response-quality issues found during post-refactor validation.

## Scope

**In Scope:**
Findings F-1 through F-18 from docs/development/issue251/live-validation-plan.md. Code in mcp_server/managers/qa_manager.py, mcp_server/config/quality_config.py, mcp_server/server.py, .st3/quality.yaml. Response contract fields: overall_pass, duration_ms, passed, skipped, fixable, file paths, message content.

**Out of Scope:**
TDD cycles C0–C31 (already completed). Gate 5/6 (pytest/coverage) — already removed. Performance optimisation. New gate types. Documentation phase obligations.

## Prerequisites

Read these first:
1. docs/development/issue251/live-validation-plan.md — all 18 findings with evidence
2. docs/development/issue251/research.md — original F1–F15 findings and architecture decisions
3. mcp_server/managers/qa_manager.py — current production code
4. mcp_server/config/quality_config.py — filter_files, GateScope, CapabilitiesMetadata
5. .st3/quality.yaml — gate catalog including gate0 pattern, gate4 scope globs
6. mcp_server/server.py — I001 import order violation
---

## Problem Statement

Live validation of the refactored run_quality_gates tool (issue #251, cycles C0–C31) produced 18 cross-scenario findings. Two bugs were fixed in-session (F-4, F-13). The remaining 16 findings span code quality regressions in production files (F-6, F-7), scope resolution bugs (F-8, F-9), response contract gaps visible to both agents and human users (F-2, F-3, F-14, F-15, F-16, F-17, F-18), and observability/UX issues (F-1, F-18). B1-pass and P1-pass remain blocked. A targeted set of additional TDD cycles is required before the branch can reach GO status.

## Research Goals

- Group all 18 validation findings by root cause and impact cluster
- Distinguish already-fixed findings (F-4, F-13) from open ones
- For each open finding: identify the exact file/function/config to change and the minimal fix
- Determine which findings affect agent consumers vs human users vs both
- Produce a prioritised list of additional TDD cycles (C32+) with explicit acceptance criteria
- Identify which findings can be resolved in one cycle and which require independent cycles

---

## Background

Issue #251 refactored run_quality_gates across 31 TDD cycles. The refactor introduced config-driven parsing, a 4-mode scope system, a baseline state machine, and a structured ViolationDTO contract. Post-refactor live validation revealed that two critical bugs were injected during cleanup (F-6: dead code with F821, F-7: I001 in server.py), two bugs were pre-existing from before the refactor (F-13: wrong Gate 0 diff prefix, F-4: PurePosixPath.match vs full_match for ** globs) — both fixed in-session. The remaining open findings are structural gaps in the response contract and scope resolution that were not covered by the TDD test suite.

---

## Findings

> All finding references (F-1..F-18) trace back to the evidence table in
> [live-validation-plan.md](live-validation-plan.md).
> Original research findings (F1–F15, no dash) are in [research.md](research.md) and relate to
> the C0–C31 TDD cycles only.

### Finding overview by cluster

| Cluster | Findings | Status | Blocks GO? |
|---------|----------|--------|------------|
| A — Code quality regressions | F-6, F-7 | Open | ✅ YES |
| B — Scope resolution bugs | F-8, F-9 | Open | F-8: B1-pass/P1-pass blocked; F-9: silent-fail risk |
| C — Response contract (agent-facing) | F-2, F-3, F-14, F-15, F-17 | Open | Partially — F-2 blocks reliable pass-detection |
| D — Response clarity & UX | F-1, F-16, F-18 | Open | No, medium priority |
| E — Fixed in-session | F-4, F-13 | **Fixed** | N/A |
| F — Non-actionable observations | F-5, F-10, F-11, F-12 | Noted | No |

---

## Investigation A: Code Quality Regressions (F-6, F-7)

**Findings:** [F-6](live-validation-plan.md) · [F-7](live-validation-plan.md)  
**Severity:** Critical (both)  
**Blocks GO:** Yes — branch cannot pass its own quality gates

### F-6 — Dead code block in `_resolve_scope` (F821 `base_ref` undefined)

**File:** `mcp_server/managers/qa_manager.py` lines 321–344  
**Root cause:** During cleanup of a prior debug session, a code block that was meant to be
removed was left unreachable after a `return []` statement. The block references a local
variable `base_ref` that does not exist in the enclosing scope, producing an F821
(undefined name) ruff violation. The block never executes at runtime but the lint gate
fails on it.

**Fix:** Delete lines 321–344 (the unreachable block). No logic is lost — the `return []`
before it is the intended termination path.

**Acceptance criterion:** `ruff check mcp_server/managers/qa_manager.py` reports zero F821
violations. Existing unit tests for `_resolve_scope` continue to pass.

**Affected files:** `mcp_server/managers/qa_manager.py`

---

### F-7 — Import order violation in `server.py` (I001)

**File:** `mcp_server/server.py` line 3  
**Root cause:** A fix commit rearranged imports in `server.py` without running ruff's import
sorter. The import block is now unsorted, producing an I001 violation that the branch's own
Gate 2 (Imports) flags on every `scope=branch` run.

**Fix:** Run `ruff check --fix --select=I001 mcp_server/server.py` or manually reorder the
imports to match ruff's expected sort order.

**Acceptance criterion:** `ruff check --select=I001 mcp_server/server.py` exits 0.

**Affected files:** `mcp_server/server.py`

---

### Proposed cycle

Both F-6 and F-7 are single-file cleanups with no logic change. They can be resolved in a
single `chore` cycle (no RED phase needed — they are pre-existing failures, not new
behaviour).

**Proposed cycle C32:** Remove dead code block (F-6) + fix import order (F-7).
Exit criteria: `scope=branch` run no longer emits F821 or I001 from production files.
B1-pass and P1-pass unblocked.

---

## Investigation B: Scope Resolution Bugs (F-8, F-9)

**Findings:** [F-8](live-validation-plan.md) · [F-9](live-validation-plan.md)  
**Severity:** F-8 High · F-9 High

### F-8 — `_resolve_branch_scope` reads wrong key path for `parent_branch`

**File:** `mcp_server/managers/qa_manager.py` → `_resolve_branch_scope`  
**Root cause:** The code does:
```python
state.get("workflow", {}).get("parent_branch")
```
But `state.json` stores `parent_branch` at the **top level**, not under a `"workflow"` key:
```json
{
  "parent_branch": "main",
  "branch": "refactor/251-...",
  ...
}
```
The lookup always returns `None`, causing unconditional fallback to `"main"`. The configured
`parent_branch` from `state.json` is silently ignored for the lifetime of the branch. The
fallback to `"main"` happens to produce a working result when the parent branch IS main, but
will silently produce wrong scope on feature branches derived from non-main parents (e.g.
epic branches).

**Impact on consumers:** Agent and human see scope=branch results calculated against `main`
regardless of the actual configured parent. No error, no warning.

**Fix:**
```python
# Before
parent = state.get("workflow", {}).get("parent_branch") or "main"
# After
parent = state.get("parent_branch") or "main"
```

**Acceptance criterion:**
- Unit test: when `state.json` has `parent_branch: "epic/76-quality-gates"`, `_resolve_branch_scope` calls `_git_diff_py_files("epic/76-quality-gates")`.
- Unit test: when `state.json` has no `parent_branch`, fallback to `"main"` occurs.
- B3 scenario (explicit fallback) now tests a genuinely distinct code path.

**Affected files:** `mcp_server/managers/qa_manager.py`

---

### F-9 — Directory paths in `scope="files"` silently skipped with no error

**File:** `mcp_server/managers/qa_manager.py` → `_files_for_gate` / input processing  
**Root cause:** The file list is forwarded verbatim to gates. Gates filter by `.py` extension
(via `capabilities.file_types`). A path like `"backend/"` has no extension → filtered out
→ zero files evaluated → all gates skip → result is `⚠️ 5/5 active (1 skipped)`,
indistinguishable from a clean run. No validation step rejects non-`.py` paths.

**Impact on consumers:** An agent or user passing `files=["backend/"]` receives a false
"all passed" signal. This is a correctness bug — silent data loss at the input layer.

**Fix options:**

1. **Pydantic validation** (preferred): in the `RunQualityGatesInput` model, add a
   `@field_validator("files")` that rejects any path not ending in `.py` (or not being an
   existing file). Produces a structured `ValidationError` pre-execution, consistent with
   how missing `files` on `scope="files"` is already handled (F7 scenario: PASS).

2. **Runtime warning**: in `_files_for_gate`, if the input list is non-empty but `eligible`
   is empty after filtering, emit a structured warning in the gate result rather than silently
   skipping.

Option 1 is preferred because it fails fast before any gate runs and is consistent with
existing input validation behaviour. Option 2 is a fallback if changing the Pydantic model
causes downstream test churn.

**Acceptance criterion:**
- `run_quality_gates(scope="files", files=["backend/"])` returns a ValidationError or a
  structured warning — **never** a clean-gates-passed result.
- `run_quality_gates(scope="files", files=["backend/__init__.py"])` continues to work.

**Affected files:** `mcp_server/tools/quality_tools.py` (Pydantic model) or
`mcp_server/managers/qa_manager.py` (runtime warning path)

---

### Proposed cycles

**Proposed cycle C33:** Fix `_resolve_branch_scope` key path (F-8).
Small targeted fix with unit tests.

**Proposed cycle C34:** Validate `files` list rejects non-`.py` paths (F-9).
Pydantic validator + unit + integration tests.

---

## Investigation C: Response Contract Gaps (F-2, F-3, F-14, F-15, F-17)

**Findings:** [F-2](live-validation-plan.md) · [F-3](live-validation-plan.md) · [F-14](live-validation-plan.md) · [F-15](live-validation-plan.md) · [F-17](live-validation-plan.md)  
**Severity:** F-2 Medium · F-3 Low · F-14 Medium · F-15 Medium · F-17 Low  
**Audience:** Primarily **agent consumers** — programmatic parsers of `content[1]` JSON

---

### F-2 — Compact payload missing `overall_pass` and `duration_ms`

**File:** `mcp_server/managers/qa_manager.py` → `_build_compact_result`  
**Root cause:** The compact result builder explicitly omits top-level `overall_pass` and
`duration_ms` fields. An agent must iterate all gate entries, check each `passed` field, and
infer the overall outcome — 3–6 conditional checks instead of one boolean read.

**Consumer impact (agent):** Cannot determine pass/fail in a single field lookup. Any
agent that short-circuits on `payload["overall_pass"]` will raise `KeyError`. This is a
contract violation — the tool's text summary (`content[0]`) carries pass/fail signal but the
JSON payload does not.

**Consumer impact (human):** None visible — the summary line in `content[0]` shows ❌/✅.

**Fix:** Add `overall_pass: bool` and `duration_ms: int` as top-level fields in the compact
result dict returned by `_build_compact_result`. Both values are already computed before
`_build_compact_result` is called.

**Acceptance criterion:** `content[1]["overall_pass"]` exists and matches the inferred
outcome from iterating `gates[].passed`. Contract test asserts both fields present and
correct for PASS, FAIL, and all-skipped runs.

**Affected files:** `mcp_server/managers/qa_manager.py` → `_build_compact_result`

---

### F-3 — `skipped: true` + `passed: true` semantically contradictory

**File:** `mcp_server/managers/qa_manager.py` → `_build_compact_result` / gate entry serialisation  
**Root cause:** When a gate is skipped, both `passed: true` and `skipped: true` are set.
Semantically these are contradictory: "passed" implies evaluation occurred and succeeded;
"skipped" means evaluation did not occur. An agent checking `gate.passed == true` will
incorrectly count skipped gates as passed.

**Consumer impact (agent):** Agents counting `passed` gates get a higher count than the
number of actually-evaluated gates. Agents relying on `gate.passed` as "gate evaluated and
succeeded" get wrong results for runs with all-skipped outcomes.

**Fix options:**

1. **Preferred:** When `skipped: true`, set `passed: null` (or omit `passed`). Consumers
   must check `skipped` first, then `passed`.

2. **Alternative:** Add a `status` enum field: `"passed" | "failed" | "skipped"`. This is
   the most explicit contract. Existing `passed`/`skipped` booleans can remain for backward
   compat during a transition period.

Option 2 creates forward compatibility; option 1 is a breaking change to the `passed` field
semantics. Recommend option 2.

**Acceptance criterion:** A skipped gate entry has `status: "skipped"` and `passed: true`
is not asserted as "gate passed evaluation". Contract tests updated.

**Affected files:** `mcp_server/managers/qa_manager.py` → gate result building

---

### F-14 — `fixable: false` on Gate 0 violations despite `supports_autofix: true`

**File:** `mcp_server/managers/qa_manager.py` → `_parse_text_violations` /
`.st3/quality.yaml` gate0 config  
**Root cause:** The `json_violations` parser supports `fixable_when: "fix/applicability"` —
a config key that resolves a per-violation fixable flag from a field in the JSON output.
The `text_violations` parser has **no equivalent mechanism**. It produces violations with
`fixable: false` unconditionally. Gate 0 config has `supports_autofix: true` at the gate
level, but this is never propagated to the individual violation entries.

**Consumer impact (agent):** An agent that follows the `fixable` flag to decide whether to
run autofix will skip `ruff format` because Gate 0 violations are marked `fixable: false`.
The autofix contract is broken for the only autofix-capable text_violations gate.

**Consumer impact (human):** Minimal — the gate hint text mentions `ruff format`, but an
automated agent cannot rely on hints.

**Fix options:**

1. **Config approach:** Add `fixable_when: "gate"` to the `text_violations` block in
   `quality.yaml`. The parser checks this and propagates `gate.capabilities.supports_autofix`
   as the per-violation `fixable` value. Minimal code change, all controlled in config.

2. **Code approach:** In `_parse_text_violations`, if the gate has `supports_autofix: true`,
   set all parsed violations to `fixable: True`. Same result, no new config syntax.

Option 1 is preferred for consistency with the existing `json_violations` `fixable_when`
pattern and config-over-code principle.

**Acceptance criterion:** Gate 0 FORMAT violation has `fixable: true` when gate config has
`supports_autofix: true`. `fixable: false` when gate has `supports_autofix: false`.

**Affected files:** `.st3/quality.yaml` (gate0 config) + `mcp_server/managers/qa_manager.py`
→ `_parse_text_violations` or `quality_config.py` → `CapabilitiesMetadata`/`TextViolationsConfig`

---

### F-15 — Four different path formats across gates in one response

**File:** All gates — root cause is in tool-side output + parsing layer  
**Root cause:** Each tool emits paths in its own format:

| Gate | Tool | Path format emitted | Example |
|------|------|-------------------|---------|
| Gate 0 | ruff format (text diff) | Relative, OS backslash | `tests\mcp_server\...` |
| Gate 1 | ruff JSON | Absolute, uppercase drive | `C:\temp\st3\...` |
| Gate 3 | ruff JSON | Absolute, uppercase drive | `C:\temp\st3\...` |
| Gate 4 | mypy text | Relative, OS backslash | `backend\dtos\...` |
| Gate 4b | Pyright JSON | Absolute, lowercase drive | `c:\temp\st3\...` |

The violation normaliser (`_normalize_violation`) maps raw fields via `field_map` but
performs no path normalisation. The resulting `file` field in the ViolationDTO carries
whatever the tool emitted.

**Consumer impact (agent):** An agent deduplicating violations across gates (e.g. F-17:
Gate 4 + Gate 4b report the same error) will see different file strings for the same file.
Cannot use simple `==` equality. Any agent building file-indexed violation maps will have
multiple keys for the same physical file. This is the most impactful contract gap for
multi-gate reasoning.

**Consumer impact (human):** Paths render inconsistently in output — noticeable when
comparing violations side-by-side but not blocking.

**Fix:** Add post-parse normalisation in `_normalize_violation` (or in `_build_compact_result`):
1. Resolve absolute paths to workspace-relative paths using `workspace_root`.
2. Convert OS separators to forward slashes (`Path(p).as_posix()`).
3. Lowercase the result for case-insensitive filesystems.

Result: all violations have `file` in consistent relative POSIX form.

**Acceptance criterion:** All violation `file` fields in a single response are in the same
format. Integration test comparing Gate 0 + Gate 1 violations for the same file asserts
identical `file` values.

**Affected files:** `mcp_server/managers/qa_manager.py` → `_normalize_violation` or
`_build_compact_result`

---

### F-17 — Gate 4b `severity: null` + Gate 4/4b double-report same error

**File:** `.st3/quality.yaml` gate4_pyright config · `mcp_server/managers/qa_manager.py`  

**Part A — `severity: null` in Gate 4b:**  
The config maps `severity: "severity"` from Pyright's `generalDiagnostics` JSON. Yet
live runs show `severity: null` in every Gate 4b violation. Two hypotheses:

1. **Field name change:** Pyright may have renamed the field in its JSON output. Known
   candidate: `diagnosticCategory` (used in older Pyright), or the field may be nested
   differently in the current Pyright version installed.
2. **Value format mismatch:** The field exists but the value type differs (e.g. integer
   category code instead of a string).

**Investigation needed:** Run `python -m pyright --outputjson <file> | python -c "import sys,json; d=json.load(sys.stdin); print(d['generalDiagnostics'][0].keys())"` on the fixture to inspect the actual Pyright JSON structure and confirm whether `severity` is the correct key.

**Part B — Duplicate reporting (Gate 4 + Gate 4b):**  
Gates 4 (mypy) and 4b (Pyright) both run on `backend/dtos/**/*.py`. For a type mismatch
on the same line, both gates fire:
- Gate 4: `rule: "assignment"`, `col: null`, `severity: "error"`
- Gate 4b: `rule: "reportAssignmentType"`, `col: 14`, `severity: null`

An agent receives two violation objects for one code defect, with inconsistent `rule`,
`col`, and `severity`. The agent cannot determine they refer to the same issue without a
cross-tool rule mapping table.

**Design question:** Are Gate 4 and Gate 4b intended to be complementary (mypy+Pyright
run together for maximum coverage) or redundant? If complementary, the duplicate-report
behaviour is expected and agents need to know not to deduplicate across these two gates.
If redundant, one should be removed.

**Recommendation:** Document the intended relationship in `quality.yaml` comments. For the
`severity: null` bug: fix the `field_map` in quality.yaml once the correct Pyright field
name is confirmed.

**Acceptance criterion (severity):** Gate 4b violations have `severity: "error"` or
`severity: "warning"` — not null — when Pyright reports that severity.

**Affected files:** `.st3/quality.yaml` → gate4_pyright `field_map`

---

### Proposed cycles

**Proposed cycle C35:** Add `overall_pass` + `duration_ms` to compact result (F-2) +
fix `skipped/passed` semantic contradiction with `status` enum (F-3).
Both target `_build_compact_result` — one cycle, one review.

**Proposed cycle C36:** Fix path normalisation — relative POSIX across all gates (F-15).
Core normalisation in `_normalize_violation`.

**Proposed cycle C37:** Fix `fixable` propagation for text_violations gates (F-14).
Config extension + parser update.

**Proposed cycle C38:** Fix Gate 4b `severity: null` — investigate Pyright JSON field name,
update `field_map` in quality.yaml (F-17 Part A). Document Gate 4 + 4b intended relationship
(F-17 Part B). Small — likely `quality.yaml` only.

---

## Investigation D: Response Clarity & UX (F-1, F-16, F-18)

**Findings:** [F-1](live-validation-plan.md) · [F-16](live-validation-plan.md) · [F-18](live-validation-plan.md)  
**Severity:** F-1 Medium · F-16 Low · F-18 Low  
**Audience:** Primarily **human users** reading `content[0]` text or displaying violations
in a chat UI. Agents are less affected but multi-line messages (F-18) can break log parsers.

---

### F-1 — `⚠️` emitted for expected clean state (empty diff)

**File:** `mcp_server/managers/qa_manager.py` → `_format_summary_line`  
**Root cause:** When scope=auto resolves to an empty file set (clean diff, no failed_files),
all gates are skipped. The current summary logic emits `⚠️ 0/0 active (N skipped)`. The
`⚠️` signal is reserved for "attention needed" situations but an empty diff is the expected
clean state — no attention needed.

**Fix:** In `_format_summary_line`, when all gates are skipped AND the overall_pass is True,
emit `✅ Nothing to check (no changed files)` instead of the warning signal.

**Acceptance criterion:** A1-pass scenario emits a `✅` summary line, not `⚠️`.

**Affected files:** `mcp_server/managers/qa_manager.py` → `_format_summary_line`

---

### F-16 — Gate 0 violations have `line: null, col: null`

**File:** N/A — structural limitation of ruff format diff output  
**Root cause:** `ruff format --check --diff` produces a unified diff, not a per-line
violation list. The `text_violations` pattern matches the `--- <file>` diff header,
yielding one violation per file with no line/col information. This is inherent to the
tool's output — ruff format does not report line numbers for formatting violations.

**Consumer impact:** The violation object has only `file`, `rule: "FORMAT"`, and
`message: "File requires formatting"`. A human or agent cannot navigate to a specific line.
They must re-run `ruff format <file>` to see the diff.

**Mitigation (not a fix):** The gate hint text already says "Re-run: `ruff format <file>`".
This is currently the only actionable path. Combined with F-14 fix (setting `fixable: true`),
an agent that follows `fixable` will know to run `ruff format` without needing line/col.

**No code change needed for F-16** — the `null` values are correct given the tool's output
format. The fix is to ensure `fixable: true` (F-14) and clear hint text (already present).

---

### F-18 — Gate 4b (Pyright) messages contain `\n` and `\u00a0`

**File:** `mcp_server/managers/qa_manager.py` → `_normalize_violation` / `_parse_json_violations`  
**Root cause:** Pyright's JSON output includes multi-line diagnostic messages with
non-breaking spaces for indentation. The parser passes these through verbatim.
Example: `"Type \"str\" is not assignable...\n\u00a0\u00a0\"str\" is not assignable..."`.

**Consumer impact (agent):** Log parsers that assume single-line messages will split
incorrectly. Agents constructing inline code comments will embed literal newlines in
single-line contexts.

**Consumer impact (human):** Chat UIs that render the JSON field as a string will display
the secondary line (after `\n`) separately, which can actually improve readability — but
it is inconsistent with all other gates that always produce single-line messages.

**Fix:** In `_normalize_violation`, after extracting the `message` field, normalise it:
```python
message = message.replace("\u00a0", " ").replace("\n", " — ").strip()
```
This converts `\n` to ` — ` (em-dash separator), producing a single line while preserving
the secondary type annotation information that Pyright includes.

**Acceptance criterion:** All violation messages in the compact response contain no `\n` or
`\u00a0` characters. Gate 4b message for the `str→int` fixture reads as a single line.

**Affected files:** `mcp_server/managers/qa_manager.py` → `_normalize_violation`

---

### Proposed cycle

**Proposed cycle C39:** Fix summary line signal (F-1) + sanitise Pyright messages (F-18).
Both are small, single-function changes. F-16 requires no code change — close as
"by design, fixable: true (F-14) is the mitigation".

---

## Investigation E: Fixed In-Session (F-4, F-13)

These findings were discovered and fixed during the validation session. Documented here for
completeness.

### F-4 — `PurePosixPath.match()` does not handle `**` in non-trailing position

**Status:** Fixed in commit `ca065718`  
**File:** `mcp_server/config/quality_config.py` → `GateScope.filter_files()`  
**Root cause:** `PurePosixPath.match("backend/dtos/**/*.py")` returns `False` on Python 3.13
because `.match()` applies suffix-matching semantics. A pattern with `**` in a non-terminal
position is not handled correctly. `full_match()` (available since Python 3.12) performs a
full-path match and returns `True` correctly.  
**Fix applied:** `.match(pattern)` → `.full_match(pattern)` (both include and exclude).  
**Tests:** `tests/mcp_server/unit/config/test_quality_config_scope.py` — 7 tests, all pass.

---

### F-13 — Gate 0 parser pattern `^--- a/(?P<file>.+)$` never matches ruff format output

**Status:** Fixed in commit `ca065718`  
**File:** `.st3/quality.yaml` → gate0_ruff_format `text_violations.pattern`  
**Root cause:** The pattern expected git-diff unified format (`--- a/path`). Ruff format
`--diff` output on Windows uses `--- path` (no `a/` prefix). Every Gate 0 run silently
reported `passed=true, violations=[]` regardless of actual formatting violations.  
**Fix applied:** Pattern changed from `^--- a/(?P<file>.+)$` to `^--- (?P<file>.+)$`.  
**Note:** Original research.md Investigation 2 / F2 documented the Gate 0 diff approach as
correct in principle — the bug was in the prefix assumption, not the strategy.

---

## Investigation F: Non-Actionable Observations (F-5, F-10, F-11, F-12)

### F-5 — 502KB responses for scope=project exceed MCP inline transport

**Status:** Known scalability limitation — no fix planned for this issue  
**Observation:** `scope=project` on a 400+ file codebase produces responses too large for
MCP inline transport. The response is written to disk. This is expected behaviour and is
already documented in the code. A proper fix would require response streaming or pagination,
which is out of scope for issue #251.

### F-10 and F-11 — Test plan errors in original live-validation-plan.md

**Status:** Test plan corrected in-session  
**F-10:** The plan expected Gate 0 violations from `violations.py` but the fixture doesn't
trigger ruff format. Corrected — Gate 0 now verified via dedicated `gate0_format_violation.py`.  
**F-11:** The plan used `script.py` as a "clean" reference file but it contains real
violations. Corrected — `backend/__init__.py` used instead.

### F-12 — Server-side WARNING log for ValidationError (double-reported)

**Status:** By design — no change needed  
**Observation:** Pydantic ValidationError is both returned to the client in the chat response
AND logged server-side as a structured WARNING with `call_id`/`tool_name`/`arguments`.
Double-reporting is intentional for server-side observability. No consumer confusion: the
client sees only the structured error; the log is server-internal.

---

## Proposed TDD Cycles Summary

| Cycle | Finding(s) | Description | Files changed | Priority |
|-------|-----------|-------------|--------------|----------|
| C32 | F-6, F-7 | Remove dead code block + fix import order | `qa_manager.py`, `server.py` | **Critical** (unblocks B1/P1) |
| C33 | F-8 | Fix `_resolve_branch_scope` key path for `parent_branch` | `qa_manager.py` | High |
| C34 | F-9 | Reject non-`.py` paths in `scope="files"` (Pydantic validator) | `quality_tools.py` | High |
| C35 | F-2, F-3 | Add `overall_pass` + `duration_ms` to compact result; add `status` enum to gate entries | `qa_manager.py` | Medium |
| C36 | F-15 | Normalise all violation `file` paths to relative POSIX | `qa_manager.py` | Medium |
| C37 | F-14 | Propagate `supports_autofix` → per-violation `fixable` for text_violations gates | `quality.yaml`, `qa_manager.py` | Medium |
| C38 | F-17 | Fix Gate 4b `severity: null` (Pyright field name); document Gate 4 + 4b relationship | `quality.yaml` | Low |
| C39 | F-1, F-18 | Fix `⚠️` signal for clean state; sanitise Pyright multi-line messages | `qa_manager.py` | Low |

**F-16** closed as by-design (null line/col is inherent to ruff format diff; mitigation via
F-14 `fixable: true`).  
**F-5, F-10, F-11, F-12** closed as noted above.

---

## Open Questions — Answers

> ❓ Can F-2 (missing overall_pass) and F-3 (skipped semantic) be resolved in a single cycle targeting _build_compact_result?

**Yes.** Both target `_build_compact_result` and the gate result building path. F-2 adds
top-level fields; F-3 adds a `status` enum to gate entries. Neither change conflicts with
the other. Proposed as C35.

---

> ❓ Should F-15 (path normalisation) be normalised at parse time in _parse_text_violations/_parse_json_violations, or at serialisation time in _build_compact_result?

**At normalisation time in `_normalize_violation`** — the single point where all violation
dicts (from both JSON and text parsers) pass through. This avoids duplicating the logic in
each parser and ensures the contract is enforced regardless of parsing strategy.
`workspace_root` is available on `QAManager` so relative-path conversion is feasible there.

---

> ❓ Does F-17 (Gate 4b severity: null) indicate a Pyright JSON schema change, or a field_map misconfiguration in quality.yaml?

**Requires investigation** (see C38). Probable hypothesis is a Pyright JSON schema change —
the field may now be named `diagnosticSeverity` or `category` in the installed Pyright
version. Must be confirmed by inspecting raw Pyright JSON output before changing the config.

---

> ❓ Should F-14 (fixable propagation from gate to violation) be a quality.yaml config change (add fixable_when to text_violations) or a code change in the text_violations parser?

**Both** — a small config extension (`fixable_when: "gate"` in `text_violations` config)
plus a parser-side check that reads this value and uses the parent gate's `supports_autofix`
flag. This keeps the behaviour config-driven (consistent with the `json_violations`
`fixable_when` pattern) while requiring minimal code in the parser.

---

> ❓ Is F-9 (silent dir skip) best fixed with Pydantic validation on the files list, or in _files_for_gate before gate execution?

**Pydantic validation** on the input model is strongly preferred. It produces a
`ValidationError` before any gate runs, is consistent with how `files=None` on
`scope="files"` is already handled, and provides a clear error message to the caller. The
runtime warning fallback (option 2) is acceptable only if test churn from changing the
Pydantic model proves excessive.

## Open Questions

- ❓ Can F-2 (missing overall_pass) and F-3 (skipped semantic) be resolved in a single cycle targeting _build_compact_result?
- ❓ Should F-15 (path normalisation) be normalised at parse time in _parse_text_violations/_parse_json_violations, or at serialisation time in _build_compact_result?
- ❓ Does F-17 (Gate 4b severity: null) indicate a Pyright JSON schema change, or a field_map misconfiguration in quality.yaml?
- ❓ Should F-14 (fixable propagation from gate to violation) be a quality.yaml config change (add fixable_when to text_violations) or a code change in the text_violations parser?
- ❓ Is F-9 (silent dir skip) best fixed with Pydantic validation on the files list, or in _files_for_gate before gate execution?


## Related Documentation
- **[docs/development/issue251/live-validation-plan.md — F-1..F-18 findings table][related-1]**
- **[docs/development/issue251/research.md — original investigations I1–I15, findings F1–F15][related-2]**
- **[mcp_server/config/quality_config.py — GateScope.filter_files()][related-3]**
- **[mcp_server/managers/qa_manager.py — _resolve_branch_scope, _build_compact_result, _format_summary_line, dead code lines 321-344][related-4]**
- **[mcp_server/server.py — I001 at line 3][related-5]**
- **[.st3/quality.yaml — gate0 text_violations pattern, gate4_types scope.include_globs][related-6]**

<!-- Link definitions -->

[related-1]: docs/development/issue251/live-validation-plan.md — F-1..F-18 findings table
[related-2]: docs/development/issue251/research.md — original investigations I1–I15, findings F1–F15
[related-3]: mcp_server/config/quality_config.py — GateScope.filter_files()
[related-4]: mcp_server/managers/qa_manager.py — _resolve_branch_scope, _build_compact_result, _format_summary_line, dead code lines 321-344
[related-5]: mcp_server/server.py — I001 at line 3
[related-6]: .st3/quality.yaml — gate0 text_violations pattern, gate4_types scope.include_globs

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |
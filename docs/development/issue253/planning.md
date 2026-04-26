<!-- docs\development\issue253\planning.md -->
<!-- template=planning version=130ac5ea created=2026-04-25T12:41Z updated= -->
# run_tests Reliability — TDD Implementation Planning

**Status:** DRAFT
**Version:** 2.0
**Last Updated:** 2026-04-25

---

## Purpose

Define the TDD cycle breakdown, file-level deliverables, dependency order, and cleanup scope for issue #253 so implementation can proceed cycle by cycle with verifiable deliverables.

## Scope

**In Scope:**
New mcp_server/managers/pytest_runner.py; IPytestRunner in mcp_server/core/interfaces/__init__.py; rewritten mcp_server/tools/test_tools.py; modified mcp_server/tools/project_tools.py and mcp_server/server.py; new and rewritten test files under tests/mcp_server/unit/

**Out of Scope:**
run_quality_gates changes; new YAML config for coverage or exit codes; NoteContext operation_notes.py new note types; CI/CD pipeline changes; mcp_server/managers/qa_manager.py

## Prerequisites

Read these first:
1. design.md v2.3 APPROVED (444c92e)
2. Branch fix/253-run-tests-reliability in planning phase
3. QUALITY_GATES.md §5 Integration Test Boundary Contract committed
4. create_branch encoding fix committed (git_tools.py:160)
---

## Summary

Refactor RunTestsTool into a thin MCP adapter backed by a new PytestRunner manager (IPytestRunner Protocol + PytestResult typed contract). Closes three gaps simultaneously: SRP/DIP violations, summary_line contract drift, and missing coverage enforcement. Six TDD cycles cover new manager, interface, tool refactor, GetProjectPlanTool fix, cleanup of legacy code, and quality-gate validation.

---

## Dependencies

- C2 depends on C1 (PytestRunner uses PytestResult, PytestExitCode, ExitCodePolicy)
- C3 depends on C1 (FakePytestRunner returns PytestResult)
- C4 depends on C1, C2, C3 (RunTestsTool injects IPytestRunner; uses PytestResult fields)
- C5 is independent — GetProjectPlanTool change has no dependency on C1-C4
- C6 depends on C4 AND C5 (legacy functions only deletable after thin tool is working; GetProjectPlanTool fix must also be complete)

---

## TDD Cycles

Dependency graph:

```
C1 ──► C2 ──► C4 ──► C6 (cleanup)
C1 ──► C3 ──► C4      ▲
                  C5 ──┘
```

---

### C1 — Data Contracts (PytestResult + Enums + Policy Table)

**Depends on:** nothing
**Delivers to:** C2 (uses PytestResult), C3 (FakePytestRunner needs PytestResult)

**Goal:**
Create all value types that flow between PytestRunner and RunTestsTool.
No subprocess, no tool — pure data layer.

**Files changed:**

| Action | File |
|--------|------|
| CREATE | `mcp_server/managers/pytest_runner.py` (types only, no PytestRunner class yet) |

**New symbols in `pytest_runner.py` after C1:**

```
PytestExitCode(IntEnum)          — ALL_PASSED=0, TESTS_FAILED=1, INTERRUPTED=2,
                                   INTERNAL_ERROR=3, USAGE_ERROR=4, NO_TESTS_COLLECTED=5

FailureDetail(frozen dataclass)  — test_id: str, location: str, short_reason: str, traceback: str

PytestResult(frozen dataclass)   — exit_code: int                   (raw int, not PytestExitCode)
                                   summary_line: str                 (always non-empty field, not property)
                                   passed: int
                                   failed: int
                                   skipped: int
                                   errors: int
                                   failures: tuple[FailureDetail, ...]  (tuple, not list)
                                   coverage_pct: float | None
                                   lf_cache_was_empty: bool
                                   should_raise: bool
                                   note: NoteEntry | None

ExitCodePolicy(frozen dataclass) — outcome: Literal["return", "raise"]
                                   note_factory: Callable[[int], NoteEntry] | None
                                   summary_line_when_no_parse: str   (fallback when parser finds nothing)

_EXIT_CODE_POLICY: dict[int, ExitCodePolicy]  — keys 0-5
  code 0: ("return", None, "")
  code 1: ("return", None, "")
  code 2: ("raise", lambda c: RecoveryNote(...), "pytest interrupted (exit 2)")
  code 3: ("raise", lambda c: RecoveryNote(...), "pytest internal error (exit 3)")
  code 4: ("raise", lambda c: RecoveryNote(...), "pytest usage error (exit 4)")
  code 5: ("return", lambda c: SuggestionNote(...), "no tests collected")   ← NOT raise

_UNKNOWN_CODE_POLICY: ExitCodePolicy          — ("raise", lambda c: RecoveryNote(...), "pytest exited with unexpected code")
```

**Invariants enforced by PytestRunner:**
- `summary_line` is NEVER the empty string — fallback to `policy.summary_line_when_no_parse`
- `failures` is a `tuple`, not a `list` (frozen dataclass + hashability)
- `coverage_pct` is `None` unless the cmd contained `--cov`
- `exit_code` is a raw `int` — not cast to `PytestExitCode`

**Tests:** None in C1. Data types are exercised by C2 parser tests. Total test count preserved at 29.

**Success Criteria:**
- `PytestResult`, `ExitCodePolicy`, `PytestExitCode` importable from `mcp_server.managers.pytest_runner`
- `mypy --strict` clean on `pytest_runner.py` (types-only module)

---

### C2 — PytestRunner Manager (subprocess + parser + policy stamp)

**Depends on:** C1
**Delivers to:** C4 (RunTestsTool injects PytestRunner)

**Goal:**
Implement `PytestRunner` that wraps subprocess execution, parses stdout, applies exit-code policy, returns `PytestResult`.

**Files changed:**

| Action | File |
|--------|------|
| MODIFY | `mcp_server/managers/pytest_runner.py` (add PytestRunner class, _PytestExecution, helpers) |
| CREATE | `tests/mcp_server/unit/managers/test_pytest_runner.py` (8 parser tests) |

**New symbols after C2:**

```
_PytestExecution(dataclass)  — internal: stdout, stderr, returncode (NEVER exported)
PytestRunner                 — run(cmd: list[str], cwd: str, timeout: int) -> PytestResult
                               _parse_output(stdout: str) -> dict
                               _parse_coverage_pct(stdout: str) -> float | None
```

**Parser responsibilities:**
- Extract `passed`, `failed`, `errors`, `skipped` from summary line regex
- Build `tuple[FailureDetail, ...]` from `FAILED test::name - reason` lines; attach tracebacks
- Extract `coverage_pct` from `TOTAL ... XX%` line
- Set `lf_cache_was_empty=True` when LF-empty fallback message detected in stdout
- Stamp `should_raise` + `note` via `_EXIT_CODE_POLICY.get(returncode, _UNKNOWN_CODE_POLICY)`
- `summary_line` NEVER empty — fallback to `policy.summary_line_when_no_parse`

**Exit-code-5 contract (CRITICAL — differs from codes 2/3/4):**

```
code 5 (NO_TESTS_COLLECTED):
  outcome = "return"          ← return ToolResult, do NOT raise
  note    = SuggestionNote("No tests matched the filter. Check markers and path.")
  summary_line = "no tests collected"
```

**Tests (new file):** `tests/mcp_server/unit/managers/test_pytest_runner.py`

All 8 PytestRunner tests from design.md §3.10. These are the ONLY tests for the runner layer (design total = 8):

| # | Test | Assertion |
|---|------|-----------|
| 1 | `test_runner_all_passed_stdout` | `passed=N, failed=0, errors=0`, `summary_line` non-empty |
| 2 | `test_runner_failing_tests_stdout` | `failures` tuple populated with `FailureDetail` per FAILED line |
| 3 | `test_runner_skipped_tests_stdout` | `skipped=N` |
| 4 | `test_runner_errors_during_collection_stdout` | `errors=N` |
| 5 | `test_runner_coverage_report_line_present` | `coverage_pct` parsed correctly |
| 6 | `test_runner_lf_empty_fallback_message` | `lf_cache_was_empty=True` |
| 7 | `test_runner_empty_unparseable_stdout` | `summary_line` falls back to policy; never empty |
| 8 | `test_runner_exit_code_5_returns_suggestion_note` | `should_raise=False`, `note` is `SuggestionNote`, `summary_line == "no tests collected"` |

**Test count after C2:** 8 (total running count toward 29)

**Success Criteria:**
- All 8 tests GREEN
- mypy compliance maintained
- `PytestRunner` correctly creates `PytestResult` with `exit_code` as raw `int` (not `PytestExitCode` cast)

---

### C3 — IPytestRunner Protocol + FakePytestRunner Fixture

**Depends on:** C1
**Delivers to:** C4 (RunTestsTool type-checked against Protocol; tests use FakePytestRunner)

**Goal:**
Define the formal Protocol boundary and provide a deterministic test double.

**Files changed:**

| Action | File |
|--------|------|
| MODIFY | `mcp_server/core/interfaces/__init__.py` (add IPytestRunner Protocol) |
| CREATE | `tests/mcp_server/fixtures/fake_pytest_runner.py` |

**IPytestRunner signature:**

```python
class IPytestRunner(Protocol):
    def run(self, cmd: list[str], cwd: str, timeout: int) -> PytestResult: ...
```

> Import `PytestResult` under `TYPE_CHECKING` to prevent core → managers import cycle.

**FakePytestRunner:**

```python
@dataclass
class FakePytestRunner:
    result: PytestResult
    captured_cmd: list[str] | None = None

    def run(self, cmd: list[str], cwd: str, timeout: int) -> PytestResult:
        self.captured_cmd = cmd
        return self.result
```

**Tests:** No dedicated test file. Structural compatibility validated implicitly when C4 tests pass.

**Success Criteria:**
- `IPytestRunner` importable from `mcp_server.core.interfaces`
- `FakePytestRunner` importable from `tests.mcp_server.fixtures.fake_pytest_runner`
- `mypy --strict` clean on `core/interfaces/__init__.py`

---

### C4 — RunTestsTool Refactor (thin adapter + coverage flag + composition root)

**Depends on:** C1, C2, C3
**Delivers to:** C6 (old patch-based tests can now be deleted)

**Goal:**
Replace RunTestsTool internals: inject `IPytestRunner`, add `coverage` field, fix `_build_cmd`, consume `PytestResult.note` + `PytestResult.should_raise`, update `server.py` composition root.

**Files changed:**

| Action | File |
|--------|------|
| MODIFY | `mcp_server/tools/test_tools.py` (RunTestsInput + RunTestsTool refactor) |
| MODIFY | `mcp_server/server.py` (inject PytestRunner()) |

**Key changes:**
- `RunTestsInput`: add `coverage: bool = False`; all other fields unchanged
- `RunTestsTool.__init__`: `runner: IPytestRunner` as first required arg (no default, composition root injects)
- `_build_cmd`: add `--cov=backend --cov=mcp_server --cov-branch --cov-fail-under=90` when `coverage=True`
- `execute()`: remove `del context`; call `context.produce(result.note)` when note present; raise `ExecutionError` when `result.should_raise`; return `_to_tool_result(result)` otherwise
- `server.py` line 301: `RunTestsTool(runner=PytestRunner(), settings=settings)` + import `PytestRunner`

**API corrections (CRITICAL):**

```python
# Wrong (not in this codebase):
raise ToolError(...)
context.add_note(...)

# Correct (per NoteContext API and design.md §3.6):
raise ExecutionError(...)
context.produce(...)
```

**execute() structure (thin adapter — no pytest protocol knowledge):**

```python
async def execute(self, params: RunTestsInput, context: NoteContext) -> ToolResult:
    cmd = self._build_cmd(params)
    timeout = params.timeout or self.DEFAULT_TIMEOUT
    try:
        result = await asyncio.to_thread(self._runner.run, cmd, self._workspace_root, timeout)
    except subprocess.TimeoutExpired:
        context.produce(RecoveryNote(f"Tests timed out after {timeout}s. ..."))
        raise ExecutionError(f"Tests timed out after {timeout}s") from None
    except OSError as exc:
        context.produce(RecoveryNote("Verify the Python interpreter and venv are reachable."))
        raise ExecutionError(f"Failed to run tests: {exc}") from exc

    if result.note is not None:
        context.produce(result.note)
    _emit_lf_cache_note(result, params, context)

    if result.should_raise:
        raise ExecutionError(f"pytest exited with returncode {result.exit_code}")

    return _to_tool_result(result)
```

**Tests (new FakePytestRunner-based tests):** `tests/mcp_server/unit/tools/test_test_tools.py`

> Legacy tests still present at this point — deleted in C6. Design §3.10 defines exactly 18 scenarios:

| # | Scenario | FakePytestRunner.result exit_code | Expected outcome | Note assertions |
|---|----------|------------------------------------|------------------|-----------------|
| 1 | All tests pass | 0 | `ToolResult` content[0]==summary_line | none |
| 2 | Some tests fail | 1 | `ToolResult` with failures in content[1] | none |
| 3 | Pytest interrupted | 2 | raises `ExecutionError` | 1× `RecoveryNote` |
| 4 | Pytest internal error | 3 | raises `ExecutionError` | 1× `RecoveryNote` |
| 5 | Pytest usage error | 4 | raises `ExecutionError` | 1× `RecoveryNote` |
| 6 | No tests collected | 5 | returns `ToolResult`, summary_line="no tests collected" | 1× `SuggestionNote` |
| 7 | Unknown exit code (99) | 99 | raises `ExecutionError` | 1× `RecoveryNote` (fail-safe) |
| 8 | LF cache empty + last_failed_only=True | 0, lf_cache_was_empty=True | normal `ToolResult` | 1× `InfoNote` |
| 9 | LF cache populated + last_failed_only=True | 0, lf_cache_was_empty=False | normal `ToolResult` | none |
| 10 | last_failed_only=False, lf_cache_was_empty=True | 0 | normal `ToolResult` | none (flag ignored unless requested) |
| 11 | coverage=True | 0, coverage_pct=92.5 | content[1].json.coverage_pct == 92.5 | none |
| 12 | coverage=False | 0, coverage_pct=None | content[1].json.coverage_pct is None | none |
| 13 | content/summary parity invariant | any | content[0]["text"] == content[1]["json"]["summary_line"] | n/a |
| 14 | timeout | runner raises TimeoutExpired | raises `ExecutionError` | 1× `RecoveryNote` |
| 15 | OSError on subprocess start | runner raises OSError | raises `ExecutionError` | 1× `RecoveryNote` |
| 16 | _build_cmd adds --cov packages when coverage=True | n/a | captured_cmd contains --cov=backend, --cov=mcp_server, --cov-branch | n/a |
| 17 | _build_cmd adds --cov-fail-under=90 when coverage=True | n/a | captured_cmd contains --cov-fail-under=90 | n/a |
| 18 | _build_cmd omits all --cov* when coverage=False | n/a | captured_cmd contains no --cov* | n/a |

**Test count after C4:** 8 + 18 = 26 (running count toward 29)

**Success Criteria:**
- All 18 new tests GREEN
- Server boots: `PytestRunner()` injected in `server.py`
- No import of `_EXIT_CODE_POLICY` in `test_tools.py`
- `ExecutionError` used (not `ToolError`); `context.produce()` used (not `context.add_note()`)

---

### C5 — GetProjectPlanTool Fix (SuggestionNote + del context)

**Depends on:** nothing (independent)
**Delivers to:** C6 quality sweep

**Goal:**
Add `SuggestionNote` to the not-found error path; remove `del context` anti-pattern.

**Files changed:**

| Action | File |
|--------|------|
| MODIFY | `mcp_server/tools/project_tools.py` (GetProjectPlanTool.execute) |

**Before:**

```python
del context  # Not used
...
return ToolResult.error(f"No project plan found for issue #{params.issue_number}")
```

**After:**

```python
# del context line removed
...
context.produce(SuggestionNote(
    "Run initialize_project first to create a project plan.",
    subject=f"issue #{params.issue_number}"
))
return ToolResult.error(f"No project plan found for issue #{params.issue_number}")
```

**Tests (added to):** `tests/mcp_server/unit/tools/test_project_tools.py`

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_get_plan_not_found_returns_error` | ToolResult.error with issue number |
| 2 | `test_get_plan_not_found_adds_suggestion_note` | 1× SuggestionNote appended |
| 3 | `test_get_plan_not_found_suggestion_subject_contains_issue_number` | subject == f"issue #{n}" |

**Test count after C5:** 8 + 18 + 3 = 29 ✓ (matches design.md §3.10 total)

**Success Criteria:**
- All 3 tests GREEN
- No `del context` in `GetProjectPlanTool.execute`
- `context.produce()` used (not `context.add_note()`)

---

### C6 — Legacy Cleanup

**Depends on:** C4, C5
**⚠️ This cycle is mandatory: no legacy or old test code may remain after implementation.**

**Goal:**
Delete every line of replaced legacy code. Leave zero orphaned symbols, zero patch-based tests, zero dead imports, and zero unmigrated `RunTestsTool(...)` call sites that omit the required `runner=` argument.

**Files changed:**

| Action | File | What to delete / migrate |
|--------|------|--------------------------|
| MODIFY | `mcp_server/tools/test_tools.py` | Delete `_run_pytest_sync` function |
| MODIFY | `mcp_server/tools/test_tools.py` | Delete `_parse_pytest_output` function |
| MODIFY | `tests/mcp_server/unit/tools/test_test_tools.py` | Delete ALL 21 legacy test functions (see list) |
| MODIFY | `tests/mcp_server/unit/tools/test_test_tools.py` | Delete `mock_run_pytest_sync` fixture |
| MODIFY | `tests/mcp_server/unit/tools/test_test_tools.py` | Delete `# pyright: reportPrivateUsage=false` |
| MODIFY | `tests/mcp_server/unit/tools/test_test_tools.py` | Remove unused imports (patch, MagicMock, Generator) |
| MIGRATE | `tests/mcp_server/unit/tools/test_dev_tools.py` | Replace `RunTestsTool(settings=...)` + `patch(_run_pytest_sync)` with `RunTestsTool(runner=FakePytestRunner(...), settings=...)` |
| MIGRATE | `tests/mcp_server/unit/integration/test_all_tools.py` | Replace both `RunTestsTool()` calls with `RunTestsTool(runner=PytestRunner())` |
| VERIFY | `mcp_server/tools/test_tools.py` | No reference to `_run_pytest_sync` or `_parse_pytest_output` |
| VERIFY | `tests/mcp_server/unit/tools/test_test_tools.py` | No `patch("mcp_server.tools.test_tools._run_pytest_sync")` |
| VERIFY | `mcp_server/server.py` | `RunTestsTool(runner=PytestRunner(), ...)` is the composition root |
| VERIFY | entire codebase | grep `RunTestsTool(` → all occurrences include `runner=` |

**RunTestsTool call sites requiring migration (breaking refactor — no shim):**

| File | Line | Current (broken after refactor) | Migration |
|------|------|----------------------------------|-----------|
| `mcp_server/server.py` | 301 | `RunTestsTool(settings=settings)` | `RunTestsTool(runner=PytestRunner(), settings=settings)` |
| `tests/mcp_server/unit/tools/test_test_tools.py` | multiple | `RunTestsTool(settings=injected_settings)` | Replaced by 18 new tests using `FakePytestRunner` in C4 |
| `tests/mcp_server/unit/tools/test_dev_tools.py` | 24 | `RunTestsTool(settings=Settings(...))` | `RunTestsTool(runner=FakePytestRunner(...), settings=Settings(...))` |
| `tests/mcp_server/unit/integration/test_all_tools.py` | 220 | `RunTestsTool()` | `RunTestsTool(runner=PytestRunner())` |
| `tests/mcp_server/unit/integration/test_all_tools.py` | 542 | `RunTestsTool()` | `RunTestsTool(runner=PytestRunner())` |

**Legacy test functions to delete from test_test_tools.py (all 21):**

```
test_run_tests_success
test_run_tests_failure
test_run_tests_markers
test_run_tests_exception
test_parse_pytest_output_importable
test_parse_pytest_output_green
test_parse_pytest_output_red
test_run_tests_json_response_on_success
test_run_tests_json_response_on_failure
test_run_tests_input_has_no_verbose_field
test_run_tests_input_has_last_failed_only_field
test_build_cmd_method_exists_on_tool
test_last_failed_only_adds_lf_flag
test_last_failed_only_default_no_lf_flag
test_last_failed_only_combined_with_path
test_path_accepts_space_separated_string
test_scope_full_field_exists_and_is_accepted
test_no_path_no_scope_raises_validation_error
test_path_and_scope_mutual_exclusion_raises_validation_error
test_space_separated_paths_produce_multiple_args_in_cmd
test_scope_full_produces_no_path_args_in_cmd
```

**Quality gate sweep (end of C6):**

```
run_tests(path="tests/mcp_server/unit/tools/test_test_tools.py")          # 18 GREEN, 0 legacy
run_tests(path="tests/mcp_server/unit/managers/test_pytest_runner.py")    # 8 GREEN
run_tests(path="tests/mcp_server/unit/tools/test_project_tools.py")       # all GREEN incl. 3 new
run_tests(path="tests/mcp_server/unit/tools/test_dev_tools.py")           # GREEN (migrated)
run_tests(path="tests/mcp_server/unit/integration/test_all_tools.py")     # GREEN (migrated)
run_quality_gates(scope="files", files=[
    "mcp_server/tools/test_tools.py",
    "mcp_server/managers/pytest_runner.py",
    "mcp_server/core/interfaces/__init__.py",
    "mcp_server/tools/project_tools.py",
    "mcp_server/server.py",
    "tests/mcp_server/unit/tools/test_dev_tools.py",
    "tests/mcp_server/unit/integration/test_all_tools.py",
])
run_quality_gates(scope="branch")   # GREEN
run_tests(path="tests/")            # full suite GREEN
```

**Success Criteria:**
- Zero references to `_run_pytest_sync` anywhere
- Zero `patch("mcp_server.tools.test_tools._run_pytest_sync")` calls
- `test_test_tools.py` contains exactly 18 tests, all GREEN
- All `RunTestsTool(...)` call sites include `runner=` argument
- `run_quality_gates(scope="branch")` GREEN
- Full test suite GREEN


---

## Risks & Mitigation

- **Risk:** Parser regex fragility — `_parse_pytest_output` partially handles skipped/errors/coverage
  - **Mitigation:** C2 extends coverage with dedicated stdout fixtures per variant; frozen result objects prevent accidental mutation

- **Risk:** Async boundary mismatch — `asyncio.to_thread` wraps sync `runner.run()`; FakePytestRunner must also be synchronous
  - **Mitigation:** `IPytestRunner.run()` is typed as synchronous; asyncio.to_thread wrapping lives exclusively in `execute()`, not in the runner

- **Risk:** Import cycle — `IPytestRunner` in `core/interfaces` references `PytestResult` in `managers/pytest_runner`
  - **Mitigation:** Use `TYPE_CHECKING` guard per TYPE_CHECKING_PLAYBOOK.md; `PytestResult` only referenced in annotation strings at runtime

- **Risk:** Legacy test contamination — old `test_test_tools.py` patch-based tests may pass alongside new tests, masking the cleanup requirement
  - **Mitigation:** C6 is a mandatory dedicated cleanup cycle; success criteria explicitly require 18 tests and zero legacy functions

- **Risk:** `content[0]/content[1]` order in ToolResult — established by issue #251; construction path must not change
  - **Mitigation:** Thin adapter constructs ToolResult identically to current code; only the source of `stdout/stderr/returncode` changes

---

## Milestones

- After C1: PytestResult + ExitCodePolicy + PytestExitCode importable; data contracts verified structurally (no own tests — C2 parser tests cover the contracts)
- After C2: PytestRunner passes all 8 parser/runner tests; PytestResult returned for each exit code scenario
- After C3: IPytestRunner Protocol + FakePytestRunner usable in tool tests
- After C4: run_tests MCP tool passes all 18 tool-level tests; server boots with new composition root
- After C5: GetProjectPlanTool SuggestionNote test passes (3 test cases)
- After C6: no legacy patch-based tests remain; ruff/mypy clean on all changed files; run_quality_gates(scope=branch) GREEN

## Related Documentation
- **[docs/development/issue253/design.md][related-1]**
- **[docs/development/issue253/research.md][related-2]**
- **[docs/coding_standards/QUALITY_GATES.md][related-3]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-4]**
- **[docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md][related-5]**
- **[mcp_server/tools/test_tools.py][related-6]**
- **[mcp_server/tools/project_tools.py][related-7]**
- **[mcp_server/core/interfaces/__init__.py][related-8]**
- **[mcp_server/managers/qa_manager.py][related-9]**

<!-- Link definitions -->

[related-1]: docs/development/issue253/design.md
[related-2]: docs/development/issue253/research.md
[related-3]: docs/coding_standards/QUALITY_GATES.md
[related-4]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-5]: docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md
[related-6]: mcp_server/tools/test_tools.py
[related-7]: mcp_server/tools/project_tools.py
[related-8]: mcp_server/core/interfaces/__init__.py
[related-9]: mcp_server/managers/qa_manager.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |
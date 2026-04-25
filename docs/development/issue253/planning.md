<!-- docs\development\issue253\planning.md -->
<!-- template=planning version=130ac5ea created=2026-04-25T12:41Z updated= -->
# run_tests Reliability — TDD Implementation Planning

**Status:** DRAFT  
**Version:** 1.0  
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
- C4 depends on C2 and C3 (RunTestsTool injects IPytestRunner; uses PytestResult fields)
- C5 is independent — GetProjectPlanTool change has no dependency on C1-C4
- C6 depends on C4 (legacy functions only deletable after thin tool is working)

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
PytestExitCode(IntEnum)          — 0=OK, 1=TESTS_FAILED, 2=INTERRUPTED,
                                   3=INTERNAL_ERROR, 4=CLI_USAGE_ERROR, 5=NO_TESTS
FailureDetail(frozen dataclass)  — file: str, test: str, reason: str
PytestResult(frozen dataclass)   — passed, failed, errors, skipped: int
                                   failures: list[FailureDetail]
                                   coverage_pct: float | None
                                   exit_code: PytestExitCode
                                   should_raise: bool
                                   note: NoteEntry | None
                                   summary_line: str (property)
ExitCodePolicy(frozen dataclass) — should_raise: bool, note_factory: Callable[[int], NoteEntry] | None
_EXIT_CODE_POLICY: dict[int, ExitCodePolicy]  — keys 0-5; None factories for 0 and 1
_UNKNOWN_CODE_POLICY: ExitCodePolicy          — fallback for unknown exit codes
```

**Tests (new file):** `tests/mcp_server/unit/managers/test_pytest_runner.py`

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_exit_code_policy_code0_no_raise_no_note` | code 0 → should_raise=False, note_factory=None |
| 2 | `test_exit_code_policy_code1_no_raise_no_note` | code 1 → should_raise=False, note_factory=None |
| 3 | `test_exit_code_policy_code2_raises` | code 2 → should_raise=True |
| 4 | `test_exit_code_policy_unknown_code_raises` | unknown code → _UNKNOWN_CODE_POLICY.should_raise=True |
| 5 | `test_pytest_result_summary_line_all_passed` | summary_line format for all-passed |
| 6 | `test_pytest_result_summary_line_some_failed` | summary_line format with failures |
| 7 | `test_pytest_result_frozen_rejects_mutation` | dataclass is frozen |
| 8 | `test_failure_detail_frozen` | FailureDetail is frozen |

**Success Criteria:**
- All 8 tests GREEN
- `PytestResult`, `ExitCodePolicy`, `PytestExitCode` importable from `mcp_server.managers.pytest_runner`
- `mypy --strict` clean on `pytest_runner.py`

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

**New symbols after C2:**

```
_PytestExecution(dataclass)  — internal: stdout, stderr, returncode
PytestRunner                 — run(cmd, cwd, timeout) -> PytestResult
                               _parse_output(stdout) -> dict
                               _parse_coverage_pct(stdout) -> float | None
```

**Parser responsibilities:**
- Extract `passed`, `failed`, `errors`, `skipped` from summary line
- Build `list[FailureDetail]` from `FAILED test::name - reason` lines
- Extract `coverage_pct` from `TOTAL ... XX%` line
- Stamp `should_raise` + `note` via `_EXIT_CODE_POLICY.get(returncode, _UNKNOWN_CODE_POLICY)`

**Tests (added to same file):**

| # | Test | Stdout Fixture |
|---|------|----------------|
| 1 | `test_runner_returns_passed_counts` | all-passed |
| 2 | `test_runner_returns_failed_counts_and_details` | some-failed |
| 3 | `test_runner_handles_skipped_tests` | with-skipped |
| 4 | `test_runner_handles_errors` | with-errors |
| 5 | `test_runner_parses_coverage_pct` | with-coverage |
| 6 | `test_runner_handles_last_failed_empty` | last-failed-empty (exit 5) |
| 7 | `test_runner_handles_empty_stdout` | empty string |
| 8 | `test_runner_stamps_should_raise_for_exit5` | exit_code=5, should_raise=True |

**Success Criteria:**
- All 8 runner tests GREEN (design.md total: 8 tests in test_pytest_runner.py)
- mypy compliance maintained

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
- `RunTestsInput`: add `coverage: bool = False`
- `RunTestsTool.__init__`: `runner: IPytestRunner` as first required arg (no default)
- `_build_cmd`: add `--cov=backend --cov=mcp_server --cov-branch --cov-fail-under=90` when `coverage=True`
- `execute()`: remove `del context`; call `runner.run()`; append `result.note`; raise if `result.should_raise`
- `server.py` line 301: `RunTestsTool(runner=PytestRunner(), settings=settings)`
- Add import: `from mcp_server.managers.pytest_runner import PytestRunner`

**Tests (new FakePytestRunner-based tests):** `tests/mcp_server/unit/tools/test_test_tools.py`

> Legacy tests still present at this point — deleted in C6.

| # | Test | Verifies |
|---|------|----------|
| 1 | `test_input_has_coverage_field` | coverage default=False |
| 2 | `test_input_path_and_scope_mutual_exclusion` | validation error |
| 3 | `test_input_no_path_no_scope_raises` | validation error |
| 4 | `test_build_cmd_basic_path` | cmd contains path |
| 5 | `test_build_cmd_scope_full_no_path_arg` | no path arg |
| 6 | `test_build_cmd_coverage_flags` | --cov=backend, --cov-fail-under=90 |
| 7 | `test_build_cmd_no_coverage_flags_by_default` | --cov absent |
| 8 | `test_build_cmd_last_failed_only_adds_lf` | --lf present |
| 9 | `test_build_cmd_markers` | -m marker present |
| 10 | `test_execute_success_returns_tool_result` | exit 0 → ToolResult.text |
| 11 | `test_execute_passes_cmd_to_runner` | captured_cmd verified |
| 12 | `test_execute_should_raise_raises_tool_error` | should_raise → ToolError |
| 13 | `test_execute_note_appended_to_context` | note → context.add_note |
| 14 | `test_execute_no_note_nothing_appended` | note=None → no add_note |
| 15 | `test_execute_coverage_cmd_when_coverage_true` | --cov-fail-under=90 in cmd |
| 16 | `test_execute_space_separated_paths` | "a b" → two args |
| 17 | `test_execute_scope_full_no_path_in_cmd` | no path args |
| 18 | `test_execute_timeout_forwarded_to_runner` | timeout reaches runner |

**Success Criteria:**
- All 18 new tests GREEN
- Server boots: `PytestRunner()` injected in `server.py`
- No import of `_EXIT_CODE_POLICY` in `test_tools.py`

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
context.add_note(SuggestionNote(
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

**Success Criteria:**
- All 3 tests GREEN
- No `del context` in `GetProjectPlanTool.execute`

---

### C6 — Legacy Cleanup

**Depends on:** C4, C5
**⚠️ This cycle is mandatory: no legacy or old test code may remain after implementation.**

**Goal:**
Delete every line of replaced legacy code. Leave zero orphaned symbols, zero patch-based tests, and zero dead imports.

**Files changed:**

| Action | File | What to delete |
|--------|------|----------------|
| MODIFY | `mcp_server/tools/test_tools.py` | Delete `_run_pytest_sync` function |
| MODIFY | `mcp_server/tools/test_tools.py` | Delete `_parse_pytest_output` function |
| MODIFY | `tests/mcp_server/unit/tools/test_test_tools.py` | Delete ALL 21 legacy test functions |
| MODIFY | `tests/mcp_server/unit/tools/test_test_tools.py` | Delete `mock_run_pytest_sync` fixture |
| MODIFY | `tests/mcp_server/unit/tools/test_test_tools.py` | Delete `# pyright: reportPrivateUsage=false` |
| MODIFY | `tests/mcp_server/unit/tools/test_test_tools.py` | Remove unused imports (patch, MagicMock, Generator) |
| VERIFY | `mcp_server/tools/test_tools.py` | No reference to `_run_pytest_sync` or `_parse_pytest_output` |
| VERIFY | `tests/mcp_server/unit/tools/test_test_tools.py` | No `patch("mcp_server.tools.test_tools._run_pytest_sync")` |
| VERIFY | `mcp_server/server.py` | `RunTestsTool(runner=PytestRunner(), ...)` is the composition root |

**Legacy test functions to delete (all 21):**

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
run_quality_gates(scope="files", files=[
    "mcp_server/tools/test_tools.py",
    "mcp_server/managers/pytest_runner.py",
    "mcp_server/core/interfaces/__init__.py",
    "mcp_server/tools/project_tools.py",
    "mcp_server/server.py",
])
run_quality_gates(scope="branch")   # GREEN
run_tests(path="tests/")            # full suite GREEN
```

**Success Criteria:**
- Zero references to `_run_pytest_sync` anywhere
- Zero `patch("mcp_server.tools.test_tools._run_pytest_sync")` calls
- `test_test_tools.py` contains exactly 18 tests, all GREEN
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

- After C1: PytestResult + enum + policy table importable and unit-tested
- After C2: PytestRunner passes all 8 parser tests; subprocess integration verified
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
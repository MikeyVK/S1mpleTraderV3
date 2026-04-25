<!-- docs\development\issue253\design.md -->
<!-- template=design version=5827e841 created=2026-04-25T11:15Z updated=2026-04-25 -->
# run_tests Reliability — Thin Tool + PytestRunner Manager, Typed Result Contract, Coverage Support

**Status:** APPROVED  
**Version:** 2.3  
**Last Updated:** 2026-04-25

---

## Purpose

Define finalized interface contracts for all changes in issue #253 so TDD implementation can proceed without design ambiguity. The chosen architecture brings `run_tests` into structural parity with the existing `run_quality_gates` tool/manager pattern: a thin MCP adapter, a domain manager that owns pytest protocol semantics, and a strongly typed result contract that eliminates output drift by construction.

## Scope

**In Scope:**
- `RunTestsTool` refactored to a thin MCP adapter (input validation, dependency delegation, result rendering)
- New `PytestRunner` manager owning pytest command execution, output parsing, exit-code classification, and LF-cache detection
- New `IPytestRunner` Protocol in `core/interfaces/` for DIP and testability
- New `PytestResult` frozen dataclass as the single source of truth for `summary_line`, counts, failures, and coverage
- Coverage support (issue #253 Gap 3) via `coverage: bool` input flag — materializes coverage enforcement command including `--cov-fail-under=90`; the 90% threshold value comes from the project standard documented in `pyproject.toml` comments and `QUALITY_GATES.md`
- `GetProjectPlanTool` SuggestionNote operator hint
- Documentation note for stale `.st3/projects.json`

**Out of Scope:**
- New YAML config file for run_tests (no new YAML; the 90% project standard documented in `pyproject.toml` comments and `QUALITY_GATES.md` is materialized by `RunTestsTool._build_cmd` when `coverage=True`)
- `run_quality_gates` changes
- New `NoteEntry` variants in `mcp_server/core/operation_notes.py`
- CI/CD pipeline

## Prerequisites

1. `research.md` v1.2 complete — all 8 findings documented, NoteContext migration scope (Finding 8) locked
2. `create_branch` encoding fix already committed (`git_tools.py:160` — pre-design delivery)
3. `QUALITY_GATES.md` §5 Integration Test Boundary Contract added (pre-design delivery)
4. QA design discussion v2 conclusions accepted: Option B's structural approach (thin tool + runner + typed Protocol) is justified; no new YAML config needed for pytest exit codes or coverage policy

---

## 1. Context & Requirements

### 1.1. Problem Statement

`RunTestsTool` currently violates multiple architectural principles laid down in [docs/coding_standards/ARCHITECTURE_PRINCIPLES.md](../../coding_standards/ARCHITECTURE_PRINCIPLES.md):

- **SRP:** `RunTestsTool` owns 8 responsibilities (input validation, command construction, subprocess orchestration, output parsing, exit-code semantics, LF-cache detection, NoteContext production, ToolResult rendering)
- **DIP:** the tool reaches a module-level private function (`_run_pytest_sync`); tests are forced to patch private symbols rather than inject a fake
- **Contract drift:** `summary_line` lives in two unrelated locations (`content[0].text` constructed in `execute()` and `parsed["summary_line"]` constructed in `_parse_pytest_output`), enabling the exact mismatch class issue #253 is meant to fix
- **Lost signals:** the pytest returncode is discarded (`stdout, stderr, _ = ...`), and `NoteContext` is dropped (`del context`); pytest exit codes 2, 3, 4, 5 all produce a misleading `"0 passed, 0 failed"` fallback summary
- **Missing capability:** issue #253 lists "missing coverage support" as Gap 3; coverage is currently unreachable through the MCP tool path even though `QUALITY_GATES.md` Gate 6 assigns coverage responsibility to `run_tests`

`GetProjectPlanTool` returns a bare not-found error without guiding the caller to run `initialize_project` first, causing avoidable workflow confusion.

### 1.2. Requirements

**Functional:**

- [ ] A new `PytestResult` frozen dataclass MUST be the single source of truth for `summary_line`, `passed`, `failed`, `skipped`, `errors`, `failures`, `coverage_pct`, `exit_code`, `lf_cache_was_empty`
- [ ] A new `IPytestRunner` Protocol MUST be defined in `mcp_server/core/interfaces/__init__.py` with method `run(cmd: list[str], cwd: str, timeout: int) -> PytestResult`; `PytestRunner` is the domain manager — it owns command execution, output parsing, and exit-code classification, so callers receive a fully typed result, not raw output; `PytestExecution` (stdout/stderr/returncode) is a private internal implementation detail of `PytestRunner`, not part of the Protocol surface
- [ ] A new `PytestRunner` concrete implementation MUST live in `mcp_server/managers/pytest_runner.py` and own command execution, output parsing, exit-code classification, and LF-cache detection
- [ ] `RunTestsTool` MUST accept `runner: IPytestRunner` via constructor injection; no default runner is created inside the tool — the composition root is solely responsible for constructing and injecting `PytestRunner()`
- [ ] `RunTestsTool.execute()` MUST be a thin adapter: build cmd → call runner → emit notes → render `ToolResult`
- [ ] `RunTestsTool.execute()` MUST remove the `del context` line and call `context.produce()` for all notes
- [ ] `content[0].text` MUST be `result.summary_line` literally — no parallel construction; this guarantees content[0]/content[1] cannot drift
- [ ] Pytest exit codes 0, 1 produce a normal `ToolResult`; codes 2, 3, 4 raise `ExecutionError` with a `RecoveryNote`; code 5 returns a zero-count `ToolResult` with a `SuggestionNote`; unknown non-zero codes raise `ExecutionError` with a fail-safe `RecoveryNote`
- [ ] Exit-code semantics MUST live in a typed `_EXIT_CODE_POLICY: dict[int, ExitCodePolicy]` lookup table inside `pytest_runner.py` — no if/elif chains in `RunTestsTool` or `PytestRunner.run`; `dict[int, ...]` is used rather than `dict[PytestExitCode, ...]` because `result.exit_code` is a raw int that may fall outside the known enum values
- [ ] `RunTestsInput` MUST gain a `coverage: bool = False` field; when `True`, `_build_cmd` adds `--cov=backend --cov=mcp_server --cov-branch --cov-fail-under=90`; the 90% threshold value is materialized here from the project standard (documented in `pyproject.toml` comments and `QUALITY_GATES.md`)
- [ ] `PytestResult` MUST carry `should_raise: bool` and `note: NoteEntry | None` fields stamped by `PytestRunner` via policy, so `RunTestsTool` never imports `_EXIT_CODE_POLICY`
- [ ] `PytestRunner` MUST parse the coverage report line and populate `PytestResult.coverage_pct` when present; otherwise `None`
- [ ] LF-empty-cache detection MUST be a `PytestResult.lf_cache_was_empty` flag set by the parser; `RunTestsTool` only emits the `InfoNote` when the flag is `True` and `params.last_failed_only` was `True`
- [ ] `GetProjectPlanTool` MUST produce a `SuggestionNote` before returning the not-found `ToolResult.error`, and MUST remove `del context`

**Non-Functional:**

- [ ] No new YAML config file is introduced; `pyproject.toml` remains the documented reference for the 90% threshold; `_build_cmd` is the machine-enforceable source of truth when `coverage=True`; no duplication of threshold/packages in YAML
- [ ] No new `NoteEntry` variants — all four conditions map to existing types (`RecoveryNote`, `SuggestionNote`, `InfoNote`)
- [ ] `RunTestsTool.execute()` body MUST fit in one screen and contain no pytest-protocol knowledge (exit code numbers, output substrings, parser regexes)
- [ ] All new code uses strict typing: no `dict[str, Any]` returns from public methods of `PytestRunner`; the public surface returns `PytestResult` exclusively
- [ ] Tests MUST inject a `FakePytestRunner` (implementing `IPytestRunner`) — no `unittest.mock.patch` of module-level private functions for happy-path tests
- [ ] All async tests use `asyncio_mode="strict"` with `@pytest.mark.asyncio` (already enforced by pyproject)
- [ ] Mypy/Pyright strict: no untyped defs, no ignored return values
- [ ] All new modules carry the standard file header per `CODE_STYLE.md`
- [ ] Existing `RunTestsTool` callers in tests/integration paths MUST be migrated in the same branch — this is a breaking refactor with no shim

### 1.3. Constraints

- The `content[0]` text + `content[1]` JSON order contract (established by issue #251) MUST NOT be broken — only the construction path changes
- `NoteContext` is a per-call local variable — MUST NOT be stored as instance state on `RunTestsTool`, `PytestRunner`, or `GetProjectPlanTool`
- Exit codes outside the known set (0, 1, 2, 3, 4, 5) MUST still produce a `RecoveryNote` + `ExecutionError` rather than silently falling through to the parser
- `IPytestRunner` lives in `core/interfaces/` per the architectural rule (interfaces for external systems live there, never in `managers/`)
- `PytestRunner` MUST NOT read or mutate any persisted state (no `state.json`, no caches) — it is a stateless command/parse engine
- Pytest exit code numbers MUST be encoded as a `PytestExitCode` enum, not bare integer literals scattered through code
- This is a **breaking refactor**: the `RunTestsTool.__init__` signature changes, no backward-compat shim is provided, no deprecated alias remains

---

## 2. Design Options

### 2.1. Option A — Minimal repair inside `RunTestsTool.execute()`

Capture the returncode, fix the exit-code-5 summary mismatch, add code 3, add coverage. Leave `_parse_pytest_output` and `_build_cmd` as module-level private functions. Tests continue to patch `_run_pytest_sync`.

**Pros:**
- Smallest diff
- No new files

**Cons:**
- SRP unchanged: `RunTestsTool` still owns 8 responsibilities
- DIP unchanged: tests still patch private module functions
- Contract drift unchanged: `content[0].text` and JSON `summary_line` are still independently constructed
- Fails Gate 7 architectural review (SRP, DIP)
- Adds coverage logic on top of an already-overloaded `execute()`

---

### 2.2. Option B — Thin tool + pytest runner (typed code, no config)

Introduce `PytestRunner` and `IPytestRunner`, refactor `RunTestsTool` to a thin adapter. Exit-code semantics in a typed lookup table. No new YAML.

**Pros:**
- Resolves SRP, DIP, contract-drift, missing-signals, coverage-gap simultaneously
- Aligns with the existing `RunQualityGatesTool` / `QAManager` pattern
- `_EXIT_CODE_POLICY` dict satisfies OCP — adding a new known code is one new entry, not a code change in dispatch
- Tests inject `FakePytestRunner` — public-surface testing only

**Cons:**
- One new file in `managers/`, one new Protocol in `core/interfaces/`
- Larger initial diff than Option A

---

### 2.3. Option C — Full config-backed test policy mirroring quality.yaml

Same as B, plus a new `.st3/config/test_runner.yaml` declaring exit-code-to-note mappings, recovery messages, coverage threshold, and packages.

**Pros:**
- Strongest possible Config-First story

**Cons:**
- Pytest exit codes are external library protocol, not ST3 policy — encoding them in YAML moves typed compiler-checkable knowledge into stringly-typed config
- Coverage threshold (90%) and packages (`backend`, `mcp_server`) are documented in `pyproject.toml` comments — duplicating them in YAML violates DRY; `_build_cmd` is the machine-enforced command source
- The recovery messages are developer diagnostics, not user-configurable
- Over-engineering: introduces a config-loader, schema, and validator for knowledge that does not change

---

### 2.4. Chosen — Option B ✅

Option B delivers all the architectural rigor of Option C's structural ideal (thin tool, typed result contract, injected runner) without introducing a config layer for knowledge that has no business being configurable. `_build_cmd` materializes the 90% coverage threshold from the project standard (documented in `pyproject.toml` and `QUALITY_GATES.md`) when `coverage=True`. The `PytestExitCode` enum and `_EXIT_CODE_POLICY` lookup are the SSOT for pytest protocol semantics, expressed in typed code.

---

## 3. Chosen Design

**Decision:** Thin `RunTestsTool` adapter delegating to an injected `IPytestRunner`. `PytestRunner` manager owns command execution, output parsing, exit-code classification, and LF-cache detection. `PytestResult` frozen dataclass is the single source of truth for the summary line and counts. `GetProjectPlanTool` emits `SuggestionNote` on not-found.

**Rationale:** The chosen design eliminates four root causes simultaneously by structural means rather than procedural patches. Contract drift is impossible because `content[0].text == result.summary_line` is the only construction path. Exit-code dispatch is OCP-compliant because new known codes are added as one enum entry plus one dict entry, not a branch in a method. Tests are DIP-compliant because the thread-pool seam is replaced by a Protocol. The coverage gap is closed without inventing new configuration: the runner adds the documented `pyproject.toml` flags and parses the report line.

### 3.1. Key Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | New `mcp_server/managers/pytest_runner.py` containing `PytestRunner`, `PytestExitCode`, `ExitCodePolicy`, `_EXIT_CODE_POLICY`, `PytestResult`, `FailureDetail`; `_PytestExecution` (stdout/stderr/returncode) is a private internal dataclass, not exported | Symmetry with `qa_manager.py`; co-locates pytest protocol knowledge in one module; Protocol surface exposes `PytestResult` only |
| 2 | `IPytestRunner` Protocol in `mcp_server/core/interfaces/__init__.py` | Architectural rule: interfaces for external systems live in `core/interfaces/`, never in `managers/` |
| 3 | `PytestResult` is `@dataclass(frozen=True)` | CQS: query results are immutable; eliminates accidental mutation |
| 4 | `summary_line` is always non-empty and is the canonical display string | Prevents the issue #253 drift class structurally |
| 5 | Exit code 5 returns `summary_line="no tests collected"` (matching pytest's own phrasing) | Consistency with pytest output; informative one-liner |
| 6 | Exit codes 2, 3, 4 raise `ExecutionError` with a `RecoveryNote`; code 5 returns with `SuggestionNote`; unknown codes raise with fail-safe `RecoveryNote` | Hard errors require user action (raise); empty collection is a soft miss (return); fail-safe for the unknown |
| 7 | `_EXIT_CODE_POLICY: dict[int, ExitCodePolicy]` is the SSOT for exit-code semantics; `dict[int, ...]` rather than `dict[PytestExitCode, ...]` because unknown raw codes must also be lookable via `.get()` with a fallback | OCP — adding a known code is a registration, not a method change |
| 8 | Coverage opt-in via `RunTestsInput.coverage: bool = False` | Off-by-default preserves fast feedback; on-demand for Gate 6 / PR readiness |
| 9 | `coverage=True` materializes `--cov=backend --cov=mcp_server --cov-branch --cov-fail-under=90` in `_build_cmd`; the 90% value comes from the project standard documented in `pyproject.toml` comments and `QUALITY_GATES.md` | Enforces Gate 6 threshold at the command level; no new YAML duplication; `_build_cmd` is the machine-enforceable source of truth |
| 10 | `LF-empty-cache` detection moves from `RunTestsTool.execute()` into `PytestRunner` parser as a typed `PytestResult.lf_cache_was_empty: bool` flag | Pytest output classification is runner concern, not tool concern |
| 11 | `RunTestsTool` is constructed at composition root with `PytestRunner()` injected | DIP — tool depends on the Protocol abstraction, not the concrete runner |
| 12 | Tests use a `FakePytestRunner` implementing `IPytestRunner` | No private-symbol patching for happy paths; aligns with TYPE_CHECKING_PLAYBOOK guidance |
| 13 | `GetProjectPlanTool` produces `SuggestionNote(message="Run initialize_project first to create a project plan", subject=f"issue #{n}")` before returning the error | Operator hint pattern: note tells the user what to do, error tells what was missing |
| 14 | Breaking refactor: no backward-compat shim, no deprecated alias | All callers within this repo migrated in the same branch; no external API consumers |

---

### 3.2. Module layout (new + changed)

```
mcp_server/
  core/
    interfaces/
      __init__.py                  ← add IPytestRunner Protocol
  managers/
    pytest_runner.py               ← NEW: PytestRunner, PytestResult, PytestExitCode,
                                     ExitCodePolicy, _EXIT_CODE_POLICY, FailureDetail,
                                     _PytestExecution (private internal), _parse_pytest_output (moved here)
  tools/
    test_tools.py                  ← REWRITTEN: thin RunTestsTool adapter
    project_tools.py               ← MODIFIED: GetProjectPlanTool emits SuggestionNote
  server.py                        ← MODIFIED: composition root injects PytestRunner()
tests/
  mcp_server/
    unit/
      managers/
        test_pytest_runner.py      ← NEW: parser + classification + LF detection tests
      tools/
        test_test_tools.py         ← REWRITTEN: thin-adapter tests using FakePytestRunner
        test_project_tools.py      ← AUGMENTED: SuggestionNote assertion on not-found
    fixtures/
      fake_pytest_runner.py        ← NEW: FakePytestRunner reusable fixture
```

---

### 3.3. Interface Contract — `IPytestRunner` (Protocol)

Location: `mcp_server/core/interfaces/__init__.py` (alongside `IPRStatusReader`, `IPRStatusWriter`).

```python
@runtime_checkable
class IPytestRunner(Protocol):
    """Run a pytest invocation and return a structured PytestResult."""

    def run(self, cmd: list[str], cwd: str, timeout: int) -> "PytestResult":
        """Execute pytest, parse output, classify exit code, return typed result.

        Raises:
            subprocess.TimeoutExpired: pytest exceeded the timeout
            OSError: process could not be started
        """
        ...
```

Note: `PytestResult` is imported under `TYPE_CHECKING` to avoid the `core` → `managers` cycle at runtime. The Protocol is the only contract; `PytestResult` is structurally compatible regardless of import ordering.

---

### 3.4. Data contract — `PytestResult`, `FailureDetail`, `PytestExitCode`, `ExitCodePolicy`

Location: `mcp_server/managers/pytest_runner.py`.

```python
class PytestExitCode(IntEnum):
    """Pytest exit codes per pytest CLI specification."""
    ALL_PASSED        = 0
    TESTS_FAILED      = 1
    INTERRUPTED       = 2
    INTERNAL_ERROR    = 3
    USAGE_ERROR       = 4
    NO_TESTS_COLLECTED = 5

@dataclass(frozen=True)
class FailureDetail:
    test_id: str
    location: str
    short_reason: str
    traceback: str

@dataclass(frozen=True)
class PytestResult:
    exit_code: int                        # raw int — may be unknown (not in PytestExitCode)
    summary_line: str                     # ALWAYS non-empty — canonical display string
    passed: int
    failed: int
    skipped: int
    errors: int
    failures: tuple[FailureDetail, ...]   # tuple for hashability + immutability
    coverage_pct: float | None            # None when coverage flag was not requested
    lf_cache_was_empty: bool              # True iff pytest --lf fell back to full run
    should_raise: bool                    # True for exit codes 2, 3, 4, unknown — stamped by runner policy
    note: NoteEntry | None               # RecoveryNote/SuggestionNote from policy; None for codes 0, 1

@dataclass(frozen=True)
class ExitCodePolicy:
    outcome: Literal["return", "raise"]
    note_factory: Callable[[int], NoteEntry] | None    # None for codes that produce no note (0, 1)
    summary_line_when_no_parse: str                     # used when parser found no summary
```

**Invariants** (enforced by `PytestRunner`):
- `summary_line` is never the empty string — fallback to `_EXIT_CODE_POLICY[code].summary_line_when_no_parse`
- `failures` is a tuple, not a list (frozen dataclass + hashability)
- `coverage_pct` is `None` unless the cmd contained `--cov`

---

### 3.5. SSOT — `_EXIT_CODE_POLICY`

```python
_EXIT_CODE_POLICY: dict[int, ExitCodePolicy] = {
    PytestExitCode.ALL_PASSED:         ExitCodePolicy("return", None, ""),
    PytestExitCode.TESTS_FAILED:       ExitCodePolicy("return", None, ""),
    PytestExitCode.INTERRUPTED:        ExitCodePolicy("raise",
        lambda c: RecoveryNote("Pytest was interrupted; check for hung tests or external SIGINT."),
        "pytest interrupted (exit 2)"),
    PytestExitCode.INTERNAL_ERROR:     ExitCodePolicy("raise",
        lambda c: RecoveryNote("Pytest reported an internal error; inspect stderr and pytest plugins."),
        "pytest internal error (exit 3)"),
    PytestExitCode.USAGE_ERROR:        ExitCodePolicy("raise",
        lambda c: RecoveryNote("Pytest could not start. Verify the path exists and the CLI options are valid."),
        "pytest usage error (exit 4)"),
    PytestExitCode.NO_TESTS_COLLECTED: ExitCodePolicy("return",
        lambda c: SuggestionNote("No tests matched the filter. Check markers and path."),
        "no tests collected"),
}

_UNKNOWN_CODE_POLICY = ExitCodePolicy("raise",
    lambda c: RecoveryNote(f"Pytest exited with unexpected code {c}; inspect stderr."),
    "pytest exited with unexpected code")
```

`PytestRunner.run()` looks up `_EXIT_CODE_POLICY.get(returncode, _UNKNOWN_CODE_POLICY)`. The lookup is the entire dispatch. `PytestRunner` stamps `result.should_raise` and `result.note` before returning, so `RunTestsTool` never needs to import the policy.

---

### 3.6. Interface Contract — `RunTestsTool` (thin adapter)

```python
class RunTestsInput(BaseModel):
    path: str | None = None
    scope: Literal["full"] | None = None
    markers: str | None = None
    timeout: int = 300
    last_failed_only: bool = False
    coverage: bool = False                  # NEW

    @model_validator(mode="after")
    def validate_path_or_scope(self) -> "RunTestsInput": ...   # unchanged

class RunTestsTool(BaseTool):
    name = "run_tests"
    description = "Run tests using pytest"
    args_model = RunTestsInput
    DEFAULT_TIMEOUT = 300

    def __init__(
        self,
        runner: IPytestRunner,                      # injected — no default in the tool; composition root must provide PytestRunner()
        workspace_root: str | os.PathLike[str] | None = None,
        settings: Settings | None = None,
    ) -> None:
        super().__init__()
        self._runner = runner
        base = workspace_root or (settings.server.workspace_root if settings else Path.cwd())
        self._workspace_root = str(base)

    def _build_cmd(self, params: RunTestsInput) -> list[str]:
        cmd = [sys.executable, "-m", "pytest", "--tb=short"]
        if params.path is not None:
            cmd.extend(params.path.split())
        if params.last_failed_only:
            cmd.append("--lf")
        if params.markers:
            cmd.extend(["-m", params.markers])
        if params.coverage:
            cmd.extend(["--cov=backend", "--cov=mcp_server", "--cov-branch", "--cov-fail-under=90"])
        return cmd

    async def execute(self, params: RunTestsInput, context: NoteContext) -> ToolResult:
        cmd = self._build_cmd(params)
        timeout = params.timeout or self.DEFAULT_TIMEOUT
        try:
            result = await asyncio.to_thread(self._runner.run, cmd, self._workspace_root, timeout)
        except subprocess.TimeoutExpired:
            context.produce(RecoveryNote(
                f"Tests timed out after {timeout}s. Run a smaller subset or raise the timeout."
            ))
            raise ExecutionError(f"Tests timed out after {timeout}s") from None
        except OSError as exc:
            context.produce(RecoveryNote("Verify the Python interpreter and venv are reachable."))
            raise ExecutionError(f"Failed to run tests: {exc}") from exc

        if result.note is not None:
            context.produce(result.note)             # stamped by runner via policy
        _emit_lf_cache_note(result, params, context) # cross-concern: result flag + params intent

        if result.should_raise:
            raise ExecutionError(f"pytest exited with returncode {result.exit_code}")

        return _to_tool_result(result)                      # one-liner helper
```

`_emit_lf_cache_note`, `_to_tool_result` are module-level helpers in `test_tools.py` — each <10 lines. The tool body is <30 lines and contains no pytest protocol knowledge. `_EXIT_CODE_POLICY` is **never imported** by `test_tools.py` — the runner stamps `result.should_raise` and `result.note` so the tool acts on typed outcome fields, not policy entries.

---

### 3.7. Output contract — `_to_tool_result(result: PytestResult)`

```python
def _to_tool_result(result: PytestResult) -> ToolResult:
    payload = {
        "exit_code": result.exit_code,
        "summary": {
            "passed": result.passed,
            "failed": result.failed,
            "skipped": result.skipped,
            "errors": result.errors,
        },
        "summary_line": result.summary_line,
        "failures": [asdict(f) for f in result.failures],
        "coverage_pct": result.coverage_pct,
        "lf_cache_was_empty": result.lf_cache_was_empty,
    }
    return ToolResult(content=[
        {"type": "text", "text": result.summary_line},   # literally the same field
        {"type": "json", "json": payload},
    ])
```

`content[0].text` is `result.summary_line`. The JSON `summary_line` is `result.summary_line`. They cannot drift.

---

### 3.8. Interface Contract — `GetProjectPlanTool`

```python
async def execute(self, params: GetProjectPlanInput, context: NoteContext) -> ToolResult:
    try:
        plan = self.manager.get_project_plan(issue_number=params.issue_number)
        if plan:
            return ToolResult.text(json.dumps(plan, indent=2))
        context.produce(SuggestionNote(
            "Run initialize_project first to create a project plan",
            subject=f"issue #{params.issue_number}",
        ))
        return ToolResult.error(f"No project plan found for issue #{params.issue_number}")
    except (ValueError, OSError) as exc:
        return ToolResult.error(str(exc))
```

The `del context` line is removed. The note is produced before the error return so `render_to_response` appends it on the error path.

---

### 3.9. Stale-artifact note — `.st3/projects.json`

No code change. Recorded in `research.md` Finding 6. A follow-up cleanup issue is created after implementation completes.

---

### 3.10. Test contract

All new code paths require unit tests under `tests/mcp_server/unit/`. Tests MUST follow project standards:

- `asyncio_mode = "strict"` — all async tests carry `@pytest.mark.asyncio`
- File header per `CODE_STYLE.md`; module docstring with `@layer: Tests (Unit)`
- `NoteContext()` constructed directly in the test — never mocked
- Note assertions via `context.of_type(RecoveryNote)`, `context.of_type(SuggestionNote)`, `context.of_type(InfoNote)` — type-safe, no string matching
- `ToolResult.content` assertions via index access (`result.content[0]["text"]`, `result.content[1]["json"]`)
- **No private-symbol patches** for happy-path tests of `RunTestsTool` — use `FakePytestRunner`
- Parser tests in `test_pytest_runner.py` are the only place that exercise raw pytest stdout strings

**`FakePytestRunner` shape (fixture):**

```python
@dataclass
class FakePytestRunner:
    """Test double that returns a pre-built PytestResult."""
    result: PytestResult
    captured_cmd: list[str] | None = None

    def run(self, cmd: list[str], cwd: str, timeout: int) -> PytestResult:
        self.captured_cmd = cmd
        return self.result
```

**RunTestsTool — required test cases (using `FakePytestRunner`):**

| # | Scenario | `FakePytestRunner.result` exit_code | Expected outcome | Note assertions |
|---|----------|------------------------------------|------------------|-----------------|
| 1 | All tests pass | 0 | `ToolResult` content[0]==summary_line | none |
| 2 | Some tests fail | 1 | `ToolResult` with failures in content[1] | none |
| 3 | Pytest interrupted | 2 | raises `ExecutionError` | 1× `RecoveryNote` |
| 4 | Pytest internal error | 3 | raises `ExecutionError` | 1× `RecoveryNote` |
| 5 | Pytest usage error | 4 | raises `ExecutionError` | 1× `RecoveryNote` |
| 6 | No tests collected | 5 | returns `ToolResult` with `summary_line="no tests collected"` | 1× `SuggestionNote` |
| 7 | Unknown exit code (99) | 99 | raises `ExecutionError` | 1× `RecoveryNote` (fail-safe) |
| 8 | LF cache empty + last_failed_only=True | 0, `lf_cache_was_empty=True` | normal `ToolResult` | 1× `InfoNote` |
| 9 | LF cache populated + last_failed_only=True | 0, `lf_cache_was_empty=False` | normal `ToolResult` | none |
| 10 | last_failed_only=False, lf flag True | 0, `lf_cache_was_empty=True` | normal `ToolResult` | none (flag ignored unless requested) |
| 11 | coverage=True | 0, `coverage_pct=92.5` | content[1].json.coverage_pct == 92.5 | none |
| 12 | coverage=False | 0, `coverage_pct=None` | content[1].json.coverage_pct is None | none |
| 13 | content/summary parity invariant | any | assert `content[0]["text"] == content[1]["json"]["summary_line"]` | n/a |
| 14 | timeout | n/a — runner raises `TimeoutExpired` | raises `ExecutionError` | 1× `RecoveryNote` |
| 15 | OSError on subprocess start | n/a — runner raises `OSError` | raises `ExecutionError` | 1× `RecoveryNote` |
| 16 | `_build_cmd` adds `--cov` packages when coverage=True | n/a | `runner.captured_cmd` contains `--cov=backend`, `--cov=mcp_server`, `--cov-branch` | n/a |
| 17 | `_build_cmd` adds `--cov-fail-under=90` when coverage=True | n/a | `runner.captured_cmd` contains `--cov-fail-under=90` (Gate 6 threshold enforced) | n/a |
| 18 | `_build_cmd` omits all `--cov*` when coverage=False | n/a | `runner.captured_cmd` contains no `--cov*` flag and no `--cov-fail-under` | n/a |

**PytestRunner — required test cases (parser unit tests, raw stdout fixtures):**

| # | Scenario | Assertion |
|---|----------|-----------|
| 1 | All-passed stdout | `passed=N, failed=0, errors=0, summary_line` non-empty |
| 2 | Failing tests stdout | `failures` populated with `FailureDetail` per FAILED line; tracebacks attached |
| 3 | Skipped tests stdout | `skipped=N` |
| 4 | Errors-during-collection stdout | `errors=N` |
| 5 | Coverage report line present | `coverage_pct` parsed |
| 6 | LF empty fallback message in stdout | `lf_cache_was_empty=True` |
| 7 | Empty/unparseable stdout | `summary_line` falls back to policy; never empty |
| 8 | Exit code 5 path | `summary_line == "no tests collected"` |

**GetProjectPlanTool — required test cases:**

| # | Scenario | Expected result | Note assertions |
|---|----------|----------------|-----------------|
| 1 | Plan exists | `ToolResult.text(json)` | none |
| 2 | Plan not found | `ToolResult.error(...)` | 1× `SuggestionNote` with subject == `f"issue #{n}"` |
| 3 | Manager raises `ValueError` | `ToolResult.error(...)` | none |

---

### 3.11. Composition root impact

`mcp_server/server.py` builds the tool list at startup. Change (within the existing `self.tools = [...]` list):

```python
# BEFORE
RunTestsTool(settings=settings),

# AFTER
RunTestsTool(runner=PytestRunner(), settings=settings),
```

`PytestRunner` is imported at the top of `server.py` alongside `RunTestsTool`. All other call sites (none currently exist outside the composition root) are migrated in the same branch.

---

### 3.12. Quality gate compliance map

| Gate | Coverage by this design |
|------|-------------------------|
| Gate 0 (ruff format) | All new modules formatted; pre-commit handles enforcement |
| Gate 1 (ruff lint) | New modules pass strict select |
| Gate 2 (import placement) | All imports top-level (no in-function imports) |
| Gate 3 (line length) | Tables and code blocks within 100 chars |
| Gate 4 (type checking) | `PytestResult`, `IPytestRunner`, `_EXIT_CODE_POLICY` all strictly typed; no `dict[str, Any]` on public surface |
| Gate 5 (tests passing) | All 18 + 8 + 3 = 29 new test cases listed in §3.10 |
| Gate 6 (coverage ≥ 90%) | New `pytest_runner.py` and refactored `test_tools.py` tested at branch level; coverage flag itself exercises the cmd path |
| Gate 7 (architectural review) | SRP (each class one responsibility), DIP (Protocol injection), OCP (`_EXIT_CODE_POLICY` table), Config-First (90% threshold documented in `pyproject.toml`/`QUALITY_GATES.md`; machine-enforced via `_build_cmd` — no policy duplicated in code or new YAML), Contract-Driven (`PytestResult` + `IPytestRunner`), DRY (one `summary_line` source), Fail-Fast (unknown exit codes raise) |

---

## Related Documentation
- **[docs/development/issue253/research.md][related-1]**
- **[mcp_server/tools/test_tools.py][related-2]**
- **[mcp_server/tools/project_tools.py][related-3]**
- **[mcp_server/core/operation_notes.py][related-4]**
- **[mcp_server/core/interfaces/__init__.py][related-5]**
- **[mcp_server/managers/qa_manager.py][related-6]**
- **[mcp_server/tools/quality_tools.py][related-7]**
- **[docs/coding_standards/QUALITY_GATES.md][related-8]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-9]**
- **[docs/coding_standards/CODE_STYLE.md][related-10]**
- **[docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md][related-11]**
- **[pyproject.toml][related-12]**

<!-- Link definitions -->

[related-1]: docs/development/issue253/research.md
[related-2]: mcp_server/tools/test_tools.py
[related-3]: mcp_server/tools/project_tools.py
[related-4]: mcp_server/core/operation_notes.py
[related-5]: mcp_server/core/interfaces/__init__.py
[related-6]: mcp_server/managers/qa_manager.py
[related-7]: mcp_server/tools/quality_tools.py
[related-8]: docs/coding_standards/QUALITY_GATES.md
[related-9]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-10]: docs/coding_standards/CODE_STYLE.md
[related-11]: docs/coding_standards/TYPE_CHECKING_PLAYBOOK.md
[related-12]: pyproject.toml

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-25 | Agent | Initial draft — minimal in-tool returncode dispatch; rejected by QA review |
| 2.0 | 2026-04-25 | Agent | Full rewrite: thin RunTestsTool adapter, new PytestRunner manager, IPytestRunner Protocol, PytestResult typed contract eliminating summary_line drift, coverage support, exit codes 2/3/4/5 + unknown handled via _EXIT_CODE_POLICY lookup, complete test contract using FakePytestRunner; rejected by QA review |
| 2.1 | 2026-04-25 | Agent | QA corrections: IPytestRunner returns PytestResult (not PytestExecution); _PytestExecution internal; coverage=True materializes --cov-fail-under=90 in _build_cmd; ExitCodePolicy.note_factory typed as Callable \| None; PytestResult gains should_raise+note so RunTestsTool never imports _EXIT_CODE_POLICY; test case 17 added for fail-under assertion; "Direction C" wording replaced with "Option B"; date metadata corrected; rejected by QA review |
| 2.2 | 2026-04-25 | Agent | QA corrections: --cov-fail-under=90 added to §3.6 _build_cmd pseudocode; constructor contract fixed (no default, composition root injects); Out of Scope wording clarified (no SSOT claim for pyproject comment); _EXIT_CODE_POLICY typed as dict[int, ExitCodePolicy] consistently; §3.11 server snippet corrected to existing list form; rejected by QA review |
| 2.3 | 2026-04-25 | Agent | QA GO — doc-nits: Option C cons replaced "already in pyproject.toml" with accurate documented-standard wording; Gate 7 Config-First entry clarified; status set to APPROVED |

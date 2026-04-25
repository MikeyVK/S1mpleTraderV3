<!-- docs\development\issue253\design.md -->
<!-- template=design version=5827e841 created=2026-04-25T11:15Z updated= -->
# run_tests Reliability — Returncode Handling, NoteContext Migration, Operator Hints

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-04-25

---

## Purpose

Define finalized interface contracts for all changes in issue #253 so that TDD implementation can proceed without design ambiguity.

## Scope

**In Scope:**
RunTestsTool (returncode capture, exit-code dispatch, NoteContext migration), GetProjectPlanTool (SuggestionNote operator hint), .st3/projects.json stale-artifact documentation note

**Out of Scope:**
Coverage support (Gap 3, deferred to follow-up issue), run_quality_gates, NoteContext protocol (no new note variants), CI/CD pipeline

## Prerequisites

Read these first:
1. research.md v1.2 complete — all 8 findings documented, NoteContext migration scope (Finding 8) locked
2. create_branch encoding fix already committed (git_tools.py:160 — pre-design delivery)
3. QUALITY_GATES.md §5 Integration Test Boundary Contract added (pre-design delivery)
---

## 1. Context & Requirements

### 1.1. Problem Statement

RunTestsTool discards the pytest returncode (stdout, stderr, _ = ...) and drops the NoteContext (del context). This means pytest exit codes 2, 4, and 5 — which signal hard errors or empty-collection conditions — all produce the same misleading '0 passed, 0 failed' fallback summary. GetProjectPlanTool returns a bare not-found error without guiding the caller to run initialize_project first, causing unnecessary workflow confusion.

### 1.2. Requirements

**Functional:**
- [ ] RunTestsTool MUST capture the pytest returncode (change tuple unpacking from _ to returncode)
- [ ] RunTestsTool MUST dispatch on returncode BEFORE calling the parser: codes 2 and 4 raise ExecutionError with a RecoveryNote; code 5 returns a zero-count ToolResult with a SuggestionNote; code 0 or 1 use the existing parser path unchanged
- [ ] RunTestsTool MUST detect the last-failed-only empty-cache condition and produce an InfoNote when last_failed_only=True and the full suite ran as fallback
- [ ] RunTestsTool MUST remove the 'del context' line and use context.produce() for all notes
- [ ] GetProjectPlanTool MUST produce a SuggestionNote before returning the not-found ToolResult.error when no plan exists for the requested issue number
- [ ] GetProjectPlanTool MUST remove the 'del context' line
- [ ] ToolResult.content order MUST remain unchanged: item 0 = text summary line, item 1 = JSON payload; NoteContext notes appear as item 2 appended by render_to_response

**Non-Functional:**
- [ ] No new NoteEntry variants — all four conditions map to existing types (RecoveryNote, SuggestionNote, InfoNote)
- [ ] The existing _parse_pytest_output function and _build_cmd method are unchanged
- [ ] Existing client-side consumers that read content[0] and content[1] continue to work without modification
- [ ] All new code paths covered by unit tests using asyncio_mode=strict and pytest.mark.asyncio
- [ ] Mypy strict: no untyped defs, no ignored return values in the modified execute methods

### 1.3. Constraints

- The `content[0]` text + `content[1]` JSON order contract (established by issue #251) MUST NOT be broken
- `NoteContext` is a per-call local variable — MUST NOT be stored as instance state on `RunTestsTool` or `GetProjectPlanTool`
- Exit codes outside the known set (0, 1, 2, 4, 5) MUST still produce a `RecoveryNote` + `ExecutionError` rather than silently falling through to the parser
---

## 2. Design Options

### 2.1. Option A — Inline diagnostic text into the summary line

Append human-readable context directly to the `summary_line` text when a non-zero exit code is detected. For example: `"pytest exited with code 4 — bad path or usage error"`.

**Pros:**
- Minimal code change: only `_run_pytest_sync` return and string formatting

**Cons:**
- Breaks the parser-friendly contract: `content[0]` is no longer a machine-readable summary line
- Existing consumers that parse the summary line (e.g. test assertions on `content[0]`) would need updating
- Does not use the established `NoteContext` inter-tool messaging pattern — architectural deviation
- No machine-readable signal for note consumers; all context is embedded in an opaque string

---

### 2.2. Option B — Returncode-first dispatch with NoteContext notes ✅ CHOSEN

Capture the returncode from the thread-pool call, dispatch on it before the parser runs, and emit typed notes via `context.produce()`. The parser path (codes 0/1) is untouched. Hard-failure codes raise `ExecutionError` with a `RecoveryNote`. Code 5 returns a zero-count `ToolResult` with a `SuggestionNote`. The LF-empty-cache condition produces an `InfoNote` appended to the normal result.

**Pros:**
- `content[0]` and `content[1]` are structurally unchanged for codes 0/1 — no breaking change for existing consumers
- All diagnostic signals are machine-readable typed notes via the established NoteContext pattern
- No new `NoteEntry` variants required
- Blast radius confined to `execute()` and the unit tests for the new code paths

**Cons:**
- Slightly more branching in `execute()` than Option A

---

## 3. Chosen Design

**Decision:** Returncode-first dispatch in RunTestsTool.execute with NoteContext notes; SuggestionNote in GetProjectPlanTool on not-found

**Rationale:** The NoteContext interface is the established architectural pattern for secondary, machine-readable, user-visible signals layered onto a primary ToolResult. Inlining hints into the text block would break the parser-friendly two-entry content contract. All four signal conditions (hard error, usage error, empty collection, LF-cache miss) map cleanly to existing typed note variants without requiring new types. The dispatch-before-parse design keeps the parser path for codes 0/1 identical to the current implementation, minimising blast radius.

### 3.1. Key Design Decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | Capture `returncode` instead of discarding it | Root cause of Gap 1 and Gap 2 — without the returncode the parser cannot distinguish failure from empty collection |
| 2 | Dispatch BEFORE parser for codes ≠ 0/1 | Parser output is untrustworthy for error exits; early dispatch prevents misleading fallback summary |
| 3 | Code 2/4 → `RecoveryNote` + raise `ExecutionError` | Hard errors require user action; raising is the correct semantic (tool cannot continue) |
| 4 | Code 5 → `SuggestionNote` + return zero-count result | Empty collection is a valid filtered run, not a hard error; caller should revise the filter |
| 5 | Unknown non-zero codes → `RecoveryNote` + raise `ExecutionError` | Fail-safe: unknown exit codes treated as hard errors rather than silently misreported |
| 6 | LF-empty-cache → `InfoNote` on the normal (code 0/1) path | UX trust gap only; full fallback run completed successfully; no exception warranted |
| 7 | `GetProjectPlanTool` emits `SuggestionNote` before not-found error | Operator hint pattern: the note tells the user what to do, the error tells what was missing |

---

### 3.2. Interface Contract — `RunTestsTool.execute`

**Structural change (tuple unpacking):**
```python
# BEFORE (broken):
stdout, stderr, _ = await asyncio.to_thread(_run_pytest_sync, cmd, ...)
# del context  # Not used  ← DELETE this line

# AFTER:
stdout, stderr, returncode = await asyncio.to_thread(_run_pytest_sync, cmd, ...)
# context is now used below — do NOT del
```

**Exit-code dispatch table (runs before `_parse_pytest_output`):**

| Exit code | Condition | Note variant | Raise or return |
|-----------|-----------|--------------|-----------------|
| `0` | All tests passed | — | Return via parser path |
| `1` | Tests ran, some failed | — | Return via parser path |
| `2` | Pytest interrupted or internal error | `RecoveryNote("Pytest reported an internal error; inspect stderr.")` | Raise `ExecutionError("pytest exited with returncode 2")` |
| `4` | Usage error (bad path, bad option) | `RecoveryNote("Pytest could not start. Verify the path exists and is readable.")` | Raise `ExecutionError("pytest exited with returncode 4: bad path or usage error")` |
| `5` | No tests collected after filtering | `SuggestionNote("No tests matched the filter. Check markers and path.")` | Return `ToolResult` with zero-count content (see §3.3) |
| other | Unexpected | `RecoveryNote(f"Pytest exited with unexpected code {returncode}; inspect stderr.")` | Raise `ExecutionError(f"pytest exited with returncode {returncode}")` |

**Zero-count ToolResult shape for exit code 5:**
```python
_EMPTY_SUMMARY = {"passed": 0, "failed": 0}
return ToolResult(
    content=[
        {"type": "text", "text": "0 passed, 0 failed"},
        {"type": "json", "json": {"summary": _EMPTY_SUMMARY, "summary_line": ""}},
    ]
)
```

---

### 3.3. Interface Contract — LF-empty-cache detection

Applied on the normal (code 0 or 1) path, AFTER the parser call, ONLY when `params.last_failed_only is True`:

```python
_LF_EMPTY_PATTERN = "no previously failed tests, running all"

if params.last_failed_only and _LF_EMPTY_PATTERN in stdout.lower():
    context.produce(InfoNote("Last-failed cache was empty; ran full selection instead."))
```

`_LF_EMPTY_PATTERN` is a module-level constant. The `.lower()` normalises pytest output casing.

---

### 3.4. Interface Contract — `GetProjectPlanTool.execute`

```python
# BEFORE:
del context  # Not used
...
if plan:
    return ToolResult.text(json.dumps(plan, indent=2))
return ToolResult.error(f"No project plan found for issue #{params.issue_number}")

# AFTER:
# del context  ← DELETE this line
...
if plan:
    return ToolResult.text(json.dumps(plan, indent=2))
context.produce(SuggestionNote(
    "Run initialize_project first to create a project plan",
    subject=f"issue #{params.issue_number}",
))
return ToolResult.error(f"No project plan found for issue #{params.issue_number}")
```

The `SuggestionNote` is produced BEFORE returning the error so it is appended by `render_to_response` on the error path.

---

### 3.5. Stale-artifact note — `.st3/projects.json`

No code change. The finding is recorded in `research.md` Finding 6. The file MUST NOT be removed during this branch. A follow-up documentation or cleanup issue should be created after implementation is complete.

---

### 3.6. Test Contract

All new code paths require unit tests. Tests MUST follow project standards:

- `asyncio_mode = "strict"` — mark all async tests with `@pytest.mark.asyncio`
- Use `unittest.mock.AsyncMock` / `MagicMock` for `_run_pytest_sync` thread-pool calls
- `NoteContext` is constructed directly in tests (`NoteContext()`) — not mocked
- Assertions on notes use `context.of_type(RecoveryNote)` etc. for type-safe access
- `ToolResult.content` assertions use index access (`result.content[0]`, `result.content[1]`)

**Test cases required per exit code (RunTestsTool):**

| Scenario | Expected exception / result | Note assertions |
|----------|----------------------------|-----------------|
| returncode=0, tests pass | `ToolResult` with summary | no notes |
| returncode=1, tests fail | `ToolResult` with failures in content[1] | no notes |
| returncode=2 | raises `ExecutionError` | 1× `RecoveryNote` in context |
| returncode=4 | raises `ExecutionError` | 1× `RecoveryNote` in context |
| returncode=5 | returns zero-count `ToolResult` | 1× `SuggestionNote` in context |
| returncode=99 (unknown) | raises `ExecutionError` | 1× `RecoveryNote` in context |
| last_failed_only=True, LF cache empty | normal `ToolResult` | 1× `InfoNote` in context |
| last_failed_only=True, LF cache populated | normal `ToolResult` | no notes |

**Test cases required (GetProjectPlanTool):**

| Scenario | Expected result | Note assertions |
|----------|----------------|-----------------|
| plan exists | `ToolResult.text(json)` | no notes |
| plan not found | `ToolResult.error(...)` | 1× `SuggestionNote` in context |

## Related Documentation
- **[docs/development/issue253/research.md][related-1]**
- **[mcp_server/tools/test_tools.py][related-2]**
- **[mcp_server/tools/project_tools.py][related-3]**
- **[mcp_server/core/operation_notes.py][related-4]**
- **[docs/coding_standards/QUALITY_GATES.md][related-5]**

<!-- Link definitions -->

[related-1]: docs/development/issue253/research.md
[related-2]: mcp_server/tools/test_tools.py
[related-3]: mcp_server/tools/project_tools.py
[related-4]: mcp_server/core/operation_notes.py
[related-5]: docs/coding_standards/QUALITY_GATES.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |
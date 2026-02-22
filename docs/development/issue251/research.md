<!-- docs\development\issue251\research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-22T17:36Z updated=2026-02-22 -->
# Issue #251 Research: Refactor run_quality_gates — venv pytest, structured output, smart scope

**Status:** COMPLETE  
**Version:** 1.0  
**Last Updated:** 2026-02-22

---

## Purpose

Establish a factual baseline and design decisions before planning and TDD cycles for this refactor.

## Scope

**In Scope:**
QAManager, RunQualityGatesTool, quality.yaml active_gates, state.json schema extension, git-diff scope resolution, run_tests reference pattern

**Out of Scope:**
CI/CD pipeline changes, non-Python gate support, frontend changes, pyproject.toml gate config migration

## Prerequisites

Read these first:
1. Issue #251 read and understood
2. `run_quality_gates(files=[])` executed — output observed (venv bug confirmed, double JSON output confirmed)
3. `run_tests` reference implementation read in [mcp_server/tools/test_tools.py](../../../../mcp_server/tools/test_tools.py)
4. User decisions recorded (see Section 6)

---

## Problem Statement

`run_quality_gates` has three confirmed bugs and two architectural weaknesses:

1. **Bug: system pytest** — Gate 5/6 resolve to `C:\...\Python313\Scripts\pytest.EXE` instead of the venv. `addopts = -n auto` in `pyproject.toml` requires `pytest-xdist` which only exists in the venv. Exit code 4.
2. **Bug: silent truncation** — Gate 0 (`ruff format --diff`) caps stdout at `MAX_OUTPUT_LINES=50` / `MAX_OUTPUT_BYTES=5120`. Truncation flag is buried in `output.truncated` (per-gate), not surfaced in `issues[]` or summary.
3. **Bug: double JSON output** — The complete JSON blob appears twice in the MCP response.
4. **Weakness: mode bifurcation** — The `files=[]` vs `files=[...]` split exists solely to handle pytest being a repo-scoped gate mixed with file-scoped gates. Removing pytest from QG eliminates the need for this split.
5. **Weakness: no summary_line / output too large** — Agent receives 3-8 KB of JSON per invocation. `run_tests` proves a `summary_line` + `failures[]` approach is sufficient for agent consumption. QG emits `text_output` appended at the end of the blob, not exposed as a top-level MCP text content item.

## Research Goals

- Document all current bugs with reproduction steps and root cause
- Establish the reference implementation pattern from `run_tests` (issue #103)
- Validate the decision to remove pytest/coverage from `run_quality_gates`
- Design the scope resolution strategy: `auto` (git-diff baseline), `branch`, `project`, explicit files
- Design the baseline state machine: when does all-green reset the baseline SHA
- Define the failure-narrowing re-run strategy: `failed_files ∪ changed_since_last_run`
- Define the new output model: `summary_line` first, then structured `violations[]`
- Identify all changes needed in `QAManager`, `RunQualityGatesTool`, `state.json`, `quality.yaml`

## Related Documentation
- **[docs/reference/mcp/tools/quality.md](../../../../docs/reference/mcp/tools/quality.md)**
- **[docs/development/issue103/](../../../../docs/development/issue103/)**
- **[mcp_server/tools/test_tools.py](../../../../mcp_server/tools/test_tools.py)**
- **[mcp_server/managers/qa_manager.py](../../../../mcp_server/managers/qa_manager.py)**
- **[mcp_server/tools/quality_tools.py](../../../../mcp_server/tools/quality_tools.py)**
- **[.st3/quality.yaml](../../../../.st3/quality.yaml)**
- **[.st3/state.json](../../../../.st3/state.json)**

---

## Investigation 1: Bug — System pytest instead of venv pytest

### Finding: `_resolve_command` does not handle bare `pytest` executable

**Root cause** in [mcp_server/managers/qa_manager.py](../../../../mcp_server/managers/qa_manager.py):

```python
def _resolve_command(self, base_command: list[str], files: list[str]) -> list[str]:
    cmd = list(base_command)
    if cmd and cmd[0] == "python":           # ← only replaces "python"
        venv_python = Path(__file__).parents[2] / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            cmd[0] = str(venv_python)
        else:
            cmd[0] = sys.executable

    if cmd and cmd[0] in {"pyright", "pyright.exe"}:
        cmd[0] = _venv_script_path(_pyright_script_name())

    return [*cmd, *files]
```

The gate commands in `quality.yaml` for Gate 5 and Gate 6 start with `"pytest"` (bare binary):

```yaml
gate5_tests:
  execution:
    command: ["pytest", "tests/", "--tb=short"]
```

`_resolve_command` does not handle `cmd[0] == "pytest"` → `shutil.which("pytest")` resolves to `C:\...\Python313\Scripts\pytest.EXE`. The venv `pytest-xdist` plugin is unavailable → `-n auto` from `pyproject.toml addopts` fails with exit code 4.

**Confirmed by live run output:**
```json
"environment": {
  "python_version": "3.13.5",
  "tool_path": "C:\\Users\\miche\\AppData\\Local\\Programs\\Python\\Python313\\Scripts\\pytest.EXE"
}
```

**Fix options:**

| Option | Description |
|--------|-------------|
| A | Change `quality.yaml` Gate 5/6 commands to `["python", "-m", "pytest", ...]` — `_resolve_command` already handles `python` |
| B | Remove Gate 5/6 from `active_gates` (agreed with user — see Section 6) |
| C | Extend `_resolve_command` to also handle bare `pytest` → `sys.executable -m pytest` |

**Decision:** Option B is primary (pytest out of QG per Section 6). Option A is the correct fallback for any future pytest gate re-introduction. Option C is defense-in-depth. Implement B + A as a documentation note.

---

## Investigation 2: Bug — Silent truncation (Gate 0 ruff format diff)

### Finding: truncation flag buried in `output.truncated`, not surfaced to agent

Constants in `qa_manager.py`:

```python
MAX_OUTPUT_LINES = 50
MAX_OUTPUT_BYTES = 5120
```

**Which gates are affected:**

| Gate | `produces_json` | Truncation impact |
|------|-----------------|-------------------|
| Gate 0: ruff format | `false` | ⚠️ Text diff truncated — agent sees partial diff |
| Gate 1: ruff strict lint | `true` | ✅ JSON parsed into `issues[]` — no truncation |
| Gate 2: imports | `true` | ✅ JSON parsed — no truncation |
| Gate 3: line length | `true` | ✅ JSON parsed — no truncation |
| Gate 4: mypy | `exit_code` text | ⚠️ Text output truncated |
| Gate 4b: pyright | `json_field` | ✅ JSON parsed — no truncation |

**Actual truncation behavior:** When truncated, `output.truncated = true` and `output.details` gets `[truncated to 50 lines / 5120 bytes per stream]` appended — but this is inside the per-gate `output` dict. The `issues[]` list contains only `[{message: "Gate failed with exit code N"}]`. An agent relying on `issues[]` for violations sees nothing actionable.

**Root cause:** The `_build_output_capture` method caps text output, which is correct for reducing noise. But for gates that do NOT produce JSON (Gate 0, Gate 4 mypy text mode), the raw text diff IS the structured output — there is no violation list to fall back to.

**Fix:** For Gate 0 (ruff format), use `ruff format --check` with a separate `ruff format --output-format=json` pass to produce structured output, OR increase limits significantly and emit an explicit truncation issue in `issues[]`. Given the agreed removal of reliance on raw text and the introduction of `violations[]`, the cleanest fix is to implement a `mode="fix"` that runs `ruff format` automatically, making Gate 0 failures self-healing.

---

## Investigation 3: Bug — Double JSON output in MCP response

### Finding: `ToolResult.json_data` produces content that is serialized twice by server

**Observed:** The full JSON blob (3–8 KB) appears twice verbatim in the MCP response back to the agent.

**Likely cause:** Same class of bug fixed in Issue #103 / server.py — `_convert_tool_result_to_content` adds a text item for the JSON, and the JSON itself is also included as a separate content block. The `run_tests` fix returned:

```python
return ToolResult(
    content=[
        {"type": "json", "json": parsed},
        {"type": "text", "text": summary_line},
    ]
)
```

The new `run_quality_gates` output model should follow this exact pattern — the double-output bug will be resolved as a side effect.

---

## Investigation 4: Architecture — Mode bifurcation (files=[] vs files=[...])

### Finding: the two-mode design is a workaround for pytest being in QG

**Current modes:**

| Mode | Trigger | Runs | Skips |
|------|---------|------|-------|
| `project-level` | `files=[]` | Gate 5 (pytest), Gate 6 (coverage) | Gates 0-4 (static analysis) |
| `file-specific` | `files=[...]` | Gates 0-4 (static analysis) | Gate 5, Gate 6 |

**Why this exists:** pytest is a repo-scoped tool — it does not accept file arguments in the same way ruff does. The only reason for two modes is to separate "run pytest" from "run static analysis on these files".

**If pytest is removed from `active_gates`:**
- `files=[]` becomes meaningless — every call would skip all gates (no files → nothing to analyze)
- The mode field can be removed or repurposed
- All calls provide files, either explicitly or via scope resolution

**Residual question:** Should `scope="project"` discover all Python files internally, or should the caller still pass them? **Answer:** Internal discovery — `QAManager._discover_project_files()` globs `backend/**/*.py` + `mcp_server/**/*.py` + `tests/**/*.py`. The caller passes `scope` enum, not file paths.

---

## Investigation 5: Architecture — Output model (no summary_line, too much data)

### Finding: output blob is 3–8 KB; no top-level text content item

**Current output structure:**
```json
{
  "version": "2.0",
  "mode": "...",
  "files": [...],
  "summary": { "passed": 0, "failed": 2, "skipped": 6, ... },
  "gates": [ { /* full gate with command, environment, output, hints */ } ],
  "overall_pass": false,
  "timings": { ... },
  "text_output": "..."     ← appended at end, not a MCP text content item
}
```

**Reference: `run_tests` output model (issue #103):**
```python
return ToolResult(
    content=[
        {"type": "json", "json": parsed},    # compact: summary + failures[] only
        {"type": "text", "text": summary_line},  # "3 passed in 1.2s"
    ]
)
```

The agent reads the `text` content item first — it's the summary line. Only when there are failures does the agent inspect the `json` content.

**Target output model for `run_quality_gates`:**
```python
return ToolResult(
    content=[
        {"type": "json", "json": compact_result},  # summary + violations[] only
        {"type": "text", "text": summary_line},     # "✅ 6/6 gates passed (42 files)" or "❌ 2/6 failed: Gate 0, Gate 1"
    ]
)
```

**Compact result structure (agent-optimized):**
```json
{
  "overall_pass": false,
  "summary_line": "❌ 2/6 gates failed — 14 violations (8 auto-fixable)",
  "summary": { "passed": 4, "failed": 2, "skipped": 0 },
  "gates": [
    {
      "name": "Gate 0: Ruff Format",
      "passed": false,
      "violations": [
        { "file": "mcp_server/tools/quality_tools.py", "line": 42, "code": "W291", "message": "...", "fixable": true }
      ]
    }
  ],
  "scope": { "mode": "auto", "files_checked": 3, "baseline_sha": "abc123" }
}
```

**What is removed from current output per gate:**
- `command` object (executable, args, cwd, environment) — moves to artifact log only
- `output.stdout/stderr` — moves to artifact log only
- `hints` — useful but verbose; keep only for failed gates, max 1 hint per gate
- `duration_ms` — keep in `timings` top-level but not per-gate in compact view

---

## Investigation 6: Design — Smart scope resolution

### Finding: git-based scope is feasible with 3 subprocess calls

**Target scope modes:**

| Mode | Trigger | Files resolved from |
|------|---------|---------------------|
| `auto` | default | `git diff <baseline_sha>..HEAD --name-only *.py` ∪ `state.quality_gates.failed_files` |
| `branch` | explicit / first run (no baseline) | `git diff <parent_branch>..HEAD --name-only *.py` |
| `project` | explicit / pre-PR | All `.py` files in `backend/`, `mcp_server/`, `tests/` |
| `files=[...]` | explicit | Caller-provided list (backward compat) |

**Git commands required:**

```bash
git rev-parse HEAD                                    # get current SHA
git diff <sha>..HEAD --name-only -- "*.py"           # changed files since baseline
git status --porcelain -- "*.py"                     # untracked new files
```

**Edge cases:**
1. **Untracked files** — `git diff` misses new `.py` files not yet staged. Supplement with `git status --porcelain | grep "^\?\? .*\.py"`.
2. **Renamed files** — `git diff --name-only --diff-filter=AMRTD` catches renames. Ruff/mypy need the new filename.
3. **No baseline (first run)** — fallback to `scope="branch"`. Parent branch known from `state.json`.
4. **Empty diff** — if `baseline_sha == HEAD`, no files changed → check `failed_files` only. If both empty, return early with `overall_pass=true` (nothing to check).

**Implementation location:** `QAManager._resolve_scope(scope: str, state: QGState) -> list[str]` — pure function, easy to test.

---

## Investigation 7: Design — Baseline state machine

### Finding: state.json extension adequate; global baseline (not per-gate)

**State stored in `.st3/state.json` (branch-scoped):**

```json
{
  "branch": "refactor/251-...",
  "quality_gates": {
    "baseline_sha": "abc1234",
    "failed_files": ["mcp_server/tools/quality_tools.py"]
  }
}
```

**State transitions:**

```
[no baseline_sha]
      │
      ▼
  First run → scope="branch" (diff vs parent_branch)
      │
      ├─ RED (any gate fails) → baseline_sha unchanged, failed_files = union(prev_failed, new_failed)
      │
      └─ GREEN (all gates pass) → baseline_sha = HEAD, failed_files = []

[has baseline_sha]
      │
      ▼
  Auto run → scope = git_diff(baseline_sha..HEAD) ∪ failed_files
      │
      ├─ RED → failed_files = union(prev_failed, new_failed_from_this_run)
      │         baseline_sha unchanged
      └─ GREEN → baseline_sha = HEAD, failed_files = []
```

**Why global, not per-gate:**
- Fixing Gate 0 may introduce a Gate 1 violation (e.g., after `ruff format` auto-fix, line length changes)
- Per-gate baselines create false confidence: "Gate 0 passed last commit" but Gate 0 hasn't been re-checked since Gate 1 was fixed
- Global baseline is conservative and correct: all gates must agree before baseline advances

**Re-run scope (failure narrowing):**

`scope = git_diff(baseline..HEAD) ∪ failed_files`

Example:
- Baseline: commit A. Files checked last run: {A.py, B.py, C.py}
- A.py failed Gate 1. B.py passed. C.py passed.
- Developer fixes A.py (commit B) and also edits B.py.
- Next run scope: `git_diff(A..B) = {A.py, B.py}` ∪ `failed_files = {A.py}` = **{A.py, B.py}**
- C.py is NOT re-checked (unchanged since baseline, always passed)

---

## Investigation 8: Design — Pytest removal from quality gates

### Finding: removing Gate 5/6 from active_gates is a config-only change

**Required changes:**

1. Remove `gate5_tests` and `gate6_coverage` from `active_gates` in `.st3/quality.yaml`
2. Keep gate definitions in the catalog (they may be useful for documentation / future use)
3. Update `_is_pytest_gate()` — no longer needed for skip logic (can be kept for future safety)
4. Remove the `files=[]` project-level mode — after pytest removal, `files=[]` would skip everything
5. Update the MCP tool description

**Rationale (ratified by user):**

| Concern | `run_quality_gates` | `run_tests` |
|---------|---------------------|-------------|
| Question | Is this code well-written? | Does this code do what it should? |
| Scope | Modified/failed files | Test files (filtered by path/markers) |
| Speed | Fast (seconds per file) | Slow (full suite = minutes) |
| During TDD | On every refactor | On every green cycle |
| Pre-PR | Project scope | Full suite (scope=full) |

Mixing these two concerns in one tool created the mode bifurcation, broke the single-responsibility principle, and introduced the venv pytest bug as a consequence.

---

## Section 6: User Decisions (Design Input)

The following decisions were agreed with the user during research:

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Pytest + coverage removed from `run_quality_gates`** | Separation of concerns; `run_tests` owns test execution |
| 2 | **`scope` parameter replaces implicit mode detection** | Explicit > implicit; enables branch/project scopes |
| 3 | **Global baseline** (reset when ALL gates green) | Fixing one gate may introduce violation in another |
| 4 | **Re-run scope = `failed_files ∪ changed_since_last_run`** | Prevents missing new violations in concurrently edited files |
| 5 | **`summary_line` at top of response** | Agent reads summary first without parsing KB of JSON |
| 6 | **Unix-style compact JSON** | Aligned with `run_tests` output model |
| 7 | **`summary_line` also to be applied to `run_tests`** | Consistency — tracked as follow-up in this issue |

---

## Investigation 9: Reference Implementation — run_tests (issue #103)

### Finding: run_tests pattern is the target for QG output

**Key patterns to adopt:**

```python
# 1. Always use sys.executable for subprocess
cmd = [sys.executable, "-m", "pytest", ...]

# 2. Return compact JSON + summary_line as separate text content
return ToolResult(
    content=[
        {"type": "json", "json": parsed},
        {"type": "text", "text": summary_line},
    ]
)

# 3. summary_line is always present (fallback if parsing fails)
summary_line = parsed.get("summary_line") or f"{passed} passed, {failed} failed"

# 4. failures[] only when failed > 0 (no empty arrays)
if failures:
    result["failures"] = failures
```

**Divergence from run_tests pattern (QG-specific):**
- QG has multiple tools (gates), not a single pytest run → JSON has `gates[]` not `failures[]`
- Each gate has its own `violations[]` list
- QG needs scope metadata in response (`files_checked`, `scope_mode`, `baseline_sha`)

---

## Findings Summary

| # | Finding | Severity | Fix |
|---|---------|---------|-----|
| F1 | System pytest used for Gate 5/6 | Bug | Remove Gate 5/6 from active_gates |
| F2 | Gate 0 ruff format diff silently truncated | Bug | Increase limits + explicit truncation in issues[] |
| F3 | Double JSON in MCP response | Bug | Adopt ToolResult content[] pattern from run_tests |
| F4 | Mode bifurcation (files=[] vs files=[...]) | Architecture | Replace with `scope` parameter |
| F5 | No summary_line / giant JSON response | Architecture | Compact output + summary_line |
| F6 | Scope manually provided by agent | Architecture | git-diff auto scope with baseline state machine |
| F7 | No failure-narrowing on re-run | Architecture | `failed_files ∪ changed_since_last_run` |
| F8 | Pytest mixed with static analysis gates | Architecture | Pytest → run_tests only |

---

## Open Questions

1. **`scope="project"` discovery paths**: glob `backend/**/*.py + mcp_server/**/*.py + tests/**/*.py` — should `tests/` be included for static analysis (import checks etc.)? **Tentative: yes for format/lint, no for type gates (mypy scope config handles this).**
2. **Backward compatibility**: existing callers that pass `files=[...]` should still work. `files=[...]` maps to `scope="files"` internally. `files=[]` should be deprecated and mapped to `scope="auto"`.
3. **`run_tests` summary_line**: user requested this also be moved to top in `run_tests`. Track as follow-up task in planning.

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-22 | Agent | Initial complete research — 9 investigations, 8 findings, 7 user decisions |

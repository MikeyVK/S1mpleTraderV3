<!-- docs\development\issue251\research.md -->
<!-- template=research version=8b7bb3ab created=2026-02-22T17:36Z updated=2026-02-22T21:45Z -->
# Issue #251 Research: Refactor run_quality_gates — venv pytest, structured output, smart scope

**Status:** COMPLETE  
**Version:** 1.6  
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
3. `run_tests` reference implementation read in [mcp_server/tools/test_tools.py](#f-test-tools)
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
- **[docs/reference/mcp/tools/quality.md](#f-docs-quality)**
- **[docs/development/issue103/](#f-issue103)**
- **[mcp_server/tools/test_tools.py](#f-test-tools)**
- **[mcp_server/managers/qa_manager.py](#f-qa-manager)**
- **[mcp_server/tools/quality_tools.py](#f-quality-tools)**
- **[.st3/quality.yaml](#f-quality-yaml)**
- **[.st3/state.json](#f-state-json)**

---

## Investigation 1: Bug — System pytest instead of venv pytest

### Finding: `_resolve_command` does not handle bare `pytest` executable

**Root cause** in [mcp_server/managers/qa_manager.py](#f-qa-manager):

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

**Fix (aligned with Investigation 15):** Gate 0 acquires `parsing.strategy: "text_violations"` in [quality.yaml](#f-quality-yaml) with `pattern: "^--- a/(?P<file>.+)$"` and `defaults: {code: "FORMAT", message: "File requires formatting", fixable: true}`. The `text_violations` executor in `QAManager._parse_text_violations()` extracts one `ViolationDTO` per file from the diff `--- a/<file>` header lines. The full diff content moves to the artifact log only via `_build_output_capture`. `MAX_OUTPUT_LINES` / `MAX_OUTPUT_BYTES` constants are removed from the signal path — raw output is artifact-only.

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

## Investigation 5: Architecture — Output model (F5) and ViolationDTO contract (F14 intro)

### F5: Output blob is 3–8 KB; summary_line missing as top-level MCP content item

**Current output structure (what the agent receives today):**
```json
{
  "version": "2.0",
  "mode": "...",
  "files": [...],
  "summary": { "passed": 0, "failed": 2, "skipped": 6, ... },
  "gates": [ { /* full gate with command, environment, output, hints */ } ],
  "overall_pass": false,
  "timings": { ... },
  "text_output": "..."     ← buried at end of JSON, NOT a separate MCP content item
}
```

**Reference: `run_tests` output model (issue #103):**
```python
return ToolResult(
    content=[
        {"type": "text", "text": summary_line},  # ← FIRST: "3 passed in 1.2s"
        {"type": "json", "json": parsed},         # ← SECOND: compact details
    ]
)
```

The agent reads the `text` content item first — it's the summary line. Only when there are failures does it inspect the JSON. This is the pattern to follow.

**Target ToolResult for `run_quality_gates`:**
```python
return ToolResult(
    content=[
        {"type": "text", "text": summary_line},    # ← FIRST: one-line verdict
        {"type": "json", "json": compact_result},  # ← SECOND: violations only
    ]
)
```

Examples of `summary_line`:
- `"✅ 6/6 gates passed — 42 files checked (auto)"`
- `"❌ 2/6 gates failed — 14 violations (8 auto-fixable): Gate 0, Gate 1"`
- `"⏭️ 0/0 gates active — nothing to check (no changes since baseline)"`

---

### F14 — Problem statement: heterogeneous gate outputs, no uniform ViolationDTO contract

Different active gates produce fundamentally different raw outputs. Without a normalized schema, agents cannot uniformly parse violations across gate types.

> *Mypy-specific analysis and initial parser design: Investigation 14. Architectural solution for all gates: Investigation 15 (F15).*

**Current output diversity:**

| Gate | Tool | Raw output format | Current parsed result |
|------|------|-------------------|-----------------------|
| Gate 0 | ruff format | Text diff (`--- a/file\n+++ b/file\n@@ ...`) | `{message: "Gate failed exit=1", details: "<truncated diff>"}` — **not actionable** |
| Gate 1-3 | ruff check | JSON array `[{code, message, location, fix}]` | ✅ Structured via `_parse_ruff_json` |
| Gate 4 | mypy | Text `file.py:42: error: message [rule]` | `{message: "Gate failed exit=1", details: "<truncated text>"}` — **not actionable** |
| Gate 4b | pyright | JSON `{generalDiagnostics: [{file, range, message, rule}]}` | ✅ Structured via `_parse_json_field_issues` |
| Gate M (future) | pymarkdownlnt | JSON (SARIF-compatible) | Would need new parser |

**Problems:**
- Gate 0 and Gate 4 currently produce `{message: "Gate failed"}` — the agent knows nothing failed but not *what* or *where*
- Gate 4 mypy text is parsed as a blob and truncated at 50 lines — the truncation silently hides violations

**Required: normalized `ViolationDTO` schema across all gates:**

```typescript
{
  file: string,        // relative path — always present
  line: int | null,    // null for file-level violations (Gate 0)
  column: int | null,  // null if tool doesn't provide it
  code: string | null, // rule code (e.g. "E501", "return-value") — null if not applicable
  message: string,     // human-readable, always present, actionable
  severity: "error" | "warning" | "info",  // default "error"
  fixable: bool        // true if tool supports auto-fix for this violation
}
```

**Mapping each gate to the normalized schema:**

**Gate 0 — ruff format (text diff → file-level violations):**
`ruff format --check` exits 1 when files need reformatting. There is no line-level JSON from `ruff format`. The violation is file-level:
```json
{ "file": "mcp_server/tools/quality_tools.py", "line": null, "code": "FORMAT",
  "message": "File requires formatting. Run: python -m ruff format mcp_server/tools/quality_tools.py",
  "fixable": true }
```
One entry per file that needs formatting. The raw diff moves to the artifact log only — **the agent does not see the diff in the MCP response**, so the `message` must be self-contained and actionable.

**Gates 1–3 — ruff check (JSON → already normalized):**
`_parse_ruff_json` already produces `{file, line, column, code, message, fixable}`. Map `location.row → line`, `location.column → column`. Already close to the target schema — minor field renames.

**Gate 4 — mypy (text → needs new parser `_parse_mypy_text`):**
mypy output format: `path/to/file.py:42: error: Incompatible return value [return-value]`
Regex: `^(?P<file>[^:]+):(?P<line>\d+): (?P<severity>\w+): (?P<message>.+?)(?:\s+\[(?P<code>[^\]]+)\])?$`
```json
{ "file": "mcp_server/foo.py", "line": 42, "column": null, "code": "return-value",
  "message": "Incompatible return value type (got \"str\", expected \"int\")",
  "severity": "error", "fixable": false }
```
This replaces the current truncated text blob with a structured list — no truncation needed.

**Gate 4b — pyright (JSON → already normalized):**
`_parse_json_field_issues` already extracts `{file, line, column, message, code, severity}`. Matches target schema.

**Gate M (future pymarkdownlnt):**
pymarkdownlnt supports `--log-format jsonl` output. Each line is `{file, line_number, column_number, rule_id, description}`. New parser `_parse_pymarkdownlnt_json` maps cleanly to the normalized schema.

---

**Compact result structure (agent-optimized):**

```json
{
  "overall_pass": false,
  "summary": { "passed": 4, "failed": 2, "skipped": 0, "total_violations": 14, "auto_fixable": 8 },
  "scope": { "mode": "auto", "files_checked": 3, "baseline_sha": "abc123" },
  "gates": [
    {
      "id": "gate0_ruff_format",
      "name": "Gate 0: Ruff Format",
      "status": "failed",
      "violations": [
        { "file": "mcp_server/tools/quality_tools.py", "line": null, "code": "FORMAT",
          "message": "File requires formatting", "fixable": true }
      ],
      "fix_hint": "Run: python -m ruff format mcp_server/tools/quality_tools.py"
    },
    {
      "id": "gate1_formatting",
      "name": "Gate 1: Ruff Strict Lint",
      "status": "failed",
      "violations": [
        { "file": "mcp_server/tools/quality_tools.py", "line": 42, "column": 1,
          "code": "ANN201", "message": "Missing return type annotation for public function",
          "severity": "error", "fixable": false }
      ],
      "fix_hint": "Add return type annotations to all public functions"
    },
    {
      "id": "gate4_types",
      "name": "Gate 4: Types",
      "status": "skipped",
      "skip_reason": "No matching files in scope (gate scoped to backend/dtos/**)"
    }
  ],
  "timings": { "total_ms": 1840 }
}
```

**What is removed from current output (moved to artifact log only):**
- `command` object (executable, args, environment) — debug info, not actionable
- `output.stdout / output.stderr` — raw tool output, only needed when debugging
- Per-gate `duration_ms` — replaced by top-level `timings.total_ms`
- `hints[]` array — replaced by single `fix_hint` string per failed gate
- `version`, `mode`, `files[]` top-level fields — replaced by `scope` object

---

## Investigation 6: Design — Smart scope resolution

### Finding: git-based scope is feasible with 3 subprocess calls

**Target scope modes:**

| Mode | Trigger | Files resolved from |
|------|---------|---------------------|
| `auto` | default | `git diff <baseline_sha>..HEAD --name-only *.py` ∪ `state.quality_gates.failed_files` |
| `branch` | explicit / first run (no baseline) | `git diff <parent_branch>..HEAD --name-only *.py` |
| `project` | explicit / pre-PR | All `.py` files in `mcp_server/`, `tests/mcp_server/` |

> **No backward compatibility:** the `files=[...]` parameter is removed entirely. Callers that currently pass explicit file lists must switch to `scope="auto"` (see Open Questions #2).

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

## Investigation 10: quality.yaml Analysis — Config-Over-Code Principle (F9, F10)

### F9: Per-gate scope exists; top-level project discovery scope is missing

**quality.yaml already has per-gate scope config (example `gate4_types`):**
```yaml
gate4_types:
  scope:
    include_globs:
      - "backend/dtos/**/*.py"
    exclude_globs:
      - "tests/**/*.py"
```

This is the correct pattern. The coding standard (`QUALITY_GATES.md`) states:
> Gates apply to production AND test code — all Python files in `mcp_server/` and `tests/mcp_server/` must pass

**What is missing:** A top-level `project_scope` section in `quality.yaml` to define which paths are discovered when `scope="project"`. Without it, `QAManager` would need to hardcode these paths — a direct OCP violation.

**Solution — add `project_scope` to quality.yaml (correct globs per Investigation 13):**
```yaml
project_scope:
  include_globs:
    - "mcp_server/**/*.py"
    - "tests/mcp_server/**/*.py"
  exclude_globs: []
```

`QualityGateScope` Pydantic model is reused — no new model needed. `QualityConfig` gains one optional field:
```python
class QualityConfig(BaseModel):
    version: str
    active_gates: list[str]
    project_scope: QualityGateScope | None = None  # new
    artifact_logging: ArtifactLoggingConfig
    gates: dict[str, QualityGate]
```

### F10: gate5/gate6 use bare `pytest` command in quality.yaml config

Both gate commands start with `"pytest"` (bare binary), not `"python", "-m", "pytest"`. Every other gate uses `python -m <tool>`. Since gate5/gate6 are removed from `active_gates`, the config fix is to remove them from the list. Gate definitions are kept as legacy reference in the catalog.

### Separation: static config vs dynamic runtime state

| Data | Location | Reason |
|------|----------|--------|
| `project_scope` globs | `quality.yaml` | Static policy, identical for all branches |
| `baseline_sha` | `state.json` | Dynamic runtime state, branch-scoped |
| `failed_files` | `state.json` | Dynamic runtime state, branch-scoped |
| `active_gates` | `quality.yaml` | Static policy, identical for all branches |

This separation is SOLID-compliant (Single Responsibility: config = static policy, state = dynamic runtime).

---

## Investigation 11: _filter_files() — Global .py Hardcode is a SOLID Violation (F11)

### F11: Global pre-filtering prevents non-Python gate support

```python
def _filter_files(self, files: list[str]) -> tuple[list[str], list[dict[str, Any]]]:
    python_files = [f for f in files if str(f).endswith(".py")]  # ← hardcoded
```

This is called once before any gates execute. All subsequent gates receive only `.py` files, regardless of their `capabilities.file_types` config.

**OCP violation:** Adding a markdown gate (`file_types: [".md"]`) requires a code change — the global filter eliminates all `.md` files before any gate sees them.

**Correct architecture:** Remove `_filter_files()`. The full scope-resolved file list is passed to gate execution. Each gate filters for its own `file_types`:

```python
def _files_for_gate(self, gate: QualityGate, all_files: list[str]) -> list[str]:
    return [
        f for f in all_files
        if any(f.endswith(ext) for ext in gate.capabilities.file_types)
        and (gate.scope is None or gate.scope.matches(f))
    ]
```

Adding a markdown/YAML/JSON gate becomes a pure config operation. No code changes needed.

---

## Investigation 12: Pytest-Specific Dead Code in QAManager (F12)

### F12: 4 methods become dead code after pytest removal from active_gates

| Method | Purpose | Status after refactor |
|--------|---------|----------------------|
| `_is_pytest_gate()` | Detect pytest by command inspection | Remove |
| `_maybe_enable_pytest_json_report()` | Add `--json-report` flag if plugin installed | Remove |
| `_get_skip_reason()` | Mode-based skip logic for pytest vs static gates | Remove (mode split dissolves) |
| `_files_for_gate()` | Return `[]` for pytest, filter by file_types for static | Rewrite without pytest branch |

The `is_file_specific_mode` boolean and the entire mode-split block in `run_quality_gates()` also dissolves:

```python
# CURRENT — pytest-driven architecture leaking into all gate execution
is_file_specific_mode = bool(files)
if is_file_specific_mode:
    python_files = self._filter_files(files)
else:
    python_files = []   # empty so static gates skip, pytest proceeds
for gate in active_gates:
    gate_files = self._files_for_gate(gate, python_files)  # [] for pytest
    skip_reason = self._get_skip_reason(gate, gate_files, is_file_specific_mode)
```

```python
# NEW — scope-driven, fully generic
files = self._resolve_scope(scope, state)
for gate in active_gates:
    gate_files = self._files_for_gate(gate, files)  # filter by file_types + gate.scope
    if not gate_files:
        # standard skip: no matching files
        ...
```

No special-casing for any tool. QAManager becomes a true generic gate executor.

---

## Investigation 13: pyproject.toml Relationship + Correct project_scope Globs (F13)

### F13: project_scope globs must match testpaths in pyproject.toml

`pyproject.toml` is not modified by this refactor. It confirms:

```toml
testpaths = ["tests/mcp_server"]   # ← quality gate scope = mcp_server + tests/mcp_server
addopts = ["-n", "auto", ...]      # ← exact cause of exit code 4 bug
```

**Correct `project_scope` (replaces earlier incorrect draft with `backend/`):**
```yaml
project_scope:
  include_globs:
    - "mcp_server/**/*.py"
    - "tests/mcp_server/**/*.py"
  exclude_globs: []
```

Quality gates enforce the MCP server codebase only. `backend/` is out of QG scope. The `pyproject.toml` / `quality.yaml` two-tier authority model (IDE baseline vs CI authority) is unchanged by this refactor.

---

## Investigation 14: F14 Drill-down — Mypy Text Parser (stepping stone)

> ⚠️ **Stepping stone — superseded by Investigation 15.** This investigation analyzed the mypy-specific case of F14 and proposed a dedicated `_parse_mypy_text()` method with a `parser: "mypy"` field in [quality.yaml](#f-quality-yaml). Investigation 15 generalized this into the declarative `text_violations` strategy, eliminating all tool-specific methods from `QAManager`. Read this section to understand the reasoning chain; see Investigation 15 for the final design.
>
> *Problem statement: Investigation 5 (F14). Final solution: Investigation 15 (F15).*

### Mypy-specific case of F14

Gate 4 uses `parsing.strategy: "exit_code"` without JSON output. The current result when failing:

```json
{
  "issues": [{ "message": "Gate failed with exit code 1", "details": "<truncated mypy text>" }]
}
```

The agent knows the gate failed but cannot see which file/line/rule is violating. The raw text is truncated at 50 lines, silently hiding further violations.

**mypy text output format:**
```
mcp_server/managers/qa_manager.py:42: error: Incompatible return value type (got "str", expected "int")  [return-value]
mcp_server/managers/qa_manager.py:57: error: Argument 1 to "run" has incompatible type  [arg-type]
Found 2 errors in 1 file (checked 3 source files)
```

**New `_parse_mypy_text(stdout: str) -> list[ViolationDTO]`:**
```python
MYPY_LINE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+): (?P<severity>error|warning|note): "
    r"(?P<message>.+?)(?:\s+\[(?P<code>[^\]]+)\])?$"
)
```

Produces normalized violations:
```json
[
  { "file": "mcp_server/managers/qa_manager.py", "line": 42, "column": null,
    "code": "return-value", "message": "Incompatible return value type ...",
    "severity": "error", "fixable": false },
  { "file": "mcp_server/managers/qa_manager.py", "line": 57, "column": null,
    "code": "arg-type", "message": "Argument 1 to \"run\" has incompatible type ...",
    "severity": "error", "fixable": false }
]
```

No truncation needed — each violation is a compact struct. The "Found N errors" summary line is parsed separately into `gate.score`.

**quality.yaml needs a hint to use this parser.** Two options:
- Option A: Add `produces_text_violations: true` to capabilities → QAManager detects and uses text parser
- Option B: Add `parsing.strategy: "text_violations"` as a new strategy in quality.yaml → explicit, config-driven

**Decision: Option B** — consistent with the existing strategy enum (`exit_code`, `json_field`, `text_regex`). New strategy `"text_violations"` with `parser: "mypy"` field. Config-over-code: parser selection lives in quality.yaml, not detected in code.

```yaml
gate4_types:
  parsing:
    strategy: "text_violations"
    parser: "mypy"   # selects _parse_mypy_text in QAManager
```

---

## Investigation 15: Parsing Architecture — Config-Driven Violation Normalization (F15)

### Root cause analysis: three structural defects in the current parsing dispatch

Reading `qa_manager.py` lines 619–717 reveals that the dispatch contains implicit coupling and a dead config path that block adding any new tool without Python code changes.

#### Defect 1: `produces_json=true` is an implicit selector for `_parse_ruff_json`

```python
# execute_gate, line 619
if gate.parsing.strategy == "exit_code":
    if gate.capabilities.produces_json:          # ← hidden: "this means ruff check"
        parsed_issues = self._parse_ruff_json(parser_input)   # ← hardcoded
```

The `produces_json` flag in `CapabilitiesMetadata` was intended as metadata ("does this tool output JSON?"). In practice it is used as a parser selector: `produces_json=true` → call `_parse_ruff_json`. This is a hidden coupling that silently breaks for any other JSON-emitting tool. Adding `pymarkdownlnt` with `--log-format jsonl` (also JSON) and `produces_json=true` would call `_parse_ruff_json` — which expects a ruff violation array and would silently produce wrong output.

#### Defect 2: `text_regex` strategy — config exists, executor is a stub

`TextRegexParsing` has a full Pydantic model with `patterns: list[RegexPattern]`:
```python
class TextRegexParsing(BaseModel):
    strategy: Literal["text_regex"]
    patterns: list[RegexPattern] = Field(..., min_length=1)
```

But `execute_gate` for `text_regex`:
```python
elif gate.parsing.strategy == "text_regex":     # line 694
    if proc.returncode in set(gate.success.exit_codes_ok):
        result["passed"] = True
        result["issues"] = []
    else:
        result["passed"] = False
        result["issues"] = [{"message": f"Gate failed..."}]   # no regex parsing at all
```

The `patterns` are parsed by Pydantic and then ignored. This is dead config — the regex-to-violations path is never executed. F14 (mypy text normalization) cannot be solved by simply adding a `patterns` entry to quality.yaml because the executor does nothing with it.

#### Defect 3: `json_field` is semi-generic but does not output ViolationDTO

`_parse_json_field_issues` uses `diagnostics_path` (JSON Pointer) to locate the violations array, then extracts fields such as `file`, `range.start.line`, `rule`, `severity`. This is closer to config-driven behavior, but:
- Line numbers are adjusted (`+1`) because pyright uses 0-based indices — this offset is hardcoded in the method, not in config
- The resulting dict is not a `ViolationDTO` — it's an ad-hoc `dict[str, Any]` with inconsistent field presence
- `_parse_ruff_json` and `_parse_json_field_issues` exist as separate methods with different field conventions

**Net result:** Each tool has its own extraction path and its own output shape. The agent receives heterogeneous `issues[]` per gate — no guaranteed field contract.

---

### F15: Solution — two new declarative parsing strategies, zero tool-specific methods

**Design principle:** Move all tool output knowledge to `quality.yaml`. QAManager gains two generic executors; all tool-specific field paths are config. Adding a new tool = add YAML + Python package, zero Python code changes.

#### New strategy: `json_violations` (replaces `exit_code+produces_json` and `json_field`)

```python
class JsonViolationsParsing(BaseModel):
    strategy: Literal["json_violations"]
    violations_path: str = Field(default="/")   # JSON Pointer to violations array
    field_map: dict[str, str] = Field(...)      # ViolationDTO field → path inside each item
    fixable_when: str | None = Field(default=None)  # "path == 'value'" expression
    line_offset: int = Field(default=0)         # normalize 0-based to 1-based (+1 for pyright)
```

`field_map` uses `/`-separated JSON Pointer fragments local to each violation object (no RFC 6901 `#` anchors needed at item level):

```yaml
# gate1_formatting (ruff check)
parsing:
  strategy: "json_violations"
  violations_path: "/"                 # ruff outputs a root-level array
  field_map:
    file: "filename"
    line: "location/row"
    column: "location/column"
    code: "code"
    message: "message"
  fixable_when: "fix/applicability == 'safe'"

# gate4_pyright
parsing:
  strategy: "json_violations"
  violations_path: "/generalDiagnostics"   # pyright nests under this key
  line_offset: 1                           # pyright is 0-based, ViolationDTO is 1-based
  field_map:
    file: "file"
    line: "range/start/line"
    column: "range/start/character"
    code: "rule"
    message: "message"
    severity: "severity"
```

`_parse_json_violations()` in QAManager (fully generic, ~25 lines):
```python
def _parse_json_violations(self, stdout: str, p: JsonViolationsParsing) -> list[ViolationDTO]:
    try:
        data = json.loads(stdout)
    except (json.JSONDecodeError, ValueError):
        return []
    arr = self._resolve_json_pointer(data, p.violations_path)
    if not isinstance(arr, list):
        return []
    violations = []
    for item in arr:
        mapped: dict[str, Any] = {}
        for dto_field, path in p.field_map.items():
            val = self._resolve_path_fragment(item, path)
            if val is not None:
                mapped[dto_field] = val
        if p.fixable_when and "/" in p.fixable_when:
            path, _, expected = p.fixable_when.partition(" == ")
            raw = self._resolve_path_fragment(item, path.strip())
            mapped["fixable"] = str(raw) == expected.strip().strip("'\"")
        if "line" in mapped and isinstance(mapped["line"], int):
            mapped["line"] += p.line_offset
        violations.append(ViolationDTO(**mapped))
    return violations
```

`_resolve_path_fragment(item, "location/row")` splits on `/` and recursively gets nested keys. No third-party dependency — 4 lines of standard dict traversal.

#### New strategy: `text_violations` (replaces `text_regex` stub and resolves F14)

```python
class TextViolationsParsing(BaseModel):
    strategy: Literal["text_violations"]
    pattern: str = Field(...)              # regex with named groups → ViolationDTO fields
    defaults: dict[str, Any] = Field(default_factory=dict)   # literals for unmatched fields
    severity_default: str = Field(default="error")
```

```yaml
# gate4_types (mypy)
parsing:
  strategy: "text_violations"
  pattern: "^(?P<file>[^:]+):(?P<line>\\d+): (?P<severity>\\w+): (?P<message>.+?)(?:\\s+\\[(?P<code>[^\\]]+)\\])?$"
  defaults:
    fixable: false

# gate0_ruff_format
parsing:
  strategy: "text_violations"
  pattern: "^--- a/(?P<file>.+)$"         # each diff hunk starts with --- a/<file>
  defaults:
    code: "FORMAT"
    message: "File requires formatting. Fix: python -m ruff format {file}"  # {file} interpolated from named group
    fixable: true
    severity: "error"
```

> **`{fieldname}` interpolation in `defaults`:** `TextViolationsParsing.defaults` string values support `str.format(**groups)` expansion using the matched named groups. This allows `message: "... {file}"` to produce a fully concrete command per violation. The executor adds one line: `dto = {k: v.format(**groups) if isinstance(v, str) else v for k, v in {**p.defaults, **groups}.items()}`. The agent sees a self-contained, actionable message without needing to read the artifact log.

`_parse_text_violations()` in QAManager (fully generic, ~15 lines):
```python
def _parse_text_violations(self, stdout: str, p: TextViolationsParsing) -> list[ViolationDTO]:
    compiled = re.compile(p.pattern, re.MULTILINE)
    violations = []
    for match in compiled.finditer(stdout):
        groups = {k: v for k, v in match.groupdict().items() if v is not None}
        # Merge defaults + named groups; interpolate {fieldname} in default strings
        dto = {
            k: v.format(**groups) if isinstance(v, str) else v
            for k, v in {**p.defaults, **groups}.items()
        }
        if "severity" not in dto:
            dto["severity"] = p.severity_default
        if "line" in dto:
            dto["line"] = int(dto["line"])
        violations.append(ViolationDTO(**dto))
    return violations
```

#### Updated execute_gate dispatch (no tool names, no flags)

```python
match gate.parsing.strategy:
    case "json_violations":
        parser_input = proc.stdout if proc.stdout.strip() else combined_output
        violations = self._parse_json_violations(parser_input, gate.parsing)
    case "text_violations":
        violations = self._parse_text_violations(combined_output, gate.parsing)
    case "exit_code":
        violations = []   # pass/fail only — no violations (used for tools with no output)
    case _:
        violations = [ViolationDTO(message=f"Unsupported strategy: {gate.parsing.strategy}")]
```

**Zero `if tool == "..."` statements. Zero `produces_json` flag checks.**

---

### Impact: what is removed vs what is added

**Removed from QAManager:**
| Method | Reason |
|--------|--------|
| `_parse_ruff_json()` | Inlined into `field_map` config in quality.yaml |
| `_parse_json_field_issues()` | Replaced by `_parse_json_violations()` (generic) |
| `produces_json` flag branch in `execute_gate` | Replaced by `json_violations` strategy |

**Removed from Pydantic models (`quality_config.py`):**
| Model | Change |
|-------|--------|
| `TextRegexParsing` | Replace: add `TextViolationsParsing` (patterns → single `pattern`, add `defaults`) |
| `JsonFieldParsing` | Replace: add `JsonViolationsParsing` (field_map + violations_path + line_offset) |
| `CapabilitiesMetadata.produces_json` | Remove flag — strategy is now explicit in `parsing.strategy` |

**Added to QAManager:**
| Method | Size |
|--------|------|
| `_parse_json_violations()` | ~25 lines, fully generic |
| `_parse_text_violations()` | ~15 lines, fully generic |
| `_resolve_path_fragment()` | ~4 lines, recursive dict traversal |

**Net: 2 tool-specific methods → 3 generic methods. New tool requires zero Python changes.**

---

### Constraint: `fixable_when` expression syntax

`fixable_when` is a single `"path == 'value'"` string — parsed by splitting on ` == `, trimming quotes. This covers all known cases:
- ruff: `fix/applicability == 'safe'`
- (All other current tools have constant `fixable: false`)

If future tools need `!=` or `in` expressions, `fixable_when` can be extended. No DSL is needed for the current gate catalog.

---

### Gate 0 special case: ruff format diff → file-level violations

`ruff format --check --diff` outputs a unified diff. The `text_violations` strategy with pattern `^--- a/(?P<file>.+)$` extracts one violation per file from the diff (each diff hunk's `--- a/<file>` header line). This is both minimal (no external process needed) and accurate (matches exactly the files ruff reports as needing format).

**The full diff content** still moves to the artifact log — `_build_output_capture` writes it there. The agent sees only file-level `{code: "FORMAT", fixable: true}` violations in the MCP result.

---

## Findings Summary

| # | Finding | Severity | Fix |
|---|---------|---------|-----|
| F1 | System pytest used for Gate 5/6 | Bug | Remove Gate 5/6 from active_gates |
| F2 | Gate 0 ruff format diff silently truncated | Bug | `text_violations` strategy extracts file-level FORMAT violations; diff → artifact log |
| F3 | Double JSON in MCP response | Bug | `ToolResult.content[]` with `text` first, `json` second |
| F4 | Mode bifurcation (files=[] vs files=[...]) | Architecture | Replace with `scope` enum — no backward compat |
| F5 | No summary_line as first MCP content item | Architecture | `summary_line` as `{"type": "text"}` first in ToolResult |
| F6 | Scope manually provided by agent | Architecture | git-diff auto scope with baseline state machine in state.json |
| F7 | No failure-narrowing on re-run | Architecture | `failed_files ∪ changed_since_last_run` |
| F8 | Pytest mixed with static analysis gates | Architecture | Pytest → run_tests only; remove gate5/gate6 from active_gates |
| F9 | Project-level file discovery hardcoded | SOLID/OCP | `project_scope` in quality.yaml — reuse `QualityGateScope` model |
| F10 | gate5/gate6 use bare `pytest` binary in config | Config bug | Remove from active_gates (gate defs kept as legacy reference) |
| F11 | `_filter_files()` hardcodes `.py` globally | SOLID/OCP | Remove — each gate filters via `capabilities.file_types` |
| F12 | 4 pytest-specific methods in QAManager | Dead code | Remove `_is_pytest_gate`, `_maybe_enable_pytest_json_report`, `_get_skip_reason`; rewrite `_files_for_gate` |
| F13 | project_scope globs wrong in earlier draft | Config error | Correct: `mcp_server/**/*.py`, `tests/mcp_server/**/*.py` |
| F14 | Gate 4 mypy violations unstructured/truncated | Architecture | `text_violations` strategy with mypy regex pattern + `defaults` in quality.yaml |
| F15 | `produces_json` implicit coupling + `text_regex` dead config + `json_field` no ViolationDTO | Architecture | New `json_violations` + `text_violations` strategies; remove `_parse_ruff_json` + `_parse_json_field_issues`; zero tool-specific methods in QAManager |

---

## Open Questions

1. ~~`scope="project"` discovery paths~~ — **RESOLVED:** Discovery paths are config-driven via `project_scope` in `quality.yaml` (see Investigation 10). Per-gate exclusions via `gate.scope` still apply.
2. ~~Backward compatibility~~ — **RESOLVED by user: No backward compatibility.** The `files` parameter is removed. New API uses `scope` enum exclusively.
3. ~~`run_tests` summary_line~~ — **RESOLVED:** Add as a separate TDD cycle in planning phase.
4. **Documentation phase obligation (carry to planning):** `QUALITY_GATES.md` currently describes Gate 5 (tests) and Gate 6 (coverage) as part of the quality gates checklist. Removing them from `active_gates` is a config-only change in `quality.yaml`, but the doc still implies a single tool runs all 7 gates. In the documentation phase, `QUALITY_GATES.md` must be updated to clarify: the conceptual 7-gate checklist still applies for a PR, but execution is now split — `run_quality_gates` runs Gates 0–4b (static analysis), `run_tests` runs Gates 5–6 (tests and coverage).

---

## Referenced Files

<table id="file-references">
<thead>
  <tr><th>Anchor</th><th>File</th><th>Path</th></tr>
</thead>
<tbody>
  <tr id="f-qa-manager"><td><code>f-qa-manager</code></td><td><code>qa_manager.py</code></td><td><code>mcp_server/managers/qa_manager.py</code></td></tr>
  <tr id="f-quality-tools"><td><code>f-quality-tools</code></td><td><code>quality_tools.py</code></td><td><code>mcp_server/tools/quality_tools.py</code></td></tr>
  <tr id="f-test-tools"><td><code>f-test-tools</code></td><td><code>test_tools.py</code></td><td><code>mcp_server/tools/test_tools.py</code></td></tr>
  <tr id="f-quality-config"><td><code>f-quality-config</code></td><td><code>quality_config.py</code></td><td><code>mcp_server/config/quality_config.py</code></td></tr>
  <tr id="f-quality-yaml"><td><code>f-quality-yaml</code></td><td><code>quality.yaml</code></td><td><code>.st3/quality.yaml</code></td></tr>
  <tr id="f-state-json"><td><code>f-state-json</code></td><td><code>state.json</code></td><td><code>.st3/state.json</code></td></tr>
  <tr id="f-pyproject"><td><code>f-pyproject</code></td><td><code>pyproject.toml</code></td><td><code>pyproject.toml</code></td></tr>
  <tr id="f-docs-quality"><td><code>f-docs-quality</code></td><td><code>quality.md</code></td><td><code>docs/reference/mcp/tools/quality.md</code></td></tr>
  <tr id="f-issue103"><td><code>f-issue103</code></td><td><code>issue103/</code></td><td><code>docs/development/issue103/</code></td></tr>
</tbody>
</table>

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-22 | Agent | Initial complete research — 9 investigations, 8 findings, 7 user decisions |
| 1.1 | 2026-02-22 | Agent | Add Inv. 10–13 (SOLID, dead code, globs), F9–F13; fix ordering |
| 1.2 | 2026-02-22 | Agent | Rewrite Inv. 5 (output model, ViolationDTO schema); add Inv. 14 (F14, mypy parsing) |
| 1.3 | 2026-02-22 | Agent | Add Inv. 15 (F15): config-driven parsing architecture; `json_violations` + `text_violations` strategies; zero tool-specific methods in QAManager |
| 1.4 | 2026-02-22 | Agent | Consistency pass: fix header version, Investigation 2 Fix aligned with Inv. 15, Inv. 5 title, superseded note on Inv. 14, HTML file-reference table, anchor links throughout |
| 1.5 | 2026-02-22 | Agent | Fix F14 dual-section confusion: Inv. 5 = problem statement, Inv. 14 = stepping stone with upfront banner; remove duplicate `### F14:` heading |
| 1.6 | 2026-02-22 | Agent | Fix backward compat inconsistency (Inv. 6 table vs Open Questions); explicit Gate 0 `message` with `{file}` interpolation; `{fieldname}` interpolation in `TextViolationsParsing.defaults`; QUALITY_GATES.md doc-phase obligation in Open Questions |

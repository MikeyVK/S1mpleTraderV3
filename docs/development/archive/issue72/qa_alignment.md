# QA Alignment (Issue 72) — Quality Gates SSOT + VS Code Clean Slate

Date: 2026-01-25  
Owner: QA/Architecture  
Scope: Issue 72 (Template Library Management) – tooling alignment

## Context

We experience ping-pong between implementation and QA due to misalignment between:
- `run_quality_gates` (MCP server tool) running **mypy --strict** on all provided `.py` files (including tests),
- VS Code Problems (Pylance/Pyright) emitting diagnostics based on `pyrightconfig.json`,
- Project docs that sometimes describe Gate 4 as “DTO-only”, while the current tooling is more general.

This causes:
- **False positives** (especially around `Mock/AsyncMock` usage in tests: `.call_args`, dynamic attributes),
- or **noise** in VS Code that breaks the “clean slate” workflow and increases the chance of missing real issues.

## Goals

1. `.st3/quality.yaml` is the **Single Source of Truth (SSOT)** for quality-gate policy (including strict vs non-strict scopes).
2. `run_quality_gates` is **config-driven** and decides per gate which files to evaluate.
   - No manual “agent chooses file set” logic.
3. VS Code Problems remains a **clean slate**: minimal noise in tests, strict signal in production code.
4. Reduce false positives without losing strictness where it matters.

## Non-goals

- No dependency from MCP server policy on IDE settings.
- No hard-coded heuristics in code like `if path startswith tests/`.

## Decision: Option C (Config-driven Hybrid)

- Production code (`backend/**`, `mcp_server/**`): strict typing checks.
  - mypy strict
  - pyright strict
- Tests (`tests/**`): “light” typing checks.
  - pyright basic
  - mypy strict gate is skipped for tests (via scope)
- Linting (pylint) remains strict (10/10) everywhere unless explicitly scoped otherwise.

## Implementation Plan

### A) Extend `.st3/quality.yaml` with gate scopes

Problem: the current `mypy` gate in `.st3/quality.yaml` defines how to execute mypy, but not *which* files should be considered “strict”.

Solution: introduce an optional, explicit `scope` per gate.

#### 1) New schema shape

Add an optional `scope` section per gate:

```yaml
scope:
  include_globs:
    - "backend/**/*.py"
    - "mcp_server/**/*.py"
  exclude_globs:
    - "tests/**/*.py"
```

Scope semantics:
- If `scope` is absent: gate applies to all `.py` files passed to the tool.
- `include_globs` is an allow-list. If empty/missing, treat as “include all”.
- `exclude_globs` is a deny-list applied after includes.

#### 2) Apply to the `mypy` gate

Update `.st3/quality.yaml` `mypy` gate (example):

```yaml
mypy:
  name: "Type Checking"
  description: "Static type checking"
  execution:
    command: ["python", "-m", "mypy", "--strict", "--no-error-summary"]
    timeout_seconds: 60
    working_dir: null
  parsing:
    strategy: "exit_code"
  success:
    mode: "exit_code"
    exit_codes_ok: [0]
  capabilities:
    file_types: [".py"]
    supports_autofix: false
    produces_json: false
  scope:
    include_globs:
      - "backend/**/*.py"
      - "mcp_server/**/*.py"
    exclude_globs:
      - "tests/**/*.py"
```

This is the SSOT policy: tests are not part of “mypy strict gate”, by design.

### B) Update MCP server gate config model to support `scope`

File: `mcp_server/config/quality_config.py`

Reason: the Pydantic models currently use `extra="forbid"`, so adding `scope` in YAML requires schema support.

Implementation steps:
1. Add a `GateScope` model with:
   - `include_globs: list[str] = Field(default_factory=list)`
   - `exclude_globs: list[str] = Field(default_factory=list)`
2. Extend `QualityGate` with:
   - `scope: GateScope | None = Field(default=None)`

### C) Make `run_quality_gates` filter files per gate (config-driven)

File: `mcp_server/managers/qa_manager.py`

#### 1) Add a scope filter helper

Requirements:
- Works on Windows paths.
- Treat YAML patterns as POSIX (`/`) globs.
- Prefer repo-relative matching.

Suggested approach:
- Normalize each input file to repo-relative:
  - `rel = Path(file).resolve().relative_to(Path.cwd().resolve())` (fallback to the original file string if this fails)
- Convert to POSIX string: `rel.as_posix()`
- Match patterns using `PurePosixPath(posix).match(pattern)`

#### 2) Apply scope filtering to the mypy gate (initially)

In `QAManager.run_quality_gates()`:
- Keep pylint and pyright running over all provided python files.
- For mypy:
  - `mypy_files = filter_by_scope(python_files, mypy_gate.scope)`
  - If `mypy_files` is empty:
    - return a gate result with `passed=True`, `score="Skipped (no matching files)"`, `issues=[]`
  - Else:
    - run mypy on `mypy_files`.

This removes test-related mypy strict false positives without needing any caller logic.

#### 3) Make mypy parsing robust

In `_run_mypy()`:
- Parse combined streams: `proc.stdout + proc.stderr`.

### D) Align VS Code Problems once to match project policy

VS Code Problems comes from Pylance/Pyright. We align it one-time to the policy in `.st3/quality.yaml`:
- strict in production code
- basic in tests

File: `pyrightconfig.json`

Add `executionEnvironments`:

```json
{
  "include": ["backend", "mcp_server", "tests", "frontends"],
  "exclude": [
    "**/__pycache__",
    "**/.pytest_cache",
    "**/node_modules",
    "results",
    "source_data"
  ],

  "typeCheckingMode": "strict",

  "executionEnvironments": [
    { "root": "./backend", "typeCheckingMode": "strict" },
    { "root": "./mcp_server", "typeCheckingMode": "strict" },
    { "root": "./tests", "typeCheckingMode": "basic" }
  ]

  // keep existing report* settings as-is
}
```

VS Code follow-up:
- Restart language server: “Python: Restart Language Server”.
- Avoid setting `python.analysis.typeCheckingMode` in `.vscode/settings.json` in a way that overrides the above intent.

## Acceptance Criteria

1. Running `run_quality_gates` on a mixed file set (prod + tests):
   - Pylint runs and stays strict.
   - Mypy runs only on files matched by the gate scope (prod), and skips tests.
   - Pyright runs; tests produce minimal/noisy diagnostics due to basic mode.
2. No mypy strict false positives from `Mock/AsyncMock` usage in tests.
3. VS Code Problems remains a “clean slate” for tests, but strict for production code.
4. No caller/agent needs to choose which files mypy should check.

## Notes

- This introduces policy into `.st3/quality.yaml` (SSOT) and removes tool/IDE drift.
- Docs in `docs/coding_standards/QUALITY_GATES.md` should be updated later to describe that Gate 4 scope is config-driven via `.st3/quality.yaml`.

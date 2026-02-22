<!-- docs/reference/mcp/tools/quality.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-02-12 -->
# Quality & Validation Tools

**Status:** DEFINITIVE  
**Version:** 2.1  
**Last Updated:** 2026-02-12  

**Source:** [mcp_server/tools/quality_tools.py](../../../../mcp_server/tools/quality_tools.py), [test_tools.py](../../../../mcp_server/tools/test_tools.py), [validation_tools.py](../../../../mcp_server/tools/validation_tools.py), [template_validation_tool.py](../../../../mcp_server/tools/template_validation_tool.py)  
**Tests:** [tests/unit/test_quality_tools.py](../../../../tests/unit/test_quality_tools.py)  

---

## Purpose

Complete reference documentation for quality assurance and validation tools covering code quality gates, test execution, architectural validation, DTO validation, and template conformance checking.

These tools integrate with `safe_edit_file` validation modes and enforce code quality standards defined in [.st3/quality.yaml](../../../../.st3/quality.yaml).

---

## Overview

The MCP server provides **5 quality/validation tools**:

| Tool | Purpose | Key Features |
|------|---------|-------------|
| `run_quality_gates` | Run configured quality gates | Config-driven static checks + tests |
| `run_tests` | Run pytest with markers | Test execution with timeout |
| `validate_architecture` | Validate code against patterns | DTO/worker/platform architecture checks |
| `validate_dto` | Validate DTO definition | DTO-specific validation rules |
| `validate_template` | Validate file vs template spec | Template conformance checking |

---

## API Reference

### run_quality_gates

**MCP Name:** `run_quality_gates`  
**Class:** `RunQualityGatesTool`  
**File:** [mcp_server/tools/quality_tools.py](../../../../mcp_server/tools/quality_tools.py)

Run the configured quality gates from `.st3/quality.yaml` against the provided files.

Gates are executed in the order of `active_gates`. Each gate definition provides its own command, parsing strategy, and success criteria.

#### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `files` | `list[str]` | No | `[]` | List of file paths. `[]` = project-level test validation (pytest/coverage only). `[...]` = file-specific mode (static analysis on specified files). |

#### Returns

Response format v2.0 — a structured JSON dict returned via `ToolResult.json_data()`:

```json
{
  "version": "2.0",
  "mode": "file-specific",
  "files": ["backend/dtos/user.py"],
  "summary": {
    "passed": 5,
    "failed": 1,
    "skipped": 2,
    "total_violations": 3,
    "auto_fixable": 1
  },
  "overall_pass": false,
  "gates": [
    {
      "gate_number": 1,
      "id": 1,
      "name": "Gate 0: Ruff Format",
      "passed": true,
      "status": "passed",
      "skip_reason": null,
      "score": "Pass",
      "issues": [],
      "duration_ms": 124,
      "command": {
        "executable": "D:\\dev\\project\\.venv\\Scripts\\python.exe",
        "args": ["-m", "ruff", "format", "--check", "--diff", "--isolated", "--line-length=100", "backend/dtos/user.py"],
        "cwd": null,
        "exit_code": 0,
        "environment": {
          "python_version": "3.13.5",
          "tool_path": "D:\\dev\\project\\.venv\\Scripts\\ruff.exe",
          "platform": "Windows-11-10.0.26100-SP0",
          "tool_version": "ruff 0.14.2"
        }
      }
    },
    {
      "gate_number": 2,
      "id": 2,
      "name": "Gate 1: Ruff Strict Lint",
      "passed": false,
      "status": "failed",
      "skip_reason": null,
      "score": "3 violations, 1 auto-fixable",
      "issues": [
        {
          "code": "ANN401",
          "message": "Dynamically typed expressions (typing.Any) are disallowed",
          "line": 15,
          "column": 22,
          "file": "backend/dtos/user.py",
          "fixable": false
        }
      ],
      "duration_ms": 131,
      "command": { "..." : "..." },
      "output": {
        "stdout": "[{\"code\": \"ANN401\", ...}]",
        "stderr": "",
        "truncated": false,
        "details": "stdout:\n[{\"code\": \"ANN401\", ...}]"
      },
      "hints": [
        "Re-run: python -m ruff check --isolated ...",
        "This gate is stricter than the VS Code/IDE baseline (it does not inherit pyproject ignores).",
        "Line length (E501) and import placement (PLC0415) are enforced in Gate 2/3."
      ],
      "artifact_path": "temp/qa_logs/20260212T120000Z_gate2_gate_1_ruff_strict_lint.json"
    },
    {
      "gate_number": 6,
      "id": 6,
      "name": "Gate 4b: Pyright",
      "passed": true,
      "status": "passed",
      "skip_reason": null,
      "score": "Pass",
      "issues": [],
      "duration_ms": 2465,
      "command": { "..." : "..." },
      "fields": {
        "diagnostics": [],
        "error_count": 0
      }
    },
    {
      "gate_number": 7,
      "id": 7,
      "name": "Gate 5: Tests",
      "passed": true,
      "status": "skipped",
      "skip_reason": "Skipped (file-specific mode - tests run project-wide)",
      "score": "Skipped (file-specific mode - tests run project-wide)",
      "issues": []
    }
  ],
  "timings": {
    "1": 124,
    "2": 131,
    "3": 118,
    "4": 116,
    "5": 0,
    "6": 2465,
    "7": 0,
    "8": 0,
    "total": 2954
  },
  "text_output": "Quality Gates Results (mode: file-specific):\nSummary: 5 passed, 1 failed, 2 skipped\n..."
}
```

##### Response fields reference

| Field | Type | Description |
|-------|------|-------------|
| `version` | `str` | Schema version, currently `"2.0"` |
| `mode` | `str` | `"file-specific"` or `"project-level"` |
| `files` | `list[str]` | Input files (empty for project-level) |
| `summary` | `dict` | Aggregate counts: `passed`, `failed`, `skipped`, `total_violations`, `auto_fixable` |
| `overall_pass` | `bool` | `true` if all gates passed or were skipped |
| `gates` | `list[dict]` | Per-gate results (see below) |
| `timings` | `dict[str, int]` | Per-gate timing: `{gate_number: duration_ms, ..., "total": sum}` |
| `text_output` | `str` | Human-readable summary (added by tool layer) |

##### Per-gate fields

| Field | Presence | Description |
|-------|----------|-------------|
| `gate_number` | Always | 1-based index in active_gates |
| `id` | Always | Same as gate_number |
| `name` | Always | Gate display name from config |
| `passed` | Always | `true` / `false` |
| `status` | Always | `"passed"`, `"failed"`, or `"skipped"` |
| `skip_reason` | Always | Mode-aware skip message or `null` |
| `score` | Always | Human-readable score: `"Pass"`, `"Fail (exit=N)"`, `"N violations, M auto-fixable"`, `"Timeout"` |
| `issues` | Always | List of structured violations (empty if none) |
| `duration_ms` | Executed only | Wall-clock time of gate execution |
| `command` | Executed only | Exact command with `executable`, `args`, `cwd`, `exit_code`, `environment` |
| `output` | Failed only | `stdout`, `stderr`, `truncated`, `details`; plus `full_log_path` when truncated |
| `hints` | Failed only | Actionable next-step guidance |
| `artifact_path` | Failed only | Path to full diagnostics JSON in `temp/qa_logs/` |
| `fields` | json_field only | Parsed fields from JSON output (e.g., Pyright `diagnostics`, `error_count`) |

##### Environment metadata (in `command.environment`)

| Field | Description |
|-------|-------------|
| `python_version` | Python interpreter version |
| `tool_path` | Resolved path to tool binary via `shutil.which()` |
| `platform` | OS platform string |
| `tool_version` | Best-effort `--version` output (detects `python -m <tool>` pattern) |

**Notes:**
- `hints` provide targeted, actionable next-step guidance (primarily for automated agents).
- `output` is only present on failures. Streams are truncated to 50 lines / 5 KB per stream; when truncated, `full_log_path` points to the complete artifact JSON.
- When `python -m <tool>` is detected, `tool_version` reflects the actual tool version (e.g., `ruff 0.14.2`), not the Python version.

#### Example Usage

**Project-level test validation (pytest/coverage enforcement):**
```json
{
  "files": []
}
```

**Single file validation (static analysis):**
```json
{
  "files": ["backend/dtos/user.py"]
}
```

**Multiple files validation (static analysis):**
```json
{
  "files": [
    "backend/dtos/user.py",
    "backend/services/auth_service.py",
    "tests/test_user.py"
  ]
}
```

#### Execution Modes

**Project-level test validation mode (`files=[]`):**
- Runs **pytest gates only** (Gate 5: Tests, Gate 6: Coverage ≥90%)
- File-based static gates (Gates 0–4b: Ruff, Mypy, Pyright) are **skipped** (no file list provided)
- Used for CI/CD test/coverage enforcement before merge
- Example use case: Block PR merge if tests fail or coverage < 90%
- **Note:** For full-repo static analysis, provide explicit file list via Git diff or glob

**File-specific validation mode (`files=[...]`):**
- Runs **file-based static gates** (Gates 0–4b: Ruff formatting, linting, imports, line length, Mypy, Pyright)
- **Skips** pytest gates (Gate 5 & 6) — tests run at project-level, not per-file
- Validates file existence and filters to `.py` files
- Example use case: IDE save hooks, pre-commit validation on changed files

#### Behavior Notes

- Gates executed in the order of `active_gates` from [.st3/quality.yaml](../../../../.st3/quality.yaml)
- `.py` filtering: non-Python inputs are reported as skipped
- Scope filtering: when `scope` is present, include/exclude globs apply per-gate
- **Silent skips:** Gates without matching files show as "Skipped (no matching files)" in output

#### Quality Gate Configuration

From [.st3/quality.yaml](../../../../.st3/quality.yaml):

```yaml
version: "1.0"
active_gates:
  - gate0_ruff_format    # Gate 0: Formatting
  - gate1_formatting     # Gate 1: Strict Lint (stricter than IDE)
  - gate2_imports        # Gate 2: Import placement
  - gate3_line_length    # Gate 3: Line length (E501)
  - gate4_types          # Gate 4: Mypy strict (DTOs only)
  - gate4_pyright        # Gate 4b: Pyright (warnings fail)
  - gate5_tests          # Gate 5: Unit tests
  - gate6_coverage       # Gate 6: Coverage ≥90%

artifact_logging:
  enabled: true
  output_dir: "temp/qa_logs"
  max_files: 200

gates:
  gate0_ruff_format:
    name: "Gate 0: Ruff Format"
    description: "Code formatting (ruff format --check)"
    execution:
      command: ["python", "-m", "ruff", "format", "--check", "--diff", "--isolated", "--line-length=100"]
      timeout_seconds: 60
    parsing:
      strategy: "exit_code"
    success:
      mode: "exit_code"
      exit_codes_ok: [0]
    capabilities:
      file_types: [".py"]
      supports_autofix: true
      produces_json: false

  gate1_formatting:
    name: "Gate 1: Ruff Strict Lint"
    description: "Strict linting (stricter than VS Code/IDE baseline)"
    execution:
      command: ["python", "-m", "ruff", "check", "--isolated", "--output-format=json",
        "--select=E,W,F,I,N,UP,ANN,B,C4,DTZ,T10,ISC,RET,SIM,ARG,PLC",
        "--ignore=E501,PLC0415", "--line-length=100", "--target-version=py311"]
      timeout_seconds: 60
    parsing:
      strategy: "exit_code"
    success:
      mode: "exit_code"
      exit_codes_ok: [0]
    capabilities:
      file_types: [".py"]
      supports_autofix: true
      produces_json: true          # ← Ruff JSON parsed for structured issues

  gate4_pyright:
    name: "Gate 4b: Pyright"
    description: "Type checking (Pyright strict; warnings fail)"
    execution:
      command: ["python", "-m", "pyright", "--project", "pyrightconfig.json",
        "--pythonversion", "3.11", "--pythonplatform", "Windows",
        "--level", "warning", "--warnings", "--outputjson"]
      timeout_seconds: 120
    parsing:
      strategy: "json_field"       # ← JSON Pointer-based field extraction
      fields:
        diagnostics: "/generalDiagnostics"
        error_count: "/summary/errorCount"
      diagnostics_path: "/generalDiagnostics"
    success:
      mode: "json_field"
      max_errors: 0
      require_no_issues: true
    capabilities:
      file_types: [".py"]
      produces_json: true

  gate6_coverage:
    name: "Gate 6: Coverage"
    description: "Branch coverage >= 90% (backend + mcp_server)"
    execution:
      command: ["pytest", "tests/", "--cov=backend", "--cov=mcp_server",
        "--cov-branch", "--cov-fail-under=90", "--tb=short"]
      timeout_seconds: 300
    parsing:
      strategy: "exit_code"
    success:
      mode: "exit_code"
      exit_codes_ok: [0]

  # ... gate2_imports, gate3_line_length, gate4_types, gate5_tests omitted for brevity
```

##### Parsing strategies

| Strategy | Used By | Behavior |
|----------|---------|----------|
| `exit_code` | Gates 0–5, 6 | Check return code against `exit_codes_ok`. If `produces_json: true`, also parses Ruff JSON for structured violations. |
| `json_field` | Gate 4b (Pyright) | Parses JSON output, extracts fields via RFC 6901 JSON Pointers (`/generalDiagnostics`, `/summary/errorCount`). |
| `text_regex` | (unused) | Regex-based text parsing with named groups. Falls back to exit code on failure. |

---

## Configuration Files: Dual-User Scenario

**Status:** Updated for Issue #131
**Principle:** Quality gates use `.st3/quality.yaml` for CI/CD enforcement; individual tools (Ruff, Mypy, Pyright) read `pyproject.toml` / `pyrightconfig.json` for IDE/CLI behavior.

This project maintains **two separate configuration layers** to support different user workflows:

### 1. Developer IDE/CLI Experience: pyproject.toml

**Purpose:** Baseline code quality for VS Code, CLI usage, and local development.

**Audience:** Human developers working in their IDE

**Key Characteristics:**
- **Relaxed rules:** Allows common IDE patterns (e.g., E501 line length warnings instead of errors)
- **Inline ignores:** Developers can use `# type: ignore` or `# noqa` for edge cases
- **Tool-specific sections:** Each tool (Ruff, Mypy, Pyright) has its own configuration block
- **Independent execution:** Developers run `ruff check`, `mypy`, `pyright` directly

**Example (pyproject.toml):**
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
# Relaxed ruleset for IDE: warnings allowed
select = ["E", "W", "F", "I", "UP"]
ignore = ["E501"]  # Line too long (warning only in IDE)

[tool.mypy]
python_version = "3.11"
strict = false  # Enforce strict typing in quality gates only
```

### 2. CI/CD Quality Gates: .st3/quality.yaml

**Purpose:** Strict quality enforcement for automated systems (GitHub Actions, MCP tools, pre-merge checks).

**Audience:** Automated agents (AI assistants, CI/CD pipelines)

**Key Characteristics:**
- **Strict rules:** Enforces stricter checks than IDE baseline (e.g., E501 becomes an error)
- **Config-driven execution:** Gates run in sequence defined by `active_gates` list
- **No inline ignores:** Cannot override gate failures with `# noqa` or `# type: ignore`
- **Unified execution:** All gates run via `QAManager` → ensures consistent enforcement

**Example (.st3/quality.yaml):**
```yaml
version: "1.0"
active_gates:
  - gate0_ruff_format
  - gate1_formatting
  - gate3_line_length  # E501 enforced as error here
  - gate4_pyright

gates:
  gate3_line_length:
    name: "Gate 3: Line Length"
    execution:
      # Stricter than pyproject.toml: E501 is  an error, not a warning
      command: ["python", "-m", "ruff", "check", "--select=E501", "--line-length=100"]
      timeout_seconds: 60
    parsing:
      strategy: "exit_code"
    success:
      mode: "exit_code"
      exit_codes_ok: [0]  # Fail on any E501 violation
```

### Why Two Configuration Layers?

**Design Philosophy:**
- **Developers** need flexible, warning-based feedback for rapid iteration
- **Automated systems** need strict, pass/fail gates to enforce code quality standards

**Hierarchical Enforcement:**
1. **IDE/CLI (pyproject.toml):** Baseline quality with warnings
2. **Pre-commit hooks:** Run subset of gates (e.g., formatting, imports)
3. **CI/CD (.st3/quality.yaml):** Full gate suite with strict enforcement

**Example Workflow:**
```
Human developer:
  1. Write code in VS Code
  2. Ruff/Mypy show warnings (E501 line too long)
  3. Developer ignores warning temporarily, continues work
  4. Runs `git commit`
  5. Pre-commit hook fails with Gate 3 (E501 enforced)
  6. Developer fixes line length, commit succeeds

AI agent/CI:
  1. Agent writes code via safe_edit_file
  2. Tool internally runs run_quality_gates(files=[...])
  3. Gate 3 fails with E501 violation
  4. Agent automatically rewrites code to fix line length
  5. All gates pass, commit proceeds
```

### Gate Configuration Override Behavior

**Command Flag Precedence:**
- Gates explicitly specify flags (e.g., `--select=E501`, `--ignore=`) in their `command` array
- These flags **override** the corresponding settings from `pyproject.toml` / `pyrightconfig.json`
- This ensures gate behavior is **deterministic** and independent of local IDE config

**Example:**
```yaml
# .st3/quality.yaml (Gate 2)
command: ["python", "-m", "ruff", "check", "--select=PLC0415", "--ignore="]
# --ignore= clears any ignore patterns from pyproject.toml
# --select=PLC0415 enforces import placement (even if not in pyproject.toml select list)
```

```toml
# pyproject.toml (IDE config)
[tool.ruff.lint]
select = ["E", "W", "F"]  # Does NOT include PLC0415ignore = ["PLC0415"]  # Attempts to ignore import errors
```

**Result:** Gate 2 will **fail** on PLC0415 violations, regardless of `pyproject.toml` configuration.

### Migration Path (Pre-Issue #131)

**Before (hardcoded gates):**
- Quality gates were hardcoded in `QAManager._run_*` methods
- No `.st3/quality.yaml` file
- Gate activation required code changes

**After (config-driven):**
- All gates defined in `.st3/quality.yaml`
- Gate activation via `active_gates` list (no code changes)
- Gate definitions reusable across projects (copy quality.yaml)

---


### run_tests

**MCP Name:** `run_tests`  
**Class:** `RunTestsTool`  
**File:** [mcp_server/tools/test_tools.py](../../../../mcp_server/tools/test_tools.py)

Run pytest with structured JSON output. Returns per-failure details including traceback. Optimised for large test suites (1000+ tests).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | `str` | No* | Path(s) to test file(s) or director(y/ies). Space-separated for multiple: `"tests/unit tests/core/test_proxy.py"`. Mutually exclusive with `scope`. |
| `scope` | `str` | No* | Set to `"full"` to run the entire suite without path restriction. Mutually exclusive with `path`. |
| `markers` | `str` | No | Pytest marker expression, passed 1-to-1 as `-m`. Supports all pytest syntax: `"slow"`, `"not slow"`, `"slow or unit"`. |
| `last_failed_only` | `bool` | No | Re-run only previously failed tests (`--lf`). Default: `false`. |
| `timeout` | `int` | No | Timeout in seconds. Default: `300`. |

\* Either `path` or `scope` must be provided. Providing both raises a `ValidationError`.

#### Returns

Two content items are returned:

1. **JSON** — structured result:

```json
{
  "summary": {
    "passed": 43,
    "failed": 2
  },
  "summary_line": "2 failed, 43 passed in 12.50s",
  "failures": [
    {
      "test_id": "test_create_user",
      "location": "tests/test_user.py::test_create_user",
      "short_reason": "AssertionError: Expected 'admin' but got 'user'",
      "traceback": "tests/test_user.py:25: in test_create_user\n    assert role == 'admin'\nE   AssertionError: Expected 'admin' but got 'user'"
    }
  ]
}
```

> `failures` key is only present when `failed > 0`.

2. **Text** — human-readable summary line (e.g. `"2 failed, 43 passed in 12.50s"`).

#### Example Usage

**Run specific test file:**
```json
{ "path": "tests/mcp_server/unit/tools/test_test_tools.py" }
```

**Run multiple paths (space-separated):**
```json
{ "path": "tests/mcp_server/unit tests/mcp_server/core/test_proxy.py" }
```

**Run full suite:**
```json
{ "scope": "full" }
```

**Re-run only previously failed tests:**
```json
{ "path": "tests/", "last_failed_only": true }
```

**Run tests with marker filter:**
```json
{ "path": "tests/", "markers": "slow" }
```

**Exclude slow tests:**
```json
{ "path": "tests/", "markers": "not slow" }
```

#### Pytest Markers

Markers currently defined in `pyproject.toml`:

| Marker | Description |
|--------|-------------|
| `slow` | Slow-running tests, skipped by default in CI |
| `manual` | Tests requiring manual setup or live credentials |
| `asyncio` | Async tests (asyncio_mode = strict) |

#### Behavior Notes

- **No temp file:** Output is returned directly in the tool response — no intermediate file.
- **--tb=short:** Always active; traceback per failure is captured in the `traceback` field.
- **Structured output:** `summary`, `summary_line`, and `failures` (with traceback) are always present.
- **Timeout:** Kills the pytest process and raises `ExecutionError` if exceeded.
- **venv-aware:** Uses `sys.executable -m pytest` — always the venv's pytest, never system pytest.

---

### validate_architecture

**MCP Name:** `validate_architecture`  
**Class:** `ValidationTool`  
**File:** [mcp_server/tools/validation_tools.py](../../../../mcp_server/tools/validation_tools.py)

Validate code against architectural patterns (DTO, worker, platform conventions).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scope` | `str` | No | Validation scope: `"all"`, `"dtos"`, `"workers"`, `"platform"` (default: `"all"`) |

#### Returns

```json
{
  "success": true,
  "results": {
    "dtos": {
      "passed": true,
      "files_checked": 12,
      "violations": []
    },
    "workers": {
      "passed": false,
      "files_checked": 8,
      "violations": [
        {
          "file": "backend/workers/order_worker.py",
          "rule": "Worker must inherit from BaseWorker",
          "line": 10
        }
      ]
    },
    "platform": {
      "passed": true,
      "files_checked": 20,
      "violations": []
    }
  },
  "overall_passed": false
}
```

#### Example Usage

**Validate everything:**
```json
{
  "scope": "all"
}
```

**Validate DTOs only:**
```json
{
  "scope": "dtos"
}
```

#### Validation Scopes

| Scope | Checks | Files |
|-------|--------|-------|
| `all` | DTOs + workers + platform | All `backend/` files |
| `dtos` | Dataclass, frozen, type hints | `backend/dtos/**/*.py` |
| `workers` | BaseWorker inheritance, methods | `backend/workers/**/*.py` |
| `platform` | Import conventions, structure | All `backend/` files |

#### DTO Validation Rules

- Must use `@dataclass` decorator
- Should use `frozen=True` for immutability
- All fields must have type hints
- No mutable defaults (use `field(default_factory=...)` instead)

#### Worker Validation Rules

- Must inherit from `BaseWorker`
- Must implement `execute()` method
- Must use async/await patterns

#### Platform Validation Rules

- Must follow import order (stdlib → third-party → local)
- Must use absolute imports (not relative)
- Must follow directory structure from [.st3/project_structure.yaml](../../../../.st3/project_structure.yaml)

---

### validate_dto

**MCP Name:** `validate_dto`  
**Class:** `ValidateDTOTool`  
**File:** [mcp_server/tools/validation_tools.py](../../../../mcp_server/tools/validation_tools.py)

Validate DTO definition against DTO-specific rules.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | `str` | **Yes** | Path to DTO file |

#### Returns

```json
{
  "success": true,
  "dto": {
    "name": "UserDTO",
    "file": "backend/dtos/user.py",
    "fields": [
      {"name": "id", "type": "int"},
      {"name": "username", "type": "str"},
      {"name": "email", "type": "str"},
      {"name": "roles", "type": "list[str]"}
    ],
    "frozen": true,
    "violations": []
  }
}
```

**With violations:**
```json
{
  "success": false,
  "dto": {
    "name": "OrderDTO",
    "file": "backend/dtos/order.py",
    "violations": [
      {
        "rule": "Field 'items' has mutable default (list)",
        "line": 15,
        "suggestion": "Use field(default_factory=list) instead"
      },
      {
        "rule": "Missing type hint for field 'status'",
        "line": 20
      }
    ]
  }
}
```

#### Example Usage

```json
{
  "file_path": "backend/dtos/user.py"
}
```

#### DTO Validation Rules

| Rule | Severity | Description |
|------|----------|-------------|
| Must use `@dataclass` | ERROR | DTO must be a dataclass |
| Should use `frozen=True` | WARNING | DTOs should be immutable |
| All fields must have types | ERROR | Type hints required for all fields |
| No mutable defaults | ERROR | Use `field(default_factory=...)` for lists/dicts |
| Field names snake_case | WARNING | Follow Python naming conventions |
| Class name PascalCase + DTO suffix | WARNING | Naming convention |

---

### validate_template

**MCP Name:** `validate_template`  
**Class:** `TemplateValidationTool`  
**File:** [mcp_server/tools/template_validation_tool.py](../../../../mcp_server/tools/template_validation_tool.py)

Validate a file's structure against a project template (worker, tool, dto, adapter, base).

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | `str` | **Yes** | Absolute path to the file |
| `template_type` | `str` | **Yes** | Template type: `"worker"`, `"tool"`, `"dto"`, `"adapter"`, `"base"` |

#### Returns

```json
{
  "success": true,
  "validation": {
    "file": "backend/workers/order_worker.py",
    "template_type": "worker",
    "conforms": true,
    "violations": []
  }
}
```

**With violations:**
```json
{
  "success": false,
  "validation": {
    "file": "backend/workers/custom_worker.py",
    "template_type": "worker",
    "conforms": false,
    "violations": [
      {
        "section": "Class Definition",
        "expected": "Must inherit from BaseWorker",
        "actual": "Inherits from object"
      },
      {
        "section": "Methods",
        "expected": "Must implement execute() method",
        "actual": "execute() method missing"
      }
    ]
  }
}
```

#### Example Usage

```json
{
  "path": "/workspace/backend/workers/order_worker.py",
  "template_type": "worker"
}
```

#### Template Types

| Template | Sections Validated | Key Requirements |
|----------|-------------------|------------------|
| `worker` | Imports, class, methods | Inherit BaseWorker, implement execute() |
| `tool` | Imports, class, methods | Inherit BaseTool, implement run() |
| `dto` | Imports, dataclass, fields | Use @dataclass, type hints, frozen |
| `adapter` | Imports, class, methods | Inherit BaseAdapter, implement interface |
| `base` | Imports, class | Base class pattern validation |

#### Behavior Notes

- Uses template definitions from [.st3/artifacts.yaml](../../../../.st3/artifacts.yaml)
- Validates SCAFFOLD header format (if present) against [.st3/scaffold_metadata.yaml](../../../../.st3/scaffold_metadata.yaml)
- Returns detailed violation messages with line numbers
- `conforms=true` means file fully matches template spec

---

## Integration with safe_edit_file

Quality validation is automatically triggered by `safe_edit_file` in `strict` and `interactive` modes:

```python
# safe_edit_file delegates to ValidationService
# ValidationService selects validator by file extension:

.py → PythonValidator
      ├─ Syntax check (ast.parse)
      ├─ run_quality_gates (Ruff, Pyright — config-driven)
      └─ validate_architecture (if backend/ file)

.md → MarkdownValidator
      ├─ Structure validation
      └─ SCAFFOLD header format

SCAFFOLD header → TemplateValidator
                  └─ validate_template
```

---

## Configuration

### .st3/quality.yaml (authoritative)

All gate definitions, ordering, and behavior live in [.st3/quality.yaml](../../../../.st3/quality.yaml). See the [Quality Gate Configuration](#quality-gate-configuration) section above for the full schema.

Key config sections:

| Section | Purpose |
|---------|---------|
| `active_gates` | Ordered list of gate IDs to execute |
| `gates.<id>.execution` | Command, timeout, working_dir |
| `gates.<id>.parsing` | Strategy (`exit_code`, `json_field`, `text_regex`) and field mappings |
| `gates.<id>.success` | Pass/fail criteria (exit codes, max errors, regex patterns) |
| `gates.<id>.capabilities` | File types, autofix support, JSON output flag |
| `gates.<id>.scope` | Optional include/exclude globs (e.g., Gate 4 Mypy runs on `backend/dtos/**` only) |
| `artifact_logging` | Enable/disable, output dir, max file count |

---

## Common Use Cases

### Pre-Commit Quality Check

```
1. git_status() → get list of modified files
2. run_quality_gates(files=[...modified files...])
3. run_tests(path="tests/", markers="unit")
4. If all pass: git_add_or_commit(phase="green", message="...")
```

### TDD Red Phase

```
1. scaffold_artifact(artifact_type="dto", name="OrderDTO")
2. run_tests(path="tests/test_order.py") → expect failure
3. git_add_or_commit(phase="red", message="Add failing test")
```

### TDD Green Phase with Validation

```
1. safe_edit_file(..., mode="strict") → auto-runs quality gates
2. run_tests(path="tests/test_order.py") → expect pass
3. validate_dto(file_path="backend/dtos/order.py")
4. git_add_or_commit(phase="green", message="Implement OrderDTO")
```

### Architecture Audit

```
1. validate_architecture(scope="all")
2. Review violations
3. Fix violations
4. run_quality_gates(files=[...fixed files...])
```

---

## Related Documentation

- [README.md](README.md) — MCP Tools navigation index
- [editing.md](editing.md) — safe_edit_file and quality gate integration
- [.st3/quality.yaml](../../../../.st3/quality.yaml) — Quality gate configuration
- [.st3/artifacts.yaml](../../../../.st3/artifacts.yaml) — Template definitions for validation
- [docs/reference/mcp/validation_api.md](../validation_api.md) — ValidationService API reference
- [docs/development/issue19/research.md](../../../development/issue19/research.md) — Tool inventory research (Section 1.11: Quality tools)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.1 | 2026-02-12 | Agent | Aligned with actual v2.0 response schema: full gate structure, timings, environment metadata, command block, output/truncation, artifact logging, parsing strategies, all 8 active gates |
| 2.0 | 2026-02-08 | Agent | Complete reference for 5 quality tools: quality gates, tests, architecture validation, DTO validation, template validation |

<!-- docs/reference/mcp/tools/quality.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-02-08 -->
# Quality & Validation Tools

**Status:** DEFINITIVE  
**Version:** 2.0  
**Last Updated:** 2026-02-08  

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

```json
{
  "overall_pass": false,
  "gates": [
    {
      "gate_number": 0,
      "name": "File Filtering",
      "passed": true,
      "score": "N/A",
      "issues": []
    },
    {
      "gate_number": 1,
      "name": "Gate 1: Formatting",
      "passed": true,
      "score": "Pass",
      "issues": []
    }
  ]
}
```

**Notes:**
- `hints` (optional): when a gate fails, it may include `hints: list[str]` with targeted, actionable next-step guidance (primarily intended for automated agents).

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
- File-based static gates (Gates 0-4: Ruff, Mypy) are **skipped** (no file list provided)
- Used for CI/CD test/coverage enforcement before merge
- Example use case: Block PR merge if tests fail or coverage < 90%
- **Note:** For full-repo static analysis, provide explicit file list via Git diff or glob

**File-specific validation mode (`files=[...]`):**
- Runs **file-based static gates** (Gates 0-4: Ruff formatting, linting, imports, line length, type checking)
- **Skips** pytest gates (Gate 5 & 6) - tests run at project-level, not per-file
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
  - gate0_ruff_format
  - gate1_formatting
  - gate2_imports
  - gate3_line_length
  - gate4_types
  - gate5_tests

gates:
  gate0_ruff_format:
    name: "Gate 0: Ruff Format"
    description: "Code formatting (ruff format --check)"
    execution:
      command: ["python", "-m", "ruff", "format", "--check", "--diff", "--isolated", "--line-length=100"]
      timeout_seconds: 60
      working_dir: null
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
      command: ["python", "-m", "ruff", "check", "--isolated", "--select=E,W,F,I,N,UP,ANN,B,C4,DTZ,T10,ISC,RET,SIM,ARG,PLC", "--ignore=E501,PLC0415", "--line-length=100", "--target-version=py311"]
      timeout_seconds: 60
      working_dir: null
    parsing:
      strategy: "exit_code"
    success:
      mode: "exit_code"
      exit_codes_ok: [0]
    capabilities:
      file_types: [".py"]
      supports_autofix: true
      produces_json: false
```

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

Run pytest with optional markers, path filtering, and timeout.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `path` | `str` | No | Path to test file or directory (default: `"tests/"`) |
| `markers` | `str` | No | Pytest markers to filter by (e.g., `"unit"`, `"integration"`) |
| `verbose` | `bool` | No | Verbose output (`-v` flag) (default: `True`) |
| `timeout` | `int` | No | Timeout in seconds (default: `300`) |

#### Returns

```json
{
  "success": true,
  "summary": {
    "total": 45,
    "passed": 43,
    "failed": 2,
    "skipped": 0,
    "duration": 12.5
  },
  "failures": [
    {
      "test": "tests/test_user.py::test_create_user",
      "message": "AssertionError: Expected 'admin' but got 'user'"
    },
    {
      "test": "tests/test_auth.py::test_login_expired_token",
      "message": "ValidationError: Token expired"
    }
  ],
  "output": "============================= test session starts ==============================\n..."
}
```

#### Example Usage

**Run all tests:**
```json
{
  "path": "tests/"
}
```

**Run specific test file:**
```json
{
  "path": "tests/test_user.py",
  "verbose": true
}
```

**Run tests with markers:**
```json
{
  "path": "tests/",
  "markers": "unit",
  "timeout": 60
}
```

**Run integration tests only:**
```json
{
  "markers": "integration",
  "timeout": 600
}
```

#### Pytest Markers

Common markers (defined in [pytest.ini](../../../../pytest.ini)):

| Marker | Description | Example |
|--------|-------------|---------|
| `unit` | Fast unit tests | `@pytest.mark.unit` |
| `integration` | Slower integration tests | `@pytest.mark.integration` |
| `slow` | Slow-running tests | `@pytest.mark.slow` |
| `github` | Tests requiring GitHub API | `@pytest.mark.github` |

#### Behavior Notes

- **Default Path:** If no path specified, runs all tests in `tests/` directory
- **Timeout:** Returns error if tests exceed timeout (kills pytest process)
- **Verbose:** Default `verbose=True` provides detailed output
- **Failure Details:** Captures failure messages and stack traces
- **Exit Code:** `success=false` if any tests fail or timeout exceeded

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
      ├─ run_quality_gates (pylint, mypy)
      └─ validate_architecture (if backend/ file)

.md → MarkdownValidator
      ├─ Structure validation
      └─ SCAFFOLD header format

SCAFFOLD header → TemplateValidator
                  └─ validate_template
```

---

## Configuration

### .st3/quality.yaml

```yaml
quality_gates:
  python:
    - tool: pylint
      enabled: true
      min_score: 8.0
      ignore_patterns:
        - "W0613"  # unused-argument
        - "R0903"  # too-few-public-methods (for DTOs)
    
    - tool: mypy
      enabled: true
      strict: false
      config_file: "pyproject.toml"
    
    - tool: pyright
      enabled: true
      fallback_to_mypy: true
      config_file: "pyrightconfig.json"
  
  test:
    pytest:
      default_markers: "unit"
      default_timeout: 300
```

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
| 2.0 | 2026-02-08 | Agent | Complete reference for 5 quality tools: quality gates, tests, architecture validation, DTO validation, template validation |

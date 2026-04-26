# Quality Gates

## Overview

> **⚠️ Read first:** [ARCHITECTURE_PRINCIPLES.md](ARCHITECTURE_PRINCIPLES.md) — tooling gates validate *form*, architectural principles validate *correctness*. Code can pass all gates and still be REJECTED on architectural grounds.

All code must pass **8 mandatory quality gates** before merging to main. Each gate must **pass** (exit code 0) to ensure code quality and consistency.

## Configuration Doctrine: IDE vs CI

**Two-tier quality enforcement strategy:**

1. **`pyproject.toml`** = **IDE Baseline** (Pragmatic)
   - Used by VS Code, PyCharm, and local Ruff/Mypy runs
   - Balanced for developer productivity
   - May have pragmatic ignores for known false positives

2. **`ci-quality.yaml` (or equivalent CI config)** = **CI Authority** (Strict)
   - Used by quality gates in CI/CD pipelines
   - Stricter enforcement before merge
   - Ruff gates use `--isolated` flag to ignore IDE config
   - Final arbiter for pull request approval

3. **Gates apply to production AND test code**
   - All Python files in `backend/`, `mcp_server/`, and `tests/` must pass
   - Tests held to same quality bar as production code

4. **Ruff `--isolated` mode in CI**
   - Gates 0-3 run with `--isolated` to prevent inheriting IDE ignores
   - Ensures deterministic, strict enforcement independent of local settings

**Result:** Developers get helpful local feedback, while CI enforces non-negotiable quality standards.

## Gate Checklist

Every DTO implementation must pass all gates for **both** the DTO file and its test file:

- [ ] Gate 0: Ruff Format
- [ ] Gate 1: Ruff Strict Lint
- [ ] Gate 2: Import Placement
- [ ] Gate 3: Line Length
- [ ] Gate 4: Type Checking (DTOs only)
- [ ] Gate 5: Tests Passing
- [ ] Gate 6: Code Coverage (>= 90%)
- [ ] Gate 7: Architectural Review (see ARCHITECTURE_PRINCIPLES.md)

### Gate 0: Ruff Format

**Purpose:** Enforce consistent formatting (formatter check is as important as lint).

```powershell
# Check formatting (no changes written)
python -m ruff format --isolated --check --diff --line-length=100 backend/dtos/strategy/my_dto.py
python -m ruff format --isolated --check --diff --line-length=100 tests/unit/dtos/strategy/test_my_dto.py

# Apply formatting (writes changes)
python -m ruff format --isolated --line-length=100 backend/dtos/strategy/my_dto.py
python -m ruff format --isolated --line-length=100 tests/unit/dtos/strategy/test_my_dto.py

```

**Expected:** `Pass` (exit code 0)

### Gate 1: Ruff Strict Lint (excluding line length & import placement)

**Purpose:** Enforce strict linting in CI (stricter than VS Code baseline).

**Note:** This gate intentionally excludes:
- **E501** (line length) → Checked separately in Gate 3
- **PLC0415** (import placement) → Checked separately in Gate 2

This separation follows Single Responsibility Principle - each gate validates one specific aspect.

**What is ANN?** Type annotation rules (`flake8-annotations`) - ensures function parameters and return types have explicit type hints. This applies to both production code and test files.

```powershell
# Strict lint (same intent as CI gate; does not inherit IDE ignores)
python -m ruff check --isolated --select=E,W,F,I,N,UP,ANN,B,C4,DTZ,T10,ISC,RET,SIM,ARG,PLC --ignore=E501,PLC0415 --line-length=100 --target-version=py311 backend/dtos/strategy/my_dto.py
python -m ruff check --isolated --select=E,W,F,I,N,UP,ANN,B,C4,DTZ,T10,ISC,RET,SIM,ARG,PLC --ignore=E501,PLC0415 --line-length=100 --target-version=py311 tests/unit/dtos/strategy/test_my_dto.py

# Optional: apply safe autofixes
python -m ruff check --fix --isolated --select=E,W,F,I,N,UP,ANN,B,C4,DTZ,T10,ISC,RET,SIM,ARG,PLC --ignore=E501,PLC0415 --line-length=100 --target-version=py311 backend/dtos/strategy/my_dto.py
python -m ruff check --fix --isolated --select=E,W,F,I,N,UP,ANN,B,C4,DTZ,T10,ISC,RET,SIM,ARG,PLC --ignore=E501,PLC0415 --line-length=100 --target-version=py311 tests/unit/dtos/strategy/test_my_dto.py
```

**Expected:** `Pass` (exit code 0)

**Common ANN violations in tests:**
```python
# ❌ WRONG - test function missing return type
def test_my_feature(dto):
    assert dto.value == 42

# ✅ CORRECT - explicit return type
def test_my_feature(dto: MyDTO) -> None:
    assert dto.value == 42
```

### Gate 2: Import Placement

**Purpose:** All imports must be at top-level (never inside functions/methods).

**Note:** Scaffolded files automatically comply via base templates (`base_component.py.jinja2`, `base_test.py.jinja2`). This gate validates non-scaffolded or manually edited files.

```powershell
# Check DTO file
python -m ruff check --isolated --select=PLC0415 --target-version=py311 backend/dtos/strategy/my_dto.py

# Check test file
python -m ruff check --isolated --select=PLC0415 --target-version=py311 tests/unit/dtos/strategy/test_my_dto.py
```

**Expected:** `Pass` (exit code 0)

**Common violation:**
```python
# ❌ WRONG - import inside function
def my_function():
    from datetime import datetime  # NEVER DO THIS
    return datetime.now()

# ✅ CORRECT - import at top (enforced by scaffolding templates)
from datetime import datetime

def my_function():
    return datetime.now()
```

### Gate 3: Line Length

**Purpose:** Enforce maximum line length of 100 characters for readability.

```powershell
# Check DTO file
python -m ruff check --isolated --select=E501 --line-length=100 --target-version=py311 backend/dtos/strategy/my_dto.py

# Check test file
python -m ruff check --isolated --select=E501 --line-length=100 --target-version=py311 tests/unit/dtos/strategy/test_my_dto.py
```

**Expected:** `Pass` (exit code 0)

**Techniques to fix:**
- Split long assertions into multiple variables
- Use line continuation for long strings
- Break method chains across lines

```python
# ❌ WRONG - line too long
assert dto.some_very_long_field_name == expected_very_long_value_name  # Line 102 chars

# ✅ CORRECT - use intermediate variable
field_value = dto.some_very_long_field_name
assert field_value == expected_very_long_value_name
```

### Gate 4: Type Checking

**Purpose:** Ensure type safety with mypy strict mode (DTOs only).

```powershell
# Check DTO file only (tests may have Pydantic false positives)
python -m mypy backend/dtos/strategy/my_dto.py --strict --no-error-summary
```

**Expected:** `0 errors` for DTO file

**Note:** Test files are exempt from this gate due to known Pydantic FieldInfo limitations (see "Known Acceptable Warnings" below).

### Gate 5: Tests Passing

**Purpose:** All unit tests must pass (correctness validation).

```powershell
pytest tests/unit/dtos/strategy/test_my_dto.py -q --tb=line
```

**Expected:** All tests passing

**Note:** Coverage is enforced separately in Gate 6 (SRP: tests validate correctness, coverage validates thoroughness).

### Gate 6: Code Coverage

**Purpose:** Ensure comprehensive test coverage with branch coverage >= 90%.

```powershell
# Check coverage for backend and mcp_server packages
pytest tests/ --cov=backend --cov=mcp_server --cov-branch --cov-fail-under=90 --tb=short
```

**Expected:** Branch coverage >= 90% (hard fail below threshold)

**Scope:** Production packages only:
- `backend/` - Core trading logic
- `mcp_server/` - MCP server implementation

**Why separate from Gate 5?**
- **Gate 5:** Validates test correctness (do tests pass?)
- **Gate 6:** Validates test thoroughness (are all code paths tested?)
- Follows Single Responsibility Principle - each gate checks one aspect

**Adding new packages:** When adding new production Python packages, extend Gate 6 scope:
```powershell
pytest tests/ --cov=backend --cov=mcp_server --cov=new_package --cov-branch --cov-fail-under=90
```

## Post-Implementation Workflow

### Gate 7: Architectural Review

**Purpose:** Ensure code conforms to the architectural principles in [ARCHITECTURE_PRINCIPLES.md](ARCHITECTURE_PRINCIPLES.md). This gate is a **human/agent review**, not a tooling check.

**Checklist — run through these questions for every PR:**

| Question | Expected answer |
|---|---|
| Does each new class have exactly one responsibility? | Yes — otherwise split |
| Are there if-chains on phase names, action types, or workflow names? | No — OCP violation |
| Is business knowledge (phase names, commit-type maps, branch types) stored in config? | Yes — Config-First |
| Are dependencies injected via constructor? | Yes — DIP |
| Are read-only consumers limited to a narrow read interface? | Yes — ISP |
| Do `get_state()` / `get_current_phase()` return without calling `save()`? | Yes — CQS |
| Are value objects `frozen=True`? | Yes — CQS enforcement |
| Are singletons implemented via `ClassVar` + lazy init (no module-level side effects)? | Yes — Fail-Fast |
| Does the config loader validate inconsistent config combinations at startup? | Yes — Fail-Fast |
| Is there a new hardcoded list or regex with branch types or phase names? | No — read from config |
| Were migration layers written for deprecated parameters? | No — YAGNI |
| Does each new method belong to the class of its domain? | Yes — Cohesion |

**If in doubt:** consult [ARCHITECTURE_PRINCIPLES.md](ARCHITECTURE_PRINCIPLES.md) for the full principle definitions and prohibited patterns.

Complete workflow for a new DTO:

```powershell
# Step 1: Apply formatting (writes changes)
python -m ruff format --isolated --line-length=100 backend/dtos/strategy/my_dto.py
python -m ruff format --isolated --line-length=100 tests/unit/dtos/strategy/test_my_dto.py

# Step 2: Run lint gates
python -m ruff check --isolated --select=E,W,F,I,N,UP,ANN,B,C4,DTZ,T10,ISC,RET,SIM,ARG,PLC --ignore=E501,PLC0415 --line-length=100 --target-version=py311 backend/dtos/strategy/my_dto.py
python -m ruff check --isolated --select=PLC0415 --target-version=py311 backend/dtos/strategy/my_dto.py
python -m ruff check --isolated --select=E501 --line-length=100 --target-version=py311 backend/dtos/strategy/my_dto.py

# Step 3: Run type checking (DTOs only)
python -m mypy backend/dtos/strategy/my_dto.py --strict --no-error-summary

# Step 4: Run tests
pytest tests/unit/dtos/strategy/test_my_dto.py -q --tb=line

# Step 5: Run coverage (entire test suite with branch coverage)
pytest tests/ --cov=backend --cov=mcp_server --cov-branch --cov-fail-under=90 --tb=short
```

## Bulk Quality Checks

Check all modified files at once:

```powershell
# Find all modified Python files
git diff --name-only | Where-Object { $_ -like "*.py" } | ForEach-Object {
    python -m ruff format --isolated --check --diff --line-length=100 $_
    python -m ruff check --isolated --select=E,W,F,I,N,UP,ANN,B,C4,DTZ,T10,ISC,RET,SIM,ARG,PLC --ignore=E501,PLC0415 --line-length=100 --target-version=py311 $_
    python -m ruff check --isolated --select=PLC0415 --target-version=py311 $_
    python -m ruff check --isolated --select=E501 --line-length=100 --target-version=py311 $_
}
```

## pyrightconfig.json Configuration

Project uses `pyrightconfig.json` for consistent type checking:

```json
{
  "pythonVersion": "3.13",
  "typeCheckingMode": "basic",
  "reportUnknownMemberType": false,
  "reportUnknownVariableType": false,
  "reportCallIssue": false,
  "reportArgumentType": false,
  "reportAttributeAccessIssue": false
}
```

**Rationale:**
- **Python 3.13 target** - Project language version
- **Basic mode** - Pragmatic balance (not overly strict)
- **Disabled checks** - Suppress Pydantic-specific false positives
- **Enabled checks** - Unused imports, duplicate imports, undefined variables

## Known Acceptable Warnings

### 1. Pydantic Field() with Generics
**Standard policy:** Follow [TYPE_CHECKING_PLAYBOOK.md](TYPE_CHECKING_PLAYBOOK.md) for the mandatory resolution order (narrow → refactor types → targeted ignore). This keeps agent fixes consistent and avoids global disables.


**Issue:** `list[ContextFactor]` triggers "partially unknown" warnings

**Fix:** Add inline type ignore:
```python
factors: list[ContextFactor] = Field(
    default_factory=list,
    description="Context factors"
)  # type: ignore[valid-type]
```

### 2. Pydantic FieldInfo in Tests

**Issue:** Pylance doesn't recognize that Pydantic fields resolve to actual values at runtime.

**Pattern:** `signal.initiator_id.startswith("TCK_")` → "FieldInfo has no member 'startswith'"

**Preferred fix:** Use `getattr()` to bypass type narrowing:
```python
# ✅ BEST - Use getattr()
assert getattr(signal, "initiator_id").startswith("TCK_")

# ✅ ACCEPTABLE - Intermediate variable (legacy pattern)
initiator_id = str(signal.initiator_id)
assert initiator_id.startswith("TCK_")
```

**For complex nested attributes:**
```python
from typing import cast
from datetime import datetime

# Datetime attributes need casting + getattr
dt = cast(datetime, directive.decision_timestamp)
assert getattr(dt, "tzinfo") is not None
```

**Status:** Runtime works perfectly, all tests pass. This is a Pylance limitation.

### 3. Pydantic Optional Fields

**Issue:** `Field(None, ...)` triggers "missing parameter" warnings

**Root cause:** Pylance doesn't recognize `Field(None, default=None)` pattern

**Fix:** Already suppressed globally via `pyrightconfig.json`:
```json
{
  "reportCallIssue": false,
  "reportArgumentType": false,
  "reportAttributeAccessIssue": false
}
```

**Status:** Systematically suppressed at workspace level - no action needed.

### 4. Pytest Fixture Redefined Names (W0621)

**Issue:** Fixtures that depend on other fixtures can shadow names at module scope, causing linter warnings.

**Preferred pattern:** Fixture aliasing with `name=` parameter:
```python
# ✅ BEST - Private function name + public fixture name
@pytest.fixture(name="temp_workspace")
def _temp_workspace(...) -> Path:
    """Hermetic workspace fixture."""
    ...

@pytest.fixture(name="artifact_manager")
def _artifact_manager(
    temp_workspace: Path,  # ✅ No conflict - 'temp_workspace' is only a fixture name
    ...
) -> ArtifactManager:
    ...
```

**Benefits:**
- Zero suppressions needed
- Test code unchanged (uses public fixture name)
- No module-scope symbol collision
- Standard pytest pattern for fixture composition

**Status:** Use this pattern for all fixtures that inject other fixtures as parameters.


### 5. Integration Test Boundary Contract

Integration tests in `tests/mcp_server/integration/` are part of the **default test suite** and run with every `pytest tests/mcp_server` invocation. The following contract must hold to keep the full suite safe and side-effect-free.

**What "integration" means in this codebase:**

| Characteristic | Rule |
|---|---|
| External API adapter | Always mocked (`MagicMock` or `MagicMock(spec=...)`) |
| Filesystem writes | Exclusively via `tmp_path` (pytest fixture) |
| Real workspace reads | Permitted for read-only operations (e.g. `ruff`/`mypy` on a real source file) |
| Network calls | Never — zero real HTTP/GitHub API traffic |
| Side effects outside `tmp_path` | Not allowed — test must be fully reversible |
| Environment variable guards | Not needed — the adapter boundary is the safety layer |

Integration tests exercise multiple real layers simultaneously (e.g. tool + manager + config) while mocking the external boundary. They are not slower-running tests requiring an opt-in flag; they are hermetic tests with a wider internal scope.

**Boundary enforcement:**

The `test_pytest_config.py` suite actively guards these invariants:

- `testpaths = ["tests/mcp_server"]` — backend tests never run implicitly
- No `-m not integration` filter — the integration marker is intentionally abolished (merged via #237)
- `integration` marker not defined in `pyproject.toml` — not needed because the adapter boundary provides safety, not a marker
- `asyncio_mode = "strict"` — async tests pay no event-loop overhead unless marked
- `pytest-xdist` enabled via `-n auto` — parallel execution requires `tmp_path` isolation

**Writing a new integration test — checklist:**

- [ ] File lives in `tests/mcp_server/integration/`
- [ ] Module docstring includes `@layer: Tests (Integration)`
- [ ] External API adapter replaced with `MagicMock` or `MagicMock(spec=AdapterClass)`
- [ ] All filesystem writes via `tmp_path` — never writes to the real workspace
- [ ] No env-gated or opt-in skip guard (no `pytest.mark.skipif(os.getenv(...))` or `pytest.skip` conditioned on an environment variable)
- [ ] No `subprocess.run` targeting remote services — local git ops on `tmp_path` are fine
- [ ] Compatible with `pytest-xdist` parallel execution (no shared mutable state between test functions)

## Code Review Rejection Criteria

**REJECT if any of these conditions:**

*Tooling (automated):*
- ❌ Any quality gate fails (non-zero exit code)
- ❌ Failing tests
- ❌ Missing type hints
- ❌ Imports inside functions (must be top-level)
- ❌ Code without tests (for new features)
- ❌ Lines > 100 characters
- ❌ Import grouping violations (see [CODE_STYLE.md](CODE_STYLE.md))

*Architecture (Gate 7 — human/agent review):*
- ❌ Hardcoded phase/workflow/branch-type names in production code (Config-First)
- ❌ Dependency instantiated inside `execute()` or other methods (DIP)
- ❌ Read-only consumer injected with write-capable interface (ISP)
- ❌ Query method calls `save()` or mutates state (CQS)
- ❌ Module-level `Config.load()` or similar — import-time side effects
- ❌ God Class with multiple unrelated responsibilities (SRP)
- ❌ If-chain on type/phase/action — use registry or config-driven dispatch (OCP)

**ACCEPT only when:**
- ✅ All quality gates pass (exit code 0)
- ✅ All tests green (no skips)
- ✅ Type hints complete
- ✅ Docstrings present (module + public methods)
- ✅ No trailing whitespace
- ✅ Imports at top-level
- ✅ Max line length 100 chars
- ✅ Import grouping correct
- ✅ Gate 7 architectural review checklist passes

## VS Code Settings (Recommended)

Add to `.vscode/settings.json`:

```json
{
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true,
    "editor.rulers": [100],
    "python.analysis.typeCheckingMode": "basic"
}
```

## Related Documentation

- [TDD_WORKFLOW.md](TDD_WORKFLOW.md) - Test-driven development cycle
- [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - Branching and commit conventions
- [CODE_STYLE.md](CODE_STYLE.md) - Code formatting standards

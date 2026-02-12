# Quality Gates

## Overview

All code in S1mpleTrader V3 must pass **7 mandatory quality gates** before merging to main. Each gate must **pass** (exit code 0) to ensure code quality and consistency.

## Configuration Doctrine: IDE vs CI

**Two-tier quality enforcement strategy:**

1. **`pyproject.toml`** = **IDE Baseline** (Pragmatic)
   - Used by VS Code, PyCharm, and local Ruff/Mypy runs
   - Balanced for developer productivity
   - May have pragmatic ignores for known false positives

2. **`.st3/quality.yaml`** = **CI Authority** (Strict)
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

# ✅ CORRECT - import at top
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

**Issue:** Fixtures that depend on other fixtures trigger `redefined-outer-name` when fixture names exist at module scope.

**Pattern:**
```python
@pytest.fixture
def temp_workspace(...) -> Path:
    ...

@pytest.fixture
def artifact_manager(
    temp_workspace: Path,  # ❌ W0621: redefines 'temp_workspace' from outer scope
    ...
) -> ArtifactManager:
    ...
```

**Preferred fix:** Fixture aliasing with `name=` parameter:
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
- Pylint sees no module-scope symbol collision
- Standard pytest pattern for fixture composition

**Status:** Use this pattern for all fixtures that inject other fixtures as parameters.

## Code Review Rejection Criteria

**REJECT if any of these conditions:**

- ❌ Pylint score < 10.00 for whitespace/parens/imports
- ❌ Failing tests
- ❌ Missing type hints
- ❌ Imports inside functions (must be top-level)
- ❌ Code without tests (for new features)
- ❌ Lines > 100 characters
- ❌ Import grouping violations (see [CODE_STYLE.md](CODE_STYLE.md))

**ACCEPT only when:**
- ✅ All quality gates pass (exit code 0)
- ✅ All tests green (no skips)
- ✅ Type hints complete
- ✅ Docstrings present (module + public methods)
- ✅ No trailing whitespace
- ✅ Imports at top-level
- ✅ Max line length 100 chars
- ✅ Import grouping correct

## VS Code Settings (Recommended)

Add to `.vscode/settings.json`:

```json
{
    "files.trimTrailingWhitespace": true,
    "files.insertFinalNewline": true,
    "editor.rulers": [100],
    "python.linting.pylintEnabled": true,
    "python.linting.enabled": true,
    "python.analysis.typeCheckingMode": "basic"
}
```

## Related Documentation

- [TDD_WORKFLOW.md](TDD_WORKFLOW.md) - Test-driven development cycle
- [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - Branching and commit conventions
- [CODE_STYLE.md](CODE_STYLE.md) - Code formatting standards

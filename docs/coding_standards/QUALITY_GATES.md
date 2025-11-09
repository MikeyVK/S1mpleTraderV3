# Quality Gates

## Overview

All code in S1mpleTrader V3 must pass **5 mandatory quality gates** before merging to main. Each gate checks specific aspects of code quality and must score **10.00/10**.

## Gate Checklist

Every DTO implementation must pass all gates for **both** the DTO file and its test file.

### Gate 1: Trailing Whitespace & Parens

**Purpose:** Ensure clean code without trailing spaces or superfluous parentheses.

```powershell
# Check DTO file
python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=trailing-whitespace,superfluous-parens

# Check test file
python -m pylint tests/unit/dtos/strategy/test_my_dto.py --disable=all --enable=trailing-whitespace,superfluous-parens
```

**Expected:** `10.00/10` for both files

**Auto-fix whitespace:**
```powershell
(Get-Content backend/dtos/strategy/my_dto.py) | ForEach-Object { $_.TrimEnd() } | Set-Content backend/dtos/strategy/my_dto.py
(Get-Content tests/unit/dtos/strategy/test_my_dto.py) | ForEach-Object { $_.TrimEnd() } | Set-Content tests/unit/dtos/strategy/test_my_dto.py
```

### Gate 2: Import Placement

**Purpose:** All imports must be at top-level (never inside functions/methods).

```powershell
# Check DTO file
python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=import-outside-toplevel

# Check test file
python -m pylint tests/unit/dtos/strategy/test_my_dto.py --disable=all --enable=import-outside-toplevel
```

**Expected:** `10.00/10` for both files

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
python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=line-too-long --max-line-length=100

# Check test file
python -m pylint tests/unit/dtos/strategy/test_my_dto.py --disable=all --enable=line-too-long --max-line-length=100
```

**Expected:** `10.00/10` for both files

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

**Purpose:** All unit tests must pass.

```powershell
pytest tests/unit/dtos/strategy/test_my_dto.py -q --tb=line
```

**Expected:** All tests passing (complete coverage, not arbitrary quantity targets)

## Post-Implementation Workflow

Complete workflow for a new DTO:

```powershell
# Step 1: Auto-fix trailing whitespace
(Get-Content backend/dtos/strategy/my_dto.py) | ForEach-Object { $_.TrimEnd() } | Set-Content backend/dtos/strategy/my_dto.py
(Get-Content tests/unit/dtos/strategy/test_my_dto.py) | ForEach-Object { $_.TrimEnd() } | Set-Content tests/unit/dtos/strategy/test_my_dto.py

# Step 2: Run all 5 gates for DTO
python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=trailing-whitespace,superfluous-parens
python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=import-outside-toplevel
python -m pylint backend/dtos/strategy/my_dto.py --disable=all --enable=line-too-long --max-line-length=100
python -m mypy backend/dtos/strategy/my_dto.py --strict --no-error-summary

# Step 3: Run all 5 gates for tests (except mypy)
python -m pylint tests/unit/dtos/strategy/test_my_dto.py --disable=all --enable=trailing-whitespace,superfluous-parens
python -m pylint tests/unit/dtos/strategy/test_my_dto.py --disable=all --enable=import-outside-toplevel
python -m pylint tests/unit/dtos/strategy/test_my_dto.py --disable=all --enable=line-too-long --max-line-length=100
pytest tests/unit/dtos/strategy/test_my_dto.py -q --tb=line

# Step 4: Verify VS Code Problems panel
# Only acceptable warnings should remain (see below)
```

## Bulk Quality Checks

Check all modified files at once:

```powershell
# Find all modified Python files
git diff --name-only | Where-Object { $_ -like "*.py" } | ForEach-Object {
    python -m pylint $_ --disable=all --enable=trailing-whitespace,superfluous-parens,import-outside-toplevel,line-too-long --max-line-length=100
}

# Cleanup trailing whitespace in bulk
Get-ChildItem -Recurse -Filter "*.py" | ForEach-Object {
    (Get-Content $_.FullName) | ForEach-Object { $_.TrimEnd() } | Set-Content $_.FullName
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

- ✅ All pylint checks at 10.00/10
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

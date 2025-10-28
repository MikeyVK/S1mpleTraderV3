# Test-Driven Development (TDD) Workflow

## Overview

S1mpleTrader V3 follows **strict TDD discipline** integrated with Git workflow. This is **NOT OPTIONAL** - all new features must follow the RED → GREEN → REFACTOR cycle with feature branches.

## Feature Branch Setup

Every new feature starts with a dedicated branch:

```powershell
# Create feature branch from main
git checkout -b feature/size-plan-dto
```

**Branch naming conventions:**
- `feature/*` - New DTOs, workers, adapters
- `fix/*` - Bug fixes
- `refactor/*` - Code quality improvements
- `docs/*` - Documentation only

## The TDD Cycle

### 1. RED Phase: Write Failing Tests First

Write comprehensive tests **BEFORE** any implementation.

```python
def test_new_feature():
    """Test that new feature works correctly."""
    result = my_new_function(input_data)
    assert result == expected_output  # FAILS - function not implemented
```

**Commit failing tests to document intent:**

```powershell
git add tests/unit/dtos/strategy/test_size_plan.py
git commit -m "test: add failing tests for SizePlan DTO

- Test creation with valid fields
- Test validation rules
- Test edge cases

Status: RED - tests fail (implementation pending)"
```

**Typical test count:** 20-30 tests per DTO covering:
- Creation tests (valid instantiation)
- Field validation tests (ranges, formats, types)
- Edge cases (boundaries, None handling)
- Immutability tests (frozen models)
- Cross-field validation (XOR, dependencies)

### 2. GREEN Phase: Minimal Implementation

Implement the **minimum code** needed to make tests pass.

```python
def my_new_function(data):
    """Implement minimal working solution."""
    return process(data)  # Test now PASSES
```

**Commit working implementation:**

```powershell
git add backend/dtos/strategy/size_plan.py
git commit -m "feat: implement SizePlan DTO

- Add quantity, risk_amount, position_value fields
- Add validation for positive values
- All tests passing (20/20)

Status: GREEN"
```

### 3. REFACTOR Phase: Improve Code Quality

Enhance code while keeping all tests green:

- Fix trailing whitespace
- Add/improve type hints
- Enhance docstrings
- Split long lines (<100 chars)
- Add `json_schema_extra` examples (see [CODE_STYLE.md](CODE_STYLE.md))

**Verify:** Tests remain 100% passing during refactoring!

```powershell
git add backend/dtos/strategy/size_plan.py tests/unit/dtos/strategy/test_size_plan.py
git commit -m "refactor: improve SizePlan DTO code quality

- Add comprehensive docstrings
- Fix line length violations
- Add type hints for all fields
- Clean up whitespace
- Add json_schema_extra examples

Quality gates: All 10/10
Status: GREEN (tests still 20/20)"
```

### 4. Quality Gates Verification

Run complete quality checklist (see [QUALITY_GATES.md](QUALITY_GATES.md)).

If all gates pass, update metrics:

```powershell
git add docs/implementation/IMPLEMENTATION_STATUS.md
git commit -m "docs: update Quality Metrics Dashboard for SizePlan

- Added SizePlan row: 10/10 all gates
- Test coverage: 20/20 passing"
```

### 5. Merge to Main

Once all quality gates pass, merge back to main:

```powershell
# Switch back to main
git checkout main

# Merge feature (squash or regular based on preference)
git merge feature/size-plan-dto

# Push to GitHub
git push origin main

# Delete feature branch
git branch -d feature/size-plan-dto
```

## Commit Message Conventions

Use **Conventional Commits** format with clear prefixes:

- `test:` - Tests only (Red phase)
- `feat:` - New feature implementation (Green phase)
- `refactor:` - Code quality improvements (Refactor phase)
- `docs:` - Documentation updates
- `fix:` - Bug fixes
- `chore:` - Build/tooling changes

**Message structure:**
```
<type>: <short summary>

<optional body with details>
- Bullet point 1
- Bullet point 2

<optional footer with status>
Status: RED|GREEN
Quality gates: 10/10
```

## Branching Strategy

- **`main`** - Always stable
  - All tests passing
  - All quality gates met (10/10)
  - No trailing whitespace
  - Imports at top-level only

- **`feature/*`** - Development branches
  - Commit early, commit often
  - RED → GREEN → REFACTOR commits
  - Only merge to main when ALL quality gates pass

## Anti-Patterns to Avoid

❌ **Direct commits to main** (use feature branches)

❌ **Combined test + implementation commits** (separate RED and GREEN)

❌ **Skipping test phase** (write tests first, always)

❌ **Breaking tests during refactor** (tests must stay green)

❌ **Merging with failing quality gates** (10/10 required)

## Historical Note

Recent commits (1d4258a, d3418dd, 7b62902) violated this workflow:
- No feature branches used (direct on main)
- Tests + implementation in single commit
- No separate RED phase commits

**From now on:** STRICT adherence to TDD + Git workflow. No exceptions.

## Related Documentation

- [QUALITY_GATES.md](QUALITY_GATES.md) - Quality checklist
- [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - Branching and commit conventions
- [CODE_STYLE.md](CODE_STYLE.md) - Code formatting standards

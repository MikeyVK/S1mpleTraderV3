# Coding Standards

## Overview

This directory contains the comprehensive coding standards for S1mpleTrader V3. All development must follow these guidelines to maintain code quality, consistency, and maintainability.

## Quick Links

📖 **Start Here:** [TDD_WORKFLOW.md](TDD_WORKFLOW.md) - Understand the development cycle

🎯 **Daily Use:** [QUALITY_GATES.md](QUALITY_GATES.md) - Pre-merge checklist

🌳 **Git Strategy:** [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - Branching and commits

✨ **Style Guide:** [CODE_STYLE.md](CODE_STYLE.md) - Code formatting rules

## Documentation Structure

### 1. [TDD_WORKFLOW.md](TDD_WORKFLOW.md)

**Test-Driven Development (TDD) Workflow**

Learn the RED → GREEN → REFACTOR cycle with Git integration.

**Topics:**
- Feature branch setup
- RED phase: Write failing tests first
- GREEN phase: Minimal implementation
- REFACTOR phase: Code quality improvements
- Quality gates verification
- Merge to main workflow
- Commit message conventions
- Historical anti-patterns to avoid

**When to read:**
- Starting a new feature/DTO
- Need reminder of TDD discipline
- Uncertain about commit structure

### 2. [QUALITY_GATES.md](QUALITY_GATES.md)

**Quality Gates - Pre-Merge Checklist**

The 5 mandatory quality gates that all code must pass.

**Topics:**
- Gate 1: Trailing whitespace & parens (10/10 required)
- Gate 2: Import placement (top-level only)
- Gate 3: Line length (<100 chars)
- Gate 4: Type checking (mypy strict for DTOs)
- Gate 5: Tests passing (100%)
- Post-implementation workflow
- Bulk quality checks
- pyrightconfig.json configuration
- Known acceptable warnings (Pydantic limitations)
- Code review rejection criteria

**When to read:**
- Before merging to main
- Fixing quality gate failures
- Understanding VS Code warnings
- Setting up new workspace

### 3. [GIT_WORKFLOW.md](GIT_WORKFLOW.md)

**Git Workflow - Branching & Commit Conventions**

Feature branch workflow with strict quality requirements.

**Topics:**
- Main branch requirements (always stable)
- Feature branch naming (`feature/*`, `fix/*`, `refactor/*`, `docs/*`)
- Feature development flow (create → TDD cycle → quality gates → merge)
- Commit message conventions (Conventional Commits)
- Commit best practices (atomic, descriptive)
- Branch cleanup after merge
- Integration with GitHub (PRs, tags)
- Historical anti-patterns

**When to read:**
- Starting new feature branch
- Writing commit messages
- Preparing to merge to main
- Setting up GitHub integration

### 4. [CODE_STYLE.md](CODE_STYLE.md)

**Code Style Guide - Formatting & Conventions**

Comprehensive style guide for Python code in S1mpleTrader V3.

**Topics:**
- File headers (mandatory architectural documentation)
- Import organization (3 groups with comments)
- Docstring conventions (module verbose, class/method concise)
- Line length rules (max 100 chars, techniques to fix)
- Whitespace rules (no trailing, auto-fix commands)
- Type hinting (mandatory, modern Python 3.10+ syntax)
- Pydantic DTO conventions (field order, json_schema_extra)
- Contract-driven development (DTOs vs primitives)
- Logging & traceability (typed IDs, IJournalWriter)
- VS Code configuration
- Anti-patterns to avoid

**When to read:**
- Creating new modules/files
- Uncertain about style conventions
- Writing Pydantic DTOs
- Setting up VS Code environment

## Common Workflows

### Starting a New DTO

1. **Read:** [TDD_WORKFLOW.md](TDD_WORKFLOW.md) - Understand the cycle
2. **Create feature branch:**
   ```powershell
   git checkout -b feature/my-dto
   ```
3. **RED phase:** Write failing tests, commit
4. **GREEN phase:** Minimal implementation, commit
5. **REFACTOR phase:** Quality improvements, commit
6. **Check:** [QUALITY_GATES.md](QUALITY_GATES.md) - Run all 5 gates
7. **Merge:** [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - Merge to main

### Fixing Quality Gate Failures

1. **Identify failure:** Check VS Code Problems panel or gate output
2. **Consult:** [QUALITY_GATES.md](QUALITY_GATES.md) - Find gate details
3. **Fix common issues:**
   - Trailing whitespace → Auto-fix command
   - Line length → [CODE_STYLE.md](CODE_STYLE.md) techniques
   - Imports → Move to top-level
   - Type hints → Add return types
4. **Re-run gates:** Verify 10/10 before merge

### Writing Good Commit Messages

1. **Read:** [GIT_WORKFLOW.md](GIT_WORKFLOW.md) - Commit conventions
2. **Use prefixes:** `test:`, `feat:`, `refactor:`, `docs:`, `fix:`, `chore:`
3. **Structure:** Short summary + optional body + optional footer
4. **Include status:** `Status: RED|GREEN`, `Quality gates: 10/10`

### Setting Up New Workspace

1. **VS Code settings:** [CODE_STYLE.md](CODE_STYLE.md) - Recommended config
2. **pyrightconfig.json:** [QUALITY_GATES.md](QUALITY_GATES.md) - Type checking
3. **Auto-fix setup:** [QUALITY_GATES.md](QUALITY_GATES.md) - Whitespace commands
4. **Git hooks (optional):** Pre-commit quality checks

## Quality Metrics

All code must meet these standards before merge:

| Gate | Check | Target | Tool |
|------|-------|--------|------|
| 1 | Whitespace & Parens | 10/10 | `pylint --enable=trailing-whitespace,superfluous-parens` |
| 2 | Import Placement | 10/10 | `pylint --enable=import-outside-toplevel` |
| 3 | Line Length | 10/10 | `pylint --enable=line-too-long --max-line-length=100` |
| 4 | Type Checking | 0 errors | `mypy --strict` (DTOs only) |
| 5 | Tests Passing | 100% | `pytest` |

## Key Principles

1. **TDD First** - Write tests before implementation (RED → GREEN → REFACTOR)
2. **Quality Gates** - All 10/10 before merge to main
3. **Feature Branches** - Never commit directly to main during development
4. **Conventional Commits** - Clear, structured commit messages
5. **Type Safety** - Full type hints, Pydantic DTOs only
6. **Documentation** - Module headers, concise docstrings
7. **No Shortcuts** - Quality is non-negotiable

## Historical Context

**Recent violations (commits 1d4258a, d3418dd, 7b62902):**
- ❌ Direct commits to main (should use feature branches)
- ❌ Tests + implementation combined (should separate RED/GREEN)
- ❌ No RED phase commits (tests written after implementation)

**Correction:** From now on, STRICT adherence to all standards. No exceptions.

## Related Documentation

- **Architecture:** [../architecture/README.md](../architecture/README.md) - System design principles
- **Implementation:** [../implementation/IMPLEMENTATION_STATUS.md](../implementation/IMPLEMENTATION_STATUS.md) - Current progress
- **Reference:** [../reference/README.md](../reference/README.md) - Templates and examples

## Support

**Questions about standards?**
- Check relevant document first
- Look for examples in existing code (see [../reference/README.md](../reference/README.md))
- Update this documentation if clarification needed

**Found outdated information?**
- Create `docs/update-coding-standards` branch
- Fix documentation
- Submit with `docs:` commit prefix

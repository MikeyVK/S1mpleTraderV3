# Changelog

All notable changes to the S1mpleTrader V3 MCP Workflow will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-02-16

### Added
- **Workflow-first commit scopes** - Issue #138
  - New `workflow_phase` parameter for `git_add_or_commit` tool
  - Support for all workflow phases: research, planning, design, tdd, integration, documentation, coordination
  - Auto-detection of workflow_phase from state.json (no parameters needed!)
  - Scope encoding: `test(P_TDD_SP_RED):`, `docs(P_DOCUMENTATION):`, etc.
  - `sub_phase` parameter for subphase specification (red, green, refactor, c1, c2, etc.)
  - `cycle_number` parameter for multi-cycle TDD support
  - `commit_type` parameter override (auto-determined from workphases.yaml if omitted)

- **PhaseStateEngine** integration
  - Phase detection hierarchy: commit-scope > state.json > unknown
  - ScopeDecoder for commit message parsing
  - ScopeEncoder for scope generation with strict validation
  - phase_source field (commit-scope, state.json, unknown)

- **Config-driven validation**
  - workphases.yaml: Phase definitions with subphase whitelists
  - commit_type auto-determination per phase
  - Strict sub_phase validation against workphases.yaml

- **E2E testing**
  - Full workflow cycle validation (research → documentation)
  - Integration tests for scope detection and encoding
  - Backward compatibility test suite

### Changed
- **git_add_or_commit** signature updated
  - Old: `git_add_or_commit(phase, message, files)`
  - New: `git_add_or_commit(message, workflow_phase?, sub_phase?, cycle_number?, commit_type?, files?)`
  - Auto-detect when no workflow_phase provided (reads from state.json)

### Deprecated
- `phase` parameter in `git_add_or_commit` (use `workflow_phase` + `sub_phase` instead)
  - Still supported for backward compatibility
  - Will be removed in v3.0.0
- `commit_tdd_phase()` method in GitManager (use `commit_with_scope()` instead)
- `commit_docs()` method in GitManager (use `commit_with_scope()` instead)

### Fixed
- Issue #138: git_add_or_commit only accepted TDD phases (red/green/refactor/docs)
- Issue #139: get_project_plan missing current_phase field
- PhaseStateEngine runtime crash (workspace_root dependency)

### Migration Guide
**Old syntax (DEPRECATED):**
```python
git_add_or_commit(phase="red", message="add test")
# Generates: test: add test
```

**New syntax (RECOMMENDED):**
```python
# Option 1: Explicit workflow_phase
git_add_or_commit(workflow_phase="tdd", sub_phase="red", message="add test")
# Generates: test(P_TDD_SP_RED): add test

# Option 2: Auto-detect (BEST)
git_add_or_commit(message="add test")
# Generates: test(P_TDD_SP_RED): add test (if current_phase=tdd in state.json)
```

**Backward compatibility:**
- Old `phase` parameter still works (uses legacy commit_tdd_phase/commit_docs methods)
- No breaking changes for existing code
- Gradual migration recommended

## [1.0.0] - 2026-01-XX

### Added
- Initial MCP server implementation
- ST3 workflow tools (create_branch, git_status, transition_phase, etc.)
- GitHub integration (issues, labels, milestones, PRs)
- Template scaffolding system
- Quality gates integration
- Documentation templates

[Unreleased]: https://github.com/mivdnber/SimpleTraderV3/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/mivdnber/SimpleTraderV3/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/mivdnber/SimpleTraderV3/releases/tag/v1.0.0

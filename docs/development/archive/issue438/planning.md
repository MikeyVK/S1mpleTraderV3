<!-- c:\temp\pgmcp\docs\development\issue438\planning.md -->
<!-- template=planning version=130ac5ea created=2026-07-20T21:12Z updated= -->
# Dynamic State File Versioning Implementation Plan

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-07-20

---

## Purpose

Outline the TDD cycle breakdown, exit criteria, and validation plan for dynamic state file version validation.

## Scope

**In Scope:**
Sequencing cycles C_EXC_VALIDATOR.1, C_MODELS_PROJECT.2, C_REPO_TOOL.3, C_VALIDATION_GATES.4 and hard-removal of test ballast.

**Out of Scope:**
Writing database migration scripts.

## Prerequisites

Read these first:
1. Approved Design Document
2. Clean Break Strategy decision
---

## Summary

Implementation plan for Issue #438 to introduce dynamic load-time version validation, backup on version mismatch/corruption using the Clean Break strategy, remove silent reconstructs in PhaseStateEngine, and refactor bootstrapper validation for SRP.

---

## Dependencies

- C_EXC_VALIDATOR.1 must complete before C_MODELS_PROJECT.2
- C_MODELS_PROJECT.2 must complete before C_REPO_TOOL.3
- C_REPO_TOOL.3 must complete before C_VALIDATION_GATES.4

---

## TDD Cycles


### Cycle 1: C_EXC_VALIDATOR.1

**Goal:** Implement custom exceptions subclassing ConfigError and build the CQS-compliant StateVersionValidator service.

**Tests:**
- test_state_version_validator_missing_returns_none
- test_state_version_validator_corrupt_renames_to_bak_and_raises_state_corrupted_error
- test_state_version_validator_mismatch_renames_to_bak_and_raises_state_version_mismatch_error

**Success Criteria:**
- StateVersionValidator.validate_file and backup_file methods exist and are CQS-compliant.
- Custom exception classes (StateNotFoundError, StateCorruptedError, StateVersionMismatchError, PlanningVersionMismatchError) exist and inherit from ConfigError.
- Unit tests pass successfully.



### Cycle 2: C_MODELS_PROJECT.2

**Goal:** Add schema_version to BranchState and QualityState models, and integrate version envelope checking and persistence in ProjectManager.

**Tests:**
- test_branch_state_includes_schema_version
- test_quality_state_includes_schema_version
- test_project_manager_read_projects_validates_envelope
- test_project_manager_write_deliverables_saves_envelope
- test_project_manager_write_paths_delegate_to_write_deliverables

**Success Criteria:**
- BranchState and QualityState models have schema_version field with default value '1.0.0'.
- ProjectManager._read_projects validates the deliverables.json version envelope using validate_file.
- All ProjectManager write paths (initialize_project, save_planning_deliverables, update_planning_deliverables) delegate to _write_deliverables which saves the SemVer envelop.
- Outdated deliverables version-migration tests are hard-removed.
- Unit tests pass successfully.

**Dependencies:** C_EXC_VALIDATOR.1


### Cycle 3: C_REPO_TOOL.3

**Goal:** Integrate validator into repositories, remove silent state reconstruct fallback, enforce GetWorkContextTool error boundary, and extract Bootstrapper validation.

**Tests:**
- test_state_repository_load_orchestrates_cqs_backup_on_error
- test_quality_repository_resets_on_error_after_backup
- test_get_work_context_bubbles_corrupt_and_mismatch_but_catches_missing
- test_workspace_version_validator_asserts_and_bypasses

**Success Criteria:**
- FileStateRepository and FileQualityStateRepository load paths check version and backup on failure using the validator.
- PhaseStateEngine._load_state_or_reconstruct and StateReconstructor class are deleted.
- GetWorkContextTool catches only StateNotFoundError.
- WorkspaceVersionValidator exists and is called by ServerBootstrapper.bootstrap().
- All legacy tests for _load_state_or_reconstruct and StateReconstructor are hard-removed.
- Unit tests pass successfully.

**Dependencies:** C_MODELS_PROJECT.2


### Cycle 4: C_VALIDATION_GATES.4

**Goal:** Run integration tests across tools boundaries and execute final quality gates.

**Tests:**
- test_integration_tools_with_corrupt_files_bubble_to_decorator_and_return_config_error_output

**Success Criteria:**
- Integration tests verifying tool behavior on corrupt or mismatched state files pass successfully.
- run_quality_gates returns overall pass: True for all changed python files.

**Dependencies:** C_REPO_TOOL.3

---

## Risks & Mitigation

- **Risk:** Legacy test suites failing due to removal of PhaseStateEngine silent reconstruct fallback.
  - **Mitigation:** Identify and hard-remove all such tests as part of the cycle C_REPO_TOOL.3 deliverables.

## Related Documentation
- **[docs/development/issue438/research.md][related-1]**
- **[docs/development/issue438/design.md][related-2]**

<!-- Link definitions -->

[related-1]: docs/development/issue438/research.md
[related-2]: docs/development/issue438/design.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-20 | Agent | Initial draft |
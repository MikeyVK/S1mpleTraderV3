<!-- c:\temp\pgmcp\docs\development\issue438\design.md -->
<!-- template=design version=5827e841 created=2026-07-20T20:38Z updated=2026-07-20T23:05Z -->
# Dynamic State File Versioning Design

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-07-20

---

## Purpose

Define the architectural and interface design for dynamic state file version validation and SRP bootstrapper refactoring.

## Scope

**In Scope:**
- Exception hierarchy subclassing `ConfigError` for state errors.
- Design of the `StateVersionValidator` utility service respecting Command-Query Separation (CQS).
- Deliverables validation and envelope save paths in `ProjectManager`.
- Integration points in `FileStateRepository` and `FileQualityStateRepository`.
- Refactoring `GetWorkContextTool` error handling to let corruption and mismatch exceptions bubble.
- Removal of the git-log silent reconstruction fallback in `PhaseStateEngine`.
- Schema additions (`schema_version: str = "1.0.0"`) to all state DTO models.
- Design of the `WorkspaceVersionValidator` service and `ServerBootstrapper` cleanup.

**Out of Scope:**
- Python-level database-like JSON schema migration scripts.

## Prerequisites

1. Approved Strategy from the Research phase
2. Familiarity with the Russian Doll Decorator Pipeline

---

## 1. Context & Requirements

### 1.1. Problem Statement

Dynamic state files (`state.json`, `deliverables.json`, `quality_state.json`) lack version validation and consistent error mapping. Mismatches and file corruptions cause unhandled Python exception crashes and raw tracebacks, and silent overwrites in `PhaseStateEngine` violate the Single Source of Truth.

### 1.2. Requirements

**Functional:**
- **DFV.1 (Lazy Validation):** Verify state schema versions dynamically during load-time.
- **DFV.2 (Backup & Reset):** Rename mismatched or corrupt files to a `.bak` suffix (without timestamps) and raise standard `ConfigError` subclasses.
- **DFV.3 (Enforce SSOT):** Eliminate the silent git-log reconstruction fallback in `PhaseStateEngine` on state read/load failure.
- **DFV.4 (Version Headers):** Add `schema_version` to `state.json`, `deliverables.json` (root-level), and `quality_state.json` DTOs in SemVer format (`x.y.z`).
- **DFV.5 (SRP Bootstrapper):** Decouple `.version` file verification out of `ServerBootstrapper` to a separate class.

**Non-Functional:**
- **NFR.1 (DRY Error Handling):** Map all state exceptions to `ConfigError` to leverage the existing `ToolErrorHandlerDecorator`.
- **NFR.2 (Graceful context degradation):** Do not allow `get_work_context` to crash when state files are missing; return success with warnings in instructions.

### 1.3. Constraints

- SemVer format (`x.y.z`) for all schema versions (e.g. `"1.0.0"`).
- Backup renaming must strictly use `{filename}.bak` suffix without timestamps.
- All dependencies must be constructor-injected; no direct instantiation inside execution paths.

---

## 2. Design Options

### 2.1. Option 1: Central StateVersionValidator service called lazy at runtime (Preferred)

A dedicated manager service `StateVersionValidator` performs load-time file validation, schema-version checking, and backup rename logic.

**Pros:**
- Keeps logic DRY, co-located in managers, reusable, and respects load-time/branch-switch dynamics.
- Isolates disk manipulation (`.bak` renaming) in one place.

**Cons:**
- Requires modifying repositories to compose the validator service.

### 2.2. Option 2: Automatic Pydantic schema migration in Python code

Implement python-level migration logic to translate older schema formats to new schema formats on the fly.

**Pros:**
- Preserves existing state data across minor version changes.

**Cons:**
- Extremely complex to maintain, prone to version-migration bugs (migration hell), violates YAGNI.

---

## 3. Chosen Design

**Decision:** Implement a central `StateVersionValidator` service called lazy by repositories at load-time. Mismatches/corruptions rename files to `*.bak` and raise custom `ConfigError` subclasses caught and formatted cleanly by the Russian Doll Decorator pipeline.

### 3.1. Approved Strategy: Clean Break

For all affected dynamic state file boundaries (`state.json`, `deliverables.json`, `quality_state.json`), we explicitly select the **Clean Break** strategy. 
- We do not preserve backward compatibility or implement data migration logic for corrupt or mismatched schema versions.
- Older, corrupt, or mismatched files are backed up to a `.bak` extension and reset/re-initialized to keep the state tracking engine clean, robust, and free of versioning drift.

### 3.2. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **File-wide version envelope (Option A)** | Wraps the deliverables project dictionary in a root envelope: `{ "schema_version": "1.0.0", "projects": { ... } }`. Highly cohesive, avoids nested structural diving. |
| **Quality State Auto-Reset** | Rename to `quality_state.json.bak`, log warning, and auto-initialize a fresh empty `QualityState` DTO (transient cache data only). |
| **Remove Silent Reconstruct** | Remove `PhaseStateEngine._load_state_or_reconstruct` entirely to enforce `state.json` as the strict Single Source of Truth (SSOT). |
| **Workspace Version Delegation** | Extract `.version` checking out of `ServerBootstrapper` to `WorkspaceVersionValidator`. |

---

## 4. Technical Specification

### 4.1. State Exceptions (`mcp_server/core/exceptions.py`)

We introduce/refactor the following exceptions as subclasses of `ConfigError` to align with the Russian Doll pipeline:

```python
from mcp_server.core.exceptions import ConfigError

class StateNotFoundError(ConfigError):
    """Raised when a dynamic state file is missing."""
    def __init__(self, message: str, file_path: str) -> None: ...

class StateCorruptedError(ConfigError):
    """Raised when a dynamic state file contains malformed JSON."""
    def __init__(self, message: str, file_path: str) -> None: ...

class StateVersionMismatchError(ConfigError):
    """Raised when state.json schema version does not match expected version."""
    def __init__(self, message: str, file_path: str, actual_version: str, expected_version: str) -> None: ...

class PlanningVersionMismatchError(ConfigError):
    """Raised when deliverables.json schema version does not match expected version."""
    def __init__(self, message: str, file_path: str, actual_version: str, expected_version: str) -> None: ...
```

---

### 4.2. State Version Validator with CQS Compliance (`mcp_server/managers/state_version_validator.py`)

To satisfy Command-Query Separation (CQS), validation checks (Queries) are split from file operations (Commands).

```python
from pathlib import Path

class StateVersionValidator:
    """Service responsible for validating dynamic state file schema versions and corruptions."""
    
    def validate_file(
        self,
        file_path: Path,
        expected_version: str,
        is_planning: bool = False
    ) -> None:
        """Read and validate the version and syntax of a state file (Query).
        
        Does not mutate the filesystem.
        
        Raises:
            StateNotFoundError: If the file does not exist.
            StateCorruptedError: If JSON decoding or base schema validation fails.
            StateVersionMismatchError: If the version field does not match expected_version.
            PlanningVersionMismatchError: If deliverables.json version does not match expected_version.
        """
        ...

    def backup_file(self, file_path: Path) -> None:
        """Rename the invalid file at file_path to file_path.bak (Command).
        
        If a backup file already exists, it is overwritten.
        """
        ...
```

#### Orchestration Flow in Repositories/Managers (CQS Integration)
Repositories compose `StateVersionValidator` and orchestrate the Query and Command operations in their load paths:

```python
# Conceptual repository loading logic
try:
    # 1. Query: Validate the file (throws on mismatch/corrupt)
    self._validator.validate_file(self._backing_file, EXPECTED_VERSION)
    # 2. Query: Read and parse file if valid
    return self._read_validated_file()
except (StateCorruptedError, StateVersionMismatchError) as e:
    # 3. Command: Execute backup/rename operation on error
    self._validator.backup_file(self._backing_file)
    raise e
```

---

### 4.3. Deliverables.json Version Control and Save Envelope (`mcp_server/managers/project_manager.py`)

#### A. Load-Time Version Validation
When `ProjectManager` reads the deliverables, it invokes the validator lazy to enforce the SemVer version envelope:

```python
def _read_projects(self) -> dict[str, Any]:
    """Load and validate projects from deliverables.json (Query/Orchestration).
    
    Orchestration:
    1. Check file existence (return empty dict if missing).
    2. Query: Invoke StateVersionValidator.validate_file.
    3. Query: Load and parse file if valid.
    4. Command (on corruption/version mismatch): Invoke StateVersionValidator.backup_file and reraise.
    """
    ...
```

#### B. Envelope Saving in All Write Paths
To ensure the `"schema_version"` envelope is saved across all writes, the private persistence bottleneck `_write_deliverables` is used. The three public write paths in `ProjectManager` must delegate to this method:

1. `initialize_project(...)`
2. `save_planning_deliverables(...)`
3. `update_planning_deliverables(...)`

```python
def _write_deliverables(self, projects: dict[str, Any]) -> None:
    """Persist deliverables.json via atomic replacement inside version envelope (Command)."""
    ...
```

---

### 4.4. GetWorkContext Tool Error Handling (`mcp_server/tools/discovery_tools.py`)

To ensure uninitialized branches fail gracefully while version mismatches and corruptions block agent actions, `GetWorkContextTool.execute` restricts exception trapping:

```python
# Inside GetWorkContextTool.execute:
try:
    state = self._state_engine.get_state(branch)
    # ... read status
    phase_source = "state.json"
    phase_confidence = "high"
except StateNotFoundError:
    # Catch only StateNotFoundError (uninitialized branch).
    # Gracefully degrade to phase_source="unknown".
    pass
# StateCorruptedError and StateVersionMismatchError are NOT caught here
# and bubble up to ToolErrorHandlerDecorator, blocking execution with a clear diagnostics message.
```

---

### 4.5. QualityState Storage in Apply Method (`mcp_server/managers/quality_state_repository.py`)

`FileQualityStateRepository.apply` serializes the mutated `QualityState` DTO. It must write the `schema_version` to the payload:

```python
def apply(self, mutate: Callable[[QualityState], QualityState]) -> None:
    """Load, mutate, and persist the QualityState DTO, writing schema_version to the payload."""
    ...
```

---

### 4.6. DTO Models Schema Updates

#### `BranchState` (`mcp_server/managers/state_repository.py`)
```python
class BranchState(BaseModel):
    schema_version: str = "1.0.0"
    branch: str
    workflow_name: str
    current_phase: str
    # ... other fields
```

#### `QualityState` (`mcp_server/state/quality_state.py`)
```python
class QualityState(BaseModel):
    schema_version: str = "1.0.0"
    baseline_sha: str | None = None
    failed_files: list[str] = Field(default_factory=list)
```

#### `WorkspaceVersionValidator` (`mcp_server/core/workspace_validator.py`)
```python
from mcp_server.config.settings import ServerSettings

class WorkspaceVersionValidator:
    """Validator for workspace .version compatibility checking at server boot."""
    
    def validate(self, settings: ServerSettings) -> None:
        """Validate workspace .version file against server package version.
        
        Bypasses if bypass_version_check is configured.
        Raises ConfigError on mismatch or missing file.
        """
        ...
```

---

## 5. Design Validation & Test Plan

### 5.1. Unit and Integration Test Plan
1. **Validator Tests (`test_state_version_validator.py`):**
   - Verify missing file triggers `StateNotFoundError`.
   - Verify `backup_file` moves the file and renames it to `{filename}.bak`.
2. **Repository Integration Tests:**
   - Verify `FileStateRepository.load()` handles CQS backup orchestration.
   - Verify `ProjectManager` handles deliverables envelope load-time mismatches.
   - Verify `FileQualityStateRepository` auto-resets on mismatch/corruption after backing up.
3. **GetWorkContext Error Handling Verification:**
   - Verify `GetWorkContextTool` passes on `StateNotFoundError`.
   - Verify `GetWorkContextTool` bubbles `StateCorruptedError` and `StateVersionMismatchError`.
4. **Removal of Test Ballast (Outdated Reconstruct Tests):**
   - All existing unit, integration, or regression tests verifying git-based state reconstruction (`PhaseStateEngine._load_state_or_reconstruct` or the `StateReconstructor` class itself) must be **hard-removed** from the codebase.
   - Commenting out or skipping tests via `@pytest.mark.skip` is forbidden. We do not allow dead test code or test ballast.
---

## 6. Open Questions & Risks

### 6.1. Resolved Questions
- **Version Format:** Use standard SemVer string format (e.g. `"1.0.0"`) for all schema version fields to ensure consistency.
- **Backup Naming:** Use simple `{filename}.bak` suffix without timestamps. Mismatches will overwrite the backup, avoiding disk clutter.
- **Silent Reconstruct Removal Risk:** We must ensure all transition test suites mock the repository states properly instead of relying on git-based auto-reconstructs.

---

## Related Documentation
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md][related-1]**
- **[docs/coding_standards/DOCUMENTATION_STANDARD.md][related-2]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md
[related-2]: docs/coding_standards/DOCUMENTATION_STANDARD.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-20 | Agent | Initial design artifact for dynamic state version validation and bootstrapper refactoring. |
| 1.1 | 2026-07-20 | Agent | Refine design for CQS compliance, ProjectManager write paths, GetWorkContext error boundaries, and QualityState persistence. |

<!-- docs/development/issue428/design.md -->
<!-- template=design version=5827e841 created=2026-07-22T15:42Z updated=2026-07-22 -->
# Design Document - Implement `--upgrade` CLI command and release v2.0.0

**Status:** DEFINITIVE  
**Version:** 1.1.0  
**Last Updated:** 2026-07-22  

---

## 1. Context & Requirements

### 1.1. Problem Statement
Currently, there is no standardized way to upgrade an existing user workspace `.pgmcp/` directory when a newer version of the wheel package is installed. Upgrades to schemas, default templates, rules, and configurations require manual intervention, leading to startup crashes, version mismatches, or outdated workspace assets.

### 1.2. Requirements

**Functional:**
- [x] Add `--upgrade` CLI argument to `argparse` in `mcp_server/cli.py`.
- [x] Implement fail-safe timestamped backup (`.pgmcp_backup_YYYYMMDD_HHMMSS/`) before asset renewal.
- [x] Implement Smart Version-Aware Preservation of templates/docs/schemas using existing `ConfigLoader` validation.
- [x] Strictly preserve dynamic runtime state files (`state.json`, `deliverables.json`, `template_registry.json`, `logs/`).
- [x] Write a single structured upgrade log artifact to `.pgmcp/logs/upgrade_YYYYMMDD_HHMMSS.json`.
- [x] Decouple workspace version validation from `ServerBootstrapper` into `WorkspaceVersionValidator`.
- [x] Synchronize package release version SSOT (`pyproject.toml`, `release_manifest.yaml`, `settings.py`) to `2.0.0`.
- [x] Provide repository release changelog `CHANGELOG.md` for the v2.0.0 release.

**Non-Functional:**
- [x] 100% compliance with `ARCHITECTURE_PRINCIPLES.md` (SRP, CQS, DIP across production AND test code).
- [x] Zero risk of user configuration data loss during upgrade.
- [x] Fast execution, 100% type-strict test code, and zero test ballast policy.

---

## 2. Design Options

### 2.1. Option A: Inline Upgrader in `cli.py` / `bootstrap.py`
Monolithic approach implementing backup, asset copying, version checks, and log writing directly inside `cli.py` or `ServerBootstrapper`.

**Pros:**
- Fewer new files to create.

**Cons:**
- Violates Single Responsibility Principle (SRP §1.1).
- Hard to unit test without executing full CLI or server startup.
- Mixes command (upgrade mutations) with query (version checks) violating CQS.

### 2.2. Option B: Modular Architecture (Selected)
Modular approach creating a dedicated `WorkspaceUpgrader` service (`mcp_server/services/workspace_upgrader.py`), a decoupled `WorkspaceVersionValidator` manager (`mcp_server/managers/workspace_version_validator.py`), a frozen `UpgradeLogDTO` (`mcp_server/dtos/upgrade_log.py`), synchronized v2.0.0 version configuration, and `CHANGELOG.md`.

**Pros:**
- Strict alignment with `ARCHITECTURE_PRINCIPLES.md` (SRP, CQS, DIP).
- Decouples version validation from `ServerBootstrapper`.
- Highly testable via isolated unit tests with mock settings/paths.
- Clear separation between process orchestration, release configuration, and DTO logging.

**Cons:**
- Requires creating three new dedicated files.

---

## 3. Chosen Design & Component Architecture

**Decision:** Option B (Modular Architecture).

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Modular Service + Manager** | Decouples version check from bootstrapper and isolates upgrade orchestration. |
| **Smart Asset Preservation via `ConfigLoader`** | Leverages existing schema validation logic to preserve valid user custom YAML configs without building fragile custom diff engines. |
| **Single Audit Log Artifact** | Writes `.pgmcp/logs/upgrade_YYYYMMDD_HHMMSS.json` as a standalone audit file. |
| **Clean CLI Interface** | Keeps CLI clean (`pgmcp --upgrade`); workspace recovery relies on deleting `.pgmcp/` and running `pgmcp --init`. |
| **v2.0.0 Release Synchronization** | Bumps SSOT files (`pyproject.toml`, `release_manifest.yaml`, `settings.py`) to `"2.0.0"` and adds repository `CHANGELOG.md`. |

---

## 4. Component Specification & Interfaces

### 4.1. `WorkspaceUpgrader` Service
**File:** `mcp_server/services/workspace_upgrader.py`

Orchestrates fail-safe workspace upgrades:
- Generates timestamped backup (`.pgmcp_backup_YYYYMMDD_HHMMSS/`).
- Copies new release assets from package `mcp_server/assets/` while preserving valid user custom YAML configs and dynamic runtime state.
- Updates workspace `.pgmcp/.version`.
- Writes `.pgmcp/logs/upgrade_YYYYMMDD_HHMMSS.json`.

```python
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from mcp_server.dtos.upgrade_log import UpgradeLogDTO

if TYPE_CHECKING:
    from mcp_server.config.settings import Settings


class WorkspaceUpgrader:
    """Orchestrates workspace upgrades with backup creation and state preservation."""

    def __init__(
        self,
        settings: Settings,
        assets_dir: Path | None = None,
    ) -> None:
        """Initialize upgrader with injected settings and optional assets path."""
        ...

    def execute_upgrade(self) -> UpgradeLogDTO:
        """Execute complete workspace upgrade flow and return UpgradeLogDTO."""
        ...

    def get_current_workspace_version(self) -> str:
        """Query current version string from .pgmcp/.version file."""
        ...

    def create_backup(self, timestamp_str: str) -> Path:
        """Create timestamped backup directory of .pgmcp."""
        ...

    def renew_workspace_assets(self) -> tuple[list[str], list[str]]:
        """Perform Smart Version-Aware Preservation of assets."""
        ...

    def update_version_file(self, target_version: str) -> None:
        """Write target version string to .pgmcp/.version."""
        ...

    def write_upgrade_log(self, log_dto: UpgradeLogDTO, timestamp_str: str) -> Path:
        """Write structured UpgradeLogDTO to .pgmcp/logs/upgrade_YYYYMMDD_HHMMSS.json."""
        ...
```

### 4.2. `WorkspaceVersionValidator` Manager
**File:** `mcp_server/managers/workspace_version_validator.py`

Decouples version validation out of `ServerBootstrapper`:
- Validates workspace `.version` existence and version string against expected server version.
- Raises descriptive `ConfigError` directing user to run `pgmcp --upgrade`.

```python
from __future__ import annotations

from pathlib import Path


class WorkspaceVersionValidator:
    """Validates workspace version against expected server version."""

    def validate(
        self,
        server_root: Path,
        expected_version: str,
        bypass_version_check: bool = False,
    ) -> None:
        """Validate workspace version.

        Raises:
            ConfigError: If version file is missing or version mismatches.
        """
        ...

    def read_version(self, server_root: Path) -> str | None:
        """Read version string from workspace if file exists, else return None."""
        ...
```

### 4.3. `UpgradeLogDTO` Value Object
**File:** `mcp_server/dtos/upgrade_log.py`

```python
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict


class UpgradeLogDTO(BaseModel):
    """Immutable data transfer object representing a workspace upgrade run log."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    timestamp: str
    from_version: str
    to_version: str
    backup_path: str
    renewed_files: list[str]
    preserved_files: list[str]
    status: Literal["success", "failed"]
    details: str | None = None
```

### 4.4. CLI Argument Parsing & Bootstrapper Delegation
**Files:** `mcp_server/cli.py` & `mcp_server/bootstrap.py`

- `cli.py`: Defines `--upgrade` flag. If specified, checks `.pgmcp/` existence and invokes `WorkspaceUpgrader(_settings).execute_upgrade()`.
- `bootstrap.py`: `ServerBootstrapper._validate_version()` delegates to `WorkspaceVersionValidator().validate(...)`.

### 4.5. v2.0.0 Release Synchronization & `CHANGELOG.md` Deliverable
**Files:** `pyproject.toml`, `.pgmcp/config/release_manifest.yaml`, `mcp_server/config/settings.py`, `CHANGELOG.md`

- **Version Bump SSOT**: Update version string to `"2.0.0"` in:
  - `pyproject.toml` (`version = "2.0.0"`)
  - `.pgmcp/config/release_manifest.yaml` (`version: "2.0.0"`)
  - `mcp_server/config/settings.py` (`version = "2.0.0"`)
- **Package Release Changelog (`CHANGELOG.md`)**: Provide repository root `CHANGELOG.md` documenting functional delta from `v1.0.0` to `v2.0.0` (CLI `--upgrade`, frictionless `safe_edit_file`, dynamic state versioning, bug fixes).

---

## 5. Test Plan, Code Quality Standards & "No Test Ballast" Policy

### 5.1. Test Code Architecture Principles
Test code is subject to the exact same architectural standards as production code (`ARCHITECTURE_PRINCIPLES.md`):
1. **Strict Dependency Inversion & Protocols**: Mock dependencies injected in test fixtures must strictly implement protocol interfaces (`IAtomicFileWriter`, etc.).
2. **No Uncleaned Global State Mutation**: Tests mutating environment variables or settings must clean up after execution (using `monkeypatch` fixtures or `try...finally`).
3. **100% Pyright/Mypy Strict Typing**: Test files must pass full static type checking without untyped stubs or ignored errors.

### 5.2. "No Test Ballast" Policy
1. **Zero Exploratory Ballast**: Any temporary, exploratory, or duplicate test cases written during TDD cycles must be hard-removed before phase completion.
2. **High-Value Permanent Tests Only**: Only durable, maintainable unit and integration tests that verify specific contracts or edge cases remain in `tests/`.

### 5.3. Planned Test Cases

1. **Unit Tests (`tests/mcp_server/unit/services/test_workspace_upgrader.py`)**:
   - `test_execute_upgrade_creates_timestamped_backup`: Verifies `.pgmcp_backup_YYYYMMDD_HHMMSS/` is created before asset renewal.
   - `test_execute_upgrade_preserves_dynamic_state`: Verifies `state.json`, `deliverables.json`, `template_registry.json`, and `logs/` are strictly preserved.
   - `test_execute_upgrade_preserves_valid_custom_configs`: Verifies valid user YAML configs remain intact via `ConfigLoader`.
   - `test_execute_upgrade_writes_upgrade_log`: Verifies JSON log file is created in `.pgmcp/logs/`.

2. **Unit Tests (`tests/mcp_server/unit/managers/test_workspace_version_validator.py`)**:
   - `test_validate_missing_version_file_raises_config_error`: Verifies `ConfigError` with `--init` advice.
   - `test_validate_version_mismatch_raises_config_error`: Verifies `ConfigError` with `pgmcp --upgrade` advice.
   - `test_validate_matching_version_succeeds`: Verifies clean pass when versions match.

3. **CLI & Version Consistency Unit Tests (`tests/mcp_server/unit/test_cli.py`)**:
   - `test_cli_upgrade_missing_server_root_exits_1`: Verifies error message when `.pgmcp/` missing.
   - `test_cli_upgrade_success_exits_0`: Verifies `--upgrade` flow and stdout message.
   - `test_version_consistency`: Verifies that `pyproject.toml`, `release_manifest.yaml`, `settings.py`, and `mcp_server/assets/.version` report exact matching version strings (`"2.0.0"`).

---

## Related Documentation

- [research.md](research.md)
- [docs/coding_standards/ARCHITECTURE_PRINCIPLES.md](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-07-22 | Agent | Initial design for Issue #428 |
| 1.1.0 | 2026-07-22 | Agent | Updated with Section 4.5 (v2.0.0 version bump & CHANGELOG.md) and Section 5 (test architecture principles, No Test Ballast policy, test_version_consistency) |

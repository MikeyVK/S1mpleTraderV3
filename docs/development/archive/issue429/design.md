<!-- docs\development\issue429\design.md -->
<!-- template=design version=5827e841 created=2026-07-17T16:13Z updated= -->
# Centralized SemVer Validation & Template Bundling

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-07-17

---

## Purpose

Define the interface contracts and rules for semantic version validation.

## Scope

**In Scope:**
Centralized versioning utility, template-to-yaml validation.

**Out of Scope:**
Migration of legacy configuration contents.

---

## 1. Context & Requirements

### 1.1. Problem Statement

Currently, version pairing logic and validation across templates, configs, and wheels is decentralized, leading to risk of mismatch and DRY/SRP violations. We also need to safely handle version discrepancies between templates and YAML configurations according to strict semantic versioning.

### 1.2. Requirements

**Functional:**
- [ ] Provide a centralized `validate_compatibility` function for semantic version checking.
- [ ] Throw an exception and crash on MAJOR version mismatch.
- [ ] Log a warning on MINOR version mismatch (newer template/asset).
- [ ] Silently accept PATCH version mismatch.

**Non-Functional:**
- [ ] Utility must have 100% test coverage.
- [ ] Must enforce strict SemVer regex `^\d+\.\d+\.\d+$`.

### 1.3. Constraints

None
---

## 2. Design Options

| Option | Pros | Cons |
|--------|------|------|
| **A. Decentralized validation** | None | Violates DRY/SRP, error-prone, duplicates logic |
| **B. Centralized SemVerValidator** | Follows DRY/SRP, testable, uniform policy | Requires updating call sites |
---

## 3. Chosen Design

**Decision:** Implement `SemVerValidator` as a central utility within `mcp_server.utils.versioning`.

**Rationale:** By centralizing the version parsing and validation, we adhere strictly to DRY and ensure that all layers of the application (wheel, yaml, jinja2) conform to the exact same versioning policy.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| MAJOR=Crash, MINOR=Warn/Accept, PATCH=Accept |  |
| Strict `X.Y.Z` string matching (regex `^\d+\.\d+\.\d+$`) | To ensure complete compatibility and fail-fast behavior |

### 3.2. Concrete Interface Contracts

**Dataclass:** `SemVer`
```python
from dataclasses import dataclass
from mcp_server.exceptions import ConfigError

@dataclass(frozen=True)
class SemVer:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, version_string: str) -> "SemVer":
        ... # Parses strictly ^\d+\.\d+\.\d+$ or raises ConfigError
```

**Utility Function:** `validate_compatibility`
```python
def validate_compatibility(expected_version: str, actual_version: str, context: str) -> None:
    """
    Validates if actual_version matches expected_version based on SemVer rules.
    - MAJOR mismatch: raises ConfigError
    - MINOR mismatch (actual > expected): logs Warning
    - MINOR mismatch (actual < expected): silently accepted
    - PATCH mismatch: silently accepted
    """
```
## Related Documentation
None
---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-17 | Agent | Initial draft |
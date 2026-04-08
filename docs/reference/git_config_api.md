# GitConfig API Reference

**Module**: `mcp_server.config.schemas.git_config`
**Date**: 2026-04-08
**Related**: Issue #55, Issue #273

## Overview

`GitConfig` is a Pydantic `BaseModel` value object that holds the typed git conventions
loaded from `.st3/config/git.yaml`. It is instantiated via `ConfigLoader.load_git_config()`
on server startup and injected into all tools and managers that need git convention access.

There is no singleton or class-level caching. Each `ConfigLoader.load_git_config()` call
returns a fresh instance validated against the current file contents.

## Loading Pattern

```python
from pathlib import Path
from mcp_server.config.loader import ConfigLoader

# Standard usage (server startup)
loader = ConfigLoader(config_root=Path(".st3/config"))
git_config = loader.load_git_config()

# Load from explicit path (tests)
git_config = ConfigLoader(custom_path.parent).load_git_config(config_path=custom_path)
```

**Raises**:
- `ConfigError`: File not found, or YAML is invalid / missing required fields

## Class: GitConfig

**Base Class**: `pydantic.BaseModel`

**File Location**: `mcp_server/config/schemas/git_config.py`

### Fields

All fields are required — there are no optional fields or Python-level defaults.

#### `branch_types: list[str]`
Allowed branch type prefixes for `create_branch` validation.

**Constraints**: non-empty list

**Example value**: `["feature", "bug", "fix", "refactor", "docs", "hotfix", "epic"]`

---

#### `protected_branches: list[str]`
Branch names that `git_delete_branch` will refuse to delete.

**Constraints**: non-empty list

**Example value**: `["main", "master", "develop"]`

---

#### `branch_name_pattern: str`
Regex applied to the name-suffix portion of a branch (`type/number-{name}` → `{name}`).

**Constraints**: non-blank string, must compile as valid regex

**Validation**: `validate_branch_name_pattern()` model validator compiles and caches the
pattern at load time; raises `ValueError` on blank or invalid regex.

**Example value**: `"^[a-z0-9-]+$"`

---

#### `commit_types: list[str]`
Allowed [Conventional Commit](https://www.conventionalcommits.org/) type identifiers.

Used by:
- `GitCommitInput.validate_commit_type()` — rejects unknown overrides
- `PolicyEngine.decide()` (when `require_tdd_prefix: true`) — validates message prefix

**Constraints**: non-empty list

**Example value**: `["feat", "fix", "docs", "style", "refactor", "test", "chore", "perf", "ci", "build", "revert"]`

---

#### `default_base_branch: str`
Default base branch for `create_branch` when no explicit base is provided.

**Example value**: `"main"`

---

#### `issue_title_max_length: int`
Maximum character length for issue titles created via `create_issue`.

**Constraints**: `>= 1`

**Example value**: `72`

---

### Model Validator

#### `validate_branch_name_pattern() -> GitConfig`
Runs after model construction (`mode="after"`). Validates `branch_name_pattern` is
non-blank and compiles it as a regex. Stores the compiled result in `_compiled_pattern`
(class variable) for reuse by `validate_branch_name()`.

**Raises**: `ValueError` with actionable message when pattern is blank or invalid.

---

## Instance Methods

### `has_branch_type(branch_type: str) -> bool`
Returns `True` if `branch_type` is in `branch_types` (case-sensitive).

```python
gc.has_branch_type("feature")  # True
gc.has_branch_type("FEATURE")  # False
```

---

### `validate_branch_name(name: str) -> bool`
Returns `True` if `name` matches `branch_name_pattern`.

```python
gc.validate_branch_name("my-feature-123")  # True
gc.validate_branch_name("My_Feature")       # False (uppercase + underscore)
```

---

### `has_commit_type(commit_type: str) -> bool`
Returns `True` if `commit_type` is in `commit_types` (case-insensitive).

```python
gc.has_commit_type("feat")  # True
gc.has_commit_type("FEAT")  # True
gc.has_commit_type("yolo")  # False
```

---

### `is_protected(branch_name: str) -> bool`
Returns `True` if `branch_name` is in `protected_branches` (case-sensitive exact match).

```python
gc.is_protected("main")        # True
gc.is_protected("Main")        # False
gc.is_protected("feature/123") # False
```

---

### `get_all_prefixes() -> list[str]`
Returns each commit type formatted as a conventional commit prefix (`"type:"`).

Used by `PolicyEngine.decide()` for the `require_tdd_prefix` check.

```python
gc.get_all_prefixes()
# ["feat:", "fix:", "docs:", "style:", "refactor:", "test:", "chore:", "perf:", "ci:", "build:", "revert:"]
```

---

### `build_branch_type_regex() -> str`
Returns a non-capturing regex alternation group of all branch types.

Used internally by `extract_issue_number()`.

```python
gc.build_branch_type_regex()
# "(?:feature|bug|fix|refactor|docs|hotfix|epic)"
```

---

### `extract_issue_number(branch: str) -> int | None`
Parses the issue number from a branch name formatted as `type/number-name`.
Returns `None` when no issue number is present.

```python
gc.extract_issue_number("feature/42-my-feature")  # 42
gc.extract_issue_number("fix/7-hotpatch")          # 7
gc.extract_issue_number("main")                    # None
gc.extract_issue_number("feature/no-number")       # None
```

---

## Integration Points

### GitManager
Receives `git_config` at construction. Uses it for:
- `has_branch_type()` — branch type validation in `create_branch`
- `build_branch_type_regex()` / `extract_issue_number()` — internal branch parsing
- `is_protected()` — protected branch enforcement

### PolicyEngine
Loads its own `GitConfig` via `ConfigLoader.load_git_config()` (independent load).
Uses `get_all_prefixes()` for the `require_tdd_prefix` commit-message check.

### GitCommitInput / CreateBranchInput (tools)
Receive `GitConfig` via `configure(git_config)` class method at tool construction.
Use `has_commit_type()` and `has_branch_type()` for Pydantic field validators.

---

## Testing

### Loading in tests
```python
from pathlib import Path
from mcp_server.config.loader import ConfigLoader

def _load_git_config(config_path=None):
    if config_path is None:
        return ConfigLoader(Path(".st3/config")).load_git_config()
    return ConfigLoader(config_path.parent).load_git_config(config_path=config_path)
```

### Custom config in tests
```python
import yaml, tempfile
from pathlib import Path
from mcp_server.config.loader import ConfigLoader

payload = {
    "branch_types": ["feature", "fix"],
    "protected_branches": ["main"],
    "branch_name_pattern": "^[a-z0-9-]+$",
    "commit_types": ["feat", "fix", "test"],
    "default_base_branch": "main",
    "issue_title_max_length": 72,
}
with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
    yaml.dump(payload, f)
    tmp_path = Path(f.name)

gc = ConfigLoader(tmp_path.parent).load_git_config(config_path=tmp_path)
assert gc.branch_types == ["feature", "fix"]
```

## See Also

- [GitConfig Customization Guide](./git_config_customization.md) — user guide for editing git.yaml

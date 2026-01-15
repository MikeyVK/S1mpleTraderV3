# GitConfig API Reference

**Module**: `mcp_server.config.git_config`  
**Date**: 2026-01-15  
**Related**: Issue #55

## Overview

`GitConfig` is a Pydantic BaseModel singleton that loads and validates git workflow conventions from `.st3/git.yaml`. It provides 11 externalized conventions with type-safe access and validation.

## Class: GitConfig

**Base Class**: `pydantic.BaseModel`

**Pattern**: Singleton (via `_instance` class variable)

**File Location**: `mcp_server/config/git_config.py`

### Class Variables

```python
_instance: Optional["GitConfig"] = None  # Singleton instance
```

### Configuration Fields

#### 1. `branch_types: list[str]`
List of allowed branch type prefixes.

**Default**: `["feature", "fix", "refactor", "docs", "epic"]`

**Validation**: Non-empty, lowercase-only strings

**Example**:
```python
gc = GitConfig.from_file()
assert "feature" in gc.branch_types
```

#### 2. `tdd_phases: list[str]`
Sequential TDD workflow phases.

**Default**: `["red", "green", "refactor", "docs"]`

**Validation**: Must have matching keys in `commit_prefix_map`

#### 3. `commit_prefix_map: dict[str, str]`
Maps TDD phases to conventional commit prefixes.

**Default**: `{"red": "test", "green": "feat", "refactor": "refactor", "docs": "docs"}`

**Validation**: Keys must match all `tdd_phases`

#### 4. `protected_branches: list[str]`
Branches that cannot be deleted.

**Default**: `["main", "master", "develop"]`

#### 5. `branch_name_pattern: str`
Regex pattern for valid branch name suffixes.

**Default**: `"^[a-z0-9-]+$"`

**Usage**: Validates the `{name}` part of `{type}/{issue_number}-{name}`

#### 6. `default_base_branch: str`
Default branch for creating new branches.

**Default**: `"main"`

#### 7. `issue_number_pattern: str`
Regex pattern for extracting issue numbers from branch names.

**Default**: `"(?:^|/)(\\d+)-"`

**Usage**: Extracts `123` from `feature/123-my-branch`

#### 8. `epic_branch_format: str`
Format template for epic branches.

**Default**: `"epic/{issue_number}-{name}"`

#### 9. `epic_issue_pattern: str`
Regex pattern for extracting issue numbers from epic branches.

**Default**: `"(?:^|/)epic-(\\d+)"`

#### 10. `phase_transition_map: dict[str, str]`
Maps each phase to its allowed next phase.

**Default**: Sequential transitions based on `tdd_phases`

**Generated**: Automatically from `tdd_phases` list

#### 11. `protected_branch_patterns: list[str]`
Regex patterns for additional protected branches.

**Default**: `["^release/.*$"]`

**Usage**: Pattern-based protection (e.g., all `release/*` branches)

#### 12. `branch_format: str`
Template for creating branch names.

**Default**: `"{type}/{issue_number}-{name}"`

**Usage**: Used by `create_branch` tool

## Class Methods

### `from_file(cls, path: Optional[str] = None) -> GitConfig`
Load configuration from YAML file (singleton pattern).

**Parameters**:
- `path` (optional): Path to yaml file. Defaults to `.st3/git.yaml`

**Returns**: `GitConfig` instance (singleton)

**Example**:
```python
from mcp_server.config.git_config import GitConfig

gc = GitConfig.from_file()
print(gc.branch_types)  # ['feature', 'fix', 'refactor', 'docs', 'epic']

# Load from custom path
gc = GitConfig.from_file("custom/config.yaml")
```

**Behavior**:
- Creates singleton instance on first call
- Returns cached instance on subsequent calls
- Validates all fields via Pydantic

**Raises**:
- `FileNotFoundError`: If config file doesn't exist
- `ValidationError`: If config is invalid (wrong types, missing keys, regex errors)

### `reset_instance(cls) -> None`
Reset the singleton instance (force reload on next `from_file()`).

**Usage**: Testing and config hot-reload scenarios

**Example**:
```python
from mcp_server.config.git_config import GitConfig

# Load original config
gc1 = GitConfig.from_file()

# Modify .st3/git.yaml externally
# ...

# Force reload
GitConfig.reset_instance()
gc2 = GitConfig.from_file()  # Loads new config

assert gc1 is not gc2  # Different instances
```

**Important**: In production, config is loaded once at server startup. Use `reset_instance()` only in tests or when explicitly reloading config.

## Validators

### `@field_validator("branch_types")`
Validates branch types are non-empty lowercase strings.

**Rules**:
- Each type must be non-empty
- Each type must contain only lowercase letters

**Raises**: `ValueError` with descriptive message

### `@field_validator("commit_prefix_map")`
Validates commit prefix map keys match TDD phases.

**Rules**:
- All `tdd_phases` must have a mapping
- No extra keys allowed
- Values are conventional commit types (e.g., "feat", "test")

**Raises**: `ValueError` if keys mismatch

### `@model_validator(mode="after")`
Post-initialization validator for complex rules.

**Checks**:
- `phase_transition_map` generated from `tdd_phases`
- Regex patterns are valid
- No circular dependencies

## Usage Examples

### Basic Usage
```python
from mcp_server.config.git_config import GitConfig

gc = GitConfig.from_file()

# Check branch type allowed
if "hotfix" in gc.branch_types:
    print("Hotfix branches supported")

# Get commit prefix for phase
prefix = gc.commit_prefix_map.get("green")  # "feat"

# Check if branch protected
if "main" in gc.protected_branches:
    print("Main branch is protected")
```

### Integration with PolicyEngine
```python
from mcp_server.config.git_config import GitConfig
from mcp_server.managers.policy_engine import PolicyEngine

gc = GitConfig.from_file()
pe = PolicyEngine(gc)

# Validate branch name
is_valid = pe.is_valid_branch_name("feature/123-my-branch")

# Get commit prefix for phase
prefix = pe.get_commit_prefix_for_phase("red")  # "test"
```

### Testing Custom Configurations
```python
from mcp_server.config.git_config import GitConfig

# Load custom test config
GitConfig.reset_instance()
gc = GitConfig.from_file(".st3/test_git.yaml")

# Verify custom values
assert gc.branch_types == ["epic", "hotfix", "experiment"]
assert gc.tdd_phases == ["test", "impl", "refactor"]
assert gc.default_base_branch == "develop"

# Cleanup
GitConfig.reset_instance()
```

### Validation Error Handling
```python
from mcp_server.config.git_config import GitConfig
from pydantic import ValidationError

try:
    gc = GitConfig.from_file("invalid_config.yaml")
except ValidationError as e:
    print("Config validation failed:")
    for error in e.errors():
        print(f"  {error['loc']}: {error['msg']}")
except FileNotFoundError:
    print("Config file not found, using defaults")
```

## Integration Points

### 1. PolicyEngine
Uses `GitConfig` for all validation logic:
- Branch name validation
- Branch type checking
- Protected branch checks
- Commit prefix generation

### 2. GitManager
Uses `GitConfig` for:
- Default base branch detection
- Branch format string
- Protected branch enforcement

### 3. PhaseStateEngine
Uses `GitConfig` for:
- Phase transition validation
- TDD phase sequencing
- Commit prefix mapping

### 4. MCP Tools
Tools use `GitConfig` indirectly via PolicyEngine and GitManager:
- `create_branch`: Validates branch type, generates name
- `git_delete_branch`: Checks protected branches
- `git_add_or_commit`: Maps phase to commit prefix
- `transition_phase`: Validates phase transitions

## Testing

### Unit Tests
Location: `tests/unit/test_git_config.py`

**Coverage**:
- Default value loading
- Custom config loading
- Singleton pattern behavior
- Validation error cases
- Reset instance functionality

**Example**:
```python
def test_singleton_pattern():
    gc1 = GitConfig.from_file()
    gc2 = GitConfig.from_file()
    assert gc1 is gc2  # Same instance

def test_reset_instance():
    gc1 = GitConfig.from_file()
    GitConfig.reset_instance()
    gc2 = GitConfig.from_file()
    assert gc1 is not gc2  # Different instances
```

### Integration Tests
Location: `tests/integration/test_git_config_integration.py`

**Scenarios**:
- Custom config with PolicyEngine
- Custom config with GitManager
- Config reload during server runtime
- MCP tool compatibility

## See Also

- [GitConfig Customization Guide](./git_config_customization.md) - User guide for customizing config
- [PolicyEngine Documentation](../development/policy_engine.md) - How config is used for validation
- [MCP Schema Caching Limitation](../development/issue55/mcp_schema_caching_limitation.md) - Important client-side limitation

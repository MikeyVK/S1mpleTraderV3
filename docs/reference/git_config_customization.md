# GitConfig Customization Guide

**Status**: APPROVED
**Date**: 2026-04-08
**Related**: Issue #55, Issue #273

## Overview

The `.st3/config/git.yaml` file controls 6 git-related conventions used by the MCP server
workflow tools. The server loads this file once at startup via `ConfigLoader` and injects
the resulting `GitConfig` value object into all tools and managers that need it.

## Configuration File Location

- **Path**: `.st3/config/git.yaml`
- **Format**: YAML
- **Loaded**: On server startup via `ConfigLoader.load_git_config()`
- **Reload**: Restart the MCP server to apply changes

## Available Fields

### 1. Branch Types (`branch_types`)
List of allowed branch type prefixes used by `create_branch`.

**Type**: `list[str]` — required, non-empty

**Default (project)**:
```yaml
branch_types:
  - feature
  - bug
  - fix
  - refactor
  - docs
  - hotfix
  - epic
```

**Example** (team-specific):
```yaml
branch_types:
  - feature
  - bugfix
  - hotfix
  - experiment
```

### 2. Protected Branches (`protected_branches`)
Branch names that cannot be deleted via `git_delete_branch`.

**Type**: `list[str]` — required, non-empty

**Default (project)**:
```yaml
protected_branches:
  - main
  - master
  - develop
```

**Example** (stricter):
```yaml
protected_branches:
  - main
  - staging
  - production
```

### 3. Branch Name Pattern (`branch_name_pattern`)
Regex pattern applied to the name suffix of a branch (the part after `type/number-`).

**Type**: `str` — required, must be a valid regex, cannot be blank

**Default (project)**: `^[a-z0-9-]+$` (lowercase letters, digits, hyphens)

**Example** (allow underscores):
```yaml
branch_name_pattern: "^[a-z0-9_-]+$"
```

### 4. Commit Types (`commit_types`)
List of allowed [Conventional Commit](https://www.conventionalcommits.org/) type prefixes.
Used by `git_add_or_commit` input validation and by `PolicyEngine.decide()` when
`require_tdd_prefix: true` is set in `policies.yaml`.

**Type**: `list[str]` — required, non-empty

**Default (project)**:
```yaml
commit_types:
  - feat
  - fix
  - docs
  - style
  - refactor
  - test
  - chore
  - perf
  - ci
  - build
  - revert
```

**Example** (minimal set):
```yaml
commit_types:
  - feat
  - fix
  - test
  - refactor
  - docs
```

### 5. Default Base Branch (`default_base_branch`)
Default branch used as the base when `create_branch` is called without an explicit base.

**Type**: `str` — required

**Default (project)**: `main`

**Example**:
```yaml
default_base_branch: develop
```

### 6. Issue Title Max Length (`issue_title_max_length`)
Maximum character length enforced when creating issues via `create_issue`.

**Type**: `int` — required, must be ≥ 1

**Default (project)**: `72`

**Example**:
```yaml
issue_title_max_length: 80
```

## Complete Example

Current project configuration (`.st3/config/git.yaml`):

```yaml
# Git Conventions Configuration
branch_types:
  - feature
  - bug
  - fix
  - refactor
  - docs
  - hotfix
  - epic

protected_branches:
  - main
  - master
  - develop

branch_name_pattern: "^[a-z0-9-]+$"

commit_types:
  - feat
  - fix
  - docs
  - style
  - refactor
  - test
  - chore
  - perf
  - ci
  - build
  - revert

default_base_branch: main

issue_title_max_length: 72
```

## Applying Configuration Changes

After editing `.st3/config/git.yaml`, restart the MCP server for changes to take effect:

1. Edit `.st3/config/git.yaml`
2. Restart the MCP server via VS Code Command Palette:
   `MCP: Restart Server`
3. Verify with `get_work_context` or any tool call

**Note**: The VS Code MCP client caches tool input schemas at startup. If you add or
remove `branch_types` or `commit_types`, a full VS Code window reload
(`Developer: Reload Window`) may be needed to update autocomplete.

## Validation

`ConfigLoader.load_git_config()` runs Pydantic validation on load. Any error raises
`ConfigError` and stops server startup with a clear message.

**Rules enforced**:
- All fields must be present (no optional fields with defaults)
- `branch_types` and `protected_branches` must be non-empty lists
- `branch_name_pattern` must be a non-blank, valid regex
- `commit_types` must be a non-empty list
- `issue_title_max_length` must be ≥ 1

**Test your config** (unit test style):
```python
from pathlib import Path
from mcp_server.config.loader import ConfigLoader

config = ConfigLoader(Path(".st3/config")).load_git_config()
print(config.branch_types)        # verify branch types
print(config.commit_types)        # verify commit types
print(config.default_base_branch) # verify default base
```

## Troubleshooting

### Issue: Tool rejects custom branch type
**Symptom**: `create_branch` fails with "Invalid branch_type" error

**Cause**: VS Code MCP client uses cached JSON schema enum from startup

**Solution**: Restart VS Code window (`Developer: Reload Window`) after adding branch types

### Issue: Validation error on load
**Symptom**: Server fails to start; logs show `ConfigError: Config file not found` or
Pydantic validation error

**Cause**: Invalid configuration (missing field, wrong type, invalid regex syntax)

**Solution**:
1. Check `.st3/config/git.yaml` syntax — all 6 fields must be present
2. Verify `branch_name_pattern` is a valid regex
3. Fix the reported field and restart the server

### Issue: Commit type rejected
**Symptom**: `git_add_or_commit` fails with "Invalid commit_type" error

**Cause**: The `commit_type` provided is not in `commit_types`

**Solution**: Either add the type to `commit_types` in `git.yaml` and restart, or use a
type that is already in the list

## See Also

- [GitConfig API Reference](./git_config_api.md) — `GitConfig` class, fields and methods

# GitConfig Customization Guide

**Status**: APPROVED  
**Date**: 2026-01-15  
**Related**: Issue #55

## Overview

The `.st3/git.yaml` file controls 11 git-related conventions used by the MCP server workflow tools. This guide shows you how to customize these conventions for your team's workflow.

## Configuration File Location

- **Path**: `.st3/git.yaml`
- **Format**: YAML
- **Loaded**: On server startup (singleton pattern)
- **Backup**: Automatically created as `.st3/git.yaml.backup` on first modification

## Available Conventions

### 1. Branch Types (`branch_types`)
List of allowed branch type prefixes for branch names.

**Default**: `[feature, fix, refactor, docs, epic]`

**Example**:
```yaml
branch_types:
  - feature
  - bugfix
  - hotfix
  - experiment
```

### 2. TDD Phases (`tdd_phases`)
Sequential phases for Test-Driven Development workflow.

**Default**: `[red, green, refactor, docs]`

**Example**:
```yaml
tdd_phases:
  - test
  - impl
  - refactor
```

### 3. Commit Prefix Map (`commit_prefix_map`)
Maps TDD phases to conventional commit prefixes.

**Default**:
```yaml
commit_prefix_map:
  red: test
  green: feat
  refactor: refactor
  docs: docs
```

**Example** (custom phases):
```yaml
commit_prefix_map:
  test: test
  impl: feat
  refactor: refactor
```

### 4. Protected Branches (`protected_branches`)
Branches that cannot be deleted via `git_delete_branch` tool.

**Default**: `[main, master, develop]`

**Example**:
```yaml
protected_branches:
  - main
  - staging
  - production
```

### 5. Branch Name Pattern (`branch_name_pattern`)
Regex pattern for valid branch name suffixes (after type/number).

**Default**: `^[a-z0-9-]+$` (lowercase, digits, hyphens)

**Example** (allow underscores):
```yaml
branch_name_pattern: ^[a-z0-9_-]+$
```

### 6. Default Base Branch (`default_base_branch`)
Default branch to create new branches from when not specified.

**Default**: `main`

**Example**:
```yaml
default_base_branch: develop
```

### 7. Issue Number Pattern (`issue_number_pattern`)
Regex pattern for extracting issue numbers from branch names.

**Default**: `(?:^|/)(\\d+)-`

**Example** (support JIRA keys):
```yaml
issue_number_pattern: (?:^|/)([A-Z]+-\\d+)-
```

### 8. Epic Naming Conventions (`epic_branch_format`, `epic_issue_pattern`)
Patterns specific to epic branches.

**Defaults**:
```yaml
epic_branch_format: epic/{issue_number}-{name}
epic_issue_pattern: (?:^|/)epic-(\\d+)
```

### 9. Phase Transition Map (`phase_transition_map`)
Defines allowed sequential phase transitions (internal use).

**Default**: Sequential red → green → refactor → docs

### 10. Branch Format String (`branch_format`)
Template for creating branch names: `{type}/{issue_number}-{name}`

### 11. Protected Branch Patterns (`protected_branch_patterns`)
Regex patterns for additional protected branches (e.g., `release/*`).

**Default**: `[^release/.*$]`

## Customization Examples

### Example 1: Trunk-Based Development
```yaml
branch_types: [feature, hotfix]
tdd_phases: [test, impl]
commit_prefix_map:
  test: test
  impl: feat
default_base_branch: trunk
protected_branches: [trunk, main]
```

### Example 2: GitFlow with JIRA
```yaml
branch_types: [feature, bugfix, release, hotfix]
tdd_phases: [red, green, refactor, docs]
default_base_branch: develop
protected_branches: [main, develop]
issue_number_pattern: (?:^|/)([A-Z]+-\\d+)-
branch_name_pattern: ^[a-z0-9_-]+$
```

### Example 3: Minimal TDD Workflow
```yaml
branch_types: [feature, fix]
tdd_phases: [test, impl]
commit_prefix_map:
  test: test
  impl: feat
```

## Applying Configuration Changes

### Important: MCP Client Restart Required

⚠️ **JSON Schema Caching Limitation**: The VS Code MCP client caches JSON schemas at initialization. After modifying `.st3/git.yaml`, you must **restart the VS Code MCP extension connection** (not just the server) for changes to take effect in MCP tools.

**Steps**:
1. Edit `.st3/git.yaml`
2. Restart VS Code MCP extension:
   - Open VS Code Command Palette (`Ctrl+Shift+P`)
   - Run: `MCP: Restart Server` (or disconnect/reconnect)
3. Verify changes: Use `get_work_context` or test a tool call

**Alternative**: Reload VS Code window (`Developer: Reload Window`)

### Validation

The `GitConfig` class validates all settings on load:
- Branch types must be non-empty lowercase strings
- TDD phases must match commit_prefix_map keys
- Patterns must be valid regex
- Protected branches must not overlap with branch types

**Test your config**:
```python
from mcp_server.config.git_config import GitConfig

GitConfig.reset_instance()
gc = GitConfig.from_file()
print(gc.branch_types)  # Verify your changes loaded
```

## Troubleshooting

### Issue: Tool rejects custom branch type
**Symptom**: `create_branch` with custom type fails with pattern validation error

**Cause**: VS Code MCP client uses cached JSON schema from initialization

**Solution**: Restart VS Code MCP extension connection (see "Applying Configuration Changes")

### Issue: Config changes not reflected
**Symptom**: Python tests show new config but tools use old values

**Cause**: Server loaded config at startup, singleton pattern caches instance

**Solution**: 
1. For Python tests: Call `GitConfig.reset_instance()` before `from_file()`
2. For MCP tools: Restart VS Code MCP extension

### Issue: Validation error on load
**Symptom**: Server logs Pydantic validation error on startup

**Cause**: Invalid configuration (typo, wrong type, regex syntax error)

**Solution**: 
1. Check `.st3/git.yaml` syntax
2. Restore from `.st3/git.yaml.backup` if available
3. Review validation error message for specific issue

### Issue: Commit prefixes mismatch
**Symptom**: `git_add_or_commit` creates wrong conventional commit prefix

**Cause**: `commit_prefix_map` doesn't match custom `tdd_phases`

**Solution**: Ensure every phase in `tdd_phases` has an entry in `commit_prefix_map`

## See Also

- [GitConfig API Reference](./git_config_api.md) - Complete class documentation
- [MCP Schema Caching Limitation](../development/issue55/mcp_schema_caching_limitation.md) - Technical details
- [Integration Testing](../development/issue55/integration_test_plan.md) - How we validated the system

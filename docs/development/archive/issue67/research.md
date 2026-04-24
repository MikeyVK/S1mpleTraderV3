# Issue #67 Research: LabelConfig Singleton Stale Cache Bug

## Problem Statement

`LabelConfig.load()` returns a stale cached instance after the YAML schema file has been modified, causing tool failures and ModelPrivateAttr errors.

## Root Cause Analysis

### LabelConfig Implementation (Buggy)

```python
class LabelConfig(BaseModel):
    _instance: Optional["LabelConfig"] = None  # Class-level cache
    
    @classmethod
    def load(cls, config_path: Path | None = None) -> "LabelConfig":
        if cls._instance is not None:
            return cls._instance  # ❌ Returns stale cache!
        
        # ... load from file ...
        cls._instance = instance  # Cache forever
        return instance
```

**Problem:** Once loaded, `_instance` is never invalidated, even if:
- The YAML file is modified
- New fields are added to the schema
- Labels are added/removed

### WorkflowConfig Implementation (Correct)

```python
# workflows.py
class WorkflowConfig(BaseModel):
    @classmethod
    def load(cls, path: Path | None = None) -> "WorkflowConfig":
        # No caching - loads fresh every time
        with open(path, "r", encoding="utf-8") as file_handle:
            data = yaml.safe_load(file_handle)
        return cls(**data)

# Module-level singleton (loaded once at import)
workflow_config = WorkflowConfig.load()  # ✅ Static, no runtime reload needed
```

**Difference:** WorkflowConfig uses a module-level singleton loaded at import time, not a class-level cache that persists across load() calls.

## Bug Reproduction

### Test Results

```bash
$ pytest tests/unit/mcp_server/config/test_labelconfig_singleton_bug.py -v

test_singleton_returns_stale_instance_after_file_change PASSED  # ✅ BUG CONFIRMED
test_singleton_reset_allows_reload FAILED                      # Cache pollution
test_impact_on_label_tools FAILED                              # Cache pollution
```

**Key finding:** First test confirms the bug - even after modifying the YAML file, `load()` returns the cached instance with old data.

### Reproduction Steps

1. Load `LabelConfig` from `labels.yaml` → `_instance` cached
2. Modify `labels.yaml` (add labels, change patterns)
3. Call `load()` again → Returns stale `_instance`
4. Result:
   - `label_exists("newly-added")` returns `False`
   - `len(config.labels)` shows old count
   - `config.label_patterns` missing new patterns

## Impact Assessment

### Affected Components

**LabelConfig**: Uses class-level singleton with no invalidation
- ❌ Stale cache after YAML changes
- ❌ Tools fail with outdated schema

**WorkflowConfig**: Uses module-level singleton
- ✅ No stale cache issue (loaded once at import)
- ✅ To reload, must restart Python process

### Affected Tools

1. **AddLabelsTool** - Uses `label_config.label_exists()`
   - Fails to validate newly added labels
   - Returns "label not found" errors

2. **CreateLabelTool** - Uses `label_config.validate_label_name()`
   - Pattern validation fails with stale patterns
   - Cannot create labels matching new patterns

3. **DetectLabelDriftTool** - Compares YAML vs GitHub
   - Shows incorrect drift (compares stale cache vs live GitHub)

### When Bug Occurs

**Scenario A: Development workflow**
1. Developer adds new label to `labels.yaml`
2. Agent tries to use label via tool
3. Tool validation fails because singleton has stale schema

**Scenario B: Schema evolution**
1. Add `label_patterns` field to schema
2. Load config → Pydantic sets missing field to `ModelPrivateAttr`
3. Access `config.label_patterns` → AttributeError

**Scenario C: MCP server long-running**
1. MCP server loads config at startup
2. User updates `labels.yaml` during session
3. All subsequent load() calls return stale data

## Current Workarounds

### Manual Reset (Ugly)
```python
LabelConfig._instance = None  # Force cache invalidation
config = LabelConfig.load()
```

**Problems:**
- Requires protected member access
- Not discoverable
- Breaks encapsulation

### Process Restart (Heavy)
- Restart MCP server
- All cached state lost
- Slow for development

## Comparison: Class-Level vs Module-Level Singleton

| Aspect | LabelConfig (Class) | WorkflowConfig (Module) |
|--------|-------------------|------------------------|
| Pattern | `cls._instance` cache | `workflow_config = load()` |
| Scope | Persists across calls | Loaded once at import |
| Invalidation | None (bug!) | Process restart only |
| Flexibility | Can reload (if fixed) | Static after import |
| Use case | Runtime config changes | Static config |

## Why WorkflowConfig Pattern Doesn't Apply

**WorkflowConfig assumptions:**
- Workflows rarely change during execution
- Changes require code reload anyway
- Static configuration acceptable

**LabelConfig requirements:**
- Labels change frequently (GitHub sync, new issues)
- Must support runtime updates
- Schema can evolve (patterns, exceptions)

**Conclusion:** LabelConfig needs intelligent cache invalidation, not just removal of caching.

## Recommended Solution

### Option A: Smart Cache (File Modification Time)

```python
class LabelConfig(BaseModel):
    _instance: Optional["LabelConfig"] = None
    _loaded_path: Optional[Path] = None
    _loaded_mtime: Optional[float] = None
    
    @classmethod
    def load(cls, config_path: Path | None = None) -> "LabelConfig":
        if config_path is None:
            config_path = Path(".st3/labels.yaml")
        
        current_mtime = config_path.stat().st_mtime
        
        # Check if cache is valid
        if (
            cls._instance is not None and
            cls._loaded_path == config_path and
            cls._loaded_mtime == current_mtime
        ):
            return cls._instance  # Cache still valid
        
        # Load fresh instance
        instance = cls._load_from_file(config_path)
        
        # Update cache
        cls._instance = instance
        cls._loaded_path = config_path
        cls._loaded_mtime = current_mtime
        
        return instance
```

**Benefits:**
- Automatic reload on file change
- Zero performance impact (stat() is fast)
- No manual intervention needed
- Backward compatible

### Option B: Manual Reset Method

```python
class LabelConfig(BaseModel):
    @classmethod
    def reset(cls) -> None:
        """Force cache invalidation for next load()."""
        cls._instance = None
        cls._loaded_path = None
        cls._loaded_mtime = None
```

**Benefits:**
- Simple API for edge cases
- Explicit control for testing
- Complements Option A

### Option C: No Singleton (Always Reload)

```python
@classmethod
def load(cls, config_path: Path | None = None) -> "LabelConfig":
    # No caching - always load fresh
    return cls._load_from_file(config_path)
```

**Problems:**
- File I/O on every load() call
- Performance impact
- Loses performance benefit of caching

## Recommendation

**Implement Option A + Option B:**
- Smart cache with mtime checking (automatic)
- Manual reset() method (explicit fallback)
- Best of both worlds

## Implementation Plan

### Phase 1: Add mtime-based cache invalidation
1. Add `_loaded_path` and `_loaded_mtime` class attributes
2. Update `load()` to check mtime before returning cache
3. Extract file loading logic to `_load_from_file()` helper

### Phase 2: Add manual reset method
1. Add `@classmethod reset()` method
2. Clear all cache variables

### Phase 3: Apply pattern to WorkflowConfig
1. WorkflowConfig currently doesn't need runtime reload
2. Add same pattern for consistency
3. Future-proof for schema evolution

### Phase 4: Update tests
1. Fix test isolation (reset singleton between tests)
2. Add mtime-based reload test
3. Add reset() method test

## Metrics

**Before Fix:**
- Cache invalidation: Manual only
- File change detection: None
- Tool failure rate: High after YAML changes

**After Fix:**
- Cache invalidation: Automatic (mtime check)
- File change detection: Every load() call
- Tool failure rate: Zero (always current schema)

## Related Issues

- Issue #68: InitializeProjectTool parameter mismatch (fixed on this branch)
- Issue #51: Label management system (parent issue)

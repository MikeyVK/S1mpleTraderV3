# Issue #67 Implementation Plan

## Overview

Fix LabelConfig singleton stale cache bug by implementing intelligent cache invalidation based on file modification time, with manual reset fallback.

## API Design

### 1. Cache State Tracking

```python
class LabelConfig(BaseModel):
    # Existing fields...
    version: str
    labels: list[Label]
    freeform_exceptions: list[str]
    label_patterns: list[LabelPattern]
    
    # Cache state (class-level)
    _instance: Optional["LabelConfig"] = None
    _loaded_path: Optional[Path] = None  # NEW: Track which file was loaded
    _loaded_mtime: Optional[float] = None  # NEW: Track file modification time
    
    # Instance caches (unchanged)
    _labels_by_name: dict[str, Label] = {}
    _labels_by_category: dict[str, list[Label]] = {}
```

**Rationale:**
- `_loaded_path`: Handle multiple config files in tests
- `_loaded_mtime`: Fast file change detection without re-reading
- `Optional[float]`: None when no config loaded yet

### 2. Load Method with Smart Cache

```python
@classmethod
def load(cls, config_path: Path | None = None) -> "LabelConfig":
    """Load label configuration with intelligent cache invalidation.
    
    Automatically reloads if:
    - No cached instance exists
    - Config path changed
    - File was modified (mtime check)
    
    Args:
        config_path: Path to labels.yaml (default: .st3/labels.yaml)
    
    Returns:
        LabelConfig instance (cached or freshly loaded)
    
    Raises:
        FileNotFoundError: Config file not found
        ValueError: Invalid YAML syntax or schema
    """
    # Resolve default path
    if config_path is None:
        config_path = Path(".st3/labels.yaml")
    
    # Check if file exists
    if not config_path.exists():
        raise FileNotFoundError(
            f"Label configuration not found: {config_path}"
        )
    
    # Get current file mtime
    current_mtime = config_path.stat().st_mtime
    
    # Check if cache is still valid
    if (
        cls._instance is not None and
        cls._loaded_path == config_path and
        cls._loaded_mtime == current_mtime
    ):
        return cls._instance  # ✅ Cache hit - file unchanged
    
    # Cache miss - load fresh instance
    instance = cls._load_from_file(config_path)
    
    # Update cache state
    cls._instance = instance
    cls._loaded_path = config_path
    cls._loaded_mtime = current_mtime
    
    return instance
```

**Design decisions:**
- **Early file existence check**: Fail fast before stat() call
- **Three-condition cache validation**: Path, mtime, and instance must all match
- **stat().st_mtime**: Platform-independent, high precision
- **Cache before return**: Ensure cache is always consistent

### 3. File Loading Helper (Extracted)

```python
@classmethod
def _load_from_file(cls, config_path: Path) -> "LabelConfig":
    """Load configuration from YAML file (no caching logic).
    
    Private method - use load() instead for caching.
    
    Args:
        config_path: Path to labels.yaml (must exist)
    
    Returns:
        New LabelConfig instance
    
    Raises:
        ValueError: Invalid YAML syntax or validation error
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML syntax in {config_path}: {e}") from e
    
    # Parse labels (ensure labels field exists)
    if "labels" not in data:
        raise ValueError("Missing required field: labels")
    label_dicts = data["labels"]
    labels = [Label(**ld) for ld in label_dicts]
    
    # Parse label patterns (optional)
    pattern_dicts = data.get("label_patterns", [])
    patterns = [LabelPattern(**pd) for pd in pattern_dicts]
    
    # Create instance
    instance = cls(
        version=data.get("version"),
        labels=labels,
        freeform_exceptions=data.get("freeform_exceptions", []),
        label_patterns=patterns
    )
    
    # Build internal caches
    instance._build_caches()
    
    return instance
```

**Rationale:**
- Extracted from current `load()` method (lines 115-150)
- Pure function - no side effects on class state
- Makes `load()` cleaner - separates caching from loading

### 4. Manual Reset Method

```python
@classmethod
def reset(cls) -> None:
    """Force cache invalidation for next load() call.
    
    Use cases:
    - Testing: Reset singleton between test cases
    - Development: Force reload after external file changes
    - Edge cases: Manual cache busting when mtime unreliable
    
    Example:
        >>> LabelConfig.reset()
        >>> config = LabelConfig.load()  # Guaranteed fresh load
    """
    cls._instance = None
    cls._loaded_path = None
    cls._loaded_mtime = None
```

**Design decisions:**
- **Simple API**: No parameters, just clears cache
- **Complete reset**: All three cache variables cleared
- **Public method**: `reset()` not `_reset()` - intentional part of API
- **No return value**: Side-effect only

## Refactoring Plan

### Step 1: Extract _load_from_file() helper

**Current code (lines 115-150):**
```python
@classmethod
def load(cls, config_path: Path | None = None) -> "LabelConfig":
    if cls._instance is not None:
        return cls._instance  # OLD: Always return cache
    
    if config_path is None:
        config_path = Path(".st3/labels.yaml")
    
    # ... file loading logic (35 lines) ...
    
    cls._instance = instance
    return instance
```

**Step 1a: Extract file loading**
- Move lines 120-145 to new `_load_from_file(config_path)` method
- Keep method signature identical
- No behavior change yet

**Step 1b: Update load() to use helper**
```python
@classmethod
def load(cls, config_path: Path | None = None) -> "LabelConfig":
    if cls._instance is not None:
        return cls._instance
    
    if config_path is None:
        config_path = Path(".st3/labels.yaml")
    
    instance = cls._load_from_file(config_path)  # NEW
    cls._instance = instance
    return instance
```

**Verification:** Run existing tests - all should pass.

### Step 2: Add cache state fields

**Add to class:**
```python
_loaded_path: Optional[Path] = None
_loaded_mtime: Optional[float] = None
```

**Verification:** No behavior change - fields are just declared.

### Step 3: Implement mtime-based cache invalidation

**Replace cache check:**
```python
# OLD:
if cls._instance is not None:
    return cls._instance

# NEW:
if not config_path.exists():
    raise FileNotFoundError(...)

current_mtime = config_path.stat().st_mtime

if (
    cls._instance is not None and
    cls._loaded_path == config_path and
    cls._loaded_mtime == current_mtime
):
    return cls._instance
```

**Update cache storage:**
```python
cls._instance = instance
cls._loaded_path = config_path  # NEW
cls._loaded_mtime = current_mtime  # NEW
```

**Verification:** Run bug reproduction tests - should now pass.

### Step 4: Add reset() method

Simple addition - no refactoring needed.

**Verification:** Add test for reset() method.

## Test Strategy

### Existing Tests (56 tests in test_label_config.py)

**No changes needed** - all existing tests should pass:
- Label creation and validation
- Color format validation
- Immutability tests
- YAML loading tests
- Label lookup methods
- GitHub sync functionality

**Why?** External API unchanged - only caching behavior improved.

### Bug Reproduction Tests (test_labelconfig_singleton_bug.py)

**Current state: 1 passing, 2 failing**

After fix:
1. `test_singleton_returns_stale_instance_after_file_change` → Should FAIL
   - Update assertions: `assert len(config2.labels) == 3` (not 2)
   - Update pattern check: `assert len(config2.label_patterns) == 1`
2. `test_singleton_reset_allows_reload` → Should PASS
3. `test_impact_on_label_tools` → Should PASS

**Rename file:** `test_labelconfig_singleton_fix.py` (no longer a bug!)

### New Tests to Add

**Test 1: Mtime-based cache invalidation**
```python
def test_load_detects_file_modification(tmp_path: Path) -> None:
    """Verify load() reloads when file mtime changes."""
    config_file = tmp_path / "labels.yaml"
    # ... write initial file ...
    
    config1 = LabelConfig.load(config_file)
    assert len(config1.labels) == 2
    
    # Modify file and ensure mtime changes
    time.sleep(0.01)  # Ensure mtime differs
    # ... write updated file ...
    
    config2 = LabelConfig.load(config_file)
    assert len(config2.labels) == 3  # ✅ Reloaded!
    assert config1 is not config2  # Different objects
```

**Test 2: Cache reuse when file unchanged**
```python
def test_load_reuses_cache_when_file_unchanged(tmp_path: Path) -> None:
    """Verify load() returns cached instance when file unchanged."""
    config_file = tmp_path / "labels.yaml"
    # ... write file ...
    
    config1 = LabelConfig.load(config_file)
    config2 = LabelConfig.load(config_file)
    
    assert config1 is config2  # ✅ Same object (cached)
```

**Test 3: Reset method**
```python
def test_reset_invalidates_cache(tmp_path: Path) -> None:
    """Verify reset() forces reload on next load()."""
    config_file = tmp_path / "labels.yaml"
    # ... write file ...
    
    config1 = LabelConfig.load(config_file)
    LabelConfig.reset()
    config2 = LabelConfig.load(config_file)
    
    assert config1 is not config2  # Different objects after reset
```

**Test 4: Different config paths**
```python
def test_load_different_paths_independent_caches(tmp_path: Path) -> None:
    """Verify different config paths don't share cache."""
    config1_file = tmp_path / "config1.yaml"
    config2_file = tmp_path / "config2.yaml"
    # ... write different files ...
    
    cfg1 = LabelConfig.load(config1_file)
    cfg2 = LabelConfig.load(config2_file)
    
    assert cfg1 is not cfg2
    assert len(cfg1.labels) != len(cfg2.labels)
```

### Test Isolation Strategy

**Problem:** Tests share class-level singleton state

**Solution:** Reset in fixture
```python
@pytest.fixture(autouse=True)
def reset_labelconfig_singleton():
    """Reset LabelConfig singleton before each test."""
    LabelConfig.reset()
    yield
    LabelConfig.reset()  # Cleanup after test
```

**Apply to:** `test_labelconfig_singleton_fix.py` only (scoped fixture)

## WorkflowConfig Decision

### Should we apply the same pattern?

**Current WorkflowConfig behavior:**
- Module-level singleton: `workflow_config = WorkflowConfig.load()`
- Loaded once at import time
- No runtime reload capability

**Analysis:**

| Aspect | Apply Pattern? | Reasoning |
|--------|---------------|-----------|
| Consistency | ✅ Yes | Same pattern across all config classes |
| Future-proofing | ✅ Yes | Schema may evolve (add fields) |
| Performance | ⚠️ Neutral | Stat() is fast, module singleton already cached |
| Complexity | ⚠️ Small increase | More code, but cleaner API |
| Current need | ❌ No | Workflows rarely change at runtime |

**Decision: YES, but lower priority**

**Rationale:**
1. **Consistency**: Both are Pydantic config models from YAML
2. **Schema evolution**: If we add fields to workflows.yaml, same bug will occur
3. **Low risk**: Pattern is proven with LabelConfig
4. **Future features**: May need workflow hot-reload for development

**Implementation order:**
1. Fix LabelConfig (Issue #67) - **Priority 1**
2. Apply to WorkflowConfig - **Priority 2** (same PR or follow-up)

### WorkflowConfig changes needed

**Minimal change:**
```python
class WorkflowConfig(BaseModel):
    _instance: Optional["WorkflowConfig"] = None
    _loaded_path: Optional[Path] = None
    _loaded_mtime: Optional[float] = None
    
    @classmethod
    def load(cls, path: Path | None = None) -> "WorkflowConfig":
        if path is None:
            path = Path(".st3/workflows.yaml")
        
        if not path.exists():
            raise FileNotFoundError(...)
        
        current_mtime = path.stat().st_mtime
        
        if (
            cls._instance is not None and
            cls._loaded_path == path and
            cls._loaded_mtime == current_mtime
        ):
            return cls._instance
        
        instance = cls._load_from_file(path)
        cls._instance = instance
        cls._loaded_path = path
        cls._loaded_mtime = current_mtime
        return instance
    
    @classmethod
    def reset(cls) -> None:
        """Force cache invalidation."""
        cls._instance = None
        cls._loaded_path = None
        cls._loaded_mtime = None
```

**Module-level singleton update:**
```python
# Keep for backward compatibility
workflow_config = WorkflowConfig.load()
```

**Tests needed:** Same 4 tests as LabelConfig

## Implementation Checklist

### Phase 1: LabelConfig Fix (Issue #67)

- [ ] Extract `_load_from_file()` helper method
- [ ] Add `_loaded_path` and `_loaded_mtime` fields
- [ ] Implement mtime-based cache check in `load()`
- [ ] Add `reset()` class method
- [ ] Update bug reproduction tests (flip assertions)
- [ ] Add 4 new tests (mtime detection, cache reuse, reset, multi-path)
- [ ] Add fixture for test isolation
- [ ] Run full test suite (56 existing + 7 new = 63 tests)
- [ ] Update research.md with "Fixed" section

### Phase 2: WorkflowConfig Consistency (Optional)

- [ ] Extract `_load_from_file()` helper method
- [ ] Add cache state fields
- [ ] Implement mtime-based cache check
- [ ] Add `reset()` class method
- [ ] Add 4 tests for WorkflowConfig
- [ ] Run workflow tests (12 existing + 4 new = 16 tests)
- [ ] Document in research.md

## Risk Assessment

### Low Risk

✅ **Backward compatible**: External API unchanged
- `LabelConfig.load()` signature identical
- All existing code works without changes
- Module imports unchanged

✅ **Test coverage**: 100% of new code paths tested
- Existing 56 tests validate unchanged behavior
- 7 new tests cover all cache scenarios

✅ **Performance**: Improved or neutral
- Cache reuse: Same performance (fast path)
- Cache miss: +1 stat() call (~0.1ms on SSD)
- File reload: Same as before

### Medium Risk

⚠️ **Edge case: Rapid file modifications**
- If file modified twice within mtime precision (~1ms on most filesystems)
- Mitigation: time.sleep(0.01) in tests forces mtime change
- Real-world impact: Low (human edits are slow)

⚠️ **Test isolation**
- Singleton state leaks between tests if reset() not called
- Mitigation: autouse fixture in singleton test file
- Alternative: Use tmp_path and explicit config_path in all tests

### Mitigations

1. **Test isolation**: `@pytest.fixture(autouse=True)` for reset
2. **Documentation**: Clear docstring in `reset()` method
3. **Gradual rollout**: Fix LabelConfig first, then WorkflowConfig
4. **Monitoring**: Verify tool success rates after deployment

## Success Criteria

### Functional Requirements

✅ **Cache invalidation works**
- File modification triggers reload
- Tools get current schema immediately
- No manual intervention needed

✅ **Manual reset available**
- `LabelConfig.reset()` works in tests
- Documented in docstring
- Used in test fixtures

✅ **Performance maintained**
- Cache hit: O(1) - same as before
- Cache miss: O(file_read) + O(stat) - negligible overhead

### Quality Requirements

✅ **All tests passing**
- 56 existing tests: unchanged behavior
- 7 new tests: cache scenarios covered
- Bug reproduction tests: assertions flipped

✅ **Code quality maintained**
- Pylint: 10/10 (no exceptions)
- Mypy: strict mode passing
- Pyright: no new warnings

✅ **Documentation complete**
- Docstrings for new methods
- Research document updated
- Implementation plan captured

## Timeline Estimate

| Phase | Tasks | Time | 
|-------|-------|------|
| Refactor | Extract helper, add fields | 15 min |
| Implement | Mtime check, reset method | 20 min |
| Test | Write 7 new tests, fix old tests | 30 min |
| Validate | Run full suite, fix issues | 15 min |
| Document | Update research.md | 10 min |
| **Total** | **Issue #67 complete** | **~90 min** |

**WorkflowConfig (optional):** +60 min (same pattern, less complexity)

## Next Steps

1. ✅ Research phase complete (current)
2. → Planning phase complete (this document)
3. → TDD phase: Implement with red-green-refactor
4. → Integration phase: Verify tools work
5. → Documentation phase: Update Issue #67

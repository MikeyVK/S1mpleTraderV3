# Issue #51 TDD Implementation Plan

**Phase:** TDD  
**Date:** 2025-12-28  
**Issue:** #51 - Config: Label Management System (labels.yaml)

---

## Overview

**TDD Approach:** 6 RED-GREEN-REFACTOR cycles
**Target:** 10.0/10 all quality gates, 100% meaningful coverage
**Branch:** refactor/51-labels-yaml (from epic refactor/49)

**Key Principles from coding_standards:**
1. Tests FIRST (RED), then minimal implementation (GREEN), then quality (REFACTOR)
2. Commit each phase separately with conventional commits
3. All 5 quality gates checked in REFACTOR phase
4. Type hints complete, imports organized, max 100 chars/line

---

## Cycle 1: Label Dataclass (Foundation)

### RED Phase - Write Tests First

**File:** `tests/config/test_label_config.py`

**Scaffold with generic template:**
```python
"""
Unit tests for Label dataclass.

Tests immutable label definition with color validation.

@layer: Tests (Unit)
@dependencies: [pytest, dataclasses, mcp_server.config.label_config]
"""
```

**Tests to write (8 tests):**
1. `test_label_creation_valid()` - Create label with valid color
2. `test_label_creation_with_description()` - Optional description
3. `test_label_creation_lowercase_color()` - "ff0000" accepted
4. `test_label_creation_uppercase_color()` - "FF0000" accepted
5. `test_label_creation_mixed_color()` - "AbC123" accepted
6. `test_label_invalid_color_hash_prefix()` - Reject "#ff0000"
7. `test_label_invalid_color_too_short()` - Reject "ff00"
8. `test_label_invalid_color_non_hex()` - Reject "gggggg"
9. `test_label_immutable()` - frozen=True enforced
10. `test_label_to_github_dict()` - Converts to API format

**Expected failures:** ImportError (module doesn't exist)

**Commit:**
```
test: add Label dataclass tests (RED)

- 10 tests for Label creation, validation, immutability
- Color format validation: 6-char hex WITHOUT # prefix
- Test to_github_dict() conversion

Status: RED
Expected: ImportError (module not created yet)
```

### GREEN Phase - Minimal Implementation

**File:** `mcp_server/config/label_config.py`

**Scaffold with generic template:**
```python
"""
Label configuration management.

Loads and validates label definitions from labels.yaml.

@layer: Backend (Config)
@dependencies: [dataclasses, re, pathlib, yaml, pydantic]
@responsibilities:
    - Load labels from YAML
    - Validate label format (name, color)
    - Provide label lookup by name/category
    - Sync labels to GitHub
"""
```

**Implementation (Label only):**
```python
from dataclasses import dataclass
import re

@dataclass(frozen=True)
class Label:
    """Immutable label definition from labels.yaml."""
    name: str
    color: str  # 6-char hex WITHOUT # prefix
    description: str = ""
    
    def __post_init__(self):
        """Validate color format on construction."""
        if not self._is_valid_color(self.color):
            raise ValueError(
                f"Invalid color format '{self.color}'. "
                f"Expected 6-character hex WITHOUT # prefix (e.g., 'ff0000')"
            )
    
    @staticmethod
    def _is_valid_color(color: str) -> bool:
        """Check if color is valid 6-char hex."""
        return bool(re.match(r'^[0-9a-fA-F]{6}$', color))
    
    def to_github_dict(self) -> dict[str, str]:
        """Convert to GitHub API format."""
        return {
            "name": self.name,
            "color": self.color,
            "description": self.description
        }
```

**Verify:**
```bash
pytest tests/config/test_label_config.py -v
```
Expected: All 10 tests pass

**Commit:**
```
feat: implement Label dataclass with color validation

- Immutable dataclass (frozen=True)
- Color validation in __post_init__: 6-char hex, no # prefix
- to_github_dict() for API conversion
- Type hints complete

Status: GREEN
Tests: 10/10 passing
```

### REFACTOR Phase - Quality Gates

**Quality checks (all must be 10/10):**

**Gate 1: Whitespace/Parens**
```powershell
python -m pylint mcp_server/config/label_config.py --disable=all --enable=trailing-whitespace,superfluous-parens
```

**Gate 2: Imports**
```powershell
python -m pylint mcp_server/config/label_config.py --disable=all --enable=import-outside-toplevel
```

**Gate 3: Line Length**
```powershell
python -m pylint mcp_server/config/label_config.py --disable=all --enable=line-too-long --max-line-length=100
```

**Gate 5: Tests**
```powershell
pytest tests/config/test_label_config.py --tb=line
```

**Pylance Check:**
- Open both files in VS Code
- Check Problems panel: 0 errors, 0 warnings

**Improvements:**
- Add file header with @layer, @dependencies
- Organize imports (groups with comments)
- Add comprehensive docstrings
- Format to 100 char max

**Commit:**
```
refactor: add quality improvements to Label dataclass

- File header with layer/dependencies
- Import organization (standard/third-party/project)
- Enhanced docstrings
- Pylance: 0 errors, 0 warnings

Quality gates: 10/10 (all 5 gates)
Status: REFACTOR complete
```

---

## Cycle 2: LabelConfig Loading (YAML → Pydantic)

### RED Phase - Write Tests First

**Add to:** `tests/config/test_label_config.py`

**Tests to write (12 tests):**
1. `test_load_valid_yaml()` - Load simple valid YAML
2. `test_load_multiple_labels()` - Multiple labels in list
3. `test_load_with_freeform_exceptions()` - Optional freeform list
4. `test_load_file_not_found()` - FileNotFoundError with clear message
5. `test_load_invalid_yaml_syntax()` - ValueError for YAML syntax errors
6. `test_load_missing_version_field()` - Pydantic ValidationError
7. `test_load_missing_labels_field()` - Pydantic ValidationError
8. `test_load_invalid_color_in_yaml()` - ValueError from Label.__post_init__
9. `test_load_duplicate_label_names()` - Pydantic validator catches
10. `test_load_singleton_pattern()` - Same instance returned
11. `test_load_empty_labels_list()` - Valid but empty
12. `test_load_builds_caches()` - _labels_by_name populated

**Use tmp_path fixture for YAML files**

**Commit:**
```
test: add LabelConfig loading tests (RED)

- 12 tests for YAML loading, validation, error handling
- Tests singleton pattern
- Tests Pydantic validation (missing fields, duplicates)
- Tests cache initialization

Status: RED
Expected: NameError (LabelConfig not defined)
```

### GREEN Phase - Implement Loading

**Add to:** `mcp_server/config/label_config.py`

**Implementation:**
```python
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
import yaml

class LabelConfig(BaseModel):
    """Label configuration loaded from labels.yaml."""
    version: str = Field(..., description="Schema version")
    labels: list[Label] = Field(..., description="Label definitions")
    freeform_exceptions: list[str] = Field(
        default_factory=list,
        description="Non-pattern labels"
    )
    
    model_config = {
        "arbitrary_types_allowed": True  # Allow Label dataclass
    }
    
    _instance: Optional["LabelConfig"] = None
    _labels_by_name: dict[str, Label] = {}
    
    @classmethod
    def load(cls, config_path: Path | None = None) -> "LabelConfig":
        """Load label configuration from YAML file."""
        if cls._instance is not None:
            return cls._instance
        
        if config_path is None:
            config_path = Path(".st3/labels.yaml")
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Label configuration not found: {config_path}"
            )
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in {config_path}: {e}")
        
        # Parse labels
        label_dicts = data.get("labels", [])
        labels = [Label(**ld) for ld in label_dicts]
        
        # Create instance
        instance = cls(
            version=data.get("version"),
            labels=labels,
            freeform_exceptions=data.get("freeform_exceptions", [])
        )
        
        instance._build_caches()
        cls._instance = instance
        return instance
    
    def _build_caches(self):
        """Build internal lookup caches."""
        self._labels_by_name = {label.name: label for label in self.labels}
    
    @field_validator("labels")
    @classmethod
    def validate_no_duplicates(cls, labels: list[Label]) -> list[Label]:
        """Ensure no duplicate label names."""
        names = [label.name for label in labels]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            raise ValueError(f"Duplicate label names: {set(duplicates)}")
        return labels
```

**Verify:**
```bash
pytest tests/config/test_label_config.py::test_load -v
```

**Commit:**
```
feat: implement LabelConfig loading from YAML

- Pydantic BaseModel with version, labels, freeform_exceptions
- Singleton pattern with _instance class variable
- YAML loading with yaml.safe_load
- Duplicate name validation via field_validator
- Cache building (_labels_by_name dict)

Status: GREEN
Tests: 22/22 passing (10 Label + 12 LabelConfig)
```

### REFACTOR Phase - Quality & Examples

**Add to LabelConfig:**
```python
model_config = {
    "arbitrary_types_allowed": True,
    "json_schema_extra": {
        "examples": [
            {
                "description": "Minimal config",
                "version": "1.0",
                "labels": [
                    {"name": "type:feature", "color": "1D76DB"}
                ]
            },
            {
                "description": "With freeform exceptions",
                "version": "1.0",
                "labels": [
                    {"name": "type:bug", "color": "D73A4A"}
                ],
                "freeform_exceptions": ["good first issue"]
            }
        ]
    }
}
```

**Run all quality gates**

**Commit:**
```
refactor: add json_schema_extra examples to LabelConfig

- 2 examples: minimal config, with freeform exceptions
- Enhanced error messages
- Docstring improvements

Quality gates: 10/10
Pylance: 0 errors, 0 warnings
```

---

## Cycle 3: LabelConfig Validation (Name/Color Rules)

### RED Phase - Write Tests

**Add to test file:**

**Tests to write (10 tests):**
1. `test_validate_label_name_valid_type()` - "type:feature" passes
2. `test_validate_label_name_valid_priority()` - "priority:high" passes
3. `test_validate_label_name_all_categories()` - Test each category
4. `test_validate_label_name_freeform_exception()` - "good first issue" passes
5. `test_validate_label_name_no_colon()` - "invalid" fails
6. `test_validate_label_name_wrong_category()` - "wrong:value" fails
7. `test_validate_label_name_uppercase()` - "Type:Feature" fails
8. `test_validate_label_name_spaces()` - "type: feature" fails (unless freeform)
9. `test_label_exists_true()` - Defined label returns True
10. `test_label_exists_false()` - Undefined returns False

**Commit:**
```
test: add label validation tests (RED)

- 10 tests for validate_label_name() method
- Tests all 8 categories (type, priority, status, phase, scope, component, effort, parent)
- Tests freeform exceptions
- Tests label_exists() lookup

Status: RED
Expected: AttributeError (methods not implemented)
```

### GREEN Phase - Implement Validation

**Add to LabelConfig:**
```python
def validate_label_name(self, name: str) -> tuple[bool, str]:
    """Validate label name against pattern rules."""
    if name in self.freeform_exceptions:
        return (True, "")
    
    pattern = r'^(type|priority|status|phase|scope|component|effort|parent):[a-z0-9-]+$'
    if not re.match(pattern, name):
        return (
            False,
            f"Label '{name}' does not match required pattern. "
            f"Expected 'category:value' format."
        )
    
    return (True, "")

def label_exists(self, name: str) -> bool:
    """Check if label is defined in labels.yaml."""
    return name in self._labels_by_name
```

**Verify tests pass**

**Commit:**
```
feat: implement label name validation and existence check

- validate_label_name(): regex pattern + freeform exceptions
- label_exists(): O(1) lookup via cache
- Validates 8 categories: type, priority, status, phase, scope, component, effort, parent

Status: GREEN
Tests: 32/32 passing
```

### REFACTOR Phase - Clear Error Messages

**Improve error message:**
```python
return (
    False,
    f"Label '{name}' does not match required pattern. "
    f"Expected format: 'category:value' where category is one of "
    f"[type, priority, status, phase, scope, component, effort, parent] "
    f"and value is lowercase alphanumeric with hyphens. "
    f"Freeform labels must be in freeform_exceptions list."
)
```

**Run quality gates**

**Commit:**
```
refactor: enhance validation error messages

- Detailed explanation of pattern requirements
- Lists valid categories
- Mentions freeform_exceptions option

Quality gates: 10/10
```

---

## Cycle 4: LabelConfig Queries (Lookup by Name/Category)

### RED Phase - Write Tests

**Tests to write (8 tests):**
1. `test_get_label_found()` - Returns Label object
2. `test_get_label_not_found()` - Returns None
3. `test_get_label_case_sensitive()` - "Type:feature" != "type:feature"
4. `test_get_labels_by_category_type()` - Returns all type: labels
5. `test_get_labels_by_category_priority()` - Returns all priority: labels
6. `test_get_labels_by_category_empty()` - Unknown category returns []
7. `test_get_labels_by_category_cache_correct()` - Verify grouping
8. `test_cache_build_on_load()` - Caches populated at load time

**Commit:**
```
test: add label query tests (RED)

- 8 tests for get_label() and get_labels_by_category()
- Tests cache correctness
- Tests case sensitivity
- Tests empty results

Status: RED
Expected: Some methods incomplete
```

### GREEN Phase - Implement Queries

**Add to LabelConfig:**
```python
def get_label(self, name: str) -> Label | None:
    """Get label by exact name match."""
    return self._labels_by_name.get(name)

def get_labels_by_category(self, category: str) -> list[Label]:
    """Get all labels in a category."""
    return self._labels_by_category.get(category, [])

def _build_caches(self):
    """Build internal lookup caches."""
    self._labels_by_name = {label.name: label for label in self.labels}
    
    # Group by category
    self._labels_by_category = {}
    for label in self.labels:
        if ":" in label.name:
            cat = label.name.split(":", 1)[0]
            if cat not in self._labels_by_category:
                self._labels_by_category[cat] = []
            self._labels_by_category[cat].append(label)
```

**Add _labels_by_category field:**
```python
_labels_by_category: dict[str, list[Label]] = {}
```

**Verify tests**

**Commit:**
```
feat: implement label query methods

- get_label(): O(1) lookup by name
- get_labels_by_category(): O(1) category filtering
- _build_caches(): builds both name and category indexes

Status: GREEN
Tests: 40/40 passing
```

### REFACTOR Phase - Type Hints & Docstrings

**Ensure:**
- All type hints present
- Docstrings complete
- Line length < 100

**Run quality gates**

**Commit:**
```
refactor: complete type hints and docstrings for queries

- Enhanced docstrings with Args/Returns
- Type hints verified
- Line length checked

Quality gates: 10/10
```

---

## Cycle 5: GitHub Sync Mechanism

### RED Phase - Write Tests

**Tests to write (12 tests):**
1. `test_sync_create_new_labels()` - Creates missing labels
2. `test_sync_update_changed_color()` - Updates color difference
3. `test_sync_update_changed_description()` - Updates description
4. `test_sync_skip_unchanged()` - Skips identical labels
5. `test_sync_dry_run_no_changes()` - Dry run doesn't call GitHub API
6. `test_sync_dry_run_reports_changes()` - Dry run shows what would change
7. `test_sync_github_api_error()` - Handles API errors gracefully
8. `test_sync_partial_success()` - Some succeed, some fail
9. `test_sync_empty_labels_list()` - Handles empty YAML
10. `test_sync_result_format()` - Returns correct dict structure
11. `test_needs_update_color_differs()` - Helper detects color change
12. `test_needs_update_description_differs()` - Helper detects description change

**Use mock for GitHubAdapter**

**Commit:**
```
test: add GitHub sync tests (RED)

- 12 tests for sync_to_github() method
- Tests create, update, skip logic
- Tests dry-run mode
- Tests error handling and partial success
- Uses mock GitHubAdapter

Status: RED
Expected: AttributeError (sync_to_github not implemented)
```

### GREEN Phase - Implement Sync

**Add to LabelConfig:**
```python
def sync_to_github(
    self,
    github_adapter: Any,
    dry_run: bool = False
) -> dict[str, list[str]]:
    """Sync labels to GitHub repository."""
    result = {
        "created": [],
        "updated": [],
        "skipped": [],
        "errors": []
    }
    
    try:
        existing = github_adapter.list_labels()
        existing_by_name = {label["name"]: label for label in existing}
    except Exception as e:
        result["errors"].append(f"Failed to fetch labels: {e}")
        return result
    
    for label in self.labels:
        try:
            if label.name not in existing_by_name:
                if not dry_run:
                    github_adapter.create_label(
                        name=label.name,
                        color=label.color,
                        description=label.description
                    )
                result["created"].append(label.name)
            else:
                existing_label = existing_by_name[label.name]
                needs_update = (
                    existing_label["color"] != label.color or
                    existing_label.get("description", "") != label.description
                )
                
                if needs_update:
                    if not dry_run:
                        github_adapter.update_label(
                            name=label.name,
                            color=label.color,
                            description=label.description
                        )
                    result["updated"].append(label.name)
                else:
                    result["skipped"].append(label.name)
        
        except Exception as e:
            result["errors"].append(f"{label.name}: {e}")
    
    return result
```

**Verify tests**

**Commit:**
```
feat: implement GitHub sync mechanism

- sync_to_github(): create/update/skip logic
- Dry-run mode support
- Error handling per label (partial success)
- Returns detailed diff report

Status: GREEN
Tests: 52/52 passing
```

### REFACTOR Phase - Extract Helper

**Extract needs_update logic:**
```python
def _needs_update(self, yaml_label: Label, github_label: dict) -> bool:
    """Check if GitHub label needs update."""
    return (
        yaml_label.color != github_label["color"] or
        yaml_label.description != github_label.get("description", "")
    )
```

**Use in sync method**

**Run quality gates**

**Commit:**
```
refactor: extract _needs_update helper method

- Cleaner sync logic
- Reusable comparison logic
- Enhanced readability

Quality gates: 10/10
```

---

## Cycle 6: Tool Integration

### RED Phase - Write Tests

**File:** `tests/tools/test_label_tools.py` (create new)

**Tests to write (15 tests):**

**CreateLabelTool:**
1. `test_create_label_validates_name()` - Rejects invalid pattern
2. `test_create_label_rejects_hash_prefix()` - Rejects "#ff0000"
3. `test_create_label_valid_succeeds()` - Creates valid label
4. `test_create_label_freeform_exception()` - Allows "good first issue"

**AddLabelsTool:**
5. `test_add_labels_validates_existence()` - Rejects undefined labels
6. `test_add_labels_all_valid()` - Adds all valid labels
7. `test_add_labels_partial_invalid()` - Rejects if any invalid
8. `test_add_labels_freeform_allowed()` - Accepts freeform exceptions

**SyncLabelsToGitHubTool (NEW):**
9. `test_sync_tool_dry_run_default()` - Dry-run is default
10. `test_sync_tool_shows_summary()` - Returns formatted summary
11. `test_sync_tool_applies_changes()` - dry_run=False applies
12. `test_sync_tool_handles_errors()` - Graceful error handling
13. `test_sync_tool_success_false_on_errors()` - success=False if errors
14. `test_sync_tool_empty_labels()` - Handles empty YAML
15. `test_sync_tool_loads_config()` - Calls LabelConfig.load()

**Commit:**
```
test: add tool integration tests (RED)

- 15 tests for CreateLabelTool, AddLabelsTool, SyncLabelsToGitHubTool
- Tests validation hooks
- Tests error handling
- Tests new sync tool

Status: RED
Expected: Tool validation not yet added
```

### GREEN Phase - Update Tools

**Update CreateLabelTool** in `mcp_server/tools/label_tools.py`:
```python
def execute(self, name: str, color: str, description: str = "") -> dict:
    # Validate name pattern
    label_config = LabelConfig.load()
    is_valid, error_msg = label_config.validate_label_name(name)
    if not is_valid:
        return {"success": False, "error": error_msg}
    
    # Reject # prefix
    if color.startswith("#"):
        return {
            "success": False,
            "error": f"Color must not include # prefix. Use '{color[1:]}' instead."
        }
    
    # Create via GitHub API
    # ... existing code
```

**Update AddLabelsTool** in `mcp_server/tools/issue_tools.py`:
```python
def execute(self, issue_number: int, labels: list[str]) -> dict:
    # Validate existence
    label_config = LabelConfig.load()
    
    undefined = [label for label in labels if not label_config.label_exists(label)]
    if undefined:
        return {
            "success": False,
            "error": f"Labels not defined in labels.yaml: {undefined}"
        }
    
    # Add labels
    # ... existing code
```

**Create SyncLabelsToGitHubTool** in `mcp_server/tools/label_tools.py`:
```python
class SyncLabelsToGitHubTool(BaseTool):
    """Sync labels from labels.yaml to GitHub."""
    
    name = "sync_labels_to_github"
    description = "Sync label definitions from labels.yaml to GitHub"
    
    input_schema = {
        "type": "object",
        "properties": {
            "dry_run": {
                "type": "boolean",
                "description": "Preview changes without applying",
                "default": True
            }
        }
    }
    
    def execute(self, dry_run: bool = True) -> dict:
        """Execute label sync."""
        label_config = LabelConfig.load()
        github_adapter = self.context.get_adapter("github")
        
        result = label_config.sync_to_github(github_adapter, dry_run=dry_run)
        
        summary = (
            f"Created {len(result['created'])}, "
            f"Updated {len(result['updated'])}, "
            f"Skipped {len(result['skipped'])}"
        )
        
        if result['errors']:
            summary += f", Errors {len(result['errors'])}"
        
        return {
            "success": len(result['errors']) == 0,
            "summary": summary,
            "details": result,
            "dry_run": dry_run
        }
```

**Verify tests**

**Commit:**
```
feat: integrate label validation into tools

- CreateLabelTool: validate name pattern, reject # prefix
- AddLabelsTool: validate label existence
- SyncLabelsToGitHubTool: NEW tool for GitHub sync

Status: GREEN
Tests: 67/67 passing (52 config + 15 tools)
```

### REFACTOR Phase - Final Quality Pass

**Check all files:**
- mcp_server/config/label_config.py
- mcp_server/tools/label_tools.py  
- mcp_server/tools/issue_tools.py
- tests/config/test_label_config.py
- tests/tools/test_label_tools.py

**Run ALL quality gates on ALL files**

**Commit:**
```
refactor: final quality pass on all files

- All imports organized (3 groups)
- All docstrings complete
- All type hints present
- Line length < 100
- Pylance: 0 errors, 0 warnings on all files

Quality gates: 10/10 (implementation AND tests)
Status: REFACTOR complete
```

---

## Quality Gates (Detailed)

### Gate 1: Trailing Whitespace & Parens
```powershell
python -m pylint mcp_server/config/label_config.py --disable=all --enable=trailing-whitespace,superfluous-parens
python -m pylint mcp_server/tools/label_tools.py --disable=all --enable=trailing-whitespace,superfluous-parens
python -m pylint mcp_server/tools/issue_tools.py --disable=all --enable=trailing-whitespace,superfluous-parens
python -m pylint tests/config/test_label_config.py --disable=all --enable=trailing-whitespace,superfluous-parens
python -m pylint tests/tools/test_label_tools.py --disable=all --enable=trailing-whitespace,superfluous-parens
```
**Target:** 10.00/10 for EACH file

### Gate 2: Import Placement
```powershell
python -m pylint <each_file> --disable=all --enable=import-outside-toplevel
```
**Target:** 10.00/10 (no imports inside functions)

### Gate 3: Line Length
```powershell
python -m pylint <each_file> --disable=all --enable=line-too-long --max-line-length=100
```
**Target:** 10.00/10

### Gate 4: Type Checking
```powershell
python -m mypy mcp_server/config/label_config.py --strict --no-error-summary
python -m mypy mcp_server/tools/label_tools.py --strict --no-error-summary
```
**Target:** 0 errors
**Note:** Skip test files (Pydantic false positives)

### Gate 5: Tests Passing
```powershell
pytest tests/config/test_label_config.py -v
pytest tests/tools/test_label_tools.py -v
```
**Target:** All tests pass (100%)

### Pylance Verification
**Steps:**
1. Open ALL 5 files in VS Code
2. Check Problems panel
3. **Target:** 0 errors, 0 warnings

---

## Commit Strategy

### Commit Format (Conventional Commits)
```
<type>: <subject>

<body with bullets>

Status: RED|GREEN|REFACTOR
Quality gates: 10/10 (if REFACTOR)
Tests: X/X passing (if GREEN/REFACTOR)
Pylance: 0 errors, 0 warnings (if REFACTOR)
```

### Commit Types
- `test:` - RED phase (tests only)
- `feat:` - GREEN phase (implementation)
- `refactor:` - REFACTOR phase (quality improvements)
- `docs:` - Documentation updates

### Example Commit Sequence (Cycle 1)
1. `test: add Label dataclass tests (RED)`
2. `feat: implement Label dataclass with color validation`
3. `refactor: add quality improvements to Label dataclass`

### Total Expected Commits
- Cycle 1: 3 commits (RED, GREEN, REFACTOR)
- Cycle 2: 3 commits
- Cycle 3: 3 commits
- Cycle 4: 3 commits
- Cycle 5: 3 commits
- Cycle 6: 3 commits
- Final: 1 commit (labels.yaml creation + docs update)

**Total: ~19 commits**

---

## Success Criteria

**Must achieve:**
- ✅ All 67+ tests passing
- ✅ Quality gates 10/10 on ALL files (implementation + tests)
- ✅ Pylance 0 errors, 0 warnings on ALL files
- ✅ Type hints complete (mypy strict passes)
- ✅ File headers present (all files)
- ✅ Import organization correct (all files)
- ✅ Docstrings complete (all public methods)
- ✅ Line length < 100 (all files)
- ✅ Conventional commit format (all commits)

**Deliverables:**
- `.st3/labels.yaml` with 50+ labels
- `mcp_server/config/label_config.py` (Label + LabelConfig)
- Updated `mcp_server/tools/label_tools.py` (CreateLabel + Sync)
- Updated `mcp_server/tools/issue_tools.py` (AddLabels)
- `tests/config/test_label_config.py` (52+ tests)
- `tests/tools/test_label_tools.py` (15+ tests)

---

## References

- **Planning:** docs/development/issue51/planning.md
- **Design:** docs/development/issue51/design.md
- **Research:** docs/development/issue51/research.md
- **Coding Standards:** docs/coding_standards/
- **Issue #50:** WorkflowConfig reference implementation (10.0/10 achieved)

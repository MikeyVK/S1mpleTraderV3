# Issue #51 Design: Label Management System

**Phase:** Design  
**Status:** DRAFT  
**Date:** 2025-12-28  
**Issue:** #51 - Config: Label Management System (labels.yaml)

---

## Executive Summary

This document specifies the technical implementation of the label management system using `labels.yaml`. It defines class structures, field types, validation logic, error handling, and integration patterns based on the planning phase decisions.

**Key Components:**
- `Label` dataclass: Immutable label definition
- `LabelConfig` class: Singleton pattern, Pydantic validation
- Validation: Regex-based name/color checks with clear errors
- GitHub sync: Create/update via PyGithub with diff reporting
- Tool integration: Validation hooks in existing tools

---

## 1. Class Structure

### 1.1 Label Dataclass

**Location:** `mcp_server/config/label_config.py`

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Label:
    """Immutable label definition from labels.yaml"""
    name: str
    color: str  # 6-char hex WITHOUT # prefix
    description: str = ""
    
    def __post_init__(self):
        """Validate color format on construction"""
        if not self._is_valid_color(self.color):
            raise ValueError(
                f"Invalid color format '{self.color}'. "
                f"Expected 6-character hex WITHOUT # prefix (e.g., 'ff0000')"
            )
    
    @staticmethod
    def _is_valid_color(color: str) -> bool:
        """Check if color is valid 6-char hex"""
        import re
        return bool(re.match(r'^[0-9a-fA-F]{6}$', color))
    
    def to_github_dict(self) -> dict[str, str]:
        """Convert to GitHub API format"""
        return {
            "name": self.name,
            "color": self.color,
            "description": self.description
        }
```

**Design Decisions:**
- `frozen=True`: Immutable to prevent accidental modification
- `__post_init__`: Validate color format at construction time
- `to_github_dict()`: Clean separation of internal/external representation

### 1.2 LabelConfig Class

**Location:** `mcp_server/config/label_config.py`

```python
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator
import yaml

class LabelConfig(BaseModel):
    """
    Label configuration loaded from labels.yaml.
    Uses singleton pattern like WorkflowConfig.
    """
    version: str = Field(..., description="Schema version (e.g., '1.0')")
    labels: list[Label] = Field(..., description="List of label definitions")
    freeform_exceptions: list[str] = Field(
        default_factory=list,
        description="Label names exempt from pattern validation"
    )
    
    # Singleton instance
    _instance: Optional["LabelConfig"] = None
    _labels_by_name: dict[str, Label] = {}  # Cache for fast lookup
    _labels_by_category: dict[str, list[Label]] = {}  # Cache by category
    
    @classmethod
    def load(cls, config_path: Path | None = None) -> "LabelConfig":
        """
        Load label configuration from YAML file.
        Returns cached instance if already loaded.
        
        Args:
            config_path: Path to labels.yaml (default: .st3/labels.yaml)
            
        Returns:
            LabelConfig instance
            
        Raises:
            FileNotFoundError: If labels.yaml doesn't exist
            ValueError: If YAML is invalid or contains errors
        """
        if cls._instance is not None:
            return cls._instance
        
        if config_path is None:
            config_path = Path(".st3/labels.yaml")
        
        if not config_path.exists():
            raise FileNotFoundError(
                f"Label configuration not found: {config_path}. "
                f"Create labels.yaml with 'version' and 'labels' fields."
            )
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in {config_path}: {e}")
        
        # Parse labels into Label dataclasses
        label_dicts = data.get("labels", [])
        labels = [Label(**label_dict) for label_dict in label_dicts]
        
        # Create instance with Pydantic validation
        instance = cls(
            version=data.get("version"),
            labels=labels,
            freeform_exceptions=data.get("freeform_exceptions", [])
        )
        
        # Build lookup caches
        instance._build_caches()
        
        # Store singleton
        cls._instance = instance
        return instance
    
    def _build_caches(self):
        """Build internal lookup caches for performance"""
        self._labels_by_name = {label.name: label for label in self.labels}
        
        # Group by category (prefix before colon)
        self._labels_by_category = {}
        for label in self.labels:
            if ":" in label.name:
                category = label.name.split(":", 1)[0]
                if category not in self._labels_by_category:
                    self._labels_by_category[category] = []
                self._labels_by_category[category].append(label)
    
    @field_validator("labels")
    @classmethod
    def validate_no_duplicates(cls, labels: list[Label]) -> list[Label]:
        """Ensure no duplicate label names"""
        names = [label.name for label in labels]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            raise ValueError(
                f"Duplicate label names found: {set(duplicates)}"
            )
        return labels
    
    def get_label(self, name: str) -> Label | None:
        """
        Get label by exact name match.
        
        Args:
            name: Label name (case-sensitive)
            
        Returns:
            Label if found, None otherwise
        """
        return self._labels_by_name.get(name)
    
    def get_labels_by_category(self, category: str) -> list[Label]:
        """
        Get all labels in a category.
        
        Args:
            category: Category name (e.g., 'type', 'priority')
            
        Returns:
            List of labels (empty if category not found)
        """
        return self._labels_by_category.get(category, [])
    
    def validate_label_name(self, name: str) -> tuple[bool, str]:
        """
        Validate label name against pattern rules.
        
        Args:
            name: Label name to validate
            
        Returns:
            (is_valid, error_message) tuple
            
        Rules:
            1. Must match category:value pattern (e.g., 'type:feature')
            2. OR be in freeform_exceptions list
            3. Category must be: type, priority, status, phase, scope, component, effort, parent
            4. Value must be lowercase alphanumeric with hyphens
        """
        import re
        
        # Check freeform exceptions first
        if name in self.freeform_exceptions:
            return (True, "")
        
        # Pattern validation
        pattern = r'^(type|priority|status|phase|scope|component|effort|parent):[a-z0-9-]+$'
        if not re.match(pattern, name):
            return (
                False,
                f"Label '{name}' does not match required pattern. "
                f"Expected format: 'category:value' where category is one of "
                f"[type, priority, status, phase, scope, component, effort, parent] "
                f"and value is lowercase alphanumeric with hyphens. "
                f"Freeform labels must be added to freeform_exceptions list."
            )
        
        return (True, "")
    
    def label_exists(self, name: str) -> bool:
        """Check if label is defined in labels.yaml"""
        return name in self._labels_by_name
    
    def sync_to_github(
        self,
        github_adapter: Any,
        dry_run: bool = False
    ) -> dict[str, list[str]]:
        """
        Sync labels to GitHub repository.
        
        Args:
            github_adapter: GitHubAdapter instance
            dry_run: If True, only report changes without applying
            
        Returns:
            {
                "created": ["type:new-label"],
                "updated": ["type:changed-color"],
                "skipped": ["type:unchanged"],
                "errors": ["type:failed: Error message"]
            }
        """
        result = {
            "created": [],
            "updated": [],
            "skipped": [],
            "errors": []
        }
        
        # Get existing GitHub labels
        try:
            existing_labels = github_adapter.list_labels()
            existing_by_name = {label["name"]: label for label in existing_labels}
        except Exception as e:
            result["errors"].append(f"Failed to fetch labels: {e}")
            return result
        
        # Process each label from YAML
        for label in self.labels:
            try:
                if label.name not in existing_by_name:
                    # Create new label
                    if not dry_run:
                        github_adapter.create_label(
                            name=label.name,
                            color=label.color,
                            description=label.description
                        )
                    result["created"].append(label.name)
                else:
                    # Check if update needed
                    existing = existing_by_name[label.name]
                    needs_update = (
                        existing["color"] != label.color or
                        existing.get("description", "") != label.description
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

**Design Decisions:**
- **Singleton pattern**: Prevents multiple loads, matches WorkflowConfig
- **Pydantic validation**: Automatic field validation, clear error messages
- **Lookup caches**: `_labels_by_name` and `_labels_by_category` for O(1) access
- **Immutable after load**: Labels list not modifiable, only reload via new load()
- **Validate on load**: All validation happens at load time, not at query time
- **Sync dry-run**: Preview changes before applying

---

## 2. Data Models

### 2.1 labels.yaml Schema

**Location:** `.st3/labels.yaml`

```yaml
version: "1.0"

freeform_exceptions:
  - "good first issue"
  - "help wanted"
  - "wontfix"
  - "duplicate"
  - "invalid"

labels:
  # Type labels
  - name: "type:feature"
    color: "1D76DB"
    description: "New feature or enhancement"
  
  - name: "type:bug"
    color: "D73A4A"
    description: "Something isn't working"
  
  - name: "type:refactor"
    color: "0E8A16"
    description: "Code improvement without behavior change"
  
  # Priority labels
  - name: "priority:critical"
    color: "B60205"
    description: "Must be fixed immediately"
  
  - name: "priority:high"
    color: "D93F0B"
    description: "Should be addressed soon"
  
  - name: "priority:medium"
    color: "FBCA04"
    description: "Normal priority"
  
  - name: "priority:low"
    color: "BFD4F2"
    description: "Low priority, nice to have"
  
  # Phase labels (13 total)
  - name: "phase:discovery"
    color: "0E8A16"
    description: "Discovery phase"
  
  # ... (remaining 50+ labels)
```

**Schema Rules:**
1. `version` (required): Schema version string
2. `freeform_exceptions` (optional): List of non-pattern labels
3. `labels` (required): List of label objects
4. Each label: `name` (required), `color` (required), `description` (optional)

### 2.2 Validation Error Types

```python
# Custom exceptions for clear error handling
class LabelConfigError(Exception):
    """Base exception for label configuration errors"""
    pass

class LabelNotFoundError(LabelConfigError):
    """Label not defined in labels.yaml"""
    pass

class InvalidLabelNameError(LabelConfigError):
    """Label name doesn't match pattern"""
    pass

class InvalidColorFormatError(LabelConfigError):
    """Color format invalid (not 6-char hex)"""
    pass

class DuplicateLabelError(LabelConfigError):
    """Duplicate label name in labels.yaml"""
    pass
```

---

## 3. Validation Logic

### 3.1 Color Validation

**Implementation in Label.__post_init__:**

```python
def _is_valid_color(color: str) -> bool:
    """
    Validate hex color format.
    
    Rules:
    - Exactly 6 characters
    - Only hex digits (0-9, a-f, A-F)
    - NO # prefix
    
    Examples:
        "ff0000" ✅
        "FF0000" ✅
        "abc123" ✅
        "#ff0000" ❌ (has # prefix)
        "ff00" ❌ (too short)
        "gggggg" ❌ (invalid hex)
    """
    import re
    return bool(re.match(r'^[0-9a-fA-F]{6}$', color))
```

**Error Message:**
```
Invalid color format 'ff00'. Expected 6-character hex WITHOUT # prefix (e.g., 'ff0000')
```

### 3.2 Name Validation

**Implementation in LabelConfig.validate_label_name:**

```python
def validate_label_name(self, name: str) -> tuple[bool, str]:
    """
    Validate label name pattern.
    
    Allowed formats:
    1. category:value (e.g., 'type:feature')
       - category: type, priority, status, phase, scope, component, effort, parent
       - value: lowercase alphanumeric with hyphens
    
    2. Freeform exceptions (e.g., 'good first issue')
       - Must be in freeform_exceptions list
    
    Returns:
        (is_valid, error_message)
    """
    import re
    
    # Check freeform first
    if name in self.freeform_exceptions:
        return (True, "")
    
    # Pattern check
    pattern = r'^(type|priority|status|phase|scope|component|effort|parent):[a-z0-9-]+$'
    if not re.match(pattern, name):
        return (False, f"Label '{name}' does not match required pattern...")
    
    return (True, "")
```

### 3.3 Existence Check

**Implementation in LabelConfig.label_exists:**

```python
def label_exists(self, name: str) -> bool:
    """
    Check if label is defined in labels.yaml.
    Used by tools to validate before applying labels.
    
    O(1) lookup via _labels_by_name cache.
    """
    return name in self._labels_by_name
```

---

## 4. GitHub Sync Mechanism

### 4.1 Sync Algorithm

**Implementation in LabelConfig.sync_to_github:**

```python
def sync_to_github(self, github_adapter, dry_run=False):
    """
    Three-way sync algorithm:
    1. Fetch existing GitHub labels
    2. Compare with labels.yaml
    3. Create missing, update changed, skip unchanged
    
    Returns diff report for user review.
    """
    # Step 1: Fetch existing
    existing = github_adapter.list_labels()  # [{"name": "...", "color": "...", ...}]
    existing_by_name = {label["name"]: label for label in existing}
    
    # Step 2: Compare each YAML label
    for label in self.labels:
        if label.name not in existing_by_name:
            # CREATE
            if not dry_run:
                github_adapter.create_label(label.name, label.color, label.description)
            result["created"].append(label.name)
        else:
            # UPDATE or SKIP
            existing_label = existing_by_name[label.name]
            if needs_update(label, existing_label):
                if not dry_run:
                    github_adapter.update_label(label.name, label.color, label.description)
                result["updated"].append(label.name)
            else:
                result["skipped"].append(label.name)
    
    return result

def needs_update(yaml_label: Label, github_label: dict) -> bool:
    """Check if GitHub label needs update"""
    return (
        yaml_label.color != github_label["color"] or
        yaml_label.description != github_label.get("description", "")
    )
```

### 4.2 Diff Report Format

**Output structure:**

```python
{
    "created": ["type:new-feature"],      # Will be created
    "updated": ["type:bug"],              # Color/description changed
    "skipped": ["priority:high"],         # Already up-to-date
    "errors": ["type:fail: API error"]    # Failed operations
}
```

### 4.3 Dry-Run Mode

**Usage:**

```python
# Preview changes
result = label_config.sync_to_github(github_adapter, dry_run=True)
print(f"Would create: {len(result['created'])} labels")

# Apply changes
result = label_config.sync_to_github(github_adapter, dry_run=False)
```

---

## 5. Error Handling

### 5.1 Load Errors

**Scenario 1: File not found**
```python
try:
    config = LabelConfig.load()
except FileNotFoundError as e:
    # Error: "Label configuration not found: .st3/labels.yaml. Create labels.yaml..."
    # Action: Provide clear path to create file
```

**Scenario 2: Invalid YAML syntax**
```python
try:
    config = LabelConfig.load()
except ValueError as e:
    # Error: "Invalid YAML syntax in .st3/labels.yaml: ..."
    # Action: Show line number and syntax error from PyYAML
```

**Scenario 3: Missing version field**
```python
# Pydantic raises ValidationError
try:
    config = LabelConfig.load()
except pydantic.ValidationError as e:
    # Error: "1 validation error for LabelConfig\nversion\n  field required"
    # Action: Add version field to YAML
```

**Scenario 4: Invalid color format**
```python
# Label.__post_init__ raises ValueError
try:
    config = LabelConfig.load()
except ValueError as e:
    # Error: "Invalid color format '#ff0000'. Expected 6-character hex WITHOUT # prefix..."
    # Action: Remove # prefix from color
```

**Scenario 5: Duplicate labels**
```python
# Pydantic validator raises ValidationError
try:
    config = LabelConfig.load()
except pydantic.ValidationError as e:
    # Error: "Duplicate label names found: {'type:feature'}"
    # Action: Remove duplicate from YAML
```

### 5.2 Query Errors

**get_label() with non-existent name:**
```python
label = config.get_label("nonexistent")
# Returns: None (graceful, caller checks)
```

**get_labels_by_category() with invalid category:**
```python
labels = config.get_labels_by_category("invalid")
# Returns: [] (empty list, graceful)
```

### 5.3 Sync Errors

**GitHub API failures:**
```python
result = config.sync_to_github(github_adapter)
if result["errors"]:
    # Partial success: some labels synced, some failed
    # Each error includes label name and reason
    for error in result["errors"]:
        print(f"Failed: {error}")
```


## 5.4 Startup Validation

**Purpose:** Validate labels.yaml at MCP server startup for early problem detection.

**Implementation in MCP server initialization:**

```python
# mcp_server/__init__.py or similar startup module
import logging
from mcp_server.config.label_config import LabelConfig

logger = logging.getLogger(__name__)

def validate_label_config_on_startup():
    """
    Validate labels.yaml at server startup.
    
    Logs warnings but does NOT block startup.
    Tools will validate at operation time (Level 2).
    """
    try:
        label_config = LabelConfig.load()
        logger.info(f"Loaded labels.yaml: {len(label_config.labels)} labels")
        
        # Optional: Check if GitHub sync needed
        # (This is passive detection, not enforcement)
        # Actual sync enforcement happens via tools (Issue #61)
        
    except FileNotFoundError:
        logger.warning(
            "labels.yaml not found at .st3/labels.yaml. "
            "Label validation will fail until file is created. "
            "Run scaffold tool or create manually."
        )
    except ValueError as e:
        logger.error(
            f"Invalid labels.yaml configuration: {e}. "
            f"Fix configuration before using label tools."
        )
    except Exception as e:
        logger.error(
            f"Unexpected error loading labels.yaml: {e}. "
            f"Label tools may not function correctly."
        )

# Call during server initialization
validate_label_config_on_startup()
```

**Behavior:**

**Success:**
```
[INFO] Loaded labels.yaml: 52 labels
```

**File not found:**
```
[WARNING] labels.yaml not found at .st3/labels.yaml. 
Label validation will fail until file is created.
Run scaffold tool or create manually.
```

**Invalid YAML:**
```
[ERROR] Invalid labels.yaml configuration: Duplicate label names found: {'type:feature'}.
Fix configuration before using label tools.
```

**Key design decisions:**
- ✅ **Non-blocking:** Warnings/errors logged but server starts
- ✅ **Early detection:** Problems found at startup, not at first tool use
- ✅ **Clear guidance:** Error messages explain how to fix
- ✅ **Level 1 only:** Detection, not enforcement (tools enforce at Level 2)

**Testing:**
- Unit test: Call validate function with missing/invalid YAML
- Integration test: Server startup with various config states
- Verify logs contain appropriate messages
---

## 6. Tool Integration

### 6.1 CreateLabelTool Updates

**Location:** `mcp_server/tools/label_tools.py`

**Changes:**

```python
class CreateLabelTool(BaseTool):
    def execute(self, name: str, color: str, description: str = "") -> dict:
        # NEW: Validate name pattern
        label_config = LabelConfig.load()
        is_valid, error_msg = label_config.validate_label_name(name)
        if not is_valid:
            return {"success": False, "error": error_msg}
        
        # NEW: Validate color format (reject # prefix)
        if color.startswith("#"):
            return {
                "success": False,
                "error": f"Color must not include # prefix. Use '{color[1:]}' instead."
            }
        
        # Existing: Create via GitHub API
        github_adapter.create_label(name, color, description)
        return {"success": True, "label": name}
```

### 6.2 AddLabelsTool Updates

**Location:** `mcp_server/tools/issue_tools.py`

**Changes:**

```python
class AddLabelsTool(BaseTool):
    def execute(self, issue_number: int, labels: list[str]) -> dict:
        # NEW: Validate each label exists in labels.yaml
        label_config = LabelConfig.load()
        
        undefined = [label for label in labels if not label_config.label_exists(label)]
        if undefined:
            return {
                "success": False,
                "error": f"Labels not defined in labels.yaml: {undefined}. "
                        f"Add to .st3/labels.yaml or freeform_exceptions list."
            }
        
        # Existing: Add labels via GitHub API
        github_adapter.add_labels(issue_number, labels)
        return {"success": True, "labels": labels}
```

### 6.3 SyncLabelsToGitHubTool (NEW)

**Location:** `mcp_server/tools/label_tools.py`

**Implementation:**

```python
class SyncLabelsToGitHubTool(BaseTool):
    """
    Sync labels from labels.yaml to GitHub repository.
    
    Shows diff preview before applying changes.
    Supports dry-run mode for safety.
    """
    
    name: str = "sync_labels_to_github"
    description: str = "Sync label definitions from labels.yaml to GitHub"
    
    input_schema = {
        "type": "object",
        "properties": {
            "dry_run": {
                "type": "boolean",
                "description": "Preview changes without applying (default: true)",
                "default": True
            }
        }
    }
    
    def execute(self, dry_run: bool = True) -> dict:
        """
        Execute label sync.
        
        Returns:
            {
                "success": true,
                "summary": "Created 5, Updated 3, Skipped 42",
                "details": {
                    "created": [...],
                    "updated": [...],
                    "skipped": [...],
                    "errors": [...]
                },
                "dry_run": true
            }
        """
        label_config = LabelConfig.load()
        github_adapter = self.context.get_adapter("github")
        
        # Run sync
        result = label_config.sync_to_github(github_adapter, dry_run=dry_run)
        
        # Format summary
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

---

## 7. File Structure

### 7.1 New Files

```
.st3/
  labels.yaml              # Label definitions (50+ labels)

mcp_server/
  config/
    label_config.py        # Label + LabelConfig classes
    __init__.py            # Export Label, LabelConfig
  
  tools/
    label_tools.py         # Updated CreateLabelTool + NEW SyncLabelsToGitHubTool
    issue_tools.py         # Updated AddLabelsTool with validation

tests/
  config/
    test_label_config.py   # Unit tests for LabelConfig
  tools/
    test_label_tools.py    # Integration tests for tools
```

### 7.2 Import Structure

```python
# From other modules
from mcp_server.config.label_config import Label, LabelConfig

# Usage in tools
label_config = LabelConfig.load()  # Singleton, safe to call multiple times
if label_config.label_exists("type:feature"):
    # ...
```

### 7.3 Configuration Loading

**Lazy loading pattern (like WorkflowConfig):**

```python
# First call: loads from disk
config = LabelConfig.load()  # Reads .st3/labels.yaml

# Subsequent calls: returns cached instance
config2 = LabelConfig.load()  # Returns same instance
assert config is config2  # True
```

---

## 8. Migration Path

### 8.1 Step 1: Create labels.yaml

**Action:** Create `.st3/labels.yaml` with all 50+ current labels

**Validation:**
- All existing GitHub labels included
- Color format correct (no # prefix)
- No duplicates
- Version field present

### 8.2 Step 2: Deploy LabelConfig

**Action:** Merge `label_config.py` to codebase

**Validation:**
- Unit tests pass (100% coverage)
- Can load labels.yaml successfully
- Queries return correct results

### 8.3 Step 3: Update Tools (Warning Mode)

**Action:** Add validation to CreateLabelTool and AddLabelsTool

**Behavior:**
- Tools warn if label not in YAML
- Tools still execute (don't block)
- Log warnings for review

### 8.4 Step 4: Sync to GitHub

**Action:** Run `SyncLabelsToGitHubTool` with dry_run=True

**Validation:**
- Review diff report
- Verify no unwanted changes
- Run with dry_run=False to apply

### 8.5 Step 5: Enable Strict Mode

**Action:** Change tools to reject undefined labels

**Behavior:**
- CreateLabelTool rejects invalid names
- AddLabelsTool rejects undefined labels
- Users must update labels.yaml first

---

## 9. Testing Strategy (Detailed)

### 9.1 Unit Tests for Label

```python
def test_label_valid_color():
    """Valid 6-char hex colors"""
    Label("type:test", "ff0000")  # lowercase
    Label("type:test", "FF0000")  # uppercase
    Label("type:test", "AbC123")  # mixed

def test_label_invalid_color():
    """Reject invalid colors"""
    with pytest.raises(ValueError, match="Invalid color format"):
        Label("type:test", "#ff0000")  # has # prefix
    
    with pytest.raises(ValueError, match="Invalid color format"):
        Label("type:test", "ff00")  # too short
    
    with pytest.raises(ValueError, match="Invalid color format"):
        Label("type:test", "gggggg")  # invalid hex
```

### 9.2 Unit Tests for LabelConfig

```python
def test_load_valid_yaml(tmp_path):
    """Load valid labels.yaml"""
    yaml_content = """
version: "1.0"
labels:
  - name: "type:test"
    color: "ff0000"
    description: "Test label"
"""
    yaml_file = tmp_path / "labels.yaml"
    yaml_file.write_text(yaml_content)
    
    config = LabelConfig.load(yaml_file)
    assert config.version == "1.0"
    assert len(config.labels) == 1
    assert config.get_label("type:test").color == "ff0000"

def test_load_duplicate_names(tmp_path):
    """Reject duplicate label names"""
    yaml_content = """
version: "1.0"
labels:
  - name: "type:test"
    color: "ff0000"
  - name: "type:test"
    color: "00ff00"
"""
    yaml_file = tmp_path / "labels.yaml"
    yaml_file.write_text(yaml_content)
    
    with pytest.raises(ValueError, match="Duplicate label names"):
        LabelConfig.load(yaml_file)

def test_validate_label_name_valid():
    """Valid label names pass"""
    config = LabelConfig(version="1.0", labels=[])
    
    assert config.validate_label_name("type:feature")[0] is True
    assert config.validate_label_name("priority:high")[0] is True

def test_validate_label_name_invalid():
    """Invalid patterns fail"""
    config = LabelConfig(version="1.0", labels=[])
    
    is_valid, error = config.validate_label_name("invalid")
    assert is_valid is False
    assert "does not match required pattern" in error

def test_get_labels_by_category():
    """Query labels by category"""
    labels = [
        Label("type:feature", "ff0000"),
        Label("type:bug", "00ff00"),
        Label("priority:high", "0000ff")
    ]
    config = LabelConfig(version="1.0", labels=labels)
    config._build_caches()
    
    type_labels = config.get_labels_by_category("type")
    assert len(type_labels) == 2
    assert all(label.name.startswith("type:") for label in type_labels)
```

### 9.3 Integration Tests for sync_to_github

```python
def test_sync_create_new_labels(mock_github):
    """Create labels not in GitHub"""
    # Mock GitHub has no labels
    mock_github.list_labels.return_value = []
    
    labels = [Label("type:new", "ff0000")]
    config = LabelConfig(version="1.0", labels=labels)
    
    result = config.sync_to_github(mock_github, dry_run=False)
    
    assert "type:new" in result["created"]
    mock_github.create_label.assert_called_once_with(
        name="type:new",
        color="ff0000",
        description=""
    )

def test_sync_update_changed_labels(mock_github):
    """Update labels with changed colors"""
    # Mock GitHub has label with different color
    mock_github.list_labels.return_value = [
        {"name": "type:feature", "color": "old_color", "description": ""}
    ]
    
    labels = [Label("type:feature", "new_color")]
    config = LabelConfig(version="1.0", labels=labels)
    
    result = config.sync_to_github(mock_github, dry_run=False)
    
    assert "type:feature" in result["updated"]
    mock_github.update_label.assert_called_once_with(
        name="type:feature",
        color="new_color",
        description=""
    )

def test_sync_dry_run(mock_github):
    """Dry-run doesn't modify GitHub"""
    mock_github.list_labels.return_value = []
    
    labels = [Label("type:new", "ff0000")]
    config = LabelConfig(version="1.0", labels=labels)
    
    result = config.sync_to_github(mock_github, dry_run=True)
    
    assert "type:new" in result["created"]
    mock_github.create_label.assert_not_called()  # Not called in dry-run
```

### 9.4 Integration Tests for Tools

```python
def test_create_label_tool_validates_name():
    """CreateLabelTool validates name pattern"""
    tool = CreateLabelTool(context)
    
    result = tool.execute(name="invalid", color="ff0000")
    
    assert result["success"] is False
    assert "does not match required pattern" in result["error"]

def test_create_label_tool_rejects_hash_prefix():
    """CreateLabelTool rejects # prefix"""
    tool = CreateLabelTool(context)
    
    result = tool.execute(name="type:test", color="#ff0000")
    
    assert result["success"] is False
    assert "must not include # prefix" in result["error"]

def test_add_labels_tool_validates_existence():
    """AddLabelsTool validates labels exist"""
    tool = AddLabelsTool(context)
    
    result = tool.execute(issue_number=1, labels=["undefined:label"])
    
    assert result["success"] is False
    assert "not defined in labels.yaml" in result["error"]
```

---

## 10. Performance Considerations

### 10.1 Singleton Pattern

**Benefit:** Load YAML once per process
- First LabelConfig.load(): ~10ms (YAML parse + validation)
- Subsequent calls: ~0.001ms (return cached instance)

### 10.2 Lookup Caches

**Benefit:** O(1) label queries
- `_labels_by_name`: Direct dict lookup
- `_labels_by_category`: Pre-grouped by category prefix

### 10.3 Immutable Labels

**Benefit:** Thread-safe, no defensive copying
- `@dataclass(frozen=True)` prevents modification
- Safe to share Label instances across threads

---

## 11. Security Considerations

### 11.1 YAML Injection

**Mitigation:** Use `yaml.safe_load()` not `yaml.load()`
- Prevents arbitrary code execution
- Only loads basic Python types

### 11.2 Color Format Validation

**Mitigation:** Strict regex validation
- Reject # prefix (prevents confusion)
- Only allow hex characters (prevents injection)

### 11.3 GitHub API Rate Limits

**Mitigation:** sync_to_github batches operations
- GitHub API: 5000 requests/hour for authenticated
- Sync 50 labels: ~50 requests (well under limit)

---

## 12. Open Questions

**Q: Should sync_to_github delete labels from GitHub not in YAML?**
A: No, for safety. Labels may be manually created for ad-hoc use. Only create/update from YAML.

**Q: Should LabelConfig support hot-reload?**
A: No, for simplicity. Reload requires process restart (like WorkflowConfig).

**Q: Should freeform_exceptions be validated?**
A: Yes, at load time. Check that exceptions don't match category:value pattern (would be redundant).

---

## 13. References

- **Research:** docs/development/issue51/research.md
- **Planning:** docs/development/issue51/planning.md
- **WorkflowConfig:** mcp_server/config/workflow_config.py (pattern reference)
- **GitHub Labels API:** https://docs.github.com/en/rest/issues/labels
- **PyGithub Docs:** https://pygithub.readthedocs.io/
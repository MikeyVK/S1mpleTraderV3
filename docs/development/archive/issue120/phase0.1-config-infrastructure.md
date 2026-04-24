# Phase 0.1: Config Infrastructure - Design Document

**Issue:** #120  
**Phase:** 0.1/0.4 (Config Infrastructure)  
**Status:** Design  
**Created:** 2026-01-20  
**Estimated Time:** 2-3 hours  
**Dependencies:** Phase 0.0 complete ✅

---

## Objective

Create a configuration system that defines:
1. **Comment syntaxes** for 4 file types (Python, TypeScript, Markdown, Jinja2)
2. **Metadata field formats** with regex validation (template, version, created, updated, path)
3. **Pydantic models** for type-safe config loading

This config will be consumed by Phase 0.2 (Metadata Parser) and Phase 0.3 (ArtifactManager).

---

## Config File Design

### Location & Format

**File:** `.st3/scaffold_metadata.yaml`  
**Format:** YAML (human-readable, Git-friendly)  
**Rationale:** 
- Already using `.st3/` for project configs
- YAML supports comments for documentation
- Easy to extend with new syntaxes/fields

### Structure Overview

```yaml
# .st3/scaffold_metadata.yaml
# Defines how to inject and parse scaffold metadata

comment_patterns:
  # Pattern ID → regex pattern for matching
  hash:
    pattern: "^#\\s+SCAFFOLD:\\s+(.+)$"
    extensions: [".py", ".yaml", ".sh"]
  
  double_slash:
    pattern: "^//\\s+SCAFFOLD:\\s+(.+)$"
    extensions: [".ts", ".js", ".java", ".cs"]
  
  html_comment:
    pattern: "^<!--\\s+SCAFFOLD:\\s+(.+)\\s+-->$"
    extensions: [".md", ".html", ".xml"]
  
  jinja_comment:
    pattern: "^\\{#\\s+SCAFFOLD:\\s+(.+)\\s+#\\}$"
    extensions: [".jinja2", ".j2"]

metadata_fields:
  # Field name → validation pattern + required/optional
  template:
    pattern: "^[a-z0-9_-]+$"
    required: true
    description: "Artifact template ID from artifacts.yaml"
  
  version:
    pattern: "^\\d+\\.\\d+$"
    required: true
    description: "Template version (semver major.minor)"
  
  created:
    pattern: "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$"
    required: true
    description: "UTC timestamp when scaffolded (ISO 8601)"
  
  updated:
    pattern: "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}Z$"
    required: false
    description: "UTC timestamp of last template update (optional)"
  
  path:
    pattern: "^[a-zA-Z0-9_/\\-\\.]+$"
    required: false
    description: "Relative path from workspace root (optional for ephemeral artifacts)"
```

### Design Decisions

**1. Pattern-based approach:**
- ✅ Extensible (add new syntaxes without code changes)
- ✅ Maintainable (single source of truth)
- ❌ Regex complexity (mitigated by tests)

**2. Extension-to-pattern mapping:**
- Avoids ambiguity (`.py` always uses `hash` pattern)
- Multiple extensions can share same pattern
- Parser filters patterns by file extension

**3. Field-level validation:**
- Each field has its own regex (no composite regex)
- Runtime validation via Pydantic
- Clear error messages ("version must match `\d+.\d+`")

**4. Required vs optional:**
- `template`, `version`, `created` → ALWAYS required
- `updated` → Optional (only after template changes)
- `path` → Optional (ephemeral artifacts like git commits)

---

## Pydantic Models Design

### Model Hierarchy

```
ScaffoldMetadataConfig (root)
├── comment_patterns: Dict[str, CommentPattern]
└── metadata_fields: Dict[str, MetadataField]
```

### Model Definitions

#### 1. CommentPattern Model

**Purpose:** Validate comment syntax patterns

```python
from pydantic import BaseModel, Field, field_validator
from typing import List
import re

class CommentPattern(BaseModel):
    """Single comment pattern (e.g., hash, double-slash)."""
    
    pattern: str = Field(..., description="Regex pattern to match comment line")
    extensions: List[str] = Field(..., description="File extensions using this pattern")
    
    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Ensure pattern is valid regex."""
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
        return v
    
    @field_validator("extensions")
    @classmethod
    def validate_extensions(cls, v: List[str]) -> List[str]:
        """Ensure extensions start with dot."""
        for ext in v:
            if not ext.startswith("."):
                raise ValueError(f"Extension must start with '.': {ext}")
        return v
    
    def matches(self, line: str) -> bool:
        """Check if line matches this pattern."""
        return bool(re.match(self.pattern, line))
    
    def extract_metadata(self, line: str) -> str:
        """Extract metadata string from comment line."""
        match = re.match(self.pattern, line)
        if not match:
            raise ValueError(f"Line doesn't match pattern: {line}")
        return match.group(1).strip()
```

**Rationale:**
- Self-contained validation (regex compile test)
- Helper methods (`matches()`, `extract_metadata()`) for parser
- Clear error messages

#### 2. MetadataField Model

**Purpose:** Define + validate individual metadata fields

```python
class MetadataField(BaseModel):
    """Single metadata field (e.g., template, version, created)."""
    
    pattern: str = Field(..., description="Regex pattern for field value")
    required: bool = Field(..., description="Whether field is mandatory")
    description: str = Field(..., description="Human-readable explanation")
    
    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Ensure pattern is valid regex."""
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")
        return v
    
    def validate_value(self, value: str) -> bool:
        """Check if value matches field pattern."""
        return bool(re.match(self.pattern, value))
    
    def format_error(self, value: str) -> str:
        """Generate helpful error message."""
        return (
            f"Invalid value '{value}' for field.\n"
            f"Expected format: {self.description}\n"
            f"Pattern: {self.pattern}"
        )
```

**Rationale:**
- Runtime validation method (`validate_value()`)
- Error formatting for parser
- Description field for introspection (future schema tool)

#### 3. ScaffoldMetadataConfig Model

**Purpose:** Root config with file loading

```python
from pathlib import Path
import yaml

class ScaffoldMetadataConfig(BaseModel):
    """Root config for scaffold metadata system."""
    
    comment_patterns: Dict[str, CommentPattern] = Field(
        ..., description="Comment syntax patterns by ID"
    )
    metadata_fields: Dict[str, MetadataField] = Field(
        ..., description="Metadata field definitions"
    )
    
    @classmethod
    def from_file(cls, path: Path = Path(".st3/scaffold_metadata.yaml")) -> "ScaffoldMetadataConfig":
        """Load config from YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        try:
            with path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {path}: {e}")
        
        return cls.model_validate(data)
    
    def get_pattern_for_extension(self, extension: str) -> CommentPattern | None:
        """Find pattern matching file extension."""
        for pattern in self.comment_patterns.values():
            if extension in pattern.extensions:
                return pattern
        return None
    
    def validate_metadata(self, metadata: Dict[str, str]) -> List[str]:
        """Validate all fields, return list of errors."""
        errors = []
        
        # Check required fields present
        for field_name, field_def in self.metadata_fields.items():
            if field_def.required and field_name not in metadata:
                errors.append(f"Missing required field: {field_name}")
        
        # Validate field values
        for field_name, field_value in metadata.items():
            if field_name not in self.metadata_fields:
                errors.append(f"Unknown field: {field_name}")
                continue
            
            field_def = self.metadata_fields[field_name]
            if not field_def.validate_value(field_value):
                errors.append(field_def.format_error(field_value))
        
        return errors
```

**Rationale:**
- `from_file()` classmethod → standard Pydantic pattern
- Helper methods for parser (`get_pattern_for_extension()`)
- Validation method returns ALL errors (not just first)

---

## TDD Test Design

### Test File Structure

**Location:** `tests/unit/config/test_scaffold_metadata_config.py`

### Test Categories

#### 1. Config Loading Tests (RED → GREEN)

```python
def test_load_config_from_file():
    """Config loads successfully from .st3/scaffold_metadata.yaml"""
    config = ScaffoldMetadataConfig.from_file()
    
    assert len(config.comment_patterns) == 4  # hash, double-slash, html, jinja
    assert len(config.metadata_fields) == 5   # template, version, created, updated, path

def test_load_config_missing_file():
    """Missing config file raises FileNotFoundError"""
    with pytest.raises(FileNotFoundError):
        ScaffoldMetadataConfig.from_file(Path("nonexistent.yaml"))

def test_load_config_invalid_yaml():
    """Invalid YAML raises ValueError"""
    # Create temp file with malformed YAML
    # ...
    with pytest.raises(ValueError, match="Invalid YAML"):
        ScaffoldMetadataConfig.from_file(temp_path)
```

#### 2. Comment Pattern Tests (RED → GREEN)

```python
def test_hash_pattern_matches_python():
    """Hash pattern matches Python comment"""
    config = ScaffoldMetadataConfig.from_file()
    pattern = config.comment_patterns["hash"]
    
    assert pattern.matches("# SCAFFOLD: template=dto version=1.0 created=2026-01-20T14:00:00Z")
    assert not pattern.matches("## Not a scaffold comment")

def test_pattern_extension_mapping():
    """Extensions correctly map to patterns"""
    config = ScaffoldMetadataConfig.from_file()
    
    assert config.get_pattern_for_extension(".py") == config.comment_patterns["hash"]
    assert config.get_pattern_for_extension(".ts") == config.comment_patterns["double_slash"]
    assert config.get_pattern_for_extension(".md") == config.comment_patterns["html_comment"]
    assert config.get_pattern_for_extension(".jinja2") == config.comment_patterns["jinja_comment"]
    assert config.get_pattern_for_extension(".unknown") is None

def test_extract_metadata_from_comment():
    """Extract metadata string from comment line"""
    config = ScaffoldMetadataConfig.from_file()
    pattern = config.comment_patterns["hash"]
    
    line = "# SCAFFOLD: template=dto version=1.0 created=2026-01-20T14:00:00Z"
    metadata_str = pattern.extract_metadata(line)
    
    assert metadata_str == "template=dto version=1.0 created=2026-01-20T14:00:00Z"
```

#### 3. Field Validation Tests (RED → GREEN)

```python
def test_validate_template_field():
    """Template field validates correctly"""
    config = ScaffoldMetadataConfig.from_file()
    field = config.metadata_fields["template"]
    
    assert field.validate_value("dto")
    assert field.validate_value("commit_message")
    assert not field.validate_value("Invalid Template")  # Uppercase not allowed
    assert not field.validate_value("template@123")      # Special chars not allowed

def test_validate_version_field():
    """Version field validates semver major.minor"""
    config = ScaffoldMetadataConfig.from_file()
    field = config.metadata_fields["version"]
    
    assert field.validate_value("1.0")
    assert field.validate_value("2.5")
    assert not field.validate_value("1.0.0")  # Patch not allowed
    assert not field.validate_value("v1.0")   # Prefix not allowed

def test_validate_timestamp_field():
    """Timestamp fields validate ISO 8601 UTC"""
    config = ScaffoldMetadataConfig.from_file()
    field = config.metadata_fields["created"]
    
    assert field.validate_value("2026-01-20T14:35:42Z")
    assert not field.validate_value("2026-01-20 14:35:42")  # Missing T
    assert not field.validate_value("2026-01-20T14:35:42")  # Missing Z

def test_validate_path_field():
    """Path field validates relative paths"""
    config = ScaffoldMetadataConfig.from_file()
    field = config.metadata_fields["path"]
    
    assert field.validate_value("mcp_server/dto/user_dto.py")
    assert field.validate_value("docs/architecture/design.md")
    assert not field.validate_value("/absolute/path")      # Absolute not allowed
    assert not field.validate_value("path with spaces")    # Spaces not allowed
```

#### 4. Full Metadata Validation Tests (RED → GREEN)

```python
def test_validate_complete_metadata():
    """Complete metadata with all required fields passes"""
    config = ScaffoldMetadataConfig.from_file()
    metadata = {
        "template": "dto",
        "version": "1.0",
        "created": "2026-01-20T14:00:00Z",
        "path": "mcp_server/dto/user_dto.py"
    }
    
    errors = config.validate_metadata(metadata)
    assert errors == []

def test_validate_metadata_missing_required():
    """Missing required field returns error"""
    config = ScaffoldMetadataConfig.from_file()
    metadata = {
        "template": "dto",
        # Missing: version, created
    }
    
    errors = config.validate_metadata(metadata)
    assert "Missing required field: version" in errors
    assert "Missing required field: created" in errors

def test_validate_metadata_invalid_format():
    """Invalid field format returns helpful error"""
    config = ScaffoldMetadataConfig.from_file()
    metadata = {
        "template": "dto",
        "version": "invalid",  # Should be \d+.\d+
        "created": "2026-01-20T14:00:00Z"
    }
    
    errors = config.validate_metadata(metadata)
    assert len(errors) == 1
    assert "version" in errors[0]
    assert "invalid" in errors[0]

def test_validate_metadata_optional_path():
    """Ephemeral artifacts without path are valid"""
    config = ScaffoldMetadataConfig.from_file()
    metadata = {
        "template": "commit_message",
        "version": "1.0",
        "created": "2026-01-20T14:00:00Z",
        # No path (ephemeral artifact)
    }
    
    errors = config.validate_metadata(metadata)
    assert errors == []  # Path is optional
```

---

## Implementation Checklist

### Phase 0.1 Tasks (TDD Order)

**Step 1: RED (30 min)**
- [ ] Create `tests/unit/config/test_scaffold_metadata_config.py`
- [ ] Write all test skeletons (12 tests total)
- [ ] Run tests → ALL FAIL (no implementation yet)
- [ ] Commit: `test(phase-0.1): RED - Add config infrastructure tests`

**Step 2: Config File (30 min)**
- [ ] Create `.st3/scaffold_metadata.yaml`
- [ ] Define 4 comment patterns (hash, double-slash, html, jinja)
- [ ] Define 5 metadata fields (template, version, created, updated, path)
- [ ] Add inline documentation
- [ ] Commit: `feat(phase-0.1): Add scaffold metadata config file`

**Step 3: GREEN (45 min)**
- [ ] Create `mcp_server/config/scaffold_metadata_config.py`
- [ ] Implement `CommentPattern` model
- [ ] Implement `MetadataField` model
- [ ] Implement `ScaffoldMetadataConfig` model
- [ ] Run tests → ALL PASS
- [ ] Commit: `feat(phase-0.1): GREEN - Implement config Pydantic models`

**Step 4: REFACTOR (30 min)**
- [ ] Extract validation helpers (if duplicated)
- [ ] Optimize YAML loading (caching if needed)
- [ ] Add comprehensive docstrings
- [ ] Improve error messages
- [ ] Run tests → STILL ALL PASS
- [ ] Commit: `refactor(phase-0.1): Optimize config loading and error messages`

**Total Time:** ~2-3 hours

---

## Success Criteria

✅ **All tests pass (GREEN)**  
✅ **Config loads from `.st3/scaffold_metadata.yaml`**  
✅ **Field validation works for all 5 fields**  
✅ **Invalid configs raise clear ValidationErrors**  
✅ **Code coverage >90% for config module**

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Regex complexity | Hard to debug pattern failures | Test each pattern separately, use regex101.com |
| YAML syntax errors | Config won't load | IDE validation, schema validation tests |
| Extension ambiguity | Wrong pattern selected | Test all extensions, document in config |
| Performance overhead | Slow config loading | Cache config singleton, load once at startup |

---

## Next Phase

**Phase 0.2: Metadata Parser** (depends on this phase)
- Will consume `ScaffoldMetadataConfig` for pattern matching
- Uses `validate_metadata()` for runtime validation
- Estimated: 3-4 hours (next TDD cycle)

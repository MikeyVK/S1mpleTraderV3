# Phase 0: Scaffold Metadata Implementation - S1mpleTraderV3

<!--
GENERATED DOCUMENT
Template: generic.md.jinja2
Type: Generic
-->

<!-- ═══════════════════════════════════════════════════════════════════════════
     HEADER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

**Status:** Draft
**Version:** 0.1
**Last Updated:** 2026-01-20
**Issue:** #120
**Phase:** Research


---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTEXT SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Purpose

Design and implement a config-driven metadata system for scaffolded artifacts that:
1. Injects metadata into scaffolded artifacts (first-line comment)
2. Supports multiple comment syntaxes via config
3. Enables discovery for content-aware editing (Issue #121)
4. Maintains template-driven approach

## Scope

**In Scope:**
- Config file for comment patterns (`.st3/scaffold_metadata.yaml`)
- Config loader with Pydantic models (`mcp_server/config/scaffold_metadata_config.py`)
- Metadata parser with pattern matching (`mcp_server/scaffolding/metadata.py`)
- Metadata injection in ArtifactManager
- Template context enrichment (template_id, version, date, path)
- Unit tests for parser and config loader

**Out of Scope:**
- Checksum calculation (future phase)
- Template file updates (separate task after research)
- Migration of existing files (future phase)
- Schema validation error messages (Phase 1 of Issue #120)
- Discovery tool implementation (Issue #121)

## Prerequisites

- Issue #120 created and branch initialized
- Python environment configured
- Understanding of Jinja2 templates and artifacts.yaml registry

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTENT SECTION
     ═══════════════════════════════════════════════════════════════════════════ -->

## Overview

Current scaffolded artifacts lack metadata for template identification and version tracking. This prevents:
- Content-aware editing (blocks Issue #121)
- Template version compatibility detection
- Graceful degradation for manually edited files
- Template migration tracking

This research document defines Phase 0: implementing a config-driven metadata system that injects template information into scaffolded artifacts via first-line comments.

## Problem Statement

**Current State:**
- Scaffolded files have no metadata
- Cannot detect which template was used
- Cannot validate template version compatibility
- Manual edits break template awareness
- Discovery tool (Issue #121) cannot identify scaffolded files

**Example - Current DTO:**
```python
from pydantic import BaseModel, Field

class UserDTO(BaseModel):
    """User data transfer object."""
    # No way to know this came from dto template v2.0
```

**Desired State:**
```python
# SCAFFOLD: template=dto version=2.0 created=2026-01-20T14:32:15Z path=src/dto/user_dto.py
from pydantic import BaseModel, Field

class UserDTO(BaseModel):
    """User data transfer object."""
```

**After Migration:**
```python
# SCAFFOLD: template=dto version=2.1 created=2026-01-20T14:32:15Z updated=2026-01-21T09:15:00Z path=src/dto/user_dto.py
from pydantic import BaseModel, Field

class UserDTO(BaseModel):
    """User data transfer object (migrated to v2.1)."""
```

**Git Commit (no path):**
```bash
# SCAFFOLD: template=commit-message version=1.0 created=2026-01-20T14:35:42Z
feat: Implement user authentication
```

## Design Decisions

### 1. Config-Driven Pattern Matching

**Rationale:** Config before code principle - patterns can be added without code changes.

**Implementation:** `.st3/scaffold_metadata.yaml`
```yaml
version: "1.0"

comment_patterns:
  - name: "hash"
    description: "Hash comment (Python, YAML, Shell, Ruby, etc.)"
    pattern: '^# SCAFFOLD: (.+)$'
    extensions: [".py", ".yaml", ".yml", ".sh", ".rb"]
    
  - name: "double-slash"
    description: "Double-slash comment (TypeScript, JavaScript, Java, C#, C++)"
    pattern: '^// SCAFFOLD: (.+)$'
    extensions: [".ts", ".js", ".java", ".cs", ".cpp", ".c", ".go"]
    
  - name: "html-comment"
    description: "HTML-style comment (Markdown, HTML, XML)"
    pattern: '^<!-- SCAFFOLD: (.+) -->$'
    extensions: [".md", ".html", ".xml"]
    
  - name: "jinja-comment"
    description: "Jinja2 comment (for templates)"
    pattern: '^{# SCAFFOLD: (.+) #}$'
    extensions: [".jinja2", ".j2"]

metadata_fields:
  - name: "template"
    required: true
    description: "Artifact type ID from artifacts.yaml"
    format: "^[a-z0-9-]+$"
    
  - name: "version"
    required: true
    description: "Template version from artifacts.yaml"
    format: "^\d+\.\d+(\.\d+)?$"
    
  - name: "created"
    required: true
    description: "Scaffold creation timestamp (ISO 8601 UTC)"
    format: "^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
    
  - name: "updated"
    required: false
    description: "Last migration/update timestamp (ISO 8601 UTC)"
    format: "^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
    
  - name: "path"
    required: false
    description: "Relative workspace path with extension (file artifacts only, determined by artifacts.yaml)"
    format: "^.+\..+$"
```

### 2. Template-Driven Syntax

**Rationale:** Templates know their target language and appropriate comment syntax.

**Examples:**

**Python DTO:**
```jinja
{# components/dto.py.jinja2 #}
# SCAFFOLD: template={{ template_id }} version={{ template_version }} created={{ scaffold_created }} path={{ output_path }}
from pydantic import BaseModel, Field
```

**TypeScript Interface:**
```jinja
{# components/interface.ts.jinja2 #}
// SCAFFOLD: template={{ template_id }} version={{ template_version }} created={{ scaffold_created }} path={{ output_path }}
export interface {{ name }} {
```

**Markdown Document:**
```jinja
{# documents/design.md.jinja2 #}
<!-- SCAFFOLD: template={{ template_id }} version={{ template_version }} created={{ scaffold_created }} path={{ output_path }} -->
# Design: {{ title }}
```

**Git Commit (no path):**
```jinja
{# documents/commit-message.txt.jinja2 #}
# SCAFFOLD: template={{ template_id }} version={{ template_version }} created={{ scaffold_created }}
{{ type }}: {{ description }}
```

### 3. Key-Value Format

**Rationale:** Simple, human-readable, easy to parse.

**Format:** `key=value key2=value2`

**Example:**
```
template=dto version=2.0 created=2026-01-20T14:32:15Z path=src/dto/user_dto.py
```

**Parser:**
```python
def parse_key_value_pairs(kv_string: str) -> dict:
    result = {}
    for pair in kv_string.split():
        if '=' in pair:
            key, value = pair.split('=', 1)
            result[key] = value
    return result
```

### 4. Five Fields with Timestamps

**Fields:**
- `template`: Artifact type_id from artifacts.yaml
- `version`: Template version from artifacts.yaml
- `created`: Scaffold creation timestamp (ISO 8601 UTC)
- `updated`: Last migration/update timestamp (ISO 8601 UTC, optional)
- `path`: Relative workspace path with extension (optional, template-driven)

**Timestamp rationale:**
- ✅ **Staleness detection** - Issue #121 can warn if template updated after file created
- ✅ **Migration tracking** - `updated` timestamp shows when file was migrated
- ✅ **Conflict detection** - Compare file mtime vs metadata.updated
- ✅ **Audit trail** - Exact chronology for debugging/forensics
- ✅ **Low cost** - `datetime.now(timezone.utc).isoformat()` is cheap
- ✅ **Future-proof** - Adding later would break existing metadata

**Path optional rationale:**
- ✅ **Ephemeral artifacts** - Git commits, REPL snippets have no file path
- ✅ **Template-driven** - artifacts.yaml defines output_type (file vs ephemeral)
- ✅ **Validation logic** - Parser checks artifacts.yaml to determine if path required
- ✅ **SSOT principle** - No duplication of type info in metadata

**Checksum decision:** Still deferred to future phase due to:
- Breaks on every edit (formatting, comments, typo fixes)
- Requires complex "what to hash" decision
- Adds implementation complexity
- Can be added later without breaking changes

### 5. Discovery via Pattern Matching

**Rationale:** No mapping needed - try all patterns until match.

**Implementation:**
```python
class ScaffoldMetadataParser:
    def parse(self, file_content: str, file_extension: str | None = None) -> dict | None:
        first_line = file_content.split('\n')[0].strip()
        
        # Filter patterns by extension if provided
        patterns = self.config.comment_patterns
        if file_extension:
            patterns = [p for p in patterns if file_extension in p.extensions]
        
        # Try each pattern
        for pattern_config in patterns:
            match = re.match(pattern_config.pattern, first_line)
            if match:
                return self._parse_key_value_pairs(match.group(1))
        
        return None  # Not a scaffolded file
```

## Implementation Plan

### Phase 0.1: Config Infrastructure (TDD: RED)

**Files to create:**
1. `.st3/scaffold_metadata.yaml` - Pattern definitions
2. `mcp_server/config/scaffold_metadata_config.py` - Pydantic models
3. `tests/unit/config/test_scaffold_metadata_config.py` - Unit tests

**TDD Approach - Tests FIRST:**
```python
# tests/unit/config/test_scaffold_metadata_config.py
def test_load_config_from_yaml():
    """RED: Test fails - config loader doesn't exist yet."""
    config = ScaffoldMetadataConfig.from_file(".st3/scaffold_metadata.yaml")
    assert config.version == "1.0"
    assert len(config.comment_patterns) == 4

def test_validate_metadata_field_formats():
    """RED: Test fails - field validation doesn't exist yet."""
    field = MetadataField(
        name="created",
        required=True,
        format=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"
    )
    assert field.validate("2026-01-20T14:32:15Z") == True
    assert field.validate("2026-01-20") == False
```

**Implementation (GREEN):**
```python
class MetadataField(BaseModel):
    name: str
    required: bool
    description: str
    format: str | None = None
    
    def validate(self, value: str) -> bool:
        if self.format:
            return bool(re.match(self.format, value))
        return True

class ScaffoldMetadataConfig(BaseModel):
    version: str
    comment_patterns: list[CommentPattern]
    metadata_fields: list[MetadataField]
    
    @classmethod
    def from_file(cls, path: str = ".st3/scaffold_metadata.yaml"):
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        return cls(**data)
```

**Refactor:** Clean up, extract helpers, optimize

---

### Phase 0.2: Metadata Parser (TDD: RED → GREEN → REFACTOR)

**File:** `mcp_server/scaffolding/metadata.py`
**Tests:** `tests/unit/scaffolding/test_metadata_parser.py`

**TDD Approach - Tests FIRST (RED):**
```python
def test_parse_python_metadata():
    """RED: Parser doesn't exist yet."""
    content = "# SCAFFOLD: template=dto version=2.0 created=2026-01-20T14:32:15Z path=src/dto/user.py\n..."
    parser = ScaffoldMetadataParser()
    result = parser.parse(content, ".py")
    assert result == {
        "template": "dto",
        "version": "2.0",
        "created": "2026-01-20T14:32:15Z",
        "path": "src/dto/user.py"
    }

def test_parse_no_metadata():
    """RED: Parser doesn't handle non-scaffolded files."""
    content = "from pydantic import BaseModel\n..."
    parser = ScaffoldMetadataParser()
    assert parser.parse(content, ".py") is None
```

**Implementation (GREEN):**
```python
class ScaffoldMetadataParser:
    def __init__(self, config: ScaffoldMetadataConfig | None = None):
        self.config = config or ScaffoldMetadataConfig.from_file()
    
    def parse(self, file_content: str, file_extension: str | None = None) -> dict | None:
        """Parse metadata from first line. Returns None if not scaffolded."""
        first_line = file_content.split('\n')[0].strip()
        
        # Filter patterns by extension (performance)
        patterns = self._filter_patterns(file_extension)
        
        # Try each pattern
        for pattern in patterns:
            match = re.match(pattern.pattern, first_line)
            if match:
                return self._parse_key_value_pairs(match.group(1))
        
        return None  # Not a scaffolded file
    
    def _parse_key_value_pairs(self, kv_string: str) -> dict:
        """Parse 'key=value key2=value2' format with validation."""
        result = {}
        for pair in kv_string.split():
            if '=' in pair:
                key, value = pair.split('=', 1)
                # Validate against config field formats
                field_def = self._get_field_def(key)
                if field_def and not field_def.validate(value):
                    raise ValueError(f"Invalid format for {key}: {value}")
                result[key] = value
        return result
```

**Refactor:** Extract validators, optimize pattern matching

---

### Phase 0.3: ArtifactManager Integration (TDD: RED → GREEN → REFACTOR)

**Update:** `mcp_server/managers/artifact_manager.py`
**Tests:** `tests/unit/managers/test_artifact_manager_metadata.py`

**TDD Approach - Tests FIRST (RED):**
```python
def test_context_enrichment_with_timestamps():
    """RED: Context enrichment doesn't add timestamp fields yet."""
    manager = ArtifactManager()
    context = await manager._enrich_context("dto", {"name": "User"})
    
    assert "template_id" in context
    assert "template_version" in context
    assert "scaffold_created" in context  # ISO 8601 UTC timestamp
    assert "output_path" in context

def test_ephemeral_artifact_no_path():
    """RED: Ephemeral artifacts shouldn't get path field."""
    manager = ArtifactManager()
    context = await manager._enrich_context("commit-message", {"type": "feat"})
    
    assert "output_path" not in context  # Ephemeral = no path
```

**Implementation (GREEN):**
```python
from datetime import datetime, timezone

async def scaffold_artifact(self, artifact_type: str, output_path: str | None = None, **context: Any) -> str:
    # 1. Get artifact definition
    artifact = self.registry.get_artifact(artifact_type)
    
    # 2. Enrich context with metadata fields
    context['template_id'] = artifact_type
    context['template_version'] = artifact.version
    context['scaffold_created'] = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # 3. Path only for file artifacts
    if artifact.output_type == "file":
        context['output_path'] = output_path or self._resolve_path(artifact_type, context.get('name'))
    
    # 4. Scaffold (template uses enriched context)
    result = self.scaffolder.scaffold(artifact_type, **context)
    
    # 5-8. Existing validation and write logic...
```

**Refactor:** Extract enrichment to separate method, add type hints

---

### Phase 0.4: End-to-End Tests

**Test files:**
- `tests/integration/test_metadata_e2e.py` - Full scaffold → parse → validate flow
- `tests/unit/scaffolding/test_metadata_parser.py` - Parser unit tests

**Unit Test Coverage (100% target):**
```python
# Parser unit tests
def test_parse_python_metadata():
    content = "# SCAFFOLD: template=dto version=2.0 created=2026-01-20T14:32:15Z path=src/dto/user.py\n..."
    parser = ScaffoldMetadataParser()
    result = parser.parse(content, ".py")
    assert result == {
        "template": "dto",
        "version": "2.0",
        "created": "2026-01-20T14:32:15Z",
        "path": "src/dto/user.py"
    }

def test_parse_markdown_metadata():
    content = "<!-- SCAFFOLD: template=design version=1.0 created=2026-01-20T14:32:15Z path=docs/design/x.md -->\n..."
    # ... similar assertions

def test_parse_no_metadata():
    """Graceful handling of non-scaffolded files."""
    content = "from pydantic import BaseModel\n..."
    parser = ScaffoldMetadataParser()
    assert parser.parse(content, ".py") is None

def test_parse_invalid_timestamp_format():
    """Validation rejects invalid timestamp."""
    content = "# SCAFFOLD: template=dto version=2.0 created=2026-01-20 path=src/dto/user.py\n..."
    parser = ScaffoldMetadataParser()
    with pytest.raises(ValueError, match="Invalid format for created"):
        parser.parse(content, ".py")

def test_parse_ephemeral_no_path():
    """Ephemeral artifacts without path are valid."""
    content = "# SCAFFOLD: template=commit-message version=1.0 created=2026-01-20T14:35:42Z\n..."
    parser = ScaffoldMetadataParser()
    result = parser.parse(content, ".txt")
    assert "path" not in result
```

**E2E Integration Tests:**
```python
# tests/integration/test_metadata_e2e.py
@pytest.mark.asyncio
async def test_scaffold_dto_with_metadata():
    """Full flow: scaffold → read → parse → validate."""
    manager = ArtifactManager()
    
    # 1. Scaffold DTO
    result = await manager.scaffold_artifact("dto", name="User")
    
    # 2. Read generated file
    file_path = Path("src/dto/user_dto.py")
    assert file_path.exists()
    content = file_path.read_text()
    
    # 3. Parse metadata
    parser = ScaffoldMetadataParser()
    metadata = parser.parse(content, ".py")
    
    # 4. Validate metadata
    assert metadata["template"] == "dto"
    assert metadata["version"] == "2.0"  # from artifacts.yaml
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", metadata["created"])
    assert metadata["path"] == "src/dto/user_dto.py"

@pytest.mark.asyncio
async def test_scaffold_git_commit_ephemeral():
    """E2E for ephemeral artifact (no path)."""
    manager = ArtifactManager()
    
    # 1. Scaffold commit message
    result = await manager.scaffold_artifact("commit-message", type="feat", description="Add auth")
    
    # 2. Parse metadata from result
    parser = ScaffoldMetadataParser()
    metadata = parser.parse(result, ".txt")
    
    # 3. Validate - no path for ephemeral
    assert metadata["template"] == "commit-message"
    assert "path" not in metadata
```

**Coverage Target:** 100% for new code (config, parser, enrichment logic)

---

## Success Criteria

**Phase 0 complete when:**
- ✅ Config file (`.st3/scaffold_metadata.yaml`) loads without errors
- ✅ Config models validate all field formats (template, version, created, updated, path)
- ✅ Parser correctly identifies all 4 comment syntaxes
- ✅ Parser returns `None` for non-scaffolded files (graceful degradation)
- ✅ Parser validates metadata field formats at runtime
- ✅ Parser handles ephemeral artifacts (no path field) correctly
- ✅ Context enrichment adds 5 fields with correct formats:
  - `template_id` (from artifact type)
  - `template_version` (from artifacts.yaml)
  - `scaffold_created` (ISO 8601 UTC timestamp)
  - `output_path` (only for file artifacts, based on artifacts.yaml)
  - Note: `updated` only added during migrations (future phase)
- ✅ **TDD workflow followed:** RED → GREEN → REFACTOR for all phases
- ✅ **100% test coverage** for new code (config, parser, enrichment)
- ✅ **E2E integration tests** pass for both file and ephemeral artifacts
- ✅ Unit tests cover:
  - Valid metadata parsing (all 4 syntaxes)
  - Invalid format rejection
  - Non-scaffolded files (graceful None)
  - Ephemeral artifacts (no path)
  - Timestamp validation

**Not required for Phase 0:**
- ❌ Template file updates (separate task after research approval)
- ❌ Migration of existing files (future phase)
- ❌ Discovery tool implementation (Issue #121)
- ❌ `updated` field population (only during migrations)



---

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     FOOTER SECTION (REQUIRED)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Related Documentation

- **[README.md](../../README.md)** - Project overview

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | YYYY-MM-DD | GitHub Copilot | Initial creation |

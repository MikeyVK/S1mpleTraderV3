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
# SCAFFOLD: template=dto version=2.0 date=2026-01-20 path=src/dto/user_dto.py
from pydantic import BaseModel, Field

class UserDTO(BaseModel):
    """User data transfer object."""
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
    
  - name: "version"
    required: true
    description: "Template version from artifacts.yaml"
    
  - name: "date"
    required: true
    description: "Scaffold creation date (ISO 8601 format)"
    format: "YYYY-MM-DD"
    
  - name: "path"
    required: true
    description: "Relative path from workspace root"
```

### 2. Template-Driven Syntax

**Rationale:** Templates know their target language and appropriate comment syntax.

**Examples:**

**Python DTO:**
```jinja
{# components/dto.py.jinja2 #}
# SCAFFOLD: template={{ template_id }} version={{ template_version }} date={{ scaffold_date }} path={{ output_path }}
from pydantic import BaseModel, Field
```

**TypeScript Interface:**
```jinja
{# components/interface.ts.jinja2 #}
// SCAFFOLD: template={{ template_id }} version={{ template_version }} date={{ scaffold_date }} path={{ output_path }}
export interface {{ name }} {
```

**Markdown Document:**
```jinja
{# documents/design.md.jinja2 #}
<!-- SCAFFOLD: template={{ template_id }} version={{ template_version }} date={{ scaffold_date }} path={{ output_path }} -->
# Design: {{ title }}
```

### 3. Key-Value Format

**Rationale:** Simple, human-readable, easy to parse.

**Format:** `key=value key2=value2`

**Example:**
```
template=dto version=2.0 date=2026-01-20 path=src/dto/user_dto.py
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

### 4. Four Core Fields (No Checksum Yet)

**Fields:**
- `template`: Artifact type_id from artifacts.yaml
- `version`: Template version from artifacts.yaml
- `date`: Scaffold creation date (ISO 8601)
- `path`: Relative path from workspace root

**Checksum decision:** Deferred to future phase due to:
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

### Phase 0.1: Config Infrastructure

**Files to create:**
1. `.st3/scaffold_metadata.yaml` - Pattern definitions
2. `mcp_server/config/scaffold_metadata_config.py` - Pydantic models
3. `mcp_server/scaffolding/metadata.py` - Parser implementation

**Models:**
```python
class CommentPattern(BaseModel):
    name: str
    description: str
    pattern: str
    extensions: list[str]

class MetadataField(BaseModel):
    name: str
    required: bool
    description: str
    format: str | None = None

class ScaffoldMetadataConfig(BaseModel):
    version: str
    comment_patterns: list[CommentPattern]
    metadata_fields: list[MetadataField]
    
    @classmethod
    def from_file(cls, path: str = ".st3/scaffold_metadata.yaml"):
        # Load and validate config
```

### Phase 0.2: Metadata Parser

**File:** `mcp_server/scaffolding/metadata.py`

**Functions:**
```python
class ScaffoldMetadataParser:
    def __init__(self, config: ScaffoldMetadataConfig | None = None):
        self.config = config or ScaffoldMetadataConfig.from_file()
    
    def parse(self, file_content: str, file_extension: str | None = None) -> dict | None:
        """Parse metadata from first line."""
        
    def _parse_key_value_pairs(self, kv_string: str) -> dict:
        """Parse 'key=value key2=value2' format."""
```

### Phase 0.3: ArtifactManager Integration

**Update:** `mcp_server/managers/artifact_manager.py`

**Changes:**
```python
async def scaffold_artifact(self, artifact_type: str, output_path: str | None = None, **context: Any) -> str:
    # 1. Get artifact definition
    artifact = self.registry.get_artifact(artifact_type)
    
    # 2. Enrich context with metadata
    context['template_id'] = artifact_type
    context['template_version'] = artifact.version  # from artifacts.yaml
    context['scaffold_date'] = datetime.now().strftime('%Y-%m-%d')
    context['output_path'] = output_path or self.get_artifact_path(artifact_type, context['name'])
    
    # 3. Scaffold artifact (template uses enriched context)
    result = self.scaffolder.scaffold(artifact_type, **context)
    
    # 4-7. Existing validation and write logic...
```

### Phase 0.4: Unit Tests

**Test file:** `tests/unit/scaffolding/test_metadata_parser.py`

**Test cases:**
```python
def test_parse_python_metadata():
    content = "# SCAFFOLD: template=dto version=2.0 date=2026-01-20 path=src/dto/user.py\n..."
    parser = ScaffoldMetadataParser()
    result = parser.parse(content, ".py")
    assert result == {
        "template": "dto",
        "version": "2.0", 
        "date": "2026-01-20",
        "path": "src/dto/user.py"
    }

def test_parse_markdown_metadata():
    content = "<!-- SCAFFOLD: template=design version=1.0 date=2026-01-20 path=docs/design/x.md -->\n..."
    ...

def test_parse_no_metadata():
    content = "from pydantic import BaseModel\n..."
    parser = ScaffoldMetadataParser()
    result = parser.parse(content, ".py")
    assert result is None
```

## Success Criteria

**Phase 0 complete when:**
- ✅ Config file loads without errors
- ✅ Parser correctly identifies all 4 comment syntaxes
- ✅ Parser returns None for non-scaffolded files
- ✅ Context enrichment adds all 4 fields
- ✅ Unit tests pass (100% coverage for new code)
- ✅ Integration test: scaffold DTO → verify metadata line exists

**Not required for Phase 0:**
- Template file updates (separate task)
- Migration of existing files
- Discovery tool implementation



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

# Jinja2 Template Whitespace Control Strategy (Issue #72)

## Problem Statement
Multi-tier template inheritance creates unpredictable whitespace:
- Explicit newlines (`{{ "\n" }}`) + implicit source newlines = doubled spacing
- Inconsistent trim patterns ({%- -%}) across tiers break composition
- Ad-hoc fixes for one artifact type break others

## Universal Principles

### 1. Block Boundaries = Natural Newlines
```jinja
{%- block content %}
...content...
{% endblock %}
```
- Opening `{% block %}` consumes newline before it
- Closing `{% endblock %}` produces newline after it
- Result: ONE newline between blocks naturally

### 2. Internal Trimming for Content Merging
```jinja
{%- if condition -%}
content without surrounding whitespace
{%- endif -%}
```
- Use `-` only when you want to REMOVE whitespace
- Left trim (`{%-`) removes before
- Right trim (`-%}`) removes after

### 3. Super() Calls Must Be Right-Trimmed (CRITICAL FIX)
```jinja
{% block imports %}
{{ super() -}}
additional imports
{% endblock %}
```
- `super()` outputs parent block content AS-IS (includes parent's endblock newline)
- **MUST use `{{ super() -}}`** (right-trim) to prevent extra blank line
- Without right-trim: parent newline + block boundary newline = double spacing
- Learned from Jinja2 docs: variable expressions can be trimmed like blocks

### 4. No Explicit Newlines
```jinja
BAD:  {{ "\n" }}
GOOD: Let block boundaries do it
```

## Application Per Tier

### Tier 0 (tier0_base_artifact.jinja2)
**Purpose:** SCAFFOLD header only
**Output:** `# SCAFFOLD: ...\n` (one newline from endblock)

```jinja
{% block content -%}
{%- set variables... -%}
{{comment_start}} SCAFFOLD: ...{{comment_end}}
{% endblock %}
```
- `{% block content -%}` - trim after opening (no space before SCAFFOLD)
- `{%- set ... -%}` - variables don't produce output, trim both sides  
- SCAFFOLD line has NO explicit newline
- `{% endblock %}` produces natural newline

### Tier 1 CODE (tier1_base_code.jinja2)
**Purpose:** Module docstring, imports structure, class structure
**Output:**
```
# SCAFFOLD: ...
"""Docstring"""

imports

class:
```

```jinja
{%- block content %}
{{ super() -}}

{% block module_docstring %}
"""..."""
{% endblock %}

{% block imports_section %}
{% if imports %}
imports here
{% endif %}
{% endblock %}

{% block class_structure %}
class definition
{% endblock %}
{% endblock %}
```

**Logic:**
- `{%- block content %}` (left-trim) - prevents leading newline
- `{{ super() -}}` (RIGHT-TRIM) - prevents extra blank line after SCAFFOLD
- Each section block naturally produces newlines between sections

### Tier 1 DOCUMENT (tier1_base_document.jinja2)
**Purpose:** Markdown header, sections
**Similar pattern to CODE but for Markdown structure**

### Tier 2 PYTHON (tier2_base_python.jinja2)
**Purpose:** Python-specific typing, base classes, dunder methods
**Extends tier1_base_code**

```jinja
{% block imports_section %}
{% block type_imports %}
{% if type_imports %}
from typing import ...
{% endif %}
{% endblock %}
{{ super() }}
{% endblock %}

{% block class_structure %}
class {{ name }}(BaseModel):
    ...
{% endblock %}
```

**Logic:**
- Override imports_section to prepend type imports
- `{{ super() }}` brings tier1's imports (stdlib/third_party/project)
- Natural newlines between type imports and super() output

### Concrete Templates (dto.py.jinja2, worker.py.jinja2, etc)
**Purpose:** Specific implementation
**Extends tier2 (Python) or tier1 (generic)**

```jinja
{% block type_imports %}
from pydantic import BaseModel, Field
{% endblock %}

{% block class_structure %}
class {{ name }}(BaseModel):
    """{{ description }}"""
    
    fields here
{% endblock %}
```

**Logic:**
- Override only what's different
- No trim unless merging content
- Let parent tiers handle structure

## Testing Strategy

### Per-Tier Testing
1. **Tier 0 only:** Minimal concrete that just extends tier0
2. **Tier 0 + Tier 1 CODE:** Simple Python class (no tier2)
3. **Tier 0 + Tier 1 DOCUMENT:** Simple markdown (no tier2)
4. **Full stack CODE:** Tier0 → Tier1 → Tier2 → DTO
5. **Full stack DOCUMENT:** Tier0 → Tier1 → Tier2_md → Design

### All Artifact Types
Must test with representative from each category:
- **CODE:** dto, worker, service, adapter, tool, resource
- **DOCUMENT:** design, architecture, tracking, generic
- **CONFIG:** (future)

## Expected Output Format

### Python artifacts:
```python
# SCAFFOLD: template=dto version=abc123 created=2026-01-26T... path=dto.py
"""Module docstring."""

from typing import List
from pydantic import BaseModel, Field

class UserDTO(BaseModel):
    """User data transfer object."""
    
    id: int
    name: str
```

**Spacing rules:**
- 1 newline after SCAFFOLD
- 1 newline after docstring  
- 1 newline after imports
- 1 newline after class docstring
- 1 newline between fields and methods

### Markdown artifacts:
```markdown
<!-- SCAFFOLD: template=design version=abc123 created=2026-01-26T... path=design.md -->
# Document Title

## Section

Content here.
```

**Spacing rules:**
- 1 newline after SCAFFOLD
- 1 newline after title
- 1 newline after section header

## Implementation Checklist

- [ ] tier0_base_artifact.jinja2 - Remove explicit `{{ "\n" }}`
- [ ] tier1_base_code.jinja2 - Consistent block boundaries
- [ ] tier1_base_document.jinja2 - Same principles
- [ ] tier1_base_config.jinja2 - Same principles
- [ ] tier2_base_python.jinja2 - Proper super() handling
- [ ] tier2_base_markdown.jinja2 - If exists
- [ ] tier2_base_yaml.jinja2 - If exists
- [ ] concrete/dto.py.jinja2 - No special trimming
- [ ] concrete/worker.py.jinja2 - No special trimming
- [ ] concrete/service.py.jinja2 - No special trimming
- [ ] concrete/adapter.py.jinja2 - No special trimming
- [ ] concrete/tool.py.jinja2 - No special trimming
- [ ] concrete/resource.py.jinja2 - No special trimming
- [ ] concrete/design.md.jinja2 - No special trimming
- [ ] concrete/architecture.md.jinja2 - No special trimming
- [ ] concrete/tracking.md.jinja2 - No special trimming
- [ ] concrete/generic.py.jinja2 - No special trimming

## Validation

Every template must produce:
1. Valid syntax (compile for Python, valid Markdown)
2. Exactly 1 newline between major sections
3. Consistent across ALL artifact types
4. No empty lines where not semantically meaningful

## Lessons Learned: Control Structure Indentation (Issue #72.3)

**Problem:** Methods generated outside class despite template having 4 leading spaces before `{% if %}`.

**Root Cause:** Jinja2 treats spaces **before** control structures as template formatting, NOT output content.

**Example (BROKEN):**
```jinja
class TestExample:
    """Docstring."""
    
    {% if method.async %}async {% endif %}def {{ method.name }}(
```
Output: `def test_name(` at column 0 (method outside class!)

**Fix:** Move indentation **inside** both branches of the conditional:
```jinja
class TestExample:
    """Docstring."""
    
{% if method.async %}    async def {{ method.name }}{% else %}    def {{ method.name }}{% endif %}(
```
Output:
- Async: `    async def test_name(` ✅
- Sync: `    def test_name(` ✅

**Key Insight:**
- Spaces **before** `{% if %}` = template formatting (ignored in output)
- Spaces **inside** `{% if %}...{% else %}...{% endif %}` = actual output
- BOTH branches must include the indentation

**Applied to:**
- test_unit.py.jinja2 line 79
- test_integration.py.jinja2 line 93

## Lessons Learned: Trailing Newlines in Loops (Issue #72.3.1)

**Problem:** Generated files ended with 2 empty lines instead of 1 newline (POSIX standard).

**Root Cause:** Blank line between `{% endif %}` and `{% endfor %}` in method loops was preserved in output.

**Symptom:** 
```
        assert True  # Replace with actual assertions
[blank line]
[blank line at EOF]
```

**Fix Pattern:** Use right-trim on loop-closing tags:
```jinja
        {% if method.assertions %}
        {{ method.assertions | indent(8) }}
        {% else %}
        # TODO: Add assertions
        assert True  # Replace with actual assertions
        {% endif -%}

    {%- endfor %}
```

**Why this works:**
- `{% endif -%}` removes newline AFTER the endif tag
- `{%- endfor %}` removes whitespace/newline BEFORE the endfor tag
- Together they eliminate the blank line while preserving code structure

**Applied to:**
- test_unit.py.jinja2 lines 105-107 (assertions endif + method endfor)
- test_integration.py.jinja2 lines 118-120 (assertions endif + method endfor)

**Key Insight:** Blank lines in template source between control structures are literal content unless explicitly trimmed. Use surgical trim (`-%}` or `{%-`) only where needed.

## Anti-Patterns to Avoid

❌ Explicit newlines: `{{ "\n" }}`
❌ Aggressive trimming: `{%- block -%}` at boundaries
❌ Ad-hoc fixes: "This works for DTO so ship it"
❌ Inconsistent patterns: Different trim style per template

✅ Natural newlines: Block boundaries
✅ Surgical trimming: Only for content merging
✅ Universal rules: Same logic all templates
✅ Comprehensive testing: All artifact types

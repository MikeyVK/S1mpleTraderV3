# Document Template Tier Allocation

**Status:** PROPOSED  
**Date:** 2026-01-26  
**Context:** Issue #72 - Multi-Tier Template Architecture

---

## Overview

This document defines the tier allocation for DOCUMENT artifacts (design, architecture, reference) in the Jinja2 template hierarchy.

**Tier Strategy:**
- **Tier 1:** Universal document structure (all knowledge docs inherit)
- **Tier 2:** Markdown language syntax (replaceable with RST/AsciiDoc)
- **Concrete:** Document-type specific content (design/architecture/reference)

---

## Tier 1: tier1_base_document.jinja2

**Purpose:** Format-level structure shared by ALL knowledge documents.

**Responsibility:** Define document sections, NOT markdown syntax.

### Sections Provided

#### 1. Header Metadata Block
```jinja2
{%- block header_metadata -%}
**Status:** {{ status }}
**Version:** {{ version }}
**Last Updated:** {{ last_updated }}
{%- endblock %}
```

**Variables:**
- `status` (required): DRAFT | PRELIMINARY | APPROVED | DEFINITIVE
- `version` (required): X.Y format
- `last_updated` (required): YYYY-MM-DD format

**Note:** Concrete templates can extend this block to add type-specific fields (e.g., Design adds `Created`, `Implementation Phase`).

---

#### 2. Purpose Section
```jinja2
{%- block purpose_section -%}
## Purpose

{{ purpose }}
{%- endblock %}
```

**Variables:**
- `purpose` (required): 2-4 sentence paragraph describing:
  - What this document covers
  - Why it exists (problem/decision)
  - Who should read it

---

#### 3. Scope Section
```jinja2
{%- block scope_section -%}
## Scope

**In Scope:**
{%- for item in scope_in %}
- {{ item }}
{%- endfor %}

**Out of Scope:**
{%- for item in scope_out %}
- {{ item }}
{%- endfor %}
{%- endblock %}
```

**Variables:**
- `scope_in` (required): List of topics covered
- `scope_out` (required): List of exclusions (with cross-refs to other docs)

---

#### 4. Prerequisites Section (Optional)
```jinja2
{%- block prerequisites_section -%}
{%- if prerequisites %}
## Prerequisites

Read these first:
{%- for prereq in prerequisites %}
{{ loop.index }}. {{ prereq }}
{%- endfor %}
{%- endif %}
{%- endblock %}
```

**Variables:**
- `prerequisites` (optional): List of required reading (with reasons)

---

#### 5. Content Block (Abstract)
```jinja2
{%- block content -%}
{#- Subclass MUST override this block -#}
{%- endblock %}
```

**Responsibility:** Concrete templates provide type-specific content structure.

---

#### 6. Related Documentation Section
```jinja2
{%- block related_section -%}
## Related Documentation

{%- for doc in related_docs %}
- **{{ doc.title }}** - {{ doc.description }}
{%- endfor %}
{%- endblock %}
```

**Variables:**
- `related_docs` (required): List of `{title, description}` dicts

---

#### 7. Version History Section
```jinja2
{%- block version_history -%}
## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
{%- for entry in version_entries %}
| {{ entry.version }} | {{ entry.date }} | {{ entry.author }} | {{ entry.changes }} |
{%- endfor %}
{%- endblock %}
```

**Variables:**
- `version_entries` (required): List of `{version, date, author, changes}` dicts

---

### Full Block Structure

```jinja2
{%- block document_structure -%}
  {%- block header_metadata -%}{%- endblock %}
  ---
  {%- block purpose_section -%}{%- endblock %}
  {%- block scope_section -%}{%- endblock %}
  {%- block prerequisites_section -%}{%- endblock %}
  ---
  {%- block content -%}{#- Abstract -#}{%- endblock %}
  ---
  {%- block related_section -%}{%- endblock %}
  {%- block version_history -%}{%- endblock %}
{%- endblock document_structure -%}
```

---

## Tier 2: tier2_base_markdown.jinja2

**Purpose:** Markdown language-specific syntax.

**Responsibility:** Convert tier1 structure to Markdown syntax, NO content logic.

### Syntax Elements Provided

#### 1. SCAFFOLD Comment Syntax
```jinja2
{%- block scaffold_comment -%}
<!-- SCAFFOLD: {{ artifact_type }}:{{ version_hash }} | {{ timestamp }} | {{ output_path }} -->
{%- endblock %}
```

**Rationale:** Markdown uses `<!-- -->` for comments.

---

#### 2. Document Title Syntax
```jinja2
{%- block document_title -%}
# {{ title }}

{%- endblock %}
```

**Rationale:** Markdown H1 with blank line after.

---

#### 3. Horizontal Rule Syntax
```jinja2
{%- block separator -%}

---

{%- endblock %}
```

**Rationale:** Markdown uses `---` for separators (with blank lines).

---

#### 4. Code Block Syntax
```jinja2
{%- block code_block -%}
```{{ language | default('python') }}
{{ code_content }}
```
{%- endblock %}
```

**Rationale:** Markdown fenced code blocks with language specifier.

---

#### 5. Link Definitions Syntax
```jinja2
{%- block link_definitions -%}
{%- if link_refs %}
<!-- Link definitions -->
{%- for ref in link_refs %}
[{{ ref.id }}]: {{ ref.url }} "{{ ref.title }}"
{%- endfor %}
{%- endif %}
{%- endblock %}
```

**Rationale:** Markdown reference-style link definitions (hidden in render).

---

#### 6. Checkbox List Syntax
```jinja2
{%- block checkbox_list -%}
{%- for item in items %}
- [ ] {{ item }}
{%- endfor %}
{%- endblock %}
```

**Rationale:** GitHub-flavored Markdown checkbox syntax.

---

### Inheritance Pattern

```jinja2
{%- extends "tier1_base_document.jinja2" -%}

{#- Override blocks to add Markdown syntax -#}
{%- block document_structure -%}
{{ self.scaffold_comment() }}

{{ self.document_title() }}

{{ super() }}  {#- Call tier1 structure -#}
{%- endblock %}
```

**Key:** `super()` calls tier1 structure, tier2 wraps it with Markdown syntax.

---

## Concrete: concrete/design.md.jinja2

**Purpose:** Design-specific content structure and fields.

**Responsibility:** Define DESIGN template sections (numbered, options, decisions).

### Design-Specific Additions

#### 1. Extended Header Metadata
```jinja2
{%- block header_metadata -%}
{{ super() }}  {#- Include tier1 Status/Version/Updated -#}
**Created:** {{ created }}
**Implementation Phase:** {{ implementation_phase }}
{%- endblock %}
```

**Variables:**
- `created` (required): YYYY-MM-DD when design started
- `implementation_phase` (required): Phase X.Y description

---

#### 2. Content Block Override (Numbered Sections)
```jinja2
{%- block content -%}

## 1. Context & Requirements

### 1.1. Problem Statement

{{ problem_statement }}

### 1.2. Requirements

**Functional:**
{%- for req in functional_requirements %}
- [ ] {{ req }}
{%- endfor %}

**Non-Functional:**
{%- for req in non_functional_requirements %}
- [ ] {{ req }}
{%- endfor %}

### 1.3. Constraints

{%- for constraint in constraints %}
- {{ constraint }}
{%- endfor %}

---

## 2. Design Options

{%- for option in design_options %}

### 2.{{ loop.index }}. Option {{ loop.index }}: {{ option.name }}

{{ option.description }}

{%- if option.code %}
```python
{{ option.code }}
```
{%- endif %}

**Pros:**
{%- for pro in option.pros %}
- ✅ {{ pro }}
{%- endfor %}

**Cons:**
{%- for con in option.cons %}
- ❌ {{ con }}
{%- endfor %}
{%- endfor %}

---

## 3. Chosen Design

**Decision:** {{ chosen_option }}

**Rationale:** {{ decision_rationale }}

{%- if design_decisions %}

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
{%- for decision in design_decisions %}
| {{ decision.what }} | {{ decision.why }} |
{%- endfor %}
{%- endif %}

---

{%- if open_questions %}
## 4. Open Questions

| Question | Options | Status |
|----------|---------|--------|
{%- for q in open_questions %}
| {{ q.question }} | {{ q.options }} | {{ q.status }} |
{%- endfor %}
{%- endif %}

{%- endblock content -%}
```

---

### Design-Specific Variables

**Required:**
- `created`: YYYY-MM-DD
- `implementation_phase`: String (e.g., "Phase 1.2 - TDD")
- `problem_statement`: Paragraph
- `functional_requirements`: List of strings
- `non_functional_requirements`: List of strings
- `constraints`: List of strings
- `design_options`: List of `{name, description, code, pros, cons}` dicts
- `chosen_option`: String (e.g., "Option A: Event-Driven")
- `decision_rationale`: Paragraph

**Optional:**
- `design_decisions`: List of `{what, why}` dicts (for section 3.1)
- `open_questions`: List of `{question, options, status}` dicts (section 4)

---

## Tier Allocation Summary

| Element | Tier 1 (Document) | Tier 2 (Markdown) | Concrete (Design) |
|---------|------------------|-------------------|-------------------|
| **Status/Version/Updated** | ✅ Structure | | |
| **Purpose section** | ✅ Structure | | |
| **Scope In/Out** | ✅ Structure | | |
| **Prerequisites** | ✅ Structure | | |
| **Related docs** | ✅ Structure | | |
| **Version history** | ✅ Structure | | |
| **Markdown `<!-- -->`** | | ✅ Syntax | |
| **Markdown `# title`** | | ✅ Syntax | |
| **Markdown `---` separator** | | ✅ Syntax | |
| **Markdown code blocks** | | ✅ Syntax | |
| **Markdown link defs** | | ✅ Syntax | |
| **Markdown checkboxes** | | ✅ Syntax | |
| **Created date** | | | ✅ Design field |
| **Implementation Phase** | | | ✅ Design field |
| **Numbered sections** | | | ✅ Design structure |
| **Context & Requirements** | | | ✅ Design section |
| **Design Options** | | | ✅ Design section |
| **Pros/Cons tables** | | | ✅ Design format |
| **Chosen Design** | | | ✅ Design section |
| **Key Decisions table** | | | ✅ Design section |
| **Open Questions table** | | | ✅ Design section |

---

## Rationale for Allocation

### Why Status/Purpose/Scope in Tier 1?

**All knowledge documents need these sections:**
- Design documents: context for implementation decisions
- Architecture documents: system overview and boundaries
- Reference documents: API scope and usage context

**Reusability:** By placing in tier1, architecture.md.jinja2 and reference.md.jinja2 automatically inherit without duplication.

---

### Why Markdown Syntax in Tier 2?

**Language independence:** Future RST or AsciiDoc templates only replace tier2, tier1 structure remains.

**Example:**
```
tier1_base_document.jinja2 (Status, Purpose, Scope)
├── tier2_base_markdown.jinja2 (<!-- -->, # heading)
├── tier2_base_rst.jinja2 (.. comment, # with underline)
└── tier2_base_asciidoc.jinja2 (// comment, = heading)
```

**Separation of Concerns:** tier1 = WHAT sections, tier2 = HOW to write them.

---

### Why Numbered Sections in Concrete?

**Design-specific convention:** DESIGN_TEMPLATE uses numbered sections (1. Context, 2. Options, 3. Decision).

**Architecture vs Design:**
- Architecture: Conceptual sections (## Components, ## Data Flow) - unnumbered
- Design: Decision flow (## 1. Context, ## 2. Options, ## 3. Decision) - numbered
- Reference: API sections (## API Reference, ## Usage Examples) - unnumbered

**Each concrete template controls its numbering style.**

---

## Other Document Types

### Architecture Document (concrete/architecture.md.jinja2)

**Extends:** tier2_base_markdown → tier1_base_document

**Differences from Design:**
- **No numbered sections** (conceptual, not decision-oriented)
- **Mermaid diagrams** (architecture-specific)
- **No code** (links to source, no implementation)
- **Status lifecycle:** DRAFT → REVIEW → APPROVED → DEFINITIVE (extra REVIEW state)

**Unique variables:**
- `diagrams`: List of `{type, content}` dicts (mermaid/plantuml)
- `components`: List of `{name, responsibility}` dicts

---

### Reference Document (concrete/reference.md.jinja2)

**Extends:** tier2_base_markdown → tier1_base_document

**Differences from Design:**
- **Unnumbered sections** (API Reference, Usage Examples, Best Practices)
- **Working code required** (not illustrative - must run)
- **Source links** (GitHub permalinks to implementation)
- **Test links** (GitHub permalinks to test files)

**Unique variables:**
- `source_file`: GitHub permalink
- `test_file`: GitHub permalink
- `api_entries`: List of `{name, signature, description}` dicts
- `examples`: List of `{title, code}` dicts

---

## SCAFFOLD Format & File Header Standards

### SCAFFOLD Comment Format (2-line)

**Regel 1: Filepath**
```python
# backend/workers/process_worker.py
```
- Relatief pad vanaf workspace root
- Geen `SCAFFOLD:` prefix
- Geen `path=` veld

**Regel 2: Metadata**
```python
# template=worker version=e1bfa313 created=2026-01-26T14:16Z updated=2026-01-27T10:30Z
```
- Template type
- Version hash (8 chars)
- Created timestamp (ISO 8601, UTC, minute precision)
- Updated timestamp (optional, empty bij eerste scaffolding)

**Rationale:**
- 2 regels = beter leesbaar
- Eerste regel = standaard filepath comment (ook zonder scaffold metadata bruikbaar)
- Korter dan oude 1-line format (was vaak >100 chars)

---

### File Header Structure (CODE templates)

**Complete structure (tier2_base_python.jinja2 + concrete):**

```python
# backend/workers/process_worker.py
# template=worker version=e1bfa313 created=2026-01-26T14:16Z

"""
ProcessWorker - Processes incoming events for trading platform.

This worker handles event validation and asynchronous processing.
It integrates with EventAdapter for data ingestion.

@layer: Backend (Workers)
@dependencies: [backend.core.interfaces.base_worker, backend.dtos.execution]
@responsibilities:
    - Validate incoming EventDTO payloads
    - Process events asynchronously
    - Return ResultDTO with processing status
"""

# Standard library
from __future__ import annotations
from typing import TYPE_CHECKING, Any

# Third-party
from pydantic import BaseModel

# Project modules
from backend.core.interfaces.base_worker import BaseWorker
from backend.dtos.execution.event import EventDTO
from backend.dtos.execution.result import ResultDTO

if TYPE_CHECKING:
    from backend.core.interfaces.strategy_cache import IStrategyCache


class ProcessWorker(BaseWorker[EventDTO, ResultDTO]):
    """Process worker for event handling.
    
    Responsibilities:
    - Validate incoming events
    - Process events asynchronously  
    - Return processing results
    """
```

**Module Docstring Elements:**

1. **Line 1: Summary** (format: `ClassName - Purpose`)
   - Start with class/module name
   - Hyphen separator
   - Brief purpose statement

2. **Line 2: Blank**

3. **Lines 3+: Detailed Description**
   - Multi-paragraph explanation
   - Can use numbered/bullet lists
   - Architecture context

4. **Blank line before @labels**

5. **@layer:** Architecture layer
   - Format: `@layer: Backend (Workers)` or `@layer: Platform (Adapters)`

6. **@dependencies:** Module dependencies
   - Format: `@dependencies: [module1, module2, module3]`
   - List of import namespaces (not full paths)

7. **@responsibilities:** Bullet list
   - Format: Indented bullet list (4 spaces)
   - Action-oriented statements
   - 3-5 bullets typical

**Import Structure (3 levels):**

```python
# Standard library
<stdlib imports>

# Third-party  
<pypi package imports>

# Project modules
<local backend.* imports>
```

**Comment headers:**
- `# Standard library` (not "stdlib")
- `# Third-party` (not "external" or "dependencies")
- `# Project modules` (not "local" or "internal")

---

### File Header Structure (DOCUMENT templates)

**Complete structure (tier2_base_markdown.jinja2 + concrete):**

```markdown
<!-- docs/development/issue72/design.md -->
<!-- template=design version=a1b2c3d4 created=2026-01-26T14:16Z -->

# Issue #72 Multi-Tier Template Design

**Status:** DRAFT  
**Version:** 1.0  
**Created:** 2026-01-26  
**Last Updated:** 2026-01-26  

---

## Purpose

Define technical architecture for 5-tier Jinja2 template system that...
```

**SCAFFOLD comments:**
- Line 1: `<!-- filepath -->`
- Line 2: `<!-- template metadata -->`
- Both use HTML comment syntax for Markdown
- No blank line between them

**Header metadata:**
- Bold labels: `**Status:**`, `**Version:**`, etc.
- Two spaces after value for line break
- Horizontal rule `---` after metadata block

**Link Definitions Footer:**
```markdown
<!-- Link definitions -->

[other-design]: ./OTHER_DESIGN.md "Related design"
[prereq-1]: ../architecture/ARCHITECTURE.md "Architecture"
[prereq-2]: ./RELATED_DESIGN.md "Related design"
[arch]: ../architecture/RELEVANT.md "Architecture context"
[related]: ./RELATED_DESIGN.md "Related component"
[todo]: ../TODO.md "Project tracking"
```

**Format:**
- `[id]: relative/path/to/file.md "Title/Description"`
- HTML comment header: `<!-- Link definitions -->`
- Placed at bottom of document (before Version History)
- Invisible in Markdown preview
- Referenced in text as: `[link text][id]`

**Rationale:**
- **Centralized:** All file references in one location
- **Agent-friendly:** Easy to bulk update when files move
- **DRY:** Reuse same link multiple times with different text
- **Clean:** Links don't clutter document body

**Usage in document body:**
```markdown
See [other design document][other-design] for details.
Design extends [architecture document][arch].
```

**Renders as:**
```
See other design document for details.
Design extends architecture document.
```
(With clickable links to actual files)

---

### Google Style Docstrings (CODE templates)

**Format:**
```python
def initialize(
    self,
    strategy_cache: IStrategyCache | None = None,
    **capabilities: Any
) -> None:
    """
    Initialize with runtime dependencies.
    
    Args:
        strategy_cache: StrategyCache instance (REQUIRED - Platform-within-Strategy)
        **capabilities: Required capabilities:
            - dto_types: Dict[str, Type[BaseModel]] - DTO type mappings
    
    Raises:
        WorkerInitializationError: If strategy_cache is None or dto_types missing
    """
```

**Elements:**

1. **Summary line** (imperative mood)
   - Single line, no period
   - Starts with verb (Initialize, Execute, Validate, etc.)

2. **Blank line**

3. **Args:** (capital A, colon, no indent)
   - Argument name, colon, description
   - Multi-line descriptions indented 4 spaces
   - Nested bullets for dict/object fields

4. **Returns:** (if applicable)
   - Single line or multi-line description

5. **Raises:** (if applicable)
   - Exception type, colon, condition

**NOT included:**
- ❌ No `Notes:` sections
- ❌ No `Example:` sections  
- ❌ No `See Also:` sections
- ❌ No triple backtick code blocks in docstrings

---

## Implementation Order

1. ✅ Document this tier allocation (this file)
2. Implement tier1_base_document.jinja2 (universal structure)
3. Implement tier2_base_markdown.jinja2 (markdown syntax)
4. Implement concrete/design.md.jinja2 (design-specific)
5. Update artifacts.yaml (design template_path = "concrete/design.md.jinja2")
6. Create test context for design scaffolding
7. Run E2E test: scaffold_artifact(artifact_type="design", ...)
8. Validate: SCAFFOLD header, all sections present, tier chain correct
9. Implement concrete/architecture.md.jinja2 (next)
10. Implement concrete/reference.md.jinja2 (last)

---

## Validation Against Issue #52 Design (CORRECTED)

### Issue #52 Three-Tier Enforcement Model

**From [issue52/research.md](../issue52/research.md):**

```
TIER 1: BASE TEMPLATES (Format - STRICT)
  - Import order, docstrings, type hints, file structure
  - Severity: ERROR (blocks save)
  - Source: Base templates (base_component.py, base_document.md)

TIER 2: SPECIFIC TEMPLATES (Architectural - MIXED)
  - STRICT: Base class inheritance, required methods, protocol compliance
  - GUIDELINES: Naming conventions, docstring format, field ordering
  - Severity: ERROR for strict, WARNING for guidelines
  - Source: Specific templates (worker.py, dto.py, design.md)

TIER 3: DOCUMENT TEMPLATES (Content Guidance - LOOSE)
  - Format (from base): STRICT via base_document.md
  - Content: GUIDELINES with agent hints
  - Severity: WARNING (never blocks)
  - Source: Document templates (research.md, planning.md)
```

---

### CRITICAL CORRECTION: Tier Mapping

**Issue #72 template tiers ≠ Issue #52 validation tiers**

**CORRECT Understanding:**

1. **Issue #72 tier1 + tier2 = Issue #52 "Base Template"**
   - tier1_base_document = universal document structure (Status, Purpose, Scope)
   - tier2_base_markdown = Markdown language syntax (comments, headings, links)
   - **Both are STRICT format enforcement** (SRP split of legacy base template)

2. **Issue #72 concrete templates = Issue #52 "Specific Templates"**
   - CODE concrete (worker.py, dto.py) → ARCHITECTURAL enforcement
   - DOC concrete (design.md, research.md) → GUIDELINE enforcement
   - TRACKING concrete (commit.txt, pr.md) → GUIDELINE enforcement

---

### SRP Splitsing: Base Template → tier1 + tier2

**Legacy Issue #52 (origineel concept):**
```yaml
base_template.jinja2:
  enforcement: STRICT
  validates:
    - document structure (sections, metadata)
    - language syntax (comments, headings, links)
```

**Issue #72 (SRP split):**
```yaml
tier1_base_document.jinja2:
  enforcement: STRICT
  level: format
  validates:
    - "## Purpose section exists"
    - "## Scope section exists" 
    - "**Status:** field present"
    - "## Version History table exists"

tier2_base_markdown.jinja2:
  enforcement: STRICT
  level: format
  extends: tier1_base_document.jinja2
  validates:
    - "<!-- SCAFFOLD: --> comment format correct"
    - "# H1 title present"
    - "[link]: url format correct"
```

**Rationale:** 
- **tier1** = WHAT sections (language-agnostic)
- **tier2** = HOW to write sections (Markdown-specific)
- Both STRICT because format violations break readability/parsing

---

### Enforcement Levels: ARCHITECTURAL vs GUIDELINE

#### ARCHITECTURAL (CODE concrete templates)

**Characteristics:**
- **Severity:** ERROR (blocks save/commit)
- **Validates:** System-critical structure that would break at runtime
- **Use case:** worker.py, dto.py, adapter.py
- **Template field:** `validates.strict`

**Example (worker.py):**
```yaml
TEMPLATE_METADATA:
  enforcement: ARCHITECTURAL
  level: content
  extends: tier2_base_python.jinja2
  validates:
    strict:
      - "class must inherit BaseWorker[InputDTO, OutputDTO]"
      - "must implement IWorkerLifecycle protocol"
      - "must have async def process() method"
      - "must import from backend.core.interfaces"
    guidelines:
      - "Worker suffix is optional (flexible naming)"
      - "Docstring should include Responsibilities section"
```

**Violation behavior:**
```python
# Missing base class
class MyWorker:  # ❌ ERROR: Must inherit BaseWorker
    pass

# Result:
ValidationResult(
    passed=False,
    score=0.0,
    issues=[ValidationIssue(severity="ERROR", message="Missing base class")]
)
# → BLOCKS SAVE
```

---

#### GUIDELINE (DOCUMENT/TRACKING concrete templates)

**Characteristics:**
- **Severity:** WARNING (saves with notification)
- **Validates:** Best practices that improve quality but don't break anything
- **Use case:** design.md, research.md, commit.txt, pr.md
- **Template field:** `validates.guidelines`

**Example (design.md):**
```yaml
TEMPLATE_METADATA:
  enforcement: GUIDELINE
  level: content
  extends: tier2_base_markdown.jinja2
  validates:
    guidelines:
      - "Use numbered sections (## 1. Context, ## 2. Options, ## 3. Decision)"
      - "Include pros/cons for each design option"
      - "Provide decision rationale in section 3"
  agent_hint: "Design docs focus on decision rationale (WHY), not implementation (HOW)"
  content_guidance:
    includes: ["Problem analysis", "Design options", "Decision rationale"]
    excludes: ["Implementation code", "Test plans"]
```

**Violation behavior:**
```markdown
# Design Document

## Context
...

## Options
Option A: Event-driven
(No pros/cons)  ⚠️ WARNING

## Decision
We chose Option A.
(No rationale)  ⚠️ WARNING

# Result:
ValidationResult(
    passed=True,  # ← Still passes!
    score=0.8,
    issues=[
        ValidationIssue(severity="WARNING", message="Missing pros/cons"),
        ValidationIssue(severity="WARNING", message="Missing decision rationale")
    ],
    agent_hint="Design docs focus on decision rationale (WHY)..."
)
# → SAVES WITH WARNINGS (user notified)
```

---

### Validation Timing

#### 1. safe_edit_file (Interactive editing)
```python
safe_edit_file(path="backend/workers/process_worker.py", content="...", mode="strict")

# Flow:
1. Apply edits
2. Detect template type (worker.py)
3. LayeredTemplateValidator.validate():
   a. Tier 1: STRICT format (tier2_base_python) → ERROR stops
   b. Tier 2: ARCHITECTURAL (worker.py strict) → ERROR stops
   c. Tier 3: GUIDELINE (worker.py guidelines) → WARNING continues
4. If ERROR: rollback, return error
5. If WARNING only: save, show warnings
```

---

#### 2. scaffold_artifact (Generation)
```python
scaffold_artifact(artifact_type="worker", name="ProcessWorker", context={...})

# Flow:
1. Render Jinja2 template
2. IMMEDIATE validation (before disk write)
3. If ERROR: Don't write, return error
4. If pass/warning: Write file, return path + warnings
```

**Note:** Scaffolded files should NEVER have STRICT/ARCHITECTURAL errors (template is source of truth). Only GUIDELINE warnings if context incomplete.

---

#### 3. run_quality_gates (Batch validation)
```python
run_quality_gates(files=["backend/workers/*.py", "docs/*.md"])

# Flow:
1. For each file:
   - Detect template type
   - Run LayeredTemplateValidator
   - Collect all issues
2. Return summary:
   - Files with errors (blocks commit)
   - Files with warnings (commit allowed)
3. Exit code: 1 if any ERROR, 0 if WARNINGs only
```

---

### Enforcement Level Comparison

| Aspect | ARCHITECTURAL | GUIDELINE |
|--------|--------------|-----------|
| **Severity** | ERROR | WARNING |
| **Blocks save?** | ✅ Yes | ❌ No |
| **Use case** | CODE templates | DOC/TRACKING templates |
| **Rationale** | System breaks if violated | Best practices |
| **When validated** | safe_edit, scaffold, quality_gates | safe_edit, scaffold, quality_gates |
| **Example rules** | Base class, required methods | Numbered sections, pros/cons |
| **Template field** | `validates.strict` | `validates.guidelines` |
| **Score impact** | 0.0 if violated | 0.8 if violated |
| **Agent hints** | No (technical, clear-cut) | Yes (guidance needed) |

---

### Complete Tier → Enforcement Mapping

```
tier0_base_artifact.jinja2
├── enforcement: STRICT
├── level: format
└── validates: SCAFFOLD comment format (universal across ALL artifacts)

tier1_base_code.jinja2 / tier1_base_document.jinja2 / tier1_base_tracking.jinja2
├── enforcement: STRICT
├── level: format
└── validates: Universal structure (imports/docstrings for code, sections for docs)

tier2_base_python.jinja2 / tier2_base_markdown.jinja2 / tier2_tracking_text.jinja2
├── enforcement: STRICT
├── level: format
└── validates: Language syntax (Python/Markdown/plain text specific)

concrete/worker.py.jinja2 / dto.py.jinja2 / adapter.py.jinja2
├── enforcement: ARCHITECTURAL
├── level: content
├── validates.strict: Base class, required methods, imports (ERROR)
└── validates.guidelines: Naming, docstring format (WARNING)

concrete/design.md.jinja2 / research.md.jinja2 / architecture.md.jinja2
├── enforcement: GUIDELINE
├── level: content
├── validates.guidelines: Numbered sections, content type (WARNING)
└── agent_hint: "Focus on WHY, not HOW"

concrete/commit.txt.jinja2 / pr.md.jinja2 / issue.md.jinja2
├── enforcement: GUIDELINE
├── level: content
├── validates.guidelines: Message format, length, references (WARNING)
└── agent_hint: "Commit messages explain WHY change was made"
```

---

### Validation Flow Example (Complete)

**Scaffolding design.md:**
```python
scaffold_artifact(
    artifact_type="design",
    name="multi-tier-templates",
    context={
        "title": "Issue #72 Multi-Tier Template Design",
        "status": "DRAFT",
        "purpose": "...",
        # ... more context
    }
)
```

**LayeredTemplateValidator execution:**

1. **Load metadata chain:**
   ```
   concrete/design.md.jinja2 
   → tier2_base_markdown.jinja2 
   → tier1_base_document.jinja2
   → tier0_base_artifact.jinja2
   ```

2. **Merge metadata:**
   ```python
   {
       "enforcement": "GUIDELINE",  # From concrete (child wins)
       "validates": {
           "strict": [
               "SCAFFOLD comment present",      # tier0
               "## Purpose section exists",     # tier1
               "# H1 title present"            # tier2
           ],
           "guidelines": [
               "Use numbered sections",         # concrete
               "Include pros/cons"             # concrete
           ]
       }
   }
   ```

3. **Validate STRICT format (tier0+tier1+tier2):**
   - Check SCAFFOLD comment → ERROR if missing → STOP
   - Check Purpose section → ERROR if missing → STOP
   - Check H1 title → ERROR if missing → STOP

4. **Validate GUIDELINE content (concrete):**
   - Check numbered sections → WARNING if missing → CONTINUE
   - Check pros/cons → WARNING if missing → CONTINUE

5. **Return result:**
   ```python
   ValidationResult(
       passed=True,
       score=1.0 if no warnings else 0.8,
       issues=[...warnings only...],
       agent_hint="Design docs focus on decision rationale..."
   )
   ```

---

### Consistency Verification

✅ **tier0 + tier1 + tier2 = STRICT format (Issue #52 Tier 1)**
- All validate format, not content
- All block on ERROR
- No agent hints needed (technical, objective)

✅ **CODE concrete = ARCHITECTURAL (Issue #52 Tier 2 strict)**
- Validates system-critical structure
- Blocks on ERROR (validates.strict)
- Allows WARNING (validates.guidelines)

✅ **DOC/TRACKING concrete = GUIDELINE (Issue #52 Tier 3)**
- Validates best practices only
- Never blocks (WARNING only)
- Provides agent hints

✅ **Metadata merging:**
- Child enforcement overrides parent
- Strict rules concatenate (tier0 + tier1 + tier2 + concrete)
- Guidelines concatenate (all levels)

---

### Key Takeaway

**Issue #72 extends Issue #52 with language-agnostic tier1:**

- **Issue #52:** base_template.py/base_template.md (language-specific)
- **Issue #72:** tier1_base_document (universal) + tier2_base_markdown (language-specific)

This enables:
```
tier1_base_document
├── tier2_base_markdown → concrete/design.md
├── tier2_base_rst → concrete/design.rst (future)
└── tier2_base_asciidoc → concrete/design.adoc (future)
```

**All share tier1 structure validation, only tier2 changes per language.**

---

## Validation Against Issue #52 Design

### Issue #52 Three-Tier Enforcement Model

**From [issue52/design.md](../issue52/design.md):**

```
Tier 1 (Base Template Format): STRICT
  - Import order, docstrings, type hints, file structure
  - Severity: ERROR (blocks save)
  - Source: Base templates (base_component.py, base_document.md)

Tier 2 (Architectural Rules): STRICT
  - Base class inheritance, required methods, protocol compliance
  - Severity: ERROR (blocks save)
  - Source: Specific templates strict section

Tier 3 (Guidelines): LOOSE
  - Naming conventions, field ordering, docstring format
  - Severity: WARNING (saves with notification)
  - Source: Specific templates guidelines section
```

### Mapping Issue #72 Template Tiers to Issue #52 Validation Tiers

**CRITICAL DISTINCTION:**
- **Issue #72 tiers** = Template inheritance hierarchy (tier0 → tier1 → tier2 → concrete)
- **Issue #52 tiers** = Validation enforcement levels (STRICT → ARCHITECTURAL → GUIDELINE)

**These are ORTHOGONAL concerns:**

| Issue #72 Template Tier | Issue #52 Validation Level | TEMPLATE_METADATA Field |
|------------------------|----------------------------|------------------------|
| **tier1_base_document** | Tier 1: STRICT Format | `enforcement: STRICT` + `level: format` |
| **tier2_base_markdown** | Tier 1: STRICT Format | `enforcement: STRICT` + `level: format` |
| **concrete/design.md** | Tier 2: ARCHITECTURAL | `enforcement: ARCHITECTURAL` + `level: content` |

### Validation Metadata in Each Template Tier

#### tier1_base_document.jinja2
```jinja2
{#-
TEMPLATE_METADATA:
  enforcement: STRICT
  level: format
  validates:
    strict:
      - "## Purpose section exists"
      - "## Scope section exists"
      - "**Status:** field present"
      - "## Version History table exists"
  purpose: "Universal document structure for all knowledge docs"
  version: "1.0.0"
-#}
```

**Rationale:**
- **STRICT enforcement** because ALL documents MUST have these sections
- **Format level** because this is structural, not content-specific
- **Issue #52 Tier 1:** Base template format validation

---

#### tier2_base_markdown.jinja2
```jinja2
{#-
TEMPLATE_METADATA:
  enforcement: STRICT
  level: format
  validates:
    strict:
      - "<!-- SCAFFOLD: comment present"
      - "# H1 title present"
      - "Link definitions use [id]: url format"
  extends: tier1_base_document.jinja2
  purpose: "Markdown language syntax for documents"
  version: "1.0.0"
-#}
```

**Rationale:**
- **STRICT enforcement** because Markdown syntax MUST be correct
- **Format level** because this is language syntax, not content
- **Issue #52 Tier 1:** Base template format validation (language-specific)

---

#### concrete/design.md.jinja2
```jinja2
{#-
TEMPLATE_METADATA:
  enforcement: ARCHITECTURAL
  level: content
  validates:
    strict:
      - "## 1. Context & Requirements section exists"
      - "## 2. Design Options section exists"
      - "## 3. Chosen Design section exists"
    guidelines:
      - "Use numbered sections for decision flow"
      - "Include pros/cons for each option"
      - "Provide decision rationale"
  extends: tier2_base_markdown.jinja2
  purpose: "Design document with decision structure"
  version: "1.0.0"
  content_guidance:
    sections:
      - name: "Context & Requirements"
        required_subsections: ["Problem Statement", "Requirements", "Constraints"]
      - name: "Design Options"
        format: "numbered_subsections"
      - name: "Chosen Design"
        required_fields: ["Decision", "Rationale"]
  agent_hint: "Design documents focus on decision rationale, not implementation details"
-#}
```

**Rationale:**
- **ARCHITECTURAL enforcement** because design structure is system-critical
- **Content level** because this validates document content, not format
- **Issue #52 Tier 2:** Architectural validation (design-specific)
- **Guidelines:** Tier 3 validation (warnings only)

---

### Validation Flow Example

**Scaffolding a design document:**
```python
scaffold_artifact(
    artifact_type="design",
    name="multi-tier-templates",
    context={
        "title": "Issue #72 Multi-Tier Template Design",
        "status": "DRAFT",
        "version": "1.0",
        "purpose": "...",
        "scope_in": [...],
        "scope_out": [...],
        "problem_statement": "...",
        "functional_requirements": [...],
        "design_options": [...]
    }
)
```

**LayeredTemplateValidator runs:**

1. **Load metadata chain:**
   - concrete/design.md.jinja2 → tier2_base_markdown → tier1_base_document
   - Merge metadata (child overrides parent, strict rules concatenate)

2. **Validate Tier 1 (STRICT Format):**
   - From tier1_base_document: Check Purpose, Scope, Status, Version History
   - From tier2_base_markdown: Check SCAFFOLD comment, H1 title, link format
   - **Result:** ERROR if missing → STOP

3. **Validate Tier 2 (ARCHITECTURAL):**
   - From concrete/design: Check numbered sections (1. Context, 2. Options, 3. Decision)
   - **Result:** ERROR if missing → STOP

4. **Validate Tier 3 (GUIDELINES):**
   - From concrete/design: Check pros/cons present, decision rationale exists
   - **Result:** WARNING if missing → CONTINUE

5. **Return ValidationResult:**
   ```python
   ValidationResult(
       passed=True,
       score=1.0,
       issues=[],
       agent_hint="Design documents focus on decision rationale..."
   )
   ```

---

### Consistency Verification

✅ **Issue #52 Tier 1 (STRICT Format) maps to:**
- Issue #72 tier1_base_document (universal structure)
- Issue #72 tier2_base_markdown (language syntax)

✅ **Issue #52 Tier 2 (ARCHITECTURAL) maps to:**
- Issue #72 concrete templates (document-type structure)

✅ **Issue #52 Tier 3 (GUIDELINES) maps to:**
- TEMPLATE_METADATA.validates.guidelines in concrete templates

✅ **Inheritance merging:**
- TemplateAnalyzer.merge_metadata() concatenates strict rules
- Child enforcement level can override parent (ARCHITECTURAL > STRICT)

✅ **Agent hints:**
- Concrete templates provide agent_hint and content_guidance
- ValidationResult includes these fields

---

### Potential Issues & Resolutions

**Issue 1: Enforcement level inheritance**

**Problem:** If tier1 says `enforcement: STRICT` and concrete says `enforcement: ARCHITECTURAL`, which wins?

**Resolution:** Child wins (concrete overrides tier1), BUT strict rules concatenate:
```python
# Merged metadata
{
    "enforcement": "ARCHITECTURAL",  # From concrete (child wins)
    "validates": {
        "strict": [
            "## Purpose exists",  # From tier1
            "## 1. Context exists"  # From concrete (both enforced)
        ]
    }
}
```

---

**Issue 2: tier2_base_markdown has `enforcement: STRICT`, but is that format or content?**

**Resolution:** tier2 validates **format** (Markdown syntax), not content:
```yaml
TEMPLATE_METADATA:
  enforcement: STRICT
  level: format  # ← KEY: This is format validation, not content
```

This allows:
- tier1 (STRICT format) + tier2 (STRICT format) → both format-level
- concrete (ARCHITECTURAL content) → content-level

No conflict because tier1+tier2 validate format, concrete validates content.

---

**Issue 3: Do we need separate tier1_base_document and tier2_base_markdown validation?**

**Answer:** YES, they validate different aspects:
- tier1: Document structure (sections exist, header metadata present)
- tier2: Markdown syntax (comment format, heading format, link format)

**Example failure scenarios:**
- Missing Purpose section → tier1 STRICT format ERROR
- Wrong comment syntax (`// SCAFFOLD` instead of `<!-- SCAFFOLD -->`) → tier2 STRICT format ERROR
- Missing numbered sections → concrete ARCHITECTURAL content ERROR

All three are orthogonal validation concerns.

---

### Conclusion

✅ **Issue #72 tier allocation is CONSISTENT with Issue #52 validation design:**

1. Template inheritance (tier0→tier1→tier2→concrete) is separate from validation enforcement (STRICT→ARCHITECTURAL→GUIDELINE)
2. tier1+tier2 provide STRICT format validation (Issue #52 Tier 1)
3. Concrete templates provide ARCHITECTURAL content validation (Issue #52 Tier 2)
4. Guidelines in concrete templates provide WARNING-only validation (Issue #52 Tier 3)
5. TEMPLATE_METADATA merging follows Issue #52 merge rules (concatenate strict, child overrides)

**No conflicts detected. Design is consistent.**

---

## Related Documents

- [design.md](design.md) - Multi-tier template architecture (full spec)
- [tracking-type-architecture.md](tracking-type-architecture.md) - Tracking artifact type decision
- `docs/reference/templates/BASE_TEMPLATE.md` - Legacy base structure (source of truth for sections)
- `docs/reference/templates/DESIGN_TEMPLATE.md` - Legacy design structure (numbered sections)
- `.st3/artifacts.yaml` - Artifact registry (template_path definitions)

# docs/reference/{category}/{COMPONENT_NAME}.md
# {Component} Reference

<!--
REFERENCE TEMPLATE - Extends BASE_TEMPLATE
Purpose: Post-implementation reference documentation (300-600 lines)

Inherits from BASE:
├── Header (Status, Version, Last Updated)
├── Purpose, Scope, Prerequisites
├── Related Documentation + Link definitions
└── Version History

Adds:
├── Header: Source, Tests
├── Unnumbered categorical sections
├── API Reference with signatures
└── Usage examples (working code)

Rules:
├── Always link to source file
├── Include test file reference
├── Status is always DEFINITIVE
└── Examples must be working code
-->

<!-- ═══════════════════════════════════════════════════════════════════════════
     HEADER SECTION (from BASE + Reference-specific fields)
     ═══════════════════════════════════════════════════════════════════════════ -->

**Status:** DEFINITIVE  
**Version:** {X.Y}  
**Last Updated:** {YYYY-MM-DD}  

**Source:** [{component_name}.py][source]  
**Tests:** [{test_component_name}.py][tests] ({X} tests)  

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTEXT SECTION (from BASE)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Purpose

{One paragraph describing:
- What this component does
- Where it fits in the architecture
- Key responsibility (single sentence)}

## Scope

**In Scope:**
- {What this reference covers}
- {API details included}

**Out of Scope:**
- Design rationale → See [{DESIGN_DOC.md}][design]
- Architectural context → See [{ARCHITECTURE.md}][arch]

## Prerequisites

[OPTIONAL - delete if no prior reading required]

Read these first:
1. [{ARCHITECTURE_DOC.md}][prereq-1] - Understand the concept
2. [{RELATED_REFERENCE.md}][prereq-2] - Related component

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     CONTENT SECTION (REFERENCE-SPECIFIC: unnumbered, API style)
     ═══════════════════════════════════════════════════════════════════════════ -->

## API Reference

### Constructor

```python
def __init__(self, param1: Type1, param2: Type2) -> None:
    """Initialize component."""
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `param1` | `Type1` | Yes | Description |
| `param2` | `Type2` | No | Description (default: `value`) |

### Methods

#### `method_name()`

```python
def method_name(self, arg: ArgType) -> ReturnType:
    """Brief description."""
```

**Returns:** `ReturnType` - Description

**Raises:**
- `ExceptionType`: When {condition}

---

## Usage Examples

### Basic Usage

```python
from backend.path.to.component import Component

component = Component(param1="value1")
result = component.method_name(arg=some_value)
```

### {Specific Use Case}

```python
# Example for specific scenario
...
```

---

## Field Reference

[FOR DTOs - delete section if not applicable]

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `field1` | `str` | Yes | Description |
| `field2` | `int` | No | Description (default: `0`) |

---

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| `ValidationError` | {when raised} | {how to fix} |

---

## Testing

**Test File:** [{test_component.py}][tests]  
**Coverage:** {X}% ({Y} tests)

```powershell
pytest tests/unit/path/to/test_component.py -v
```

---

<!-- ═══════════════════════════════════════════════════════════════════════════
     FOOTER SECTION (from BASE)
     ═══════════════════════════════════════════════════════════════════════════ -->

## Related Documentation

- **[{ARCHITECTURE.md}][arch]** - Why this component exists
- **[{DESIGN.md}][design]** - Original design decisions
- **[{RELATED_COMPONENT.md}][related]** - Related component

<!-- Link definitions -->

[source]: ../../backend/path/to/component.py "Source implementation"
[tests]: ../../tests/unit/path/to/test_component.py "Unit tests"
[arch]: ../architecture/RELEVANT.md "Architecture context"
[design]: ../development/COMPONENT_DESIGN.md "Design document"
[prereq-1]: ../architecture/RELEVANT.md "Architecture"
[prereq-2]: ./related_component.md "Related reference"
[related]: ./related_component.md "Related component"

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| {X.Y} | {YYYY-MM-DD} | {Name/AI} | {Brief description} |
| 1.0 | {YYYY-MM-DD} | {Name/AI} | Initial reference |

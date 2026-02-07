<!-- docs/reference/mcp/TEMPLATE_LIBRARY_PATTERNS.md -->
<!-- template=reference version=064954ea created=2026-02-07T00:00Z updated= -->
# Template Library Pattern Guide (Tier 3) - S1mpleTraderV3


**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-07  

**Source:** [mcp_server/scaffolding/templates/][source]  
**Tests:** [tests/integration/test_metadata_e2e.py][tests]  

---

## Purpose

Catalog the Tier 3 pattern templates (block library) and explain how to compose them via {% import %}.

## Scope

**In Scope:**
['Tier 3 pattern templates under mcp_server/scaffolding/templates/tier3_pattern_*', 'Macro names provided by each pattern', 'Typical consumption points (imports, sections, helper snippets)']

**Out of Scope:**
['Tier 0–2 base template structure → See docs/architecture/TEMPLATE_LIBRARY.md', 'Concrete template specifics per artifact type → See mcp_server/scaffolding/templates/concrete/*']

---

## API Reference

### Tier 3 pattern templates

Tier 3 templates are macro libraries imported into concrete templates. Each pattern is small (SRP) and optionally composed.

**Methods:**

- `{% import "tier3_pattern_..." as alias %}`
  - **Parameters:** alias: macro namespace; pattern selection is explicit
  - **Returns:** Macros available under alias.*

---

## Usage Examples

**Example import + macro call (Jinja2)**

```python
{% import "tier3_pattern_python_logging.jinja2" as p_logging %}

{{ p_logging.pattern_logging_imports() }}
```

## Related Documentation
- **[docs/architecture/TEMPLATE_LIBRARY.md][related-1]**
- **[docs/reference/mcp/TEMPLATE_LIBRARY_USAGE.md][related-2]**

<!-- Link definitions -->

[related-1]: docs/architecture/TEMPLATE_LIBRARY.md
[related-2]: docs/reference/mcp/TEMPLATE_LIBRARY_USAGE.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-07 | Agent | Initial draft |
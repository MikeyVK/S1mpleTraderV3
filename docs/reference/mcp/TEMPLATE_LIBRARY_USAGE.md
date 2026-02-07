<!-- docs/reference/mcp/TEMPLATE_LIBRARY_USAGE.md -->
<!-- template=reference version=064954ea created=2026-02-07T00:00Z updated= -->
# Template Library Usage Guide - S1mpleTraderV3


**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-07  

**Source:** [mcp_server/tools/scaffold_artifact.py][source]  
**Tests:** [tests/integration/mcp_server/test_scaffold_tool_execute_e2e.py][tests]  

---

## Purpose

Practical guide for using and extending the multi-tier Jinja2 template library that powers scaffold_artifact.

## Scope

**In Scope:**
['Scaffolding an artifact type (using the MCP tool)', 'How artifact types map to templates (.st3/artifacts.yaml)', 'How to cherry-pick Tier 3 patterns via {% import %}', 'How provenance is recorded (.st3/template_registry.json)', 'Adding a new Tier 3 pattern (SRP)', 'Adding a new Tier 2 language/syntax or Tier 1 format']

**Out of Scope:**
['Full TEMPLATE_METADATA format → See docs/reference/mcp/template_metadata_format.md', 'Deep architecture rationale → See docs/architecture/TEMPLATE_LIBRARY.md']

---

## API Reference

### scaffold_artifact (MCP tool)

Unified tool to scaffold any registered artifact type (code or document). Resolves a template via .st3/artifacts.yaml, renders via Jinja2, injects SCAFFOLD provenance, and updates .st3/template_registry.json.

**Methods:**

- `scaffold_artifact(artifact_type: str, name: str, output_path: str | None = None, context: dict | None = None)`
  - **Parameters:** artifact_type: registry type_id; name: PascalCase (code) / kebab-case (docs); output_path: override file location; context: template variables
  - **Returns:** Path to scaffolded artifact

---

## Usage Examples

**Minimal usage (pseudo-Python dict for MCP client call)**

```python
{
  "artifact_type": "worker",
  "name": "process-worker",
  "output_path": "backend/workers/ProcessWorker.py",
  "context": {
    "layer": "Backend (Workers)",
    "module_description": "Processes incoming events"
  }
}
```

## Related Documentation
- **[docs/architecture/TEMPLATE_LIBRARY.md][related-1]**
- **[docs/reference/mcp/TEMPLATE_LIBRARY_PATTERNS.md][related-2]**
- **[docs/reference/mcp/template_metadata_format.md][related-3]**

<!-- Link definitions -->

[related-1]: docs/architecture/TEMPLATE_LIBRARY.md
[related-2]: docs/reference/mcp/TEMPLATE_LIBRARY_PATTERNS.md
[related-3]: docs/reference/mcp/template_metadata_format.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-07 | Agent | Initial draft |
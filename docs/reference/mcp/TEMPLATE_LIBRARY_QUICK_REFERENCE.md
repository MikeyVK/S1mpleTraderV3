<!-- docs/reference/mcp/TEMPLATE_LIBRARY_QUICK_REFERENCE.md -->
<!-- template=reference version=064954ea created=2026-02-07T00:00Z updated= -->
# Template Library Quick Reference - S1mpleTraderV3


**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-07  

**Source:** [mcp_server/scaffolding/templates/][source]  
**Tests:** [tests/integration/test_metadata_e2e.py][tests]  

---

## API Reference

### Master Template Inventory

Templates root: `mcp_server/scaffolding/templates/`

| Tier | Purpose | Location / Prefix |
|------|---------|-------------------|
| 0 | Universal provenance header | `tier0_*` |
| 1 | Format structure (CODE/DOCUMENT/TRACKING/CONFIG) | `tier1_*` |
| 2 | Language/syntax framing | `tier2_*` |
| 3 | Pattern macro libraries (SRP) | `tier3_pattern_*` |
| Concrete | Artifact outputs | `concrete/*` |

Registry/provenance: `.st3/template_registry.json` (hash → tier chain).

### Element Flow Tables

### CODE

| Element | Tier responsibility |
|---------|---------------------|
| SCAFFOLD header | Tier 0 |
| Module docstring + imports/class skeleton | Tier 1 |
| Python language syntax specifics | Tier 2 |
| Optional architectural patterns (logging/DI/async/...) | Tier 3 (`{% import %}`) |
| Artifact-specific behavior (worker/tool/dto/service) | Concrete |

### DOCUMENT

| Element | Tier responsibility |
|---------|---------------------|
| SCAFFOLD header | Tier 0 |
| BASE_TEMPLATE structure (Purpose/Scope/etc) | Tier 1 |
| Markdown link-definitions/code-block patterns | Tier 2 |
| Optional doc patterns (status header, related docs, agent hints, etc.) | Tier 3 (`{% import %}`) |
| Doc-specific sections (architecture numbered concepts, design options, etc.) | Concrete |

### TRACKING

| Element | Tier responsibility |
|---------|---------------------|
| SCAFFOLD header | Tier 0 |
| Tracking-specific structure | Tier 1 tracking |
| Markdown/text tracking syntax | Tier 2 tracking |
| (Typically no tier3 patterns needed) | N/A |
| commit/pr/issue templates | Concrete |

### Pattern Cherry-Picking Table

| Concrete template | Typical Tier 3 imports |
|------------------|------------------------|
| `concrete/worker.py.jinja2` | async, lifecycle, error, logging, di, log_enricher, translator |
| `concrete/tool.py.jinja2` | error, logging |
| `concrete/dto.py.jinja2` | pydantic, typed_id |
| `concrete/service_command.py.jinja2` | async, error, logging, translator, di |
| `concrete/test_unit.py.jinja2` | pytest, test_structure, async, mocking |
| `concrete/test_integration.py.jinja2` | pytest, test_structure, async |

### Validation Hierarchy Table

| Tier | Enforcement | Intent |
|------|-------------|--------|
| Tier 0–2 | STRICT | Non-negotiable structure/syntax foundation |
| Tier 3 patterns | ARCHITECTURAL | Enforce architectural presence when a pattern is chosen |
| Concrete templates | GUIDELINE | Helpful defaults; allow pragmatic variation |


---

## Usage Examples

**Find the tier chain for a file**

```python
1) Open a scaffolded file and locate its `SCAFFOLD: <type>:<version_hash> | ...` header.
2) Look up `<version_hash>` in `.st3/template_registry.json`.
3) Read the tier chain entries (template_id + version per tier).
```

## Related Documentation
None
---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-07 | Agent | Initial draft |
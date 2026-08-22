<!-- docs/reference/mcp/tools/scaffolding.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-06-02 -->
# Scaffolding Tools

**Status:** DEFINITIVE  
**Version:** 3.3  
**Last Updated:** 2026-08-22  

**Source:** [mcp_server/tools/scaffold_artifact.py](../../../mcp_server/tools/scaffold_artifact.py) | [mcp_server/tools/scaffold_schema_tool.py](../../../mcp_server/tools/scaffold_schema_tool.py)  
**Tests:** [tests/mcp_server/unit/tools/test_scaffold_schema_tool.py](../../../tests/mcp_server/unit/tools/test_scaffold_schema_tool.py)

---

## Purpose

Complete reference documentation for the two MCP scaffolding tools: `scaffold_artifact` (artifact generation from templates) and `scaffold_schema` (proactive context schema discovery). Both tools use the same modular artifact registry defined under [.pgmcp/templates/config/](../../../.pgmcp/templates/config/).

The scaffolding system provides:
- **Unified tool** for code and documentation generation (replaces separate tools)
- **Template composition** via Jinja2 includes and inheritance
- **Automatic directory resolution** from [.pgmcp/config/project_structure.yaml](../../../.pgmcp/config/project_structure.yaml)
- **SCAFFOLD header injection** for template provenance tracking
- **Context-driven customization** via template variables
- **Proactive schema exposure** via `scaffold_schema` — inspect context requirements before scaffolding

---

## Overview

The MCP server provides **2 scaffolding tools**:

| Tool | Purpose | Artifact Types |
|------|---------|----------------|
| `scaffold_artifact` | Generate code/docs from templates | 21 types (including adapter, resource, interface, validation_report, generic_doc, etc.) |
| `scaffold_schema` | Return JSON Schema for context parameter | Artifact types in the three-layer scaffolding architecture |


**Supported Artifact Categories:**
- **Code Artifacts:** `dto`, `worker`, `adapter`, `tool`, `resource`, `schema`, `interface`, `service`, `generic`, `unit_test`, `integration_test`
- **Document Artifacts:** `design`, `architecture`, `research`, `planning`, `reference`, `validation_report`, `generic_doc`
- **Tracking Artifacts:** `commit`, `pr`, `issue`


---

## API Reference

### scaffold_artifact

**MCP Name:** `scaffold_artifact`  
**Class:** `ScaffoldArtifactTool`  
**File:** [mcp_server/tools/scaffold_artifact.py](../../../mcp_server/tools/scaffold_artifact.py)

Generate any artifact type (code or document) from unified registry.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artifact_type` | `str` | **Yes** | Artifact type ID from registry (e.g., `\"dto\"`, `\"design\"`, `\"worker\"`). The available values are populated at runtime from the modular configurations under `.pgmcp/templates/config/`. |
| `name` | `str` | **Yes** | Artifact name — PascalCase for code, kebab-case for docs |
| `output_path` | `str` | No | Explicit output path. **Optional** — auto-resolved by ArtifactManager via `project_structure.yaml`. Provide only as override. Optional for ephemeral artifacts (`issue`, `tracking`, …) — when provided, artifact is written there instead of `.pgmcp/temp/`. |
| `context` | `dict` | No | Template rendering context (varies by artifact type) — default: `{}` |

#### Returns (via MCP Resource Cache)

On success, `scaffold_artifact` presents the artifact type and name plus up to 20 paths
from `files_created`. On context-validation failure, it presents the error and bounded
`missing_fields` and `provided_fields` collections. Other failures use the configured
scalar failure template.

The DTO is stored in the MCP Resource cache at `pgmcp://cache/runs/{run_id}` and contains the following fields:
- `success`: `bool`
- `error_message`: `string | null`
- `post_tool_instruction`: `string | null`
- `artifact_type`: `string`
- `name`: `string`
- `files_created`: `list[string]`
- `validation_schema`: `dict | null`
- `missing_fields`: `list[string]`
- `provided_fields`: `list[string]`

The complete validation schema remains cache-only. No duplicate preformatted file or
schema summary fields exist.

#### Example Usage

**Scaffold DTO:**
```json
{
  "artifact_type": "dto",
  "name": "OrderDTO",
  "output_path": "backend/dtos/OrderDTO.py",
  "context": {
    "dto_name": "OrderDTO",
    "fields": ["id: int", "user_id: int", "total: Decimal"]
  }
}
```

**Scaffold Worker:**
```json
{
  "artifact_type": "worker",
  "name": "OrderProcessingWorker",
  "context": {
    "description": "Processes orders asynchronously",
    "methods": [
      {"name": "validate_order", "params": "order: OrderDTO", "returns": "bool"},
      {"name": "calculate_total", "params": "items: list[OrderItem]", "returns": "Decimal"}
    ]
  }
}
```

**Scaffold Design Document:**
```json
{
  "artifact_type": "design",
  "name": "oauth-design",
  "context": {
    "title": "OAuth 2.0 Integration Design",
    "summary": "Design document for integrating OAuth 2.0 authentication",
    "purpose": "Define the architecture and flows for the new auth system"
  }
}
```

**Scaffold Architecture Document:**
```json
{
  "artifact_type": "architecture",
  "name": "worker-pattern",
  "context": {
    "pattern_name": "Async Worker Pattern",
    "description": "Design for asynchronous background task processing",
    "use_cases": ["Order processing", "Email notifications", "Report generation"]
  }
}
```

#### Naming Conventions

| Artifact Category | Name Format | Example |
|-------------------|-------------|---------|
| Code (DTO, worker, adapter, tool, service) | PascalCase | `OrderDTO`, `ProcessOrderWorker` |
| Documentation (design, architecture, etc.) | kebab-case | `oauth-design`, `worker-pattern-architecture` |

---

### scaffold_schema

**MCP Name:** `scaffold_schema`  
**Class:** `ScaffoldSchemaTool`  
**File:** [mcp_server/tools/scaffold_schema_tool.py](../../../mcp_server/tools/scaffold_schema_tool.py)  
**Implements:** `ICoreTool` (read-only — no branch mutation)

Return the JSON Schema for the `context` parameter of an artifact type. Use this before calling `scaffold_artifact` to discover exactly which fields are required and optional for a given type.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artifact_type` | `str` | **Yes** | Artifact type ID from registry. The available values are populated at runtime from `.pgmcp/templates/config/`. |

#### Returns (via MCP Resource Cache)

`scaffold_schema` deliberately presents only the successful artifact-type lookup and the
cache link. The nested schema is resource-oriented and is not flattened into chat text.

The DTO is stored in the MCP Resource cache at `pgmcp://cache/runs/{run_id}` and contains:
- `success`: `bool`
- `error_message`: `string | null`
- `post_tool_instruction`: `string | null`
- `artifact_type`: `string`
- `schema_data`: `dict` (the JSON Schema describing the `context` parameter)
#### Error Handling

| Condition | Response |
|-----------|----------|
| Type without registered Context schema | `is_error=true` — "No Context schema registered for type: <type>" |
| Unknown type | `is_error=true` — type not in registry |

#### Recommended Workflow

Call `scaffold_schema` to inspect required and optional fields before calling `scaffold_artifact`:

1. `scaffold_schema(artifact_type="design")` → returns full JSON Schema for `DesignContext`
2. Build complete context dict from required and optional fields in the schema
3. `scaffold_artifact(artifact_type="design", name="my-design", context={...})` → first-time-right

This eliminates trial-and-error context validation failures.

**Note:** `scaffold_artifact` also exposes the full JSON Schema in its error response when context validation fails. `scaffold_schema` is the proactive alternative for inspecting the schema before the first call.

---
## Artifact Registry


The unified artifact registry is defined by modular YAML configuration files under [.pgmcp/templates/config/](../../../.pgmcp/templates/config/).


### Registry Structure

The registry is loaded from individual `.yaml` files under `.pgmcp/templates/config/`. Each file defines at minimum: `type_id`, `name`, `description`, `template_path`, `file_extension`, `strict_validation`, and the `context_schema`.

**See:** [.pgmcp/templates/config/](../../../.pgmcp/templates/config/) for the configuration files.

### Supported Artifact Types

#### Code Artifacts (12 types)

| ID | Template | Description |
|----|----------|-------------|
| `dto` | `concrete/dto.py.jinja2` | Data Transfer Objects (frozen Pydantic models) |
| `typescript_dto` | `concrete/typescript_dto.ts.jinja2` | TypeScript Data Transfer Objects |
| `worker` | `concrete/worker.py.jinja2` | Async background workers |
| `adapter` | `concrete/adapter.py.jinja2` | Adapter classes |
| `tool` | `concrete/tool.py.jinja2` | MCP server tools |
| `resource` | `concrete/resource.py.jinja2` | Resource classes |
| `schema` | `concrete/config_schema.py.jinja2` | Configuration schema classes |
| `interface` | `concrete/interface.py.jinja2` | Interface / protocol classes |
| `service` | `concrete/service_command.py.jinja2` | Service layer classes |
| `generic` | `concrete/generic.py.jinja2` | Generic Python classes (catch-all) |
| `unit_test` | `concrete/test_unit.py.jinja2` | Unit test modules |
| `integration_test` | `concrete/test_integration.py.jinja2` | Integration test modules |

#### Document Artifacts (7 types)

| ID | Template | Description |
|----|----------|-------------|
| `research` | `concrete/research.md.jinja2` | Research documents |
| `planning` | `concrete/planning.md.jinja2` | Implementation planning documents |
| `design` | `concrete/design.md.jinja2` | Feature/bug design documents |
| `architecture` | `concrete/architecture.md.jinja2` | Architecture documents |
| `reference` | `concrete/reference.md.jinja2` | API/tool reference documents |
| `validation_report` | `concrete/validation_report.md.jinja2` | Validation report documents |
| `generic_doc` | `concrete/generic.md.jinja2` | Generic markdown documents |

#### Tracking Artifacts (3 types)

| ID | Template | Description |
|----|----------|-------------|
| `commit` | `concrete/commit.txt.jinja2` | Commit message templates |
| `pr` | `concrete/pr.md.jinja2` | Pull request descriptions |
| `issue` | `concrete/issue.md.jinja2` | Issue descriptions |



## Template System

Templates are organized in a tier hierarchy within `.pgmcp/templates/`. See [docs/manuals/architecture.md](../../manuals/architecture.md) for full architecture details.

### Template Location

Templates root: `.pgmcp/templates/`

```
.pgmcp/templates/
├── concrete/          ← artifact-specific output templates
│   ├── dto.py.jinja2
│   ├── worker.py.jinja2
│   ├── design.md.jinja2
│   └── ...
├── tier0_base_artifact.jinja2
├── tier1_base_code.jinja2
├── tier1_base_document.jinja2
├── tier2_base_python.jinja2
├── tier2_base_markdown.jinja2
└── tier3_pattern_*.jinja2  ← composable macro libraries
```

### Template Composition

Concrete templates extend the appropriate tier 2 base (`{% extends %}`) and import optional pattern libraries (`{% import %}`). Every concrete template contains a `TEMPLATE_METADATA` block that is the authoritative variable contract for that type.

### Context Variables

Each artifact type defines its required and optional context fields in the declarative `context_schema` under `.pgmcp/templates/config/<type>.yaml`. Use `scaffold_schema(artifact_type=\"<type>\")` to retrieve the full JSON Schema before scaffolding.

```json
{
  "artifact_type": "dto",
  "name": "OrderDTO",
  "output_path": "custom/path/order_dto.py"
}
```

**Resolved path:** `custom/path/order_dto.py` (explicit override)

---

## SCAFFOLD Headers

All generated artifacts include a SCAFFOLD header for template provenance tracking:

**Code Artifact Header:**
```python
# backend/dtos/order_dto.py
# template=dto version=a3b5c7d9 created=2026-02-08T12:00:00+01:00 updated=
```

**Documentation Artifact Header:**
```markdown
<!-- docs/design/oauth-integration.md -->
<!-- template=design version=a3b5c7d9 created=2026-02-08T12:00:00+01:00 updated= -->
# OAuth2 Integration Design
```

**Header Fields:**
- `template` — Template ID from the configuration
- `version` — Template version hash (8-char SHA from template content)
- `created` — ISO 8601 timestamp when artifact was scaffolded
- `updated` — ISO 8601 timestamp of last update (empty when first created)

**Purpose:**
- Track which template generated the artifact
- Enable template conformance validation via `validate_template` tool
- Support template upgrade migrations

---

## Template Tiers

Templates are organized into tiers based on complexity and composition depth:

| Tier | Description | Examples |
|------|-------------|----------|
| **Tier 0** | Base templates (no dependencies) | `dto`, `base` |
| **Tier 1** | Templates with includes | `worker`, `adapter`, `design` |
| **Tier 2** | Templates with inheritance | `tool`, `architecture` |

Tier information is stored in the modular configurations and `template_registry.json`.

---

## Anti-Patterns & Common Mistakes

### 1. Wrong Name Format

**❌ WRONG:**
```json
{
  "artifact_type": "dto",
  "name": "order-dto"  // kebab-case for code artifact
}
```

**✅ CORRECT:**
```json
{
  "artifact_type": "dto",
  "name": "OrderDTO"  // PascalCase for code artifact
}
```

---

### 2. Missing Required Context

**❌ WRONG:**
```json
{
  "artifact_type": "dto",
  "name": "OrderDTO"
  // Missing "fields" in context
}
```

**✅ CORRECT:**
```json
{
  "artifact_type": "dto",
  "name": "OrderDTO",
  "context": {
    "fields": [
      {"name": "id", "type": "int"}
    ]
  }
}
```


---

## Configuration

### .pgmcp/templates/config/

Complete modular artifact registry with template mappings, context schemas, and tier information.

**See:** [.pgmcp/templates/config/](../../../.pgmcp/templates/config/) for the configuration files.

---

### .pgmcp/config/project_structure.yaml

Directory resolution rules for artifact types.

**See:** [.pgmcp/config/project_structure.yaml](../../../.pgmcp/config/project_structure.yaml) for full structure.

---

### .pgmcp/config/scaffold_metadata.yaml

SCAFFOLD header format specification (comment patterns for different file types).

**See:** [.pgmcp/config/scaffold_metadata.yaml](../../../.pgmcp/config/scaffold_metadata.yaml) for header specs.

---

### .pgmcp/template_registry.json

Template provenance tracking (version hashes → tier chains).

**See:** [.pgmcp/template_registry.json](../../../.pgmcp/template_registry.json) for version history.

---

## Common Workflows

### TDD Red Phase: Scaffold DTO with Test

```
1. scaffold_artifact(
     artifact_type="dto",
     name="OrderDTO",
     context={
       "fields": [
         {"name": "id", "type": "int"},
         {"name": "total", "type": "Decimal"}
       ]
     }
   )
2. run_tests(path="tests/test_order_dto.py") → expect failure
3. git_add_or_commit(workflow_phase="implementation", sub_phase="red", cycle_number=1, message="Add failing test for OrderDTO")
```

### Scaffold Worker for Background Processing

```
1. scaffold_artifact(
     artifact_type="worker",
     name="EmailNotificationWorker",
     context={
       "description": "Send email notifications asynchronously",
       "methods": [
         {"name": "send_email", "params": "recipient: str, body: str", "returns": "bool"}
       ]
     }
   )
2. safe_edit_file(...) → implement logic
3. run_tests(path="tests/test_email_worker.py")
```

### Design Document for New Feature

```
1. scaffold_artifact(
     artifact_type="design",
     name="payment-gateway-integration",
     context={
       "feature_name": "Payment Gateway Integration",
       "goals": [
         "Support Stripe payments",
         "Support PayPal payments",
         "Implement refund logic"
       ],
       "components": [
         {"name": "PaymentService", "type": "Service"},
         {"name": "PaymentDTO", "type": "DTO"},
         {"name": "PaymentAdapter", "type": "Adapter"}
       ]
     }
   )
2. Review design with team
3. Scaffold components: PaymentDTO, PaymentService, PaymentAdapter
```

---

## Template Upgrade Process

When templates are updated:

1. **Version Hash Changes:** Template content change → new 8-char SHA hash
2. **Registry Update:** `template_registry.json` records new version
3. **Validation:** `validate_template` tool detects version mismatch
4. **Migration:** Optional migration script upgrades existing artifacts

**Example:**
```json
// Old artifact with outdated template version
// template=dto version=a3b5c7d9 created=2026-01-01

// validate_template detects mismatch:
{
  "success": false,
  "message": "Template version mismatch",
  "current_version": "a3b5c7d9",
  "latest_version": "f8e2d4a1",
  "migration_required": true
}
```

---

## Related Documentation

- [README.md](README.md) — MCP Tools navigation index
- [editing.md](editing.md) — safe_edit_file for manual edits
- [quality.md](quality.md) — validate_template for conformance checking
- [.pgmcp/templates/config/](../../../.pgmcp/templates/config/) — Modular configuration directory
- [.pgmcp/config/project_structure.yaml](../../../.pgmcp/config/project_structure.yaml) — Directory resolution
- [.pgmcp/config/scaffold_metadata.yaml](../../../.pgmcp/config/scaffold_metadata.yaml) — SCAFFOLD header specs
- [.pgmcp/templates/](../../../.pgmcp/templates/) — Template library
- [docs/manuals/architecture.md](../../manuals/architecture.md) — Three-layer architecture reference

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 3.3 | 2026-08-22 | Agent | Align bounded scaffold results and resource-oriented schema presentation |
| 3.2 | 2026-07-16 | Agent | Updated for modular YAML configuration loading, dynamic validation model, and added typescript_dto. |
| 3.1 | 2026-07-08 | Agent | Update template locations to Git-tracked `.pgmcp/templates` and correct broken architecture link (#420) |
| 2.2 | 2026-06-04 | Agent | Remove legacy error example; fix artifact type tables (17 registered types); fix template paths; replaced fake context schema YAML with registry reference; removed stale links (#286) |
| 2.1 | 2026-06-02 | Agent | Add scaffold_schema API Reference section; update tool counts (1→2); proactive schema exposure documented |
| 2.0 | 2026-02-08 | Agent | Complete reference for scaffold_artifact: artifact registry, template system, directory resolution, SCAFFOLD headers, tier architecture |

<!-- docs/reference/mcp/tools/scaffolding.md -->
<!-- template=reference version=064954ea created=2026-02-08T12:00:00+01:00 updated=2026-02-08 -->
# Scaffolding Tools

**Status:** DEFINITIVE  
**Version:** 2.0  
**Last Updated:** 2026-02-08  

**Source:** [mcp_server/tools/scaffold_artifact.py](../../../../mcp_server/tools/scaffold_artifact.py)  
**Tests:** [tests/unit/test_scaffold_artifact.py](../../../../tests/unit/test_scaffold_artifact.py)  

---

## Purpose

Complete reference documentation for unified artifact scaffolding via the `scaffold_artifact` tool. This tool generates code and documentation artifacts from Jinja2 templates defined in the [.st3/artifacts.yaml](../../../../.st3/artifacts.yaml) registry.

The scaffolding system provides:
- **Unified tool** for code and documentation generation (replaces separate tools)
- **Template composition** via Jinja2 includes and inheritance
- **Automatic directory resolution** from [.st3/project_structure.yaml](../../../../.st3/project_structure.yaml)
- **SCAFFOLD header injection** for template provenance tracking
- **Context-driven customization** via template variables

---

## Overview

The MCP server provides **1 scaffolding tool**:

| Tool | Purpose | Artifact Types |
|------|---------|----------------|
| `scaffold_artifact` | Generate code/docs from templates | 14+ types (DTO, worker, adapter, tool, design, architecture, etc.) |

**Supported Artifact Categories:**
- **Code Artifacts:** `dto`, `worker`, `adapter`, `tool`, `manager`, `service`
- **Documentation Artifacts:** `design`, `architecture`, `tracking`, `research`, `reference`, `planning`, `guide`, `procedure`

---

## API Reference

### scaffold_artifact

**MCP Name:** `scaffold_artifact`  
**Class:** `ScaffoldArtifactTool`  
**File:** [mcp_server/tools/scaffold_artifact.py](../../../../mcp_server/tools/scaffold_artifact.py)

Generate any artifact type (code or document) from unified registry.

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `artifact_type` | `str` | **Yes** | Artifact type ID from registry (e.g., `"dto"`, `"design"`, `"worker"`) |
| `name` | `str` | **Yes** | Artifact name — PascalCase for code, kebab-case for docs |
| `output_path` | `str` | **Yes** (file artifacts) / No (ephemeral) | Explicit output path. **Required** for file artifacts (`dto`, `worker`, `adapter`, `tool`, etc.) — omitting raises `ERR_VALIDATION`. Optional for ephemeral artifacts (`issue`, `tracking`, …) — when provided, artifact is written there instead of `.st3/temp/`. |
| `context` | `dict` | No | Template rendering context (varies by artifact type) — default: `{}` |

#### Returns

```json
{
  "success": true,
  "artifact": {
    "type": "dto",
    "name": "OrderDTO",
    "path": "/workspace/backend/dtos/order_dto.py",
    "template": "dto.py.j2",
    "context": {
      "name": "OrderDTO",
      "fields": [
        {"name": "id", "type": "int"},
        {"name": "total", "type": "Decimal"}
      ]
    }
  },
  "message": "Artifact 'OrderDTO' scaffolded successfully"
}
```

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
  "name": "oauth-integration-design",
  "context": {
    "feature_name": "OAuth2 Integration",
    "goals": [
      "Support Google OAuth2",
      "Support GitHub OAuth2",
      "Implement token refresh"
    ],
    "components": [
      {"name": "OAuthService", "type": "Service"},
      {"name": "TokenDTO", "type": "DTO"}
    ]
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

## Artifact Registry

The unified artifact registry is defined in [.st3/artifacts.yaml](../../../../.st3/artifacts.yaml).

### Registry Structure

```yaml
# .st3/artifacts.yaml
artifacts:
  # Code Artifacts
  - id: dto
    category: code
    type: dto
    template: dto.py.j2
    tier: 0
    context_schema:
      fields: list[dict]
      imports: list[str]
  
  - id: worker
    category: code
    type: worker
    template: worker.py.j2
    tier: 1
    context_schema:
      description: str
      methods: list[dict]
  
  # Documentation Artifacts
  - id: design
    category: documentation
    type: design
    template: design.md.j2
    tier: 1
    context_schema:
      feature_name: str
      goals: list[str]
      components: list[dict]
  
  - id: architecture
    category: documentation
    type: architecture
    template: architecture.md.j2
    tier: 1
    context_schema:
      pattern_name: str
      description: str
      use_cases: list[str]
```

### Supported Artifact Types

#### Code Artifacts (6 types)

| ID | Template | Output Directory | Description |
|----|----------|------------------|-------------|
| `dto` | `dto.py.j2` | `backend/dtos/` | Data Transfer Objects (frozen dataclasses) |
| `worker` | `worker.py.j2` | `backend/workers/` | Async background workers |
| `adapter` | `adapter.py.j2` | `backend/adapters/` | External service adapters |
| `tool` | `tool.py.j2` | `mcp_server/tools/` | MCP server tools |
| `manager` | `manager.py.j2` | `mcp_server/managers/` | Manager classes |
| `service` | `service.py.j2` | `backend/services/` | Service layer classes |

#### Documentation Artifacts (8+ types)

| ID | Template | Output Directory | Description |
|----|----------|------------------|-------------|
| `design` | `design.md.j2` | `docs/design/` | Feature design documents |
| `architecture` | `architecture.md.j2` | `docs/architecture/` | Architectural decision records |
| `tracking` | `tracking.md.j2` | `docs/development/issue*/` | Issue tracking documents |
| `research` | `research.md.j2` | `docs/development/issue*/` | Research and analysis |
| `reference` | `reference.md.j2` | `docs/reference/` | API/tool reference docs |
| `planning` | `planning.md.j2` | `docs/development/issue*/` | Planning documents |
| `guide` | `guide.md.j2` | `docs/guides/` | How-to guides |
| `procedure` | `procedure.md.j2` | `docs/procedures/` | Standard operating procedures |

---

## Template System

### Template Location

Templates are stored in [mcp_server/templates/](../../../../mcp_server/templates/):

```
mcp_server/templates/
├── code/
│   ├── dto.py.j2
│   ├── worker.py.j2
│   ├── adapter.py.j2
│   └── tool.py.j2
├── docs/
│   ├── design.md.j2
│   ├── architecture.md.j2
│   ├── research.md.j2
│   └── reference.md.j2
└── shared/
    ├── base_class.j2
    └── common_imports.j2
```

### Template Composition

Templates use Jinja2 composition features:

**Include Pattern:**
```jinja2
{# dto.py.j2 #}
{% include 'shared/common_imports.j2' %}

@dataclass(frozen=True)
class {{ name }}:
    {% for field in fields %}
    {{ field.name }}: {{ field.type }}
    {% endfor %}
```

**Inheritance Pattern:**
```jinja2
{# worker.py.j2 #}
{% extends 'shared/base_class.j2' %}

{% block imports %}
from backend.core.interfaces import BaseWorker
{{ super() }}
{% endblock %}

{% block class_definition %}
class {{ name }}(BaseWorker):
    """{{ description }}"""
    
    async def execute(self) -> None:
        pass
{% endblock %}
```

### Context Variables

Each artifact type defines expected context variables in `context_schema`:

**DTO Context:**
- `fields: list[dict]` — List of field definitions
  - `name: str` — Field name (snake_case)
  - `type: str` — Python type annotation
  - `description: str` — Field documentation
  - `default: any` — Optional default value
- `imports: list[str]` — Additional import statements

**Worker Context:**
- `description: str` — Worker purpose
- `methods: list[dict]` — Additional methods
  - `name: str` — Method name
  - `params: str` — Parameter list
  - `returns: str` — Return type

**Design Document Context:**
- `feature_name: str` — Feature being designed
- `goals: list[str]` — Feature goals
- `components: list[dict]` — System components
  - `name: str` — Component name
  - `type: str` — Component type (DTO, Worker, Service, etc.)

---

## Directory Resolution

The `scaffold_artifact` tool automatically resolves output directories from [.st3/project_structure.yaml](../../../../.st3/project_structure.yaml):

```yaml
# .st3/project_structure.yaml
directories:
  code:
    dto: "backend/dtos/"
    worker: "backend/workers/"
    adapter: "backend/adapters/"
    service: "backend/services/"
  
  documentation:
    design: "docs/design/"
    architecture: "docs/architecture/"
    reference: "docs/reference/"
    tracking: "docs/development/issue{issue_number}/"
```

**Example:**
```json
{
  "artifact_type": "dto",
  "name": "OrderDTO"
}
```

**Resolved path:** `backend/dtos/order_dto.py` (auto-resolved from `project_structure.yaml`)

**Override with `output_path`:**
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
- `template` — Template ID from artifacts.yaml
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

Tier information is stored in `artifacts.yaml` and `template_registry.json`.

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

### 3. Using `create_file` Instead of `scaffold_artifact`

**❌ WRONG:**
```json
{
  "tool": "create_file",
  "path": "backend/dtos/order.py",
  "content": "from dataclasses import dataclass\n..."
}
```

**✅ CORRECT:**
```json
{
  "tool": "scaffold_artifact",
  "artifact_type": "dto",
  "name": "OrderDTO",
  "context": {...}
}
```

**Rationale:** `scaffold_artifact` ensures:
- Correct template usage
- SCAFFOLD header injection
- Directory structure compliance
- Template version tracking

---

## Configuration

### .st3/artifacts.yaml

Complete artifact registry with template mappings, context schemas, and tier information.

**See:** [.st3/artifacts.yaml](../../../../.st3/artifacts.yaml) for full registry.

---

### .st3/project_structure.yaml

Directory resolution rules for artifact types.

**See:** [.st3/project_structure.yaml](../../../../.st3/project_structure.yaml) for full structure.

---

### .st3/scaffold_metadata.yaml

SCAFFOLD header format specification (comment patterns for different file types).

**See:** [.st3/scaffold_metadata.yaml](../../../../.st3/scaffold_metadata.yaml) for header specs.

---

### .st3/template_registry.json

Template provenance tracking (version hashes → tier chains).

**See:** [.st3/template_registry.json](../../../../.st3/template_registry.json) for version history.

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
3. git_add_or_commit(phase="red", message="Add failing test for OrderDTO")
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
- [.st3/artifacts.yaml](../../../../.st3/artifacts.yaml) — Complete artifact registry
- [.st3/project_structure.yaml](../../../../.st3/project_structure.yaml) — Directory resolution
- [.st3/scaffold_metadata.yaml](../../../../.st3/scaffold_metadata.yaml) — SCAFFOLD header specs
- [mcp_server/templates/](../../../../mcp_server/templates/) — Template library
- [docs/development/issue19/research.md](../../../development/issue19/research.md) — Tool inventory research (Section 1.10: Scaffolding)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 2.0 | 2026-02-08 | Agent | Complete reference for scaffold_artifact: artifact registry, template system, directory resolution, SCAFFOLD headers, tier architecture |

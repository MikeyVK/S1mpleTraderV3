# Phase 1: Template Introspection & Schema Generation - Technical Design

<!-- SCAFFOLD: template=design version=1.0 created=2026-01-21T16:00:00Z path=docs/development/issue120/phase1-template-introspection-design.md -->

**Status:** ✅ APPROVED - Ready for Implementation
**Author:** Agent
**Created:** 2026-01-21
**Last Updated:** 2026-01-21
**Approved:** 2026-01-21
**Issue:** #120 - Scaffolder: Improve error messages and context validation

---

## 1. Overview

### 1.1 Purpose

This design specifies the technical implementation for automatic template introspection using Jinja2 AST parsing to eliminate DRY violations between `artifacts.yaml` and templates. Templates become the Single Source of Truth for validation schema.

### 1.2 Scope

**In Scope:**
- TemplateIntrospector class for Jinja2 AST parsing
- Required/optional field classification algorithm
- System field filtering (template_id, template_version, scaffold_created, output_path)
- Structured JSON schema in MCP responses (success + error)
- TemplateScaffolder integration (replace manual validation)
- Removal of required_fields/optional_fields from ArtifactDefinition
- Migration path for artifacts.yaml cleanup

**Out of Scope:**
- Caching (performance is adequate without - add later if needed)
- Query tool (get_artifact_schema - Phase 1.4)
- Issue #121 (content-aware editing)
- Type validation beyond presence checking

### 1.3 Related Documents

- [unified_research.md](unified_research.md) - Research foundation
- [phase1-implementation-plan.md](phase1-implementation-plan.md) - Implementation roadmap
- [phase0-metadata-planning.md](phase0-metadata-planning.md) - Completed Phase 0

---

## 2. Background

### 2.1 Current State

**Validation Flow:**
```
Agent → scaffold_artifact(dto, name="X")
  ↓
TemplateScaffolder.validate_fields()
  └─ Checks: artifact.required_fields (manual list in artifacts.yaml)
     └─ Missing field → ValidationError (minimal hints)
  ↓
Template.render(context)
  └─ Jinja2 UndefinedError if field used but not provided (cryptic)
```

**Problems:**
1. **DRY Violation:** required_fields in artifacts.yaml can drift from template
2. **Late Failure:** Validation during rendering, not pre-flight
3. **Poor Errors:** Text messages, no structured schema for agents
4. **Duplication:** validate_artifact_fields() method exists but unused

### 2.2 Problem Statement

**Core Problem:** Templates use variables (e.g., `{{ fields }}`) that aren't listed in `required_fields`, causing drift and confusing errors.

**Agent Impact:** No way to know what's needed until scaffold fails.

**Maintenance Burden:** Every template change requires manual artifacts.yaml sync.

### 2.3 Requirements

#### Functional Requirements

- **FR1:** Extract schema from template automatically (no manual lists)
- **FR2:** Classify variables as required or optional (conservative algorithm)
- **FR3:** Filter system-injected fields from agent requirements
- **FR4:** Return structured JSON schema in all MCP responses
- **FR5:** Validate agent context before template rendering (fail fast)

#### Non-Functional Requirements

- **NFR1:** Performance < 2ms per introspection (measured: ~1ms average)
- **NFR2:** Backward compatible with existing templates (no modifications)
- **NFR3:** Zero drift between template and validation (single source of truth)
- **NFR4:** Testable (pure functions, no hidden state)

---

## 3. Design

### 3.1 ToolResult Contract Compliance

**CRITICAL:** All changes must adhere to existing ToolResult/error_handler contract.

**Existing Contract:**
```python
# Success response:
ToolResult(
    content=[{"type": "text", "text": "..."}],
    is_error=False
)

# Error response (via @tool_error_handler):
ToolResult(
    content=[{"type": "text", "text": "..."}],
    is_error=True,
    error_code="ERR_VALIDATION",  # or ERR_CONFIG, etc.
    hints=["Suggestion 1", "..."]
)
```

**Our Enhancement (Additive, Non-Breaking):**
- Add **resource** content item alongside text (both success and error)
- Resource contains structured JSON schema (agent-input only)
- Existing text content preserved (backward compatible)
- @tool_error_handler still works (catches ValidationError)
- Hints still human-readable (not for agent parsing)

**Schema Exposure Principle:**
- **Agent-Input Schema:** What agent provides (system fields filtered)
  - Exposed in ToolResult resources
  - Used for validation
  - Example: `{"required": ["name"], "optional": ["frozen"]}`

- **Template Variables Schema:** All template vars (including system)
  - Internal analysis only
  - Never exposed to agent
  - Example: `["name", "template_id", "scaffold_created"]`

**Integration Points:**
1. TemplateScaffolder raises ValidationError with schema
2. @tool_error_handler catches and converts to ToolResult
3. Tool adds resource content item with schema JSON
4. Agent gets both text (human) and resource (programmatic)

---

### 3.2 Architecture Position

```
┌─────────────────────────────────────────────────────┐
│ MCP Tool Layer                                       │
│  scaffold_artifact(type, **context) → JSON response │
│  ├─ Success: {schema: {...}, path: "..."}          │
│  └─ Error: {schema: {...}, validation: {...}}      │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│ Manager Layer: ArtifactManager                       │
│  ├─ Inject system context (template_id, version, etc)│
│  └─ Delegate to scaffolder                          │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│ Scaffolder Layer: TemplateScaffolder                 │
│  ├─ Get template schema (NEW: via introspector)     │
│  ├─ Validate agent context (pre-render)             │
│  └─ Render template                                 │
└──────────────────┬───────────────────────────────────┘
                   │
┌──────────────────▼───────────────────────────────────┐
│ NEW: Introspector Layer: TemplateIntrospector        │
│  ├─ Parse template AST                              │
│  ├─ Extract variables                               │
│  ├─ Classify required/optional                      │
│  └─ Filter system fields                            │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
               Jinja2 AST
```

### 3.3 Component Design

#### 3.3.1 TemplateIntrospector (NEW)

**Location:** `mcp_server/scaffolding/template_introspector.py`

**Purpose:** Pure function module for extracting schema from Jinja2 templates

**Responsibilities:**
- Parse template source into Jinja2 AST
- Detect all undeclared variables (via `meta.find_undeclared_variables`)
- Classify variables as required or optional
- Filter system-injected fields

**Algorithm:**

```
1. Parse template source → Jinja2 AST
2. Extract all undeclared variables (meta.find_undeclared_variables)
3. Walk AST to classify variables:
   
   FOR each variable in undeclared_vars:
     IF variable in SYSTEM_FIELDS:
       → SKIP (filtered - not agent responsibility)
     
     ELIF variable used in {% if variable %} block:
       → OPTIONAL (conditional usage)
     
     ELIF variable has | default(...) filter:
       → OPTIONAL (has fallback)
     
     ELSE:
       → REQUIRED (conservative - fail fast)
   
4. Return TemplateSchema(required=[...], optional=[...])
```

**System Fields Filter:**
```python
SYSTEM_FIELDS = {
    "template_id",       # Injected by ArtifactManager
    "template_version",  # Injected by ArtifactManager
    "scaffold_created",  # Injected by ArtifactManager
    "output_path",       # Injected by ArtifactManager (file artifacts only)
}
```

**Dependencies:**
- `jinja2.Environment` (template parsing)
- `jinja2.meta` (AST introspection)
- `pathlib.Path` (template file handling)

---

#### 3.3.2 TemplateScaffolder.validate_fields (MODIFIED)

**Location:** `mcp_server/scaffolding/template_scaffolder.py`

**Current Implementation:**
```python
def validate_fields(self, artifact: ArtifactDefinition, **kwargs):
    """Validate required fields are present."""
    missing = [f for f in artifact.required_fields if f not in kwargs]
    if missing:
        raise ValidationError(f"Missing required fields: {missing}")
```

**New Implementation:**
```python
def validate_fields(self, artifact: ArtifactDefinition, **kwargs):
    """Validate required fields using template introspection."""
    # 1. Extract schema from template (NEW)
    schema = introspect_template(
        self.template_path,
        self.env
    )
    
    # 2. Check missing required fields
    provided = set(kwargs.keys())
    missing = [f for f in schema.required if f not in provided]
    
    # 3. Raise with structured error (NEW)
    if missing:
        raise ValidationError(
            message=f"Missing required fields: {missing}",
            schema=schema,  # NEW: structured data
            provided=list(provided),
            missing=missing
        )
```

**Changes:**
- Replace `artifact.required_fields` with introspected schema
- Add structured schema to exception
- Remove dependency on manual field lists

---

#### 3.3.3 ArtifactDefinition (MODIFIED)

**Location:** `mcp_server/config/artifact_registry_config.py`

**Fields to REMOVE:**
```python
# REMOVE these lines:
required_fields: list[str] = Field(default_factory=list, ...)
optional_fields: list[str] = Field(default_factory=list, ...)

# REMOVE this method:
def validate_artifact_fields(self, provided: dict) -> None:
    # Unused duplication - delete entire method
```

**Rationale:**
- Template is SSOT - no manual maintenance needed
- Eliminates drift risk
- Core goal of Issue #120

---

#### 3.3.4 scaffold_artifact MCP Tool (MODIFIED)

**Location:** `mcp_server/tools/scaffold_artifact.py`

**Current Response:**
```python
# Success: returns ToolResult with path
return ToolResult.success(str(output_path))

# Error: ValidationError raised, caught by @tool_error_handler
raise ValidationError("Missing required fields: ...")
```

**New Response Format (via ToolResult contract):**

**Success Response:**
```python
# ToolResult structure:
ToolResult(
    content=[
        {
            "type": "text",
            "text": str(output_path)  # Primary content (backward compatible)
        },
        {
            "type": "resource",  # NEW: structured schema as resource
            "resource": {
                "uri": f"schema://{artifact_type}",
                "mimeType": "application/json",
                "text": json.dumps({
                    "artifact_type": artifact_type,
                    "schema": {
                        "required": ["name", "description"],  # Agent-input only
                        "optional": ["frozen"]
                    }
                })
            }
        }
    ],
    is_error=False
)
```

**Validation Error Response:**
```python
# Enhanced ValidationError:
raise ValidationError(
    message=f"Missing required fields: {missing}",
    hints=[
        f"Required: {', '.join(schema.required)}",
        f"Optional: {', '.join(schema.optional)}",
        f"Missing: {', '.join(missing)}"
    ],
    schema=schema  # NEW: attach schema for programmatic access
)

# Results in ToolResult (via @tool_error_handler):
ToolResult(
    content=[
        {
            "type": "text",
            "text": "Missing required fields: description"
        },
        {
            "type": "resource",  # NEW: structured schema in error too
            "resource": {
                "uri": f"schema://{artifact_type}",
                "mimeType": "application/json",
                "text": json.dumps({
                    "artifact_type": artifact_type,
                    "schema": schema.to_dict(),  # Same format as success
                    "validation": {
                        "missing": ["description"],
                        "provided": ["name", "fields"]
                    }
                })
            }
        }
    ],
    is_error=True,
    error_code="ERR_VALIDATION",
    hints=[...],  # Human-readable hints
)
```

**Key Changes:**
- ✅ Adheres to existing ToolResult contract (no breaking changes)
- ✅ Schema available as structured resource (not text parsing)
- ✅ Backward compatible (primary content still text)
- ✅ Works with @tool_error_handler decorator
- ✅ Consistent format in success and error responses

---

### 3.4 Data Model

#### 3.4.1 Schema Types (CRITICAL DISTINCTION)

**Two Schema Concepts - Must Be Explicit:**

1. **Agent-Input Schema (Exposed to MCP Tools)**
   - Variables the agent MUST provide in scaffold_artifact() call
   - System fields FILTERED OUT (template_id, template_version, etc.)
   - This is what we return in ToolResult resources
   - Example: `{"required": ["name", "description"], "optional": ["frozen"]}`

2. **Template Variables Schema (Internal Analysis)**
   - ALL variables found in template (including system fields)
   - Used internally for introspection completeness
   - Never exposed directly to agent
   - Example: `{"all": ["name", "description", "template_id", "scaffold_created"]}`

**Why This Matters:**
- Tests must verify agent-input schema (after filtering)
- MCP responses contain agent-input schema only
- Internal analysis uses template variables schema
- Documentation must specify which schema is referenced

---

#### 3.4.2 TemplateSchema Dataclass

```python
from dataclasses import dataclass

@dataclass
class TemplateSchema:
    """Agent-input schema extracted from Jinja2 template.
    
    IMPORTANT: This is the AGENT-INPUT schema.
    System fields (template_id, template_version, scaffold_created, output_path)
    are ALREADY FILTERED OUT during introspection.
    
    Use Case:
        - MCP tool responses (success and error)
        - Validation error hints
        - Agent pre-flight checks (query tool)
    
    Attributes:
        required: Fields agent must provide (no default in template)
        optional: Fields agent can provide (has default or in if-block)
    
    Example:
        TemplateSchema(
            required=["name", "description", "fields"],
            optional=["frozen", "validators"]
        )
        # Note: template_id, template_version NOT in lists (filtered)
    """
    required: list[str]  # Must be in context, no default
    optional: list[str]  # Used in if-blocks or has default filter
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for MCP responses.
        
        Returns:
            Dict with required and optional lists (agent-input only)
        """
        return {
            "required": self.required,
            "optional": self.optional
        }
```

---

#### 3.4.3 Enhanced ValidationError

```python
class ValidationError(MCPError):
    """Enhanced validation error with structured schema.
    
    Integrates with existing @tool_error_handler decorator and ToolResult contract.
    Schema is available both in hints (human-readable) and as attached data
    (programmatic access for building ToolResult resources).
    
    Attributes:
        message: Human-readable error message
        hints: List of actionable suggestions (from MCPError)
        schema: Agent-input TemplateSchema (NEW - for ToolResult resource)
        provided: List of fields agent gave
        missing: List of required fields not provided
    """
    def __init__(
        self,
        message: str,
        schema: TemplateSchema | None = None,
        provided: list[str] | None = None,
        missing: list[str] | None = None,
        hints: list[str] | None = None
    ):
        # Generate hints if not provided
        if hints is None and schema is not None:
            hints = self._generate_hints(schema, provided or [], missing or [])
        
        # Call MCPError.__init__ (sets code="ERR_VALIDATION", hints)
        super().__init__(
            message=message,
            code="ERR_VALIDATION",
            hints=hints
        )
        
        # Store structured data for ToolResult resource generation
        self.schema = schema
        self.provided = provided or []
        self.missing = missing or []
    
    def _generate_hints(
        self,
        schema: TemplateSchema,
        provided: list[str],
        missing: list[str]
    ) -> list[str]:
        """Generate hints for human logs (not for agent parsing).
        
        Returns:
            List of hint strings for ToolResult.hints field
        """
        hints = []
        if schema.required:
            hints.append(f"Required fields: {', '.join(schema.required)}")
        if schema.optional:
            hints.append(f"Optional fields: {', '.join(schema.optional)}")
        if missing:
            hints.append(f"Missing: {', '.join(missing)}")
        return hints
    
    def to_resource_dict(self, artifact_type: str) -> dict:
        """Generate structured resource data for ToolResult.
        
        This is used by the tool to add a resource content item with
        the complete schema and validation details.
        
        Args:
            artifact_type: Artifact type identifier (e.g., "dto")
        
        Returns:
            Dict suitable for ToolResult resource content item
        """
        data = {
            "artifact_type": artifact_type,
        }
        
        if self.schema:
            data["schema"] = self.schema.to_dict()
        
        if self.missing or self.provided:
            data["validation"] = {
                "missing": self.missing,
                "provided": self.provided
            }
        
        return data
```

---

#### 3.4.4 ToolResult Integration Pattern

```python
# In scaffold_artifact tool:

async def execute(self, params: ScaffoldParams) -> ToolResult:
    """Execute scaffolding with enhanced error responses.
    
    Strategy: Let @tool_error_handler catch ValidationError, then enhance
    ToolResult with schema resource in both success and error paths.
    """
    
    # Get schema first (needed for both success and error)
    schema = self._get_artifact_schema(params.artifact_type)
    
    try:
        # Scaffold artifact (may raise ValidationError with schema attached)
        output_path = await self.manager.scaffold_artifact(
            artifact_type=params.artifact_type,
            **params.context
        )
        
        # Success: Return path + schema resource
        return ToolResult(
            content=[
                {
                    "type": "text",
                    "text": str(output_path)  # Backward compatible
                },
                {
                    "type": "resource",  # Structured schema
                    "resource": {
                        "uri": f"schema://{params.artifact_type}",
                        "mimeType": "application/json",
                        "text": json.dumps({
                            "artifact_type": params.artifact_type,
                            "schema": schema.to_dict()
                        })
                    }
                }
            ],
            is_error=False
        )
        
    except ValidationError as e:
        # Enhance error with schema resource before re-raising
        # @tool_error_handler will catch and convert to ToolResult
        
        # Add schema resource to error
        error_result = ToolResult.error(
            message=e.message,
            error_code="ERR_VALIDATION",
            hints=e.hints
        )
        
        # Append schema resource to content
        error_result.content.append({
            "type": "resource",
            "resource": {
                "uri": f"schema://{params.artifact_type}",
                "mimeType": "application/json",
                "text": json.dumps(e.to_resource_dict(params.artifact_type))
            }
        })
        
        return error_result


def _get_artifact_schema(self, artifact_type: str) -> TemplateSchema:
    """Get agent-input schema for artifact type.
    
    Helper method to extract schema once and reuse in success/error paths.
    """
    artifact = self.registry.get_artifact(artifact_type)
    template_path = self.templates_dir / artifact.template_path
    return introspect_template(template_path, self.jinja_env)
```

**Implementation Notes:**
- Single code path (no alternative options in production code)
- Schema fetched once, used in both success and error
- @tool_error_handler still works (we return ToolResult directly)
- Schema resource consistently added to both success and error
- Backward compatible (text content first, resource second)

---

### 3.5 Interface Design

#### TemplateIntrospector Module

```python
def introspect_template(
    template_path: Path,
    env: Environment
) -> TemplateSchema:
    """Extract schema from Jinja2 template.
    
    Args:
        template_path: Path to .jinja2 template file
        env: Jinja2 Environment for parsing
    
    Returns:
        TemplateSchema with required/optional fields (system fields filtered)
    
    Raises:
        ConfigError: If template not found or invalid syntax
    
    Performance:
        ~1ms average (tested with real templates)
    """
    # Implementation in next section
```

```python
def _classify_variables(
    ast: jinja2.nodes.Template,
    all_vars: set[str]
) -> tuple[list[str], list[str]]:
    """Classify variables as required or optional.
    
    Algorithm:
        - Variable in {% if var %} → optional
        - Variable with | default(...) → optional
        - Else → required (conservative)
    
    Args:
        ast: Parsed Jinja2 AST
        all_vars: All undeclared variables (from meta)
    
    Returns:
        Tuple of (required, optional) lists
    """
    # Implementation in next section
```

---

## 4. Implementation Details

### 4.1 Introspection Algorithm

**Step 1: Parse Template**
```python
def introspect_template(template_path: Path, env: Environment) -> TemplateSchema:
    # 1. Read template source
    if not template_path.exists():
        raise ConfigError(f"Template not found: {template_path}")
    
    source = template_path.read_text()
    
    # 2. Parse AST
    try:
        ast = env.parse(source)
    except jinja2.TemplateSyntaxError as e:
        raise ConfigError(f"Invalid template syntax: {e}")
    
    # 3. Extract all undeclared variables
    all_vars = meta.find_undeclared_variables(ast)
    
    # 4. Filter system fields
    agent_vars = all_vars - SYSTEM_FIELDS
    
    # 5. Classify required vs optional
    required, optional = _classify_variables(ast, agent_vars)
    
    return TemplateSchema(required=sorted(required), optional=sorted(optional))
```

**Step 2: Classify Variables**
```python
def _classify_variables(
    ast: jinja2.nodes.Template,
    agent_vars: set[str]
) -> tuple[list[str], list[str]]:
    """Conservative classification: ambiguous → required."""
    
    optional = set()
    
    # Walk AST to find conditional usage
    for node in ast.find_all(jinja2.nodes.If):
        # Variables in {% if variable %} are optional
        condition_vars = _extract_vars_from_node(node.test)
        optional.update(condition_vars & agent_vars)
    
    # Find default filter usage
    for node in ast.find_all(jinja2.nodes.Filter):
        if node.name == "default":
            # {{ variable | default(...) }} is optional
            var = _extract_var_from_filter(node)
            if var in agent_vars:
                optional.add(var)
    
    # Rest are required (conservative)
    required = agent_vars - optional
    
    return list(required), list(optional)
```

**Helper Functions:**
```python
def _extract_vars_from_node(node: jinja2.nodes.Node) -> set[str]:
    """Recursively extract variable names from AST node."""
    vars = set()
    if isinstance(node, jinja2.nodes.Name):
        vars.add(node.name)
    elif hasattr(node, 'iter_child_nodes'):
        for child in node.iter_child_nodes():
            vars.update(_extract_vars_from_node(child))
    return vars
```

### 4.2 Migration Path

**Phase 1: Add Introspection (Parallel)**
1. Implement TemplateIntrospector
2. Add introspection to TemplateScaffolder (keep old validation as fallback)
3. Compare results: log where manual fields != introspected schema
4. Fix drift in artifacts.yaml (one-time cleanup)

**Phase 2: Switch Over**
5. Remove fallback - use introspection only
6. All tests pass (validation behavior unchanged, just source changed)

**Phase 3: Cleanup**
7. Remove required_fields/optional_fields from ArtifactDefinition
8. Remove fields from artifacts.yaml
9. Delete validate_artifact_fields() method

**Phase 4: Response Format**
10. Update MCP tool to return structured schema
11. Update all error handling to include schema

---

## 5. Testing Strategy

### 5.1 Unit Tests

**TemplateIntrospector:**
- Parse real templates (dto, worker, design) → verify variable extraction
- Classify if-blocks correctly → optional
- Classify default filters correctly → optional
- Filter system fields → not in agent requirements
- Handle template syntax errors → ConfigError with hints
- Edge case: nested conditionals
- Edge case: complex filter chains

**Test Files:**
- `tests/unit/scaffolding/test_template_introspector.py` (~20 tests)
- `tests/unit/scaffolding/test_template_introspector_edge_cases.py` (~10 tests)

### 5.2 Integration Tests

**E2E Validation:**
- Scaffold dto with missing field → structured error with schema
- Scaffold dto with all fields → success with schema
- Compare introspected schema vs manual fields → log mismatches
- Verify system fields NOT in required list

**Test Files:**
- `tests/integration/test_introspection_validation_e2e.py` (~8 tests)

### 5.3 Performance Tests

**Benchmark:**
- Introspect all templates → avg < 2ms
- Repeat 100x → verify no memory leak
- Compare with/without caching (future)

**Test Files:**
- `test_introspection_performance.py` (already exists - expand)

---

## 6. Alternatives Considered

### 6.1 Caching Strategy

**Decision:** No caching in initial implementation

**Alternatives:**
- Module-level dict (shared state between instances)
- LRU cache with mtime invalidation
- Redis cache (over-engineering)

**Rationale:**
- Performance test shows ~1ms average
- Cache overhead > benefit for this use case
- Simpler code (YAGNI principle)
- Can add later if bottleneck found

**Risks:**
- Performance degradation with very large templates (>1000 lines)
- Mitigation: Monitor in production, add caching if needed

---

### 6.2 Required/Optional Classification

**Decision:** Conservative (ambiguous → required)

**Alternatives:**
- Complex AST traversal (handle all edge cases)
- Machine learning classification (overkill)
- Manual hints in templates (defeats purpose)

**Rationale:**
- Start simple: if-blocks + default filters
- Fail-fast safer than false positives
- Agent gets clear error, can fix
- Extend iteratively based on real patterns

**Risks:**
- May over-classify optional as required
- Mitigation: Iterate based on actual template patterns

---

### 6.3 Schema Response Format

**Decision:** Structured JSON in all responses

**Alternatives:**
- Text-based error messages only (current)
- Schema only in query tool (inconsistent)
- Full JSON Schema format (complex for flat structure)

**Rationale:**
- MCP best practice (no text parsing)
- Consistent across success and error
- Simple flat format (Issue #99 lesson)
- Agent-friendly (JSON dict, not text)

**Risks:**
- Slightly larger response payload
- Mitigation: Minimal - 2 lists, ~100 bytes

---

## 7. Open Questions & Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Cache introspection results? | NO (initial) | ~1ms is fast enough, add later if needed |
| Handle nested conditionals? | Phase 2 | Start simple, extend iteratively |
| Support custom classification hints? | NO | Defeats SSOT principle |
| Deprecation timeline for manual fields? | Immediate | Core goal of #120, not optional |
| Query tool (get_artifact_schema)? | Phase 1.4 | Optional, not blocking core feature |

---

## 8. Migration & Rollout

### 8.1 Compatibility

**Backward Compatible:**
- ✅ Existing templates work unchanged
- ✅ Phase 0 metadata system unaffected
- ✅ Validation behavior logically identical (just source changed)

**Breaking Changes:**
- ❌ required_fields removed from ArtifactDefinition (Pydantic model)
- ❌ validate_artifact_fields() method deleted (unused anyway)

**Migration:**
- Update artifacts.yaml (remove manual field lists)
- No template changes needed
- No test changes needed (behavior preserved)

### 8.2 Rollout Plan

**Step 1: Introspection Foundation (TDD Phase)**
- Implement TemplateIntrospector
- Unit tests: 30+ tests
- Integration tests: 8+ tests

**Step 2: TemplateScaffolder Integration**
- Replace manual validation with introspection
- Keep same error behavior (validation preserved)
- Log drift warnings (introspected != manual)

**Step 3: Structured Responses**
- Update MCP tool response format
- Update ValidationError to include schema
- Update all callers

**Step 4: Cleanup (Refactor Phase)**
- Remove required_fields from Pydantic model
- Remove fields from artifacts.yaml
- Delete unused validate_artifact_fields()

**Step 5: Validation**
- Full test suite: 1278+ tests pass
- Performance check: < 2ms per scaffold
- Manual testing: Agent workflow improvement confirmed

---

## 9. Success Criteria

### 9.1 Functional

- ✅ Template schema extracted automatically (no manual maintenance)
- ✅ System fields filtered (agent doesn't provide them)
- ✅ Validation happens pre-render (fail fast)
- ✅ Structured JSON schema in all MCP responses
- ✅ Zero drift between template and validation

### 9.2 Non-Functional

- ✅ Performance < 2ms per introspection (measured: ~1ms avg)
- ✅ All existing tests pass (1278+ tests)
- ✅ No breaking changes to templates
- ✅ Code simpler (no manual field maintenance)

### 9.3 Quality Gates

- ✅ 100% test coverage on introspection logic
- ✅ Pylint 10/10 on new code
- ✅ All quality gates pass
- ✅ Manual agent workflow testing confirms improvement

---

## 10. References

- [unified_research.md](unified_research.md) - Complete research document
- [phase1-implementation-plan.md](phase1-implementation-plan.md) - Implementation roadmap
- [Jinja2 AST Documentation](https://jinja.palletsprojects.com/en/3.0.x/api/#jinja2.meta)
- Issue #99 - Flat schemas for Claude (lesson learned)
- Issue #120 - This issue
- Issue #121 - Content-aware editing (follows sequentially)

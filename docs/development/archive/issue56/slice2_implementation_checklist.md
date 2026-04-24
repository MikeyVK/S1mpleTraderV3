# Slice 2 Implementation Checklist

**Issue**: #56 Unified Artifact System  
**Slice**: 2 - Fix Template Loading & Paths  
**Status**: PREPARATION  
**Created**: Pre-implementation (lessons learned from Slice 0 & 1)  
**Purpose**: Prevent premature "DONE" claims via explicit verification checklist

## Lessons Learned Applied

### From Slice 0:
- ✅ Use monkeypatch.chdir() for test isolation (not os.chdir)
- ✅ Check trailing whitespace before commit
- ✅ Run quality gates BEFORE claiming DONE

### From Slice 1:
- ❌ **CRITICAL**: Claimed "COMPLETE" without verifying all requirements
- ❌ **CRITICAL**: E2E test passed but didn't verify what it claimed (tool boundary contract)
- ❌ Missing mandatory file headers
- ❌ Duplicate error formatting (tool + decorator both formatting)
- ✅ **LESSON**: Cannot claim DONE until ALL Definition of Done items explicitly verified

## Problem Statement

### Current Unsafe Pattern
```python
# mcp_server/scaffolders/template_scaffolder.py:121-149
def _load_and_render_template(...):
    with open(template_path, 'r', encoding='utf-8') as f:  # ❌ UNSAFE
        template_content = f.read()
    template = Template(template_content)
    return template.render(**context)
```

**Problems**:
1. Direct `open()` bypasses Jinja2 FileSystemLoader security
2. Absolute paths required (not portable)
3. No template existence validation before load
4. Creates security risk (arbitrary file read)

### Target Safe Pattern
```python
# Use existing JinjaRenderer with FileSystemLoader
renderer = JinjaRenderer(template_dir=Path("mcp_server/templates"))
rendered = renderer.render("components/dto.py.jinja2", **context)
```

**Benefits**:
1. FileSystemLoader restricts access to template_dir only
2. Relative paths (portable, safe)
3. Template validation via get_template()
4. Proper Jinja2 Environment (filters, extensions)

## Architecture Analysis

### Existing Safe Pattern (JinjaRenderer)
**File**: [mcp_server/scaffolding/renderer.py](mcp_server/scaffolding/renderer.py)

**Key Features**:
- `FileSystemLoader(template_dir)` - restricts access
- Default template_dir: `mcp_server/templates`
- Methods:
  - `get_template(name: str)` - validates existence
  - `render(name: str, **kwargs)` - renders template
  - `list_templates()` - lists available templates
- Error handling: Raises ExecutionError on TemplateNotFound

### Current Unsafe Pattern (TemplateScaffolder)
**File**: [mcp_server/scaffolders/template_scaffolder.py](mcp_server/scaffolders/template_scaffolder.py)

**Problem Areas**:
- Line 121-149: `_load_and_render_template()` uses `open()`
- No JinjaRenderer injection
- Template paths must be absolute (not portable)

### Template Structure
**Root**: `mcp_server/templates/`

**Directories**:
- `base/` - Base templates (3 files)
- `components/` - Code templates (12 files)
- `documents/` - Document templates (4 files)

**Total**: 19 template files

## Implementation Plan

### Task 1: Update TemplateScaffolder Constructor
**File**: [mcp_server/scaffolders/template_scaffolder.py](mcp_server/scaffolders/template_scaffolder.py)

**Changes**:
```python
def __init__(
    self,
    artifact_manager: ArtifactManager,
    renderer: JinjaRenderer | None = None,  # NEW: inject renderer
):
    self._artifact_manager = artifact_manager
    # NEW: Default to templates directory
    if renderer is None:
        template_dir = Path(__file__).parent.parent / "templates"
        renderer = JinjaRenderer(template_dir=template_dir)
    self._renderer = renderer
```

**Acceptance Criteria**:
- [ ] JinjaRenderer injected via constructor
- [ ] Default renderer created if not provided
- [ ] Template dir resolves to `mcp_server/templates`
- [ ] Renderer stored in `self._renderer`

**Verification**:
```python
# Unit test
scaffolder = TemplateScaffolder(artifact_manager)
assert scaffolder._renderer is not None
assert scaffolder._renderer.template_dir.name == "templates"
```

### Task 2: Replace _load_and_render_template Method
**File**: [mcp_server/scaffolders/template_scaffolder.py](mcp_server/scaffolders/template_scaffolder.py:121-149)

**Current (UNSAFE)**:
```python
def _load_and_render_template(
    self,
    template_path: str,
    context: dict[str, Any],
) -> str:
    if not Path(template_path).exists():
        raise ValidationError(...)
    
    with open(template_path, 'r', encoding='utf-8') as f:  # ❌ UNSAFE
        template_content = f.read()
    
    template = Template(template_content)
    return template.render(**context)
```

**New (SAFE)**:
```python
def _load_and_render_template(
    self,
    template_name: str,  # CHANGED: relative path not absolute
    context: dict[str, Any],
) -> str:
    """Load and render template using JinjaRenderer.
    
    Args:
        template_name: Template path relative to templates/ 
                      e.g. "components/dto.py.jinja2"
        context: Template variables
        
    Returns:
        Rendered content
        
    Raises:
        ValidationError: Template not found (via ExecutionError)
    """
    try:
        return self._renderer.render(template_name, **context)
    except ExecutionError as e:
        # Re-raise as ValidationError for consistent error handling
        raise ValidationError(
            message=f"Template not found: {template_name}",
            hints=[
                f"Expected template at: mcp_server/templates/{template_name}",
                f"Original error: {e.message}",
            ],
            file_path=f"mcp_server/templates/{template_name}",
        ) from e
```

**Acceptance Criteria**:
- [ ] No `open()` calls remain
- [ ] Uses `self._renderer.render()`
- [ ] Parameter renamed to `template_name` (not `template_path`)
- [ ] Template name is relative (e.g., "components/dto.py.jinja2")
- [ ] ExecutionError caught and re-raised as ValidationError
- [ ] Error includes hints and file_path

**Verification**:
```python
# Unit test - template not found
with pytest.raises(ValidationError) as exc_info:
    scaffolder._load_and_render_template("nonexistent.jinja2", {})
assert "Template not found" in str(exc_info.value)
assert exc_info.value.hints is not None
assert exc_info.value.file_path is not None

# Unit test - successful render
content = scaffolder._load_and_render_template(
    "components/dto.py.jinja2",
    {"name": "TestDTO", "description": "Test"}
)
assert "class TestDTO" in content
```

### Task 3: Update scaffold Method (Template Path Handling)
**File**: [mcp_server/scaffolders/template_scaffolder.py](mcp_server/scaffolders/template_scaffolder.py)

**Changes**:
- Get `template_path` from artifact definition (already relative in artifacts.yaml)
- If `template_path` is None, raise ValidationError
- Pass template_path directly to `_load_and_render_template()` (already relative)

**Current Code**:
```python
def scaffold(self, artifact_type: str, context: dict[str, Any]) -> ScaffoldResult:
    # ... validation ...
    
    template_path = artifact.get("template_path")
    if not template_path:
        return ScaffoldResult.error(...)
    
    # PROBLEM: Might convert to absolute path somewhere
    content = self._load_and_render_template(template_path, merged_context)
```

**Expected Behavior**:
- `template_path` from artifacts.yaml is ALREADY relative
- Just pass it directly to `_load_and_render_template()`
- No path manipulation needed

**Acceptance Criteria**:
- [ ] Get `template_path` from artifact definition
- [ ] Verify it's not None (raise ValidationError if missing)
- [ ] Pass template_path as-is (don't convert to absolute)
- [ ] Template path is relative (e.g., "documents/design.md.jinja2")

**Verification**:
```python
# Integration test
result = scaffolder.scaffold(
    artifact_type="design",
    context={"title": "Test", "author": "Agent", "issue_number": 56}
)
assert result.success
assert "# Test" in result.content
```

### Task 4: Update artifacts.yaml (Fill Missing Template Paths)
**File**: [.st3/artifacts.yaml](.st3/artifacts.yaml)

**Current State**:
- Code artifacts (dto, worker, adapter, etc.): `template_path: null` ❌
- Document artifacts (research, planning, design, etc.): Have template_path ✅

**Required Changes**:
Map each code artifact `type_id` to its template:

```yaml
# CODE ARTIFACTS (need template_path filled)
- type_id: dto
  template_path: "components/dto.py.jinja2"  # NEW

- type_id: worker
  template_path: "components/worker.py.jinja2"  # NEW

- type_id: adapter
  template_path: "components/adapter.py.jinja2"  # NEW

- type_id: tool
  template_path: "components/tool.py.jinja2"  # NEW

- type_id: resource
  template_path: "components/resource.py.jinja2"  # NEW

- type_id: schema
  template_path: "components/schema.py.jinja2"  # NEW

- type_id: interface
  template_path: "components/interface.py.jinja2"  # NEW

- type_id: service
  template_path: null  # SPECIAL: service_type determines template
  # Options: service_orchestrator.py.jinja2, service_command.py.jinja2, service_query.py.jinja2

- type_id: generic
  template_path: null  # SPECIAL: template_name from context determines template
```

**Special Cases**:

1. **Service**: Template depends on `service_type` context field
   - orchestrator → "components/service_orchestrator.py.jinja2"
   - command → "components/service_command.py.jinja2"
   - query → "components/service_query.py.jinja2"
   - Default → "components/service_orchestrator.py.jinja2"

2. **Generic**: Template from `template_name` context field
   - User provides: `context["template_name"] = "custom/my_template.py.jinja2"`
   - Must be relative to templates/

**Acceptance Criteria**:
- [ ] All non-null template_path values are relative paths
- [ ] All paths start with "components/" or "documents/"
- [ ] All referenced templates exist in `mcp_server/templates/`
- [ ] Service and generic type_id document special handling in comments

**Verification**:
```bash
# Check all templates exist
for path in $(grep 'template_path:' .st3/artifacts.yaml | grep -v 'null' | awk '{print $2}' | tr -d '"'); do
    if [ ! -f "mcp_server/templates/$path" ]; then
        echo "MISSING: $path"
    fi
done
```

### Task 5: Handle Service Template Selection
**File**: [mcp_server/scaffolders/template_scaffolder.py](mcp_server/scaffolders/template_scaffolder.py)

**Changes**:
```python
def scaffold(self, artifact_type: str, context: dict[str, Any]) -> ScaffoldResult:
    # ... existing validation ...
    
    template_path = artifact.get("template_path")
    
    # SPECIAL: Service type selects template based on service_type
    if artifact_type == "service" and template_path is None:
        service_type = context.get("service_type", "orchestrator")
        template_path = f"components/service_{service_type}.py.jinja2"
    
    # SPECIAL: Generic type uses template_name from context
    elif artifact_type == "generic" and template_path is None:
        template_path = context.get("template_name")
        if not template_path:
            return ScaffoldResult.error(
                "Generic artifacts require 'template_name' in context",
                hints=["Provide template_name: 'path/to/template.jinja2'"]
            )
    
    if not template_path:
        return ScaffoldResult.error(
            f"No template configured for artifact type: {artifact_type}",
            hints=[
                "Check .st3/artifacts.yaml for template_path configuration",
                f"Artifact type '{artifact_type}' must have template_path",
            ]
        )
    
    # Continue with rendering...
    content = self._load_and_render_template(template_path, merged_context)
```

**Acceptance Criteria**:
- [ ] Service type: Reads `service_type` from context
- [ ] Service type: Maps to correct template (orchestrator/command/query)
- [ ] Service type: Defaults to "orchestrator" if not specified
- [ ] Generic type: Reads `template_name` from context
- [ ] Generic type: Raises ValidationError if template_name missing
- [ ] Both special cases use relative paths

**Verification**:
```python
# Unit test - service orchestrator
result = scaffolder.scaffold(
    artifact_type="service",
    context={"name": "TestService", "service_type": "orchestrator"}
)
assert result.success
assert "TestService" in result.content

# Unit test - service command
result = scaffolder.scaffold(
    artifact_type="service",
    context={"name": "TestCommand", "service_type": "command"}
)
assert result.success

# Unit test - generic with template_name
result = scaffolder.scaffold(
    artifact_type="generic",
    context={
        "name": "CustomComponent",
        "template_name": "components/generic.py.jinja2",
        "output_path": "custom/component.py"
    }
)
assert result.success

# Unit test - generic without template_name (error)
result = scaffolder.scaffold(
    artifact_type="generic",
    context={"name": "Broken"}
)
assert not result.success
assert "template_name" in result.error
```

## Testing Requirements

### Unit Tests
**File**: `tests/unit/test_template_scaffolder.py` (new or update existing)

**Tests Required**:

1. **Test Constructor**:
   ```python
   def test_constructor_default_renderer():
       """TemplateScaffolder creates default JinjaRenderer."""
       scaffolder = TemplateScaffolder(artifact_manager)
       assert scaffolder._renderer is not None
       assert scaffolder._renderer.template_dir.name == "templates"
   
   def test_constructor_custom_renderer():
       """TemplateScaffolder accepts custom renderer."""
       custom_renderer = Mock(spec=JinjaRenderer)
       scaffolder = TemplateScaffolder(artifact_manager, renderer=custom_renderer)
       assert scaffolder._renderer is custom_renderer
   ```

2. **Test _load_and_render_template**:
   ```python
   def test_load_and_render_success(tmp_path, monkeypatch):
       """Render template successfully."""
       # Setup mock renderer
       mock_renderer = Mock(spec=JinjaRenderer)
       mock_renderer.render.return_value = "rendered content"
       
       scaffolder = TemplateScaffolder(artifact_manager, renderer=mock_renderer)
       result = scaffolder._load_and_render_template(
           "components/dto.py.jinja2",
           {"name": "TestDTO"}
       )
       
       assert result == "rendered content"
       mock_renderer.render.assert_called_once_with(
           "components/dto.py.jinja2",
           name="TestDTO"
       )
   
   def test_load_and_render_template_not_found(tmp_path):
       """Template not found raises ValidationError."""
       scaffolder = TemplateScaffolder(artifact_manager)
       
       with pytest.raises(ValidationError) as exc_info:
           scaffolder._load_and_render_template("nonexistent.jinja2", {})
       
       assert "Template not found" in exc_info.value.message
       assert exc_info.value.hints is not None
       assert "mcp_server/templates" in exc_info.value.hints[0]
   ```

3. **Test scaffold Method**:
   ```python
   def test_scaffold_dto_success():
       """Scaffold DTO artifact successfully."""
       result = scaffolder.scaffold(
           artifact_type="dto",
           context={"name": "UserDTO", "description": "User data"}
       )
       assert result.success
       assert "class UserDTO" in result.content
   
   def test_scaffold_design_doc_success():
       """Scaffold design document successfully."""
       result = scaffolder.scaffold(
           artifact_type="design",
           context={
               "title": "Test Design",
               "author": "Agent",
               "issue_number": 56
           }
       )
       assert result.success
       assert "# Test Design" in result.content
   
   def test_scaffold_service_with_type():
       """Service type selects correct template."""
       result = scaffolder.scaffold(
           artifact_type="service",
           context={"name": "MyService", "service_type": "command"}
       )
       assert result.success
       # Verify command service template was used
   
   def test_scaffold_generic_with_template_name():
       """Generic artifact uses template_name from context."""
       result = scaffolder.scaffold(
           artifact_type="generic",
           context={
               "name": "Custom",
               "template_name": "components/generic.py.jinja2",
               "output_path": "custom.py"
           }
       )
       assert result.success
   
   def test_scaffold_generic_without_template_name():
       """Generic artifact without template_name fails."""
       result = scaffolder.scaffold(
           artifact_type="generic",
           context={"name": "Broken"}
       )
       assert not result.success
       assert "template_name" in result.error.lower()
   ```

**Acceptance Criteria**:
- [ ] All unit tests pass
- [ ] Constructor tests verify default and custom renderer
- [ ] _load_and_render_template tests verify safe rendering
- [ ] Template not found raises ValidationError with hints
- [ ] scaffold method tests cover all artifact types
- [ ] Service special case tested (orchestrator/command/query)
- [ ] Generic special case tested (with/without template_name)
- [ ] All tests use mock renderer or real templates

### Integration Tests
**File**: `tests/integration/test_template_scaffolder_integration.py` (new)

**Tests Required**:

1. **Test Real Template Rendering**:
   ```python
   def test_render_dto_template_with_real_context(hermetic_env):
       """Render real DTO template in hermetic environment."""
       scaffolder = TemplateScaffolder(artifact_manager)
       
       result = scaffolder.scaffold(
           artifact_type="dto",
           context={
               "name": "ProductDTO",
               "description": "Product data transfer object",
               "fields": [
                   {"name": "id", "type": "int", "default": None},
                   {"name": "name", "type": "str", "default": '""'},
               ],
           }
       )
       
       assert result.success
       assert "class ProductDTO(BaseModel)" in result.content
       assert "id: int" in result.content
       assert 'name: str = ""' in result.content
   
   def test_render_worker_template_with_real_context(hermetic_env):
       """Render real Worker template."""
       result = scaffolder.scaffold(
           artifact_type="worker",
           context={
               "name": "ProcessOrder",
               "input_dto": "OrderInputDTO",
               "output_dto": "OrderResultDTO",
               "docstring": "Process an order",
           }
       )
       
       assert result.success
       assert "class ProcessOrderWorker" in result.content
       assert "OrderInputDTO" in result.content
       assert "OrderResultDTO" in result.content
   
   def test_render_design_doc_template(hermetic_env):
       """Render real design document template."""
       result = scaffolder.scaffold(
           artifact_type="design",
           context={
               "title": "API Design",
               "author": "Agent",
               "issue_number": 56,
               "status": "DRAFT",
               "summary": "Design for new API endpoints",
           }
       )
       
       assert result.success
       assert "# API Design" in result.content
       assert "**Status**: DRAFT" in result.content
       assert "Design for new API endpoints" in result.content
   ```

2. **Test All Template Types**:
   ```python
   @pytest.mark.parametrize("artifact_type,context", [
       ("dto", {"name": "TestDTO", "description": "Test"}),
       ("worker", {"name": "TestWorker", "input_dto": "In", "output_dto": "Out"}),
       ("adapter", {"name": "TestAdapter", "interface": "ITest"}),
       ("tool", {"name": "TestTool", "input_schema": {}}),
       ("resource", {"name": "TestResource", "uri_pattern": "test://*"}),
       ("schema", {"name": "TestSchema"}),
       ("interface", {"name": "ITestInterface"}),
       ("design", {"title": "Test", "author": "Agent", "issue_number": 1}),
       ("architecture", {"title": "Test", "author": "Agent"}),
   ])
   def test_scaffold_all_artifact_types(hermetic_env, artifact_type, context):
       """Verify all artifact types can be scaffolded."""
       scaffolder = TemplateScaffolder(artifact_manager)
       result = scaffolder.scaffold(artifact_type, context)
       
       assert result.success, f"Failed to scaffold {artifact_type}: {result.error}"
       assert len(result.content) > 0
   ```

**Acceptance Criteria**:
- [ ] All integration tests pass
- [ ] Real templates rendered with real context
- [ ] Output content matches expected structure
- [ ] All artifact types tested (code + documents)
- [ ] Template variables substituted correctly
- [ ] Generated code/docs are valid (not just rendered)

### E2E Tests
**File**: `tests/e2e/test_template_scaffolder_e2e.py` (new)

**Tests Required**:

1. **Test Full Scaffold Flow (Code Artifact)**:
   ```python
   def test_scaffold_dto_full_flow(hermetic_env):
       """E2E: Scaffold DTO from artifacts.yaml to disk."""
       # Setup
       artifact_manager = ArtifactManager(...)
       scaffolder = TemplateScaffolder(artifact_manager)
       output_path = hermetic_env.workspace / "dtos" / "user_dto.py"
       
       # Scaffold
       result = scaffolder.scaffold(
           artifact_type="dto",
           context={
               "name": "UserDTO",
               "description": "User data",
               "fields": [
                   {"name": "id", "type": "int"},
                   {"name": "username", "type": "str"},
               ],
           }
       )
       
       # Write to disk (simulating tool behavior)
       output_path.parent.mkdir(parents=True, exist_ok=True)
       output_path.write_text(result.content, encoding='utf-8')
       
       # Verify
       assert output_path.exists()
       content = output_path.read_text(encoding='utf-8')
       assert "class UserDTO(BaseModel)" in content
       assert "id: int" in content
       assert "username: str" in content
       
       # Verify valid Python (can import)
       import_result = subprocess.run(
           ["python", "-c", f"import sys; sys.path.insert(0, '{hermetic_env.workspace}'); from dtos.user_dto import UserDTO"],
           capture_output=True,
           text=True
       )
       assert import_result.returncode == 0
   ```

2. **Test Full Scaffold Flow (Document Artifact)**:
   ```python
   def test_scaffold_design_doc_full_flow(hermetic_env):
       """E2E: Scaffold design document from artifacts.yaml to disk."""
       # Setup
       artifact_manager = ArtifactManager(...)
       scaffolder = TemplateScaffolder(artifact_manager)
       output_path = hermetic_env.workspace / "docs" / "design.md"
       
       # Scaffold
       result = scaffolder.scaffold(
           artifact_type="design",
           context={
               "title": "Authentication Design",
               "author": "System",
               "issue_number": 42,
               "status": "DRAFT",
               "summary": "OAuth2 implementation",
               "sections": [
                   "## Requirements",
                   "## Architecture",
                   "## Implementation",
               ],
           }
       )
       
       # Write to disk
       output_path.parent.mkdir(parents=True, exist_ok=True)
       output_path.write_text(result.content, encoding='utf-8')
       
       # Verify
       assert output_path.exists()
       content = output_path.read_text(encoding='utf-8')
       assert "# Authentication Design" in content
       assert "**Status**: DRAFT" in content
       assert "OAuth2 implementation" in content
       assert "## Requirements" in content
   ```

3. **Test Template Path Security**:
   ```python
   def test_template_path_traversal_blocked(hermetic_env):
       """E2E: Path traversal attempts are blocked."""
       scaffolder = TemplateScaffolder(artifact_manager)
       
       # Attempt path traversal
       result = scaffolder.scaffold(
           artifact_type="generic",
           context={
               "name": "Malicious",
               "template_name": "../../etc/passwd",  # ❌ Should fail
               "output_path": "output.txt"
           }
       )
       
       # Verify blocked
       assert not result.success
       assert "Template not found" in result.error
   ```

**Acceptance Criteria**:
- [ ] E2E test scaffolds code artifact to disk
- [ ] Generated code is valid Python (can import)
- [ ] E2E test scaffolds document artifact to disk
- [ ] Generated document has correct structure
- [ ] Path traversal attempts are blocked
- [ ] All tests use hermetic environment (temp dirs)
- [ ] Tests prove safe template loading (no open() bypass)

## Quality Gates

### Code Quality
**Tool**: Pylint

**Target**: 10/10 on all modified files

**Files to Check**:
- `mcp_server/scaffolders/template_scaffolder.py`
- Any new test files

**Command**:
```bash
pylint mcp_server/scaffolders/template_scaffolder.py
```

**Acceptance Criteria**:
- [ ] Pylint score: 10.00/10
- [ ] No trailing whitespace
- [ ] Proper docstrings (Google style)
- [ ] Type hints on all public methods
- [ ] No unused imports

### Type Safety
**Tool**: Pyright

**Target**: PASS (zero errors)

**Command**:
```bash
pyright mcp_server/scaffolders/template_scaffolder.py
```

**Acceptance Criteria**:
- [ ] Pyright: 0 errors
- [ ] All type hints correct
- [ ] No type: ignore comments (unless justified)

### Test Coverage
**Tool**: pytest with coverage

**Target**: 100% on modified code

**Command**:
```bash
pytest --cov=mcp_server/scaffolders/template_scaffolder --cov-report=term-missing
```

**Acceptance Criteria**:
- [ ] Line coverage: 100% on template_scaffolder.py
- [ ] All branches covered
- [ ] No uncovered lines

### Test Execution
**Tool**: pytest

**Target**: All tests GREEN, no regressions

**Command**:
```bash
pytest tests/ -v
```

**Acceptance Criteria**:
- [ ] All new tests pass (unit + integration + E2E)
- [ ] All existing tests still pass (no regressions)
- [ ] Test count increased (prove new tests added)
- [ ] No skipped tests (unless intentional)

## Definition of Done

### Code Changes
- [ ] TemplateScaffolder.__init__ accepts JinjaRenderer parameter
- [ ] TemplateScaffolder creates default renderer if not provided
- [ ] _load_and_render_template uses renderer.render() (no open())
- [ ] _load_and_render_template parameter renamed to template_name
- [ ] Template paths are relative (not absolute)
- [ ] ExecutionError caught and re-raised as ValidationError
- [ ] Service type special handling implemented
- [ ] Generic type special handling implemented
- [ ] No direct file I/O in TemplateScaffolder (all via renderer)

### Configuration Changes
- [ ] artifacts.yaml: All code artifact template_path filled
- [ ] artifacts.yaml: All template paths are relative
- [ ] artifacts.yaml: Service and generic special cases documented
- [ ] All referenced templates exist in mcp_server/templates/

### Testing
- [ ] Unit tests written (constructor, render, scaffold)
- [ ] Integration tests written (real templates)
- [ ] E2E tests written (full flow to disk)
- [ ] Security test (path traversal blocked)
- [ ] All tests pass (1197+ tests GREEN)
- [ ] No test regressions (all existing tests still pass)

### Quality
- [ ] Pylint: 10.00/10 on template_scaffolder.py
- [ ] Pyright: PASS (0 errors)
- [ ] Coverage: 100% on modified code
- [ ] No trailing whitespace
- [ ] Mandatory file headers present
- [ ] Docstrings on all public methods

### Documentation
- [ ] Code comments explain why (not what)
- [ ] Docstrings follow Google style
- [ ] Type hints on all public methods
- [ ] Acceptance criteria explicitly verified

### Commit
- [ ] Commit message references this checklist
- [ ] Commit message: "Slice 2 COMPLETE: Fix Template Loading & Paths"
- [ ] All DoD items checked before commit
- [ ] Quality gates run and passed before commit

## Verification Steps

### Pre-Commit Verification
Run these commands BEFORE claiming "DONE":

```bash
# 1. Run all tests
pytest tests/ -v

# 2. Check quality (Pylint)
pylint mcp_server/scaffolders/template_scaffolder.py

# 3. Check types (Pyright)
pyright mcp_server/scaffolders/template_scaffolder.py

# 4. Check coverage
pytest --cov=mcp_server/scaffolders/template_scaffolder --cov-report=term-missing

# 5. Check for trailing whitespace
git diff --check

# 6. Verify all templates exist
python -c "
import yaml
from pathlib import Path

# Load artifacts.yaml
with open('.st3/artifacts.yaml') as f:
    data = yaml.safe_load(f)

# Check all template paths
missing = []
for artifact in data['artifact_types']:
    template_path = artifact.get('template_path')
    if template_path and template_path != 'null':
        full_path = Path('mcp_server/templates') / template_path
        if not full_path.exists():
            missing.append(template_path)

if missing:
    print('MISSING TEMPLATES:')
    for m in missing:
        print(f'  - {m}')
    exit(1)
else:
    print('✓ All templates exist')
"
```

**Acceptance Criteria**:
- [ ] All commands exit with code 0
- [ ] No errors, no warnings, no failures
- [ ] All DoD items verified programmatically

### Post-Commit Verification
Run these AFTER commit to verify:

```bash
# 1. Verify no open() calls remain in TemplateScaffolder
grep -n "open(" mcp_server/scaffolders/template_scaffolder.py
# Expected: No matches (or only in comments)

# 2. Verify renderer injection
grep -n "_renderer" mcp_server/scaffolders/template_scaffolder.py
# Expected: Multiple matches (init, usage)

# 3. Verify test count increased
pytest tests/ --co -q | wc -l
# Expected: > 1197 (proof of new tests)

# 4. Run E2E smoke test
pytest tests/e2e/test_template_scaffolder_e2e.py -v
# Expected: All pass
```

## Success Criteria

### Primary Goals
1. ✅ No unsafe `open()` calls in TemplateScaffolder
2. ✅ All template loading via JinjaRenderer + FileSystemLoader
3. ✅ Template paths relative and portable
4. ✅ Path traversal attempts blocked
5. ✅ All tests GREEN (no regressions)
6. ✅ Quality gates: 10/10 Pylint, PASS Pyright
7. ✅ Definition of Done explicitly verified

### Risk Mitigation
- **Risk**: Claim "DONE" prematurely (like Slice 1)
- **Mitigation**: Explicit checklist, verification steps, pre-commit checks

- **Risk**: E2E tests pass but don't prove security
- **Mitigation**: Security-specific test (path traversal)

- **Risk**: Break existing functionality
- **Mitigation**: Run full test suite, check for regressions

- **Risk**: Miss edge cases
- **Mitigation**: Parametrized tests, all artifact types covered

## Timeline
- **Preparation**: COMPLETE (this document)
- **Implementation**: ~2-3 hours
  - Task 1-2: 30 min (constructor + render method)
  - Task 3-5: 30 min (scaffold method + special cases)
  - Testing: 60-90 min (unit + integration + E2E)
  - Quality: 15 min (pylint + pyright + coverage)
  - Verification: 15 min (run all checks)
- **Total**: ~2.5-3.5 hours

## Notes
- This checklist is PREVENTION (not correction like slice1_gaps.md)
- Cannot claim "DONE" until ALL checkboxes checked
- User has right to review checklist and verify claims
- Lessons learned: Thoroughness > Speed

# Template Analysis: Gap Analysis & Quality Assessment

**Date:** 2025-12-30  
**Purpose:** Comprehensive template review for SSOT architecture (Issue #52)  
**Scope:** Inventory, patterns, gaps, quality

---

## Executive Summary

**Templates as Single Source of Truth:**
With templates becoming the foundation for both scaffolding AND validation, we must ensure:
1. **Completeness** - All component types have templates
2. **Quality** - Templates match actual codebase patterns
3. **Metadata** - Templates contain validation rules (future: frontmatter)
4. **Consistency** - Templates follow established standards

**Findings:**
- ✅ **21 templates exist** - Good foundation
- ⚠️ **3 critical gaps** - research.md, planning.md, ST3 integration tests  
- ⚠️ **Quality issues** - Some templates don't match actual code patterns
- ✅ **Good structure** - Base templates + inheritance working well

---

## 1. Template Inventory

### 1.1 Existing Templates (21 files, 73KB total)

#### Base Templates (3)
| Template | Purpose | Extends | Quality |
|----------|---------|---------|---------|
| `base/base_component.py.jinja2` | Python component base | - | ⭐⭐⭐⭐ Good |
| `base/base_document.md.jinja2` | Documentation base | - | ⭐⭐⭐ OK |
| `base/base_test.py.jinja2` | Test file base | - | ⭐⭐⭐⭐ Excellent |

**Assessment:**
- ✅ Base templates enforce consistency (imports, header, structure)
- ✅ Inheritance pattern works well (DRY principle)
- ✅ base_test.py.jinja2 has excellent structure:
  - Forces stdlib → third-party → local import order
  - Enforces snake_case mock naming (mock_manager_class)
  - Requires type hints and docstrings
  - Supports async tests

#### Component Templates (12)
| Template | Purpose | Size | Extends Base | Quality |
|----------|---------|------|--------------|---------|
| `components/worker.py.jinja2` | Worker components | 153 lines | No | ⭐⭐⭐⭐ Good |
| `components/worker_test.py.jinja2` | Worker tests | TBD | base_test | ⭐⭐⭐ OK |
| `components/dto.py.jinja2` | Data Transfer Objects | 144 lines | No | ⭐⭐⭐⭐⭐ Excellent |
| `components/dto_test.py.jinja2` | DTO tests | TBD | base_test | ⭐⭐⭐ OK |
| `components/tool.py.jinja2` | MCP Tools | ~50 lines | base_component | ⭐⭐⭐⭐ Good |
| `components/adapter.py.jinja2` | External adapters | TBD | base_component | ⚠️ Not analyzed |
| `components/interface.py.jinja2` | Protocol interfaces | TBD | base_component | ⚠️ Not analyzed |
| `components/resource.py.jinja2` | MCP Resources | TBD | base_component | ⚠️ Not analyzed |
| `components/schema.py.jinja2` | Pydantic schemas | TBD | base_component | ⚠️ Not analyzed |
| `components/service_*.py.jinja2` | Services (3 types) | TBD | base_component | ⚠️ Not analyzed |
| `components/generic.py.jinja2` | Generic component | TBD | base_component | ⚠️ Not analyzed |

**Key Findings:**

**Worker Template (worker.py.jinja2):**
- ✅ Excellent structure matches backend/core/interfaces/worker.py
- ✅ Supports all worker types (signal_detector, risk_monitor, context_worker)
- ✅ Proper dependency injection pattern
- ✅ BaseWorker[InputDTO, OutputDTO] generic typing
- ✅ Comprehensive docstrings with responsibilities
- ✅ Async process() method signature correct
- ⚠️ **Gap:** No IWorkerLifecycle two-phase initialization pattern!
  - Backend uses: `__init__(build_spec)` + `initialize(strategy_cache)`
  - Template uses: `__init__(strategy_cache, deps)` (old pattern)
  - **Impact:** Generated workers don't match actual architecture

**DTO Template (dto.py.jinja2):**
- ⭐⭐⭐⭐⭐ **Excellent** - Best template in codebase
- ✅ Matches backend/dtos/strategy/*.py patterns perfectly
- ✅ Causality tracking support (optional)
- ✅ ID generation with generate_*_id() pattern
- ✅ Timestamp with UTC timezone
- ✅ Field validation (ge, le, pattern, min_length, max_length)
- ✅ Pydantic model_config (frozen, validate_assignment, extra="forbid")
- ✅ Examples in json_schema_extra
- ✅ field_validator support
- ✅ Proper import organization
- 💡 **Exemplar:** Use this as quality benchmark for other templates

**Tool Template (tool.py.jinja2):**
- ✅ Extends base_component (good inheritance)
- ✅ BaseTool pattern correct
- ✅ name, description, input_schema properties present
- ✅ execute() returns ToolResult
- ⚠️ Simple structure - may need enhancement for complex tools

#### Document Templates (5)
| Template | Purpose | Extends | Quality |
|----------|---------|---------|---------|
| `documents/design.md.jinja2` | Design documents | base_document | ⭐⭐⭐⭐ Good |
| `documents/architecture.md.jinja2` | Architecture docs | base_document | ⭐⭐⭐ OK |
| `documents/tracking.md.jinja2` | Issue tracking docs | base_document | ⭐⭐⭐ OK |
| `documents/reference.md.jinja2` | Reference docs | base_document | ⭐⭐⭐ OK |
| `documents/generic.md.jinja2` | Generic markdown | base_document | ⭐⭐⭐ OK |

**Assessment:**
- ✅ Good coverage of document types
- ✅ Design template matches Epic #49 structure (Status, Author, Sections)
- ❌ **CRITICAL GAP:** No research.md template!
- ❌ **CRITICAL GAP:** No planning.md template!
- ⚠️ Templates don't match actual research/planning docs exactly

### 1.2 Template Missing vs Present Matrix

| Component Type | Template Exists | Used in Codebase | Priority |
|----------------|-----------------|------------------|----------|
| Worker | ✅ Yes | ✅ backend/workers/ | HIGH |
| DTO | ✅ Yes | ✅ backend/dtos/ | HIGH |
| Tool | ✅ Yes | ✅ mcp_server/tools/ | HIGH |
| Adapter | ✅ Yes | ✅ backend/adapters/ | MEDIUM |
| Interface | ✅ Yes | ✅ backend/core/interfaces/ | MEDIUM |
| Service | ✅ Yes (3 types) | ⚠️ Not found in backend/ | LOW |
| Resource | ✅ Yes | ✅ mcp_server/resources/ | LOW |
| Schema | ✅ Yes | ✅ backend/config/schemas/ | LOW |
| Generic Component | ✅ Yes | N/A | LOW |
| **research.md** | ❌ **NO** | ✅ **docs/development/issue*/research.md** | **CRITICAL** |
| **planning.md** | ❌ **NO** | ✅ **docs/development/issue*/planning.md** | **CRITICAL** |
| **Unit Test (ST3)** | ⚠️ Partial | ✅ tests/unit/core/ | **HIGH** |
| **Integration Test** | ❌ **NO** | ✅ tests/integration/ | **HIGH** |

---

## 2. Code Pattern Analysis

### 2.1 Backend Patterns (Actual Implementation)

#### DTOs (backend/dtos/strategy/signal.py)
```python
# Actual pattern from codebase:
"""
Signal DTO: SignalDetector output contract.

IMPORTANT: Signal is a PRE-CAUSALITY DTO.
- Signal represents a detection FACT
- CausalityChain created by StrategyPlanner
- Signal does NOT have causality field

@layer: DTO (Strategy)
@dependencies: [pydantic, datetime, decimal, backend.utils.id_generators]
@responsibilities: [signal detection contract, confidence scoring]
"""

class Signal(BaseModel):
    signal_id: str = Field(
        default_factory=generate_signal_id,
        pattern=r'^SIG_\d{8}_\d{6}_[0-9a-f]{8}$',
        description="Typed signal ID (military datetime format)"
    )
    timestamp: datetime = Field(description="When the signal was detected (UTC)")
    symbol: str = Field(pattern=r'^[A-Z]{2,10}_[A-Z]{2,10}$')
    direction: Literal["long", "short"]
    signal_type: str = Field(pattern=r'^[A-Z][A-Z0-9_]{2,24}$')
    confidence: Decimal | None = Field(default=None, ge=Decimal("0.0"), le=Decimal("1.0"))
```

**Template Match:** ⭐⭐⭐⭐⭐ **EXCELLENT** - dto.py.jinja2 can generate this!

#### Workers (backend/core/interfaces/worker.py)
```python
# Actual pattern from codebase:
class IWorkerLifecycle(Protocol):
    """Two-phase initialization pattern:
    1. Construction (__init__): Receive BuildSpec, store manifest
    2. Runtime initialization (initialize): Inject runtime dependencies
    """

# Worker implementation should be:
class SignalDetector:
    def __init__(self, build_spec: BuildSpec) -> None:
        self._manifest = build_spec.manifest
        self._strategy_cache: IStrategyCache | None = None  # Injected later
    
    def initialize(self, strategy_cache: IStrategyCache) -> None:
        """Runtime initialization - inject dependencies."""
        self._strategy_cache = strategy_cache
```

**Template Match:** ⚠️ **MISMATCH** - worker.py.jinja2 uses old single-phase pattern!

**Required Fix:**
```jinja
class {{ name }}(BaseWorker[{{ input_dto }}, {{ output_dto }}]):
    def __init__(self, build_spec: BuildSpec) -> None:
        """Construction phase - store manifest."""
        super().__init__()
        self._manifest = build_spec.manifest
        # Dependencies not injected yet
        
    def initialize(self, strategy_cache: IStrategyCache{% for dep in dependencies %}, {{ dep }}{% endfor %}) -> None:
        """Runtime initialization phase."""
        self._strategy_cache = strategy_cache
        {% for dep in dependencies %}
        self._{{ dep.split(':')[0].strip() }} = {{ dep.split(':')[0].strip() }}
        {% endfor %}
```

### 2.2 Test Patterns

#### ST3 Integration Tests (tests/integration/test_issue39_cross_machine.py)
```python
# Actual pattern:
"""Integration tests for Issue #39: Cross-machine state recovery.

Tests the complete flow:
1. Machine A: Initialize project
2. Machine A: Make commits with phase:label
3. Machine B: Pull code (state.json missing)
4. Machine B: Tools work transparently
"""

class TestIssue39CrossMachine:
    """Integration tests for cross-machine state recovery."""
    
    @pytest.fixture
    def workspace_root(self, tmp_path: Path) -> Path:
        """Create temporary workspace with git repo."""
        # Setup git repo, initial commit, etc.
    
    @pytest.mark.asyncio
    async def test_complete_cross_machine_flow(self, workspace_root: Path) -> None:
        """Test complete flow: Initialize → Commit → Delete state → Auto-recover."""
        # Arrange: Setup
        # Act: Execute flow
        # Assert: Verify outcome
```

**Template Match:** ⚠️ **PARTIAL** - base_test.py.jinja2 has good structure, but:
- ❌ No integration test specific template
- ❌ No git repo fixture pattern
- ❌ No tmp_path workspace setup pattern
- ❌ No cross-machine simulation pattern

### 2.3 Documentation Patterns

#### Research Documents (docs/development/issue39/research.md)
```markdown
# Actual pattern:
# Issue #39 Research: Project Initialization Infrastructure Gap

**Issue:** InitializeProjectTool does not initialize branch state  
**Epic Context:** Part of Epic #49, enables Epic #18  
**Date:** 2025-12-30  
**Status:** Research Complete

---

## Executive Summary
[3-5 paragraphs summarizing problem, solution, impact]

## Scope: Infrastructure Foundation (Not Enforcement)
**What This Issue Delivers:**
- ✅ Item 1
- ✅ Item 2

**What This Issue Does NOT Deliver:**
- ❌ Item 1
- ❌ Item 2

## Problem Statement
### Symptom: Manual Workarounds Required
### Root Cause: Foundation Infrastructure Missing

## Research Findings
[Detailed analysis with code examples]

## Recommendations
[Actionable recommendations]
```

**Template Match:** ❌ **MISSING** - No research.md template exists!

#### Planning Documents (docs/development/issue39/planning.md)
```markdown
# Actual pattern:
# Issue #39 Planning: Dual-Mode State Management Implementation

**Status:** DRAFT  
**Phase:** Planning  
**Date:** 2025-12-30

---

## Purpose
[Why this planning doc exists]

## Scope
**In Scope:**
**Out of Scope:**

## Implementation Goals
### Goal 1: Feature Name
**Objective:** [What]
**Success Criteria:**
- ✅ Criterion 1
**What Changes:**
- File changes

## Testing Strategy
## Rollout Plan
## Success Metrics
```

**Template Match:** ❌ **MISSING** - No planning.md template exists!

---

## 3. Gap Analysis

### 3.1 Critical Gaps (MUST FIX)

#### Gap 1: research.md Template
**Priority:** 🔴 **CRITICAL**  
**Impact:** Every issue needs research phase documentation  
**Used in:** docs/development/issue*/research.md (5+ examples exist)

**Required Template Structure:**
```jinja
# Issue #{{ issue_number }} Research: {{ title }}

**Issue:** {{ issue_description }}
**Epic Context:** {{ epic_context | default('Standalone issue') }}
**Date:** {{ date }}
**Status:** {{ status | default('In Progress') }}

---

## Executive Summary
{{ executive_summary | default('[3-5 paragraph summary]') }}

## Scope: {{ scope_title | default('Implementation Scope') }}

**What This Issue Delivers:**
{% for item in delivers %}
- ✅ {{ item }}
{% endfor %}

**What This Issue Does NOT Deliver:**
{% for item in not_delivers %}
- ❌ {{ item }}
{% endfor %}

## Problem Statement
{{ problem_statement }}

## Research Findings
{{ research_findings }}

## Recommendations
{{ recommendations }}
```

**Validation Rules to Extract:**
- Required sections: Executive Summary, Scope, Problem Statement, Research Findings, Recommendations
- Required frontmatter: Issue, Date, Status
- Checkboxes use ✅/❌ consistently
- Code blocks use proper syntax highlighting

#### Gap 2: planning.md Template
**Priority:** 🔴 **CRITICAL**  
**Impact:** Every issue needs planning phase documentation  
**Used in:** docs/development/issue*/planning.md (4+ examples exist)

**Required Template Structure:**
```jinja
# Issue #{{ issue_number }} Planning: {{ title }}

**Status:** {{ status | default('DRAFT') }}
**Phase:** Planning
**Date:** {{ date }}

---

## Purpose
{{ purpose }}

## Scope

**In Scope:**
{% for item in in_scope %}
- {{ item }}
{% endfor %}

**Out of Scope:**
{% for item in out_scope %}
- {{ item }}
{% endfor %}

## Implementation Goals

{% for goal in goals %}
### Goal {{ loop.index }}: {{ goal.name }}
**Objective:** {{ goal.objective }}

**Success Criteria:**
{% for criterion in goal.success_criteria %}
- ✅ {{ criterion }}
{% endfor %}

**What Changes:**
{% for change in goal.changes %}
- {{ change }}
{% endfor %}

{% endfor %}

## Testing Strategy
{{ testing_strategy }}

## Rollout Plan
{{ rollout_plan }}

## Success Metrics
{{ success_metrics }}
```

**Validation Rules to Extract:**
- Required sections: Purpose, Scope, Implementation Goals, Testing Strategy
- Goals must have: Objective, Success Criteria, What Changes
- Success criteria use ✅ checkboxes
- Status must be: DRAFT, REVIEW, APPROVED

#### Gap 3: Integration Test Template
**Priority:** 🔴 **HIGH**  
**Impact:** ST3 workflow tests need consistent structure  
**Used in:** tests/integration/ directory

**Required Template Structure:**
```jinja
{% extends "base/base_test.py.jinja2" %}

{% block test_description %}
Integration tests for {{ name }}: {{ description }}.

Tests the complete flow:
{% for step in flow_steps %}
{{ loop.index }}. {{ step }}
{% endfor %}
{% endblock %}

{% block test_stdlib_imports %}
{{ super() }}
import subprocess
from pathlib import Path
{% endblock %}

{% block shared_fixtures %}
@pytest.fixture
def workspace_root(self, tmp_path: Path) -> Path:
    """Create temporary workspace with git repo."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # Initialize git repo
    subprocess.run(["git", "init"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=workspace, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=workspace, check=True, capture_output=True)
    
    return workspace
{% endblock %}

{% block test_classes %}
class Test{{ name }}:
    """Integration tests for {{ description }}."""
    
    @pytest.mark.asyncio
    async def test_{{ test_name }}(self, workspace_root: Path) -> None:
        """{{ test_description }}"""
        # Arrange: {{ arrange_description }}
        
        # Act: {{ act_description }}
        
        # Assert: {{ assert_description }}
{% endblock %}
```

### 3.2 Medium Priority Gaps

#### Gap 4: Worker Template Two-Phase Init
**Priority:** 🟡 **HIGH**  
**Impact:** Generated workers don't match IWorkerLifecycle protocol  
**Fix:** Update worker.py.jinja2 to use two-phase initialization pattern

#### Gap 5: Service Templates Not Used
**Priority:** 🟢 **LOW**  
**Impact:** Service templates exist but no services in backend/  
**Action:** Verify if services planned, or remove unused templates

### 3.3 Template Quality Issues

| Template | Issue | Severity | Fix Required |
|----------|-------|----------|--------------|
| worker.py.jinja2 | Old single-phase init pattern | 🔴 HIGH | Implement IWorkerLifecycle |
| worker_test.py.jinja2 | Not analyzed yet | ⚠️ UNKNOWN | Review against actual tests |
| documents/design.md.jinja2 | Doesn't match research.md structure | 🟡 MEDIUM | May be correct (different doc type) |

---

## 4. Recommendations

### 4.1 Immediate Actions (Issue #52 Scope)

**Before implementing validation.yaml:**

1. **Create Missing Templates (CRITICAL):**
   - ✅ Create `documents/research.md.jinja2`
   - ✅ Create `documents/planning.md.jinja2`
   - ✅ Create `base/integration_test.py.jinja2`

2. **Fix Worker Template (HIGH):**
   - ✅ Update `components/worker.py.jinja2` with two-phase initialization
   - ✅ Match IWorkerLifecycle protocol from backend/core/interfaces/worker.py

3. **Quality Audit (MEDIUM):**
   - ⚠️ Review worker_test.py.jinja2 against actual test files
   - ⚠️ Review dto_test.py.jinja2 against actual test files
   - ⚠️ Review adapter.py.jinja2 against backend/adapters/ (if any)

### 4.2 Template Metadata Strategy (Issue #52 Core)

**Frontmatter Format:**
```jinja
{# TEMPLATE_METADATA
type: worker
description: "Worker component for data processing"
generates:
  class_pattern: "{{name}}Worker"
  required_class_suffix: "Worker"
  required_methods:
    - name: "process"
      async: true
      params: ["input_data: {{input_dto}}"]
      returns: "{{output_dto}}"
  required_imports:
    - "backend.core.interfaces.base_worker.BaseWorker"
    - "backend.core.interfaces.strategy_cache.IStrategyCache"
  base_class: "BaseWorker[{{input_dto}}, {{output_dto}}]"
validation:
  severity:
    missing_methods: "error"
    missing_imports: "warning"
    missing_class_suffix: "warning"
#}
```

**Parser Implementation:**
```python
def extract_template_metadata(template_path: Path) -> dict:
    """Extract validation metadata from template frontmatter."""
    source = template_path.read_text()
    
    # Find {# TEMPLATE_METADATA ... #} block
    match = re.search(r'\{#\s*TEMPLATE_METADATA\s*(.*?)\s*#\}', source, re.DOTALL)
    if not match:
        return {}
    
    # Parse YAML inside comment block
    metadata_yaml = match.group(1)
    return yaml.safe_load(metadata_yaml)
```

### 4.3 Validation Strategy

**SSOT Architecture:**
```
Templates (SSOT)
    ↓
    ├── Scaffolding → Generates code from templates
    │
    └── Validation → Reads metadata from templates
                    → Validates generated code matches template rules
```

**Implementation Order:**
1. Add metadata to existing templates (worker, tool, dto, adapter)
2. Create missing templates (research.md, planning.md, integration_test)
3. Build TemplateAnalyzer to read metadata
4. Build ValidationConfig that loads from templates (NOT yaml)
5. Update TemplateValidator to use template metadata
6. Remove hardcoded RULES dict

### 4.4 Quality Standards

**Template Quality Checklist:**
- [ ] Matches actual codebase patterns (compare against backend/, tests/)
- [ ] Includes comprehensive docstrings
- [ ] Has TEMPLATE_METADATA frontmatter with validation rules
- [ ] Uses proper import organization (stdlib → third-party → local)
- [ ] Supports common variations (async/sync, optional fields)
- [ ] Has usage examples in comments
- [ ] Generates Pylint 10/10 compliant code
- [ ] Includes type hints for all parameters and returns

**Before Committing New Template:**
1. ✅ Compare against 3+ real examples in codebase
2. ✅ Generate sample code and verify it passes quality gates
3. ✅ Add metadata with validation rules
4. ✅ Document all template variables in header comment
5. ✅ Test with scaffold_component tool

---

## 5. Impact on Issue #52

### 5.1 Revised Scope

**Original Scope:**
- Migrate RULES dict to validation.yaml

**Revised Scope (SSOT Architecture):**
- ❌ NOT validation.yaml (would be duplicate source of truth)
- ✅ Add metadata to templates (templates become SSOT)
- ✅ Create missing templates (research.md, planning.md, integration_test)
- ✅ Fix worker template (two-phase initialization)
- ✅ Build TemplateAnalyzer to read template metadata
- ✅ Update TemplateValidator to use template metadata
- ✅ Remove hardcoded RULES dict

### 5.2 Success Criteria (Updated)

**Must Have:**
- [ ] All component templates have TEMPLATE_METADATA frontmatter
- [ ] research.md template exists
- [ ] planning.md template exists
- [ ] integration_test.py template exists
- [ ] worker.py template uses two-phase initialization
- [ ] TemplateAnalyzer extracts metadata from templates
- [ ] TemplateValidator uses template metadata (not RULES dict)
- [ ] RULES dict removed from code
- [ ] All tests passing
- [ ] Pylint 10/10

**Quality Gates:**
- [ ] Templates match actual codebase patterns (verified against backend/, tests/)
- [ ] Generated code passes quality gates (Pylint 10/10)
- [ ] No hardcoded validation rules outside templates
- [ ] Documentation updated

### 5.3 Estimated Effort

**Original Estimate:** 1-2 days (simple dict → yaml migration)  
**Revised Estimate:** 3-4 days (architectural shift to SSOT + template creation)

**Breakdown:**
- Day 1: Create missing templates (research.md, planning.md, integration_test) - 4 hours
- Day 1: Fix worker template (two-phase init) - 2 hours
- Day 1: Add metadata to existing templates - 2 hours
- Day 2: Build TemplateAnalyzer - 4 hours
- Day 2: Update TemplateValidator - 2 hours
- Day 2: Testing and quality gates - 2 hours
- Day 3: Documentation and cleanup - 4 hours
- Day 3: Integration testing - 2 hours
- Buffer: 6 hours for unexpected issues

---

## 6. Next Steps

### Phase 1: Template Completion (Research Phase - CURRENT)
1. ✅ Document analysis complete (this document)
2. ⏳ Review with PO (human decision on scope change)
3. ⏳ Update research.md with SSOT approach
4. ⏳ Transition to planning phase

### Phase 2: Template Creation (Planning Phase)
1. Create research.md template
2. Create planning.md template
3. Create integration_test.py template
4. Fix worker.py template (two-phase init)
5. Add metadata frontmatter to all templates

### Phase 3: Implementation (TDD Phase)
1. Build TemplateAnalyzer (read metadata)
2. Update TemplateValidator (use metadata)
3. Remove RULES dict
4. Run quality gates

### Phase 4: Documentation
1. Update architecture docs
2. Document template metadata format
3. Add template creation guide

---

## 7. Appendix: Template Metadata Examples

### Example 1: Worker Template
```jinja
{# TEMPLATE_METADATA
type: worker
description: "Worker component following IWorkerLifecycle protocol"
generates:
  class_pattern: "{{name}}"
  required_class_suffix: ""  # No enforced suffix (flexible)
  base_class: "BaseWorker[{{input_dto}}, {{output_dto}}]"
  required_methods:
    - name: "__init__"
      params: ["build_spec: BuildSpec"]
      returns: "None"
    - name: "initialize"
      params: ["strategy_cache: IStrategyCache"]
      returns: "None"
    - name: "process"
      async: true
      params: ["input_data: {{input_dto}}"]
      returns: "{{output_dto}}"
  required_imports:
    - "backend.core.interfaces.base_worker.BaseWorker"
    - "backend.core.interfaces.worker.IWorkerLifecycle"
    - "backend.core.interfaces.strategy_cache.IStrategyCache"
validation:
  severity:
    missing_methods: "error"
    missing_base_class: "error"
    missing_imports: "warning"
file_patterns:
  - "backend/workers/**/*.py"
  - "!backend/workers/base_worker.py"
#}
```

### Example 2: Research Document Template
```jinja
{# TEMPLATE_METADATA
type: research_document
description: "Research phase documentation for issues"
generates:
  sections:
    - "Executive Summary"
    - "Scope"
    - "Problem Statement"
    - "Research Findings"
    - "Recommendations"
  required_frontmatter:
    - "Issue"
    - "Date"
    - "Status"
validation:
  severity:
    missing_sections: "error"
    missing_frontmatter: "warning"
    incorrect_checkbox_format: "warning"
file_patterns:
  - "docs/development/issue*/research.md"
#}
```

---

**Analysis Complete:** Ready for PO review and scope decision.

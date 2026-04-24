# Template-Driven Validation System - Technical Design

**Status:** DRAFT
**Author:** AI Agent
**Created:** 2026-01-01
**Last Updated:** 2026-01-01
**Issue:** #52

---

## 1. Overview

### 1.1 Purpose

This design document specifies the technical architecture for migrating from hardcoded validation rules (RULES dict) to a template-driven validation system where Jinja2 templates serve as the single source of truth (SSOT) for both scaffolding AND validation.

**Key Innovation:** Templates embed validation metadata in YAML frontmatter, enabling a three-tier enforcement model (Format → Architectural → Guidelines) that balances strictness with flexibility.

### 1.2 Scope

**In Scope (Epic #49: Config Infrastructure):**
- TemplateAnalyzer component (metadata extraction from templates)
- LayeredTemplateValidator component (three-tier enforcement logic)
- Template metadata schema specification (YAML frontmatter format)
- Integration contracts with SafeEditTool and ValidatorRegistry
- **Template metadata ONLY** for 6 core templates (dto, tool, base_document - no redesign)
- Removal of hardcoded RULES dict (30 lines) from existing validator
- Template version field support (for future template evolution)

**Out of Scope (Moved to Other Epics):**
- Worker template redesign (IWorkerLifecycle two-phase) → Epic: Template Library
- Document templates (research, planning, unit_test) → Epic: Template Library  
- Template governance (quarterly review, Rule of Three) → Epic: Template Governance
- AST-based Python validation improvements (future enhancement)
- Epic #18 enforcement policy tooling (separate concern)

### 1.3 Related Documents

- [Research Document](research.md) - Problem analysis and proposed architecture
- [Planning Document](planning.md) - Implementation goals and rollout strategy
- [Core Principles](../../architecture/CORE_PRINCIPLES.md)
- [Architectural Shifts](../../architecture/ARCHITECTURAL_SHIFTS.md)

---

## 2. Background

### 2.1 Current State

**Existing Architecture:**
\\\python
# mcp_server/validation/template_validator.py
class TemplateValidator:
    RULES: dict[str, dict[str, Any]] = {
        \"worker\": {
            \"required_class_suffix\": \"Worker\",
            \"required_methods\": [\"execute\"],
            \"required_imports\": [\"BaseWorker\", \"TaskResult\"]
        },
        \"tool\": {...},
        \"dto\": {...}
    }
\\\

**Problems:**
1. **Duplicate SSOT:** Templates define structure, RULES dict defines validation
2. **Synchronization Burden:** Changes require updating both template AND RULES
3. **Limited Flexibility:** Single enforcement level (all rules are strict)
4. **No Agent Guidance:** Document templates lack content guidance

### 2.2 Problem Statement

How do we maintain validation rules in templates (SSOT) while enabling:
- **Strict format enforcement** (import order, docstrings) → blocks on error
- **Strict architectural enforcement** (base class, required methods) → blocks on error  
- **Flexible guideline suggestions** (naming, ordering) → warnings only

### 2.3 Requirements

#### Functional Requirements

- **FR1:** Extract validation metadata from Jinja2 template comments without rendering
- **FR2:** Support three enforcement levels: STRICT (format), ARCHITECTURAL (mixed), GUIDELINE (loose)
- **FR3:** Enforce base template format rules universally across all child templates
- **FR4:** Stop validation on first ERROR, continue through all WARNINGs
- **FR5:** Include agent hints in validation responses for document templates
- **FR6:** Resolve template inheritance chains to merge metadata from base templates

#### Non-Functional Requirements

- **NFR1:** Performance - Metadata extraction < 100ms per template
- **NFR2:** Testability - 100% coverage on TemplateAnalyzer and LayeredTemplateValidator
- **NFR3:** Maintainability - Zero hardcoded rules, all validation from templates
- **NFR4:** Extensibility - Adding new template requires only template file (no code changes)

#### Backward Compatibility & Versioning

**Validation Mechanism: NO backward compatibility (clean break)**
- Old RULES dict will be removed completely (30 lines deleted)
- No compatibility layer between hardcoded validation and template-driven validation
- Files must pass new template-driven validation immediately

**Template Evolution: YES versioning support**
- Templates include `version` field in metadata: `{# TEMPLATE_METADATA version: "2.0" #}`
- Template versions enable future evolution (v1.0 → v2.0 → v3.0)
- Validation logic CAN check version field for version-specific rules (future)
- Example: worker v1.0 (single-phase) vs v2.0 (IWorkerLifecycle) can coexist during transition

**Rationale:**
- Clean break for infrastructure (no technical debt)
- Controlled evolution for templates (gradual adoption)

---

## 3. Design

### 3.1 Architecture Position

\\\mermaid
graph TD
    A[SafeEditTool] -->|validates file| B[LayeredTemplateValidator]
    B -->|extracts metadata| C[TemplateAnalyzer]
    C -->|reads| D[Jinja2 Templates]
    D -->|inheritance| E[base_document.md.jinja2]
    D -->|inheritance| F[base_component.py.jinja2]
    
    B -->|Tier 1| G[Format Validation]
    B -->|Tier 2| H[Architectural Validation]
    B -->|Tier 3| I[Guidelines Validation]
    
    G -->|ERROR blocks| J[ValidationResult]
    H -->|ERROR blocks| J
    I -->|WARNING only| J
    
    J -->|with hints| A
    
    style D fill:#e1f5ff
    style B fill:#ffe1f5
    style J fill:#e1ffe1
\\\

**Component Relationships:**
- **Templates** (SSOT) → contain both scaffolding structure and validation metadata
- **TemplateAnalyzer** → extracts metadata from template YAML frontmatter
- **LayeredTemplateValidator** → enforces three-tier validation model
- **SafeEditTool** → orchestrates validation and returns results with hints

### 3.2 Component Design

#### 3.2.1 TemplateAnalyzer

**Purpose:** Extract and parse validation metadata from Jinja2 templates.

**Responsibilities:**
- Parse YAML metadata from Jinja2 comment blocks
- Extract Jinja2 variables using \meta.find_undeclared_variables()\
- Resolve template inheritance chain (extends tracking)
- Merge metadata from parent templates
- Handle missing metadata gracefully

**Dependencies:**
- \jinja2\ (Environment, meta module)
- \yaml\ (safe_load)
- \pathlib\ (Path operations)

**Class Interface:**
\\\python
from pathlib import Path
from typing import Any
from jinja2 import Environment, meta
import yaml
import re

class TemplateAnalyzer:
    \"\"\"Analyzes Jinja2 templates to extract validation metadata.\"\"\"
    
    def __init__(self, template_root: Path):
        \"\"\"
        Initialize analyzer with template directory root.
        
        Args:
            template_root: Root directory containing all templates.
        \"\"\"
        self.template_root = template_root
        self.env = Environment()
    
    def extract_metadata(self, template_path: Path) -> dict[str, Any]:
        \"\"\"
        Extract validation metadata from template.
        
        Returns metadata dict with structure:
        {
            \"enforcement\": \"STRICT\" | \"ARCHITECTURAL\" | \"GUIDELINE\",
            \"level\": \"format\" | \"content\",
            \"extends\": \"path/to/base.jinja2\" | None,
            \"validates\": {
                \"strict\": [...],
                \"guidelines\": [...]
            },
            \"variables\": [\"name\", \"type\", ...],
            \"purpose\": \"...\",
            \"content_guidance\": {...},
            \"agent_hint\": \"...\"
        }
        
        Returns empty dict if no metadata found.
        \"\"\"
        pass
    
    def get_base_template(self, template_path: Path) -> Path | None:
        \"\"\"
        Get the base template this template extends.
        
        Args:
            template_path: Path to template file.
            
        Returns:
            Path to base template or None if no inheritance.
        \"\"\"
        pass
    
    def get_inheritance_chain(self, template_path: Path) -> list[Path]:
        \"\"\"
        Get complete inheritance chain from base to specific.
        
        Args:
            template_path: Path to template file.
            
        Returns:
            List of template paths from most specific to most general.
            Example: [worker.py.jinja2, base_component.py.jinja2]
        \"\"\"
        pass
    
    def merge_metadata(
        self, 
        child: dict[str, Any], 
        parent: dict[str, Any]
    ) -> dict[str, Any]:
        \"\"\"
        Merge child and parent metadata, with child taking precedence.
        
        Merging rules:
        - strict rules: concatenate (child + parent, no duplicates)
        - guidelines: concatenate (child + parent, no duplicates)
        - enforcement: child overrides parent
        - variables: union of both
        - purpose/hints: child overrides parent
        
        Args:
            child: Child template metadata.
            parent: Parent template metadata.
            
        Returns:
            Merged metadata dictionary.
        \"\"\"
        pass
\\\

**Implementation Notes:**
- Use regex to extract YAML from Jinja2 comments: \{# TEMPLATE_METADATA ... #}\
- Use \Environment.parse()\ for Jinja2 AST analysis
- Cache inheritance chains to avoid repeated filesystem reads
- Handle circular inheritance gracefully (log warning, return chain so far)

#### 3.2.2 LayeredTemplateValidator

**Purpose:** Enforce three-tier validation model with fail-fast on errors.

**Responsibilities:**
- Validate format rules from base templates (Tier 1)
- Validate architectural rules from specific templates (Tier 2)
- Validate guidelines from all templates (Tier 3)
- Stop on first ERROR, continue through WARNINGs
- Include agent hints in validation results

**Dependencies:**
- \TemplateAnalyzer\ (metadata extraction)
- \BaseValidator\ (validation interface)
- \ValidationResult\, \ValidationIssue\ (result types)

**Class Interface:**
\\\python
from pathlib import Path
from .base import BaseValidator, ValidationResult, ValidationIssue
from .template_analyzer import TemplateAnalyzer

class LayeredTemplateValidator(BaseValidator):
    \"\"\"
    Three-tier template validator enforcing format → architectural → guidelines.
    
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
    \"\"\"
    
    def __init__(
        self, 
        template_type: str,
        template_analyzer: TemplateAnalyzer
    ):
        \"\"\"
        Initialize validator for specific template type.
        
        Args:
            template_type: Template identifier (worker, dto, tool, research, etc.)
            template_analyzer: Analyzer for extracting template metadata.
        \"\"\"
        self.template_type = template_type
        self.analyzer = template_analyzer
        self.metadata = self._load_metadata()
    
    async def validate(
        self, 
        path: str, 
        content: str | None = None
    ) -> ValidationResult:
        \"\"\"
        Validate file against template rules using three-tier model.
        
        Validation flow:
        1. Validate format rules (base template) - stop on ERROR
        2. Validate architectural rules (specific template) - stop on ERROR
        3. Validate guidelines (all templates) - collect WARNINGs
        4. Return combined result with agent hints
        
        Args:
            path: File path to validate.
            content: Optional file content (reads from path if None).
            
        Returns:
            ValidationResult with issues, score, and optional agent hints.
        \"\"\"
        pass
    
    def _load_metadata(self) -> dict[str, Any]:
        \"\"\"Load and merge metadata for template type.\"\"\"
        pass
    
    def _validate_format(
        self, 
        content: str, 
        metadata: dict[str, Any]
    ) -> list[ValidationIssue]:
        \"\"\"
        Validate Tier 1: Format rules from base template.
        
        Checks:
        - Import order (stdlib → third-party → local)
        - Docstring presence
        - Type hints on functions
        - File header/frontmatter
        
        Returns:
            List of ValidationIssue with severity ERROR.
        \"\"\"
        pass
    
    def _validate_architectural(
        self, 
        content: str, 
        metadata: dict[str, Any]
    ) -> list[ValidationIssue]:
        \"\"\"
        Validate Tier 2: Architectural rules from specific template.
        
        Checks (from metadata.validates.strict):
        - Base class inheritance
        - Required methods with signatures
        - Required imports
        - Protocol compliance
        
        Returns:
            List of ValidationIssue with severity ERROR.
        \"\"\"
        pass
    
    def _validate_guidelines(
        self, 
        content: str, 
        metadata: dict[str, Any]
    ) -> list[ValidationIssue]:
        \"\"\"
        Validate Tier 3: Guidelines from all templates.
        
        Checks (from metadata.validates.guidelines):
        - Naming conventions
        - Field/section ordering
        - Docstring format
        - Content type (for documents)
        
        Returns:
            List of ValidationIssue with severity WARNING.
        \"\"\"
        pass
    
    def _combine_results(
        self, 
        issues: list[ValidationIssue],
        metadata: dict[str, Any]
    ) -> ValidationResult:
        \"\"\"
        Combine validation issues into result with agent hints.
        
        Calculates score:
        - 1.0 if no issues
        - 0.8 if only warnings
        - 0.0 if any errors
        
        Adds agent hints from metadata if present.
        \"\"\"
        pass
\\\

**Implementation Notes:**
- Fail-fast on ERROR: Return immediately after first error found
- Continue through WARNINGs: Collect all warnings before returning
- Agent hints: Include \metadata.agent_hint\ in response for document templates
- Pattern matching: Use regex for Python/Markdown pattern detection

#### 3.2.3 ValidationResult Enhancement

**Purpose:** Extend ValidationResult to include agent hints and guidance.

**Changes to Existing:**
\\\python
# In mcp_server/validation/base.py

@dataclass
class ValidationResult:
    \"\"\"Result of validation operation.\"\"\"
    passed: bool
    score: float
    issues: list[ValidationIssue]
    
    # NEW FIELDS
    agent_hint: str | None = None
    content_guidance: dict[str, Any] | None = None
    
    def to_dict(self) -> dict[str, Any]:
        \"\"\"Convert to dictionary for JSON serialization.\"\"\"
        return {
            \"passed\": self.passed,
            \"score\": self.score,
            \"issues\": [issue.to_dict() for issue in self.issues],
            \"agent_hint\": self.agent_hint,
            \"content_guidance\": self.content_guidance
        }
\\\

### 3.3 Data Model

#### Template Metadata Schema

**Base Template (Format Enforcement):**
\\\yaml
{# TEMPLATE_METADATA
enforcement: STRICT
level: format
version: \"2.0\"

validates:
  strict:
    - rule: import_order
      description: \"Imports ordered: stdlib → third-party → local\"
      pattern: \"^(import |from )(stdlib|typing|dataclasses)\"
      
    - rule: docstring_presence
      description: \"All classes and functions have docstrings\"
      pattern: '\"\"\".*?\"\"\"'
      
    - rule: type_hints
      description: \"All function parameters and returns have type hints\"
      pattern: \"def \\w+\\(.*: .*\\) -> \"
#}
\\\

**Specific Template (Architectural + Guidelines):**
\\\yaml
{# TEMPLATE_METADATA
enforcement: ARCHITECTURAL
level: content
extends: base/base_component.py.jinja2
version: \"2.0\"

validates:
  strict:
    - rule: base_class
      description: \"Must inherit from BaseWorker[InputDTO, OutputDTO]\"
      pattern: \"class \\w+\\(BaseWorker\\[\\w+, \\w+\\]\\)\"
      
    - rule: required_methods
      description: \"Must implement IWorkerLifecycle protocol\"
      methods:
        - name: __init__
          signature: \"def __init__\\(self, build_spec: BuildSpec\\)\"
        - name: initialize
          signature: \"def initialize\\(self, strategy_cache: IStrategyCache\\)\"
        - name: process
          signature: \"async def process\\(self, input_data: \\w+\\) -> \\w+\"
    
    - rule: required_imports
      description: \"Must import IWorkerLifecycle protocol\"
      imports:
        - \"backend.core.interfaces.worker.IWorkerLifecycle\"
        - \"backend.core.interfaces.base_worker.BaseWorker\"
  
  guidelines:
    - rule: naming_convention
      description: \"Worker class name should be descriptive (suffix optional)\"
      severity: WARNING
      
    - rule: docstring_format
      description: \"Docstring should include Responsibilities section\"
      pattern: \"Responsibilities:\"
      severity: WARNING
#}
\\\

**Document Template (Content Guidance):**
\\\yaml
{# TEMPLATE_METADATA
enforcement: GUIDELINE
level: content
extends: base/base_document.md.jinja2
version: \"2.0\"

purpose: |
  Research documents analyze problems and gather information.
  They answer: \"What is the situation?\" and \"What should we do?\"

content_guidance:
  includes:
    - Problem analysis and root cause investigation
    - Findings from code/documentation analysis
    - Recommendations for next steps
  
  excludes:
    - Implementation details (that's planning phase)
    - Code designs or class structures (that's design docs)
    - Test plans (that's planning phase)

agent_hint: |
  Focus on WHY and WHAT, not HOW. You're a detective gathering
  evidence, not an architect designing solutions. Include analysis,
  findings, and recommendations.

validates:
  guidelines:
    - rule: recommended_sections
      sections: [\"Executive Summary\", \"Problem Statement\", \"Findings\", \"Recommendations\"]
      severity: WARNING
      
    - rule: content_type
      description: \"Should contain analysis, not implementation\"
      excludes_patterns: [\"class \\w+:\", \"def \\w+\\(\", \"`python\"]
      severity: WARNING
#}
\\\

### 3.4 Interface Design

#### Integration with SafeEditTool

**Current SafeEditTool Flow:**
\\\python
# mcp_server/tools/safe_edit_tool.py

async def execute(self, arguments: dict[str, Any]) -> ToolResult:
    # 1. Read file
    # 2. Apply edits
    # 3. VALIDATE using TemplateValidator
    # 4. Return result
\\\

**Updated Flow with LayeredTemplateValidator:**
\\\python
async def execute(self, arguments: dict[str, Any]) -> ToolResult:
    # 1. Read file
    # 2. Apply edits
    
    # 3. Determine template type from file path
    template_type = self._infer_template_type(file_path)
    
    # 4. Get validator for template type
    analyzer = TemplateAnalyzer(template_root=Path(\"mcp_server/templates\"))
    validator = LayeredTemplateValidator(template_type, analyzer)
    
    # 5. Validate with three-tier model
    result = await validator.validate(file_path, edited_content)
    
    # 6. Block on ERROR, warn on WARNING
    if not result.passed:
        return ToolResult(
            success=False,
            error=f\"Validation failed: {result.issues[0].message}\"
        )
    
    # 7. Save file if passed
    # 8. Return result with agent hints
    return ToolResult(
        success=True,
        output={
            \"validation\": result.to_dict(),
            \"agent_hint\": result.agent_hint,  # NEW
            \"content_guidance\": result.content_guidance  # NEW
        }
    )
\\\

#### Integration with ValidatorRegistry

**Current Registry:**
\\\python
# mcp_server/tools/validation_tools.py

class ValidatorRegistry:
    _validators: dict[str, BaseValidator] = {
        \"python\": PythonValidator(),
        \"markdown\": MarkdownValidator(),
        # Template validators registered manually
    }
\\\

**Updated Registry (Template-Driven):**
\\\python
class ValidatorRegistry:
    \"\"\"Registry that auto-discovers validators from templates.\"\"\"
    
    def __init__(self, template_root: Path):
        self.template_root = template_root
        self.analyzer = TemplateAnalyzer(template_root)
        self._validators: dict[str, BaseValidator] = {}
        self._load_validators()
    
    def _load_validators(self):
        \"\"\"Load validators dynamically from template directory.\"\"\"
        # Discover all templates
        for template_path in self.template_root.rglob(\"*.jinja2\"):
            # Extract template type from filename
            template_type = template_path.stem.replace(\".py\", \"\").replace(\".md\", \"\")
            
            # Create validator for this template
            validator = LayeredTemplateValidator(template_type, self.analyzer)
            self._validators[template_type] = validator
    
    def get_validator(self, file_type: str) -> BaseValidator | None:
        \"\"\"Get validator for file type (auto-discovered from templates).\"\"\"
        return self._validators.get(file_type)
    
    def list_validators(self) -> list[str]:
        \"\"\"List all available validator types.\"\"\"
        return list(self._validators.keys())
\\\

**Benefits:**
- No manual registration needed
- Adding new template automatically creates validator
- Template changes automatically update validation rules

---

## 4. Implementation Plan

### 4.1 Phases

#### Phase 1: Template Infrastructure (Goals 1-4)

**Goal:** Create base templates and add metadata to core templates.

**Tasks:**
1. Create \ase/base_document.md.jinja2\ with frontmatter enforcement
2. Update \components/worker.py.jinja2\ with IWorkerLifecycle pattern
3. Add metadata to \components/dto.py.jinja2\ and \components/tool.py.jinja2\
4. Create \documents/research.md.jinja2\ with agent guidance
5. Create \documents/planning.md.jinja2\ with agent guidance

**TDD Approach:**
\\\python
# Test 1: Base document template
def test_base_document_template_enforces_frontmatter():
    # Generate doc without frontmatter → should fail
    # Generate doc with frontmatter → should pass

# Test 2: Worker template  
def test_worker_template_generates_two_phase_init():
    # Generate worker → should have __init__(build_spec)
    # Generate worker → should have initialize(strategy_cache)

# Test 3: DTO template metadata
def test_dto_template_has_metadata():
    # Extract metadata → should have strict rules for BaseModel
    # Extract metadata → should have guidelines for field ordering
\\\

**Exit Criteria:**
- All 6 templates exist with metadata
- Generated code matches backend patterns
- Scaffold tool creates valid code from templates

#### Phase 2: Analyzer Infrastructure (Goal 5)

**Goal:** Build TemplateAnalyzer to extract metadata from templates.

**Tasks:**
1. Implement \extract_metadata()\ with regex YAML parsing
2. Implement \get_base_template()\ with extends detection
3. Implement \get_inheritance_chain()\ with recursive traversal
4. Implement \merge_metadata()\ with rule concatenation
5. Add caching for performance (metadata and inheritance chains)

**TDD Approach:**
\\\python
# Test 1: Extract metadata
def test_extract_metadata_from_jinja2_comment():
    template = Path(\"worker.py.jinja2\")
    metadata = analyzer.extract_metadata(template)
    assert metadata[\"enforcement\"] == \"ARCHITECTURAL\"
    assert \"strict\" in metadata[\"validates\"]

# Test 2: Get base template
def test_get_base_template_returns_parent():
    template = Path(\"worker.py.jinja2\")
    base = analyzer.get_base_template(template)
    assert base.name == \"base_component.py.jinja2\"

# Test 3: Inheritance chain
def test_get_inheritance_chain_returns_ordered_list():
    template = Path(\"worker.py.jinja2\")
    chain = analyzer.get_inheritance_chain(template)
    assert chain == [
        Path(\"worker.py.jinja2\"),
        Path(\"base_component.py.jinja2\")
    ]

# Test 4: Merge metadata
def test_merge_metadata_concatenates_rules():
    child = {\"validates\": {\"strict\": [\"rule1\"]}}
    parent = {\"validates\": {\"strict\": [\"rule2\"]}}
    merged = analyzer.merge_metadata(child, parent)
    assert merged[\"validates\"][\"strict\"] == [\"rule1\", \"rule2\"]
\\\

**Exit Criteria:**
- TemplateAnalyzer extracts metadata correctly
- Inheritance chains resolve properly
- Metadata merging works (no duplicates)
- Performance < 100ms per template
- 100% test coverage

#### Phase 3: Validator Infrastructure (Goal 6)

**Goal:** Build LayeredTemplateValidator with three-tier enforcement.

**Tasks:**
1. Implement \_validate_format()\ for base template rules
2. Implement \_validate_architectural()\ for strict rules
3. Implement \_validate_guidelines()\ for warnings
4. Implement fail-fast logic (stop on ERROR)
5. Implement \_combine_results()\ with agent hints

**TDD Approach:**
\\\python
# Test 1: Format validation (Tier 1)
def test_format_validation_checks_import_order():
    content = \"from local import X\\nimport stdlib\"  # Wrong order
    result = await validator.validate(\"test.py\", content)
    assert not result.passed
    assert \"import order\" in result.issues[0].message

# Test 2: Architectural validation (Tier 2)
def test_architectural_validation_checks_base_class():
    content = \"class MyWorker:\"  # Missing BaseWorker
    result = await validator.validate(\"test.py\", content)
    assert not result.passed
    assert \"BaseWorker\" in result.issues[0].message

# Test 3: Guidelines validation (Tier 3)
def test_guidelines_validation_warns_on_naming():
    content = \"class MyComponent(BaseWorker):\"  # No Worker suffix
    result = await validator.validate(\"test.py\", content)
    assert result.passed  # WARNING doesn't block
    assert len(result.issues) > 0
    assert result.issues[0].severity == \"WARNING\"

# Test 4: Fail-fast on error
def test_validation_stops_on_first_error():
    content = \"invalid python code\"
    result = await validator.validate(\"test.py\", content)
    assert not result.passed
    assert len(result.issues) == 1  # Only first error

# Test 5: Agent hints included
def test_validation_includes_agent_hints_for_documents():
    content = \"# Research\\n\\nclass MyClass: pass\"  # Code in research
    result = await validator.validate(\"research.md\", content)
    assert result.agent_hint is not None
    assert \"detective\" in result.agent_hint.lower()
\\\

**Exit Criteria:**
- Three-tier validation enforces correctly
- Fail-fast stops on first ERROR
- Agent hints included for documents
- 100% test coverage

#### Phase 4: Integration and Cleanup (Goals 7-8)

**Goal:** Integrate with SafeEditTool and remove RULES dict.

**Tasks:**
1. Update SafeEditTool to use LayeredTemplateValidator
2. Update ValidatorRegistry to auto-discover from templates
3. Remove RULES dict from template_validator.py
4. Update all tests to use template metadata
5. Create template metadata documentation
6. Create template governance documentation

**TDD Approach:**
\\\python
# Test 1: SafeEditTool integration
async def test_safe_edit_tool_uses_template_validator():
    tool = SafeEditTool()
    result = await tool.execute({
        \"file_path\": \"test_worker.py\",
        \"content\": \"invalid worker\"
    })
    assert not result.success
    assert \"validation\" in result.output

# Test 2: ValidatorRegistry auto-discovery
def test_validator_registry_discovers_templates():
    registry = ValidatorRegistry(template_root)
    validators = registry.list_validators()
    assert \"worker\" in validators
    assert \"dto\" in validators
    assert \"research\" in validators

# Test 3: No hardcoded rules
def test_no_rules_dict_in_codebase():
    validator_file = Path(\"template_validator.py\")
    content = validator_file.read_text()
    assert \"RULES = {\" not in content
\\\

**Exit Criteria:**
- SafeEditTool uses LayeredTemplateValidator
- ValidatorRegistry auto-discovers validators
- RULES dict removed from codebase
- All tests passing (30+ tests)
- Documentation complete
- Pylint 10/10

### 4.2 Testing Strategy

| Test Category | Component | Test Count | Focus |
|---------------|-----------|-----------|-------|
| Unit | TemplateAnalyzer | 10 | Metadata extraction, inheritance |
| Unit | LayeredTemplateValidator | 15 | Three-tier enforcement, fail-fast |
| Integration | SafeEditTool | 5 | End-to-end validation workflow |
| Integration | ValidatorRegistry | 3 | Auto-discovery, registration |
| Acceptance | Generated Code | 6 | Templates produce valid code |

**Total Test Count:** 39 tests (exceeds 28 minimum from planning)

### 4.3 Rollout Sequence

**Step 1:** Create templates with metadata (non-breaking)
**Step 2:** Build analyzer and validator (new code, no impact)
**Step 3:** Update SafeEditTool (uses new validator, old still works)
**Step 4:** Remove RULES dict (breaking, do last)
**Step 5:** Documentation and training

---

## 5. Alternatives Considered

### Alternative A: Separate validation.yaml File

**Description:** Store validation rules in \config/validation.yaml\ separate from templates.

**Pros:**
- Centralized configuration
- Easy to edit without touching templates
- YAML is more familiar than Jinja2 comments

**Cons:**
- Creates duplicate SSOT (templates + validation.yaml)
- Requires synchronization between template structure and rules
- Changes require updating both files
- No inheritance relationship (can't leverage template extends)

**Decision:** Rejected. Violates SSOT principle. Templates are already defining structure, adding metadata is natural extension.

### Alternative B: AST-Based Validation Only

**Description:** Use Python AST parsing for validation instead of regex patterns.

**Pros:**
- More robust (parses actual Python structure)
- Better error messages with line numbers
- Can detect complex patterns

**Cons:**
- Only works for Python (not Markdown documents)
- Slower performance (full parse on every validation)
- More complex implementation
- Overkill for simple pattern matching

**Decision:** Deferred. Start with regex patterns (fast, simple), upgrade to AST in future if needed.

### Alternative C: Single Enforcement Level

**Description:** All rules are strict (no guidelines, no warnings).

**Pros:**
- Simpler implementation (one validation path)
- Consistent enforcement
- Clear pass/fail

**Cons:**
- Too rigid for guidelines (blocks innovation)
- No way to suggest improvements without blocking
- Document content guidance can't warn about wrong phase

**Decision:** Rejected. Three-tier model provides necessary flexibility while maintaining strictness where needed.

---

## 6. Open Questions

- [x] **Q1:** Should metadata be in YAML or JSON format?
  - **Decision:** YAML (more human-readable, supports multi-line strings for agent hints)

- [x] **Q2:** How to handle templates without metadata?
  - **Decision:** Return empty dict, validator falls back to basic Python/Markdown validation

- [x] **Q3:** Should validation cache metadata between calls?
  - **Decision:** Yes, cache metadata and inheritance chains for performance

- [ ] **Q4:** How to handle template versioning (v1.0 vs v2.0)?
  - **Deferred:** Implement when first breaking change needed (worker template update is v2.0)

- [ ] **Q5:** Should SafeEditTool always validate or make it optional?
  - **Deferred:** Always validate for now, add skip flag if users request it

---

## 7. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-01 | Use template metadata as SSOT | Templates already define structure, metadata natural extension |
| 2026-01-01 | Three-tier enforcement model | Balances strictness (format/architectural) with flexibility (guidelines) |
| 2026-01-01 | YAML format for metadata | More readable, supports multi-line agent hints |
| 2026-01-01 | Fail-fast on ERROR | Saves time, prevents cascading failures |
| 2026-01-01 | Continue through WARNINGs | Collect all guidance before returning |
| 2026-01-01 | Regex patterns for validation | Fast, simple, sufficient for current needs (upgrade to AST if needed) |
| 2026-01-01 | Auto-discovery in ValidatorRegistry | No manual registration, templates self-register |
| 2026-01-01 | No backward compatibility for worker template | Clean break to IWorkerLifecycle v2.0 |

---

## 8. Appendices

### Appendix A: Metadata Schema Reference

**Complete Schema:**
\\\yaml
{# TEMPLATE_METADATA
# Required fields
enforcement: STRICT | ARCHITECTURAL | GUIDELINE
level: format | content
version: \"2.0\"

# Optional inheritance
extends: path/to/base.jinja2

# Validation rules
validates:
  strict:
    - rule: rule_name
      description: Human-readable description
      pattern: regex_pattern | null
      methods: [...] | null
      imports: [...] | null
      
  guidelines:
    - rule: rule_name
      description: Human-readable description
      severity: WARNING
      pattern: regex_pattern | null

# Document-specific fields
purpose: |
  Multi-line description of document purpose
  
content_guidance:
  includes:
    - Thing that should be in this document
  excludes:
    - Thing that should NOT be in this document
    
agent_hint: |
  Multi-line guidance for AI agents
#}
\\\

### Appendix B: Example Templates

**Base Component Template:**
\\\jinja
{# TEMPLATE_METADATA
enforcement: STRICT
level: format
version: \"2.0\"

validates:
  strict:
    - rule: import_order
      description: \"Imports ordered: stdlib → third-party → local\"
    - rule: docstring_presence
      description: \"All classes and functions have docstrings\"
    - rule: type_hints
      description: \"All function parameters have type hints\"
#}

\"\"\"{{description}}\"\"\"
from typing import Any
from dataclasses import dataclass

# Third-party imports
from pydantic import BaseModel

# Local imports
from backend.core.interfaces import {{base_class}}


class {{name}}({{base_class}}):
    \"\"\"{{description}}.
    
    Responsibilities:
    - {{responsibility}}
    \"\"\"
    
    def __init__(self, build_spec: BuildSpec) -> None:
        \"\"\"Initialize {{name}}.\"\"\"
        pass
\\\

**Worker Template:**
\\\jinja
{# TEMPLATE_METADATA
enforcement: ARCHITECTURAL
level: content
extends: base/base_component.py.jinja2
version: \"2.0\"

validates:
  strict:
    - rule: base_class
      description: \"Must inherit BaseWorker[InputDTO, OutputDTO]\"
      pattern: \"class \\w+\\(BaseWorker\\[\\w+, \\w+\\]\\)\"
      
    - rule: required_methods
      methods:
        - name: __init__
          signature: \"def __init__\\(self, build_spec: BuildSpec\\)\"
        - name: initialize
          signature: \"def initialize\\(self, strategy_cache: IStrategyCache\\)\"
        - name: process
          signature: \"async def process\\(self, input_data: \\w+\\) -> \\w+\"
    
    - rule: required_imports
      imports:
        - \"backend.core.interfaces.worker.IWorkerLifecycle\"
        - \"backend.core.interfaces.base_worker.BaseWorker\"
  
  guidelines:
    - rule: naming_convention
      description: \"Worker class name should be descriptive\"
      severity: WARNING
      
    - rule: docstring_format
      description: \"Docstring should include Responsibilities section\"
      severity: WARNING
#}

{% extends \"base/base_component.py.jinja2\" %}

{% block imports %}
from backend.core.interfaces.worker import IWorkerLifecycle
from backend.core.interfaces.base_worker import BaseWorker
from backend.core.interfaces.strategy_cache import IStrategyCache
from backend.dtos.build_spec import BuildSpec
{% endblock %}

{% block class_definition %}
class {{name}}(BaseWorker[{{input_dto}}, {{output_dto}}], IWorkerLifecycle):
    \"\"\"{{description}}.
    
    Responsibilities:
    - {{responsibility}}
    \"\"\"
    
    def __init__(self, build_spec: BuildSpec) -> None:
        \"\"\"Initialize {{name}} with build specification.\"\"\"
        self._manifest = build_spec.manifest
        self._strategy_cache: IStrategyCache | None = None
    
    def initialize(self, strategy_cache: IStrategyCache) -> None:
        \"\"\"Initialize runtime dependencies.\"\"\"
        self._strategy_cache = strategy_cache
    
    async def process(self, input_data: {{input_dto}}) -> {{output_dto}}:
        \"\"\"Process input and return result.\"\"\"
        # TODO: Implement processing logic
        pass
{% endblock %}
\\\

---

**Design Complete.** Ready for TDD phase transition.

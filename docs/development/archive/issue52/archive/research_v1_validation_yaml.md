# Issue #52 Research: Validation Rules Configuration (validation.yaml)

**Status:** COMPLETE
**Author:** AI Agent
**Created:** 2025-12-30
**Parent:** Epic #49 - MCP Platform Configurability

---

## 1. Executive Summary

**Objective:** Migrate template validation rules from hardcoded `RULES` dict to `config/validation.yaml`.

**Current State:**
- 30 lines of hardcoded validation rules in `template_validator.py`
- 5 template types: worker, tool, dto, adapter, base
- Used by SafeEditTool validator registry and TemplateValidator
- Tests in 3 files rely on hardcoded RULES

**Target State:**
- All rules in `.st3/validation.yaml`
- Pydantic `ValidationConfig` model with singleton pattern
- Zero hardcoded rules in Python code
- Tests use config instead of RULES dict

**Complexity:** MEDIUM
- Simple data migration (dict → YAML)
- Established pattern from #50, #51
- More complex validation logic than workflows/labels

**Estimated Effort:** 1-2 days (following #50 and #51 pattern)

---

## 2. Current Implementation Analysis

### 2.1 Hardcoded RULES Dictionary

**Location:** `mcp_server/validators/template_validator.py:12-41`

```python
RULES: dict[str, dict[str, Any]] = {
    "worker": {
        "required_class_suffix": "Worker",
        "required_methods": ["execute"],
        "required_imports": ["BaseWorker", "TaskResult"],
        "description": "Worker components"
    },
    "tool": {
        "required_class_suffix": "Tool",
        "required_methods": ["execute"],
        "required_attrs": ["name", "description", "input_schema"],
        "description": "MCP Tools"
    },
    "dto": {
        "required_class_suffix": "DTO",
        "required_decorators": ["@dataclass"],
        "description": "Data Transfer Objects"
    },
    "adapter": {
        "required_class_suffix": "Adapter",
        "description": "External System Adapters"
    },
    "base": {
        "description": "Base Python Component",
        "required_imports": ["typing"]
    }
}
```

**Fields Per Rule:**
- `description` (str) - Human-readable purpose
- `required_class_suffix` (str) - Class name must end with this (e.g., "Worker")
- `required_methods` (list[str]) - Methods that must exist (e.g., ["execute"])
- `required_attrs` (list[str]) - Attributes that must exist (e.g., ["name", "description"])
- `required_imports` (list[str]) - Import statements that must exist
- `required_decorators` (list[str]) - Decorators that must be present (e.g., ["@dataclass"])

### 2.2 Usage Locations

**Primary Consumer:**
1. **TemplateValidator class** (`template_validator.py`)
   - `__init__()` - Loads rules for template type
   - `validate()` - Applies rules to file content
   - 5 validation methods (one per field type)

**Secondary Consumers:**
2. **SafeEditTool** (`mcp_server/tools/safe_edit_tool.py`)
   - Registers validators via `ValidatorRegistry`
   - Pattern matching: `.*_workers?\.py$` → worker validator
   - Fallback: Python files without pattern → base validator

3. **Scaffold Tools** (referenced but not direct usage)
   - Component type validation
   - Referenced in scaffolding component types

**Test Files:**
4. `tests/unit/mcp_server/validators/test_template_validator.py`
5. `tests/unit/mcp_server/validators/test_validator_registry_default.py`
6. `tests/unit/mcp_server/tools/test_safe_edit_tool_validation.py`

### 2.3 Validation Logic Details

**How Rules Are Applied:**

1. **Initialization:**
   ```python
   self.rules = self.RULES[template_type]
   ```

2. **Validation Flow** (TemplateValidator.validate()):
   ```python
   issues = []
   issues.extend(self._check_class_suffix(content))
   issues.extend(self._check_required_methods(content))
   issues.extend(self._check_required_attrs(content))
   issues.extend(self._check_required_imports(content))
   issues.extend(self._check_required_decorators(content))
   
   return ValidationResult(
       passed=not [i for i in issues if i.severity == "error"],
       score=10.0 if not issues else 5.0,
       issues=issues
   )
   ```

3. **Severity Levels:**
   - **ERROR** (blocks): Missing required methods, missing required attributes
   - **WARNING** (allows): Missing imports, missing decorators, missing class suffix

4. **Pattern Matching:**
   - Class suffix: `rf"class \w+{suffix}\b"` - Matches class names
   - Methods: `rf"(?:async\s+)?def {method}\("` - Supports sync/async
   - Attributes: `rf"(?:self\.)?{attr}\s*(?:=|:)"` - Assignment or property
   - Imports: Substring search `import_name in content`
   - Decorators: Substring search `decorator in content`

### 2.4 File Pattern Mapping

**Current Pattern Registration** (`safe_edit_tool.py`):
```python
ValidatorRegistry.register_pattern(r".*_workers?\.py$", TemplateValidator("worker"))
ValidatorRegistry.register_pattern(r".*_tools?\.py$", TemplateValidator("tool"))
ValidatorRegistry.register_pattern(r".*_dtos?\.py$", TemplateValidator("dto"))
ValidatorRegistry.register_pattern(r".*_adapters?\.py$", TemplateValidator("adapter"))
```

**Fallback Logic:**
- Python files without specific pattern → "base" validator
- Ensures minimum typing standards for all Python files

### 2.5 Special Cases

**Test File Exemption:**
```python
is_test = "tests/" in path.replace("\\", "/") or Path(path).name.startswith("test_")
if is_test:
    validators = [
        v for v in validators
        if not isinstance(v, TemplateValidator) or v.template_type == "base"
    ]
```
- Test files exempt from template validation
- Only "base" validator applies (ensures typing imports)

**Async Method Support:**
- Pattern `(?:async\s+)?def` matches both `def` and `async def`
- Critical for modern async Python code

**Property vs Assignment:**
- Pattern `(?:self\.)?{attr}\s*(?:=|:)` matches:
  - `self.name = "value"` (assignment)
  - `name: str` (type annotation)
  - `@property\n  def name()` (property method)

### 2.6 Known Limitations

**Substring Matching Naivety:**
1. **Imports** - `"BaseWorker" in content`
   - Could match in comments: `# Don't use BaseWorker`
   - Could match in strings: `"BaseWorker is deprecated"`
   
2. **Decorators** - `"@dataclass" in content`
   - Same false positive risk
   - No actual AST parsing

**Recommendation:** Document as known limitation, consider AST parsing in future enhancement.

---

## 3. Lessons Learned from Issues #50 and #51

### 3.1 Architecture Pattern (Applied Successfully)

**Three-Tier Structure:**
1. **Dataclass** (frozen=True) - Individual items
2. **Pydantic BaseModel** - Collection + validation
3. **Module-level singleton** - Load at import time

**Why This Works:**
- ✅ Fail-fast - Invalid config crashes at startup
- ✅ Type safety - Pydantic validates structure
- ✅ Immutability - Frozen dataclasses prevent modification
- ✅ Zero runtime overhead - Loaded once

**Example from workflows.yaml:**
```python
@dataclass(frozen=True)
class WorkflowTemplate:
    name: str
    phases: list[str]

class WorkflowConfig(BaseModel):
    version: str
    workflows: dict[str, WorkflowTemplate]
    
    @classmethod
    def load(cls, path: Path | None = None) -> "WorkflowConfig":
        # Standard loading logic

workflow_config = WorkflowConfig.load()  # Singleton
```

### 3.2 Testing Pattern

**Critical Insight:** Singleton tests need reset!

**From Issue #51 Bug (#67):**
```python
@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before EACH test."""
    ValidationConfig.reset()  # Without this: test pollution!
    yield
```

**Test Categories:**
1. Config loading (valid, invalid, missing file)
2. Schema validation (field types, required fields)
3. Business logic (duplicate detection, custom validators)
4. Integration (usage in actual code)

### 3.3 Common Pitfalls Avoided

**From Issues #50 and #51:**
1. ❌ Don't use Enums for config-driven values (violates Config Over Code)
2. ❌ Don't provide fallback defaults (fail-fast, not fail-slow)
3. ❌ Don't use `yaml.load()` - always `yaml.safe_load()` (security)
4. ❌ Don't skip singleton reset in tests (test pollution)
5. ❌ Don't forget `arbitrary_types_allowed` for dataclasses in Pydantic
6. ❌ Don't skip helpful error messages (always include hints)

### 3.4 Quality Standards

**From Epic #49:**
- ✅ Pylint 10/10 (no exceptions, even in test files)
- ✅ 100% coverage for config layer
- ✅ All validators have success AND failure tests
- ✅ Documentation complete (docstrings + inline comments)
- ✅ TDD discipline: RED → GREEN → REFACTOR → QA

---

## 4. Proposed YAML Schema

### 4.1 Structure Design

**File:** `.st3/validation.yaml`

```yaml
version: "1.0"

# Template validation rules for code generation and validation
templates:
  worker:
    description: "Worker components"
    validation:
      required_class_suffix: "Worker"
      required_methods:
        - name: "execute"
          severity: "error"
      required_imports:
        - name: "BaseWorker"
          severity: "warning"
        - name: "TaskResult"
          severity: "warning"
  
  tool:
    description: "MCP Tools"
    validation:
      required_class_suffix: "Tool"
      required_methods:
        - name: "execute"
          severity: "error"
      required_attrs:
        - name: "name"
          severity: "error"
        - name: "description"
          severity: "error"
        - name: "input_schema"
          severity: "error"
  
  dto:
    description: "Data Transfer Objects"
    validation:
      required_class_suffix: "DTO"
      required_decorators:
        - name: "@dataclass"
          severity: "warning"
  
  adapter:
    description: "External System Adapters"
    validation:
      required_class_suffix: "Adapter"
  
  base:
    description: "Base Python Component"
    validation:
      required_imports:
        - name: "typing"
          severity: "warning"

# File pattern mappings (used by ValidatorRegistry)
file_patterns:
  - pattern: ".*_workers?\\.py$"
    template: "worker"
  
  - pattern: ".*_tools?\\.py$"
    template: "tool"
  
  - pattern: ".*_dtos?\\.py$"
    template: "dto"
  
  - pattern: ".*_adapters?\\.py$"
    template: "adapter"

# Special validation rules
special_rules:
  test_files:
    exempt_templates: true
    detection_patterns:
      - "tests/"
      - "test_*.py"
  
  fallback:
    python_files_without_template: "base"
```

### 4.2 Design Rationale

**Why This Structure:**

1. **Explicit Severity**: Makes severity configurable (currently hardcoded)
2. **Nested Validation**: Separates rule metadata from validation criteria
3. **File Patterns**: Decouples pattern→template mapping from rules
4. **Special Rules**: Documents test exemptions and fallback behavior
5. **Extensibility**: Easy to add new template types or criteria

**Backwards Compatibility:**
- All current validation rules preserved
- Severity levels match current implementation:
  - methods/attrs → error
  - imports/decorators/suffix → warning

**Future Enhancements** (out of scope for #52):
- Method signatures validation
- Import statement parsing (AST-based)
- Decorator parsing (AST-based)
- Custom regex patterns per rule

---

## 5. Migration Strategy

### 5.1 Implementation Phases

**Phase 1: Config Infrastructure** (TDD Phase - RED)
1. Create `.st3/validation.yaml` with complete schema
2. Create dataclasses for rule components
3. Create `ValidationConfig` Pydantic model
4. Implement `load()` method with singleton pattern
5. Add `reset()` method for testing
6. Write failing tests for config loading

**Phase 2: Rule Access Methods** (TDD Phase - GREEN)
1. Implement `get_template_rule(template_type)`
2. Implement `get_file_patterns()`
3. Implement `get_special_rules()`
4. Make tests pass
5. Add integration tests

**Phase 3: Code Migration** (TDD Phase - REFACTOR)
1. Update `TemplateValidator` to use `validation_config`
2. Remove `RULES` dict
3. Update `SafeEditTool` pattern registration
4. Update all test files
5. Run quality gates (Pylint 10/10)

**Phase 4: Documentation** (Documentation Phase)
1. Add docstrings to all new code
2. Create reference documentation
3. Document validation rules
4. Update architecture docs

### 5.2 Affected Files

**New Files:**
- `.st3/validation.yaml` - Config file
- `mcp_server/config/validation.py` - Config model

**Modified Files:**
- `mcp_server/validators/template_validator.py` - Use config instead of RULES
- `mcp_server/tools/safe_edit_tool.py` - Use config for pattern registration
- `tests/unit/mcp_server/validators/test_template_validator.py` - Update tests
- `tests/unit/mcp_server/validators/test_validator_registry_default.py` - Update tests
- `tests/unit/mcp_server/tools/test_safe_edit_tool_validation.py` - Update tests

**Deleted Code:**
- `RULES` dict (30 lines) - Replaced by YAML

### 5.3 Testing Strategy

**Config Loading Tests** (10 tests):
```python
test_load_valid_yaml()
test_load_missing_file()
test_load_invalid_yaml()
test_load_invalid_schema()
test_get_template_rule_exists()
test_get_template_rule_unknown()
test_duplicate_template_names()
test_invalid_severity_value()
test_invalid_pattern_regex()
test_load_default_path()
```

**Rule Validation Tests** (15 tests):
```python
test_worker_rule_has_execute_method()
test_tool_rule_has_required_attrs()
test_dto_rule_has_dataclass_decorator()
test_base_rule_has_typing_import()
test_severity_levels_preserved()
test_file_pattern_matching_worker()
test_file_pattern_matching_tool()
test_special_rules_test_exemption()
test_special_rules_fallback()
# ... etc
```

**Integration Tests** (5 tests):
```python
test_template_validator_uses_config()
test_safe_edit_pattern_registration_from_config()
test_validation_on_real_worker_file()
test_validation_on_real_tool_file()
test_validation_on_real_dto_file()
```

**Singleton Reset Test:**
```python
@pytest.fixture(autouse=True)
def reset_singleton():
    """Critical: Reset before EACH test."""
    ValidationConfig.reset()
    yield
```

### 5.4 Risk Assessment

**Low Risks:**
- ✅ Established pattern (2 successful implementations)
- ✅ Simple data structure (dict → YAML)
- ✅ No external dependencies

**Medium Risks:**
- ⚠️ Validation logic more complex than workflows/labels
- ⚠️ Multiple consumers (TemplateValidator, SafeEditTool, tests)
- ⚠️ Regex patterns need escaping in YAML

**Mitigation:**
- Follow established pattern exactly
- Thorough testing (30+ tests)
- Quality gates enforced (Pylint 10/10)

---

## 6. Success Criteria

**Must Have:**
- [ ] `.st3/validation.yaml` exists with all 5 template rules
- [ ] `ValidationConfig` Pydantic model complete
- [ ] Singleton pattern with `reset()` method
- [ ] `RULES` dict removed from code
- [ ] All tests passing (30+ tests)
- [ ] Pylint 10/10 (no exceptions)
- [ ] 100% coverage for `validation.py`

**Quality Gates:**
- [ ] No hardcoded validation rules in Python
- [ ] Error messages include helpful hints
- [ ] Documentation complete (docstrings)
- [ ] Integration tests verify end-to-end usage

**Out of Scope:**
- AST-based import/decorator parsing (future enhancement)
- Method signature validation (future enhancement)
- Custom regex patterns per rule (future enhancement)

---

## 7. Recommendations

### 7.1 Follow Established Pattern

**From Issues #50 and #51:**
1. Use three-tier structure (dataclass → Pydantic → singleton)
2. Load at module import time (fail-fast)
3. Include `reset()` method for testing
4. Use `yaml.safe_load()` always
5. Provide helpful error messages

### 7.2 Watch Out For

**Specific to Validation Rules:**
1. ⚠️ Regex escaping in YAML (`.` becomes `\\.`)
2. ⚠️ Severity levels must match current behavior
3. ⚠️ File patterns support singular/plural (`workers?`)
4. ⚠️ Test exemption logic must be preserved
5. ⚠️ Substring matching limitations documented

### 7.3 Quality Checklist

Before committing:
- [ ] Pylint 10/10 (`mcp_server/config/validation.py`)
- [ ] Pylint 10/10 (all test files)
- [ ] Mypy strict mode passing
- [ ] 100% coverage for validation.py
- [ ] All tests pass
- [ ] Singleton reset implemented
- [ ] Error messages have hints
- [ ] Documentation complete

---

## 8. Appendix: Code References

### 8.1 Current RULES Location
`mcp_server/validators/template_validator.py:12-41`

### 8.2 Validation Methods
- `_check_class_suffix()` - Line 89
- `_check_required_methods()` - Line 102
- `_check_required_attrs()` - Line 115
- `_check_required_imports()` - Line 128
- `_check_required_decorators()` - Line 139

### 8.3 Pattern Registration
`mcp_server/tools/safe_edit_tool.py` - Validator registry setup

### 8.4 Test Files
- `tests/unit/mcp_server/validators/test_template_validator.py`
- `tests/unit/mcp_server/validators/test_validator_registry_default.py`
- `tests/unit/mcp_server/tools/test_safe_edit_tool_validation.py`

---

**Research Complete:** Ready for planning phase.

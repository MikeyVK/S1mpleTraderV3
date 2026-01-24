# Failing Tests Analysis - Template Scaffolder Refactoring

**Date:** 2026-01-24  
**Issue:** 13 failing tests na verwijdering hardcoded service fallback  
**Goal:** Uniforme fix strategie voor alle failing tests

---

## 📊 Failure Categorieën

### Categorie 1: Oude Template Paths (components/ → concrete/)
**Affected Tests:** 2  
**Files:** `test_template_registry.py`

**Root Cause:**
- Tests gebruiken `template_path = 'components/dto.py.jinja2'`
- Task 1.6 verplaatste templates naar `concrete/` directory
- Tests moeten geupdate worden naar nieuwe paths

**Failing Tests:**
1. `test_loads_artifact_from_registry` - Line 21: `components/dto.py.jinja2`
2. `test_uses_template_path_from_artifact` - Line 41: `components/worker.py.jinja2`

**Fix Strategie:**
```python
# OLD
artifact.template_path = 'components/dto.py.jinja2'

# NEW
artifact.template_path = 'concrete/dto.py.jinja2'
```

---

### Categorie 2: Verkeerde Template Root Directory
**Affected Tests:** 7  
**Files:** `test_template_scaffolder.py`

**Root Cause:**
- Fixture `real_jinja_renderer()` (line 40) gebruikt:
  ```python
  template_dir = Path(...) / "mcp_server" / "templates"
  ```
- Correct pad is: `mcp_server/scaffolding/templates`
- Renderer zoekt in verkeerde directory

**Failing Tests:**
1. `test_accepts_custom_renderer` - Line 104
2. `test_scaffold_dto_renders_template` - Line 187
3. `test_scaffold_worker_includes_name_suffix` - Line 204
4. `test_scaffold_design_doc_uses_markdown_extension` - Line 223
5. `test_scaffold_generic_without_template_name_fails` - Line 309
6. `test_scaffold_passes_all_context_to_renderer` - Line 323
7. Plus service tests (zie Categorie 3)

**Fix Strategie:**
```python
# OLD (line 40)
template_dir = Path(__file__).parent.parent.parent.parent / "mcp_server" / "templates"

# NEW
from mcp_server.config.template_config import get_template_root
template_dir = get_template_root()

# OF alternatief
template_dir = Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates"
```

---

### Categorie 3: Service Template Selection Logic Changed
**Affected Tests:** 3  
**Files:** `test_template_scaffolder.py`

**Root Cause:**
- Tests verwachten dynamische service template selection:
  - `service_type="orchestrator"` → `components/service_orchestrator.py.jinja2`
  - `service_type="command"` → `components/service_command.py.jinja2`
- Hardcoded fallback verwijderd in commit 7362e16
- Nieuwe architectuur: service gebruikt ALTIJD `template_path` uit artifacts.yaml
  - Default: `concrete/service_command.py.jinja2`
  - GEEN dynamische template selectie meer

**Failing Tests:**
1. `test_scaffold_service_orchestrator_selects_correct_template` - Line 235
2. `test_scaffold_service_command_selects_correct_template` - Line 250
3. `test_scaffold_service_defaults_to_orchestrator` - Line 265

**Fix Strategie - OPTIE A (Delete Tests):**
Deze tests testen functionaliteit die **niet meer bestaat**. Service artifacts krijgen geen dynamische template selectie meer.

**Fix Strategie - OPTIE B (Rewrite Tests):**
Verander tests om nieuwe behavior te testen:
```python
def test_service_uses_default_template_from_artifacts_yaml(self):
    """Service gebruikt template_path uit artifacts.yaml (geen dynamische selectie)."""
    result = scaffolder.scaffold(
        artifact_type="service",
        name="OrderService"
        # service_type wordt genegeerd - niet meer relevant
    )
    # Verwacht: gebruikt concrete/service_command.py.jinja2 (default uit artifacts.yaml)
    assert "OrderService" in result.content
```

**Recommendation:** OPTIE A (Delete) - tests testen legacy behavior

---

### Categorie 4: Validation Behavior Changed
**Affected Tests:** 2  
**Files:** `test_template_scaffolder.py`, `test_template_scaffolder_introspection.py`

**Root Cause:**
- Tests verwachten `ValidationError` bij missing required fields
- Mogelijk dat template introspection nu andere required fields detecteert
- Of validation logic is veranderd

**Failing Tests:**
1. `test_validate_fails_when_required_field_missing` - Line 151
2. `test_validate_error_includes_template_schema` - Line 68

**Investigation Needed:**
Lees concrete template om te zien welke required fields het heeft:
```bash
cat mcp_server/scaffolding/templates/concrete/dto.py.jinja2
```

Check of `description` nog steeds required is in nieuwe templates.

**Fix Strategie:**
Afhankelijk van investigation:
- Als template changed → Update test expectations
- Als validation bug → Fix validation logic
- Als test assumptions wrong → Rewrite test

---

## 🎯 Uniforme Fix Strategie

### Phase 1: Quick Wins (Categorie 1 & 2)
1. Fix template paths: `components/` → `concrete/`
2. Fix template root: gebruik `get_template_root()` in fixture
3. Estimated: 5 minuten

### Phase 2: Architectural Decision (Categorie 3)
1. **DECISION:** Delete service template selection tests (legacy behavior)
2. **RATIONALE:** Tests testen functionaliteit die bewust verwijderd is
3. **ALTERNATIVE:** Rewrite om nieuwe behavior te documenteren
4. Estimated: 10 minuten

### Phase 3: Investigation (Categorie 4)
1. Lees concrete/dto.py.jinja2 template
2. Check required fields via introspection
3. Update test expectations of fix validation
4. Estimated: 15 minuten

---

## 📝 Implementation Order

1. **Batch 1:** Fix template_registry.py (2 tests)
   - Simple path update: `components/` → `concrete/`

2. **Batch 2:** Fix test_template_scaffolder.py fixture (affects 7+ tests)
   - Update `real_jinja_renderer()` fixture template_dir
   - Run tests to see which pass automatically

3. **Batch 3:** Handle service tests (3 tests)
   - Decision: Delete or rewrite
   - Commit with clear rationale

4. **Batch 4:** Fix validation tests (2 tests)
   - Investigation first
   - Fix based on findings

---

## ✅ Success Criteria

- All 34 unit tests in tests/unit/scaffolders/ passing
- No new tests added (unless rewriting service tests)
- Clear commit messages explaining architectural decisions
- Updated test documentation if behavior changed

# Refactoring Checklist - Signal/Risk Terminology

**Branch:** `refactor/quant-terminology`  
**Started:** 2025-11-02  
**Status:** 🟢 IN PROGRESS

---

## Phase 1: Preparation ✅

- [x] Create feature branch
- [x] Create documentation files
- [x] Finalize terminology decisions

---

## Phase 2: Backend Code Refactoring

### 2.1 File Renames (git mv)
- [ ] `backend/dtos/strategy/opportunity_signal.py` → `signal.py`
- [ ] `backend/dtos/strategy/threat_signal.py` → `risk.py`

### 2.2 Class & Content Updates

#### signal.py (was opportunity_signal.py)
- [ ] Class: `OpportunitySignal` → `Signal`
- [ ] Field: `opportunity_id` → `signal_id`
- [ ] Docstrings: Remove SWOT references
- [ ] Field descriptions: Update terminology
- [ ] Examples: Update with SIG_ prefix

#### risk.py (was threat_signal.py)
- [ ] Class: `ThreatSignal` → `Risk`
- [ ] Field: `threat_id` → `risk_id`
- [ ] Docstrings: Remove SWOT references
- [ ] Field descriptions: Update terminology
- [ ] Examples: Update with RSK_ prefix

#### __init__.py
- [ ] Import: `from .signal import Signal`
- [ ] Import: `from .risk import Risk`
- [ ] Remove: Old imports
- [ ] Export: Update `__all__`

#### causality.py
- [ ] Field: `opportunity_signal_ids` → `signal_ids`
- [ ] Field: `threat_ids` → `risk_ids`
- [ ] Docstrings: Update descriptions
- [ ] Examples: Update with new field names

#### strategy_directive.py
- [ ] Docstrings: Remove SWOT references
- [ ] Comments: Update terminology
- [ ] Examples: Update field names

#### enums.py
- [ ] Enum: `OpportunityType` → `SignalType`
- [ ] Enum: `ThreatType` → `RiskType`
- [ ] Docstrings: Update descriptions

#### id_generators.py
- [ ] Function: `generate_opportunity_id()` → `generate_signal_id()`
- [ ] Function: `generate_threat_id()` → `generate_risk_id()`
- [ ] Prefix: `"OPP"` → `"SIG"`
- [ ] Prefix: `"THR"` → `"RSK"`
- [ ] VALID_PREFIXES: Update set
- [ ] __all__: Update exports
- [ ] Docstrings: Remove SWOT references
- [ ] Comments: Update examples

---

## Phase 3: Test Suite Refactoring

### 3.1 File Renames
- [ ] `tests/unit/dtos/strategy/test_opportunity_signal.py` → `test_signal.py`
- [ ] `tests/unit/dtos/strategy/test_threat_signal.py` → `test_risk.py`

### 3.2 test_signal.py Updates
- [ ] Import: Update to `from backend.dtos.strategy.signal import Signal`
- [ ] Classes: `TestOpportunitySignal*` → `TestSignal*`
- [ ] Instances: `OpportunitySignal(...)` → `Signal(...)`
- [ ] IDs: `OPP_` → `SIG_`
- [ ] Fields: `opportunity_id` → `signal_id`
- [ ] Docstrings: Update descriptions

### 3.3 test_risk.py Updates
- [ ] Import: Update to `from backend.dtos.strategy.risk import Risk`
- [ ] Classes: `TestThreatSignal*` → `TestRisk*`
- [ ] Instances: `ThreatSignal(...)` → `Risk(...)`
- [ ] IDs: `THR_` → `RSK_`
- [ ] Fields: `threat_id` → `risk_id`
- [ ] Docstrings: Update, remove SWOT

### 3.4 test_causality.py Updates
- [ ] Fields: `opportunity_signal_ids` → `signal_ids`
- [ ] Fields: `threat_ids` → `risk_ids`
- [ ] IDs: `OPP_` → `SIG_`, `THR_` → `RSK_`
- [ ] Method names: Update test method names
- [ ] Comments: Update worker references

### 3.5 test_strategy_directive.py Updates
- [ ] Fields: `opportunity_signal_ids` → `signal_ids`
- [ ] Fields: `threat_ids` → `risk_ids`
- [ ] IDs: `OPP_` → `SIG_`, `THR_` → `RSK_`
- [ ] Test data: Update planner names

### 3.6 test_enums.py Updates
- [ ] Test names: `test_all_opportunity_types_present` → `test_all_signal_types_present`
- [ ] Test names: `test_all_threat_types_present` → `test_all_risk_types_present`
- [ ] Enum refs: `OpportunityType` → `SignalType`
- [ ] Enum refs: `ThreatType` → `RiskType`

### 3.7 test_id_generators.py Updates
- [ ] Function calls: `generate_opportunity_id()` → `generate_signal_id()`
- [ ] Function calls: `generate_threat_id()` → `generate_risk_id()`
- [ ] Prefixes: `OPP_` → `SIG_`, `THR_` → `RSK_`
- [ ] Method names: Update all test method names
- [ ] Extraction tests: Update prefix tests

---

## Phase 4: Documentation Refactoring

### 4.1 Implementation Status
- [ ] `docs/implementation/IMPLEMENTATION_STATUS.md`
  - [ ] Section header: "Strategy SWOT" → "Signal Detection"
  - [ ] Table rows: Update DTO names
  - [ ] Remove: SWOT terminology
  - [ ] Update: Test counts if changed

### 4.2 Reference Documentation
- [ ] Rename: `docs/reference/dtos/opportunity_signal.md` → `signal.md`
- [ ] Create: `docs/reference/dtos/risk.md`
- [ ] Update: `docs/reference/README.md` component table
- [ ] Update: `docs/reference/dtos/STRATEGY_DTO_TEMPLATE.md` prefix table

### 4.3 Architecture Documentation
- [ ] `docs/architecture/WORKER_TAXONOMY.md`
  - [ ] Category: OpportunityWorker → SignalDetector
  - [ ] Category: ThreatWorker → RiskMonitor
- [ ] `docs/architecture/DATA_FLOW.md`
  - [ ] Update: Signal flow examples
- [ ] `docs/architecture/OBJECTIVE_DATA_PHILOSOPHY.md`
  - [ ] Update: Examples with new terminology

### 4.4 Other Documentation
- [ ] `docs/TODO.md`
  - [ ] Update: DTO references
  - [ ] Update: Worker references
- [ ] `docs/DOCUMENTATION_MAINTENANCE.md`
  - [ ] Update: DTO references
- [ ] `agent.md`
  - [ ] Update: Architecture description
  - [ ] Update: Examples

### 4.5 Archive/Delete Obsolete
- [ ] DELETE: `docs/development/#Archief/decision_framework.md`
- [ ] Clean: `docs/development/#Archief/design_causality_chain.md` (SWOT sections)
- [ ] Clean: `docs/development/#Archief/design_trigger_context_v1.md` (SWOT sections)

---

## Phase 5: Verification & Testing

### 5.1 Test Execution
- [ ] Run: `pytest tests/ -v`
- [ ] Verify: 336/336 tests passing
- [ ] Check: No test failures

### 5.2 Code Quality
- [ ] Run: `pylint backend/ --rcfile=.pylintrc`
- [ ] Verify: 10.00/10 score
- [ ] Check: No new errors

### 5.3 Search for Remnants
- [ ] Search: `OpportunitySignal` in .py files
- [ ] Search: `ThreatSignal` in .py files
- [ ] Search: `OPP_` in code/tests
- [ ] Search: `THR_` in code/tests
- [ ] Search: `SWOT` in active docs

### 5.4 Manual Verification
- [ ] Check: All imports resolve
- [ ] Check: No broken doc links
- [ ] Verify: IMPLEMENTATION_STATUS.md accurate

---

## Phase 6: Finalization

- [ ] Commit all changes
- [ ] Update REFACTORING_LOG.md with completion
- [ ] Merge to main
- [ ] Archive documentation files

---

**Progress:** 0/100+ items completed

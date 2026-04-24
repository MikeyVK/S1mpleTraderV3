# Issue #76 Planning: Quality Gates Tooling Implementation

**Status:** IN PROGRESS

**Created:** 2026-01-08

**Issue:** #76

---

## 1. Scope (from Issue #76)

### In scope (this epic)
- Create `.st3/quality.yaml` containing a catalog of quality gate tool definitions (≥7 tools).
- Implement Pydantic validation models for the configuration (frozen/immutable, Epic #49 style).
- Document generic execution patterns and output parsing strategies (design documentation only).

### Out of scope (explicit non-goals)
- Enforcement policies / phase requirements (belongs to Epic #18).
- Refactor `mcp_server/managers/qa_manager.py` or change runtime execution behavior.
- Activating Ruff/Coverage/Bandit/Black in runtime execution (future issues after executor refactor).

---

## 2. Current State Summary (facts)

- `mcp_server/managers/qa_manager.py` currently hardcodes 3 gates (Pylint/Mypy/Pyright) with parsing + timeouts.
- `mcp_server/tools/quality_tools.py` exposes MCP tool `run_quality_gates` with only `files: list[str]`.
- `mcp_server/validation/python_validator.py` consumes QAManager output shape.
- `.st3/quality.yaml` does not exist yet (no `config/` directory in repo currently).

---

## 3. Planning Goal

Produce a clear, minimal, testable path to deliver the epic outcomes **without touching the current executor**.

This planning phase ends when:
- We have a clear list of deliverables and acceptance criteria.
- We have an agreed set of files to add and tests to write.
- We have identified the decisions that must be made in the design phase.

---

## 4. Deliverables (what this branch should contain)

### 4.1 Configuration
- `.st3/quality.yaml`
  - Contains ≥7 gate definitions as a catalog, including:
    - Implemented in current executor: Pylint, Mypy, Pyright
    - Catalog/configured for future activation: Ruff, Coverage, Bandit, Black
  - Contains only tooling configuration (no enforcement fields like required/phase/enabled).

### 4.2 Pydantic models + loader
- New module(s) under `mcp_server/config/` to:
  - Define `QualityConfig` root model
  - Define nested models for execution/parsing/capabilities metadata
  - Load YAML from `.st3/quality.yaml`
  - Provide clear validation errors
  - Follow existing style patterns (see `mcp_server/config/workflows.py` and `mcp_server/config/label_config.py`).

### 4.3 Tests
- Unit tests targeting:
  - Valid config loads
  - Invalid config rejected with clear error messages
  - Field-level validation (e.g., command non-empty, timeout > 0)
  - Parsing strategy model validation

Success requirement: 100% coverage on validation logic for the config models.

### 4.4 Documentation (design-only outputs)
- A schema reference and examples for `.st3/quality.yaml`.
- A guide describing the supported parsing strategy types (conceptual, not code).
- A generic “executor pattern” description (design only, no QAManager changes in this epic).

---

## 5. Work Breakdown (planning-level)

### Phase A: Design (next phase after planning)
- Define the `.st3/quality.yaml` schema.
- Define model hierarchy and validation rules.
- Define parsing strategy representations.
- Define documentation structure.

### Phase B: Implementation (after design approval)
- Add `.st3/quality.yaml`.
- Add Pydantic models and loader under `mcp_server/config/`.
- Add unit tests.
- Add docs for schema + parsing strategies + execution patterns.

### Phase C: Verification
- Run unit tests.
- Run quality gates on modified Python files.

---

## 6. Acceptance Criteria (for this epic)

### Configuration
- `.st3/quality.yaml` exists and includes ≥7 gate definitions.
- YAML validates against Pydantic models.
- No enforcement policy fields present.

### Models
- Models are immutable/frozen (consistent with Epic #49 patterns).
- Validation rejects invalid configs with clear error messages.
- Validation logic has 100% test coverage.

### Documentation
- Schema reference document exists and matches models.
- Parsing strategy guide exists with examples.
- Generic execution patterns doc exists (design-only; no runtime changes).

### Safety boundary
- No behavioral change to `mcp_server/managers/qa_manager.py` in this epic.

---

## 7. Design Decisions Required (to be made in Design Phase)

These are intentionally not decided in planning:
- Exact YAML structure (keys, naming, nesting).
- How to represent parsing strategies (e.g., `text_regex` vs `json_field` vs `exit_code`).
- How to represent capabilities metadata (and which fields are required vs optional).
- Where documentation should live and exact doc structure.

---

## 8. Next Step

Move to design phase and produce:
- `docs/development/issue76/design.md` (schema + model design + examples)


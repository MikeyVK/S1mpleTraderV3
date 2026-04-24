# Issue #76 Design: Quality Gates Tooling (quality.yaml + models)

**Status:** DRAFT
**Author:** GitHub Copilot
**Created:** 2026-01-08
**Last Updated:** 2026-01-08
**Issue:** #76

---

## 1. Overview

### 1.1 Purpose

Define the **configuration-layer design** for quality gate tooling:
- A `.st3/quality.yaml` schema that describes quality gate tools (catalog)
- Pydantic models that validate that schema (consistent with Epic #49 patterns)
- Parsing strategy abstractions suitable for a future generic executor

This document intentionally does **not** implement the schema/models, nor refactor the current executor.

### 1.2 Scope

**In Scope:**
- `.st3/quality.yaml` schema design (tool definitions only; no enforcement policy)
- Pydantic model structure and validation rules
- Design of parsing strategy options (`text_regex`, `json_field`, `exit_code`)
- Design of generic execution patterns (documentation-level)

**Out of Scope:**
- Enforcement fields (e.g., `required`, `enabled`, `phase`) and enforcement logic (Epic #18)
- Refactoring `mcp_server/managers/qa_manager.py` or changing runtime behavior
- Activating Ruff/Coverage/Bandit/Black in runtime execution (future issues)

### 1.3 Related Documents

- [Research baseline](./research.md)
- [Planning](./planning.md)
- [Issue #53 research](../issue53/research.md)
- [Quality gates standard](../../coding_standards/QUALITY_GATES.md)

---

## 2. Background

### 2.1 Current State (facts)

- Current executor: `mcp_server/managers/qa_manager.py` hardcodes 3 gates (Pylint/Mypy/Pyright) with per-gate parsing and timeouts.
- Current MCP wrapper: `mcp_server/tools/quality_tools.py` exposes `run_quality_gates(files=[...])`.
- A validator (`mcp_server/validation/python_validator.py`) consumes QAManager output shape.
- Config file `.st3/quality.yaml` does not exist in this repo yet.

### 2.2 Problem Statement

Quality gate tool definitions are currently embedded in code (command shapes, timeouts, parsing logic). This makes adding or adjusting gates high-friction and mixes configuration concerns with execution/enforcement concerns.

Issue #76 requires a **configuration layer** that can be validated independently (today), and that enables a later executor refactor (future issue) without enforcing “when/where” policies (Epic #18).

### 2.3 Requirements

#### Functional Requirements
- [ ] **FR1:** Define a schema for `.st3/quality.yaml` that can express ≥7 tool definitions: Pylint, Mypy, Pyright, Ruff, Coverage, Bandit, Black.
- [ ] **FR2:** Schema must represent execution information (command, timeout, working_dir) and parsing strategy choice.
- [ ] **FR3:** Schema must represent success/failure determination as part of tool definition (tooling, not enforcement).
- [ ] **FR4:** Schema must explicitly avoid enforcement fields (no `required`, no `phase`, no `enabled`).
- [ ] **FR5:** Pydantic models must validate the schema with clear error messages.

#### Non-Functional Requirements
- [ ] **NFR1:** Compatibility — design must not require changing `QAManager` in this epic.
- [ ] **NFR2:** Testability — model validation should be unit-testable to 100% coverage.
- [ ] **NFR3:** Maintainability — adding a new tool should be primarily a YAML change, not a new Python method.

---

## 3. Design

### 3.1 Architecture Position

This epic defines the **configuration layer** and a **design-only execution layer pattern**.

```
┌───────────────────────────────┐
│ Enforcement (Epic #18)        │  OUT OF SCOPE
│ - phases / required gates     │
└───────────────┬───────────────┘
                │ uses
┌───────────────▼───────────────┐
│ Config Layer (THIS EPIC)      │  IN SCOPE
│ - .st3/quality.yaml         │
│ - Pydantic models + loader    │
└───────────────┬───────────────┘
                │ used by
┌───────────────▼───────────────┐
│ Execution Layer (FUTURE)      │  OUT OF SCOPE
│ - generic executor            │
│ - parser dispatch             │
└───────────────────────────────┘
```

### 3.2 Schema Design: `.st3/quality.yaml`

#### 3.2.1 Top-level structure

Proposed top-level keys:
- `version: str`
- `gates: { <gate_id>: <QualityGate> }`

`gate_id` is a stable identifier (e.g., `pylint`, `mypy`, `pyright`, `ruff`, `coverage`, `bandit`, `black`).

#### 3.2.2 Gate structure

Each `QualityGate` has:
- `name: str` — display name
- `description: str` — short explanation
- `execution: ExecutionConfig`
- `parsing: ParsingConfig`
- `success: SuccessCriteria`
- `capabilities: CapabilitiesMetadata`

No enforcement fields are allowed.

#### 3.2.3 ExecutionConfig

Fields:
- `command: list[str]` (non-empty; first element is executable/module runner)
- `timeout_seconds: int` (> 0)
- `working_dir: str | null` (optional)

Notes:
- `command` is a list (not a single string) to avoid shell escaping issues and to be consistent with `subprocess.run([...])`.

#### 3.2.4 ParsingConfig

`strategy` is an enum:
- `text_regex` — parse plain text output
- `json_field` — parse JSON output and extract fields by path
- `exit_code` — no parsing needed; rely on exit code

Strategy-specific fields:

`text_regex`:
- `patterns: list[RegexPattern]`

`RegexPattern` (B2):
- `name: str` — stable identifier for the extracted value (e.g., `rating`, `total`)
- `regex: str` — Python-style regex pattern
- `flags: list[str] | null` — optional; allowed values: `IGNORECASE`, `MULTILINE`, `DOTALL`
- `group: int | str | null` — optional; capture group index (e.g., `1`) or named group (e.g., `score`)
- `required: bool` — default `true`; if true, missing match should be treated as invalid output (future executor concern)

`json_field`:
- `fields: dict[str, str]` mapping logical names to JSON Pointer paths (C2, RFC 6901)
  - Example: `error_count: /summary/errorCount`
  - Example: `diagnostics: /generalDiagnostics`
- `diagnostics_path: str | null` (optional) — JSON Pointer path to a list of diagnostic items

`exit_code`:
- no additional fields

#### 3.2.5 SuccessCriteria

Success criteria is part of *tool definition* (what “pass” means for that tool), without expressing enforcement (when/where it is required).

A2 (contained flexibility):
- `success.mode` is kept for explicitness, **but must exactly equal** `parsing.strategy`.
- This avoids ambiguous “mixed signal” semantics while keeping the schema extensible.

Fields:
- `mode: str` — enum: `text_regex` | `json_field` | `exit_code`
  - Validation rule: `success.mode == parsing.strategy`
- Optional numeric thresholds, depending on `mode`:
  - `exit_codes_ok: list[int]` (default `[0]`) — used when `mode=exit_code`
  - `max_errors: int | null` — used when `mode` yields a count
  - `min_score: float | null` — used when `mode` yields a score
  - `require_no_issues: bool` (default `true`)

Non-goal (v1): Multi-signal success (e.g., parse JSON for reporting but decide on exit code) is intentionally not modeled here.

#### 3.2.6 CapabilitiesMetadata

Fields (metadata only):
- `file_types: list[str]` (e.g., `[".py"]`)
- `supports_autofix: bool`
- `produces_json: bool`

---

### 3.3 Pydantic Model Design

Models (names follow Issue #76):
- `QualityConfig`
  - `version: str`
  - `gates: dict[str, QualityGate]`
- `QualityGate`
  - `name`, `description`, `execution`, `parsing`, `success`, `capabilities`
- `ExecutionConfig`
- `ParsingConfig` (discriminated union by `strategy`)
- `SuccessCriteria`
- `CapabilitiesMetadata`

Validation rules (non-exhaustive):
- `version` must be non-empty.
- `gates` must be non-empty.
- `command` must be non-empty; all elements must be non-empty strings.
- `timeout_seconds` must be > 0.
- Enforce “no enforcement fields” by schema/model strictness (reject unknown fields).

Immutability:
- Models should be frozen/immutable to match config pattern expectations.

---

### 3.4 Parsing Strategies (Design)

This epic defines parsing abstractions; actual parsing/execution is implemented in a future issue.

- **text_regex:** for tools that output human text with stable patterns (typical for pylint/mypy).
- **json_field:** for tools that emit JSON (`pyright --outputjson`).
- **exit_code:** for tools where exit code is sufficient (e.g., `ruff check`, `black --check`, `bandit`).

---

### 3.5 Examples (7+ gates)

These are examples of how the schema can represent the required catalog. These examples do not imply runtime activation today.

```yaml
version: "1.0"

gates:
  pylint:
    name: "Pylint"
    description: "Python linting"
    execution:
      command: ["python", "-m", "pylint", "--enable=all", "--max-line-length=100", "--output-format=text"]
      timeout_seconds: 60
      working_dir: null
    parsing:
      strategy: "text_regex"
      patterns:
        - name: "rating"
          regex: "Your code has been rated at ([\\d.]+)/10"
    success:
      mode: "text_regex"
      min_score: 10.0
      require_no_issues: true
    capabilities:
      file_types: [".py"]
      supports_autofix: false
      produces_json: false

  mypy:
    name: "Mypy"
    description: "Static type checking"
    execution:
      command: ["python", "-m", "mypy", "--strict", "--no-error-summary"]
      timeout_seconds: 60
      working_dir: null
    parsing:
      strategy: "text_regex"
      patterns:
        - name: "error_line"
          regex: "^(.+?):(\\d+): (error|warning): (.+)$"
    success:
      mode: "text_regex"
      max_errors: 0
      require_no_issues: false
    capabilities:
      file_types: [".py"]
      supports_autofix: false
      produces_json: false

  pyright:
    name: "Pyright"
    description: "Type checking (Pylance parity)"
    execution:
      command: ["pyright", "--outputjson"]
      timeout_seconds: 120
      working_dir: null
    parsing:
      strategy: "json_field"
      fields:
        diagnostics: "/generalDiagnostics"
    success:
      mode: "json_field"
      max_errors: 0
      require_no_issues: true
    capabilities:
      file_types: [".py"]
      supports_autofix: false
      produces_json: true

  ruff:
    name: "Ruff"
    description: "Fast linter (catalog entry)"
    execution:
      command: ["ruff", "check"]
      timeout_seconds: 60
      working_dir: null
    parsing:
      strategy: "exit_code"
    success:
      mode: "exit_code"
      exit_codes_ok: [0]
      require_no_issues: true
    capabilities:
      file_types: [".py"]
      supports_autofix: true
      produces_json: false

  black:
    name: "Black"
    description: "Formatter check (catalog entry)"
    execution:
      command: ["black", "--check"]
      timeout_seconds: 60
      working_dir: null
    parsing:
      strategy: "exit_code"
    success:
      mode: "exit_code"
      exit_codes_ok: [0]
      require_no_issues: true
    capabilities:
      file_types: [".py"]
      supports_autofix: true
      produces_json: false

  bandit:
    name: "Bandit"
    description: "Security scanning (catalog entry)"
    execution:
      command: ["bandit", "-r"]
      timeout_seconds: 120
      working_dir: null
    parsing:
      strategy: "exit_code"
    success:
      mode: "exit_code"
      exit_codes_ok: [0]
      require_no_issues: true
    capabilities:
      file_types: [".py"]
      supports_autofix: false
      produces_json: false

  coverage:
    name: "Coverage"
    description: "Coverage reporting via pytest-cov (catalog entry)"
    execution:
      command: ["pytest", "--cov=backend", "--cov-report=term-missing"]
      timeout_seconds: 300
      working_dir: null
    parsing:
      strategy: "text_regex"
      patterns:
        - name: "total"
          regex: "TOTAL\\s+\\d+\\s+\\d+\\s+(\\d+)%"
    success:
      mode: "text_regex"
      require_no_issues: false
    capabilities:
      file_types: [".py"]
      supports_autofix: false
      produces_json: false
```

---

## 4. Implementation Notes (Non-Goals)

Implementation is out of scope for the design phase.

- See planning for sequencing and deliverables: `docs/development/issue76/planning.md`.
- This design should enable a later executor refactor without requiring schema changes.

---

## 5. Alternatives Considered

### Alternative A: Minimal YAML with tool-specific freeform fields

**Description:** Allow each gate to define arbitrary keys with minimal validation.

**Pros:**
- Very flexible
- Minimal model work

**Cons:**
- Weak validation
- Harder to evolve and document

**Decision:** Rejected; Issue #76 requires strong validation and consistent patterns.

### Alternative B: Strict schema with discriminated unions for parsing and success

**Description:** A small set of well-defined strategies with strict validation.

**Pros:**
- Clear extensibility patterns
- Strong validation and better error messages

**Cons:**
- Requires upfront design work

**Decision:** Chosen.

---

## 6. Open Questions

Resolved decisions (to unblock implementation/TDD):
- **A2:** `success.mode` is required and must equal `parsing.strategy`.
- **B2:** `RegexPattern` includes optional `flags`, `group`, and `required`.
- **C2:** JSON extraction uses JSON Pointer paths (RFC 6901).

Resolved (contained) decisions for v1:
- **C2a:** JSON Pointer usage allows array indexing (e.g., `/generalDiagnostics/0/rule`) because it is part of RFC 6901. Model validation will only ensure the value is a non-empty string that starts with `/` (or is exactly `/`).
- **B2a:** `RegexPattern.required` may be `false` (optional patterns). In v1, this only affects validation strictness in config parsing (i.e., it is allowed in YAML); runtime semantics are deferred to the future executor.

Remaining open questions (future executor/policy):
- If `RegexPattern.required=false`, should a missing match still be reported as a warning vs silently ignored? (executor behavior, out of scope here)

---

## 7. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-08 | Use YAML + Pydantic models | Consistent with Epic #49 patterns; strong validation |
| 2026-01-08 | Use 3 parsing strategies | Matches Issue #76 guidance; covers current + catalog tools |
| 2026-01-08 | A2: `success.mode` must equal `parsing.strategy` | Keep explicitness but prevent mixed-signal semantics |
| 2026-01-08 | B2: RegexPattern supports flags/group/required | Make regex parsing robust without executor coupling |
| 2026-01-08 | C2: JSON Pointer paths for JSON extraction | Standardized paths incl. arrays; clear validation |
| 2026-01-08 | C2a: Allow JSON Pointer array indexing | RFC 6901 supports arrays; keep v1 validation simple |
| 2026-01-08 | B2a: Allow optional regex patterns | Keep schema flexible; executor semantics deferred |
| 2026-01-08 | Exclude enforcement fields | SRP boundary per Issue #76; enforcement belongs to Epic #18 |

---

## 8. References

- `docs/development/issue76/research.md`
- `docs/development/issue76/planning.md`
- `docs/development/issue53/research.md`
- `docs/coding_standards/QUALITY_GATES.md`

(Note: links above are relative in section 1.3; references here are paths for grep/navigation.)

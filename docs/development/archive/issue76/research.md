# Issue #76 Research: Quality Gates Tooling (Configuration Layer)

**Issue:** #76 – Epic: Quality Gates Tooling Implementation

**Date:** 2026-01-08

---

## 1. Research Objective (Scope = Research)

This document is the **research** baseline for Issue #76.

It aims to be **self-contained** for this branch by collecting:
- The exact scope boundaries from Issue #76
- Current implementation facts (what exists today)
- The concrete gaps that motivate the work
- The validated findings from Issue #53 research (as inputs)

This research explicitly does **not**:
- Propose sequencing / milestones / work breakdown (planning)
- Decide a schema structure (design)
- Implement or refactor execution (coding)

---

## 2. Primary Scope Statement (from Issue #76)

Issue #76 scope states:

**In scope (today):**
- `.st3/quality.yaml` with tool definitions
- Pydantic models for validation
- Generic execution patterns (documentation)
- Output parsing strategies (documentation)

**Out of scope (today):**
- Enforcement policies / phase requirements (Epic #18)
- QAManager refactor / changing actual runtime execution
- Integrating additional gates into QAManager runtime (future issues)

---

## 3. Current State in This Repo (Facts)

### 3.1 Current execution implementation

File: `mcp_server/managers/qa_manager.py`

Observed behavior:
- Input: list of paths
- Pre-check: missing file paths cause an early failing gate result
- Filtering: only `.py` files are executed; non-`.py` are skipped and reported
- Current gates executed:
  1. Linting (Pylint)
  2. Type Checking (Mypy)
  3. Pyright
- Execution style:
  - subprocess-based
  - continue-on-error (all gates run)
  - timeouts: 60s / 60s / 120s
- Parsing:
  - Pylint: text parsing and rating extraction
  - Mypy: text parsing of errors
  - Pyright: JSON parsing via `--outputjson` (defensive parsing)

### 3.2 Tool wrapper

File: `mcp_server/tools/quality_tools.py`

Observed behavior:
- MCP tool `run_quality_gates` accepts **only** `files: list[str]`.
- Tool calls `QAManager.run_quality_gates(files)` and formats output as text.

### 3.3 Validator consumption

File: `mcp_server/validation/python_validator.py`

Observed behavior:
- Calls `QAManager.run_quality_gates([scan_path])`.
- Translates gate issues into `ValidationIssue` objects.
- Extracts numeric score from the "Linting" gate score string if present.

Implication:
- The shape of QAManager results (gate names, score formatting, issue fields) is an external contract for validators.

---

## 4. Documentation vs Implementation (Facts)

### 4.1 Manual quality standard describes 5 gates

File: `docs/coding_standards/QUALITY_GATES.md`

Observed:
- Describes **5 mandatory gates** for DTO workflow (3x pylint checks + mypy + pytest).

### 4.2 Current QAManager executes 3 gates

File: `mcp_server/managers/qa_manager.py`

Observed:
- Executes 3 gates (Pylint/Mypy/Pyright) and does not run pytest as a gate.

### 4.3 MCP tools documentation mismatch

File: `docs/mcp_server/TOOLS.md`

Observed:
- Documents `run_quality_gates` with optional params (`include_tests`, `gates`) that are **not present** in `mcp_server/tools/quality_tools.py`.

---

## 5. Issue #53 Research Findings (Validated Inputs)

File: `docs/development/issue53/research.md`

Issue #53 established the baseline facts motivating externalization:
- ~24 hardcoded configuration points exist across the current gates (command shape, timeout, parsing rules, etc.)
- Gate execution code has significant gate-specific logic and duplication
- Parsing strategies needed include at least:
  - text+regex parsing (pylint/mypy patterns)
  - JSON parsing (pyright)
- Ruff and Coverage are configured at project level but not currently enforced by QAManager
- Documentation and implementation have drift (manual vs automated gate sets)

Important note:
- Issue #76 requires a catalog of **≥7 tools** in `.st3/quality.yaml` (Pylint, Mypy, Pyright, Ruff, Coverage, Bandit, Black), but adding these to runtime is explicitly a future concern.

---

## 6. Existing “Config + Validation” Patterns in Repo

The repo already has examples of YAML + Pydantic patterns:

- `.st3/workflows.yaml` loaded by `mcp_server/config/workflows.py`
- `.st3/labels.yaml` loaded by `mcp_server/config/label_config.py`

Observed properties worth noting (fact-only):
- YAML is loaded and validated by Pydantic models.
- Errors are raised with explicit messages when config is missing/invalid.

---

## 7. Research Outputs (What Planning/Design Can Rely On)

From Issue #76 + Issue #53 + current codebase inspection, planning/design can rely on:
- Current execution layer exists and must not be refactored under this epic.
- A configuration layer is missing (`.st3/quality.yaml` does not exist yet in this repo).
- There is documented expectation of 5 gates, but implemented automation is 3 gates.
- Tools docs describe parameters that the implemented tool does not accept.
- Validators consume QAManager output shape.

---

## 8. Open Questions (For Planning/Design; No Answers Here)

- Should `.st3/quality.yaml` mirror the **current executor gates** (3) and add additional catalog entries (≥7) as disabled/unimplemented metadata, or represent a broader conceptual set?
- Should the documentation drift be corrected as part of this epic (docs-only), or deferred?
- How strictly should model validation enforce command non-emptiness, timeout constraints, and parsing configuration without adding enforcement policy fields?

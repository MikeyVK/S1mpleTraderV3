<!-- docs/development/issue229/design.md -->
<!-- template=design version=5827e841 created=2026-02-19 updated= -->
# Phase Deliverables Enforcement — Design

**Status:** DRAFT
**Version:** 1.0
**Last Updated:** 2026-02-19

## Prerequisites

Read these first:
1. `research.md` — hook architecture, gap analysis
2. `findings.md` — GAP-01..04, Option C validation strategy, structured `validates` schema
3. `planning.md` v1.2 — 4 cycle breakdown, test names, success criteria

---

## 1. Context & Requirements

### 1.1. Problem Statement

`PhaseStateEngine` hardcodes phase gate logic: planning deliverables are validated at TDD *entry* (wrong layer), there is no planning *exit* gate, forced transitions bypass all checks silently, and `save_planning_deliverables` is not reachable via MCP. `workphases.yaml` has no mechanism to declare per-phase deliverable contracts.

### 1.2. Requirements

**Functional:**
- [ ] Leaving planning phase must raise `PhaseDeliverableError` if `exit_requires` entries in `workphases.yaml` are not satisfied
- [ ] Entering a phase that declares `entry_expects` must log a warning per unsatisfied entry (no block)
- [ ] Forced transition must log `logger.warning` listing each skipped `exit_requires` and `entry_expects` gate
- [ ] `DeliverableChecker` must support `file_exists`, `contains_text`, `absent_text`, `key_path` validate types
- [ ] `save_planning_deliverables` must be callable as an MCP tool

**Non-Functional:**
- [ ] `DeliverableChecker` is pure — no I/O side effects beyond reading
- [ ] Existing phases without `exit_requires`/`entry_expects` in `workphases.yaml` load and transition without error
- [ ] All new behaviour covered by unit tests before wiring into engine (Cycle 1 before Cycle 2)

### 1.3. Constraints

- Must not break existing phases without `exit_requires` (backward compat)
- `DeliverableChecker` must be pure — no side effects, no state mutation
- `force_transition()` remains unconditional — only adds a warning, never blocks
- Existing `on_enter_tdd_phase` cycle-init logic must be preserved after planning-deliverables check is removed

---

## 2. Design Options

### 2.1. Option A — Inline specs in `workphases.yaml`

`exit_requires` lists deliverable specs inline (file, type, text). Engine runs checker directly from YAML.

**Pros:**
- Single SSOT per phase

**Cons:**
- Couples phase config to file layout — `workphases.yaml` grows unwieldy
- Cannot reuse per-issue deliverable context

---

### 2.2. Option B — Indirection via `projects.json` ✅ CHOSEN

`exit_requires` lists key names (e.g. `planning_deliverables`). Engine reads `validates` entries from `projects.json[issue][key]`, runs `DeliverableChecker` on each entry.

**Pros:**
- Phase config stays stable — `workphases.yaml` only names the required key, not the spec
- Per-issue deliverable specs live with the issue in `projects.json`
- `DeliverableChecker` is reusable across any phase/key combination

**Cons:**
- Two-file lookup (`workphases.yaml` → `projects.json`): slightly more indirection

---

### 2.3. Option C — Hardcoded hooks (status quo extended)

No YAML config. Engine hardcodes which phases have gates (same pattern as current TDD hooks).

**Pros:**
- Simple, no YAML parsing

**Cons:**
- Perpetuates the architectural problem — not extensible, goes against #229 goal

---

## 3. Decision

**Option B — Indirection via `projects.json`**

`workphases.yaml` is stable phase metadata; it declares *which key* must exist. `projects.json` carries *what that key must contain*. The `DeliverableChecker` is a pure utility operating on any `validates` spec, regardless of which phase triggered it. The indirection is intentional and clearly bounded.

---

## 4. Rationale

The separation is architecturally meaningful:
- **What** a phase requires → `workphases.yaml` `exit_requires` (stable, shared across all issues)
- **What** a specific issue produced → `projects.json` deliverable entries with `validates` specs (per-issue, evolves during planning)
- **How** to verify a deliverable → `DeliverableChecker` (pure, testable in isolation)

This matches the existing pattern: `workflow_config.validate_transition()` reads `workflows.yaml` for workflow rules; the engine reads `projects.json` for issue state. Adding `workphases.yaml` as a third config layer is consistent.

---

## 5. Interface Contracts

### 5.1. `workphases.yaml` schema extension

```yaml
planning:
  display_name: "Planning"
  # ... existing fields unchanged ...
  exit_requires:
    - key: "planning_deliverables"
      description: "TDD cycle breakdown with structured deliverables"
  entry_expects: []   # planning produces, does not consume

tdd:
  # ... existing fields unchanged ...
  exit_requires: []
  entry_expects:
    - key: "planning_deliverables"
      description: "Expected from planning phase"
```

Fields are **optional** — phases without them behave identically to current behaviour.

---

### 5.2. `DeliverableChecker`

**Location:** `mcp_server/managers/deliverable_checker.py`

**`validates` spec types:**

| `type` | Required fields | Check performed |
|--------|----------------|-----------------|
| `file_exists` | `file` | File present on disk |
| `contains_text` | `file`, `text` | File contains literal `text` |
| `absent_text` | `file`, `text` | File does NOT contain `text` |
| `key_path` | `file`, `path` | Dot-notation path resolves to a value in JSON/YAML |

**Interface:**

```python
class DeliverableCheckError(ValueError):
    """Raised when a structural deliverable check fails."""

class DeliverableChecker:
    def __init__(self, workspace_root: Path) -> None: ...

    def check(self, deliverable_id: str, validates: dict[str, str]) -> None:
        """Raise DeliverableCheckError if check fails. Silent on success."""
```

---

### 5.3. `PhaseStateEngine` hook dispatch (Cycle 2)

`transition()` already calls `on_exit_tdd_phase` / `on_enter_tdd_phase` by name. The same pattern is extended:

```python
# Pseudo-code — no implementation detail
if from_phase == "planning":
    self.on_exit_planning_phase(branch, issue_number)   # hard gate

if to_phase in <phases with entry_expects>:
    self.on_enter_{to_phase}_phase(branch, issue_number)  # soft warning
```

`on_exit_planning_phase` reads `workphases.yaml` exit_requires, resolves each key from `projects.json`, runs `DeliverableChecker.check()` per `validates` entry. Raises `PhaseDeliverableError` on first failure.

`on_enter_tdd_phase` retains only cycle auto-init logic. Planning deliverables check is removed entirely.

---

### 5.4. `force_transition()` skipped-gate warning (Cycle 3)

After recording the transition, reads `workphases.yaml` for:
- `exit_requires` on `from_phase`
- `entry_expects` on `to_phase`

Logs one `logger.warning` per non-empty gate list:

```
WARNING: force_transition skipped exit_requires gate on 'planning': ['planning_deliverables']
WARNING: force_transition skipped entry_expects gate on 'tdd': ['planning_deliverables']
```

No blocking. No re-checking deliverable presence — warning is unconditional if the gate *exists* in YAML.

---

### 5.5. `SavePlanningDeliverablesTool` (Cycle 4)

**Location:** `mcp_server/tools/project_tools.py`  
**Pattern:** follows `InitializeProjectTool` (existing `BaseTool` subclass in same file)

```python
class SavePlanningDeliverablesInput(BaseModel):
    issue_number: int
    tdd_cycles: dict  # validated by ProjectManager

class SavePlanningDeliverablesTool(BaseTool):
    # Wraps ProjectManager.save_planning_deliverables()
    # Delegates validation to existing ProjectManager logic
    # Registered in server.py alongside InitializeProjectTool
```

---

## 6. Open Questions

- **`entry_expects` hard block vs warning?** → Soft warning only. Consuming phase must not be held hostage by producing phase. Cycle 2 implements warning only.
- **`DeliverableChecker` path resolution?** → Relative to `workspace_root` — same convention as all other managers.

---

## Related Documentation

- **[docs/development/issue229/research.md](research.md)**
- **[docs/development/issue229/planning.md](planning.md)**
- **[docs/development/issue229/findings.md](findings.md)**
- **[mcp_server/managers/phase_state_engine.py](../../../mcp_server/managers/phase_state_engine.py)**
- **[mcp_server/managers/project_manager.py](../../../mcp_server/managers/project_manager.py)**
- **[mcp_server/tools/project_tools.py](../../../mcp_server/tools/project_tools.py)**
- **[.st3/workphases.yaml](../../../.st3/workphases.yaml)**

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-19 | Agent | Initial draft |

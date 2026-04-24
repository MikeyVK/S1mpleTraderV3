# C5–C7 Design: update_planning_deliverables, exit_requires file_glob, phase-generic schema

**Status:** draft  
**Version:** 1.0  
**Date:** 2026-02-19  
**Issue:** #229 (Cycles 5–7)

---

## 1. Problem Statement

Three gaps discovered during the validation phase smoke-test of issue #229:

| Gap | Summary |
|-----|---------|
| **GAP-09** | `save_planning_deliverables` is write-once — no update path for evolving cycles. Direct `projects.json` edits were needed multiple times during this issue. |
| **GAP-10** | `exit_requires` in `workphases.yaml` only supports `key:` checks against `projects.json`. No file-system gate pattern exists, so the research phase has no enforced exit gate. |
| **GAP-11** | `planning_deliverables` schema is TDD-centric (`tdd_cycles` only). Design, validation, documentation phases have no planning-defined deliverable gates. |

---

## 2. Prerequisites

- C1–C4 complete and all tests passing
- `DeliverableChecker._check_file_glob()` available (C2)
- `validate_spec()` available (C4)
- Skipped-gate warning pattern in `PhaseStateEngine` / `ForceCycleTransitionTool` available (C3)

---

## 3. C5 — UpdatePlanningDeliverablesTool (GAP-09)

### 3.1 Options Considered

**Option A — New `update_planning_deliverables` tool with merge-by-id strategy (CHOSEN)**  
Keeps `save_planning_deliverables` write-once (intentional first-commit guard). A separate tool handles subsequent mutations. Merge strategy: new cycle_number → append; existing cycle_number + new deliverable id → append; existing cycle_number + existing deliverable id → overwrite in place.

**Option B — Add `allow_overwrite: bool` flag to existing `save_planning_deliverables`**  
Simpler surface, but blurs the semantic distinction between "initial planning commit" and "iterative update". The write-once guard exists for a reason: forcing explicit action for the first write.

### 3.2 Decision: Option A

### 3.3 Interface Design

```python
class UpdatePlanningDeliverablesInput(BaseModel):
    issue_number: int
    planning_deliverables: dict[str, Any]  # same schema as save

class UpdatePlanningDeliverablesTool(BaseTool):
    name = "update_planning_deliverables"
```

**`ProjectManager.update_planning_deliverables(issue_number, planning_deliverables)`**  
- Raises `ValueError` if `planning_deliverables` key does not yet exist (must call `save_planning_deliverables` first)
- `tdd_cycles.cycles` merge algorithm:
  - Build index: `existing_cycles = {c["cycle_number"]: c for c in existing}`
  - For each incoming cycle: if `cycle_number` not in index → append; else merge `deliverables` by `id` within that cycle
  - Update `tdd_cycles.total` to `max(existing_total, highest incoming cycle_number)` if changed
- Layer 2 `validate_spec()` reused (identical to `save_planning_deliverables`)
- Atomic write (read → merge → write)

---

## 4. C6 — exit_requires file_glob support (GAP-10)

### 4.1 Options Considered

**Option A — Extend `exit_requires` schema with `type: file_glob` variant (CHOSEN)**  
Data-driven, consistent with the existing `key:` variant. `PhaseStateEngine` dispatches on `type` field. Reuses `DeliverableChecker._check_file_glob()`. `{issue_number}` interpolated at gate-check time.

**Option B — Hardcode file-system checks per phase name in `PhaseStateEngine`**  
Tight coupling to phase names. Not extensible. Rejected.

### 4.2 Decision: Option A

### 4.3 Schema Extension

`workphases.yaml` research phase (after C6):
```yaml
research:
  exit_requires:
    - type: file_glob
      file: "docs/development/issue{issue_number}/*research*.md"
      description: "Research document aanwezig"
```

**`PhaseStateEngine` gate-check logic (in `_check_exit_requires`):**
```python
for entry in exit_requires:
    if entry.get("type") == "file_glob":
        pattern = entry["file"].format(issue_number=issue_number)
        checker._check_file_glob({"file": pattern})  # raises DeliverableCheckError on no match
    else:  # existing key: behaviour
        key = entry["key"]
        if key not in project_data:
            raise ValueError(f"Exit requires '{key}' not present in projects.json")
```

Forced transition: if gate skipped, the existing `skipped_gates` list gets `"research.exit_requires[file_glob: ...]"` appended — same C3 pattern.

### 4.4 Impact

- `WorkphasesConfig` needs to accept `exit_requires` entries without `key:` (currently only `key:` is validated)
- `DeliverableChecker._check_file_glob()` already exists — no changes needed there
- `WorkphasesSchema` pydantic model: `exit_requires` items become `Union[KeyRequirement, FileGlobRequirement]`

---

## 5. C7 — planning_deliverables schema generalization (GAP-11)

### 5.1 Options Considered

**Option A — Flat dict with phase keys alongside `tdd_cycles` (CHOSEN)**  
```json
{
  "planning_deliverables": {
    "tdd_cycles": { ... },
    "design": { "deliverables": [...] },
    "validation": { "deliverables": [...] }
  }
}
```
Single entry point for all deliverables. `PhaseStateEngine` checks `planning_deliverables.<phase>.deliverables` on phase exit when key present.

**Option B — Separate top-level key per phase in `projects.json`**  
More explicit but fragments the deliverables across multiple top-level keys. Harder to query in one place. Rejected.

### 5.2 Decision: Option A

### 5.3 Gate Behaviour

```
on_exit_<phase>_phase(branch, issue_number):
    plan = project_manager.get_project_plan(issue_number)
    phase_deliverables = plan.get("planning_deliverables", {}).get(phase_name, {})
    deliverables = phase_deliverables.get("deliverables", [])
    if not deliverables:
        return  # gate optional — silent pass when key absent
    for d in deliverables:
        checker.check(d["id"], d["validates"])  # raises on failure
```

### 5.4 Schema Changes

`save_planning_deliverables` validation in `ProjectManager`:
- Currently rejects keys other than `tdd_cycles` (implicit)
- After C7: accept any key that is either `tdd_cycles` (validated fully) or a known phase name (`design`, `validation`, `documentation`) with a `deliverables: list` sub-key
- Unknown keys → `ValueError` with list of valid phase names

`update_planning_deliverables` (C5) handles per-phase deliverables the same way as `tdd_cycles.cycles` — merge by `id`.

### 5.5 Hotfix Exception

`hotfix` workflow has no `planning` phase → no `planning_deliverables` key in `projects.json` → all per-phase gates silently pass. No code change needed; this falls out naturally from the "gate optional when key absent" rule.

---

## 6. Cross-Cutting Concerns

### Dependency Order

```
C5 (update tool) → C7 (per-phase deliverables, needs update tool for iterative saves)
C6 (file_glob gate) is independent — can run in parallel with C5/C7
```

Recommended TDD order: **C5 → C6 → C7** (C5 first unblocks C7).

### Backward Compatibility

| Change | Impact |
|--------|--------|
| `exit_requires` accepts `type:` field | New schema variant, old `key:` entries unaffected |
| `planning_deliverables` new phase keys | Existing `tdd_cycles`-only entries unaffected |
| `update_planning_deliverables` new tool | Additive only |
| `on_exit_<phase>_phase` gate check | Pass-through when `planning_deliverables.<phase>` absent — no behaviour change for existing projects |

---

## 7. Related Files

| File | Change |
|------|--------|
| `mcp_server/managers/project_manager.py` | Add `update_planning_deliverables()`, relax `planning_deliverables` schema for phase keys |
| `mcp_server/managers/phase_state_engine.py` | `_check_exit_requires` supports `type:file_glob`; `on_exit_<phase>` gates check per-phase deliverables |
| `mcp_server/tools/project_tools.py` | Add `UpdatePlanningDeliverablesInput`, `UpdatePlanningDeliverablesTool` |
| `mcp_server/server.py` | Register `UpdatePlanningDeliverablesTool` |
| `.st3/workphases.yaml` | Add `exit_requires` to research phase |
| `mcp_server/core/workphases_config.py` (if exists) | Extend schema for `FileGlobRequirement` |

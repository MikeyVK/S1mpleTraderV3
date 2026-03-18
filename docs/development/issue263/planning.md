<!-- docs\development\issue263\planning.md -->
<!-- template=planning version=130ac5ea created=2026-03-18T19:39Z updated= -->
# Issue #263 Planning — Copilot Orchestration V1 Package Seam Migration

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-03-18

---

## Purpose

Turn the completed research decisions into an execution plan for the first migration run only.

**Dual purpose:** this document remains the human-readable planning reference and also acts as input for `save_planning_deliverables`. The **Deliverables** table at the top of each cycle is the source for machine-readable planning deliverables; the rest of the cycle text stays implementation-facing.

## Scope

**In Scope:**
Create the package seam under `src/copilot_orchestration/`, move the current orchestration implementation into that package in a coarse-grained way, keep the current hook-level structure mostly intact, and leave repo-specific agents/prompts/doctrine outside the package.

**Out of Scope:**
Migrating `mcp_server` to `src/`, migrating the ST3/backend application layer, redesigning role-versus-prompt boundaries, implementing declarative v2 contracts, rebuilding the orchestration test suite, or performing full architecture hardening in the first run.

## Prerequisites

Read these first:
1. Research phase closed with explicit decisions on scope and package direction
2. Branch phase transitioned from research to planning
3. Only `copilot_orchestration` is in migration scope; `mcp_server` and ST3/backend stay untouched
4. The first run remains structurally coarse rather than a full v2 decomposition

---

## Summary

Plan the first cleanup run as a coarse-grained migration that introduces a new `src/copilot_orchestration/` package seam for the VS Code orchestration layer only, without migrating `mcp_server` or the ST3/backend layer and without performing the deeper v2 refactor.

---

## Dependencies

- Current hook scripts remain the source material for coarse relocation
- Repo-specific wrappers and prompt files must stay outside the new package boundary
- Any future deeper module split depends on later v2 refactor work, not on this planning cycle

---

## Execution Order

This first migration run is sequential at the cycle level.

Required order:
1. `C_PKG.1 Boundary Freeze`
2. `C_PKG.2 Package Root Creation`
3. `C_PKG.3 Coarse Hook Relocation`
4. `C_PKG.4 Thin Shim Conversion`
5. `C_PKG.5 Closure And Deferrals`

Rules:
- A later cycle does not start before the previous cycle is materially complete.
- The order is structural, not granular: it constrains cycle progression, not the exact line-by-line implementation sequence inside a cycle.
- `C_PKG.2` depends on `C_PKG.1` freezing the scope and minimal shape.
- `C_PKG.3` depends on `C_PKG.2` creating the package root.
- `C_PKG.4` depends on `C_PKG.3` relocating implementation ownership into the package.
- `C_PKG.5` depends on `C_PKG.4` making repo-local scripts thin shims.

Machine-readable note:
- This same order is already encoded in `.st3/deliverables.json` through `cycle_number: 1..5`.
- The planning document is the human-readable explanation of that sequence.

---

## TDD Cycles

## Cycle 1 — C_PKG.1 Boundary Freeze

**Goal:** Freeze the exact scope boundary and minimal V1 package shape for the first run.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_pkg_1.scope_only_orchestration` | Scope limited to copilot_orchestration | decision | planning + research docs explicitly limit migration to `copilot_orchestration` | planning and research documents both state that `mcp_server` and ST3/backend are out of scope | `contains_text: docs/development/issue263/planning.md -> "Only \`copilot_orchestration\` is in migration scope"` |
| `c_pkg_1.future_model_context_only` | Future sibling-package model marked as context only | decision | package-boundary research doc distinguishes current scope from future repo model | the future `src/mcp_server` and `src/st3` model is documented as later architectural context only | `contains_text: docs/development/issue263/copilot_orchestration_packaging_research.md -> "future sibling-package model is architectural context only"` |
| `c_pkg_1.v1_shape_frozen` | Minimal V1 package fill agreed | decision | minimal V1 fill documented as `src/copilot_orchestration/hooks/` | the coarse V1 fill is explicit and treated as sufficient for the first run | `contains_text: docs/development/issue263/copilot_orchestration_packaging_research.md -> "Minimal acceptable V1 package fill"` |

**Tests:**
- No mandatory test migration in this cycle.
- Verification is document and path based.

**Success Criteria:**
- Package boundary is explicit in planning and research documents.
- Minimal V1 package shape is agreed: `src/copilot_orchestration/hooks/`.
- Out-of-scope boundaries are explicit enough to reject scope drift during implementation.

## Cycle 2 — C_PKG.2 Package Root Creation

**Goal:** Create the package root under `src/copilot_orchestration/` without forcing the final v2 submodule design.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_pkg_2.package_root` | Package root created | component | `src/copilot_orchestration/__init__.py` | package import root exists under `src/` | `file_exists: src/copilot_orchestration/__init__.py` |
| `c_pkg_2.hooks_namespace` | Coarse hooks namespace created | component | `src/copilot_orchestration/hooks/` | the new package contains a hooks namespace for the coarse V1 migration | `file_exists: src/copilot_orchestration/hooks/__init__.py` |
| `c_pkg_2.pythonpath_extended` | src/ toegevoegd aan Python discovery | wiring | `pyproject.toml` of `pytest pythonpath` bevat `src/` | `from copilot_orchestration.hooks import ...` werkt in tests en runtime zonder `spec_from_file_location` | `contains_text: pyproject.toml -> "src"` |
| `c_pkg_2.repo_scope_preserved` | No repo-wide src migration introduced | guard | no collateral move of `mcp_server` or ST3/backend into `src/` during this cycle | package creation touches only `copilot_orchestration` paths | `absent_text: docs/development/issue263/planning.md -> "Migrating mcp_server to src"` |

**Tests:**
- Import-path and file-layout validation only.
- No requirement to rebuild or migrate the current ad hoc orchestration tests.

**Success Criteria:**
- `src/copilot_orchestration/__init__.py` exists.
- `src/copilot_orchestration/hooks/` becomes the new package-owned location for the current orchestration implementation.
- `src/` is included in Python package discovery through `pyproject.toml` or pytest `pythonpath` so `from copilot_orchestration...` imports resolve without bespoke file loading.
- No repo-wide `src/` migration is introduced as collateral work.

## Cycle 3 — C_PKG.3 Coarse Hook Relocation

**Goal:** Move the current orchestration code into the new package boundary in a coarse-grained way while preserving the existing script-level shape as much as possible.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_pkg_3.workspace_session_start` | Workspace session_start relocated | relocation | `src/copilot_orchestration/hooks/session_start.py` | workspace hook implementation now lives in the package | `file_exists: src/copilot_orchestration/hooks/session_start.py` |
| `c_pkg_3.imp_qa_session_start` | Role-specific session_start hooks relocated | relocation | `src/copilot_orchestration/hooks/session_start_imp.py` and `src/copilot_orchestration/hooks/session_start_qa.py` | imp and qa session-start implementations now live in the package | `file_exists: src/copilot_orchestration/hooks/session_start_imp.py` |
| `c_pkg_3.pre_compact_hooks` | PreCompact hooks relocated | relocation | `src/copilot_orchestration/hooks/pre_compact.py` and `src/copilot_orchestration/hooks/pre_compact_agent.py` | both workspace and agent pre-compact implementations now live in the package | `file_exists: src/copilot_orchestration/hooks/pre_compact_agent.py` |
| `c_pkg_3.stop_guard_relocated` | Stop hook relocated | relocation | `src/copilot_orchestration/hooks/stop_handover_guard.py` | stop guard implementation now lives in the package | `file_exists: src/copilot_orchestration/hooks/stop_handover_guard.py` |
| `c_pkg_3.no_premature_split` | No final v2 module split forced | guard | no mandatory extraction into final `compact/`, `session/`, `contracts/`, `config/`, or `enforcement/` modules | the first run keeps hook-level decomposition largely intact | `contains_text: docs/development/issue263/copilot_orchestration_packaging_research.md -> "the first cleanup run is allowed to be structurally coarse"` |

**Tests:**
- Focus on runtime continuity and basic import correctness.
- Use the smallest direct validation surface needed to prove relocation did not break hook entry behavior.

**Success Criteria:**
- The six current hook implementations live under `src/copilot_orchestration/hooks/`.
- No broad internal decomposition is introduced unless a tiny helper extraction is technically unavoidable.
- Python ownership of orchestration logic is clearly inside the package boundary rather than spread across repo-local scripts.

## Cycle 4 — C_PKG.4 Thin Shim Conversion

**Goal:** Turn `scripts/copilot_hooks/*.py` into thin entry shims that delegate into the package while keeping VS Code registration paths stable.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_pkg_4.workspace_shim` | Workspace hook shims delegate to package | wiring | repo-local `session_start.py` and `pre_compact.py` act as entry shims | repo-local workspace scripts import from `copilot_orchestration` rather than owning the implementation | `contains_text: scripts/copilot_hooks/session_start.py -> "copilot_orchestration"` |
| `c_pkg_4.role_shims` | Role-specific shims delegate to package | wiring | repo-local `session_start_imp.py`, `session_start_qa.py`, and `pre_compact_agent.py` act as entry shims | role-specific repo-local scripts import from `copilot_orchestration` rather than owning the implementation | `contains_text: scripts/copilot_hooks/session_start_imp.py -> "copilot_orchestration"` |
| `c_pkg_4.stop_shim` | Stop guard shim delegates to package | wiring | repo-local `stop_handover_guard.py` acts as entry shim | stop guard repo-local script imports from `copilot_orchestration` rather than owning the implementation | `contains_text: scripts/copilot_hooks/stop_handover_guard.py -> "copilot_orchestration"` |

**Tests:**
- Basic shim-to-package invocation checks.
- No expectation that the old ad hoc test suite is preserved as a migration anchor.

**Success Criteria:**
- Repo-local hook scripts are reduced to adapter/entry responsibilities.
- VS Code wiring can continue to call the same script paths.
- The distinction between package-owned logic and repo-owned entrypoints is visible in code layout.

## Cycle 5 — C_PKG.5 Closure And Deferrals

**Goal:** Close the first migration run without overstating its architectural completeness and record exactly what was intentionally deferred to v2.

### Deliverables

| id | title | type | artifact | done_when | validates |
|---|---|---|---|---|---|
| `c_pkg_5.v1_claim_narrowed` | V1 migration claim narrowed correctly | documentation | handover and planning state seam established, not v2 complete | documentation explicitly distinguishes coarse seam migration from later refactor work | `contains_text: docs/development/issue263/copilot_orchestration_packaging_research.md -> "deeper decomposition belongs to the later refactor"` |
| `c_pkg_5.v2_deferrals_explicit` | V2 deferrals captured explicitly | documentation | deferred work list covers role/prompt separation, declarative redesign, deeper decomposition, hardening, and later test strategy | all major deferred concerns are recorded as out of scope for the first run | `contains_text: docs/development/issue263/planning.md -> "Deferrals to later v2 work are explicit"` |
| `c_pkg_5.repo_local_surfaces_preserved` | Repo-local guides and prompts remain outside package | boundary | markdown guides, prompt files, and wrappers remain repository-specific | documentation and final migration outcome preserve the package-vs-repo boundary | `contains_text: docs/development/issue263/planning.md -> "repo-specific agents/prompts/doctrine outside the package"` |

**Tests:**
- Documentation and handover verification only.

**Success Criteria:**
- Deferrals to later v2 work are explicit: stricter role/prompt separation, declarative contract design, deeper decomposition, stronger architectural hardening, and future test strategy.
- Stop-hook sub-role expansion from steps 3-4 of `design_v2_sub_role_orchestration.md` and slash-prompt restructuring from steps 5-6 of that same design are outside the current C_PKG cycles and require a separate future issue.
- The migration claim is truthful: seam established, not v2 completed.
- Planning stays aligned with the coarse-grained scope of the first run.

---

## Risks & Mitigation

- **Risk:** Scope drift into `mcp_server` or ST3/backend migration
  - **Mitigation:** Keep the package decision explicit in planning, research, and implementation handover; reject unrelated path moves.
- **Risk:** Premature decomposition into final v2 submodules during relocation
  - **Mitigation:** Treat `src/copilot_orchestration/hooks/` as the minimal acceptable V1 package fill and defer deeper splits unless a small technical extraction is unavoidable.
- **Risk:** Existing weak orchestration tests distort the migration scope
  - **Mitigation:** Treat the current tests as disposable for the first run and avoid rebuilding test structure as a migration prerequisite.
- **Risk:** Package-owned Python logic and repo-specific role/prompt surfaces remain blurred
  - **Mitigation:** Keep markdown guides, prompts, and wrapper files explicitly outside the package boundary and document that they remain repository-specific.

---

## Milestones

- Package boundary decision frozen for `copilot_orchestration` only
- Minimal V1 package fill under `src/copilot_orchestration/hooks/` agreed
- Thin shim strategy for `scripts/copilot_hooks/*.py` documented
- Deferrals to v2 refactor captured explicitly in the handover

## Related Documentation
- **[docs/development/issue263/research.md][related-1]**
- **[docs/development/issue263/copilot_orchestration_packaging_research.md][related-2]**
- **[docs/development/issue263/design.md][related-3]**
- **[docs/development/issue263/design_v2_sub_role_orchestration.md][related-4]**

<!-- Link definitions -->

[related-1]: docs/development/issue263/research.md
[related-2]: docs/development/issue263/copilot_orchestration_packaging_research.md
[related-3]: docs/development/issue263/design.md
[related-4]: docs/development/issue263/design_v2_sub_role_orchestration.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-03-18 | Agent | Added concrete deliverables per cycle for save_planning_deliverables input |
| 1.0 | 2026-03-18 | Agent | Initial draft |

<!-- docs\development\issue263\planning.md -->
<!-- template=planning version=130ac5ea created=2026-03-21T10:08Z updated= -->
# V2 Sub-Role Orchestration — Implementation Planning

**Status:** DRAFT  
**Version:** 1.1  
**Last Updated:** 2026-03-21

---

## Purpose

Provide a human-readable, cycle-by-cycle breakdown of the v2 implementation work so the team knows what to build, in what order, and what constitutes done for each deliverable. This document is the authoritative source for the planning deliverables that will be registered in .st3/projects.json.

## Scope

**In Scope:**
New copilot_orchestration submodules (contracts/, config/, utils/); hook entry-point implementations (detect_sub_role.py, notify_compaction.py); stop_handover_guard.py DI refactor; agent file updates (.github/agents/imp.agent.md, .github/agents/qa.agent.md, imp_agent.md, qa_agent.md); .vscode/settings.json; .copilot/sub-role-requirements.yaml; v1 test deletion (C_V2.0 prerequisite).

**Out of Scope:**
MCP server changes; .st3 schema changes; prompt body content (deferred to the **documentation phase** — bodies written after enforcement machinery is tested and smoke-tested, per design §15 OQ-1; trigger: C_V2.5 tests pass + C_V2.4 smoke test confirmed); package extraction to own git repository (deferred per design §15 OQ-2); Gap D content validation extension point; any changes to scripts/copilot_hooks/ (existing hooks untouched in v2).

## Prerequisites

Read these first:
1. design_v2_sub_role_orchestration.md v2.9 reviewed and approved
2. research.md §10.10 target package structure confirmed
3. src/copilot_orchestration/hooks/ namespace already exists (v1)
4. stop_handover_guard.py already in place (will be refactored, not replaced)
5. pre_compact_agent.py already in both agent files' PreCompact arrays (will not be moved)
---

## Summary

Break down the v2 sub-role orchestration design (issue #263, design v2.9) into 8 independently executable cycles. Covers the new copilot_orchestration package structure (contracts/, config/, utils/ submodules), hook entry-point refactor, stop_handover_guard DI migration, agent file wiring, and YAML config. All cycles follow RED → GREEN → REFACTOR. Planning deliverables map 1:1 to the Files to Create / Files to Modify tables in design §13.

---

## Dependencies

- C_V2.0 must complete before any TDD cycle begins (v1 tests will conflict with v2 implementations)
- C_V2.1 (_paths.py) must complete before C_V2.4 and C_V2.6 (both import find_workspace_root)
- C_V2.2 (interfaces.py) must complete before C_V2.3 (loader implements Protocol) and C_V2.4 (detect_sub_role uses SessionSubRoleState)
- C_V2.3 (loader) must complete before C_V2.4 (detect_sub_role receives ISubRoleRequirementsLoader) and C_V2.5 (stop_handover_guard DI)
- C_V2.4 (detect_sub_role) and C_V2.5 (stop_handover_guard) are independent of each other — can run in parallel
- C_V2.6 (notify_compaction) depends on C_V2.1 only — can run after C_V2.1 regardless of C_V2.3–C_V2.5
- C_V2.7 (agent wires) depends on C_V2.3 (YAML config must exist before frontmatter references hooks) and C_V2.4 (hook must exist before being referenced in frontmatter)

---

## TDD Cycles


### C_V2.0 — Pre-TDD: V1 Technical Debt Cleanup *(prerequisite — no new code)*

**Goal:** Delete the two v1 test files that test internals which will not exist after the v2 refactor:
- `tests/mcp_server/unit/utils/test_stop_handover_guard.py`
- `tests/mcp_server/unit/utils/test_pre_compact_agent.py`

Both files test `ROLE_REQUIREMENTS` and `parse_transcript_content` — neither exists in v2. Keeping them creates false-green tests that would mask correct v2 implementation failures.

**Tests:** None. This is a deletion step, not a TDD cycle.

**Success Criteria:** Both files gone. No other test files touched. Confirmed via `git status`. Design ref: §13 Prerequisites, research §10.9.

---

### C_V2.1 — Package Scaffold + Path Utilities

**Goal:** Create the package skeleton and implement `copilot_orchestration/utils/_paths.py`. This is the foundation all subsequent cycles depend on.

New files:
- `src/copilot_orchestration/contracts/__init__.py`
- `src/copilot_orchestration/config/__init__.py`
- `src/copilot_orchestration/utils/__init__.py`
- `src/copilot_orchestration/utils/_paths.py` — `find_workspace_root(anchor: Path) -> Path` + `STATE_RELPATH`
- `tests/copilot_orchestration/__init__.py`
- `tests/copilot_orchestration/unit/__init__.py`
- `tests/copilot_orchestration/unit/utils/__init__.py`
- `tests/copilot_orchestration/unit/utils/test_paths.py`

Existing (verify, do not overwrite):
- `src/copilot_orchestration/__init__.py` *(already present from v1 — verify content, do not overwrite)*

`find_workspace_root` walks upward from anchor until `pyproject.toml` or `.git` is found; raises `RuntimeError` with descriptive message if neither is found. `STATE_RELPATH = Path(".copilot/session-sub-role.json")`.

**Tests:** `test_paths.py` — correct resolution from arbitrary depth, `RuntimeError` on missing sentinel, `STATE_RELPATH` value.

**Success Criteria:** `find_workspace_root(Path(__file__))` resolves to workspace root from any depth within the repo. `RuntimeError` raised correctly. No magic depth numbers anywhere. All tests pass. Design ref: §9.8.

---

### C_V2.2 — Contracts: ISubRoleRequirementsLoader Protocol + TypedDicts

**Goal:** Implement `copilot_orchestration/contracts/interfaces.py`. Pure type definitions — zero runtime I/O. Also create namespace `__init__.py` for `tests/.../unit/hooks/` and `tests/.../unit/config/`.

New files:
- `src/copilot_orchestration/contracts/interfaces.py`
- `tests/copilot_orchestration/unit/hooks/__init__.py` *(empty)*
- `tests/copilot_orchestration/unit/config/__init__.py` *(empty)*

`ISubRoleRequirementsLoader` Protocol: `valid_sub_roles(role) -> frozenset[str]`, `default_sub_role(role) -> str`, `requires_crosschat_block(role, sub_role) -> bool`, `get_requirement(role, sub_role) -> SubRoleSpec`. `SubRoleSpec` TypedDict: `requires_crosschat_block`, `heading`, `block_prefix`, `guide_line`, `markers`. `SessionSubRoleState` TypedDict: `session_id`, `role`, `sub_role`, `detected_at`.

**Tests:** Structural tests — a minimal in-memory class must satisfy Protocol; TypedDicts must reject wrong key types.

**Success Criteria:** Protocol compliance verified. TypedDict shapes correct. No logic in contracts layer. Tests pass. Design ref: §9.2, §9.5.

---

### C_V2.3 — Config: SubRoleRequirementsLoader + YAML Config Files

**Goal:** Implement `SubRoleRequirementsLoader` and both YAML config files (package default + project-level).

New files:
- `src/copilot_orchestration/config/requirements_loader.py` — `SubRoleRequirementsLoader(requirements_path: Path)`
- `src/copilot_orchestration/config/_default_requirements.yaml` — package fallback covering all 11 sub-roles
- `.copilot/sub-role-requirements.yaml` — project-level override (same schema)
- `tests/copilot_orchestration/unit/config/test_requirements_loader.py`

Loader: reads YAML, validates via Pydantic, caches result. `from_copilot_dir(workspace_root)` factory resolves project YAML first; falls back to package `_default_requirements.yaml`; raises `FileNotFoundError` if neither exists. Unknown `(role, sub_role)` → `ConfigError`. `valid_sub_roles('imp')` returns frozenset of 6; `valid_sub_roles('qa')` returns frozenset of 5. YAML covers all 11 sub-roles with correct `requires_crosschat_block` flags and marker lists per design §6.1 and §6.2.

**Tests:** Loader tests with fixture YAML (temp file) — Fail-Fast behaviour, fallback chain, unknown sub-role error, frozenset contents, marker retrieval. No module-level state patching.

**Success Criteria:** Pydantic catches malformed YAML. `FileNotFoundError` raised when neither config found. All tests pass. Design ref: §9.2, §9.3, §6.1, §6.2.

---

### C_V2.4 — Hook: detect_sub_role.py (UserPromptSubmit adapter)

**Goal:** Implement `copilot_orchestration/hooks/detect_sub_role.py` with a pure query function and a `__main__` block that owns all I/O.

New files:
- `src/copilot_orchestration/hooks/detect_sub_role.py`
- `tests/copilot_orchestration/unit/hooks/test_detect_sub_role.py`

`detect_sub_role(prompt, loader, role) -> str` — pure query, no filesystem calls. Step 1: regex on `loader.valid_sub_roles(role)` candidates (case-insensitive). Step 2: `difflib.get_close_matches` on words ≥7 chars, cutoff 0.85. Default: `loader.default_sub_role(role)`.

`__main__` block: reads `sys.argv[1]` (role), stdin JSON (`prompt`, `sessionId`); idempotency check (reads state file, if `session_id` matches → `sys.exit(0)`); calls `detect_sub_role()`; writes `SessionSubRoleState` via `find_workspace_root(Path(__file__)) + STATE_RELPATH`.

**Tests:** Unit tests for pure query only (exact match, case-insensitive, difflib typo, default). Idempotency test via mocked `Path.write_text`. Pure query tested without any filesystem interaction.

**Success Criteria:** Pure query fully unit-tested without filesystem. Idempotency verified. `detect_sub_role()` has no pathlib imports at call time — `__main__` block is sole I/O owner. Tests pass. Design ref: §9.1, §9.6.

---

### C_V2.5 — Hook: stop_handover_guard.py DI Refactor

**Goal:** Refactor existing `stop_handover_guard.py` — remove `ROLE_REQUIREMENTS` dict and transcript parsing; inject `ISubRoleRequirementsLoader` via DI; read sub-role from state file with stale detection.

Modified files:
- `src/copilot_orchestration/hooks/stop_handover_guard.py` *(existing — refactored)*

New files:
- `tests/copilot_orchestration/unit/hooks/test_stop_handover_guard.py` *(v2 tests)*

Pass-through for `requires_crosschat_block=False`. Enforce markers for `requires_crosschat_block=True`. Stale detection per §9.5: `FileNotFoundError` and `JSONDecodeError` → default; `session_id` mismatch → default. Default always routes to strictest enforcement (`implementer`/`verifier`).

**Tests:** ~12 behavior-condition cases using loader fixture. Test categories: pass-through (8 sub-roles); block enforcement (implementer, validator, verifier); missing/stale state → default → enforcement. No sub-role name literals in test code.

**Success Criteria:** All behavior-condition cases pass. No `ROLE_REQUIREMENTS` dict exists anywhere in the file. Tests use loader fixture — no inline dicts. Tests pass. Design ref: §9.3, §9.4, §9.5.

---

### C_V2.6 — Hook: notify_compaction.py (PreCompact adapter)

**Goal:** Implement `copilot_orchestration/hooks/notify_compaction.py` as a thin `__main__`-only adapter.

New files:
- `src/copilot_orchestration/hooks/notify_compaction.py`

Reads stdin JSON (`sessionId`). Resolves state path via `find_workspace_root(Path(__file__)) + STATE_RELPATH`. If state file exists and `session_id` matches → outputs `{"systemMessage": "Context was compacted. Your active sub-role is **X**. Use /resume-work to restore full behavioral context before continuing."}`. If mismatch or file absent → outputs `{}`. Always exits 0 (soft failure — hook errors must not break the agent session). No unit test file — it is a thin adapter; coverage provided by C_V2.1 and C_V2.4.

**Tests:** Manual smoke test: `echo '{"sessionId": "x", "trigger": "auto"}' | python copilot_orchestration/hooks/notify_compaction.py` → verify `{}` output when no state file present.

**Success Criteria:** Imports `find_workspace_root` and `STATE_RELPATH` from `utils._paths` — no inline path definitions. Correct JSON output for matching session_id. Exits 0 in all cases. Smoke test passes. Design ref: §9.7.

---

### C_V2.7 — Agent Wires: .agent.md + Role Guide Updates + VS Code Settings

**Goal:** Update all agent configuration files, role guides, and VS Code settings. This is a configuration and documentation cycle — no TDD. Verification is by manual inspection.

Modified files:
- `.github/agents/imp.agent.md` — add `UserPromptSubmit` hook + append `notify_compaction.py` to `PreCompact` + update argument-hint
- `.github/agents/qa.agent.md` — same pattern with `qa` arg
- `imp_agent.md` — add sub-role definitions + output format expectations (§5.1)
- `qa_agent.md` — add sub-role definitions (§5.2)
- `.vscode/settings.json` — add `"chat.useCustomAgentHooks": true`
- `.github/prompts/*.prompt.md` — revise from 7 → 6 prompts (research §10.7):
  - Rename `start-implementation.prompt.md` → `start-work.prompt.md` + add sub-role list to argument-hint
  - Rename `resume-implementation.prompt.md` → `resume-work.prompt.md` + add state-file recovery step
  - `prepare-handover.prompt.md` — keep name; update markers to reference requirements file
  - Rename `request-qa-review.prompt.md` → `request-review.prompt.md` + add sub-role context to startup protocol
  - `prepare-implementation-brief.prompt.md` — keep name; add sub-role context (implementer/validator)
  - `prepare-qa-brief.prompt.md` — keep name; add sub-role context (verifier)
  - Delete `plan-executionDirectiveBatchCoordination.prompt.md` (outside orchestration scope)

Hook config: `UserPromptSubmit` command for `imp.agent.md`: `"python copilot_orchestration/hooks/detect_sub_role.py imp"`. For `qa.agent.md`: same with `qa` argument. `PreCompact` array: `pre_compact_agent.py` remains first (existing position preserved); `notify_compaction.py` appended second. Argument-hints updated with full sub-role name lists.

**Tests:** None (configuration). Verification: YAML frontmatter is syntactically valid; `pre_compact_agent.py` remains first in `PreCompact`; no existing hook entries removed.

**Success Criteria:** Both agent files have correct YAML. `settings.json` has required setting. Role guides contain sub-role tables matching design §5. Prompt set reduced to 6: `start-work.prompt.md`, `resume-work.prompt.md`, `prepare-handover.prompt.md`, `request-review.prompt.md`, `prepare-implementation-brief.prompt.md`, `prepare-qa-brief.prompt.md` all present; `plan-executionDirectiveBatchCoordination.prompt.md` absent; `start-implementation.prompt.md` and `resume-implementation.prompt.md` absent (renamed). Manual hook invocation verifiable. Design ref: §8, §9.6, §9.7, §5.1, §5.2, research §10.7.


---

## Risks & Mitigation

- **Risk:** VS Code 1.112 injects `session_id` into hook stdin — fallback if absent.
  - **Mitigation:** C_V2.4 uses `detected_at` timestamp window as fallback when `session_id` key absent; graceful re-detection via empty string non-match. Tests cover both code paths.
- **Risk:** Pydantic v2 compatibility — `model_config` syntax differs from Pydantic v1.
  - **Mitigation:** C_V2.3 unit tests catch incompatibility immediately. Constraint: `pydantic >= 2.0` documented in `pyproject.toml`.
- **Risk:** Existing callers of `stop_handover_guard.py` silently rely on the `ROLE_REQUIREMENTS` dict.
  - **Mitigation:** Before starting C_V2.5: run `grep -r "ROLE_REQUIREMENTS" .` to detect all callers. Update any caller within the same cycle commit — no silent breakage permitted.
- **Risk:** `pre_compact_agent.py` and `notify_compaction.py` ordering contract violated in `PreCompact` array.
  - **Mitigation:** C_V2.7 enforces `pre_compact_agent.py` as first entry in the array. Ordering contract documented in design §9.7 and §13. Verified by manual YAML inspection after edit.

---

## Milestones

- M1 — Foundation ready (C_V2.0 + C_V2.1 + C_V2.2): package skeleton created, path utilities tested, contracts defined. All subsequent cycles can build on this.
- M2 — Enforcement machinery complete (C_V2.3 + C_V2.4 + C_V2.5): loader, detection, and guard all tested with DI. Hook stack is functionally complete.
- M3 — Hook stack connected (C_V2.6 + C_V2.7): PreCompact adapter live, all agent files wired, VS Code settings enabled. End-to-end hook flow can be manually verified.

## Related Documentation
- **[docs/development/issue263/design_v2_sub_role_orchestration.md (v2.9) — authoritative design][related-1]**
- **[docs/development/issue263/research.md §10.8–§10.10 — coding standards review + target package structure][related-2]**
- **[docs/coding_standards/ARCHITECTURE_PRINCIPLES.md — binding standards (SRP, DIP, Fail-Fast, Config-First, DI)][related-3]**

<!-- Link definitions -->

[related-1]: docs/development/issue263/design_v2_sub_role_orchestration.md (v2.9) — authoritative design
[related-2]: docs/development/issue263/research.md §10.8–§10.10 — coding standards review + target package structure
[related-3]: docs/coding_standards/ARCHITECTURE_PRINCIPLES.md — binding standards (SRP, DIP, Fail-Fast, Config-First, DI)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-03-21 | Agent | OQ-1 fase-eigenaar: documentation phase expliciet benoemd in Out of Scope. C_V2.7: prompt renames (7→6) toegevoegd aan Modified files + Success Criteria. C_V2.1: src/copilot_orchestration/__init__.py gecorrigeerd (bestaat al, v1). |
| 1.0 | 2026-03-21 | Agent | Initial draft |
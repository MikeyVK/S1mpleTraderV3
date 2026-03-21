<!-- docs\development\issue263\planning_sub_role_detection_v2.md -->
<!-- template=planning version=130ac5ea created=2026-03-21T21:26Z updated= -->
# Sub-Role Detection V2 — Bug-Fix Planning (C_V2.8–C_V2.11)

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-21

---

## Scope

**In Scope:**
_paths.py, detect_sub_role.py, stop_handover_guard.py, test_detect_sub_role.py, test_stop_handover_guard.py, integration smoke tests

**Out of Scope:**
Prompt body rewrites, acceptance tests (C_V2.7), reference documentation updates, sub-role-requirements.yaml schema changes

## Prerequisites

Read these first:
1. Research doc approved (research_sub_role_detection_v2.md, commit bdb0c49)
2. 63/63 tests green on branch feature/263-vscode-implementation-orchestration
3. Phase transitioned: research → planning
---

## Summary

Four TDD cycles to fix three confirmed bugs in the copilot orchestration hook system: (1) role-scoped state files replacing shared STATE_RELPATH, (2) first-word detection with slash-command prefix stripping replacing the broken idempotency lock, (3) exploration mode pass-through and ConfigError catch in the stop hook, and (4) test updates covering all new behaviours. The existing 63 tests remain green throughout.

---

## TDD Cycles

### C_V2.8 — `_paths.py`: Role-scoped state files

**Goal:**
Remove the shared `STATE_RELPATH` constant and replace it with `state_path_for_role(role: str) -> Path` that returns `.copilot/session-sub-role-{role}.json`. Update all callers. Root cause fix for Bug 2 (imp reads qa state file → `ConfigError` crash).

**Deliverables:**
- D8.1 — `state_path_for_role` exported from `_paths.py`
- D8.2 — `STATE_RELPATH` absent from `_paths.py`

**Tests:**
- Update `test_paths.py`: `state_path_for_role('imp')` returns `Path('.copilot/session-sub-role-imp.json')`, `state_path_for_role('qa')` returns `Path('.copilot/session-sub-role-qa.json')`
- Verify `STATE_RELPATH` import absent from all callers

**Success Criteria:**
`grep` finds no `STATE_RELPATH` in `src/`; `state_path_for_role('imp')` returns correct path; `test_paths.py` updated and green; full suite green.

---

### C_V2.9 — `detect_sub_role.py`: First-word detection + slash-strip

**Goal:**
Replace the broken idempotency lock (`session_id == session_id → sys.exit(0)`) with first-word extraction after stripping the `/command\s*` prefix. New file behaviour:
- No file + no match → do nothing (exploration mode)
- No file + match → write role-scoped file
- File exists + match → overwrite (allows mid-session sub-role change, fixes Bug 3)
- File exists + no match → preserve existing

`sessionId` written for audit only, never used for decisions. Fixes Bug 1 and Bug 3.

**Deliverables:**
- D9.1 — slash-strip regex `^/\S+\s*` present in `detect_sub_role.py`
- D9.2 — idempotency `sys.exit(0)` absent from `detect_sub_role.py`
- D9.3 — role-scoped path (`session-sub-role-{role}.json`) referenced in `detect_sub_role.py` or `_paths.py`

**Tests:**
- Slash-prefix stripped before first-word extraction: `/start-work implementer` → first word is `implementer`
- First-word-only: `implementer: do something` → `implementer`
- Exploration mode: no file + no match → no write, exit 0
- Role-scoped file written on match, overwritten on subsequent match

**Success Criteria:**
Slash-prefix, first-word-only, and exploration-mode tests pass; sessionId absence does not change behaviour; full suite green.

---

### C_V2.10 — `stop_handover_guard.py`: Exploration mode + ConfigError guard

**Goal:**
Two targeted fixes:
1. Read role-scoped file (not shared); no file → explicit pass-through (exploration mode, no enforcement)
2. Wrap `get_requirement()` call in `try/except ConfigError` → explicit pass-through instead of unhandled exception crash

Remove `session_id` comparison from `read_sub_role`. Fixes Bug 2 crash and aligns with the Bug 1/3 design.

**Deliverables:**
- D10.1 — `ConfigError` caught in `evaluate_stop_hook` in `stop_handover_guard.py`
- D10.2 — exploration mode (no file) returns pass JSON without exception; `default_sub_role` fallback absent
- D10.3 — `session_id` comparison absent from `read_sub_role`

**Tests:**
- Exploration mode: missing role-scoped file → hook returns pass-through JSON, exit 0
- ConfigError injection: loader raises `ConfigError` → hook returns pass-through JSON, exit 0
- Both tests use injected loader fixture (no filesystem dependency)

**Success Criteria:**
Exploration-mode and ConfigError tests pass; stale-session tests removed; full suite green.

---

### C_V2.11 — Test updates: slash-strip, exploration mode, integration smoke

**Goal:**
Update both unit test files and add integration smoke tests to cover all new code paths introduced in C_V2.8–C_V2.10.

**Deliverables:**
- D11.1 — slash-prefix test present in `test_detect_sub_role.py`
- D11.2 — exploration mode test present in `test_stop_handover_guard.py`
- D11.3 — integration smoke tests cover both role-scoped files (imp + qa) in `tests/copilot_orchestration/integration/test_hooks_smoke.py`

**Tests:**
- `test_detect_sub_role.py`: slash-prefix strip cases, first-word-only cases, role-scoped file write verification
- `test_stop_handover_guard.py`: exploration-mode cases, ConfigError injection, stale-session tests rewritten or removed
- Integration smoke: end-to-end write + read for `session-sub-role-imp.json` and `session-sub-role-qa.json`

**Success Criteria:**
All 63+ tests pass; no test references `STATE_RELPATH` or `session_id`-based branching; coverage for all new code paths >= pre-existing baseline.


## Related Documentation
- **[docs/development/issue263/research_sub_role_detection_v2.md][related-1]**

<!-- Link definitions -->

[related-1]: docs/development/issue263/research_sub_role_detection_v2.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |
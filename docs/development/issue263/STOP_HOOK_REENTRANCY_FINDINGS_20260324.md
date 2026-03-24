<!-- c:\temp\st3\docs\development\issue263\STOP_HOOK_REENTRANCY_FINDINGS_20260324.md -->
<!-- template=research version=8b7bb3ab created=2026-03-24T08:46Z updated=2026-03-24 -->
# Issue #263 Stop Hook Reentrancy Findings

**Status:** FINAL  
**Version:** 1.1  
**Last Updated:** 2026-03-24

---

## Problem Statement

Determine whether the VS Code Stop hook can be used as a re-entrant multi-retry mechanism and capture any runtime findings uncovered during live testing.

## Research Goals

- Document the live validation results for Stop hook reentrancy.
- Record the confirmed snake_case versus camelCase payload mismatch discovered during testing.
- Capture implications for future orchestration design outside Stop re-entry.

---

## Finding 1 — snake_case vs. camelCase payload mismatch (CRITICAL)

**File:** `src/copilot_orchestration/hooks/stop_handover_guard.py`, line 87  
**Code:**
```python
def is_stop_retry_active(event: JsonObject) -> bool:
    value = event.get("stop_hook_active")   # ← snake_case
    ...
```

**VS Code actual payload key:** `stopHookActive` (camelCase)

VS Code sets the re-entry flag in camelCase (`stopHookActive: true`) when the model is in a Stop-hook retry cycle. The implementation reads `stop_hook_active` (snake_case), which is never present in the real payload. `event.get("stop_hook_active")` therefore always returns `None`, and `is_stop_retry_active()` always returns `False`.

**Evidence from `orchestration.log`:**  
Every Stop hook invocation — including retries — logs:
```
DEBUG stop hook: stop_hook_active=False
```
The value is never `True` under live VS Code execution, confirming the key is never found.

**Consequence:**  
The re-entry guard is completely inoperative under VS Code. Every Stop hook call is treated as a fresh invocation. The hook either always blocks (when a `requires_crosschat_block` sub-role is active) or always passes through (when no state file is present). It can never differentiate between a first call and a retry call.

**Tests affected:**  
The unit and smoke tests exercise the happy-path logic using `{"stop_hook_active": True}` as a test fixture. These tests pass, but they test behavior that is unreachable in production — VS Code never sends this key. The tests do not cover the camelCase key name.

---

## Finding 2 — Reentrancy mechanism is architecturally broken regardless of key name

Even if the key name mismatch were corrected (`stopHookActive`), the retry counter approach carries a second fundamental problem:

VS Code's documented behavior for hooks is:
1. Hook returns `"decision": "block"` → VS Code sends one correction prompt
2. On retry VS Code sets `stopHookActive: true`
3. Hook **must** return `{}` to prevent an infinite loop
4. The model gets **exactly one** retry opportunity; after that, the chat is closed

There is **no VS Code documentation** confirming that a hook can return `"decision": "block"` a second time when `stopHookActive` is already `true`. Empirical live tests on 2026-03-23 and 2026-03-24 show the hook never reaches this branch (due to Finding 1 above), so behavior in scenario (b) — hook blocks on retry — remains **unverified**.

**Previous analysis** (SESSIE_OVERDRACHT_20260323_STOP_HOOK_ANALYSE.md, Strategie 3) classified this as "CONCERN: Geblokkeerd tot handmatige test."

---

## Conclusion: Stop hook reentrancy is not a viable design strategy

The retry counter mechanism (`stop_count_test.json`, POC code on `feature/263`) is **rejected** for the following reasons:

| Reason | Detail |
|--------|--------|
| **Key mismatch** | `stop_hook_active` (snake_case) never matches the real VS Code key `stopHookActive` (camelCase) |
| **Unverified VS Code behavior** | No documentation or empirical evidence that VS Code honors a second `block` when `stopHookActive=true` is already set |
| **State management cost** | Requires persistent counter file, reset logic, and race-condition handling across subprocess invocations |
| **Test breakage** | POC counter logic broke 10 unit tests + 4 smoke tests on the feature branch |
| **Wrong layer** | Model compliance enforcement belongs in the prompt (UserPromptSubmit systemMessage), not in a mechanical retry loop |

**Recommended architecture** (from SESSIE_OVERDRACHT_20260323_STOP_HOOK_ANALYSE.md):

| Priority | Approach | Status |
|----------|----------|--------|
| 1 | Front-loading via `UserPromptSubmit` systemMessage | **Implement** |
| 2 | Reason text optimisation in `build_stop_reason()` | **Implement** |
| 3 | Retry counter | **Rejected** |

The stop hook's correct role is a single-shot enforcement gate: block once, provide a clear handover template, and rely on the model prompt (strategy 1) for compliance. Re-entry is not needed and not safe.

---

## Action Items

| # | Action | Owner |
|---|--------|-------|
| A1 | Rename `is_stop_retry_active` key to `stopHookActive` (camelCase) to match VS Code spec — or remove the guard and replace with front-load approach | @imp |
| A2 | Update unit/smoke tests to use `stopHookActive` as the payload key if A1 corrects the mismatch | @imp |
| A3 | Implement `UserPromptSubmit` systemMessage injection in `detect_sub_role.py` (strategy 1) | @imp |
| A4 | Optimise `build_stop_reason()` assertion text (strategy 2) | @imp |

---

## Related Documentation

- [SESSIE_OVERDRACHT_20260323_STOP_HOOK_ANALYSE.md](SESSIE_OVERDRACHT_20260323_STOP_HOOK_ANALYSE.md) — drie-vlaks verbetervoorstel + eindoordeel
- [src/copilot_orchestration/hooks/stop_handover_guard.py](../../../src/copilot_orchestration/hooks/stop_handover_guard.py)
- [tests/copilot_orchestration/unit/hooks/test_stop_handover_guard.py](../../../tests/copilot_orchestration/unit/hooks/test_stop_handover_guard.py)
- [tests/copilot_orchestration/integration/test_stop_handover_guard_smoke.py](../../../tests/copilot_orchestration/integration/test_stop_handover_guard_smoke.py)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-24 | Agent | Initial scaffold (empty) |
| 1.1 | 2026-03-24 | Agent | Full findings: camelCase/snake_case mismatch, reentrancy rejection, action items |

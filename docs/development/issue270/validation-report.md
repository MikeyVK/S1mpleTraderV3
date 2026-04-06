# Issue #270 — Validation Report

**Branch:** `refactor/270-remove-dead-config-fields`  
**Date:** 2026-04-06  
**Scope:** YAML-only removal of confirmed-dead config fields + 1 test fix

---

## Test Results

**Full test suite:** `2659 passed, 12 skipped, 2 xfailed, 0 failed`

Targeted:
- `tests/mcp_server/config/test_operation_policies.py` — 15/15 passed  
- `tests/mcp_server/` — 2158/2158 passed  
- `tests/` (full suite) — 2659/2659 passed

---

## Quality Gates

**Files changed:** `test_operation_policies.py`, `workphases.yaml`, `policies.yaml`, `research.md`  

| Gate | Status |
|------|--------|
| Gate 0: Ruff Format | ✅ passed |
| Gate 1: Ruff Strict Lint | ✅ passed |
| Gate 2: Imports | ✅ passed |
| Gate 3: Line Length | ✅ passed |
| Gate 4b: Pyright | ✅ passed |

---

## Scope Verification

| Change | Expected | Actual |
|--------|----------|--------|
| `exit_requires` removed from `workphases.yaml` (research, planning) | ✅ removed | ✅ confirmed |
| `entry_expects` removed from `workphases.yaml` (implementation) | ✅ removed | ✅ confirmed |
| `allowed_prefixes` removed from `policies.yaml` (commit) | ✅ removed | ✅ confirmed |
| Subphase whitelists NOT touched | ✅ intact | ✅ confirmed |
| `require_tdd_prefix` NOT touched | ✅ intact | ✅ confirmed |
| Python schema fields NOT touched | ✅ intact | ✅ confirmed |
| `test_operation_policies.py` lines 50-51 fixed | ✅ fixed | ✅ confirmed |
| `test_validate_commit_message_required` updated | ✅ fixed | ✅ confirmed |

---

## Verdict

**PASS** — All removals safe, all tests green, quality gates pass.

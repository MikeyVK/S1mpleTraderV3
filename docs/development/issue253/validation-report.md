<!-- docs/development/issue253/validation-report.md -->
<!-- template=generic_doc version=43c84181 created=2026-04-26T00:00:00Z updated=2026-04-26T08:00:00Z -->
# Issue #253 - Validation Report

**Status:** APPROVED  
**Version:** 1.1  
**Last Updated:** 2026-04-26

---

## Purpose

Capture validation evidence for the run_tests reliability work before exiting the validation phase.

## Scope

**In Scope:**
Validation evidence for the run_tests fixes: summary_line synchronization, invocation-error surfacing, coverage support, coverage parsing, and thin-adapter cleanup.

**Out of Scope:**
Workflow state lost-update races and cycle/phase boundary semantics are tracked separately in issues #292 and #293 and are not part of issue #253 acceptance.

## Environment

- Branch: `fix/253-run-tests-reliability`
- Workflow phase at report finalization: `documentation` (successful exit from `validation` recorded on 2026-04-26)
- OS: Windows
- Python environment: `venv` at `c:/temp/st3/.venv`
- Python version: `3.13.7.final.0`
- Evidence run date: 2026-04-26
- Tester: GitHub Copilot (`@imp`); QA follow-up reviewed with `@qa`
- Commit SHA: not captured in the MCP-only evidence trail used for this report update

---

## Validation Inputs

| Input | Status | Evidence |
|---|---|---|
| Implementation work completed through the runner-based architecture | PASS | C1-C6 deliverables landed on the branch and the phase exited validation successfully |
| Targeted unit/integration slices available | PASS | Re-runs completed on 2026-04-26 for the C6 sweep targets |
| Full regression suite available | PASS | `run_tests(path="tests/")` completed successfully on 2026-04-26 |
| Live MCP tool path available | PASS | Runtime scenarios below were executed against the real `run_tests` MCP tool |

---

## Summary

Issue #253 is ready to leave the validation phase. The three documented run_tests gaps were addressed, the C6 cleanup criteria are now explicitly evidenced, and the real MCP tool path was validated with concrete runtime scenarios instead of relying only on unit tests.

---

## Key Changes

- Synchronized `summary_line` behavior between JSON and text output paths
- Surfaced invocation/startup failures through the tool error contract instead of returning a misleading empty success summary
- Added `coverage` support to `run_tests` for full-scope execution and fixed coverage percentage parsing for branch-coverage output
- Removed the legacy helper path and standardized the tool boundary on the injected `PytestRunner`

---

## Test Results

| Scope | Command | Result |
|---|---|---|
| Thin adapter slice | `run_tests(path="tests/mcp_server/unit/tools/test_test_tools.py")` | PASS - 18 passed |
| Runner slice | `run_tests(path="tests/mcp_server/unit/managers/test_pytest_runner.py")` | PASS - 8 passed |
| Project tool slice | `run_tests(path="tests/mcp_server/unit/tools/test_project_tools.py")` | PASS - 28 passed |
| Migrated call-site slices | `run_tests(path="tests/mcp_server/unit/tools/test_dev_tools.py tests/mcp_server/unit/integration/test_all_tools.py")` | PASS - 29 passed, 3 warnings |
| Full regression suite | `run_tests(path="tests/")` | PASS - 2876 passed, 11 skipped, 6 xfailed, 21 warnings |

---

## Quality Gate Evidence

| Scope | Command | Result |
|---|---|---|
| C6 file sweep | `run_quality_gates(scope="files", files=[...])` | GREEN - overall_pass=true; Gate 0/1/2/3/4b/4c passed; Gate 4 skipped |
| Branch sweep | `run_quality_gates(scope="branch")` | GREEN - overall_pass=true; Gate 0/1/2/3/4b/4c passed; Gate 4 skipped |

**C6 file sweep files:**
- `mcp_server/tools/test_tools.py`
- `mcp_server/managers/pytest_runner.py`
- `mcp_server/core/interfaces/__init__.py`
- `mcp_server/tools/project_tools.py`
- `mcp_server/server.py`
- `tests/mcp_server/unit/tools/test_dev_tools.py`
- `tests/mcp_server/unit/integration/test_all_tools.py`

---

## Planning Exit Criteria

| Criterion | Status | Evidence |
|---|---|---|
| Zero `_run_pytest_sync` references in the source tree | PASS | Grep over `mcp_server/**` and `tests/**` returned no source matches on 2026-04-26 |
| Zero `patch("mcp_server.tools.test_tools._run_pytest_sync")` calls | PASS | Grep over `tests/**` returned no source matches on 2026-04-26 |
| `tests/mcp_server/unit/tools/test_test_tools.py` contains exactly 18 tests, all GREEN | PASS | Grep found 18 source test definitions; targeted rerun passed 18/18 |
| All source `RunTestsTool(...)` call sites include `runner=` | PASS | Source call sites in `mcp_server/server.py`, `tests/mcp_server/unit/tools/test_dev_tools.py`, `tests/mcp_server/unit/integration/test_all_tools.py`, and `tests/mcp_server/unit/tools/test_test_tools.py` all use runner injection |
| `run_quality_gates(scope="branch")` GREEN | PASS | Branch sweep rerun on 2026-04-26 returned `overall_pass=true` |
| Full suite GREEN | PASS | `run_tests(path="tests/")` rerun on 2026-04-26 returned 2876 passed, 11 skipped, 6 xfailed, 21 warnings |

---

## Scope Verification

- Gap 1 fixed: `summary_line` now stays synchronized between JSON and human-readable text output
- Gap 2 fixed: invocation/startup failures are treated as explicit tool errors on the raw adapter path
- Gap 3 fixed: coverage is reachable through `run_tests(coverage=true, scope="full")` and the returned coverage percentage is parsed from branch-coverage output
- The legacy `_run_pytest_sync` / `_parse_pytest_output` helper layer was removed from the tool boundary

---

## Live Validation

| Scenario | Setup | Observed Result |
|---|---|---|
| Passing targeted selection | `run_tests(path="tests/mcp_server/unit/managers/test_pytest_runner.py")` | PASS - 8 tests passed through the real MCP tool path |
| No tests collected | `run_tests(path="tests/mcp_server/unit/tools/test_test_tools.py", markers="nonexistentmarker")` | `summary_line="no tests collected"`, exit code 5, and `SuggestionNote` guidance returned |
| Invalid marker / startup error path | `run_tests(path="tests/mcp_server/unit/tools/test_test_tools.py", markers="(")` | Non-success result returned as `pytest exited with returncode 3` plus `RecoveryNote` |
| Coverage-enabled full-scope run | `run_tests(scope="full", coverage=true)` | 2375 passed, 11 skipped, 6 xfailed, 21 warnings; `coverage_pct=77.0`; non-zero exit reflects coverage threshold enforcement |
| Full regression suite | `run_tests(path="tests/")` | PASS - 2876 passed, 11 skipped, 6 xfailed, 21 warnings |
| `last_failed_only` rerun | `run_tests(path="tests/mcp_server/unit/tools/test_test_tools.py", last_failed_only=true)` | Selection reran successfully, but `lf_cache_was_empty` remained false in the current rerun |

---

## Integration Verification

- `RunTestsTool` is wired to the injected `PytestRunner` in the server composition root
- Live MCP validation confirmed the production server path, not only isolated unit seams
- The migrated source call sites now consistently construct `RunTestsTool(runner=...)`

---

## Limitations & Caveats

- The LF-empty informational path is now explicitly disclosed: the 2026-04-26 documentation-phase rerun with `last_failed_only=true` did not reproduce the empty-cache `InfoNote`. No `.pytest_cache/**/lastfailed` file was present, yet pytest did not emit the specific stdout text that sets `lf_cache_was_empty=true` in the runner. This behavior remains directly covered by the source-level test `test_c4_run_tests_lf_empty_emits_info_note_when_requested`.
- Coverage validation is live-proven, but the current full-scope coverage measurement is intentionally below the configured threshold (`77.0 < 90`). The coverage-enabled run is included here as behavioral proof of the coverage path, not as a passing branch-exit gate.
- Earlier draft counts in this document have been superseded by the dated reruns above. This report now uses the 2026-04-26 evidence set consistently.

---

## Known Follow-ups / Out of Scope

- Workflow state lost-update race is tracked separately in issue #292
- Cycle-transition phase-exit gate leakage is tracked separately in issue #293
- Dedicated validation-report template follow-up is tracked in issue #294
- Issue #253 scope remains limited to run_tests correctness/completeness gaps

---

## Verdict

APPROVED - the evidence trail is now explicit and traceable: C6 success criteria are mapped one-to-one, quality-gate runs are documented with exact scopes, and the LF-empty caveat is disclosed instead of being silently omitted.

## Related Documentation
- **[docs/development/issue253/research.md][related-1]**
- **[docs/development/issue253/planning.md][related-2]**
- **[docs/development/issue253/design.md][related-3]**
- **[docs/development/issue103/planning.md][related-4]**
- **[docs/development/issue251/design.md][related-5]**

<!-- Link definitions -->

[related-1]: docs/development/issue253/research.md
[related-2]: docs/development/issue253/planning.md
[related-3]: docs/development/issue253/design.md
[related-4]: docs/development/issue103/planning.md
[related-5]: docs/development/issue251/design.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.1 | 2026-04-26 | Agent | Added environment, quality-gate evidence, planning exit criteria, live validation evidence, and explicit caveats after QA review |
| 1.0 | 2026-04-26 | Agent | Initial draft |

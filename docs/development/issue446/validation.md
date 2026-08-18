<!-- docs\development\issue446\validation.md -->
<!-- template=validation_report version=fe38a66d created=2026-08-18T15:00Z updated=2026-08-18T15:03Z -->
# Issue #446 Validation: First-Class Chore Workflow

**Status:** PRELIMINARY  
**Version:** 1.0  
**Last Updated:** 2026-08-18  
**Validation Outcome:** FAIL  
**Issue:** #446  
**Cycle:** Configuration and documentation implementation

---

## Scope

Branch-wide verification of the first-class chore workflow, legacy
`fix`/`custom` cleanup, mechanical lint repairs, and deferred quality-gate
integrity finding.

Documentation-phase deliverables are not included in this preliminary verdict;
they remain the next phase's active scope.

## Prerequisites

- [Issue #446 research][research]
- [Architecture Principles][architecture]
- [Documentation Standard][documentation-standard]
- The approved clean-break and config-driven strategy in the research artifact
- The focused implementation and regression evidence produced on this branch

## Summary Verdict

**FAIL for formal branch-wide validation.**

The chore-specific implementation and all focused regressions are green. The
workspace-wide suite was executed twice and failed once per run in different
tests from the same Windows concurrent-state fixture. Both failures were
`PermissionError` races against a temporary `.pgmcp/state.json`; isolated
reruns passed. The failures are not connected to the chore configuration
surfaces, but the full suite is not yet deterministically green and therefore
cannot be reported as PASS.

The functioning quality gates are project-wide green. Ruff strict lint is not
valid evidence because its command exits with code 2 while the runner
incorrectly classifies the gate as passed. That integrity defect is recorded as
deferred work for `@co` triage and a dedicated issue.

## Test Evidence

| Run | Result | Assessment |
|---|---|---|
| Focused repaired-surface suite | 144 passed in 7.80s | PASS |
| Full workspace run 1 | 1 failed, 2778 passed, 2 skipped, 1 xpassed, 25 warnings | FAIL |
| Failed test rerun | 1 passed in 4.78s | Non-reproducing in isolation |
| Full workspace run 2 | 1 failed, 2778 passed, 2 skipped, 1 xpassed, 25 warnings | FAIL |
| Concurrent-state test file rerun | 2 passed in 4.69s | Non-reproducing in isolation |

Full-run failures:

1. `TestSecondaryHomogeneousConcurrentWritesC4::
   test_two_concurrent_force_transitions_both_records_present`
2. `TestPrimaryMixedConcurrentWritesC4::
   test_force_transition_and_force_cycle_transition_concurrent`

Both failed with Windows `PermissionError: [Errno 13]` against a temporary
`.pgmcp/state.json`.

## Quality-Gate Evidence

The explicit ten-file rerun and the project-wide 497-file run both report:

- Ruff format: PASS
- Imports: PASS
- Line length: PASS
- Pyright: PASS with zero diagnostics
- mypy for `mcp_server`: PASS
- Ruff strict lint: **INVALID RESULT** — command exit code 2 is incorrectly
  reported as PASS

The branch-scope gate is not used as proof while the implementation remains
uncommitted because it compares committed branch state and resolves zero dirty
working-tree files.

## Deliverable and Strategy Alignment

| Boundary | Evidence | Status |
|---|---|---|
| Chore issue/workflow mapping | Config and loader/tool tests cover `chore -> chore` | PASS |
| Chore branch and enforcement | Git and enforcement config/tests expose chore and remove fix | PASS |
| Chore phase contract | Research, implementation, validation, documentation, ready; non-cycle implementation | PASS |
| Legacy fix/custom cleanup | Current config, prompts, code descriptions, tests, and current docs inventoried and corrected | PASS |
| Config-driven runtime | Existing configuration-derived schemas and managers are reused | PASS |
| YAML alias decision | No anchors, aliases, merge keys, or instruction composition added | PASS |
| Active documentation and agent sources | Current workflow references, authoritative host sources, and tracked consumers aligned; extension guide added | PASS |

The implementation preserves the Approved Strategy: the behavioral extension
is configuration-driven, archived documentation remains untouched, and no
cross-config validator or YAML composition mechanism was introduced.

## Live Demonstration Proposal

The smallest safe observable demonstration is a temporary project
initialization using `workflow_name="chore"`:

1. Load the current server configuration.
2. Initialize a disposable issue workspace with the chore workflow.
3. Observe that the workflow is accepted and begins in `research`.
4. Inspect the configured phase order:
   `research -> implementation -> validation -> documentation -> ready`.
5. Confirm that chore implementation is non-cycle-based.

Before issue #446, chore mapped to the feature workflow and no matching chore
branch type existed. Automated initialization and transition tests provide the
closest repeatable fallback evidence without mutating a real issue or branch.

## Residual Risks and Deferred Work

- The full workspace suite is not deterministically green under its parallel
  Windows execution context. The concurrent-state tests pass in isolation but
  produced two different temporary-file permission races in consecutive full
  runs. This remains visible as a validation failure until a full run passes or
  the underlying test/execution issue is triaged.
- Ruff strict-lint command syntax, `fix_command`, exit-code handling, summary
  integrity, and regression coverage are explicitly deferred in
  [deferred-work.md][deferred-work].

## Related Documentation

- [Issue #446 research][research]
- [Deferred quality-gate work][deferred-work]
- [Architecture Principles][architecture]
- [Documentation Standard][documentation-standard]

[research]: research.md
[deferred-work]: deferred-work.md
[architecture]: ../../coding_standards/ARCHITECTURE_PRINCIPLES.md
[documentation-standard]: ../../coding_standards/DOCUMENTATION_STANDARD.md

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-18 | Agent | Preliminary validation with focused, full-suite, gate, and residual-risk evidence |

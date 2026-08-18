<!-- docs\development\issue446\deferred-work.md -->
<!-- template=generic_doc version=43c84181 created=2026-08-18T14:47Z updated=2026-08-18T15:28Z -->
# Issue #446 Deferred Work for @co Triage

**Status:** PENDING  
**Version:** 1.1  
**Last Updated:** 2026-08-18

---

## Purpose

Record out-of-scope validation findings that must remain visible in the issue
#446 PR body and be triaged by `@co` after merge.

## Scope

**In Scope:**

- Dedicated follow-up for Ruff command, auto-fix, exit-code, and result-summary
  integrity.
- Triage of nondeterministic Windows permission failures in the concurrent
  state integration tests.

**Out of Scope:**

- Repairing either finding on the issue #446 branch.
- Weakening or removing workspace-wide validation requirements.

## Deferred Work Item 1: Quality-Gate Command and Result Integrity

**Owner:** `@co` triage after merge of issue #446  
**Disposition:** Create a dedicated issue; do not repair under #446.  
**Priority:** Determine during triage.

### Finding

The Ruff strict-lint gate and its configured `fix_command` pass
`--per-file-ignores=tests/**/*.py:ANN,ARG`. Ruff interprets `ARG` as another
list entry without a file pattern and exits with code 2:
`Expected <FilePattern>:<RuleCode> pattern`.

The quality runner then parses empty stdout as zero JSON violations and marks
the gate passed despite the non-zero exit. This allows an invalid command to
appear green and makes the overall and human-readable summaries misleading.

### Reason for Deferral

The finding affects quality-runner behavior rather than the first-class chore
workflow. The user explicitly directed that it be triaged and implemented
under its own issue.

### Impact or Risk

A broken lint command can be classified as successful, so the gate may provide
false confidence and the configured auto-fix path is unusable.

### Recommended Follow-up

1. Correct both the Ruff gate execution command and `fix_command` without
   weakening the intended test-file exemptions.
2. Make parsed gates fail on disallowed non-zero exit codes even when stdout is
   empty or parseable as an empty violation list.
3. Make human-readable, structured, and overall result classification
   consistent.
4. Add focused regression tests for all three behaviors.

### Acceptance Criteria

- [ ] Ruff strict-lint execution uses syntactically valid per-file ignores.
- [ ] The configured Ruff `fix_command` uses the same valid semantics.
- [ ] A disallowed non-zero exit always fails a `json_violations` gate.
- [ ] Human-readable and structured summaries agree with `overall_pass`.
- [ ] Regression tests cover invalid syntax, empty stdout, and classification.

### Evidence

- An explicit ten-file quality run passed format, imports, line length,
  Pyright, and mypy; Ruff strict lint returned exit code 2 while reported as
  passed.
- A project-wide 497-file quality run reproduced the same false-positive Ruff
  result.
- All mechanical lint and typing findings surfaced by the functioning gates
  were repaired under #446.

## Deferred Work Item 2: Concurrent State Test Permission Race

**Owner:** `@co` triage after merge of issue #446  
**Disposition:** Check for an existing tracking issue; otherwise create a
dedicated test-reliability issue.  
**Priority:** Determine during triage.

### Finding

Two consecutive full workspace runs each failed one different test in
`tests/mcp_server/integration/test_phase_state_engine_concurrent.py`. Both
failures were Windows `PermissionError: [Errno 13]` races against a temporary
`.pgmcp/state.json`.

The first failed test passed on an isolated rerun. The full test file then
passed in isolation. The test file and concurrent-state implementation were not
changed for the chore workflow.

### Reason for Deferral

The failures are outside the approved chore boundary and are not reproducible
in isolated execution. Repair requires dedicated concurrency and Windows
file-sharing analysis rather than a documentation or configuration change.

### Impact or Risk

The workspace-wide suite is nondeterministic under its parallel Windows
execution context. This can block trustworthy validation and conceal genuine
regressions among environmental failures.

### Recommended Follow-up

1. Reproduce under the full-suite parallel execution settings on Windows.
2. Inspect temporary-file replacement, locking, teardown, and xdist/process
   interaction around `.pgmcp/state.json`.
3. Determine whether production locking or only the concurrency fixture needs
   hardening.
4. Add a deterministic regression that distinguishes expected lock contention
   from unexpected filesystem permission failures.
5. Keep the ready-phase workspace test requirement; rerun until a current full
   suite is green before PR submission.

### Evidence

- Full run 1: 1 failed, 2778 passed, 2 skipped, 1 xpassed, 25 warnings.
- Failed test rerun: 1 passed.
- Full run 2: 1 different concurrent-state test failed; 2778 passed.
- Concurrent-state integration file rerun: 2 passed.

## Related Documentation

- [Issue #446 research][research]
- [Issue #446 validation][validation]
- [Quality gate configuration][quality-config]
- [Quality runner][quality-runner]

[research]: research.md
[validation]: validation.md
[quality-config]: ../../../.pgmcp/config/quality.yaml
[quality-runner]: ../../../mcp_server/managers/qa_manager.py

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-18 | Agent | Record deferred quality-gate integrity work |
| 1.1 | 2026-08-18 | Agent | Add concurrent-state test reliability triage item |

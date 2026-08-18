<!-- docs\development\issue446\deferred-work.md -->
<!-- template=generic_doc version=43c84181 created=2026-08-18T14:47Z updated=2026-08-18 -->
# Issue #446 Deferred Work for @co Triage

**Status:** PENDING  
**Version:** 1.2  
**Last Updated:** 2026-08-18

---

## Purpose

Record the remaining out-of-scope validation finding that must be included in
the issue #446 PR body and triaged by `@co` after merge.

## Scope

**In Scope:**

- Dedicated follow-up for Ruff command syntax, auto-fix behavior, exit-code
  handling, and result-summary integrity.

**Out of Scope:**

- Repairing the quality runner or Ruff configuration on the issue #446 branch.
- Weakening or removing workspace-wide validation requirements.

## Deferred Work Item: Quality-Gate Command and Result Integrity

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

- The final branch-scope 29-file quality run passed format, imports, line
  length, Pyright, and mypy.
- In that same run Ruff strict lint returned exit code 2 while the runner
  reported the gate and overall result as passed.
- A focused one-file quality run reproduced the same false-positive
  classification.
- All mechanical lint and typing findings surfaced by the functioning gates
  were repaired under #446.

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
| 1.1 | 2026-08-18 | Agent | Record initial validation follow-up findings |
| 1.2 | 2026-08-18 | Agent | Retain only the unresolved quality-gate integrity item |

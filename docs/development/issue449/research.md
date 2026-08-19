<!-- docs\development\issue449\research.md -->
<!-- template=research version=8b7bb3ab created=2026-08-19T05:53Z updated= -->
# Issue #449 — Ruff Command Validation and Quality-Gate Result Integrity

**Status:** APPROVED  
**Version:** 0.1  
**Last Updated:** 2026-08-19

---

## Purpose

Provide a lightweight, reproducible decision record for completing issue #449.

## Scope

**In Scope:**
Ruff strict-lint and fix command syntax in quality.yaml; QAManager result integrity for parsed gates and autofix; focused regression coverage; minimal workflow completion.

**Out of Scope:**
Changing the configured rule set, redesigning the quality subsystem, changing public tool DTO semantics, or addressing unrelated lint findings.

## Prerequisites

Read these first:
1. Issue #449
2. Current uncommitted changes on bug/449-fix-ruff-command-validation-quality-gate-result-integrity
---

## Problem Statement

The strict Ruff lint and autofix commands use invalid per-file-ignore CLI arguments, while parsed quality-gate results can report success despite a non-zero process exit code. This creates false-green validation and an unusable autofix path.

## Research Goals

- Determine the valid Ruff CLI syntax that exempts ANN and ARG rules only for test files.
- Verify that command failures remain failures even when stdout contains no parsed violations.
- Identify the smallest implementation and workflow steps needed to close issue #449 safely.

---

## Background

Issue #449 was split from issue #446 after validation exposed an invalid Ruff invocation and a false-green quality-gate result. A prior agent added source changes while the project remained in research.

---

## Findings

Ruff documents `--per-file-ignores` as a list of mappings from file pattern to excluded rule code. Local verification with the repository's Ruff version showed that repeated dedicated flags fail, and `tests/**/*.py:ANN,ARG` also fails because `ARG` is parsed as a new mapping without a file pattern.

The accepted form is one argument containing complete comma-separated mappings:

```text
--per-file-ignores
tests/**/*.py:ANN,tests/**/*.py:ARG
```

The exact strict-lint invocation against `tests/mcp_server/unit/managers/test_qa_manager.py` returned exit code 0 and an empty JSON result. The same argument must be used in `command` and `fix_command`.

The current `QAManager` direction is correct: parsed gates must require an allowed exit code and zero parsed violations, and non-zero exits without parsed issues must expose exit code and captured stderr. Autofix must aggregate any non-zero fixer result into `success=false`.

## Minimal Closure Plan

1. Replace the two invalid per-file-ignore sequences in `.pgmcp/config/quality.yaml` with the verified single mapping-list argument.
2. Retain the current exit-code-aware logic for both JSON and text parsing strategies.
3. Add focused regression coverage for:
   - JSON parsing with exit code 2, empty stdout, and diagnostic stderr;
   - text parsing with exit code 2 and no parsed violations;
   - autofix returning `success=false` when a fixer exits non-zero.
4. Run Ruff formatting and correct the two line-length violations introduced in `qa_manager.py`.
5. Restart the MCP server so validation exercises the changed source and configuration.
6. Run the focused manager tests, project quality gates, and the full workspace test suite.
7. Complete the remaining bug-workflow artifacts and phases. Design and planning can stay lightweight because the approved change does not alter architecture or public schemas; validation must record the exact gate and test evidence. Documentation needs only an explicit no-user-facing-doc-change conclusion unless implementation reveals a changed operator contract.

## Open Questions

- None. The clean-correction strategy was approved by the human collaborator on 2026-08-19.


---

## Approved Strategy

APPROVED 2026-08-19 — Apply a clean correction: replace the invalid Ruff arguments in both command variants without compatibility shims; retain existing public output schemas; make non-zero subprocess exits authoritative failures while preserving parsed violations and stderr diagnostics; add focused regressions for all changed paths. Human approval was provided explicitly in chat.

---

## Expected Results

Both Ruff command variants parse successfully and preserve ANN/ARG exemptions for tests; invalid tool invocations fail quality gates with exit code and stderr; failed fixers return success=false; focused tests, project quality gates, and the full workspace test suite pass before ready.

## Related Documentation
- **[https://docs.astral.sh/ruff/configuration/][related-1]**
- **[https://docs.astral.sh/ruff/settings/#lint_per-file-ignores][related-2]**

<!-- Link definitions -->

[related-1]: https://docs.astral.sh/ruff/configuration/
[related-2]: https://docs.astral.sh/ruff/settings/#lint_per-file-ignores

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-08-19 | Agent | Initial draft |
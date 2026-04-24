# Issue 283 Documentation Index

This directory contains the working documentation set for issue #283 (`refactor/283-ready-phase-enforcement`).

## Current Documents

Use these as the normative documents for the implemented `submit_pr` + PR-status enforcement model:

- [planning.md](planning.md)
  Executed planning baseline for the implemented branch.
- [design-submit-pr-prstatus-enforcement.md](design-submit-pr-prstatus-enforcement.md)
  Current design for `submit_pr`, `PRStatusCache`, and `BranchMutatingTool`.
- [research-submit-pr-impact-analysis.md](research-submit-pr-impact-analysis.md)
  Final research baseline for the submit_pr redesign.
- [research-model1-branch-tip-neutralization.md](research-model1-branch-tip-neutralization.md)
  Supporting research for artifact neutralization behavior.

## Superseded Documents

These documents describe earlier designs and should not be used as the active contract:

- [planning-ready-phase-enforcement.md](planning-ready-phase-enforcement.md)
  Earlier planning for the old ready-phase enforcement model.
- [design-ready-phase-enforcement.md](design-ready-phase-enforcement.md)
  Earlier design built around the superseded `create_pr` + exclusion-rule model.
- [research-ready-phase-enforcement.md](research-ready-phase-enforcement.md)
  Earlier research baseline before the submit_pr redesign.
- [design-git-add-commit-regression-fix.md](design-git-add-commit-regression-fix.md)
  Historical supplement for the removed `create_pr` merge-readiness path.
- [qa-handover-design-v2.md](qa-handover-design-v2.md)
  Historical QA review against the superseded ready-phase design.

## Historical Context

These files provide session-level or review-level history only:

- `SESSIE_OVERDRACHT_*.md`
- `qa-handover-*.md`

## Reading Order

1. [research-submit-pr-impact-analysis.md](research-submit-pr-impact-analysis.md)
2. [design-submit-pr-prstatus-enforcement.md](design-submit-pr-prstatus-enforcement.md)
3. [planning.md](planning.md)
4. [docs/mcp_server/architectural_diagrams/04_enforcement_layer.md](../../mcp_server/architectural_diagrams/04_enforcement_layer.md)
5. [docs/reference/mcp/tools/github.md](../../reference/mcp/tools/github.md)

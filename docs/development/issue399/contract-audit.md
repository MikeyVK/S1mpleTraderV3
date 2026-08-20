<!-- docs\development\issue399\contract-audit.md -->
<!-- template=generic_doc version=43c84181 created=2026-08-20T12:08Z updated= -->
# Issue 399 Phase Instruction Contract Audit

**Status:** DRAFT  
**Version:** 0.1  
**Last Updated:** 2026-08-20

---

## Purpose

Record contract-by-contract C01-C23 implementation evidence without creating a runtime source of truth.

## Scope

**In Scope:**
All 39 effective phase_instructions and their coupled handover_template contracts in .pgmcp/config/contracts.yaml.

**Out of Scope:**
Runtime configuration semantics, historical migration narrative, and independent QA verdicts.

## Prerequisites

Read these first:
1. docs/development/issue399/research.md
2. docs/development/issue399/planning.md
---

## Summary

Execution ledger for the 39 effective workflow phase contracts. Records remain unapproved until their implementation cycle supplies evidence.

## Recording Rules

Each effective contract is its `phase_instructions` plus coupled
`handover_template`. Complete every field from direct evidence and evaluate C01-C23
individually before accepting that rewrite. Use `N/A` only with a reason. A producer
records evidence but does not turn this ledger into an independent QA verdict.

## Baseline Metrics

Parsed from the RED commit before any runtime-contract rewrite. Block-scalar clipping
matches the YAML loader; totals reproduce the Research baseline exactly.

| Contract | Instruction chars | Hand-over chars | Effective chars | Lexical units |
|---|---:|---:|---:|---:|
| `bug/design` | 6539 | 623 | 7162 | 1256 |
| `bug/documentation` | 3072 | 591 | 3663 | 661 |
| `bug/implementation` | 4310 | 0 | 4310 | 829 |
| `bug/planning` | 7292 | 794 | 8086 | 1413 |
| `bug/ready` | 4010 | 914 | 4924 | 1000 |
| `bug/research` | 5793 | 1019 | 6812 | 1222 |
| `bug/validation` | 4143 | 874 | 5017 | 914 |
| `chore/documentation` | 1009 | 254 | 1263 | 215 |
| `chore/implementation` | 1225 | 425 | 1650 | 305 |
| `chore/ready` | 1873 | 0 | 1873 | 348 |
| `chore/research` | 951 | 264 | 1215 | 227 |
| `chore/validation` | 1710 | 504 | 2214 | 423 |
| `docs/documentation` | 3015 | 577 | 3592 | 643 |
| `docs/planning` | 4483 | 504 | 4987 | 896 |
| `docs/ready` | 4016 | 918 | 4934 | 996 |
| `epic/coordination` | 268 | 130 | 398 | 101 |
| `epic/design` | 7159 | 609 | 7768 | 1320 |
| `epic/documentation` | 3189 | 631 | 3820 | 684 |
| `epic/planning` | 5239 | 719 | 5958 | 1043 |
| `epic/ready` | 4050 | 1028 | 5078 | 1036 |
| `epic/research` | 5724 | 1029 | 6753 | 1179 |
| `feature/design` | 6440 | 569 | 7009 | 1219 |
| `feature/documentation` | 3108 | 561 | 3669 | 655 |
| `feature/implementation` | 2372 | 0 | 2372 | 576 |
| `feature/planning` | 6948 | 754 | 7702 | 1353 |
| `feature/ready` | 4001 | 914 | 4915 | 995 |
| `feature/research` | 5455 | 901 | 6356 | 1140 |
| `feature/validation` | 3837 | 850 | 4687 | 861 |
| `hotfix/documentation` | 3094 | 589 | 3683 | 660 |
| `hotfix/implementation` | 4475 | 0 | 4475 | 858 |
| `hotfix/ready` | 4008 | 914 | 4922 | 996 |
| `hotfix/validation` | 3804 | 838 | 4642 | 860 |
| `refactor/design` | 3588 | 504 | 4092 | 757 |
| `refactor/documentation` | 3119 | 600 | 3719 | 660 |
| `refactor/implementation` | 4464 | 0 | 4464 | 840 |
| `refactor/planning` | 7186 | 795 | 7981 | 1395 |
| `refactor/ready` | 4012 | 914 | 4926 | 996 |
| `refactor/research` | 5784 | 1012 | 6796 | 1207 |
| `refactor/validation` | 3900 | 897 | 4797 | 874 |
| **Total** | **158665** | **24019** | **182684** | **33613** |

## Contract Records

### C_READY

#### `feature/ready`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Package verified branch evidence, deferred work, and closure claims into a submitted pull request.
- **Workflow distinction:** N/A — C20 deliberately makes terminal behavior identical; workflow-specific meaning is supplied by prior artifacts and PR content.
- **Retained activations:** Evidence-freshness decision; final `git_status` and `git_diff_stat`; deferred-work search and @co transfer; PR scaffolding; final state commit when needed; clean-state check; `submit_pr`; outcome-neutral hand-over.
- **Removed or relocated content:** Per-workflow prose, unconditional branch gates, repeated issue curation, merge-approval checks, merge prohibitions already enforced by tooling, and producer readiness claims.
- **Test/evidence policy:** Reuse fresh Validation evidence; rerun only invalidated checks at the narrowest sufficient scope, including the workspace-wide suite only when stale or missing.
- **Document reads:** Conditional — inspect the issue, Validation evidence, and current documentation only when needed to support final claims.
- **Delegation/QA:** No delegated review. The producer supplies evidence and `Review requested`; independent QA/review authority is external to this contract.
- **Hand-over:** Canonical Scope → Deliverables → Evidence → Open Work → Review Request; includes clickable PR and repository-relative artifact link forms.
- **Agent-instruction impact:** Aligned in C_AGENT_AUTHORITY across host-authoritative AGENTS, implementation/coordination/QA roles, Codex skills, and tracked consumers.
- **Audit result:** PASS: C01,C03,C04,C07,C10,C11,C13-C20,C22,C23. N/A with reason: C02 (C20 exact equality), C05 (Research-owned), C06 (pre-draft phases), C08-C09 (no test creation), C12 (no delegation), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 4001/914/4915/995; after = 1849/520/2369/505.
- **Residual concern:** None.
#### `bug/ready`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Package verified branch evidence, deferred work, and closure claims into a submitted pull request.
- **Workflow distinction:** N/A — C20 deliberately makes terminal behavior identical; workflow-specific meaning is supplied by prior artifacts and PR content.
- **Retained activations:** Evidence-freshness decision; final `git_status` and `git_diff_stat`; deferred-work search and @co transfer; PR scaffolding; final state commit when needed; clean-state check; `submit_pr`; outcome-neutral hand-over.
- **Removed or relocated content:** Per-workflow prose, unconditional branch gates, repeated issue curation, merge-approval checks, merge prohibitions already enforced by tooling, and producer readiness claims.
- **Test/evidence policy:** Reuse fresh Validation evidence; rerun only invalidated checks at the narrowest sufficient scope, including the workspace-wide suite only when stale or missing.
- **Document reads:** Conditional — inspect the issue, Validation evidence, and current documentation only when needed to support final claims.
- **Delegation/QA:** No delegated review. The producer supplies evidence and `Review requested`; independent QA/review authority is external to this contract.
- **Hand-over:** Canonical Scope → Deliverables → Evidence → Open Work → Review Request; includes clickable PR and repository-relative artifact link forms.
- **Agent-instruction impact:** Aligned in C_AGENT_AUTHORITY across host-authoritative AGENTS, implementation/coordination/QA roles, Codex skills, and tracked consumers.
- **Audit result:** PASS: C01,C03,C04,C07,C10,C11,C13-C20,C22,C23. N/A with reason: C02 (C20 exact equality), C05 (Research-owned), C06 (pre-draft phases), C08-C09 (no test creation), C12 (no delegation), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 4010/914/4924/1000; after = 1849/520/2369/505.
- **Residual concern:** None.
#### `hotfix/ready`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Package verified branch evidence, deferred work, and closure claims into a submitted pull request.
- **Workflow distinction:** N/A — C20 deliberately makes terminal behavior identical; workflow-specific meaning is supplied by prior artifacts and PR content.
- **Retained activations:** Evidence-freshness decision; final `git_status` and `git_diff_stat`; deferred-work search and @co transfer; PR scaffolding; final state commit when needed; clean-state check; `submit_pr`; outcome-neutral hand-over.
- **Removed or relocated content:** Per-workflow prose, unconditional branch gates, repeated issue curation, merge-approval checks, merge prohibitions already enforced by tooling, and producer readiness claims.
- **Test/evidence policy:** Reuse fresh Validation evidence; rerun only invalidated checks at the narrowest sufficient scope, including the workspace-wide suite only when stale or missing.
- **Document reads:** Conditional — inspect the issue, Validation evidence, and current documentation only when needed to support final claims.
- **Delegation/QA:** No delegated review. The producer supplies evidence and `Review requested`; independent QA/review authority is external to this contract.
- **Hand-over:** Canonical Scope → Deliverables → Evidence → Open Work → Review Request; includes clickable PR and repository-relative artifact link forms.
- **Agent-instruction impact:** Aligned in C_AGENT_AUTHORITY across host-authoritative AGENTS, implementation/coordination/QA roles, Codex skills, and tracked consumers.
- **Audit result:** PASS: C01,C03,C04,C07,C10,C11,C13-C20,C22,C23. N/A with reason: C02 (C20 exact equality), C05 (Research-owned), C06 (pre-draft phases), C08-C09 (no test creation), C12 (no delegation), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 4008/914/4922/996; after = 1849/520/2369/505.
- **Residual concern:** None.
#### `refactor/ready`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Package verified branch evidence, deferred work, and closure claims into a submitted pull request.
- **Workflow distinction:** N/A — C20 deliberately makes terminal behavior identical; workflow-specific meaning is supplied by prior artifacts and PR content.
- **Retained activations:** Evidence-freshness decision; final `git_status` and `git_diff_stat`; deferred-work search and @co transfer; PR scaffolding; final state commit when needed; clean-state check; `submit_pr`; outcome-neutral hand-over.
- **Removed or relocated content:** Per-workflow prose, unconditional branch gates, repeated issue curation, merge-approval checks, merge prohibitions already enforced by tooling, and producer readiness claims.
- **Test/evidence policy:** Reuse fresh Validation evidence; rerun only invalidated checks at the narrowest sufficient scope, including the workspace-wide suite only when stale or missing.
- **Document reads:** Conditional — inspect the issue, Validation evidence, and current documentation only when needed to support final claims.
- **Delegation/QA:** No delegated review. The producer supplies evidence and `Review requested`; independent QA/review authority is external to this contract.
- **Hand-over:** Canonical Scope → Deliverables → Evidence → Open Work → Review Request; includes clickable PR and repository-relative artifact link forms.
- **Agent-instruction impact:** Aligned in C_AGENT_AUTHORITY across host-authoritative AGENTS, implementation/coordination/QA roles, Codex skills, and tracked consumers.
- **Audit result:** PASS: C01,C03,C04,C07,C10,C11,C13-C20,C22,C23. N/A with reason: C02 (C20 exact equality), C05 (Research-owned), C06 (pre-draft phases), C08-C09 (no test creation), C12 (no delegation), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 4012/914/4926/996; after = 1849/520/2369/505.
- **Residual concern:** None.
#### `docs/ready`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Package verified branch evidence, deferred work, and closure claims into a submitted pull request.
- **Workflow distinction:** N/A — C20 deliberately makes terminal behavior identical; workflow-specific meaning is supplied by prior artifacts and PR content.
- **Retained activations:** Evidence-freshness decision; final `git_status` and `git_diff_stat`; deferred-work search and @co transfer; PR scaffolding; final state commit when needed; clean-state check; `submit_pr`; outcome-neutral hand-over.
- **Removed or relocated content:** Per-workflow prose, unconditional branch gates, repeated issue curation, merge-approval checks, merge prohibitions already enforced by tooling, and producer readiness claims.
- **Test/evidence policy:** Reuse fresh Validation evidence; rerun only invalidated checks at the narrowest sufficient scope, including the workspace-wide suite only when stale or missing.
- **Document reads:** Conditional — inspect the issue, Validation evidence, and current documentation only when needed to support final claims.
- **Delegation/QA:** No delegated review. The producer supplies evidence and `Review requested`; independent QA/review authority is external to this contract.
- **Hand-over:** Canonical Scope → Deliverables → Evidence → Open Work → Review Request; includes clickable PR and repository-relative artifact link forms.
- **Agent-instruction impact:** Aligned in C_AGENT_AUTHORITY across host-authoritative AGENTS, implementation/coordination/QA roles, Codex skills, and tracked consumers.
- **Audit result:** PASS: C01,C03,C04,C07,C10,C11,C13-C20,C22,C23. N/A with reason: C02 (C20 exact equality), C05 (Research-owned), C06 (pre-draft phases), C08-C09 (no test creation), C12 (no delegation), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 4016/918/4934/996; after = 1849/520/2369/505.
- **Residual concern:** None.
#### `chore/ready`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Package verified branch evidence, deferred work, and closure claims into a submitted pull request.
- **Workflow distinction:** N/A — C20 deliberately makes terminal behavior identical; workflow-specific meaning is supplied by prior artifacts and PR content.
- **Retained activations:** Evidence-freshness decision; final `git_status` and `git_diff_stat`; deferred-work search and @co transfer; PR scaffolding; final state commit when needed; clean-state check; `submit_pr`; outcome-neutral hand-over.
- **Removed or relocated content:** Per-workflow prose, unconditional branch gates, repeated issue curation, merge-approval checks, merge prohibitions already enforced by tooling, and producer readiness claims.
- **Test/evidence policy:** Reuse fresh Validation evidence; rerun only invalidated checks at the narrowest sufficient scope, including the workspace-wide suite only when stale or missing.
- **Document reads:** Conditional — inspect the issue, Validation evidence, and current documentation only when needed to support final claims.
- **Delegation/QA:** No delegated review. The producer supplies evidence and `Review requested`; independent QA/review authority is external to this contract.
- **Hand-over:** Canonical Scope → Deliverables → Evidence → Open Work → Review Request; includes clickable PR and repository-relative artifact link forms.
- **Agent-instruction impact:** Aligned in C_AGENT_AUTHORITY across host-authoritative AGENTS, implementation/coordination/QA roles, Codex skills, and tracked consumers.
- **Audit result:** PASS: C01,C03,C04,C07,C10,C11,C13-C20,C22,C23. N/A with reason: C02 (C20 exact equality), C05 (Research-owned), C06 (pre-draft phases), C08-C09 (no test creation), C12 (no delegation), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 1873/0/1873/348; after = 1849/520/2369/505.
- **Residual concern:** None.
#### `epic/ready`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Package verified branch evidence, deferred work, and closure claims into a submitted pull request.
- **Workflow distinction:** N/A — C20 deliberately makes terminal behavior identical; workflow-specific meaning is supplied by prior artifacts and PR content.
- **Retained activations:** Evidence-freshness decision; final `git_status` and `git_diff_stat`; deferred-work search and @co transfer; PR scaffolding; final state commit when needed; clean-state check; `submit_pr`; outcome-neutral hand-over.
- **Removed or relocated content:** Per-workflow prose, unconditional branch gates, repeated issue curation, merge-approval checks, merge prohibitions already enforced by tooling, and producer readiness claims.
- **Test/evidence policy:** Reuse fresh Validation evidence; rerun only invalidated checks at the narrowest sufficient scope, including the workspace-wide suite only when stale or missing.
- **Document reads:** Conditional — inspect the issue, Validation evidence, and current documentation only when needed to support final claims.
- **Delegation/QA:** No delegated review. The producer supplies evidence and `Review requested`; independent QA/review authority is external to this contract.
- **Hand-over:** Canonical Scope → Deliverables → Evidence → Open Work → Review Request; includes clickable PR and repository-relative artifact link forms.
- **Agent-instruction impact:** Aligned in C_AGENT_AUTHORITY across host-authoritative AGENTS, implementation/coordination/QA roles, Codex skills, and tracked consumers.
- **Audit result:** PASS: C01,C03,C04,C07,C10,C11,C13-C20,C22,C23. N/A with reason: C02 (C20 exact equality), C05 (Research-owned), C06 (pre-draft phases), C08-C09 (no test creation), C12 (no delegation), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 4050/1028/5078/1036; after = 1849/520/2369/505.
- **Residual concern:** None.
### C_FEATURE

#### `feature/research`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `feature/design`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `feature/planning`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `feature/implementation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `feature/validation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `feature/documentation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

### C_BUG

#### `bug/research`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `bug/design`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `bug/planning`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `bug/implementation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `bug/validation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `bug/documentation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

### C_REFACTOR_HOTFIX

#### `refactor/research`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `refactor/design`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `refactor/planning`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `refactor/implementation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `refactor/validation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `refactor/documentation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `hotfix/implementation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `hotfix/validation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `hotfix/documentation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

### C_CHORE_DOCS

#### `chore/research`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `chore/implementation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `chore/validation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `chore/documentation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `docs/planning`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `docs/documentation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

### C_EPIC

#### `epic/research`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `epic/planning`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `epic/design`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `epic/coordination`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.

#### `epic/documentation`

- **Implementation status:** PENDING
- **Owned purpose:** Pending implementation evidence.
- **Workflow distinction:** Pending implementation evidence.
- **Retained activations:** Pending implementation evidence.
- **Removed or relocated content:** Pending implementation evidence.
- **Test/evidence policy:** Pending implementation evidence.
- **Document reads:** Pending implementation evidence.
- **Delegation/QA:** Pending implementation evidence.
- **Hand-over:** Pending implementation evidence.
- **Agent-instruction impact:** Pending implementation evidence.
- **Audit result:** C01-C23 PENDING — no criterion is pre-marked PASS or N/A.
- **Size:** Instruction and hand-over characters and lexical proxy units: pending before/after measurement.
- **Residual concern:** Pending implementation evidence.






## Related Documentation
- **[docs/development/issue399/research.md][related-1]**
- **[docs/development/issue399/planning.md][related-2]**
- **[.pgmcp/config/contracts.yaml][related-3]**

<!-- Link definitions -->

[related-1]: docs/development/issue399/research.md
[related-2]: docs/development/issue399/planning.md
[related-3]: .pgmcp/config/contracts.yaml

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-08-20 | Agent | Initial draft |
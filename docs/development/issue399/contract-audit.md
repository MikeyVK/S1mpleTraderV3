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

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Establish evidence, proportional blast radius, and human-approved strategy boundaries for a new feature.
- **Workflow distinction:** Feature research frames new supported capability and consumer impact rather than defect correction or preservation-only change.
- **Retained activations:** `get_work_context`; `get_issue`; proportional direct-source investigation; conditional bounded discovery; human Approved Strategy; research scaffolding; research commit; first branch push; review hand-over.
- **Removed or relocated content:** Unconditional full-document reads, harness-specific exploration, repeated orientation scripts, premature design/planning detail, and duplicated self-review prose.
- **Test/evidence policy:** Identify affected tests/helpers and stable behavior boundaries; defer test architecture and permanent-test selection to Design/Planning.
- **Document reads:** Required boundary check before drafting; Architecture, Documentation, and other references only when they govern an affected or uncertain boundary.
- **Delegation/QA:** Optional discovery is bounded, direct-source-based, counterevidence-seeking, uncertainly reported, producer-verified, and non-authoritative.
- **Hand-over:** Canonical structure with direct Research and source-evidence links; outcome-neutral.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required for this contract.
- **Audit result:** PASS: C01-C07,C10-C19,C22,C23. N/A: C08-C09 (test design/retention belongs to later phases), C20 (Ready-only), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 5455/901/6356/1140; after = 2084/527/2611/500.
- **Residual concern:** None.
#### `feature/design`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Convert approved feature evidence into architecture, interfaces, failure behavior, and durable production/test design.
- **Workflow distinction:** Feature design introduces a new capability while protecting explicitly chosen consumer and migration strategy boundaries.
- **Retained activations:** Research and Approved Strategy intake; applicable standards; option comparison; production and test design; conditional discovery/preflight; human stop on strategy conflict; design scaffolding; commit; independent-review request.
- **Removed or relocated content:** Harness-specific explore/QA calls, internal PASS loop, model selection, repeated orientation, and planning/implementation work.
- **Test/evidence policy:** First-class test architecture, public boundaries, durable behavior/invariant coverage, reuse/adaptation, and rejection of ceremony-only tests.
- **Document reads:** Research and Approved Strategy required; applicable Architecture and Documentation sections conditional on affected design boundaries.
- **Delegation/QA:** Optional discovery and adversarial preflight are bounded and findings-only; producer verifies and decides.
- **Hand-over:** Canonical structure with clickable Design, Research, and source-seam links.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required for this contract.
- **Audit result:** PASS: C01-C04,C06-C19,C22,C23. N/A: C05 (Research-owned blast-radius inventory), C20 (Ready-only), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 6440/569/7009/1219; after = 2131/593/2724/519.
- **Residual concern:** None.
#### `feature/planning`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Translate approved feature design into dependency-ordered, executable cycles and structured deliverables.
- **Workflow distinction:** Feature planning sequences capability construction and validation while preserving new-interface and consumer strategy obligations.
- **Retained activations:** Approved artifacts intake; applicable standards; cycle/deliverable/test/gate design; conditional discovery; planning scaffolding; `save_planning_deliverables`; commit; review request.
- **Removed or relocated content:** Mandatory full TYPE_CHECKING read, harness-specific exploration/internal QA, PASS loops, repeated interaction scripts, and blanket per-cycle full gates.
- **Test/evidence policy:** Change-type/risk-driven TDD; durable tests only; test code at production quality; focused cycle checks; one full suite and branch gates reserved for Validation.
- **Document reads:** Approved artifacts required; standards conditional on planned work and uncertainty.
- **Delegation/QA:** Optional planning discovery is bounded, direct-source-based, producer-verified, and findings-only.
- **Hand-over:** Canonical structure linking Planning, Design, and Research plus saved payload evidence.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required for this contract.
- **Audit result:** PASS: C01-C04,C06-C19,C22,C23. N/A: C05 (Research-owned), C20 (Ready-only), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 6948/754/7702/1353; after = 2248/586/2834/567.
- **Residual concern:** None.
#### `feature/implementation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Execute each approved feature cycle without redesign, scope creep, or strategy drift.
- **Workflow distinction:** Feature implementation builds new behavior through cycle-specific evidence while preserving approved new contracts and consumers.
- **Retained activations:** `get_work_context`; `get_project_plan`; active-cycle stop checks; conditional execution delegation; planned RED/GREEN/REFACTOR or justified non-RED path; focused `run_tests`; file gates; commits; producer self-check; `transition_cycle`; final review request.
- **Removed or relocated content:** Caveman formatting rules, mandatory explore subagent, hardcoded GPT-5.4, producer-owned QA PASS/FAIL, QA-driven auto-progression, blanket TDD, and verbose tool narration.
- **Test/evidence policy:** Strict TDD for planned behavior/durable gaps; no artificial RED for mechanical/test-maintenance work; tests/helpers held to production standards; no full suite before Validation.
- **Document reads:** Plan and active-cycle artifacts required; other sources inspected only for the active boundary.
- **Delegation/QA:** Execution delegation is bounded with direct inputs and evidence; producer verifies. Optional preflight is adversarial findings-only and never authorizes progression.
- **Hand-over:** Canonical proportional implementation hand-over with primary production/test links and branch diff as complete inventory.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required for this contract.
- **Audit result:** PASS: C01-C04,C07-C19,C22,C23. N/A: C05 (Research-owned), C06 (pre-draft phases), C20 (Ready-only), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 2372/0/2372/576; after = 2255/665/2920/566.
- **Residual concern:** None.
#### `feature/validation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Produce branch-wide evidence that the implemented feature satisfies plan, design, strategy, tests, and quality obligations.
- **Workflow distinction:** Feature validation proves newly introduced behavior and offers a safe demonstration or reviewable fallback.
- **Retained activations:** Approved artifacts and plan intake; deliverable mapping; one `run_tests(scope='full')`; `run_quality_gates(scope='branch')`; targeted gap validation; demo/fallback; deferred-work discovery; validation artifact creation/update; commit; independent QA request.
- **Removed or relocated content:** Mandatory rereading of whole standards, harness-specific exploration, duplicated self-check prose, and any permission to redesign or patch from Validation.
- **Test/evidence policy:** Single full suite plus branch gates; targeted checks only for material gaps; no permanent diagnostic/ceremony tests; failures remain explicit.
- **Document reads:** Approved artifacts required; standards conditional on affected validation boundaries.
- **Delegation/QA:** N/A — no delegated review is required; producer evidence is handed to separate independent QA.
- **Hand-over:** Canonical structure linking Validation, Planning, and primary evidence; findings and failures precede review request.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required for this contract.
- **Audit result:** PASS: C01-C04,C07-C11,C13-C19,C22,C23. N/A: C05-C06 (Research/pre-draft), C12 (no delegation), C20 (Ready-only), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 3837/850/4687/861; after = 1861/625/2486/492.
- **Residual concern:** None.
#### `feature/documentation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Reconcile active documentation and instruction consumers with validated feature behavior.
- **Workflow distinction:** Feature documentation explains a newly supported capability, its use, limits, and authoritative operational surfaces.
- **Retained activations:** Validation intake; active-docs/agent/template blast-radius inventory; authoritative-source-first edits; consumer parity; targeted documentation checks; deferred-work capture; documentation commit; review request.
- **Removed or relocated content:** Harness-specific workspace scan, repeated historical-boundary prose, blanket implementation checks, and producer readiness claims.
- **Test/evidence policy:** Run only documentation/link/template/parity tests invalidated by edits; do not repeat fresh implementation evidence.
- **Document reads:** Validation and applicable Documentation Standard boundaries required; other docs/references conditional; historical artifacts context-only by default.
- **Delegation/QA:** N/A — no delegation required; any scan result is producer-owned and cannot authorize progression.
- **Hand-over:** Canonical structure with clickable updated docs, source/consumer assets, Validation, and reviewed-unchanged surfaces.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required for this contract.
- **Audit result:** PASS: C01-C04,C07,C10-C19,C22,C23. N/A: C05-C06 (Research/pre-draft), C08-C09 (no test design/creation), C20 (Ready-only), C21 (Coordination-only).
- **Size:** Before instruction/hand-over/effective/units = 3108/561/3669/655; after = 1650/586/2236/410.
- **Residual concern:** None.
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
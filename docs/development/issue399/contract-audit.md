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

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Establish reproducible defect evidence, root cause, corrected behavior, proportional blast radius, and approved strategy.
- **Workflow distinction:** Bug research distinguishes symptoms from causal evidence and frames correction/regression boundaries.
- **Retained activations:** Reproduction/direct evidence; causal alternatives; full proportional blast radius; conditional discovery; human Approved Strategy; research scaffold/commit/first push; review request.
- **Removed or relocated content:** Unconditional document reads, harness-specific exploration, repeated interaction scripts, premature fix design, and generic feature framing.
- **Test/evidence policy:** Identify affected regression surfaces and corrected behavior; leave durable test design to Design/Planning.
- **Document reads:** Required research boundary; standards/references conditional on affected uncertainty.
- **Delegation/QA:** Optional causal discovery is bounded, counterevidence-seeking, direct-source-based, producer-verified, and non-authoritative.
- **Hand-over:** Canonical links to Research and reproduction/root-cause evidence.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C07,C10-C19,C22,C23. N/A: C08-C09 (later test design), C20 (Ready), C21 (Coordination).
- **Size:** Before instruction/hand-over/effective/units = 5793/1019/6812/1222; after = 2108/583/2691/521.
- **Residual concern:** None.
#### `bug/design`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Design the smallest root-cause correction with preserved supported behavior and durable regression coverage.
- **Workflow distinction:** Bug design removes an evidenced cause instead of introducing general new capability.
- **Retained activations:** Causal input; option comparison; smallest correction; preservation/strategy; first-class regression design; conditional discovery/preflight; design scaffold/commit; independent review request.
- **Removed or relocated content:** Internal QA PASS loop, model selection, harness-specific exploration, repeated checkpoints, symptom-only or planning work.
- **Test/evidence policy:** Durable public-boundary regression or invariant; adapt existing coverage; reject diagnostic/detail ballast.
- **Document reads:** Research/strategy required; applicable Architecture/Documentation sections conditional.
- **Delegation/QA:** Discovery/preflight findings-only, bounded, producer-verified.
- **Hand-over:** Canonical links to Design, Research, and causal seams.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C06-C19,C22,C23. N/A: C05 (Research), C20 (Ready), C21 (Coordination).
- **Size:** Before instruction/hand-over/effective/units = 6539/623/7162/1256; after = 2090/598/2688/507.
- **Residual concern:** None.
#### `bug/planning`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Slice root-cause correction, regression protection, and cleanup into executable cycles.
- **Workflow distinction:** Bug planning maps cause and corrected behavior directly to minimal correction cycles.
- **Retained activations:** Approved inputs; cycle/deliverable/dependency mapping; regression-value policy; focused checks; conditional discovery; Planning scaffold; saved payload; commit/review.
- **Removed or relocated content:** Mandatory reference reads, harness/internal QA, PASS loops, repeated interactions, blanket full gates.
- **Test/evidence policy:** Default durable failing regression; reuse existing failing coverage; no diagnostic ballast or artificial mechanical RED; production-quality tests.
- **Document reads:** Approved artifacts required; other standards conditional on planned seams.
- **Delegation/QA:** Bounded causal/sequencing discovery, producer-verified, findings-only.
- **Hand-over:** Canonical links to Planning, Design, and Research plus payload proof.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C06-C19,C22,C23. N/A: C05 (Research), C20 (Ready), C21 (Coordination).
- **Size:** Before instruction/hand-over/effective/units = 7292/794/8086/1413; after = 2208/591/2799/559.
- **Residual concern:** None.
#### `bug/implementation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Execute active correction cycles against root cause and corrected behavior without scope/strategy drift.
- **Workflow distinction:** Bug implementation defaults behavior fixes to durable regression RED evidence and minimal root-cause GREEN.
- **Retained activations:** Plan/context; causal stop checks; bounded execution; first-class test code; change-appropriate RED/GREEN/REFACTOR; focused tests/file gates; self-check; cycle transition; final review.
- **Removed or relocated content:** Mandatory explore, internal QA PASS/auto-progression, blanket TDD duplicates, verbose narration, and missing hand-over.
- **Test/evidence policy:** Durable failing regression or existing failing test; no duplicate/diagnostic test; mechanical exception; Validation owns broad checks.
- **Document reads:** Plan/cycle and causal inputs required; other reads active-boundary only.
- **Delegation/QA:** Execution bounded and producer-verified; adversarial preflight findings-only; objective producer progression.
- **Hand-over:** Canonical proportional production/regression links plus branch diff inventory.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C07-C19,C22,C23. N/A: C05 (Research), C06 (pre-draft), C20 (Ready), C21 (Coordination).
- **Size:** Before instruction/hand-over/effective/units = 4310/0/4310/829; after = 2174/708/2882/551.
- **Residual concern:** None.
#### `bug/validation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Prove branch-wide corrected behavior, root-cause removal, preservation, and regression safety.
- **Workflow distinction:** Bug validation makes before/after defect evidence and durable regression scope explicit.
- **Retained activations:** Approved inputs; evidence mapping; one full suite; branch gates; visible regression proof; demo/fallback; deferred work; Validation artifact/commit; independent QA request.
- **Removed or relocated content:** Harness exploration, unconditional full-doc reads, duplicated self-checks, patching/redesign permission, and producer verdict.
- **Test/evidence policy:** Full suite/branch gates once; explicit regression scope if needed; permanent test only for new stable gap.
- **Document reads:** Approved artifacts required; standards conditional on validation boundary.
- **Delegation/QA:** No delegated review required; separate independent QA owns GO/NOGO.
- **Hand-over:** Canonical links to Validation, Planning, and regression/reproduction evidence.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C07-C11,C13-C19,C22,C23. N/A: C05-C06, C12 (no delegation), C20, C21.
- **Size:** Before instruction/hand-over/effective/units = 4143/874/5017/914; after = 1832/669/2501/505.
- **Residual concern:** None.
#### `bug/documentation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Reconcile current docs and instruction consumers with validated corrected behavior.
- **Workflow distinction:** Bug documentation removes obsolete failure guidance and explains corrected behavior or residual limits.
- **Retained activations:** Validation intake; active docs/source-consumer inventory; minimal updates; source-first synchronization/parity; focused docs checks; deferred capture; commit/review.
- **Removed or relocated content:** Harness scan, repeated historical prose, blanket tests/gates, unsupported readiness/behavior claims.
- **Test/evidence policy:** Only invalidated documentation/link/template/parity checks; reuse fresh runtime evidence.
- **Document reads:** Validation/applicable doc boundary required; historical/context and other reads conditional.
- **Delegation/QA:** No delegation required; producer owns scan and cannot authorize progression.
- **Hand-over:** Canonical clickable docs/source-consumer/Validation evidence.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C07,C10-C19,C22,C23. N/A: C05-C06,C08-C09,C20,C21.
- **Size:** Before instruction/hand-over/effective/units = 3072/591/3663/661; after = 1443/584/2027/365.
- **Residual concern:** None.
### C_REFACTOR_HOTFIX

#### `refactor/research`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Evidence current structure, invariants, blast radius, candidate seams, and strategy.
- **Workflow distinction:** Refactor research distinguishes structural debt from behavior change and makes preservation explicit.
- **Retained activations:** Issue/context; structural/test investigation; proportional blast radius; invariant evidence; bounded/internal or targeted external discovery; human strategy; Research scaffold/commit/first push; review.
- **Removed or relocated content:** Unconditional docs/web exploration, repeated interactions, premature target design/cycles, and generic migration prose.
- **Test/evidence policy:** Identify existing preservation evidence, test/helper coupling, and durable gaps without prescribing rewrites.
- **Document reads:** Research boundary required; standards/externals conditional on an exact affected question.
- **Delegation/QA:** Bounded direct-source/counterexample discovery, producer-verified; external sources traceable.
- **Hand-over:** Canonical links to Research and structural/invariant evidence.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C07,C10-C19,C22,C23. N/A: C08-C09 (Design/Planning), C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 5784/1012/6796/1207; after = 2200/582/2782/526.
- **Residual concern:** None.
#### `refactor/design`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Design target responsibilities, dependencies, transitions, cleanup, and test architecture while preserving behavior.
- **Workflow distinction:** Refactor design changes structure only and treats obsolete-code/test removal as part of the target.
- **Retained activations:** Research/strategy; applicable standards; target alternatives; invariant mapping; first-class test architecture; bounded preflight; Design scaffold/commit/review.
- **Removed or relocated content:** Internal QA PASS, harness discovery, repeated checkpoints, planning/implementation leakage.
- **Test/evidence policy:** Prefer existing invariant coverage; characterization only for durable gap; clean fixture/helper coupling and implementation-detail tests.
- **Document reads:** Research/strategy required; standards conditional.
- **Delegation/QA:** Discovery/preflight bounded, findings-only, producer-verified.
- **Hand-over:** Canonical Design/Research/seam links.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C06-C19,C22,C23. N/A: C05,C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 3588/504/4092/757; after = 2000/607/2607/491.
- **Residual concern:** None.
#### `refactor/planning`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Plan reversible structural cycles, preservation evidence, cutover, deletion, and cleanup.
- **Workflow distinction:** Refactor planning sequences seam introduction/migration/removal without assuming behavior RED.
- **Retained activations:** Approved inputs; structural cycles/dependencies; invariant and cleanup obligations; non-artificial test mode; focused verification; bounded discovery; Planning scaffold/saved payload/commit/review.
- **Removed or relocated content:** Mandatory full reads, harness/internal QA PASS, blanket TDD, repeated broad gates.
- **Test/evidence policy:** Green preservation baseline by default; failing characterization only for durable uncovered invariant; obsolete-coupled tests adapted/removed.
- **Document reads:** Approved artifacts required; standards conditional on seams.
- **Delegation/QA:** Bounded structural/sequencing discovery, producer-verified, findings-only.
- **Hand-over:** Canonical Planning/Design/Research links plus saved payload.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C06-C19,C22,C23. N/A: C05,C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 7186/795/7981/1395; after = 2141/588/2729/547.
- **Residual concern:** None.
#### `refactor/implementation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Execute active structural cycles with preserved behavior and complete planned cleanup.
- **Workflow distinction:** Refactor Implementation keeps a green invariant baseline unless a real durable coverage gap justifies RED.
- **Retained activations:** Context/plan; bounded execution; first-class test structure; characterization exception; structural GREEN; cleanup/deletion REFACTOR; focused checks; purity self-check; objective cycle transition; review.
- **Removed or relocated content:** Mandatory explore/internal QA PASS, artificial TDD, QA-driven progression, repeated gates, and missing hand-over.
- **Test/evidence policy:** Existing focused green baseline normally; RED only for uncovered durable invariant; cleanup obsolete tests/helpers; full suite in Validation.
- **Document reads:** Active cycle/strategy required; other reads only for seam.
- **Delegation/QA:** Execution bounded and verified; adversarial structural preflight findings-only; producer decides.
- **Hand-over:** Canonical proportional structural/test links and diff inventory.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C07-C19,C22,C23. N/A: C05-C06,C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 4464/0/4464/840; after = 2022/704/2726/519.
- **Residual concern:** None.
#### `refactor/validation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Prove structural completion, cleanup, invariants, and supported-behavior preservation.
- **Workflow distinction:** Refactor validation searches for remnants/dependency purity and demonstrates unchanged behavior.
- **Retained activations:** Approved inputs; structural/deliverable mapping; remnant checks; one full suite; branch gates; targeted structural gaps; Validation artifact/commit; independent QA.
- **Removed or relocated content:** Harness exploration, unconditional reads, duplicated self-check, redesign/patching, producer PASS.
- **Test/evidence policy:** Full suite/branch gates once; targeted invariant checks only; no diagnostic/detail tests.
- **Document reads:** Approved artifacts required; standards conditional.
- **Delegation/QA:** No delegated review; independent QA owns verdict.
- **Hand-over:** Canonical Validation/Planning/structural evidence links.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C07-C11,C13-C19,C22,C23. N/A: C05-C06,C12,C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 3900/897/4797/874; after = 1720/639/2359/467.
- **Residual concern:** None.
#### `refactor/documentation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Reconcile architecture/developer docs with validated structure while preserving user-facing behavior claims.
- **Workflow distinction:** Refactor docs primarily update responsibilities, seams, extension points, and obsolete paths; user docs may remain unchanged.
- **Retained activations:** Validation intake; architecture/dev/source-consumer inventory; minimal source-first updates/parity; reviewed-unchanged user docs; focused checks; deferred debt; commit/review.
- **Removed or relocated content:** Harness scan, historical churn, repeated runtime verification, and invented behavior changes.
- **Test/evidence policy:** Only invalidated docs/link/template/parity checks; reuse Validation.
- **Document reads:** Validation/applicable doc boundary required; other references conditional.
- **Delegation/QA:** No delegation required; producer retains scan/decision.
- **Hand-over:** Canonical architecture/docs/consumer/Validation links.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C07,C10-C19,C22,C23. N/A: C05-C06,C08-C09,C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 3119/600/3719/660; after = 1418/598/2016/376.
- **Residual concern:** None.
#### `hotfix/implementation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Execute the smallest safe correction/containment slice without broadening scope.
- **Workflow distinction:** Hotfix starts directly in Implementation and must derive explicit containment from issue/user evidence rather than missing Research/Design phases.
- **Retained activations:** Context/issue/plan; first push; bounded execution; durable focused RED or existing failure; minimal GREEN; risk-only cleanup; focused checks; objective cycle transitions; independent review request.
- **Removed or relocated content:** Mandatory explore/internal QA PASS, blanket TDD duplication, broad refactor latitude, and missing hand-over.
- **Test/evidence policy:** Durable regression or existing failure; no diagnostic ballast; focused file evidence; broad proof deferred to Validation.
- **Document reads:** Issue, constraints, and active slice required; other reads only for affected boundary.
- **Delegation/QA:** Bounded execution and adversarial findings-only preflight; producer decides/progresses.
- **Hand-over:** Canonical proportional correction/test links plus diff inventory.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C07-C19,C22,C23. N/A: C05-C06 (no pre-implementation phases), C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 4475/0/4475/858; after = 2191/656/2847/549.
- **Residual concern:** None.
#### `hotfix/validation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Verify correction, containment, rollback exposure, and branch-wide safety.
- **Workflow distinction:** Hotfix validation emphasizes operational containment and excludes nonessential cleanup.
- **Retained activations:** Inputs/constraint mapping; one full suite; branch gates; focused regression; risk/rollback assessment; Validation artifact/commit; independent QA request.
- **Removed or relocated content:** Harness exploration, unconditional reads, duplicated self-checks, patching/broadening from Validation, and producer verdict.
- **Test/evidence policy:** Full suite/branch gates once plus visible hotfix regression; no diagnostic permanent tests.
- **Document reads:** Hotfix constraints required; standards conditional on boundary.
- **Delegation/QA:** No delegated review; separate independent QA owns GO/NOGO.
- **Hand-over:** Canonical links to Validation and hotfix evidence.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C07-C11,C13-C19,C22,C23. N/A: C05-C06,C12,C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 3804/838/4642/860; after = 1684/559/2243/438.
- **Residual concern:** None.
#### `hotfix/documentation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Reconcile current operational guidance with the validated hotfix.
- **Workflow distinction:** Hotfix documentation prioritizes safe operator/user guidance, containment, and rollback clarity over broad docs cleanup.
- **Retained activations:** Validation intake; operational docs inventory; minimal safe updates; source-first sync/parity; focused docs checks; deferred cleanup; commit/review.
- **Removed or relocated content:** Broad workspace scan, historical churn, repeated gates, and claims beyond validated containment.
- **Test/evidence policy:** Only invalidated docs/link/template/parity checks; reuse Validation.
- **Document reads:** Validation and applicable Documentation boundary required; operational reads conditional.
- **Delegation/QA:** No delegation required; producer scan is non-authoritative.
- **Hand-over:** Canonical links to runbooks/guidance, consumers, and Validation.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no additional static-source change required.
- **Audit result:** PASS: C01-C04,C07,C10-C19,C22,C23. N/A: C05-C06,C08-C09,C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 3094/589/3683/660; after = 1333/595/1928/349.
- **Residual concern:** None.
### C_CHORE_DOCS

#### `chore/research`

- **Implementation status:** REWRITTEN — producer audit complete; independent review remains separate.
- **Owned purpose:** Establish a proportionate, human-approved maintenance boundary without forcing an artifact.
- **Workflow distinction:** Chore research is deliberately lighter than feature/bug/refactor research and stops when the work is no longer mechanical.
- **Retained activations:** Context/issue; proportional code/config/test/docs/agent/consumer blast radius; risk and strategy stop; optional Research scaffold/commit/first push; hand-over.
- **Removed or relocated content:** Explanatory outcome lists, unconditional external/subagent research, mandatory artifact creation, and implementation detail.
- **Test/evidence policy:** Identify stable test boundaries and verification needs; design or create no tests here.
- **Document reads:** Conditional on affected standards or material uncertainty; Documentation Standard only when persisting Research.
- **Delegation/QA:** No delegation required; producer stops outcome-neutrally and retains all decisions.
- **Hand-over:** Canonical linked Research/direct-outcome and blast-radius review index.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; agent and consumer impact remains explicit in blast radius.
- **Audit result:** PASS: C01-C07,C10-C11,C13-C19,C22-C23. N/A: C08-C09 (later-phase test decisions), C12 (no delegation), C20 (Ready), C21 (Coordination).
- **Size:** Before instruction/hand-over/effective/units = 951/264/1215/227; after = 842/371/1213/244.
- **Residual concern:** None.

#### `chore/implementation`

- **Implementation status:** REWRITTEN — producer audit complete; independent review remains separate.
- **Owned purpose:** Apply one complete, non-cycle-based maintenance change within the approved boundary.
- **Workflow distinction:** Chore implementation avoids artificial TDD cycles while retaining durable-test and focused-proof standards.
- **Retained activations:** Context/strategy stop; smallest coherent cross-surface edit; first-class tests; focused tests/file gates; diff review; commit; hand-over.
- **Removed or relocated content:** Feature/refactor latitude, broad validation checks, ceremony-driven tests, verbose deliverable narration, and user-transition instructions.
- **Test/evidence policy:** Permanent tests only for stable behavior/durable gaps; no diagnostic or ceremony tests; full suite and branch gates belong to Validation.
- **Document reads:** Approved Research outcome required; other standards conditional on affected boundaries.
- **Delegation/QA:** No delegation required; producer verifies direct evidence and stops without a verdict.
- **Hand-over:** Canonical proportional production/config/test links with complete-diff reference.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no new static-source change required.
- **Audit result:** PASS: C01-C04,C07-C11,C13-C19,C22-C23. N/A: C05-C06 (Research/pre-draft), C12 (no delegation), C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 1225/425/1650/305; after = 1087/388/1475/297.
- **Residual concern:** None.

#### `chore/validation`

- **Implementation status:** REWRITTEN — producer audit complete; independent QA remains separate.
- **Owned purpose:** Prove the chore workspace-wide and expose deferred work before PR preparation.
- **Workflow distinction:** Chore Validation always runs one final full suite and branch gates despite lightweight earlier phases.
- **Retained activations:** Approved inputs; full diff/status; one full suite; branch gates; cached-resource inspection; defect return; active deferred-work search; persistent evidence when needed; independent QA request.
- **Removed or relocated content:** Duplicate focused runs, repair permission, producer approval, stale-evidence acceptance, and repeated explanatory detail.
- **Test/evidence policy:** Full workspace suite and branch gates once after final changes; narrow checks only for an uncovered material gap.
- **Document reads:** Issue, boundary, and implementation evidence required; other references only when a claim is uncertain.
- **Delegation/QA:** No delegated review; fresh independent QA reads workspace evidence and alone owns GO/NOGO.
- **Hand-over:** Canonical linked Validation/evidence and explicit deferred-work tracking.
- **Agent-instruction impact:** Covered by C_AGENT_AUTHORITY; no new static-source change required.
- **Audit result:** PASS: C01-C04,C07-C11,C13-C19,C22-C23. N/A: C05-C06,C12 (no delegation), C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 1710/504/2214/423; after = 1246/455/1701/347.
- **Residual concern:** None.

#### `chore/documentation`

- **Implementation status:** REWRITTEN — producer audit complete; independent review remains separate.
- **Owned purpose:** Reconcile current authoritative and derived documentation invalidated by the chore.
- **Workflow distinction:** Chore documentation stays proportional and may explicitly conclude that no documentation edit is required.
- **Retained activations:** Validation intake; applicable doc boundary; active surface inventory; source-first sync; focused docs/parity checks; commit when changed; hand-over.
- **Removed or relocated content:** Historical trace, archive rewrites, broad runtime reruns, repeated result prose, and transition control.
- **Test/evidence policy:** Only invalidated documentation, link, template, rendering, or parity checks; reuse fresh Validation.
- **Document reads:** Validation and applicable Documentation Standard boundary required; other docs conditional.
- **Delegation/QA:** No delegation required; producer owns reconciliation and makes no review verdict.
- **Hand-over:** Canonical authoritative-source/consumer and Validation review links.
- **Agent-instruction impact:** Source-first order and consumer synchronization align with C_AGENT_AUTHORITY.
- **Audit result:** PASS: C01-C04,C07,C10-C11,C13-C19,C22-C23. N/A: C05-C06,C08-C09,C12,C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 1009/254/1263/215; after = 836/423/1259/245.
- **Residual concern:** None.

#### `docs/planning`

- **Implementation status:** REWRITTEN — producer audit complete; independent review remains separate.
- **Owned purpose:** Produce an executable documentation-only plan grounded in authoritative sources.
- **Workflow distinction:** Docs Planning maps audiences, current docs, sources, consumers, and review proof without production/test work.
- **Retained activations:** Context/issue; explicit in/out/unknown boundary; applicable Documentation Standard; direct source mapping; bounded discovery; dependency-ordered tasks; Planning scaffold/commit/first push; hand-over.
- **Removed or relocated content:** Mandatory broad exploration, repeated human checkpoints, internal QA PASS loop, implementation-cycle payloads, and verbose planning nucleus.
- **Test/evidence policy:** Plan focused documentation/parity proof only; runtime test work is out of scope.
- **Document reads:** Applicable Documentation Standard sections and named/source docs required; other references conditional.
- **Delegation/QA:** Optional discovery is neutral, counterevidence-seeking, source-citing, uncertainly reported, and producer-verified; no delegated verdict.
- **Hand-over:** Canonical clickable Planning, target-doc, and authoritative-input review index.
- **Agent-instruction impact:** Source/consumer planning aligns with C_AGENT_AUTHORITY; no additional static edit required.
- **Audit result:** PASS: C01-C04,C06-C07,C10-C19,C22-C23. N/A: C05 (Research-only full blast radius), C08-C09 (no test code), C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 4483/504/4987/896; after = 1841/463/2304/426.
- **Residual concern:** None.

#### `docs/documentation`

- **Implementation status:** REWRITTEN — producer audit complete; fresh documentation QA remains separate.
- **Owned purpose:** Deliver the approved documentation plan as a coherent, current, source-backed surface.
- **Workflow distinction:** Docs Documentation is the workflow's delivery phase and remains documentation-only.
- **Retained activations:** Plan/standard intake; claim-to-source recheck; minimal updates; source-first consumer sync; focused documentation proof; self-check; commit; independent doc QA request.
- **Removed or relocated content:** Harness-specific workspace scan, broad runtime tests, repeated narrative checklists, producer PASS, and historical/default issue-artifact edits.
- **Test/evidence policy:** Only checks invalidated by docs edits: links, examples, templates, terminology, rendering, and parity.
- **Document reads:** Planning and applicable Documentation Standard sections required; historical/context material conditional.
- **Delegation/QA:** No delegation required; producer stops with review index, fresh external doc QA owns verdict.
- **Hand-over:** Canonical Planning, updated-doc, source-consumer, and focused-evidence links.
- **Agent-instruction impact:** Authoritative-first consumer synchronization aligns with C_AGENT_AUTHORITY.
- **Audit result:** PASS: C01-C04,C07,C10-C11,C13-C19,C22-C23. N/A: C05-C06,C08-C09,C12,C20-C21.
- **Size:** Before instruction/hand-over/effective/units = 3015/577/3592/643; after = 1614/519/2133/387.
- **Residual concern:** None.

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
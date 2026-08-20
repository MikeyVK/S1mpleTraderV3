<!-- docs\development\issue399\planning.md -->
<!-- template=planning version=130ac5ea created=2026-08-20T11:47Z updated=2026-08-20 -->
# Issue #399 Planning: Audit and Streamline Phase Instruction Contracts

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-08-20

---

## Purpose

Define implementation-sized cycles, dependencies, deliverables, evidence, and stop-go criteria for rewriting all 39 effective phase contracts without reopening the Approved Strategy.

## Scope

**In Scope:**

- All 39 `phase_instructions` values and their `handover_template` values in [contracts.yaml](../../../.pgmcp/config/contracts.yaml).
- Authoritative host agent instructions, QA roles, and QA skills whose global rules must align with the resulting contracts.
- Tracked derived consumers of changed agent sources.
- Durable structural contract tests and source-consumer parity tests.
- An issue-local per-contract audit ledger.
- Current reference documentation affected by the validated ownership model.

**Out of Scope:**

- Workflow membership or phase-order changes.
- YAML anchors, aliases, merge keys, generated instruction composition, or Python runtime composition.
- Production Python changes unless later evidence proves a current config-driven path insufficient; that evidence requires a human checkpoint before scope expands.
- Archived documentation and historical issue artifacts.
- Tests that lock prose, duplicate the semantic contract, or exist only to satisfy one implementation cycle.
- A permanent test per rewritten instruction.

## Prerequisites

1. [Final research and Approved Strategy](research.md).
2. The C01-C23 audit rubric in the research artifact.
3. [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md).
4. [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md).
5. [Type Checking Playbook](../../coding_standards/TYPE_CHECKING_PLAYBOOK.md).

---

## Summary

Execute eight sequential cycles. Align static agent authority first, then rewrite every effective runtime contract exactly once in workflow-driven groups. Each contract's instruction and hand-over are rewritten together and accepted independently through C01-C23 before the next contract in that group. Close with aggregate metrics and focused implementation verification. A single workspace-wide test run belongs to Validation; Ready reuses it while fresh.

## Binding Planning Decisions

| Decision | Planning result |
|---|---|
| Primary slicing axis | Workflow responsibility; cross-workflow Ready is handled together because exact equality is binding |
| Contract acceptance | Instruction plus hand-over are one effective contract and must pass C01-C23 together |
| Audit evidence location | `docs/development/issue399/contract-audit.md`; issue-local execution evidence, never runtime SSOT |
| Canonical hand-over skeleton | Scope → Deliverables → Evidence → Open Work → Review Request |
| Hand-over authority | Navigation and evidence index only; no producer PASS/GO or compliance conclusion |
| Automated test boundary | Automate durable structure and source parity; do not encode natural-language meaning as a second Python SSOT |
| Full-suite timing | Once in Validation; rerun only if later changes invalidate it |
| Production-code posture | No production Python change expected; stop for human approval if evidence makes one necessary |

## Contract Coverage

The six contract-rewrite cycles cover all 39 configured effective contracts exactly once.

| Cycle | Effective contracts | Count |
|---|---|---:|
| C_READY | Ready for Feature, Bug, Hotfix, Refactor, Docs, Chore, and Epic | 7 |
| C_FEATURE | Feature Research, Design, Planning, Implementation, Validation, Documentation | 6 |
| C_BUG | Bug Research, Design, Planning, Implementation, Validation, Documentation | 6 |
| C_REFACTOR_HOTFIX | Refactor Research, Design, Planning, Implementation, Validation, Documentation; Hotfix Implementation, Validation, Documentation | 9 |
| C_CHORE_DOCS | Chore Research, Implementation, Validation, Documentation; Docs Planning, Documentation | 6 |
| C_EPIC | Epic Research, Planning, Design, Coordination, Documentation | 5 |
| **Total** |  | **39** |

## Per-Contract Execution Protocol

For each effective contract, in configured order within its cycle:

1. Record baseline instruction and hand-over characters and lexical proxy units.
2. Record phase purpose, workflow distinction, retained activations, and relevant evidence policy.
3. Rewrite `phase_instructions` and `handover_template` together.
4. Apply C01-C23 independently. Record every `N/A` with a reason; never use it to hide a workflow obligation.
5. Revise immediately when any applicable criterion fails. Do not accept or move past that contract on a blanket group-level assertion.
6. Record agent-instruction impact, final metrics, and residual concern in the audit ledger.
7. Parse the complete YAML after every accepted edit batch; run the cycle's focused tests before its stop-go checkpoint.

The audit ledger uses one compact record per contract with these evidence groups:

- owned purpose and workflow distinction;
- retained activations plus removed or relocated content;
- test/evidence policy and document-read boundary;
- delegation, preflight, and external-QA behavior;
- hand-over links and agent-instruction impact;
- C01-C23 result, before/after metrics, and residual concern.

## Canonical Hand-over Contract

Every hand-over template uses these headings in this order:

1. `### <Workflow> / <Phase> Hand-over`
2. `#### Scope`
3. `#### Deliverables`
4. `#### Evidence`
5. `#### Open Work`
6. `#### Review Request`

Content beneath the headings remains phase- and workflow-specific.

- Pre-implementation Deliverables link the primary artifact and material inputs directly.
- Implementation links all changed files while useful; large diffs link primary review entry points and tests, group the remainder, and identify the branch diff as the complete inventory.
- Evidence names exact relevant checks and outcomes without copying the phase checklist.
- Open Work records blockers, questions, risks, and deferred work or explicitly says `None`.
- Review Request is outcome-neutral and states `Review requested`; it never claims PASS, GO, approval, or readiness as fact.
- Repository artifacts use repository-relative Markdown targets. Transient chat may use absolute targets only when the harness requires them.

---

## Implementation Cycles

### Cycle 1 — C_AGENT_AUTHORITY

**Goal:** Align static agent authority before rewriting runtime contracts.

**Deliverables:**

- **D_AGENT_GLOBAL:** Update relevant authoritative global host instructions so TDD, test scope, gate timing, document reads, delegation, hand-over, Ready, and phase authority match the Approved Strategy.
- **D_QA_BOOTSTRAP:** Add the anti-anchoring bootstrap and invocation-mode distinction near the start of every authoritative QA role and QA skill.
- **D_AGENT_CONSUMERS:** Synchronize every changed tracked consumer from its authoritative host source.
- **D_AGENT_PARITY_TESTS:** Expand durable, topology-based source-consumer parity and QA-bootstrap coverage.
- **D_AUDIT_LEDGER:** Scaffold `contract-audit.md` with 39 contract records and the research-defined evidence fields.

**Test strategy:**

- RED is justified only for durable QA-bootstrap and source-consumer parity behavior.
- GREEN updates authoritative sources first and then their consumers.
- REFACTOR keeps topology mapping centralized and test code compliant with the same architecture, typing, and public-boundary standards as production code.
- Run the focused documentation/agent test module and quality gates only on changed Python test files.

**Exit criteria:**

- Authoritative and derived QA entrypoints begin with equivalent anti-anchoring semantics.
- Producer-delegated review is findings-only; independent QA alone returns evidence-backed GO/NOGO.
- Changed source-consumer pairs are byte-equal.
- Static global rules no longer contradict the Approved Strategy.
- The 39-row audit ledger exists with no contract pre-marked PASS.

### Cycle 2 — C_READY

**Goal:** Establish terminal behavior and the common hand-over contract.

**Deliverables:**

- **D_READY_INSTRUCTIONS:** Rewrite all seven Ready instructions to one identical string.
- **D_READY_HANDOVERS:** Rewrite all seven Ready hand-overs to one identical canonical template.
- **D_READY_TESTS:** Add or update durable tests for exact Ready equality and required terminal invariants.
- **D_READY_AUDIT:** Complete seven C01-C23 audit records.

**Test strategy:**

- Use RED only for durable Ready equality and structural terminal invariants.
- Parse the real contracts config and run focused loader tests.
- Do not test prose synonyms or exact sentence wording beyond the intentional equality contract.

**Exit criteria:**

- All Ready instruction strings and hand-over templates are exactly equal.
- Ready activates evidence freshness, deferred-work discovery, final diff/status inspection, PR content, branch-state completeness, and PR submission.
- Ready does not check human merge approval and does not duplicate enforced merge authorization.
- All seven Ready effective contracts pass C01-C23 independently.

### Cycle 3 — C_FEATURE

**Goal:** Rewrite the six non-Ready Feature contracts without flattening feature-specific responsibilities.

**Deliverables:**

- **D_FEATURE_CONTRACTS:** Rewrite Research, Design, Planning, Implementation, Validation, and Documentation effective contracts.
- **D_FEATURE_AUDIT:** Complete six C01-C23 audit records.

**Test strategy:**

- Run focused loader and discovery-output tests.
- Preserve durable behavior and contract tests; use TDD by default only for stable executable behavior.
- Add no wording-lock test unless a separately identified durable structural gap requires it.

**Exit criteria:**

- All six Feature contracts pass C01-C23.
- Feature-specific discovery, target contract design, implementation slicing, durable behavior proof, and documentation reconciliation remain explicit.
- Test code is first-class and permanent tests require durable value.
- No producer-owned review verdict controls progression.

### Cycle 4 — C_BUG

**Goal:** Rewrite the six non-Ready Bug contracts around defect evidence and durable corrected behavior.

**Deliverables:**

- **D_BUG_CONTRACTS:** Rewrite Research, Design, Planning, Implementation, Validation, and Documentation effective contracts.
- **D_BUG_AUDIT:** Complete six C01-C23 audit records.

**Test strategy:**

- Run focused loader and Bug discovery-output tests.
- Require a durable regression test by default at a stable boundary, but permit evidence-backed omission when the test would protect only temporary diagnosis or implementation detail.

**Exit criteria:**

- All six Bug contracts pass C01-C23.
- Root cause, corrected behavior, supported-contract boundaries, and regression-sensitive validation remain distinct from Feature.
- Test maintenance and collateral test impact are explicit without creating workflow-only ballast.
- No parent-owned preflight can authorize cycle or phase progression.

### Cycle 5 — C_REFACTOR_HOTFIX

**Goal:** Preserve distinct refactor-baseline and hotfix-containment policies.

**Deliverables:**

- **D_REFACTOR_CONTRACTS:** Rewrite six non-Ready Refactor effective contracts.
- **D_HOTFIX_CONTRACTS:** Rewrite three non-Ready Hotfix effective contracts.
- **D_REFACTOR_HOTFIX_AUDIT:** Complete nine C01-C23 audit records.

**Test strategy:**

- Run focused loader, resolver, workflow, and affected discovery tests.
- Refactor establishes an existing-green preservation baseline and adds tests only for durable gaps or intended behavior change.
- Hotfix uses the minimum safe containment proof and retains a permanent regression only when it protects durable behavior.

**Exit criteria:**

- All nine contracts pass C01-C23.
- Refactor does not inherit feature-style test creation pressure.
- Hotfix remains small and safe without losing containment, rollback, or residual-risk evidence when materially relevant.
- Workflow distinctions remain explicit despite shared phase names.

### Cycle 6 — C_CHORE_DOCS

**Goal:** Keep Chore and Docs as the lightest appropriate workflows.

**Deliverables:**

- **D_CHORE_CONTRACTS:** Rewrite four non-Ready Chore effective contracts.
- **D_DOCS_CONTRACTS:** Rewrite two non-Ready Docs effective contracts.
- **D_CHORE_DOCS_AUDIT:** Complete six C01-C23 audit records.

**Test strategy:**

- Run focused loader, Chore workflow, and relevant documentation-alignment tests.
- Chore uses focused existing checks and adds tests only for changed durable behavior.
- Docs validates documentation, links, examples, generation, and source parity without production-code TDD.

**Exit criteria:**

- All six contracts pass C01-C23.
- Chore remains lightweight while retaining validation and deferred-work responsibilities.
- Docs Planning and Documentation remain bounded to documentation delivery.
- Both workflows use the canonical hand-over without inheriting irrelevant fields.

### Cycle 7 — C_EPIC

**Goal:** Keep Epic coordination mechanical while preserving cross-issue acceptance and integration obligations.

**Deliverables:**

- **D_EPIC_CONTRACTS:** Rewrite Research, Planning, Design, Coordination, and Documentation effective contracts.
- **D_EPIC_AUDIT:** Complete five C01-C23 audit records.

**Test strategy:**

- Run focused Epic loader and workflow tests.
- Use semantic C21 evidence for Coordination; do not add a wording-lock test for intentional brevity.

**Exit criteria:**

- All five contracts pass C01-C23.
- Epic phases define cross-workstream boundaries, child acceptance, shared contracts, and integration proof.
- Coordination remains concise and does not duplicate host workflows, skills, or commands.
- Epic does not create child implementation tests inside the epic contract.

### Cycle 8 — C_ALIGNMENT

**Goal:** Close implementation evidence without repeating full validation.

**Deliverables:**

- **D_AUDIT_COMPLETE:** Complete and inspect all 39 audit records.
- **D_METRICS_FINAL:** Rerun parsed instruction, hand-over, and combined metrics using the research method.
- **D_CONTRACT_INVARIANTS:** Verify count, hand-over presence, canonical structure, Ready equality, cycle semantics, artifact activations, workflow distinction, and prohibited QA/orchestration patterns.
- **D_AGENT_PARITY_FINAL:** Verify all relevant authoritative-to-derived pairs and current agent authority semantics.
- **D_LIVE_CONTEXT:** Restart the server once and perform focused live `get_work_context` smoke checks after startup-loaded configuration changes.

**Test strategy:**

- Run focused contract loader, resolver, discovery, workflow, and agent-source parity suites.
- Run branch-scoped quality gates once after all Python test edits.
- Do not run the full workspace suite in Implementation; reserve one full run for Validation.

**Exit criteria:**

- All 39 contracts pass C01-C23 with no concealed failure or unjustified `N/A`.
- Final instruction-plus-hand-over character and lexical-proxy totals are below baseline without semantic loss.
- No hardcoded harness orchestration, model version, parent-owned QA verdict, or QA-driven automatic progression remains.
- Source-consumer parity and live config loading are proven.
- Implementation evidence is ready for independent Validation.

---

## Later-Phase Obligations

### Validation

- **V_FULL_TESTS:** Run the complete workspace test suite once against the final implementation state.
- **V_QUALITY:** Run applicable branch quality gates and inspect cached structured evidence.
- **V_CONTRACT_REVIEW:** Independently assess all 39 audit records, final diff, strategy preservation, test-code quality, and live context behavior.
- **V_DEFERRED:** Identify residual or deferred work explicitly for Ready triage.

Validation produces evidence first. A producer-owned preflight may report findings but cannot provide the authoritative GO/NOGO.

### Documentation

- **DOC_AGENT_MODEL:** Update [Agent Instructions Model](../../reference/copilot-agent-instructions-model.md) to reflect workflow-driven delegation, QA invocation authority, anti-anchoring, and hand-over ownership.
- **DOC_WORKFLOW_GUIDE:** Reconcile [Workflow Extension Guide](../../reference/workflow-extension-guide.md) with the final compact contract and test policy where needed.
- **DOC_RELEASE_ASSETS:** Update [Release Assets Procedure](../../reference/release-assets-procedure.md) only if validated source-consumer behavior changes.
- **DOC_CURRENT_ONLY:** Update current documentation and active instruction sources; do not produce a migration diary or rewrite archives.

### Ready

Reuse current Validation evidence while it remains fresh. Actively surface deferred work in the PR body, inspect final branch state and diff, and submit the PR. Do not rerun the full suite merely because Ready started; rerun only when post-validation changes invalidate evidence.

---

## Dependencies

| Cycle | Depends on | Reason |
|---|---|---|
| C_AGENT_AUTHORITY | Final research | Static authority must match the Approved Strategy before contract work |
| C_READY | C_AGENT_AUTHORITY | Establishes common terminal and hand-over invariants |
| C_FEATURE | C_READY | Uses the established hand-over skeleton |
| C_BUG | C_FEATURE | Reuses proven mechanics while retaining Bug semantics |
| C_REFACTOR_HOTFIX | C_BUG | Applies stable mechanics to preservation and containment workflows |
| C_CHORE_DOCS | C_REFACTOR_HOTFIX | Applies stable mechanics to lightweight workflows |
| C_EPIC | C_CHORE_DOCS | Completes the specialized coordination workflow last |
| C_ALIGNMENT | C_EPIC | Requires all 39 effective contracts and consumers in final form |

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Compression removes an activation obligation that enforcement does not initiate | Apply C14 and record retained activations before accepting each contract |
| Cross-workflow normalization erases intentional distinctions | Use workflow-driven cycles and require C02 evidence per contract |
| Canonical hand-overs become generic and unhelpful | Standardize headings only; retain phase/workflow-specific fields and proportional links |
| Permanent wording tests create a second semantic SSOT | Automate only durable structural invariants; keep semantic evidence in the audit ledger |
| Broad agent synchronization causes source/consumer drift | Edit authoritative host sources first and verify topology-based byte parity |
| Current active instructions contradict the Approved Strategy during execution | Complete C_AGENT_AUTHORITY before runtime contract cycles |
| Implementation uncovers a need for production Python changes | Stop and request human approval; do not silently expand scope |
| Repeated full gates inflate time and token cost | Use focused checks per cycle, one branch gate after Python edits, and one full suite in Validation |

## Stop-Go Criteria

Implementation may start when:

- the eight-cycle structure and deliverable IDs are approved;
- no Approved Strategy ambiguity remains;
- all 39 contracts are accounted for exactly once;
- the audit ledger and canonical hand-over skeleton are accepted as execution constraints;
- no production-code change is assumed.

Implementation stops and returns to the user when:

- a contract cannot pass C01-C23 without changing supported behavior or phase membership;
- the Approved Strategy proves technically unsound;
- a Python production change or runtime composition mechanism appears necessary;
- authoritative agent sources cannot be mapped safely to their consumers;
- a durable test would require duplicating natural-language semantics as code.

## Related Documentation

- [Research and Approved Strategy](research.md)
- [Runtime contracts](../../../.pgmcp/config/contracts.yaml)
- [Agent Instructions Model](../../reference/copilot-agent-instructions-model.md)
- [Workflow Extension Guide](../../reference/workflow-extension-guide.md)
- [Release Assets Procedure](../../reference/release-assets-procedure.md)
- [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)
- [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)
- [Type Checking Playbook](../../coding_standards/TYPE_CHECKING_PLAYBOOK.md)

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-08-20 | Agent | Initial scaffold |
| 0.2 | 2026-08-20 | Agent | Add eight-cycle execution plan, 39-contract coverage, audit evidence, hand-over skeleton, and proportional verification |
| 1.0 | 2026-08-20 | Agent | Approve the implementation plan after human review |

<!-- docs\development\issue399\validation.md -->
<!-- template=validation_report version=fe38a66d created=2026-08-20T14:18Z updated=2026-08-20 -->
# Issue #399 Validation: Audit and Streamline Phase Instruction Contracts

**Status:** DEFINITIVE  
**Version:** 1.0  
**Last Updated:** 2026-08-20  
**Validation Outcome:** PENDING INDEPENDENT QA  
**Issue:** #399  
**Cycle:** Branch-wide Refactor validation  

---

## Scope

Validate branch-wide structural completion, preservation of the Approved Strategy,
workflow-contract semantics, agent source-consumer alignment, test quality, and
verification evidence. Validation assesses evidence only; it does not redesign, patch,
or issue the independent GO/NOGO verdict.

## Authoritative Inputs

- [Research and Approved Strategy](research.md) is FINAL.
- [Planning](planning.md) is APPROVED and accounts for all eight implementation cycles
  and all 39 effective contracts.
- [Contract audit](contract-audit.md) is corrected after the independent QA NOGO and
  explicitly marks all producer records as non-authoritative pending re-review.
- `get_project_plan(issue_number=399)` reports Research, Design, Planning, and
  Implementation completed and Validation active.
- The implementation correction commit is `6d6506be806a13eaacb731c00c1d13504db165e7`.

### Design artifact caveat

No separate `design.md` exists. This does not conceal an unfinished production-code
design cycle: the approved scope excludes production Python and runtime composition,
and the design constraints are carried directly by the Research Approved Strategy and
the approved Planning decisions. Independent QA must still assess whether this
issue-specific evidence is sufficient for the completed Design state.

## Branch Inventory

The branch diff against `main` contains 39 files, 4,704 insertions, and 3,768 deletions.
The changed surfaces are:

- runtime contract SSOT: [.pgmcp/config/contracts.yaml](../../../.pgmcp/config/contracts.yaml);
- authoritative host agent sources under [docs/agents](../../agents/) and their active
  `.agents`, `.github`, and root consumers;
- durable contract and source-consumer tests:
  [test_contracts_loader.py](../../../tests/mcp_server/unit/config/test_contracts_loader.py)
  and
  [test_agent_instruction_search_contract.py](../../../tests/documentation/test_agent_instruction_search_contract.py);
- issue evidence: [Research](research.md), [Planning](planning.md),
  [contract audit](contract-audit.md), and this report;
- workflow-owned `.pgmcp` state and deliverable metadata.

No production Python file changed.

## Deliverable and Cycle Mapping

| Planned scope | Validation evidence |
|---|---|
| C_AGENT_AUTHORITY | Host-authoritative agent sources and active consumers are included in the branch; parity and QA-bootstrap behavior are exercised by the documentation contract tests. |
| C_READY | Seven Ready contracts are textually equal, workflow-neutral, and covered by strict loader invariants. |
| C_FEATURE | Six non-Ready Feature contracts and their audit records are present. |
| C_BUG | Six non-Ready Bug contracts and their audit records are present. |
| C_REFACTOR_HOTFIX | Six Refactor and three Hotfix contracts and their audit records are present. |
| C_CHORE_DOCS | Four Chore and two Docs contracts include executable scaffolding, strict transfers, and explicit Chore Research intake. |
| C_EPIC | Five Epic contracts include executable scaffolding and strict canonical transfers; Coordination remains intentionally concise. |
| C_ALIGNMENT | The audit contains 39 reconciled records, final metrics, strict invariants, source-consumer evidence, and live server context evidence. |

All 39 configured effective contracts are represented exactly once in Planning and the
audit ledger. The audit-to-runtime metric reconciliation reports 39 of 39 matches and
zero mismatches.

## Strategy and Invariant Assessment

| Approved boundary | Evidence |
|---|---|
| Preserve local inline contracts | No YAML anchors, aliases, generated composition, or runtime composition were introduced. |
| Preserve 39 workflow-phase contracts | Loader tests enumerate 39 contracts and the audit reconciles all 39. |
| Workflow-driven semantics | Workflow-specific Research, Design, Planning, Implementation, Validation, Documentation, and Coordination responsibilities remain in the runtime SSOT. |
| Canonical hand-overs | Tests require the exact workflow/phase title and exact `####` section order for every non-Ready contract. |
| Ready equality without false phase assumptions | All seven Ready contracts are equal and derive evidence from the selected workflow rather than assuming Validation or a universal full suite. |
| Executable artifact activation | Docs Planning and Epic Research, Planning, and Design require schema discovery plus schema-complete scaffold context. |
| Explicit Chore transfer | Chore Implementation accepts and verifies either a persisted Research artifact or the direct Research hand-over and stops when neither exists. |
| Test-code durability | The branch changes two existing structural test modules; it adds no per-sentence or per-contract prose-lock test suite. |
| QA anti-anchoring and authority | Authoritative and derived QA instructions treat caller claims as non-binding, require direct evidence, and separate advisory preflight from independent GO/NOGO. |
| Server-owned context bootstrap | Runtime contracts contain no redundant `get_work_context` activation; the server-enforced bootstrap remains external to phase text. |

## Verification Evidence

### Full workspace tests

- Call: `run_tests(scope='full', timeout=900, coverage=false)`
- Result: **2,775 passed, 2 skipped, 1 xpassed, 25 warnings, 0 failed,
  0 errors in 48.40 seconds**.
- Cached evidence: `pgmcp://cache/runs/f8d3291eff6a49e996e5711553ecdfe0`.
- This was the single full workspace run required by Planning and Validation.

### Branch quality gates

- Call: `run_quality_gates(scope='branch', verbose=true)`
- Result: **overall pass**; two quality-relevant Python files selected.
- Ruff format: passed; two files already formatted.
- Ruff strict lint: passed; no findings.
- Import validation: passed; no findings.
- Line length: passed; no findings.
- Pyright 1.1.408: passed; two files analyzed, zero errors, warnings, or
  information diagnostics.
- Non-matching type gates were correctly skipped.
- Cached evidence: `pgmcp://cache/runs/ddfee38aeb9647eda6e0d19e563e2eb4`.

### Focused structural evidence

The full suite includes the previously focused 74 runtime-contract loader and
agent-source/consumer tests. No additional targeted test was added or rerun because the
full suite and branch gates exposed no material behavioral proof gap. A direct link check
resolved all 16 Markdown links in this report with zero missing targets.

### Live context

After the final contract correction, the server restarted successfully and
`get_work_context` returned the rewritten Refactor contract without duplicated
server-owned bootstrap text. After the phase transition it returns the active Refactor
Validation contract from `state.json` with high confidence.

## Independent QA NOGO Correction Mapping

| QA finding | Corrected evidence |
|---|---|
| Ready invalid for Docs and Epic | Ready now uses workflow-required evidence from completed phases and does not universally require Validation or a full suite. |
| Artifact scaffolds not first-time-right | Docs Planning and Epic Research, Planning, and Design discover schemas and pass explicit context. |
| Eleven transfers non-canonical | All eleven use exact titles and `####` headings; strict tests reject the former permissive form. |
| Chore Research outcome ambiguous | Chore Implementation accepts artifact or direct hand-over and stops if neither is available. |
| Audit overclaimed PASS | Every record is producer-corrected, non-authoritative, and pending fresh independent re-review. |

## Failures, Risks, and Caveats

- No test or quality-gate failure was observed.
- The full suite reported 25 warnings. The structured run evidence exposes the count but
  no warning categories; no criterion was weakened and no second full run was performed.
- No standalone Design artifact exists; the rationale and evidence boundary are recorded
  above for independent assessment.
- Epic Coordination grew from 398 to 969 effective characters because the former
  transfer lacked canonical evidence and authority fields. The total effective-contract
  surface still decreased from 182,684 to 91,516 characters (49.90%).
- Semantic acceptance of all 39 contracts remains an independent QA responsibility;
  green structural tests do not prove natural-language quality.

## Deferred Work and Next-Phase Obligations

**Deferred work for Ready/@co triage:** None identified from branch behavior, tests,
gates, structural inspection, or strategy alignment.

The following are not deferred work:

- independent QA re-review is the required review boundary for this Validation output;
- current reference-document reconciliation belongs to the planned Documentation phase;
- Ready must reuse this evidence while fresh and surface any later deferred work in the
  pull-request body.

## Demonstration and Fallback

The closest observable demonstration is live `get_work_context` delivery from the
restarted server plus successful parsing and execution of the complete workspace suite.
If independent QA finds a semantic contract defect, return to Implementation and correct
the smallest affected contract, test invariant, and audit record; any correction
invalidates this Validation evidence and requires proportionate revalidation.

## Outcome

Validation evidence is complete and contains no producer-identified blocker. The report
does not claim GO. Independent QA must inspect the direct branch evidence and determine
GO/NOGO.

## Related Documentation

- [Research and Approved Strategy](research.md)
- [Planning](planning.md)
- [Contract audit](contract-audit.md)
- [Runtime contracts](../../../.pgmcp/config/contracts.yaml)
- [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)
- [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 0.1 | 2026-08-20 | Agent | Initial scaffold |
| 1.0 | 2026-08-20 | Agent | Record branch-wide Validation evidence and independent-review boundary |

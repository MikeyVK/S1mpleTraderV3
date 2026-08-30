<!-- docs\development\issue460\README.md -->
<!-- template=generic_doc version=43c84181 created=2026-08-27T09:08Z updated=2026-08-27 -->
# Issue 460 Pre-Implementation Documentation Contract

**Status:** DEFINITIVE  
**Version:** 1.5  
**Last Updated:** 2026-08-30

---

## Purpose

This issue-local contract defines the required structure, ownership, traceability, and
lifecycle of the Research and Design documentation for issue #460. It exists to keep a
large pre-implementation evidence and decision set navigable without creating a
monolithic Design document or duplicating authority across files.

## Scope

### In Scope

- the topology and responsibility of every Research and Design document for issue #460;
- the distinction between navigation, evidence, decisions, contracts, and review history;
- mandatory section and traceability rules for Design documents;
- the collaboration workflow used to draft, integrate, and review Design decisions;
- conflict resolution and change control inside the pre-implementation set.

### Out of Scope

- implementation code, production migrations, and concrete implementation sequencing;
- Planning cycles, commit boundaries, and task estimates;
- repeating evidence inventories already owned by the Research documents;
- deferred feature work excluded by [Deferred Work](deferred-work.md);
- repository-wide documentation conventions beyond issue #460.

## Contract Position

This README is the **form and navigation authority** for issue #460 pre-implementation
documentation. It does not replace the content authority of Research or Design.

The authority order is:

1. the active phase instructions returned by `get_work_context` govern the current
   workflow actions;
2. [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md) and
   [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md) remain
   binding;
3. [Research](research.md) owns the Research gate, invariants, expected results, and
   Approved Strategy;
4. Research companion documents own their named evidence, inventories, exclusions, and
   Design intake;
5. the planned `design.md` owns Design rationale, integration status, decision
   navigation, and whole-set coverage;
6. each Design package document owns the exact decisions and contracts assigned to it
   below;
7. Planning will later own implementation order, cycles, and deliverable scheduling.

A summary may point to an authoritative decision, but may not restate it as a second
source of truth.

## Research Documentation Structure

Research closed definitively on 2026-08-30 after the user reported that the independent
QA authority approved the third narrowly bounded F-10/F-11 ownership correction. The
approved two-fingerprint direction and compact persisted artifact provenance remain
unchanged; only the overbroad PGMCP promise for historical retention and lookup is
removed. The unconditional Design GO dated 2026-08-29 remains historical evidence for
the superseded first-amendment interpretation. The targeted 2026-08-30 confirmation
supersedes the later pending gate and authorizes Design to continue.

| Document | Authority and Responsibility |
|---|---|
| This README | Form, topology, navigation, and ownership rules for the pre-implementation set |
| [research.md](research.md) | Canonical Research conclusion, Approved Strategy, invariants, expected results, gate status, and Research hand-over |
| [research-findings.md](research-findings.md) | Detailed findings, evidence, implications, and design obligations |
| [template-suite-catalog.md](template-suite-catalog.md) | Complete public artifact, suite-file, consumer, and test/helper inventories and dispositions |
| [probe-evidence.yaml](probe-evidence.yaml) | Reproducible structured probe observations; evidence rather than policy |
| [deferred-work.md](deferred-work.md) | Explicit exclusions and post-issue work that Design must not absorb |
| [design-intake-map.md](design-intake-map.md) | Authoritative routing from findings, strategies, invariants, expected results, consumers, and removals into DI-01–DI-08, XC-01–XC-02, and RC-01 |
| [research-to-design-qa-audit.md](research-to-design-qa-audit.md) | Independent point-in-time Research review history; the user separately reported targeted independent QA approval of the third ownership correction on 2026-08-30, so no Research gate remains pending |
| [validation-quality-gates-brainstorm-handover.md](validation-quality-gates-brainstorm-handover.md) | Historical exploratory input for the validation/quality boundary; not a current gate or Design authority |

Research documents retain detailed ledgers. Design documents reference their stable IDs
and source sections instead of copying those ledgers.

## Design Documentation Structure

Design uses a hub-and-spoke structure. The hub integrates the phase; the package
documents own the detailed decisions. Files marked **planned** are created only when the
corresponding workshop has produced a stable decision nucleus.

| Document | Design Ownership | Initial Status |
|---|---|---|
| `design.md` | Thin Design hub: rationale, package register, dependency and decision indexes, whole-set coverage, integration risks, and Design hand-over | Planned |
| `design-shared-contracts.md` | Exact interfaces, DTOs, configuration shapes, status vocabularies, and interaction rules genuinely shared by multiple package documents | Planned |
| `design-suite-resolution.md` | DI-01 suite contract metamodel and public schema exposure; DI-02 resolved graph, runtime selection, introspection, and provenance | Planned |
| `design-mutation-validation.md` | DI-04 scaffold/safe-edit mutation orchestration and persistence; DI-05 factual output-validation capabilities and quality orchestration | Planned |
| `design-document-tracking-artifacts.md` | DI-03 contracts and renderer semantics for documentation, issue, PR, commit, planning, validation-report, and related tracking artifacts | Planned |
| `design-code-test-artifacts.md` | DI-03 contracts and renderer semantics for production-code and public unit/integration-test artifact families | Planned |
| `design-distribution.md` | DI-06 package distribution, renewal, customization, adoption, and owner-deployment migration | Planned |
| `design-workflow-documentation.md` | DI-07 workflow semantics, phase-document carriers, agent-instruction alignment, and active documentation authority | Planned |
| `design-test-architecture.md` | DI-08 shared repository test fixtures/helpers and cross-package assurance; XC-02 removal-completeness integration | Planned |

### Boundary Between the Two Test Concerns

The distinction is normative:

- public scaffolded test artifact contracts belong to
  `design-code-test-artifacts.md` under DI-03;
- repository test fixtures, helper APIs, reusable test architecture, and cross-package
  removal assurance belong to `design-test-architecture.md` under DI-08;
- DI-01–DI-07 retain ownership of their package-specific behavioral evidence, migration
  tests, and concrete removals even when they consume DI-08 infrastructure.

## Document Ownership Rules

1. Every decision and exact contract has one authoritative owner.
2. `design-shared-contracts.md` owns only contracts consumed by more than one package.
   Package-local interfaces and representations stay in the owning package document.
3. A consuming document links to a shared or upstream contract and records its local
   consequence; it does not reproduce the contract.
4. `design.md` records decision status and integration consequences but does not become
   a second detailed design.
5. The [Design Intake Map](design-intake-map.md) remains authoritative for package
   routing. A Design document may refine a boundary but may not silently move ownership.
6. XC-01 and RC-01 apply as binding constraints throughout. XC-02 is integrated through
   the owning package documents and audited by DI-08.
7. Conditional catalog dispositions must be resolved in their owning Design package,
   not left as unassigned Planning work.
8. Deferred work is linked, not redesigned.
9. No Design document may introduce a compatibility strategy that conflicts with the
   Approved Strategy. New evidence that invalidates it stops the affected design thread
   and reopens the decision explicitly.

## Required Design Document Contract

Every detailed Design document must contain the following sections. A section that is
not applicable is retained with a short rationale rather than silently omitted.

1. **Purpose and Authority** — the exact decisions the document owns.
2. **Scope and Exclusions** — included boundaries, consumers, and deliberate exclusions.
3. **Binding Inputs** — linked findings, Approved Strategy rows, invariants, expected
   results, intake obligations, Architecture Principles, and upstream contracts.
4. **Owned Decisions** — a concise decision register with stable local IDs and status.
5. **Responsibilities and Boundaries** — production and test responsibilities, ownership,
   dependencies, and composition-root placement.
6. **Options and Rationale** — materially viable alternatives, trade-offs, chosen option,
   and rejected options.
7. **Detailed Design** — exact components, interfaces, DTOs, configuration, schemas,
   status semantics, and algorithms owned by the document.
8. **Control, Data, and State Flow** — success, failure, unavailable, and
   not-executed paths where applicable.
9. **Compatibility, Migration, and Removal** — preservation or clean-break behavior,
   cutover, concrete legacy removals, and absence-of-old-path proof.
10. **Test and Validation Design** — package-owned behavioral evidence, shared DI-08
    dependencies, self-hosting risks, and independent proof obligations.
11. **Integration Risks and Open Questions** — only unresolved Design work; no hidden
    implementation TODOs.
12. **Planning Consequences** — deliverable boundaries and ordering constraints without
    defining Planning cycles.
13. **Traceability Matrix** — exact coverage of owned DI/XC/RC obligations, findings,
    strategy rows, invariants, expected results, consumers, and conditional dispositions.
14. **Related Documentation and Version History**.

Each detailed document header must also state its primary DI package or packages,
upstream dependencies, downstream consumers, and lifecycle status.

## The Design Hub Contract

The planned `design.md` remains deliberately thin. It owns:

- the overall Design rationale and selected document topology;
- a package-status register using `Not started`, `Drafting`, `Decided`, or
  `Integrated`;
- the dependency order and cross-document integration decisions;
- a decision index that points to the exact owning document and section;
- consolidated coverage accounting for all 21 findings, 43 Approved Strategy rows,
  16 invariants, 20 expected results, DI-01–DI-08, XC-01–XC-02, and RC-01;
- unresolved conflicts, integration risks, and the final Design hand-over.

It does not own copied component designs, repeated inventories, implementation cycles,
or a second rendering of package-local contracts.

## Traceability Rules

- Use the existing `F-*`, `I-*`, `E-*`, `DI-*`, `XC-*`, and `RC-*`
  identifiers; do not invent aliases for the same obligation.
- Identify Approved Strategy rows by their existing finding/strategy wording and link to
  the canonical table.
- Every Design decision has one local stable ID and one owning section.
- Every detailed Design document ends with an explicit coverage matrix.
- `design.md` aggregates coverage by reference and flags gaps or duplicate ownership;
  it does not copy the detailed matrices.
- Inventory totals and file ledgers are read from the Research owners. Design records
  only dispositions and impacts that it owns.
- A requirement is covered only when the document defines the resulting structure,
  behavior, or proof obligation. A bare link is navigation, not coverage.

## Hands-On Collaboration Workflow

Design proceeds as a sequence of bounded workshops:

1. select one coherent package boundary and load only its authoritative Research inputs;
2. agree interactively on the problem framing, alternatives, and stable decision
   nucleus;
3. scaffold the owning Design document once that nucleus is stable;
4. refine the document through small reviewed edits, keeping exact contracts with their
   single owner;
5. update the `design.md` decision, dependency, status, and coverage indexes;
6. run a cross-document consistency check before declaring the package `Integrated`;
7. repeat for the next package in dependency order;
8. perform a final whole-set traceability, removal, and contradiction audit before the
   independent Design review.

This lets the user shape decisions hands-on without requiring the entire Research corpus
or the entire Design set to be rewritten in every conversational step.

## Recommended Workshop Order

The default order follows dependency pressure rather than filename order:

1. Design hub skeleton and shared contract vocabulary.
2. DI-01/DI-02 suite contract and resolved-graph design.
3. DI-03 concrete artifact contracts, split across its two documents.
4. DI-05 factual validation contract, then DI-04 mutation policy around those facts.
5. DI-08 shared test architecture and XC-02 assurance.
6. DI-06 distribution and migration.
7. DI-07 workflow/documentation alignment after public decisions stabilize.
8. Cross-package integration and final Design hand-over.

The order may change when new evidence requires it, but ownership does not change
implicitly.

## Conflict and Change Protocol

When two documents disagree:

1. stop work on the affected dependent decision;
2. identify the authoritative owner using this README and the Design Intake Map;
3. update the owning document first;
4. record downstream consequences in each consumer without duplicating the contract;
5. update the `design.md` indexes and coverage;
6. explicitly reopen human approval if the Approved Strategy would change.

Changes to this README that alter document ownership, topology, or the required document
contract require explicit human agreement. Routine link, status, and version-history
maintenance does not.

## Completion Criteria

The pre-implementation documentation contract is satisfied when:

- Research gate status matches the canonical Research artifact, including any active amendment review;
- every Research artifact has a single stated responsibility;
- every Design package and cross-cutting obligation has one detailed owner;
- all detailed Design documents conform to the required section contract;
- the Design hub proves complete, non-duplicated traceability;
- cross-document contracts have one authority and all consumers link to it;
- no historical reservation is presented as an active gate;
- no deferred, Planning, or implementation work is silently absorbed into Design.

## Related Documentation

- [Research](research.md)
- [Research Findings](research-findings.md)
- [Template Suite Catalog](template-suite-catalog.md)
- [Design Intake Map](design-intake-map.md)
- [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)
- [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.5 | 2026-08-30 | `@imp researcher` | Record the user-reported targeted independent QA approval, close the Research gate, and index the unconditional Design GO. |
| 1.4 | 2026-08-30 | `@imp researcher` | Index the third F-10/F-11 ownership correction, record that the QA finding is addressed, and retain targeted independent confirmation as the active gate. |
| 1.3 | 2026-08-30 | `@imp researcher` | Reflect the second F-10/F-11 Research reopening and mark the prior QA GO as point-in-time evidence pending fresh review. |
| 1.2 | 2026-08-29 | `@imp researcher` | Record the independent amendment review and unconditional GO to resume Design with global-provenance reconciliation first. |
| 1.1 | 2026-08-29 | `@imp researcher` | Reflect the bounded F-10/F-11 Research reopening and require current gate status to follow the canonical Research artifact. |
| 1.0 | 2026-08-27 | `@imp designer` | Establish the issue-local Research and Design documentation topology, ownership rules, required Design sections, traceability contract, and hands-on workshop workflow. |

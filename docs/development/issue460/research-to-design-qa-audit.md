<!-- docs/development/issue460/research-to-design-qa-audit.md -->
<!-- template=generic_doc version=43c84181 created=2026-08-25T14:44Z updated=2026-08-25 -->
# Issue #460 Research-to-Design QA Audit

**Status:** DEFINITIVE REVIEW HISTORY — AMENDMENT DESIGN GO  
**Version:** 1.2  
**Last Updated:** 2026-08-29  
**Review Authority:** Independent `@qa design-reviewer`  
**Recorded By:** `@imp researcher`, without substantive alteration of the historical QA verdict  
**Current Applicability:** Unconditional Design GO for the 2026-08-29 F-10/F-11 amendment; the original NOGO remains historical

---

## Supersession Notice

This audit preserves the independent point-in-time NOGO issued before the original Research reconciliation and records both later independent GO decisions. The original remediation was closed on 2026-08-27. Design then exposed an unsound F-10/F-11 identity boundary, Research was reopened for that boundary only, and fresh independent QA granted an unconditional GO on 2026-08-29. Historical wording is retained as evidence and must not be interpreted as current debt or an open gate. [Research](research.md) and the [Design Intake Map](design-intake-map.md) own the current closed status and active mandate.

## Purpose

Record the independent QA assessment of the issue #460 research set, with particular emphasis on substantive completeness, Design coverage, and the feasibility and manageability of the downstream phases.

## Scope

### In Scope

- Substantive quality and traceability of the Research evidence.
- Completeness and accessibility of the mandate passed to Design.
- Scope governance, compatibility decisions, and deferred work.
- Feasibility and manageability of Design, Planning, Implementation, Validation, and Documentation.
- Compliance of the Research deliverables and hand-over with the active workflow contract.

### Out of Scope

- Approval of a target architecture.
- Selection or sequencing of implementation cycles.
- Production-code verification.
- Authorization to start Design despite unresolved Research blockers.

## Historical Verdict — Superseded

**Point-in-time verdict on 2026-08-25: NOGO for the Research-to-Design transition in the form reviewed at that time. This verdict has been superseded by the unconditional Design GO.**

This is not a rejection of the substantive Research quality. The evidence base is strong and largely complete. The blocking concern is that the evidence has not yet been converted into a bounded, explicit, and auditable Design mandate. Design would currently need to regroup the Research, reconstruct scope decisions, and establish coverage itself. That would make Design repeat part of Research and prematurely perform Planning work.

## Executive Assessment

The Research set provides a broad and credible evidence base:

- 18 executive findings;
- 43 approved strategy boundary rows;
- 20 expected results;
- 16 core invariants;
- 79 template-suite files;
- 102 active runtime, setup, agent, standards, manual, and reference consumers, plus two binding source rows outside that census;
- 105 test and helper candidates.

The authority hierarchy, finding classification, probe semantics, deferred feature treatment, inventory traceability, and preservation analysis have materially improved. The Research does not require another bottom-up discovery cycle.

The principal deficiency is delivery governance: five high-level Design-owned questions do not expose demonstrable coverage of the 43 strategy boundaries and the wider consumer inventory. The Design scope is therefore substantively present but operationally under-specified.

## Findings

### QA-460-01 — [P0] The complete Design scope is not explicitly exposed

The primary Research contains 43 strategy boundary decisions and 20 expected results, but its Design-owned question set contains only five high-level questions. Those questions identify important abstraction areas, yet they do not establish one-to-one or package-level coverage of all approved strategies, invariants, consumers, removals, migrations, and proof obligations.

Only F01 through F11 have individual `Design hand-off` sections in the evidence companion. F12 through F18 and several later cross-cutting strategies do not have equivalent hand-offs.

Without a canonical coverage map, an independent reviewer cannot determine whether Design deliberately addressed every Research obligation or merely covered the most visible subjects.

**Required correction:** add one authoritative **Design Intake Map**. Each Design package must identify:

- related findings and approved strategy rows;
- governing invariants;
- affected responsibilities, boundaries, consumers, and interfaces;
- decisions owned by Design;
- dependencies on other Design packages;
- compatibility, migration, and removal constraints;
- required proof and test obligations;
- explicit exclusions and deferred work.

This map is a Research-to-Design scope index, not an implementation plan.

### QA-460-02 — [P0] Late scope expansion is not governed as a separate boundary

The approved strategies introduce two high-impact concerns beyond the original issue nucleus:

1. a shared output-validation and quality-gate authority;
2. transactional post-edit validation behavior for `safe_edit`.

Together these affect `safe_edit`, `ValidationService`, `QAManager`, `run_quality_gates`, quality configuration, validator registration, output profiles, and result models. They alter public behavior and expand the architecture and validation blast radius substantially.

These concerns are not represented as fully independent findings with their own classification, option analysis, consumer impact, compatibility strategy, and explicit human scope-packaging decision. The proposed single injected capability catalog and normalized executor also approaches a target-architecture decision rather than remaining solely a Research seam.

**Required correction:** either:

- defer and split these concerns into a separately governed refactor; or
- retain them within issue #460 as an explicit Design package with its own compatibility, migration, validation, and self-hosting evidence obligations.

The scope choice must be human-approved before Design starts.

### QA-460-03 — [P1] The formal Research hand-over is absent

The active Refactor Research contract requires an outcome-neutral `Refactor / Research Hand-over` with Scope, Deliverables, Evidence, Open Work, and Review Request sections. No such hand-over is present in the issue460 Research set.

This omission is material because the hand-over should be the navigation and evidence index between the large Research set and Design. The statement that independent QA is the only remaining Research work is therefore incomplete.

**Required correction:** add the formal hand-over and use it to link the primary Research, evidence companion, catalog, probe evidence, deferred work, this audit, and the Design Intake Map.

### QA-460-04 — [P1] The canonical Approved Strategy table is malformed

A blank line follows the `Workflow/template semantic alignment` row in `research.md`. The `Test-suite architecture compliance` row starts after that blank line.

Under Markdown table semantics, the blank line terminates the table. The later strategy rows consequently render without the canonical table header and are not structurally part of the displayed decision register.

**Required correction:** remove the interruption and verify that every approved strategy row renders within one complete table.

### QA-460-05 — [P1] Several inventory dispositions remain conditional

The catalog claims an explicit retain, adapt, or remove disposition for each component, but several rows still use conditional forms such as:

- adapt or remove;
- rewrite or reduce;
- remove or replace;
- replace or consolidate;
- retain or adapt if still consumed.

These may legitimately be target-architecture decisions. If so, they must not simultaneously appear to be closed Research outcomes.

**Required correction:** label each remaining conditional disposition as `Design decision required`, assign it to a Design Intake Map package, and state its constraints and preservation obligations.

### QA-460-06 — [P2] Deferred-work lifecycle status is inconsistent

`deferred-work.md` remains marked `PRELIMINARY`, while the primary Research states that deferred ownership and Research dispositions are closed.

**Required correction:** align the lifecycle status and wording of the deferred-work register with the primary Research authority.

## Positive Substantive Assessment

The QA review found that earlier weaknesses were largely corrected:

- the primary Research and evidence companion now have a clear authority relationship;
- findings F01 through F18 have a canonical classification;
- F18 is correctly treated as a deferred feature request outside the refactor scope;
- probe evidence contains normalized semantic observations and relevant omitted, null, empty, false, zero, and default cases;
- major runtime claims are linked to source or probe evidence;
- the inventory covers template, runtime, setup, workflow, documentation, agent, and test consumers;
- compatibility, migration, clean-break, retention, and removal strategies are broadly recorded;
- the Research distinguishes the evidence base from target Design ownership.

The remaining work is therefore focused Research reconciliation and packaging, not renewed broad discovery.

## Downstream Feasibility and Manageability

| Phase | Assessment |
|---|---|
| Design | Not manageable in the current form. Designers would need to reclassify 3,461 lines across five Research files and infer missing coverage. |
| Planning | Not responsibly executable until Design packages, dependencies, cutovers, and removals are complete and traceable. |
| Implementation | Not manageable as one undivided change or oversized PR. The surface requires bounded cycles or child issues with explicit integration contracts. |
| Validation | High self-hosting risk if validation and quality-gate infrastructure are changed while also being used as the sole certification mechanism. Independent bootstrap or known-good evidence is required. |
| Documentation | Manageable only after final identifiers, contracts, migration paths, and removals are designed; earlier execution would create substantial churn. |

## Recommended Design Intake Packages

The Design Intake Map should organize the mandate into approximately the following packages:

1. **Suite contract model** — JSON Schema authoring, composition, resolution, artifact descriptions, identifiers, and naming.
2. **Resolved graph and identity** — Jinja dependency graph, startup catalog, fingerprints, provenance, and renewal identity.
3. **Scaffold execution pipeline** — caller/envelope separation, strict validation, rendering, result states, and persistence.
4. **Output-validation capability** — profiles, strictness, availability, and normalized result semantics.
5. **Artifact-family contracts** — document, tracking, and code families; shared primitives; retained contracts; removals; and renames.
6. **Distribution and migration** — official baseline, staged candidates, external or custom roots, and atomic adoption.
7. **Workflow and documentation alignment** — phase carriers, workflow contracts, templates, reference documentation, and generated agent variants.
8. **Legacy removal and test architecture** — removal of parallel scaffold, registry, and validator surfaces; export cleanup; and public-boundary coverage.

The `safe_edit` and broader quality-gate consolidation should preferably become a separate ninth package or a separate issue.

### Dependency Direction

- Package 1 precedes Packages 2, 3, and 5.
- Package 2 precedes Packages 3 and 6.
- Package 4 integrates with Package 3.
- Packages 1 and 5 precede Package 7.
- Packages 1 through 7 provide the inputs for Package 8 and its test architecture.
- Any retained `safe_edit` or quality-gate package requires independent evidence that changed validation infrastructure does not certify itself exclusively.

These are Design coverage dependencies, not implementation-cycle sequencing.

## Historical Remediation Checklist — Completed

All seven remediations were completed before the unconditional Design GO. This is a closure record, not an open checklist.

1. [x] Repair the canonical Approved Strategy table.
2. [x] Add the formal Research hand-over.
3. [x] Add a complete Design Intake Map covering every finding, strategy boundary, invariant, consumer family, and expected result.
4. [x] Convert every conditional catalog disposition into an assigned Design decision with explicit constraints.
5. [x] Obtain a human scope decision for `safe_edit` and the quality-gate consolidation.
6. [x] Align the deferred-work lifecycle status.
7. [x] Complete focused independent QA re-review of coverage, scope governance, and rendered document integrity.

## Original Re-review Outcome

The bounded re-review was completed after the corrections above and returned an unconditional GO for Design. No original Research remediation or transition reservation remained open.

## F-10/F-11 Amendment Re-review — 2026-08-29

Independent QA found no substantive Research blocker. The amended boundary coherently separates three consumer identities: human-readable package version, resolved selected-package fingerprint, and complete-suite management identity. Package-local changes no longer create lateral package effects; transitively reachable shared contributors remain part of provenance; complete-suite identity remains available only to install, baseline, candidate, adoption, and renewal consumers; and exact mechanisms remain Design-owned.

The review identified two follow-up conditions rather than Research blockers:

1. the existing global-provenance decisions in `design-suite-resolution.md` and `design-shared-contracts.md` are superseded and must be the first Design reconciliation;
2. the definitive Research amendment must be committed before the formal phase transition.

**Gate outcome: unconditional GO to resume Design on the amended F-10/F-11 boundary.**

## Evidence Reviewed

- [Primary Research][research]
- [Detailed Research Findings][findings]
- [Template Suite Catalog][catalog]
- [Probe Evidence][probes]
- [Deferred Work Register][deferred]
- GitHub issue #460 scope and acceptance criteria
- Active Refactor Research workflow contract
- Documentation and architecture standards applicable to the researched boundaries

No production tests or quality gates were used as substantive evidence for this audit because the reviewed delta against `origin/main` contained Research documentation and workflow metadata rather than production-code changes.

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.2 | 2026-08-29 | Independent QA; recorded by `@imp researcher` | Record the bounded F-10/F-11 amendment review, its unconditional Design GO, and the mandatory first Design reconciliation. |
| 1.1 | 2026-08-27 | `@imp designer` | Preserve the original verdict as historical evidence while recording completed remediation and the superseding unconditional Design GO. |
| 1.0 | 2026-08-25 | Independent QA; recorded by @imp | Initial definitive Research-to-Design audit |

[research]: research.md
[findings]: research-findings.md
[catalog]: template-suite-catalog.md
[probes]: probe-evidence.yaml
[deferred]: deferred-work.md

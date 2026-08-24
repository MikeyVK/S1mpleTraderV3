# Research: Issue 460 — Scaffolding Schema–Template Rendering Contract Audit

**Status:** REVIEW — RESEARCH OPEN  
**Version:** 2.2  
**Last Updated:** 2026-08-24  
**Issue:** 460  
**Workflow:** Refactor / Research

## Purpose

Establish the observable content, compatibility, ownership, and portability boundaries required for first-time-right scaffolding by humans and LLM callers.

The public caller contract is the output of `scaffold_schema`. Template configuration, Jinja sources, loader and packaging code, tests, and reference documentation are evidence about that contract, not alternative caller authorities.

This document is the sole authority for issue-460 decision status, Approved Strategy, expected results, open work, and the Research gate. Detailed evidence is retained in [Research Findings](research-findings.md).

## Current Status and Gate

Research is open. Inventory and baseline probes are complete, but the catalog has not closed every component disposition.

- Seven public artifact types still require a joint disposition.
- Thirty-eight suite files still carry a pending joint disposition.
- The 103 test/helper candidates still require keep/adapt/remove review.
- Runtime, setup, documentation, and agent consumers require final impact dispositions.
- The Generic Python class responsibility was explicitly approved on 2026-08-24 with an artifact-local body-free boundary.
- No transition to Design is authorized until these obligations close and a new independent QA review returns GO.

## Scope

### In scope

- All 22 artifact types currently exposed through `scaffold_schema`.
- All 79 files in the active packaged template suite.
- Configured and embedded examples, resolved inheritance/import graphs, unreachable sources, and runtime overrides.
- Schema discoverability, representability, determinism, consumption, completeness, optional safety, and portability.
- Runtime, setup, packaging, renewal, test/helper, agent-instruction, and active-documentation consumers.
- Compatibility and migration strategy per affected public boundary.
- Observable responsibilities that must be retained, adapted, or removed.

### Out of scope

- Production fixes or implementation sequencing.
- Target class topology, parser APIs, provider containers, staging paths, or digest serialization.
- Snapshot tests or a server-owned matrix of template-specific prose.
- Cross-repository implementation.
- New YAML or Python artifact types deferred from issue 460.
- Subjective artifact-quality evaluation beyond declared contracts and output profiles.

## Problem Statement

Issue 460 began with four confirmed PR scaffolding defects:

1. `related_docs` has no reliable schema-valid clickable-link representation.
2. `closes_issues` accepts ambiguous strings while the renderer adds its own prefix.
3. `tracking_state` is exposed but not rendered.
4. `checklist_items` cannot express the checked state consumed by the template.

The audit established that these are suite-level contract failures. Some schema-valid values fail during rendering or produce malformed, incomplete, ambiguous, or machine-specific output. Some renderer-required values cannot be constructed from `scaffold_schema`, while other exposed values are ignored.

## Research Questions

1. What does `scaffold_schema` expose for every public artifact type?
2. Can every renderer-consumed value be constructed from that introspection alone?
3. Does every exposed value have one deterministic meaning and observable effect?
4. Do minimal and property-complete valid contexts render substantively correct output?
5. Does the resolved graph include every inherited and imported contract contributor?
6. Can the suite own and evolve its content contract independently from pgmcp-server?
7. Which compatibility, migration, and preservation decisions require human approval before Design?

## Evidence Authority

| Evidence | Authority |
|---|---|
| [Research Findings](research-findings.md) | Detailed observations, option analysis, blast radius, and historical rationale |
| [Template Suite Work Catalog](template-suite-catalog.md) | Complete inventory and per-component disposition state |
| [Probe Evidence](probe-evidence.yaml) | Exact durable minimal/property-complete contexts and outcomes for 44 calls |
| Live `scaffold_schema` and `scaffold_artifact` tools | Reproduction of the current public caller behavior |
| [Deferred Work](deferred-work.md) | All future work explicitly excluded from issue 460 |
| This document | Decision status, Approved Strategy, expected results, open work, and Research gate |

Cached tool resources and ignored temporary outputs are supplementary diagnostics only. They are not durable evidence authorities.

## Executive Findings

| ID | Finding | Human/LLM impact | Affected boundary |
|---|---|---|---|
| F-01 | Nested collection members are absent or typed as strings where templates consume objects. | A caller cannot infer valid shapes; schema-valid inputs can fail or render blank content. | scaffold_schema, template content |
| F-02 | Optional values are normalized to null-equivalent values while templates often distinguish only undefined values. | Omission can become render failure, literal None-like content, or changed defaults. | context preparation, template content |
| F-03 | Unknown caller fields are filtered before strict validation. | Undiscoverable template capabilities cannot be supplied, and caller mistakes can disappear silently. | scaffold_artifact context handling |
| F-04 | The active DTO renderer differs from the template described by the public registration. | scaffold_schema and provenance can describe a renderer that is not used. | runtime selection, provenance |
| F-05 | Inheritance and imports are incompletely analyzed. | Tiered behavior, metadata, and version provenance are not fully visible as one resolved contract. | template graph analysis |
| F-06 | Link-valued fields have no canonical representation and some macros emit unresolved references. | Generated Markdown can contain dead or nested links. | cross-template macros, schema semantics |
| F-07 | Some fields are exposed but ignored; other rendered fields are hidden. | Caller intent is silently lost or only available through undocumented knowledge. | individual artifact contracts |
| F-08 | Several templates produce syntactically invalid source from schema-valid rich contexts. | A successful scaffold operation does not imply a usable artifact. | Python artifact templates |
| F-09 | Reference examples contradict live scaffold_schema responses. | Humans and LLMs receive competing instructions; examples encourage invalid calls. | documentation |
| F-10 | Workspace renewal can update templates while preserving their contract configuration separately. | A valid package can become a mixed-version contract/template installation. | distribution and upgrades |
| F-11 | Current metadata dialects and version hashes do not cover the complete resolved graph. | Consumers cannot reliably determine which semantic contract produced an artifact. | portable suite metadata, provenance |
| F-12 | The four issue-460 PR defects are manifestations of representation ambiguity, not isolated formatting errors. | Local template edits would leave the same failure class elsewhere. | suite-wide content model |
| F-13 | Successful scaffolding can still emit visibly null, blank, concatenated, or machine-specific content. | Callers receive artifacts that require immediate manual repair despite tool success. | cross-cutting acceptance, output profiles, concrete templates |
| F-14 | Some code templates embed project-specific imports and architecture assumptions absent from scaffold_schema. | The advertised generic template suite is not independently reusable in other environments. | template-suite portability |
| F-15 | Absolute host paths are embedded in every generated artifact header. | Output is machine-specific, noisy in review, and can disclose local directory structure. | provenance presentation |
| F-16 | Suite-owned artifact purpose descriptions are dropped by `scaffold_schema`. | Callers see field mechanics but must infer why and when the artifact type is useful. | artifact registry, schema introspection |
| F-17 | Eleven Python- or framework-specific contracts use language-agnostic public IDs. | Callers infer the wrong construct semantics and future language extensions cannot occupy an unambiguous namespace. | public artifact identity, configs, docs, consumers |
| F-18 | Runtime tool schemas enumerate artifact IDs but expose no runtime ID-to-purpose discovery surface. | Agents can see available names but still depend on static docs or guesswork to select the right contract. | MCP discovery, active registry, harness instructions |

## Canonical Finding Classification

This matrix classifies the primary nature and issue-460 disposition of every finding. A finding can have a structural root and still be classified as a behavior defect when a supported or schema-valid call already produces observable failure. The Design hypotheses are navigation inputs only; they are not selected mechanisms.

| ID | Classification | Issue-scope disposition | Observable invariant | Compatibility strategy | Non-binding Design hypothesis |
|---|---|---|---|---|---|
| F-01 | Behavior defect | Required by issue 460 | `scaffold_schema` alone describes every renderer-consumed caller shape | Clean break | Suite-owned resolved standard JSON Schema |
| F-02 | Behavior defect | Equivalent defect | Omitted, null, empty, false, zero, defaulted, and populated values remain distinct | Clean break | Omission-preserving validation and explicit default materialization |
| F-03 | Behavior defect | Enabling correction | Original caller context reaches strict validation unchanged; envelope metadata is merged afterward | Clean break | Separate caller-context and render-envelope stages |
| F-04 | Behavior defect | Required by issue 460 | Public contract, selected DTO renderer, provenance, and validation describe the same artifact | Clean break | One declaratively selected DTO renderer |
| F-05 | Structural debt | Enabling correction | One complete inheritance/import/include graph is resolved consistently for schema, rendering, and identity | Clean break | Parser-supported startup graph resolution |
| F-06 | Behavior defect | Required by issue 460 | One documented link input always produces a complete clickable link | Clean break | Presentation-neutral structured link value |
| F-07 | Behavior defect | Required by issue 460 and equivalent defects | Every exposed caller field is consumed; every rendered caller value is declared | Clean break | Startup input-source and consumption coherence checks |
| F-08 | Behavior defect | Equivalent defect | Every accepted context produces profile-valid output or explicit pre-persistence failure/unavailable evidence | Clean break | Declarative output profile with on-use validator capability resolution |
| F-09 | Structural debt | Enabling correction | Active documentation cannot compete with live schema and catalog facts | Not applicable — authority cleanup | Remove duplication; derive exact views only when retained value is proven |
| F-10 | Structural debt | Enabling correction | Renewal never creates a mixed contract/template suite and never overwrites unproven user customization | Staged migration | One active root with managed baseline and non-authoritative candidate |
| F-11 | Structural debt | Enabling correction | Provenance identity covers the complete resolved graph and caller contract | Clean break | Suite-scoped content-addressed graph fingerprint |
| F-12 | Behavior defect | Required by issue 460 | Issue references and checklist state each have one canonical input representation | Clean break | Positive issue IDs and structured checklist items |
| F-13 | Behavior defect | Equivalent defect | Tool success distinguishes contract, render, validation, persistence, and unavailable evidence | Clean break | Structured result states rather than inferred success |
| F-14 | Behavior defect | Equivalent portability defect | Portable package artifacts contain no hidden consumer-project dependencies | Clean break | Portable package baseline plus workspace-owned specialization |
| F-14A | Structural debt | Enabling correction | Dormant metadata cannot act as duplicate agent/workflow guidance | Clean break | Remove unused pattern/imports and stale commented hints |
| F-14B | Structural debt | Enabling correction | Unreachable placeholders do not imply unsupported test capabilities | Clean break | Remove placeholders; any future fixture capability is explicit and reachable |
| F-15 | Behavior defect | Equivalent portability defect | Generic artifact bodies do not embed their persistence target | Clean break | Report paths through tool/result evidence only |
| F-16 | Structural debt | Enabling correction | Existing suite-owned artifact purpose remains visible through selected-artifact introspection | Preserve existing semantic data | Carry the registered root description through the current introspection response |
| F-17 | Structural debt | Enabling correction | Public identity states language/framework semantics that materially determine the contract | Clean break | Language/technology-qualified IDs; exact names remain Design-owned |
| F-18 | Feature request | Deferred / out of scope | Issue 460 adds no new purpose-aware runtime discovery capability | Deferred decision | Future Research compares a new tool, extension of existing introspection, and documentation-only discovery |

## Core Invariants

1. Every renderer-consumed caller value is discoverable through `scaffold_schema`.
2. Every exposed caller-content field has one declared meaning and an observable rendering effect.
3. The selected schema, renderer, dependency graph, output profile, package identity, and renewal unit remain coherent.
4. Caller context is validated unchanged before render-envelope or server metadata is added.
5. Public client schemas remain finite, self-contained, and reference-free.
6. Optional, omitted, empty, null, and defaulted values remain semantically distinct.
7. Generic package artifacts contain no hidden consumer-project dependencies.
8. Suite-owned content truth does not migrate into artifact-specific pgmcp Python code or prose snapshots.
9. Generated content is portable across machines and does not embed persistence targets by default.
10. Compatibility and migration strategy is explicit per affected boundary.

## Approved Strategy and Decision Status

The table below is the canonical strategy and status register. Supporting rationale and option analysis live in [Research Findings](research-findings.md). A row marked pending is not binding input for Design.

| Boundary | Status | Decision |
|---|---|---|
| F-01 / S-01 public context ownership | Approved 2026-08-23 | Template suite owns complete standard JSON Schema contracts; pgmcp validates and exposes one resolved contract generically |
| F-01 / S-02 nested collections | Approved 2026-08-23 | Structured items replace primitive and opaque forms through a clean break; no compatibility bridge |
| F-01 client compatibility | Approved 2026-08-23 | Client-facing schemas remain self-contained and reference-free; internal composition is acyclic and fail-fast |
| F-02 / S-03 optionality and nullability | Approved 2026-08-23 | Optional permits omission, null is explicit, empty typed values remain distinct, and defaults have deterministic behavior |
| F-03 caller context and render-envelope ownership | Approved 2026-08-23 | Validate caller context unchanged against the selected artifact schema; add validated tool-envelope and server metadata only afterward |
| F-04 / S-08 DTO runtime selection | Approved 2026-08-23 | One declaratively selected richer DTO contract drives schema, rendering, graph identity, and provenance; remove implicit V2 override without a bridge |
| F-05 / S-09 resolved template graph | Approved 2026-08-23 | Server startup resolves one coherent restart-stable suite view through parser-supported Jinja semantics; runtime tools share it, suite mutations require restart, and JSON Schema remains the data-shape authority; concrete APIs and topology remain Design-owned |
| F-06 / S-04 link semantics | Approved 2026-08-23 | Required label and target form one presentation-neutral link object; concrete artifacts choose inline or complete reference-style rendering |
| F-07 / S-07 input ownership and consumption | Approved 2026-08-23 | Artifact context contains only rendered content; scaffold/server inputs are separate, downstream tool envelopes never tunnel through bodies, hidden routing and unconsumed values are removed |
| F-08 / S-14 output validation and strictness | Approved 2026-08-23 | Applicable output evidence is declared per artifact/profile; passed, failed, and unavailable remain distinct; strict persistence requires executed passing evidence; dormant artifacts impose no provider availability requirement. Provider discovery, injection, and call topology remain Design-owned |
| F-09 / S-15 documentation authority | Approved 2026-08-23 | Live schema and catalog own exact facts; handwritten docs explain semantics and discovery, duplicate inventories are removed, and generation remains YAGNI-driven |
| F-10 / S-10 distribution and customization | Approved 2026-08-23 | Renewal never creates a mixed suite: proven unchanged official roots may fast-forward completely, while customized, legacy-unknown, and external roots are preserved completely and receive an inspectable non-authoritative candidate. Baseline evidence, comparison, staging, and adoption mechanics remain Design-owned |
| F-11 / S-16 source provenance | Approved 2026-08-23 | Current resolved contract and Jinja graph produce a verifiable suite-scoped fingerprint; historical registry state is removed and adopted artifacts remain independent content |
| F-12 / S-05 issue references | Approved 2026-08-23 | Positive integers carry issue identity; renderers own # and other presentation syntax |
| F-12 / S-06 checklist items | Approved 2026-08-23 | Required text and explicit checked state form one structured item; primitive strings and bridges are rejected |
| F-12 original-issue coverage | Covered 2026-08-23 | All four PR defects map to approved suite-wide boundaries; no PR-only strategy remains |
| F-13 success semantics | Approved 2026-08-23 | Objective contract, render, output-profile, and persistence evidence define success; no subjective artifact-quality engine is introduced |
| F-14 / S-12 package portability | Approved 2026-08-23 | Generic package types become portable through a clean break; six confirmed S1mpleTrader patterns are removed from PGMCP and migrated only in that owning workspace after its upgrade |
| F-14A agent hints | Approved 2026-08-23 | Remove the unused pattern, three dead imports, and stale commented workflow guidance; contracts.yaml remains workflow authority |
| Deferred YAML artifact subset | Deferred 2026-08-23 | Remove the two incomplete unreachable bases now; coordination should create the complete package subset as the first post-460 PGMCP issue on its own branch |
| [Portable Python artifact coverage](deferred-work.md) | Deferred 2026-08-24 | Add no new Python artifact types in issue 460; preserve the inventory centrally; the approved Generic plain-class artifact remains bounded and may not absorb those deferred responsibilities |
| F-14B unreachable test patterns | Approved 2026-08-23 | Remove the empty assertions placeholder and unreachable incomplete fixture decorator; future fixture support must be first-class test-artifact behavior |
| F-15 / S-13 output path semantics | Approved 2026-08-23 | Persistence targets remain tool-envelope and result evidence; generic artifact bodies contain no absolute or relative filesystem path by default |
| F-16 artifact-purpose introspection | Approved 2026-08-24 | Expose the suite-owned concise artifact description through scaffold_schema; exact carrier is Design-owned and speculative catalog metadata remains out of scope |
| F-17 language/technology-qualified identity | Approved 2026-08-24 | Language/framework semantics belong to artifact identity, not caller context; rename eleven implicit-Python IDs through a clean break without aliases |
| [F-18 purpose-aware runtime artifact discovery](deferred-work.md#purpose-aware-runtime-artifact-discovery) | Deferred 2026-08-24 | Classify as a feature request and add no new runtime capability in issue 460; future Research must compare a new discovery tool, extension of an existing introspection surface, and improved existing/static discovery |
| DTO artifact responsibility | Approved 2026-08-24 | Retain/adapt one language-qualified immutable Python/Pydantic DTO; preserve valid empty skeletons, require descriptions, and conditionally require at least one JSON-compatible example whenever concrete fields exist; one semantic identity resolves explicit representations |
| Generic Python class responsibility | Approved 2026-08-24 | Retain/adapt a bounded language-qualified plain-class skeleton with required self-documentation, valid empty classes, optional structured imports, bases, and body-free method signatures; remove hidden routing, forced project behavior, and specialized fallbacks through a clean break. Caller-supplied method bodies are excluded only from Generic and this creates no suite-wide rule for specialized Python artifacts |
| Deployment compatibility | Approved 2026-08-23 | Sole current owner accepts manual migration across two machines and approximately four workspaces; repository evidence cannot prove absence of future external consumers, so the clean break is explicit and documented rather than silently generalized |

## Expected Results

Issue 460 should be considered substantively resolved only when:

1. A fresh human or LLM caller can use scaffold_schema alone to construct every supported context shape.
2. The schema describes the actual resolved runtime renderer, including relevant inherited and imported contributions.
3. Every accepted context passes the complete selected contract, renders successfully, satisfies its applicable output-profile policy, and is persisted only when the approved strictness rules permit it.
4. Optionality, nullability, emptiness, and defaults have one declared meaning.
5. Links, issue references, and checklist items each have one canonical representation.
6. Every exposed field has an explicit role and no caller intent is silently discarded.
7. Template-suite metadata, contracts, templates, any included examples, and version identity travel as a coherent portable unit.
8. pgmcp-server does not become the owner of template-specific content truth.
9. Human documentation cannot contradict the live scaffold_schema field surface.
10. Generic artifact names do not conceal consumer-project imports, lifecycle assumptions, or prerequisites.
11. Generated content is reproducible across host machines and does not embed absolute local paths by default.
12. Compatibility choices are approved per affected boundary before design.
13. Output validity, validator availability, and strict persistence policy remain distinct observable states.

## Deferred Work

Detailed deferred evidence is centralized in [Deferred Work](deferred-work.md).

| Boundary | Issue-460 decision |
|---|---|
| S1mpleTrader-local specialization | Remove consumer-specific behavior from the portable suite; perform no cross-repository implementation |
| Complete YAML artifact subset | Remove the two incomplete unreachable seeds; create the capability only through a future full Research/Design cycle |
| Portable Python artifact coverage | Introduce no new Python artifact types; preserve the non-exhaustive inventory for future Research |
| Purpose-aware runtime artifact discovery | Add no new discovery tool or overloaded introspection mode; preserve the option comparison for a future issue |

The approved Generic Python class responsibility remains bounded to a body-free plain-class skeleton and may not absorb the deferred Python artifact responsibilities. Its artifact-local body exclusion does not constrain the independently researched contracts of specialized Python templates.

## Open Research Work

1. Close the remaining seven public artifact dispositions in the catalog.
2. Close all remaining suite-file dispositions.
3. Review the 103 test/helper candidates for durable behavior value.
4. Record final impact dispositions for runtime, setup, agent, and active-documentation consumers.
5. Confirm that every deferred statement is owned only by `deferred-work.md`.
6. Request a new independent QA review after the catalog and evidence set are complete.

## Design-Owned Questions After Research Closes

Design may answer these questions only after every required strategy is approved:

1. Which standard JSON Schema draft and composition form produce one resolved reference-free public contract?
2. How are schema and Jinja dependency edges resolved, ordered, validated, and identified?
3. Which portable metadata form replaces inconsistent current tier-three representations?
4. How do result DTOs report target, validation evidence, suite identity, and graph fingerprint outside caller content?
5. Which concrete interfaces realize the approved boundaries without introducing artifact-specific server knowledge?

These are navigation inputs, not selected Design mechanisms.

## Research Deliverables

- [Primary Research](research.md)
- [Detailed Research Findings](research-findings.md)
- [Template Suite Work Catalog](template-suite-catalog.md)
- [Probe Evidence](probe-evidence.yaml)
- [Deferred Work](deferred-work.md)

## References

- [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)
- [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)
- [Scaffolding Tool Reference](../../reference/tools/scaffolding.md)
- [Template Metadata Format](../../reference/template_metadata_format.md)
- [Template Library Usage](../../reference/TEMPLATE_LIBRARY_USAGE.md)
- [Scaffolding Subsystem](../../manuals/architectural_diagrams/09_scaffolding_subsystem.md)
- [Configuration Loading Architecture](../../reference/config-loading-architecture.md)
- [Schema–Template Maintenance](../schema-template-maintenance.md)
- [Release Assets Procedure](../../reference/release-assets-procedure.md)

## Version History

| Version | Date | Changes |
|---|---|---|
| 2.2 | 2026-08-24 | Add the canonical F-01–F-18 classification matrix and defer F-18 purpose-aware runtime discovery as an explicitly approved feature request outside issue 460 |
| 2.1 | 2026-08-24 | Record explicit approval of the bounded Generic Python plain-class responsibility and clarify that its body-free contract creates no suite-wide rule for specialized Python artifacts |
| 2.0 | 2026-08-24 | Reconcile Research into one decision authority with separate findings, catalog, probe, and deferred-work responsibilities; restore Generic to pending human approval |
| 1.40 | 2026-08-24 | Last pre-reconciliation research state |
| 1.18 | 2026-08-23 | Reopen Research after independent QA found incomplete evidence, preserved behavior, blast radius, and phase separation |
| 1.0 | 2026-08-22 | Initial standalone schema-first semantic audit |

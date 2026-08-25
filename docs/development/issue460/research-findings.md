<!-- docs/development/issue460/research-findings.md -->
<!-- template=generic_doc version=43c84181 created=2026-08-24 updated=2026-08-25 -->
# Issue 460 Research Findings

**Status:** REVIEW  
**Version:** 1.2  
**Last Updated:** 2026-08-25  
**Issue:** 460

## Purpose

Preserve detailed factual findings, option analysis, blast-radius evidence, and observed behavior for the issue-460 scaffolding schema-template contract audit without enlarging the primary Research artifact.

## Authority

This document is an evidence companion, not a decision authority.

- [Research](research.md) owns the current decision status, Approved Strategy, expected results, open work, and Research gate.
- [Template Suite Work Catalog](template-suite-catalog.md) owns inventory and per-component dispositions.
- [Probe Evidence](probe-evidence.yaml) owns exact durable probe contexts and outcomes.
- [Deferred Work](deferred-work.md) owns all follow-up work outside issue 460.

Any decision wording retained below is historical rationale only. If it differs from `research.md`, the primary Research artifact governs. The Generic Python class and Python/pytest integration-test responsibilities are approved in `research.md`; any older proposal wording below is retained only as supporting rationale.

---

## Method and Evidence Authority

### Primary caller evidence

The original 2026-08-22 survey was repeated on 2026-08-23 for all 22 exposed artifact types. Each type received one minimal required-field probe and one property-complete probe:

- adapter
- architecture
- commit
- design
- dto
- generic
- generic_doc
- integration_test
- interface
- issue
- planning
- pr
- reference
- research
- resource
- schema
- service
- tool
- typescript_dto
- unit_test
- validation_report
- worker

The returned schemas are the authoritative evidence for what a first-time caller can discover. Conclusions about missing nested properties, optionality, or value representation are based on those tool responses.

### Secondary implementation evidence

The following were inspected to explain contract divergence:

- all 57 templates under .pgmcp/templates;
- all concrete-template registrations and their implementation metadata;
- inheritance and import relationships;
- runtime selection and context preparation;
- template analysis and provenance logic;
- packaged-asset and workspace-renewal behavior;
- human reference documentation and examples.

Configuration files are not treated as the caller contract. A change that makes a YAML definition internally consistent but leaves scaffold_schema incomplete would not solve this issue.

### Semantic evaluation criteria

Each artifact was evaluated against seven content properties:

1. **Discoverability** — scaffold_schema reveals every field and nested member the renderer expects.
2. **Representability** — a caller can express the required intent without undocumented shapes or magic values.
3. **Determinism** — one schema-valid value has one intended interpretation.
4. **Consumption** — exposed fields are rendered, deliberately metadata-only, or explicitly marked as non-rendering.
5. **Completeness** — generated source or documentation contains the necessary definitions, targets, and context.
6. **Optional safety** — omitted optional values and explicit null-equivalent values do not cause failure or accidental text.
7. **Portability** — the content contract can be maintained with the template suite without duplicating its meaning in server code or server tests.

Render probes were used as diagnostic observations of content behavior, not as test-based proof and not as a proposed server regression matrix.

The durable evidence authorities for the reopened audit are:

- [Template Suite Work Catalog](template-suite-catalog.md) — complete inventory of all 22 public artifacts, all 79 suite files, example surfaces, 102 active runtime/setup and synchronization consumers, and 105 candidate test/helper files.
- [Probe Evidence](probe-evidence.yaml) — exact minimal and property-complete contexts plus normalized schema, render, output-validation, and error outcomes for all 44 calls.

Cached MCP resources and ignored files below `.pgmcp/temp/issue460/` are supplementary diagnostics only. Research claims must remain reproducible from the committed evidence and live public tools without relying on a machine-local temporary path.

### Known deployment and migration context

Repository search found no durable external payload or caller contract that could prove a supported compatibility dependency. Absence from this repository does not prove absence in the field, so Research does not claim zero external-consumer risk.

The human owner is currently the sole pgmcp-server user, across two machines and approximately four repository workspaces, and confirmed that the pgmcp workspace contains the most complete current suite. The owner accepts manual migration of those workspaces. The approved compatibility posture is therefore a deliberate clean break for the defective context dialects and runtime contract:

- no primitive/object, implicit-V2, or silently-filtered compatibility bridge;
- clean installations receive the coherent packaged suite;
- upgrades preserve customized, legacy-unknown, and explicitly external active roots rather than overwriting them;
- an active preserved suite that is incompatible with the new runtime contract fails explicitly and remains inactive until the owner migrates or replaces it;
- release notes and actionable startup evidence carry the bounded migration burden.

This deployment fact reduces current migration cost but does not weaken the generic package boundary or license future silent breakage.

## Live Scaffolding Probe

### Probe layout

Disposable outputs were scaffolded below .pgmcp/temp/issue460 so that research could exercise the same public tools a daily human or LLM caller uses without touching production paths:

- minimal/ — one context per all 22 public artifact types, containing only required scaffold_schema fields;
- rich/ — 18 targeted contexts using optional and collection values exactly as scaffold_schema permits them;
- inferred/ — 11 attempts using object shapes a human might infer from the rendered document concepts or template intent.

These files are diagnostic research evidence. They are not golden outputs, snapshots, or a test suite.

### Outcome summary

| Probe | Calls | Artifacts created | Calls failed | Meaning |
|---|---:|---:|---:|---|
| Minimal scaffold_schema-derived | 22 | 20 | 2 | Even the smallest public contract is not render-safe for every type |
| Rich scaffold_schema-valid | 18 | 10 | 8 | Optional fields and string collections activate multiple renderer/schema contradictions |
| Human-inferred object shapes | 11 | 3 | 8 | Some intended shapes work only by guessing; most are rejected because scaffold_schema declares strings |
| **Total** | **51** | **33** | **18** | Tool-level live use confirms both hard failures and silent semantic corruption |

### Hard failures observed through scaffold_artifact

#### Minimal contexts

- dto passed context validation with only dto_name, then failed generated-artifact validation.
- unit_test passed context validation with its two required fields, then failed rendering because an optional collection had become a null-equivalent value and was iterated.

#### Rich scaffold_schema-valid contexts

The following values were legal according to scaffold_schema but failed after the call advanced into rendering or generated-artifact validation:

- adapter.methods containing a string;
- generic.methods containing a string;
- integration_test.test_methods containing a string;
- interface.methods containing a string;
- resource.methods containing a string;
- unit_test.test_methods containing a string;
- schema.fields containing a string;
- service.parameters containing a string.

The method-oriented templates raised member-access failures such as “str object has no attribute name.” Schema and service produced content that failed generated-artifact validation.

#### Human-inferred structured contexts

Object forms that match the renderer’s apparent concepts were rejected at context validation for:

- adapter methods;
- architecture concepts and decisions;
- generic_doc FAQ and custom sections;
- PR checklist items;
- reference usage examples;
- schema fields;
- service parameters;
- unit-test methods.

This proves a closed contradiction for those fields: the string form allowed by scaffold_schema is not usable when content is populated, while the structured form consumed by the renderer is rejected.

Three opaque object arrays did accept guessed object shapes and render meaningful content:

- design options and key decisions;
- planning cycles and risks;
- reference API entries and methods.

They remain first-time-right defects because scaffold_schema returns unconstrained item schemas and does not reveal the successful nested members.

### Silent content defects in successful calls

The following issues were observed in artifacts for calls that reported successful scaffolding:

1. **Architecture:** a string concept rendered as an empty numbered heading; a string decision rendered as an empty table row. The supplied constraint was absent.
2. **Design:** string options and decisions rendered as a blank option and blank decision row.
3. **Planning:** string cycles and risks rendered headings and labels with no content.
4. **Generic document:** string FAQ and custom-section entries rendered an empty question, empty answer, and empty heading.
5. **Reference:** one usage_examples string was iterated character by character, creating 21 empty example/code blocks.
6. **PR issue references:** values 460 and #461 rendered as #460 and ##461.
7. **PR and issue links:** raw paths rendered as unresolved reference uses; a preformatted Markdown link became a nested link.
8. **PR tracking state:** the supplied research value was absent from output.
9. **Reference links:** source and test values rendered as reference links without source or tests definitions.
10. **Validation report:** an explicit null scope rendered as the word None; the outcome sentence and Related Documentation heading were concatenated on one line.
11. **Unknown context:** a reference purpose value, absent from scaffold_schema, was accepted by the call but silently removed and did not render.
12. **Optional code metadata:** minimal adapter, generic, interface, resource, schema, service, tool, worker, and integration-test artifacts visibly rendered null-equivalent values as descriptions, layers, targets, or scopes.
13. **Absolute machine paths:** every successful artifact embedded its absolute local Windows output path in the first source comment or Markdown comment.
14. **Project coupling:** minimal worker and service outputs contained hard-coded backend imports and project-specific architecture assumptions that were not described by scaffold_schema.
15. **Naming ambiguity:** supplying the schema-described service class name LiveService produced class LiveServiceService.
16. **TypeScript readability:** generated JSDoc metadata collapsed layer and responsibilities onto one malformed-looking line despite a successful call.
17. **Issue title role:** title is required and accepted but is absent from the issue body, with no caller-visible field-role explanation.


## Contract Model

The desired public flow is:

    Independently maintained template suite
        -> resolved, introspectable content contract
        -> scaffold_schema
        -> human or LLM context construction
        -> scaffold_artifact
        -> substantively correct artifact

The current flow can diverge at three points:

    declared surface -> scaffold_schema
    active runtime template -> hidden renderer expectations
    packaged or renewed assets -> mismatched contract/template pair

The key invariant is:

> Every value consumed by the resolved renderer must be discoverable through scaffold_schema, and every value offered by scaffold_schema must have a single documented meaning in that renderer or be explicitly identified as non-rendering metadata.

## Inventory Findings

- The public introspection surface contains 22 artifact types.
- The template directory contains 57 Jinja files.
- Fifty-three templates are reachable from configured public types plus the DTO runtime override.
- Four templates are not reachable from any public resolved graph:
  - tier1_base_config.jinja2
  - tier2_base_yaml.jinja2
  - tier3_pattern_python_assertions.jinja2
  - tier3_pattern_python_test_fixtures.jinja2
- Twenty of the 22 configured concrete templates use whitespace-trimmed inheritance syntax that the current analyzer does not recognize. Their reported chain stops at the concrete template.
- The two test templates expose one inheritance edge, but their chain then stops at the next trimmed edge.
- Imported macros are not part of the analyzed inheritance chain or its version hash.
- Twenty-two tier-three pattern files use a metadata form that the current analyzer does not parse as structured template metadata.
- The DTO public registration and the DTO template selected at runtime are different files with different field semantics and versions.

These graph facts matter because scaffold_schema should describe the resolved renderer, not merely a configured entry file.

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

## Cross-Cutting Analysis

### F-01 — scaffold_schema cannot describe several renderer-required structures

The dominant failure class is a mismatch between introspected collection shapes and renderer access patterns.

Examples:

- adapter, generic, interface, and resource expose methods as arrays of strings while their templates read members such as name, params, return_type, docstring, and body;
- architecture exposes concepts and decisions as arrays of strings while the template reads concept names, descriptions, diagrams, subsections, decisions, rationales, and alternatives;
- integration_test and unit_test expose test_methods as arrays of strings while the templates read markers, async state, name, fixtures, return type, description, arrange, act, and assertions;
- schema exposes fields as strings while the template reads name, type, default, default_factory, and description;
- service exposes parameters as strings while the template reads name, type, and description;
- generic_doc exposes faq and custom_sections as strings while the template reads structured questions, answers, headings, content, bullets, and checklist entries;
- reference and planning expose opaque object arrays whose scaffold_schema items do not reveal the nested properties that templates require.

#### Closed contract contradiction

For adapter methods, the [declarative contract](../../../.pgmcp/templates/config/adapter.yaml) accepts an array of strings while the [renderer](../../../.pgmcp/templates/concrete/adapter.py.jinja2) reads object members. A caller following scaffold_schema can submit a string that passes validation and fails during rendering. A caller supplying the structured object required by the renderer is rejected by the public contract. The same contradiction occurs across the affected artifact families; opaque arrays replace rejection with undocumented guesswork rather than first-time-right introspection.

The current [SchemaFieldDef](../../../mcp_server/config/schemas/artifact_registry_config.py) and [dynamic model builder](../../../mcp_server/managers/artifact_manager.py) implement only a small custom schema subset. Arrays become list[str] or list[Any], so the server cannot expose nested renderer semantics without extending server-owned template knowledge.

#### Boundary and consumer blast radius

| Boundary | F-01 impact |
|---|---|
| Portable template suite | Owns the renderer concepts and must own their complete machine-readable context contract |
| Artifact registry configuration | Primitive and opaque collection declarations cannot express the active templates |
| Pgmcp schema/validation path | Must validate arbitrary JSON-shaped context generically without artifact or field-name dispatch |
| scaffold_schema | Remains the sole caller-facing introspection API and must return the complete resolved contract |
| scaffold_artifact and Jinja | Must validate and render the same contract without format-then-reinterpret behavior |
| Human and agent callers | The agent is the only relevant runtime consumer and discovers the current contract immediately before scaffolding |
| Agent instructions and documentation | Current first-time-right claims depend on scaffold_schema being complete; they must not become a parallel field inventory |
| Tests and suite auditing | Must protect generic contract resolution, validation, and representative schema-to-render behavior without snapshotting template prose |
| Release and workspace assets | Template content and its contract must travel as one coherent suite version |

No durable external caller or stored payload contract was identified. The existing primitive and opaque collection forms do not provide working supported behavior for the affected renderers.

#### Historical client-compatibility evidence

[Issue 99 research](../archive/issue99/research.md) established that some Claude and VS Code MCP clients could not construct tool calls when client-facing input schemas contained Pydantic-generated $defs and $ref indirection. Later work made reference-free client schemas a cross-tool invariant. The current [schema resolver](../../../mcp_server/utils/schema_utils.py) safely inlines only simple local Pydantic references; it is not a standards-complete resolver for suite authoring because it has no external-reference, general JSON Pointer, missing-target, or cycle handling.

This history constrains the public boundary rather than prohibiting internal reuse. Template-suite authoring may compose exact shared definitions, but every schema presented to an agent must be finite, self-contained, and reference-free.

#### Historical Preservation Rationale

- Preserve public artifact responsibilities and expressive content capabilities while allowing the identity changes governed by the canonical F-17 decision.
- Preserve scaffold_schema as proactive introspection and scaffold_artifact as the validated rendering entry point.
- Preserve reference-free MCP client-facing schemas.
- Do not preserve unusable primitive or opaque collection shapes as compatibility behavior.
- A fresh caller using only scaffold_schema must be able to construct every supported nested value without template inspection or documentation-only knowledge.
- Every accepted nested value must reach the renderer without semantic reinterpretation or loss.

#### Historical Decision Rationale

- Apply a clean break: structured collection items replace primitive or opaque declarations wherever the renderer consumes multiple item properties. No primitive/object compatibility bridge is required.
- The portable template suite owns complete standard JSON Schema context contracts. Pgmcp remains artifact-agnostic and must not encode field names or template concepts in Python.
- The same resolved schema governs caller introspection and runtime context validation.
- Internal schema composition may reuse exact definitions, but the authoring graph must be acyclic for the current scope and must fail fast on invalid or unresolved references.
- scaffold_schema and every MCP client-facing schema expose only a fully resolved, self-contained representation without $defs or $ref.
- Recursive context schemas are out of scope because no current template performs recursive rendering.

#### Schema meaning versus workflow completeness

Artifact-schema guidance and workflow instructions have different authority:

- schema and property descriptions explain the stable, workflow-neutral meaning of caller-owned content, including what a valid value represents;
- the active `contracts.yaml` phase instructions explain which evidence and level of completeness the current workflow and phase require;
- the resolved template graph controls presentation only and does not redefine either authority.

Phase artifacts such as research, design, planning, and validation reports are normally scaffolded during their corresponding active phases. The server already forces callers to load the active work context after phase and cycle transitions. `scaffold_schema` should therefore make the workflow-specific authority discoverable by an unambiguous reference instead of copying phase instructions into template configuration or field descriptions. The artifact schema must remain understandable outside an active workflow, and the reference must not hard-code one workflow's phase order or turn the template suite into a second workflow authority.

#### Recorded workflow-artifact responsibilities

- **Research — Retain/adapt.** Preserve the carrier for problem, goals, structural evidence, open questions, internal and external references, expected outcomes, and conditional Decision context. Stable field meaning is discoverable through the schema; active Research instructions own workflow-specific completeness.
- **Design — Retain/adapt.** Preserve the technical decision record for problem boundary, requirements, constraints, alternatives, chosen direction, rationale, key decisions, and open questions. It must also be capable of carrying production and test design as first-class content, relevant interfaces/contracts, data/control flow, failure/state behavior, preservation or migration obligations, validation obligations, planning consequences, and source links. Active Design instructions select the workflow-specific emphasis. Requirements must not acquire completion-state semantics merely through incidental checkbox presentation. The exact fields, nested shapes, section layout, and rendering belong to Design.
- **Planning — Retain/adapt.** Replace the universal TDD framing with a dependency-ordered executable plan: bounded work units, exclusions, deliverables, risks, dependencies, stop/go conditions, and proportionate exit evidence. Active Planning instructions determine whether units are implementation cycles, correction or migration steps, documentation tasks, or child issues, and whether RED/TDD is justified. Test work remains first-class but is not universally mandatory. Where workflows persist a structured project plan, the document and `save_planning_deliverables` payload must remain semantically identical; exact ownership and representation belong to Design.
- **Validation Report — Retain/adapt.** Replace the placeholder scope/outcome shell with a compact, navigable evidence index that can record scope/exclusions, obligation-to-evidence mapping, exact and fresh test/gate/targeted outcomes, behavior/correction/containment/preservation proof as applicable, demonstration or fallback, failures, caveats, residual risks, and explicit deferred work. Producer-reported evidence status must remain distinct from independent QA authority. Raw logs remain in their authoritative resources rather than being copied into prose.

#### Mandatory runtime architecture and hardcoding sweep for issue 460

The template engine refactor crosses configuration, discovery, validation, rendering, persistence, provenance, and upgrade boundaries. Direct-import inspection alone is therefore insufficient. Every runtime and setup candidate in the work catalog must be checked against the complete binding [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md).

The sweep must explicitly identify generic Python that hardcodes artifact IDs, context field names, workflow or phase names, template filenames/paths, output-profile or validator-provider choices, package/install policy, or user-facing presentation. Such knowledge belongs in the packaged suite, workflow configuration, or presentation boundary unless a documented generic structural invariant proves otherwise. It must also record SRP/OCP/ISP/DIP, DRY/SSOT and single-reader ownership, Config-First, fail-fast startup, CQS/frozen query results, Law of Demeter, constructor injection/composition-root ownership, import-time side effects, Explicit-over-Implicit, YAGNI, and template-package cohesion impacts.

Research records the violated or preserved boundary and consumer effect per component. It does not select replacement classes, parser APIs, registries, or call topology; those remain Design-owned. A green test or quality gate is not architecture evidence.


#### Runtime sweep evidence recorded on 2026-08-24

The completed architecture and direct-consumer pass confirms that the dominant problem is not merely incomplete template data. The initial 20-file runtime census was incomplete: tracing imports and public tool registration exposed a parallel legacy scaffolding stack, source-header metadata infrastructure, and an always-pass validation tool. These are now explicit work-catalog entries rather than hidden implementation discoveries. Several generic runtime components currently reinterpret, supplement, or silently repair suite-owned meaning:

- `ArtifactManager` rebuilds a restricted Pydantic model from only string, integer, boolean, and shallow-array declarations; filters unknown context fields; copies `name` into `dto_name`; searches for an undeclared `_v2` sibling; special-cases Generic output paths; inspects renderer internals to recover the template root; and constructs scaffolding, validation, filesystem, and registry collaborators when injection is absent.
- `TemplateScaffolder` special-cases Service variants and Generic routing, accepts hidden template overrides, derives output format from a fixed extension map, and treats Jinja variable inference as the validation contract.
- `ValidationService` registers process-global validators, selects them through filename regexes and hardcoded artifact IDs/extensions, applies Python and Markdown rules in the universal path, silently accepts unknown output types, and creates its own settings/analyzer when not injected.
- `LayeredTemplateValidator` and `TemplateAnalyzer` turn embedded metadata and regex matches into a second validation language. They can select the first filename match, ignore missing metadata, stop inheritance traversal on missing/cyclic parents, or return an empty variable set after parser failure.
- `TemplateRegistry` and `version_hash.py` persist mutable historical state with no evidenced runtime decision consumer. Malformed registry state becomes an empty registry; unreadable or unversioned templates become version `1.0.0`; incomplete inheritance becomes a best-effort hash. This contradicts Fail-Fast and does not provide trustworthy provenance.
- `WorkspaceUpgrader` preserves YAML by path category, overwrites other existing assets, and treats `template_registry.json` as dynamic state. That behavior cannot implement the approved managed-baseline/staged-candidate policy or distinguish an unchanged installed suite from user customization.
- `ConfigLoader` is the correct single-reader seam, but its optional template-root path falls back through `Settings.from_env()` and then a broad-exception inferred directory. The refactored suite path must receive an explicit root and reject an incoherent graph during startup.
- `bootstrap.py` is the valid composition root, but currently constructs and exports the obsolete TemplateRegistry while `ArtifactManager` still constructs other collaborators internally. The new restart-stable resolved suite and validation capabilities belong in composition, not in tool execution.
- `TemplateEngine` provides the useful generic Jinja render boundary, but its compatibility constructor alias and Python-identifier filter show that language/profile capabilities are currently mixed into the universal engine.
- `BaseContext`, `BaseRenderContext`, and `LifecycleMixin` preserve an obsolete context-inheritance dialect and inject path/timestamp/template/hash data into render content. They are not a neutral carrier for the approved complete standard JSON Schema and separate scaffold envelope.
- `mcp_server/scaffolding/base.py`, its eight component scaffolders, `utils.py`, and `renderer.py` form a parallel legacy stack. They hardcode artifact identities, template paths, PascalCase, command/query/orchestrator fallback, extension behavior, and a package-relative/CWD authority while duplicating the active scaffolder, result, and renderer abstractions.
- `scaffold_metadata.yaml`, `ScaffoldMetadataConfig`, and `ScaffoldMetadataParser` preserve generated source-header provenance through a global extension/comment registry. That responsibility has no retained decision consumer and conflicts with output-profile ownership.
- The public `validate_template` tool hardcodes five artifact families, constructs its validator inside `execute()`, and delegates to a deprecated validator that always succeeds. Its registration, DTOs, documentation, agent allowlists, and tests must be removed together; it cannot serve as evidence for the retained startup-graph or output-profile boundaries.
- `ConfigValidator` remains the correct fail-fast cross-config boundary. It should consume the resolved suite to check graph and profile/capability coherence, while exports and loader methods for removed metadata/context types are cleaned up rather than retained as compatibility surfaces.

The public scaffold tools themselves are comparatively sound seams: both derive the artifact enum from the loaded registry and delegate to the manager. Their fixed example text is documentation debt, not dispatch logic. `SafeEditTool` is a legitimate post-scaffold consumer and evidence that first-time-right scaffolding is not synonymous with final phase completion. It must validate the complete proposed result through the same injected configured output-profile boundary as scaffolding: strict failure or unavailable required validation preserves the original file, while interactive persistence returns structured findings. Only its current environment-derived default dependency conflicts with that boundary; staging, atomic-write, and rollback mechanics remain Design-owned. `issue_tools.py` consumes pre-rendered tracking Markdown and does not need to understand template context.

Pre-existing settings concerns outside the template path—test-environment-driven defaults, silent package-version fallback, and repository-specific GitHub defaults—are recorded as architecture debt but do not expand issue 460 into a general Settings refactor. Design must avoid depending on or reproducing them.


#### Mandatory test-suite architecture sweep for issue 460

The behavioral test/helper ledger is not only a coverage-retention exercise. Every affected test module, fixture, factory, fake, and shared harness is production-quality code under the applicable Architecture Principles. The audit therefore produces two separate answers per candidate:

- **Does it protect a durable public behavior or architectural invariant?** Exact prose, incidental import order, current type counts, private call sequences, obsolete registry history, and scaffold metadata snapshots are not automatically durable.
- **Is the test implementation itself architecturally sound?** A valuable claim may still be implemented through the wrong boundary and require adaptation or replacement.

The applicable architecture evidence is concrete:

| Principle boundary | Test-suite interpretation |
|---|---|
| Public API / Explicit over Implicit | Exercise observable tool, manager, loader, renderer, validator-capability, or upgrade decisions. Avoid asserting private helper calls, internal collection shape, arbitrary invocation order, or source text where public behavior can prove the obligation |
| DIP and constructor injection | Build the subject with explicit collaborators or through the real composition boundary. Do not rely on production fallbacks that call `Settings.from_env()`, process CWD, package assets, or hidden registries |
| Config-First / DRY / OCP | Derive artifact IDs, schemas, paths, workflow names, output profiles, and provider availability from the fixture config or runtime catalog. A test matrix may enumerate approved behavior cases, but it may not become a manually synchronized second registry |
| SRP / ISP / Law of Demeter | Fixtures and harnesses provide the narrow setup required by the behavior. Avoid omniscient factories that reach through private renderer/manager state, patch multi-hop internals, or assemble unrelated system concerns |
| CQS and isolated state | Query assertions do not mutate persistent state. Registry, validator, cache, filesystem, environment, and clock state are isolated and restored; order-dependent tests and process-global registrations are rejected |
| Fail-Fast | Negative tests prove invalid schema graphs, unresolved references/dependencies, unavailable required capabilities, invalid profiles, and incoherent install state fail at the owning boundary with actionable context. They do not preserve silent fallback as compatibility |
| No import-time I/O | Importing test helpers or production subjects must not read workspace/config/template state or mutate global registries |
| Test code as first-class code | Retained tests and helpers meet the same typing, naming, maintainability, and quality standards as production code. Mocks represent owned interfaces, not arbitrary implementation objects |
| YAGNI | Do not preserve a helper abstraction, fixture hierarchy, generated example, or snapshot merely because it exists. Keep the smallest evidence set that protects the approved contract and meaningful failure paths |

The architecture sweep is proportional rather than ritualistic: principles irrelevant to a test's responsibility need no fabricated compliance mechanism. For example, a pure frozen config-model test does not require a dependency-injection harness, while an end-to-end upgrade test does require explicit roots and isolated filesystem state. Design and Planning must preserve both disposition axes so that implementation does not mechanically port architecturally invalid tests into the new engine.


##### Completed test/helper audit outcome

All 105 candidates now have an explicit behavior-value and architecture disposition in the work catalog. The original broad-signal census contained 103 files; direct consumer tracing added `test_template_validation_tool.py` and `test_scaffold_metadata_config.py`, preventing obsolete public-validation and metadata-config coverage from escaping the migration:

- 9 adjacent modules are excluded from semantic issue-460 changes; only shared fixture wiring may move.
- 24 modules/helpers are removed outright because their source responsibility, historical registry/provenance behavior, placeholder pattern, or duplicate claim is gone.
- 14 duplicate suites are removed after any unique durable evidence is consolidated into the new central acceptance/config/graph/profile coverage.
- 21 modules are replaced wholly or through consolidation because their intent remains useful but their current boundary is wrong.
- 37 modules are adapted, consolidated, renamed, split, or fixture-adjusted around retained public behavior.

The counts are implementation workload evidence, not prescribed file arithmetic: Design may combine replacement coverage differently as long as every row's durable claim and architecture constraint remains traceable.

Five systemic test-architecture findings explain the breadth:

1. **Second configuration authority.** The all-types smoke matrix, production-config copies, locally assembled YAML strings, and hardcoded artifact examples repeat IDs, context shapes, paths, and defaults outside the suite. They become stale on every suite change and can pass while the runtime catalog differs.
2. **Implicit process state.** Shared harnesses and several integration tests set template/config environment variables, change CWD, or call `Settings.from_env()`. This masks missing dependency injection and makes execution order, host state, and parallelism relevant.
3. **Implementation-shaped assertions.** Numerous files assert tier inheritance, macro names/import counts, exact comment headers, manager private methods, patched call sequences, or renderer internals. These tests impede an OCP-compliant refactor without protecting caller-visible outcomes.
4. **Prose and historical-state snapshots.** Document-section wording, version histories, scaffold headers, mutable TemplateRegistry entries, and best-effort hashes are treated as contracts even though Research explicitly retires or permits those representations to evolve.
5. **Duplicated integration proof.** Acceptance, E2E, smoke, concrete-template, document-template, and tool-error suites repeatedly exercise the same narrow Design/DTO examples through different fixture graphs, increasing runtime and maintenance without complete catalog coverage.

The replacement evidence must close the material gaps these suites currently obscure: one complete resolved-catalog acceptance path; standard JSON Schema composition and nested validation; Jinja dependency/import resolution including missing edges and cycles; one caller-context/envelope boundary; declared output-profile pass/fail/unavailable behavior; strict pre-persistence enforcement; public error/schema recovery; and clean-install plus managed-baseline/staged-candidate upgrade decisions. Artifact-specific syntax or semantic cases remain explicit where the artifact contract genuinely differs, but they are not a second inventory of the installed suite.

#### Mandatory phase-instruction alignment for issue 460

The four workflow-document artifacts and the workflow contracts are one cooperating toolchain. Design must compare every active Research, Design, Planning, and Validation `phase_instructions` variant with the corresponding final schema and renderer.

- Every instruction that requires persisted phase content must map to a semantically named schema section. The shared artifact schema contains a common core plus optional sections; the active workflow instruction determines which optional sections its outcome requires.
- Every stable artifact concept must be explained by schema guidance and used coherently by applicable phase instructions, or be justified as reusable outside workflow execution. Optionality in the scaffold contract does not make a workflow-required outcome optional at the phase boundary.
- Substantive actions, authority boundaries, workflow-specific completeness, and enforcement of the correct MCP tool, timing, and evidence scope remain in `contracts.yaml`; templates and schemas do not copy them. Phase instructions name required tools when enforcement matters but never embed complete invocations or duplicate input parameters.
- Templates own presentation and stable document structure; they do not redefine workflow behavior.
- Phase instructions may be edited within issue 460 when alignment removes contradiction, missing artifact capacity, obsolete terminology, or inefficient workaround authoring. Such edits must preserve the approved workflow responsibilities rather than silently redesign them.
- The alignment should minimize agent repair work and duplicate context: the phase instruction tells the agent what outcome is required, `scaffold_schema` explains how artifact content is supplied, and the renderer produces a fitting first draft.
- First-time-right describes call correctness: one schema-valid invocation renders and persists a truthful, structurally coherent basis without a failed discovery/repair loop. It does not mean the scaffolded content is the final complete phase deliverable.
- Normal substantive refinement through `safe_edit_file` remains expected. Contract wording must not pressure an LLM to invent all final content inside the initial scaffold context, nor cause it to reinterpret ordinary editing as scaffolding failure.
- The comparison record must flag both error classes: instructions that demand content the artifact cannot carry, and instructions/schema descriptions that imply scaffold completion eliminates necessary reasoning, evidence gathering, or later editing.

This makes [.pgmcp/config/contracts.yaml](../../../.pgmcp/config/contracts.yaml), its loader/validation tests, and active workflow-instruction documentation explicit members of the issue-460 blast radius. The exact comparison matrix, edits, and verification mechanism belong to Design and Planning.


#### Workflow × phase × artifact alignment record

The active contract set contains five Research variants (Feature, Bug, Refactor, Chore, Epic), four Design variants (Feature, Bug, Refactor, Epic), five Planning variants (Feature, Bug, Refactor, Docs, Epic), and five Validation variants (Feature, Bug, Refactor, Hotfix, Chore). The comparison below records semantic carrier obligations, not a target field layout.

| Artifact | Workflow-specific persisted outcomes required by active instructions | Current carrier assessment | Binding Design obligation |
|---|---|---|---|
| Research | Feature: evidence, options, risks, expected outcomes, and strategy boundaries. Bug: observed/expected behavior, reproduction, causal evidence/root cause, occurrence conditions, corrected behavior, regression boundary, and strategy. Refactor: responsibilities, coupling/duplication, invariants, supported behavior, candidate seams, coverage gaps, and preservation strategy. Chore when persistence is warranted: objective, exclusions/mechanical boundary, proportional blast radius, risks, and approved boundary. Epic: initiative framing, candidate workstreams, dependencies/ownership, shared proof obligations, assumptions/risks, and shared strategy | Scope, goals, findings, questions, links, strategy, and expected results provide partial generic capacity. One free-form `findings` field is the only carrier for most evidence, blast-radius, causal, structural, consumer, and shared-obligation concepts, so `scaffold_schema` cannot make expected content obvious and the renderer cannot give each concept a stable navigable role | Provide a finite workflow-neutral evidence/strategy carrier broad enough for every variant, with semantically named capacity for scope/exclusions, evidence and sources, blast radius/consumers, findings, risks/unknowns, expected outcomes, and approved decisions. Workflow instructions retain variant-specific emphasis such as root cause or candidate workstreams |
| Design | Feature: architecture, interfaces, data/control flow, state/failures, dependencies, alternatives, production/test design, validation, migration, and planning consequences. Bug: smallest root-cause correction, preservation, regression design, failure behavior, alternatives, and validation. Refactor: target responsibilities/dependencies, transitions/cutover/deletion, invariant preservation, test architecture/cleanup, and alternatives. Epic: cross-workstream responsibilities, shared interfaces/contracts, flow/failure/cutover, child ownership, integration, sequencing constraints, and shared test architecture | Problem, requirements, decision/rationale, constraints, opaque options/key decisions, and open questions are insufficient. There is no discoverable carrier for production and test design, interfaces/contracts, flows/state/failures, preservation/migration, validation obligations, cleanup, ownership, or planning consequences; opaque object arrays are not executable contracts | Expose the stable design-decision vocabulary and fully describe every nested option/decision/source shape. Provide obvious capacity for production and test design plus contracts, flow/state/failure, preservation/transition, validation, risks, and planning consequences without embedding workflow-specific instructions |
| Planning | Feature: dependency-ordered implementation cycles. Bug: minimal correction/regression/cleanup cycles. Refactor: characterization/seam/migration/cutover/deletion cycles. Docs: documentation tasks with authoritative sources, files, current-state outcome, review proof, and consistency risk. Epic: child-work outcomes, ownership, prerequisites, shared obligations, integration, acceptance, cleanup, and coordination gates | The artifact labels every work unit a TDD cycle and documents an incomplete opaque object mini-schema. It cannot first-time-right express docs tasks or epic child work, and it lacks explicit exclusions, deliverables, strategy obligations, stop/go conditions, exact evidence, ownership, and structured risks. It can also drift from `save_planning_deliverables` because the two representations are not one declared semantic contract | Define a finite dependency-ordered work-unit carrier usable as cycles, documentation tasks, or child work according to the active workflow. Each unit must be able to carry scope/exclusions, dependencies, owned deliverables, obligations, verification/acceptance evidence, risks, and stop/go criteria. Preserve semantic identity with the structured planning payload; exact representation/ownership is Design-owned |
| Validation Report | Feature: deliverable/design/strategy mapping, exact suite/gate evidence, demonstration/fallback, failures, caveats, risk, and deferred work. Bug: root-cause/reproduction/corrected-behavior and regression proof plus preservation. Refactor: structural completion, deletion/cleanup, invariant/behavior preservation, remnants/coupling. Hotfix: correction, containment/rollback, regression, and operational risk. Chore when persisted: objective/consumer coverage, full-suite/gate/diff evidence, freshness, risks, and deferred-work triage data | The current contract carries only metadata, optional issue/cycle/status, and one scope string. It cannot represent any exact check result, obligation mapping, evidence link, failure, risk, demonstration, preservation/containment proof, or deferred item required by the phase contracts | Provide a compact evidence-index carrier for scope/exclusions, obligation-to-evidence mappings, exact checks and freshness, targeted/demonstration evidence, failures/caveats/risks, and deferred work. Producer status remains evidence reporting and must not impersonate independent QA authority |

The comparison also exposes instruction-side friction:

- All embedded pseudo-invocations such as `scaffold_artifact(... context={...})`, `run_tests(scope=...)`, and `git_add_or_commit(...)` duplicate MCP input contracts and will drift when parameters evolve. Phase instructions may still require `scaffold_artifact`, `run_tests`, `run_quality_gates`, or another authoritative tool by name and purpose. `scaffold_schema` is not an unconditional phase step: an agent with the current schema may scaffold directly, while the global scaffolding rule requires discovery when the schema is absent or stale.
- Docs Planning and all three Epic document phases ask for “schema-complete evidence” in the initial scaffold call. That phrase can be read as “construct the final artifact before scaffolding” and defeats the intended scaffold-then-refine workflow.
- Chore correctly permits a direct Research outcome and optional persistence. Its Research schema must not become mandatory merely because the richer artifact exists.
- Validation variants correctly allow creation followed by updating, which already models scaffold-as-basis. The other document phases should communicate the same lifecycle without implying that a schema-valid first render is phase-complete.
- No phase instruction may require a generic catch-all field to smuggle in a concept the schema does not name. Conversely, schema descriptions must not copy root-cause, preservation, epic-decomposition, TDD, or other workflow-specific obligations.

The Design acceptance test for this boundary is therefore semantic, not textual: for each of the nineteen variants, the shared schema exposes a common core and clearly named optional sections capable of carrying the workflow-required outcome. An agent that already holds the current schema may invoke `scaffold_artifact` directly; an agent without that knowledge can discover it without the phase instruction prescribing the call. One valid scaffold produces a truthful structural basis, after which normal evidence gathering and `safe_edit_file` refinement reach the phase outcome. Only the reviewed and refined artifact may be called phase-complete. Across all phase instructions, required tool choice, timing, and evidence scope remain enforceable while complete invocation syntax and parameters are absent.

#### Recorded general-document responsibilities

- **Architecture — Retain/adapt.** Preserve durable system concepts, component boundaries and relationships, architectural constraints, system-level decisions and rationale, rejected alternatives, source/document relationships, and optional diagrams/subsections. Make every nested shape introspectable, render constraints explicitly, and distinguish long-lived architecture from issue-specific Design. Diagram support must not force unavailable validators into workspaces that do not use that capability.
- **Generic Document — Retain/adapt.** Preserve a bounded structured fallback for guides, migration, operational, standards, and other documents without a specialized artifact contract. Retain purpose, summary, scope, prerequisites, links, key changes, ordered migration steps, validation checklists, FAQ, and flat custom sections. FAQ and section shapes must be fully introspectable; extension remains flat and finite rather than becoming a recursive document DSL. Its purpose description must direct callers toward specialized artifact types when applicable.
- **Reference — Retain/adapt.** Preserve technical reference documentation for implemented public interfaces/components, including purpose, API semantics, signatures, parameters, returns, relevant error behavior, language-aware usage examples, and complete links to authoritative implementation sources. Support optional repeatable test/evidence links, remove volatile test counts, and never hard-code Python as the example language. Reference-style links remain first-class but must always include their definitions.

#### Recorded code-artifact responsibilities

- **Interface — Retain/adapt.** Preserve the Python `Protocol` contract under the language-qualified identity required by F-17. Public methods are explicitly caller-owned through an introspectable method contract; the scaffold tool envelope owns the rendered class name. Omitted methods must not fabricate an `execute()` contract. Design decides whether an empty marker protocol is valid or at least one method is required. Remove hard-coded Backend/layer assumptions. Test creation remains workflow/plan/risk-owned; the currently unconsumed `generate_test` flag receives a suite-wide disposition during the engine/config audit rather than becoming automatic behavior.
- **Adapter — Retain/adapt.** Preserve a portable Python boundary adapter under a language-qualified identity. Its local contract relationship, dependencies/imports, translation and failure behavior, and concrete methods must be caller-owned and introspectable. Do not fabricate `adapt()`, hard-code Backend layers, force unused logging, or let the artifact type create tests. Common signature definitions may be composed with Interface without collapsing abstract and concrete method semantics. S1mpleTrader-specific logging/Translator boilerplate is deferred preserved specialization, not package behavior.

#### Approved Python/pytest integration-test responsibility (2026-08-24)

The current public contract accepts primitive test-method strings while the renderer consumes structured members for names, markers, async state, fixtures, return types, descriptions, and Arrange/Act/Assert bodies. The property-complete schema-valid probe therefore fails with `UndefinedError: 'str object' has no attribute 'name'`. Its minimal success is not reliable evidence: omitted options silently enable async imports, a temporary-workspace fixture, and a fabricated filesystem test that passes without proving the requested scenario. Setting `workspace_fixture=false` can leave that fallback referring to a fixture that was not rendered.

The renderer also conflates integration testing with E2E/full-stack testing, requires a pytest class, guesses imports from manager class names under `mcp_server.managers`, and emits unused or unconditional Python dependencies. These are consumer-project and style assumptions rather than portable integration-test semantics. Existing generated pgmcp tests show that useful tests require substantial editing beyond this scaffold; generated metadata survives, but real imports, doubles, fixtures, boundaries, and assertions are scenario-specific.

**Recorded responsibility summary:** retain and adapt one language- and framework-qualified Python/pytest integration-test module for observable behavior that requires collaboration across multiple concrete components or boundaries.

- Integration and E2E remain distinct. The artifact owns integration-test structure and does not claim a complete user/system flow unless caller content explicitly describes one.
- Imports, dependencies, fixtures, markers, sync/async intent, grouping, and test cases are caller-owned and introspectable. The renderer does not infer project module locations or force classes, async execution, filesystem interaction, or a temporary workspace.
- Every generated test targets observable behavior through public boundaries in accordance with the architecture contract. Template structure must not encourage private-API coupling or tests of implementation prose.
- Omitted test content must never produce a fabricated passing test. Design owns the exact honest incomplete-test behavior and the structured representation of test cases and bodies.
- The schema and renderer must produce syntactically valid Python for every accepted context. First-time-right means a truthful, coherent test basis, not an application-complete or automatically passing suite.
- F-17 requires a Python/pytest-qualified public identity through a clean break. The exact ID, class-versus-function representation, fixture/import objects, source-body boundary, and validation profile remain Design-owned.
- Shared pytest, async, and test-structure patterns remain reusable only where their output is explicitly selected and needed; they may not inject unconditional imports or a universal Arrange/Act/Assert style.

Direct blast radius includes the [integration-test config](../../../.pgmcp/templates/config/integration_test.yaml), [integration-test renderer](../../../.pgmcp/templates/concrete/test_integration.py.jinja2), shared [Python base](../../../.pgmcp/templates/tier2_base_python.jinja2), [pytest](../../../.pgmcp/templates/tier3_pattern_python_pytest.jinja2), [async](../../../.pgmcp/templates/tier3_pattern_python_async.jinja2), and [test-structure](../../../.pgmcp/templates/tier3_pattern_python_test_structure.jinja2) patterns, output validation, active scaffolding references, all-type smoke/probe evidence, and generated tests that retain scaffold provenance. Durable verification must protect schema/render parity, syntactic validity, explicit optional behavior, and absence of fabricated passing assertions without snapshotting complete test prose.

#### Approved Resource artifact removal (2026-08-24)

The public Resource artifact claims an MCP resource but renders a generic logged Python class. It exposes a `resource_type` value only in a module comment, accepts primitive method strings while reading structured method members, and fabricates a synchronous `read()` returning `None`. It does not inherit [BaseResource](../../../mcp_server/resources/base.py), declare a URI pattern or MIME type, implement `async read(uri: str) -> str`, or participate in resource composition. The property-complete valid probe fails on the primitive/structured method mismatch.

Repository evidence establishes no real scaffold consumer. Existing pgmcp resource providers are hand-written architectural implementations, while the only historical scaffold requirement found in issue 286 was an end-to-end registry smoke call. That issue added Adapter, Resource, and Interface together to complete a previously missing pipeline and gave them the same generic method vocabulary; it did not establish a distinct Resource responsibility or recurring use case.

Python itself has no general resource code construct. Files, connections, package data, HTTP resources, cloud resources, domain resources, and MCP providers have unrelated structures. Once forced logging, the inert `resource_type`, and the fabricated `read()` are removed, this artifact is equivalent to the approved Generic Python class skeleton. A pgmcp-specific resource-provider artifact could be designed later, but current usage does not justify retaining or rebuilding one.

**Recorded disposition:** remove the Resource artifact, its public config, and its concrete renderer through a clean break.

- Existing [BaseResource](../../../mcp_server/resources/base.py), concrete runtime resources, and resource composition remain production behavior and are not removed.
- Existing generated files remain ordinary independent source files.
- Active registry inventories, documentation, schema enumeration, and tests that assume Resource solely for type-count completeness must be updated.
- No alias, compatibility bridge, replacement artifact, or deferred feature is created without a concrete future consumer.
- Generic remains the suitable scaffold for an otherwise unspecialized Python class; a framework-specific resource provider requires its own future evidence and strategy rather than a misleading universal name.

Direct removal blast radius includes the [Resource config](../../../.pgmcp/templates/config/resource.yaml), [Resource renderer](../../../.pgmcp/templates/concrete/resource.py.jinja2), runtime catalog/type enumeration, all-type smoke and schema tests, and active template/scaffolding inventories. Tests must preserve behavior of the remaining registry and runtime resources rather than preserve an obsolete count or prose list.

#### Approved Python/Pydantic configuration-model responsibility (2026-08-24)

The current public Schema identity is ambiguous, but its config name, concrete template, metadata, and recurring pgmcp consumers consistently indicate a Python/Pydantic model for validating declarative configuration. Unlike the removed Resource artifact, this responsibility is structurally distinct from Generic: it defines accepted external input, defaults, constraints, extra-field policy, conversion, and invalid combinations. It is also distinct from DTO, whose primary responsibility is behavior-free data transfer across a boundary.

The current contract remains unusable when populated. It accepts primitive `"name: type"` field strings while the renderer reads structured field members; undefined members render malformed declarations that fail Python output validation. The renderer couples every `default_factory` to the S1mpleTrader-owned typed-ID pattern, permits unstructured string examples for object-shaped models, duplicates class identity in caller context, exposes project-oriented layer prose, and advertises automatic test creation.

**Recorded responsibility summary:** retain and adapt one language- and framework-qualified Python/Pydantic configuration model for declarative external configuration.

- The model owns a bounded, introspectable vocabulary for described fields, types, required/default/factory semantics, declarative constraints, explicit imports, strict extra handling, and explicit immutability.
- Optional examples are JSON-compatible configuration instances, are never invented, and are validated where the selected output capability can do so. They are not universally required merely because fields exist.
- The artifact remains separate from DTO and Generic even though all can render Python classes. Historical use of Schema provenance on output DTOs does not redefine the new responsibility or require rewriting independent production files.
- Typed-ID generation, architecture-layer headers, automatic tests, and project-specific imports are not package behavior.
- Complex validators, computed behavior, and the entire Pydantic API are not modeled as an unrestricted YAML programming language. Editing a valid scaffold remains normal.
- F-17 requires a language/framework-qualified identity through a clean break. The exact ID, finite field/constraint/factory representation, validation provider, and renderer composition remain Design-owned.

Direct blast radius includes the [Schema config](../../../.pgmcp/templates/config/schema.yaml), [Pydantic config renderer](../../../.pgmcp/templates/concrete/config_schema.py.jinja2), shared [Pydantic pattern](../../../.pgmcp/templates/tier3_pattern_python_pydantic.jinja2), removal of the [typed-ID pattern](../../../.pgmcp/templates/tier3_pattern_python_typed_id.jinja2), output validation, active scaffolding references, registry/type tests, and generated files carrying historical Schema provenance. Durable tests must verify structured contract/render parity and valid configuration-model output without asserting complete generated prose or preserving a stale artifact count.

#### Approved Service artifact removal and deferred command/query family (2026-08-24)

The public Service artifact combines a broad “orchestration or business logic” identity with one S1mpleTrader-derived asynchronous Service Command renderer. It forces Backend-layer prose, Translator/message-key infrastructure, module logging, capabilities-style DI, `Any`, broad exception translation, an `execute()` operation, and an async placeholder. Its public parameter strings contradict the structured members read by the renderer, so the property-complete schema-valid probe produces Python that fails output validation.

Historical issue-72 evidence shows that Service Command was selected as one of five minimal concrete templates to unblock scaffolding tests and was enriched from S1mpleTrader V2 pattern assumptions. Active files carrying Service provenance—presenters, a text limiter, a collection renderer, and a state validator—do not share the generated command structure. They are independent cohesive classes for which the approved Generic artifact is the portable scaffold responsibility.

The engine also contains hidden subtype routing in [TemplateScaffolder](../../../mcp_server/scaffolders/template_scaffolder.py): `service_type` selects command, query, or orchestrator paths even though the public schema does not expose that field and only the command concrete template exists. The legacy [ServiceScaffolder](../../../mcp_server/scaffolding/components/service.py) repeats the hardcoded map, silently defaults differently, and falls back to Generic when missing templates fail. These paths are structural debt, not dormant supported variants.

**Recorded disposition:** remove the broad Service artifact, its concrete command renderer, legacy scaffolder, and all service-specific hidden routing through a clean break.

- Existing generated production classes remain independent code and are not rewritten.
- Generic owns the portable scaffold need for ordinary cohesive Python classes, including classes named “service” by a workspace.
- Registry, active documentation, schema/tool enumeration, and tests must stop requiring Service or the command template solely for historical type completeness.
- Issue 460 does not create command, query, or orchestrator templates and does not preserve hidden routing as a temporary bridge.
- S1mpleTrader-specific command boilerplate remains covered by that workspace's deferred specialization boundary.

Command and Query can be more defensible responsibilities than a universal Service because they describe different behavioral contracts. They are nevertheless not approved package artifacts here. A future dedicated issue must establish concrete consumers, command/query semantics, input/output and side-effect boundaries, language/framework identity, relationship to Generic and Tool, and whether separate public types are justified. Orchestrator is not included automatically merely because the obsolete router named it.

#### Approved Tool artifact removal (2026-08-24)

The current Tool artifact claims an MCP tool but renders an untyped logged Python class with `async execute(**params: Any) -> Any`, a fabricated empty mapping result, and broad exception replacement. Its public context exposes no input/output contract, dependencies, protocol metadata, or consumer boundary. Syntax probes pass, but the generated class implements neither pgmcp's internal `ICoreTool` contract nor a declared external MCP SDK contract.

PGMCP's typed tool architecture is real and heavily used, but it is repository-specific. Encoding `ICoreTool`, `NoteContext`, wrapper, caching, presentation, or enforcement conventions in the distributed package suite would export stable workspace internals as a universal artifact. Conversely, MCP Python SDKs and harnesses choose different decorator, function, registration, and schema forms. A framework-neutral “Python tool” has no language-level structure beyond a described callable class or function and is therefore covered by Generic or future independently justified Python constructs.

**Recorded disposition:** remove the Tool artifact, public config, and concrete renderer through a clean break.

- Existing pgmcp tool implementations and internal tool architecture remain production behavior and are not rewritten.
- No pgmcp-specific or MCP-SDK-specific replacement is introduced.
- No deferred pgmcp/MCP tool artifact is recorded.
- Generic remains the portable scaffold for a plain Python class whose workspace assigns it a tool role.
- Active inventories, examples, agent instructions, schema enumeration, and tests must stop advertising or requiring the removed type.
- Forced logging, `Any`, broad exception mapping, fabricated results, layer prose, and automatic test intent are removed with the artifact rather than generalized.

Direct blast radius includes the [Tool config](../../../.pgmcp/templates/config/tool.yaml), [Tool renderer](../../../.pgmcp/templates/concrete/tool.py.jinja2), registry/type enumeration, active scaffolding documentation and agent examples, all-type smoke and template-content tests, and files that retain historical Tool provenance. Those generated files remain independent source and their provenance does not preserve the obsolete scaffold contract.

#### Approved Python/pytest unit-test responsibility (2026-08-24)

The Unit Test artifact has a durable responsibility distinct from Generic and Integration Test: express observable behavior of one bounded unit while keeping its collaborators controlled explicitly. The current public schema and renderer do not implement that responsibility coherently. `test_methods` is exposed as primitive strings but rendered as structured objects; optional `imported_classes` can normalize to a non-iterable value; broad booleans infer mocks, asyncio, Pydantic, and imports; and a test class is mandatory even where ordinary pytest functions are the clearer form.

More seriously, absent test intent produces a fabricated `test_placeholder`, while absent assertions produce `assert True`. The template therefore creates tests that can pass without proving behavior. Its embedded metadata also declares every unit test a RED/TDD-phase artifact and prescribes mocks, AAA comments, edge cases, and workflow sequencing regardless of the active workflow contract. That directly conflicts with the approved workflow-driven test strategy and encourages test explosion and maintenance ballast.

**Recorded responsibility summary:** retain and adapt one language- and framework-qualified Python/pytest unit-test artifact for explicit behavior cases.

- At least one concrete behavior case is required; callers that cannot state behavior must not scaffold a unit-test artifact yet.
- Cases, imports, fixtures, markers, sync/async execution, and test doubles are explicit contract data rather than inferred from broad booleans.
- The renderer never invents a placeholder, `assert True`, empty act/result, project import, error scenario, mock, or passing outcome.
- Function-based pytest tests remain valid; class grouping is optional rather than mandatory.
- Tests target observable behavior, not template prose, implementation structure, or workflow compliance.
- The artifact does not prescribe TDD or a RED phase; the active workflow and approved plan own test timing.
- Generated test code remains first-class code under the same architecture, typing, and quality standards as production code.

The exact structured case vocabulary, representation of executable arrange/act/assert behavior, grouping model, import/reference schema, incomplete-case rejection, and output-validation profile belong to Design. Design must preserve the minimum-one-case boundary and may not reintroduce fabricated passing evidence.

Direct blast radius includes the [Unit Test config](../../../.pgmcp/templates/config/unit_test.yaml), [renderer](../../../.pgmcp/templates/concrete/test_unit.py.jinja2), shared [pytest](../../../.pgmcp/templates/tier3_pattern_python_pytest.jinja2) and [test-structure](../../../.pgmcp/templates/tier3_pattern_python_test_structure.jinja2) patterns, async/mocking imports, registry/schema discovery, active testing/scaffolding guidance, all-type probes, and template/scaffolding tests. Existing tests that assert tier imports, metadata text, AAA comments, or placeholders require durable behavior-value review rather than mechanical preservation.

#### Approved TypeScript DTO-class responsibility (2026-08-24)

The public TypeScript DTO identity is already language-qualified and its generated framework-neutral data-carrier class has a defensible structure beyond a generic class: typed properties, explicit `readonly` intent, constructor initialization, and optional interface implementation. Current repository use is limited to scaffolding coverage, but absence of a local TypeScript application is not itself a removal criterion for a portable package artifact with an independently useful contract.

The current implementation nevertheless exposes `fields` as strings in the undocumented form `[readonly] name: type` and parses that mini-language inside Jinja. Splitting on `:` cannot safely represent ordinary TypeScript object and function types, malformed values silently default to `string`, and the same parsing is duplicated for declarations, constructor input, and assignments. The inherited TypeScript base also reads `module_title`, `module_description`, `layer`, `dependencies`, `responsibilities`, and structured imports that the artifact contract does not own. Its fixed `src/dtos/` base path assumes a consumer layout. The dedicated unit test reconstructs simplified templates rather than exercising the packaged graph, so it proves the manager can write a `.ts` file but not that the distributed contract and renderer remain coherent.

**Recorded responsibility summary:** retain and adapt one framework-neutral TypeScript DTO-class artifact.

- Structured typed properties replace the field-string mini-language through the approved clean-break schema strategy.
- Property optionality and immutability are explicit data, not syntax encoded in a field name.
- Constructor initialization remains part of the artifact's distinguishing behavior.
- Optional interface implementation remains explicit; dependencies or imports must not be inferred.
- Project layer, responsibilities, fixed directory layout, hidden metadata, and framework-specific validation/serialization behavior are excluded.
- No local TypeScript consumer is invented as justification, and the artifact is not retained merely as an engine demonstration.
- Durable coverage must exercise the real resolved package graph and observable TypeScript output/profile behavior rather than copy template content into the test.

The exact finite field schema, supported type-expression boundary, handling of defaults, comments/descriptions, constructor parameter representation, interface-reference shape, output-validation profile, and renderer organization belong to Design.

Direct blast radius includes the [TypeScript DTO config](../../../.pgmcp/templates/config/typescript_dto.yaml), [concrete root](../../../.pgmcp/templates/concrete/typescript_dto.ts.jinja2), [TypeScript DTO pattern](../../../.pgmcp/templates/tier3_pattern_typescript_dto.jinja2), [TypeScript base](../../../.pgmcp/templates/tier2_base_typescript.jinja2), shared code bases, output validation, registry/schema discovery, active documentation, and [dedicated scaffolding test](../../../tests/mcp_server/unit/managers/test_typescript_dto_scaffold.py).

#### Approved DTO responsibility (2026-08-24)

The DTO cluster currently exposes four incompatible stories:

| Evidence surface | Observable contract |
|---|---|
| `.pgmcp/templates/config/dto.yaml` / `scaffold_schema` | Requires `dto_name`; permits optional `fields: array<string>` and `description`; advertises an immutable Pydantic data container |
| Configured `concrete/dto.py.jinja2` | Uses `name`, structured field members, `frozen`, examples, dependencies, responsibilities, validators, and optional typed-ID factories that the public schema does not expose |
| Runtime-selected `concrete/dto_v2.py.jinja2` | Is selected only because the sibling filename exists; consumes primitive `"name: type"` strings, omits descriptions/examples/default semantics, and hard-codes `frozen=False` |
| Active callers and evidence | A schema-minimal DTO fails generated-output validation, a populated primitive-field DTO succeeds, active references call the type a frozen BaseModel, and tests exercise both hidden structured fields and the primitive V2 dialect |

Direct production blast radius includes the [DTO config](../../../.pgmcp/templates/config/dto.yaml), both [configured](../../../.pgmcp/templates/concrete/dto.py.jinja2) and [runtime-selected](../../../.pgmcp/templates/concrete/dto_v2.py.jinja2) renderers, the sibling-selection and compatibility logic in [ArtifactManager](../../../mcp_server/managers/artifact_manager.py), and the legacy [DTOScaffolder](../../../mcp_server/scaffolding/components/dto.py). Direct regression consumers include [all-type smoke coverage](../../../tests/mcp_server/integration/test_smoke_all_types.py), [artifact E2E coverage](../../../tests/mcp_server/integration/test_artifact_e2e.py), [concrete-template tests](../../../tests/mcp_server/integration/test_concrete_templates.py), [metadata coverage](../../../tests/mcp_server/integration/test_metadata_e2e.py), [provenance coverage](../../../tests/mcp_server/integration/test_provenance_e2e.py), and the shared [artifact test harness](../../../tests/mcp_server/fixtures/artifact_test_harness.py). Active guidance that currently promises primitive fields or frozen output includes [Template Library Usage](../../reference/TEMPLATE_LIBRARY_USAGE.md), the [Scaffolding Tool Reference](../../reference/tools/scaffolding.md), [MCP Vision Reference](../../reference/mcp_vision_reference.md), and the repository-local [Code Style Guide](../../coding_standards/CODE_STYLE.md).

**Recorded responsibility summary:** retain and adapt one portable, language-qualified Python/Pydantic DTO artifact as an immutable, behavior-free data-transfer contract.

- One caller-owned semantic identity may resolve to different class-symbol, file-name, and presentation forms. The scaffold envelope remains the identity boundary, but its raw `name` must not be copied blindly into every representation. Artifact/language naming policy must derive or validate each form explicitly; `dto_name` does not remain a competing caller-owned identity.
- A required artifact description, required descriptions for every supplied field, a valid Python module docstring, a concise class docstring, and Pydantic field descriptions form the portable self-documentation baseline. Documentation-generator dialects, extended Google/NumPy/Sphinx sections, project architecture headers, and domain-specific documentation policy remain workspace specialization.
- The artifact is `frozen=True` with `extra="forbid"`. Declarative field constraints and defaults that describe the data contract are legitimate; free validator bodies, arbitrary methods, lifecycle behavior, typed-ID factories, project imports, and automatic test generation are not package behavior.
- A schema-valid context with no fields produces a valid empty Pydantic skeleton class. It requires no example and emits no empty examples metadata. This supports workspace skeleton scaffolding before implementation details are known.
- Once at least one concrete field is supplied, at least one caller-supplied example is required. Each example represents a JSON-compatible serialized DTO instance, includes every required field, may omit optional/defaulted fields, and is never invented by the template.
- Where the selected output-validation capability can import or otherwise validate the generated DTO safely, examples are checked against it. Unavailable example validation remains explicit unavailable evidence rather than a silent pass.
- First-time-right means every schema-valid call yields a syntactically correct, structurally coherent, and—where the required capability is available—validatable artifact basis without repair. It does not mean the artifact is application-complete; editing after scaffolding is a normal, healthy workflow action.
- The implicit `_v2` sibling selection is removed under F-04/S-08, the typed-ID dependency remains outside the portable suite under F-14, and primitive field strings receive no compatibility bridge under S-02.

The exact language-qualified type ID, naming-profile representation, conditional JSON Schema, structured field/default/constraint vocabulary, docstring layout, example-validation provider, and renderer organization belong to Design. Design may not weaken the approved empty-skeleton behavior, conditional example obligation, self-documentation baseline, immutability, or one-identity invariant.

#### Approved Generic Python class responsibility (2026-08-24)

The public `generic` type currently combines two responsibilities that must be separated before its artifact disposition can close:

| Evidence surface | Observable contract |
|---|---|
| [Generic config](../../../.pgmcp/templates/config/generic.yaml) / `scaffold_schema` | Requires a class `name`; exposes optional description, project-oriented layer, primitive method strings, and responsibilities |
| [Generic renderer](../../../.pgmcp/templates/concrete/generic.py.jinja2) | Presents a catch-all Python class, consumes structured method members, forces module logging and a logger, hard-codes a Backend layer fallback, and fabricates a placeholder method when none is supplied |
| Public probes | Minimal context succeeds, but the property-complete schema-valid context fails because a string method has no `name` member |
| [TemplateScaffolder routing](../../../mcp_server/scaffolders/template_scaffolder.py) | Also treats generic as an escape hatch: hidden `template_name` context can replace the registered renderer, and a missing generic root may be supplied at call time |
| Legacy component scaffolders | [DTO](../../../mcp_server/scaffolding/components/dto.py), [worker](../../../mcp_server/scaffolding/components/worker.py), [service](../../../mcp_server/scaffolding/components/service.py), [schema](../../../mcp_server/scaffolding/components/schema.py), and [tool](../../../mcp_server/scaffolding/components/tool.py) can fall back to legacy generic component rendering after a missing-template error |
| Active guidance and tests | [Scaffolding reference](../../reference/tools/scaffolding.md) and [Quick Reference](../../reference/TEMPLATE_LIBRARY_QUICK_REFERENCE.md) describe a generic Python catch-all; [template-resolution tests](../../../tests/mcp_server/unit/scaffolders/test_template_scaffolder.py) preserve the hidden custom-template override; [concrete-template tests](../../../tests/mcp_server/integration/test_concrete_templates.py) preserve project-style headers and imports |

Several outcomes are already constrained by approved cross-cutting strategies:

- Under F-07, renderer selection is declarative registry configuration, not hidden caller context. `template_name` cannot remain a generic routing key or an override available to every artifact.
- Under F-10 and F-16/F-18, a workspace-owned custom template is installed as an explicit active-suite artifact with its own discoverable ID, purpose, and contract. It is not tunneled through a generic artifact call.
- Under Fail-Fast and the one-contract invariant, a missing specialized template fails instead of silently producing a different generic artifact.
- Under F-14, the portable package type cannot force project layers, responsibilities, or logging. Logging remains an available shared pattern for artifact types whose own contract selects it; it is not a generic-class default.
- Under F-17, any retained type receives a language-qualified identity. The scaffold-envelope naming and representation warning approved for DTO applies equally to a Python class symbol and file target.

**Recorded responsibility summary:** retain and adapt a bounded, language-qualified plain Python class skeleton for concrete classes that do not match a more specialized artifact contract.

- Callers choose this artifact deliberately after purpose-aware discovery. It is not an automatic catch-all, a fallback for a failed specialized artifact, or a custom-template router.
- A required description, a valid Python module docstring, and a concise class docstring form the portable self-documentation baseline.
- A schema-valid call without base classes or methods produces a valid empty class with `pass`. It does not fabricate a placeholder method, logger, architectural layer, or responsibility list.
- Optional structured imports and base-class declarations may capture already-known structural dependencies.
- Optional structured method signatures may capture method name, sync/async form, structured parameters, return annotation, and required method description/docstring without fixing implementation details.
- Caller-supplied method bodies are excluded. A declared but unimplemented method fails explicitly through a valid `NotImplementedError` stub until normal editing supplies behavior; it does not silently return `None`.
- Constructors with assignments, arbitrary decorators, free source fragments, logging, project imports, architecture metadata, and automatic test generation remain edit-time work or workspace-owned specialization.
- One semantic artifact identity resolves explicit Python-symbol and file-target representations under the naming boundary established for DTO.
- Hidden `template_name` routing is removed. Workspace-owned templates become explicit active-suite artifact registrations with their own discoverable IDs, purposes, and contracts.
- Missing specialized templates fail fast; legacy DTO, worker, service, schema, and tool fallback paths may not substitute a generic class.
- First-time-right retains the approved meaning: a valid, coherent, and applicable-profile-validatable skeleton that is expected to be edited, not an application-complete class.

The exact language-qualified ID, import/base/method JSON Schema, allowed initial method kinds, naming-profile mechanics, stub rendering, and shared Python-class composition belong to Design. Generic must remain finite and must not absorb functions/modules, enums, exceptions, dataclasses, abstract contracts, or other constructs merely to simulate broad Python coverage; those are separate candidate artifact responsibilities.

#### Design hand-off

Design must choose the JSON Schema draft, authoring layout, local versus suite-shared composition mechanism, standards-compliant validation/resolution implementation, and lifecycle of resolved schemas. It must also separate suite-owned context from server-owned scaffold metadata. For schema guidance, Design must define how schema-level and property-level descriptions reach `scaffold_schema`, and how phase-oriented artifacts refer callers to the already-loaded active phase instructions without duplicating their text. The exact reference carrier and resolution mechanism are Design decisions. These choices may not contradict the canonical Research decision register, create a parallel workflow contract, or reintroduce artifact-specific context models in pgmcp.

### F-02 — optionality has inconsistent meaning

The current dynamic model path converts every absent field with required: false into an explicit null-equivalent value. This collapses four distinct caller states before rendering: omitted, explicit null, an empty typed value, and a populated value.

#### Manifestations

- [unit_test.yaml](../../../.pgmcp/templates/config/unit_test.yaml) declares imported_classes as an optional string array. Omission becomes None, so the [template fallback and join](../../../.pgmcp/templates/concrete/test_unit.py.jinja2) receive a defined non-iterable value instead of activating the default list; the minimal public context can fail during rendering.
- [validation_report.yaml](../../../.pgmcp/templates/config/validation_report.yaml) declares scope as an optional string. Omission becomes None, so the [template fallback](../../../.pgmcp/templates/concrete/validation_report.md.jinja2) does not activate and the artifact can render the literal word None.
- Boolean false, numeric zero, an empty string, and an empty collection can be deliberate values. Treating every falsey value as missing through broad template defaults would replace caller intent rather than solve the contract defect.

In standard JSON Schema, a property that is absent from required may be omitted but is not thereby nullable. Null is valid only when the property schema explicitly admits it. JSON Schema defaults are annotations unless the consuming system defines deterministic materialization behavior.

#### Boundary and consumer blast radius

| Boundary | F-02 impact |
|---|---|
| Template-suite context contracts | Must declare requiredness, nullability, empty-value constraints, and any semantic default separately |
| Pgmcp validation and normalization | Must preserve omission rather than inject None for every optional property |
| Resolved render context | Must contain caller-provided values and only defaults whose application is explicitly defined |
| Jinja templates | May distinguish undefined, empty, false, zero, null, and populated values according to the declared contract |
| scaffold_schema | Must expose whether omission and null are valid and whether a default exists |
| Agent callers | Can omit optional values without guessing null or empty sentinels |
| Tests and suite auditing | Must treat omitted, null, empty, false/zero, and populated values as distinct representative cases |
| Documentation | Must not use optional as a synonym for nullable |

#### Historical Preservation Rationale

- Preserve intentional false, zero, empty-string, and empty-collection values.
- Preserve template-owned presentation fallbacks where omission is valid.
- Preserve explicit useful defaults, but require their effect to agree between introspection, validation, and rendering.
- Do not preserve automatic None injection as supported behavior.
- Every accepted context must retain the caller's semantic distinction through rendering.

#### Historical Decision Rationale

- Optional means that a property may be omitted. It does not make null a valid value.
- A present property must satisfy its declared type and constraints.
- Empty strings, collections, false, and zero remain distinct typed values unless the schema explicitly excludes them.
- Nullability is allowed only where null has an explicit domain meaning.
- Pgmcp must not automatically materialize omitted properties as None.
- Declared defaults must have one deterministic externally observable effect; their exact application mechanism is deferred to Design.

#### Design hand-off

Design must determine how the chosen JSON Schema validator preserves omitted keys, where declared defaults are applied, and how server-owned render metadata is added without changing suite-owned omission semantics. It must not solve the problem through blanket falsey normalization or template-by-template None coercion.

### F-03 — strict schema validation is weakened before it runs

Scaffolding has two legitimate input-validation boundaries:

1. The static MCP tool envelope validates artifact_type, name, output_path, and the fact that context is an object.
2. After artifact_type resolves the contract, dynamic artifact-context validation checks the caller-owned context against that suite-owned schema.

These boundaries serve different purposes and must remain separate. The outer tool schema cannot contain every artifact-specific field; the selected artifact schema is the authority for those fields.

The current implementation mixes caller-owned artifact context with tool- and server-owned render values before dynamic validation. It then reduces the combined dictionary to fields known by the selected schema. This allowed values such as name and output_path to travel toward rendering without being rejected by the artifact schema, but the filter is broader than that lifecycle need. It also removes unknown caller fields before the strict model with extra-forbid behavior sees them. Name is restored after validation, demonstrating that the filtering is a pipeline workaround rather than intended caller tolerance.

#### Observable failure

- A misspelled or obsolete caller field appears accepted while its content is lost.
- A renderer capability omitted from scaffold_schema cannot be supplied, even if a caller learned about it elsewhere.
- Strict unknown-field rejection is configured but cannot protect the public contract because the unknown value has already disappeared.
- Combining the namespaces creates ambiguous precedence when an artifact-context key resembles a tool-envelope or provenance value.

The first-time-right contract requires error visibility. Silent loss is not supported compatibility behavior and is more damaging than an actionable validation failure.

#### Historical Decision Rationale (2026-08-23)

- Preserve the two-stage validation model: the static tool envelope remains generic, and the resolved artifact schema validates artifact-specific context.
- Validate the original caller-owned context without pre-filtering or silent key removal.
- Closed schema objects reject undeclared properties with actionable path context. Deliberately open maps remain possible only when the suite-owned schema explicitly defines that openness.
- Keep validated tool-envelope values such as name and output_path, and server-owned provenance or timestamp values, outside caller-owned artifact context during artifact validation.
- Add those values only after artifact-context validation through an explicit render-context boundary.
- Treat ownership semantically rather than lexically: a content field is not redundant merely because it is also called `name` or `title` elsewhere.
- A renderer may derive a symbol, file stem, display form, or other name representation from envelope identity only through a deterministic artifact/language naming profile, such as case conversion, normalization, or a declared artifact-specific prefix/suffix.
- If the required value needs business interpretation, combines independently meaningful inputs, loses caller intent, or cannot be validated as one deterministic representation, expose it as an explicit suite-owned artifact-content field. Do not force inference merely to avoid similarly named values.
- Do not introduce a compatibility bridge for silently ignored keys; silent acceptance was not a reliable contract.

#### Design hand-off

Design must define the typed boundary and deterministic merge rules between caller-owned artifact context, validated tool-envelope input, and server-owned render metadata. It must specify collision handling, which values are visible to templates, and the finite naming profiles that may derive artifact/language representations from envelope identity. Each artifact schema audit must distinguish a pure representation from a semantically independent name or title; the latter remains explicit context. The exact classes and pipeline arrangement belong to Design; template-specific field names and composition rules must not leak into generic pgmcp code.

### F-04 — DTO introspection and DTO runtime selection are split

The public DTO registration selects concrete/dto.py.jinja2, but its declarative context still describes fields as primitive strings. Artifact creation prepares version and tier provenance for that configured template, then conditionally replaces the renderer with concrete/dto_v2.py.jinja2 whenever the conventionally named file exists. The substitution is based on filesystem presence rather than an explicit registry decision.

The two templates implement different DTO languages:

- dto.py.jinja2 expects structured field objects and supports descriptions, defaults, default factories, validators, examples, dependencies, responsibilities, and configurable immutability;
- dto_v2.py.jinja2 expects strings such as name: type, splits presentation syntax inside Jinja, fixes frozen to false, and synthesizes generic descriptions.

The current scalar context shape happens to align more closely with dto_v2, while template registration, graph discovery, version hashing, and provenance begin from dto.py. Removing or adding the _v2 file can therefore change generated behavior without changing configuration. The caller-facing schema, identified template graph, and actual renderer do not share one authority.

#### Historical classification

The _v2 convention originated in the issue-135 Pydantic scaffolding migration. Later issue-349 research and design approved removal of the V1/V2 pipelines and their feature flag in favor of one declarative runtime model. The remaining filename substitution and name-to-dto_name compatibility copy are therefore migration residue, not an intentional current extension mechanism.

#### Boundary and consumer impact

- scaffold_schema cannot promise the semantics of the runtime renderer while selection occurs later and implicitly.
- Provenance can identify and hash dto.py contributors while dto_v2 produced the file.
- Template-suite maintainers cannot reason from registry configuration alone.
- Agent callers cannot deliberately choose or discover the variant.
- No persistent external context consumer requires preservation of the primitive DTO dialect.

#### Historical Decision Rationale (2026-08-23)

- Select exactly one DTO renderer declaratively; filesystem presence must never override the registered artifact.
- Use one resolved authority for the public context schema, runtime renderer, template graph, version identity, and provenance.
- Use the richer structured DTO field language as the canonical direction established by F-01.
- Remove the obsolete implicit V2 compatibility behavior; do not expose a second versioned artifact type or temporary bridge without a distinct supported consumer.
- Preserve DTO as one public artifact type while improving its discoverable context contract through a clean break.

#### Design hand-off

Design must define the canonical DTO field object and the exact retained DTO capabilities, then align the registry, resolved graph, validation, rendering, and provenance with that selection. It must identify obsolete DTO migration artifacts for removal without generalizing a DTO-specific convention into the generic runtime.

### F-05 — the resolved tiered graph is not fully introspected

A rendered artifact is produced by a dependency graph rather than one concrete file. For example, the DTO renderer extends tier2_base_python, which extends tier1_base_code and then tier0_base_artifact; it also imports the Pydantic and typed-ID pattern templates. Inheritance contributes structure and blocks, while imports contribute macros that emit artifact content.

The current analyzer finds parent templates with a handwritten regex that recognizes only an untrimmed double-quoted extends statement. The suite predominantly uses Jinja whitespace-trimmed statements such as {%- extends "tier2_base_python.jinja2" -%}, so the detected chain can stop at the concrete template. Import, from-import, and include dependencies are not part of the graph at all. Jinja itself still resolves these dependencies during rendering, creating a split between actual behavior and analyzed identity.

#### Observable impact

- A shared base or macro can change generated artifacts without changing their reported version hash.
- Provenance can omit files that materially produced the artifact.
- Missing or invalid static dependencies can survive startup and fail only when an agent scaffolds the affected type.
- Suite renewal and contract validation cannot prove that all semantic contributors travel as one coherent version.
- Future schema-composition checks cannot safely associate a resolved contract with the actual renderer graph.

#### Authority distinction

Real Jinja syntax analysis can identify statically referenced templates and top-level undeclared variables, but it cannot reliably infer a complete nested JSON data model from expressions such as field.name. The suite-owned JSON Schema remains authoritative for caller-context types and constraints. The resolved Jinja graph is independently authoritative for the templates and macros that produce output. Pgmcp verifies their coherence without heuristically generating one authority from the other.

#### Historical Decision Rationale (2026-08-23)

- Replace regex-based dependency discovery with real Jinja syntax analysis.
- Resolve every static extends, import, from-import, and include edge used by the selected renderer.
- Include every resolved semantic contributor in startup validation, version identity, and provenance.
- Resolve the complete suite once during server startup into one coherent, restart-stable suite view shared by scaffold_schema and scaffold_artifact. Research requires one authority and restart semantics; Design chooses its concrete representation.
- Require a server restart after any template or suite-contract addition, modification, or removal; do not add file watching, hot reload, or per-call graph analysis.
- Fail fast on missing dependencies, dynamic references that cannot be resolved deterministically, and dependency cycles.
- Do not duplicate statically discoverable edges in manually maintained metadata.
- Permit explicit dependency metadata only for a genuine semantic dependency that Jinja syntax cannot reveal.
- Keep suite-owned JSON Schema authoritative for data shape; Jinja analysis may verify variable/dependency coherence but must not invent nested types.

#### Design hand-off

Design must choose the parser-supported Jinja dependency API, resolved-graph value model, deterministic traversal and identity ordering, restart-stable suite-view boundary, and actionable startup failure format. It must define how graph evidence is checked against the suite-owned schema while preserving their separate responsibilities. Runtime tool calls must consume the startup-resolved view without rereading or reanalyzing suite files.

### F-06 — link values do not have one canonical representation

The related-document macro emits reference-style link uses but does not emit matching definitions. Document-oriented artifacts may add definitions through separate blocks, while the tracking-oriented PR and issue graphs import the same macro without that parent behavior. The reference artifact independently emits source and test references without definitions.

The string schema is ambiguous: a caller cannot know whether a value is a raw path or URL, a visible label, or preformatted Markdown. A raw target can become an unresolved reference; preformatted Markdown can be nested inside another generated link. Repairing definitions template by template would leave this caller-contract ambiguity intact.

#### Semantic and presentation boundaries

A link has two semantic values: visible label and target. Whether those values render as an inline Markdown link or as a reference-style use plus centralized definition is presentation policy owned by the resolved artifact. Reference-style links remain valuable because the target has one in-document source of truth and can be updated independently from its uses.

The caller must not select style or supply Markdown. The same structured link data supports both renderers:

- inline: the visible `Scaffolding reference` label and its `docs/reference/scaffolding.md` target occur at the use site;
- reference-style: `[Scaffolding reference][related-1]` is paired with a `related-1` definition whose target is `docs/reference/scaffolding.md`.

#### Historical Decision Rationale (2026-08-23)

- Use one canonical link object with required, non-empty label and target properties.
- Do not permit caller-supplied Markdown or an implicit target-as-label shorthand.
- Support both inline and reference-style rendering as first-class suite behavior.
- Let the concrete artifact or its selected macros choose the render strategy; style is not caller data.
- Require every reference-style use and its matching definition to belong to the same resolved artifact graph.
- Do not rely on accidental inheritance from another template family to supply definitions.
- Keep reference identifiers template-owned and deterministic unless a concrete future consumer establishes a need for caller-owned identifiers.

#### Design hand-off

Design must define the reusable suite-owned link schema, inline and reference render macros, identifier namespace and deduplication rules, and startup coherence checks that prevent orphaned uses or definitions. It must preserve reference-style target SSOT while keeping caller input presentation-neutral.

### F-07 — exposed, hidden, and unused fields are mixed

The current artifact schemas mix body or file content with values belonging to tool envelopes, hidden routing, and obsolete migrations. Conversely, inherited templates consume legitimate content that scaffold_schema does not expose. Silent filtering from F-03 masks both directions.

#### Confirmed mismatches

- PR tracking_state is accepted but never rendered; deferred_work already owns the visible hand-off.
- Architecture constraints is accepted but not rendered, despite constraints being part of the declared artifact purpose.
- Reference inherits and consumes purpose although scaffold_schema does not offer it.
- TypeScript DTO inherits layer, dependencies, and responsibilities, but only fields and implements are discoverable; name arrives through the scaffold tool envelope.
- Service contains Python-specific hidden subtype routing for command, query, and orchestrator, although service_type is not public and only the command renderer exists.
- Research gives references precedence over related_docs, silently discarding the latter when both distinct content concepts are supplied.
- Issue and PR body schemas carry external titles and GitHub operation metadata. Issue additionally renders labels, milestone, and assignees into body text even though those values belong to create_issue arguments.

#### Recorded Boundary Model

The artifact context exposed by scaffold_schema contains only caller-owned values intentionally rendered as artifact content. It is not a transport for a later tool's envelope.

- The scaffold tool envelope validates values such as name and output_path separately. A resolved renderer may receive them only after artifact-context validation where they have a legitimate render use. Name representations may be derived only through an explicit deterministic naming profile; semantically independent titles, subjects, labels, or symbols remain artifact content.
- Server-owned artifact type, timestamps, version identity, and provenance are injected separately.
- Downstream GitHub title, labels, milestone, assignees, branch, base, draft, and similar operation inputs remain governed by their own tool schemas and do not travel through an issue or PR body context.
- If a concept genuinely belongs in the body, its concrete template defines a content field and renders an explicit section. It does not reuse an identically named downstream API field as implicit metadata.
- Template routing is declarative artifact configuration, not a hidden context key or Python dispatch table.
- Any caller-context property without a rendered effect is removed. Any renderer-required caller content is exposed in the suite-owned schema.

#### Recorded Field Outcomes

| Current value | Outcome |
|---|---|
| PR tracking_state | Remove; deferred_work remains the rendered contract |
| Architecture constraints | Retain as content and render explicitly |
| Reference purpose | Expose as caller content |
| TypeScript DTO layer, dependencies, responsibilities | Expose as inherited caller content; keep name in the tool envelope |
| Service service_type override | Remove hidden routing and nonexistent variants; use the declaratively registered renderer |
| Research references and related_docs | Preserve both distinct content concepts and render both without fallback shadowing |
| Issue/PR title | Remove from body context; downstream tool envelope owns the external title |
| Issue labels, milestone, assignees and comparable PR/GitHub metadata | Remove from body context; downstream tool schemas own them |

#### Recorded Tracking-Artifact Behavior

- Commit scaffolding retains responsibility for conventional-commit content. Its caller contract must distinguish the subject, optional scope and body, breaking-change intent, free-form footer content, and referenced issue identities without making callers supply presentation punctuation.
- Issue scaffolding produces body content only. Reproduction steps are an optional ordered sequence and render as numbered steps. External title, labels, milestone, and assignees remain downstream issue-tool envelope data. Internal and external document references retain their approved explicit link semantics.
- PR scaffolding produces body content only. Deferred work is never silently omitted: the body states either that none was found or describes the work identified within the current change. The implementation agent reports potential follow-up work; the coordination agent exclusively owns triage, deduplication, prioritization, issue creation or reuse, and cross-issue linkage. Research requires no `tracking_issue` field or equivalent coupling.
- The exact nested properties, conditional constraints, and rendering forms belong to Design. Research fixes the observable responsibilities and ownership boundary only.

No compatibility bridge is required because the agent is the only relevant runtime caller and rediscovers both scaffold and downstream tool schemas before use.

#### Startup coherence

The F-05 startup resolver compares suite-owned context properties with variables read across the resolved Jinja graph and with explicitly available scaffold-envelope or server metadata. A caller-content property that is not rendered, or a renderer content variable with no valid source, fails startup. Downstream tool arguments are not valid sources for artifact rendering.

#### Design hand-off

Design must define the resolved input-source classification and coherence diagnostics without adding artifact field names to generic Python. It must update every affected suite schema and renderer consistently, preserve deliberately distinct content concepts, and keep downstream operation DTOs outside the artifact-context model.

### F-08 — schema-valid rich contexts can produce invalid source

The substantive probes found source-level failures when richer schema-valid values were supplied:

- adapter, generic, interface, resource, integration_test, and unit_test can fail while trying to access object members on strings;
- schema and service can render invalid Python when string items are interpreted as structured definitions;
- the runtime DTO template can render invalid Python for a minimal schema-valid context while accepting a richer string-based context.

The public success criterion must be “usable artifact from any valid context,” not “the renderer returned non-empty text.”

#### Current validation ambiguity

The current validation boundary conflates three independent concerns:

1. an output profile determines which rules apply to an artifact;
2. an applicable validator determines whether the rendered output passes those rules;
3. strict_validation determines whether a failed or unavailable validation may be persisted.

The default for strict_validation is false. Code artifacts currently override it to true, while document and tracking artifacts generally inherit the permissive default. More importantly, an empty validator set currently returns passed=true. A strict artifact can therefore appear validated even when no matching validator ran; the TypeScript DTO is a present example.

Extension-only selection is also too coarse. A complete Markdown document may require an H1, while a GitHub issue body intentionally excludes the external issue title and may validly begin with an H2. Missing an H1 is not a validation failure for that output profile under either strictness setting. Strictness must never change the truth of a validation outcome; it changes only the persistence policy after that outcome.

#### Boundary and consumer blast radius

| Boundary | F-08 impact |
|---|---|
| Artifact configuration | Must declare the required output-validation capability and distinguish validation policy from output validity |
| Portable template suite | May contain many dormant language templates without carrying or activating every language toolchain |
| Startup catalog | Validates template syntax, graph integrity, schema coherence, and configuration combinations without requiring providers for every dormant artifact |
| Validator discovery | Resolves a configured capability through an extensible injected boundary; language and output-profile dispatch must not be hardcoded in the scaffold pipeline, while the concrete registry/container shape remains Design-owned |
| scaffold_artifact | Resolves the selected capability before mutation, renders in memory, validates the concrete result, and persists only according to the declared policy |
| Validation result | Must distinguish passed, failed, and unavailable/not executed evidence without converting one state into another through strictness |
| Human and agent caller | Receives an actionable missing-capability or output-validation result for the selected artifact |
| Tests | Protect observable schema-to-render-to-validation behavior through public APIs without permanent example-code fixtures or template-prose snapshots |

#### Historical Preservation Rationale

- Preserve a broad independently reusable template suite; unused template languages do not impose workspace dependencies.
- Preserve in-memory rendering followed by pre-persistence validation where a capability is declared.
- Preserve explicit opt-out behavior, but make it visible and intentional.
- Do not require permanent suite-owned example contexts solely to exercise validators.
- Do not infer validity from non-empty output, absence of a renderer exception, an empty validator set, or strictness itself.
- Do not treat rules from a different output profile as failures.
- A concrete requested artifact either runs its applicable validator and reports the real result or reports that the required capability is unavailable before filesystem mutation.

#### Reconciliation option analysis

| Option | Cost, risk, consumer impact, and migration consequence |
|---|---|
| Hardcode validators by artifact name or extension in the scaffold pipeline | Direct implementation, but couples pgmcp to suite languages/profiles, violates open extension, and makes future types server changes |
| Declare required output evidence and resolve a suitable validator only when that artifact is requested | Preserves dormant portable templates and extensibility; requires a Design-owned resolution/injection mechanism and explicit unavailable state |
| Require every possible validator at startup | Strong global availability signal, but makes unrelated dormant templates impose toolchain dependencies and can prevent otherwise valid startup |
| Persist first and validate afterward | Simplest execution order, but violates strict first-time-right persistence and leaves cleanup/recovery after invalid output |

Research selects the observable policy—declared applicable evidence, distinct passed/failed/unavailable states, and strict pre-persistence enforcement—not a concrete provider container, registry API, or call topology. On-use injected resolution remains the leading Design hypothesis because it satisfies those constraints without hardcoded language dispatch.

#### Quality-gate consolidation boundary (approved 2026-08-25)

The current runtime implements two overlapping routes. `ValidationService` owns artifact and extension dispatch plus canonical issue aggregation, while `QAManager` owns configured quality-gate execution. `PythonSyntaxValidator` already delegates its full-QA path to `QAManager`, but does so through a temporary file and then translates a manager-specific dictionary. At the same time, `ArtifactManager` and `SafeEditTool` construct validation services independently, and bootstrap constructs the quality manager separately. This is evidence of duplicated authority and dependency wiring, not evidence that either current top-level class should become the universal validator.

The approved boundary is one injected, config-first catalog of executable check capabilities plus one normalized execution/result boundary:

- a capability's provider, command, availability semantics, and result parsing are defined once;
- artifact output profiles and quality gate sets are selectors over that same catalog rather than parallel validator definitions;
- scaffolding and safe edit run applicable checks against the complete proposed content before mutation and do not acquire quality-state, baseline, logging, or autofix side effects;
- `run_quality_gates` may add requested file/branch/project scope, quality-state lifecycle, diagnostics/presentation, and optional fixing around the shared execution boundary;
- strictness determines whether a proposed mutation may persist, never whether evidence is reported as passed, failed, unavailable, or not executed.

“Quality” qualifies the gates. A workspace is only one possible execution scope and therefore must not become a second semantic owner or configuration authority. Input JSON Schema validation, startup graph/coherence validation, workflow-gate enforcement, and behavioral test execution remain separate because they prove different contracts. Design owns the exact configuration layout, interfaces, adapters, and composition-root topology; it may not introduce a third output-profile provider/command authority while reconciling the two current paths.

#### Historical Decision Rationale (2026-08-23)

- Change strict_validation to default true. Omission means validation is blocking by default; false is an explicit per-artifact opt-out.
- With strict_validation=true, persistence requires the selected configured capability to be available, executed, and passing. A missing provider blocks only when that artifact is requested, not when an unrelated dormant template is loaded.
- With strict_validation=false, a real validation failure remains failed and an unavailable validator remains unavailable; the policy may permit persistence but must report the retained outcome explicitly.
- The portable artifact contract declares an output-validation capability or profile. Pgmcp treats its identifier opaquely and resolves it through injected, extensible provider registration without language-, extension-, or artifact-name if-chains in the scaffold path.
- Output-profile semantics determine applicable rules. A GitHub Markdown body is not failed for omitting a document H1; a full Markdown document may use a profile that requires one.
- Startup performs language-agnostic structural checks for every template. Provider availability is resolved at the earliest relevant execution boundary so a large dormant catalog does not inflate each workspace.
- The selected provider is checked before rendering or mutation, the artifact is rendered in memory, and the rendered output is validated before persistence.
- Permanent example content is not required. Existing examples may provide supplementary audit evidence but are neither authoritative nor necessary for the runtime guarantee.
- Apply the stricter default as an intentional behavior correction without a temporary permissive bridge. Every existing explicit or inherited opt-out must be reviewed rather than mechanically retained.

#### Design hand-off

Design must define the declarative capability/profile and quality-gate selector shapes, the single shared capability catalog and normalized execution/result boundary, provider discovery and injection, result states for passed, failed, unavailable, and not-executed validation, and the exact pre-persistence sequence. It must reuse strict_validation as enforcement policy rather than duplicate it, preserve quality-gate scope and lifecycle behavior outside side-effect-free pre-mutation validation, validate inconsistent configuration combinations at startup, and keep dormant-provider absence out of global startup failure. It must also audit current Markdown, Python, TypeScript, tracking, text, and document profiles so the default change does not apply irrelevant rules.

### F-09 — documentation competes with scaffold_schema

Several references contain examples or minimum-field tables that do not match the live introspection response. Examples include:

- the scaffolding reference reports 21 types while 22 are exposed;
- worker examples use fields that are absent and omit a required layer;
- design and architecture examples omit live required values and include absent ones;
- quick-reference entries understate generic_doc requirements;
- commit is described using workflow_phase while scaffold_schema requires type;
- validation_report examples use validation_outcome while scaffold_schema exposes validation_status.

Human documentation must explain semantics and show calls, but it must not become a separately maintained field inventory.

#### Root cause and manifestation

The documentation currently duplicates three kinds of live contract data:

1. exact artifact counts and identifier inventories;
2. hand-maintained minimum-required-field tables;
3. executable-looking context examples that imply a complete valid call.

These forms drift immediately when an artifact or field changes. Because closed artifact schemas reject unknown values, the consequence is not merely imprecise prose: an agent following the documented worker or architecture examples receives an avoidable validation failure and must rediscover the contract through scaffold_schema. Updating the current tables to today's schemas would repair individual examples while preserving the structural source of recurring documentation debt.

#### Boundary and consumer blast radius

| Boundary | F-09 impact |
|---|---|
| scaffold_schema | Remains the sole authority for exact field names, shapes, requiredness, defaults, and constraints |
| Runtime artifact catalog | Remains the authority for the installed artifact inventory; documentation must not freeze its count independently |
| Scaffolding and template references | Retain semantic explanations, architecture, workflow, and navigation while removing competing contract copies |
| Agent instructions | Teach schema discovery and authority boundaries rather than embedding artifact-specific field inventories |
| Examples | May illustrate the discovery sequence or domain meaning but must not masquerade as an independently maintained executable contract |
| Documentation automation | Generation is justified only for an exact inventory or example with demonstrated human value; it is not required merely to retain existing duplication |
| Tests | Must not lock prose, artifact counts, or field-name tables through fragile documentation snapshots |
| Release and maintenance | Reconciliation follows the final issue-460 contract so active documentation tells the current story without a historical migration trace |

#### Historical Preservation Rationale

- Preserve useful explanation of the scaffolding workflow, artifact purpose, architecture, validation behavior, and caller responsibilities.
- Preserve scaffold_schema-first instructions and actionable examples of that interaction pattern.
- Do not preserve manually maintained exact counts, complete field inventories, or minimum-context tables as a second contract.
- Do not correct examples against an intermediate schema that issue 460 is about to replace.
- Complete executable examples are retained only when they are derived from or generically checked against the live contract; otherwise use explicit pseudocode or remove them.
- Documentation and agent instructions must not require prose-snapshot or field-list tests to remain synchronized.
- A future artifact or field addition must not create immediate documentation debt solely because a hand-maintained duplicate exists.

#### Historical Decision Rationale (2026-08-23)

- Treat scaffold_schema as the only caller-facing SSOT for exact context fields and the runtime catalog as the only installed-inventory SSOT.
- Remove static exact artifact counts and manually maintained minimum-required-field inventories from active prose. Where an exact inventory has proven human value, derive it from the runtime catalog rather than hand-maintaining it.
- Keep human-authored documentation focused on semantics, conceptual distinctions, lifecycle, and the schema-discovery workflow.
- Prefer discovery-sequence pseudocode over full contexts. Retain full executable examples only when a generic derivation or validation mechanism justifies their maintenance cost.
- Do not introduce documentation tests that assert prose, artifact counts, or duplicated field lists.
- Reconcile active documentation and agent instructions once against the final implemented issue-460 contracts, without preserving stale examples as compatibility behavior.
- Apply YAGNI to generation: removal is the default; introduce derived documentation only for information whose human value is explicit.

#### Design hand-off

Design must identify the active references that currently duplicate exact contract data and classify each block as semantic explanation, removable duplication, or demonstrably valuable derived content. It must define no per-artifact documentation matrix in pgmcp code and must not add a generation subsystem unless a retained exact view requires one. Documentation work must target the final resolved catalog and schemas, not the current defective surface.

### F-10 — renewal can split paired assets

Release packaging copies both templates and their contract configuration as assets. Workspace renewal treats configuration paths as preserve-worthy while renewing template files.

Because template contract files live below a path containing config, renewal can preserve an older contract while installing newer Jinja content. This defeats atomic versioning of the independently maintained suite.

The current heuristic preserves any existing YAML file whose path contains config and renews other assets. It does not compare versions or ownership. A release that changes both templates/config/adapter.yaml and concrete/adapter.py.jinja2 can therefore leave the old contract beside the new renderer, reproducing the F-01 mismatch in an upgraded workspace even though the packaged release itself is coherent.

#### Ownership model

One active template root remains the sole runtime authority and is intentionally user-extensible. A separately staged packaged candidate is a distribution source only; the template engine and catalog never read it implicitly. This distinction permits user modification without requiring package overlays, precedence rules, or semantic merge analysis.

The active root is compared with the last officially installed suite baseline, not with the incoming candidate. A content manifest must identify the complete official baseline through stable suite identity and deterministic file-content evidence. Runtime artifact provenance in template_registry.json is usage-dependent and cannot serve as that installation baseline.

#### Renewal decision model

| Active target state | Required renewal behavior |
|---|---|
| Missing on clean initialization | Install the packaged suite atomically and record it as the official baseline |
| Byte-equivalent to the recorded baseline; packaged suite unchanged | Do nothing |
| Byte-equivalent to the recorded baseline; packaged suite changed | Atomically fast-forward the complete active suite and record the new baseline |
| Added, removed, or modified relative to the baseline | Preserve the complete active suite and stage the complete packaged candidate separately |
| Legacy workspace without trustworthy baseline evidence | Preserve the active suite and stage the candidate; never infer that it is safe to overwrite |
| Active suite made byte-equivalent to the candidate by the user | Recognize deliberate adoption and record that official baseline |
| Explicit external template root | Treat as user-owned and never overwrite automatically |

A server release that does not change the packaged suite causes no template copy or resolution work. A customized user only resolves a candidate when choosing to adopt upstream template changes.

#### Boundary and consumer blast radius

| Boundary | F-10 impact |
|---|---|
| Release build | Produces one coherent suite candidate plus deterministic suite identity/content evidence |
| Workspace initialization | Installs the candidate into the default active root and records the baseline |
| Workspace renewal | Replaces only an unchanged official baseline, otherwise stages without mutating active content |
| Template settings | Custom or external roots remain user-owned; only the configured active root is authoritative at runtime |
| Startup catalog | Validates the selected active suite and its supported contract format; it does not combine active and staged content |
| Upgrade result DTO/presentation | Reports active, baseline, and candidate identity plus bounded added/removed/modified path evidence and an actionable candidate location |
| State and recovery | Installation-baseline metadata is distinct from usage provenance; existing workspace backup remains emergency recovery rather than the normal customization workflow |
| Tests | Protect clean install, unchanged fast-forward, customized preservation, legacy preservation, external-root safety, and no mixed-version writes |
| Documentation | Explains the active/candidate distinction and manual adoption without presenting the staged copy as a second authority |

#### Historical Preservation Rationale

- Preserve direct user development and extension within the active template root.
- Preserve automatic upgrades for workspaces that still use the unchanged official baseline.
- Preserve a complete inspectable packaged candidate for customized workspaces.
- Do not overwrite, partially merge, or semantically reinterpret user-modified suites.
- Do not require recovery from backup after ordinary server upgrades.
- Do not build a package manager, overlay-precedence system, or automatic semantic merge engine.
- A renewal operation never creates a config/template combination that was absent from both the active suite and packaged candidate.

#### Reconciliation option analysis

| Option | Cost, risk, consumer impact, and migration consequence |
|---|---|
| Overwrite the complete active suite on every package upgrade | Always installs a coherent official suite, but destroys supported workspace customization |
| Preserve the complete existing suite indefinitely | Protects customization and coherence, but prevents automatic adoption of safe official updates |
| Distinguish an unchanged official installation from a customized/legacy root and offer the complete candidate separately when replacement is unsafe | Preserves both coherent fast-forward and user ownership; requires Design-owned baseline evidence, comparison, staging, and adoption behavior |
| Compose packaged and workspace files through overlays or automatic merge | Can reduce duplicated files, but introduces precedence, semantic merge, partial-version, and recovery complexity |

Research selects the observable renewal outcomes: no mixed suite, safe complete fast-forward only when official ownership is proven, complete preservation otherwise, and an inspectable non-authoritative candidate. Managed-baseline/candidate mechanics remain a Design hypothesis rather than a prescribed metadata format or staging algorithm.

#### Historical Decision Rationale (2026-08-23)

- Use a managed-baseline plus staged-candidate model with one active runtime template root.
- Fast-forward the active suite only when deterministic content comparison proves it is byte-equivalent to the recorded official baseline.
- If any file was added, removed, or modified, preserve the active suite completely and stage the new packaged suite outside the active root.
- Keep staged candidates outside documentation paths and make them non-authoritative by construction.
- Record sufficient per-file content evidence to identify local-only, upstream-only, and overlapping changed paths without attempting automatic merge or semantic compatibility decisions.
- Treat missing legacy baseline evidence and externally configured template roots conservatively as user-owned.
- Recognize exact adoption of the staged official candidate without requiring manual baseline editing.
- Separate suite-version changes from server-version changes so unrelated minor releases do not touch templates.
- Rely on startup catalog validation for active-suite integrity and supported contract-format compatibility.
- Reject file-by-file path heuristics, implicit overlays, package-manager behavior, and a compatibility bridge that preserves mixed versions.

#### Design hand-off

Design must choose the managed baseline metadata format and location, deterministic directory-digest algorithm, non-document staging location, atomic replace/stage procedure, legacy adoption flow, and bounded upgrade reporting. It must define the relationship between suite identity and the supported contract-format version without using template_registry.json as installation authority. It must preserve the single configured runtime root and may not load staged content automatically.

### F-11 — metadata and version identity omit semantic contributors

Tier-three pattern files use a metadata representation that is not parsed by the current analyzer. Imported macros are absent from the version hash, and the incomplete inheritance chain further narrows provenance.

A rendered artifact can therefore change because of a macro or inherited pattern while its recorded contract identity remains stable. The configured context contract can also change without affecting the current hash. Conversely, the hash is presented as version provenance even though it is derived largely from manually maintained version labels rather than the source content it claims to identify.

#### Current graph and identity defects

For a PR artifact, the effective sources include config/pr.yaml, the concrete PR template, its transitive inheritance chain, and the imported related-document macro. The current implementation:

- discovers only extends edges through a whitespace-sensitive regex and can miss the suite's trimmed Jinja syntax;
- excludes import, from-import, and include contributors;
- parses only one embedded TEMPLATE_METADATA dialect while tier-three patterns use another;
- substitutes fallback versions when metadata is missing or unreadable;
- hashes names and declared versions rather than actual contributor content;
- excludes the resolved caller contract;
- persists usage-driven partial tier information in template_registry.json.

Two different source graphs can therefore produce the same recorded hash. The registry cannot repair this because it stores neither the historical source files nor a complete content-addressed graph.

#### Provenance is not artifact lifecycle

A graph fingerprint describes the scaffold recipe used at creation. It is not a content hash and does not prove that the current artifact still equals the original rendering. Once an artifact is adopted and edited for production use, its content owns its lifecycle; template changes must not imply automatic regeneration or update.

If a fresh template result is desired later, the safe workflow is to scaffold a new candidate beside the existing production artifact and compare or merge them explicitly with a human, LLM, or text editor. The existing artifact is the comparison baseline. No historical template registry or automatic template-driven update mechanism is required.

A fingerprint is one-way and cannot reconstruct its input graph. The artifact type and suite identity can select a currently available catalog graph, whose fingerprint can be recomputed:

- a match proves that the available contract and contributors equal the scaffold source identity;
- a mismatch proves only that the available graph differs;
- an unavailable matching suite snapshot makes historical reconstruction impossible.

Exact historical reconstruction requires the original suite snapshot in an active root, staged candidate, release, Git history, or explicit backup. Storing partial registry metadata does not provide that snapshot.

#### Boundary and consumer blast radius

| Boundary | F-11 impact |
|---|---|
| Startup catalog | Owns the current artifact type to resolved contract/graph/fingerprint mapping |
| Template graph analysis | Reuses the complete static dependency graph approved under F-05 |
| Artifact contract | Contributes the resolved caller schema to source identity |
| Suite identity | Reuses F-10 suite identity so a graph fingerprint has a source namespace |
| Generated metadata | Describes initial scaffold source, not current content integrity or an update obligation |
| scaffold_schema | Can expose current suite identity, graph fingerprint, and contributor paths beside the resolved contract |
| template_registry.json | Has no demonstrated production consumer or complete historical evidence and is YAGNI |
| ArtifactManager/bootstrap/upgrade | Remove registry persistence, lookup, migration, injection, and dynamic-state preservation |
| Tests | Protect deterministic current-graph fingerprinting and observable metadata; remove tests whose only value is historical registry mechanics |
| Documentation | Explains source identity, match/mismatch limits, and side-by-side regeneration without claiming historical reconstruction |

#### Historical Preservation Rationale

- Preserve a compact, deterministic indication of the source graph used for initial scaffolding.
- Preserve the ability to resolve and inspect contributors when the matching suite snapshot is available.
- Preserve normal post-scaffold editing without marking the artifact invalid or stale.
- Do not present source provenance as artifact content integrity.
- Do not use newer templates to mutate or automatically update adopted artifacts.
- Do not persist partial historical graph logs without a concrete consumer.
- Do not add artifact content hashes, historical suite snapshots, or an automatic regeneration engine.
- A newly scaffolded candidate can be compared beside an existing production artifact without changing the existing file.

#### Historical Decision Rationale (2026-08-23)

- Remove template_registry.json and its persistence, lookup, migration, bootstrap injection, upgrade preservation, documentation, and registry-only tests.
- Replace the manually versioned partial chain with a deterministic graph fingerprint derived from the resolved caller contract plus every static Jinja contributor identified by the startup catalog.
- Reuse the F-10 suite identity; generated scaffold metadata identifies artifact type, source suite, and graph fingerprint with names that do not imply content integrity.
- Make current contributor paths and graph identity available through the resolved catalog boundary, with scaffold_schema as the existing caller-facing query seam unless Design identifies a narrower existing seam.
- Interpret comparison strictly: match, mismatch, or matching suite unavailable. Never claim that a hash alone can reconstruct historical sources.
- Treat adopted artifacts as independent production content. Refresh, when explicitly desired, means scaffold a separate candidate and compare manually or with an LLM.
- Do not retain a historical provenance store, content hash, automatic updater, or compatibility bridge for the registry.

#### Design hand-off

Design must define canonical graph-fingerprint input and serialization, compact metadata field names and length, suite/graph identity exposure, registry-removal blast radius, and the side-by-side candidate safety contract. It must determine whether scaffold_schema can carry provenance metadata without confusing it with the JSON Schema payload. It may not reintroduce manual version labels as fingerprint authority or turn provenance into an artifact update mechanism.

### F-12 — the PR defects are suite-level contract symptoms

F-12 is a traceability synthesis rather than an independent defect class. The four issue examples map directly to established suite-wide boundaries:

| Original PR defect | Governing boundary | Recorded outcome summary |
|---|---|---|
| related_docs | F-06 / S-04 canonical links | Required label/target objects; concrete template owns complete inline or reference-style rendering |
| closes_issues | S-05 issue references | Positive integer issue numbers; renderer owns the # presentation prefix |
| tracking_state | F-07 / S-07 content ownership | Remove from PR body context because it has no rendered body consumer |
| checklist_items | F-01 / S-06 structured collections | Objects with required text and explicit checked boolean; no primitive compatibility form |

Fixing only pr.md.jinja2 would leave the same ambiguity in issue, research, reference, architecture, planning, generic_doc, and several source-code templates. No separate F-12 implementation strategy is required: its purpose is to prove that the original issue scope is closed through the broader approved boundaries and that local PR-only patches are insufficient.

### F-13 — Successful calls can produce repair-required content

F-13 is a cross-cutting acceptance finding, not a separate engine defect class. Its visible symptoms map to already identified boundaries:

| Symptom | Governing boundary |
|---|---|
| Literal None-like content | F-02 omission and null semantics |
| Blank sections or cells from structured input | F-01 complete structural schemas and F-03 unchanged caller validation |
| Character-by-character list rendering | F-01 collection item typing |
| Missing or ignored body content | F-07 content/envelope ownership |
| Broken links, duplicated issue prefixes, and ambiguous checklist data | F-06 and F-12 canonical representations |
| Objectively malformed rendered Markdown or source | F-08 output-profile validation or a concrete template defect |
| Machine-specific output | F-14 and F-15 portability boundaries |

A successful scaffold call has an objective meaning: the unchanged caller context satisfies the complete selected contract, rendering completes, the configured output-profile validation is executed and passes under the approved strictness policy, and persistence succeeds. Non-empty output and absence of a renderer exception remain insufficient.

The runtime does not promise subjective prose quality, naming taste, or semantic usefulness beyond declared schema and output-profile rules. Do not add a generic artifact-quality evaluator, mandatory example contexts, LLM review, or full-text snapshot assertions. A concrete artifact that is schema-valid and profile-valid but still poorly worded or formatted is a template-suite defect; correct its template or declarative contract and protect only durable observable behavior.

**Historical decision rationale (2026-08-23):** treat F-13 as an acceptance and traceability synthesis. Map every observed symptom to an owning contract, define success through contract validation, rendering, applicable output-profile validation, and persistence, and introduce no additional subjective validation layer.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### F-14 — Generic public types can resolve to project-specific content

The live worker and service artifacts import backend-specific modules and encode a particular worker lifecycle, translator, logging, and strategy-cache model. These templates originated legitimately as first-generation scaffolding for a specific source project, where the patterns were coherent and useful. Packaging later moved those workspace-owned assumptions into the official suite without changing their generic public identity or making their prerequisites discoverable.

The boundary must distinguish:

- portable package-contained artifact types with no hidden consumer-local dependencies;
- explicitly named architecture patterns with complete, discoverable prerequisites;
- workspace-local templates and overrides owned by their consuming environment.

The official generic worker and service types must become portable and minimal. Remove the hidden backend-specific imports, lifecycle, translator, logging, strategy-cache, and naming assumptions from those package contracts through a clean break. Do not compensate by turning the generic types into a universal architecture DSL.

The original opinionated templates may return when their source project is activated in its new form, but then as workspace-local templates maintained by that consumer. Do not add packaged branded variants speculatively. A named architecture-pattern type belongs in the official suite only when a concrete supported consumer justifies its identity, prerequisites, ownership, and versioning.

**Historical decision rationale (2026-08-23):** official generic artifact types are portable package contracts. Remove residual source-project behavior from worker, service, and any other affected generic type without a compatibility bridge. Preserve the ability for the source project or another consumer to own specialized workspace-local templates under the F-10 customization model. Add packaged opinionated variants only for an evidenced future consumer.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

#### Confirmed source-project ownership

**Owner attestation (human-confirmed 2026-08-24):** S1mpleTrader owns the workspace-local variants of the six patterns listed below. The observed adapter/service boilerplate around logging, LogEnricher, Translator, lifecycle, dependencies, and errors belongs to the same local specialization set. Those capabilities must be preserved and recomposed during the later S1mpleTrader migration, but they do not belong in the portable PGMCP suite. This attestation establishes ownership and migration intent; it does not substitute for revision-pinned evidence about the current contents of the external repository.

The six affected patterns are owned by [S1mpleTrader](https://github.com/MikeyVK/S1mpleTrader), whose workspace already contains its own active `.pgmcp/templates` copies:

- `tier3_pattern_python_di.jinja2`
- `tier3_pattern_python_error.jinja2`
- `tier3_pattern_python_lifecycle.jinja2`
- `tier3_pattern_python_log_enricher.jinja2`
- `tier3_pattern_python_translator.jinja2`
- `tier3_pattern_python_typed_id.jinja2`

Historical S1mpleTraderV2 evidence confirms that LogEnricher and Translator were concrete service infrastructure. Current S1mpleTrader evidence shows that lifecycle, dependency requirements, and WorkerInitializationError belong to its worker protocol, while typed-ID generators are consumed across execution, state, and strategy DTOs. The error pattern is therefore worker-initialization behavior, not an error-DTO pattern; typed_id is a DTO/event-traceability pattern.

The official pgmcp suite must remove all six imports and files. Their optimized successors belong only in S1mpleTrader's complete active template root. That workspace already owns copies and will migrate them in a separate repository-local issue only after adopting the new pgmcp server and packaged template contract. Issue 460 performs no cross-repository edits, carries no duplicate migration assets, and is not blocked by that later consumer work. Activation of the upgraded server in S1mpleTrader remains blocked until its preserved local suite satisfies the new extension contract.

### F-14A — Agent hints are obsolete duplicate guidance

Agent hints predate declarative artifact schemas, `scaffold_schema`, and schema-field descriptions. At that time, Jinja introspection was the only way to give an agent usage guidance. That historical need no longer exists: schema descriptions explain caller-owned artifact content, while `contracts.yaml` remains authoritative for workflow behavior.

The shared `tier3_pattern_markdown_agent_hints.jinja2` macro is imported by research, design, and planning but never invoked. All 22 concrete templates also carry plural `agent_hints` metadata inside Jinja comments; these blocks are not rendered, are not part of the public scaffold contract, and include stale phase order, TDD, status, and approval assumptions. Retaining them creates hidden guidance debt without observable product value.

**Historical decision rationale (2026-08-23):** remove the shared pattern, its unused imports, and all concrete commented `agent_hints` blocks. The later engine/consumer audit must confirm and remove any dormant hint-extraction path that has no retained public consumer; exact code edits remain a Design and Planning concern. No compatibility bridge is required because no generated artifact or supported caller contract consumes the hints.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### F-14B — Unreachable test-pattern placeholders

The `tier3_pattern_python_assertions.jinja2` file intentionally provides no macros or output, while `tier3_pattern_python_test_fixtures.jinja2` exposes an unused decorator macro whose name argument is ignored and whose scope, autouse, and params options cannot be combined. Neither file is reachable from the unit-test or integration-test artifact graphs, and their public contracts expose no corresponding generic fixture model.

**Historical decision rationale (2026-08-23):** remove both placeholders without a compatibility bridge. Assertions remain test-body behavior. Any future reusable fixture scaffolding must be introduced through an explicit structured unit/integration-test contract, a reachable renderer, and durable behavior tests rather than by reviving the orphan macro.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### F-15 — Provenance presentation embeds the caller’s host path

Every successful probe starts with the absolute output path, including drive letter and workspace layout. This was a deliberate first-generation development aid: in a traditional IDE with many open files and previews, the first line made the current file location immediately visible. It was useful transient feedback for that source-project workflow, but tier-zero inheritance turned it into persistent production content for every artifact.

The persistence target and artifact content have different ownership:

- output_path remains a validated scaffold-tool envelope value used to resolve the write target and reported through result information;
- suite/type/graph identity can describe the initial scaffold source under F-11;
- the target path does not belong in generic rendered content.

Absolute paths make identical inputs differ across machines, disclose local directory structure, and become stale when files move. Workspace-relative paths avoid host disclosure but retain the stale-content and redundant-diff problem. Remove both forms from the generic tier-zero artifact body.

A concrete artifact may render a path only when that path has domain meaning and is declared explicitly by its own schema and template. It must not receive the generic persistence target implicitly.

**Historical decision rationale (2026-08-23):** omit filesystem paths from generic artifact bodies. Retain output_path for target resolution and result evidence only; retain source provenance independently through the F-11 suite/type/graph identity. No compatibility bridge is required for the development-only header convention.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### F-16 — scaffold_schema drops artifact-level purpose

All 22 artifact configurations already declare one concise root `description`, but live `scaffold_schema(artifact_type='architecture')` evidence returns only the generated model title and property schemas. The suite-owned description `System architecture documentation` is absent. Field descriptions explain valid parts; they do not tell a human or LLM the artifact's overall purpose, boundary, or intended use.

The public introspection response must expose a short, stable, workflow-neutral artifact purpose separately from property descriptions. For phase artifacts it may also carry the approved reference to active phase instructions for workflow-specific completeness, but it must not copy those instructions. The purpose remains useful when scaffolding outside an active workflow.

#### Reconciliation option analysis

| Option | Cost, risk, consumer impact, and migration consequence |
|---|---|
| Preserve the existing root description through the selected artifact's current introspection response | Reuses suite-owned data and avoids a second inventory; requires an additive response/schema carrier but no new selection workflow |
| Keep purpose only in active documentation and instructions | Lowest runtime cost, but preserves the drift and split-authority risk established by F-09 |
| Introduce a richer runtime catalog or discovery capability | Improves pre-selection guidance, but adds public feature scope beyond restoring existing introspection data and is separated as deferred F-18 |

The canonical Research register selects the first behavioral boundary. Exact response placement remains a Design comparison, and the third option is not smuggled into F-16.

**Historical decision rationale (2026-08-24):** preserve the existing suite-owned root description as caller-visible artifact guidance through `scaffold_schema`. Keep the surface YAGNI-bounded: issue 460 requires the concise purpose and the already-required context contract, not an expanding catalog of speculative metadata. Exact JSON Schema placement, response DTO representation, and phase-authority reference belong to Design.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### F-17 — language-specific contracts have generic identities

Eleven public IDs — `adapter`, `dto`, `generic`, `integration_test`, `interface`, `resource`, `schema`, `service`, `tool`, `unit_test`, and `worker` — resolve exclusively to Python templates. Several are more specific still: the interface is a `typing.Protocol`, DTO and schema contracts are Pydantic-based, and tool/resource templates implement MCP concepts in Python. Only `typescript_dto` currently makes its language explicit.

Language is not a presentation option for these contracts. A Python Protocol, Rust trait, and TypeScript interface require materially different fields, validation, rendering, and output profiles. A shared generic ID plus caller-supplied `language` would create conditional schemas, irrelevant optional fields, and data-driven template dispatch, defeating one-ID/one-contract introspection.

#### Reconciliation option analysis

| Option | Cost, risk, consumer impact, and migration consequence |
|---|---|
| Qualify all language/framework-determined IDs through one clean break | Produces one unambiguous namespace and finite contracts; requires coordinated migration of eleven IDs across configs, tests, docs, agents, and supported consumers |
| Preserve generic IDs and add a caller-supplied language selector | Reduces immediate renaming but creates conditional schemas, irrelevant fields, data-driven renderer dispatch, and permanent ambiguity in `scaffold_schema` |
| Preserve current Python IDs and qualify only future languages | Minimizes current migration but makes Python an implicit exception, complicates discovery, and creates a lasting asymmetric compatibility surface or aliases |

The canonical Research register selects the clean-break identity boundary. Exact qualified names and naming convention remain Design-owned.

**Historical decision rationale (2026-08-24):** when language or framework determines context semantics, it forms part of the public artifact identity rather than caller context. Apply a clean break without aliases to the eleven implicit-Python IDs; exact language/technology-qualified names and naming convention belong to Design. Update configs, active docs/instructions, tests/fixtures, and current PGMCP consumers in issue 460. Other owned workspaces migrate manually; S1mpleTrader combines the identity migration with its deferred local specialization work.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### F-18 — artifact selection lacks purpose-aware runtime discovery

Both scaffolding tools populate the `artifact_type` enum dynamically from the active validated registry at server startup. This exposes which IDs exist, but not why a caller should select one. Workflow phase instructions name their fixed document artifacts, while free code/document selection still depends on static AGENTS/examples, reference tables, or inference from ambiguous IDs. `scaffold_schema` is useful only after an ID has already been selected.

#### Reconciliation option analysis

The [central deferred-work notice](deferred-work.md#purpose-aware-runtime-artifact-discovery) compares a new discovery tool, extension of an existing introspection surface, and improved existing/static discovery with their cost, risk, consumer, and migration consequences. Canonical Research classifies F-18 as a feature request and defers all three; the historical single-tool proposal below is not binding.

**Historical decision rationale (2026-08-24):** add one harness-agnostic MCP discovery tool backed by the same restart-stable active registry. Its caller-facing result is intentionally minimal: artifact `type_id` and the concise suite-owned purpose from F-16. It introduces no separately maintained inventory. A caller discovers type and purpose, selects one, calls `scaffold_schema` for the exact context contract, then calls `scaffold_artifact`.

Harness-specific skills or commands may describe this reusable sequence, but remain thin consumers of the MCP tool and contain no artifact inventory. Fixed workflow instructions may continue naming known phase artifacts directly. Exact tool name, input/output DTO, cache/presentation behavior, and optional derived skill updates belong to Design; speculative catalog metadata remains out of scope.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

## Per-Artifact Semantic Audit

| Artifact | What scaffold_schema lets the caller express | Resolved renderer expectation or observation | Assessment |
|---|---|---|---|
| adapter | methods as strings plus module/class metadata | Structured method objects with names, parameters, returns, documentation, and bodies | Contract mismatch; rich valid input can fail |
| architecture | concepts, decisions, and constraints as primitive or opaque collections | Structured concepts, optional diagrams/subsections, structured decisions; constraints is unused | Nested contract missing; exposed intent lost |
| commit | type, message, optional scope/body/breaking change/refs | Primitive values align with renderer | Structurally aligned; semantic constraints remain descriptive only |
| design | opaque options and decisions collections | Options require name, description, pros, and cons; decisions require decision and rationale | Nested contract undiscoverable |
| dto | public contract follows configured DTO entry | Runtime selects a different DTO template with different field semantics | Public/runtime split; minimal valid input can yield invalid Python |
| generic | methods as strings | Structured method objects | Contract mismatch; rich valid input can fail |
| generic_doc | faq and custom sections as strings | FAQ objects and section objects with multiple nested content forms | Contract mismatch; minimal path is usable, extensions are not discoverable |
| integration_test | test_methods as strings | Structured test case objects | Contract mismatch; rich valid input can fail |
| interface | methods as strings | Structured method signature objects | Contract mismatch; rich valid input can fail |
| issue | title/body metadata, issue references, related docs, labels, milestone, tracking data | External title is not in body; related links inherit ambiguity; some external-envelope roles are implicit | Mostly renderable, but representation and field-role semantics need clarification |
| planning | cycles and risks as opaque objects without discoverable members | Structured cycles with goals, tests, criteria, dependencies; structured risks | Callers cannot construct complete content from introspection |
| pr | string issue references, string checklist items, related docs, tracking state | Adds issue prefix, optionally reads checklist object members, emits incomplete related links, ignores tracking_state | Confirmed issue-460 failures |
| reference | opaque API entries; usage_examples described as strings; source/test values | Structured API/method objects and structured examples; emits link labels without targets; hidden purpose use | Multiple contract and completeness defects |
| research | core prose and list fields are largely primitive and aligned | Related-document representation remains ambiguous; legacy fallback is hidden/dead | Core aligned; link and legacy semantics unresolved |
| resource | methods as strings | Structured method objects | Contract mismatch; rich valid input can fail |
| schema | fields as strings | Structured field definitions | Contract mismatch; rich valid input can render invalid Python |
| service | parameters as strings | Structured parameters; additional service-type behavior is hidden | Contract mismatch; rich valid input can render invalid Python |
| tool | primitive tool metadata, parameters, behavior | Renderer largely consumes the exposed shape | Structurally aligned; semantic value constraints are prose-only |
| typescript_dto | string fields and core metadata | String fields align; inherited optional metadata is hidden and formatting is compressed | Core shape aligned; graph completeness and output readability remain |
| unit_test | test_methods as strings; optional imported classes | Structured test methods; optional collection can become non-iterable after normalization | Contract mismatch plus optionality failure |
| validation_report | core report fields and optional scope | Core shape mostly aligns; null-equivalent scope can defeat fallback text | Mostly aligned; optional semantics need normalization |
| worker | primitive worker metadata and configuration | Renderer largely consumes the exposed shape | Structurally aligned; semantic constraints remain descriptive only |

## Human and LLM Interpretation Risks

### Ambiguous strings

A JSON Schema type of string answers how data is encoded, not what it means. The following values remain ambiguous without machine-readable semantics:

- an issue number with or without a prefix;
- a documentation path, URL, Markdown link, or reference identifier;
- a checklist label versus an item carrying checked state;
- a Python parameter declaration versus a parameter name;
- a field declaration versus a field name;
- a method name versus an entire method object encoded as text.

Descriptions can help a human but do not provide the nested structure required for reliable LLM generation. Where multiple attributes affect output, the introspection result needs actual object properties.

### Opaque objects

An array whose item schema is an unconstrained object is not first-time-right introspection. It tells a caller that an object exists but not which members are required, optional, nullable, repeated, or mutually exclusive.

### Descriptive constraints without structural enforcement

Several schemas describe enums, identifier formats, or allowed categories only in prose. A human may follow the prose; an LLM may vary capitalization, punctuation, or vocabulary. If a value set changes rendering behavior, scaffold_schema should expose the enum or pattern structurally.

### Silent success

Blank cells, omitted sections, discarded unknown keys, and unresolved Markdown links can all be produced without a rendering exception. For human and LLM use, silent semantic loss is a contract failure even when the tool call reports success.

## Strategy Options and Historical Decision Context

The option analysis below preserves historical rationale only. Current approval status and binding decisions live exclusively in the [Research decision register](research.md#approved-strategy-and-decision-status). This section has no approval authority.

### S-01 — Source of the public introspection contract

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Resolve portable contract metadata from the complete template graph and return it through scaffold_schema | Keeps scaffold_schema authoritative; supports inheritance/import composition; suite remains portable | Requires one merge model for requiredness, nullability, nested objects, and overrides |
| B. Keep one explicit complete contract beside each public resolved artifact and have scaffold_schema return it | Simple caller model; avoids runtime inference ambiguity | Can duplicate shared tier semantics unless composition is disciplined |
| C. Infer fields directly from Jinja usage | Reduces declared duplication | Jinja access does not reliably express semantic types, alternatives, or requiredness; inference can be incomplete |
| D. Preserve the current configured-entry lookup | Minimal change | Does not describe the resolved renderer and cannot meet first-time-right goals |

**Historical decision rationale (2026-08-23):** use a disciplined A/B boundary. The portable template suite owns complete standard JSON Schema contracts and any internal composition; scaffold_schema remains the only caller-facing introspection API and returns the fully resolved contract. Pgmcp validates and transports the resolved contract generically rather than owning artifact-specific context models. Exact authoring and graph-resolution mechanics remain a Design concern constrained by F-01 and F-05.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-02 — Nested collection representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Expose structured objects matching renderer concepts | Preserves expressive templates and makes nested intent discoverable | Clean-break schema changes for callers using primitive lists |
| B. Simplify renderers to consume strings only | Very easy caller surface | Loses checked state, descriptions, signatures, pros/cons, code sections, and other semantics |
| C. Temporarily accept a oneOf primitive/object bridge | Eases migration | Prolongs ambiguity and increases renderer branches; must have a removal boundary |

**Historical decision rationale (2026-08-23):** choose A as a clean break for every affected artifact family. The agent is the only relevant runtime consumer and re-discovers the contract through scaffold_schema before use; the existing primitive and opaque forms are not working supported behavior. Do not introduce a primitive/object union or migration bridge.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-03 — Optional, omitted, empty, and null values

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Optional means omitted or a typed value; null is rejected unless explicitly meaningful | Clear deterministic contract | Existing callers sending null may break |
| B. Normalize null, omission, and empty collection before rendering | Tolerant caller experience | Can erase intentional distinctions |
| C. Permit explicit nullable fields and make every template null-safe | Maximum expressiveness | Larger public surface and more semantic cases |

**Historical decision rationale (2026-08-23):** choose A. Optional permits omission but not null; present values retain their declared type and empty-value semantics. Null is admitted only for an explicit domain meaning. Omitted values remain omitted through validation and rendering, and declared defaults must have one deterministic effect.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-04 — Link representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Raw target strings; templates emit self-contained inline links | Simple for callers and portable across tiers | Labels must be derived or supplied separately |
| B. Structured objects with label and target | Fully explicit and extensible | More verbose for common cases |
| C. Caller-supplied Markdown passed through unchanged | Flexible | Hard to validate, unsafe to rewrap, and inconsistent across output formats |

**Historical decision rationale (2026-08-23):** use one structured object with required label and target. Concrete artifacts choose either inline or reference-style rendering; every reference use and definition must resolve within the same artifact graph. Caller-supplied Markdown and implicit string forms are rejected.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-05 — Issue-reference representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Positive integer issue numbers; renderer owns the prefix | Most unambiguous | Schema-breaking for prefixed strings |
| B. Digit strings without a prefix; renderer owns the prefix | JSON-friendly across systems | Still needs a pattern and numeric semantics |
| C. Canonical prefixed references such as #460; renderer passes through | Directly reflects Markdown | Ties data to presentation syntax |

**Historical decision rationale (2026-08-23):** choose A. Expose positive integer issue numbers and let the concrete renderer own the # prefix or other presentation syntax. Reject prefixed strings and do not add a compatibility union.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-06 — Checklist representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Objects with text and checked | Preserves state and intent | Breaks primitive-list callers |
| B. Strings only, always initially unchecked | Minimal schema | Cannot represent state |
| C. Temporary union of string and object | Migration path | Ambiguous long-term contract |

**Historical decision rationale (2026-08-23):** choose A as a clean break. Each checklist item has required non-empty text and an explicit checked boolean. Reject primitive strings and do not add a compatibility union.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-07 — Exposed but unused and hidden fields

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Render every public content field and expose every renderer input | Symmetric and easy to reason about | May force output additions that are not desired |
| B. Classify fields as content, external envelope, routing, or internal metadata in scaffold_schema | Preserves valid non-rendering inputs such as external titles | Requires machine-readable role metadata |
| C. Remove all non-rendered values from artifact context | Smallest render contract | May push necessary API envelope data into a separate call surface |

**Historical decision rationale (2026-08-23):** combine A and C at the correct boundary. scaffold_schema exposes only rendered caller content; every such field has a visible effect and every caller-supplied render variable is exposed. Scaffold-envelope and server values are sourced separately, downstream tool-envelope values stay in their own tool contracts, hidden routing is removed, and values without a consumer are deleted.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-08 — DTO variant and other runtime overrides

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Register the actual runtime template as the public artifact | One schema, renderer, version, and provenance | Clean break from legacy DTO behavior |
| B. Expose separate versioned artifact types | Explicit compatibility | Expands the public registry and migration burden |
| C. Keep conditional file-existence override | Minimal immediate change | Permanently violates introspection and provenance integrity |

**Historical decision rationale (2026-08-23):** choose A with the richer structured DTO contract. Keep one public DTO artifact, select its renderer declaratively, and remove the implicit _v2 override without a compatibility bridge. Do not add a separately versioned DTO artifact without a concrete supported consumer.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-09 — Graph metadata and provenance

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Resolve inheritance and imports with one portable parser and hash every semantic contributor | Accurate contract identity | Requires dependency-graph and cycle handling |
| B. Declare dependencies explicitly in suite metadata | Deterministic and parser-independent | Manual dependency declarations can drift |
| C. Keep inheritance-only best-effort analysis | Low effort | Cannot identify the actual rendered contract |

**Historical decision rationale (2026-08-23):** choose A. Use parser-supported Jinja semantics rather than regular-expression heuristics to discover every static semantic contributor. Use explicit metadata only for dependencies that syntax cannot reveal, and reject missing, dynamic-unresolvable, or cyclic graph edges fail-fast. Design owns the exact parser API, graph model, traversal, and identity serialization.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-10 — Distribution and local customization

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Replace the complete target suite on every server upgrade | Very simple renewal | Repeatedly overwrites user extensions and makes backup recovery routine |
| B. Compare the active suite with its recorded official baseline; fast-forward only unchanged targets and otherwise stage a complete candidate | One active authority, safe automatic updates, direct customization, and no partial merges | Customized users adopt upstream suite changes manually |
| C. Compose official and user packages or overlays at runtime | Automatic base updates alongside custom content | Requires identity, precedence, dependency, compatibility, and conflict semantics |
| D. Preserve config paths while replacing template paths | Minimal current change | Creates invalid mixed-version installations |

**Historical decision rationale (2026-08-23):** choose B. Use deterministic installed-baseline evidence, one user-extensible active root, and a non-authoritative packaged candidate. Unchanged official targets fast-forward atomically; customized, legacy-unknown, and external targets remain untouched and receive targeted difference evidence. Do not introduce runtime overlays, automatic merging, or per-path renewal heuristics.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-11 — Human documentation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Generate every exact inventory and example from scaffold_schema | Prevents manual drift | Adds a documentation-generation subsystem without a demonstrated retained consumer |
| B. Hand-maintain exact field inventories and executable examples | Flexible prose | Recreates a parallel contract authority and immediate documentation debt |
| C. Treat documentation as authoritative over scaffold_schema | Familiar to humans | Breaks tool-driven LLM usage and first-time-right introspection |
| D. Remove duplicated exact facts; let live schema/catalog own them and keep prose semantic | One authority with minimal machinery | Readers use discovery tools for current exact fields and inventory |

**Historical decision rationale (2026-08-23):** choose D. Handwritten references explain meaning, boundaries, and discovery; scaffold_schema and the runtime catalog own exact contract and inventory facts. Generate a retained exact documentation view only if a concrete consumer later demonstrates its value.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-12 — Generic versus project-specific artifact types

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Keep generic names and remove undeclared project assumptions | Portable, predictable public surface | Project consumers must own richer local patterns |
| B. Rename and package project-specific variants with explicit prerequisites | Preserves opinionated patterns centrally | Expands the official registry and creates unsupported ownership/versioning obligations without an evidenced consumer |
| C. Let a consuming workspace own local templates or overrides | Restores opinionated patterns where their dependencies actually exist | The active suite can differ by workspace and must expose its resolved identity |
| D. Keep hidden hard-coded assumptions | No migration effort | Violates standalone reuse and first-time-right discoverability |

**Historical decision rationale (2026-08-23):** combine A and C. Make official generic artifact types portable through a clean break and let consuming workspaces own specialized variants under the F-10 active-suite model. Do not package option B until a concrete supported consumer demonstrates its need and ownership.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-13 — Output provenance path semantics

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Omit filesystem paths from generic artifact bodies; retain target evidence outside the content | Reproducible and portable content | Removes a development convenience already available from the IDE, filesystem, and tool result |
| B. Emit a workspace-relative path | Repository context without host disclosure | Still redundant, becomes stale after moves, and creates content diffs |
| C. Keep absolute paths | Direct local traceability | Machine-specific output, noisy diffs, stale metadata, and local path disclosure |

**Historical decision rationale (2026-08-23):** choose A. Keep output_path in the scaffold envelope and result DTO, not the artifact body. A concrete artifact may expose a domain-significant path only through its own explicit content schema.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-14 — Rendered-output validation and strictness

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Require every catalogued template's language provider at startup | Strong global availability guarantee | Makes large portable suites impose unused toolchains and prevents lightweight workspaces |
| B. Resolve a declared capability only when its artifact is selected; strict by default | Strong pre-persistence guarantee without dormant dependencies; preserves suite breadth | First use of an unprovisioned strict artifact fails with actionable capability feedback |
| C. Run whichever extension validator happens to be registered and treat none as pass | Minimal configuration | Produces false passes, applies rules at the wrong output granularity, and hides unsupported languages |
| D. Require permanent example contexts and validate all rendered examples at startup | Exercises concrete outputs before use | Adds partial, duplicative content and cannot prove all schema-valid combinations |

**Historical decision rationale (2026-08-23):** choose B. Default strict_validation to true, declare output-validation capabilities or profiles in the portable artifact contract, resolve them through an extensible injected capability boundary only when the artifact is selected, and validate rendered content before persistence. Strictness controls enforcement only; it never changes passed, failed, or unavailable evidence. Startup remains responsible for language-agnostic template/schema/graph coherence, and permanent example contexts are not required. Design chooses the concrete provider registry or container mechanism.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-15 — Documentation contract duplication

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Correct and continue hand-maintaining exact counts, field tables, and full examples | Familiar static reference experience | Recreates immediate documentation debt after every contract change |
| B. Generate every inventory, field table, and example from the live catalog | Eliminates drift for derived content | Adds generation machinery and preserves views without proving their human value |
| C. Remove duplicate contract views by default; derive only proven valuable exact views | Small, durable documentation surface with one authority | Readers must use scaffold_schema for exact current fields |

**Historical decision rationale (2026-08-23):** choose C. Handwritten references explain meaning and the discovery workflow; scaffold_schema and the runtime catalog own exact contract and inventory facts. Remove static counts, minimum-field matrices, and unverified executable examples. Apply YAGNI to generation and do not replace the removed duplication with fragile documentation tests.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

### S-16 — Artifact source provenance

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Preserve manual version chains and template_registry.json history | Retains the current mechanism | Incomplete graph, discipline-dependent identity, and no historical source snapshots or production consumer |
| B. Keep deterministic current graph fingerprints and remove historical registry state | Minimal verifiable source identity; catalog can resolve available contributors | Historical graphs are unavailable when their suite snapshot no longer exists |
| C. Persist complete historical template and contract snapshots | Full reconstruction | Significant storage, lifecycle, and retention complexity without a demonstrated use case |
| D. Remove all scaffold source metadata | Smallest implementation | Loses low-cost current-suite traceability and graph comparison |

**Historical decision rationale (2026-08-23):** choose B. Fingerprint the resolved contract and complete static Jinja graph under the F-10 suite identity, expose current contributors through the catalog boundary, and remove template_registry.json. Metadata describes initial scaffold source only. Production artifacts remain independently editable; a later refresh is a separately scaffolded candidate compared with the existing artifact, never an automatic update.

**Canonical decision/status:** see the [Research decision register](research.md#approved-strategy-and-decision-status).

## Portable Maintenance Boundary

The template suite must remain independently maintainable and extensible in environments where pgmcp-server is only a consumer or execution tool.

That requirement rules out using server-owned tests as the canonical store of expected template content. It also rules out embedding per-template field knowledge in server code solely so the server can verify the suite.

A sound separation is:

### Template-suite responsibility

- public artifact contracts;
- nested value semantics;
- inheritance and import dependency metadata;
- content-oriented portable validation or auditing rules;
- optional examples, when present, that are derived from the same introspection surface;
- suite version and resolved graph identity.

### pgmcp-server responsibility

- expose the suite-owned contract through scaffold_schema;
- validate caller context against that returned contract;
- invoke the resolved renderer without silently changing the contract;
- preserve suite version coherence during packaging and workspace operations;
- report actionable contract or render failures.

### Human/LLM responsibility

- discover the contract through scaffold_schema before first use;
- provide only declared values with their declared semantics;
- make explicit product decisions where the schema offers genuine alternatives.

A portable auditor may inspect generic invariants such as undeclared variable use, unresolved dependency edges, unconsumed public fields, or missing link targets. Optional suite-owned examples may provide supplementary rendered-output evidence, but the runtime guarantee must not depend on permanent example content. The auditor must not become a pgmcp-server matrix that hardcodes each template’s expected prose or layout.


# Research: Issue 460 — Scaffolding Schema–Template Rendering Contract Audit

**Status:** REVIEW  
**Version:** 1.23  
**Last Updated:** 2026-08-23  
**Issue:** 460  
**Research Mode:** Standalone, non-destructive, pre-initialization research

## Purpose

Establish the substantive content contract required for first-time-right scaffolding by humans and LLM callers.

The public caller contract is the output of the scaffold_schema introspection tool. The underlying configuration files, Jinja templates, loader code, packaging code, and reference documentation are implementation and distribution evidence: they explain why the introspection contract and rendered result agree or disagree, but they are not substitutes for scaffold_schema in the caller workflow.

This research began without an implementation strategy. It identifies affected boundaries, consumers, options, and trade-offs and records each explicit human-approved boundary strategy before Design.

## Scope

### In scope

- Every artifact type currently exposed through scaffold_schema: 22 types.
- Every file in the active packaged template suite: 22 artifact configuration files and 57 Jinja files.
- Every configured or embedded example surface in the suite.
- The resolved template graph, including concrete templates, inherited tiers, imported macros, unreachable files, and runtime template selection.
- Runtime, setup, test, fixture/helper, agent-instruction, and active-documentation consumers that can be affected by the contract refactor.
- Whether scaffold_schema lets a human or LLM discover every value shape needed by the renderer.
- Whether schema-valid values render content that is syntactically usable, semantically complete, and unambiguous.
- Links, issue references, checklists, nested collections, optional values, hidden fields, and unused fields.
- Portability of the template suite as an independently maintained and extensible asset outside pgmcp-server installations.
- Workspace/runtime packaging and renewal behavior where it can split the introspection contract from the templates it describes.
- Reference documentation only as a secondary human guidance surface that must agree with scaffold_schema.

### Out of scope

- Production fixes.
- Workflow initialization or phase transitions for issue 460.
- Commits, branch changes, or changes to issue state.
- A server-owned matrix of template-specific expected outputs.
- Snapshot tests or prose-output assertions that duplicate template-suite content inside pgmcp.
- Detailed implementation design or planning, including concrete parser APIs, class topology, provider containers, staging paths, and digest serialization.
- Testability as the primary proof of correctness; behavioral test blast radius and durable regression obligations remain in scope.

## Problem Statement

Issue 460 starts from four confirmed pull-request scaffolding defects:

1. related_docs accepts values whose intended representation is unclear and renders reference-style links without definitions.
2. closes_issues accepts strings while the template unconditionally adds a number-sign prefix.
3. tracking_state is exposed but not rendered.
4. checklist_items is exposed as a list of strings while the template also treats each item as an object with checked state and description.

Those defects are instances of a broader contract failure. The caller asks scaffold_schema how to construct context, but multiple resolved templates require structures, variables, or semantics that scaffold_schema does not reveal. Conversely, some fields revealed by scaffold_schema are ignored by the active renderer. A schema-valid call can therefore fail at render time, produce invalid source code, produce incomplete Markdown, or silently discard caller intent.

First-time-right scaffolding is impossible when the introspection contract is less expressive than the renderer contract or when the same input has more than one plausible human interpretation.

## Research Questions

1. What does scaffold_schema expose for every public artifact type?
2. Can every template-consumed value be represented from that introspection alone?
3. Does every exposed value have one unambiguous meaning and a visible effect?
4. Do minimal and richly populated schema-valid contexts remain substantively correct after rendering?
5. Does the resolved graph include every inherited and imported contract contribution?
6. Can the template suite own and evolve its content contract independently from the pgmcp server?
7. Which compatibility and migration decisions require human approval before design?

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

- [Template Suite Work Catalog](template-suite-catalog.md) — complete inventory of all 22 public artifacts, all 79 suite files, example surfaces, runtime/setup consumers, and 103 candidate test/helper files.
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

### Representative live evidence

- [.pgmcp/temp/issue460/rich/pr/pr.md](../../../.pgmcp/temp/issue460/rich/pr/pr.md)
- [.pgmcp/temp/issue460/rich/reference/reference.md](../../../.pgmcp/temp/issue460/rich/reference/reference.md)
- [.pgmcp/temp/issue460/rich/architecture/architecture.md](../../../.pgmcp/temp/issue460/rich/architecture/architecture.md)
- [.pgmcp/temp/issue460/rich/planning/planning.md](../../../.pgmcp/temp/issue460/rich/planning/planning.md)
- [.pgmcp/temp/issue460/rich/validation_report/validation-report.md](../../../.pgmcp/temp/issue460/rich/validation_report/validation-report.md)
- [.pgmcp/temp/issue460/inferred/inferred-design/design.md](../../../.pgmcp/temp/issue460/inferred/inferred-design/design.md)
- [.pgmcp/temp/issue460/inferred/inferred-reference/reference.md](../../../.pgmcp/temp/issue460/inferred/inferred-reference/reference.md)
- [.pgmcp/temp/issue460/minimal/worker/live_worker.py](../../../.pgmcp/temp/issue460/minimal/worker/live_worker.py)
- [.pgmcp/temp/issue460/minimal/service/live_service.py](../../../.pgmcp/temp/issue460/minimal/service/live_service.py)

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

#### Preserved behavior and required outcome

- Preserve all public artifact type identifiers and the expressive content capabilities of their active templates.
- Preserve scaffold_schema as proactive introspection and scaffold_artifact as the validated rendering entry point.
- Preserve reference-free MCP client-facing schemas.
- Do not preserve unusable primitive or opaque collection shapes as compatibility behavior.
- A fresh caller using only scaffold_schema must be able to construct every supported nested value without template inspection or documentation-only knowledge.
- Every accepted nested value must reach the renderer without semantic reinterpretation or loss.

#### Approved Strategy

- Apply a clean break: structured collection items replace primitive or opaque declarations wherever the renderer consumes multiple item properties. No primitive/object compatibility bridge is required.
- The portable template suite owns complete standard JSON Schema context contracts. Pgmcp remains artifact-agnostic and must not encode field names or template concepts in Python.
- The same resolved schema governs caller introspection and runtime context validation.
- Internal schema composition may reuse exact definitions, but the authoring graph must be acyclic for the current scope and must fail fast on invalid or unresolved references.
- scaffold_schema and every MCP client-facing schema expose only a fully resolved, self-contained representation without $defs or $ref.
- Recursive context schemas are out of scope because no current template performs recursive rendering.

#### Design hand-off

Design must choose the JSON Schema draft, authoring layout, local versus suite-shared composition mechanism, standards-compliant validation/resolution implementation, and lifecycle of resolved schemas. It must also separate suite-owned context from server-owned scaffold metadata. These choices may not weaken the Approved Strategy or reintroduce artifact-specific context models in pgmcp.

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

#### Preserved behavior and required outcome

- Preserve intentional false, zero, empty-string, and empty-collection values.
- Preserve template-owned presentation fallbacks where omission is valid.
- Preserve explicit useful defaults, but require their effect to agree between introspection, validation, and rendering.
- Do not preserve automatic None injection as supported behavior.
- Every accepted context must retain the caller's semantic distinction through rendering.

#### Approved Strategy

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

#### Approved Strategy (2026-08-23)

- Preserve the two-stage validation model: the static tool envelope remains generic, and the resolved artifact schema validates artifact-specific context.
- Validate the original caller-owned context without pre-filtering or silent key removal.
- Closed schema objects reject undeclared properties with actionable path context. Deliberately open maps remain possible only when the suite-owned schema explicitly defines that openness.
- Keep validated tool-envelope values such as name and output_path, and server-owned provenance or timestamp values, outside caller-owned artifact context during artifact validation.
- Add those values only after artifact-context validation through an explicit render-context boundary.
- Do not introduce a compatibility bridge for silently ignored keys; silent acceptance was not a reliable contract.

#### Design hand-off

Design must define the typed boundary and deterministic merge rules between caller-owned artifact context, validated tool-envelope input, and server-owned render metadata. It must also specify collision handling and which values are visible to templates. The exact classes and pipeline arrangement belong to Design; template-specific field names must not leak into generic pgmcp code.

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

#### Approved Strategy (2026-08-23)

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

#### Approved Strategy (2026-08-23)

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

#### Approved Strategy (2026-08-23)

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

#### Approved boundary model (2026-08-23)

The artifact context exposed by scaffold_schema contains only caller-owned values intentionally rendered as artifact content. It is not a transport for a later tool's envelope.

- The scaffold tool envelope validates values such as name and output_path separately. A resolved renderer may receive them only after artifact-context validation where they have a legitimate render use.
- Server-owned artifact type, timestamps, version identity, and provenance are injected separately.
- Downstream GitHub title, labels, milestone, assignees, branch, base, draft, and similar operation inputs remain governed by their own tool schemas and do not travel through an issue or PR body context.
- If a concept genuinely belongs in the body, its concrete template defines a content field and renders an explicit section. It does not reuse an identically named downstream API field as implicit metadata.
- Template routing is declarative artifact configuration, not a hidden context key or Python dispatch table.
- Any caller-context property without a rendered effect is removed. Any renderer-required caller content is exposed in the suite-owned schema.

#### Approved field outcomes

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

#### Approved tracking-artifact behavior (2026-08-23)

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

#### Preserved behavior and required outcome

- Preserve a broad independently reusable template suite; unused template languages do not impose workspace dependencies.
- Preserve in-memory rendering followed by pre-persistence validation where a capability is declared.
- Preserve explicit opt-out behavior, but make it visible and intentional.
- Do not require permanent suite-owned example contexts solely to exercise validators.
- Do not infer validity from non-empty output, absence of a renderer exception, an empty validator set, or strictness itself.
- Do not treat rules from a different output profile as failures.
- A concrete requested artifact either runs its applicable validator and reports the real result or reports that the required capability is unavailable before filesystem mutation.

#### Approved Strategy (2026-08-23)

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

Design must define the declarative capability/profile shape, provider discovery and injection mechanism, result states for passed, failed, and unavailable validation, and the exact pre-persistence sequence. It must reuse strict_validation as enforcement policy rather than duplicate it, validate inconsistent configuration combinations at startup, and keep dormant-provider absence out of global startup failure. It must also audit current Markdown, Python, TypeScript, tracking, text, and document profiles so the default change does not apply irrelevant rules.

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

#### Preserved behavior and required outcome

- Preserve useful explanation of the scaffolding workflow, artifact purpose, architecture, validation behavior, and caller responsibilities.
- Preserve scaffold_schema-first instructions and actionable examples of that interaction pattern.
- Do not preserve manually maintained exact counts, complete field inventories, or minimum-context tables as a second contract.
- Do not correct examples against an intermediate schema that issue 460 is about to replace.
- Complete executable examples are retained only when they are derived from or generically checked against the live contract; otherwise use explicit pseudocode or remove them.
- Documentation and agent instructions must not require prose-snapshot or field-list tests to remain synchronized.
- A future artifact or field addition must not create immediate documentation debt solely because a hand-maintained duplicate exists.

#### Approved Strategy (2026-08-23)

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

#### Preserved behavior and required outcome

- Preserve direct user development and extension within the active template root.
- Preserve automatic upgrades for workspaces that still use the unchanged official baseline.
- Preserve a complete inspectable packaged candidate for customized workspaces.
- Do not overwrite, partially merge, or semantically reinterpret user-modified suites.
- Do not require recovery from backup after ordinary server upgrades.
- Do not build a package manager, overlay-precedence system, or automatic semantic merge engine.
- A renewal operation never creates a config/template combination that was absent from both the active suite and packaged candidate.

#### Approved Strategy (2026-08-23)

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

#### Preserved behavior and required outcome

- Preserve a compact, deterministic indication of the source graph used for initial scaffolding.
- Preserve the ability to resolve and inspect contributors when the matching suite snapshot is available.
- Preserve normal post-scaffold editing without marking the artifact invalid or stale.
- Do not present source provenance as artifact content integrity.
- Do not use newer templates to mutate or automatically update adopted artifacts.
- Do not persist partial historical graph logs without a concrete consumer.
- Do not add artifact content hashes, historical suite snapshots, or an automatic regeneration engine.
- A newly scaffolded candidate can be compared beside an existing production artifact without changing the existing file.

#### Approved Strategy (2026-08-23)

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

| Original PR defect | Governing boundary | Approved outcome |
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

**Approved Strategy (2026-08-23):** treat F-13 as an acceptance and traceability synthesis. Map every observed symptom to an owning contract, define success through contract validation, rendering, applicable output-profile validation, and persistence, and introduce no additional subjective validation layer.

**Status:** approved; no separate F-13 compatibility or migration strategy is required.

### F-14 — Generic public types can resolve to project-specific content

The live worker and service artifacts import backend-specific modules and encode a particular worker lifecycle, translator, logging, and strategy-cache model. These templates originated legitimately as first-generation scaffolding for a specific source project, where the patterns were coherent and useful. Packaging later moved those workspace-owned assumptions into the official suite without changing their generic public identity or making their prerequisites discoverable.

The boundary must distinguish:

- portable package-contained artifact types with no hidden consumer-local dependencies;
- explicitly named architecture patterns with complete, discoverable prerequisites;
- workspace-local templates and overrides owned by their consuming environment.

The official generic worker and service types must become portable and minimal. Remove the hidden backend-specific imports, lifecycle, translator, logging, strategy-cache, and naming assumptions from those package contracts through a clean break. Do not compensate by turning the generic types into a universal architecture DSL.

The original opinionated templates may return when their source project is activated in its new form, but then as workspace-local templates maintained by that consumer. Do not add packaged branded variants speculatively. A named architecture-pattern type belongs in the official suite only when a concrete supported consumer justifies its identity, prerequisites, ownership, and versioning.

**Approved Strategy (2026-08-23):** official generic artifact types are portable package contracts. Remove residual source-project behavior from worker, service, and any other affected generic type without a compatibility bridge. Preserve the ability for the source project or another consumer to own specialized workspace-local templates under the F-10 customization model. Add packaged opinionated variants only for an evidenced future consumer.

**Status:** approved for package portability and consumer-local specialization.

#### Confirmed source-project ownership

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

**Approved Strategy (2026-08-23):** remove the shared pattern, its unused imports, and all concrete commented `agent_hints` blocks. The later engine/consumer audit must confirm and remove any dormant hint-extraction path that has no retained public consumer; exact code edits remain a Design and Planning concern. No compatibility bridge is required because no generated artifact or supported caller contract consumes the hints.

**Status:** approved for suite-wide removal; engine blast radius remains scheduled for the engine audit.

### Deferred Work — Complete YAML artifact package subset

The unreachable `tier1_base_config.jinja2` and `tier2_base_yaml.jinja2` files are incomplete seeds, not supported behavior. They have no public artifact registration, concrete renderer, complete schema, output-profile contract, or behavioral consumer. Issue 460 removes them from the official suite instead of carrying an unreachable partial tier.

The first PGMCP issue after issue 460 merges should build a complete YAML configuration artifact subset on its own branch. That issue must treat the work as a real public/extensibility capability rather than restore the two files verbatim. Its research and design should cover:

- a public YAML/config artifact registration and complete portable context contract;
- tier-one config, tier-two YAML, and concrete renderer responsibilities;
- bounded acyclic structured entries and sections rather than an unrestricted recursive YAML DSL;
- strict-by-default YAML output-profile validation;
- startup discovery, complete graph identity, and `scaffold_schema` exposure without artifact-specific Python registration;
- minimal and property-complete rendering whose parsed YAML data proves semantic behavior without full-text snapshots;
- a temporary complete active-root fixture that proves a new artifact can be added through suite files alone;
- packaging, documentation, and extension-boundary evidence.

The current files remain recoverable through Git history and this durable specification; keeping dead package files is not required to preserve the idea.

**Deferred Strategy (human-approved 2026-08-23):** remove both incomplete files in issue 460. Hand the complete YAML artifact package subset to coordination as the explicitly recommended first follow-up PGMCP issue on its own branch.

### F-14B — Unreachable test-pattern placeholders

The `tier3_pattern_python_assertions.jinja2` file intentionally provides no macros or output, while `tier3_pattern_python_test_fixtures.jinja2` exposes an unused decorator macro whose name argument is ignored and whose scope, autouse, and params options cannot be combined. Neither file is reachable from the unit-test or integration-test artifact graphs, and their public contracts expose no corresponding generic fixture model.

**Approved Strategy (2026-08-23):** remove both placeholders without a compatibility bridge. Assertions remain test-body behavior. Any future reusable fixture scaffolding must be introduced through an explicit structured unit/integration-test contract, a reachable renderer, and durable behavior tests rather than by reviving the orphan macro.

**Status:** approved for removal.

### F-15 — Provenance presentation embeds the caller’s host path

Every successful probe starts with the absolute output path, including drive letter and workspace layout. This was a deliberate first-generation development aid: in a traditional IDE with many open files and previews, the first line made the current file location immediately visible. It was useful transient feedback for that source-project workflow, but tier-zero inheritance turned it into persistent production content for every artifact.

The persistence target and artifact content have different ownership:

- output_path remains a validated scaffold-tool envelope value used to resolve the write target and reported through result information;
- suite/type/graph identity can describe the initial scaffold source under F-11;
- the target path does not belong in generic rendered content.

Absolute paths make identical inputs differ across machines, disclose local directory structure, and become stale when files move. Workspace-relative paths avoid host disclosure but retain the stale-content and redundant-diff problem. Remove both forms from the generic tier-zero artifact body.

A concrete artifact may render a path only when that path has domain meaning and is declared explicitly by its own schema and template. It must not receive the generic persistence target implicitly.

**Approved Strategy (2026-08-23):** omit filesystem paths from generic artifact bodies. Retain output_path for target resolution and result evidence only; retain source provenance independently through the F-11 suite/type/graph identity. No compatibility bridge is required for the development-only header convention.

**Status:** approved for portable, reproducible artifact content.

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

## Approved Strategy Decisions

The following boundary decisions were approved interactively during Research and are binding input for Design. Design owns their concrete realization but may not silently change their compatibility, ownership, or portability strategy.

### S-01 — Source of the public introspection contract

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Resolve portable contract metadata from the complete template graph and return it through scaffold_schema | Keeps scaffold_schema authoritative; supports inheritance/import composition; suite remains portable | Requires one merge model for requiredness, nullability, nested objects, and overrides |
| B. Keep one explicit complete contract beside each public resolved artifact and have scaffold_schema return it | Simple caller model; avoids runtime inference ambiguity | Can duplicate shared tier semantics unless composition is disciplined |
| C. Infer fields directly from Jinja usage | Reduces declared duplication | Jinja access does not reliably express semantic types, alternatives, or requiredness; inference can be incomplete |
| D. Preserve the current configured-entry lookup | Minimal change | Does not describe the resolved renderer and cannot meet first-time-right goals |

**Approved Strategy (2026-08-23):** use a disciplined A/B boundary. The portable template suite owns complete standard JSON Schema contracts and any internal composition; scaffold_schema remains the only caller-facing introspection API and returns the fully resolved contract. Pgmcp validates and transports the resolved contract generically rather than owning artifact-specific context models. Exact authoring and graph-resolution mechanics remain a Design concern constrained by F-01 and F-05.

**Status:** approved for the F-01 public-contract boundary; Design owns the exact authoring and graph mechanics under the approved S-09 constraints.

### S-02 — Nested collection representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Expose structured objects matching renderer concepts | Preserves expressive templates and makes nested intent discoverable | Clean-break schema changes for callers using primitive lists |
| B. Simplify renderers to consume strings only | Very easy caller surface | Loses checked state, descriptions, signatures, pros/cons, code sections, and other semantics |
| C. Temporarily accept a oneOf primitive/object bridge | Eases migration | Prolongs ambiguity and increases renderer branches; must have a removal boundary |

**Approved Strategy (2026-08-23):** choose A as a clean break for every affected artifact family. The agent is the only relevant runtime consumer and re-discovers the contract through scaffold_schema before use; the existing primitive and opaque forms are not working supported behavior. Do not introduce a primitive/object union or migration bridge.

**Status:** approved.

### S-03 — Optional, omitted, empty, and null values

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Optional means omitted or a typed value; null is rejected unless explicitly meaningful | Clear deterministic contract | Existing callers sending null may break |
| B. Normalize null, omission, and empty collection before rendering | Tolerant caller experience | Can erase intentional distinctions |
| C. Permit explicit nullable fields and make every template null-safe | Maximum expressiveness | Larger public surface and more semantic cases |

**Approved Strategy (2026-08-23):** choose A. Optional permits omission but not null; present values retain their declared type and empty-value semantics. Null is admitted only for an explicit domain meaning. Omitted values remain omitted through validation and rendering, and declared defaults must have one deterministic effect.

**Status:** approved.

### S-04 — Link representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Raw target strings; templates emit self-contained inline links | Simple for callers and portable across tiers | Labels must be derived or supplied separately |
| B. Structured objects with label and target | Fully explicit and extensible | More verbose for common cases |
| C. Caller-supplied Markdown passed through unchanged | Flexible | Hard to validate, unsafe to rewrap, and inconsistent across output formats |

**Approved Strategy (2026-08-23):** use one structured object with required label and target. Concrete artifacts choose either inline or reference-style rendering; every reference use and definition must resolve within the same artifact graph. Caller-supplied Markdown and implicit string forms are rejected.

**Status:** approved.

### S-05 — Issue-reference representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Positive integer issue numbers; renderer owns the prefix | Most unambiguous | Schema-breaking for prefixed strings |
| B. Digit strings without a prefix; renderer owns the prefix | JSON-friendly across systems | Still needs a pattern and numeric semantics |
| C. Canonical prefixed references such as #460; renderer passes through | Directly reflects Markdown | Ties data to presentation syntax |

**Approved Strategy (2026-08-23):** choose A. Expose positive integer issue numbers and let the concrete renderer own the # prefix or other presentation syntax. Reject prefixed strings and do not add a compatibility union.

**Status:** approved for issue-reference representation.

### S-06 — Checklist representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Objects with text and checked | Preserves state and intent | Breaks primitive-list callers |
| B. Strings only, always initially unchecked | Minimal schema | Cannot represent state |
| C. Temporary union of string and object | Migration path | Ambiguous long-term contract |

**Approved Strategy (2026-08-23):** choose A as a clean break. Each checklist item has required non-empty text and an explicit checked boolean. Reject primitive strings and do not add a compatibility union.

**Status:** approved for checklist representation.

### S-07 — Exposed but unused and hidden fields

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Render every public content field and expose every renderer input | Symmetric and easy to reason about | May force output additions that are not desired |
| B. Classify fields as content, external envelope, routing, or internal metadata in scaffold_schema | Preserves valid non-rendering inputs such as external titles | Requires machine-readable role metadata |
| C. Remove all non-rendered values from artifact context | Smallest render contract | May push necessary API envelope data into a separate call surface |

**Approved Strategy (2026-08-23):** combine A and C at the correct boundary. scaffold_schema exposes only rendered caller content; every such field has a visible effect and every caller-supplied render variable is exposed. Scaffold-envelope and server values are sourced separately, downstream tool-envelope values stay in their own tool contracts, hidden routing is removed, and values without a consumer are deleted.

**Status:** approved, including the field outcomes recorded under F-07.

### S-08 — DTO variant and other runtime overrides

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Register the actual runtime template as the public artifact | One schema, renderer, version, and provenance | Clean break from legacy DTO behavior |
| B. Expose separate versioned artifact types | Explicit compatibility | Expands the public registry and migration burden |
| C. Keep conditional file-existence override | Minimal immediate change | Permanently violates introspection and provenance integrity |

**Approved Strategy (2026-08-23):** choose A with the richer structured DTO contract. Keep one public DTO artifact, select its renderer declaratively, and remove the implicit _v2 override without a compatibility bridge. Do not add a separately versioned DTO artifact without a concrete supported consumer.

**Status:** approved.

### S-09 — Graph metadata and provenance

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Resolve inheritance and imports with one portable parser and hash every semantic contributor | Accurate contract identity | Requires dependency-graph and cycle handling |
| B. Declare dependencies explicitly in suite metadata | Deterministic and parser-independent | Manual dependency declarations can drift |
| C. Keep inheritance-only best-effort analysis | Low effort | Cannot identify the actual rendered contract |

**Approved Strategy (2026-08-23):** choose A. Use parser-supported Jinja semantics rather than regular-expression heuristics to discover every static semantic contributor. Use explicit metadata only for dependencies that syntax cannot reveal, and reject missing, dynamic-unresolvable, or cyclic graph edges fail-fast. Design owns the exact parser API, graph model, traversal, and identity serialization.

**Status:** approved.

### S-10 — Distribution and local customization

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Replace the complete target suite on every server upgrade | Very simple renewal | Repeatedly overwrites user extensions and makes backup recovery routine |
| B. Compare the active suite with its recorded official baseline; fast-forward only unchanged targets and otherwise stage a complete candidate | One active authority, safe automatic updates, direct customization, and no partial merges | Customized users adopt upstream suite changes manually |
| C. Compose official and user packages or overlays at runtime | Automatic base updates alongside custom content | Requires identity, precedence, dependency, compatibility, and conflict semantics |
| D. Preserve config paths while replacing template paths | Minimal current change | Creates invalid mixed-version installations |

**Approved Strategy (2026-08-23):** choose B. Use deterministic installed-baseline evidence, one user-extensible active root, and a non-authoritative packaged candidate. Unchanged official targets fast-forward atomically; customized, legacy-unknown, and external targets remain untouched and receive targeted difference evidence. Do not introduce runtime overlays, automatic merging, or per-path renewal heuristics.

**Status:** approved for the F-10 distribution and customization boundary.

### S-11 — Human documentation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Generate every exact inventory and example from scaffold_schema | Prevents manual drift | Adds a documentation-generation subsystem without a demonstrated retained consumer |
| B. Hand-maintain exact field inventories and executable examples | Flexible prose | Recreates a parallel contract authority and immediate documentation debt |
| C. Treat documentation as authoritative over scaffold_schema | Familiar to humans | Breaks tool-driven LLM usage and first-time-right introspection |
| D. Remove duplicated exact facts; let live schema/catalog own them and keep prose semantic | One authority with minimal machinery | Readers use discovery tools for current exact fields and inventory |

**Approved Strategy (2026-08-23):** choose D. Handwritten references explain meaning, boundaries, and discovery; scaffold_schema and the runtime catalog own exact contract and inventory facts. Generate a retained exact documentation view only if a concrete consumer later demonstrates its value.

**Status:** approved through F-09 / S-15; no separate documentation generator or fragile synchronization tests are introduced.

### S-12 — Generic versus project-specific artifact types

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Keep generic names and remove undeclared project assumptions | Portable, predictable public surface | Project consumers must own richer local patterns |
| B. Rename and package project-specific variants with explicit prerequisites | Preserves opinionated patterns centrally | Expands the official registry and creates unsupported ownership/versioning obligations without an evidenced consumer |
| C. Let a consuming workspace own local templates or overrides | Restores opinionated patterns where their dependencies actually exist | The active suite can differ by workspace and must expose its resolved identity |
| D. Keep hidden hard-coded assumptions | No migration effort | Violates standalone reuse and first-time-right discoverability |

**Approved Strategy (2026-08-23):** combine A and C. Make official generic artifact types portable through a clean break and let consuming workspaces own specialized variants under the F-10 active-suite model. Do not package option B until a concrete supported consumer demonstrates its need and ownership.

**Status:** approved for worker, service, and every generic package type with consumer-local assumptions.

### S-13 — Output provenance path semantics

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Omit filesystem paths from generic artifact bodies; retain target evidence outside the content | Reproducible and portable content | Removes a development convenience already available from the IDE, filesystem, and tool result |
| B. Emit a workspace-relative path | Repository context without host disclosure | Still redundant, becomes stale after moves, and creates content diffs |
| C. Keep absolute paths | Direct local traceability | Machine-specific output, noisy diffs, stale metadata, and local path disclosure |

**Approved Strategy (2026-08-23):** choose A. Keep output_path in the scaffold envelope and result DTO, not the artifact body. A concrete artifact may expose a domain-significant path only through its own explicit content schema.

**Status:** approved; the old header is recognized as a useful development aid that does not belong in persistent generic output.

### S-14 — Rendered-output validation and strictness

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Require every catalogued template's language provider at startup | Strong global availability guarantee | Makes large portable suites impose unused toolchains and prevents lightweight workspaces |
| B. Resolve a declared capability only when its artifact is selected; strict by default | Strong pre-persistence guarantee without dormant dependencies; preserves suite breadth | First use of an unprovisioned strict artifact fails with actionable capability feedback |
| C. Run whichever extension validator happens to be registered and treat none as pass | Minimal configuration | Produces false passes, applies rules at the wrong output granularity, and hides unsupported languages |
| D. Require permanent example contexts and validate all rendered examples at startup | Exercises concrete outputs before use | Adds partial, duplicative content and cannot prove all schema-valid combinations |

**Approved Strategy (2026-08-23):** choose B. Default strict_validation to true, declare output-validation capabilities or profiles in the portable artifact contract, resolve them through an extensible injected capability boundary only when the artifact is selected, and validate rendered content before persistence. Strictness controls enforcement only; it never changes passed, failed, or unavailable evidence. Startup remains responsible for language-agnostic template/schema/graph coherence, and permanent example contexts are not required. Design chooses the concrete provider registry or container mechanism.

**Status:** approved for the F-08 rendered-output boundary.

### S-15 — Documentation contract duplication

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Correct and continue hand-maintaining exact counts, field tables, and full examples | Familiar static reference experience | Recreates immediate documentation debt after every contract change |
| B. Generate every inventory, field table, and example from the live catalog | Eliminates drift for derived content | Adds generation machinery and preserves views without proving their human value |
| C. Remove duplicate contract views by default; derive only proven valuable exact views | Small, durable documentation surface with one authority | Readers must use scaffold_schema for exact current fields |

**Approved Strategy (2026-08-23):** choose C. Handwritten references explain meaning and the discovery workflow; scaffold_schema and the runtime catalog own exact contract and inventory facts. Remove static counts, minimum-field matrices, and unverified executable examples. Apply YAGNI to generation and do not replace the removed duplication with fragile documentation tests.

**Status:** approved for the F-09 documentation-authority boundary.

### S-16 — Artifact source provenance

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Preserve manual version chains and template_registry.json history | Retains the current mechanism | Incomplete graph, discipline-dependent identity, and no historical source snapshots or production consumer |
| B. Keep deterministic current graph fingerprints and remove historical registry state | Minimal verifiable source identity; catalog can resolve available contributors | Historical graphs are unavailable when their suite snapshot no longer exists |
| C. Persist complete historical template and contract snapshots | Full reconstruction | Significant storage, lifecycle, and retention complexity without a demonstrated use case |
| D. Remove all scaffold source metadata | Smallest implementation | Loses low-cost current-suite traceability and graph comparison |

**Approved Strategy (2026-08-23):** choose B. Fingerprint the resolved contract and complete static Jinja graph under the F-10 suite identity, expose current contributors through the catalog boundary, and remove template_registry.json. Metadata describes initial scaffold source only. Production artifacts remain independently editable; a later refresh is a separately scaffolded candidate compared with the existing artifact, never an automatic update.

**Status:** approved for the F-11 provenance and lifecycle boundary.

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

## Required Outcome Characteristics

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

## Design Questions

The Approved Strategy closes the compatibility and ownership decisions. Design must still select concrete mechanics without reopening them:

1. Which standard JSON Schema draft, authoring layout, and internal composition form produce one fully resolved, reference-free public contract?
2. How are acyclic schema references and Jinja dependency edges resolved, ordered, validated, and identified in the coherent restart-stable suite view?
3. Which portable metadata representation replaces or normalizes the inconsistent current tier-three forms without making pgmcp own template-specific semantics?
4. What minimal generic worker and service contracts preserve useful scaffolding while excluding source-project assumptions?
5. Which result DTO fields report output target, validation evidence, resolved suite identity, and graph fingerprint without injecting them into caller content?

## Research Deliverables

This research provides:

- A complete scaffold_schema-first audit of all public artifact types.
- A durable [Template Suite Work Catalog](template-suite-catalog.md) covering all 79 suite files, example surfaces, runtime/setup consumers, and candidate tests/helpers.
- Reproducible [Probe Evidence](probe-evidence.yaml) for 44 exact minimal and property-complete calls.
- A resolved-template-graph assessment that respects the tiered architecture and identifies four unreachable files.
- A suite-wide classification of content contract defects.
- Explicit strategy options, costs, consumers, migration risks, and accepted clean-break posture per affected boundary.
- A portability boundary that keeps template-specific truth outside pgmcp-server.
- A per-component human disposition gate before design.

## References

- [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)
- [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)
- [Scaffolding Tool Reference](../../reference/tools/scaffolding.md)
- [Template Metadata Format](../../reference/template_metadata_format.md)
- [Template Library Usage](../../reference/TEMPLATE_LIBRARY_USAGE.md)
- [Template Library Patterns](../../reference/TEMPLATE_LIBRARY_PATTERNS.md)
- [Template Library Quick Reference](../../reference/TEMPLATE_LIBRARY_QUICK_REFERENCE.md)
- [Scaffolding Subsystem](../../manuals/architectural_diagrams/09_scaffolding_subsystem.md)
- [Configuration Loading Architecture](../../reference/config-loading-architecture.md)
- [Schema–Template Maintenance](../schema-template-maintenance.md)
- [Release Assets Procedure](../../reference/release-assets-procedure.md)

Implementation evidence:

- .pgmcp/templates/
- .pgmcp/templates/config/
- mcp_server/managers/artifact_manager.py
- mcp_server/tools/scaffold_schema.py
- mcp_server/tools/scaffold_artifact.py
- mcp_server/validation/template_analyzer.py
- mcp_server/services/workspace_upgrader.py
- .pgmcp/config/release_manifest.yaml

## Decision Status

**Approved Strategy:** Reopened after independent QA; existing decisions remain provisionally binding except where preserved behavior or phase purity is incomplete.

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
| F-08 / S-14 output validation and strictness | Approved 2026-08-23 | Strict validation defaults true; selected capabilities resolve through an extensible boundary on use, output profiles own applicable rules, validation evidence remains independent of persistence policy, dormant templates impose no provider dependencies, and the concrete provider mechanism remains Design-owned |
| F-09 / S-15 documentation authority | Approved 2026-08-23 | Live schema and catalog own exact facts; handwritten docs explain semantics and discovery, duplicate inventories are removed, and generation remains YAGNI-driven |
| F-10 / S-10 distribution and customization | Approved 2026-08-23 | Unchanged official targets fast-forward atomically; customized, legacy-unknown, and external roots are never overwritten, receive a complete non-authoritative candidate plus targeted difference evidence, and must be manually migrated if the selected preserved suite is incompatible with the new runtime contract |
| F-11 / S-16 source provenance | Approved 2026-08-23 | Current resolved contract and Jinja graph produce a verifiable suite-scoped fingerprint; historical registry state is removed and adopted artifacts remain independent content |
| F-12 / S-05 issue references | Approved 2026-08-23 | Positive integers carry issue identity; renderers own # and other presentation syntax |
| F-12 / S-06 checklist items | Approved 2026-08-23 | Required text and explicit checked state form one structured item; primitive strings and bridges are rejected |
| F-12 original-issue coverage | Covered 2026-08-23 | All four PR defects map to approved suite-wide boundaries; no PR-only strategy remains |
| F-13 success semantics | Approved 2026-08-23 | Objective contract, render, output-profile, and persistence evidence define success; no subjective artifact-quality engine is introduced |
| F-14 / S-12 package portability | Approved 2026-08-23 | Generic package types become portable through a clean break; six confirmed S1mpleTrader patterns are removed from PGMCP and migrated only in that owning workspace after its upgrade |
| F-14A agent hints | Approved 2026-08-23 | Remove the unused pattern, three dead imports, and stale commented workflow guidance; contracts.yaml remains workflow authority |
| Deferred YAML artifact subset | Deferred 2026-08-23 | Remove the two incomplete unreachable bases now; coordination should create the complete package subset as the first post-460 PGMCP issue on its own branch |
| F-14B unreachable test patterns | Approved 2026-08-23 | Remove the empty assertions placeholder and unreachable incomplete fixture decorator; future fixture support must be first-class test-artifact behavior |
| F-15 / S-13 output path semantics | Approved 2026-08-23 | Persistence targets remain tool-envelope and result evidence; generic artifact bodies contain no absolute or relative filesystem path by default |
| Deployment compatibility | Approved 2026-08-23 | Sole current owner accepts manual migration across two machines and approximately four workspaces; repository evidence cannot prove absence of future external consumers, so the clean break is explicit and documented rather than silently generalized |

Independent QA identified incomplete durable evidence, preserved-behavior decisions, test/helper/consumer blast-radius coverage, and phase separation. Research remains open while those gaps are resolved. Previously approved human decisions remain recorded; no Design transition is authorized until the catalog closes every affected component and a new independent QA review returns GO.

## Version History

| Version | Date | Changes |
|---|---|---|
| 1.22 | 2026-08-23 | Approve removal of the two unreachable test-pattern placeholders and close all four orphan-template dispositions |
| 1.21 | 2026-08-23 | Defer a complete YAML artifact package subset as the first post-460 PGMCP issue and classify its two incomplete bases for removal now |
| 1.20 | 2026-08-23 | Approve removal of seven patterns, assign six workspace-specific patterns to S1mpleTrader, and keep their later migration outside issue 460 |
| 1.19 | 2026-08-23 | Add durable 79-file work catalog, exact 44-probe evidence, test/helper/consumer blast radius, deployment migration posture, and Research/Design mechanism separation |
| 1.18 | 2026-08-23 | Reopen Research after independent QA found incomplete durable evidence, preserved behavior, blast radius, and phase separation |
| 1.17 | 2026-08-23 | Reconcile all approved strategies, close stale research questions, and hand concrete schema, catalog, portability, and result-shape mechanics to Design |
| 1.16 | 2026-08-23 | Approve removal of development-only filesystem paths from generic artifact bodies while retaining target resolution and result evidence |
| 1.15 | 2026-08-23 | Approve portable generic package types and consumer-owned local specialization for residual source-project worker and service patterns |
| 1.14 | 2026-08-23 | Reclassify F-13 as cross-cutting acceptance evidence and define objective scaffold success without a subjective quality engine |
| 1.13 | 2026-08-23 | Reclassify F-12 as coverage synthesis and approve integer issue references plus structured checklist items without bridges |
| 1.12 | 2026-08-23 | Record F-11 current-graph provenance, registry removal, production-artifact independence, and side-by-side refresh semantics |
| 1.11 | 2026-08-23 | Record F-10 baseline/candidate renewal, atomic fast-forward, complete custom-suite preservation, and rejection of overlays or semantic automerge |
| 1.10 | 2026-08-23 | Record F-09 live documentation authority, removal-first deduplication, YAGNI generation, and rejection of fragile doc-contract tests |
| 1.9 | 2026-08-23 | Record F-08 output-profile validation, on-use provider resolution, strict-by-default enforcement, and no mandatory example fixtures |
| 1.8 | 2026-08-23 | Record F-07 content/envelope separation, approved field outcomes, startup coherence, and Design hand-off |
| 1.7 | 2026-08-23 | Record F-06 canonical link objects, inline/reference rendering policy, reference SSOT, and Design hand-off |
| 1.6 | 2026-08-23 | Add the approved startup-resolved catalog lifecycle and mandatory restart boundary to F-05 |
| 1.5 | 2026-08-23 | Record F-05 dependency-graph evidence, Jinja syntax-analysis strategy, authority boundary, and Design hand-off |
| 1.4 | 2026-08-23 | Record F-04 DTO variant evidence, migration classification, canonical renderer strategy, and Design hand-off |
| 1.3 | 2026-08-23 | Record F-03 validation-boundary evidence, context ownership separation, approved strategy, and Design hand-off |
| 1.2 | 2026-08-23 | Record F-02 optionality evidence, semantic distinctions, approved strategy, and Design hand-off |
| 1.1 | 2026-08-23 | Record F-01 evidence, blast radius, historical client constraint, clean-break strategy, and Design hand-off |
| 1.0 | 2026-08-22 | Initial standalone scaffold_schema-first semantic audit for issue 460 |

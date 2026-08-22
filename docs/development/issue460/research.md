# Research: Issue 460 — Scaffolding Schema–Template Rendering Contract Audit

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-08-22  
**Issue:** 460  
**Research Mode:** Standalone, non-destructive, pre-initialization research

## Purpose

Establish the substantive content contract required for first-time-right scaffolding by humans and LLM callers.

The public caller contract is the output of the scaffold_schema introspection tool. The underlying configuration files, Jinja templates, loader code, packaging code, and reference documentation are implementation and distribution evidence: they explain why the introspection contract and rendered result agree or disagree, but they are not substitutes for scaffold_schema in the caller workflow.

This research does not approve an implementation strategy. It identifies affected boundaries, consumers, options, and trade-offs so that an explicit strategy can be approved before design begins.

## Scope

### In scope

- Every artifact type currently exposed through scaffold_schema: 22 types.
- Every Jinja template in the active template suite: 57 files.
- The resolved template graph, including concrete templates, inherited tiers, imported macros, and runtime template selection.
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
- Detailed implementation design or planning.
- Testability as the primary proof of correctness.

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

On 2026-08-22, scaffold_schema was invoked for all 22 exposed artifact types:

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
| F-13 | Successful scaffolding can still emit visibly null, blank, concatenated, or machine-specific content. | Callers receive artifacts that require immediate manual repair despite tool success. | default semantics, portable output |
| F-14 | Some code templates embed project-specific imports and architecture assumptions absent from scaffold_schema. | The advertised generic template suite is not independently reusable in other environments. | template-suite portability |
| F-15 | Absolute host paths are embedded in every generated artifact header. | Output is machine-specific, noisy in review, and can disclose local directory structure. | provenance presentation |

## Cross-Cutting Analysis

### F-01 — scaffold_schema cannot describe several renderer-required structures

The dominant failure class is a mismatch between introspected collection shapes and renderer access patterns.

Examples:

- adapter, generic, interface, and resource expose methods as arrays of strings while their templates read members such as name, params, return_type, docstring, and body.
- architecture exposes concepts and decisions as arrays of strings while the template reads concept names, descriptions, diagrams, subsections, decisions, rationales, and alternatives.
- integration_test and unit_test expose test_methods as arrays of strings while the templates read markers, async state, name, fixtures, return type, description, arrange, act, and assertions.
- schema exposes fields as strings while the template reads name, type, default, default_factory, and description.
- service exposes parameters as strings while the template reads name, type, and description.
- generic_doc exposes faq and custom_sections as strings while the template reads structured questions, answers, headings, content, bullets, and checklist entries.
- reference and planning use object-like arrays whose scaffold_schema items do not reveal the nested properties that templates require.

This is not a request for more elaborate YAML alone. The required outcome is that scaffold_schema returns a complete nested JSON Schema for the resolved renderer.

### F-02 — optionality has inconsistent meaning

The runtime prepares absent optional fields as null-equivalent values. Many templates use a default filter that only substitutes for an undefined value unless explicitly configured otherwise. Other templates iterate optional collections directly.

Observed consequences include:

- unit_test can attempt to iterate an optional imported_classes value after it has become null-equivalent;
- validation_report can render an unintended null-equivalent value rather than its descriptive fallback;
- default labels and descriptions vary depending on whether a value was omitted, undefined, empty, or null-equivalent.

scaffold_schema must make nullability and omission semantics explicit, and the resolved renderer must implement those semantics consistently. “Optional” cannot simultaneously mean omitted, null, empty string, and empty collection unless those cases are intentionally equivalent.

### F-03 — strict schema validation is weakened before it runs

Caller context is reduced to the set of known schema fields before strict model validation. Unknown values are therefore removed rather than rejected.

This has two semantic effects:

1. A misspelled or obsolete field can appear to be accepted while its content is lost.
2. A template capability that exists but is missing from scaffold_schema cannot be reached by an informed caller, even if the caller discovered it elsewhere.

The first-time-right contract requires error visibility. Silently discarded intent is more damaging than a clear validation failure.

### F-04 — DTO introspection and DTO runtime selection are split

The public DTO registration points to concrete/dto.py.jinja2 and advertises that contract and version. Artifact creation conditionally replaces it with concrete/dto_v2.py.jinja2 when that file exists.

The two templates do not consume the same field representation:

- the configured template expects structured field objects and additional top-level values;
- the runtime override expects a simpler field representation.

The public scaffold_schema response, runtime renderer, and provenance therefore need not describe the same artifact. This is a boundary defect, not merely a DTO formatting defect.

### F-05 — the resolved tiered graph is not fully introspected

The analyzer recognizes only a narrow extends form and misses whitespace-trimmed Jinja inheritance used throughout the suite. Imported macro dependencies are also outside the resolved chain.

Consequences:

- caller-facing introspection cannot safely be composed from the actual graph;
- metadata and version reporting omit inherited or imported semantic behavior;
- changes to shared macros may alter output without altering the reported contract identity;
- tiered templates appear flatter than they are.

A graph-aware contract must include concrete, inherited, and imported contributors. This preserves the existing tiered architecture instead of reasoning across it.

### F-06 — link values do not have one canonical representation

The related-document macro emits reference-style link uses but does not emit matching definitions. The document-oriented tier supplies definitions elsewhere; the tracking-oriented PR and issue paths do not.

This produces two incompatible interpretations of a schema string:

- raw path or URL, which currently becomes an unresolved reference-style link;
- preformatted Markdown link, which can become nested inside another generated link.

The reference artifact separately emits source and test link labels without definitions. Link correctness must be owned by the resolved artifact, not assumed from a tier that may not be in its graph.

The content contract must choose one representation:

- raw targets, with the template generating self-contained links;
- structured link objects, with separate label and target;
- caller-supplied Markdown, passed through without rewrapping.

Supporting multiple implicit interpretations should not be the final strategy.

### F-07 — exposed, hidden, and unused fields are mixed

Examples include:

- PR tracking_state is introspectable but is not rendered.
- architecture constraints is exposed but not consumed by the active template.
- reference consumes purpose although that field is not exposed by scaffold_schema.
- typescript_dto has inherited metadata capabilities that are not visible in its public schema.
- service contains a hard-coded or hidden service-type choice not available through scaffold_schema.
- research contains a legacy fallback field path that is not part of the current introspection surface.
- issue requires title in the context even though the body template intentionally does not render it because title belongs to the external issue object.

Not every non-rendering value is inherently wrong. A title used exclusively by an external API can be valid. The defect is that the role is not explicit. Each field needs one declared classification: rendered content, output routing, external envelope metadata, or deprecated/unsupported.

### F-08 — schema-valid rich contexts can produce invalid source

The substantive probes found source-level failures when richer schema-valid values were supplied:

- adapter, generic, interface, resource, integration_test, and unit_test can fail while trying to access object members on strings;
- schema and service can render invalid Python when string items are interpreted as structured definitions;
- the runtime DTO template can render invalid Python for a minimal schema-valid context while accepting a richer string-based context.

The public success criterion must be “usable artifact from any valid context,” not “the renderer returned non-empty text.”

### F-09 — documentation competes with scaffold_schema

Several references contain examples or minimum-field tables that do not match the live introspection response. Examples include:

- the scaffolding reference reports 21 types while 22 are exposed;
- worker examples use fields that are absent and omit a required layer;
- design and architecture examples omit live required values and include absent ones;
- quick-reference entries understate generic_doc requirements;
- commit is described using workflow_phase while scaffold_schema requires type;
- validation_report examples use validation_outcome while scaffold_schema exposes validation_status.

Human documentation must explain semantics and show calls, but it must not become a separately maintained field inventory. Where possible, examples and tables should be derived from or checked against the live scaffold_schema surface belonging to the template suite.

### F-10 — renewal can split paired assets

Release packaging copies both templates and their contract configuration as assets. Workspace renewal treats configuration paths as preserve-worthy while renewing template files.

Because template contract files live below a path containing config, renewal can preserve an older contract while installing newer Jinja content. This defeats atomic versioning of the independently maintained suite.

The server installation should not own the template content, but distribution must treat a suite version as a coherent unit. Local customization policy must operate on the whole contract/template pair or on explicit overlays, not on path-name heuristics.

### F-11 — metadata and version identity omit semantic contributors

Tier-three pattern files use a metadata representation that is not parsed by the current analyzer. Imported macros are absent from the version hash, and the incomplete inheritance chain further narrows provenance.

A rendered artifact can therefore change because of a macro or inherited pattern while its recorded contract identity remains stable. Portable provenance must identify the resolved suite graph and its public introspection contract.

### F-12 — the PR defects are suite-level contract symptoms

The four issue examples map directly to the cross-cutting classes:

- related_docs: ambiguous representation plus non-self-contained cross-tier macro;
- closes_issues: unconstrained semantic type plus renderer-added syntax;
- tracking_state: exposed but unconsumed intent;
- checklist_items: primitive introspection shape versus structured renderer use.

Fixing only pr.md.jinja2 would leave the same ambiguity in issue, research, reference, architecture, planning, generic_doc, and several source-code templates.

### F-13 — Successful calls can produce repair-required content

The live outputs show a recurring false-positive success state. Visible None values, empty headings, empty table cells, concatenated Markdown headings, and repeated empty code blocks all passed the scaffold operation.

This strengthens the substantive invariant: success must mean the declared caller intent was preserved in a coherent artifact. Non-empty output and absence of a renderer exception are insufficient.

### F-14 — Generic public types can resolve to project-specific content

The live worker and service artifacts import backend-specific modules and encode a particular worker lifecycle, translator, logging, and strategy-cache model. Those assumptions are not discoverable through scaffold_schema and are not suitable defaults for an independently reusable suite unless the artifact type is explicitly branded and scoped to that project architecture.

The strategy must distinguish:

- truly generic portable artifact types;
- named project-pattern artifact types with explicit prerequisites;
- local overrides supplied by the consuming environment.

A generic public name must not conceal project-specific dependencies.

### F-15 — Provenance presentation embeds the caller’s host path

Every successful probe starts with the absolute output path, including drive letter and workspace layout. Provenance can identify the suite and template version without copying machine-local path data into the artifact body.

This is a portability and human-content issue: identical inputs on two machines create needless content differences, generated patches disclose local structure, and copied templates carry irrelevant origin paths.

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

## Strategy Decisions Required Before Design

No Approved Strategy exists yet for issue 460. The following decisions must be made explicitly per boundary.

### S-01 — Source of the public introspection contract

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Resolve portable contract metadata from the complete template graph and return it through scaffold_schema | Keeps scaffold_schema authoritative; supports inheritance/import composition; suite remains portable | Requires one merge model for requiredness, nullability, nested objects, and overrides |
| B. Keep one explicit complete contract beside each public resolved artifact and have scaffold_schema return it | Simple caller model; avoids runtime inference ambiguity | Can duplicate shared tier semantics unless composition is disciplined |
| C. Infer fields directly from Jinja usage | Reduces declared duplication | Jinja access does not reliably express semantic types, alternatives, or requiredness; inference can be incomplete |
| D. Preserve the current configured-entry lookup | Minimal change | Does not describe the resolved renderer and cannot meet first-time-right goals |

**Research recommendation:** choose A or a disciplined A/B hybrid in which the portable template suite owns explicit semantic metadata and graph resolution, while scaffold_schema is the only caller-facing introspection API. Do not define raw YAML as the user or LLM contract.

**Approval required:** yes.

### S-02 — Nested collection representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Expose structured objects matching renderer concepts | Preserves expressive templates and makes nested intent discoverable | Clean-break schema changes for callers using primitive lists |
| B. Simplify renderers to consume strings only | Very easy caller surface | Loses checked state, descriptions, signatures, pros/cons, code sections, and other semantics |
| C. Temporarily accept a oneOf primitive/object bridge | Eases migration | Prolongs ambiguity and increases renderer branches; must have a removal boundary |

**Research recommendation:** use structured objects wherever the renderer makes more than one decision from an item. Any compatibility bridge must be explicitly time-bounded per artifact.

**Approval required:** yes, separately for affected artifact families.

### S-03 — Optional, omitted, empty, and null values

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Optional means omitted or a typed value; null is rejected unless explicitly meaningful | Clear deterministic contract | Existing callers sending null may break |
| B. Normalize null, omission, and empty collection before rendering | Tolerant caller experience | Can erase intentional distinctions |
| C. Permit explicit nullable fields and make every template null-safe | Maximum expressiveness | Larger public surface and more semantic cases |

**Research recommendation:** default to A; use explicit nullable fields only where null has a distinct domain meaning.

**Approval required:** yes.

### S-04 — Link representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Raw target strings; templates emit self-contained inline links | Simple for callers and portable across tiers | Labels must be derived or supplied separately |
| B. Structured objects with label and target | Fully explicit and extensible | More verbose for common cases |
| C. Caller-supplied Markdown passed through unchanged | Flexible | Hard to validate, unsafe to rewrap, and inconsistent across output formats |

**Research recommendation:** A for path lists whose label can equal the target; B when a distinct label is meaningful. Do not infer whether a string is raw or preformatted Markdown.

**Approval required:** yes.

### S-05 — Issue-reference representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Positive integer issue numbers; renderer owns the prefix | Most unambiguous | Schema-breaking for prefixed strings |
| B. Digit strings without a prefix; renderer owns the prefix | JSON-friendly across systems | Still needs a pattern and numeric semantics |
| C. Canonical prefixed references such as #460; renderer passes through | Directly reflects Markdown | Ties data to presentation syntax |

**Research recommendation:** A unless cross-system identifiers require non-numeric references.

**Approval required:** yes.

### S-06 — Checklist representation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Objects with text and checked | Preserves state and intent | Breaks primitive-list callers |
| B. Strings only, always initially unchecked | Minimal schema | Cannot represent state |
| C. Temporary union of string and object | Migration path | Ambiguous long-term contract |

**Research recommendation:** A because the renderer already expresses checked state. Use C only as an approved, time-bounded bridge.

**Approval required:** yes.

### S-07 — Exposed but unused and hidden fields

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Render every public content field and expose every renderer input | Symmetric and easy to reason about | May force output additions that are not desired |
| B. Classify fields as content, external envelope, routing, or internal metadata in scaffold_schema | Preserves valid non-rendering inputs such as external titles | Requires machine-readable role metadata |
| C. Remove all non-rendered values from artifact context | Smallest render contract | May push necessary API envelope data into a separate call surface |

**Research recommendation:** B, followed by removal of fields that have no legitimate role.

**Approval required:** yes per field whose role is currently ambiguous, including PR tracking_state and architecture constraints.

### S-08 — DTO variant and other runtime overrides

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Register the actual runtime template as the public artifact | One schema, renderer, version, and provenance | Clean break from legacy DTO behavior |
| B. Expose separate versioned artifact types | Explicit compatibility | Expands the public registry and migration burden |
| C. Keep conditional file-existence override | Minimal immediate change | Permanently violates introspection and provenance integrity |

**Research recommendation:** A or B; reject C.

**Approval required:** yes.

### S-09 — Graph metadata and provenance

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Resolve inheritance and imports with one portable parser and hash every semantic contributor | Accurate contract identity | Requires dependency-graph and cycle handling |
| B. Declare dependencies explicitly in suite metadata | Deterministic and parser-independent | Manual dependency declarations can drift |
| C. Keep inheritance-only best-effort analysis | Low effort | Cannot identify the actual rendered contract |

**Research recommendation:** A with explicit metadata only for dependencies that Jinja cannot reveal.

**Approval required:** yes.

### S-10 — Distribution and local customization

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Renew an official template suite atomically, including its introspection metadata | Prevents mixed versions | Local edits need a separate override mechanism |
| B. Preserve a customized suite atomically and report that it is not renewed | Respects external ownership | Users do not receive upstream fixes automatically |
| C. Maintain explicit versioned overlays on top of an official suite | Best extensibility model | More complex resolution and conflict reporting |
| D. Preserve config paths while replacing template paths | Current simplicity | Creates invalid mixed-version installations |

**Research recommendation:** support A plus B or C. Reject D.

**Approval required:** yes.

### S-11 — Human documentation

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Generate field inventories and examples from scaffold_schema; keep prose focused on meaning | Prevents parallel contract drift | Documentation build needs access to the portable introspection surface |
| B. Hand-maintain all examples | Flexible prose | Repeats the current drift risk |
| C. Treat documentation as authoritative over scaffold_schema | Familiar to humans | Breaks tool-driven LLM usage and first-time-right introspection |

**Research recommendation:** A.

**Approval required:** yes.

### S-12 — Generic versus project-specific artifact types

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Keep generic names and remove undeclared project assumptions | Portable, predictable public surface | Project consumers must supply or select richer patterns |
| B. Rename and expose project-specific variants with explicit prerequisites through scaffold_schema | Preserves valuable opinionated templates without disguising them | Expands the registry and requires clear ownership/versioning |
| C. Resolve consumer-local overrides under the same generic name | Flexible installations | The same artifact type can mean different content unless scaffold_schema exposes the resolved identity |
| D. Keep hidden hard-coded assumptions | No migration effort | Violates standalone reuse and first-time-right discoverability |

**Research recommendation:** A plus explicitly named B where the opinionated pattern is valuable. If C is supported, scaffold_schema must expose the resolved suite/type identity and prerequisite contract.

**Approval required:** yes for worker, service, and any other artifact found to depend on consumer-local architecture.

### S-13 — Output provenance path semantics

| Option | Benefits | Costs and risks |
|---|---|---|
| A. Omit filesystem paths from artifact bodies; retain suite/type/version provenance only | Reproducible and portable content | Loses a local convenience that can be obtained from the file itself |
| B. Emit a workspace-relative path | Useful repository context without host disclosure | Renames and moves still change content |
| C. Keep absolute paths | Direct local traceability | Machine-specific output, noisy diffs, and local path disclosure |

**Research recommendation:** A, or B only where the artifact standard requires a path header.

**Approval required:** yes.

## Portable Maintenance Boundary

The template suite must remain independently maintainable and extensible in environments where pgmcp-server is only a consumer or execution tool.

That requirement rules out using server-owned tests as the canonical store of expected template content. It also rules out embedding per-template field knowledge in server code solely so the server can verify the suite.

A sound separation is:

### Template-suite responsibility

- public artifact contracts;
- nested value semantics;
- inheritance and import dependency metadata;
- content-oriented portable validation or auditing rules;
- examples that are derived from the same introspection surface;
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

A portable auditor may inspect generic invariants such as undeclared variable use, unresolved dependency edges, unconsumed public fields, missing link targets, or syntax-invalid rendered source from suite-owned examples. It must not become a pgmcp-server matrix that hardcodes each template’s expected prose or layout.

## Required Outcome Characteristics

Issue 460 should be considered substantively resolved only when:

1. A fresh human or LLM caller can use scaffold_schema alone to construct every supported context shape.
2. The schema describes the actual resolved runtime renderer, including relevant inherited and imported contributions.
3. Every schema-valid context either produces a substantively usable artifact or receives a precise validation error before rendering.
4. Optionality, nullability, emptiness, and defaults have one declared meaning.
5. Links, issue references, and checklist items each have one canonical representation.
6. Every exposed field has an explicit role and no caller intent is silently discarded.
7. Template-suite metadata, templates, examples, and version identity travel as a coherent portable unit.
8. pgmcp-server does not become the owner of template-specific content truth.
9. Human documentation cannot contradict the live scaffold_schema field surface.
10. Generic artifact names do not conceal consumer-project imports, lifecycle assumptions, or prerequisites.
11. Generated content is reproducible across host machines and does not embed absolute local paths by default.
12. Compatibility choices are approved per affected boundary before design.

## Open Questions

1. Should the public contract be composed from metadata attached to every tier/import, or should each public artifact publish one resolved contract generated by the suite?
2. Which artifact types have external consumers that currently send primitive arrays and therefore require a temporary bridge?
3. Is PR tracking_state intended as rendered content, external coordination metadata, or obsolete input?
4. Is architecture constraints intentionally reserved for another output channel, or should it render in the document?
5. Should issue title remain part of artifact context as explicit external-envelope metadata, or move to the issue tool envelope?
6. Which DTO behavior is the intended public version, and does legacy DTO scaffolding require a separately named compatibility type?
7. Should related-document labels always equal targets, or is a structured label/target object required?
8. Does the standalone suite need format-specific link types for Markdown, Python docstrings, YAML, and other future outputs?
9. What is the approved policy for customized workspace suites during official renewal: preserve whole suite, overlay, or explicit replacement?
10. Which current tier-three metadata form is intended to be the portable canonical representation?

## Expected Research Deliverables

- A complete scaffold_schema-first audit of all public artifact types.
- A resolved-template-graph assessment that respects the tiered architecture.
- A suite-wide classification of content contract defects.
- Explicit strategy options, costs, consumers, and risks per affected boundary.
- A portability boundary that keeps template-specific truth outside pgmcp-server.
- A human decision point before design.

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

**Approved Strategy:** None.

Research remains open until a human explicitly approves the strategy for each affected boundary. Design must not infer approval from the recommendations in this document.

## Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-08-22 | Initial standalone scaffold_schema-first semantic audit for issue 460 |

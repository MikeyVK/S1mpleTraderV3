<!-- docs/development/issue456/planning.md -->
<!-- template=planning version=130ac5ea created=2026-08-20T20:26Z updated=2026-08-20 -->
# Compact Actionable Tool Summaries — Planning

**Status:** REVIEW  
**Version:** 1.5  
**Last Updated:** 2026-08-21

---

## Purpose

Convert the approved Research and Design into dependency-ordered implementation cycles with proportional, durable evidence and no invalid runtime/configuration intermediate.

## Scope

**In Scope:** One runtime-derived complete supported-tool catalog and settings-dependent active subset; frozen presentation configuration; fail-fast complete-catalog alignment; generic list/tuple sequence and recursive collection rendering; final UTF-8 byte limiting; TextPresenter composition; the approved workflow-state, canonical SafeEdit-validation, pytest-duration, and duplicate-field clean breaks; all 50 approved presentation projections; the complete 29-tool mechanics matrix; and removal of the two obsolete documentation-test modules.

**Out of Scope:** Structured quality-gate findings; DTO or cache-payload changes beyond the Approved Strategy; static or public tool-catalog metadata; arbitrary iterable/query rendering; tool-specific renderer branches; sorting/filtering; production documentation edits before Documentation; and workspace-wide verification before Validation.

## Prerequisites

1. [Approved Research v1.9](research.md)
2. [Approved Design v1.7](design.md)
3. [Approved 50-tool field audit v1.4](tool-presentation-field-audit.md)
4. [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)
5. [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)

---

## Summary

Eight coherent cycles establish the composition-root catalog before its configuration consumer, add generic presentation capabilities before integrating them, perform DTO/configuration clean breaks atomically, complete every approved tool projection, and finally remove obsolete documentation tests. Cycles 1–7 change durable behavior and use RED → GREEN → REFACTOR. Cycle 8 is approved test maintenance and deliberately creates no artificial RED test.

The plan preserves the Approved Strategy:

- one authoritative runtime assembly derives both complete supported contracts and the active tool subset;
- presentation configuration exactly covers all supported tools, including valid inactive tools;
- complete structured results remain available through the resource cache;
- presentation stays configuration-driven and independent of tool names and DTO types;
- only concrete `list[T]` and `tuple[T, ...]` ordered sequences are supported;
- every approved DTO clean break moves atomically with its dependent template;
- every tool field is intentionally inline or cache-only;
- DTO order is retained and the only universal text ceiling is 8,000 UTF-8 bytes.

## Planning Boundary

Planning owns work slicing, dependencies, deliverables, test mechanics, gates, and stop/go evidence. It does not reinterpret the approved projections, expand the catalog beyond its two designed consumers, change compatibility strategy, or prescribe implementation code bodies. New evidence that contradicts Research or Design stops Implementation and reopens the applicable decision.

## Dependency Order

| Cycle | Depends on | Unlocks |
|---|---|---|
| 1. Runtime tool assembly and supported catalog | Approved Design | Authoritative supported contracts and active objects |
| 2. Presentation configuration and complete-catalog alignment | Cycle 1 | Validated declarative policy for every supported output model |
| 3. Generic ordered-sequence and collection presentation | Cycle 2 | Reusable bounded projection behavior |
| 4. UTF-8 text budget enforcement | Cycle 2 | Independently proven final-response safety boundary |
| 5. TextPresenter composition | Cycles 1–4 | Generic end-to-end presentation pipeline |
| 6. Atomic structured DTO and dependent-template migration | Cycle 5 | Approved clean-break contracts without invalid startup state |
| 7. Complete 50-tool projection rollout | Cycle 6 | Full approved field audit and 29-tool mechanics closure |
| 8. Obsolete documentation-test removal | Cycle 7 | Stable implementation baseline for Validation |

Do not begin a cycle while a dependency has unresolved focused tests, file-scoped gates, or stop conditions. Evidence from an earlier cycle is reused unless later changes invalidate it.

---

## Cycle 1 — Runtime Tool Assembly and Supported Catalog

**Mode:** Durable architecture and behavior change; RED → GREEN → REFACTOR required.

**Goal:** Replace settings-split registration knowledge with one composition-root assembly that derives the complete supported contracts and the settings-dependent active object subset from the same tool instances.

### Scope and Seams

- [Bootstrap composition](../../../mcp_server/bootstrap.py)
- Core tool identity/output-model contracts and the narrow assembly seam adjacent to bootstrap
- [Bootstrap unit tests](../../../tests/mcp_server/unit/server/test_bootstrap.py)
- Focused assembly/catalog tests if a separate production seam is extracted

**Excluded:** Presentation content, catalog persistence, descriptive metadata, capability APIs, and external-work constructor changes.

**Approved Strategy obligation:** The catalog is runtime-derived and YAGNI-limited to tool identity/output model plus the construction/activation information already needed by bootstrap; it is not a static file or second tool-name list.

### Deliverables

| ID | Deliverable |
|---|---|
| C_ASSEMBLY.1 | One `ToolAssembly` exposes immutable `supported_tools`, `active_tools`, and derived `supported_contracts` tuples from one authoritative composition-root construction path. |
| C_ASSEMBLY.2 | Each supported contract resolves exactly one non-empty tool name and Pydantic output model; empty/duplicate names and unresolved or conflicting explicit/generic output models fail deterministically. |
| C_ASSEMBLY.3 | Active tools are an object subset of supported tools; token-enabled activation covers the supported set and tokenless activation preserves the existing credential-free subset without a separately maintained count/name catalog. |
| C_ASSEMBLY.4 | Supported-but-inactive tool construction performs no external work; the existing lazy GitHub boundary and tokenless startup remain intact. |
| C_ASSEMBLY.5 | Focused tests cover both settings variants and every assembly invariant through the public bootstrap/assembly contract. |

### Test and Gate Evidence

- RED: focused tests expose the duplicated settings branches and missing catalog/active-subset invariants.
- GREEN: run the focused assembly and bootstrap tests for token-enabled and tokenless settings.
- REFACTOR: rerun those tests and file-scoped gates for changed production and test files.
- Tests derive expectations from the assembly contract and activation policy; they do not introduce a second 50-name list or freeze observed counts as catalog truth.

### Exit and Stop Conditions

Exit only when one assembly owns supported and active objects, every supported output model resolves, tokenless startup succeeds, and all invalid identity/subset cases fail with actionable context. Stop if inactive construction performs external work, a separate catalog must be maintained, or broader metadata/capability design becomes necessary.

---

## Cycle 2 — Presentation Configuration and Complete-Catalog Alignment

**Mode:** Durable configuration behavior; RED → GREEN → REFACTOR required.

**Goal:** Establish frozen presentation policy and validate it fail-fast against every supported contract from Cycle 1, regardless of runtime activation.

### Scope and Seams

- [Presentation configuration schema](../../../mcp_server/config/schemas/presentation_config.py)
- Presentation-alignment seam currently in [TextPresenter](../../../mcp_server/presenters/text_presenter.py), extracted only if cohesion requires it
- [Presentation configuration](../../../.pgmcp/config/presentation.yaml) global policy
- Existing presenter tests plus a focused presentation-config/alignment test module

**Excluded:** Sequence rendering, TextPresenter orchestration changes, and per-tool projection rollout.

**Approved Strategy obligation:** `presentation.yaml` keys exactly equal the complete supported catalog. A supported-but-inactive key is valid; missing supported keys, unknown keys, and duplicate identities are startup failures.

### Deliverables

| ID | Deliverable |
|---|---|
| C_CONFIG.1 | Frozen schema represents recursive direct-child collections, enum cases, list/tuple scalar sequences, one per-tool `max_items`, omission/truncation wording, and the global byte ceiling. |
| C_CONFIG.2 | Startup alignment recursively validates direct fields, list/tuple item categories, placeholders, duplicate siblings, enum cases, `max_items` use, and mandatory-tail budget against every supported output model. |
| C_CONFIG.3 | Alignment enforces deterministic bidirectional supported-catalog/config parity while accepting valid inactive templates and rejecting missing, unknown, or obsolete keys. |
| C_CONFIG.4 | Global `presentation.yaml` values supply the 8,000-byte ceiling and all generic omission/truncation wording without adding tool-specific Python policy. |
| C_CONFIG.5 | Durable schema/alignment tests cover representative flat, scalar-sequence, model-collection, nested, enum, list, and tuple declarations plus every designed startup rejection category. |

### Test and Gate Evidence

- RED: focused tests fail for absent schema/alignment behavior, active-only parity, skipped output models, and malformed declarations.
- GREEN: run the presentation-config and alignment test scopes using supported contracts from Cycle 1.
- REFACTOR: rerun those focused tests and file-scoped gates.
- Tests assert structured configuration behavior and path-rich errors, not presentation prose.

### Exit and Stop Conditions

Exit only when all current supported contracts and bundled keys match, inactive templates are accepted, every supported output model is validated, and invalid declarations fail with deterministic tool/path context. Stop if alignment constructs tools, uses the active subset as catalog truth, silently skips unresolved models, or requires tool-name dispatch.

---

## Cycle 3 — Generic Ordered-Sequence and Collection Presentation

**Mode:** Durable presentation behavior; RED → GREEN → REFACTOR required.

**Goal:** Provide one generic ordered-sequence classifier and bounded rendering behavior for scalar and Pydantic-model `list[T]` and `tuple[T, ...]` values.

### Scope and Seams

- Cohesive generic value-formatting seam under `mcp_server/presenters`
- Generic `CollectionTextRenderer` seam under `mcp_server/presenters`
- Presentation configuration models from Cycle 2
- Focused public-contract tests under `tests/mcp_server/unit/presenters`

**Excluded:** TextPresenter orchestration, per-tool declarations, arbitrary iterables, dotted paths, conditions, sorting, and filtering.

**Approved Strategy obligation:** Generic mechanisms inspect configuration and structural field categories only; they never import or branch on tool names, `ValidationIssue`, or any other DTO type.

### Deliverables

| ID | Deliverable |
|---|---|
| C_SEQUENCE.1 | One shared classifier recognizes only concrete scalar/model `list[T]` and `tuple[T, ...]` shapes for both alignment and rendering. |
| C_SEQUENCE.2 | `SafeNoneFormatter` generically renders bounded flat scalar lists/tuples with configured separators, omission count, and None behavior. |
| C_SEQUENCE.3 | `CollectionTextRenderer` renders scalar/model lists and tuples, siblings, and direct-child nesting depth-first in authoritative DTO order. |
| C_SEQUENCE.4 | Empty, exact-limit, over-limit, None, multibyte, list, tuple, sibling, and nested behavior has durable public-contract coverage. |
| C_SEQUENCE.5 | Missing fields, non-list/tuple containers, and wrongly typed items raise `ConfigError` with usable field/path and item-index context. |
| C_SEQUENCE.6 | Source and tests prove there is no tool/DTO dispatch, sorting, filtering, model-sequence Python repr, or arbitrary-iterable acceptance. |

### Test and Gate Evidence

- RED: public-contract tests fail for the absent generic list/tuple behaviors and all three malformed runtime-shape classes.
- GREEN: run only focused formatter/classifier/renderer tests.
- REFACTOR: rerun focused tests and file-scoped gates for changed production and test files.
- Tests exercise public formatting/rendering contracts; parameterization covers containers and item categories without multiplying wording snapshots.

### Exit and Stop Conditions

Exit only when order, limits, omission counts, nested association, and scalar formatting are deterministic for lists and tuples, and every unexpected runtime shape raises path-rich `ConfigError`. Stop if implementation needs a generic query language, tool-specific handling, DTO changes, or silent skipping.

---

## Cycle 4 — UTF-8 Text Budget Enforcement

**Mode:** Durable presentation behavior; RED → GREEN → REFACTOR required.

**Goal:** Enforce the configured final text ceiling while retaining readable Markdown, truthful truncation wording, and the complete cache URI whenever available.

### Scope and Seams

- New `TextBudgetLimiter` seam under `mcp_server/presenters`
- Global budget and notice configuration from Cycle 2
- Focused public-contract tests under `tests/mcp_server/unit/presenters`

**Excluded:** TextPresenter wiring, tool templates, and limits on separately embedded MCP resources.

**Approved Strategy obligation:** 8,000 UTF-8 bytes is the one server-owned hard ceiling; normal item limits improve usefulness but never replace the final limiter.

### Deliverables

| ID | Deliverable |
|---|---|
| C_BUDGET.1 | `TextBudgetLimiter` returns under-budget content byte-for-byte unchanged and caps every overflow result at `max_text_response_bytes`. |
| C_BUDGET.2 | Overflow reserves the complete cache reference and correct configured notice before retaining body content. |
| C_BUDGET.3 | Truncation preserves UTF-8 code points, prefers complete blocks/lines, and closes an intersected fenced block. |
| C_BUDGET.4 | Cache-unavailable truncation remains bounded without claiming that complete detail was cached. |
| C_BUDGET.5 | Boundary tests cover under, exact, over, mandatory-tail, multibyte, fenced Markdown, and cache-unavailable cases. |

### Test and Gate Evidence

- RED: focused limiter tests fail at designed byte and Markdown boundaries.
- GREEN: run only the focused limiter test module.
- REFACTOR: rerun limiter tests and file-scoped gates.
- Mandatory-tail cases use a stable representative cache URI without asserting incidental wording.

### Exit and Stop Conditions

The hard invariant is `len(result.encode("utf-8")) <= configured_budget` for every case. Stop if any path corrupts UTF-8, exceeds budget, loses an available cache URI, changes under-budget text, or misrepresents cache failure.

---

## Cycle 5 — TextPresenter Composition

**Mode:** Durable integration behavior; RED → GREEN → REFACTOR required.

**Goal:** Compose the generic sequence/collection renderer and byte limiter under TextPresenter before any broad projection or DTO migration.

### Scope and Seams

- [TextPresenter](../../../mcp_server/presenters/text_presenter.py)
- [ResponsePresenter](../../../mcp_server/presenters/response_presenter.py), whose external contract remains unchanged
- [Bootstrap composition](../../../mcp_server/bootstrap.py)
- Focused presenter, server, and pipeline integration tests using synthetic representative configurations

**Excluded:** The approved DTO clean breaks and complete 50-tool template rollout.

**Approved Strategy obligation:** TextPresenter assembles generic configured blocks only; cache publication remains prior and authoritative, and separately embedded validation resources remain outside the text budget.

### Deliverables

| ID | Deliverable |
|---|---|
| C_COMPOSE.1 | TextPresenter assembles scalar text, enum cases, configured collections, instructions, notes, sanitized fallback, reserved cache reference, and the final limiter in the approved order. |
| C_COMPOSE.2 | Bootstrap injects/composes the new helpers once and decorates/registers only `ToolAssembly.active_tools`; alignment still receives complete supported contracts. |
| C_COMPOSE.3 | Under-budget legacy-compatible templates remain byte-for-byte unchanged; over-budget output changes only through the universal limiter. |
| C_COMPOSE.4 | Server/pipeline evidence proves cached DTOs remain complete and separately embedded validation resources are not counted in the text ceiling. |
| C_COMPOSE.5 | Presenter source and tests contain no tool-name, output-DTO-type, or validation-record-type dispatch. |

### Test and Gate Evidence

- RED: focused presenter/server/pipeline tests fail for block order, generic composition, active/supported wiring, under-budget identity, and final limiting.
- GREEN: run the focused presenter, bootstrap/server, and pipeline cases only.
- REFACTOR: rerun affected tests and file-scoped gates.
- Use representative flat, enum, nested, list, and tuple configurations; do not snapshot all tool wording.

### Exit and Stop Conditions

Exit only when the generic pipeline works end to end, complete supported alignment remains distinct from active registration, cache evidence is unchanged, and an intentionally retained compact template is stable below the ceiling. Stop if ResponsePresenter/cache contracts change or composition requires any tool/DTO special case.

---

## Cycle 6 — Atomic Structured DTO and Dependent-Template Migration

**Mode:** Durable architecture and behavior change; RED → GREEN → REFACTOR required.

**Goal:** Apply every approved structured clean break together with every template that depends on the removed representation, preventing an invalid startup/configuration intermediate.

### Scope and Seams

- [Validation records](../../../mcp_server/validation/base.py)
- [ValidationService](../../../mcp_server/validation/validation_service.py)
- [ArtifactManager](../../../mcp_server/managers/artifact_manager.py)
- [SafeEditTool](../../../mcp_server/tools/safe_edit_tool.py)
- [Tool output DTOs](../../../mcp_server/schemas/tool_outputs.py) and affected producers
- [GetWorkContextTool](../../../mcp_server/tools/discovery_tools.py)
- [PytestRunner](../../../mcp_server/managers/pytest_runner.py)
- [RunTestsTool](../../../mcp_server/tools/test_tools.py)
- Exactly the [presentation configuration](../../../.pgmcp/config/presentation.yaml) entries that consume changed/removed fields
- Focused public-contract tests for each affected boundary

**Excluded:** Unaffected tool projection optimization, compatibility aliases, dual writes, and redesign of startup/input/template validation systems.

**Approved Strategy obligation:** One canonical frozen serializable `ValidationIssue` remains unchanged across validators, ValidationService, ArtifactManager, SafeEditOutput, cache serialization, and generic collection presentation. No duplicate DTO, mapping, parsing, or presentation-specific service result is allowed.

### Deliverables

| ID | Deliverable |
|---|---|
| C_STRUCTURED.1 | `WorkflowStateStatus` represents available, missing, unreadable, and invalid-phase states; GetWorkContextTool emits structured state/supporting data and no warning/recovery prose. |
| C_STRUCTURED.2 | The existing canonical `ValidationIssue` becomes the single frozen serializable record; ValidationService aggregates ordered records and ArtifactManager/SafeEditTool forward the same records without formatting, parsing, copying, or field mapping. |
| C_STRUCTURED.3 | `SafeEditOutput.issues` is the canonical record tuple and its template uses the generic bounded model-collection mechanism with message, severity, line, column, and code. |
| C_STRUCTURED.4 | `RunTestsOutput` exposes numeric `duration_seconds`; PytestRunner parses it without producing presentation wording and `summary_line` is removed. |
| C_STRUCTURED.5 | All seven approved duplicate presentation fields and their producer writes are removed without aliases or dual writes. |
| C_STRUCTURED.6 | Every template affected by C_STRUCTURED.1–5 moves atomically to structured fields and passes complete-catalog startup alignment at cycle exit. |
| C_STRUCTURED.7 | Durable public-contract tests cover enum outcomes, canonical record identity/value propagation through both consumers, optional validation locations/codes, numeric/missing duration, removed-field absence, cache serialization, and immutability. |
| C_STRUCTURED.8 | Config validation, input validation, and explicit template-validation tools retain their existing separate DTOs and responsibilities. |

### Test and Gate Evidence

- RED: focused tests expose tool-owned workflow prose, validation string collapse, SafeEdit scalar issues, pytest summary wording, and duplicate-field contracts.
- GREEN: run discovery/workflow-state, validation service, ArtifactManager, SafeEdit, PytestRunner, RunTests, affected producer, presentation-alignment, and cache-serialization scopes.
- REFACTOR: rerun all affected focused tests and file-scoped gates for changed Python/config/test files.
- Tests assert canonical record continuity and public structured behavior; they do not parse logs or compare mutable presentation prose.

### Exit and Stop Conditions

Exit only when all structured contracts and their dependent templates load together, the same canonical validation records reach both consumers, all approved obsolete fields are absent, and server startup alignment remains green. Stop if any layer needs a second issue DTO, field mapping, string parsing, presenter type dispatch, compatibility bridge, or a change to unrelated validation responsibilities.

---

## Cycle 7 — Complete 50-Tool Projection Rollout

**Mode:** Durable configuration and presentation behavior; RED → GREEN → REFACTOR required.

**Goal:** Implement or explicitly retain every approved field-audit projection and close the complete 29-tool mechanics matrix through generic configuration.

### Scope and Seams

- [Presentation configuration](../../../.pgmcp/config/presentation.yaml)
- [Approved 50-tool field audit](tool-presentation-field-audit.md)
- Complete mechanics authority in [Design Section 3.8](design.md)
- Focused configuration/presenter structural tests
- Representative server/pipeline presentation tests for decision-dense outputs

**Excluded:** New DTO changes, per-tool renderer code, deep-log publication, and exact-wording snapshots for all tools.

**Approved Strategy obligation:** Every supported tool-specific output field is either intentionally inline or cache-only with the approved rationale; all 29 sequence/collection tools use the designed generic mechanisms and limits.

### Deliverables

| ID | Deliverable |
|---|---|
| C_ROLLOUT.1 | All 50 supported tool templates implement or explicitly retain the approved inline/cache-only target from the field audit. |
| C_ROLLOUT.2 | One structural matrix proves all 29 tools declare every required inline scalar sequence, root/child collection, item contract, and limit from Design Section 3.8. |
| C_ROLLOUT.3 | `get_work_context`, `get_issue`, and `get_pr` expose the three approved scalar expansions; issue labels use bounded generic sequence formatting. |
| C_ROLLOUT.4 | `run_quality_gates` and `validate_template` use outcome-neutral completion wording and expose their actual result as data. |
| C_ROLLOUT.5 | Representative `run_tests` and `run_quality_gates` summaries expose bounded actionable rows while excluding traceback, stderr, and verbose gate details. |
| C_ROLLOUT.6 | `get_project_plan` renders its nested phase/task association in DTO order; list and tuple projections use the same generic behavior. |
| C_ROLLOUT.7 | Complete supported-catalog/config parity and recursive output-model alignment pass for token-enabled and tokenless settings; valid inactive keys remain accepted. |
| C_ROLLOUT.8 | Cached DTOs remain complete, each cache-only decision matches an approved rationale category, and source inspection finds no tool/DTO dispatch. |
| C_ROLLOUT.9 | A template explicitly retained by the audit remains byte-for-byte stable below budget and limiter-only different above it. |

### Test and Gate Evidence

- RED: adapt one structural matrix test plus representative behavior tests for the missing approved projections, 29-tool mechanics, semantic outcomes, nested plan, bounded labels/findings/failures, verbose-field exclusion, and retained-template compatibility.
- GREEN: run focused presentation-config, presenter, bootstrap/server, and pipeline scopes.
- REFACTOR: rerun affected focused tests and file-scoped gates for all changed source/config/test files.
- Structural evidence may name the approved 29 field/mechanism rows; it must derive the complete supported key set at runtime and must not duplicate a static tool catalog or create 50 prose snapshots.

### Exit and Stop Conditions

Exit only when all 50 audit rows and all 29 mechanics rows are closed, both settings variants start, exact supported/config parity passes, diagnostic outputs are actionable and bounded, cache authority is intact, and no approved row was reinterpreted. Stop if any field lacks an approved classification, a static catalog appears, or implementation requires new DTO/cache/transport behavior.

---

## Cycle 8 — Obsolete Documentation-Test Removal

**Mode:** Mechanical test maintenance; no artificial RED.

**Goal:** Delete the two approved brittle documentation-test modules without replacing them with mutable prose assertions.

### Scope and Seams

- `tests/documentation/test_c4_doc_alignment.py`
- `tests/documentation/test_agent_instruction_search_contract.py`

**Excluded:** Production, configuration, agent-instruction, and active documentation content.

**Approved Strategy obligation:** Remove workflow-created textual ballast while retaining behavior-oriented tests introduced by Cycles 1–7.

### Deliverables

| ID | Deliverable |
|---|---|
| C_TEST_CLEANUP.1 | `tests/documentation/test_c4_doc_alignment.py` is absent. |
| C_TEST_CLEANUP.2 | `tests/documentation/test_agent_instruction_search_contract.py` is absent. |
| C_TEST_CLEANUP.3 | All 62 collected cases disappear without replacement mutable-prose tests. |

### Test and Gate Evidence

- Record the approved no-RED rationale in the cycle hand-over.
- Verify both exact paths are absent and `tests/documentation` contains no remaining test module.
- Do not run unrelated tests merely to accompany deletion.
- Validation owns the workspace-wide run and final collected-count evidence.

### Exit and Stop Conditions

Stop if either module contains behavior coverage beyond mutable documentation/instruction text; otherwise exit on exact deletion, absence of replacement tests, and no unrelated change.

---

## Documentation-Phase Deliverables

| ID | Deliverable |
|---|---|
| DOC_PRESENTATION.1 | Update presentation architecture for runtime supported/active assembly, complete-catalog alignment, declarative list/tuple collections, final byte limiting, and cache authority. |
| DOC_TOOLS.1 | Correct active discovery, project, GitHub, quality, scaffolding, and tools-overview claims affected by richer inline summaries. |
| DOC_AGENT.1 | Review agent cache guidance and change it only where it still mandates a resource read for information now guaranteed inline. |
| DOC_DEFERRED.1 | Preserve the structured quality-gate finding as deferred work, not current behavior. |

Documentation work remains a current-state description and creates no historical trace prose.

## Validation-Phase Deliverables

| ID | Deliverable |
|---|---|
| VAL_FOCUSED.1 | Reconfirm affected assembly, catalog, config, formatter, renderer, limiter, presenter, structured-boundary, server, and pipeline tests after final implementation changes. |
| VAL_FULL.1 | Run one workspace-wide test suite and record exact totals. |
| VAL_GATES.1 | Run branch-wide quality gates once and inspect the cached structured result. |
| VAL_BEHAVIOR.1 | Record evidence for supported/active assembly invariants, tokenless startup, exact complete-catalog parity, 8,000-byte enforcement, cache-URI retention, list/tuple order and limits, all 29 mechanics, nested plan, labels, enum warnings, canonical SafeEdit issues, numeric test duration, removed-field absence, semantic outcomes, all 50 audit rows, retained-template compatibility, and complete cached DTOs. |
| VAL_DEFERRED.1 | Carry the structured quality-gate findings gap into `validation.md` for Ready/PR triage. |
| VAL_REPORT.1 | Publish the validation report with failures, residual risks, and deferred work. |

Do not repeat the workspace-wide suite or branch-wide gates unless a later change invalidates their evidence.

## Deferred Work

Structured `GateFindingDTO` research remains explicitly outside issue #456. Implementation must not parse gate-specific details or change quality-gate output DTOs. Validation records the finding; Ready includes it in the PR body for post-merge coordination triage.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Catalog and active registration drift | Cycle 1 derives both from one ToolAssembly and tests subset/identity invariants without a static catalog. |
| Configuration validates only active tools | Cycle 2 consumes complete supported contracts; Cycle 7 proves both settings variants accept the same 50-key configuration. |
| Inactive construction starts external work | Cycle 1 verifies constructor safety and stops on any external-work assumption breach. |
| Config and renderer evolve out of step | Cycle 2 establishes fail-fast structural alignment; Cycle 3 shares one list/tuple classifier. |
| DTO migration creates an invalid server intermediate | Cycle 6 moves each clean break and every dependent template atomically, then runs startup alignment. |
| Validation records are copied or reformatted | Cycle 6 tests one canonical record across validators, service, manager, tool output, and serialization. |
| Full rollout becomes indiscriminate DTO dumping | Cycle 7 is bound to the approved field audit and its cache-only rationale categories. |
| Text limiting corrupts Markdown or loses cache reference | Cycle 4 isolates byte/Markdown behavior and treats URI retention as blocking. |
| Implementation recreates per-tool branches | Generic seam tests plus source inspection in Cycles 3, 5, and 7. |
| Test explosion returns | Capability tests, one structural mechanics matrix, representative integrations, and explicit Cycle 8 cleanup replace per-tool wording snapshots. |
| Quality-gate output remains less actionable than test failures | Preserve it as deferred work instead of widening the current DTO boundary. |

## Milestones

- M1: Runtime supported catalog and active subset share one authoritative assembly.
- M2: Complete-catalog configuration and generic list/tuple projection contracts are executable.
- M3: Final text budgeting and TextPresenter composition are independently proven.
- M4: Structured clean breaks and dependent templates are atomic and startup-valid.
- M5: All 50 projections and all 29 mechanics rows are closed.
- M6: Obsolete documentation tests are removed.
- M7: Validation owns one workspace-wide test run and one branch-wide gate run.

## Open Work

None at the Planning decision boundary. Implementation must stop and reopen Design if an inactive constructor performs external work, output-model resolution cannot remain minimal, or any approved field projection requires a new DTO/cache/transport contract.

## Related Documentation

- [Research](research.md)
- [Design](design.md)
- [Tool Presentation Field Audit](tool-presentation-field-audit.md)
- [Presentation Architecture](../../reference/presentation_architecture.md)
- [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)
- [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-20 | Agent | Initial five-cycle implementation, documentation, and validation plan |
| 1.1 | 2026-08-20 | Agent | Add runtime-shape and unchanged-tool compatibility obligations; restore preliminary review status |
| 1.2 | 2026-08-21 | Agent | Add exact registration/config parity and full 50-tool template optimization |
| 1.3 | 2026-08-21 | Agent | Add structured DTO/service refactor and shift complete rollout/cleanup |
| 1.4 | 2026-08-21 | Agent | Align scope, prerequisites, compatibility claims, configuration references, and deferred boundaries |
| 1.5 | 2026-08-21 | Agent | Align eight implementation cycles with runtime-derived catalog parity, all 29 mechanics, and canonical validation-record reuse |

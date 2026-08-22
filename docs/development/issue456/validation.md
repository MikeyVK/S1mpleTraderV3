<!-- docs/development/issue456/validation.md -->
<!-- template=validation_report version=fe38a66d created=2026-08-22T00:00Z updated=2026-08-22 -->
# Issue 456 Validation Report

**Status:** DEFINITIVE  
**Version:** 1.0  
**Last Updated:** 2026-08-22  
**Validation Outcome:** PASS  
**Issue:** #456  
**Cycle:** Feature branch validation  

---

## Scope

This report validates the completed implementation against the approved
[Research](research.md), [Design](design.md), [Planning](planning.md), and
[Tool Presentation Field Audit](tool-presentation-field-audit.md). It covers the
runtime-derived tool catalog, declarative presentation configuration, ordered-sequence
rendering, final UTF-8 byte limiting, TextPresenter composition, structured DTO clean
breaks, the complete 50-tool projection rollout, and approved documentation-test
removal.

Production documentation updates remain owned by the Documentation phase. Independent
QA approval is not claimed by this report.

## Outcome

**PASS.** The definitive post-correction workspace suite and branch-wide quality gates
are green. No implementation blocker remains for the Documentation phase.

## Definitive Evidence

### Workspace-Wide Tests

`run_tests(scope='full', timeout=900, verbose=false)`

| Result | Count |
|---|---:|
| Passed | 2,859 |
| Failed | 0 |
| Skipped | 2 |
| Errors | 0 |
| Duration | 38.30 seconds |

Cached structured evidence:
`pgmcp://cache/runs/eb121630998f4aaf9373841f41e97665`.

Coverage was not requested by the workflow's Validation instruction and was not
reported by this run.

### Branch-Wide Quality Gates

`run_quality_gates(scope='branch', verbose=false)`

- Scope: 44 branch-changed quality files.
- Overall result: pass.
- Ruff format, strict lint, imports, line length, Pyright, and the
  `mcp_server` type gate passed.
- The general Types gate was skipped because no matching files were selected; the
  dedicated `mcp_server` type gate passed.

Cached structured evidence:
`pgmcp://cache/runs/1e0874554d3e415db83d43759cb4aaf1`.

### Runtime Demonstration

The server was restarted after the final implementation correction. Startup accepted
the complete runtime-derived tool catalog and presentation configuration, and
`health_check` returned `healthy` for server version 2.0.0. Subsequent
`get_work_context`, `run_tests`, and `run_quality_gates` calls exercised the live
configured summaries, bounded collections, resource references, and outcome-neutral
quality wording.

## Deliverable Mapping

| Planned deliverables | Evidence and result |
|---|---|
| C_ASSEMBLY.1–5 | [Bootstrap assembly](../../../mcp_server/bootstrap.py) derives immutable supported contracts and the active subset from one construction path. Token-enabled and tokenless bootstrap tests pass. |
| C_CONFIG.1–5 | [Presentation schema](../../../mcp_server/config/schemas/presentation_config.py) and [alignment tests](../../../tests/mcp_server/unit/config/test_presentation_config.py) cover frozen recursive policy, exact catalog parity, enum/list/tuple validation, invalid shapes, and the 8,000-byte ceiling. |
| C_SEQUENCE.1–6 | [Collection renderer](../../../mcp_server/presenters/collection_text_renderer.py) and its [unit tests](../../../tests/mcp_server/unit/presenters/test_collection_text_renderer.py) preserve DTO order, bound each depth, and fail fast on missing or invalid success-output shapes without tool-specific dispatch. |
| C_BUDGET.1–5 | [Text budget limiter](../../../mcp_server/presenters/text_budget_limiter.py) and [boundary tests](../../../tests/mcp_server/unit/presenters/test_text_budget_limiter.py) prove byte-for-byte under-budget identity, UTF-8-safe truncation, Markdown repair, correct notices, and complete cache-reference retention. |
| C_COMPOSE.1–5 | [TextPresenter](../../../mcp_server/presenters/text_presenter.py) and [composition tests](../../../tests/mcp_server/unit/presenters/test_text_presenter_composition.py) verify ordered assembly, complete cached/resource data, generic failure-envelope handling, and no tool-name, output-DTO-type, or validation-record-type dispatch. |
| C_STRUCTURED.1–8 | [Tool output schemas](../../../mcp_server/schemas/tool_outputs.py), [ValidationService](../../../mcp_server/validation/validation_service.py), and [migration tests](../../../tests/mcp_server/unit/schemas/test_structured_tool_output_migration.py) cover structured workflow state, canonical validation issues across every service path, numeric test duration, seven removed duplicate fields, and retained separation between validation domains. |
| C_ROLLOUT.1–9 | [presentation.yaml](../../../.pgmcp/config/presentation.yaml), the [29-tool mechanics test](../../../tests/mcp_server/unit/config/test_tool_presentation_rollout.py), live startup, and the approved field audit close all 50 projections, all limits and nested mechanics, scalar expansions, neutral outcomes, cache-only classifications, and retained-template compatibility. |
| C_TEST_CLEANUP.1–3 | The two approved mutable-prose test modules are absent; `tests/documentation` contains no remaining test module and no replacement wording assertions were added. The stale generated-release-assets assertion was also removed because those assets are intentionally release-built rather than source-owned. |
| VAL_FULL.1, VAL_GATES.1 | The definitive full-suite and branch-gate results above are green and their structured cache records were inspected. |
| VAL_BEHAVIOR.1 | The complete suite, focused public-contract tests, source inspection, live startup, and actual presented tool calls cover every behavior named in Planning. |
| VAL_DEFERRED.1, VAL_REPORT.1 | Deferred quality-gate findings are recorded below and this report is published. |

## Design and Approved Strategy Alignment

- The supported catalog is derived at runtime and contains only the identity and output
  model data required for catalog alignment; no static public 50-tool catalog exists.
- Tool activation remains settings-dependent, with tokenless startup preserving the
  credential-free subset and without constructing external GitHub work.
- Presentation remains declarative. Python owns generic scalar, ordered collection,
  enum, failure-envelope, and byte-budget mechanics; `presentation.yaml` owns field
  selection, wording, ordering, and limits.
- The final limiter is universal and capped at 8,000 UTF-8 bytes while preserving one
  complete cache URI whenever publication succeeds.
- Complete structured DTOs remain authoritative in cache. Chat output is a bounded
  projection and does not mutate or prune cached data.
- The approved clean breaks are complete: canonical `ValidationIssue` records remain
  structured, pytest duration is numeric, and the seven duplicate presentation fields
  have no aliases or dual writes.
- Generic error envelopes may omit success-output collections. Present malformed
  collections and all missing collections on successful outputs still fail fast through
  the shared renderer.
- No tool-name, output-DTO-type, validation-record-type, gate-name, sorting, or filtering
  branch was introduced in presentation code.

## Validation Feedback Resolved

An earlier, invalidated Validation run exposed stale transition-presentation assertions,
an incomplete cache-failure test configuration, an obsolete generated-assets assertion,
and a generic error-envelope collection failure. Implementation was reopened; the
fixtures and assertions were aligned and the presenter behavior was corrected.

A first correction used output-DTO type inspection. Deliverable mapping then identified
that this contradicted C_COMPOSE.5. Implementation was reopened again and replaced it
with the final type-agnostic success/failure-contract behavior. The definitive evidence
above was collected only after that correction.

## Failures, Caveats, and Residual Risk

- Definitive failures: none.
- Two workspace tests were skipped by the suite. Their identities are not part of the
  compact test DTO; the run reported no error or failure associated with them.
- The server-start demonstration proves configuration/catalog acceptance and live
  presentation composition, but not client-specific rendering in every external agent
  harness. The 8,000-byte server ceiling is the cross-harness safety contract.
- [Research](research.md) still contains two source links to the documentation-test
  modules intentionally deleted in Cycle 8. Documentation must convert those historical
  source references to non-link path references or otherwise remove the now-broken
  links.

## Deferred Work for Ready and Coordination Triage

Structured quality-gate findings remain deliberately outside issue #456. The current
`GateResultDTO.details` stays cache-only, so the compact response identifies a failing
gate but cannot yet show a bounded set of concrete diagnostics without parsing
gate-specific text.

Post-merge coordination should triage a dedicated issue to investigate a generic
`GateFindingDTO` (or equivalent) with gate, file, location, diagnostic code, and
concise message; decide its ownership in the quality DTO; add a configurable inline
finding limit; and preserve complete raw checker output in cache without gate-specific
presenter branches.

## Documentation-Phase Follow-Up

- Complete DOC_PRESENTATION.1, DOC_TOOLS.1, DOC_AGENT.1, and DOC_DEFERRED.1 from
  [Planning](planning.md).
- Repair the two deleted-test links noted above.
- Describe current behavior only; do not add historical implementation trace prose.

## Independent Review Boundary

This report records producer-side Validation evidence. Independent QA must read the
direct artifacts and evidence and alone determines GO/NOGO for progression.

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-22 | Agent | Definitive branch-wide Validation evidence and deferred-work transfer |

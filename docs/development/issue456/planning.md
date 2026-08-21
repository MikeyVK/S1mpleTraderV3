<!-- docs/development/issue456/planning.md -->
<!-- template=planning version=130ac5ea created=2026-08-20T20:26Z updated=2026-08-20 -->
# Compact Actionable Tool Summaries — Planning

**Status:** PRELIMINARY  
**Version:** 1.2  
**Last Updated:** 2026-08-21

---

## Purpose

Convert the approved presentation design into dependency-ordered implementation cycles with proportional, durable evidence.

## Scope

**In Scope:** Presentation configuration and exact registered-tool/config-key alignment, generic inline-sequence and collection rendering, final UTF-8 byte limiting, TextPresenter integration, field-level optimization of all 50 registered tool templates, structural matrix evidence, representative behavioral tests, and deletion of the two obsolete documentation-test modules.

**Out of Scope:** Structured quality-gate findings, DTO or cache-payload changes, tool-specific renderers, sorting/filtering, production documentation edits before the Documentation phase, and workspace-wide verification before Validation.

## Prerequisites

1. [Approved Research v1.3](research.md)
2. [Approved Design v1.2](design.md)
3. [Approved 50-tool field audit v1.1](tool-presentation-field-audit.md)
4. [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)
5. [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)

---

## Summary

Five coherent cycles establish validated configuration with exact key parity, generic collection presentation, UTF-8-safe limiting, end-to-end rollout of the approved targets for all 50 tool templates, and mechanical removal of obsolete documentation tests. Cycles 1–4 change durable behavior and use RED → GREEN → REFACTOR. Cycle 5 is test maintenance and deliberately creates no artificial RED test.

The cycles preserve the Approved Strategy: complete DTOs and resources remain unchanged, presentation stays configuration-driven, registered tools and presentation keys match exactly, every field is intentionally inline or cache-only, DTO order is retained, and the only universal text limit is 8,000 UTF-8 bytes.

## Dependency Order

| Cycle | Depends on | Unlocks |
|---|---|---|
| 1. Presentation configuration and alignment | Approved Design | Typed policy consumed by all later cycles |
| 2. Generic sequence and collection presentation | Cycle 1 | Reusable bounded projection |
| 3. UTF-8 text budget enforcement | Cycles 1–2 | Safe final-response boundary |
| 4. TextPresenter integration and tool rollout | Cycles 1–3 | Complete feature behavior |
| 5. Obsolete documentation-test removal | Cycle 4 | Stable branch baseline for Validation |

Do not begin a cycle while a dependency has unresolved focused tests, file-scoped gates, or stop conditions.

---

## Cycle 1 — Presentation Configuration and Alignment

**Mode:** Durable behavior change; RED → GREEN → REFACTOR required.

**Goal:** Establish frozen configuration contracts and fail-fast alignment for exact registered-tool/config-key parity, recursive collections, inline scalar sequences, item limits, omission wording, truncation wording, and the global byte ceiling.

### Scope and Seams

- [Presentation configuration schema](../../../mcp_server/config/schemas/presentation_config.py)
- [Presentation alignment validator](../../../mcp_server/presenters/text_presenter.py)
- [Presentation configuration](../../../.pgmcp/config/presentation.yaml)
- Existing presenter tests plus a focused presentation-config test module

No rendering or TextPresenter orchestration changes belong in this cycle.

### Deliverables

| ID | Deliverable |
|---|---|
| C_CONFIG.1 | Frozen schema represents the Design 3.2 configuration contracts and their local invariants. |
| C_CONFIG.2 | Startup alignment recursively validates collection fields, element types, placeholders, duplicate siblings, inline sequences, max_items usage, and mandatory-tail budget. |
| C_CONFIG.5 | Startup alignment enforces deterministic exact parity between registered public tool names and `presentation.yaml` keys and rejects duplicate registered names. |
| C_CONFIG.3 | Global presentation.yaml values supply the 8,000-byte ceiling and all omission/truncation wording without per-tool rollout yet. |
| C_CONFIG.4 | Durable schema/alignment tests cover accepted flat, scalar-sequence, and nested declarations plus every designed rejection category. |

### Test and Gate Evidence

- RED: focused tests fail because the new schema/alignment behavior is absent, including missing-key, unknown-key, and duplicate-registration cases.
- GREEN: run the new presentation-config tests and the alignment subset in [test_presenter.py](../../../tests/mcp_server/unit/test_presenter.py).
- REFACTOR: rerun those focused tests and file-scoped gates for changed Python production and test files.
- Do not run the full suite.

### Exit and Stop Conditions

Exit only when valid configuration loads, registered public tools and presentation keys match exactly, each invalid contract fails with actionable tool/path context, and no tool-name dispatch was introduced. Stop if the solution moves registry ownership into configuration or cannot express the approved invariants without changing the Design or DTO boundary.

---

## Cycle 2 — Generic Sequence and Collection Presentation

**Mode:** Durable behavior change; RED → GREEN → REFACTOR required.

**Goal:** Provide generic ordered rendering for bounded flat scalar sequences and recursively configured collections.

### Scope and Seams

- New cohesive value-formatting seam under mcp_server/presenters
- New CollectionTextRenderer seam under mcp_server/presenters
- Focused public-contract tests under tests/mcp_server/unit/presenters
- Configuration models from Cycle 1

TextPresenter orchestration and the thirteen production tool declarations remain excluded until Cycle 4.

### Deliverables

| ID | Deliverable |
|---|---|
| C_COLLECTION.1 | SafeNoneFormatter is a standalone generic value boundary that renders flat scalar sequences with configured separator, omission text, and max_items. |
| C_COLLECTION.2 | CollectionTextRenderer renders scalar lists, model lists, sibling lists, and nested lists depth-first in DTO order. |
| C_COLLECTION.3 | Empty, exact-limit, over-limit, None, multibyte, and nested data have durable public-contract coverage. |
| C_COLLECTION.4 | Neither formatter nor renderer inspects tool names, sorts, filters, or formats model-valued lists as Python repr. |
| C_COLLECTION.5 | Missing fields, non-list runtime values, and wrongly typed collection items fail with ConfigError containing usable field/path context. |

### Test and Gate Evidence

- RED: focused public-contract tests fail for missing inline-sequence and recursive collection behavior, including missing fields, non-list runtime values, and wrongly typed collection items.
- GREEN: run only the focused collection-presentation test module(s), proving valid rendering and ConfigError with field/path context for all three malformed runtime-shape classes.
- REFACTOR: rerun focused tests and file-scoped gates for formatter, renderer, and their tests.
- Tests call public formatting/rendering methods only.

### Exit and Stop Conditions

Exit only when order, limits, omission counts, nested association, and label formatting are deterministic, and every unexpected runtime collection shape raises ConfigError with usable field/path context. Stop if implementation silently skips malformed data or requires dotted paths, tool-specific branches, DTO changes, or a generic query language.

---

## Cycle 3 — UTF-8 Text Budget Enforcement

**Mode:** Durable behavior change; RED → GREEN → REFACTOR required.

**Goal:** Enforce the configured final text ceiling while retaining readable Markdown, a correct truncation notice, and the complete cache URI whenever available.

### Scope and Seams

- New TextBudgetLimiter seam under mcp_server/presenters
- Focused public-contract tests under tests/mcp_server/unit/presenters
- Global budget and notice configuration from Cycle 1

TextPresenter wiring remains excluded until Cycle 4.

### Deliverables

| ID | Deliverable |
|---|---|
| C_BUDGET.1 | TextBudgetLimiter returns under-budget content unchanged and caps overflow at max_text_response_bytes. |
| C_BUDGET.2 | Overflow reserves the complete cache reference and correct notice before retaining body content. |
| C_BUDGET.3 | Truncation prefers complete blocks/lines, preserves UTF-8 code points, and closes an intersected fenced block. |
| C_BUDGET.4 | Cache-unavailable truncation is bounded without claiming complete cached detail. |

### Test and Gate Evidence

- RED: focused limiter tests fail at under, exact, and over-budget boundaries, including multibyte and fenced Markdown.
- GREEN: run only the focused limiter test module.
- REFACTOR: rerun limiter tests and file-scoped gates for limiter and tests.
- Include a fixed 32-character run-id URI in mandatory-tail cases.

### Exit and Stop Conditions

The hard stop-go invariant is len(result.encode("utf-8")) <= configured budget for every case. Stop if any path can corrupt UTF-8, exceed budget, lose an available cache URI, or misrepresent cache failure.

---

## Cycle 4 — TextPresenter Integration and Tool Rollout

**Mode:** Durable behavior change; RED → GREEN → REFACTOR required.

**Goal:** Compose the generic services in TextPresenter and atomically implement the approved field-level presentation target for all 50 registered tools without changing DTO or resource contracts.

### Scope and Seams

- [TextPresenter](../../../mcp_server/presenters/text_presenter.py)
- [ResponsePresenter](../../../mcp_server/presenters/response_presenter.py) external contract remains unchanged
- [Bootstrap composition](../../../mcp_server/bootstrap.py) only if concrete dependency assembly requires it
- [Presentation configuration](../../../.pgmcp/config/presentation.yaml)
- [Approved 50-tool field audit](tool-presentation-field-audit.md)
- [Presenter unit tests](../../../tests/mcp_server/unit/test_presenter.py)
- [Server unit tests](../../../tests/mcp_server/unit/test_server.py)
- [Pipeline integration tests](../../../tests/mcp_server/integration/test_pipeline_e2e.py)

### Deliverables

| ID | Deliverable |
|---|---|
| C_INTEGRATION.1 | TextPresenter assembles scalar text, configured collections, instructions, notes, sanitized fallback, reserved cache reference, and final limit in the approved order. |
| C_INTEGRATION.2 | All thirteen collection tools have valid max_items and collection declarations within the complete 50-tool configuration. |
| C_INTEGRATION.3 | get_work_context, get_issue, get_pr, and safe_edit_file expose the approved scalar additions; get_issue labels are bounded to ten. |
| C_INTEGRATION.4 | run_quality_gates and validate_template use outcome-neutral wording. |
| C_INTEGRATION.5 | Representative run_tests and run_quality_gates output excludes traceback, stderr, and verbose gate details while exposing bounded actionable rows. |
| C_INTEGRATION.6 | Server/presenter evidence proves the cached DTO stays complete and separately embedded validation resources remain outside the text budget. |
| C_INTEGRATION.7 | A tool whose approved compact template remains unchanged is byte-for-byte stable while under budget and changes only through the universal limiter when over budget. |
| C_INTEGRATION.8 | Every one of the 50 registered tool templates is implemented or explicitly confirmed against the approved field-audit inline/cache-only target. |
| C_INTEGRATION.9 | Structural evidence proves every tool-specific DTO field is classified inline or cache-only and every cache-only choice matches an approved rationale category. |
| C_INTEGRATION.10 | Bundled `presentation.yaml` has exact bidirectional parity with the runtime public-tool registry; missing, obsolete, or duplicate identities fail startup. |

### Test and Gate Evidence

- RED: adapt durable presenter/integration tests for block order, labels, nested plan, collection matrix, scalar expansions, semantic outcomes, verbose-field exclusion, byte cap, cache preservation, registered/config parity, and under/over-budget behavior of a template intentionally retained by the approved audit.
- GREEN: run [test_presenter.py](../../../tests/mcp_server/unit/test_presenter.py), the affected server test scope, and [test_pipeline_e2e.py](../../../tests/mcp_server/integration/test_pipeline_e2e.py), including the unchanged-tool under/over-budget compatibility case.
- REFACTOR: rerun affected tests and file-scoped gates for every changed Python source and test file.
- Use structural matrices for all 50 field targets and for the thirteen collection declarations; do not create 50 wording snapshots.

### Exit and Stop Conditions

Exit only when startup alignment accepts exact 50-tool parity, every field-audit row is closed, representative output is actionable and bounded, cache publication is unchanged, one intentionally retained compact template is byte-for-byte stable below the ceiling and limiter-only different above it, and source inspection finds no tool-name dispatch. Stop if any field target lacks an inline/cache-only decision or integration requires DTO, cache, transport, or Approved Strategy changes.

---

## Cycle 5 — Obsolete Documentation-Test Removal

**Mode:** Mechanical test maintenance; no artificial RED.

**Goal:** Delete the two approved brittle documentation-test modules without replacing them with mutable prose assertions.

### Scope and Seams

- tests/documentation/test_c4_doc_alignment.py
- tests/documentation/test_agent_instruction_search_contract.py

No production, configuration, agent-instruction, or active documentation content changes belong in this cycle.

### Deliverables

| ID | Deliverable |
|---|---|
| C_TEST_CLEANUP.1 | C4 documentation alignment test module is absent. |
| C_TEST_CLEANUP.2 | Agent-instruction search contract test module is absent. |
| C_TEST_CLEANUP.3 | All 62 collected cases disappear without replacement prose snapshots. |

### Test and Gate Evidence

- Record the planned no-RED rationale in the cycle hand-over.
- Verify both exact paths are absent and tests/documentation contains no remaining test module.
- Do not run unrelated tests merely to accompany deletion.
- Validation owns the workspace-wide run and final collected-count evidence.

### Exit and Stop Conditions

Stop if either file contains behavior coverage beyond mutable documentation/instruction text; otherwise exit on exact deletion and absence of replacement tests.

---

## Documentation-Phase Deliverables

| ID | Deliverable |
|---|---|
| DOC_PRESENTATION.1 | Update presentation architecture for declarative collections, inline sequences, final byte limiting, and cache authority. |
| DOC_TOOLS.1 | Correct the active discovery, project, GitHub, quality, scaffolding, and tools-overview claims affected by richer inline summaries. |
| DOC_AGENT.1 | Review agent cache guidance and change it only where it still mandates a resource read for information now guaranteed inline. |
| DOC_DEFERRED.1 | Preserve the structured quality-gate finding as deferred work, not current behavior. |

Documentation work must remain a current-state description and must not create historical trace prose.

## Validation-Phase Deliverables

| ID | Deliverable |
|---|---|
| VAL_FOCUSED.1 | Reconfirm focused presenter, server, pipeline, config, formatter, renderer, and limiter tests after final implementation changes. |
| VAL_FULL.1 | Run one workspace-wide test suite and record exact totals. |
| VAL_GATES.1 | Run branch-wide quality gates once and inspect the cached structured result. |
| VAL_BEHAVIOR.1 | Record evidence for 8,000-byte enforcement, cache-URI retention, order/limits, nested plan, labels, semantic outcomes, exact 50-tool parity, full field-audit closure, retained-template compatibility, and unchanged cached DTOs. |
| VAL_DEFERRED.1 | Carry the structured quality-gate findings gap into validation.md for Ready/PR triage. |
| VAL_REPORT.1 | Publish the validation report with failures, residual risks, and deferred work. |

Do not repeat the workspace-wide suite or branch-wide gates unless a later change invalidates their evidence.

## Deferred Work

Structured GateFindingDTO research remains explicitly outside issue #456. Implementation must not parse gate-specific details or change output DTOs. Validation records the finding; Ready includes it in the PR body for post-merge coordination triage.

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Configuration and renderer evolve out of step | Cycle 1 establishes fail-fast field and exact key alignment; Cycle 4 validates the complete 50-tool matrix. |
| Full optimization turns into indiscriminate DTO dumping | The approved audit requires an explicit actionability decision and cache-only rationale for every field under the shared budget. |
| Text limiting corrupts Markdown or loses the cache reference | Cycle 3 isolates the limiter and treats URI retention as blocking. |
| Implementation recreates per-tool branches | Cycle 4 requires configuration matrix evidence and source inspection. |
| Test scope expands into prose snapshots | Capability-oriented tests plus the explicit Cycle 5 deletion boundary. |
| Quality-gate output remains less actionable than test failures | Preserve it as deferred work rather than widening the current DTO boundary. |

## Milestones

- M1: Configuration and recursive projection contracts are executable.
- M2: Final text budgeting is independently proven.
- M3: All approved tools use the generic pipeline.
- M4: Obsolete documentation tests are removed.
- M5: Validation owns one workspace-wide test run and branch-wide gate run.

## Related Documentation

- [Research](research.md)
- [Design](design.md)
- [Presentation Architecture](../../reference/presentation_architecture.md)
- [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)
- [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-20 | Agent | Initial five-cycle implementation, documentation, and validation plan |
| 1.1 | 2026-08-20 | Agent | Add runtime-shape and unchanged-tool compatibility obligations; restore preliminary review status |
| 1.2 | 2026-08-21 | Agent | Add exact registration/config parity and full 50-tool template optimization to Cycles 1 and 4 |

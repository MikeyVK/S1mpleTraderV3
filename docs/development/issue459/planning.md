<!-- docs\development\issue459\planning.md -->
<!-- template=planning version=130ac5ea created=2026-08-22T08:12Z updated= -->
# Structured Quality-Gate Findings Implementation Plan

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-08-22

---

## Purpose

Translate the approved finding contract into two dependency-ordered, behavior-driven implementation cycles.

## Scope

**In Scope:**
GateFindingDTO and additive GateResultDTO.findings; structural mapping in RunQualityGatesTool; run_quality_gates nested presentation configuration; durable focused tests; and Validation-owned workspace evidence.

**Out of Scope:**
QAManager or ViolationParser behavior changes; prose parsing; new limit configuration; sorting/deduplication; unrelated QA helper cleanup; active reference-document updates before Documentation.

## Prerequisites

Read these first:
1. Approved Research strategy in research.md
2. Approved interface, control-flow, compatibility, and test contracts in design.md
3. Existing generic nested collection renderer, startup alignment validator, resource cache, and 8,000-byte limiter
---

## Summary

Add lossless structured findings to the public quality-gate DTO graph, then expose a bounded nested inline projection using the existing generic presenter. Preserve QA normalization ownership, cache completeness, input compatibility, gate summaries, verbose details, ordering, and failure envelopes.

---

## Dependencies

- Cycle 2 depends on the public DTO graph produced by Cycle 1
- Validation depends on both implementation cycles and their focused evidence
- Documentation remains a later workflow phase and does not block Validation behavior evidence

---

## TDD Cycles


### Cycle 1: C1 — Structured finding transport

**Goal:** Introduce the frozen GateFindingDTO, add GateResultDTO.findings with an empty default, and structurally map every ordered QAManager issue in RunQualityGatesTool without changing upstream normalization. Production seams: mcp_server/schemas/tool_outputs.py and mcp_server/tools/quality_tools.py. Test seam: tests/mcp_server/unit/tools/test_quality_tools.py. Exclude presentation.yaml, presenter internals, manager/parser changes, and documentation.

**Tests:**
- RED: adapt public execute-path tests so a fully populated manager issue using canonical keys file/line/col/rule/message/severity/fixable/details must map to the exact GateFindingDTO fields and enclosing gate name.
- RED: add message-only operational finding coverage, preserved gate/finding ordering, empty findings compatibility, retained gate details, and fail-fast behavior for a missing required message.
- GREEN: implement only the frozen DTO and structural mapping required to satisfy those tests.
- REFACTOR: remove duplication in test fixtures or local mapping expression only when clarity improves; do not introduce a generic mapper or alter manager contracts.
- Focused evidence: run tests/mcp_server/unit/tools/test_quality_tools.py and file-scoped quality gates for the two production files and changed test file.

**Success Criteria:**
- C1-D1: GateFindingDTO is frozen, forbids extras, serializes every approved field, and GateResultDTO findings defaults independently to an empty list.
- C1-D2: RunQualityGatesTool preserves every manager issue and source order in the nested public DTO graph.
- C1-D3: Mapping is structural only: col becomes column, rule becomes code, the enclosing name becomes gate, optional fields become None/defaults, and no prose is parsed.
- C1-D4: A missing message is rejected rather than replaced with invented presentation text.
- C1-D5: Existing tool inputs, gate summary fields, verbose gate details, resource behavior, and top-level failure DTOs remain unchanged.
- STOP: reopen Design if actual manager records cannot satisfy the required message contract or if lossless mapping requires changes to QAManager/ViolationParser.



### Cycle 2: C2 — Bounded declarative presentation

**Goal:** Configure findings as a nested child of gate results and prove the real generic presentation path is actionable, bounded, startup-validated, cache-lossless, and compatible. Production seam: .pgmcp/config/presentation.yaml only; existing presenter/config code must remain unchanged unless a demonstrated Design contradiction stops the cycle. Test seams: tests/mcp_server/unit/config/test_tool_presentation_rollout.py and, only if needed for real-config alignment evidence, tests/mcp_server/unit/config/test_presentation_config.py.

**Tests:**
- RED: update the approved presentation mechanics matrix to require the findings child collection and its GateFindingDTO placeholders.
- RED: add public TextPresenter coverage using the real run_quality_gates config for nested actionable findings, source order, per-gate ten-item omission, absent optional fields, empty findings compatibility, raw-details exclusion, complete model_dump evidence, and existing failure-envelope behavior.
- RED: require real-config startup alignment to traverse gates[].findings[] and accept all configured placeholders; rely on existing negative generic alignment tests rather than duplicating them.
- GREEN: add only the declarative child collection and concise template in presentation.yaml.
- REFACTOR: consolidate representative DTO fixtures if useful; do not snapshot full wording or change generic renderer/limiter behavior.
- Focused evidence: run the changed presentation configuration tests and file-scoped quality gates for presentation.yaml and changed tests.

**Success Criteria:**
- C2-D1: Findings render beneath their owning gate through the existing generic nested collection mechanism.
- C2-D2: max_items=10 limits findings per gate with the generic omission notice; the global 8,000-byte limiter remains the final total bound.
- C2-D3: Complete findings and details remain in the structured DTO graph used for caching even when inline output omits findings.
- C2-D4: Details are absent from normal inline output; missing optional fields use the configured generic none value.
- C2-D5: Gates with no findings and top-level failure envelopes preserve existing presentation behavior.
- C2-D6: The real presentation config passes existing startup DTO-path and placeholder alignment validation without new validator code.
- STOP: reopen Design if generic nesting cannot express the approved projection, if bounds require new schema, or if startup alignment cannot validate the child DTO without presenter-specific logic.

**Dependencies:** C1 — Structured finding transport

---

## Risks & Mitigation

- **Risk:** Historical tests use noncanonical issue keys column/code while QAManager emits col/rule.
  - **Mitigation:** Base new public mapping evidence on QAManager and ViolationParser source contracts; adapt only tests whose fixture claims to represent manager output.
- **Risk:** A concise template may accidentally inline verbose diagnostic details.
  - **Mitigation:** Exclude details from configured placeholders and assert both inline absence and structured DTO retention.
- **Risk:** Nested limits could be mistaken for a global finding-count guarantee.
  - **Mitigation:** Test and document the actual approved semantics: max_items per nested collection and 8,000 bytes globally.
- **Risk:** Tests could become wording snapshots and repeat issue 399's documentation-test ballast.
  - **Mitigation:** Assert structural mechanics, representative fields, omission behavior, and compatibility rather than exact complete text.

---

## Milestones

- M1: Structured finding DTO graph and public execute-path mapping pass focused tests and gates.
- M2: Declarative nested projection passes real-config presentation and alignment evidence.
- M3: Validation completes one full workspace test run and branch-wide quality gates with cached evidence inspected.

## Related Documentation
- **[research.md][related-1]**
- **[design.md][related-2]**
- **[../issue456/design.md][related-3]**
- **[../../reference/presentation_architecture.md][related-4]**
- **[../../reference/tools/quality.md][related-5]**

<!-- Link definitions -->

[related-1]: research.md
[related-2]: design.md
[related-3]: ../issue456/design.md
[related-4]: ../../reference/presentation_architecture.md
[related-5]: ../../reference/tools/quality.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-22 | Agent | Initial draft |
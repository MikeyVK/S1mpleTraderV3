<!-- docs\development\issue459\research.md -->
<!-- template=research version=8b7bb3ab created=2026-08-22T07:57Z updated= -->
# Structured Quality-Gate Findings Research

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-08-22

---

## Purpose

Establish the evidence and approved strategy boundary for issue #459 without designing implementation details or sequencing work.

## Scope

**In Scope:**
Quality-gate violation normalization, QAManager result shapes, RunQualityGatesTool mapping, GateResultDTO and RunQualityGatesOutput, declarative presentation of gate findings, resource-cache completeness, durable tests, and active quality/presentation documentation.

**Out of Scope:**
Checker command changes, new parsing strategies, cleanup of runtime-unused compact/summary helpers, redesign of raw verbose output, changes to unrelated tools, scaffolding templates, agent instructions, workflow enforcement, and a second generic total-item policy beyond the existing byte ceiling.

## Prerequisites

Read these first:
1. Issue #456 approved presentation and cache boundary
2. docs/coding_standards/ARCHITECTURE_PRINCIPLES.md sections 2–4, 9–11, 14–16
3. docs/coding_standards/DOCUMENTATION_STANDARD.md phase ownership and traceability rules
---

## Problem Statement

`RunQualityGatesTool` discards the already structured gate issues produced by `QAManager` and exposes only an opaque `details` string in `GateResultDTO`. The generic presenter therefore cannot show bounded actionable diagnostics without parsing prose, while the public resource DTO omits structured findings.

## Research Goals

- Locate where checker-specific output becomes universal structured data and where that structure is lost
- Define ownership and compatibility strategy for public quality-gate findings
- Establish bounded inline ordering and cache-preservation semantics
- Identify the complete code, configuration, test, documentation, agent, template, enforcement, and consumer blast radius

---

## Background

Issue #456 delivered a generic configuration-driven collection renderer, exact startup validation of presentation fields, and a final 8,000 UTF-8-byte TextPresenter ceiling. It intentionally kept GateResultDTO.details cache-only and deferred structured quality-gate diagnostics because ownership and compatibility required a separate decision.

---

## Findings

### Current data flow

1. [ViolationParser](../../../mcp_server/utils/violation_parser.py) maps configured Ruff, mypy, and Pyright text/JSON shapes into a universal `ViolationDTO`.
2. [QAManager.execute_gate](../../../mcp_server/managers/qa_manager.py) already emits ordered structured `issues` for parsed violations and for missing files, configuration errors, non-zero exits without parsed violations, timeouts, and missing executables.
3. [RunQualityGatesTool](../../../mcp_server/tools/quality_tools.py) discards every `issues` collection while mapping manager results to the public DTO.
4. [GateResultDTO](../../../mcp_server/schemas/tool_outputs.py) exposes only gate status, score, and opaque `details`; [presentation.yaml](../../../.pgmcp/config/presentation.yaml) renders only gate summaries.
5. Verbose `details` already remains cache-only and can retain complete checker/process text. Non-verbose failures emit a note suggesting a verbose rerun.

The primary defect is therefore a public-boundary projection loss, not missing checker normalization.

### Representative source shapes

| Origin | Current universal fields |
|---|---|
| JSON parsers (Ruff/Pyright) | message, file, line, col, rule, severity, fixable |
| Text parsers (format/mypy) | message, optional file/line/col/rule/severity, fixable |
| Execution fallback | concise message plus captured diagnostic details |
| Timeout/tool/config/file failures | concise message with optional contextual data |
| Skipped/passing gate | empty issues collection |

### Strategy options

| Option | Cost and risk | Consumer impact | Disposition |
|---|---|---|---|
| Parse `details` in TextPresenter | Low initial code, high ongoing coupling and false parsing risk | Tool/gate-specific presenter behavior | Rejected |
| Migrate all QAManager internals to new Pydantic result graphs | High blast radius across baseline, logs, validators, and legacy helpers | Cleanest theoretical model but unnecessary compatibility risk | Rejected by YAGNI |
| Add a public finding DTO and map existing structured issues at the tool boundary | Small, explicit boundary change; preserves current normalization | Additive cached field and richer bounded inline output | Approved |

### Blast radius

| Surface | Expected impact |
|---|---|
| Production DTO/tool | Add frozen serializable finding records and preserve ordered structured issues in each gate result |
| Manager/parser | Remain normalization owners; no prose parsing and no checker-specific presentation behavior |
| Configuration/presenter | Add a nested finding collection to `run_quality_gates`; reuse generic rendering, per-tool item limit, omission notices, and final byte ceiling |
| Tests | Public tool DTO mapping, representative shapes, order, bounded presentation, failure envelopes, cache serialization, and retained opaque details |
| Documentation | Quality tool reference and presentation architecture; broader tool index only if its claims require correction |
| Agent instructions/templates/enforcement | Reviewed and unchanged: no instruction, scaffold, phase, or enforcement contract changes are required |
| Consumers | Existing DTO fields and inputs remain; cached JSON gains an additive nested collection and inline failure text gains bounded findings |

### Constraints

- Presentation must remain generic and configuration-driven.
- Findings remain in parser order within configured gate order; no sorting or cross-gate deduplication.
- Existing `details` semantics remain cache-only and verbose-controlled.
- The existing item limit bounds findings per gate; the 8,000-byte TextPresenter ceiling is the total inline bound.
- Full structured findings remain cached even when inline collections or final text are truncated.
- Tests exercise public behavior and durable contracts, not exact complete wording.

## Open Questions

- ❓ Design must select exact frozen DTO field names and optionality while retaining every currently useful structured value.
- ❓ Design must specify the nested presentation template and omission behavior without introducing a second total-count policy.
- ❓ Design must identify the narrowest representative failure shapes needed for durable coverage.


---

## Approved Strategy

Human-approved on 2026-08-22:

1. `QAManager` and `ViolationParser` retain normalization ownership; no checker moves presentation policy into its output.
2. Add a frozen serializable public finding DTO and an additive `GateResultDTO.findings` collection with an empty default.
3. Preserve all existing public fields, inputs, verbose `details`, cache URI behavior, and failure envelopes; no clean break, alias, or dual-write period.
4. The tool performs only structural field conversion from existing issue records and never parses prose.
5. Present findings as a nested declarative collection under each gate through the generic renderer.
6. Preserve configured gate order and parser finding order without sorting or deduplication.
7. Reuse the existing configured item limit as the per-gate finding limit and the universal 8,000-byte ceiling as the total inline limit.
8. Cache all structured findings; retain existing verbose checker/process evidence in cache-only `details`.
9. Include message-only operational failures in the same finding contract.
10. Do not opportunistically remove legacy compact/summary helpers or broaden configuration abstractions.

---

## Expected Results

- A normal failing quality-gate call exposes concrete actionable findings inline without a resource round trip when they fit.
- Every public finding is frozen, serializable, ordered, and available in the complete cached DTO.
- Bounded inline output shows configured omissions and never exposes raw verbose details.
- Verbose checker/process text remains cache-only and existing consumers retain all prior fields.
- Startup rejects any invalid finding presentation field or nested template.
- Representative checker and operational failure shapes pass durable public-contract tests.
- Focused tests, branch-wide quality gates, and the workspace validation suite pass.

## Related Documentation
- **[Issue 456 research][related-1]**
- **[Issue 456 design][related-2]**
- **[Issue 456 validation][related-3]**
- **[Presentation architecture][related-4]**
- **[Quality tools reference][related-5]**

<!-- Link definitions -->

[related-1]: ../issue456/research.md
[related-2]: ../issue456/design.md
[related-3]: ../issue456/validation.md
[related-4]: ../../reference/presentation_architecture.md
[related-5]: ../../reference/tools/quality.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-22 | Agent | Initial draft |

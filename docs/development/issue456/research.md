<!-- docs/development/issue456/research.md -->
<!-- template=research version=8b7bb3ab created=2026-08-20T19:16Z updated=2026-08-20 -->
# Compact Actionable Tool Summaries — Research

**Status:** APPROVED  
**Version:** 1.8  
**Last Updated:** 2026-08-21

---

## Purpose

Establish the evidence, scope, and Approved Strategy for compact, actionable MCP tool text presentations without weakening the resource cache as the complete structured source of truth.

## Scope

**In Scope:**

- Text produced by `TextPresenter` and configured through `.pgmcp/config/presentation.yaml`.
- All 50 supported public tools, every corresponding `presentation.yaml` template, their output DTO shapes, and the settings-dependent active subset.
- A field-level optimization decision for every supported tool template; no template is accepted as unchanged without an explicit actionability rationale.
- The approved structured clean breaks for workflow-state status, SafeEdit validation issues, pytest duration, and duplicate presentation-only DTO fields.
- Bidirectional startup validation between the complete runtime-derived tool catalog and `presentation.yaml` tool keys, while preserving supported token-dependent activation.
- Configuration validation, presentation alignment, unit and integration tests, active tool documentation, and agent-facing cache guidance.
- Cross-harness output constraints relevant to selecting a conservative text-response ceiling.
- Removal of `tests/documentation/test_c4_doc_alignment.py` and `tests/documentation/test_agent_instruction_search_contract.py`, including all 62 collected cases.

**Out of Scope:**

- Tool execution semantics outside the narrowly approved workflow-state status, SafeEdit validation-record, pytest-duration, and duplicate-field clean breaks; resource-cache publication and retention behavior.
- Tool-specific Python rendering branches, tool-specific sorting, or changing authoritative DTO order.
- Inline publication of complete verbose logs, tracebacks, JSON Schemas, diffs, or other deep structured payloads.
- A transport-wide byte guarantee for separately embedded MCP resources.
- Unrelated documentation modernization.

## Prerequisites

1. Issue #399 established the current phase-instruction and ownership baseline.
2. The bounded residual documentation reconciliation requested by issue #456 has been completed on this branch.
3. [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md) governs this Research artifact.

---

## Problem Statement

Current text presentations often expose only an aggregate status line. Routine discovery therefore requires a second resource read even when a small, stable subset of the DTO would answer the immediate question. Richer inline output, however, must not recreate the context pressure and client-side truncation that resource caching was designed to prevent.

## Research Goals

- Audit all 50 public tools and identify the useful inline presentation boundary for each.
- Determine whether one configuration-driven presentation strategy can cover different DTO shapes without tool-specific Python branches.
- Establish the boundary between compact text and the complete cached DTO.
- Select a conservative, reproducible text ceiling across agent harnesses.
- Identify the production, configuration, test, documentation, agent-instruction, template, and consumer blast radius.

---

## Current Architecture and Evidence

| Boundary | Current behavior | Evidence |
|---|---|---|
| Tool result | Tools return frozen Pydantic DTOs. | [tool outputs](../../../mcp_server/schemas/tool_outputs.py), [GitHub models](../../../mcp_server/schemas/github_models.py) |
| Cache | The DTO is published before presentation and remains complete. | [server](../../../mcp_server/server.py), [cache publication schema](../../../mcp_server/schemas/cache_publication.py) |
| Text presentation | `TextPresenter` formats top-level scalar placeholders, notes, next instructions, and the cache URI. Lists and mappings are converted through normal Python string formatting rather than purpose-built Markdown rendering. | [TextPresenter](../../../mcp_server/presenters/text_presenter.py) |
| Configuration | Tool templates are declarative, but the schema has no collection presentation or text-budget concepts. | [presentation config schema](../../../mcp_server/config/schemas/presentation_config.py), [presentation configuration](../../../.pgmcp/config/presentation.yaml) |
| Composite presentation | `ResponsePresenter` combines text with separately embedded validation resources. | [ResponsePresenter](../../../mcp_server/presenters/response_presenter.py), [validation resource presenter](../../../mcp_server/presenters/validation_resource_presenter.py) |
| Tool availability | `ServerBootstrapper` assembles 50 tools when a GitHub token is available and 38 when it is absent; tokenless startup is an explicitly tested configuration. | [bootstrap composition](../../../mcp_server/bootstrap.py), [GitHub settings](../../../mcp_server/config/settings.py), [bootstrap tests](../../../tests/mcp_server/unit/server/test_bootstrap.py), [lifecycle tests](../../../tests/mcp_server/integration/mcp_server/test_server_lifecycle.py) |
| Documentation | Active references describe a short text summary plus a cache link, but several summaries are currently less informative than those descriptions imply. | [presentation architecture](../../reference/presentation_architecture.md), [tools overview](../../reference/tools/README.md) |

The complete DTO cache is already the correct deep-inspection mechanism. The missing capability is a bounded text projection, not an alternative data authority.

## Harness Evidence

Published harness behavior is not uniform:

| Harness | Evidence | Relevance |
|---|---|---|
| GitHub Copilot CLI | Tool output above 20 KiB is saved to a temporary file by default; this explicitly includes MCP tools. | A server response below 8,000 UTF-8 bytes remains well below this published threshold. |
| Claude Code | Claude warns above 10,000 MCP-output tokens and documents a configurable 25,000-token default maximum. | Token limits are substantially above the proposed byte ceiling, but token-to-byte ratios are content-dependent. |
| Codex | The project has moved from historical 10 KiB/256-line truncation toward configurable token budgets; current behavior remains client/model/version-sensitive. | The historical 10 KiB boundary makes 8,000 bytes a conservative server-side choice. |
| Antigravity | A local harness investigation supplied during this Research observed a 46,080-byte view/file-spill boundary. No authoritative public contract was found. | Treat as observed supporting evidence, not a stable external guarantee. |
| Gemini CLI | No universal documented MCP text-output ceiling was found. | Reinforces choosing a conservative server-owned budget rather than relying on a client default. |

The selected 8,000-byte ceiling is one safety boundary, not a soft target plus a second hard target. Normal summaries should usually remain far smaller.

## Complete Tool Audit

### Compact scalar templates require explicit reassessment

The following 32 tools have compact scalar templates, but their DTOs contain additional fields that may improve the immediate next decision. Every template therefore requires an explicit field-level decision; retaining compact output is valid only when omitted fields are documented as redundant, caller-supplied, operationally verbose, or deep-inspection-only:

`health_check`, `restart_server`, `transition_cycle`, `force_cycle_transition`,
`initialize_project`, `save_planning_deliverables`,
`update_planning_deliverables`, `git_diff_stat`, `get_parent_branch`,
`check_merge`, `create_branch`, `git_add_or_commit`, `git_restore`,
`git_checkout`, `git_push`, `git_merge`, `git_delete_branch`,
`git_fetch`, `git_pull`, `create_issue`, `update_issue`, `close_issue`,
`submit_pr`, `merge_pr`, `create_label`, `delete_label`, `add_labels`,
`remove_labels`, `create_milestone`, `close_milestone`,
`transition_phase`, and `force_phase_transition`.

The approved [Tool Presentation Field Audit](tool-presentation-field-audit.md) is the binding 50-tool inventory. Optimization maximizes immediate actionability within the shared byte budget rather than indiscriminately copying every DTO field into chat; every cache-only classification is deliberate and justified.

### Declarative collection presentation is useful

| Tool | Inline decision data | Cache-only detail |
|---|---|---|
| `auto_fix` | Gate names and a bounded modified-file list. | Complete file list and DTO. |
| `get_project_plan` | Phases and their tasks, preserving DTO order. | Complete plan DTO. |
| `git_list_branches` | Bounded branch list with current/upstream identity. | Complete branch list. |
| `git_status` | Bounded modified and untracked path lists. | Complete status DTO. |
| `git_stash` | Bounded stash list when the action returns stashes. | Complete stash list. |
| `list_issues` | Number, title, state, labels, and URL for a bounded issue list. | Complete result set. |
| `list_prs` | Number, title, state, refs, and URL for a bounded PR list. | Complete result set. |
| `list_labels` | Bounded label list. | Complete label set. |
| `list_milestones` | Number, title, and state for a bounded milestone list. | Complete milestone set. |
| `scaffold_artifact` | Bounded created-file list. | Validation schema and complete scaffolding DTO. |
| `run_quality_gates` | Scope, overall result, and bounded gate status/score list. | Verbose stdout/stderr and full gate details. |
| `run_tests` | Counts plus bounded failure identifiers, locations, and short reasons. | Tracebacks, stderr, and complete verbose evidence. |
| `validate_template` | Result/count plus bounded severity/message findings. | Complete finding set. |

`get_project_plan` is the only currently audited response that requires nested collection data to remain actionable. Research requires a generic declarative capability for that shape; Design owns the exact configuration contract.

### Scalar template expansion is useful

| Tool | Required expansion | Reason |
|---|---|---|
| `get_work_context` | Phase instructions and hand-over template. | These are core outputs of the context call. The largest current phase-instruction plus hand-over combination is 2,911 UTF-8 bytes and fits comfortably within the selected ceiling. |
| `get_issue` | URL, labels, and body. | Routine issue inspection should not require a second call when the body fits. |
| `get_pr` | State and body. | Routine PR inspection should expose its actionable content directly when it fits. |
| `safe_edit_file` | Validation findings when present. | Interactive writes can succeed while retaining warnings that must remain visible. |

These are ordinary scalar template expansions. They do not justify special rendering code. The final text limiter handles exceptional length.

### Deliberate resource-oriented exception

`scaffold_schema` returns a nested JSON Schema whose semantics cannot be represented reliably by a bounded item list. Its compact text should identify the artifact type and direct the consumer to the complete cached schema. Adding a generic JSON pretty-printer solely to inline this payload would increase complexity while duplicating the resource authority.

## Documentation Test Cleanup

Implementation must delete these two brittle documentation-test modules and all 62 collected cases:

- [C4 documentation alignment tests](../../../tests/documentation/test_c4_doc_alignment.py)
- [Agent instruction search contract tests](../../../tests/documentation/test_agent_instruction_search_contract.py)

They do not provide meaningful evidence for the changed documentation and must not remain part of the routine verification load.

## Semantic Defects Found

Synthetic DTO presentation through the current `TextPresenter` reproduced two contradictory messages:

- `run_quality_gates` can say “Quality gates passed successfully” while `overall_pass=False`, because execution success and gate success are different concepts.
- `validate_template` can say “Template validation passed: False”.

Both templates must use outcome-neutral completion wording and expose the actual result as data. This is distinct from the four scalar template expansions above.

## Additional Scope Findings

### Conditional runtime registration changes the parity boundary

`ServerBootstrapper` constructs `TextPresenter` and calls `validate_presentation_alignment(text_presenter, core_tools)` at startup, so the existing composition seam is suitable for fail-fast enforcement. The validator currently iterates active tools, silently accepts a missing presentation entry, and never rejects configured keys that identify no supported tool. Schema-valid YAML can therefore omit a supported tool or retain an obsolete key without startup failure.

The active toolset is settings-dependent. `GitHubSettings.token` is optional and defaults to `None`. With a token, bootstrap registers all 50 supported tools. Without one, it registers 38: five issue tools remain available while twelve PR, label, and milestone tools are inactive. Existing bootstrap and lifecycle tests establish both variants as supported. Exact parity between the active subset and one bundled 50-key `presentation.yaml` would consequently reject every supported tokenless deployment.

| Strategy | Benefit | Cost / risk | Decision |
|---|---|---|---|
| Validate against only the active subset and require deployment-specific presentation files | Simple equality for one process configuration. | Fragments the bundled configuration, makes token changes require a matching file change, and duplicates supported-tool knowledge across deployments. | Rejected |
| Require templates for active tools but tolerate every additional key | Tokenless startup succeeds without structural change. | Typos and obsolete inactive-tool templates are no longer fail-fast detectable. | Rejected |
| Always register all 50 tools | One active set matches one presentation file. | Exposes unusable tools, changes supported runtime behavior, and may require unavailable credentials during construction. | Rejected |
| Derive a complete catalog and an active subset from one authoritative runtime registration source | Preserves exact config coverage, tokenless startup, and one source of truth for add/remove operations. | Requires a minimal registration representation that supports both validation and conditional construction. | Approved |

The complete catalog is an in-memory projection of the authoritative composition-root registrations, not a static file or separately maintained list. The same registrations serve only two current consumers: presentation validation needs tool identity and output-model information; runtime activation needs the construction and activation information required to produce the active subset. Design must choose the smallest representation that satisfies those uses. A general capabilities system, descriptive catalog metadata, persistence, documentation metadata, and new public catalog APIs are outside scope.

### Field audit requires complete rollout

The [Tool Presentation Field Audit](tool-presentation-field-audit.md) classifies every tool-specific output field for all 50 tools. It exposes potentially actionable omissions in compact templates, including workflow gate and warning context, initialization results, commit file effects, and issue metadata. A partial rollout limited to thirteen collection tools, four scalar expansions, and two semantic corrections is therefore insufficient.

Every registered tool template is an implementation deliverable. The approved matrix either places each tool-specific field inline through generic presentation mechanisms or records a concrete cache-only rationale. Planning provides implementation and structural evidence for the full matrix without introducing brittle prose snapshots per tool.

## Workflow-State Presentation Evidence and Options

The controlled missing-state probe temporarily removed `.pgmcp/state.json` and called `get_work_context`. The visible response contained empty workflow, issue, phase, role, and parent values with only `confidence=unknown`; the cached success DTO contained `phase_source="unknown"`, `phase_confidence="unknown"`, and generic non-recovery instructions. The state file was restored and normal context returned immediately.

| Option | Benefit | Cost / risk | Decision |
|---|---|---|---|
| Keep empty fields plus confidence | No contract change. | Looks like formatting failure and gives no safe recovery distinction. | Rejected |
| Produce an OperationNote | Conditional text already exists. | Reintroduces a retired presentation path and bypasses the tool/exception DTO authority. | Rejected |
| Put warning text in the tool DTO | Easy to project. | Violates the Presentation Boundary by coupling the tool to human-facing text. | Rejected |
| Add a boolean state-available field | Structured and small. | Cannot distinguish missing, unreadable, and invalid-phase recovery. | Rejected |
| Add a workflow-state enum and structured supporting fields | Keeps the tool presentation-agnostic and enables exact configured messages per condition. | Requires a narrow clean-break DTO contract change and generic enum-driven presentation selection. | Approved |

## DTO Presentation-Debt Evaluation

The completed tool review identified output fields that pre-format human-facing text inside production/tool code. Removal risk differs by whether equivalent structured data already exists.

### Category A — removable structured duplicates

| Field | DTO | Structured replacement | Known direct consumers |
|---|---|---|---|
| `formatted_modified_files` | `AutoFixOutput` | `modified_files[]` plus count | Current presentation template and focused AutoFix tests. |
| `formatted_labels` | `LabelOperationOutput` | `labels[]` | Current add/remove-label templates. |
| `formatted_files_created` | `ScaffoldArtifactOutput` | `files_created[]` | Current template plus two acceptance and two integration assertions. |
| `skipped_gates_warning` | `PhaseTransitionOutput` | `skipped_gates[]` plus count | Current forced-transition behavior/tests. |
| `passing_gates_info` | `PhaseTransitionOutput` | `passing_gates[]` plus count | Current forced-transition behavior/tests. |
| `schema_info` | `ScaffoldArtifactOutput` | `missing_fields[]`, `provided_fields[]`, and `validation_schema` resource | Current scaffold failure template. |
| `invalid_phase_warning` | `GetWorkContextOutput` | Approved `WorkflowStateStatus` plus `valid_phases[]` | Current discovery tests and active discovery reference. |

These fields can be removed in one clean break after presentation templates switch to structured inputs. No supported immediate-decision data is lost. Tests asserting the legacy convenience strings must be adapted or removed in favor of structured observable behavior.

### Category B — replacement required before removal

| Field | Why direct removal is unsafe | Structured direction |
|---|---|---|
| `summary_line` | It contains parsed pytest outcome wording and duration; counts and exit code already cover outcome. | APPROVED: remove it and add `duration_seconds: float | None`; present duration with counts, exit code, coverage, and failures. |
| `SafeEditOutput.issues` | `ValidationService` currently collapses `ValidationIssue` records into one formatted string consumed by SafeEditTool and ArtifactManager. | APPROVED: preserve structured validation issues through the service boundary and expose a frozen issue DTO collection. |

Both Category B refactors are explicitly approved for issue #456. `summary_line` is removed only after numeric duration is preserved; SafeEdit string issues are removed only after structured issue records reach the tool DTO and affected manager consumers. They require separate planning slices before the final template rollout.

### Category C — retained diagnostic text

`error_message`, failure short reasons, raw subprocess output, tracebacks, stderr, and opaque gate details are not convenience presentation fields. They carry diagnostic evidence or exception semantics. Issue #456 may keep them cache-only or project a bounded structured subset, but a blanket text-field deletion is not justified.

### Strategy Options

| Option | Cost | Architecture result | Risk | Status |
|---|---|---|---|---|
| Stop consuming fields but retain every DTO field | Small | Presentation improves, production DTO debt remains. | Dead compatibility fields persist indefinitely. | Viable but not preferred |
| Remove Category A only | Moderate | Eliminates all proven duplicate presentation fields with existing structured equivalents. | Leaves pytest and SafeEdit presentation debt. | Rejected as incomplete |
| Remove Category A and refactor Category B in issue #456 | Larger | Extends structured-data ownership through pytest and validation service boundaries. | Increases implementation and validation blast radius substantially. | Approved |
| Delete all text-like fields | Very large | Superficially strict but conflates diagnostics with presentation. | Loses evidence and breaks exception/error contracts. | Rejected |

Human approval was recorded on 2026-08-21: remove all Category A fields, replace SafeEdit string issues with structured validation issue DTOs, remove `summary_line`, add numeric duration to the test result DTO, and project that duration inline.

## Options Considered

| Option | Benefit | Cost / risk | Decision |
|---|---|---|---|
| Keep count-only text and require resource reads | No production change. | Preserves unnecessary two-step discovery and fails the issue objective. | Rejected |
| Inline complete DTOs | Maximum immediate detail. | Recreates context growth, harness truncation, and duplicated authority. | Rejected |
| Add bespoke renderer logic per tool | Fine-grained output. | Violates configuration ownership, increases drift, and scales poorly. | Rejected |
| Add one bounded declarative projection pipeline | Compact common behavior with per-tool presentation choices in configuration. | Requires a small generic collection capability and robust final text limiting. | Approved |
| Add sorting/filtering semantics | Could prioritize selected records. | Changes authoritative order and expands configuration complexity. | Rejected |
| Add a generic JSON renderer | Could inline `scaffold_schema`. | Adds complexity for one deep-inspection case and duplicates cache data. | Rejected |
| Validate only configured templates encountered while iterating tools | Reuses current behavior. | Missing registered tools and obsolete configuration remain silent. | Rejected |
| Enforce exact complete-catalog/config-key parity at startup and derive the active subset from the same registrations | Makes template coverage complete and drift deterministic without breaking supported tokenless startup. | Requires a minimal runtime registration representation; every supported tool change must update presentation configuration atomically. | Approved |
| Preserve the original partial rollout matrix | Smaller implementation scope. | Ignores the field audit and leaves avoidable second resource reads. | Rejected |
| Optimize all 50 templates against a field-level actionability matrix | Makes the user-facing contract explicit for every tool while retaining cache authority. | Broadens configuration, review, and evidence scope; requires disciplined cache-only rationales. | Approved |

## Approved Strategy

Human approval covers the complete strategy below, including exact complete-catalog/configuration parity, settings-dependent runtime activation, all 50 presentation targets, and the explicit structured DTO clean breaks.

1. Preserve each tool's complete structured result in the untruncated resource cache; inline projection and byte limiting must never reduce cached evidence.
2. Apply one configurable `8,000` UTF-8-byte ceiling to the chat text produced by `TextPresenter`.
3. Use one generic, configuration-driven presentation pipeline. Tools may declare bounded collections and a per-tool item limit in `presentation.yaml`; production code must not branch on tool names.
4. Preserve DTO order. Do not introduce presentation sorting or filtering.
5. Support actionable nested plan data generically; Design will define the minimal configuration interface.
6. Use ordinary templates for `get_work_context`, `get_issue`, `get_pr`, and `safe_edit_file` scalar expansions.
7. Correct the outcome wording for `run_quality_gates` and `validate_template`.
8. Keep tracebacks, stderr, verbose gate logs, full JSON Schemas, diffs, and other deep payloads cache-only.
9. When text exceeds the budget, retain a clear truncation notice and the cache URI within the same budget.
10. The ceiling applies to `TextPresenter` chat text. Separately embedded validation resources remain governed by the existing presentation-resource contract; no transport-wide response-size guarantee is claimed.
11. Preserve tool inputs, cache URI shape, resource publication, and unaffected output contracts. Apply only the explicit clean-break DTO changes in items 17–22, without compatibility aliases, dual writes, or a migration period.
12. Delete both current `tests/documentation` test modules and all 62 collected cases during Implementation.
13. Enforce exact bidirectional startup parity between the complete runtime-derived supported-tool catalog and `presentation.yaml` keys. Derive both that catalog and the settings-dependent active subset from one authoritative composition-root registration source; do not introduce a static catalog file or duplicated tool-name list. Known but inactive templates are valid, while missing supported templates, unknown/obsolete keys, and duplicate registrations are startup errors. Keep the registration/catalog representation limited to information required by presentation validation and runtime construction/activation; broader catalog metadata or capabilities are out of scope.
14. Treat all 50 supported tool templates as implementation scope. Use the field audit as traceability input and produce a complete design target matrix; every tool-specific DTO field must be either intentionally inline or explicitly cache-only with a concrete rationale.
15. Optimize for the immediate next decision within the shared byte and item limits. Full optimization does not override the cache-only policy for verbose logs, tracebacks, schemas, diffs, raw process output, or redundant caller-supplied data.
16. Preserve the generic configuration-driven pipeline and capability-oriented tests. Full-template coverage must not introduce tool-name branches or one exact-wording snapshot per tool.
17. For `get_work_context`, make workflow-state availability explicit through a frozen enum rather than a boolean because presentation must distinguish at least `available`, `missing`, `unreadable`, and `invalid_phase`. The tool emits no human-facing warning or recovery text.
18. Apply a clean break at this DTO boundary: replace the human-facing `invalid_phase_warning` string with the enum plus structured supporting data such as `valid_phases`. `presentation.yaml` owns status-specific warning and recovery text.
19. Preserve `success=true` for a successfully executed context query even when workflow state is unavailable; the enum represents the discovered domain condition. Keep `phase_source` and `phase_confidence` cache-only once the explicit state status is guaranteed inline.
20. Remove the seven Category A presentation-debt fields in one clean break: `formatted_modified_files`, `formatted_labels`, `formatted_files_created`, `skipped_gates_warning`, `passing_gates_info`, `schema_info`, and `invalid_phase_warning`. Their existing structured fields/configuration become the only presentation authority.
21. Replace `SafeEditOutput.issues: str | None` with a frozen structured validation-issue collection carrying message, severity, line, column, and code as available. Preserve structured issues through ValidationService and affected ArtifactManager/SafeEdit consumers; presentation.yaml owns their labels and layout.
22. Remove `RunTestsOutput.summary_line`. Add `duration_seconds: float | None`, parsed without user-facing wording, and present it inline alongside exit code, counts, coverage, and bounded failures. Exceptional outcomes remain represented by structured exit code/count/error data.
23. Do not delete diagnostic evidence fields merely because they contain text. `error_message`, `short_reason`, raw output, tracebacks, stderr, and opaque gate details retain their diagnostic/cache roles unless separately redesigned.

## Blast Radius

| Area | Expected impact |
|---|---|
| Production code | Generic text projection, collection formatting, final UTF-8-safe limiting, and a minimal composition-root registration representation from which complete catalog validation and the active tool subset are derived; plus narrow producer/service changes for structured workflow state, validation issues, and pytest duration. No unrelated execution semantics change. |
| Configuration | Additive presentation schema plus reviewed and optimized `presentation.yaml` declarations for all 50 supported tools. Keys exactly match the complete runtime-derived catalog; settings select an active subset without requiring a second presentation file. |
| DTOs | Approved clean breaks add structured workflow-state status, structured SafeEdit validation issues, and numeric pytest duration; remove `RunTestsOutput.summary_line` and the seven enumerated duplicate presentation fields. All other DTO contracts remain unchanged. |
| Tests | Delete both legacy `tests/documentation` modules and their 62 cases. For the feature itself, use presenter unit tests, complete-catalog/configuration alignment tests for both token and tokenless bootstrap, multibyte and reserved-cache-suffix boundary tests, collection-order/item-limit tests, nested-plan coverage, and a small representative set of tool presentation tests. Avoid one wording/snapshot test per tool. |
| Test quality | Tests must verify durable presentation contracts rather than snapshot every wording detail. Verbose logs remain cache assertions, not large inline snapshots. |
| Documentation | Presentation architecture and relevant tool references for discovery/project/GitHub/quality/scaffolding must reflect the compact-text/cache boundary. |
| Agent instructions | Cache guidance remains valid: agents read resources for complete structured data or verbose logs. Verify wording does not continue to require resource reads for routine summaries that are now inline. |
| Templates / enforcement | Artifact templates are unaffected. Startup presentation alignment validates new declarative fields against catalogued output models and enforces exact parity between the complete runtime-derived supported-tool catalog and presentation keys; the active subset may be smaller. |
| Consumers | Routine query consumers gain direct Markdown; consumers needing completeness continue using the same cache URI and DTO. |

## Risks and Verification Expectations

| Risk | Required evidence |
|---|---|
| Byte limiting corrupts UTF-8 or Markdown | Multibyte boundary tests and block-aware truncation tests. |
| Cache link disappears during truncation | Tests proving the cache URI and truncation notice remain inside the configured budget. |
| Collection templates drift from DTO fields | Startup/config alignment validation for collection and nested item placeholders. |
| Catalog, active tools, and presentation keys drift | Startup evidence for missing-template, unknown-key, and duplicate-registration failures; acceptance of the complete 50-tool catalog; and successful token and tokenless activation from the same presentation file. |
| A previously “unchanged” template remains under-informative | Field-level traceability showing an inline or justified cache-only decision for every tool-specific DTO field. |
| Rich summaries accidentally inline verbose logs | Representative `run_tests` and `run_quality_gates` tests for normal and verbose DTOs. |
| Nested plan rendering becomes tool-specific | Architecture review proving no tool-name branch exists. |
| Approved DTO clean breaks disrupt consumers | Public-contract tests cover every affected producer, service, manager, tool, presenter, and cached serialization; unaffected DTO contracts and cache publication remain stable. |
| Documentation reintroduces mandatory resource reads | Targeted review and local-link verification of the changed active documents. |

## Expected Results

- Routine discovery for work context, project plans, issue/PR lists, and detail views is actionable from one compact text response when the selected content fits.
- Verification tools expose concise evidence without inline tracebacks or verbose logs.
- Configured collections respect their item limit and preserve DTO order.
- Every `TextPresenter` result remains within 8,000 UTF-8 bytes while preserving a truncation notice and cache URI when content is omitted.
- Cached resources remain complete; their DTO schemas change only at the explicitly approved clean-break boundaries.
- Presentation configuration remains the source of truth for per-tool content choices and exactly covers the complete runtime-derived supported-tool catalog; known inactive tools do not block startup.
- All 50 tool templates are optimized against the field-level actionability audit; every cache-only field has an explicit rationale.
- No tool-specific presentation branches are introduced.
- Both obsolete documentation-test modules and all 62 collected cases are removed.

## Deferred Findings

### Structured quality-gate findings

The current RunQualityGatesOutput exposes each gate through GateResultDTO with name, passed, status, score, and one opaque details string. This issue deliberately keeps details and complete checker output cache-only because the presentation layer cannot reliably distinguish effective diagnostics from headers, summaries, or verbose process logs.

This leaves a known actionability gap: the compact run_quality_gates response can identify a failing gate, but it cannot present a bounded number of concrete errors without parsing gate-specific text.

**Deferred direction:**

- Investigate a structured GateFindingDTO or equivalent contract containing the gate, file, location, diagnostic code, and concise message.
- Determine whether findings belong per GateResultDTO or at RunQualityGatesOutput level.
- Add a configurable maximum for inline findings while keeping complete linter, type-checker, and process output cache-only.
- Preserve generic presentation; do not introduce gate-name-specific parsing or renderer branches.
- Treat any DTO and consumer impact as a new strategy decision in a dedicated issue.

**Disposition:** Explicitly out of scope for issue #456. Validation must carry this finding into deferred work, and Ready must include it in the PR body for post-merge triage by the coordination authority.

## Open Questions

None at the strategy boundary. The concrete minimal registration/catalog representation and activation interface belong to Design and remain constrained by the approved YAGNI boundary.

## Related Documentation

- [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)
- [Presentation Architecture](../../reference/presentation_architecture.md)
- [Tools Overview](../../reference/tools/README.md)
- [Discovery Tools](../../reference/tools/discovery.md)
- [Project Tools](../../reference/tools/project.md)
- [GitHub Tools](../../reference/tools/github.md)
- [Quality Tools](../../reference/tools/quality.md)
- [Scaffolding Tools](../../reference/tools/scaffolding.md)

## External References

- [GitHub Copilot CLI context management](https://docs.github.com/en/copilot/concepts/agents/copilot-cli/context-management)
- [Claude Code MCP output limits](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [Codex configurable tool-output limit discussion](https://github.com/openai/codex/issues/6426)
- [Codex historical/default limit follow-up](https://github.com/openai/codex/issues/7867)
- [Gemini CLI repository](https://github.com/google-gemini/gemini-cli)

---

## Version History

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-08-20 | Agent | Approved research, complete tool audit, and strategy boundary |
| 1.1 | 2026-08-20 | Agent | Add mandatory removal of brittle documentation tests to the approved scope |
| 1.2 | 2026-08-20 | Agent | Record structured quality-gate findings as explicit deferred work |
| 1.3 | 2026-08-21 | Agent | Reopen Research for exact registration/config parity and full optimization of all 50 presentation templates |
| 1.4 | 2026-08-21 | Agent | Approve structured get_work_context state enum and move all warning/recovery text into presentation configuration |
| 1.5 | 2026-08-21 | Agent | Inventory removable DTO presentation debt and separate structured duplicates from fields requiring upstream replacement |
| 1.6 | 2026-08-21 | Agent | Approve removal of all duplicate fields plus structured SafeEdit issues and numeric pytest duration replacement |
| 1.7 | 2026-08-21 | Agent | Normalize the final clean-break strategy, blast radius, evidence order, and expected results |
| 1.8 | 2026-08-21 | Agent | Approve runtime-derived complete-catalog parity with conditional activation and a strict YAGNI boundary |
